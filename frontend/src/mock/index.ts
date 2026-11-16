/**
 * Mock 数据服务层
 * ------------------------------------------------------------------
 * 与页面组件完全分离：所有页面只通过 `@/api` 调用，不直接 import 数据文件。
 * 数据来源：D:/毕业设计/开题答辩/数据包
 *   - 真实统计口径：PubMed 5026 篇 / MeSH 实体 4793 / 文献锚定三元组 36619 / 文本块 32078
 *   - 知识图谱演示子集：三高及关联疾病 264 实体 / 263 关系（基于国家级指南抽取）
 * 未来接入真实后端时，只需替换 `@/api/*` 中的实现，本目录可整体移除。
 */
import overviewRaw from './data/overview.json'
import entitiesRaw from './data/entities.json'
import relationsRaw from './data/relations.json'
import documentsRaw from './data/documents.json'
import chunksRaw from './data/chunks.json'
import pagerankRaw from './data/pagerank.json'
import usersRaw from './data/users.json'
import tasksRaw from './data/tasks.json'
import logsRaw from './data/logs.json'
import qaSessionsRaw from './data/qaSessions.json'
import yearlyRaw from './data/yearly.json'
import mlpRaw from './data/mlpTopics.json'
import diseaseAggRaw from './data/diseaseAgg.json'

export const overview: any = overviewRaw
export const entities: any[] = entitiesRaw as any
export const relations: any[] = relationsRaw as any
export const documents: any[] = documentsRaw as any
export const chunks: any[] = chunksRaw as any
export const pagerank: any[] = pagerankRaw as any
export const users: any[] = usersRaw as any
export const tasks: any[] = tasksRaw as any
export const logs: any[] = logsRaw as any
export const qaSessions: any[] = qaSessionsRaw as any
export const yearly: any = yearlyRaw
export const mlpTopics: any[] = mlpRaw as any
export const diseaseAgg: any[] = diseaseAggRaw as any

export const DISEASES = ['2型糖尿病', '高血压', '血脂异常', '冠心病', '脑卒中', '慢性肾脏病', '肥胖', '脂肪肝', '动脉粥样硬化']
export const ENTITY_TYPES = ['疾病', '症状', '危险因素', '并发症', '药物类别', '检查指标', '生活方式', '其他']
export const RELATION_TYPES = ['危险因素', '临床表现', '并发症', '常用药物', '监测指标', '干预措施', '共病', '导致', '关联疾病']
export const DOC_TYPES = ['临床指南', '专家共识', '研究论文', '综述', '其他']
export const DOC_SOURCES = ['PubMed', '本地指南文件', 'MedlinePlus']
export const REVIEW_STATUS = ['已审核', '待审核', '候选', '已驳回']

export const TYPE_COLOR: Record<string, string> = {
  疾病: '#DC2626',
  症状: '#F59E0B',
  危险因素: '#7C3AED',
  并发症: '#DB2777',
  药物类别: '#0891B2',
  检查指标: '#2563EB',
  生活方式: '#16A34A',
  其他: '#94A3B8'
}

export const RELATION_COLOR: Record<string, string> = {
  危险因素: '#7C3AED',
  临床表现: '#F59E0B',
  并发症: '#DB2777',
  常用药物: '#0891B2',
  监测指标: '#2563EB',
  干预措施: '#16A34A',
  共病: '#DC2626',
  导致: '#B91C1C',
  关联疾病: '#64748B'
}

const wait = (ms = 160) => new Promise((r) => setTimeout(r, ms))

export interface Paged<T> {
  list: T[]
  total: number
}

export function paginate<T>(arr: T[], page = 1, pageSize = 10): Paged<T> {
  const start = (page - 1) * pageSize
  return { list: arr.slice(start, start + pageSize), total: arr.length }
}

const has = (text: string, kw?: string) =>
  !kw || String(text || '').toLowerCase().includes(String(kw).toLowerCase())

/* ------------------------------- 统计 ------------------------------- */

export async function fetchOverview() {
  await wait(120)
  return overview
}

export async function fetchYearly() {
  await wait(80)
  return yearly
}

export async function fetchDiseaseAgg() {
  await wait(80)
  return diseaseAgg
}

