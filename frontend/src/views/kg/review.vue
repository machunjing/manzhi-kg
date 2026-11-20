<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { fetchReviewList, reviewAction } from '@/api'

const queue = ref<any[]>([])
const activeId = ref('')
const filter = ref('待审核')
const keyword = ref('')
const records = ref<{ id: string; action: string; time: string; note: string }[]>([])
const modified = ref('')

const all = ref<any[]>([])
const loading = ref(false)

async function reload() {
  loading.value = true
  try {
    all.value = await fetchReviewList('', keyword.value)
  } catch (e: any) {
    ElMessage.error(e?.message || '审核队列加载失败')
  } finally {
    loading.value = false
  }
}

async function init() {
  await reload()
  queue.value = all.value.filter((r) => (filter.value ? r.status === filter.value : true))
  if (!queue.value.find((r) => r.id === activeId.value)) activeId.value = queue.value[0]?.id || ''
}

onMounted(init)

const active = computed(() => queue.value.find((r) => r.id === activeId.value) || null)

const headEnt = computed(() => (active.value ? { name: active.value.head, type: active.value.headType } : null))
const tailEnt = computed(() => (active.value ? { name: active.value.tail, type: active.value.tailType } : null))

function pick(r: any) {
  activeId.value = r.id
  modified.value = ''
}

const ACT_MAP: Record<string, 'approve' | 'reject' | 'hold'> = {
  审核通过: 'approve',
  驳回: 'reject',
  修改后通过: 'approve',
  暂缓审核: 'hold'
}

async function act(action: string, note = '') {
  if (!active.value) return
  if (action === '修改后通过' && !modified.value.trim()) {
    return ElMessage.warning('请先在下方填写修改后的关系表述')
  }
  const id = active.value.id
  try {
    const r: any = await reviewAction(id, ACT_MAP[action], note || modified.value)
    records.value.unshift({
      id,
      action,
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
      note: note || modified.value || (action === '驳回' ? '证据不足或关系方向错误' : '—')
    })
    ElMessage.success(`操作「${action}」已写入数据库：${r.from} → ${r.to}`)
    await init()
  } catch (e: any) {
    ElMessage.error(e?.message || '审核操作失败')
  }
}

async function rejectWithReason() {
  try {
    const { value } = await ElMessageBox.prompt('请填写驳回理由（将写入审核日志，供后续追溯）', '驳回关系', {
      inputPlaceholder: '例如：原文仅提及相关性，不支持因果方向',
      inputValidator: (v) => (!!v && v.length >= 4) || '理由不少于 4 个字'
    })
    await act('驳回', value)
  } catch {
    /* cancelled */
  }
}

const counts = computed(() => ({
  待审核: all.value.filter((r) => r.status === '待审核').length,
  已审核: all.value.filter((r) => r.status === '已审核').length,
  已驳回: all.value.filter((r) => r.status === '已驳回').length,
  候选: all.value.filter((r) => r.status === '候选').length
}))
</script>

