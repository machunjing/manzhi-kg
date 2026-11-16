-- =============================================================================
-- 慢知 · 慢性病智能知识服务平台  数据库 Schema
-- 目标库：MySQL 8.0.16+（需要 CHECK 约束与 ngram 全文索引）
-- 字符集：utf8mb4 / utf8mb4_0900_ai_ci
-- 说明：本文件可重复执行（先按外键逆序删表再重建），不会影响其他库
-- 对应契约：慢知前端原型/docs/openapi.yaml
-- =============================================================================

SET NAMES utf8mb4;
SET time_zone = '+08:00';

CREATE DATABASE IF NOT EXISTS `manzhi`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE `manzhi`;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW  IF EXISTS `v_pending_review`;
DROP TABLE IF EXISTS `qa_messages`;
DROP TABLE IF EXISTS `qa_sessions`;
DROP TABLE IF EXISTS `operation_logs`;
DROP TABLE IF EXISTS `collect_task_logs`;
DROP TABLE IF EXISTS `collect_tasks`;
DROP TABLE IF EXISTS `relation_review`;
DROP TABLE IF EXISTS `relations`;
DROP TABLE IF EXISTS `entity_alias`;
DROP TABLE IF EXISTS `entities`;
DROP TABLE IF EXISTS `chunks`;
DROP TABLE IF EXISTS `documents`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `system_config`;
SET FOREIGN_KEY_CHECKS = 1;


