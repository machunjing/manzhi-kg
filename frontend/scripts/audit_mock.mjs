// 找出还在用 mock 的页面：mock 导出 - 已被 real 覆盖的 = 仍走假数据的函数
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const mock = fs.readFileSync(path.join(root, 'src/mock/index.ts'), 'utf8')
const idx = fs.readFileSync(path.join(root, 'src/api/index.ts'), 'utf8')

const exported = [...mock.matchAll(/export (?:async )?function (\w+)/g)].map((m) => m[1])
const overridden = new Set(
  [...idx.matchAll(/^\s{2}(\w+),?$/gm)].map((m) => m[1]).concat(
    [...idx.matchAll(/export \{([^}]+)\} from '\.\/real'/g)].flatMap((m) =>
      m[1].split(',').map((s) => s.trim())
    )
  )
)

const views = []
function walk(dir) {
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f)
    if (fs.statSync(p).isDirectory()) walk(p)
    else if (p.endsWith('.vue')) views.push(p)
  }
}
walk(path.join(root, 'src/views'))

const stillMock = {}
for (const v of views) {
  const src = fs.readFileSync(v, 'utf8')
  const imp = src.match(/import \{([^}]+)\} from '@\/api'/)
  if (!imp) continue
  const names = imp[1].split(',').map((s) => s.trim()).filter(Boolean)
  const fake = names.filter((n) => exported.includes(n) && !overridden.has(n))
  if (fake.length) stillMock[path.relative(root, v)] = fake
}

console.log('已被 real 覆盖的接口：', [...overridden].filter(Boolean).sort().join(', '))
console.log('\n仍走 mock 的页面：')
for (const [v, fns] of Object.entries(stillMock)) {
  console.log('  ' + v + '\n      ' + fns.join(', '))
}