<template>
  <div>
    <PageHeader title="关系审核" desc="医学关系审核工作台：左侧为候选关系队列，右侧展示原文证据与来源信息。审核结论必须基于原文证据，不得仅凭模型置信度判定。" />

    <div class="review-wrap">
      <!-- 左：候选队列 -->
      <div class="mz-card queue">
        <div class="queue-head">
          <div class="mz-card-title">候选关系</div>
          <span class="mz-total">{{ queue.length }} 条</span>
        </div>
        <div class="queue-filter">
          <el-select v-model="filter" size="small" style="width: 110px" @change="init">
            <el-option label="待审核" value="待审核" />
            <el-option label="候选" value="候选" />
            <el-option label="已审核" value="已审核" />
            <el-option label="已驳回" value="已驳回" />
            <el-option label="全部" value="" />
          </el-select>
          <el-input v-model="keyword" size="small" placeholder="搜索实体" clearable @keyup.enter="init" @clear="init">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="queue-list">
          <div
            v-for="r in queue"
            :key="r.id"
            class="q-item"
            :class="{ active: r.id === activeId }"
            @click="pick(r)"
          >
            <div class="q-top">
              <span class="mz-mono mz-light">{{ r.id }}</span>
              <StatusTag :status="r.status" />
            </div>
            <div class="q-claim">
              <span class="q-node">{{ r.head }}</span>
              <span class="q-rel">{{ r.relation }}</span>
              <span class="q-node">{{ r.tail }}</span>
            </div>
            <div class="q-foot">
              <span>{{ r.disease }}</span>
              <span>置信度 {{ (r.confidence * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div v-if="!queue.length" class="q-empty">当前筛选条件下没有待处理的关系</div>
        </div>
        <div class="queue-stat">
          <div><b>{{ counts['待审核'] }}</b><span>待审核</span></div>
          <div><b>{{ counts['已审核'] }}</b><span>已审核</span></div>
          <div><b>{{ counts['已驳回'] }}</b><span>已驳回</span></div>
        </div>
      </div>

      <!-- 右：证据 -->
      <div class="mz-card detail">
        <template v-if="active">
          <div class="d-top">
            <div class="d-claim">
              <span class="dc-node">{{ active.head }}</span>
              <span class="dc-rel">{{ active.relation }}</span>
              <span class="dc-node">{{ active.tail }}</span>
            </div>
            <div class="d-badges">
              <el-tag size="small" effect="plain">{{ active.disease }}</el-tag>
              <el-tag size="small" :type="active.evidenceLevel.includes('A') ? 'success' : 'warning'" effect="light">
                {{ active.evidenceLevel }}
              </el-tag>
              <StatusTag :status="active.status" />
            </div>
          </div>

          <div class="d-grid">
            <div class="d-cell">
              <div class="c-label">来源文献 / 指南</div>
              <div class="c-value">{{ active.source }}</div>
            </div>
            <div class="d-cell">
              <div class="c-label">章节 / 页码</div>
              <div class="c-value">{{ active.section }}</div>
            </div>
            <div class="d-cell">
              <div class="c-label">提取时间</div>
              <div class="c-value">{{ active.createdAt }}</div>
            </div>
            <div class="d-cell">
              <div class="c-label">模型置信度</div>
              <div class="c-value">
                <el-progress :percentage="Math.round(active.confidence * 100)" :stroke-width="6" :show-text="false" color="#2563EB" style="width: 90px; display: inline-block" />
                <span style="margin-left: 8px">{{ (active.confidence * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>

          <div class="d-sub">原始文本证据</div>
          <div class="evidence">
            <div class="ev-quote">{{ active.snippet }}</div>
            <div class="ev-meta">
              来源：{{ active.source }} · {{ active.section }} · 实体锚点：{{ headEnt?.name }} / {{ tailEnt?.name }}
            </div>
          </div>

          <div class="d-sub">实体校验</div>
          <div class="ent-check">
            <div class="ec-item">
              <span class="ec-label">主体</span>
              <span class="ec-name">{{ headEnt?.name }}</span>
              <span class="ec-type">{{ headEnt?.type }}</span>
            </div>
            <div class="ec-arrow">→</div>
            <div class="ec-item">
              <span class="ec-label">客体</span>
              <span class="ec-name">{{ tailEnt?.name }}</span>
              <span class="ec-type">{{ tailEnt?.type }}</span>
            </div>
          </div>

          <div class="d-sub">修改后表述（仅在「修改后通过」时需要填写）</div>
          <el-input v-model="modified" type="textarea" :rows="2" placeholder="例如：将「导致」修正为「危险因素」" />

          <div class="action-bar">
            <el-button type="success" @click="act('审核通过')"><el-icon><Select /></el-icon>审核通过</el-button>
            <el-button type="danger" plain @click="rejectWithReason"><el-icon><CloseBold /></el-icon>驳回</el-button>
            <el-button type="primary" plain @click="act('修改后通过')"><el-icon><EditPen /></el-icon>修改后通过</el-button>
            <el-button @click="act('暂缓审核')"><el-icon><Timer /></el-icon>暂缓审核</el-button>
            <div class="mz-toolbar-spacer" />
            <span class="mz-light">审核记录将写入系统日志</span>
          </div>
        </template>
        <div v-else class="d-empty">
          <el-icon :size="40" color="#d5dbe5"><CircleCheck /></el-icon>
          <div class="de-title">当前队列已处理完毕</div>
          <div class="de-desc">可切换筛选条件查看其他状态的关系</div>
        </div>

        <div v-if="records.length" class="records">
          <div class="d-sub">本次审核操作记录</div>
          <div v-for="(r, i) in records" :key="i" class="rec">
            <span class="rec-id">{{ r.id }}</span>
            <span class="rec-act">{{ r.action }}</span>
            <span class="rec-note">{{ r.note }}</span>
            <span class="rec-time">{{ r.time }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.review-wrap {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.queue {
  width: 340px;
  flex: 0 0 340px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 200px);
}
.queue-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 10px;
}
.queue-filter {
  display: flex;
  gap: 8px;
  padding: 0 16px 10px;
}
.queue-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}
.q-item {
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: #fff;
}
.q-item:hover {
  border-color: #c7d8f7;
  background: #fafcff;
}
.q-item.active {
  border-color: var(--mz-primary);
  background: #f4f8ff;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.08);
}
.q-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.q-claim {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
}
.q-node {
  font-weight: 600;
  color: #1f2937;
}
.q-rel {
  color: #2563eb;
  background: #eff4ff;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10.5px;
}
.q-foot {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  color: var(--mz-text-light);
  margin-top: 6px;
}
.q-empty {
  padding: 40px 12px;
  text-align: center;
  font-size: 12px;
  color: var(--mz-text-light);
}
.queue-stat {
  display: flex;
  border-top: 1px solid var(--mz-border);
  padding: 10px 0;
}
.queue-stat > div {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.queue-stat b {
  font-size: 15px;
  color: #173b70;
}
.queue-stat span {
  font-size: 10.5px;
  color: var(--mz-text-light);
}
.detail {
  flex: 1;
  min-width: 0;
  padding: 18px 20px;
}
.d-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--mz-border);
  flex-wrap: wrap;
}
.d-claim {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dc-node {
  font-size: 17px;
  font-weight: 600;
  color: #173b70;
}
.dc-rel {
  font-size: 12px;
  color: #fff;
  background: #2563eb;
  padding: 3px 12px;
  border-radius: 5px;
}
.d-badges {
  display: flex;
  gap: 6px;
}
.d-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--mz-border);
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  overflow: hidden;
  margin: 16px 0;
}
.d-cell {
  background: #fafbfd;
  padding: 10px 14px;
}
.c-label {
  font-size: 11px;
  color: var(--mz-text-light);
  margin-bottom: 5px;
}
.c-value {
  font-size: 12.5px;
  color: var(--mz-text);
  line-height: 1.5;
}
.d-sub {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--mz-text);
  margin: 16px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.evidence {
  border: 1px solid #e6ecf6;
  background: #fbfcff;
  border-radius: 8px;
  padding: 14px 16px;
}
.ev-quote {
  font-size: 13px;
  line-height: 2;
  color: #374151;
  border-left: 3px solid #c7d8f7;
  padding-left: 12px;
}
.ev-meta {
  margin-top: 10px;
  font-size: 11px;
  color: var(--mz-text-light);
}
.ent-check {
  display: flex;
  align-items: center;
  gap: 14px;
}
.ec-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fafbfd;
  border: 1px solid var(--mz-border);
  border-radius: 7px;
  padding: 8px 12px;
}
.ec-label {
  font-size: 11px;
  color: var(--mz-text-light);
}
.ec-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--mz-text);
}
.ec-type {
  font-size: 10.5px;
  color: #2563eb;
  background: #eff4ff;
  padding: 1px 6px;
  border-radius: 3px;
}
.ec-arrow {
  color: #9ca3af;
}
.action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--mz-border);
}
.d-empty {
  padding: 80px 20px;
  text-align: center;
}
.de-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--mz-text);
  margin-top: 12px;
}
.de-desc {
  font-size: 12px;
  color: var(--mz-text-light);
  margin-top: 6px;
}
.records {
  margin-top: 8px;
}
.rec {
  display: flex;
  gap: 12px;
  font-size: 11.5px;
  padding: 7px 0;
  border-bottom: 1px dashed #f0f2f6;
  color: var(--mz-text-sub);
}
.rec-id {
  font-family: Consolas, monospace;
  color: var(--mz-text-light);
}
.rec-act {
  color: #2563eb;
  font-weight: 600;
}
.rec-note {
  flex: 1;
}
.rec-time {
  color: var(--mz-text-light);
}
</style>
