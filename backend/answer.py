# -*- coding: utf-8 -*-
"""答案组织：把图谱事实 + 检索证据拼成带引用的回答

没有大模型也能给出可信答案：结论来自图谱三元组，论据来自原文切块，
每一条都标 [n] 指向具体文献/指南的哪一段。
"""
import re

import llm

REL_ORDER = ["临床表现", "常用药物", "监测指标", "并发症", "干预措施", "危险因素", "共病", "关联疾病", "导致"]

# 意图 -> (图谱关系类型, 证据里该出现的词)
INTENTS = [
    ("治疗/用药", "常用药物", ["治疗", "用药", "药物", "服药", "剂量"]),
    ("症状表现", "临床表现", ["症状", "表现", "临床", "主诉"]),
    ("检查监测", "监测指标", ["检查", "检测", "指标", "监测", "化验"]),
    ("并发症", "并发症", ["并发症", "合并症", "并发", "靶器官"]),
    ("饮食干预", "干预措施", ["饮食", "膳食", "摄入", "食物", "营养"]),
    ("概念解释", None, ["定义", "是指", "概念", "概述"]),
]


def detect_intent(q):
    """按关键词判定问题意图，返回 (意图名, 对应图谱关系类型, 证据关键词)"""
    for name, rel, kws in INTENTS:
        if any(w in q for w in kws):
            return {"intent": name, "rel": rel, "keywords": kws}
    return {"intent": "综合咨询", "rel": None, "keywords": []}


def _sent(text, n=110):
    """取切块里最靠前的一两句，作为证据摘要"""
    t = re.sub(r"\s+", "", text or "")
    m = re.split(r"(?<=[。！？；])", t)
    out = ""
    for s in m:
        if not s:
            continue
        out += s
        if len(out) >= n:
            break
    return out[:n]


def _dedupe(vals, limit=5):
    """同组内去掉被更完整词包含的短词。

    OpenCMKG 里有「糖尿」这类截断实体，和「糖尿病乳酸性酸中毒」一起出现时很突兀。
    规则：如果某个值是组内另一个值的子串，就丢掉它。
    """
    out = []
    for v in vals:
        if any(v != o and v in o for o in vals):
            continue
        out.append(v)
    return out[:limit]


def compose(question, entities, facts, chunks, intent=None, max_cite=6, use_llm=True, query_en=None):
    intent = intent or detect_intent(question)
    steps = []
    steps.append({"name": "意图识别", "detail": "问题类型：%s" % intent["intent"]})
    if entities:
        steps.append({"name": "实体链接",
                      "detail": "命中实体：" + "、".join("%s（%s）" % (e["name"], e["type"]) for e in entities)})
    else:
        steps.append({"name": "实体链接", "detail": "未命中图谱实体，仅走向量与关键词检索"})
    if query_en:
        steps.append({"name": "跨语言改写",
                      "detail": "中文问题 → 英文检索式：%s" % "、".join(query_en[:6])})
    steps.append({"name": "多路召回",
                  "detail": "关键词路 / 向量路 / 图谱路%s 并行召回，共 %d 条候选"
                            % (" / 跨语言路" if query_en else "", len(chunks))})
    steps.append({"name": "RRF 融合", "detail": "按 1/(60+rank) 累加各路排名，再按疾病维度与意图词加权"})

    # ---- 结论段：图谱事实（意图对应的关系类型优先），作为模板答案与 LLM 的依据 ----
    prefer = intent.get("rel")
    lines = []
    for f in facts[:3]:
        grouped = {}
        for r in f["relations"]:
            grouped.setdefault(r["relation"], [])
            other = r["tail"] if r["head"] == f["entity"] else r["head"]
            if other not in grouped[r["relation"]]:
                grouped[r["relation"]].append(other)
        order = ([prefer] if prefer and prefer in grouped else []) + \
                [r for r in REL_ORDER if r in grouped and r != prefer] + \
                [r for r in grouped if r not in REL_ORDER and r != prefer]
        parts = ["%s包括%s" % (rel, "、".join(_dedupe(grouped[rel]))) for rel in order if grouped.get(rel)]
        if parts:
            lines.append("【%s】%s。" % (f["entity"], "；".join(parts[:3])))
    if not lines:
        lines.append("未在知识图谱中直接匹配到相关实体，以下为文献检索结果。")

    # ---- 论据段：切块 ----
    cite_lines = []
    for i, c in enumerate(chunks[:max_cite], 1):
        cite_lines.append("[%d] %s（%s 第 %d 块）：%s" % (
            i, c["title"], c["source"], c.get("chunk_idx", 0), _sent(c["text"])))

    # ---- 优先走大模型，失败则用图谱模板兜底 ----
    gen = llm.generate_answer(question, facts, chunks, intent["intent"], max_cite) if use_llm else None
    if gen:
        body = gen["text"]
        engine = {"mode": "llm", "name": gen["model"], "elapsed_ms": gen["elapsed_ms"],
                  "usage": gen.get("usage") or {}}
        steps.append({"name": "大模型生成",
                      "detail": "%s 依据图谱事实与 %d 条证据成文，耗时 %dms"
                                % (gen["model"], min(len(chunks), max_cite), gen["elapsed_ms"])})
    else:
        body = "\n".join(lines)
        engine = {"mode": "template", "name": "图谱模板",
                  "reason": "未配置模型或调用失败，已回退模板答案"}
        steps.append({"name": "答案组织", "detail": "图谱事实作结论，原文切块作论据，逐条标注来源"})

    # 证据来源清单单独放 answer_full：页面上已经用「参考文献 / 证据卡片」渲染了一遍，
    # 再拼进正文就会重复显示一大段，正文只留答案本身。
    answer = body
    answer_full = answer + ("\n\n证据来源：\n" + "\n".join(cite_lines) if cite_lines else "")

    citations = []
    for i, c in enumerate(chunks[:max_cite], 1):
        citations.append({
            "no": i,
            "doc_id": c["doc_id"],
            "title": c["title"],
            "source": c["source"],
            "doc_type": c.get("doc_type"),
            "pmid": c.get("pmid"),
            "journal": c.get("journal"),
            "date": c.get("date"),
            "chunk_idx": c.get("chunk_idx"),
            "snippet": _sent(c["text"], 160),
            "routes": c.get("routes", []),
            "rrf": c.get("rrf"),
        })
    return {"answer": answer, "answer_full": answer_full,
            "citations": citations, "steps": steps,
            "engine": engine, "template_answer": "\n".join(lines)}
