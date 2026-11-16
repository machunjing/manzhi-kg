/**
 * 真实后端适配层
 * ------------------------------------------------------------------
 * 把 Flask 接口的返回结构，转成页面已经在用的数据结构。
 * 页面代码一行都不用改 —— 形状转换全部收敛在这个文件里。
 *
 * 已接真接口：问答、系统健康、总览统计
 * 仍走 mock：图谱、文献、审核、用户、日志等（后端接口尚未补齐）
 */
import http from './request'

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
