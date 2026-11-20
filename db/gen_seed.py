# -*- coding: utf-8 -*-
"""
从 慢知前端原型/src/mock/data/*.json 生成：
  1) db/seed.sql      —— MySQL 演示数据（与 schema.sql 配套）
  2) db/seed.cypher   —— Neo4j 图数据（UNWIND 批量导入）

用法：python db/gen_seed.py
"""
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, '..', '慢知前端原型', 'src', 'mock', 'data')

# 演示口令（与前端登录一致）的 bcrypt 散列，rounds=10
DEMO_HASH = '$2b$10$wS1bsotWGmakC9UN7bCO0eF/o2qeXje.8t7sceZhuC7Li0J1AoGFe'


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


def q(v):
    """转成 SQL 字面量"""
    if v is None or v == '':
        return 'NULL'
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, dict)):
        v = json.dumps(v, ensure_ascii=False)
    return "'" + str(v).replace('\\', '\\\\').replace("'", "''") + "'"


def rows_to_sql(table, cols, rows, batch=40):
    out = []
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        vals = ',\n'.join('  (' + ', '.join(q(v) for v in r) + ')' for r in chunk)
        out.append(f"INSERT INTO `{table}` ({', '.join('`' + c + '`' for c in cols)}) VALUES\n{vals};")
    return '\n\n'.join(out)


