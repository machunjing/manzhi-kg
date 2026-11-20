# -*- coding: utf-8 -*-
"""慢知 · 慢性病智能问答系统 —— Flask 后端

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
import llm

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
<div class="card"><h1>慢知 · 慢性病智能问答系统</h1>
<div class="sub">后端服务运行中 · Flask + MySQL · 统一响应 <code>{code, message, data}</code></div>
<div class="kv">
  <div>切块 <b>%d</b></div><div>实体 <b>%d</b></div><div>别名 <b>%d</b></div>
  <div>真实库 <b>%s</b></div><div>演示库 <b>%s</b></div>
  <div>答案引擎 <b>%s</b></div>
</div>
<div class="sub">问答接口是 POST，用下面的命令试：<br>
<code>curl -X POST http://127.0.0.1:%d/api/qa/ask -H "Content-Type: application/json" -d "{\\"question\\":\\"糖尿病有哪些并发症\\"}"</code></div>
</div>
<div class="card"><h1 style="font-size:16px">接口清单（%d 个）</h1><table>%s</table></div>
</body></html>""" % (len(s["chunks"]), len(s["entity_names"]), len(s.get("alias_map") or {}),
                     config.DB_REAL, config.DB_DEMO,
                     (llm.MODEL if llm.available() else "图谱模板（未配置模型）"),
                     config.PORT,
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
        "llm": llm.info(),
    })


@app.route("/api/llm/status")
def llm_status():
    """前端用来显示「当前答案引擎」"""
    i = llm.info()
    return ok({"mode": "llm" if i["configured"] else "template", **i})


@app.route("/api/llm/test", methods=["POST", "OPTIONS"])
def llm_test():
    """连通性自检：发一句极短的问题，返回耗时与首句"""
    if request.method == "OPTIONS":
        return ok()
    if not llm.available():
        return fail(40002, "未配置 LLM_API_KEY")
    t0 = time.time()
    text, usage = llm.chat([{"role": "user", "content": "用一句话说明高血压的危险因素"}], max_tokens=120)
    if not text:
        return fail(50001, "模型调用失败：%s" % usage)
    return ok({"model": llm.MODEL, "elapsed_ms": int((time.time() - t0) * 1000),
               "sample": text, "usage": usage})


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

    # 跨语言路：中文问题改写成英文检索式，去查 4,000+ 篇英文摘要
    trans = llm.translate_query(q)
    terms = (trans or {}).get("terms") or retrieval._fallback_terms(entities, intent["intent"])
    xl = retrieval.cross_lingual_search(terms)

    facts = retrieval.graph_facts(entities, prefer_rel=intent["rel"])
    fused = retrieval.rrf([("关键词路", kw), ("向量路", vec), ("图谱路", gph)])

    # 疾病维度 + 意图词的证据优先（中英两个池子分别重排，再均衡取证）
    disease_hint = None
    for e in entities:
        if e["type"] == "疾病":
            disease_hint = e["name"]
            break
    fused = retrieval.rerank_disease(fused, disease_hint)
    fused = retrieval.rerank_intent(fused, intent["keywords"])
    xl = retrieval.rerank_disease(xl, disease_hint)
    xl = retrieval.rerank_intent(xl, intent["keywords"])
    fused = retrieval.bilingual_select(fused, xl, config.FINAL_TOPK)

    # 演示时想对比「纯图谱模板」和「大模型」的效果，加 ?no_llm=1
    use_llm = request.args.get("no_llm") not in ("1", "true", "yes")
    out = answer_mod.compose(q, entities, facts, fused, intent,
                             use_llm=use_llm, query_en=terms)
    out["question"] = q
    out["entities"] = entities
    out["graph_facts"] = facts
    out["query_en"] = terms
    out["retrieval"] = {
        "keyword": len(kw), "vector": len(vec), "graph": len(gph),
        "cross": len(xl), "fused": len(fused), "rrf_k": config.RRF_K,
    }
    out["elapsed_ms"] = int((time.time() - t0) * 1000)
    return ok(out)


