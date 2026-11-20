# 慢知 · 慢性病智能问答系统

**把 5,063 篇文献（PubMed + 中文指南）和 28.8 万条三元组，变成可溯源、可审核的慢性病知识图谱与问答系统。**

<p>
  <img alt="Vue" src="https://img.shields.io/badge/Vue-3.5-42b883?logo=vue.js&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.6-3178c6?logo=typescript&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white">
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.0-4479a1?logo=mysql&logoColor=white">
  <img alt="Neo4j" src="https://img.shields.io/badge/Neo4j-5-008cc1?logo=neo4j&logoColor=white">
</p>

---

## 为什么做这个

慢性病患者和家属查资料，通常得到两种结果：搜索引擎给一堆互相矛盾的网页，大模型给一段没法验证的话。

这个项目想做第三件事 —— **每个结论都能指回原始文献的哪一段，每条图谱关系都要人工审核过才算数。**

## 界面

| 知识图谱 | 关系审核 |
|---|---|
| ![知识图谱](docs/screenshots/02-knowledge-graph.png) | ![关系审核](docs/screenshots/03-relation-review.png) |

| 智能问答 | 检索过程 |
|---|---|
| ![问答](docs/screenshots/04-qa-answer.png) | ![检索步骤](docs/screenshots/05-retrieval-steps.png) |

## 系统能力

| 模块 | 能力 | 实现要点 |
|---|---|---|
| 数据采集 | PubMed / MedlinePlus / 中文指南 PDF | E-utilities 增量拉取，PMID 去重 |
| 知识抽取 | 文献 → 实体 → 三元组 | 规则抽取 + MeSH 词表对齐 |
| 图谱存储 | 32,091 实体 / 288,064 关系 | MySQL 8 存业务，Neo4j 5 已导入 |
| 关系审核 | 四态状态机 + 审计留痕 | 数据库触发器强制约束 |
| 智能问答 | 四路召回 + RRF + GLM-4 生成 + 引用标注 | 全文索引 / TF-IDF / 图谱邻居 / 跨语言 |
| 关联分析 | 子图 / 最短路径 / 中心度 | 逐层 BFS，每层一条 SQL |
| 可视化 | 20 个页面 | Vue 3 + ECharts |

## 架构

```mermaid
flowchart LR
    A[PubMed E-utilities] --> B[采集与清洗]
    C[中文指南 PDF] --> B
    D[OpenCMKG 三元组] --> E[实体对齐]
    B --> E
    E --> F[(MySQL 8<br/>文献 / 切块 / 实体 / 关系)]
    F --> G[图谱构建]
    G --> H[(Neo4j 5<br/>32k 节点 / 288k 关系)]

    Q[用户提问] --> R[意图识别<br/>实体链接]
    R --> S0[跨语言改写<br/>中文问题 → 英文检索式]
    R --> S1[关键词路<br/>ngram 全文]
    R --> S2[向量路<br/>TF-IDF 余弦]
    R --> S3[图谱路<br/>实体邻居]
    F --> S1
    F --> S2
    F --> S3
    S0 --> S4[跨语言路<br/>英文摘要]
    F --> S4
    S1 --> T[RRF 融合<br/>+ 双语均衡取证]
    S2 --> T
    S3 --> T
    S4 --> T
    T --> U[GLM-4 生成<br/>逐条标注引用]
    U --> V[Vue 前端 · 20 页]
```

## 四个值得讲的设计

### 1. 审核状态机放在数据库里，不放在代码里

关系有四种状态：`候选 → 待审核 → 已审核 / 已驳回`。这条规则如果只写在服务层，任何一条 SQL 都能绕过去。

所以它被写成 `BEFORE UPDATE` 触发器：

```sql
IF NOT ((OLD.`status`='候选'   AND NEW.`status`='待审核')
     OR (OLD.`status`='待审核' AND NEW.`status` IN ('已审核','已驳回'))
     OR (OLD.`status`='已驳回' AND NEW.`status`='待审核')) THEN
  SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT='非法审核状态流转：只允许 候选→待审核→已审核/已驳回';
END IF;
```

