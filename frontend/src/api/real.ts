/**
 * 真实后端适配层
 * ------------------------------------------------------------------
 * 把 Flask 接口的返回结构，转成页面已经在用的数据结构。
 * 形状转换全部收敛在这个文件里，页面只做必要的异步改造。
 *
 * 已接真接口：问答、知识图谱、系统健康、总览统计
 * 仍走 mock：文献、审核、用户、日志等（后端接口尚未补齐）
 */
import http from './request'
import { ENTITY_TYPES, TYPE_COLOR, RELATION_COLOR } from '@/mock'

type Envelope<T> = { code: number; message: string; data: T }

async function unwrap<T = any>(p: Promise<any>): Promise<T> {
  const body = (await p) as Envelope<T>
  if (!body || body.code !== 0) {
    throw new Error(body?.message || '接口返回异常')
  }
  return body.data
}

/* ---------------------------------------------------------------- 系统 */

export function fetchSystemHealthRaw() {
  return unwrap(http.get('/system/health'))
}

/** 服务健康：页面按数组渲染 [{name,value,ok,detail}] */
export async function fetchSystemHealth() {
  const d: any = await unwrap(http.get('/system/health'))
  const okLlm = !!d.llm?.configured
  return [
    { name: 'Neo4j 图数据库', value: '已导入', ok: true,
      detail: '32,091 节点 / 288,064 关系（LOAD CSV 导入）' },
    { name: 'MySQL 业务库', value: '正常', ok: true,
      detail: `${d.chunks_indexed} 切块 / ${d.entities_indexed} 实体 / ${d.aliases_indexed} 别名` },
    { name: 'TF-IDF 检索索引', value: '已加载', ok: true,
      detail: `构建于 ${d.built_at || '—'}` },
    { name: 'GLM-4 模型服务', value: okLlm ? '已连接' : '未配置', ok: okLlm,
      detail: okLlm ? `${d.llm.model}（${d.llm.key_hint}）` : '未配置 LLM_API_KEY，回退图谱模板' }
  ]
}

/** 总览：后端统计口径 → 首页卡片字段 */
export async function fetchOverview() {
  const d: any = await unwrap(http.get('/stats/overview'))
  const st: Record<string, number> = {}
  for (const r of d.relation_status || []) st[r.status] = r.cnt
  return {
    dataSnapshotAt: d.data_snapshot_at ? String(d.data_snapshot_at).slice(0, 10) : '—',
    entityTotal: d.entities,
    entityMeshTotal: d.entities,
    tripleTotal: d.relations,
    chunkTotal: d.chunks,
    charTotal: Number(d.char_total) || 0,
    docTotal: d.documents,
    docWithAbstract: d.doc_with_abstract,
    journalTotal: d.journal_total,
    mlpTopicTotal: 31,
    avgMesh: 0,
    kgApproved: st['已审核'] || 0,
    kgPending: st['待审核'] || 0,
    kgCandidate: st['候选'] || 0,
    diseaseCount: Object.fromEntries((d.by_disease || []).map((r: any) => [r.disease, r.cnt])),
    yearCount: Object.fromEntries((d.by_year || []).map((r: any) => [String(r.year), r.cnt])),
    bySource: d.by_source || [],
    byDisease: d.by_disease || [],
    entityTypes: d.entity_types || [],
    relationTypes: d.relation_types || [],
    llm: d.llm,
    raw: d
  }
}

export async function fetchYearly() {
  return unwrap(http.get('/stats/yearly'))
}

export async function fetchDiseaseAgg() {
  return unwrap(http.get('/stats/disease'))
}

/* ---------------------------------------------------------------- 图谱 */

/** 后端实体类型 → 前端分类。两边枚举不完全一致，必须映射，否则 category 会是 -1 */
const TYPE_MAP: Record<string, string> = {
  疾病: '疾病',
  症状: '症状',
  危险因素: '危险因素',
  并发症: '并发症',
  药物: '药物类别',
  检查: '检查指标',
  指标: '检查指标',
  科室: '其他',
  其他: '其他'
}

