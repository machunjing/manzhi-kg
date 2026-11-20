<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseChart from '@/components/common/BaseChart.vue'
import { buildDiseaseNetwork, getEntity, getRelation, DISEASES, RELATION_TYPES, TYPE_COLOR, RELATION_COLOR } from '@/api'

const center = ref('糖尿病')
const relTypes = ref<string[]>(['共病', '导致', '危险因素', '并发症'])
const hops = ref(2)
const focusDiseases = ref<string[]>([])
const loading = ref(false)
const option = ref<any>({})
const stat = reactive({ nodes: 0, edges: 0, diseases: 0 })
const picked = reactive({ type: '' as '' | 'node' | 'edge', node: {} as any, edge: {} as any })

const diseaseOnly = ['糖尿病', '高血压', '血脂异常', '冠心病', '肥胖', '脂肪肝']

async function build() {
  loading.value = true
  picked.type = ''
  let g: any = { nodes: [], edges: [] }
  try {
    g = await buildDiseaseNetwork(center.value, relTypes.value, hops.value)
  } catch (e: any) {
    ElMessage.error(e?.message || '关联网络加载失败')
  }
  stat.nodes = g.nodes.length
  stat.edges = g.edges.length
  stat.diseases = g.nodes.filter((n: any) => n.type === '疾病').length
  option.value = {
    tooltip: {
      formatter: (p: any) => {
        if (p.dataType === 'edge') {
          return `${p.data.sourceName} → <b>${p.data.name}</b> → ${p.data.targetName}`
        }
        return `<b>${p.data.name}</b><br/>类型：${p.data.type}<br/>关联数：${p.data.value}`
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'none',
        roam: true,
        draggable: true,
        scaleLimit: { min: 0.4, max: 4 },
        categories: [{ name: '疾病', itemStyle: { color: TYPE_COLOR['疾病'] } }, { name: '其他实体', itemStyle: { color: '#94A3B8' } }],
        data: g.nodes.map((n: any) => {
          const dim =
            focusDiseases.value.length > 0 &&
            n.type === '疾病' &&
            n.name !== center.value &&
            !focusDiseases.value.includes(n.name)
          return {
            ...n,
            category: n.type === '疾病' ? 0 : 1,
            itemStyle: { ...n.itemStyle, opacity: dim ? 0.22 : 1 },
            label: { ...n.label, show: dim ? false : n.label?.show }
          }
        }),
        links: g.edges,
        label: { position: 'right', fontSize: 10.5, color: '#374151' },
        labelLayout: { hideOverlap: true },
        lineStyle: { opacity: 0.5 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 3, opacity: 1 }, label: { show: true, fontWeight: 'bold' } },
        blur: { itemStyle: { opacity: 0.2 }, lineStyle: { opacity: 0.06 } }
      }
    ]
  }
  loading.value = false
}

onMounted(build)

function onClick(p: any) {
  if (p.dataType === 'node') {
    picked.type = 'node'
    picked.node = getEntity(p.data.id) || p.data
  } else if (p.dataType === 'edge') {
    picked.type = 'edge'
    const rel = getRelation(p.data.id) || p.data
    picked.edge = { ...rel, headName: getEntity(rel.headId)?.name || rel.headName, tailName: getEntity(rel.tailId)?.name || rel.tailName }
  }
}

function setCenter(name: string) {
  center.value = name
  build()
}

</script>

