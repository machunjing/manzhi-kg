# -*- coding: utf-8 -*-
"""三路检索 + RRF 融合

路线：
  1. 关键词路  MySQL ngram 全文索引（近似 BM25 的词频打分）
  2. 向量路    字符 2~3-gram TF-IDF 余弦（不依赖分词，中英文都能用）
  3. 图谱路    实体链接 -> 邻居实体 -> 命中这些实体的切块（实体感知召回）

三路各自排序后用 RRF（Reciprocal Rank Fusion）融合，避免不同分数量纲不可比的问题。
"""
import re

import config
import db
import nlp

_SPECIAL = re.compile(r'[+\-<>()~*"@,;:!?\[\]{}|\\/]')

# 疑问词/虚词：中文检索前先摘掉，剩下的才是检索词
STOP_PHRASES = [
    "有哪些", "有什么", "是什么", "什么是", "怎么样", "为什么", "哪些", "哪个",
    "怎么", "如何", "是否", "可以", "需要", "应该", "常见", "一般", "主要",
    "相关", "介绍", "一下", "请问", "告诉我", "我想知道", "请", "的", "了",
    "吗", "呢", "和", "与", "及", "或", "在", "对", "中", "为", "等", "这",
    "那", "我", "你", "他", "能", "会", "要", "有", "都", "是",
]


def _safe(q):
    return _SPECIAL.sub(" ", q or "").strip()


def terms(q):
    """把自然语言问题拆成检索词（不做分词，靠停用词切段）"""
    s = _safe(q)
    for w in sorted(STOP_PHRASES, key=len, reverse=True):
        s = s.replace(w, " ")
    s = re.sub(r"\s+", " ", s).strip()
    out = []
    for p in s.split(" "):
        if not p:
            continue
        if re.search(r"[A-Za-z]", p):
            out += [w for w in re.findall(r"[A-Za-z][A-Za-z\-]+", p) if len(w) >= 2]
        elif len(p) >= 2:
            out.append(p)
    return list(dict.fromkeys(out))


def keyword_search(q, topk=None):
    """关键词路：MySQL 全文索引，按 MATCH 相关度排序

    注意：直接把整句丢进 BOOLEAN MODE 会被当成短语，中文几乎必然 0 命中，
    所以先拆词再用引号逐个 OR。
    """
    topk = topk or config.BM25_TOPK
    ts = terms(q)[:8]
    if not ts:
        return []
    expr = " ".join('"%s"' % t for t in ts)
    rows = db.query(config.DB_REAL, """
        SELECT c.id, c.doc_id, c.chunk_idx, c.disease, c.text,
               d.title, d.source, d.doc_type, d.pmid, d.journal, d.publish_date,
               MATCH(c.text) AGAINST(%s IN BOOLEAN MODE) AS score
        FROM chunks c JOIN documents d ON d.id = c.doc_id
        WHERE MATCH(c.text) AGAINST(%s IN BOOLEAN MODE)
        ORDER BY score DESC LIMIT %s
    """, (expr, expr, topk))
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "doc_id": r["doc_id"], "chunk_idx": r["chunk_idx"],
            "disease": r["disease"], "text": r["text"], "title": r["title"],
            "source": r["source"], "doc_type": r["doc_type"], "pmid": r["pmid"],
            "journal": r["journal"],
            "date": r["publish_date"].strftime("%Y-%m-%d") if r["publish_date"] else None,
            "score": float(r["score"]),
        })
    return out


def vector_search(q, topk=None):
    """向量路：TF-IDF 余弦"""
    return nlp.vector_search(q, topk or config.VEC_TOPK)


