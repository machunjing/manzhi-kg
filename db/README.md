# 数据库层说明 · 慢知

> 本目录是「慢知 · 慢性病智能问答系统」的数据层，与 `慢知前端原型/docs/openapi.yaml`
> 里的 58 个接口一一对应。字段名直接取自前端 mock 层，后端换真接口时页面不用改。

---

## 一、现在是什么状态

**两个库，分工明确：**

| 库名 | 用途 | 规模 | 状态 |
|---|---|---|---|
| `manzhi` | **演示库**。数字与前端 20 个页面完全对齐，答辩截图用这个 | 12 表 / 408 文献 / 264 实体 / 263 关系 | ✅ 已建好 |
| `manzhi_real` | **真实库**。数据包里的真实语料，检索与问答用这个 | 5,063 文献 / 34,309 切块 / 32,091 实体 / 288,064 关系 | ✅ 已建好 |
| Neo4j `manzhi-neo4j` | 图数据库，装的是 `manzhi_real` 的真实图谱 | 32,091 节点 / 288,064 关系 | ✅ 容器运行中（7474 / 7687） |

为什么分两个库：演示库的 175/41/26/21 审核四态是前端页面上写死的数字，改了就对不上；
真实库有 28 万条关系，是问答检索的底座。两个库同 schema，`schema.sql` 一次建两个。

MySQL 侧的四条硬约束都做过现场验证（非法状态流转被拦、合法流转自动留审计、
删被引用实体被外键拒绝、重复三元组被唯一键拒绝），结果见 `queries.sql` 第 13 节。

### 1.1 `manzhi_real` 里装了什么

| 来源 | 内容 | 数量 |
|---|---|---:|
| `pubmed_records.json` | PubMed 文献（英文题录 + 摘要 + MeSH） | 5,026 |
| `mlp_topics.json` | MedlinePlus 主题 | 31 |
| `向量切块清单_300重叠50.json` | 文献切块（300 字 / 50 重叠） | 32,078 |
| 6 份中文指南 PDF | 指南正文切块（PyMuPDF 解析后同样规则切块） | 2,231 |
| `OpenCMKG/triples.txt` | 中文医学三元组（13 类关系 → 映射为 9 类） | 288,064 |
| `实体候选列表_有效MeSH.json` | 有效 MeSH 实体 | 4,793 |

实测能跑通的链路：

```
中文提问「他汀类药物安全性」
  → 切块召回：DG001 中国血脂管理指南2023年 第 92/107 块（真实原文）
  → 图谱事实：糖尿病 → 常用药物 → 伏格列波糖片 / 天麦消渴片
  → 图谱事实：糖尿病 → 并发症 → 尿毒症 / 糖尿病酮症酸中毒
```

**注意一个真实数据的坑**：PubMed 的 5,026 篇文献**全是英文**，中文语料只来自指南 PDF 和
OpenCMKG。所以中文问答的中文证据靠指南，英文证据靠文献，两条路都要接——这正好是开题报告里
「多源检索」要解决的问题。

### 1.2 OpenCMKG 的 13 类关系怎么落到 9 类枚举

| OpenCMKG | 本系统 | 条数 |
|---|---|---:|
| disease_recommand_food / eat_food / noteat_food / need_treatment | 干预措施 | 104,338 |
| disease_recommand_drug / common_drug | 常用药物 | 60,671 |
| disease_has_symptom | 临床表现 | 59,195 |
| disease_need_check | 监测指标 | 38,900 |
| disease_acompany_disease | 并发症 | 24,960 |
| ~~disease_belong_department~~ | 科室不在 9 类枚举内，暂不入库 | 8,790 |
| ~~drug_relate_producer~~ | 药品-企业，与疾病知识无关 | 17,278 |
| ~~department_belong_department~~ | 科室层级 | 37 |
| ~~SameAs~~ | 实体同义，留给「实体合并」功能用 | 17,947 |


---

## 二、MySQL：DataGrip 连上就能看

### 2.1 连接参数