<template>
  <div>
    <PageHeader title="疾病关联网络" desc="以中心疾病为核心向外扩展的多跳关联网络。节点大小表示图结构关联数量，连线宽度表示经过定义的关系权重，点击节点与边可查看详情与证据。" />

    <div class="mz-card toolbar">
      <span class="tb-label">中心疾病</span>
      <el-select v-model="center" style="width: 150px" @change="build">
        <el-option v-for="d in diseaseOnly" :key="d" :label="d" :value="d" />
      </el-select>
      <span class="tb-label">关联疾病筛选</span>
      <el-select
        v-model="focusDiseases"
        multiple
        collapse-tags
        clearable
        placeholder="全部关联疾病"
        style="width: 210px"
        @change="build"
      >
        <el-option v-for="d in diseaseOnly" :key="d" :label="d" :value="d" />
      </el-select>
      <span class="tb-label">关系类型</span>
      <el-select v-model="relTypes" multiple collapse-tags style="width: 260px" @change="build">
        <el-option v-for="t in RELATION_TYPES" :key="t" :label="t" :value="t" />
      </el-select>
      <span class="tb-label">扩展跳数</span>
      <el-radio-group v-model="hops" size="small" @change="build">
        <el-radio-button :value="1">1 跳</el-radio-button>
        <el-radio-button :value="2">2 跳</el-radio-button>
        <el-radio-button :value="3">3 跳</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="build"><el-icon><Search /></el-icon>查询</el-button>
      <div class="mz-toolbar-spacer" />
      <span class="mz-total">节点 {{ stat.nodes }} · 连线 {{ stat.edges }} · 疾病 {{ stat.diseases }}</span>
    </div>

    <div class="net-wrap">
      <div class="mz-card canvas">
        <BaseChart :option="option" height="600" :loading="loading" @chart-click="onClick" />
        <div class="legend">
          <div v-for="t in ['疾病', '危险因素', '并发症', '药物类别', '检查指标']" :key="t" class="lg">
            <span class="lg-dot" :style="{ background: TYPE_COLOR[t] }" />{{ t }}
          </div>
        </div>
      </div>

      <div class="mz-card side">
        <div class="mz-card-head">
          <div class="mz-card-title">{{ picked.type === 'edge' ? '关系证据' : picked.type === 'node' ? '节点详情' : '疾病速览' }}</div>
        </div>

        <div v-if="!picked.type" class="quick">
          <div class="q-tip">点击网络中的疾病节点查看详情，或从下方快速切换中心疾病</div>
          <div class="q-list">
            <div v-for="d in diseaseOnly" :key="d" class="q-item" :class="{ on: d === center }" @click="setCenter(d)">
              <span class="q-dot" :style="{ background: TYPE_COLOR['疾病'] }" />
              <span>{{ d }}</span>
              <el-icon v-if="d === center" class="q-check"><Select /></el-icon>
            </div>
          </div>
        </div>

        <div v-else-if="picked.type === 'node'" class="side-body">
          <div class="n-name">{{ picked.node.name }}</div>
          <div class="n-type">
            <span class="n-dot" :style="{ background: TYPE_COLOR[picked.node.type] }" />{{ picked.node.type }}
          </div>
          <el-descriptions :column="1" border size="small" style="margin-top: 12px">
            <el-descriptions-item label="标准名称">{{ picked.node.standardName }}</el-descriptions-item>
            <el-descriptions-item label="别名">{{ picked.node.aliases?.join(' / ') || '—' }}</el-descriptions-item>
            <el-descriptions-item label="所属疾病">{{ picked.node.diseases?.join('、') || '通用' }}</el-descriptions-item>
            <el-descriptions-item label="关联数量">{{ picked.node.value }}</el-descriptions-item>
            <el-descriptions-item label="数据来源">{{ picked.node.source }}</el-descriptions-item>
          </el-descriptions>
          <el-button type="primary" plain size="small" style="width: 100%; margin-top: 14px" @click="setCenter(picked.node.name)">
            设为中心疾病
          </el-button>
        </div>

        <div v-else class="side-body">
          <div class="e-claim">
            <span class="e-node">{{ picked.edge.headName }}</span>
            <span class="e-rel">{{ picked.edge.relation }}</span>
            <span class="e-node">{{ picked.edge.tailName }}</span>
          </div>
          <el-descriptions :column="1" border size="small" style="margin-top: 12px">
            <el-descriptions-item label="关系 ID">{{ picked.edge.id }}</el-descriptions-item>
            <el-descriptions-item label="证据来源">{{ picked.edge.source }}</el-descriptions-item>
            <el-descriptions-item label="章节">{{ picked.edge.section }}</el-descriptions-item>
            <el-descriptions-item label="证据等级">{{ picked.edge.evidenceLevel }}</el-descriptions-item>
            <el-descriptions-item label="置信度">{{ ((picked.edge.confidence || 0) * 100).toFixed(1) }}%</el-descriptions-item>
            <el-descriptions-item label="审核状态">{{ picked.edge.status }}</el-descriptions-item>
          </el-descriptions>
          <div class="e-snip">{{ picked.edge.snippet }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.tb-label {
  font-size: 12px;
  color: var(--mz-text-sub);
  white-space: nowrap;
}
.net-wrap {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.canvas {
  flex: 1;
  min-width: 0;
  position: relative;
  padding: 6px;
}
.legend {
  position: absolute;
  left: 14px;
  bottom: 12px;
  display: flex;
  gap: 14px;
  background: rgba(255, 255, 255, 0.9);
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 11px;
  color: var(--mz-text-sub);
}
.lg {
  display: flex;
  align-items: center;
  gap: 5px;
}
.lg-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.side {
  width: 300px;
  flex: 0 0 300px;
  min-height: 600px;
}
.quick {
  padding: 14px 16px;
}
.q-tip {
  font-size: 11.5px;
  color: var(--mz-text-light);
  line-height: 1.7;
  margin-bottom: 12px;
}
.q-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.q-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--mz-text);
}
.q-item:hover {
  background: #f5f7fb;
}
.q-item.on {
  background: var(--mz-primary-soft);
  color: var(--mz-primary);
  font-weight: 600;
}
.q-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.q-check {
  margin-left: auto;
  font-size: 13px;
}
.side-body {
  padding: 16px;
}
.n-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--mz-text);
}
.n-type {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--mz-text-sub);
  margin-top: 6px;
}
.n-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.e-claim {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  background: #f7f9fd;
  border-radius: 8px;
  padding: 12px 10px;
  flex-wrap: wrap;
}
.e-node {
  font-size: 13px;
  font-weight: 600;
  color: #173b70;
}
.e-rel {
  font-size: 11px;
  color: #fff;
  background: #2563eb;
  padding: 2px 9px;
  border-radius: 4px;
}
.e-snip {
  margin-top: 12px;
  font-size: 12px;
  line-height: 1.9;
  color: #4b5563;
  background: #fafbfd;
  border: 1px solid #eef1f6;
  border-radius: 8px;
  padding: 10px 12px;
}
</style>
