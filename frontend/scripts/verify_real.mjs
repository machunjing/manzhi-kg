// 验证「智能问答」页是否真的走了后端接口（而不是 mock）
// 用法: node scripts/verify_real.mjs
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const BASE = 'http://127.0.0.1:5178'
const PORT = 9339
const W = 1440, H = 1000

const proc = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  `--remote-debugging-port=${PORT}`, `--window-size=${W},${H}`,
  '--user-data-dir=' + path.resolve('.chrome-profile-verify'), 'about:blank'], { stdio: 'ignore' })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function getWs() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`)
      const l = await r.json()
      const p = l.find((t) => t.type === 'page')
      if (p?.webSocketDebuggerUrl) return p.webSocketDebuggerUrl
    } catch {}
    await sleep(300)
  }
  throw new Error('chrome 未就绪')
}

const ws = new WebSocket(await getWs())
await new Promise((r) => (ws.onopen = r))
let id = 0
const pending = new Map()
const msgs = []
ws.onmessage = (e) => {
  const m = JSON.parse(e.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) }
  else if (m.method) msgs.push(m)
}
const send = (method, params = {}) => {
  const mid = ++id
  ws.send(JSON.stringify({ id: mid, method, params }))
  return new Promise((r) => pending.set(mid, r))
}
const evaluate = async (expression) => {
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  return r.result?.result?.value ?? r.result?.exceptionDetails?.text
}

await send('Page.enable')
await send('Runtime.enable')
await send('Network.enable')
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false })

await send('Page.navigate', { url: BASE + '/#/login' })
await sleep(2200)
await evaluate(`localStorage.setItem('mz-token','demo');localStorage.setItem('mz-profile', JSON.stringify({name:'演示管理员',account:'admin',role:'管理员',dept:'知识工程组'}));`)

// 记录所有 /api 请求
await evaluate(`window.__apiHits = []; 
  const of = window.fetch;
  window.fetch = function(...a){ try{ window.__apiHits.push(String(a[0])) }catch(e){} return of.apply(this,a) };
  const oo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m,u,...r){ try{ window.__apiHits.push(m+' '+u) }catch(e){} return oo.call(this,m,u,...r) };
  'ok'`)

await send('Page.navigate', { url: `${BASE}/?r=${Date.now()}/#/qa/chat` })

// 等输入框真正挂载（Vite 首次编译较慢，固定 sleep 不可靠）
let ready = false
for (let i = 0; i < 40; i++) {
  await sleep(500)
  ready = await evaluate(`!!document.querySelector('textarea')`)
  if (ready) { console.log('输入框就绪，用时约', (i + 1) * 0.5, '秒'); break }
}
if (!ready) console.log('警告：15 秒内未找到输入框')

const typed = await evaluate(`(async () => {
  const ta = document.querySelector('textarea')
  if (!ta) return 'no-textarea'
  const proto = ta instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(ta, '糖尿病有哪些常见并发症？')
  ta.dispatchEvent(new Event('input', { bubbles: true }))
  await new Promise(r => setTimeout(r, 400))
  const btn = [...document.querySelectorAll('button')].find(b => /发送|提问|搜索/.test(b.textContent))
  if (!btn) return 'no-button'
  btn.click()
  return 'clicked:' + btn.textContent.trim()
})()`)
console.log('输入框操作:', typed)

// 大模型生成要 10s 上下，不能固定 sleep，轮询「转圈消失且引用出现」
let done = false
for (let i = 0; i < 90; i++) {
  await sleep(500)
  done = await evaluate(`!document.querySelector('[class*="thinking"]') && document.querySelectorAll('[class*="cite-row"]').length > 0`)
  if (done) { console.log('回答生成完成，用时约', ((i + 1) * 0.5).toFixed(1), '秒'); break }
}
if (!done) console.log('警告：45 秒内未检测到完成态')

const probe = await evaluate(`({
  apiHits: (window.__apiHits || []).filter(u => u.includes('/api/')),
  citeRows: document.querySelectorAll('[class*="cite-row"]').length,
  pathRows: document.querySelectorAll('[class*="path-row"]').length,
  evCards: document.querySelectorAll('[class*="ev-card"]').length,
  head: document.body.innerText.replace(/\\s+/g, ' ').slice(0, 260),
  answer: document.body.innerText.replace(/\\s+/g, ' ').slice(260, 900)
})`)
console.log('接口请求:', JSON.stringify(probe.apiHits, null, 0))
console.log('引用条数:', probe.citeRows, '| 图谱路径:', probe.pathRows, '| 证据卡片:', probe.evCards)
console.log('页面文本:', probe.head)
console.log('回答内容:', probe.answer)

const shot = await send('Page.captureScreenshot', { format: 'png' })
fs.writeFileSync(path.resolve('shots', 'qa_real.png'), Buffer.from(shot.result.data, 'base64'))

for (const m of msgs) {
  if (m.method === 'Runtime.exceptionThrown') console.log('EXCEPTION:', m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text)
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') console.log('CONSOLE', m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 300))
}
console.log('saved shots/qa_real.png')
ws.close(); proc.kill(); process.exit(0)
