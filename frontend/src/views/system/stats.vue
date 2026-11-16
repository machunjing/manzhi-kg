<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import BaseChart from '@/components/common/BaseChart.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { fetchOverview, fetchYearly, fetchDiseaseAgg, qaSessions, tasks, TYPE_COLOR, RELATION_COLOR, ENTITY_TYPES, RELATION_TYPES } from '@/api'

const ov = ref<any>({})
const yearly = ref<any>({})
const agg = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  ov.value = await fetchOverview()
  yearly.value = await fetchYearly()
  agg.value = await fetchDiseaseAgg()
  loading.value = false
})

const cards = computed(() => [
  { title: '实体总数', value: ov.value.entityMeshTotal?.toLocaleString(), unit: '个', icon: 'Coin', color: '#2563EB' },
  { title: '候选三元组', value: ov.value.tripleTotal?.toLocaleString(), unit: '条', icon: 'Connection', color: '#7C3AED' },
  { title: '已审核关系', value: ov.value.kgApproved, unit: '条', icon: 'CircleCheck', color: '#16A34A' },
  { title: '文本块总数', value: ov.value.chunkTotal?.toLocaleString(), unit: '块', icon: 'Tickets', color: '#0891B2' },
  { title: '文献总数', value: ov.value.docTotal?.toLocaleString(), unit: '篇', icon: 'Document', color: '#F59E0B' },
  { title: '用户总数', value: 42, unit: '人', icon: 'User', color: '#DB2777' }
])

const growthOption = computed(() => {
  const years = Object.keys(yearly.value['2型糖尿病'] || {})
  return {
    grid: { left: 12, right: 20, top: 30, bottom: 4, containLabel: true },
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: '#6B7280' } },
    xAxis: { type: 'category', data: years, axisLabel: { fontSize: 11, color: '#9CA3AF' }, axisLine: { lineStyle: { color: '#E5E7EB' } }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    series: Object.keys(yearly.value).map((k, i) => ({
      name: k,
      type: 'line',
      smooth: true,
      symbolSize: 5,
      areaStyle: { opacity: 0.08 },
      lineStyle: { width: 2 },
      itemStyle: { color: ['#DC2626', '#2563EB', '#7C3AED'][i] },
      data: years.map((y) => yearly.value[k][y])
    }))
  }
})

const entTypeOption = computed(() => ({
  grid: { left: 12, right: 20, top: 10, bottom: 4, containLabel: true },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  xAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
  yAxis: {
    type: 'category',
    data: [...ENTITY_TYPES].reverse(),
    axisLabel: { fontSize: 11, color: '#6B7280' },
    axisLine: { show: false },
    axisTick: { show: false }
  },
  series: [
    {
      type: 'bar',
      barWidth: 13,
      data: [...ENTITY_TYPES].reverse().map((t) => ({ value: ov.value.typeCount?.[t] || 0, itemStyle: { color: TYPE_COLOR[t], borderRadius: [0, 4, 4, 0] } })),
      label: { show: true, position: 'right', fontSize: 10, color: '#6B7280' }
    }
  ]
}))

