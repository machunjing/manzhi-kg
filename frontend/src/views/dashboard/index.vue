<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseChart from '@/components/common/BaseChart.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { fetchOverview, fetchSystemHealth, fetchDiseaseAgg, fetchYearly, buildGraph, tasks, qaSessions, TYPE_COLOR, ENTITY_TYPES, RELATION_COLOR } from '@/api'

const router = useRouter()
const ov = ref<any>({})
const health = ref<any[]>([])
const agg = ref<any[]>([])
const yearly = ref<any>({})
const loading = ref(true)

const graphOption = ref<any>({})

onMounted(async () => {
  const [o, h, a, y] = await Promise.all([fetchOverview(), fetchSystemHealth(), fetchDiseaseAgg(), fetchYearly()])
  ov.value = o
  health.value = h
  agg.value = a
  yearly.value = y
  loading.value = false

  const g = await buildGraph({
    entityTypes: ['疾病', '危险因素', '并发症', '药物类别'],
    relationTypes: ['共病', '导致', '危险因素', '并发症', '常用药物'],
    limit: 46
  })
  graphOption.value = {
    tooltip: {
      formatter: (p: any) =>
        p.dataType === 'edge'
          ? `${p.data.source} → ${p.data.name} → ${p.data.target}`
          : `${p.data.name}<br/>类型：${p.data.type}`
    },
    legend: { show: false },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        zoom: 0.88,
        scaleLimit: { min: 0.4, max: 3 },
        draggable: true,
        categories: ['疾病', '危险因素', '并发症', '药物类别'].map((t) => ({
          name: t,
          itemStyle: { color: TYPE_COLOR[t] }
        })),
        data: g.nodes,
        links: g.edges,
        force: { repulsion: 760, edgeLength: [95, 190], gravity: 0.05, friction: 0.2 },
        label: {
          position: 'right',
          fontSize: 10,
          color: '#374151',
          backgroundColor: 'rgba(255,255,255,0.82)',
          padding: [1, 3],
          borderRadius: 2
        },
        labelLayout: { hideOverlap: true },
        lineStyle: { opacity: 0.62 },
        emphasis: { focus: 'adjacency', label: { show: true, fontWeight: 'bold' } }
      }
    ]
  }
})

const cards = computed(() => [
  {
    title: '去重实体',
    value: ov.value.entityTotal?.toLocaleString(),
    unit: '个',
    icon: 'Coin',
    color: '#2563EB',
    trend: `OpenCMKG 抽取，已与 MeSH 术语对齐`,
    trendType: 'flat' as const,
    hint: '来自 OpenCMKG 实体表，已去重并按名称建索引'
  },
  {
    title: '候选三元组',
    value: ov.value.tripleTotal?.toLocaleString(),
    unit: '条',
    icon: 'Connection',
    color: '#7C3AED',
    trend: `已审核 ${ov.value.kgApproved} · 待审核 ${ov.value.kgPending} · 候选 ${ov.value.kgCandidate}`,
    trendType: 'flat' as const,
    hint: '候选三元组不等同于已审核关系，审核状态需在关系审核页面确认'
  },
  {
    title: '文本块',
    value: ov.value.chunkTotal?.toLocaleString(),
    unit: '块',
    icon: 'Tickets',
    color: '#0891B2',
    trend: '300 字滑窗 / 50 字重叠',
    trendType: 'flat' as const,
    hint: 'PubMed 摘要 31,578 块 + MedlinePlus 500 块'
  },
  {
    title: '文本字符量',
    value: (ov.value.charTotal / 10000).toFixed(1),
    unit: '万字',
    icon: 'Document',
    color: '#16A34A',
    trend: `文献 ${ov.value.docTotal?.toLocaleString()} 篇 · 期刊 ${ov.value.journalTotal} 种`,
    trendType: 'flat' as const,
    hint: 'PubMed 摘要 + MedlinePlus 主题摘要字符合计'
  }
])

const diseasePie = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 篇（{d}%）' },
  legend: { bottom: 0, itemWidth: 9, itemHeight: 9, textStyle: { fontSize: 11, color: '#6B7280' } },
  series: [
    {
      type: 'pie',
      radius: ['52%', '72%'],
      center: ['50%', '44%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold', formatter: '{b}\n{c} 篇' } },
      data: Object.entries(ov.value.diseaseCount || {}).map(([k, v], i) => ({
        name: k,
        value: v,
        itemStyle: { color: ['#DC2626', '#2563EB', '#7C3AED', '#F59E0B'][i] }
      }))
    }
  ]
}))