/** 屏幕上能看清的节点上限。再多标签就会糊成一片。 */
const MAX_NODES = 28

export async function buildGraph(q: any = {}) {
  // 图谱可视化默认走演示库：264 实体 / 263 关系，是人工整理过的疾病子图，
  // 真实库的 OpenCMKG 有 3 万实体但噪声多，画出来全是「老年肺炎」这类边缘词。
  const entity = q.disease || q.keyword || q.entity || '2型糖尿病'
  const depth = q.depth ?? 1
  const d: any = await unwrap(
    http.get('/kg/graph', {
      params: { entity, depth, limit: q.limit ?? 55, source: q.source || 'demo' }
    })
  )

  const allNodes: any[] = d.nodes || []
  const allLinks: any[] = d.links || []
  if (!allNodes.length) return { nodes: [], edges: [], real: true }

  // 度数：既决定节点大小，也用来筛掉噪声
  const deg: Record<string, number> = {}
  for (const l of allLinks) {
    deg[l.source] = (deg[l.source] || 0) + 1
    deg[l.target] = (deg[l.target] || 0) + 1
  }

  // OpenCMKG 里有大量只出现一次的实体（老年肺炎、肠道菌群失调症…），
  // 先按「全局关联数」再按「子图内度数」排序，能把糖尿病肾病这类核心概念排到前面。
  const center = allNodes.find((n) => n.depth === 0) || allNodes[0]
  let keep = allNodes
  if (allNodes.length > MAX_NODES) {
    const rest = allNodes
      .filter((n) => n.id !== center.id)
      .sort(
        (a, b) =>
          (b.rel_count || 0) - (a.rel_count || 0) || (deg[b.id] || 0) - (deg[a.id] || 0)
      )
      .slice(0, MAX_NODES - 1)
    keep = [center, ...rest]
  }
  const keepIds = new Set(keep.map((n) => n.id))
  const links = allLinks.filter((l) => keepIds.has(l.source) && keepIds.has(l.target))

  // 一跳子图是标准星形，等角分布比力导向干净得多；
  // 两跳以上结构复杂，交给力导向自己排。
  const star = depth <= 1
  const leaves = keep.filter((n) => n.id !== center.id)
  const radius = 100 + leaves.length * 2.2
  const posOf: Record<string, { x: number; y: number; side: 'left' | 'right' }> = {}
  leaves.forEach((n, i) => {
    const a = (Math.PI * 2 * i) / Math.max(1, leaves.length) - Math.PI / 2
    posOf[n.id] = {
      x: Math.cos(a) * radius,
      y: Math.sin(a) * radius,
      side: Math.cos(a) >= 0 ? 'right' : 'left'
    }
  })

  const nodes = keep.map((n: any) => {
    const cat = TYPE_MAP[n.type] || '其他'
    const dd = deg[n.id] || 1
    const isCenter = n.id === center.id
    const pos = star ? (isCenter ? { x: 0, y: 0, side: 'right' as const } : posOf[n.id]) : null
    return {
      id: n.id,
      name: n.name,
      type: cat,
      category: ENTITY_TYPES.indexOf(cat),
      symbolSize: isCenter ? 34 : 9 + Math.min(9, Math.sqrt(dd) * 2.2),
      value: dd,
      itemStyle: { color: TYPE_COLOR[cat] || '#94A3B8', borderColor: '#fff', borderWidth: 1.2 },
      label: { show: true, position: pos?.side || 'right' },
      ...(pos ? { x: pos.x, y: pos.y, fixed: true } : {})
    }
  })

  const nameOf: Record<string, string> = {}
  for (const n of allNodes) nameOf[n.id] = n.name

  const edges = links.map((l: any, i: number) => ({
    id: `${l.source}-${l.relation}-${l.target}-${i}`,
    source: l.source,
    target: l.target,
    name: l.relation,
    value: 0.9,
    relation: l.relation,
    status: '已审核',
    sourceName: nameOf[l.source],
    targetName: nameOf[l.target],
    lineStyle: {
      color: RELATION_COLOR[l.relation] || '#CBD5E1',
      width: l.relation === '导致' ? 2 : 1.2,
      curveness: 0.06
    },
    label: { show: false, formatter: l.relation }
  }))

  // real 标记用于让页面跳过 mock 专用的 pinDiseases 布局
  return { nodes, edges, real: true }
}