export async function fetchSystemHealth() {
  await wait(200)
  return [
    { name: 'Neo4j 图数据库', value: '演示状态', ok: null, detail: '未接入真实实例，展示演示数据' },
    { name: 'Milvus 向量库', value: '演示状态', ok: null, detail: '未接入真实实例，展示演示数据' },
    { name: 'MySQL 业务库', value: '演示状态', ok: null, detail: '未接入真实实例，展示演示数据' },
    { name: 'GLM-4 模型服务', value: '未连接', ok: false, detail: '未配置 API Key' }
  ]
}

/* ------------------------------- 文献 ------------------------------- */

export interface DocQuery {
  keyword?: string
  disease?: string
  source?: string
  docType?: string
  status?: string
  year?: string
  page?: number
  pageSize?: number
}

export async function queryDocuments(q: DocQuery = {}): Promise<Paged<any>> {
  await wait()
  let list = documents.slice()
  if (q.keyword) list = list.filter((d) => has(d.title, q.keyword) || has(d.pmid, q.keyword) || has(d.journal, q.keyword))
  if (q.disease) list = list.filter((d) => d.disease === q.disease)
  if (q.source) list = list.filter((d) => d.source === q.source)
  if (q.docType) list = list.filter((d) => d.docType === q.docType)
  if (q.status) list = list.filter((d) => d.status === q.status)
  if (q.year) list = list.filter((d) => String(d.publishDate).startsWith(q.year!))
  return paginate(list, q.page || 1, q.pageSize || 10)
}

export function getDocument(id: string) {
  return documents.find((d) => d.id === id)
}

/** 按 300 字窗口 / 50 字重叠切分正文（与数据包 04_预处理中间产物 的切块策略一致） */
export function sliceChunks(doc: any, size = 300, overlap = 50) {
  const text = doc?.abstract || ''
  if (!text) return []
  const out: any[] = []
  let i = 0
  let idx = 0
  while (i < text.length && idx < 40) {
    out.push({
      id: `${doc.id}-C${idx}`,
      docId: doc.id,
      chunkIdx: idx,
      text: text.slice(i, i + size),
      textLen: Math.min(size, text.length - i)
    })
    if (i + size >= text.length) break
    i += size - overlap
    idx++
  }
  return out
}

export function getDocChunks(docId: string) {
  const real = chunks.filter((c) => c.docId === docId)
  if (real.length) return real
  return sliceChunks(getDocument(docId))
}

/* ------------------------------- 实体 ------------------------------- */

export interface EntityQuery {
  keyword?: string
  type?: string
  disease?: string
  status?: string
  page?: number
  pageSize?: number
}

export function entityStat() {
  const relCount: Record<string, number> = {}
  relations.forEach((r) => {
    relCount[r.headId] = (relCount[r.headId] || 0) + 1
    relCount[r.tailId] = (relCount[r.tailId] || 0) + 1
  })
  return relCount
}

const REL_COUNT = entityStat()

export function entityWithCount(e: any) {
  return { ...e, relCount: REL_COUNT[e.id] || 0 }
}

export async function queryEntities(q: EntityQuery = {}): Promise<Paged<any>> {
  await wait()
  let list = entities.map(entityWithCount)
  if (q.keyword) list = list.filter((e) => has(e.name, q.keyword) || e.aliases.some((a: string) => has(a, q.keyword)))
  if (q.type) list = list.filter((e) => e.type === q.type)
  if (q.disease) list = list.filter((e) => e.diseases.includes(q.disease))
  if (q.status) list = list.filter((e) => e.status === q.status)
  return paginate(list, q.page || 1, q.pageSize || 10)
}

export function getEntity(id: string) {
  return entities.find((e) => e.id === id)
}

/* ------------------------------- 关系 ------------------------------- */

export interface RelationQuery {
  keyword?: string
  relation?: string
  status?: string
  disease?: string
  page?: number
  pageSize?: number
}

export async function queryRelations(q: RelationQuery = {}): Promise<Paged<any>> {
  await wait()
  let list = relations.slice()
  if (q.keyword) list = list.filter((r) => has(r.head, q.keyword) || has(r.tail, q.keyword) || has(r.id, q.keyword))
  if (q.relation) list = list.filter((r) => r.relation === q.relation)
  if (q.status) list = list.filter((r) => r.status === q.status)
  if (q.disease) list = list.filter((r) => r.disease === q.disease)
  return paginate(list, q.page || 1, q.pageSize || 10)
}

export function getRelation(id: string) {
  return relations.find((r) => r.id === id)
}

export function relationsOf(entityId: string) {
  return relations.filter((r) => r.headId === entityId || r.tailId === entityId)
}

