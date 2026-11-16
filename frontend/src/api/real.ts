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

export function fetchSystemHealth() {
  return unwrap(http.get('/system/health'))
}

export function fetchOverview() {
  return unwrap(http.get('/stats/overview'))
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
  // 页面不选疾病时传 undefined；真库 3 万多实体不能全画，兜底到「糖尿病」
  const entity = q.disease || q.keyword || q.entity || '糖尿病'
  const depth = q.depth ?? 1
  const d: any = await unwrap(
    http.get('/kg/graph', { params: { entity, depth, limit: q.limit ?? 55 } })
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
  // 按度数排序能把「糖尿病肾病」这类真正的核心概念排到前面。
  const center = allNodes.find((n) => n.depth === 0) || allNodes[0]
  let keep = allNodes
  if (allNodes.length > MAX_NODES) {
    const rest = allNodes
      .filter((n) => n.id !== center.id)
      .sort((a, b) => (deg[b.id] || 0) - (deg[a.id] || 0))
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
      keywords: [],
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
    raw: d
  }
}
