<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { queryTasks, DISEASES } from '@/api'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const q = reactive({ keyword: '', status: '', source: '' })

const sources = ['PubMed', 'OpenCMKG', 'DiaKG', '本地指南文件', 'MedlinePlus']
const createDlg = reactive({
  visible: false,
  form: { name: '', source: 'PubMed', disease: '2型糖尿病', type: 'API 接口采集', range: [] as string[], keyword: 'type 2 diabetes AND risk factor', limit: 500 }
})
const logDrawer = reactive({ visible: false, row: {} as any, lines: [] as string[] })

let timer: any = null

async function load() {
  loading.value = true
  const r = await queryTasks({ ...q, page: page.value, pageSize: pageSize.value })
  list.value = r.list
  total.value = r.total
  loading.value = false
  if (r.list.some((t: any) => t.status === '运行中') && !timer) startTick()
}

function startTick() {
  timer = setInterval(() => {
    list.value.forEach((t) => {
      if (t.status === '运行中') {
        t.progress = Math.min(99, t.progress + 2)
        t.count += Math.floor(Math.random() * 12)
        if (t.progress >= 99) {
          t.status = '已完成'
          t.progress = 100
          t.endAt = '2026-11-04 10:30'
          ElMessage.success(`任务 ${t.id} 采集完成，共入库 ${t.count} 条`)
        }
      }
    })
  }, 2600)
}
onMounted(load)
onUnmounted(() => timer && clearInterval(timer))

const stats = computed(() => ({
  total: total.value,
  running: list.value.filter((t) => t.status === '运行中').length + 1,
  done: list.value.filter((t) => t.status === '已完成').length * 3,
  failed: list.value.filter((t) => t.status === '失败').length
}))

function search() {
  page.value = 1
  load()
}
function reset() {
  Object.assign(q, { keyword: '', status: '', source: '' })
  search()
}

function openCreate() {
  createDlg.visible = true
}
function submitCreate() {
  if (!createDlg.form.name) return ElMessage.warning('请填写任务名称')
  const t = {
    id: 'T2026' + String(Math.floor(100 + Math.random() * 900)),
    name: createDlg.form.name,
    source: createDlg.form.source,
    collectType: createDlg.form.type,
    disease: createDlg.form.disease,
    startAt: '2026-11-04 10:20',
    endAt: '',
    count: 0,
    status: '运行中',
    progress: 5,
    keyword: createDlg.form.keyword,
    operator: '马春静'
  }
  list.value.unshift(t)
  total.value++
  createDlg.visible = false
  ElMessage.success('采集任务已创建并启动（演示环境模拟状态，不访问真实外部 API）')
  if (!timer) startTick()
}

function pause(row: any) {
  if (row.status === '运行中') {
    row.status = '已暂停'
    ElMessage.warning('任务已暂停')
  } else if (row.status === '已暂停') {
    row.status = '运行中'
    ElMessage.success('任务已恢复运行')
  } else {
    ElMessage.info('仅运行中 / 已暂停的任务可执行此操作')
  }
}
function start(row: any) {
  if (row.status === '已完成') return ElMessage.info('任务已完成，无需重复启动')
  row.status = '运行中'
  row.progress = row.progress || 8
  ElMessage.success('任务已启动')
  if (!timer) startTick()
}
async function retry(row: any) {
  try {
    await ElMessageBox.confirm(`重新执行失败任务「${row.name}」？将从上次断点继续采集。`, '失败任务重试', { type: 'warning' })
    row.status = '运行中'
    row.progress = 10
    row.count = 0
    ElMessage.success('已重新提交采集任务')
  } catch {
    /* cancelled */
  }
}
function viewLog(row: any) {
  logDrawer.row = row
  const base = [
    `[10:12:01] INFO  任务 ${row.id} 初始化，数据来源 = ${row.source}`,
    `[10:12:02] INFO  检索式：${row.keyword}`,
    `[10:12:04] INFO  目标疾病：${row.disease}，时间范围：2020-01-01 ~ 2026-11-01`,
    `[10:12:09] INFO  分页请求第 1/10 批（每批 50 条）`,
    `[10:13:22] INFO  累计获取 ${row.count || 120} 条记录，去重后保留 ${Math.round((row.count || 120) * 0.92)} 条`,
    `[10:14:40] INFO  写入 03_清洗后数据/解析结构化JSON/pubmed_records.json`,
    `[10:14:41] INFO  触发文本切块（300/50）与实体抽取`
  ]
  if (row.status === '失败') {
    base.push('[10:15:02] ERROR 外部接口返回 429（请求频率超限），任务终止')
    base.push('[10:15:02] ERROR 建议：降低并发、增加重试间隔后重新执行')
  } else if (row.status === '运行中') {
    base.push(`[10:15:30] INFO  当前进度 ${row.progress}%，持续采集中…`)
  } else {
    base.push(`[10:16:10] INFO  任务结束，状态 = ${row.status}，共入库 ${row.count} 条`)
  }
  logDrawer.lines = base
  logDrawer.visible = true
}
</script>

