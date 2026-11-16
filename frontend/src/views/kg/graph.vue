<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import BaseChart from '@/components/common/BaseChart.vue'
import { buildGraph, pinDiseases, getEntity, getRelation, entities, relations, DISEASES, ENTITY_TYPES, RELATION_TYPES, TYPE_COLOR, RELATION_COLOR, REVIEW_STATUS } from '@/api'

const loading = ref(false)
const chartRef = ref<any>()
const wrap = ref<HTMLElement>()
const option = ref<any>({})
const sel = reactive({
  disease: '',
  entityTypes: [...ENTITY_TYPES],
  relationTypes: [...RELATION_TYPES],
  statuses: [] as string[],
  keyword: '',
  limit: 55
})
const picked = reactive({ type: '' as '' | 'node' | 'edge', node: {} as any, edge: {} as any })
const stat = reactive({ nodes: 0, edges: 0 })

async function build() {
  loading.value = true
  const g = await buildGraph({
    disease: sel.disease || undefined,
    entityTypes: sel.entityTypes,
    relationTypes: sel.relationTypes,
    statuses: sel.statuses.length ? sel.statuses : undefined,
    keyword: sel.keyword || undefined,
    limit: sel.limit
  })
  // 真接口的中心节点已钉在原点，不需要 mock 那套环形钉法
  if (!(g as any).real) pinDiseases(g.nodes, 150)
  stat.nodes = g.nodes.length
  stat.edges = g.edges.length
  option.value = {
    tooltip: {
      formatter: (p: any) => {
        if (p.dataType === 'edge') {
          const s = p.data.sourceName || getEntity(p.data.source)?.name
          const t = p.data.targetName || getEntity(p.data.target)?.name
          return `${s} → <b>${p.data.name}</b> → ${t}<br/><span style="color:#9CA3AF">点击查看证据</span>`
        }
        return `<b>${p.data.name}</b><br/>类型：${p.data.type}<br/>关联数：${p.data.value}`
      }
    },
    legend: { show: false },
    animationDuration: 500,
    series: [
      {
        type: 'graph',
        // 真接口已经算好等角星形坐标，用 none 直接落位；
        // mock 走力导向
        layout: (g as any).real ? 'none' : 'force',
        left: 92,
        right: 132,
        top: 40,
        bottom: 40,
        roam: true,
        draggable: true,
        scaleLimit: { min: 0.3, max: 4 },
        categories: ENTITY_TYPES.map((t) => ({ name: t, itemStyle: { color: TYPE_COLOR[t] } })),
        data: g.nodes,
        links: g.edges,
        force: { initLayout: 'circular', repulsion: 300, edgeLength: [55, 120], gravity: 0.16, friction: 0.22, layoutAnimation: false },
        labelLayout: { hideOverlap: true },
        label: {
          position: 'right',
          fontSize: 10,
          color: '#374151',
          backgroundColor: 'rgba(255,255,255,0.82)',
          padding: [1, 3],
          borderRadius: 2
        },
        lineStyle: { opacity: 0.55 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 3, opacity: 1 }, label: { show: true, fontWeight: 'bold' } },
        blur: { itemStyle: { opacity: 0.25 }, lineStyle: { opacity: 0.08 } }
      }
    ]
  }
  setTimeout(() => (loading.value = false), 260)
}

onMounted(build)

function reset() {
  sel.disease = ''
  sel.entityTypes = [...ENTITY_TYPES]
  sel.relationTypes = [...RELATION_TYPES]
  sel.statuses = []
  sel.keyword = ''
  sel.limit = 55
  picked.type = ''
  build()
}

function onChartClick(p: any) {
  if (p.dataType === 'node') {
    picked.type = 'node'
    picked.node = getEntity(p.data.id) || p.data
  } else if (p.dataType === 'edge') {
    picked.type = 'edge'
    const rel = getRelation(p.data.id) || p.data
    picked.edge = {
      ...rel,
      headName: rel.headName || rel.sourceName || getEntity(rel.headId)?.name,
      tailName: rel.tailName || rel.targetName || getEntity(rel.tailId)?.name
    }
  }
}

function focusNode(name: string) {
  sel.keyword = name
  build()
  ElMessage.success(`已定位到「${name}」及其关联子图`)
}

