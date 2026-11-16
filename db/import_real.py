# -*- coding: utf-8 -*-
"""
把「数据包」里的真实语料灌进 MySQL（库名 manzhi_real）

与 seed.sql 的区别：
  seed.sql       -> manzhi       演示库，408 篇文献 / 264 实体 / 263 关系，数字与前端页面一致
  import_real.py -> manzhi_real  真实库，5,057 篇文献 / 3.2 万切块 / 6 万实体 / 30 万关系

数据来源（均在 D:/毕业设计/开题答辩/数据包）：
  03_清洗后数据/解析结构化JSON/pubmed_records.json        5,026 篇 PubMed
  03_清洗后数据/解析结构化JSON/mlp_topics.json            31 条 MedlinePlus 主题
  04_预处理中间产物/向量切块/向量切块清单_300重叠50.json   32,078 个切块
  04_预处理中间产物/实体候选/实体候选列表_有效MeSH.json     4,793 个有效 MeSH 实体
  01_外部公开语料/结构化知识图谱/OpenCMKG/triples.txt     352,584 条实体关系

用法：py -3.8-64 db/import_real.py
"""
import io
import json
import os

def _pw():
    """数据库口令：环境变量优先，其次同目录 .env（.env 不进版本库）"""
    v = os.environ.get("MYSQL_PASSWORD")
    if v:
        return v
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                if ln.strip().startswith("MYSQL_PASSWORD="):
                    return ln.split("=", 1)[1].strip()
    return ""

import re
import sys
import time
from collections import Counter, defaultdict

import pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(HERE), "数据包")
DB = "manzhi_real"

# ---- OpenCMKG 关系 -> 本系统 9 种关系类型 --------------------------------
REL_MAP = {
    "disease_has_symptom": "临床表现",
    "disease_recommand_drug": "常用药物",
    "disease_common_drug": "常用药物",
    "disease_need_check": "监测指标",
    "disease_acompany_disease": "并发症",
    "disease_recommand_food": "干预措施",
    "disease_eat_food": "干预措施",
    "disease_noteat_food": "干预措施",
    "disease_need_treatment": "干预措施",
}
# 不入库的关系：科室/生产企业/科室层级 无法落到 9 种类型里；SameAs 用于实体合并
REL_SKIP = {
    "disease_belong_department", "drug_relate_producer",
    "department_belong_department", "SameAs",
}
# 尾实体类型推断：优先级从高到低
TYPE_OF_REL = {
    "disease_has_symptom": "症状",
    "disease_recommand_drug": "药物类别",
    "disease_common_drug": "药物类别",
    "drug_relate_producer": "药物类别",
    "disease_need_check": "检查指标",
    "disease_recommand_food": "生活方式",
    "disease_eat_food": "生活方式",
    "disease_noteat_food": "生活方式",
}
TYPE_PRIORITY = ["疾病", "症状", "药物类别", "检查指标", "生活方式", "其他"]


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def trunc(s, n):
    if s is None:
        return None
    s = str(s).strip()
    return s[:n] if len(s) > n else s