/* ------------------------------- 图谱 ------------------------------- */

export interface GraphQuery {
  disease?: string
  entityTypes?: string[]
  relationTypes?: string[]
  keyword?: string
  limit?: number
  statuses?: string[]
}

export function buildGraph(q: GraphQuery = {}) {
  const limit = q.limit || 120
  let rels = relations.slice()
  if (q.disease) rels = rels.filter((r) => r.disease === q.disease || r.head === q.disease || r.tail === q.disease)
  if (q.relationTypes?.length) rels = rels.filter((r) => q.relationTypes!.includes(r.relation))
  if (q.statuses?.length) rels = rels.filter((r) => q.statuses!.includes(r.status))
  if (q.keyword) {
    const hit = new Set(
      entities
        .filter((e) => has(e.name, q.keyword) || e.aliases.some((a: string) => has(a, q.keyword)))
        .map((e) => e.id)
    )
    rels = rels.filter((r) => hit.has(r.headId) || hit.has(r.tailId))
  }

  const nodeIds = new Set<string>()
  rels.forEach((r) => {
    nodeIds.add(r.headId)
    nodeIds.add(r.tailId)
  })
  if (q.disease) {
    const d = entities.find((e) => e.name === q.disease)
    if (d) nodeIds.add(d.id)
  }

  const nodes = entities
    .filter((e) => nodeIds.has(e.id))
    .filter((e) => !q.entityTypes?.length || q.entityTypes.includes(e.type))
    .slice(0, limit)
    .map((e) => {
      const isDisease = e.type === '疾病'
      const deg = REL_COUNT[e.id] || 1
      return {
        id: e.id,
        name: e.name,
        type: e.type,
        category: ENTITY_TYPES.indexOf(e.type),
        symbolSize: isDisease ? 30 + Math.min(10, deg * 0.35) : 8 + Math.min(14, Math.sqrt(deg) * 2.6),
        value: deg,
        itemStyle: { color: TYPE_COLOR[e.type] || '#94A3B8', borderColor: '#fff', borderWidth: 1.2 },
        label: { show: isDisease || deg > 18 }
      }
    })
  const keep = new Set(nodes.map((n) => n.id))
  const edges = rels
    .filter((r) => keep.has(r.headId) && keep.has(r.tailId))
    .map((r) => ({
      id: r.id,
      source: r.headId,
      target: r.tailId,
      name: r.relation,
      value: r.confidence,
      relation: r.relation,
      status: r.status,
      lineStyle: { color: RELATION_COLOR[r.relation] || '#CBD5E1', width: r.relation === '导致' ? 2 : 1.2, curveness: 0.08 },
      label: { show: false, formatter: r.relation }
    }))
  return { nodes, edges }
}

/** 将疾病节点均匀固定在圆环上，避免力导向布局把高连接度疾病挤在中心 */
export function pinDiseases(nodes: any[], radius = 130) {
  const ds = nodes.filter((n) => n.type === '疾病')
  ds.forEach((n, i) => {
    const a = (Math.PI * 2 * i) / Math.max(1, ds.length) - Math.PI / 2
    n.x = Math.cos(a) * radius
    n.y = Math.sin(a) * radius
    n.fixed = true
    n.label = { ...(n.label || {}), show: true, position: 'right', fontSize: 11, fontWeight: 600, color: '#173B70' }
  })
  return nodes
}

/**
 * 按跳数分层的同心圆布局：中心节点在圆心，第 k 跳节点落在第 k 层圆环上，
 * 同一父节点的子节点聚集在其角度扇区内，避免力导向布局出现长边穿插与标签堆叠。
 */
