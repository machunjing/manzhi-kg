<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseChart from '@/components/common/BaseChart.vue'
import { pagerank, entities, TYPE_COLOR, ENTITY_TYPES } from '@/api'

const loading = ref(true)
const rows = ref<any[]>([])
const typeFilter = ref('')

onMounted(() => {
  rows.value = pagerank
  setTimeout(() => (loading.value = false), 200)
})

const filtered = computed(() => (typeFilter.value ? rows.value.filter((r) => r.type === typeFilter.value) : rows.value))
const top10 = computed(() => rows.value.slice(0, 10))

const barOption = computed(() => {
  const list = [...top10.value].reverse()
  return {
    grid: { left: 10, right: 50, top: 10, bottom: 6, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p: any) => `${p[0].name}<br/>PageRank 分值：<b>${p[0].value}</b>`
    },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#F1F4F8' } }, axisLabel: { fontSize: 11, color: '#9CA3AF' } },
    yAxis: {
      type: 'category',
      data: list.map((r) => r.name),
      axisLabel: { fontSize: 11, color: '#4B5563', width: 120, overflow: 'truncate' },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        type: 'bar',
        barWidth: 14,
        data: list.map((r) => ({
          value: r.score,
          itemStyle: { color: TYPE_COLOR[r.type] || '#2563EB', borderRadius: [0, 4, 4, 0] }
        })),
        label: { show: true, position: 'right', fontSize: 10, color: '#6B7280' }
      }
    ]
  }
})

const typePie = computed(() => {
  const map: Record<string, number> = {}
  rows.value.forEach((r) => (map[r.type] = (map[r.type] || 0) + 1))
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 个（{d}%）' },
    legend: {
      bottom: 4,
      itemWidth: 9,
      itemHeight: 9,
      itemGap: 10,
      width: '92%',
      textStyle: { fontSize: 11, color: '#6B7280' }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '58%'],
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
        style: { text: `${rows.value.length}\n个节点`, textAlign: 'center', fill: '#173B70', fontSize: 13, fontWeight: 600, lineHeight: 19 }
      }
    ]
  }
})

const totalNodes = computed(() => rows.value.length)
const avgScore = computed(() => (rows.value.reduce((a, r) => a + r.score, 0) / (rows.value.length || 1)).toFixed(2))
</script>

<template>
  <div>
    <PageHeader title="PageRank 节点分析" desc="基于加权 PageRank 分析知识图谱中节点的结构重要性。PageRank 反映图结构中的连接影响力，不代表疾病严重程度或临床风险等级。" />

    <div class="calc-bar">
      <div class="calc-item">
        <div class="ci-label">算法</div>
        <div class="ci-value">加权 PageRank（damping = 0.85，迭代 30 轮）</div>
      </div>
      <div class="calc-item">
        <div class="ci-label">计算时间</div>
        <div class="ci-value">2026-11-04 09:48:12</div>
      </div>
      <div class="calc-item">
        <div class="ci-label">节点总数</div>
        <div class="ci-value">{{ totalNodes }} 个</div>
      </div>
      <div class="calc-item">
        <div class="ci-label">平均分值</div>
        <div class="ci-value">{{ avgScore }}</div>
      </div>
      <div class="calc-item">
        <div class="ci-label">关系总数</div>
        <div class="ci-value">{{ rows.reduce((a, r) => a + r.relCount, 0) / 2 }} 条</div>
      </div>
    </div>

    <div class="mz-row" style="margin-bottom: 16px">
      <div class="mz-card mz-col" style="flex: 1.35">
        <div class="mz-card-head">
          <div class="mz-card-title">PageRank Top 10</div>
          <span class="mz-card-sub">横向柱状图 · 颜色表示实体类型</span>
        </div>
        <BaseChart :option="barOption" height="330" :loading="loading" />
      </div>
      <div class="mz-card mz-col">
        <div class="mz-card-head">
          <div class="mz-card-title">节点类型分布</div>
          <span class="mz-card-sub">全图口径</span>
        </div>
        <BaseChart :option="typePie" height="330" :loading="loading" />
      </div>
    </div>

    <div class="mz-card">
      <div class="mz-card-head">
        <div class="mz-card-title">节点重要性排名</div>
        <el-select v-model="typeFilter" placeholder="全部类型" clearable size="small" style="width: 140px">
          <el-option v-for="t in ENTITY_TYPES" :key="t" :label="t" :value="t" />
        </el-select>
      </div>
      <el-table :data="filtered" v-loading="loading" size="small" max-height="440" style="width: 100%">
        <el-table-column label="排名" width="72" align="center">
          <template #default="{ $index }">
            <span class="rank" :class="{ top3: $index < 3 }">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="实体名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="实体类型" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :color="(TYPE_COLOR[row.type] || '#94A3B8') + '14'" style="border: none; color: #374151">
              {{ row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="PageRank 分值" width="140" align="right">
          <template #default="{ row }">
            <span class="score">{{ row.score }}</span>
          </template>
        </el-table-column>
        <el-table-column label="分值占比" width="150">
          <template #default="{ row }">
            <el-progress :percentage="Math.min(100, Math.round((row.score / (rows[0]?.score || 1)) * 100))" :stroke-width="6" :show-text="false" color="#2563EB" />
          </template>
        </el-table-column>
        <el-table-column prop="degree" label="关联节点数" width="110" align="right" />
        <el-table-column prop="relCount" label="关联关系数" width="110" align="right" />
        <el-table-column label="所属疾病" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.diseases?.join('、') || '通用实体' }}</template>
        </el-table-column>
      </el-table>
    </div>

    <div class="algo-note">
      <div class="an-title">算法说明</div>
      <div class="an-text">
        PageRank 通过迭代计算节点在图结构中的相对重要性：分值越高，说明该节点被越多高权重节点连接，在知识网络中处于越中心的位置。
        本页分值仅反映<strong>图结构特征</strong>，不代表疾病的严重程度、患病率或临床风险等级，也不构成任何诊疗优先级建议。
      </div>
    </div>
  </div>
</template>

<style scoped>
.calc-bar {
  display: grid;
  grid-template-columns: 1.6fr 1fr 0.8fr 0.8fr 0.8fr;
  gap: 1px;
  background: var(--mz-border);
  border: 1px solid var(--mz-border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
}
.calc-item {
  background: #fff;
  padding: 13px 18px;
}
.ci-label {
  font-size: 11px;
  color: var(--mz-text-light);
  margin-bottom: 5px;
}
.ci-value {
  font-size: 12.5px;
  font-weight: 600;
  color: #173b70;
}
.rank {
  display: inline-flex;
  width: 20px;
  height: 20px;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  background: #f2f5fa;
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
}
.rank.top3 {
  background: #173b70;
  color: #fff;
}
.score {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: #173b70;
}
.algo-note {
  margin-top: 16px;
  background: #fbfcfe;
  border: 1px dashed var(--mz-border);
  border-radius: 8px;
  padding: 14px 18px;
}
.an-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--mz-text);
  margin-bottom: 6px;
}
.an-text {
  font-size: 11.5px;
  line-height: 1.9;
  color: var(--mz-text-sub);
}
</style>