| 项 | 值 |
|---|---|
| Host | `localhost` |
| Port | `3306` |
| User | `root` |
| Password | `<你的口令>` |
| Database | `manzhi` |
| URL 建议 | `jdbc:mysql://localhost:3306/manzhi?characterEncoding=utf8mb4&serverTimezone=Asia/Shanghai` |

> 一定要带 `characterEncoding=utf8mb4`，否则 DataGrip 里中文注释和中文枚举值可能显示成问号。

### 2.2 库里有什么

| 表 | 作用 | 行数 | 对应前端页面 |
|---|---|---:|---|
| `users` | 账号、角色、状态 | 42 | 用户管理 / 登录 |
| `documents` | 文献与指南元数据 + 摘要全文 | 408 | 文献管理 |
| `chunks` | 文本切块（供向量化） | 5 | 数据处理 |
| `entities` | 图谱实体（8 类） | 264 | 知识图谱 |
| `relations` | 三元组 + 置信度 + 证据片段 | 263 | 知识图谱 / 关系审核 |
| `relation_review` | 审核流水（谁、何时、从什么状态到什么状态） | 196 | 关系审核 |
| `collect_tasks` | 采集任务与进度 | 22 | 采集任务管理 |
| `collect_task_logs` | 采集任务日志 | 0 | 采集任务详情 |
| `operation_logs` | 系统操作审计 | 90 | 日志审计 |
| `qa_sessions` / `qa_messages` | 问答会话与消息（结果存 JSON） | 12 / 0 | 智能问答 |
| `system_config` | 分组配置（JSON） | 5 | 系统设置 |

两个视图：`v_review_stats`（审核四态占比）、`v_pending_review`（待审核队列，已 join 出实体名）。

两个触发器：`trg_relations_status_guard`（拦截非法状态流转）、`trg_relations_status_audit`（流转成功自动写审计）。

### 2.3 打开就能跑

`queries.sql` 是给 DataGrip 用的验收脚本，12 组查询 + 6 条「故意报错」的约束演示：

1. 表 / 视图 / 触发器清单
2. 每张表行数
3. 审核四态分布 → 预期 `已审核 175 / 待审核 41 / 候选 26 / 已驳回 21`
4. 待审核队列（带实体名）
5. 实体类型分布 → 8 类，`其他 130` 最多
6. 关系类型分布 + 平均置信度 → 9 类，`危险因素 55` 最多
7. 证据链：一条关系追到文献与原文片段
8. **递归 CTE 取 2 跳子图**（就是 Neo4j `MATCH (c)-[:REL*1..2]-(n)` 的 SQL 等价写法）
9. 全文检索（ngram 索引）
10. 问答会话结构（JSON 列）
11. 采集任务进度
12. 系统配置
13. 约束演示：非法流转 / 合法流转 / 外键 / 唯一键 / 自环 / 枚举

### 2.4 推倒重建

```bash
cd db
# 演示库
mysql -uroot -p < schema.sql        # 建库建表建视图建触发器
mysql -uroot -p manzhi < seed.sql   # 灌演示数据

# 真实库（会重建 manzhi_real，35 秒）
py -3.8-64 import_real.py
py -3.8-64 import_guides.py         # 再补 6 份中文指南（2.6 秒）
```

`seed.sql` 由 `gen_seed.py` 从 `慢知前端原型/src/mock/data/*.json` 生成，
所以**演示库的数字和前端页面上的数字是同一套**，不会出现「页面上 175 条、库里 20 条」这种对不上的情况。

---

## 三、Neo4j：已跑起来，装的是真实图谱

容器 `manzhi-neo4j` 在跑，**32,091 节点 / 288,064 关系**，和 MySQL `manzhi_real` 完全一致。

| 项 | 值 |
|---|---|
| Browser | <http://localhost:7474> |
| 账号 / 密码 | `neo4j` / `<你的图库口令>` |
| Bolt | `bolt://localhost:7687` |
| 内存 | 堆 2G / pagecache 512M |

### 3.1 为什么不用 Cypher 语句灌数据

一开始我把 28.8 万条关系写成 `UNWIND [{id:"R1",...}, ...] AS row` 的语句，
单条语句里就有上千个 map 字面量，Neo4j 解析阶段直接 **Java heap space**。
改成官方推荐的 `LOAD CSV` 后，流式读取、每 1000 行提交一次，19 秒导完，内存恒定。