function radialPositions(nodes: any[], edges: any[], centerId: string) {
  const adj: Record<string, string[]> = {}
  edges.forEach((e) => {
    ;(adj[e.source] = adj[e.source] || []).push(e.target)
    ;(adj[e.target] = adj[e.target] || []).push(e.source)
  })
  const depth: Record<string, number> = { [centerId]: 0 }
  const parent: Record<string, string> = {}
  let frontier = [centerId]
  while (frontier.length) {
    const next: string[] = []
    frontier.forEach((id) => {
      ;(adj[id] || []).forEach((o) => {
        if (depth[o] === undefined) {
          depth[o] = depth[id] + 1
          parent[o] = id
          next.push(o)
        }
      })
    })
    frontier = next
  }
  const maxD = Math.max(1, ...Object.values(depth))
  const angle: Record<string, number> = { [centerId]: 0 }
  const levels: string[][] = []
  for (let d = 1; d <= maxD; d++) levels[d] = nodes.filter((n) => depth[n.id] === d).map((n) => n.id)
  const typeOf: Record<string, string> = {}
  nodes.forEach((n) => (typeOf[n.id] = n.type))

  /** 贪心角度分配：按偏好角排序后强制最小间隔，避免同层节点叠在一起 */
  const spread = (items: { id: string; pref: number }[], minGap: number) => {
    const n = items.length
    if (!n) return
    const gap = Math.min(minGap, (Math.PI * 2) / n)
    const sorted = items.slice().sort((a, b) => a.pref - b.pref)
    const out = sorted.map((i) => i.pref)
    for (let i = 1; i < n; i++) out[i] = Math.max(out[i], out[i - 1] + gap)
    const span = Math.PI * 2 - gap
    const used = out[n - 1] - out[0]
    if (used > span) {
      const k = span / (used || 1)
      for (let i = 0; i < n; i++) out[i] = out[0] + (out[i] - out[0]) * k
    }
    sorted.forEach((it, i) => (angle[it.id] = out[i]))
  }

  // 第 1 跳：疾病节点优先均匀铺开，其余节点填入空隙
  const lv1 = levels[1] || []
  const dis1 = lv1.filter((id) => typeOf[id] === '疾病')
  const oth1 = lv1.filter((id) => typeOf[id] !== '疾病')
  dis1.forEach((id, i) => (angle[id] = -Math.PI / 2 + (Math.PI * 2 * i) / Math.max(1, dis1.length)))
  if (dis1.length && oth1.length) {
    const step = (Math.PI * 2) / dis1.length
    oth1.forEach((id, i) => {
      const base = angle[dis1[i % dis1.length]]
      const k = Math.floor(i / dis1.length) + 1
      angle[id] = base + (step * k) / (Math.ceil(oth1.length / dis1.length) + 1)
    })
  } else {
    lv1.forEach((id, i) => (angle[id] = -Math.PI / 2 + (Math.PI * 2 * i) / Math.max(1, lv1.length)))
  }

  // 第 2 跳及以后：子节点向父节点角度靠拢，再用最小间隔拉开
  for (let d = 2; d <= maxD; d++) {
    const items = levels[d].map((id) => ({ id, pref: angle[parent[id]] ?? 0 }))
    spread(items, d === 2 ? 0.11 : 0.14)
  }

  const ry = (d: number) => Math.max(138, (250 * d) / maxD)
  const pos: Record<string, { x: number; y: number; angle: number; depth: number }> = {}
  nodes.forEach((n) => {
    const d = depth[n.id] ?? maxD
    if (d === 0) {
      pos[n.id] = { x: 0, y: 0, angle: 0, depth: 0 }
      return
    }
    const a = angle[n.id] ?? 0
    const r = ry(d) * (1 + ((n.id.length % 3) - 1) * 0.05)
    pos[n.id] = { x: Math.cos(a) * r * 1.42, y: Math.sin(a) * r, angle: a, depth: d }
  })
  return pos
}

