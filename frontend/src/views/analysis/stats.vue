<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseChart from '@/components/common/BaseChart.vue'
import { relations, entities, diseaseAgg, RELATION_TYPES, RELATION_COLOR, TYPE_COLOR, ENTITY_TYPES, DISEASES } from '@/api'

const disease = ref('')
const range = ref('全部')
const c1 = ref<any>()
const c2 = ref<any>()
const c3 = ref<any>()
const c4 = ref<any>()
const c5 = ref<any>()

const scoped = computed(() => (disease.value ? relations.filter((r) => r.disease === disease.value) : relations))
const scopedAgg = computed(() => (disease.value ? diseaseAgg.filter((d) => d.disease === disease.value) : diseaseAgg))

const barOption = computed(() => ({
  grid: { left: 12, right: 20, top: 24, bottom: 4, containLabel: true },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  xAxis: {
    type: 'category',
    data: scopedAgg.value.map((d) => d.disease),
    axisLabel: { fontSize: 11, color: '#6B7280', interval: 0, rotate: scopedAgg.value.length > 6 ? 20 : 0 },
    axisLine: { lineStyle: { color: '#E5E7EB' } },
    axisTick: { show: false }
  },
  yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
  series: [
    {
      name: '关系数',
      type: 'bar',
      barWidth: 22,
      data: scopedAgg.value.map((d) => d.relations),
      itemStyle: { color: '#2563EB', borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', fontSize: 10, color: '#6B7280' }
    },
    {
      name: '已审核',
      type: 'bar',
      barWidth: 22,
      data: scopedAgg.value.map((d) => d.approved),
      itemStyle: { color: '#16A34A', borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', fontSize: 10, color: '#6B7280' }
    }
  ],
  legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: '#6B7280' } }
}))

const stackOption = computed(() => {
  const ds = disease.value ? [disease.value] : DISEASES.slice(0, 6)
  const types = RELATION_TYPES
  return {
    grid: { left: 12, right: 20, top: 18, bottom: 30, containLabel: true },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      type: 'scroll',
      bottom: 0,
      itemWidth: 9,
      itemHeight: 8,
      itemGap: 8,
      textStyle: { fontSize: 10, color: '#6B7280' },
      pageIconSize: 9
    },
    xAxis: { type: 'category', data: ds, axisLabel: { fontSize: 11, color: '#6B7280' }, axisLine: { lineStyle: { color: '#E5E7EB' } }, axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    series: types.map((t) => ({
      name: t,
      type: 'bar',
      stack: 'total',
      barWidth: 26,
      itemStyle: { color: RELATION_COLOR[t] },
      data: ds.map((d) => relations.filter((r) => r.disease === d && r.relation === t).length)
    }))
  }
})

const heatOption = computed(() => {
  const ds = ['2型糖尿病', '高血压', '血脂异常']
  const ts = ['危险因素', '并发症', '常用药物', '监测指标', '干预措施']
  const data: any[] = []
  let max = 0
  ds.forEach((d, i) =>
    ts.forEach((t, j) => {
      const v = relations.filter((r) => r.disease === d && r.relation === t).length
      max = Math.max(max, v)
      data.push([j, i, v])
    })
  )
  return {
    grid: { left: 12, right: 20, top: 12, bottom: 56, containLabel: true },
    tooltip: { formatter: (p: any) => `${ds[p.value[1]]} × ${ts[p.value[0]]}<br/>关系数：<b>${p.value[2]}</b>` },
    xAxis: { type: 'category', data: ts, splitArea: { show: true }, axisLabel: { fontSize: 11, color: '#6B7280' }, axisLine: { show: false }, axisTick: { show: false } },
    yAxis: { type: 'category', data: ds, splitArea: { show: true }, axisLabel: { fontSize: 11, color: '#6B7280' }, axisLine: { show: false }, axisTick: { show: false } },
    visualMap: {
      min: 0,
      max: max || 10,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 4,
      itemHeight: 90,
      textStyle: { fontSize: 10.5, color: '#6B7280' },
      inRange: { color: ['#EFF4FF', '#93B4F5', '#2563EB', '#173B70'] }
    },
    series: [
      {
        type: 'heatmap',
        data,
        label: { show: true, fontSize: 11, color: '#1F2937' },
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
        emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(23,59,112,0.25)' } }
      }
    ]
  }
})

const entTypeOption = computed(() => {
  const map: Record<string, number> = {}
  const ids = new Set<string>()
  scoped.value.forEach((r) => {
    ids.add(r.headId)
    ids.add(r.tailId)
  })
  entities.filter((e) => ids.has(e.id)).forEach((e) => (map[e.type] = (map[e.type] || 0) + 1))
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 个（{d}%）' },
    legend: { bottom: 2, itemWidth: 9, itemHeight: 9, itemGap: 8, width: '94%', textStyle: { fontSize: 10, color: '#6B7280' } },
    series: [
      {
        type: 'pie',
        radius: ['40%', '60%'],
        center: ['50%', '40%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, formatter: '{b}\n{c}' } },
        data: ENTITY_TYPES.filter((t) => map[t]).map((t) => ({ name: t, value: map[t], itemStyle: { color: TYPE_COLOR[t] } }))
      }
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '33%',
        style: {
          text: `${Object.values(map).reduce((a, b) => a + b, 0)}\n个实体`,
          textAlign: 'center',
          fill: '#173B70',
          fontSize: 12,
          fontWeight: 600,
          lineHeight: 18
        }
      }
    ]
  }
})