# ---------------------------------------------------------------- 知识图谱
def _graph_data(name, depth=1, limit=120, dbname=None):
    """取以 name 为中心的子图；返回 (data, err)

    dbname='demo' 时用演示库（264 实体 / 263 关系，人工整理过的疾病子图），
    适合做可视化演示；默认走真实库（32,091 实体）。
    """
    dbname = dbname or config.DB_REAL
    if not name:
        return None, "entity 不能为空"
    if dbname == config.DB_DEMO:
        row = db.one(dbname, "SELECT id,name,type FROM entities WHERE name=%s LIMIT 1", (name,))
        if not row:
            row = db.one(dbname, "SELECT id,name,type FROM entities WHERE name LIKE %s LIMIT 1",
                         ("%" + name + "%",))
    else:
        row = nlp.resolve(name)
    if not row:
        return None, "实体不存在：%s" % name

    nodes = {row["id"]: {"id": row["id"], "name": row["name"], "type": row["type"],
                         "category": row["type"], "depth": 0,
                         "rel_count": row.get("rel_count") or 0}}
    links = []
    frontier = [row["id"]]
    for d in range(1, depth + 1):
        if not frontier:
            break
        ph = ",".join(["%s"] * len(frontier))
        rows = db.query(dbname, """
            SELECT r.id rid, r.relation, r.source rsrc, r.section rsec,
                   r.evidence_level rlev, r.confidence rconf, r.snippet rsnip, r.status rstat,
                   h.id hid, h.name hname, h.type htype,
                   t.id tid, t.name tname, t.type ttype
            FROM relations r JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id
            WHERE r.head_id IN (%s) OR r.tail_id IN (%s)
            ORDER BY FIELD(r.relation,'并发症','常用药物','监测指标','临床表现',
                                     '危险因素','共病','导致','关联疾病','干预措施')
            LIMIT %s
        """ % (ph, ph, limit), frontier + frontier)
        nxt = []
        for r in rows:
            for eid, enm, ety in ((r["hid"], r["hname"], r["htype"]),
                                  (r["tid"], r["tname"], r["ttype"])):
                if eid not in nodes:
                    nodes[eid] = {"id": eid, "name": enm, "type": ety,
                                  "category": ety, "depth": d}
                    nxt.append(eid)
            links.append({
                "id": r["rid"], "source": r["hid"], "target": r["tid"],
                "relation": r["relation"],
                "source_name": r["hname"], "target_name": r["tname"],
                "evidence_source": r["rsrc"], "section": r["rsec"],
                "evidence_level": r["rlev"],
                "confidence": float(r["rconf"]) if r["rconf"] is not None else None,
                "snippet": r["rsnip"], "status": r["rstat"],
            })
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
    src = (request.args.get("source") or "real").strip()
    data, err = _graph_data(name, depth, limit,
                            config.DB_DEMO if src == "demo" else config.DB_REAL)
    if err:
        return fail(40001 if "不能为空" in err else 40400, err)
    data["source"] = src
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
                    "SELECT id,name,type,standard_name,source,status,confidence,rel_count "
                    # 疾病类排前面：OpenCMKG 里「药物治疗」「白酒」这类泛化实体关系数也很高，
                    # 只按 rel_count 排会让列表第一屏全是这些，看不出这是医学知识图谱
                    "FROM entities %s ORDER BY (type='疾病') DESC, rel_count DESC, id LIMIT %s OFFSET %s"
                    % (w, size, (page - 1) * size),
                    args)
    return ok({"list": rows, "total": total, "page": page, "pageSize": size})


@app.route("/api/kg/types")
def kg_types():
    rows = db.query(config.DB_REAL,
                    "SELECT type, COUNT(*) AS cnt FROM entities GROUP BY type ORDER BY cnt DESC")
    return ok(rows)