def graph_facts(entities, per_entity=8, prefer_rel=None):
    """图谱路（事实侧）：实体的一跳出边

    只取「实体 -> X」的出边，因为关系语义是有方向的（疾病 -> 并发症/药物/症状）。
    如果实体只有入边（例如某个症状只出现在别人的关系里），再退化为入边并标注反向。
    prefer_rel：问题意图对应的关系类型，优先返回（问并发症就先把并发症挑出来）。
    """
    if not entities:
        return []
    ids = [e["id"] for e in entities]
    ph = ",".join(["%s"] * len(ids))
    rows = db.query(config.DB_REAL, """
        SELECT h.id hid, h.name hname, h.type htype,
               r.relation rel, t.id tid, t.name tname, t.type ttype,
               t.rel_count trels
        FROM relations r
        JOIN entities h ON h.id = r.head_id
        JOIN entities t ON t.id = r.tail_id
        WHERE r.head_id IN (%s)
        -- 尾巴按热度排：OpenCMKG 里「白细胞介素4」「血清白细胞介素3」这类罕见指标
        -- 和图谱连通度高的「血压」「糖化血红蛋白」混在一起，不排序就会挤掉常用指标
        ORDER BY t.rel_count DESC
        LIMIT 300
    """ % ph, ids)

    grouped = {}
    for r in rows:
        if r["hname"] == r["tname"]:        # OpenCMKG 里有「肥胖 并发症 肥胖」这类自环
            continue
        grouped.setdefault(r["hname"], []).append({
            "relation": r["rel"], "head": r["hname"], "head_type": r["htype"],
            "tail": r["tname"], "tail_type": r["ttype"], "direction": "out",
        })

    # 没有任何出边的实体，退回入边（标注为「被…关联」）
    missing = [e for e in entities if e["name"] not in grouped]
    if missing:
        mids = [e["id"] for e in missing]
        mph = ",".join(["%s"] * len(mids))
        rows2 = db.query(config.DB_REAL, """
            SELECT h.name hname, h.type htype, r.relation rel,
                   t.name tname, t.type ttype
            FROM relations r JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id
            WHERE r.tail_id IN (%s) LIMIT 100
        """ % mph, mids)
        for r in rows2:
            if r["hname"] == r["tname"]:
                continue
            grouped.setdefault(r["tname"], []).append({
                "relation": r["rel"], "head": r["hname"], "head_type": r["htype"],
                "tail": r["tname"], "tail_type": r["ttype"], "direction": "in",
            })

    facts = []
    for name, items in grouped.items():
        # 意图对应的关系类型排前面
        if prefer_rel:
            items = sorted(items, key=lambda x: (x["relation"] != prefer_rel, x["relation"]))
        seen, picked = set(), []
        for it in items:
            k = (it["relation"], it["head"], it["tail"])
            if k in seen:
                continue
            seen.add(k)
            picked.append(it)
            if len(picked) >= per_entity:
                break
        facts.append({"entity": name, "relations": picked})
    return facts


def graph_search(entities, topk=None):
    """图谱路（证据侧）：找提到这些实体及其邻居的切块"""
    topk = topk or config.GRAPH_TOPK
    if not entities:
        return []
    names = [e["name"] for e in entities]
    # 邻居实体名一起作为检索词
    ph = ",".join(["%s"] * len(entities))
    ids = [e["id"] for e in entities]
    nb = db.query(config.DB_REAL, """
        SELECT DISTINCT t.name AS name FROM relations r JOIN entities t ON t.id=r.tail_id
        WHERE r.head_id IN (%s) LIMIT 12
    """ % ph, ids)
    names += [r["name"] for r in nb]
    names = [n for n in dict.fromkeys(names) if n and len(n) >= 2][:16]

    expr = " ".join('"%s"' % _safe(n) for n in names)
    rows = db.query(config.DB_REAL, """
        SELECT c.id, c.doc_id, c.chunk_idx, c.disease, c.text,
               d.title, d.source, d.doc_type, d.pmid, d.journal, d.publish_date,
               MATCH(c.text) AGAINST(%s IN BOOLEAN MODE) AS score
        FROM chunks c JOIN documents d ON d.id = c.doc_id
        WHERE MATCH(c.text) AGAINST(%s IN BOOLEAN MODE)
        ORDER BY score DESC LIMIT %s
    """, (expr, expr, topk))
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "doc_id": r["doc_id"], "chunk_idx": r["chunk_idx"],
            "disease": r["disease"], "text": r["text"], "title": r["title"],
            "source": r["source"], "doc_type": r["doc_type"], "pmid": r["pmid"],
            "journal": r["journal"],
            "date": r["publish_date"].strftime("%Y-%m-%d") if r["publish_date"] else None,
            "score": float(r["score"]),
        })
    return out


