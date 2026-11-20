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
               r.relation rel, t.id tid, t.name tname, t.type ttype
        FROM relations r
        JOIN entities h ON h.id = r.head_id
        JOIN entities t ON t.id = r.tail_id
        WHERE r.head_id IN (%s)
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