所以 `seed_real.cypher`（40.5 MB，历史产物）已废弃，实际走的是：

```
db/export_graph.py  ->  nodes.csv (1.8 MB) + rels.csv (16.1 MB)
db/load_neo4j.cypher ->  LOAD CSV 导入
```

### 3.2 重新导入

```bash
py -3.8-64 db/export_graph.py          # 从 MySQL 导出 CSV
cd db
MSYS_NO_PATHCONV=1 docker cp nodes.csv manzhi-neo4j:/var/lib/neo4j/import/
MSYS_NO_PATHCONV=1 docker cp rels.csv  manzhi-neo4j:/var/lib/neo4j/import/
MSYS_NO_PATHCONV=1 docker cp load_neo4j.cypher manzhi-neo4j:/var/lib/neo4j/import/
MSYS_NO_PATHCONV=1 docker exec manzhi-neo4j cypher-shell -u neo4j -p <你的图库口令> \
  -f /var/lib/neo4j/import/load_neo4j.cypher
```

> `MSYS_NO_PATHCONV=1` 必须加，否则 Git Bash 会把容器里的 `/var/lib/...`
> 改写成 Windows 路径，报 `No such file or directory`。

### 3.3 起容器

```bash
docker run -d --name manzhi-neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/<你的图库口令> \
  -e NEO4J_server_memory_heap_max__size=2G \
  -e NEO4J_server_memory_pagecache_size=512M \
  neo4j:5
```

### 3.4 校验

```cypher
MATCH (e:Entity) RETURN count(e);        // 32091
MATCH ()-[r:REL]->() RETURN count(r);    // 288064
MATCH (e:Entity {name:'糖尿病'})-[r:REL]->(t) RETURN t.name, r.relation LIMIT 10;
MATCH p=(e:Entity {name:'糖尿病'})-[:REL*1..2]-(n) RETURN count(p);   // 20804
```

> ⚠️ **DataGrip 连不了 Neo4j**。DataGrip 只支持关系型数据库，图库要在 Neo4j Browser
> 里看。答辩演示时建议并排放两个窗口：DataGrip 看 MySQL，Browser 看图。

### 3.5 演示库的图（264 节点）

`seed.cypher` 还在，是给演示库准备的（数字与前端页面一致）。要装它：

```bash
docker exec manzhi-neo4j cypher-shell -u neo4j -p <你的图库口令> "MATCH (n) DETACH DELETE n;"
docker cp init.cypher  manzhi-neo4j:/var/lib/neo4j/import/init.cypher
docker cp seed.cypher  manzhi-neo4j:/var/lib/neo4j/import/seed.cypher
docker exec manzhi-neo4j cypher-shell -u neo4j -p <你的图库口令> -f /var/lib/neo4j/import/init.cypher
docker exec manzhi-neo4j cypher-shell -u neo4j -p <你的图库口令> -f /var/lib/neo4j/import/seed.cypher
```

### 3.6 如果哪天要重装

- Neo4j 官方下载走 CloudFront，`dist.neo4j.org` 对国内返回 403，装不了；
- 国内镜像站都没有 Neo4j 发行包；
- **只能走 Docker**（`docker pull neo4j:5` 实测可用），或者 Neo4j Aura 免费云实例。

---

## 四、文件清单