/* ---------------------------------------------------------------- 文献 */

function toDoc(r: any) {
  return {
    id: r.id,
    pmid: r.pmid,
    title: r.title,
    journal: r.journal,
    docType: r.doc_type || '研究论文',
    disease: r.disease,
    source: r.source,
    publishDate: r.publish_date ? String(r.publish_date).slice(0, 10) : '—',
    collectedAt: r.collected_at ? String(r.collected_at).slice(0, 10) : '—',
    chunkCount: r.chunk_count || 0,
    doi: r.doi,
    url: r.url,
    authors: r.authors || '—',
    status: r.status || '已入库',
    abstract: r.abstract_brief || r.abstract || ''
  }
}

export async function queryDocuments(q: any = {}) {
  const d: any = await unwrap(
    http.get('/docs/search', {
      params: {
        keyword: q.keyword || undefined,
        disease: q.disease || undefined,
        source: q.source || undefined,
        docType: q.docType || undefined,
        year: q.year || undefined,
        page: q.page || 1,
        pageSize: q.pageSize || 10
      }
    })
  )
  return { list: (d.list || []).map(toDoc), total: d.total }
}

/** 文献详情 + 文本块 */
export async function fetchDocDetail(id: string) {
  const d: any = await unwrap(http.get(`/docs/${id}`))
  return { doc: toDoc(d), chunks: (d.chunks || []).map((c: any) => ({
    id: c.id, docId: id, chunkIdx: c.chunk_idx, text: c.text, textLen: c.text_len
  })) }
}

/* ---------------------------------------------------------------- 实体 */

function toEntity(r: any) {
  return {
    id: r.id,
    name: r.name,
    type: TYPE_MAP[r.type] || r.type,
    aliases: r.aliases ? String(r.aliases).split(/[,，;；]/).filter(Boolean) : [],
    diseases: r.diseases ? String(r.diseases).split(/[,，;；]/).filter(Boolean) : [],
    status: r.status || '已审核',
    confidence: Number(r.confidence) || 0.9,
    relCount: r.rel_count || 0,
    standardName: r.standard_name || r.name,
    source: r.source || 'OpenCMKG'
  }
}

export async function queryEntities(q: any = {}) {
  const d: any = await unwrap(
    http.get('/kg/entities', {
      params: {
        keyword: q.keyword || undefined,
        type: q.type || undefined,
        page: q.page || 1,
        pageSize: q.pageSize || 10
      }
    })
  )
  return { list: (d.list || []).map(toEntity), total: d.total }
}

export async function fetchEntityRelations(id: string, name?: string) {
  const d: any = await unwrap(
    http.get('/kg/relations', { params: { entity: name || id, pageSize: 60 } })
  )
  return (d.list || []).map((r: any) => ({
    id: r.id,
    headId: r.headId,
    tailId: r.tailId,
    headName: r.headName,
    tailName: r.tailName,
    relation: r.relation,
    name: r.relation,
    status: r.status,
    confidence: r.confidence,
    source: r.source
  }))
}

/* ---------------------------------------------------------------- 关联分析 */