任何路径想跳步，拿到的都是 `ERROR 1644`。合法流转则由 `AFTER UPDATE` 触发器自动往审计表写一行「谁、什么时候、从什么状态改到什么状态」。

实测效果：

```
候选 → 已审核（跳步）  ERROR 1644: 非法审核状态流转
候选 → 待审核          ✅ 成功，审计表自动 +1 行
删除被引用的实体        ERROR 1451: fk_relations_head ... ON DELETE RESTRICT
插入重复三元组          ERROR 1062: Duplicate entry for key 'uk_relations_triple'
```

### 2. 四路召回，用 RRF 而不是加权平均

关键词路（MySQL ngram 全文）、向量路（TF-IDF 余弦）、图谱路（实体一跳邻居）、跨语言路（英文摘要）四路的分数不在同一个量纲上 —— 全文相关度是浮点分数，余弦相似度是 0~1，图谱邻居根本没有分数。直接加权要不停调参，而且换一批数据就失效。

改用 Reciprocal Rank Fusion：

```
score(d) = Σ_routes  1 / (60 + rank(d))
```

只用排名，不用分数，四路天然可比。实测各路确实互补：

| 路线 | 擅长 | 例子 |
|---|---|---|
| 关键词 | 术语精确匹配 | 问「他汀」命中指南原文第 92 块 |
| 向量 | 同义改写 | 问「血脂高怎么办」也能召回「血脂异常管理」 |
| 图谱 | 问题里没写但图上连着 | 问「糖尿病并发症」直接给出尿毒症、酮症酸中毒 |
| 跨语言 | 中文问题命中英文文献 | 问「肥胖增加哪些风险」召回 obesity 相关 PubMed 摘要 |

### 3. 跨源实体对齐

PubMed 走 MeSH 英文词表（`Diabetes Mellitus, Type 2`），中文图谱用中文名（`糖尿病`、`中风`）。两套词汇各说各话 —— 用户问「脑卒中」，在图谱里查不到，因为 OpenCMKG 管它叫「中风」。

解法是建一张 785 条的别名表，把 MeSH 词、中文别名、OpenCMKG 实体名映射到同一个标准实体。这是多源知识融合绕不开的一步，也是这个项目里最容易被低估的工作量。

### 4. 中英语料不对等，就分开取证

语料里中文只有 6 份指南，英文摘要 4,000+ 篇。中文提问如果只走中文检索，只能命中指南；如果只用 RRF 融合，中文切块能同时命中关键词/向量/图谱三路，票数天然比只命中一路的英文切块高，**英文证据永远进不了前 8**。

所以做两件事：

1. **查询改写**：用 GLM-4 把中文问题翻译成 3~6 个英文医学术语（`糖尿病有哪些并发症` → `diabetes`、`complications`），再去查英文摘要；
2. **双语均衡取证**：中英两个候选池分别重排，然后各取一半 —— 中文指南给「规范说法」，英文文献给「研究证据」。

效果是答案里既有「糖尿病合并高血压应控制在 130/80 mmHg 以下」（中文指南），也有「Diabetic cerebral microvascular disorder…」（PubMed 摘要），中英各自不可替代。

同时加了两条防噪规则：**同疾病维度加权、跨疾病降权**（问糖尿病不引一堆高血压指南），以及**泛概念实体不进实体链接**（「慢性病」这种词链接上了，图谱事实就会变成「胃炎/骨质疏松」这类噪声）。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3.5 · Vite 6 · TypeScript · Element Plus · ECharts 5 · Pinia |
| 后端 | Flask 3 · PyMySQL · scikit-learn（TF-IDF） |
| 模型 | 智谱 GLM-4-Flash（OpenAI 兼容接口，仅用标准库 `urllib` 调用） |
| 存储 | MySQL 8.0（业务表 + ngram 全文索引）· Neo4j 5（图查询） |
| 数据处理 | PubMed E-utilities · PyMuPDF · pandas |