| 文件 | 说明 |
|---|---|
| `schema.sql` | MySQL 建库脚本：12 表 + 2 视图 + 2 触发器 + 索引 + 约束 |
| `seed.sql` | 演示库数据（1.1 MB，由 `gen_seed.py` 生成，**不要手改**） |
| `gen_seed.py` | 从 `慢知前端原型/src/mock/data/*.json` 生成 `seed.sql` 与 `seed.cypher` |
| `import_real.py` | **真实库**：把数据包的文献/切块/OpenCMKG 三元组/MeSH 灌进 `manzhi_real`（35 秒） |
| `import_guides.py` | **中文语料**：6 份指南 PDF → 文本 → 300/50 切块 → 入库（2.6 秒） |
| `seed_alias.py` | **实体归一**：OpenCMKG SameAs + 人工同义词 → `entity_alias` 表（785 条） |
| `export_graph.py` | 把 `manzhi_real` 导出成 Neo4j 可执行的 `seed_real.cypher`（40.5 MB） |
| `audit_data.py` | **数据质量审计**：重复率、缺失率、中文占比、跨源一致性 |
| `init.cypher` | Neo4j 初始化：约束、索引、全文索引、模型说明、8 条生产查询、APOC 附录 |
| `seed.cypher` | 演示图数据（264 节点 / 263 关系，8 个 UNWIND 批次） |
| `seed_real.cypher` | 真实图数据（32,091 节点 / 288,064 关系，由 `export_graph.py` 生成） |
| `verify_seed.py` | **离线**校验 `seed.cypher`：唯一性 / 端点完整性 / 状态取值 / 三元组唯一 |
| `queries.sql` | DataGrip 验收与演示查询集 |
| `neo4j_up.bat` | Windows 一键起 Neo4j 容器并导入 |

`verify_seed.py` 的运行结果（当前）：

```
节点 (:Entity)  : 264
关系 (:REL)     : 263
关系状态分布    : {'候选': 26, '已审核': 175, '待审核': 41, '已驳回': 21}
[PASS] 唯一性 / 端点完整性 / 状态取值 / 三元组唯一性 全部通过
```

---

## 五、几个设计决定（答辩可以讲）

**1. 审核状态用 ENUM + 触发器，而不是只靠后端代码。**
状态机是 `候选 → 待审核 → 已审核/已驳回`，`已驳回`/`已审核` 可回到 `待审核`。
如果只在 Java/Python 里判断，任何脚本、任何 DBA 直连都能绕过；放进
`BEFORE UPDATE` 触发器后，非法流转在数据库层直接 `SIGNAL SQLSTATE '45000'` 拒绝，
业务报错信息还是中文可读的。配合 `AFTER UPDATE` 触发器，每次流转自动落一条审计，
不用信任「后端一定会记得写日志」。

**2. 关系三元组加唯一键 `(head_id, relation, tail_id)`。**
同一对实体之间允许「危险因素」和「并发症」两条关系（语义不同），
但不允许同一条关系重复入库——这是图谱去重最省事的一道闸。

**3. 外键用 `ON DELETE RESTRICT`，不用级联删。**
删一个实体时，如果还有关系指向它，数据库直接报 `ERROR 1451`，
逼着先处理关系。图谱数据最怕「删了节点留下断头关系」。
（注意：MySQL 不允许被 `ON UPDATE CASCADE` 引用的列再出现在 `CHECK` 里，
所以 `head_id/tail_id` 上没加 `ON UPDATE CASCADE`。）

**4. 全文索引用 `WITH PARSER ngram`。**
中文没有空格，默认分词器会把整句当一个词。ngram 按 2 字切分，`血脂`、`糖尿病`
这类词能命中。但 ngram 有 50% 阈值规则（命中行数超过全表一半的词返回空），
所以生产上它是 BM25 那一路召回，和 Milvus 向量召回并列，靠 RRF 融合，不单独兜底。

**5. Neo4j 里关系统一用 `:REL` + `relation` 属性，不拆成 9 种类型。**
好处：按状态/疾病过滤只写一个 `WHERE`，不用 9 条 `UNION`；新增关系类型不改 Schema。
代价：图上连线不直接显示中文类型。若答辩要「连线带中文标签」，用 `init.cypher`
文末的 APOC 附录一行转成具体类型。

---

## 六、下一步

数据层齐了，接下来按企业流程走**垂直切片**：挑一个页面（建议「关系审核」，
因为它同时用到表、视图、触发器、外键），把前端从 mock 切到真接口：

1. 后端起 FastAPI/Spring Boot，用 `openapi.yaml` 生成骨架（`openapi-generator`）
2. 只实现 3 个接口：`GET /review/pending`、`POST /review/{id}/approve`、`POST /review/{id}/reject`
3. 前端把 `src/api/index.ts` 里这 3 个方法的 mock 实现换成 axios 调用
4. 跑通后，同样的套路复制到其余模块
