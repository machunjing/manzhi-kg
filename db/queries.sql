-- =============================================================================
-- 慢知 · 慢性病智能知识服务平台 —— 数据库验收 / 演示查询集
-- 数据库：manzhi（MySQL 8.0）
-- 用法：DataGrip 连上 manzhi 后，选中某条语句 Ctrl+Enter 单条执行
-- 说明：第 4 节是「约束真的生效」的现场演示，会故意报错，属正常现象
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. 连接参数（DataGrip → New → Data Source → MySQL）
--     Host: localhost      Port: 3306
--     User: root           Password: <你的口令>
--     Database: manzhi
--     注意：URL 后面加 ?characterEncoding=utf8mb4，否则中文可能显示为问号
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- 1. 我建了什么：表 / 视图 / 触发器 清单
-- -----------------------------------------------------------------------------
SELECT table_name, table_type, table_comment
FROM information_schema.tables
WHERE table_schema = 'manzhi'
ORDER BY table_type, table_name;

SELECT trigger_name, event_object_table, action_timing, event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'manzhi';

-- -----------------------------------------------------------------------------
-- 2. 每张表多少条数据（答辩时一眼能说清数据规模）
-- -----------------------------------------------------------------------------
SELECT 'users' AS 表名, COUNT(*) AS 行数 FROM users
UNION ALL SELECT 'documents',         COUNT(*) FROM documents
UNION ALL SELECT 'chunks',            COUNT(*) FROM chunks
UNION ALL SELECT 'entities',          COUNT(*) FROM entities
UNION ALL SELECT 'relations',         COUNT(*) FROM relations
UNION ALL SELECT 'relation_review',   COUNT(*) FROM relation_review
UNION ALL SELECT 'collect_tasks',     COUNT(*) FROM collect_tasks
UNION ALL SELECT 'collect_task_logs', COUNT(*) FROM collect_task_logs
UNION ALL SELECT 'operation_logs',    COUNT(*) FROM operation_logs
UNION ALL SELECT 'qa_sessions',       COUNT(*) FROM qa_sessions
UNION ALL SELECT 'qa_messages',       COUNT(*) FROM qa_messages
UNION ALL SELECT 'system_config',     COUNT(*) FROM system_config;

-- -----------------------------------------------------------------------------
-- 3. 审核四态分布（对应「关系审核」页的环形图，视图 v_review_stats）
--    预期：已审核 175 / 待审核 41 / 候选 26 / 已驳回 21
-- -----------------------------------------------------------------------------
SELECT * FROM v_review_stats;

-- -----------------------------------------------------------------------------
-- 4. 待审核队列（视图 v_pending_review，已 join 出实体名，可直接给审核页用）
-- -----------------------------------------------------------------------------
SELECT * FROM v_pending_review LIMIT 20;

-- -----------------------------------------------------------------------------
-- 5. 实体类型分布（对应「数据总览」页的实体构成）
-- -----------------------------------------------------------------------------
SELECT type AS 实体类型, COUNT(*) AS 数量
FROM entities
GROUP BY type
ORDER BY 数量 DESC;

-- -----------------------------------------------------------------------------
-- 6. 关系类型分布 + 平均置信度（对应「关联统计」页）
-- -----------------------------------------------------------------------------
SELECT relation AS 关系类型,
       COUNT(*) AS 数量,
       ROUND(AVG(confidence), 3) AS 平均置信度
FROM relations
GROUP BY relation
ORDER BY 数量 DESC;

-- -----------------------------------------------------------------------------
-- 7. 证据链：一条关系能追到哪篇文献、哪段原文
--    relations.snippet 是证据片段，source 记录抽取来源
-- -----------------------------------------------------------------------------
SELECT h.name AS 头实体, r.relation AS 关系, t.name AS 尾实体,
       r.confidence AS 置信度, r.status AS 状态,
       r.source AS 来源, LEFT(r.snippet, 60) AS 证据片段
FROM relations r
JOIN entities h ON h.id = r.head_id
JOIN entities t ON t.id = r.tail_id
WHERE r.status = '已审核'
ORDER BY r.confidence DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- 8. 图谱取数：以「2型糖尿病」为中心取 2 跳邻居（递归 CTE，纯 SQL 版子图）
--    这就是 Neo4j 里 MATCH (c)-[:REL*1..2]-(n) 的等价写法
-- -----------------------------------------------------------------------------
WITH RECURSIVE hop AS (
    SELECT e.id, e.name, e.type, 0 AS depth, CAST(e.id AS CHAR(200)) AS visited
    FROM entities e WHERE e.name = '2型糖尿病'
    UNION ALL
    SELECT n.id, n.name, n.type, h.depth + 1,
           CONCAT(h.visited, ',', n.id)
    FROM hop h
    JOIN relations r ON r.head_id = h.id OR r.tail_id = h.id
    JOIN entities n ON n.id = IF(r.head_id = h.id, r.tail_id, r.head_id)
    WHERE h.depth < 2
      AND FIND_IN_SET(n.id, h.visited) = 0
)
SELECT DISTINCT depth AS 跳数, id, name AS 实体名, type AS 类型
FROM hop
ORDER BY 跳数, 实体名;

