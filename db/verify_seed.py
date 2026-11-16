# -*- coding: utf-8 -*-
"""
离线校验 seed.cypher 的导入结果（不需要 Neo4j 服务）

作用：把 seed.cypher 里所有 UNWIND 的 JSON 数组解析出来，
      在导入之前就确认节点数、关系数、端点完整性、状态取值是否合法。
用途：在没装 Neo4j 的机器上也能判断「这份图数据能不能导进去」。

用法：python db/verify_seed.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE / "seed.cypher"

ALLOWED_STATUS = {"候选", "待审核", "已审核", "已驳回"}
ALLOWED_TYPE = {"疾病", "危险因素", "症状", "并发症", "药物类别", "检查指标", "生活方式", "其他"}


def main() -> int:
    text = SEED.read_text(encoding="utf-8")
    # 生成器保证每个 UNWIND + JSON 数组独占一行，按行解析最稳妥
    blocks = []
    for line in text.splitlines():
        m = re.match(r"^UNWIND\s+(\[.*\])\s+AS\s+row\s*$", line)
        if m:
            blocks.append(m.group(1))
    if not blocks:
        print("[FAIL] seed.cypher 里没有找到 UNWIND 数据块")
        return 1

    nodes, rels = [], []
    for b in blocks:
        rows = json.loads(b)
        for row in rows:
            if "relation" in row:
                rels.append(row)
            else:
                nodes.append(row)

    errors = []

    # 1. 唯一性
    ids = [n["id"] for n in nodes]
    names = [n["name"] for n in nodes]
    dup_id = {i for i in ids if ids.count(i) > 1}
    dup_name = {n for n in names if names.count(n) > 1}
    if dup_id:
        errors.append(f"实体 id 重复：{sorted(dup_id)[:5]}")
    if dup_name:
        errors.append(f"实体 name 重复（会违反 entity_name_unique 约束）：{sorted(dup_name)[:5]}")

    # 2. 端点完整性
    idset = set(ids)
    bad = [r for r in rels if r["head"] not in idset or r["tail"] not in idset]
    if bad:
        errors.append(f"有 {len(bad)} 条关系的端点不存在，例如 {bad[0]}")

    # 3. 自环
    selfloop = [r for r in rels if r["head"] == r["tail"]]
    if selfloop:
        errors.append(f"有 {len(selfloop)} 条自环关系（MySQL 侧会被 CHECK 拦住）")

    # 4. 状态与类型取值
    bad_status = {n["status"] for n in nodes} - ALLOWED_STATUS
    bad_status |= {r["status"] for r in rels} - ALLOWED_STATUS
    if bad_status:
        errors.append(f"出现非法审核状态：{sorted(bad_status)}")
    bad_type = {n["type"] for n in nodes} - ALLOWED_TYPE
    if bad_type:
        errors.append(f"出现非法实体类型：{sorted(bad_type)}")

    # 5. 三元组唯一（对应 MySQL uk_relations_triple）
    triples = [(r["head"], r["relation"], r["tail"]) for r in rels]
    dup_triple = {t for t in triples if triples.count(t) > 1}
    if dup_triple:
        errors.append(f"三元组重复（会违反唯一键）：{sorted(dup_triple)[:3]}")

    # 6. 与 MySQL 侧行数对账
    rel_ids = [r["id"] for r in rels]
    dup_rid = {i for i in rel_ids if rel_ids.count(i) > 1}
    if dup_rid:
        errors.append(f"关系 id 重复：{sorted(dup_rid)[:5]}")

    # 报告
    print("=" * 62)
    print("seed.cypher 离线校验")
    print("=" * 62)
    print(f"UNWIND 批次     : {len(blocks)}")
    print(f"节点 (:Entity)  : {len(nodes)}")
    print(f"关系 (:REL)     : {len(rels)}")
    from collections import Counter
    print(f"实体类型分布    : {dict(Counter(n['type'] for n in nodes))}")
    print(f"关系状态分布    : {dict(Counter(r['status'] for r in rels))}")
    print(f"关系类型分布    : {dict(Counter(r['relation'] for r in rels))}")
    print("-" * 62)
    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        return 1
    print("[PASS] 唯一性 / 端点完整性 / 状态取值 / 三元组唯一性 全部通过")
    print("       可以在 Neo4j 中直接执行 init.cypher -> seed.cypher")
    return 0


if __name__ == "__main__":
    sys.exit(main())
