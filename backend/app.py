# -*- coding: utf-8 -*-
"""慢知 · 慢性病智能知识服务平台 —— Flask 后端

启动：py -3.8-64 backend/app.py
接口前缀：/api，统一响应 {code, message, data}
"""
import time
import traceback

from flask import Flask, Response, request
from werkzeug.exceptions import HTTPException

import config
import db
import nlp
import retrieval
import answer as answer_mod

app = Flask(__name__)

ROUTES = []   # 启动后自动收集，首页和 /api 都用它


# ---------------------------------------------------------------- 通用
@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return resp


def ok(data=None, msg="ok"):
    # 自己序列化，保证 Decimal / datetime 不炸
    return Response(db.dumps({"code": 0, "message": msg, "data": data}),
                    mimetype="application/json")


def fail(code, msg, http=200):
    return Response(db.dumps({"code": code, "message": msg, "data": None}),
                    status=http, mimetype="application/json")


@app.errorhandler(Exception)
def on_error(e):
    # 404/405 这类是客户端问题，别报成服务异常
    if isinstance(e, HTTPException):
        mapping = {404: (40400, "接口不存在"), 405: (40001, "请求方法不允许")}
        code, msg = mapping.get(e.code, (40001, e.description))
        return fail(code, "%s：%s" % (msg, request.path), e.code or 400)
    traceback.print_exc()
    return fail(50000, "服务异常：%s" % e, 500)