@app.route("/api/kg/relations")
def kg_relations():
    """关系列表：可按实体名、关系类型、审核状态、关键词筛选"""
    entity = (request.args.get("entity") or "").strip()
    rel = (request.args.get("relation") or "").strip()
    status = (request.args.get("status") or "").strip()
    disease = (request.args.get("disease") or "").strip()
    kw = (request.args.get("keyword") or "").strip()
    page = max(int(request.args.get("page") or 1), 1)
    size = min(int(request.args.get("pageSize") or 20), 100)

    where, args = [], []
    join = "JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id"
    if entity:
        where.append("(h.name=%s OR t.name=%s)")
        args += [entity, entity]
    if rel:
        where.append("r.relation=%s")
        args.append(rel)
    if status:
        where.append("r.status=%s")
        args.append(status)
    if disease:
        where.append("r.disease=%s")
        args.append(disease)
    if kw:
        where.append("(h.name LIKE %s OR t.name LIKE %s)")
        args += ["%" + kw + "%"] * 2
    w = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.scalar(config.DB_REAL,
                      "SELECT COUNT(*) AS n FROM relations r %s %s" % (join, w), args)
    rows = db.query(config.DB_REAL, """
        SELECT r.id, r.relation, r.disease, r.source, r.section, r.evidence_level,
               r.confidence, r.status, r.snippet,
               h.id hid, h.name hname, h.type htype,
               t.id tid, t.name tname, t.type ttype
        FROM relations r %s %s ORDER BY r.confidence DESC, r.id LIMIT %s OFFSET %s
    """ % (join, w, size, (page - 1) * size), args)
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "relation": r["relation"], "disease": r["disease"],
            "source": r["source"], "section": r["section"],
            "evidenceLevel": r["evidence_level"], "confidence": float(r["confidence"] or 0),
            "status": r["status"], "snippet": r["snippet"],
            "headId": r["hid"], "headName": r["hname"], "headType": r["htype"],
            "tailId": r["tid"], "tailName": r["tname"], "tailType": r["ttype"],
        })
    return ok({"list": out, "total": total, "page": page, "pageSize": size})


@app.route("/api/kg/hot")
def kg_hot():
    """热度榜：按关系条数排序，给前端下拉框和 PageRank 页用"""
    typ = (request.args.get("type") or "").strip()
    limit = min(int(request.args.get("limit") or 20), 100)
    if typ:
        rows = db.query(config.DB_REAL,
                        "SELECT id,name,type,rel_count FROM entities "
                        "WHERE type=%s AND rel_count>0 AND CHAR_LENGTH(name)>=3 "
                        "ORDER BY rel_count DESC LIMIT %s",
                        (typ, limit))
    else:
        rows = db.query(config.DB_REAL,
                        "SELECT id,name,type,rel_count FROM entities "
                        "WHERE rel_count>0 AND CHAR_LENGTH(name)>=3 "
                        "ORDER BY rel_count DESC LIMIT %s", (limit,))
    return ok(rows)


