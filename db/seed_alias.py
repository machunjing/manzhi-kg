# -*- coding: utf-8 -*-
"""
生成实体别名表 entity_alias

两个来源：
  1. OpenCMKG 的 SameAs 关系（17,947 组，之前导入关系时被跳过，正好拿来做归一）
  2. 人工补充的常用同义写法（指南用「脑卒中」，OpenCMKG 只收「中风」）

用法：py -3.8-64 db/seed_alias.py
可重复执行（INSERT IGNORE）
"""
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
PKG = os.path.join(os.path.dirname(HERE), "数据包")
DB = "manzhi_real"

# 别名 -> 标准实体名（标准实体必须已存在，否则跳过）
CURATED = {
    "脑卒中": "中风", "卒中": "中风", "脑血管意外": "中风",
    "脑梗死": "中风", "脑梗塞": "中风", "急性脑血管病": "中风",
    "肥胖": "单纯性肥胖",
    "2型糖尿病": "糖尿病", "II型糖尿病": "糖尿病", "T2DM": "糖尿病",
    "1型糖尿病": "糖尿病", "I型糖尿病": "糖尿病",
    "原发性高血压": "高血压", "血压升高": "高血压",
    "高血脂": "血脂异常", "血脂紊乱": "血脂异常", "血脂增高": "血脂异常",
    "高胆固醇血症": "高脂血症", "高甘油三酯血症": "高脂血症",
    "冠状动脉粥样硬化性心脏病": "冠心病", "缺血性心脏病": "冠心病",
    "心肌梗塞": "心肌梗死", "急性心肌梗死": "心肌梗死",
    "脂肪性肝病": "脂肪肝", "非酒精性脂肪肝": "脂肪肝",
    "动脉硬化": "动脉粥样硬化",
}

DDL = """
CREATE TABLE IF NOT EXISTS `entity_alias` (
  `alias`      VARCHAR(255) NOT NULL,
  `entity_id`  VARCHAR(16)  NOT NULL,
  `source`     VARCHAR(32)  DEFAULT NULL,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alias`),
  KEY `idx_alias_entity` (`entity_id`),
  CONSTRAINT `fk_alias_entity` FOREIGN KEY (`entity_id`) REFERENCES `entities` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='实体别名（实体归一用）';
"""


def main():
    conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", password=_pw(),
                           database=DB, charset="utf8mb4", autocommit=True)
    cur = conn.cursor()
    cur.execute(DDL)
    cur.execute("SELECT id, name FROM entities")
    name2id = {n: i for i, n in cur.fetchall()}
    print("实体 %d 个" % len(name2id))

    rows = []
    # ---- 1. OpenCMKG SameAs ----
    path = os.path.join(PKG, "01_外部公开语料/结构化知识图谱/OpenCMKG/triples.txt")
    same = 0
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            p = line.rstrip("\n").split(",")
            if len(p) != 3 or p[1] != "SameAs":
                continue
            a, b = p[0].strip(), p[2].strip()
            ia, ib = name2id.get(a), name2id.get(b)
            if not ia or not ib or a == b:
                continue
            rows.append((a, ib, "OpenCMKG-SameAs"))   # a 是 b 的别名
            rows.append((b, ia, "OpenCMKG-SameAs"))
            same += 1
    print("SameAs 关系 %d 组 -> 别名 %d 条" % (same, len(rows)))

    # ---- 2. 人工补充 ----
    manual = 0
    for alias, std in CURATED.items():
        eid = name2id.get(std)
        if not eid:
            print("  [跳过] 标准实体不存在：%s" % std)
            continue
        if alias == std:
            continue
        rows.append((alias, eid, "人工补充"))
        manual += 1
    print("人工补充别名 %d 条" % manual)

    cur.executemany(
        "INSERT IGNORE INTO entity_alias (alias, entity_id, source) VALUES (%s,%s,%s)", rows)
    cur.execute("SELECT COUNT(*) FROM entity_alias")
    total = cur.fetchone()[0]
    print("别名表合计 %d 条" % total)

    # ---- 抽查 ----
    for a in ["脑卒中", "肥胖", "2型糖尿病", "高血脂", "中风"]:
        cur.execute("SELECT a.alias, e.name, a.source FROM entity_alias a "
                    "JOIN entities e ON e.id=a.entity_id WHERE a.alias=%s", (a,))
        r = cur.fetchone()
        print("  %-10s -> %s (%s)" % (a, r[1] if r else "未收录", r[2] if r else "-"))

    cur.close()
    conn.close()


if __name__ == "__main__":
    sys.exit(main())
