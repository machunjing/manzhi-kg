// 用 Chrome DevTools Protocol 逐页截图，用于原型自检
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const BASE = 'http://127.0.0.1:5178'
const OUT = path.resolve('shots')
const W = 1440
const H = 900
const PORT = 9333

fs.mkdirSync(OUT, { recursive: true })

const routes = process.argv.slice(2).map((r) => (r.startsWith('/') ? r : '/#/' + r))
if (!routes.length) {
  console.log('usage: node shot.mjs /#/dashboard /#/kg/graph ...')
  process.exit(1)
}

const proc = spawn(
  CHROME,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    `--remote-debugging-port=${PORT}`,
    `--window-size=${W},${H}`,
    '--user-data-dir=' + path.resolve('.chrome-profile'),
    'about:blank'
  ],
  { stdio: 'ignore', detached: false }
)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function getWsUrl() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`)
      const list = await r.json()
      const page = list.find((t) => t.type === 'page')
      if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch {}
    await sleep(300)
  }
  throw new Error('chrome not ready')
}

const wsUrl = await getWsUrl()
const ws = new WebSocket(wsUrl)
await new Promise((r) => (ws.onopen = r))

let id = 0
const pending = new Map()
const events = []
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data)
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg)
    pending.delete(msg.id)
  } else if (msg.method) {
    events.push(msg)
  }
}
function send(method, params = {}) {
  const mid = ++id
  ws.send(JSON.stringify({ id: mid, method, params }))
  return new Promise((res) => pending.set(mid, res))
}

await send('Page.enable')
await send('Runtime.enable')
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false })

// 首次进入，写入登录态
await send('Page.navigate', { url: BASE + '/#/login' })
await sleep(2500)
await send('Runtime.evaluate', {
  expression: `localStorage.setItem('mz-token','demo');localStorage.setItem('mz-profile', JSON.stringify({name:'演示管理员',account:'admin',role:'管理员',dept:'知识工程组'}));`
})

const logs = []
for (const r of routes) {
  events.length = 0
  await send('Page.navigate', { url: `${BASE}/?r=${Date.now()}${r}` })
  await sleep(3600)
  const errs = events
    .filter((e) => e.method === 'Runtime.exceptionThrown')
    .map((e) => e.params.exceptionDetails?.exception?.description || e.params.exceptionDetails?.text)
  const consoleErrs = events
    .filter((e) => e.method === 'Runtime.consoleAPICalled' && e.params.type === 'error')
    .map((e) => e.params.args.map((a) => a.value ?? a.description).join(' '))
  if (errs.length || consoleErrs.length) logs.push({ route: r, errs, consoleErrs })

  const shot = await send('Page.captureScreenshot', { format: 'png' })
  const name = r.replace(/^\/#\//, '').replace(/\//g, '_') + '.png'
  fs.writeFileSync(path.join(OUT, name), Buffer.from(shot.result.data, 'base64'))
  console.log('saved', name)
}

fs.writeFileSync(path.join(OUT, '_errors.json'), JSON.stringify(logs, null, 2))
console.log('ERRORS:', JSON.stringify(logs, null, 2))

ws.close()
proc.kill()
process.exit(0)