# ---------------------------------------------------------------- 跨语言路
# 中文提问检索英文摘要：没有大模型时用这张小词典兜底，常见疾病仍能跨语言召回
ZH2EN = {
    "糖尿病": "diabetes mellitus", "2型糖尿病": "type 2 diabetes mellitus",
    "1型糖尿病": "type 1 diabetes", "高血压": "hypertension", "血脂异常": "dyslipidemia",
    "高脂血症": "hyperlipidemia", "肥胖": "obesity", "脑卒中": "stroke",
    "中风": "stroke", "冠心病": "coronary heart disease", "肾病": "nephropathy",
    "糖尿病肾病": "diabetic nephropathy", "视网膜病变": "retinopathy",
    "神经病变": "neuropathy", "并发症": "complication", "症状": "symptom",
    "治疗": "treatment", "药物": "drug therapy", "危险因素": "risk factor",
    "诊断": "diagnosis", "血糖": "blood glucose", "胰岛素": "insulin",
    "饮食": "diet", "运动": "exercise", "血压": "blood pressure",
    "心血管": "cardiovascular", "慢性肾脏病": "chronic kidney disease",
    # 图谱里高频、但指南正文少见的中文实体，补上英文才能在英文摘要里找到证据
    "脂肪肝": "fatty liver", "非酒精性脂肪肝": "nonalcoholic fatty liver",
    "动脉粥样硬化": "atherosclerosis", "酮症酸中毒": "ketoacidosis",
    "糖尿病足": "diabetic foot", "微量白蛋白尿": "microalbuminuria",
    "蛋白尿": "proteinuria", "吸烟": "smoking", "饮酒": "alcohol consumption",
    "高尿酸血症": "hyperuricemia", "痛风": "gout", "心肌梗死": "myocardial infarction",
    "心力衰竭": "heart failure", "心房颤动": "atrial fibrillation",
    "肾衰竭": "renal failure", "妊娠期糖尿病": "gestational diabetes",
}
INTENT_EN = {
    "治疗/用药": "treatment", "症状表现": "clinical manifestation", "检查监测": "monitoring",
    "并发症": "complication", "饮食干预": "diet intervention", "概念解释": "overview",
}


def _fallback_terms(entities, intent_name):
    """没有大模型时的英文检索式：实体名 + 意图词"""
    ts = []
    for e in entities or []:
        en = ZH2EN.get(e["name"])
        if en:
            ts.append(en)
    if intent_name and INTENT_EN.get(intent_name):
        ts.append(INTENT_EN[intent_name])
    return ts


def cross_lingual_search(terms, topk=None):
    """跨语言路：拿英文检索式去查英文摘要（关键词 + 向量各取一半，再内部融合）"""
    topk = topk or config.CROSS_TOPK
    terms = [t for t in (terms or []) if t and len(t) >= 3]
    if not terms:
        return []
    expr = " ".join('"%s"' % _safe(t) for t in terms[:6])
    rows = db.query(config.DB_REAL, """
        SELECT c.id, c.doc_id, c.chunk_idx, c.disease, c.text,
               d.title, d.source, d.doc_type, d.pmid, d.journal, d.publish_date,
               MATCH(c.text) AGAINST(%s IN BOOLEAN MODE) AS score
        FROM chunks c JOIN documents d ON d.id = c.doc_id
        WHERE MATCH(c.text) AGAINST(%s IN BOOLEAN MODE)
        ORDER BY score DESC LIMIT %s
    """, (expr, expr, topk))
    out = []
    for i, r in enumerate(rows, 1):
        out.append({
            "id": r["id"], "doc_id": r["doc_id"], "chunk_idx": r["chunk_idx"],
            "disease": r["disease"], "text": r["text"], "title": r["title"],
            "source": r["source"], "doc_type": r["doc_type"], "pmid": r["pmid"],
            "journal": r["journal"],
            "date": r["publish_date"].strftime("%Y-%m-%d") if r["publish_date"] else None,
            "score": float(r["score"]),
            "rrf": round(1.0 / (config.RRF_K + i), 6),
        })
    vec = nlp.vector_search(" ".join(terms[:4]), topk)
    have = {o["id"] for o in out}
    for i, v in enumerate(vec, 1):
        if v["id"] in have:
            continue
        v["rrf"] = round(1.0 / (config.RRF_K + i), 6)
        out.append(v)
    return out


