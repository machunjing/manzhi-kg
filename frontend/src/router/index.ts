import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

export const menuRoutes = [
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/index.vue'),
    meta: { title: '首页总览', icon: 'Odometer', group: '首页总览', desc: '慢性病知识服务总览' }
  },
  {
    path: '/user',
    name: 'UserRoot',
    redirect: '/user/list',
    meta: { title: '用户与权限管理', icon: 'UserFilled' },
    children: [
      {
        path: '/user/list',
        name: 'UserList',
        component: () => import('@/views/user/index.vue'),
        meta: { title: '用户管理', icon: 'User', group: '用户与权限管理', desc: '账号、角色与状态管理' }
      }
    ]
  },
  {
    path: '/data',
    name: 'DataRoot',
    redirect: '/data/overview',
    meta: { title: '慢性病知识数据管理', icon: 'Files' },
    children: [
      {
        path: '/data/overview',
        name: 'DataOverview',
        component: () => import('@/views/data/overview.vue'),
        meta: { title: '数据资源总览', group: '慢性病知识数据管理', desc: '多源语料资产与采集规模' }
      },
      {
        path: '/data/documents',
        name: 'Documents',
        component: () => import('@/views/data/documents.vue'),
        meta: { title: '文献与指南管理', group: '慢性病知识数据管理', desc: '文献元数据、文本切片与处理状态' }
      },
      {
        path: '/data/tasks',
        name: 'CollectTasks',
        component: () => import('@/views/data/tasks.vue'),
        meta: { title: '数据采集任务', group: '慢性病知识数据管理', desc: '采集任务编排、进度与日志' }
      },
      {
        path: '/data/quality',
        name: 'DataQuality',
        component: () => import('@/views/data/quality.vue'),
        meta: { title: '数据质量管理', group: '慢性病知识数据管理', desc: '实体、关系、文本与来源四维质检' }
      }
    ]
  },
  {
    path: '/kg',
    name: 'KgRoot',
    redirect: '/kg/graph',
    meta: { title: '慢性病知识图谱管理', icon: 'Share' },
    children: [
      {
        path: '/kg/graph',
        name: 'KgGraph',
        component: () => import('@/views/kg/graph.vue'),
        meta: { title: '知识图谱可视化', group: '慢性病知识图谱管理', desc: '实体关系网络交互式探索' }
      },
      {
        path: '/kg/entities',
        name: 'KgEntities',
        component: () => import('@/views/kg/entities.vue'),
        meta: { title: '实体管理', group: '慢性病知识图谱管理', desc: '实体词典、别名与审核状态' }
      },
      {
        path: '/kg/relations',
        name: 'KgRelations',
        component: () => import('@/views/kg/relations.vue'),
        meta: { title: '关系管理', group: '慢性病知识图谱管理', desc: '三元组明细与证据等级' }
      },
      {
        path: '/kg/review',
        name: 'KgReview',
        component: () => import('@/views/kg/review.vue'),
        meta: { title: '关系审核', group: '慢性病知识图谱管理', desc: '基于原文证据的医学关系审核' }
      }
    ]
  },
  {
    path: '/qa',
    name: 'QaRoot',
    redirect: '/qa/chat',
    meta: { title: '慢性病智能问答', icon: 'ChatDotRound' },
    children: [
      {
        path: '/qa/chat',
        name: 'QaChat',
        component: () => import('@/views/qa/chat.vue'),
        meta: { title: '智能问答', group: '慢性病智能问答', desc: 'GraphRAG 检索增强问答与证据溯源' }
      },
      {
        path: '/qa/history',
        name: 'QaHistory',
        component: () => import('@/views/qa/history.vue'),
        meta: { title: '问答历史', group: '慢性病智能问答', desc: '历史会话记录与检索链路回溯' }
      }
    ]
  },
  {
    path: '/analysis',
    name: 'AnalysisRoot',
    redirect: '/analysis/network',
    meta: { title: '慢性病关联分析', icon: 'DataAnalysis' },
    children: [
      {
        path: '/analysis/network',
        name: 'DiseaseNetwork',
        component: () => import('@/views/analysis/network.vue'),
        meta: { title: '疾病关联网络', group: '慢性病关联分析', desc: '疾病为中心的多跳关联网络' }
      },
      {
        path: '/analysis/path',
        name: 'RelationPath',
        component: () => import('@/views/analysis/path.vue'),
        meta: { title: '关联路径分析', group: '慢性病关联分析', desc: '两疾病之间的最短关联路径' }
      },
      {
        path: '/analysis/pagerank',
        name: 'PageRankView',
        component: () => import('@/views/analysis/pagerank.vue'),
        meta: { title: 'PageRank 节点分析', group: '慢性病关联分析', desc: '图结构重要性与节点排名' }
      },
      {
        path: '/analysis/stats',
        name: 'DiseaseStats',
        component: () => import('@/views/analysis/stats.vue'),
        meta: { title: '疾病关联统计', group: '慢性病关联分析', desc: '关联数量、类型分布与热力图' }
      }
    ]
  },
  {
    path: '/system',
    name: 'SystemRoot',
    redirect: '/system/stats',
    meta: { title: '系统统计与运行管理', icon: 'Setting' },
    children: [
      {
        path: '/system/stats',
        name: 'SystemStats',
        component: () => import('@/views/system/stats.vue'),
        meta: { title: '数据统计', group: '系统统计与运行管理', desc: '平台运行指标与增长趋势' }
      },
      {
        path: '/system/logs',
        name: 'SystemLogs',
        component: () => import('@/views/system/logs.vue'),
        meta: { title: '系统日志', group: '系统统计与运行管理', desc: '操作审计与执行结果追溯' }
      },
      {
        path: '/system/settings',
        name: 'SystemSettings',
        component: () => import('@/views/system/settings.vue'),
        meta: { title: '系统设置', group: '系统统计与运行管理', desc: '基础信息、模型与检索参数' }
      }
    ]
  }
] as any

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/dashboard',
    children: menuRoutes.flatMap((r: any) => (r.children ? r.children : [r]))
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.beforeEach((to) => {
  const store = useUserStore()
  if (to.meta.public) return true
  if (!store.token) return { path: '/login', query: { redirect: to.fullPath } }
  return true
})

router.afterEach((to) => {
  const t = (to.meta.title as string) || ''
  document.title = t ? `${t} · 慢知平台` : '慢知 · 慢性病智能知识服务平台'
})

export default router