def main():
    users = load('users.json')
    documents = load('documents.json')
    entities = load('entities.json')
    relations = load('relations.json')
    tasks = load('tasks.json')
    logs = load('logs.json')
    sessions = load('qaSessions.json')
    chunks = load('chunks.json')

    rel_count = Counter()
    for r in relations:
        rel_count[r['headId']] += 1
        rel_count[r['tailId']] += 1

    parts = []
    parts.append('-- 由 db/gen_seed.py 自动生成，请勿手工修改')
    parts.append('-- 数据来源：慢知前端原型/src/mock/data/*.json（演示数据）')
    parts.append('SET NAMES utf8mb4;\nUSE `manzhi`;\n')

    # 用户
    u_rows = [(u['id'], u['account'], DEMO_HASH, u['name'], u.get('avatar'), u.get('role'),
               u.get('dept'), u.get('phone'), u.get('email'), u.get('status'),
               u.get('lastLogin'), u.get('createdAt'))
              for u in users]
    parts.append('-- 用户 %d 条（口令均为演示口令的 bcrypt 散列）' % len(u_rows))
    parts.append(rows_to_sql('users',
                             ['id', 'account', 'password_hash', 'name', 'avatar', 'role',
                              'dept', 'phone', 'email', 'status', 'last_login_at', 'created_at'],
                             u_rows))

    # 文献
    d_rows = [(d['id'], d.get('pmid'), d['title'], d.get('titleEn'), d.get('authors'),
               d.get('journal'), d.get('docType') or '其他', d['disease'], d['source'],
               d.get('publishDate'), d.get('chunkCount') or 0, d.get('status') or '待清洗',
               d.get('doi'), d.get('url'), d.get('abstract'), d.get('mesh'), d.get('collectedAt'))
              for d in documents]
    parts.append('\n-- 文献 %d 条' % len(d_rows))
    parts.append(rows_to_sql('documents',
                             ['id', 'pmid', 'title', 'title_en', 'authors', 'journal', 'doc_type',
                              'disease', 'source', 'publish_date', 'chunk_count', 'status',
                              'doi', 'url', 'abstract', 'mesh', 'collected_at'],
                             d_rows))

    # 文本块（演示数据仅 5 条样例）
    c_rows = [(c['id'], c['docId'], c['chunkIdx'], c['disease'], c['textLen'], c['text'])
              for c in chunks]
    parts.append('\n-- 文本块 %d 条（演示样例，全量 32,078 条在向量库）' % len(c_rows))
    parts.append(rows_to_sql('chunks',
                             ['id', 'doc_id', 'chunk_idx', 'disease', 'text_len', 'text'],
                             c_rows))

    # 实体
    e_rows = [(e['id'], e['name'], e['type'], e.get('standardName'), e.get('aliases'),
               e.get('diseases'), e.get('source'), e.get('status'), e.get('confidence') or 0.5,
               rel_count.get(e['id'], 0), e.get('createdAt'))
              for e in entities]
    parts.append('\n-- 实体 %d 条' % len(e_rows))
    parts.append(rows_to_sql('entities',
                             ['id', 'name', 'type', 'standard_name', 'aliases', 'diseases',
                              'source', 'status', 'confidence', 'rel_count', 'created_at'],
                             e_rows))

    # 关系
    r_rows = [(r['id'], r['headId'], r['tailId'], r['relation'], r['disease'], r.get('source'),
               r.get('section'), r.get('evidenceLevel'), r.get('confidence') or 0.5,
               r.get('status'), r.get('snippet'), r.get('reviewer'), r.get('createdAt'))
              for r in relations]
    parts.append('\n-- 关系 %d 条' % len(r_rows))
    parts.append(rows_to_sql('relations',
                             ['id', 'head_id', 'tail_id', 'relation', 'disease', 'source',
                              'section', 'evidence_level', 'confidence', 'status', 'snippet',
                              'reviewer', 'created_at'],
                             r_rows))

    # 审核流水（已审核 / 已驳回各补一条，模拟历史审核）
    rev_rows = []
    for r in relations:
        if r['status'] == '已审核':
            rev_rows.append((r['id'], '审核通过', '待审核', '已审核',
                             r.get('reviewer') or '系统导入', '证据来源与原文一致，审核通过', r.get('createdAt')))
        elif r['status'] == '已驳回':
            rev_rows.append((r['id'], '驳回', '待审核', '已驳回',
                             r.get('reviewer') or '系统导入', '断言与原文表述不一致，驳回', r.get('createdAt')))
    parts.append('\n-- 审核流水 %d 条' % len(rev_rows))
    parts.append(rows_to_sql('relation_review',
                             ['relation_id', 'action', 'from_status', 'to_status',
                              'operator', 'comment', 'created_at'],
                             rev_rows))

    # 采集任务
    t_rows = [(t['id'], t['name'], t['source'], t.get('collectType'), t['disease'],
               t.get('keyword'), t.get('status'), t.get('progress') or 0, t.get('count') or 0,
               t.get('operator'), t.get('startAt'), t.get('endAt'))
              for t in tasks]
    parts.append('\n-- 采集任务 %d 条' % len(t_rows))
    parts.append(rows_to_sql('collect_tasks',
                             ['id', 'name', 'source', 'collect_type', 'disease', 'keyword',
                              'status', 'progress', 'fetched_count', 'operator', 'start_at', 'end_at'],
                             t_rows))

    # 操作日志
    l_rows = [(l['id'], l['user'], l['module'], l['action'], l.get('ip'), l.get('result'),
               l.get('detail'), l.get('time'))
              for l in logs]
    parts.append('\n-- 操作日志 %d 条' % len(l_rows))
    parts.append(rows_to_sql('operation_logs',
                             ['id', 'user_name', 'module', 'action', 'ip', 'result', 'detail', 'created_at'],
                             l_rows))

    # 问答会话
    s_rows = [(s['id'], s['title'], s.get('disease'), s.get('user'), s.get('rounds') or 0,
               s.get('createdAt'))
              for s in sessions]
    parts.append('\n-- 问答会话 %d 条' % len(s_rows))
    parts.append(rows_to_sql('qa_sessions',
                             ['id', 'title', 'disease', 'user_name', 'rounds', 'created_at'],
                             s_rows))

    # 系统配置
    cfg = [
        ('basic', {
            'name': '慢知 · 慢性病智能问答系统', 'shortName': '慢知',
            'org': '慢知知识工程组', 'version': 'v1.4.2',
            'owner': '慢知团队', 'contact': 'contact@manzhi.local',
            'desc': '面向 2 型糖尿病、高血压与血脂异常的慢性病知识问答与科研辅助平台'
        }),
        ('permissions', [
            {'role': '管理员', 'modules': ['用户管理', '知识数据管理', '知识图谱管理', '智能问答', '关联分析', '系统设置'],
             'scope': '全部数据', 'canReview': True, 'canDelete': True},
            {'role': '医学审核员', 'modules': ['知识数据管理', '知识图谱管理', '关系审核'],
             'scope': '所负责疾病', 'canReview': True, 'canDelete': False},
            {'role': '普通用户', 'modules': ['智能问答', '关联分析'],
             'scope': '仅已审核知识', 'canReview': False, 'canDelete': False}
        ]),
        ('sources', [
            {'name': 'PubMed E-utilities', 'type': 'API',
             'url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils', 'enabled': True},
            {'name': 'MedlinePlus', 'type': 'API', 'url': 'https://medlineplus.gov', 'enabled': True},
            {'name': '本地指南 PDF 目录', 'type': '文件', 'url': '数据包/01_外部公开语料/指南PDF', 'enabled': True},
            {'name': 'DiaKG', 'type': '图谱', 'url': 'https://github.com/China-Linguistics/DiaKG', 'enabled': True},
            {'name': 'OpenCMKG', 'type': '图谱', 'url': 'https://github.com/OpenCMKG', 'enabled': False}
        ]),
        ('models', [
            {'label': '大语言模型', 'value': '智谱 GLM-4', 'note': '用于答案生成'},
            {'label': 'Embedding 模型', 'value': 'BGE-M3', 'note': '1024 维稠密向量'},
            {'label': 'Reranker 模型', 'value': 'bge-reranker-large', 'note': 'Cross-Encoder 精排'},
            {'label': '向量数据库', 'value': 'Milvus', 'note': '集合：manzhi_chunks'},
            {'label': '图数据库', 'value': 'Neo4j', 'note': '库：neo4j'},
            {'label': '关系数据库', 'value': 'MySQL 8.0', 'note': '业务元数据'}
        ]),
        ('retrieval', {
            'vectorTopK': 20, 'rerankTopK': 5, 'rrfK': 60,
            'chunkSize': 300, 'chunkOverlap': 50, 'temperature': 0.2
        })
    ]
    cfg_rows = [(g, json.dumps(v, ensure_ascii=False), 'system') for g, v in cfg]
    parts.append('\n-- 系统配置 %d 组' % len(cfg_rows))
    parts.append(rows_to_sql('system_config', ['config_group', 'config_value', 'updated_by'], cfg_rows))

    with open(os.path.join(ROOT, 'seed.sql'), 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(parts) + '\n')

    # ---------------- Neo4j ----------------
    node_rows = []
    for e in entities:
        node_rows.append({
            'id': e['id'], 'name': e['name'], 'type': e['type'],
            'standardName': e.get('standardName') or e['name'],
            'aliases': e.get('aliases') or [],
            'diseases': e.get('diseases') or [],
            'status': e.get('status'), 'confidence': e.get('confidence') or 0.5,
            'source': e.get('source') or ''
        })
    edge_rows = []
    for r in relations:
        edge_rows.append({
            'id': r['id'], 'head': r['headId'], 'tail': r['tailId'],
            'relation': r['relation'], 'disease': r['disease'],
            'status': r.get('status'), 'confidence': r.get('confidence') or 0.5,
            'source': r.get('source') or '', 'snippet': r.get('snippet') or ''
        })

    def batches(rows, size=80):
        for i in range(0, len(rows), size):
            yield rows[i:i + size]

    cy = ['// 由 db/gen_seed.py 自动生成 —— 慢知知识图谱演示子集',
          '// 节点 %d 个、关系 %d 条' % (len(node_rows), len(edge_rows)), '']
    for b in batches(node_rows):
        cy.append('UNWIND ' + json.dumps(b, ensure_ascii=False) + ' AS row\n'
                  'MERGE (e:Entity {id: row.id})\n'
                  'SET e.name = row.name, e.type = row.type, e.standardName = row.standardName,\n'
                  '    e.aliases = row.aliases, e.diseases = row.diseases, e.status = row.status,\n'
                  '    e.confidence = row.confidence, e.source = row.source;')
        cy.append('')
    for b in batches(edge_rows):
        cy.append('UNWIND ' + json.dumps(b, ensure_ascii=False) + ' AS row\n'
                  'MATCH (h:Entity {id: row.head}), (t:Entity {id: row.tail})\n'
                  'MERGE (h)-[r:REL {id: row.id}]->(t)\n'
                  'SET r.relation = row.relation, r.disease = row.disease, r.status = row.status,\n'
                  '    r.confidence = row.confidence, r.source = row.source, r.snippet = row.snippet;')
        cy.append('')
    with open(os.path.join(ROOT, 'seed.cypher'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(cy))

    print('users', len(u_rows), 'documents', len(d_rows), 'chunks', len(c_rows),
          'entities', len(e_rows), 'relations', len(r_rows), 'review', len(rev_rows),
          'tasks', len(t_rows), 'logs', len(l_rows), 'sessions', len(s_rows))


if __name__ == '__main__':
    main()
