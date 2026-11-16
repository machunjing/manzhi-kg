# 后端服务 · 慢知

Flask + pymysql + scikit-learn，**零新增依赖**（Python 3.8 里全都装好了）。

## 一、启动

```bash
cd backend
py -3.8-64 app.py
```

首次启动会从 MySQL 载入 34,309 条切块构建 TF-IDF 索引（约 14 秒），
之后走 `.cache/index_v2.pkl` 缓存，启动只要 0.2 秒。切块数量变化会自动重建。

监听 `http://127.0.0.1:5001`，所有接口前缀 `/api`，统一响应：

```json
{ "code": 0, "message": "ok", "data": { } }
```

`code` 取值：0 成功 / 40001 参数错误 / 40400 不存在 / 40900 状态冲突 / 50000 服务异常。

## 二、已实现的接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/system/health` | 健康检查，返回索引规模 |
| POST | `/api/qa/ask` | **智能问答**（三路检索 + RRF + 引用） |
| GET | `/api/kg/graph?entity=&depth=` | 图谱子图（力导向图数据） |
| GET | `/api/kg/entities?keyword=&type=&page=` | 实体分页检索 |
| GET | `/api/kg/types` | 实体类型分布 |
| GET | `/api/docs/search?keyword=&disease=` | 文献检索 |
| GET | `/api/docs/<id>` | 文献详情 + 切块 |
| GET | `/api/review/pending` | 待审核队列（演示库） |
| POST | `/api/review/<id>/approve\|reject\|hold` | 审核动作（触发器校验） |
| GET | `/api/review/stats` | 审核四态统计 |
| GET | `/api/stats/overview` | 数据总览 |
| GET | `/api/analysis/network?entity=&depth=` | 关联网络（带跳数分布） |
| GET | `/api/analysis/path?from=&to=&maxLen=` | 最短关联路径（BFS） |

## 三、问答是怎么算出来的

```
问题 ──► 意图识别（6 类：用药/症状/检查/并发症/饮食/概念）
     ──► 实体链接（32,091 实体 + 785 别名，长名优先）
     ──┬─► 关键词路：MySQL ngram 全文，拆词后 BOOLEAN 检索（30 条）
       ├─► 向量路：字符 2~3-gram TF-IDF 余弦（30 条）
       └─► 图谱路：实体及其邻居命中的切块（20 条）
     ──► RRF 融合  score = Σ 1/(60 + rank)
     ──► 疾病维度加权 ×1.8，意图词加权 ×(1+0.45·命中数)
     ──► 答案 = 图谱事实（结论）+ 原文切块（论据）+ 逐条引用
```

几个工程决定：

- **不用分词器**。中文用 `char_wb` 2~3-gram，英文靠 3-gram 也能召回，省掉 jieba 依赖，也不怕医学缩写。
- **关键词路必须先拆词**。整句丢进 `BOOLEAN MODE` 会被当短语，中文几乎必然 0 命中（实测 0 → 拆词后 222）。
- **图谱事实只取出边**。关系有方向，`疾病 → 并发症` 不能反过来当「疾病的并发症」。
- **实体归一靠 `entity_alias` 表**。语料里「中风」和「脑卒中」是两个词，不归一就会出现「实体明明在库里却查不到」。

## 四、实测结果

| 问题 | 意图 | 图谱结论 | 耗时 |
|---|---|---|---|
| 糖尿病有哪些常见并发症？ | 并发症 | 乳酸性酸中毒、尿毒症、糖尿病性神经病 | 75 ms |
| 高血压患者应该怎么用药？ | 治疗/用药 | 卡维地洛片、厄贝沙坦片、吲达帕胺滴丸 | 69 ms |
| 血脂异常的人饮食要注意什么？ | 饮食干预 | 干预措施 + 指南原文引用 | 60 ms |

最短路径 `肥胖 → 脂肪肝 → 高血压 → 中风`（3 跳，别名已归一）。
审核接口跑通：`approve` 后触发器自动写审计，紧接着 `reject` 被 `ERROR 1644` 挡回，接口返回 40900。

## 五、前端怎么接

前端 `src/api/index.ts` 是统一出口，把对应方法从 mock 换成 axios 即可：

```ts
// 之前：mock
export const askQuestion = (q: string) => mockQa(q)

// 之后：真实接口
export const askQuestion = (q: string) =>
  http.post('/qa/ask', { question: q }).then(r => r.data.data)
```

开发期跨域已由 `after_request` 放开（`Access-Control-Allow-Origin: *`）。
