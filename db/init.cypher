// =============================================================================
// 慢知 · 慢性病智能知识服务平台  Neo4j 初始化脚本
// 适用：Neo4j 5.x（Community / Enterprise 均可）
// 用法：Neo4j Browser 中逐段执行，或 `cypher-shell -f init.cypher`
// 配套：seed.cypher（由 db/gen_seed.py 生成，含 264 节点 / 263 关系）
// =============================================================================

// -----------------------------------------------------------------------------
// 0. 清空（首次建库可跳过；重复导入前执行，避免残留）
// -----------------------------------------------------------------------------
// MATCH (n) DETACH DELETE n;

// -----------------------------------------------------------------------------
// 1. 唯一性约束
//    实体 ID 与名称都要求唯一：ID 用于程序引用，名称用于人工查重
// -----------------------------------------------------------------------------
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// -----------------------------------------------------------------------------
// 2. 属性索引（对应前端筛选条件）
// -----------------------------------------------------------------------------
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_status IF NOT EXISTS FOR (e:Entity) ON (e.status);
CREATE INDEX entity_disease IF NOT EXISTS FOR (e:Entity) ON (e.diseases);

CREATE INDEX rel_status IF NOT EXISTS FOR ()-[r:REL]-() ON (r.status);
CREATE INDEX rel_disease IF NOT EXISTS FOR ()-[r:REL]-() ON (r.disease);
CREATE INDEX rel_type IF NOT EXISTS FOR ()-[r:REL]-() ON (r.relation);

// -----------------------------------------------------------------------------
// 3. 全文索引（问答时的实体链接 / 关键词召回）
// -----------------------------------------------------------------------------
CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.standardName];

// -----------------------------------------------------------------------------
// 4. 数据模型说明
//    节点：(:Entity { id, name, type, standardName, aliases[], diseases[],
//                     status, confidence, source })
//    关系：()-[:REL { id, relation, disease, status, confidence, source, snippet }]-()
//
//    关系类型统一用 :REL + relation 属性，而不是 9 种独立类型：
//    - 便于统一按状态/疾病过滤，不必写 9 条 UNION；
//    - 关系类型新增时无需改 Schema。
//    如果答辩时希望图上直接显示中文类型，可用 APOC 转成具体类型（见文末附录）。
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// 5. 导入数据
//    打开 db/seed.cypher，整段粘贴执行；或命令行：
//    type seed.cypher | cypher-shell -u neo4j -p <密码>
// -----------------------------------------------------------------------------

// -----------------------------------------------------------------------------
// 6. 验证：节点与关系数量（应为 264 / 263）
// -----------------------------------------------------------------------------
MATCH (e:Entity) RETURN count(e) AS 实体数;
MATCH ()-[r:REL]->() RETURN count(r) AS 关系数;

// -----------------------------------------------------------------------------
// 7. 常用查询（前端各页面对应的 Cypher，后端可直接抄）
// -----------------------------------------------------------------------------

// 7.1 图谱可视化：以某疾病为中心取 2 跳子图（对应 /kg/graph）
// MATCH p = (c:Entity {name: '2型糖尿病'})-[:REL*1..2]-(n)
// RETURN p LIMIT 200;

// 7.2 只看已审核关系（对应图谱页「审核状态」筛选）
// MATCH p = (c:Entity {name: '2型糖尿病'})-[r:REL*1..2]-(n)
// WHERE all(x IN r WHERE x.status = '已审核')
// RETURN p LIMIT 200;

// 7.3 疾病关联网络（对应 /analysis/network，带跳数）
// MATCH p = (c:Entity {name: '2型糖尿病'})-[r:REL*1..2]-(n)
// RETURN c, r, n LIMIT 150;

// 7.4 最短关联路径（对应 /analysis/path）
// MATCH (a:Entity {name: '肥胖'}), (b:Entity {name: '脑卒中'}),
//       p = shortestPath((a)-[:REL*..5]-(b))
// RETURN p;

// 7.5 邻居统计（对应节点详情「关联实体数」）
// MATCH (e:Entity {id: 'E0001'})-[r]-()
// RETURN count(r) AS 关联数;

// 7.6 某个疾病下的关系类型分布（对应 /analysis/stats）
// MATCH (:Entity {name: '2型糖尿病'})-[r:REL]-(:Entity)
// RETURN r.relation AS 关系类型, count(*) AS 数量 ORDER BY 数量 DESC;

// 7.7 实体链接：按名称模糊召回（问答第一步）
// CALL db.index.fulltext.queryNodes('entity_fulltext', '糖尿病')
// YIELD node, score RETURN node.name, node.type, score LIMIT 5;

// 7.8 待审核关系（对应审核队列，可与 MySQL 对账）
// MATCH (h:Entity)-[r:REL {status: '待审核'}]->(t:Entity)
// RETURN h.name AS 头实体, r.relation AS 关系, t.name AS 尾实体 LIMIT 20;

// -----------------------------------------------------------------------------
// 附录：把 :REL 拆成 9 种具体关系类型（需要 APOC 插件）
// 优点：图上直接显示「危险因素」等中文类型，更符合答辩展示习惯
// 缺点：过滤时要写多条 UNION，且新增类型需改代码
// -----------------------------------------------------------------------------
// MATCH (h:Entity)-[r:REL]->(t:Entity)
// CALL apoc.merge.relationship(h, r.relation, {id: r.id}, r, t) YIELD rel
// RETURN count(rel);
// MATCH ()-[r:REL]->() DELETE r;