def dt(s):
    """把 ISO 时间串洗成 MySQL 认的 'YYYY-MM-DD HH:MM:SS'"""
    if not s:
        return None
    s = str(s).strip().replace("T", " ").replace("Z", "")
    s = s.split("+")[0].split(".")[0]
    return s if re.match(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$", s) else None


def connect(db=None):
    return pymysql.connect(
        host="127.0.0.1", port=3306, user="root", password=_pw(),
        database=db, charset="utf8mb4", autocommit=False,
        local_infile=False,
    )


def build_schema():
    """用 schema.sql 建 manzhi_real

    schema.sql 里有 DELIMITER $$ 的触发器块，pymysql 不认 DELIMITER，
    所以这里改写成临时文件、交给 mysql 命令行客户端执行（它认 DELIMITER）。
    """
    import subprocess
    import tempfile

    sql = io.open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read()
    sql = sql.replace("`manzhi`", "`%s`" % DB)

    fd, tmp = tempfile.mkstemp(suffix=".sql", dir=HERE)
    os.close(fd)
    try:
        with io.open(tmp, "w", encoding="utf-8") as f:
            f.write(sql)
        env = dict(os.environ)
        env["MYSQL_PWD"] = _pw()
        r = subprocess.run(
            ["mysql", "-uroot", "--default-character-set=utf8mb4",
             "--init-command=SET NAMES utf8mb4"],
            stdin=io.open(tmp, "rb"), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env)
        err = r.stderr.decode("utf-8", "replace").strip()
        if r.returncode != 0:
            raise RuntimeError("建库失败：%s" % err[:400])
        if err:
            print("      [mysql] %s" % err[:200])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def main():
    t0 = time.time()
    print("=" * 70)
    print("真实语料导入 -> %s" % DB)
    print("=" * 70)

    print("[1/6] 建库建表 ...")
    build_schema()

    conn = connect(DB)
    cur = conn.cursor()

    # ---------------- 文献 ----------------
    print("[2/6] 导入文献 ...")
    pubmed = load(os.path.join(PKG, "03_清洗后数据/解析结构化JSON/pubmed_records.json"))
    mlp = load(os.path.join(PKG, "03_清洗后数据/解析结构化JSON/mlp_topics.json"))

    docs, pmid2doc = [], {}
    for r in pubmed:
        pmid = str(r.get("pmid") or "").strip()
        if not pmid:
            continue
        did = "D" + pmid
        pubtypes = r.get("pubtypes") or []
        if isinstance(pubtypes, str):
            pubtypes = [pubtypes]
        joined = " ".join(pubtypes).lower()
        if "guideline" in joined:
            dtype = "临床指南"
        elif "review" in joined:
            dtype = "综述"
        else:
            dtype = "研究论文"
        year = r.get("year")
        pdate = None
        try:
            y = int(str(year)[:4])
            if 1900 < y < 2100:
                pdate = "%d-01-01" % y
        except Exception:
            pass
        mesh = r.get("mesh") or []
        if isinstance(mesh, str):
            mesh = [mesh]
        docs.append((
            did, pmid, trunc(r.get("title") or "(无标题)", 512), None, None,
            trunc(r.get("journal"), 255), dtype, trunc(r.get("disease") or "通用", 32),
            "PubMed", pdate, 0, "已入库", trunc(r.get("doi"), 128),
            trunc(r.get("url"), 512), r.get("abstract"),
            json.dumps(mesh, ensure_ascii=False),
            dt(r.get("collected_at")),
        ))
        pmid2doc[pmid] = did

    for r in mlp:
        tid = str(r.get("topic_id") or "").strip()
        if not tid:
            continue
        did = "DM" + tid
        also = r.get("also_called")
        docs.append((
            did, None, trunc(r.get("title") or "(无标题)", 512), None, trunc(also, 512),
            "MedlinePlus", "其他", "通用", "MedlinePlus", None, 0, "已入库",
            None, trunc(r.get("url"), 512), r.get("summary"), None,
            dt(r.get("collected_at")),
        ))

    cur.executemany(
        "INSERT INTO documents (id,pmid,title,title_en,authors,journal,doc_type,disease,"
        "source,publish_date,chunk_count,status,doi,url,abstract,mesh,collected_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,NOW()))", docs)
    conn.commit()
    print("      文献 %d 篇（PubMed %d / MedlinePlus %d）" % (len(docs), len(pubmed), len(mlp)))

    # ---------------- 切块 ----------------
    print("[3/6] 导入切块 ...")
    ck = load(os.path.join(PKG, "04_预处理中间产物/向量切块/向量切块清单_300重叠50.json"))["chunks"]
    rows, per_doc, skip = [], Counter(), 0
    for i, c in enumerate(ck, 1):
        pmid = str(c.get("pmid") or "").strip()
        tid = str(c.get("topic_id") or "").strip()
        if pmid:
            did = pmid2doc.get(pmid)
        else:
            did = ("DM" + tid) if tid else None
        if not did:
            skip += 1
            continue
        text = c.get("text") or ""
        if not text:
            skip += 1
            continue
        rows.append(("C%06d" % i, did, int(c.get("chunk_idx") or 0),
                     trunc(c.get("disease") or "通用", 32),
                     min(len(text), 2000), text[:2000]))
        per_doc[did] += 1
    cur.executemany(
        "INSERT INTO chunks (id,doc_id,chunk_idx,disease,text_len,text) "
        "VALUES (%s,%s,%s,%s,%s,%s)", rows)
    cur.executemany("UPDATE documents SET chunk_count=%s WHERE id=%s",
                    [(n, d) for d, n in per_doc.items()])
    conn.commit()
    print("      切块 %d 条（跳过 %d 条：无对应文献或空文本）" % (len(rows), skip))

    # ---------------- 实体 + 关系（OpenCMKG） ----------------
    print("[4/6] 解析 OpenCMKG 三元组 ...")
    triples_path = os.path.join(
        PKG, "01_外部公开语料/结构化知识图谱/OpenCMKG/triples.txt")
    etype = {}
    raw_triples = []
    rel_counter = Counter()
    with io.open(triples_path, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split(",")
            if len(p) != 3:
                continue
            h, rel, t = p[0].strip(), p[1].strip(), p[2].strip()
            if not h or not t or h == t:
                continue
            rel_counter[rel] += 1
            if rel in REL_SKIP:
                continue
            mapped = REL_MAP.get(rel)
            if not mapped:
                continue
            # 类型推断
            if h.startswith("disease_"):
                pass
            raw_triples.append((h, mapped, t, rel))

    # 头实体：凡出现在 disease_* 左侧的，都是疾病
    for h, mapped, t, rel in raw_triples:
        if rel.startswith("disease_"):
            if TYPE_PRIORITY.index("疾病") < TYPE_PRIORITY.index(etype.get(h, "其他")):
                etype[h] = "疾病"
            etype.setdefault(h, "疾病")
        tt = TYPE_OF_REL.get(rel, "其他")
        if TYPE_PRIORITY.index(tt) < TYPE_PRIORITY.index(etype.get(t, "其他")):
            etype[t] = tt
        etype.setdefault(t, "其他")
    # 兜底：头实体没被判定过的一律"其他"
    for h, mapped, t, rel in raw_triples:
        etype.setdefault(h, "疾病" if rel.startswith("disease_") else "其他")
        etype.setdefault(t, "其他")

    print("      有效三元组 %d 条，实体 %d 个" % (len(raw_triples), len(etype)))

    print("[5/6] 写入实体与关系 ...")
    names = sorted(etype.keys())
    ent_rows = []
    for i, n in enumerate(names, 1):
        nm = trunc(n, 255)
        ent_rows.append(("E%06d" % i, nm, etype[n], nm,
                         None, None, "OpenCMKG", "已审核", 0.900))
    # 用 INSERT IGNORE：MySQL 的 utf8mb4_0900_ai_ci 是大小写/重音不敏感，
    # Python 侧判不出来（例如同名字符串的不同 Unicode 形式），交给数据库去重
    cur.executemany(
        "INSERT IGNORE INTO entities (id,name,type,standard_name,aliases,diseases,source,status,confidence) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", ent_rows)
    conn.commit()
    cur.execute("SELECT id,name FROM entities")
    by_name, by_fold = {}, {}
    maxid = 0
    for eid, nm in cur.fetchall():
        by_name[nm] = eid
        by_fold.setdefault(nm.casefold(), eid)
        try:
            maxid = max(maxid, int(eid[1:]))
        except ValueError:
            pass

    def resolve(n):
        nm = trunc(n, 255)
        return by_name.get(nm) or by_fold.get(nm.casefold())

    print("      实体 %d 个（提交 %d 个，数据库去重 %d 个）"
          % (len(by_name), len(ent_rows), len(ent_rows) - len(by_name)))

    seen = set()
    rel_rows = []
    for h, mapped, t, rel in raw_triples:
        hid, tid = resolve(h), resolve(t)
        if not hid or not tid or hid == tid:
            continue
        key = (hid, mapped, tid)
        if key in seen:
            continue
        seen.add(key)
        rel_rows.append((hid, tid, mapped, "通用", "OpenCMKG", None, None, 0.900, "已审核"))
    rel_rows = [("R%06d" % i,) + r for i, r in enumerate(rel_rows, 1)]
    cur.executemany(
        "INSERT INTO relations (id,head_id,tail_id,relation,disease,source,section,"
        "evidence_level,confidence,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        rel_rows)
    conn.commit()
    print("      关系 %d 条（去重后）" % len(rel_rows))

    # ---------------- MeSH 实体候选 ----------------
    print("[6/6] 导入 MeSH 实体候选 ...")
    mesh = load(os.path.join(PKG, "04_预处理中间产物/实体候选/实体候选列表_有效MeSH.json"))
    cand = [m for m in mesh["entities"] if isinstance(m, str)]
    base = maxid
    rows2 = []
    for n in cand:
        nm = trunc(n, 255)
        if resolve(nm):
            continue
        eid = "E%06d" % (base + len(rows2) + 1)
        rows2.append((eid, nm, "其他", nm, None, None, "MeSH对齐", "候选", 0.700))
    cur.executemany(
        "INSERT IGNORE INTO entities (id,name,type,standard_name,aliases,diseases,source,status,confidence) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows2)
    conn.commit()
    print("      MeSH 候选 %d 个（重名跳过 %d 个）" % (len(rows2), len(cand) - len(rows2)))

    # ---------------- 校验 ----------------
    print("-" * 70)
    checks = [
        ("documents", "SELECT COUNT(*) FROM documents"),
        ("chunks", "SELECT COUNT(*) FROM chunks"),
        ("entities", "SELECT COUNT(*) FROM entities"),
        ("relations", "SELECT COUNT(*) FROM relations"),
    ]
    for name, sql in checks:
        cur.execute(sql)
        print("  %-12s %d" % (name, cur.fetchone()[0]))
    cur.execute("SELECT relation, COUNT(*) FROM relations GROUP BY relation ORDER BY 2 DESC")
    print("  关系类型分布：", dict(cur.fetchall()))
    cur.execute("SELECT type, COUNT(*) FROM entities GROUP BY type ORDER BY 2 DESC")
    print("  实体类型分布：", dict(cur.fetchall()))
    cur.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
    print("  文献来源分布：", dict(cur.fetchall()))
    cur.execute("SELECT SUM(chunk_count) FROM documents")
    print("  chunk_count 回填合计：%s" % cur.fetchone()[0])
    cur.close()
    conn.close()

    print("-" * 70)
    print("完成，用时 %.1f 秒。库：%s" % (time.time() - t0, DB))
    print("被跳过的 OpenCMKG 关系（不在 9 种类型内）：")
    for k, v in rel_counter.most_common():
        if k in REL_SKIP:
            print("   %-32s %d" % (k, v))


if __name__ == "__main__":
    sys.exit(main())