const relTypeOption = computed(() => {
  const entries = Object.entries(ov.value.relTypeCount || {}).sort((a: any, b: any) => b[1] - a[1])
  return {
    grid: { left: 12, right: 20, top: 10, bottom: 4, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    yAxis: { type: 'category', data: entries.map((e: any) => e[0]).reverse(), axisLabel: { fontSize: 11, color: '#6B7280' }, axisLine: { show: false }, axisTick: { show: false } },
    series: [
      {
        type: 'bar',
        barWidth: 13,
        data: entries.reverse().map((e: any) => ({ value: e[1], itemStyle: { color: RELATION_COLOR[e[0]] || '#2563EB', borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', fontSize: 10, color: '#6B7280' }
      }
    ]
  }
})

const docSourceOption = computed(() => {
  const list = [
    { name: 'OpenCMKG', value: 1, color: '#16A34A' },
    { name: '指南 PDF', value: 6, color: '#7C3AED' },
    { name: 'MedlinePlus', value: 31, color: '#0891B2' },
    { name: 'DiaKG', value: 41, color: '#F59E0B' },
    { name: 'PubMed', value: 5026, color: '#2563EB' }
  ]
  const total = list.reduce((a, b) => a + b.value, 0)
  return {
    grid: { left: 12, right: 58, top: 10, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p: any) => `${p[0].name}<br/>文献数：<b>${p[0].value}</b> 篇（${((p[0].value / total) * 100).toFixed(1)}%）`
    },
    xAxis: {
      type: 'log',
      min: 1,
      splitLine: { lineStyle: { color: '#F1F4F8' } },
      axisLabel: { fontSize: 10, color: '#9CA3AF' }
    },
    yAxis: {
      type: 'category',
      data: list.map((i) => i.name),
      axisLabel: { fontSize: 11, color: '#4B5563' },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        type: 'bar',
        barWidth: 15,
        data: list.map((i) => ({ value: i.value, itemStyle: { color: i.color, borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', fontSize: 10, color: '#6B7280' }
      }
    ]
  }
})

const diseaseOption = computed(() => ({
  grid: { left: 12, right: 20, top: 24, bottom: 4, containLabel: true },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: Object.keys(ov.value.diseaseCount || {}), axisLabel: { fontSize: 11, color: '#6B7280' }, axisLine: { lineStyle: { color: '#E5E7EB' } }, axisTick: { show: false } },
  yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
  series: [
    {
      type: 'bar',
      barWidth: 40,
      data: Object.values(ov.value.diseaseCount || {}).map((v: any, i: number) => ({ value: v, itemStyle: { color: ['#DC2626', '#2563EB', '#7C3AED'][i], borderRadius: [4, 4, 0, 0] } })),
      label: { show: true, position: 'top', fontSize: 11, color: '#6B7280' }
    }
  ]
}))

const qaTrendOption = computed(() => ({
  grid: { left: 12, right: 20, top: 24, bottom: 4, containLabel: true },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['10-28', '10-29', '10-30', '10-31', '11-01', '11-02', '11-03', '11-04'], axisLabel: { fontSize: 10.5, color: '#9CA3AF' }, axisLine: { lineStyle: { color: '#E5E7EB' } }, axisTick: { show: false } },
  yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
  series: [
    {
      type: 'line',
      smooth: true,
      symbolSize: 5,
      data: [12, 18, 15, 24, 31, 22, 27, 34],
      lineStyle: { width: 2.2, color: '#0891B2' },
      itemStyle: { color: '#0891B2' },
      areaStyle: { color: 'rgba(8,145,178,0.10)' }
    }
  ]
}))

const recentQa = qaSessions.slice(0, 6)
const recentTasks = tasks.slice(0, 5)
const procStatus = [
  { name: 'PubMed 文献解析', done: 5026, total: 5026, ok: true },
  { name: '文本切块与向量化', done: 32078, total: 32078, ok: true },
  { name: 'MeSH 实体抽取', done: 4793, total: 4793, ok: true },
  { name: '关系三元组生成', done: 36619, total: 36619, ok: true },
  { name: '指南 PDF 文本抽取', done: 4, total: 6, ok: false }
]
</script>

<template>
  <div>
    <PageHeader title="系统数据统计" desc="平台运行指标与知识库增长趋势。除文献 / 实体 / 文本块等实测口径外，问答量、用户量等为演示数据。" />

    <div class="mz-grid" style="grid-template-columns: repeat(6, 1fr); margin-bottom: 16px">
      <StatCard v-for="c in cards" :key="c.title" v-bind="c" />
    </div>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col" style="flex: 1.4">
        <div class="mz-card-head">
          <div class="mz-card-title">知识库数据增长趋势</div>
          <span class="mz-card-sub">PubMed 年发文命中数</span>
        </div>
        <BaseChart :option="growthOption" height="252" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head"><div class="mz-card-title">实体类型统计</div></div>
        <BaseChart :option="entTypeOption" height="252" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head"><div class="mz-card-title">关系类型统计</div></div>
        <BaseChart :option="relTypeOption" height="252" :loading="loading" />
      </div>
    </div>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">文献来源统计</div>
          <span class="mz-card-sub">条 / 篇（对数轴）</span>
        </div>
        <BaseChart :option="docSourceOption" height="230" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head"><div class="mz-card-title">疾病数据分布</div></div>
        <BaseChart :option="diseaseOption" height="230" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">问答数量趋势</div>
          <span class="mz-card-sub">演示数据</span>
        </div>
        <BaseChart :option="qaTrendOption" height="230" :loading="loading" />
      </div>
    </div>

    <div class="mz-row">
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">数据处理状态</div>
          <span class="mz-card-sub">流水线各环节进度</span>
        </div>
        <div class="proc">
          <div v-for="p in procStatus" :key="p.name" class="proc-row">
            <div class="pr-head">
              <span>{{ p.name }}</span>
              <span class="pr-num">{{ p.done.toLocaleString() }} / {{ p.total.toLocaleString() }}</span>
            </div>
            <el-progress
              :percentage="Math.round((p.done / p.total) * 100)"
              :stroke-width="6"
              :color="p.ok ? '#16A34A' : '#F59E0B'"
              :format="() => (p.ok ? '完成' : '处理中')"
            />
          </div>
        </div>
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">最近更新记录</div>
          <el-button text type="primary" size="small" @click="$router.push('/data/tasks')">采集任务</el-button>
        </div>
        <el-table :data="recentTasks" size="small">
          <el-table-column prop="id" label="任务" width="98" />
          <el-table-column prop="name" label="名称" show-overflow-tooltip />
          <el-table-column prop="count" label="数量" width="76" align="right" />
          <el-table-column label="状态" width="84">
            <template #default="{ row }"><StatusTag :status="row.status" /></template>
          </el-table-column>
        </el-table>
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">最近问答记录</div>
          <el-button text type="primary" size="small" @click="$router.push('/qa/history')">全部</el-button>
        </div>
        <el-table :data="recentQa" size="small">
          <el-table-column prop="title" label="问题" show-overflow-tooltip />
          <el-table-column prop="disease" label="疾病" width="94" />
          <el-table-column prop="createdAt" label="时间" width="118" />
        </el-table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.proc {
  padding: 8px 18px 16px;
}
.proc-row {
  padding: 9px 0;
}
.pr-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--mz-text);
  margin-bottom: 6px;
}
.pr-num {
  color: var(--mz-text-light);
  font-size: 11px;
}
</style>
