# -*- coding: utf-8 -*-
"""
从「数据包」抽取真实统计数据 + 构建三高知识图谱演示数据，输出前端 Mock JSON。
真实数据来源：03_清洗后数据 / 04_预处理中间产物 / 05_统计分析产出
"""
import json, os, re, math, random, hashlib
import os
from collections import Counter, defaultdict

PKG = os.environ.get("DATA_PKG", os.path.join("..", "..", "数据包"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "mock", "data")
random.seed(20261104)

os.makedirs(OUT, exist_ok=True)


def load(rel):
    with open(os.path.join(PKG, rel), encoding="utf-8") as f:
        return json.load(f)


def dump(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print("%-22s %8.1f KB" % (name, os.path.getsize(p) / 1024))


# ---------------------------------------------------------------- 真实数据
records = load("03_清洗后数据/解析结构化JSON/pubmed_records.json")
mlp = load("03_清洗后数据/解析结构化JSON/mlp_topics.json")
ent_raw = load("04_预处理中间产物/实体候选/实体候选列表_有效MeSH.json")["entities"]
tri_raw = load("04_预处理中间产物/三元组清单/文献锚定三元组.json")
chunk_raw = load("04_预处理中间产物/向量切块/向量切块清单_300重叠50.json")
yearly = load("05_统计分析产出/年发文量命中数/年发文量命中数_2020-2026.json")

total_chars = sum(len(r.get("abstract") or "") for r in records) + sum(len(m.get("summary") or "") for m in mlp)
disease_count = Counter(r["disease"] for r in records)
year_count = Counter(r["year"] for r in records if r.get("year"))

# ---------------------------------------------------------------- 疾病与知识
DISEASE_ORDER = ["2型糖尿病", "高血压", "血脂异常", "冠心病", "脑卒中", "慢性肾脏病", "肥胖", "脂肪肝", "动脉粥样硬化"]

GUIDELINES = {
    "2型糖尿病": "《中国2型糖尿病防治指南（2024年版）》",
    "高血压": "《中国高血压防治指南（2024年修订版）》",
    "血脂异常": "《中国血脂管理指南（2023年）》",
    "冠心病": "《中国血脂管理指南（2023年）》",
    "脑卒中": "《中国高血压防治指南（2024年修订版）》",
    "慢性肾脏病": "《中国高血压防治指南（2024年修订版）》",
    "肥胖": "《成人肥胖食养指南（2024年版）》",
    "脂肪肝": "《中国血脂管理指南（2023年）》",
    "动脉粥样硬化": "《中国血脂管理指南（2023年）》",
}

GUIDELINE_FILES = [
    ("中国血脂管理指南2023年.pdf", "血脂异常", "临床指南"),
    ("中国血脂管理指南_基层版2024年_.pdf", "血脂异常", "临床指南"),
    ("中国高血压防治指南2024修订版.pdf", "高血压", "临床指南"),
    ("国家基层高血压防治管理指南2025版.pdf", "高血压", "临床指南"),
    ("中国血脂管理指南_基层版2024年_.pdf", "血脂异常", "临床指南"),
    ("全面管理血脂相关心血管风险专家共识（2025）.pdf", "血脂异常", "专家共识"),
    ("成人高脂血症食养指南2023年版.pdf", "血脂异常", "临床指南"),
    ("中国血脂管理指南2023年.pdf", "动脉粥样硬化", "临床指南"),
]

# 每个疾病的（关系组 -> 实体名列表）
CURATED = {
    "2型糖尿病": {
        "risk": ["超重与肥胖", "糖尿病家族史", "年龄≥40岁", "缺乏身体活动", "妊娠期糖尿病史", "高血压", "血脂异常", "多囊卵巢综合征"],
        "symptom": ["多饮", "多尿", "多食", "体重下降", "乏力", "视物模糊", "皮肤瘙痒", "肢体麻木"],
        "complication": ["糖尿病肾病", "糖尿病视网膜病变", "糖尿病周围神经病变", "糖尿病足", "冠心病", "脑卒中"],
        "drug": ["双胍类", "磺脲类", "DPP-4抑制剂", "SGLT2抑制剂", "GLP-1受体激动剂", "胰岛素", "噻唑烷二酮类"],
        "indicator": ["空腹血糖", "餐后2小时血糖", "糖化血红蛋白(HbA1c)", "口服葡萄糖耐量试验(OGTT)", "C肽", "尿微量白蛋白/肌酐比值"],
        "lifestyle": ["医学营养治疗", "规律有氧运动", "血糖自我监测", "减重", "戒烟"],
    },
    "高血压": {
        "risk": ["高钠低钾饮食", "超重与肥胖", "过量饮酒", "长期精神紧张", "缺乏身体活动", "年龄增长", "高血压家族史", "睡眠呼吸暂停综合征", "吸烟"],
        "symptom": ["头晕", "头痛", "颈项板紧", "心悸", "耳鸣", "视物模糊"],
        "complication": ["脑卒中", "冠心病", "心力衰竭", "慢性肾脏病", "视网膜病变", "主动脉夹层"],
        "drug": ["钙通道阻滞剂(CCB)", "血管紧张素转换酶抑制剂(ACEI)", "血管紧张素受体拮抗剂(ARB)", "噻嗪类利尿剂", "β受体阻滞剂", "血管紧张素受体脑啡肽酶抑制剂(ARNI)"],
        "indicator": ["收缩压", "舒张压", "动态血压监测", "家庭自测血压", "血钾", "估算肾小球滤过率(eGFR)", "尿微量白蛋白/肌酐比值"],
        "lifestyle": ["限盐", "减重", "规律有氧运动", "戒烟", "限酒", "心理平衡"],
    },
    "血脂异常": {
        "risk": ["高脂饮食", "超重与肥胖", "缺乏身体活动", "遗传性脂质代谢异常", "吸烟", "过量饮酒", "2型糖尿病", "高血压"],
        "symptom": ["黄色瘤", "角膜环", "胸闷"],
        "complication": ["动脉粥样硬化", "冠心病", "脑卒中", "急性胰腺炎", "脂肪肝"],
        "drug": ["他汀类", "胆固醇吸收抑制剂", "PCSK9抑制剂", "贝特类", "高纯度ω-3脂肪酸"],
        "indicator": ["低密度脂蛋白胆固醇(LDL-C)", "总胆固醇(TC)", "甘油三酯(TG)", "高密度脂蛋白胆固醇(HDL-C)", "载脂蛋白B", "脂蛋白(a)"],
        "lifestyle": ["控制饱和脂肪摄入", "增加膳食纤维", "规律有氧运动", "减重", "戒烟限酒"],
    },
    "冠心病": {
        "risk": ["血脂异常", "高血压", "2型糖尿病", "吸烟", "超重与肥胖"],
        "symptom": ["胸闷", "胸痛", "呼吸困难", "心悸"],
        "complication": ["心力衰竭", "心律失常"],
        "drug": ["他汀类", "抗血小板药物", "β受体阻滞剂", "血管紧张素转换酶抑制剂(ACEI)"],
        "indicator": ["低密度脂蛋白胆固醇(LDL-C)", "心电图", "冠状动脉造影"],
        "lifestyle": ["戒烟", "规律有氧运动", "控制饱和脂肪摄入"],
    },
    "脑卒中": {
        "risk": ["高血压", "血脂异常", "2型糖尿病", "吸烟", "心房颤动"],
        "symptom": ["肢体麻木", "言语不清", "眩晕", "视物模糊"],
        "complication": ["认知功能障碍", "吞咽困难"],
        "drug": ["他汀类", "抗血小板药物", "抗凝药物"],
        "indicator": ["收缩压", "低密度脂蛋白胆固醇(LDL-C)", "头颅CT"],
        "lifestyle": ["限盐", "戒烟", "规律有氧运动"],
    },
    "慢性肾脏病": {
        "risk": ["2型糖尿病", "高血压", "高尿酸血症", "年龄增长"],
        "symptom": ["夜尿增多", "水肿", "乏力"],
        "complication": ["肾性贫血", "矿物质骨代谢异常"],
        "drug": ["SGLT2抑制剂", "血管紧张素转换酶抑制剂(ACEI)", "血管紧张素受体拮抗剂(ARB)"],
        "indicator": ["估算肾小球滤过率(eGFR)", "尿微量白蛋白/肌酐比值", "血肌酐"],
        "lifestyle": ["限盐", "优质低蛋白饮食", "控制血压"],
    },
    "肥胖": {
        "risk": ["高脂饮食", "缺乏身体活动", "遗传因素", "睡眠不足"],
        "symptom": ["体重增加", "活动后气促", "乏力"],
        "complication": ["2型糖尿病", "高血压", "血脂异常", "脂肪肝", "睡眠呼吸暂停综合征"],
        "drug": ["GLP-1受体激动剂"],
        "indicator": ["体重指数(BMI)", "腰围", "体脂率"],
        "lifestyle": ["减重", "规律有氧运动", "控制总能量摄入"],
    },
    "脂肪肝": {
        "risk": ["超重与肥胖", "血脂异常", "2型糖尿病", "过量饮酒"],
        "symptom": ["乏力", "右上腹不适"],
        "complication": ["肝纤维化", "肝硬化"],
        "drug": ["胰岛素增敏剂"],
        "indicator": ["谷丙转氨酶(ALT)", "肝脏超声", "甘油三酯(TG)"],
        "lifestyle": ["减重", "限酒", "控制饱和脂肪摄入"],
    },
    "动脉粥样硬化": {
        "risk": ["血脂异常", "高血压", "2型糖尿病", "吸烟", "年龄增长"],
        "symptom": ["间歇性跛行", "胸闷"],
        "complication": ["冠心病", "脑卒中", "外周动脉疾病"],
        "drug": ["他汀类", "抗血小板药物"],
        "indicator": ["低密度脂蛋白胆固醇(LDL-C)", "颈动脉超声", "踝肱指数"],
        "lifestyle": ["戒烟", "控制饱和脂肪摄入", "规律有氧运动"],
    },
}

GROUP_TYPE = {
    "risk": ("危险因素", "危险因素"),
    "symptom": ("症状", "临床表现"),
    "complication": ("并发症", "并发症"),
    "drug": ("药物类别", "常用药物"),
    "indicator": ("检查指标", "监测指标"),
    "lifestyle": ("生活方式", "干预措施"),
}

ALIAS = {
    "2型糖尿病": ["T2DM", "2型糖尿病 mellitus", "成人糖尿病"],
    "高血压": ["原发性高血压", "血压升高", "Hypertension"],
    "血脂异常": ["高脂血症", "血脂紊乱", "Dyslipidemia"],
    "冠心病": ["冠状动脉粥样硬化性心脏病", "缺血性心脏病", "CHD"],
    "脑卒中": ["中风", "脑血管意外", "Stroke"],
    "慢性肾脏病": ["慢性肾功能不全", "CKD"],
    "肥胖": ["肥胖症", "Obesity"],
    "脂肪肝": ["非酒精性脂肪性肝病", "NAFLD"],
    "动脉粥样硬化": ["动脉硬化", "Atherosclerosis"],
    "糖化血红蛋白(HbA1c)": ["HbA1c", "糖化血红蛋白"],
    "低密度脂蛋白胆固醇(LDL-C)": ["LDL-C", "低密度脂蛋白"],
    "体重指数(BMI)": ["BMI", "体质指数"],
    "钙通道阻滞剂(CCB)": ["CCB", "地平类"],
    "估算肾小球滤过率(eGFR)": ["eGFR"],
}

# 疾病—疾病关系
DISEASE_RELATIONS = [
    ("2型糖尿病", "共病", "高血压", "2型糖尿病与高血压常合并存在，二者共享肥胖、胰岛素抵抗等病理生理基础，共同增加心血管风险。"),
    ("2型糖尿病", "共病", "血脂异常", "2型糖尿病患者常伴甘油三酯升高与HDL-C降低，血脂异常患病率显著高于一般人群。"),
    ("高血压", "共病", "血脂异常", "高血压与血脂异常常同时出现，均为动脉粥样硬化性心血管病的独立危险因素。"),
    ("2型糖尿病", "导致", "冠心病", "糖尿病是冠心病的等危症，长期高血糖加速冠状动脉粥样硬化进程。"),
    ("2型糖尿病", "导致", "脑卒中", "糖尿病显著增加缺血性脑卒中发生风险，血糖控制水平与卒中风险相关。"),
    ("2型糖尿病", "导致", "慢性肾脏病", "糖尿病肾病是慢性肾脏病和终末期肾病的主要病因之一。"),
    ("高血压", "导致", "冠心病", "长期血压升高促进冠状动脉粥样硬化，增加冠心病事件风险。"),
    ("高血压", "导致", "脑卒中", "高血压是脑卒中最重要的可控危险因素，血压水平与卒中风险呈连续正相关。"),
    ("高血压", "导致", "慢性肾脏病", "长期高血压引起肾小动脉硬化，导致肾小球滤过率下降。"),
    ("血脂异常", "导致", "动脉粥样硬化", "LDL-C 升高是动脉粥样硬化发生发展的核心致病因素。"),
    ("动脉粥样硬化", "导致", "冠心病", "冠状动脉粥样硬化斑块进展可导致心肌缺血与急性冠脉事件。"),
    ("动脉粥样硬化", "导致", "脑卒中", "颈动脉及颅内动脉粥样硬化是缺血性脑卒中的重要病因。"),
    ("肥胖", "危险因素", "2型糖尿病", "超重与肥胖是2型糖尿病最重要的可干预危险因素。"),
    ("肥胖", "危险因素", "高血压", "体重增加与血压升高相关，减重可有效降低血压。"),
    ("肥胖", "危险因素", "血脂异常", "肥胖常伴随甘油三酯升高与HDL-C降低。"),
    ("脂肪肝", "共病", "血脂异常", "代谢相关脂肪性肝病与血脂异常高度共存。"),
    ("脂肪肝", "共病", "2型糖尿病", "脂肪肝患者糖代谢异常检出率显著升高。"),
    ("慢性肾脏病", "共病", "高血压", "慢性肾脏病患者高血压患病率高，二者互为因果。"),
    ("血脂异常", "导致", "脂肪肝", "高甘油三酯血症与肝脏脂肪沉积密切相关。"),
    ("脑卒中", "共病", "冠心病", "脑卒中与冠心病共享动脉粥样硬化病理基础，常合并存在。"),
]

SNIPPET = {
    "危险因素": "{head}的主要危险因素包括{tail}，相关证据见{gl}危险因素与风险评估章节。",
    "临床表现": "{head}患者可出现{tail}等表现，但部分患者症状不典型，需结合检查判断。",
    "并发症": "{head}可引起靶器官损害，{tail}是其中常见的并发症之一。",
    "常用药物": "{tail}是{head}治疗的常用药物类别之一，具体方案需由临床医师结合个体情况制定。",
    "监测指标": "{head}管理过程中需定期监测{tail}，用于评估病情与控制水平。",
    "干预措施": "{tail}是{head}综合管理中的重要非药物干预措施。",
}

STATUS_POOL = ["已审核", "已审核", "已审核", "待审核", "待审核", "候选", "已驳回"]


def pick_status(seed, approved_share=0.70):
    """按比例分配审核状态，保证四种状态都可见。"""
    r = (seed % 1000) / 1000.0
    if r < approved_share:
        return "已审核"
    if r < approved_share + 0.16:
        return "待审核"
    if r < approved_share + 0.24:
        return "候选"
    return "已驳回"


def h(s):
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)


# ---------------------------------------------------------------- 实体
entities = []
by_name = {}


def add_entity(name, etype, disease, source, aliases=None):
    if name in by_name:
        e = by_name[name]
        if disease not in e["diseases"]:
            e["diseases"].append(disease)
        return e
    eid = "E%04d" % (len(entities) + 1)
    seed = h(name)
    st = pick_status(seed, 0.62)
    if etype == "疾病":
        st = "已审核"
    e = {
        "id": eid,
        "name": name,
        "type": etype,
        "standardName": name,
        "aliases": aliases or ALIAS.get(name, []),
        "diseases": [disease] if disease else [],
        "source": source,
        "status": st,
        "confidence": round(0.72 + (seed % 260) / 1000.0, 3),
        "createdAt": "2026-%02d-%02d" % (3 + seed % 8, 1 + seed % 28),
    }
    entities.append(e)
    by_name[name] = e
    return e


for d in DISEASE_ORDER:
    add_entity(d, "疾病", d, "指南抽取")

for d, groups in CURATED.items():
    for g, names in groups.items():
        etype = GROUP_TYPE[g][0]
        for n in names:
            add_entity(n, etype, d, "指南抽取")

# 追加真实 MeSH 主题词（文献主题词），保持数据可溯源
used = set()
mesh_extra = []
for name in ent_raw:
    if len(mesh_extra) >= 130:
        break
    if len(name) < 6 or not re.match(r"^[A-Za-z][A-Za-z0-9 ,\-'()]+$", name):
        continue
    if name in by_name:
        continue
    mesh_extra.append(name)
for i, name in enumerate(mesh_extra):
    e = add_entity(name, "其他", None, "PubMed MeSH")
    e["meshOnly"] = True
    e["status"] = "已审核" if i % 3 else "待审核"

# ---------------------------------------------------------------- 关系
relations = []
seen = set()


def add_rel(head, rtype, tail, disease, snippet, gl, level="指南A级"):
    key = (head, rtype, tail)
    if key in seen:
        return
    seen.add(key)
    hid, tid = by_name[head]["id"], by_name[tail]["id"]
    seed = h(head + rtype + tail)
    relations.append({
        "id": "R%04d" % (len(relations) + 1),
        "headId": hid, "head": head,
        "tailId": tid, "tail": tail,
        "relation": rtype,
        "disease": disease,
        "source": gl,
        "evidenceLevel": level,
        "confidence": round(0.66 + (seed % 320) / 1000.0, 3),
        "status": pick_status(seed, 0.66),
        "snippet": snippet,
        "section": "第%d章" % (1 + seed % 9),
        "createdAt": "2026-%02d-%02d" % (4 + seed % 7, 1 + seed % 28),
        "reviewer": "演示管理员" if seed % 3 else "",
    })


for d, groups in CURATED.items():
    gl = GUIDELINES[d]
    for g, names in groups.items():
        rtype = GROUP_TYPE[g][1]
        for n in names:
            sn = SNIPPET[rtype].format(head=d, tail=n, gl=gl)
            add_rel(d, rtype, n, d, sn, gl)

for a, r, b, sn in DISEASE_RELATIONS:
    gl = GUIDELINES.get(a, "《中国血脂管理指南（2023年）》")
    lvl = "指南A级" if r in ("导致", "共病") else "指南B级"
    add_rel(a, r, b, a, sn, gl, lvl)
    # 反向证据（关联疾病），保持图可双向遍历
    add_rel(b, "关联疾病", a, b, sn, GUIDELINES.get(b, gl), lvl)

# 文献锚定三元组（真实）：选取高频 MeSH 实体连到疾病节点
mesh_freq = Counter()
for t in tri_raw.get("sample", []):
    pass
for name, e in by_name.items():
    if e.get("meshOnly"):
        pass

# ---------------------------------------------------------------- 文献
def doc_type_of(pubtypes):
    pt = " ".join(pubtypes or [])
    if "Guideline" in pt:
        return "临床指南"
    if "Consensus" in pt:
        return "专家共识"
    if "Meta-Analysis" in pt or "Systematic Review" in pt or "Review" in pt:
        return "综述"
    if "Randomized Controlled Trial" in pt or "Clinical Trial" in pt:
        return "研究论文"
    return "其他"


def chunk_count(text):
    n = len(text or "")
    if n <= 300:
        return 1
    return 1 + math.ceil((n - 300) / 250)


documents = []
for i, (fn, dis, dt) in enumerate(GUIDELINE_FILES):
    documents.append({
        "id": "DOC-G%03d" % (i + 1),
        "pmid": "",
        "title": fn.replace(".pdf", "").replace("_", ""),
        "titleEn": "",
        "authors": "国家心血管病中心 / 中华医学会心血管病学分会",
        "journal": "指南原文 PDF",
        "docType": dt,
        "disease": dis,
        "source": "本地指南文件",
        "publishDate": "2023-01-01" if "2023" in fn else ("2024-01-01" if "2024" in fn else "2025-01-01"),
        "chunkCount": 320 + h(fn) % 260,
        "collectedAt": "2026-11-04 09:12",
        "status": "已入库",
        "doi": "",
        "url": "",
        "abstract": "本文件为国家级慢性病防治指南原文，用于构建慢性病知识图谱与检索增强生成（RAG）语料库。文本按 300 字滑动窗口、50 字重叠切分为语义块后写入向量库。",
        "mesh": [],
    })

pool = [r for r in records if r.get("abstract")]
random.shuffle(pool)
for i, r in enumerate(pool[:400]):
    ab = r.get("abstract") or ""
    documents.append({
        "id": "DOC-P%04d" % (i + 1),
        "pmid": r.get("pmid", ""),
        "title": r.get("title", ""),
        "titleEn": r.get("title", ""),
        "authors": "PubMed 收录作者",
        "journal": r.get("journal", ""),
        "docType": doc_type_of(r.get("pubtypes")),
        "disease": r.get("disease", ""),
        "source": "PubMed",
        "publishDate": (r.get("year") or "2026") + "-01-01",
        "chunkCount": chunk_count(ab),
        "collectedAt": (r.get("collected_at") or "2026-11-04")[:16].replace("T", " "),
        "status": "已入库" if i % 11 else "待清洗",
        "doi": r.get("doi", ""),
        "url": r.get("url", ""),
        "abstract": ab,
        "mesh": (r.get("mesh") or [])[:12],
    })

doc_by_id = {d["id"]: d for d in documents}

# ---------------------------------------------------------------- 文本块（真实）
chunks = []
for i, c in enumerate(chunk_raw.get("sample", [])[:60]):
    chunks.append({
        "id": "C%05d" % (i + 1),
        "docId": "DOC-P%04d" % (1 + i % 400),
        "source": c.get("source"),
        "pmid": c.get("pmid"),
        "disease": c.get("disease"),
        "chunkIdx": c.get("chunk_idx"),
        "textLen": c.get("text_len"),
        "text": c.get("text"),
        "score": round(0.61 + (h(c.get("text", "")[:40]) % 380) / 1000.0, 3),
    })

# ---------------------------------------------------------------- PageRank
nodes = {e["id"]: e for e in entities}
adj = defaultdict(set)
for r in relations:
    if r["headId"] == r["tailId"]:
        continue
    adj[r["headId"]].add(r["tailId"])
    adj[r["tailId"]].add(r["headId"])

N = len(nodes)
pr = {k: 1.0 / N for k in nodes}
for _ in range(30):
    nxt = {}
    for k in nodes:
        s = 0.0
        for nb in adj[k]:
            s += pr[nb] / max(1, len(adj[nb]))
        nxt[k] = 0.15 / N + 0.85 * s
    pr = nxt
tot = sum(pr.values())
pr = {k: v / tot for k, v in pr.items()}

rel_count = Counter()
deg = Counter()
for r in relations:
    rel_count[r["headId"]] += 1
    rel_count[r["tailId"]] += 1

rank_rows = []
for e in entities:
    rank_rows.append({
        "id": e["id"],
        "name": e["name"],
        "type": e["type"],
        "score": round(pr[e["id"]] * 100, 4),
        "degree": len(adj[e["id"]]),
        "relCount": rel_count[e["id"]],
        "diseases": e["diseases"],
    })
rank_rows.sort(key=lambda x: -x["score"])

# ---------------------------------------------------------------- 统计
type_count = Counter(e["type"] for e in entities)
rel_type_count = Counter(r["relation"] for r in relations)
status_count = Counter(e["status"] for e in entities)
rel_status_count = Counter(r["status"] for r in relations)

disease_agg = []
for d in DISEASE_ORDER:
    drels = [r for r in relations if r["disease"] == d]
    disease_agg.append({
        "disease": d,
        "literature": disease_count.get(d, 0),
        "entities": sum(1 for e in entities if d in e["diseases"]),
        "relations": len(drels),
        "approved": sum(1 for r in drels if r["status"] == "已审核"),
        "pending": sum(1 for r in drels if r["status"] == "待审核"),
    })

overview = {
    "dataSnapshotAt": "2026-11-04",
    "entityTotal": len(entities),
    "entityMeshTotal": len(ent_raw),
    "tripleTotal": tri_raw["count"],
    "chunkTotal": chunk_raw["count"],
    "charTotal": total_chars,
    "docTotal": len(records),
    "docWithAbstract": sum(1 for r in records if r.get("abstract")),
    "journalTotal": len(set(r.get("journal") for r in records)),
    "mlpTopicTotal": len(mlp),
    "avgMesh": round(sum(len(r.get("mesh") or []) for r in records) / len(records), 1),
    "diseaseCount": dict(disease_count),
    "yearCount": {k: v for k, v in sorted(year_count.items())},
    "kgEntityTotal": len(entities),
    "kgRelationTotal": len(relations),
    "kgApproved": sum(1 for r in relations if r["status"] == "已审核"),
    "kgPending": sum(1 for r in relations if r["status"] == "待审核"),
    "kgCandidate": sum(1 for r in relations if r["status"] == "候选"),
    "kgRejected": sum(1 for r in relations if r["status"] == "已驳回"),
    "typeCount": dict(type_count),
    "relTypeCount": dict(rel_type_count),
    "entityStatus": dict(status_count),
    "relationStatus": dict(rel_status_count),
    "baseline": {"entity": 3931, "triple": 24731, "chunk": 21002, "char": 5019000},
}

# ---------------------------------------------------------------- 用户
SURNAME = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
GIVEN = ["子涵", "雨欣", "思远", "嘉宁", "若彤", "文博", "一鸣", "晓彤", "沐阳", "婉清", "梓涵", "宇轩", "静怡", "博文", "雅琪", "浩然"]
users = []
for i in range(42):
    name = SURNAME[i % len(SURNAME)] + GIVEN[i % len(GIVEN)]
    role = "管理员" if i < 5 else "普通用户"
    st = "启用" if i % 9 else "禁用"
    users.append({
        "id": "U%04d" % (i + 1),
        "avatar": name[0],
        "name": name,
        "account": ("admin" if i == 0 else "user%03d" % (i + 1)),
        "role": role,
        "phone": "1%d****%04d" % (3 + i % 6, 1000 + i * 37 % 9000),
        "email": ("admin" if i == 0 else "user%03d" % (i + 1)) + "@manzhi.edu.cn",
        "createdAt": "2026-%02d-%02d %02d:%02d" % (1 + i % 10, 1 + i % 27, 8 + i % 10, i * 7 % 60),
        "lastLogin": "2026-11-0%d %02d:%02d" % (1 + i % 4, 7 + i % 12, i * 11 % 60),
        "status": st,
        "dept": ["知识工程组", "数据治理组", "平台运维组", "医学审核组"][i % 4],
    })

# ---------------------------------------------------------------- 采集任务
SRC = ["PubMed", "OpenCMKG", "DiaKG", "本地指南文件", "MedlinePlus"]
TASK_ST = ["已完成", "已完成", "已完成", "运行中", "失败", "已暂停"]
tasks = []
for i in range(22):
    src = SRC[i % len(SRC)]
    dis = DISEASE_ORDER[i % 3]
    stt = TASK_ST[i % len(TASK_ST)]
    cnt = 0 if stt in ("运行中", "失败") else 200 + (h(str(i)) % 900)
    tasks.append({
        "id": "T2026%03d" % (i + 1),
        "name": "%s · %s 文献采集" % (dis, src),
        "source": src,
        "collectType": "API 接口采集" if src in ("PubMed", "MedlinePlus") else ("知识图谱导入" if src in ("OpenCMKG", "DiaKG") else "本地文件解析"),
        "disease": dis,
        "startAt": "2026-10-%02d %02d:%02d" % (1 + i % 28, 8 + i % 12, i * 13 % 60),
        "endAt": "" if stt == "运行中" else "2026-10-%02d %02d:%02d" % (1 + i % 28, 9 + i % 12, (i * 17 + 20) % 60),
        "count": cnt,
        "status": stt,
        "progress": 100 if stt == "已完成" else (62 if stt == "运行中" else (0 if stt == "失败" else 40)),
        "keyword": ["type 2 diabetes AND risk factor", "hypertension AND guideline", "dyslipidemia AND LDL-C", "diabetic nephropathy", "atherosclerosis AND statin"][i % 5],
        "operator": users[i % len(users)]["name"],
    })

# ---------------------------------------------------------------- 日志
MODULES = ["用户管理", "文献管理", "实体管理", "关系审核", "智能问答", "数据采集", "系统设置"]
ACTIONS = ["登录系统", "新增实体", "编辑文献元数据", "审核通过关系", "驳回关系", "发起采集任务", "导出统计数据", "修改检索参数", "删除用户", "重新处理文献"]
logs = []
for i in range(90):
    ok = i % 13 != 0
    logs.append({
        "id": "L%05d" % (i + 1),
        "user": users[i % len(users)]["name"],
        "module": MODULES[i % len(MODULES)],
        "action": ACTIONS[i % len(ACTIONS)],
        "ip": "10.%d.%d.%d" % (i % 12, i % 200, i % 254),
        "time": "2026-11-%02d %02d:%02d:%02d" % (1 + i % 4, 8 + i % 12, i * 7 % 60, i * 13 % 60),
        "result": "成功" if ok else "失败",
        "detail": "操作对象：%s；耗时 %dms" % (["DOC-P0001", "E0003", "R0012", "U0002", "T2026004"][i % 5], 30 + i * 7 % 400),
    })
logs.sort(key=lambda x: x["time"], reverse=True)

# ---------------------------------------------------------------- 问答
qa_sessions = []
QA_TITLES = [
    ("2型糖尿病与高血压有哪些关联？", "2型糖尿病", 6),
    ("高血压的主要危险因素有哪些？", "高血压", 5),
    ("血脂异常与冠心病之间有什么联系？", "血脂异常", 4),
    ("糖尿病常见并发症有哪些？", "2型糖尿病", 8),
    ("LDL-C 控制目标是多少？", "血脂异常", 3),
    ("高血压患者需要监测哪些指标？", "高血压", 4),
    ("肥胖会增加哪些慢性病风险？", "肥胖", 3),
    ("糖尿病肾病的早期筛查指标", "慢性肾脏病", 5),
    ("他汀类药物属于哪一类治疗？", "血脂异常", 2),
    ("脑卒中的可控危险因素", "脑卒中", 4),
    ("家庭自测血压的正确做法", "高血压", 3),
    ("甘油三酯升高如何干预？", "血脂异常", 5),
]
for i, (t, d, n) in enumerate(QA_TITLES):
    qa_sessions.append({
        "id": "Q%04d" % (i + 1),
        "title": t,
        "disease": d,
        "rounds": n,
        "createdAt": "2026-11-%02d %02d:%02d" % (1 + i % 4, 9 + i % 10, i * 9 % 60),
        "user": users[i % len(users)]["name"],
    })

dump("overview.json", overview)
dump("entities.json", entities)
dump("relations.json", relations)
dump("documents.json", documents)
dump("chunks.json", chunks)
dump("pagerank.json", rank_rows)
dump("users.json", users)
dump("tasks.json", tasks)
dump("logs.json", logs)
dump("qaSessions.json", qa_sessions)
dump("yearly.json", yearly)
dump("mlpTopics.json", [{"id": m["topic_id"], "title": m["title"], "alsoCalled": m.get("also_called", []), "summary": m.get("summary", "")[:900]} for m in mlp])
dump("diseaseAgg.json", disease_agg)

print("\n实体 %d / 关系 %d / 文献 %d / 文本块 %d / 字符 %.1f 万" % (
    len(entities), len(relations), len(documents), chunk_raw["count"], total_chars / 10000))