@app.route("/")
def index():
    """根路径给一个自检页面，省得打开就是 404"""
    s = nlp.state()
    groups = {}
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        p = str(rule)
        if not p.startswith("/api"):
            continue
        mod = p.split("/")[2] if len(p.split("/")) > 2 else "other"
        groups.setdefault(mod, []).append({
            "path": p,
            "methods": ",".join(sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS"))),
        })
    rows = []
    for mod, items in groups.items():
        for it in items:
            rows.append(
                '<tr><td class="m">%s</td><td class="p"><a href="%s">%s</a></td></tr>'
                % (it["methods"], it["path"], it["path"]) if it["methods"] == "GET"
                else '<tr><td class="m">%s</td><td class="p">%s</td></tr>'
                % (it["methods"], it["path"]))
    html = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>慢知 · 后端服务</title><style>
body{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:#f6f8fa;color:#1f2328;margin:0;padding:32px}
.card{max-width:900px;margin:0 auto 20px;background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:24px 28px}
h1{font-size:20px;margin:0 0 6px}.sub{color:#656d76;font-size:13px;margin-bottom:18px}
.kv{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.kv div{background:#eef6ff;border:1px solid #c8e1ff;border-radius:6px;padding:8px 12px;font-size:13px}
b{color:#0969da}table{width:100%%;border-collapse:collapse;font-size:13px}
td{padding:7px 8px;border-bottom:1px solid #eaeef2}.m{width:80px;color:#8250df;font-family:monospace}
.p{font-family:monospace}a{color:#0969da;text-decoration:none}a:hover{text-decoration:underline}
code{background:#eff2f5;padding:2px 5px;border-radius:4px;font-size:12px}
</style></head><body>
<div class="card"><h1>慢知 · 慢性病智能知识服务平台</h1>
<div class="sub">后端服务运行中 · Flask + MySQL · 统一响应 <code>{code, message, data}</code></div>
<div class="kv">
  <div>切块 <b>%d</b></div><div>实体 <b>%d</b></div><div>别名 <b>%d</b></div>
  <div>真实库 <b>%s</b></div><div>演示库 <b>%s</b></div>
</div>
<div class="sub">问答接口是 POST，用下面的命令试：<br>
<code>curl -X POST http://127.0.0.1:%d/api/qa/ask -H "Content-Type: application/json" -d "{\\"question\\":\\"糖尿病有哪些并发症\\"}"</code></div>
</div>
<div class="card"><h1 style="font-size:16px">接口清单（%d 个）</h1><table>%s</table></div>
</body></html>""" % (len(s["chunks"]), len(s["entity_names"]), len(s.get("alias_map") or {}),
                     config.DB_REAL, config.DB_DEMO, config.PORT,
                     sum(len(v) for v in groups.values()), "".join(rows))
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/api")
def api_index():
    """JSON 版的接口清单，给前端/调试用"""
    out = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        p = str(rule)
        if not p.startswith("/api"):
            continue
        out.append({"path": p,
                    "methods": sorted(m for m in rule.methods if m not in ("HEAD", "OPTIONS")),
                    "endpoint": rule.endpoint})
    return ok({"count": len(out), "routes": out})


@app.route("/api/system/health")
def health():
    s = nlp.state()
    return ok({
        "status": "up",
        "chunks_indexed": len(s["chunks"]),
        "entities_indexed": len(s["entity_names"]),
        "aliases_indexed": len(s.get("alias_map") or {}),
        "built_at": s["meta"].get("built_at"),
        "db_real": config.DB_REAL,
        "db_demo": config.DB_DEMO,
    })


# ---------------------------------------------------------------- 智能问答
@app.route("/api/qa/ask", methods=["POST", "OPTIONS"])
def qa_ask():
    if request.method == "OPTIONS":
        return ok()
    body = request.get_json(silent=True) or {}
    q = (body.get("question") or "").strip()
    if not q:
        return fail(40001, "question 不能为空")

    t0 = time.time()
    entities = nlp.link_entities(q, limit=3)
    intent = answer_mod.detect_intent(q)
    kw = retrieval.keyword_search(q)
    vec = retrieval.vector_search(q)
    gph = retrieval.graph_search(entities)
    facts = retrieval.graph_facts(entities, prefer_rel=intent["rel"])
    fused = retrieval.rrf([("关键词路", kw), ("向量路", vec), ("图谱路", gph)])

    # 疾病维度 + 意图词的证据优先
    disease_hint = None
    for e in entities:
        if e["type"] == "疾病":
            disease_hint = e["name"]
            break
    fused = retrieval.rerank_disease(fused, disease_hint)
    fused = retrieval.rerank_intent(fused, intent["keywords"])

    out = answer_mod.compose(q, entities, facts, fused, intent)
    out["question"] = q
    out["entities"] = entities
    out["graph_facts"] = facts
    out["retrieval"] = {
        "keyword": len(kw), "vector": len(vec), "graph": len(gph),
        "fused": len(fused), "rrf_k": config.RRF_K,
    }
    out["elapsed_ms"] = int((time.time() - t0) * 1000)
    return ok(out)


# ---------------------------------------------------------------- 知识图谱
def _graph_data(name, depth=1, limit=120):
    """取以 name 为中心的子图；返回 (data, err)"""
    if not name:
        return None, "entity 不能为空"
    row = nlp.resolve(name)
    if not row:
        return None, "实体不存在：%s" % name

    nodes = {row["id"]: {"id": row["id"], "name": row["name"], "type": row["type"],
                         "category": row["type"], "depth": 0}}
    links = []
    frontier = [row["id"]]
    for d in range(1, depth + 1):
        if not frontier:
            break
        ph = ",".join(["%s"] * len(frontier))
        rows = db.query(config.DB_REAL, """
            SELECT r.relation, h.id hid, h.name hname, h.type htype,
                   t.id tid, t.name tname, t.type ttype
            FROM relations r JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id
            WHERE r.head_id IN (%s) OR r.tail_id IN (%s) LIMIT %s
        """ % (ph, ph, limit), frontier + frontier)
        nxt = []
        for r in rows:
            for eid, enm, ety in ((r["hid"], r["hname"], r["htype"]),
                                  (r["tid"], r["tname"], r["ttype"])):
                if eid not in nodes:
                    nodes[eid] = {"id": eid, "name": enm, "type": ety,
                                  "category": ety, "depth": d}
                    nxt.append(eid)
            links.append({"source": r["hid"], "target": r["tid"], "relation": r["relation"]})
        frontier = nxt[:40]

    seen, uniq = set(), []
    for l in links:
        k = (l["source"], l["target"], l["relation"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(l)
    return {"center": nodes[row["id"]], "nodes": list(nodes.values()),
            "links": uniq[:limit], "depth": depth}, None


@app.route("/api/kg/graph")
def kg_graph():
    name = (request.args.get("entity") or "").strip()
    depth = min(int(request.args.get("depth") or 1), 2)
    limit = min(int(request.args.get("limit") or 120), 300)
    data, err = _graph_data(name, depth, limit)
    if err:
        return fail(40001 if "不能为空" in err else 40400, err)
    return ok(data)


@app.route("/api/kg/entities")
def kg_entities():
    kw = (request.args.get("keyword") or "").strip()
    typ = (request.args.get("type") or "").strip()
    page = max(int(request.args.get("page") or 1), 1)
    size = min(int(request.args.get("pageSize") or 20), 100)
    where, args = [], []
    if kw:
        where.append("name LIKE %s")
        args.append("%" + kw + "%")
    if typ:
        where.append("type=%s")
        args.append(typ)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    total = db.scalar(config.DB_REAL, "SELECT COUNT(*) AS n FROM entities %s" % w, args)
    rows = db.query(config.DB_REAL,
                    "SELECT id,name,type,standard_name,source,status,confidence "
                    "FROM entities %s ORDER BY id LIMIT %s OFFSET %s" % (w, size, (page - 1) * size),
                    args)
    return ok({"list": rows, "total": total, "page": page, "pageSize": size})


@app.route("/api/kg/types")
def kg_types():
    rows = db.query(config.DB_REAL,
                    "SELECT type, COUNT(*) AS cnt FROM entities GROUP BY type ORDER BY cnt DESC")
    return ok(rows)


# ---------------------------------------------------------------- 文献
@app.route("/api/docs/search")
def docs_search():
    kw = (request.args.get("keyword") or "").strip()
    disease = (request.args.get("disease") or "").strip()
    page = max(int(request.args.get("page") or 1), 1)
    size = min(int(request.args.get("pageSize") or 20), 100)
    where, args = [], []
    if kw:
        where.append("(title LIKE %s OR abstract LIKE %s)")
        args += ["%" + kw + "%"] * 2
    if disease:
        where.append("disease=%s")
        args.append(disease)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    total = db.scalar(config.DB_REAL, "SELECT COUNT(*) AS n FROM documents %s" % w, args)
    rows = db.query(config.DB_REAL,
                    "SELECT id,pmid,title,journal,doc_type,disease,source,publish_date,"
                    "chunk_count,doi,url,LEFT(abstract,200) AS abstract_brief "
                    "FROM documents %s ORDER BY publish_date DESC, id LIMIT %s OFFSET %s"
                    % (w, size, (page - 1) * size), args)
    return ok({"list": rows, "total": total, "page": page, "pageSize": size})


@app.route("/api/docs/<doc_id>")
def docs_detail(doc_id):
    row = db.one(config.DB_REAL, "SELECT * FROM documents WHERE id=%s", (doc_id,))
    if not row:
        return fail(40400, "文献不存在")
    chunks = db.query(config.DB_REAL,
                      "SELECT id,chunk_idx,text_len,LEFT(text,300) AS text "
                      "FROM chunks WHERE doc_id=%s ORDER BY chunk_idx LIMIT 20", (doc_id,))
    row["chunks"] = chunks
    return ok(row)


# ---------------------------------------------------------------- 关系审核（演示库）
@app.route("/api/review/pending")
def review_pending():
    page = max(int(request.args.get("page") or 1), 1)
    size = min(int(request.args.get("pageSize") or 20), 100)
    total = db.scalar(config.DB_DEMO, "SELECT COUNT(*) AS n FROM v_pending_review")
    rows = db.query(config.DB_DEMO,
                    "SELECT * FROM v_pending_review ORDER BY confidence DESC LIMIT %s OFFSET %s"
                    % (size, (page - 1) * size))
    return ok({"list": rows, "total": total, "page": page, "pageSize": size})


@app.route("/api/review/<rel_id>/<action>", methods=["POST", "OPTIONS"])
def review_action(rel_id, action):
    if request.method == "OPTIONS":
        return ok()
    mapping = {"approve": "已审核", "reject": "已驳回", "hold": "待审核"}
    if action not in mapping:
        return fail(40001, "不支持的动作：%s" % action)
    target = mapping[action]
    cur = db.one(config.DB_DEMO, "SELECT id,status FROM relations WHERE id=%s", (rel_id,))
    if not cur:
        return fail(40400, "关系不存在：%s" % rel_id)
    try:
        db.execute(config.DB_DEMO,
                   "UPDATE relations SET status=%s, reviewer=%s, reviewed_at=NOW() WHERE id=%s",
                   (target, (request.get_json(silent=True) or {}).get("reviewer") or "管理员", rel_id))
    except Exception as e:
        # 触发器拦截非法流转时抛出 1644
        return fail(40900, "状态流转被拒绝：%s" % str(e).split(":")[-1].strip())
    after = db.one(config.DB_DEMO, "SELECT status FROM relations WHERE id=%s", (rel_id,))
    return ok({"id": rel_id, "from": cur["status"], "to": after["status"]})


@app.route("/api/review/stats")
def review_stats():
    return ok(db.query(config.DB_DEMO, "SELECT * FROM v_review_stats"))


# ---------------------------------------------------------------- 统计
@app.route("/api/stats/overview")
def stats_overview():
    real = config.DB_REAL
    return ok({
        "documents": db.scalar(real, "SELECT COUNT(*) AS n FROM documents"),
        "chunks": db.scalar(real, "SELECT COUNT(*) AS n FROM chunks"),
        "entities": db.scalar(real, "SELECT COUNT(*) AS n FROM entities"),
        "relations": db.scalar(real, "SELECT COUNT(*) AS n FROM relations"),
        "guides": db.scalar(real, "SELECT COUNT(*) AS n FROM documents WHERE source='本地指南文件'"),
        "by_source": db.query(real, "SELECT source, COUNT(*) AS cnt FROM documents GROUP BY source"),
        "by_disease": db.query(real, "SELECT disease, COUNT(*) AS cnt FROM documents GROUP BY disease ORDER BY cnt DESC"),
        "entity_types": db.query(real, "SELECT type, COUNT(*) AS cnt FROM entities GROUP BY type ORDER BY cnt DESC"),
        "relation_types": db.query(real, "SELECT relation, COUNT(*) AS cnt FROM relations GROUP BY relation ORDER BY cnt DESC"),
    })


# ---------------------------------------------------------------- 关联分析
@app.route("/api/analysis/network")
def analysis_network():
    name = (request.args.get("entity") or "糖尿病").strip()
    depth = min(int(request.args.get("depth") or 2), 3)
    data, err = _graph_data(name, depth, 200)
    if err:
        return fail(40400, err)
    from collections import Counter
    dist = Counter(n["depth"] for n in data["nodes"])
    data["hop_dist"] = [{"depth": k, "count": v} for k, v in sorted(dist.items())]
    return ok(data)


@app.route("/api/analysis/path")
def analysis_path():
    src = (request.args.get("from") or "").strip()
    dst = (request.args.get("to") or "").strip()
    maxlen = min(int(request.args.get("maxLen") or 5), 6)
    if not src or not dst:
        return fail(40001, "from / to 不能为空")
    a = nlp.resolve(src)
    b = nlp.resolve(dst)
    if not a or not b:
        return fail(40400, "实体不存在：%s" % (src if not a else dst))

    # 逐层 BFS（每层一条 SQL，避免把 28 万条关系读进内存）
    parent = {a["id"]: None}
    frontier = [a["id"]]
    found = False
    for _ in range(maxlen):
        if not frontier or found:
            break
        ph = ",".join(["%s"] * len(frontier))
        rows = db.query(config.DB_REAL, """
            SELECT h.id hid, h.name hname, h.type htype,
                   t.id tid, t.name tname, t.type ttype, r.relation rel
            FROM relations r JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id
            WHERE r.head_id IN (%s) OR r.tail_id IN (%s)
        """ % (ph, ph), frontier + frontier)
        nxt = []
        for r in rows:
            for x, y in ((r["hid"], r["tid"]), (r["tid"], r["hid"])):
                if x in parent and y not in parent:
                    parent[y] = (x, r["rel"])
                    nxt.append(y)
                    if y == b["id"]:
                        found = True
        frontier = nxt[:200]
    if b["id"] not in parent:
        return ok({"found": False, "from": a, "to": b, "path": [], "hops": None})

    # 回溯
    chain = []
    cur = b["id"]
    while parent[cur]:
        prev, rel = parent[cur]
        chain.append((prev, rel, cur))
        cur = prev
    chain.reverse()
    ids = [a["id"]] + [c[2] for c in chain]
    ph = ",".join(["%s"] * len(ids))
    info = {r["id"]: r for r in db.query(
        config.DB_REAL, "SELECT id,name,type FROM entities WHERE id IN (%s)" % ph, ids)}
    path = [{"node": info[a["id"]], "relation": None}]
    for prev, rel, cur in chain:
        path.append({"relation": rel, "node": info[cur]})
    return ok({"found": True, "from": a, "to": b, "path": path, "hops": len(chain)})


# ---------------------------------------------------------------- 启动
def warmup():
    print("[boot] 预热索引 ...")
    nlp.build()
    s = nlp.state()
    print("[boot] 切块 %d / 实体 %d" % (len(s["chunks"]), len(s["entity_names"])))


if __name__ == "__main__":
    warmup()
    print("[boot] 监听 http://127.0.0.1:%d" % config.PORT)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)