# ---------------------------------------------------------------- 文献
@app.route("/api/docs/search")
def docs_search():
    kw = (request.args.get("keyword") or "").strip()
    disease = (request.args.get("disease") or "").strip()
    source = (request.args.get("source") or "").strip()
    doc_type = (request.args.get("docType") or "").strip()
    year = (request.args.get("year") or "").strip()
    page = max(int(request.args.get("page") or 1), 1)
    size = min(int(request.args.get("pageSize") or 20), 100)
    where, args = [], []
    if kw:
        where.append("(title LIKE %s OR abstract LIKE %s)")
        args += ["%" + kw + "%"] * 2
    if disease:
        where.append("disease=%s")
        args.append(disease)
    if source:
        where.append("source=%s")
        args.append(source)
    if doc_type:
        where.append("doc_type=%s")
        args.append(doc_type)
    if year:
        where.append("YEAR(publish_date)=%s")
        args.append(year)
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
@app.route("/api/review/list")
def review_list():
    """审核工作台：按状态取队列（演示库 manzhi，带状态机触发器）"""
    status = (request.args.get("status") or "").strip()
    kw = (request.args.get("keyword") or "").strip()
    limit = min(int(request.args.get("limit") or 200), 500)
    where, args = [], []
    if status:
        where.append("r.status=%s")
        args.append(status)
    if kw:
        where.append("(h.name LIKE %s OR t.name LIKE %s)")
        args += ["%" + kw + "%"] * 2
    w = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.query(config.DB_DEMO, """
        SELECT r.id, r.relation, r.disease, r.source, r.section, r.evidence_level,
               r.confidence, r.status, r.snippet, r.reviewer, r.reviewed_at,
               h.id hid, h.name hname, h.type htype,
               t.id tid, t.name tname, t.type ttype
        FROM relations r JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id
        %s ORDER BY FIELD(r.status,'待审核','候选','已审核','已驳回'), r.confidence DESC
        LIMIT %s
    """ % (w, limit), args)
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "relation": r["relation"], "disease": r["disease"],
            "source": r["source"], "section": r["section"],
            "evidenceLevel": r["evidence_level"], "confidence": float(r["confidence"] or 0),
            "status": r["status"], "snippet": r["snippet"],
            "reviewer": r["reviewer"],
            "reviewedAt": str(r["reviewed_at"]) if r["reviewed_at"] else None,
            "headId": r["hid"], "headName": r["hname"], "headType": r["htype"],
            "tailId": r["tid"], "tailName": r["tname"], "tailType": r["ttype"],
        })
    return ok({"list": out, "total": len(out)})


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
        "doc_with_abstract": db.scalar(
            real, "SELECT COUNT(*) AS n FROM documents WHERE abstract IS NOT NULL AND abstract<>''"),
        "chunks": db.scalar(real, "SELECT COUNT(*) AS n FROM chunks"),
        "char_total": db.scalar(real, "SELECT COALESCE(SUM(text_len),0) AS n FROM chunks"),
        "entities": db.scalar(real, "SELECT COUNT(*) AS n FROM entities"),
        "relations": db.scalar(real, "SELECT COUNT(*) AS n FROM relations"),
        "journal_total": db.scalar(real, "SELECT COUNT(DISTINCT journal) AS n FROM documents"),
        "guides": db.scalar(real, "SELECT COUNT(*) AS n FROM documents WHERE source='本地指南文件'"),
        "aliases": db.scalar(real, "SELECT COUNT(*) AS n FROM entity_alias"),
        "data_snapshot_at": db.scalar(real, "SELECT MAX(publish_date) AS d FROM documents"),
        "by_source": db.query(real, "SELECT source, COUNT(*) AS cnt FROM documents GROUP BY source"),
        "by_disease": db.query(real, "SELECT disease, COUNT(*) AS cnt FROM documents "
                                     "GROUP BY disease ORDER BY cnt DESC"),
        "by_year": db.query(real, "SELECT YEAR(publish_date) AS year, COUNT(*) AS cnt FROM documents "
                                  "GROUP BY year ORDER BY year"),
        "entity_types": db.query(real, "SELECT type, COUNT(*) AS cnt FROM entities "
                                       "GROUP BY type ORDER BY cnt DESC"),
        "relation_types": db.query(real, "SELECT relation, COUNT(*) AS cnt FROM relations "
                                         "GROUP BY relation ORDER BY cnt DESC"),
        "relation_status": db.query(real, "SELECT status, COUNT(*) AS cnt FROM relations "
                                          "GROUP BY status"),
        "llm": llm.info(),
    })


@app.route("/api/stats/yearly")
def stats_yearly():
    """按疾病 × 年份统计文献量，给趋势图用"""
    rows = db.query(config.DB_REAL, """
        SELECT disease, YEAR(publish_date) AS y, COUNT(*) AS cnt
        FROM documents WHERE publish_date IS NOT NULL
        GROUP BY disease, y ORDER BY y
    """)
    out = {}
    for r in rows:
        if not r["disease"]:
            continue
        out.setdefault(r["disease"], {})[str(r["y"])] = r["cnt"]
    return ok(out)


