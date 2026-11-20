# -*- coding: utf-8 -*-
"""大模型答案生成层（智谱 GLM-4 / 任意 OpenAI 兼容接口）

设计要点
--------
1. 只用标准库 urllib，不引入新依赖；
2. 没有 key、超时、报错一律返回 None，由 answer.py 回退到模板答案，
   保证「没网也能答、有网答得更好」；
3. 提示词把「图谱事实」和「原文切块」一起喂进去，并要求逐句标 [n]，
   这样前端引用的编号和证据卡片始终一一对应，不会出现编造引用。
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(BASE_DIR, ".env")

_cache = {}                 # question -> (ts, result)
_cache_lock = threading.Lock()
_CACHE_TTL = 1800           # 半小时内同样的问题直接命中，答辩演示不重复计费
_CACHE_MAX = 200


def _read_env():
    """读 .env（KEY=VALUE，忽略注释）；环境变量优先"""
    env = {}
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_TIMEOUT"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


_ENV = _read_env()
API_KEY = _ENV.get("LLM_API_KEY", "")
BASE_URL = _ENV.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
MODEL = _ENV.get("LLM_MODEL", "glm-4-flash")
TIMEOUT = float(_ENV.get("LLM_TIMEOUT", "45"))


def info():
    """给前端和自检页看的模型状态（不暴露 key）"""
    return {
        "configured": bool(API_KEY),
        "model": MODEL if API_KEY else None,
        "base_url": BASE_URL if API_KEY else None,
        "key_hint": ("%s****%s" % (API_KEY[:6], API_KEY[-4:])) if len(API_KEY) > 12 else "",
    }


def available():
    return bool(API_KEY)


def chat(messages, temperature=0.3, max_tokens=900):
    """调一次对话补全，返回 (text, usage) ；失败返回 (None, error_msg)"""
    if not API_KEY:
        return None, "未配置 LLM_API_KEY"
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "ignore")[:200]
        except Exception:
            pass
        return None, "HTTP %s %s" % (e.code, detail)
    except Exception as e:                       # 超时、断网、DNS 失败
        return None, "%s: %s" % (type(e).__name__, e)

    try:
        text = body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        return None, "响应格式异常：%s" % str(body)[:200]
    if not text:
        return None, "模型返回空内容"
    return text, body.get("usage") or {}


# ---------------------------------------------------------------- 提示词
SYSTEM = (
    "你是「慢知」慢性病知识问答助手，服务对象是需要了解疾病知识的普通人。\n"
    "输入会给两段资料：【知识图谱事实】（结构化三元组，没有编号）和【文献证据】（带 [1][2] 编号的原文片段）。\n"
    "写作规则：\n"
    "1. 只依据这两段资料作答，不得引入资料之外的药物名、剂量或数字；\n"
    "2. 结论优先用【知识图谱事实】，再补文献里的解释；\n"
    "3. 引用编号只能来自【文献证据】，写成 [1] 或 [1][3] 这种形式。\n"
    "   【知识图谱事实】没有编号，引用它时不要加任何方括号，直接陈述即可；\n"
    "4. 【知识图谱事实】来自多源抽取，可能含噪声；若某条与医学常识明显冲突（例如「肥胖导致胃炎」），"
    "直接忽略，不要写进答案；\n"
    "5. 中文作答，先结论后解释，150-350 字，可用 1. 2. 3. 分点；\n"
    "6. 资料不足以回答时直接说「现有资料未覆盖」，不要猜；\n"
    "7. 涉及用药剂量时补一句「具体用药请遵医嘱」。\n"
    "示例（注意第 1 条没有方括号，第 2 条有）：\n"
    "糖尿病常见并发症包括糖尿病肾病、视网膜病变、周围神经病变。\n"
    "1. 糖尿病肾病：约 20%-40% 的糖尿病患者会合并慢性肾脏病 [2]。\n"
    "2. 视网膜病变：是工作年龄人群首位致盲原因 [4][5]。"
)


def _clean(vals):
    """去掉被更完整词包含的短词与纯数字（OpenCMKG 里有「糖尿」这类截断实体）"""
    vals = [v for v in vals if v and not v.replace(".", "").isdigit()]
    out = []
    for v in sorted(set(vals), key=len, reverse=True):
        if not any(v != o and v in o for o in out):
            out.append(v)
    return out


def _facts_block(facts, limit=3):
    lines = []
    for f in facts[:limit]:
        grouped = {}
        for r in f["relations"]:
            other = r["tail"] if r["head"] == f["entity"] else r["head"]
            grouped.setdefault(r["relation"], [])
            if other not in grouped[r["relation"]]:
                grouped[r["relation"]].append(other)
        parts = ["%s：%s" % (rel, "、".join(_clean(vals)[:5]))
                 for rel, vals in grouped.items() if _clean(vals)]
        if parts:
            lines.append("- %s —— %s" % (f["entity"], "；".join(parts[:4])))
    return "\n".join(lines) if lines else "（无）"


def _evidence_block(chunks, max_cite=6):
    lines = []
    for i, c in enumerate(chunks[:max_cite], 1):
        text = " ".join((c.get("text") or "").split())[:320]
        lines.append("[%d] %s（%s）：%s"
                     % (i, c.get("title") or "", c.get("journal") or c.get("doc_type") or "", text))
    return "\n".join(lines) if lines else "（无）"


def _sanitize(text, max_no):
    """清理引用标记

    模型偶尔会写 [n] 这种占位符，或者把证据原文里的 [599] 抄进答案。
    只保留 1..max_no 范围内的编号，其余删掉，保证前端点引用不会点空。
    """
    text = text.replace("[n]", "").replace("[N]", "").replace("【n】", "")

    def fix(m):
        k = int(m.group(1))
        return m.group(0) if 1 <= k <= max_no else ""

    text = re.sub(r"\[(\d{1,3})\]", fix, text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def generate_answer(question, facts, chunks, intent_name="综合咨询", max_cite=6, temperature=0.3):
    """生成答案正文；失败返回 None（调用方回退模板）"""
    if not API_KEY or not chunks:
        return None

    ck = question.strip()
    now = time.time()
    with _cache_lock:
        hit = _cache.get(ck)
        if hit and now - hit[0] < _CACHE_TTL:
            return hit[1]

    user = (
        "【用户问题】%s\n\n"
        "【问题类型】%s\n\n"
        "【知识图谱事实】\n%s\n\n"
        "【文献证据】\n%s\n\n"
        "请依据以上资料作答。注意：【知识图谱事实】没有编号，引用它时不要写方括号；"
        "只有引用【文献证据】时才标注 [1] 这样的编号。"
        % (question, intent_name, _facts_block(facts), _evidence_block(chunks, max_cite))
    )
    t0 = time.time()
    text, extra = chat(
        [{"role": "system", "content": SYSTEM},
         {"role": "user", "content": user}],
        temperature=temperature, max_tokens=900,
    )
    if not text:
        print("[llm] 生成失败：%s" % extra)
        return None
    text = _sanitize(text, min(len(chunks), max_cite))

    result = {
        "text": text,
        "model": MODEL,
        "usage": extra if isinstance(extra, dict) else {},
        "elapsed_ms": int((time.time() - t0) * 1000),
    }
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX:
            for k in list(_cache)[:50]:
                _cache.pop(k, None)
        _cache[ck] = (now, result)
    return result


# ---------------------------------------------------------------- 跨语言检索
_TRANS_CACHE = {}


def translate_query(question):
    """把中文问题改写成英文检索式（中英跨语言检索用）

    语料里 4,000+ 篇是 PubMed 英文摘要，中文提问直接检索是 0 命中，
    所以先用大模型做一次「医学检索式翻译」，再拿英文词去查英文库。
    返回 {"terms": [...], "query": "..."} ；失败返回 None。
    """
    if not API_KEY:
        return None
    ck = question.strip()
    if ck in _TRANS_CACHE:
        return _TRANS_CACHE[ck]

    prompt = (
        "把下面的中文医学问题改写成英文检索式，用于检索 PubMed 英文摘要。\n"
        "要求：terms 是 3-6 个医学英文词或短语（小写，不要句子）；query 是合成的一句话检索式。\n"
        "只输出 JSON，不要解释：{\"terms\":[\"...\"],\"query\":\"...\"}\n"
        "问题：%s" % question
    )
    text, err = chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=160)
    if not text:
        print("[llm] 查询翻译失败：%s" % err)
        return None
    try:
        s = text[text.index("{"): text.rindex("}") + 1]
        obj = json.loads(s)
        terms = [str(t).strip().lower() for t in obj.get("terms") or [] if str(t).strip()]
        query = (obj.get("query") or " ".join(terms)).strip()
        if not terms:
            return None
        out = {"terms": terms[:6], "query": query}
    except Exception:
        # 模型没按 JSON 输出时，退化为按行/逗号切词
        raw = text.replace("\n", ",").replace("，", ",")
        terms = [t.strip().strip('"').lower() for t in raw.split(",") if len(t.strip()) > 2]
        if not terms:
            return None
        out = {"terms": terms[:6], "query": " ".join(terms[:6])}
    if len(_TRANS_CACHE) > _CACHE_MAX:
        _TRANS_CACHE.clear()
    _TRANS_CACHE[ck] = out
    return out


def self_test():
    """命令行自检：py -3.8-64 backend/llm.py"""
    print("配置：", info())
    if not available():
        print("未配置 key，跳过")
        return
    t0 = time.time()
    text, usage = chat([{"role": "user", "content": "用一句话说明高血压的危险因素"}], max_tokens=120)
    print("耗时 %dms" % int((time.time() - t0) * 1000))
    print("返回：", text if text else ("失败 " + str(usage)))
    print("用量：", usage)


if __name__ == "__main__":
    self_test()
