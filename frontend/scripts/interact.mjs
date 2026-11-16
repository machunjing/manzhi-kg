import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const BASE = 'http://127.0.0.1:5178'
const PORT = 9336
const W = 1440, H = 900
const route = process.argv[2] || 'qa/chat'
const script = process.argv[3] || ''
const out = process.argv[4] || 'interact.png'

const proc = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars','--no-first-run',`--remote-debugging-port=${PORT}`,`--window-size=${W},${H}`,'--user-data-dir=' + path.resolve('.chrome-profile3'),'about:blank'], { stdio: 'ignore' })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function getWs() {
  for (let i = 0; i < 60; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/list`); const l = await r.json(); const p = l.find(t => t.type === 'page'); if (p?.webSocketDebuggerUrl) return p.webSocketDebuggerUrl } catch {}
    await sleep(300)
  }
  throw new Error('no chrome')
}
const ws = new WebSocket(await getWs())
await new Promise(r => (ws.onopen = r))
let id = 0
const pending = new Map()
const msgs = []
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id) } else if (m.method) msgs.push(m) }
const send = (method, params = {}) => { const mid = ++id; ws.send(JSON.stringify({ id: mid, method, params })); return new Promise(r => pending.set(mid, r)) }

await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false })
await send('Page.navigate', { url: BASE + '/#/login' })
await sleep(2200)
await send('Runtime.evaluate', { expression: `localStorage.setItem('mz-token','demo');localStorage.setItem('mz-profile', JSON.stringify({name:'演示管理员',account:'admin',role:'管理员',dept:'知识工程组'}));` })
await send('Page.navigate', { url: `${BASE}/?r=${Date.now()}/#/${route}` })
await sleep(3600)
if (script) {
  const r = await send('Runtime.evaluate', { expression: script, awaitPromise: true, returnByValue: true })
  console.log('eval:', JSON.stringify(r.result?.result?.value ?? r.result?.exceptionDetails?.text))
  await sleep(4200)
}
const shot = await send('Page.captureScreenshot', { format: 'png' })
fs.writeFileSync(path.resolve('shots', out), Buffer.from(shot.result.data, 'base64'))
for (const m of msgs) {
  if (m.method === 'Runtime.exceptionThrown') console.log('EXCEPTION:', m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text)
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') console.log('CONSOLE', m.params.args.map(a => a.value ?? a.description).join(' ').slice(0, 300))
}
console.log('saved', out)
ws.close(); proc.kill(); process.exit(0)
