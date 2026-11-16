# -*- coding: utf-8 -*-
"""
把 manzhi_real 导出成 Neo4j 批量导入用的 CSV

为什么用 CSV 而不是 Cypher 语句：
  288,064 条关系写成 UNWIND [...] 语句，单条语句就有几十万行 map 字面量，
  Neo4j 解析时直接 Java heap space。LOAD CSV 是逐行流式读，内存占用恒定。

输出：db/nodes.csv、db/rels.csv
用法：py -3.8-64 db/export_graph.py
"""
import csv
import io
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

import sys

import pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
DB = "manzhi_real"
NODES = os.path.join(HERE, "nodes.csv")
RELS = os.path.join(HERE, "rels.csv")


def main():
    conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", password=_pw(),
                           database=DB, charset="utf8mb4", autocommit=True)
    cur = conn.cursor()

    cur.execute("SELECT id,name,type,status,confidence,source FROM entities")
    n = 0
    with io.open(NODES, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "type", "status", "confidence", "source"])
        for r in cur.fetchall():
            w.writerow([r[0], r[1], r[2], r[3], float(r[4] or 0.5), r[5] or ""])
            n += 1

    cur.execute("SELECT id,head_id,tail_id,relation,disease,status,confidence FROM relations")
    m = 0
    with io.open(RELS, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "head", "tail", "relation", "disease", "status", "confidence"])
        for r in cur.fetchall():
            w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], float(r[6] or 0.5)])
            m += 1

    cur.close()
    conn.close()
    print("导出完成")
    print("  %s  节点 %d  (%.1f MB)" % (NODES, n, os.path.getsize(NODES) / 1048576.0))
    print("  %s  关系 %d  (%.1f MB)" % (RELS, m, os.path.getsize(RELS) / 1048576.0))


if __name__ == "__main__":
    sys.exit(main())