def bilingual_select(cn_pool, en_pool, n=None, cn_ratio=0.5):
    """中英双语均衡取证

    中文语料只有 6 篇指南，英文摘要有 4,000+ 篇。直接 RRF 融合时，
    中文切块能同时命中关键词/向量/图谱三路、票数天然更高，英文证据永远进不了前 8。
    这里按比例各取一半：中文指南给「规范说法」，英文文献给「研究证据」。
    """
    n = n or config.FINAL_TOPK
    k = max(1, int(round(n * cn_ratio)))
    out, seen = [], set()
    for c in cn_pool[:k]:
        out.append(c)
        seen.add(c["id"])
    for c in en_pool:
        if len(out) >= n:
            break
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append(c)
    for c in cn_pool:                      # 英文不够时用中文回填
        if len(out) >= n:
            break
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append(c)
    return out


def _best_pair(text, a, b, limit=40):
    """返回 a、b 距离最近的一对出现位置；任一方不出现返回 None"""
    pa, i = [], text.find(a)
    while i >= 0 and len(pa) < limit:
        pa.append(i)
        i = text.find(a, i + 1)
    pb, j = [], text.find(b)
    while j >= 0 and len(pb) < limit:
        pb.append(j)
        j = text.find(b, j + 1)
    best = None
    for x in pa:
        for y in pb:
            d = abs(x - y)
            if best is None or d < best[0]:
                best = (d, x, y)
    return best