## 快速开始

前置：MySQL 8.0+、Python 3.8+。Neo4j 可选，没有也能跑（图谱查询有 MySQL 递归 CTE 兜底）。

```bash
# 1. 建库：13 张表 / 2 个视图 / 2 个触发器
mysql -uroot -p < db/schema.sql

# 2. 后端
cd backend
cp ../.env.example .env          # 填 MySQL 口令；想用大模型再填 LLM_API_KEY
pip install flask pymysql scikit-learn numpy
python app.py                    # http://127.0.0.1:5001

# 3. 前端（另开一个终端）
cd frontend
npm install
npm run dev                      # http://127.0.0.1:5178
```

前端开发服务器会把 `/api` 代理到 `127.0.0.1:5001`（见 `vite.config.ts`），不用额外配跨域。

后端首次启动会构建 TF-IDF 索引（约 14 秒，3.4 万条切块），之后走本地缓存。

**大模型是可选的**：`backend/.env` 里填了 `LLM_API_KEY` 就走 GLM-4 生成答案，没填或调用失败就自动回退成「图谱事实 + 原文证据」的模板答案，功能不中断。Key 只存在本地 `.env`，已被 `.gitignore` 排除。

自检命令：

```bash
python backend/llm.py                              # 测模型连通性
curl http://127.0.0.1:5001/api/system/health       # 看索引与模型状态
curl -X POST http://127.0.0.1:5001/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"糖尿病有哪些并发症？"}'          # 加 ?no_llm=1 可对比模板答案
```

**仓库不含原始语料**（版权与体积原因）。`db/samples/` 只放了 30 行格式样例，数据获取与导入方式见 [`db/README.md`](db/README.md)。

## 目录结构

```
.
├── frontend/                 Vue 3 前端 · 20 个页面
│   ├── src/views/            首页 / 数据资源 / 知识图谱 / 关系审核 / 智能问答 / 关联分析 / 系统管理
│   ├── src/api/              接口出口 —— mock 与真接口在这里切换
│   └── src/mock/             原型阶段的假数据
├── backend/                  Flask 后端 · 20 个业务接口
│   ├── app.py                路由层
│   ├── retrieval.py          四路召回 + RRF + 双语取证
│   ├── nlp.py                意图识别 / 实体链接 / TF-IDF 索引
│   ├── llm.py                GLM-4 调用、查询改写、引用清洗
│   └── answer.py             答案组装与引用标注
├── db/                       数据层
│   ├── schema.sql            建库脚本（约束 / 索引 / 触发器 / 视图）
│   ├── queries.sql           验收查询集，含 6 条「故意报错」的约束演示
│   ├── init.cypher           Neo4j 约束、索引、全文索引
│   └── import_*.py           导入管线
└── docs/
    ├── openapi.yaml          58 个接口的 OpenAPI 3.0 契约
    ├── 接口清单.md
    └── screenshots/
```

## 数据规模

| 项 | 数量 | 来源 |
|---|---:|---|
| 文献 | 5,063 | PubMed 5,026 + MedlinePlus 31 + 中文指南 6 |
| 实体别名 | 785 | OpenCMKG `SameAs` 对 + 人工补充 |
| 文本切块 | 34,309 | 300 字 / 50 重叠 + 指南按章节切分 |
| 实体 | 32,091 | OpenCMKG + MeSH 对齐 |
| 关系 | 288,064 | OpenCMKG 13 类映射为 9 类 |

## 当前进度