-- -----------------------------------------------------------------------------
-- 1. 用户与角色
-- -----------------------------------------------------------------------------
CREATE TABLE `users` (
  `id`            VARCHAR(16)  NOT NULL                COMMENT '用户ID，如 U0001',
  `account`       VARCHAR(64)  NOT NULL                COMMENT '登录账号',
  `password_hash` VARCHAR(255) NOT NULL                COMMENT 'bcrypt 口令散列（不存明文）',
  `name`          VARCHAR(64)  NOT NULL                COMMENT '姓名',
  `avatar`        VARCHAR(8)   DEFAULT NULL            COMMENT '头像文字，取姓名首字',
  `role`          ENUM('管理员','医学审核员','普通用户') NOT NULL DEFAULT '普通用户' COMMENT '角色，决定可访问模块',
  `dept`          VARCHAR(64)  DEFAULT NULL            COMMENT '所属部门/课题组',
  `phone`         VARCHAR(32)  DEFAULT NULL            COMMENT '手机号（脱敏存储）',
  `email`         VARCHAR(128) DEFAULT NULL            COMMENT '邮箱',
  `status`        ENUM('启用','禁用') NOT NULL DEFAULT '启用' COMMENT '账号状态',
  `last_login_at` DATETIME     DEFAULT NULL            COMMENT '最后登录时间',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_account` (`account`),
  KEY `idx_users_role_status` (`role`, `status`),
  CONSTRAINT `chk_users_email` CHECK (`email` IS NULL OR `email` LIKE '%@%')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户与角色';


-- -----------------------------------------------------------------------------
-- 2. 文献与指南
-- -----------------------------------------------------------------------------
CREATE TABLE `documents` (
  `id`           VARCHAR(24)  NOT NULL                 COMMENT '文献ID，如 DOC-P0001',
  `pmid`         VARCHAR(16)  DEFAULT NULL             COMMENT 'PubMed ID，指南类为空',
  `title`        VARCHAR(512) NOT NULL                 COMMENT '标题',
  `title_en`     VARCHAR(512) DEFAULT NULL             COMMENT '英文标题',
  `authors`      VARCHAR(512) DEFAULT NULL             COMMENT '作者，多作者用 / 分隔',
  `journal`      VARCHAR(255) DEFAULT NULL             COMMENT '期刊或指南发布机构',
  `doc_type`     VARCHAR(32)  NOT NULL DEFAULT '研究论文' COMMENT '研究论文/综述/临床指南/专家共识/其他',
  `disease`      VARCHAR(32)  NOT NULL                 COMMENT '所属疾病维度',
  `source`       VARCHAR(64)  NOT NULL                 COMMENT 'PubMed/本地指南文件/MedlinePlus/DiaKG/OpenCMKG',
  `publish_date` DATE         DEFAULT NULL             COMMENT '发表日期',
  `chunk_count`  INT UNSIGNED NOT NULL DEFAULT 0       COMMENT '已切分的文本块数',
  `status`       ENUM('待清洗','处理中','已入库','解析失败') NOT NULL DEFAULT '待清洗' COMMENT '处理状态',
  `doi`          VARCHAR(128) DEFAULT NULL,
  `url`          VARCHAR(512) DEFAULT NULL,
  `abstract`     MEDIUMTEXT                            COMMENT '摘要或指南正文摘录',
  `mesh`         JSON         DEFAULT NULL             COMMENT 'MeSH 主题词数组',
  `collected_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_documents_pmid` (`pmid`),
  KEY `idx_documents_disease` (`disease`),
  KEY `idx_documents_source` (`source`),
  KEY `idx_documents_type_date` (`doc_type`, `publish_date`),
  KEY `idx_documents_status` (`status`),
  FULLTEXT KEY `ft_documents_text` (`title`, `abstract`) WITH PARSER ngram,
  CONSTRAINT `chk_documents_chunk_count` CHECK (`chunk_count` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文献与指南';


-- -----------------------------------------------------------------------------
-- 3. 文本块（300 字 / 重叠 50）
-- -----------------------------------------------------------------------------
CREATE TABLE `chunks` (
  `id`         VARCHAR(24)      NOT NULL               COMMENT '切块ID，如 C00001',
  `doc_id`     VARCHAR(24)      NOT NULL               COMMENT '所属文献',
  `chunk_idx`  INT UNSIGNED     NOT NULL               COMMENT '文献内序号，从 0 开始',
  `disease`    VARCHAR(32)      NOT NULL               COMMENT '继承文献的疾病维度，便于过滤',
  `text_len`   SMALLINT UNSIGNED NOT NULL              COMMENT '字符数',
  `text`       TEXT             NOT NULL               COMMENT '切块正文',
  `vector_id`  VARCHAR(64)      DEFAULT NULL           COMMENT 'Milvus 主键，向量化后回填',
  `created_at` DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_chunks_doc_idx` (`doc_id`, `chunk_idx`),
  KEY `idx_chunks_disease` (`disease`),
  FULLTEXT KEY `ft_chunks_text` (`text`) WITH PARSER ngram,
  CONSTRAINT `fk_chunks_doc` FOREIGN KEY (`doc_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_chunks_len` CHECK (`text_len` BETWEEN 1 AND 2000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='文本切块';


-- -----------------------------------------------------------------------------
-- 4. 图谱实体
-- -----------------------------------------------------------------------------
CREATE TABLE `entities` (
  `id`            VARCHAR(16)  NOT NULL                COMMENT '实体ID，如 E0001',
  `name`          VARCHAR(255) NOT NULL                COMMENT '实体名称（唯一）',
  `type`          ENUM('疾病','危险因素','症状','并发症','药物类别','检查指标','生活方式','其他')
                               NOT NULL                COMMENT '实体类型',
  `standard_name` VARCHAR(255) DEFAULT NULL            COMMENT '标准名称（MeSH 对齐后）',
  `aliases`       JSON         DEFAULT NULL            COMMENT '别名数组',
  `diseases`      JSON         DEFAULT NULL            COMMENT '关联疾病数组',
  `source`        VARCHAR(128) DEFAULT NULL            COMMENT '抽取来源，如 指南抽取 / MeSH 对齐',
  `status`        ENUM('候选','待审核','已审核','已驳回') NOT NULL DEFAULT '候选' COMMENT '审核状态',
  `confidence`    DECIMAL(4,3) NOT NULL DEFAULT 0.500  COMMENT '抽取置信度 0~1',
  `rel_count`     INT UNSIGNED NOT NULL DEFAULT 0      COMMENT '关联关系数（冗余字段，审核后回写）',
  `synced_at`     DATETIME     DEFAULT NULL            COMMENT '同步到 Neo4j 的时间',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_entities_name` (`name`),
  KEY `idx_entities_type_status` (`type`, `status`),
  KEY `idx_entities_status` (`status`),
  CONSTRAINT `chk_entities_confidence` CHECK (`confidence` BETWEEN 0 AND 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识图谱实体';


-- -----------------------------------------------------------------------------
-- 实体别名 / 同义词
--   真实语料里同一个概念有多个叫法（OpenCMKG 用「中风」，指南用「脑卒中」），
--   不归一就会出现「实体明明在库里却查不到」。别名表就是干这个的。
--   来源：OpenCMKG 的 SameAs 关系 + 人工补充的常用同义词
-- -----------------------------------------------------------------------------
CREATE TABLE `entity_alias` (
  `alias`      VARCHAR(255) NOT NULL                   COMMENT '别名或同义写法',
  `entity_id`  VARCHAR(16)  NOT NULL                   COMMENT '指向的标准实体',
  `source`     VARCHAR(32)  DEFAULT NULL               COMMENT '别名来源：OpenCMKG-SameAs / 人工补充',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`alias`),
  KEY `idx_alias_entity` (`entity_id`),
  CONSTRAINT `fk_alias_entity` FOREIGN KEY (`entity_id`) REFERENCES `entities` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='实体别名（实体归一用）';


-- -----------------------------------------------------------------------------
-- 5. 图谱关系（三元组）
-- -----------------------------------------------------------------------------
CREATE TABLE `relations` (
  `id`             VARCHAR(16)  NOT NULL               COMMENT '关系ID，如 R0001',
  `head_id`        VARCHAR(16)  NOT NULL               COMMENT '头实体',
  `tail_id`        VARCHAR(16)  NOT NULL               COMMENT '尾实体',
  `relation`       ENUM('危险因素','临床表现','并发症','常用药物','监测指标','干预措施','共病','关联疾病','导致')
                                NOT NULL               COMMENT '关系类型',
  `disease`        VARCHAR(32)  NOT NULL               COMMENT '所属疾病维度',
  `source`         VARCHAR(255) DEFAULT NULL           COMMENT '证据来源（文献/指南名）',
  `section`        VARCHAR(64)  DEFAULT NULL           COMMENT '来源章节',
  `evidence_level` VARCHAR(32)  DEFAULT NULL           COMMENT '证据等级，如 指南A级',
  `confidence`     DECIMAL(4,3) NOT NULL DEFAULT 0.500 COMMENT '置信度 0~1',
  `status`         ENUM('候选','待审核','已审核','已驳回') NOT NULL DEFAULT '候选' COMMENT '审核状态',
  `snippet`        VARCHAR(1000) DEFAULT NULL          COMMENT '证据原文片段',
  `reviewer`       VARCHAR(64)  DEFAULT NULL           COMMENT '最近一次审核人',
  `reviewed_at`    DATETIME     DEFAULT NULL           COMMENT '最近一次审核时间',
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_relations_triple` (`head_id`, `relation`, `tail_id`),
  KEY `idx_relations_head` (`head_id`),
  KEY `idx_relations_tail` (`tail_id`),
  KEY `idx_relations_status` (`status`),
  KEY `idx_relations_disease_status` (`disease`, `status`),
  KEY `idx_relations_type` (`relation`),
  CONSTRAINT `fk_relations_head` FOREIGN KEY (`head_id`) REFERENCES `entities` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_relations_tail` FOREIGN KEY (`tail_id`) REFERENCES `entities` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `chk_relations_confidence` CHECK (`confidence` BETWEEN 0 AND 1),
  CONSTRAINT `chk_relations_self` CHECK (`head_id` <> `tail_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识图谱关系（三元组）';


-- -----------------------------------------------------------------------------
-- 6. 关系审核流水（每次状态流转一条，不可修改）
-- -----------------------------------------------------------------------------
CREATE TABLE `relation_review` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `relation_id` VARCHAR(16)  NOT NULL                  COMMENT '被审核的关系',
  `action`      ENUM('提交审核','审核通过','驳回','修改后通过','暂缓审核') NOT NULL COMMENT '审核动作',
  `from_status` ENUM('候选','待审核','已审核','已驳回') NOT NULL COMMENT '流转前状态',
  `to_status`   ENUM('候选','待审核','已审核','已驳回') NOT NULL COMMENT '流转后状态',
  `operator`    VARCHAR(64)  NOT NULL                  COMMENT '操作人',
  `comment`     VARCHAR(500) DEFAULT NULL              COMMENT '审核意见 / 驳回原因',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_review_relation` (`relation_id`, `created_at`),
  KEY `idx_review_operator` (`operator`, `created_at`),
  CONSTRAINT `fk_review_relation` FOREIGN KEY (`relation_id`) REFERENCES `relations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='关系审核流水';


-- -----------------------------------------------------------------------------
-- 7. 数据采集任务
-- -----------------------------------------------------------------------------
CREATE TABLE `collect_tasks` (
  `id`            VARCHAR(24)  NOT NULL                COMMENT '任务ID，如 T2026001',
  `name`          VARCHAR(255) NOT NULL                COMMENT '任务名称',
  `source`        ENUM('PubMed','MedlinePlus','本地指南文件','DiaKG','OpenCMKG') NOT NULL COMMENT '数据来源',
  `collect_type`  VARCHAR(64)  DEFAULT NULL            COMMENT '采集方式，如 API 接口采集',
  `disease`       VARCHAR(32)  NOT NULL                COMMENT '目标疾病',
  `keyword`       VARCHAR(500) DEFAULT NULL            COMMENT '检索式',
  `status`        ENUM('排队中','运行中','已完成','已暂停','失败') NOT NULL DEFAULT '排队中' COMMENT '任务状态',
  `progress`      TINYINT UNSIGNED NOT NULL DEFAULT 0  COMMENT '进度百分比 0~100',
  `fetched_count` INT UNSIGNED NOT NULL DEFAULT 0      COMMENT '已采集条数',
  `operator`      VARCHAR(64)  DEFAULT NULL            COMMENT '创建人',
  `start_at`      DATETIME     DEFAULT NULL            COMMENT '开始时间',
  `end_at`        DATETIME     DEFAULT NULL            COMMENT '结束时间',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_tasks_status` (`status`),
  KEY `idx_tasks_source_disease` (`source`, `disease`),
  CONSTRAINT `chk_tasks_progress` CHECK (`progress` <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='数据采集任务';


-- -----------------------------------------------------------------------------
-- 8. 采集任务运行日志
-- -----------------------------------------------------------------------------
CREATE TABLE `collect_task_logs` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `task_id`    VARCHAR(24)  NOT NULL                   COMMENT '所属任务',
  `level`      ENUM('INFO','WARN','ERROR') NOT NULL DEFAULT 'INFO',
  `message`    VARCHAR(1000) NOT NULL                  COMMENT '日志内容',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_task_logs_task` (`task_id`, `created_at`),
  CONSTRAINT `fk_task_logs_task` FOREIGN KEY (`task_id`) REFERENCES `collect_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='采集任务运行日志';


-- -----------------------------------------------------------------------------
-- 9. 操作日志（审计）
-- -----------------------------------------------------------------------------
CREATE TABLE `operation_logs` (
  `id`         VARCHAR(16)  NOT NULL                   COMMENT '日志ID，如 L00060',
  `user_name`  VARCHAR(64)  NOT NULL                   COMMENT '操作人',
  `module`     VARCHAR(64)  NOT NULL                   COMMENT '操作模块',
  `action`     VARCHAR(128) NOT NULL                   COMMENT '操作内容',
  `ip`         VARCHAR(64)  DEFAULT NULL               COMMENT '来源 IP',
  `result`     ENUM('成功','失败') NOT NULL DEFAULT '成功' COMMENT '执行结果',
  `detail`     VARCHAR(500) DEFAULT NULL               COMMENT '操作对象与耗时等明细',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_logs_time` (`created_at`),
  KEY `idx_logs_module` (`module`, `created_at`),
  KEY `idx_logs_user` (`user_name`, `created_at`),
  KEY `idx_logs_result` (`result`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='操作日志（审计）';


-- -----------------------------------------------------------------------------
-- 10. 问答会话与消息
-- -----------------------------------------------------------------------------
CREATE TABLE `qa_sessions` (
  `id`         VARCHAR(16)  NOT NULL                   COMMENT '会话ID，如 Q0001',
  `title`      VARCHAR(255) NOT NULL                   COMMENT '会话标题，取首个问题',
  `disease`    VARCHAR(32)  DEFAULT NULL               COMMENT '主要涉及疾病',
  `user_name`  VARCHAR(64)  NOT NULL                   COMMENT '所属用户',
  `rounds`     INT UNSIGNED NOT NULL DEFAULT 0         COMMENT '问答轮数',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_qa_sessions_user` (`user_name`, `updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='问答会话';


CREATE TABLE `qa_messages` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `session_id` VARCHAR(16)  NOT NULL                   COMMENT '所属会话',
  `role`       ENUM('user','assistant') NOT NULL       COMMENT '消息角色',
  `content`    MEDIUMTEXT   NOT NULL                   COMMENT '消息正文',
  `result`     JSON         DEFAULT NULL               COMMENT 'assistant 消息的完整检索结果（步骤/引用/路径）',
  `elapsed_ms` INT UNSIGNED DEFAULT NULL               COMMENT '本次回答总耗时',
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_qa_messages_session` (`session_id`, `created_at`),
  CONSTRAINT `fk_qa_messages_session` FOREIGN KEY (`session_id`) REFERENCES `qa_sessions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='问答消息';


-- -----------------------------------------------------------------------------
-- 11. 系统配置（按分组存 JSON，避免频繁改表）
-- -----------------------------------------------------------------------------
CREATE TABLE `system_config` (
  `config_group` VARCHAR(32) NOT NULL                  COMMENT '分组：basic/permissions/sources/models/retrieval',
  `config_value` JSON        NOT NULL                  COMMENT '该分组的配置内容',
  `updated_at`   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_by`   VARCHAR(64) DEFAULT NULL,
  PRIMARY KEY (`config_group`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统配置';


-- -----------------------------------------------------------------------------
-- 12. 触发器
--    12.1 状态机守卫：只允许 候选→待审核→已审核/已驳回
--    12.2 流转留痕：每次状态变化自动写一条审核流水
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_relations_status_guard`;
DROP TRIGGER IF EXISTS `trg_relations_status_audit`;

DELIMITER $$
CREATE TRIGGER `trg_relations_status_guard`
BEFORE UPDATE ON `relations`
FOR EACH ROW
BEGIN
  IF NEW.`status` <> OLD.`status` THEN
    IF NOT (
         (OLD.`status` = '候选'   AND NEW.`status` = '待审核')
      OR (OLD.`status` = '待审核' AND NEW.`status` IN ('已审核', '已驳回'))
      OR (OLD.`status` = '已驳回' AND NEW.`status` = '待审核')
      OR (OLD.`status` = '已审核' AND NEW.`status` = '待审核')
    ) THEN
      SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = '非法审核状态流转：只允许 候选→待审核→已审核/已驳回';
    END IF;
  END IF;
END$$

CREATE TRIGGER `trg_relations_status_audit`
AFTER UPDATE ON `relations`
FOR EACH ROW
BEGIN
  IF NEW.`status` <> OLD.`status` THEN
    INSERT INTO `relation_review`
      (`relation_id`, `action`, `from_status`, `to_status`, `operator`, `comment`)
    VALUES (
      NEW.`id`,
      CASE NEW.`status`
        WHEN '已审核' THEN '审核通过'
        WHEN '已驳回' THEN '驳回'
        WHEN '待审核' THEN '提交审核'
        ELSE '暂缓审核'
      END,
      OLD.`status`,
      NEW.`status`,
      COALESCE(NEW.`reviewer`, 'system'),
      '由触发器自动记录'
    );
  END IF;
END$$
DELIMITER ;


-- -----------------------------------------------------------------------------
-- 13. 视图：待审核队列（审核工作台直接用）
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `v_pending_review` AS
SELECT
  r.`id`            AS relation_id,
  r.`relation`      AS relation_type,
  r.`disease`,
  h.`name`          AS head_name,
  h.`type`          AS head_type,
  t.`name`          AS tail_name,
  t.`type`          AS tail_type,
  r.`confidence`,
  r.`evidence_level`,
  r.`source`,
  r.`snippet`,
  r.`created_at`
FROM `relations` r
JOIN `entities` h ON h.`id` = r.`head_id`
JOIN `entities` t ON t.`id` = r.`tail_id`
WHERE r.`status` = '待审核';


-- -----------------------------------------------------------------------------
-- 14. 视图：审核进度统计（首页与数据资源总览用）
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW `v_review_stats` AS
SELECT
  `status`,
  COUNT(*) AS cnt,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM `relations`), 2) AS pct
FROM `relations`
GROUP BY `status`;