def _window(text, head, tail, width=170, max_gap=220):
    """截出两个实体挨得最近的那一段；挨不到一起就认为这一段不算共现

    不能只取第一个命中位置：一段里「高血压」出现十几次、「中风」只出现一次，
    按首次出现截窗会整段都在讲血压测量，读者根本看不出这条关系从哪来。
    """
    if not text:
        return ""
    pair = _best_pair(text, head, tail)
    if pair is None or pair[0] > max_gap:
        return ""
    _, i, j = pair
    center = (i + j) // 2
    start = max(0, min(center - width // 2, max(0, len(text) - width)))
    seg = text[start:start + width].strip()
    return ("…" if start > 0 else "") + seg + ("…" if start + width < len(text) else "")


def _cooccur(expr):
    try:
        return int(db.scalar(config.DB_REAL,
                             "SELECT COUNT(*) FROM chunks WHERE MATCH(text) AGAINST(%s IN BOOLEAN MODE)",
                             (expr,)) or 0)
    except Exception:
        return 0


def evidence_for(head, tail, topk=1, exclude=None, scan=20):
    """给一条图谱三元组回文献库找「原文支撑句」

    关系表的 snippet 在 OpenCMKG 侧是空的（结构化三元组本来就没有原文），
    所以反过来做：拿头尾两个实体名同时进 ngram 全文索引捞切块。
    注意 ngram 布尔模式下空格是 OR，要 AND 必须每个词前加 +，
    否则「脂肪肝 高血压」会把只讲血压的段落也捞回来。

    中文指南只有 6 篇，很多实体在中文语料里根本不同框，
    所以第一轮没结果时用 ZH2EN 换成英文，去 4,000+ 篇英文摘要里再找一次。

    返回 (命中片段列表, 共现段数)
    """
    exclude = exclude or set()
    plans = []
    if head and tail:
        plans.append((head, tail, '+"%s" +"%s"' % (_safe(head), _safe(tail))))
    eh, et = ZH2EN.get(head), ZH2EN.get(tail)
    if eh and et and eh != head:
        plans.append((eh, et, '+"%s" +"%s"' % (_safe(eh), _safe(et))))

    for qa, qb, expr in plans:
        try:
            rows = db.query(config.DB_REAL, """
                SELECT c.id cid, c.doc_id, c.chunk_idx, c.text, d.title, d.source,
                       d.journal, d.publish_date, d.doc_type, d.pmid,
                       MATCH(c.text) AGAINST(%s IN BOOLEAN MODE) AS score
                FROM chunks c JOIN documents d ON d.id = c.doc_id
                WHERE MATCH(c.text) AGAINST(%s IN BOOLEAN MODE)
                ORDER BY score DESC LIMIT %s
            """, (expr, expr, scan))
        except Exception:
            continue

        out = []
        for r in rows:
            if r["cid"] in exclude:
                continue
            snip = _window(r["text"], qa, qb)
            if not snip:
                continue
            out.append({
                "chunk_id": r["cid"], "doc_id": r["doc_id"], "chunk_idx": r["chunk_idx"],
                "title": r["title"], "source": r["source"], "journal": r["journal"],
                "doc_type": r["doc_type"], "pmid": r["pmid"],
                "date": r["publish_date"].strftime("%Y-%m-%d") if r["publish_date"] else None,
                "snippet": snip, "lang": "en" if qa != head else "zh",
                "score": round(float(r["score"]), 4),
            })
            if len(out) >= topk:
                break
        if out:
            return out, _cooccur(expr)
    return [], 0


def rrf(ranked_lists, k=None, topk=None):
    """Reciprocal Rank Fusion：score = Σ 1/(k + rank)"""
    k = k or config.RRF_K
    topk = topk or config.FINAL_TOPK
    acc, store = {}, {}
    for name, items in ranked_lists:
        for rank, it in enumerate(items, 1):
            cid = it["id"]
            acc[cid] = acc.get(cid, 0.0) + 1.0 / (k + rank)
            if cid not in store:
                store[cid] = dict(it, routes=[])
            store[cid]["routes"].append({"route": name, "rank": rank})
    order = sorted(acc.items(), key=lambda x: -x[1])[:topk]
    out = []
    for cid, score in order:
        item = store[cid]
        item["rrf"] = round(score, 6)
        out.append(item)
    return out


def rerank_disease(chunks, hint):
    """同疾病维度的证据优先，跨疾病的证据降权

    RRF 只用了排名，没用到「这条证据属于哪个疾病」。
    问糖尿病并发症时，高血压指南里恰好提到「糖尿病」的段落会冲上来，
    读起来就是「答非所问」，所以同维度加权、异维度轻微降权。
    """
    if not hint:
        return chunks
    for c in chunks:
        d = c.get("disease") or ""
        if not d or d == "通用":
            continue
        if hint in d or d in hint:
            c["rrf"] = round((c.get("rrf") or 0) * 1.8, 6)
            c["boost"] = "disease_match"
        else:
            c["rrf"] = round((c.get("rrf") or 0) * 0.65, 6)
            c["boost"] = "disease_mismatch"
    return sorted(chunks, key=lambda x: -(x.get("rrf") or 0))


def rerank_intent(chunks, keywords):
    """意图词命中的证据优先

    问「并发症」时，含「并发症/合并症」的切块比泛泛提到疾病的更贴题。
    """
    if not keywords:
        return chunks
    for c in chunks:
        t = c.get("text") or ""
        hit = sum(1 for k in keywords if k in t)
        if hit:
            c["rrf"] = round((c.get("rrf") or 0) * (1.0 + 0.45 * min(hit, 3)), 6)
            c["boost"] = (c.get("boost") or "") + "+intent"
    return sorted(chunks, key=lambda x: -(x.get("rrf") or 0))