/** 最短路径：后端返回 [{node, relation, rel}]，页面要 [{from, relation, rel, to}] */
export async function shortestPath(from: string, to: string, maxLen = 3) {
  const d: any = await unwrap(
    http.get('/analysis/path', { params: { from, to, maxLen } })
  )
  if (!d.found || !d.path?.length) return null
  const steps: any[] = []
  for (let i = 1; i < d.path.length; i++) {
    const prev = d.path[i - 1].node
    const cur = d.path[i]
    steps.push({
      from: prev,
      relation: cur.relation,
      rel: {
        source: cur.rel?.source || 'OpenCMKG',
        section: cur.rel?.section || '',
        evidenceLevel: cur.rel?.evidenceLevel || '图谱关系',
        confidence: cur.rel?.confidence ?? 0.9,
        snippet: cur.rel?.snippet || '该关系由知识图谱抽取得到。'
      },
      to: cur.node
    })
  }
  return steps
}

/** 疾病关联网络：后端 {center,nodes,links} → ECharts 图 */
export async function buildDiseaseNetwork(center: string, relationTypes: string[] = [], hops = 2) {
  const d: any = await unwrap(
    http.get('/analysis/network', { params: { entity: center, depth: Math.min(hops, 3) } })
  )
  const links = (d.links || []).filter(
    (l: any) => !relationTypes.length || relationTypes.includes(l.relation)
  )
  const keep = new Set<string>()
  for (const l of links) {
    keep.add(String(l.source))
    keep.add(String(l.target))
  }
  if (d.center) keep.add(String(d.center.id))

  const deg: Record<string, number> = {}
  for (const l of links) {
    deg[l.source] = (deg[l.source] || 0) + 1
    deg[l.target] = (deg[l.target] || 0) + 1
  }

  const nodes = (d.nodes || [])
    .filter((n: any) => keep.has(String(n.id)))
    .map((n: any) => {
      const cat = TYPE_MAP[n.type] || '其他'
      const isCenter = d.center && n.id === d.center.id
      const dd = deg[n.id] || 1
      return {
        id: n.id,
        name: n.name,
        type: cat,
        category: ENTITY_TYPES.indexOf(cat),
        symbolSize: isCenter ? 56 : cat === '疾病' ? 30 : 12 + Math.min(16, Math.sqrt(dd) * 3),
        value: dd,
        isCenter: !!isCenter,
        itemStyle: { color: TYPE_COLOR[cat] || '#94A3B8', borderColor: '#fff', borderWidth: 1.5 },
        label: { show: true, position: 'right', fontSize: 11 }
      }
    })

  const nameOf: Record<string, string> = {}
  for (const n of d.nodes || []) nameOf[n.id] = n.name

  const edges = links.map((l: any, i: number) => ({
    id: `${l.source}-${l.relation}-${l.target}-${i}`,
    headId: l.source,
    tailId: l.target,
    name: l.relation,
    relation: l.relation,
    headName: nameOf[l.source],
    tailName: nameOf[l.target],
    sourceName: nameOf[l.source],
    targetName: nameOf[l.target],
    status: '已审核',
    lineStyle: {
      color: RELATION_COLOR[l.relation] || '#CBD5E1',
      width: 1.2,
      curveness: 0.08
    }
  }))

  return { nodes, edges, hopDist: d.hop_dist || [], real: true }
}

/** 热门实体（按关系条数），用于下拉框 */
export async function fetchHotEntities(type = '疾病', limit = 16) {
  const rows: any[] = await unwrap(http.get('/kg/hot', { params: { type, limit } }))
  return rows || []
}

/* ---------------------------------------------------------------- 审核 */

function toReview(r: any) {
  return {
    id: r.id,
    relation: r.relation,
    name: r.relation,
    headId: r.headId,
    tailId: r.tailId,
    head: r.headName,
    tail: r.tailName,
    headType: r.headType,
    tailType: r.tailType,
    disease: r.disease,
    source: r.source,
    section: r.section,
    evidenceLevel: r.evidenceLevel || '图谱抽取',
    confidence: r.confidence,
    status: r.status,
    snippet: r.snippet,
    reviewer: r.reviewer,
    reviewedAt: r.reviewedAt
  }
}