async function toggleFull() {
  if (!document.fullscreenElement) {
    await wrap.value?.requestFullscreen()
    ElMessage.success('已进入全屏，按 ESC 退出')
  } else {
    await document.exitFullscreen()
  }
  await nextTick()
  setTimeout(() => chartRef.value?.chart?.resize(), 220)
}

function saveImage() {
  const url = chartRef.value?.chart?.getDataURL({ pixelRatio: 2, backgroundColor: '#fff' })
  if (!url) return
  const a = document.createElement('a')
  a.href = url
  a.download = `知识图谱_${sel.disease || '全部疾病'}.png`
  a.click()
  ElMessage.success('图谱图片已保存')
}

const nodeRels = computed(() => (picked.type === 'node' ? relations.filter((r) => r.headId === picked.node.id || r.tailId === picked.node.id) : []))
const nodeImportance = computed(() => {
  if (picked.type !== 'node') return 0
  return Math.min(100, Math.round((picked.node.relCount || nodeRels.value.length) * 3.2 + 12))
})

const allEntityOptions = computed(() => entities.filter((e) => e.type === '疾病').map((e) => e.name))
</script>

<template>
  <div ref="wrap" class="graph-page">
    <div class="mz-page-head">
      <div>
        <div class="mz-page-title">知识图谱可视化</div>
        <div class="mz-page-desc">
          三高及关联疾病的实体关系网络。支持节点拖拽、缩放、平移与点击查看详情；关系点击可查看证据来源与审核状态。
        </div>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="saveImage"><el-icon><Download /></el-icon>保存图片</el-button>
        <el-button @click="toggleFull"><el-icon><FullScreen /></el-icon>全屏</el-button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="mz-card toolbar">
      <el-select v-model="sel.disease" placeholder="全部疾病" clearable style="width: 160px" @change="build">
        <el-option v-for="d in allEntityOptions" :key="d" :label="d" :value="d" />
      </el-select>
      <el-input v-model="sel.keyword" placeholder="实体关键词，如：肥胖" clearable style="width: 200px" @keyup.enter="build">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" @click="build"><el-icon><Search /></el-icon>查询</el-button>
      <el-button @click="reset"><el-icon><RefreshLeft /></el-icon>重置</el-button>
      <div class="mz-toolbar-spacer" />
      <span class="graph-stat">节点 <b>{{ stat.nodes }}</b> 个 · 关系 <b>{{ stat.edges }}</b> 条</span>
      <span class="mz-demo-badge">图谱子集演示</span>
    </div>

    <div class="graph-body">
      <!-- 左侧筛选 -->
      <div class="mz-card filter">
        <div class="f-title">实体类型</div>
        <el-checkbox-group v-model="sel.entityTypes" class="f-group" @change="build">
          <el-checkbox v-for="t in ENTITY_TYPES" :key="t" :value="t" class="f-item">
            <span class="dot" :style="{ background: TYPE_COLOR[t] }" />{{ t }}
          </el-checkbox>
        </el-checkbox-group>

        <div class="f-title">关系类型</div>
        <el-checkbox-group v-model="sel.relationTypes" class="f-group" @change="build">
          <el-checkbox v-for="t in RELATION_TYPES" :key="t" :value="t" class="f-item">
            <span class="line" :style="{ background: RELATION_COLOR[t] }" />{{ t }}
          </el-checkbox>
        </el-checkbox-group>

        <div class="f-title">审核状态</div>
        <el-checkbox-group v-model="sel.statuses" class="f-group" @change="build">
          <el-checkbox v-for="s in REVIEW_STATUS" :key="s" :value="s" class="f-item">{{ s }}</el-checkbox>
        </el-checkbox-group>

        <div class="f-title">节点上限</div>
        <el-slider v-model="sel.limit" :min="30" :max="264" :step="10" size="small" @change="build" />

        <div class="f-legend">
          <div class="lg-title">节点大小</div>
          <div class="lg-desc">疾病节点固定较大圆形；其他节点大小与关联数量正相关。</div>
          <div class="lg-title">连线</div>
          <div class="lg-desc">带箭头表示关系方向，颜色区分关系类型，宽度表示关系权重。</div>
        </div>
      </div>

      <!-- 中间图谱 -->
      <div class="mz-card canvas">
        <BaseChart ref="chartRef" :option="option" height="100%" :loading="loading" @chart-click="onChartClick" />
        <div class="canvas-tip">拖拽节点可调整布局 · 滚轮缩放 · 点击节点 / 关系查看详情</div>
      </div>

      <!-- 右侧详情 -->
      <div class="mz-card side">
        <div class="mz-card-head">
          <div class="mz-card-title">{{ picked.type === 'edge' ? '关系详情' : picked.type === 'node' ? '节点详情' : '详情面板' }}</div>
        </div>

        <div v-if="!picked.type" class="side-empty">
          <el-icon :size="34" color="#d5dbe5"><Pointer /></el-icon>
          <div class="se-title">点击图谱中的节点或关系</div>
          <div class="se-desc">查看实体属性、关联关系与证据来源</div>
        </div>

        <div v-else-if="picked.type === 'node'" class="side-body">
          <div class="node-head">
            <span class="node-dot" :style="{ background: TYPE_COLOR[picked.node.type] }" />
            <div>
              <div class="node-name">{{ picked.node.name }}</div>
              <el-tag size="small" effect="light" :color="TYPE_COLOR[picked.node.type] + '14'" style="border: none; color: inherit">
                {{ picked.node.type }}
              </el-tag>
            </div>
          </div>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="标准名称">{{ picked.node.standardName }}</el-descriptions-item>
            <el-descriptions-item label="别名">
              {{ picked.node.aliases?.length ? picked.node.aliases.join(' / ') : '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="所属疾病">
              {{ picked.node.diseases?.length ? picked.node.diseases.join('、') : '通用实体' }}
            </el-descriptions-item>
            <el-descriptions-item label="数据来源">{{ picked.node.source }}</el-descriptions-item>
            <el-descriptions-item label="审核状态">
              <el-tag size="small" effect="light">{{ picked.node.status }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <div class="metric-row">
            <div class="metric">
              <div class="m-val">{{ nodeImportance }}</div>
              <div class="m-lab">节点重要性</div>
            </div>
            <div class="metric">
              <div class="m-val">{{ new Set(nodeRels.map((r) => (r.headId === picked.node.id ? r.tailId : r.headId))).size }}</div>
              <div class="m-lab">关联实体</div>
            </div>
            <div class="metric">
              <div class="m-val">{{ nodeRels.length }}</div>
              <div class="m-lab">关系数量</div>
            </div>
          </div>

          <div class="side-sub">关联关系（{{ nodeRels.length }}）</div>
          <div class="rel-list">
            <div v-for="r in nodeRels.slice(0, 12)" :key="r.id" class="rel-item" @click="picked.type = 'edge'; picked.edge = { ...r, headName: r.head, tailName: r.tail }">
              <span class="ri-head">{{ r.head }}</span>
              <span class="ri-rel">{{ r.relation }}</span>
              <span class="ri-tail">{{ r.tail }}</span>
            </div>
          </div>
          <el-button class="side-btn" type="primary" plain size="small" @click="focusNode(picked.node.name)">
            以该实体为中心重构子图
          </el-button>
        </div>

        <div v-else class="side-body">
          <div class="edge-head">
            <span class="eh-node">{{ picked.edge.headName || picked.edge.head }}</span>
            <span class="eh-rel">{{ picked.edge.relation }}</span>
            <span class="eh-node">{{ picked.edge.tailName || picked.edge.tail }}</span>
          </div>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="关系 ID">{{ picked.edge.id }}</el-descriptions-item>
            <el-descriptions-item label="证据来源">{{ picked.edge.source }}</el-descriptions-item>
            <el-descriptions-item label="章节 / 页码">{{ picked.edge.section }}</el-descriptions-item>
            <el-descriptions-item label="证据等级">{{ picked.edge.evidenceLevel }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ ((picked.edge.confidence || 0) * 100).toFixed(1) }}%</el-descriptions-item>
            <el-descriptions-item label="审核状态">
              <el-tag size="small" effect="light">{{ picked.edge.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="提取时间">{{ picked.edge.createdAt }}</el-descriptions-item>
          </el-descriptions>
          <div class="side-sub">证据片段</div>
          <div class="snippet">{{ picked.edge.snippet }}</div>
          <el-button class="side-btn" type="primary" plain size="small" @click="$router.push('/kg/review')">
            前往关系审核
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.graph-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--mz-bg);
}
.graph-page:fullscreen {
  padding: 20px;
  overflow: auto;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 12px;
  flex: 0 0 auto;
}
.graph-stat {
  font-size: 12px;
  color: var(--mz-text-sub);
}
.graph-stat b {
  color: var(--mz-primary);
  font-size: 13px;
}
.graph-body {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 560px;
}
.filter {
  width: 190px;
  flex: 0 0 190px;
  padding: 14px 16px;
  overflow-y: auto;
}
.f-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--mz-text);
  margin: 12px 0 8px;
}
.f-title:first-child {
  margin-top: 0;
}
.f-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.f-item {
  height: 24px;
  font-size: 12px;
  margin-right: 0;
}
.f-item :deep(.el-checkbox__label) {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding-left: 6px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}
.line {
  width: 12px;
  height: 2px;
  border-radius: 1px;
  display: inline-block;
}
.f-legend {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed var(--mz-border);
}
.lg-title {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--mz-text-sub);
  margin-bottom: 3px;
}
.lg-desc {
  font-size: 11px;
  color: var(--mz-text-light);
  line-height: 1.6;
  margin-bottom: 10px;
}
.canvas {
  flex: 1;
  min-width: 0;
  position: relative;
  padding: 6px;
  overflow: hidden;
}
.canvas-tip {
  position: absolute;
  left: 14px;
  bottom: 10px;
  font-size: 11px;
  color: var(--mz-text-light);
  background: rgba(255, 255, 255, 0.86);
  padding: 3px 8px;
  border-radius: 4px;
  pointer-events: none;
}
.side {
  width: 286px;
  flex: 0 0 286px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.side-empty {
  padding: 60px 24px;
  text-align: center;
}
.se-title {
  font-size: 12.5px;
  color: var(--mz-text-sub);
  margin-top: 12px;
}
.se-desc {
  font-size: 11.5px;
  color: var(--mz-text-light);
  margin-top: 6px;
  line-height: 1.7;
}
.side-body {
  padding: 16px;
  overflow-y: auto;
}
.node-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 14px;
}
.node-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 7px;
}
.node-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--mz-text);
  margin-bottom: 6px;
  line-height: 1.4;
}
.metric-row {
  display: flex;
  gap: 1px;
  background: var(--mz-border);
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  overflow: hidden;
  margin: 14px 0;
}
.metric {
  flex: 1;
  background: #fafbfd;
  padding: 10px 6px;
  text-align: center;
}
.m-val {
  font-size: 17px;
  font-weight: 600;
  color: #173b70;
  font-variant-numeric: tabular-nums;
}
.m-lab {
  font-size: 10.5px;
  color: var(--mz-text-light);
  margin-top: 3px;
}
.side-sub {
  font-size: 12px;
  font-weight: 600;
  color: var(--mz-text);
  margin: 14px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.rel-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 230px;
  overflow-y: auto;
}
.rel-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #fafbfd;
  border: 1px solid #f0f3f8;
  cursor: pointer;
}
.rel-item:hover {
  background: #f0f5ff;
  border-color: #d6e3fb;
}
.ri-head,
.ri-tail {
  color: var(--mz-text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ri-rel {
  color: #2563eb;
  font-size: 10.5px;
  background: #eff4ff;
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
}
.edge-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 10px;
  background: #f7f9fd;
  border-radius: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.eh-node {
  font-size: 13px;
  font-weight: 600;
  color: #173b70;
}
.eh-rel {
  font-size: 11px;
  color: #fff;
  background: #2563eb;
  border-radius: 4px;
  padding: 2px 8px;
}
.snippet {
  font-size: 12px;
  line-height: 1.9;
  color: #4b5563;
  background: #fafbfd;
  border: 1px solid #eef1f6;
  border-radius: 8px;
  padding: 10px 12px;
}
.side-btn {
  width: 100%;
  margin-top: 14px;
}
</style>
