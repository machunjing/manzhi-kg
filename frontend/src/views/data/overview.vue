<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import BaseChart from '@/components/common/BaseChart.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { fetchOverview, fetchYearly, fetchDiseaseAgg, TYPE_COLOR, RELATION_COLOR, tasks, documents } from '@/api'

const router = useRouter()
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
  {
    title: '去重实体总数',
    value: ov.value.entityMeshTotal?.toLocaleString(),
    unit: '个',
    icon: 'Coin',
    color: '#2563EB',
    trend: '已剔除人口学与研究设计标签',
    hint: '来自 PubMed MeSH 主题词去重，剔除 Humans / Female / Risk Factors 等 36 类标签后剩余有效实体'
  },
  {
    title: '候选三元组总数',
    value: ov.value.tripleTotal?.toLocaleString(),
    unit: '条',
    icon: 'Connection',
    color: '#7C3AED',
    trend: `已审核 ${ov.value.kgApproved} · 待审核 ${ov.value.kgPending}`,
    hint: '文献锚定三元组：head = PubMed:PMID，relation = 涉及，tail = MeSH 实体'
  },
  {
    title: '文本块总数',
    value: ov.value.chunkTotal?.toLocaleString(),
    unit: '块',
    icon: 'Tickets',
    color: '#0891B2',
    trend: '300 字滑窗 · 50 字重叠',
    hint: 'PubMed 摘要 31,578 块 + MedlinePlus 主题摘要 500 块'
  },
  {
    title: '文本总字符数',
    value: (ov.value.charTotal / 10000).toFixed(1),
    unit: '万字',
    icon: 'Document',
    color: '#16A34A',
    trend: `文献 ${ov.value.docTotal} 篇 · 摘要覆盖 ${((ov.value.docWithAbstract / ov.value.docTotal) * 100).toFixed(1)}%`,
    hint: 'PubMed 摘要与 MedlinePlus 主题摘要字符合计（不含指南 PDF 待抽取文本）'
  }
])

const typePie = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 个（{d}%）' },
  legend: { bottom: 0, itemWidth: 9, itemHeight: 9, textStyle: { fontSize: 11, color: '#6B7280' } },
  series: [
    {
      type: 'pie',
      radius: ['48%', '70%'],
      center: ['50%', '43%'],
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold', formatter: '{b}\n{c}' } },
      data: Object.entries(ov.value.typeCount || {}).map(([k, v]) => ({
        name: k,
        value: v,
        itemStyle: { color: TYPE_COLOR[k] || '#94A3B8' }
      }))
    }
  ]
}))

