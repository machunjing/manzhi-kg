/**
 * 业务 API 门面：页面只依赖本文件。
 *
 * 下面的 `export *` 把 mock 的全量能力铺开，
 * 紧接着的具名导出会把同名函数覆盖成真实后端实现
 * （ES 规范里具名导出优先于星号导出）。
 *
 * 所以「哪几个能力已经接了真接口」，看这个文件最后几行就知道。
 */
export * from '@/mock'

/* ---------------- 已接真实后端 ---------------- */
export { askQuestion, fetchOverview, fetchSystemHealth } from './real'
