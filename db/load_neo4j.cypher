// =============================================================================
// 把真实图谱从 CSV 批量导入 Neo4j
// 前置：db/export_graph.py 生成 nodes.csv / rels.csv，并 docker cp 到 import 目录
// 用法：cypher-shell -f /var/lib/neo4j/import/load_neo4j.cypher
//
// 为什么用 LOAD CSV 而不是 UNWIND [...] 语句：
//   28.8 万条关系写成一条 Cypher 语句，解析阶段就会 Java heap space。
//   LOAD CSV 是流式读取，每 1000 行提交一次，内存占用恒定。
// =============================================================================

// 0. 清空（重复导入前执行）
MATCH (n) DETACH DELETE n;

// 1. 约束与索引（重复执行安全）
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_status IF NOT EXISTS FOR (e:Entity) ON (e.status);
CREATE INDEX rel_status IF NOT EXISTS FOR ()-[r:REL]-() ON (r.status);
CREATE INDEX rel_type IF NOT EXISTS FOR ()-[r:REL]-() ON (r.relation);
CREATE INDEX rel_disease IF NOT EXISTS FOR ()-[r:REL]-() ON (r.disease);

// 2. 节点
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (e:Entity {id: row.id})
SET e.name       = row.name,
    e.type       = row.type,
    e.status     = row.status,
    e.confidence = toFloat(row.confidence),
    e.source     = row.source;

// 3. 关系
LOAD CSV WITH HEADERS FROM 'file:///rels.csv' AS row
MATCH (h:Entity {id: row.head})
MATCH (t:Entity {id: row.tail})
MERGE (h)-[r:REL {id: row.id}]->(t)
SET r.relation   = row.relation,
    r.disease    = row.disease,
    r.status     = row.status,
    r.confidence = toFloat(row.confidence);

// 4. 校验（应为 32091 / 288064）
MATCH (e:Entity) RETURN count(e) AS 节点数;
MATCH ()-[r:REL]->() RETURN count(r) AS 关系数;