const relBar = computed(() => {
  const entries = Object.entries(ov.value.relTypeCount || {}).sort((a: any, b: any) => b[1] - a[1])
  return {
    grid: { left: 10, right: 34, top: 12, bottom: 6, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    yAxis: {
      type: 'category',
      data: entries.map((e: any) => e[0]).reverse(),
      axisLabel: { fontSize: 11, color: '#6B7280' },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        type: 'bar',
        barWidth: 12,
        data: entries.reverse().map((e: any) => ({ value: e[1], itemStyle: { color: RELATION_COLOR[e[0]] || '#2563EB', borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', fontSize: 10, color: '#6B7280' }
      }
    ]
  }
})

const sourceRing = computed(() => ({
  grid: { left: 10, right: 46, top: 12, bottom: 6, containLabel: true },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p: any) => `${p[0].name}：<b>${p[0].value}</b> 条 / 篇` },
  xAxis: {
    type: 'log',
    min: 1,
    splitLine: { lineStyle: { color: '#F1F4F8' } },
    axisLabel: { fontSize: 10.5, color: '#9CA3AF' }
  },
  yAxis: {
    type: 'category',
    data: ['OpenCMKG 三元组', '指南 PDF', 'MedlinePlus 主题', 'DiaKG 图谱', 'PubMed 文献'],
    axisLabel: { fontSize: 11, color: '#6B7280' },
    axisLine: { show: false },
    axisTick: { show: false }
  },
  series: [
    {
      type: 'bar',
      barWidth: 14,
      data: [
        { value: 1, itemStyle: { color: '#16A34A', borderRadius: [0, 4, 4, 0] } },
        { value: 6, itemStyle: { color: '#7C3AED', borderRadius: [0, 4, 4, 0] } },
        { value: 31, itemStyle: { color: '#0891B2', borderRadius: [0, 4, 4, 0] } },
        { value: 41, itemStyle: { color: '#F59E0B', borderRadius: [0, 4, 4, 0] } },
        { value: ov.value.docTotal || 5026, itemStyle: { color: '#2563EB', borderRadius: [0, 4, 4, 0] } }
      ],
      label: { show: true, position: 'right', fontSize: 10.5, color: '#6B7280' }
    }
  ]
}))

const trendLine = computed(() => {
  const y = yearly.value
  const years = Object.keys(y['2型糖尿病'] || {})
  const sum = years.map((yy) => Object.keys(y).reduce((a, k) => a + (y[k][yy] || 0), 0))
  return {
    grid: { left: 10, right: 20, top: 24, bottom: 6, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: years, axisLabel: { fontSize: 11, color: '#9CA3AF' }, axisLine: { lineStyle: { color: '#E5E7EB' } }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    series: [
      {
        name: '三病命中文献',
        type: 'line',
        smooth: true,
        areaStyle: { color: 'rgba(37,99,235,0.10)' },
        lineStyle: { width: 2.4, color: '#2563EB' },
        itemStyle: { color: '#2563EB' },
        symbolSize: 6,
        data: sum
      }
    ]
  }
})

const recentTasks = computed(() => tasks.slice(0, 4))
const recentDocs = computed(() =>
  documents
    .filter((d) => d.source === 'PubMed')
    .slice(0, 4)
    .map((d) => ({ ...d, title: d.title.length > 68 ? d.title.slice(0, 68) + '…' : d.title }))
)

const pendingRel = computed(() => ov.value.kgPending || 0)
const anomalies = [
  { level: '高', text: '3 篇文献摘要为空，需重新采集或人工补录', count: 3 },
  { level: '中', text: '7 组实体疑似重复（如「高血压」与「原发性高血压」）', count: 7 },
  { level: '低', text: '12 条关系缺少原文证据片段，暂不进入审核队列', count: 12 }
]
const levelType: Record<string, string> = { 高: 'danger', 中: 'warning', 低: 'info' }
</script>

<template>
  <div>
    <PageHeader
      title="数据资源总览"
      desc="展示平台多源语料资产规模与分布。卡片数值为数据包实测口径（2026-11-04），候选三元组不等同于已审核关系。"
    >
      <template #actions>
        <el-button @click="router.push('/data/documents')"><el-icon><Document /></el-icon>文献管理</el-button>
        <el-button type="primary" @click="router.push('/data/quality')"><el-icon><CircleCheck /></el-icon>数据质检</el-button>
      </template>
    </PageHeader>

    <div class="mz-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 16px">
      <StatCard v-for="c in cards" :key="c.title" v-bind="c" />
    </div>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">实体类型分布</div>
          <span class="mz-card-sub">知识图谱演示子集</span>
        </div>
        <BaseChart :option="typePie" height="270" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">关系类型分布</div>
          <span class="mz-card-sub">三元组口径</span>
        </div>
        <BaseChart :option="relBar" height="270" :loading="loading" />
      </div>
    </div>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">数据来源分布</div>
          <span class="mz-card-sub">条 / 篇</span>
        </div>
        <BaseChart :option="sourceRing" height="270" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">数据采集数量趋势</div>
          <span class="mz-card-sub">年发文命中数</span>
        </div>
        <BaseChart :option="trendLine" height="270" :loading="loading" />
      </div>
    </div>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col" style="flex: 1.2">
        <div class="mz-card-head">
          <div class="mz-card-title">最近采集记录</div>
          <el-button text type="primary" size="small" @click="router.push('/data/tasks')">全部任务</el-button>
        </div>
        <el-table :data="recentTasks" size="small">
          <el-table-column prop="id" label="任务编号" width="100" />
          <el-table-column prop="source" label="数据来源" width="104" />
          <el-table-column prop="disease" label="目标疾病" width="96" />
          <el-table-column prop="count" label="采集量" width="78" align="right" />
          <el-table-column label="状态" width="86">
            <template #default="{ row }"><StatusTag :status="row.status" /></template>
          </el-table-column>
          <el-table-column prop="startAt" label="开始时间" />
        </el-table>
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">最近数据更新记录</div>
          <el-button text type="primary" size="small" @click="router.push('/data/documents')">文献列表</el-button>
        </div>
        <el-table :data="recentDocs" size="small">
          <el-table-column prop="id" label="文献ID" width="100" />
          <el-table-column prop="title" label="文献标题" show-overflow-tooltip />
          <el-table-column prop="chunkCount" label="文本块" width="70" align="right" />
        </el-table>
      </div>
    </div>

    <div class="mz-row">
      <div class="mz-card mz-col" style="flex: 1">
        <div class="mz-card-head">
          <div class="mz-card-title">待审核关系</div>
          <el-button text type="primary" size="small" @click="router.push('/kg/review')">进入审核</el-button>
        </div>
        <div class="pending-box">
          <div class="pending-num">{{ pendingRel }}</div>
          <div class="pending-label">条关系等待医学审核</div>
          <div class="pending-meta">
            <span>候选关系 {{ ov.kgCandidate }} 条</span>
            <span>已驳回 {{ ov.kgRejected }} 条</span>
          </div>
          <el-progress
            :percentage="Math.round((ov.kgApproved / (ov.kgRelationTotal || 1)) * 100)"
            :stroke-width="8"
            color="#2563EB"
            style="margin-top: 12px"
          />
          <div class="pending-tip">审核完成度（已审核 / 关系总数）</div>
        </div>
      </div>
      <div class="mz-card mz-col" style="flex: 2">
        <div class="mz-card-head">
          <div class="mz-card-title">数据质量异常提示</div>
          <el-button text type="primary" size="small" @click="router.push('/data/quality')">查看明细</el-button>
        </div>
        <div class="anomaly-list">
          <div v-for="a in anomalies" :key="a.text" class="anomaly">
            <el-tag :type="levelType[a.level] as any" size="small" effect="light">{{ a.level }}风险</el-tag>
            <span class="anomaly-text">{{ a.text }}</span>
            <span class="anomaly-count">{{ a.count }} 条</span>
          </div>
        </div>
      </div>
    </div>

    <div class="caliber">
      数据口径说明：本页统计值来自数据包 <code>03_清洗后数据</code> / <code>04_预处理中间产物</code> 的实测结果；
      开题阶段初版摸底口径为 3,931 个实体 / 24,731 条候选三元组 / 21,002 个文本块 / 501.9 万字符，已按最新采集结果更新。
    </div>
  </div>
</template>

<style scoped>
.pending-box {
  padding: 22px 24px 18px;
  text-align: center;
}
.pending-num {
  font-size: 40px;
  font-weight: 700;
  color: #f59e0b;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.pending-label {
  font-size: 12.5px;
  color: var(--mz-text-sub);
  margin-top: 8px;
}
.pending-meta {
  display: flex;
  justify-content: center;
  gap: 18px;
  margin-top: 12px;
  font-size: 11.5px;
  color: var(--mz-text-light);
}
.pending-tip {
  font-size: 11px;
  color: var(--mz-text-light);
  margin-top: 6px;
}
.anomaly-list {
  padding: 6px 18px 14px;
}
.anomaly {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px dashed #f0f2f6;
}
.anomaly:last-child {
  border-bottom: none;
}
.anomaly-text {
  flex: 1;
  font-size: 12.5px;
  color: var(--mz-text);
}
.anomaly-count {
  font-size: 12px;
  color: var(--mz-text-sub);
}
.caliber {
  margin-top: 16px;
  font-size: 11.5px;
  color: var(--mz-text-light);
  line-height: 1.8;
  background: #fbfcfe;
  border: 1px dashed var(--mz-border);
  border-radius: 8px;
  padding: 10px 14px;
}
.caliber code {
  background: #eef2f8;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
}
</style>