const diseaseBar = computed(() => {
  const list = agg.value.slice(0, 7)
  return {
    grid: { left: 12, right: 18, top: 30, bottom: 6, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: list.map((x) => x.disease),
      axisLabel: { fontSize: 11, color: '#6B7280', interval: 0 },
      axisLine: { lineStyle: { color: '#E5E7EB' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '关系数',
      nameTextStyle: { fontSize: 11, color: '#9CA3AF' },
      splitLine: { lineStyle: { color: '#F1F4F8' } },
      axisLabel: { fontSize: 11, color: '#9CA3AF' }
    },
    series: [
      {
        type: 'bar',
        barWidth: 22,
        data: list.map((x) => x.relations),
        itemStyle: { color: '#2563EB', borderRadius: [4, 4, 0, 0] },
        label: { show: true, position: 'top', fontSize: 10, color: '#6B7280' }
      }
    ]
  }
})

const sourceBar = computed(() => ({
  grid: { left: 12, right: 26, top: 12, bottom: 6, containLabel: true },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  xAxis: {
    type: 'log',
    min: 1,
    splitLine: { lineStyle: { color: '#F1F4F8' } },
    axisLabel: { fontSize: 10.5, color: '#9CA3AF' }
  },
  yAxis: {
    type: 'category',
    data: ['PubMed 文献', 'MedlinePlus 主题', '本地指南 PDF', 'DiaKG 图谱', 'OpenCMKG 三元组'],
    axisLabel: { fontSize: 11, color: '#6B7280' },
    axisLine: { show: false },
    axisTick: { show: false }
  },
  series: [
    {
      type: 'bar',
      barWidth: 15,
      data: [ov.value.docTotal || 0, ov.value.mlpTopicTotal || 31, ov.value.raw?.guides || 6, 41, ov.value.tripleTotal || 0],
      itemStyle: {
        borderRadius: [0, 4, 4, 0],
        color: (p: any) => ['#2563EB', '#0891B2', '#7C3AED', '#F59E0B', '#16A34A'][p.dataIndex]
      },
      label: { show: true, position: 'right', fontSize: 10, color: '#6B7280' }
    }
  ]
}))

const recentTasks = computed(() => tasks.slice(0, 5))
const recentQa = computed(() => qaSessions.slice(0, 5))

const yearTrend = computed(() => {
  const y = yearly.value
  const years = Object.keys(y['2型糖尿病'] || {})
  return {
    grid: { left: 8, right: 16, top: 34, bottom: 4, containLabel: true },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: '#6B7280' } },
    xAxis: {
      type: 'category',
      data: years,
      axisLabel: { fontSize: 11, color: '#9CA3AF' },
      axisLine: { lineStyle: { color: '#E5E7EB' } },
      axisTick: { show: false }
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    series: Object.keys(y).map((k, i) => ({
      name: k,
      type: 'line',
      smooth: true,
      symbolSize: 5,
      data: years.map((yy) => y[k][yy]),
      lineStyle: { width: 2 },
      itemStyle: { color: ['#DC2626', '#2563EB', '#7C3AED'][i] }
    }))
  }
})

const healthMap: Record<string, string> = { 演示状态: 'warning', 未连接: 'danger' }
</script>

<template>
  <div>
    <div class="mz-page-head">
      <div>
        <div class="mz-page-title">慢性病知识服务总览</div>
        <div class="mz-page-desc">多源知识整合 · 疾病关系分析 · GraphRAG 智能问答</div>
      </div>
      <div style="display: flex; gap: 8px; align-items: center">
        <span class="mz-demo-badge">数据快照 2026-11-04</span>
        <el-button @click="router.push('/qa/chat')">
          <el-icon><ChatDotRound /></el-icon>进入智能问答
        </el-button>
        <el-button type="primary" @click="router.push('/kg/graph')">
          <el-icon><Share /></el-icon>探索知识图谱
        </el-button>
      </div>
    </div>

    <!-- 核心指标 -->
    <div class="mz-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 16px">
      <StatCard v-for="c in cards" :key="c.title" v-bind="c" />
    </div>

    <!-- 第二行 -->
    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col" style="flex: 2">
        <div class="mz-card-head">
          <div class="mz-card-title">
            慢性病知识图谱总览
            <span class="mz-card-sub">三高及关联疾病实体关系网络</span>
          </div>
          <div class="g-legend">
            <span v-for="t in ['疾病', '危险因素', '并发症', '药物类别']" :key="t" class="gl">
              <i :style="{ background: TYPE_COLOR[t] }" />{{ t }}
            </span>
            <el-button text type="primary" size="small" @click="router.push('/kg/graph')">查看完整图谱 →</el-button>
          </div>
        </div>
        <BaseChart :option="graphOption" height="366" :loading="loading" />
      </div>
      <div class="mz-card" style="flex: 1">
        <div class="mz-card-head">
          <div class="mz-card-title">疾病数据分布</div>
          <span class="mz-card-sub">文献口径</span>
        </div>
        <BaseChart :option="diseasePie" height="366" :loading="loading" />
      </div>
    </div>

    <!-- 第三行 -->
    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">疾病关联数量</div>
          <span class="mz-card-sub">图谱关系数</span>
        </div>
        <BaseChart :option="diseaseBar" height="252" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">知识库数据来源统计</div>
          <span class="mz-card-sub">条 / 篇</span>
        </div>
        <BaseChart :option="sourceBar" height="252" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">三病年发文趋势</div>
          <span class="mz-card-sub">PubMed 命中数</span>
        </div>
        <BaseChart :option="yearTrend" height="252" :loading="loading" />
      </div>
    </div>

    <!-- 第四行 -->
    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">最近数据采集记录</div>
          <el-button text type="primary" size="small" @click="router.push('/data/tasks')">全部任务</el-button>
        </div>
        <el-table :data="recentTasks" size="small" style="width: 100%">
          <el-table-column prop="id" label="任务编号" width="104" />
          <el-table-column prop="name" label="任务名称" show-overflow-tooltip />
          <el-table-column prop="count" label="采集量" width="82" align="right" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }"><StatusTag :status="row.status" /></template>
          </el-table-column>
        </el-table>
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">最近系统问答记录</div>
          <el-button text type="primary" size="small" @click="router.push('/qa/history')">全部记录</el-button>
        </div>
        <el-table :data="recentQa" size="small" style="width: 100%">
          <el-table-column prop="title" label="问题" show-overflow-tooltip />
          <el-table-column prop="disease" label="关联疾病" width="100" />
          <el-table-column prop="rounds" label="轮次" width="62" align="center" />
          <el-table-column prop="createdAt" label="时间" width="118" />
        </el-table>
      </div>
    </div>

    <!-- 运行状态 -->
    <div class="mz-card">
      <div class="mz-card-head">
        <div class="mz-card-title">
          系统运行状态
          <span class="mz-card-sub">未接入真实健康检查接口，仅显示演示状态</span>
        </div>
        <el-button text size="small" @click="router.push('/system/settings')">服务配置</el-button>
      </div>
      <div class="health-row">
        <div v-for="h in health" :key="h.name" class="health-item">
          <div class="h-left">
            <span class="h-dot" :class="'is-' + (h.ok === true ? 'ok' : h.ok === false ? 'err' : 'demo')" />
            <div>
              <div class="h-name">{{ h.name }}</div>
              <div class="h-detail">{{ h.detail }}</div>
            </div>
          </div>
          <el-tag :type="healthMap[h.value] || 'info'" size="small" effect="plain">{{ h.value }}</el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.health-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--mz-border);
  border-radius: 0 0 10px 10px;
  overflow: hidden;
}
.health-item {
  background: #fff;
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.h-left {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.h-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 5px;
  flex: 0 0 8px;
}
.h-dot.is-ok {
  background: #16a34a;
  box-shadow: 0 0 0 3px #e7f6ec;
}
.h-dot.is-err {
  background: #dc2626;
  box-shadow: 0 0 0 3px #fdeaea;
}
.h-dot.is-demo {
  background: #f59e0b;
  box-shadow: 0 0 0 3px #fdf4e3;
}
.h-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--mz-text);
}
.h-detail {
  font-size: 11px;
  color: var(--mz-text-light);
  margin-top: 3px;
  line-height: 1.5;
}
.g-legend {
  display: flex;
  align-items: center;
  gap: 14px;
}
.g-legend .gl {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--mz-text-sub);
  white-space: nowrap;
}
.g-legend .gl i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
</style>