<template>
  <div>
    <PageHeader title="数据采集任务" desc="编排多源数据采集任务并跟踪进度。未接入真实采集后端，任务状态与进度为模拟演示，不会访问外部 API。">
      <template #actions>
        <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新建采集任务</el-button>
      </template>
    </PageHeader>

    <div class="mz-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 16px">
      <StatCard title="任务总数" :value="stats.total" unit="个" icon="List" color="#2563EB" />
      <StatCard title="运行中任务" :value="stats.running" unit="个" icon="Loading" color="#0891B2" trend="实时模拟进度" />
      <StatCard title="已完成任务" :value="stats.done" unit="个" icon="CircleCheck" color="#16A34A" />
      <StatCard title="失败任务" :value="stats.failed" unit="个" icon="WarningFilled" color="#DC2626" trend="可重试" />
    </div>

    <div class="mz-card">
      <div class="mz-toolbar">
        <el-input v-model="q.keyword" placeholder="任务编号 / 任务名称" clearable style="width: 200px" @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="q.source" placeholder="数据来源" clearable>
          <el-option v-for="s in sources" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="q.status" placeholder="任务状态" clearable>
          <el-option v-for="s in ['运行中', '已完成', '失败', '已暂停']" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <div class="mz-toolbar-spacer" />
        <span class="mz-demo-badge">演示数据 · 非真实采集</span>
      </div>

      <el-table v-loading="loading" :data="list" style="width: 100%">
        <el-table-column prop="id" label="任务编号" width="96" />
        <el-table-column prop="name" label="任务名称" min-width="170" show-overflow-tooltip />
        <el-table-column prop="source" label="数据来源" width="100" />
        <el-table-column prop="collectType" label="采集类型" width="104" />
        <el-table-column prop="disease" label="目标疾病" width="92" />
        <el-table-column prop="startAt" label="开始时间" width="124" />
        <el-table-column label="完成时间" width="124">
          <template #default="{ row }">{{ row.endAt || '—' }}</template>
        </el-table-column>
        <el-table-column prop="count" label="采集数量" width="82" align="right" />
        <el-table-column label="任务状态" width="110">
          <template #default="{ row }">
            <div class="status-cell">
              <StatusTag :status="row.status" />
              <el-progress
                v-if="row.status === '运行中'"
                :percentage="row.progress"
                :stroke-width="4"
                :show-text="false"
                color="#2563EB"
                style="margin-top: 5px"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="152" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="start(row)" v-if="row.status !== '运行中'">启动</el-button>
            <el-button link type="warning" size="small" @click="pause(row)" v-if="['运行中', '已暂停'].includes(row.status)">
              {{ row.status === '运行中' ? '暂停' : '恢复' }}
            </el-button>
            <el-button link type="primary" size="small" @click="viewLog(row)">日志</el-button>
            <el-button v-if="row.status === '失败'" link type="danger" size="small" @click="retry(row)">重试</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState text="暂无采集任务" icon="List" /></template>
      </el-table>

      <div class="mz-table-foot">
        <span class="mz-total">共 {{ total }} 个任务</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next"
          background
          @current-change="load"
          @size-change="search"
        />
      </div>
    </div>

    <!-- 新建任务 -->
    <el-dialog v-model="createDlg.visible" title="新建采集任务" width="600px">
      <el-form :model="createDlg.form" label-width="96px">
        <el-form-item label="任务名称" required>
          <el-input v-model="createDlg.form.name" placeholder="例如：高血压 · PubMed 文献采集" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-radio-group v-model="createDlg.form.source">
            <el-radio-button v-for="s in sources" :key="s" :value="s">{{ s }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="目标疾病">
          <el-select v-model="createDlg.form.disease" style="width: 100%">
            <el-option v-for="d in DISEASES" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="采集类型">
          <el-select v-model="createDlg.form.type" style="width: 100%">
            <el-option label="API 接口采集" value="API 接口采集" />
            <el-option label="本地文件解析" value="本地文件解析" />
            <el-option label="知识图谱导入" value="知识图谱导入" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="createDlg.form.range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="检索关键词">
          <el-input v-model="createDlg.form.keyword" type="textarea" :rows="2" placeholder="支持布尔检索式，例如 type 2 diabetes AND risk factor" />
        </el-form-item>
        <el-form-item label="最大采集量">
          <el-input-number v-model="createDlg.form.limit" :min="50" :max="5000" :step="50" />
          <span class="mz-light" style="margin-left: 10px">条</span>
        </el-form-item>
      </el-form>
      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 4px">
        演示环境不会真实请求 PubMed 接口，任务启动后以模拟进度展示，入库数量为演示值。
      </el-alert>
      <template #footer>
        <el-button @click="createDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建并启动</el-button>
      </template>
    </el-dialog>

    <!-- 日志抽屉 -->
    <el-drawer v-model="logDrawer.visible" :title="`采集日志 · ${logDrawer.row.id || ''}`" size="600px">
      <div class="log-head">
        <span>{{ logDrawer.row.name }}</span>
        <StatusTag :status="logDrawer.row.status || '运行中'" />
      </div>
      <pre class="log-box">{{ logDrawer.lines.join('\n') }}</pre>
      <div class="log-note">日志为模拟输出，真实接入后由采集服务写入 collect_log.json。</div>
    </el-drawer>
  </div>
</template>

<style scoped>
.status-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.log-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--mz-border);
  font-size: 13px;
  font-weight: 600;
}
.log-box {
  margin: 14px 0 0;
  background: #0f2544;
  color: #c9d8ee;
  border-radius: 8px;
  padding: 14px 16px;
  font-family: Consolas, Monaco, monospace;
  font-size: 11.5px;
  line-height: 1.9;
  white-space: pre-wrap;
  max-height: 520px;
  overflow: auto;
}
.log-note {
  margin-top: 12px;
  font-size: 11.5px;
  color: var(--mz-text-light);
}
</style>
