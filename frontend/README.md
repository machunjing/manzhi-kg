# 前端 · 慢知

Vue 3 + Vite 6 + TypeScript 的前端工程，20 个页面。

## 启动

```bash
npm install
npm run dev      # http://127.0.0.1:5173
npm run build    # 产物在 dist/
```

## 目录

```
src/
├── api/index.ts        接口出口 —— mock 与真接口在这里切换
├── mock/               假数据服务（原型阶段）
│   └── data/*.json     13 个数据文件
├── views/              20 个页面
│   ├── dashboard/      首页总览
│   ├── data/           数据资源：概览 / 文献 / 质量 / 采集任务
│   ├── kg/             知识图谱：图谱 / 实体 / 关系 / 审核
│   ├── qa/             智能问答：对话 / 答案 / 过程 / 历史
│   ├── analysis/       关联分析：网络 / 路径 / PageRank / 统计
│   └── system/         系统管理：用户 / 统计 / 日志 / 设置
├── components/         公共组件
├── stores/             Pinia
└── router/             路由（hash 模式）
```

## mock 与真接口怎么切

所有页面只从 `src/api/index.ts` 取数据，不直接写请求。这个文件做两件事：

```ts
export * from '@/mock'                                    // 全量铺开 mock 能力
export { askQuestion, fetchOverview, fetchSystemHealth }  // 具名导出覆盖成真接口
  from './real'
```

ES 规范里**具名导出优先于星号导出**，所以后面这三行会把 mock 里的同名函数顶掉。
「哪几个能力已经接了真后端」，看这个文件最后几行就知道。

形状转换全部收敛在 `src/api/real.ts`：后端返回的是整段 `answer`、扁平 `citations`，
页面要的是 `intent.paragraphs`、`citeNo`、`rel.source`——都在适配层里转，页面代码一行不动。

开发时 `/api` 由 Vite 代理到 `http://127.0.0.1:5001`（见 `vite.config.ts`），不用配跨域。

接口契约见 [`../docs/openapi.yaml`](../docs/openapi.yaml)，58 个操作、50 个 schema。
