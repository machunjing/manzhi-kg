<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import { shortestPath, fetchHotEntities, TYPE_COLOR } from '@/api'

const from = ref('糖尿病')
const to = ref('高血压')
const maxLen = ref(3)
const result = ref<any>(null)
const searched = ref(false)
const loading = ref(false)

// 下拉框用真库里的热门疾病，避免选了库里没有的实体导致「未找到路径」
const diseases = ref<string[]>(['糖尿病', '高血压', '血脂异常', '肥胖', '脂肪肝', '冠心病'])

async function search() {
  if (from.value === to.value) return ElMessage.warning('起始疾病与目标疾病不能相同')
  loading.value = true
  try {
    result.value = await shortestPath(from.value, to.value, maxLen.value)
    searched.value = true
    if (!result.value) ElMessage.info('在给定跳数内未找到关联路径，可增加最大路径长度后重试')
  } catch (e: any) {
    result.value = null
    searched.value = true
    ElMessage.error(e?.message || '路径查询失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const hot = await fetchHotEntities('疾病', 18)
    if (hot.length) {
      diseases.value = hot.map((e: any) => e.name)
      // 保证默认的起止疾病在列表里
      if (!diseases.value.includes(from.value)) diseases.value.unshift(from.value)
      if (!diseases.value.includes(to.value)) diseases.value.unshift(to.value)
    }
  } catch {
    /* 拿不到热度榜就用内置列表，不影响查询 */
  }
  search()
})

function swap() {
  const t = from.value
  from.value = to.value
  to.value = t
  search()
}

const chain = computed(() => {
  if (!result.value?.length) return []
  const out: any[] = [{ name: result.value[0].from.name, type: result.value[0].from.type }]
  result.value.forEach((s: any) => {
    out.push({ relation: s.relation, rel: s.rel, name: s.to.name, type: s.to.type })
  })
  return out
})

const examples = [
  ['糖尿病', '高血压'],
  ['肥胖', '脂肪肝'],
  ['脂肪肝', '高血压'],
  ['糖尿病', '冠心病']
]
</script>