/** 疾病关联网络：以中心疾病为核心，向外扩展 1~2 跳 */
export function buildDiseaseNetwork(center: string, relationTypes: string[] = [], hops = 2) {
  const start = entities.find((e) => e.name === center)
  if (!start) return { nodes: [], edges: [] }
  const visited = new Set<string>([start.id])
  let frontier = [start.id]
  const usedRels: any[] = []
  for (let h = 0; h < hops; h++) {
    const next: string[] = []
    frontier.forEach((nid) => {
      relations.forEach((r) => {
        if (relationTypes.length && !relationTypes.includes(r.relation)) return
        let other = ''
        if (r.headId === nid) other = r.tailId
        else if (r.tailId === nid) other = r.headId
        else return
        usedRels.push(r)
        if (!visited.has(other)) {
          visited.add(other)
          next.push(other)
        }
      })
    })
    frontier = next
  }
  const uniq = new Map(usedRels.map((r) => [r.id, r]))
  const rels = Array.from(uniq.values()).filter((r) => visited.has(r.headId) && visited.has(r.tailId))
  const nodes = entities
    .filter((e) => visited.has(e.id))
    .map((e) => {
      const isCenter = e.id === start.id
      const isDisease = e.type === '疾病'
      const deg = REL_COUNT[e.id] || 1
      return {
        id: e.id,
        name: e.name,
        type: e.type,
        category: ENTITY_TYPES.indexOf(e.type),
        symbolSize: isCenter ? 58 : isDisease ? 34 : 12 + Math.min(18, Math.sqrt(deg) * 3),
        value: deg,
        isCenter,
        itemStyle: {
          color: TYPE_COLOR[e.type] || '#94A3B8',
          borderColor: isCenter ? '#173B70' : '#fff',
          borderWidth: isCenter ? 4 : 1.5
        },
        label: { show: isCenter || isDisease || deg > 14 }
      }
    })
  const edges = rels.map((r) => ({
    id: r.id,
    source: r.headId,
    target: r.tailId,
    name: r.relation,
    relation: r.relation,
    status: r.status,
    value: r.confidence,
    lineStyle: {
      color: RELATION_COLOR[r.relation] || '#CBD5E1',
      width: r.relation === '导致' ? 2.2 : 1.1,
      curveness: 0.06
    },
    label: { show: false, formatter: r.relation }
  }))
  const pos = radialPositions(nodes, edges, start.id)
  nodes.forEach((n: any) => {
    const p = pos[n.id]
    if (!p) return
    n.x = p.x
    n.y = p.y
    n.depth = p.depth
    if (p.depth === 0) {
      n.label = { ...n.label, position: 'bottom', fontSize: 12, fontWeight: 700, color: '#173B70' }
      return
    }
    const c = Math.cos(p.angle)
    const position = c > 0.34 ? 'right' : c < -0.34 ? 'left' : p.angle < 0 ? 'top' : 'bottom'
    n.label = {
      ...n.label,
      position,
      fontSize: 10.5,
      fontWeight: n.type === '疾病' ? 600 : 400,
      color: n.type === '疾病' ? '#173B70' : '#4B5563'
    }
  })
  return { nodes, edges }
}

/** 两实体间最短关联路径（BFS，仅使用图谱中真实存在的关系） */
export function shortestPath(fromName: string, toName: string, maxLen = 4) {
  const from = entities.find((e) => e.name === fromName)
  const to = entities.find((e) => e.name === toName)
  if (!from || !to) return null
  const adj: Record<string, any[]> = {}
  relations.forEach((r) => {
    ;(adj[r.headId] = adj[r.headId] || []).push({ to: r.tailId, rel: r, dir: 'out' })
    ;(adj[r.tailId] = adj[r.tailId] || []).push({ to: r.headId, rel: r, dir: 'in' })
  })
  const queue: any[] = [{ id: from.id, path: [], depth: 0 }]
  const seen = new Set<string>([from.id])
  while (queue.length) {
    const cur = queue.shift()
    if (cur.id === to.id) {
      return cur.path.map((step: any) => ({
        from: getEntity(step.rel.headId),
        to: getEntity(step.rel.tailId),
        relation: step.rel.relation,
        rel: step.rel
      }))
    }
    if (cur.depth >= maxLen) continue
    for (const edge of adj[cur.id] || []) {
      if (seen.has(edge.to)) continue
      seen.add(edge.to)
      queue.push({ id: edge.to, path: [...cur.path, edge], depth: cur.depth + 1 })
    }
  }
  return null
}

/* ------------------------------- 用户 / 任务 / 日志 ------------------------------- */

export async function queryUsers(q: any = {}): Promise<Paged<any>> {
  await wait()
  let list = users.slice()
  if (q.keyword) list = list.filter((u) => has(u.name, q.keyword) || has(u.account, q.keyword) || has(u.id, q.keyword))
  if (q.role) list = list.filter((u) => u.role === q.role)
  if (q.status) list = list.filter((u) => u.status === q.status)
  return paginate(list, q.page || 1, q.pageSize || 10)
}

export async function queryTasks(q: any = {}): Promise<Paged<any>> {
  await wait()
  let list = tasks.slice()
  if (q.keyword) list = list.filter((t) => has(t.name, q.keyword) || has(t.id, q.keyword))
  if (q.status) list = list.filter((t) => t.status === q.status)
  if (q.source) list = list.filter((t) => t.source === q.source)
  return paginate(list, q.page || 1, q.pageSize || 10)
}