@app.route("/api/stats/disease")
def stats_disease():
    """疾病维度聚合

    文献量来自真实库（5,063 篇按疾病分桶）；
    关系与审核状态来自演示库（manzhi，按疾病组织并带审核状态机）。
    真实库的 OpenCMKG 是通用图谱，关系本身不带疾病归属，强行归属会造假数据。
    """
    docs = {r["disease"]: r["cnt"] for r in db.query(
        config.DB_REAL, "SELECT disease, COUNT(*) AS cnt FROM documents GROUP BY disease")}
    demo = {}
    for r in db.query(config.DB_DEMO, """
        SELECT disease, COUNT(*) AS cnt,
               SUM(status='已审核') AS approved, SUM(status='待审核') AS pending
        FROM relations WHERE disease IS NOT NULL GROUP BY disease
    """):
        demo[r["disease"]] = dict(r, ents=0)
    for r in db.query(config.DB_DEMO, """
        SELECT disease, COUNT(*) AS ents FROM (
            SELECT disease, head_id AS id FROM relations WHERE disease IS NOT NULL
            UNION
            SELECT disease, tail_id AS id FROM relations WHERE disease IS NOT NULL
        ) x GROUP BY disease
    """):
        if r["disease"] in demo:
            demo[r["disease"]]["ents"] = r["ents"]
    out = []
    for d, cnt in docs.items():
        if not d:
            continue
        m = demo.get(d) or {}
        out.append({
            "disease": d, "literature": cnt,
            "entities": int(m.get("ents") or 0),
            "relations": int(m.get("cnt") or 0),
            "approved": int(m.get("approved") or 0),
            "pending": int(m.get("pending") or 0),
        })
    out.sort(key=lambda x: -x["literature"])
    return ok(out)


# ---------------------------------------------------------------- 平台运维
# 用户 / 采集任务 / 操作日志属于「平台自己的运行数据」，和文献语料不是一回事，
# 统一走演示库 manzhi（那里有 42 个用户、22 个采集任务、90 条审计日志）。
# 语料类数据（文献/切块/实体/关系）才走 manzhi_real。

def _page_args(default_size=10):
    page = max(int(request.args.get("page") or 1), 1)
    size = min(int(request.args.get("pageSize") or default_size), 100)
    return page, size, (page - 1) * size


@app.route("/api/users")
def user_list():
    kw = (request.args.get("keyword") or "").strip()
    role = (request.args.get("role") or "").strip()
    status = (request.args.get("status") or "").strip()
    page, size, offset = _page_args()

    where, args = [], []
    if kw:
        where.append("(name LIKE %s OR account LIKE %s OR id LIKE %s)")
        args += ["%" + kw + "%"] * 3
    if role:
        where.append("role=%s")
        args.append(role)
    if status:
        where.append("status=%s")
        args.append(status)
    w = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.scalar(config.DB_DEMO, "SELECT COUNT(*) AS n FROM users %s" % w, args)
    rows = db.query(config.DB_DEMO, """
        SELECT id, account, name, avatar, role, dept, phone, email, status,
               last_login_at, created_at
        FROM users %s ORDER BY id LIMIT %s OFFSET %s
    """ % (w, size, offset), args)
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "account": r["account"], "name": r["name"],
            "avatar": r["avatar"] or (r["name"] or "?")[:1],
            "role": r["role"], "dept": r["dept"], "phone": r["phone"],
            "email": r["email"], "status": r["status"],
            "createdAt": r["created_at"].strftime("%Y-%m-%d") if r["created_at"] else None,
            "lastLogin": r["last_login_at"].strftime("%Y-%m-%d %H:%M") if r["last_login_at"] else "—",
        })
    return ok({"list": out, "total": total, "page": page, "pageSize": size})


@app.route("/api/users/stats")
def user_stats():
    rows = db.query(config.DB_DEMO,
                    "SELECT role, status, COUNT(*) AS n FROM users GROUP BY role, status")
    total = sum(r["n"] for r in rows)
    active = sum(r["n"] for r in rows if r["status"] == "启用")
    by_role = {}
    for r in rows:
        by_role[r["role"]] = by_role.get(r["role"], 0) + r["n"]
    return ok({"total": total, "active": active, "by_role": by_role,
               "rows": [{"role": r["role"], "status": r["status"], "count": r["n"]} for r in rows]})