<template>
  <div>
    <PageHeader title="关联路径分析" desc="计算两个疾病在知识图谱中的最短关联路径。路径仅由图谱中真实存在的关系构成，不虚构医学因果链。" />

    <div class="path-wrap">
      <!-- 左：条件 -->
      <div class="mz-card left">
        <div class="mz-card-head"><div class="mz-card-title">路径条件</div></div>
        <div class="left-body">
          <div class="field">
            <div class="f-label">起始疾病</div>
            <el-select v-model="from" style="width: 100%">
              <el-option v-for="d in diseases" :key="d" :label="d" :value="d" />
            </el-select>
          </div>
          <div class="swap-row">
            <el-button circle size="small" @click="swap"><el-icon><Sort /></el-icon></el-button>
          </div>
          <div class="field">
            <div class="f-label">目标疾病</div>
            <el-select v-model="to" style="width: 100%">
              <el-option v-for="d in diseases" :key="d" :label="d" :value="d" />
            </el-select>
          </div>
          <div class="field">
            <div class="f-label">最大路径长度 <span class="f-val">{{ maxLen }} 跳</span></div>
            <el-slider v-model="maxLen" :min="1" :max="5" :step="1" show-stops size="small" />
          </div>
          <el-button type="primary" style="width: 100%; margin-top: 6px" :loading="loading" @click="search">
            <el-icon><Search /></el-icon>查询路径
          </el-button>

          <div class="f-label" style="margin-top: 22px">常用查询</div>
          <div class="examples">
            <div v-for="e in examples" :key="e.join()" class="example" @click="from = e[0]; to = e[1]; search()">
              <span>{{ e[0] }}</span>
              <el-icon><Right /></el-icon>
              <span>{{ e[1] }}</span>
            </div>
          </div>

          <el-alert type="info" :closable="false" style="margin-top: 20px">
            路径用于展示知识图谱中的关联链条，不等同于临床因果推断。
          </el-alert>
        </div>
      </div>

      <!-- 右：结果 -->
      <div class="mz-card right">
        <div class="mz-card-head">
          <div class="mz-card-title">路径可视化</div>
          <span v-if="result" class="mz-card-sub">共 {{ result.length }} 跳 · {{ result.length + 1 }} 个节点</span>
        </div>

        <div v-if="!searched" class="empty">
          <el-icon :size="38" color="#d5dbe5"><Share /></el-icon>
          <div>请设置起止疾病后查询</div>
        </div>

        <div v-else-if="!result" class="empty">
          <el-icon :size="38" color="#d5dbe5"><Search /></el-icon>
          <div>未找到符合条件的关联路径</div>
          <div class="em-desc">可尝试增大最大路径长度，或更换起止疾病</div>
        </div>

        <div v-else class="chain-box">
          <div class="chain">
            <template v-for="(c, i) in chain" :key="i">
              <div v-if="c.relation" class="link">
                <div class="link-rel">{{ c.relation }}</div>
                <div class="link-arrow">
                  <span class="line" />
                  <el-icon class="arrow"><CaretRight /></el-icon>
                </div>
              </div>
              <div class="node" :class="{ disease: c.type === '疾病' }">
                <span class="n-dot" :style="{ background: TYPE_COLOR[c.type] || '#94A3B8' }" />
                <span class="n-name">{{ c.name }}</span>
                <span class="n-type">{{ c.type }}</span>
              </div>
            </template>
          </div>

          <div class="seg-title">逐段关系与证据来源</div>
          <div v-for="(s, i) in result" :key="i" class="seg">
            <div class="seg-no">{{ i + 1 }}</div>
            <div class="seg-main">
              <div class="seg-claim">
                <span class="sc-node">{{ s.from.name }}</span>
                <span class="sc-rel">{{ s.relation }}</span>
                <span class="sc-node">{{ s.to.name }}</span>
              </div>
              <div class="seg-meta">
                <el-tag size="small" effect="plain">{{ s.rel.evidenceLevel }}</el-tag>
                <span>{{ s.rel.source }}</span>
                <span class="mz-light">{{ s.rel.section }}</span>
                <span class="mz-light">置信度 {{ (s.rel.confidence * 100).toFixed(1) }}%</span>
              </div>
              <div class="seg-snip">{{ s.rel.snippet }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.path-wrap {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.left {
  width: 320px;
  flex: 0 0 320px;
}
.left-body {
  padding: 18px;
}
.field {
  margin-bottom: 14px;
}
.f-label {
  font-size: 12px;
  color: var(--mz-text-sub);
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
}
.f-val {
  color: var(--mz-primary);
  font-weight: 600;
}
.swap-row {
  display: flex;
  justify-content: center;
  margin: -6px 0 8px;
}
.examples {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.example {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--mz-text-sub);
  padding: 7px 10px;
  border: 1px dashed var(--mz-border);
  border-radius: 6px;
  cursor: pointer;
}
.example:hover {
  border-color: #c7d8f7;
  color: var(--mz-primary);
  background: #fafcff;
}
.right {
  flex: 1;
  min-width: 0;
  min-height: 560px;
}
.empty {
  padding: 120px 20px;
  text-align: center;
  font-size: 12.5px;
  color: var(--mz-text-light);
  line-height: 1.9;
}
.em-desc {
  font-size: 11.5px;
  margin-top: 4px;
}
.chain-box {
  padding: 24px 24px 20px;
}
.chain {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 22px 20px;
  background: #fafcff;
  border: 1px solid #eef2f9;
  border-radius: 10px;
}
.node {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  padding: 8px 12px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
}
.node.disease {
  border-color: #f3c9c9;
  background: #fffafa;
}
.n-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.n-name {
  font-size: 12.5px;
  font-weight: 600;
  color: #1f2937;
}
.n-type {
  font-size: 10px;
  color: var(--mz-text-light);
}
.link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 84px;
}
.link-rel {
  font-size: 10px;
  color: #2563eb;
  background: #eff4ff;
  padding: 1px 7px;
  border-radius: 3px;
  white-space: nowrap;
}
.link-arrow {
  display: flex;
  align-items: center;
  width: 100%;
  justify-content: center;
}
.line {
  height: 1px;
  background: #c7d8f7;
  flex: 1;
}
.arrow {
  color: #93b4f5;
  font-size: 12px;
  margin-left: -3px;
}
.seg-title {
  font-size: 12.5px;
  font-weight: 600;
  margin: 22px 0 12px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.seg {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px dashed #eef1f6;
}
.seg:last-child {
  border-bottom: none;
}
.seg-no {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #eff4ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 22px;
}
.seg-main {
  flex: 1;
  min-width: 0;
}
.seg-claim {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.sc-node {
  font-size: 13px;
  font-weight: 600;
  color: #173b70;
}
.sc-rel {
  font-size: 11px;
  color: #fff;
  background: #2563eb;
  padding: 2px 9px;
  border-radius: 4px;
}
.seg-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 11px;
  color: var(--mz-text-sub);
  margin: 8px 0;
  flex-wrap: wrap;
}
.seg-snip {
  font-size: 11.5px;
  line-height: 1.85;
  color: #6b7280;
  background: #fafbfd;
  border: 1px solid #f0f3f8;
  border-radius: 6px;
  padding: 8px 11px;
}
</style>
