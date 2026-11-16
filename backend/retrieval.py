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
    """同疾病维度的证据优先

    RRF 只用了排名，没用到「这条证据属于哪个疾病」。
    当问题里的实体是疾病时，把同维度的切块加权，避免答糖尿病却引一堆高血压指南。
    """
    if not hint:
        return chunks
    for c in chunks:
        d = c.get("disease") or ""
        if d and (hint in d or d in hint):
            c["rrf"] = round((c.get("rrf") or 0) * 1.8, 6)
            c["boost"] = "disease_match"
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