export async function queryLogs(q: any = {}): Promise<Paged<any>> {
  await wait()
  let list = logs.slice()
  if (q.keyword) list = list.filter((l) => has(l.action, q.keyword) || has(l.user, q.keyword) || has(l.id, q.keyword))
  if (q.module) list = list.filter((l) => l.module === q.module)
  if (q.user) list = list.filter((l) => l.user === q.user)
  if (q.result) list = list.filter((l) => l.result === q.result)
  return paginate(list, q.page || 1, q.pageSize || 10)
}

/* ------------------------------- 智能问答 ------------------------------- */

export interface QaIntent {
  key: string
  label: string
  keywords: string[]
  diseases: string[]
  paragraphs: string[]
  pathPairs: [string, string, string][]
  docFilters: { disease?: string; titleKw?: string; mesh?: string }[]
  followups: string[]
}

export const QA_INTENTS: QaIntent[] = [
  {
    key: 'dm-htn',
    label: '疾病关联查询',
    keywords: ['糖尿病', '高血压', '关联', '关系', '共病'],
    diseases: ['2型糖尿病', '高血压'],
    paragraphs: [
      '2 型糖尿病与高血压在临床上高度共存，二者共享胰岛素抵抗、超重与肥胖、缺乏身体活动等病理生理基础，属于典型的代谢性共病组合。',
      '从知识图谱看，两条主线相互连接：①「肥胖 → 危险因素 → 2 型糖尿病」与「肥胖 → 危险因素 → 高血压」形成共同上游；②「2 型糖尿病 → 共病 → 高血压」为直接共病关系，且两者均「导致」冠心病、脑卒中与慢性肾脏病。',
      '管理层面，指南强调对糖尿病患者应常规监测血压（目标一般 < 130/80 mmHg），对高血压患者应筛查空腹血糖与糖化血红蛋白；降压药物选择需考虑糖代谢影响，ACEI/ARB 对合并蛋白尿者具有肾脏保护作用。',
      '提示：以上为知识层面的关联梳理，不构成个体化诊疗建议，具体方案需由临床医师制定。'
    ],
    pathPairs: [
      ['2型糖尿病', '共病', '高血压'],
      ['肥胖', '危险因素', '2型糖尿病'],
      ['高血压', '导致', '冠心病']
    ],
    docFilters: [{ disease: '2型糖尿病' }, { disease: '高血压' }],
    followups: ['糖尿病患者的血压控制目标是多少？', '两者共同的危险因素有哪些？']
  },
  {
    key: 'htn-risk',
    label: '危险因素查询',
    keywords: ['高血压', '危险因素', '原因', '诱因'],
    diseases: ['高血压'],
    paragraphs: [
      '高血压的危险因素可分为不可干预与可干预两类。不可干预因素包括年龄增长与高血压家族史；可干预因素是高钠低钾饮食、超重与肥胖、过量饮酒、吸烟、缺乏身体活动、长期精神紧张及睡眠呼吸暂停综合征。',
      '在我国人群中，高钠低钾膳食是最重要的环境危险因素之一，24 小时尿钠与血压水平呈正相关；体重指数每增加 3 kg/m²，高血压发生风险显著上升。',
      '图谱中「高血压 → 危险因素 → 高钠低钾饮食 / 超重与肥胖 / 过量饮酒 / 长期精神紧张」等关系均标注了指南来源，可在关系审核页面查看原文证据片段。',
      '干预优先级：限盐（< 5 g/d）、减重、规律有氧运动、限酒戒烟、心理平衡。'
    ],
    pathPairs: [
      ['高血压', '危险因素', '高钠低钾饮食'],
      ['高血压', '危险因素', '超重与肥胖'],
      ['高血压', '危险因素', '睡眠呼吸暂停综合征']
    ],
    docFilters: [{ disease: '高血压', titleKw: 'risk' }, { disease: '高血压' }],
    followups: ['高血压患者需要监测哪些指标？', '家庭自测血压的正确做法']
  },
  {
    key: 'lipid-chd',
    label: '疾病关联查询',
    keywords: ['血脂', '胆固醇', 'LDL', '冠心病', '动脉粥样硬化'],
    diseases: ['血脂异常', '冠心病', '动脉粥样硬化'],
    paragraphs: [
      '血脂异常与冠心病之间的核心链条是「LDL-C 升高 → 动脉粥样硬化 → 冠心病」。LDL-C 是动脉粥样硬化性心血管病（ASCVD）的致病性危险因素，其累积暴露量（水平 × 时间）决定斑块负荷。',
      '图谱中的证据链为：「血脂异常 → 导致 → 动脉粥样硬化」→「动脉粥样硬化 → 导致 → 冠心病」，同时「血脂异常 → 危险因素」指向高脂饮食、超重与肥胖、遗传性脂质代谢异常。',
      '干预上以降低 LDL-C 为核心目标，他汀类是基础用药；对他汀不耐受或未达标者可联合胆固醇吸收抑制剂或 PCSK9 抑制剂。生活方式上需控制饱和脂肪摄入、增加膳食纤维、规律运动与减重。',
      '不同危险分层对应不同 LDL-C 目标值，具体目标需结合 ASCVD 风险分层判断。'
    ],
    pathPairs: [
      ['血脂异常', '导致', '动脉粥样硬化'],
      ['动脉粥样硬化', '导致', '冠心病'],
      ['血脂异常', '监测指标', '低密度脂蛋白胆固醇(LDL-C)']
    ],
    docFilters: [{ disease: '血脂异常', titleKw: 'LDL' }, { disease: '血脂异常' }],
    followups: ['LDL-C 控制目标是多少？', '他汀类药物属于哪一类治疗？']
  },
  {
    key: 'dm-complication',
    label: '并发症查询',
    keywords: ['并发症', '糖尿病', '肾病', '视网膜', '神经病变', '糖尿病足'],
    diseases: ['2型糖尿病', '慢性肾脏病'],
    paragraphs: [
      '2 型糖尿病的慢性并发症以微血管与大血管病变为主。微血管并发症包括糖尿病肾病、糖尿病视网膜病变、糖尿病周围神经病变；大血管并发症包括冠心病、脑卒中与外周动脉疾病；糖尿病足则是神经病变、缺血与感染共同作用的结果。',
      '图谱中「2 型糖尿病 → 并发症 → 糖尿病肾病 / 糖尿病视网膜病变 / 糖尿病周围神经病变 / 糖尿病足」均来自指南抽取，其中糖尿病肾病同时与「慢性肾脏病」形成跨疾病关联。',
      '筛查建议：确诊时即应评估尿微量白蛋白/肌酐比值（UACR）与 eGFR，此后每年至少复查一次；眼底检查与足部检查同样建议每年进行。',
      '并发症风险与血糖控制水平、病程、血压及血脂密切相关，综合管理优于单纯降糖。'
    ],
    pathPairs: [
      ['2型糖尿病', '并发症', '糖尿病肾病'],
      ['2型糖尿病', '并发症', '糖尿病视网膜病变'],
      ['2型糖尿病', '导致', '慢性肾脏病']
    ],
    docFilters: [{ disease: '2型糖尿病', titleKw: 'complication' }, { disease: '2型糖尿病' }],
    followups: ['糖尿病肾病的早期筛查指标', '2型糖尿病与高血压有哪些关联？']
  },
  {
    key: 'ldl-target',
    label: '指标查询',
    keywords: ['目标', 'LDL-C', '控制目标', '多少'],
    diseases: ['血脂异常'],
    paragraphs: [
      'LDL-C 目标值按 ASCVD 危险分层设定：低危人群 < 3.4 mmol/L；中危/高危人群 < 2.6 mmol/L；极高危人群 < 1.8 mmol/L 且较基线下降 ≥ 50%；超高危人群 < 1.4 mmol/L 且较基线下降 ≥ 50%。',
      '图谱中「血脂异常 → 监测指标 → 低密度脂蛋白胆固醇(LDL-C)」记录了该指标的监测关系，可在实体管理中查看其标准名称、别名（LDL-C）与来源。',
      '降脂治疗需在生活方式干预基础上进行，并于用药后 4~6 周复查血脂、肝功能与肌酶，达标后每 3~6 个月复查一次。'
    ],
    pathPairs: [['血脂异常', '监测指标', '低密度脂蛋白胆固醇(LDL-C)']],
    docFilters: [{ disease: '血脂异常', titleKw: 'LDL' }],
    followups: ['甘油三酯升高如何干预？', '血脂异常与冠心病之间有什么联系？']
  },
  {
    key: 'obesity',
    label: '危险因素查询',
    keywords: ['肥胖', '超重', '体重', 'BMI'],
    diseases: ['肥胖', '2型糖尿病', '高血压'],
    paragraphs: [
      '超重与肥胖是多种慢性病共同的 upstream 危险因素。图谱中「肥胖 → 危险因素 → 2 型糖尿病 / 高血压 / 血脂异常」以及「肥胖 → 并发症 → 脂肪肝 / 睡眠呼吸暂停综合征」构成以肥胖为中心的关联子网。',
      '评价指标包括体重指数（BMI）与腰围：我国成人 BMI ≥ 24 为超重、≥ 28 为肥胖；男性腰围 ≥ 90 cm、女性 ≥ 85 cm 提示中心性肥胖。',
      '干预以生活方式为基础：控制总能量摄入、增加有氧运动、行为干预；必要时在医师指导下考虑药物治疗。'
    ],
    pathPairs: [
      ['肥胖', '危险因素', '2型糖尿病'],
      ['肥胖', '危险因素', '高血压'],
      ['肥胖', '并发症', '脂肪肝']
    ],
    docFilters: [{ disease: '2型糖尿病', titleKw: 'obesity' }, { disease: '高血压' }],
    followups: ['肥胖会增加哪些慢性病风险？', '高血压的主要危险因素有哪些？']
  }
]