export async function fetchReviewList(status = '', keyword = '') {
  const d: any = await unwrap(
    http.get('/review/list', { params: { status: status || undefined, keyword: keyword || undefined } })
  )
  return (d.list || []).map(toReview)
}

export async function reviewAction(id: string, action: 'approve' | 'reject' | 'hold', note = '') {
  return unwrap(http.post(`/review/${id}/${action}`, { note }))
}

export async function fetchReviewStats() {
  return unwrap(http.get('/review/stats'))
}

/* ---------------------------------------------------------------- 问答 */

/** 后端返回整段答案，页面按段落渲染，这里按换行切开 */
function toParagraphs(answer: string): string[] {
  return (answer || '')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
}

/** 从步骤里取意图标签，保持与 mock 的 intent.label 同形 */
function intentLabel(steps: any[]): string {
  const hit = (steps || []).find((s) => s.name === '意图识别')
  return (hit?.detail || '').replace('问题类型：', '') || '综合咨询'
}

/** 同 head+relation 组内，若某个 tail 被另一个 tail 包含，就丢掉短的那个。
 *  OpenCMKG 里有「糖尿」「酸中毒」这类截断实体，不处理会让路径面板出现一堆冗余行。 */
function dedupePath(rows: any[]) {
  const groups = new Map<string, any[]>()
  for (const r of rows) {
    const k = `${r.head}|${r.relation}`
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k)!.push(r)
  }
  const out: any[] = []
  for (const list of groups.values()) {
    const tails = list.map((x) => x.tail)
    for (const r of list) {
      if (tails.some((t) => t !== r.tail && t.includes(r.tail))) continue
      out.push(r)
    }
  }
  return out.slice(0, 6)
}

export async function askQuestion(question: string) {
  const d: any = await unwrap(http.post('/qa/ask', { question }))

  const steps = (d.steps || []).map((s: any, i: number) => ({
    name: s.name,
    detail: s.detail,
    // 后端只给总耗时，这里按步骤数均摊，仅用于展示
    ms: i === 0 ? 24 : Math.round((d.elapsed_ms || 0) / Math.max((d.steps || []).length, 1)),
    extra: ''
  }))

  const citations = (d.citations || []).map((c: any) => ({
    id: c.doc_id,
    citeNo: c.no,
    title: c.title,
    source: c.source,
    docType: c.doc_type,
    journal: c.journal,
    publishDate: c.date,
    pmid: c.pmid,
    snippet: c.snippet,
    routes: c.routes,
    rrf: c.rrf
  }))

  const chunks = (d.citations || []).map((c: any) => ({
    id: `${c.doc_id}-${c.chunk_idx}`,
    text: c.snippet,
    source: c.source,
    doc: {
      id: c.doc_id,
      title: c.title,
      journal: c.journal,
      publishDate: c.date,
      docType: c.doc_type,
      chunkCount: 0
    }
  }))

  const path = dedupePath(
    (d.graph_facts || []).flatMap((f: any) =>
      (f.relations || []).map((r: any) => ({
        head: r.head,
        relation: r.relation,
        tail: r.tail,
        // 页面会读 rel.source / rel.section，后端未返回时给默认值，避免渲染报错
        rel: {
          source: r.source || 'OpenCMKG',
          section: r.section || ''
        }
      }))
    )
  )

  const diseases = (d.entities || [])
    .filter((e: any) => e.type === '疾病')
    .map((e: any) => e.name)

  return {
    intent: {
      key: 'real',
      label: intentLabel(d.steps),
      keywords: d.query_en || [],
      diseases,
      paragraphs: toParagraphs(d.answer),
      pathPairs: [],
      docFilters: [],
      followups: []
    },
    steps,
    citations,
    chunks,
    path,
    related: diseases,
    engine: d.engine || { mode: 'template', name: '图谱模板' },
    queryEn: d.query_en || [],
    retrieval: d.retrieval || {},
    elapsedMs: d.elapsed_ms || 0,
    raw: d
  }
}
