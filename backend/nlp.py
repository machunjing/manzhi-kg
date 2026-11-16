# -*- coding: utf-8 -*-
"""语料索引：TF-IDF 向量索引 + 实体名词典

启动时从 MySQL 载入 34,309 条切块，构建字符 n-gram TF-IDF；
结果缓存到 .cache/，切块数变了才重建。
"""
import os
import pickle
import re
import time

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

import config
import db

_state = {"ready": False, "chunks": [], "meta": {}, "vec": None, "mat": None,
          "entity_names": [], "entity_map": {}}
CACHE = os.path.join(config.CACHE_DIR, "index_v2.pkl")

# 中文停用词（少量高频虚词，避免它们把相似度拉平）
STOP = set("的 了 和 与 及 或 是 有 在 对 中 为 等 这 那 我 你 他 请 问 什么 哪些 怎么 如何 吗 呢 要 会 能 可以 一个 一种 以及 相关 情况 问题 需要 应该 是否 关于 哪些".split())


def _clean(t):
    t = re.sub(r"\s+", " ", t or "")
    return t.strip()


def build(force=False):
    t0 = time.time()
    n_chunk = db.scalar(config.DB_REAL, "SELECT COUNT(*) AS n FROM chunks")
    if not force and os.path.exists(CACHE):
        try:
            with open(CACHE, "rb") as f:
                obj = pickle.load(f)
            if obj.get("n_chunk") == n_chunk and "lookup" in obj.get("state", {}):
                _state.update(obj["state"])
                _state["ready"] = True
                print("[index] 载入缓存：%d 条切块，%.1fs" % (len(_state["chunks"]), time.time() - t0))
                return
        except Exception as e:
            print("[index] 缓存失效：%s" % e)

    print("[index] 从数据库重建索引（%d 条切块）..." % n_chunk)
    rows = db.query(config.DB_REAL, """
        SELECT c.id, c.doc_id, c.chunk_idx, c.disease, c.text,
               d.title, d.source, d.doc_type, d.pmid, d.journal, d.publish_date
        FROM chunks c JOIN documents d ON d.id = c.doc_id
    """)
    chunks, docs = [], []
    for r in rows:
        text = _clean(r["text"])
        if not text:
            continue
        chunks.append({
            "id": r["id"], "doc_id": r["doc_id"], "chunk_idx": r["chunk_idx"],
            "disease": r["disease"], "text": text, "title": r["title"],
            "source": r["source"], "doc_type": r["doc_type"],
            "pmid": r["pmid"], "journal": r["journal"],
            "date": r["publish_date"].strftime("%Y-%m-%d") if r["publish_date"] else None,
        })
        docs.append(text)

    vec = TfidfVectorizer(analyzer=config.TFIDF_ANALYZER,
                          ngram_range=config.TFIDF_NGRAM,
                          max_features=config.TFIDF_MAX_FEATURES,
                          sublinear_tf=True, min_df=2)
    mat = vec.fit_transform(docs)
    print("[index] TF-IDF 矩阵 %s，词表 %d" % (mat.shape, len(vec.vocabulary_)))

    # 实体名词典（长名优先匹配）
    ents = db.query(config.DB_REAL, "SELECT id, name, type FROM entities")
    names = sorted((e["name"] for e in ents if e["name"]), key=len, reverse=True)
    emap = {e["name"]: e for e in ents if e["name"]}

    # 别名并入词典：查询里写「脑卒中」也要能落到「中风」这个实体上
    aliases = db.query(config.DB_REAL,
                       "SELECT a.alias, e.id, e.name, e.type FROM entity_alias a "
                       "JOIN entities e ON e.id = a.entity_id")
    amap = {}
    for a in aliases:
        amap[a["alias"]] = {"id": a["id"], "name": a["name"], "type": a["type"]}
    lookup = list(emap.items()) + [(k, v) for k, v in amap.items() if k not in emap]
    lookup.sort(key=lambda x: len(x[0]), reverse=True)

    _state.update({
        "ready": True, "chunks": chunks, "vec": vec, "mat": mat,
        "entity_names": names, "entity_map": emap,
        "alias_map": amap, "lookup": lookup,
        "meta": {"n_chunk": len(chunks), "n_alias": len(amap),
                 "built_at": time.strftime("%Y-%m-%d %H:%M:%S")},
    })
    with open(CACHE, "wb") as f:
        pickle.dump({"n_chunk": n_chunk, "state": {k: _state[k] for k in
                     ("chunks", "vec", "mat", "entity_names", "entity_map",
                      "alias_map", "lookup", "meta")}}, f)
    print("[index] 完成，%.1fs" % (time.time() - t0))


def state():
    if not _state["ready"]:
        build()
    return _state


def vector_search(q, topk=None):
    """字符 n-gram TF-IDF 余弦相似度召回"""
    s = state()
    topk = topk or config.VEC_TOPK
    qv = s["vec"].transform([_clean(q)])
    sim = (s["mat"] @ qv.T).toarray().ravel()
    if not np.any(sim):
        return []
    idx = np.argpartition(-sim, min(topk, len(sim) - 1))[:topk]
    idx = idx[np.argsort(-sim[idx])]
    out = []
    for i in idx:
        if sim[i] <= 0:
            continue
        c = dict(s["chunks"][int(i)])
        c["score"] = float(sim[i])
        out.append(c)
    return out


def link_entities(q, limit=5):
    """实体链接：查询里出现的实体名或别名（长名优先，避免"糖尿病"吃掉"糖尿病肾病"）"""
    s = state()
    ql = q.lower()
    hits, used = [], []
    for key, ent in s["lookup"]:
        kl = key.lower()
        if len(kl) < 2:
            continue
        pos = ql.find(kl)
        if pos < 0:
            continue
        if any(p <= pos < p + l for p, l in used):
            continue
        used.append((pos, len(kl)))
        if all(h["id"] != ent["id"] for h in hits):
            hits.append(ent)
        if len(hits) >= limit:
            break
    return hits


def resolve(name):
    """把用户写的名字解析成实体：原名 -> 别名 -> 模糊匹配"""
    s = state()
    if name in s["entity_map"]:
        return s["entity_map"][name]
    if name in s["alias_map"]:
        return s["alias_map"][name]
    row = db.one(config.DB_REAL,
                 "SELECT id,name,type FROM entities WHERE name LIKE %s LIMIT 1",
                 ("%" + name + "%",))
    return row