@app.route("/api/collect/tasks")
def collect_tasks():
    kw = (request.args.get("keyword") or "").strip()
    status = (request.args.get("status") or "").strip()
    src = (request.args.get("source") or "").strip()
    page, size, offset = _page_args()

    where, args = [], []
    if kw:
        where.append("(name LIKE %s OR id LIKE %s)")
        args += ["%" + kw + "%"] * 2
    if status:
        where.append("status=%s")
        args.append(status)
    if src:
        where.append("source=%s")
        args.append(src)
    w = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.scalar(config.DB_DEMO, "SELECT COUNT(*) AS n FROM collect_tasks %s" % w, args)
    rows = db.query(config.DB_DEMO, """
        SELECT id, name, source, collect_type, disease, keyword, status, progress,
               fetched_count, operator, start_at, end_at, created_at
        FROM collect_tasks %s ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s
    """ % (w, size, offset), args)
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "name": r["name"], "source": r["source"],
            "collectType": r["collect_type"], "disease": r["disease"],
            "keyword": r["keyword"], "status": r["status"],
            "progress": r["progress"], "count": r["fetched_count"],
            "operator": r["operator"],
            "startAt": r["start_at"].strftime("%Y-%m-%d %H:%M") if r["start_at"] else "—",
            "endAt": r["end_at"].strftime("%Y-%m-%d %H:%M") if r["end_at"] else "—",
        })
    return ok({"list": out, "total": total, "page": page, "pageSize": size})


@app.route("/api/system/logs")
def system_logs():
    kw = (request.args.get("keyword") or "").strip()
    module = (request.args.get("module") or "").strip()
    user = (request.args.get("user") or "").strip()
    result = (request.args.get("result") or "").strip()
    page, size, offset = _page_args()

    where, args = [], []
    if kw:
        where.append("(action LIKE %s OR user_name LIKE %s OR id LIKE %s)")
        args += ["%" + kw + "%"] * 3
    if module:
        where.append("module=%s")
        args.append(module)
    if user:
        where.append("user_name=%s")
        args.append(user)
    if result:
        where.append("result=%s")
        args.append(result)
    w = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.scalar(config.DB_DEMO, "SELECT COUNT(*) AS n FROM operation_logs %s" % w, args)
    rows = db.query(config.DB_DEMO, """
        SELECT id, user_name, module, action, ip, result, detail, created_at
        FROM operation_logs %s ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s
    """ % (w, size, offset), args)
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "user": r["user_name"], "module": r["module"],
            "action": r["action"], "ip": r["ip"], "result": r["result"],
            "detail": r["detail"],
            "time": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r["created_at"] else None,
        })
    return ok({"list": out, "total": total, "page": page, "pageSize": size})


@app.route("/api/kg/entity/<entity_id>")
def kg_entity(entity_id):
    r = db.one(config.DB_REAL, """
        SELECT id, name, type, standard_name, aliases, diseases, source, status,
               confidence, rel_count
        FROM entities WHERE id=%s
    """, (entity_id,))
    if not r:
        return fail(40400, "实体不存在：%s" % entity_id)
    return ok({
        "id": r["id"], "name": r["name"], "type": r["type"],
        "standardName": r["standard_name"] or r["name"],
        "aliases": r["aliases"] or [], "diseases": r["diseases"] or [],
        "source": r["source"], "status": r["status"],
        "confidence": float(r["confidence"] or 0),
        "value": r["rel_count"] or 0,
    })


@app.route("/api/kg/relation/<rel_id>")
def kg_relation(rel_id):
    r = db.one(config.DB_REAL, """
        SELECT r.id, r.relation, r.disease, r.source, r.section, r.evidence_level,
               r.confidence, r.status, r.snippet, r.reviewer, r.reviewed_at,
               h.id hid, h.name hname, h.type htype,
               t.id tid, t.name tname, t.type ttype
        FROM relations r JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id
        WHERE r.id=%s
    """, (rel_id,))
    if not r:
        return fail(40400, "关系不存在：%s" % rel_id)
    return ok({
        "id": r["id"], "relation": r["relation"], "disease": r["disease"],
        "source": r["source"], "section": r["section"],
        "evidenceLevel": r["evidence_level"], "confidence": float(r["confidence"] or 0),
        "status": r["status"], "snippet": r["snippet"], "reviewer": r["reviewer"],
        "reviewedAt": str(r["reviewed_at"]) if r["reviewed_at"] else None,
        "headId": r["hid"], "headName": r["hname"], "headType": r["htype"],
        "tailId": r["tid"], "tailName": r["tname"], "tailType": r["ttype"],
    })