| 部分 | 状态 |
|---|---|
| 前端 20 个页面 | ✅ 完成 |
| 后端 28 个业务接口 | ✅ 可运行（问答/图谱/文献/审核/统计/关联分析/平台运维） |
| 问答页 | ✅ 四路召回 + RRF + GLM-4 生成 + 引用标注，实测 6 篇引用 / 4 条图谱路径 / 8.5~14 秒 |
| 图谱页 | ✅ 演示库子图，按关系类型着色，实测 28 节点 / 43 关系 |
| 关联路径 / 网络 | ✅ 最短路径逐层 BFS；每跳回文献库找「同时提到两端实体」的原文，找不到就标「无文献支撑」，可一键避开该中转节点重查 |
| 实体 / 关系 / 审核 | ✅ 审核操作真实写库，四态状态机生效 |
| 文献管理 | ✅ 5,063 篇真实文献，按疾病/来源/年份筛选，文本块异步加载 |
| 首页 / 统计 | ✅ 卡片、来源分布、年度趋势全部取真实统计 |
| 图查询走 Neo4j | ⬜ Neo4j 已导入 32,091 节点 / 288,064 关系，接口当前仍走 MySQL（结果一致，未切换） |
| 用户 / 日志 / 采集任务 | ✅ 42 用户 / 22 任务 / 90 条审计日志，全部走真实分页查询 |

## 两套库，各管一段

| 库 | 内容 | 用在哪 |
|---|---|---|
| `manzhi_real` | 5,063 篇文献 / 34,309 切块 / 32,091 实体 / 288,064 关系 | 问答检索、文献管理、统计 |
| `manzhi` | 408 篇样本 / 264 实体 / 263 关系，带四态审核流转 | 图谱可视化、关联分析、关系审核 |

真实库的 OpenCMKG 是通用医学图谱，3 万实体里混着「老年肺炎」「肠道菌群失调症」这类边缘词，画成图看不清；
演示库是人工整理过的疾病子图（糖尿病 → 并发症/临床表现/危险因素/药物），适合讲清楚「图谱长什么样」。
所以**可视化走演示库，检索走真实库**，两个页面左上角都标了数据来源。

## 已知限制

写清楚，避免误导：

- **向量检索用 TF-IDF，不是 BGE-M3**。本机没有 GPU，跑不动 7B 级嵌入模型。TF-IDF 足以验证「四路召回 + RRF」这条流程；生产环境应换成 BGE-M3 + Milvus，替换点集中在 `nlp.py` 的 `build()`。
- **大模型是「可选增强」，不是唯一路径**。有 Key 走 GLM-4-Flash，没有就回退模板答案；模板答案的结论全部来自图谱三元组，不会编造。模型生成的内容仍可能不准确，所以每条都带证据编号，点开可查原文。
- **OpenCMKG 原始数据带噪声**。1,292 个实体名长度 ≤2（如「1」「21」「8-11」），4,829 个纯 ASCII 名；关系里有自环和「肥胖→胃炎」这类可疑关联。已用三道闸过滤：泛概念实体不参与链接、自环丢弃、模型按医学常识忽略明显错误条目。彻底解决要靠人工审核队列。
- **PubMed 文献是英文，中文语料只有 6 份指南**。中文提问能同时命中中文指南与英文摘要（跨语言路），但英文证据是英文原文，答案由模型译成中文。
- **6 份中文指南全是血脂与高血压，没有糖尿病指南**。问糖尿病时中文证据只能来自这两类指南里提到糖尿病的段落，答案不错但偏向合并症管理。补一部糖尿病指南 PDF 重跑导入脚本即可改善。
- **答案耗时 8.5~14 秒**。其中查询改写约 1 秒、GLM-4 生成 8~10 秒。同一问题 30 分钟内命中缓存，演示时重复提问会瞬间返回。

## 关于

个人项目，持续迭代中。想解决的是「慢病资料查得到、却不知道信不信得过」这件事。

数据来源：[PubMed](https://pubmed.ncbi.nlm.nih.gov/) · [OpenCMKG](https://github.com/OpenKG-ORG/OpenCMKG) · 公开诊疗指南

## License

[MIT](LICENSE) —— 代码可自由使用。文献与指南原文版权归原作者所有，本仓库不包含原始语料。