-- -----------------------------------------------------------------------------
-- 9. 全文检索：ngram 全文索引（中文按 2 字切分，问答里做关键词召回）
--    注意：MySQL ngram 有 50% 阈值规则，命中行数超过一半的词会返回空，
--          所以生产上用它做 BM25 一路召回，和向量召回互补，不单独兜底
-- -----------------------------------------------------------------------------
SELECT id, title, LEFT(abstract, 50) AS 摘要开头
FROM documents
WHERE MATCH(title, abstract) AGAINST('血脂' IN BOOLEAN MODE)
LIMIT 10;

-- -----------------------------------------------------------------------------
-- 10. 问答会话结构：一次提问存了什么（session → messages → result JSON）
-- -----------------------------------------------------------------------------
SELECT s.id AS 会话, s.user_name AS 用户, s.title AS 会话标题,
       s.disease AS 涉及疾病, s.rounds AS 轮数, s.updated_at AS 最近更新,
       JSON_KEYS(m.result) AS 结果字段
FROM qa_sessions s
LEFT JOIN qa_messages m ON m.session_id = s.id
ORDER BY s.updated_at DESC
LIMIT 10;

-- -----------------------------------------------------------------------------
-- 11. 采集任务：进度与状态（对应「采集任务管理」页）
-- -----------------------------------------------------------------------------
SELECT id AS 任务ID, name AS 任务名, source AS 数据源, disease AS 目标疾病,
       status AS 状态, progress AS 进度, fetched_count AS 已采条数,
       start_at AS 开始时间
FROM collect_tasks
ORDER BY created_at DESC
LIMIT 15;

-- -----------------------------------------------------------------------------
-- 12. 系统配置：JSON 列存分组配置（对应「系统设置」页的三个 Tab）
-- -----------------------------------------------------------------------------
SELECT config_group AS 配置组, JSON_PRETTY(config_value) AS 配置内容
FROM system_config;


-- =============================================================================
-- 13. 约束现场演示（这几条会报错，报错才是对的）
--     注意：13.2 成功后会把 1 条「候选」改成「待审核」，四态分布变成
--           已审核 175 / 待审核 42 / 候选 25 / 已驳回 21。
--           想恢复原样：mysql -uroot -p manzhi < seed.sql
-- =============================================================================

-- 13.1 非法状态流转：候选 → 已审核（跳过待审核），触发器 trg_relations_status_guard 拦截
--      预期：ERROR 1644 (45000): 非法审核状态流转：只允许 候选→待审核→已审核/已驳回
UPDATE relations SET status = '已审核' WHERE status = '候选' LIMIT 1;

-- 13.2 合法状态流转：候选 → 待审核，同时 AFTER 触发器自动往 relation_review 写一条审计
--      预期：1 row affected，然后 relation_review 多一行「提交审核」
UPDATE relations SET status = '待审核' WHERE status = '候选' LIMIT 1;
SELECT * FROM relation_review ORDER BY id DESC LIMIT 3;

-- 13.3 外键保护：删除仍被关系引用的实体
--      预期：ERROR 1451，fk_relations_head ON DELETE RESTRICT
DELETE FROM entities WHERE id = 'E0001';

-- 13.4 唯一键保护：插入重复三元组
--      预期：ERROR 1062 Duplicate entry 'E0001-危险因素-E0010' for key 'relations.uk_relations_triple'
INSERT INTO relations (id, head_id, relation, tail_id, disease, status, confidence, source)
VALUES ('R9999', 'E0001', '危险因素', 'E0010', '2型糖尿病', '候选', 0.8, '手工录入');

-- 13.5 自环保护：头尾同一个实体
--      预期：ERROR 3819，CHECK (head_id <> tail_id) 拦截
INSERT INTO relations (id, head_id, relation, tail_id, disease, status, confidence, source)
VALUES ('R9998', 'E0001', '共病', 'E0001', '2型糖尿病', '候选', 0.8, '手工录入');

-- 13.6 枚举保护：写入未定义的实体类型
--      预期：ERROR 1265 Data truncated for column 'type'
INSERT INTO entities (id, name, type, status, confidence, source)
VALUES ('E9999', '测试实体', '保健品', '候选', 0.5, '手工录入');
