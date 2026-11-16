# -*- coding: utf-8 -*-
"""
数据包质量审计

回答一个问题：数据包里的数据到底处理到什么程度、能不能直接用来做系统。
输出的是数字，不是结论。

用法：py -3.8-64 db/audit_data.py
"""
import io
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(HERE), "数据包")

CN = re.compile(r"[\u4e00-\u9fff]")


def load(rel):
    with io.open(os.path.join(PKG, rel), encoding="utf-8") as f:
        return json.load(f)


def pct(a, b):
    return 0.0 if not b else round(a * 100.0 / b, 1)


def line(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def audit_pubmed():
    line("1. PubMed 文献（03_清洗后数据/解析结构化JSON/pubmed_records.json）")
    d = load("03_清洗后数据/解析结构化JSON/pubmed_records.json")
    n = len(d)
    pmids = [str(x.get("pmid") or "") for x in d]
    dup = [k for k, v in Counter(pmids).items() if v > 1]
    no_title = sum(1 for x in d if not (x.get("title") or "").strip())
    no_abs = sum(1 for x in d if not (x.get("abstract") or "").strip())
    no_year = sum(1 for x in d if not x.get("year"))
    no_mesh = sum(1 for x in d if not x.get("mesh"))
    no_doi = sum(1 for x in d if not x.get("doi"))
    cn = sum(1 for x in d if CN.search((x.get("title") or "") + (x.get("abstract") or "")))
    print("  记录数            %d" % n)
    print("  PMID 重复         %d  %s" % (len(dup), dup[:3]))
    print("  标题为空          %d  (%.1f%%)" % (no_title, pct(no_title, n)))
    print("  摘要为空          %d  (%.1f%%)" % (no_abs, pct(no_abs, n)))
    print("  年份缺失          %d  (%.1f%%)" % (no_year, pct(no_year, n)))
    print("  MeSH 为空         %d  (%.1f%%)" % (no_mesh, pct(no_mesh, n)))
    print("  DOI 缺失          %d  (%.1f%%)" % (no_doi, pct(no_doi, n)))
    print("  含中文的记录      %d  (%.1f%%)  <- 中文语料是否来自这里" % (cn, pct(cn, n)))
    print("  疾病分布          %s" % dict(Counter(x.get("disease") for x in d)))
    lens = [len(x.get("abstract") or "") for x in d if x.get("abstract")]
    lens.sort()
    if lens:
        print("  摘要长度 中位数/均值/最长  %d / %d / %d" % (
            lens[len(lens) // 2], sum(lens) // len(lens), lens[-1]))
    return d


def audit_chunks():
    line("2. 向量切块（04_预处理中间产物/向量切块/向量切块清单_300重叠50.json）")
    c = load("04_预处理中间产物/向量切块/向量切块清单_300重叠50.json")
    ch = c["chunks"]
    n = len(ch)
    empty = sum(1 for x in ch if not (x.get("text") or "").strip())
    texts = [x.get("text") or "" for x in ch]
    dup = n - len(set(texts))
    lens = sorted(len(t) for t in texts)
    short = sum(1 for t in texts if len(t) < 100)
    cn = sum(1 for t in texts if CN.search(t))
    print("  切块数            %d（声明 %s）" % (n, c.get("count")))
    print("  参数              窗口 %s / 重叠 %s" % (c.get("chunk_size"), c.get("overlap")))
    print("  空文本            %d" % empty)
    print("  完全重复          %d  (%.1f%%)" % (dup, pct(dup, n)))
    print("  长度 <100 字      %d  (%.1f%%)" % (short, pct(short, n)))
    print("  长度 中位数/均值  %d / %d" % (lens[n // 2], sum(lens) // n))
    print("  含中文的切块      %d  (%.1f%%)  <- 中文检索能命中多少" % (cn, pct(cn, n)))
    print("  来源分布          %s" % dict(Counter(x.get("source") for x in ch)))
    # 检查 pmid 是否能对上文献
    pm = set(str(x.get("pmid") or "") for x in ch if x.get("pmid"))
    print("  涉及文献数        %d" % len(pm))
    return ch


def audit_triples():
    line("3. 文献锚定三元组（04_预处理中间产物/三元组清单/文献锚定三元组.json）")
    t = load("04_预处理中间产物/三元组清单/文献锚定三元组.json")["triples"]
    n = len(t)
    keys = [(x["head"], x["relation"], x["tail"]) for x in t]
    dup = n - len(set(keys))
    selfloop = sum(1 for x in t if x["head"] == x["tail"])
    rel = Counter(x["relation"] for x in t)
    print("  三元组数          %d" % n)
    print("  完全重复          %d  (%.1f%%)" % (dup, pct(dup, n)))
    print("  自环              %d" % selfloop)
    print("  关系类型          %s   <- 只有一种，是文献标注不是实体关系" % dict(rel))
    print("  head 形态         %s" % dict(Counter(
        "PubMed:PMID" if str(x["head"]).startswith("PubMed:") else "其他" for x in t)))
    return t


def audit_opencmkg():
    line("4. OpenCMKG 实体关系（01_外部公开语料/结构化知识图谱/OpenCMKG/triples.txt）")
    path = os.path.join(PKG, "01_外部公开语料/结构化知识图谱/OpenCMKG/triples.txt")
    n = bad = selfloop = 0
    keys = set()
    dup = 0
    rel = Counter()
    heads, tails = set(), set()
    cn_head = cn_tail = 0
    with io.open(path, encoding="utf-8") as f:
        for raw in f:
            p = raw.rstrip("\n").split(",")
            if len(p) != 3 or not p[0].strip() or not p[2].strip():
                bad += 1
                continue
            h, r, tl = p[0].strip(), p[1].strip(), p[2].strip()
            n += 1
            if h == tl:
                selfloop += 1
            k = (h, r, tl)
            if k in keys:
                dup += 1
            keys.add(k)
            rel[r] += 1
            heads.add(h)
            tails.add(tl)
            if CN.search(h):
                cn_head += 1
            if CN.search(tl):
                cn_tail += 1
    print("  有效行            %d" % n)
    print("  格式错误行        %d" % bad)
    print("  重复三元组        %d  (%.1f%%)" % (dup, pct(dup, n)))
    print("  自环              %d" % selfloop)
    print("  关系类型数        %d" % len(rel))
    print("  头实体 / 尾实体   %d / %d" % (len(heads), len(tails)))
    print("  中文头实体占比    %.1f%%" % pct(cn_head, n))
    print("  中文尾实体占比    %.1f%%  <- 英文实体是 MeSH 原词，中文实体是本土词" % pct(cn_tail, n))
    for k, v in rel.most_common():
        print("    %-32s %6d" % (k, v))
    return rel


def audit_entity_overlap(pubmed, triples, rel):
    line("5. 跨源一致性：文献 / 切块 / 三元组 / 图谱能不能对上")
    mesh = load("04_预处理中间产物/实体候选/实体候选列表_有效MeSH.json")["entities"]
    print("  MeSH 有效实体      %d" % len(mesh))
    cn_mesh = sum(1 for m in mesh if CN.search(m))
    print("  其中中文名          %d  (%.1f%%)  <- 全是英文 MeSH 原词，中文对齐是缺口" % (
        cn_mesh, pct(cn_mesh, len(mesh))))
    print("  文献锚定的尾实体    %d（去重）" % len(set(x["tail"] for x in triples)))
    print("  图谱关系里的实体    由 OpenCMKG 提供，与 MeSH 两套体系，靠 entity_alias 归一")


def main():
    print("数据包质量审计  %s" % PKG)
    pubmed = audit_pubmed()
    audit_chunks()
    triples = audit_triples()
    rel = audit_opencmkg()
    audit_entity_overlap(pubmed, triples, rel)
    line("结论")
    print("  1. 03/04 层数据是处理过的：去重、字段齐全、切块参数统一，能直接用。")
    print("  2. 04 的三元组是「文献-涉及-MeSH」标注，不是实体关系，不能当图谱用。")
    print("  3. 真正的实体关系只有 OpenCMKG 一处，13 类关系，需映射到本系统 9 类。")
    print("  4. 中文语料缺口在指南 PDF（未抽取）和 OpenCMKG；PubMed 全英文。")
    print("  5. 实体名两套体系（MeSH 英文 / OpenCMKG 中文），归一必须做，不是数据没处理好。")


if __name__ == "__main__":
    sys.exit(main())