function scoreDoc(doc: any, f: { disease?: string; titleKw?: string; mesh?: string }) {
  let s = 0
  if (f.disease && doc.disease === f.disease) s += 3
  if (f.titleKw && has(doc.title, f.titleKw)) s += 4
  if (f.mesh && (doc.mesh || []).some((m: string) => has(m, f.mesh))) s += 2
  if (doc.source === 'PubMed') s += 1
  return s
}

export function pickDocs(filters: { disease?: string; titleKw?: string; mesh?: string }[], n = 4) {
  const pool = documents.filter((d) => d.source === 'PubMed' && d.abstract)
  const scored = pool
    .map((d) => ({ d, s: filters.reduce((acc, f) => acc + scoreDoc(d, f), 0) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
  return scored.slice(0, n).map((x) => x.d)
}

export function pickChunks(intent: QaIntent, n = 4) {
  let list = chunks.filter((c) => intent.diseases.includes(c.disease))
  if (list.length < n) list = chunks.slice(0, n)
  return list.slice(0, n).map((c, i) => ({
    ...c,
    score: +(0.92 - i * 0.06).toFixed(3),
    doc: getDocument(c.docId)
  }))
}

export interface AskResult {
  intent: QaIntent
  steps: { name: string; detail: string; ms: number; extra?: string }[]
  citations: any[]
  chunks: any[]
  path: any[]
  related: string[]
}

export async function askQuestion(question: string): Promise<AskResult> {
  await wait(700)
  const q = question || ''
  let best = QA_INTENTS.find((it) => it.keywords.every((k) => has(q, k)))
  if (!best) {
    let maxHit = 0
    QA_INTENTS.forEach((it) => {
      const hit = it.keywords.filter((k) => has(q, k)).length
      if (hit > maxHit) {
        maxHit = hit
        best = it
      }
    })
  }
  const intent = best || QA_INTENTS[0]
  const citations = pickDocs(intent.docFilters, 4).map((d, i) => ({ ...d, citeNo: i + 1 }))
  const path = intent.pathPairs
    .map(([a, rel, b]) => {
      const r = relations.find((x) => x.head === a && x.relation === rel && x.tail === b)
      return r ? { head: a, relation: rel, tail: b, rel: r } : null
    })
    .filter(Boolean)
  const steps = [
    { name: '问题意图识别', detail: `识别为「${intent.label}」，目标疾病：${intent.diseases.join('、')}`, ms: 62, extra: intent.label },
    { name: '知识检索', detail: `图谱检索命中 ${path.length * 3 + 4} 个实体关系；BM25 召回 40 篇；BGE-M3 向量召回 Top-20`, ms: 284, extra: '图谱 + BM25 + 向量' },
    { name: '检索融合', detail: 'RRF（k=60）融合三路召回结果，保留 Top-10', ms: 41, extra: 'RRF' },
    { name: '重排序', detail: 'bge-reranker-large 精排，保留 Top-5 证据片段', ms: 176, extra: 'Reranker' },
    { name: '答案生成', detail: '基于证据片段生成回答并绑定引用序号（演示环境使用预设模板，未调用真实 GLM-4）', ms: 512, extra: 'GLM-4（模拟）' }
  ]
  return { intent, steps, citations, chunks: pickChunks(intent, 4), path, related: intent.diseases }
}