# ---------------------------------------------------------------- 关联分析
@app.route("/api/analysis/network")
def analysis_network():
    name = (request.args.get("entity") or "糖尿病").strip()
    depth = min(int(request.args.get("depth") or 2), 3)
    src = (request.args.get("source") or "demo").strip()
    data, err = _graph_data(name, depth, 200,
                            config.DB_DEMO if src == "demo" else config.DB_REAL)
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

    # 用户可以在结果里「避开某个中转节点」再查一次：图里有「巨人症 → 糖尿病/冠心病」
    # 这类语义上说不通的边，绕开它往往能得到一条更可信的路径。
    avoid, avoid_names = set(), []
    for name in (request.args.get("avoid") or "").split(","):
        name = name.strip()
        if not name:
            continue
        r = nlp.resolve(name)
        if r and r["id"] not in (a["id"], b["id"]):
            avoid.add(r["id"])
            avoid_names.append(r["name"])

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
                   t.id tid, t.name tname, t.type ttype,
                   r.id rid, r.relation rel, r.source rsrc, r.section rsec,
                   r.evidence_level rlev, r.confidence rconf, r.snippet rsnip,
                   r.status rstat
            FROM relations r JOIN entities h ON h.id=r.head_id JOIN entities t ON t.id=r.tail_id
            WHERE r.head_id IN (%s) OR r.tail_id IN (%s)
        """ % (ph, ph), frontier + frontier)
        nxt = []
        for r in rows:
            meta = {"id": r["rid"], "source": r["rsrc"], "section": r["rsec"],
                    "evidenceLevel": r["rlev"], "confidence": float(r["rconf"] or 0),
                    "snippet": r["rsnip"] or "", "status": r["rstat"]}
            for idx, (x, y) in enumerate(((r["hid"], r["tid"]), (r["tid"], r["hid"]))):
                if x in parent and y not in parent and y not in avoid:
                    # idx=0 说明沿关系表方向走，idx=1 说明是逆着关系表走的反向边
                    parent[y] = (x, r["rel"], meta, "forward" if idx == 0 else "reverse")
                    nxt.append(y)
                    if y == b["id"]:
                        found = True
        frontier = nxt[:200]
    if b["id"] not in parent:
        return ok({"found": False, "from": a, "to": b, "path": [], "hops": None,
                   "avoid": avoid_names})

    # 回溯
    chain = []
    cur = b["id"]
    while parent[cur]:
        prev, rel, meta, direction = parent[cur]
        chain.append((prev, rel, cur, meta, direction))
        cur = prev
    chain.reverse()
    ids = [a["id"]] + [c[2] for c in chain]
    ph = ",".join(["%s"] * len(ids))
    info = {r["id"]: r for r in db.query(
        config.DB_REAL, "SELECT id,name,type FROM entities WHERE id IN (%s)" % ph, ids)}
    path = [{"node": info[a["id"]], "relation": None, "rel": None, "evidence": [], "cooccur": 0}]
    used = set()   # 同一条切块不要在两跳里重复出现，否则看着像凑数
    for prev, rel, cur, meta, direction in chain:
        hname, tname = info[prev]["name"], info[cur]["name"]
        lit, cooc = retrieval.evidence_for(hname, tname, topk=1, exclude=used)
        for e in lit:
            used.add(e["chunk_id"])
        path.append({
            "relation": rel,
            "node": info[cur],
            "direction": direction,
            "rel": meta,
            "evidence": lit,
            "cooccur": cooc,
        })
    return ok({"found": True, "from": a, "to": b, "path": path, "hops": len(chain),
               "avoid": avoid_names})


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