const weightOption = computed(() => {
  const bins = [0, 0, 0, 0, 0]
  scoped.value.forEach((r) => {
    const v = r.confidence
    if (v < 0.7) bins[0]++
    else if (v < 0.78) bins[1]++
    else if (v < 0.86) bins[2]++
    else if (v < 0.94) bins[3]++
    else bins[4]++
  })
  return {
    grid: { left: 12, right: 20, top: 24, bottom: 4, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['<0.70', '0.70~0.78', '0.78~0.86', '0.86~0.94', '≥0.94'],
      axisLabel: { fontSize: 10.5, color: '#6B7280' },
      axisLine: { lineStyle: { color: '#E5E7EB' } },
      axisTick: { show: false }
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    series: [
      {
        type: 'bar',
        barWidth: 30,
        data: bins,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: (p: any) => ['#BFD3FF', '#93B4F5', '#2563EB', '#1D4ED8', '#173B70'][p.dataIndex]
        },
        label: { show: true, position: 'top', fontSize: 10, color: '#6B7280' }
      }
    ]
  }
})

function download(refObj: any, name: string) {
  const chart = refObj.value?.chart
  if (!chart) return
  const url = chart.getDataURL({ pixelRatio: 2, backgroundColor: '#fff' })
  const a = document.createElement('a')
  a.href = url
  a.download = `${name}.png`
  a.click()
  ElMessage.success('图表已下载')
}
</script>

<template>
  <div>
    <PageHeader title="疾病关联统计" desc="对知识图谱中的疾病关联数量、关系类型、实体类型与置信度分布进行多维统计。所有图表联动于上方筛选条件。">
      <template #actions>
        <el-select v-model="disease" placeholder="全部疾病" clearable style="width: 150px">
          <el-option v-for="d in DISEASES" :key="d" :label="d" :value="d" />
        </el-select>
        <el-select v-model="range" style="width: 130px">
          <el-option label="全部时间" value="全部" />
          <el-option label="近 12 个月" value="12m" />
          <el-option label="近 3 年" value="3y" />
        </el-select>
        <el-button type="primary" @click="ElMessage.success('筛选条件已应用，图表已联动更新')">应用筛选</el-button>
      </template>
    </PageHeader>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">疾病关联数量</div>
          <el-button link size="small" @click="download(c1, '疾病关联数量')"><el-icon><Download /></el-icon></el-button>
        </div>
        <BaseChart ref="c1" :option="barOption" height="260" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">疾病关系类型分布</div>
          <el-button link size="small" @click="download(c2, '疾病关系类型分布')"><el-icon><Download /></el-icon></el-button>
        </div>
        <BaseChart ref="c2" :option="stackOption" height="260" />
      </div>
    </div>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col" style="flex: 1.25">
        <div class="mz-card-head">
          <div class="mz-card-title">三高疾病关联热力图</div>
          <span class="mz-card-sub">疾病 × 关系类型</span>
          <el-button link size="small" @click="download(c3, '三高疾病关联热力图')"><el-icon><Download /></el-icon></el-button>
        </div>
        <BaseChart ref="c3" :option="heatOption" height="300" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">关联实体类型分布</div>
          <el-button link size="small" @click="download(c4, '关联实体类型分布')"><el-icon><Download /></el-icon></el-button>
        </div>
        <BaseChart ref="c4" :option="entTypeOption" height="300" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">关系权重分布</div>
          <span class="mz-card-sub">抽取置信度</span>
          <el-button link size="small" @click="download(c5, '关系权重分布')"><el-icon><Download /></el-icon></el-button>
        </div>
        <BaseChart ref="c5" :option="weightOption" height="300" />
      </div>
    </div>

    <div class="mz-card">
      <div class="mz-card-head">
        <div class="mz-card-title">疾病统计明细</div>
        <span class="mz-card-sub">文献数来自数据包实测，关系数来自图谱演示子集</span>
      </div>
      <el-table :data="scopedAgg" size="small" style="width: 100%">
        <el-table-column prop="disease" label="疾病" width="150" />
        <el-table-column prop="literature" label="文献数" width="110" align="right" />
        <el-table-column prop="entities" label="关联实体数" width="120" align="right" />
        <el-table-column prop="relations" label="关系总数" width="110" align="right" />
        <el-table-column prop="approved" label="已审核" width="100" align="right" />
        <el-table-column prop="pending" label="待审核" width="100" align="right" />
        <el-table-column label="审核完成度">
          <template #default="{ row }">
            <el-progress :percentage="Math.round((row.approved / (row.relations || 1)) * 100)" :stroke-width="7" color="#2563EB" />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
