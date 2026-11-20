<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { useRouter } from 'vue-router'
import { queryDocuments, fetchDocDetail, DOC_TYPES, DOC_SOURCES, DISEASES } from '@/api'

const router = useRouter()
const routerPush = () => router.push('/data/tasks')

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const q = reactive({ keyword: '', disease: '', source: '', docType: '', status: '', year: '' })

const drawer = reactive({ visible: false, row: {} as any, chunks: [] as any[], tab: 'meta' })
const editDlg = reactive({ visible: false, row: {} as any })

const years = ['2023', '2024', '2025', '2026']

async function load() {
  loading.value = true
  const r = await queryDocuments({ ...q, page: page.value, pageSize: pageSize.value })
  list.value = r.list
  total.value = r.total
  loading.value = false
}
onMounted(load)

function search() {
  page.value = 1
  load()
}
function reset() {
  Object.assign(q, { keyword: '', disease: '', source: '', docType: '', status: '', year: '' })
  search()
}

async function openDetail(row: any) {
  drawer.row = row
  drawer.chunks = []
  drawer.tab = 'meta'
  drawer.visible = true
  try {
    const d = await fetchDocDetail(row.id)
    drawer.row = { ...row, ...d.doc }
    drawer.chunks = d.chunks
  } catch (e: any) {
    ElMessage.error(e?.message || '文本块加载失败')
  }
}
function openEdit(row: any) {
  editDlg.row = { ...row }
  editDlg.visible = true
}
function saveEdit() {
  const i = list.value.findIndex((d) => d.id === editDlg.row.id)
  if (i > -1) list.value[i] = { ...editDlg.row }
  ElMessage.success('文献元数据已更新（演示环境，仅前端生效）')
  editDlg.visible = false
}
async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`删除文献「${row.title.slice(0, 36)}…」及其 ${row.chunkCount} 个文本块？该操作不可恢复。`, '删除文献', {
      type: 'error',
      confirmButtonText: '确认删除'
    })
    list.value = list.value.filter((d) => d.id !== row.id)
    total.value--
    ElMessage.success('文献已删除')
  } catch {
    /* cancelled */
  }
}
async function reprocess(row: any) {
  try {
    await ElMessageBox.confirm('将重新执行「文本清洗 → 分块 → 向量化 → 实体抽取」流程，确认继续？', '重新处理', { type: 'warning' })
    row.status = '待清洗'
    ElMessage.success('已加入重新处理队列（演示操作）')
  } catch {
    /* cancelled */
  }
}
function copyDoi(row: any) {
  if (!row.doi) return ElMessage.warning('该文献暂无 DOI')
  navigator.clipboard?.writeText(row.doi)
  ElMessage.success('DOI 已复制')
}
</script>

<template>
  <div>
    <PageHeader title="文献与指南管理" :desc="`管理 PubMed 文献与国家级指南原文，查看文本切片与数据处理状态。当前命中 ${total} 篇，语料库共 5,063 篇。`">
      <template #actions>
        <el-button @click="routerPush"><el-icon><Upload /></el-icon>导入文献</el-button>
        <el-button type="primary" @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
      </template>
    </PageHeader>

    <div class="mz-card">
      <div class="mz-toolbar doc-toolbar">
        <el-input v-model="q.keyword" placeholder="文献标题 / PMID / 期刊" clearable style="width: 196px" @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="q.disease" placeholder="疾病分类" clearable>
          <el-option v-for="d in DISEASES" :key="d" :label="d" :value="d" />
        </el-select>
        <el-select v-model="q.source" placeholder="数据来源" clearable>
          <el-option v-for="s in DOC_SOURCES" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="q.docType" placeholder="文献类型" clearable>
          <el-option v-for="t in DOC_TYPES" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="q.year" placeholder="发布时间" clearable style="width: 120px">
          <el-option v-for="y in years" :key="y" :label="y + ' 年'" :value="y" />
        </el-select>
        <el-select v-model="q.status" placeholder="审核状态" clearable style="width: 120px">
          <el-option label="已入库" value="已入库" />
          <el-option label="待清洗" value="待清洗" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="list" style="width: 100%">
        <el-table-column prop="id" label="文献ID" width="96" fixed />
        <el-table-column label="文献标题" min-width="200">
          <template #default="{ row }">
            <div class="doc-title" @click="openDetail(row)">{{ row.title }}</div>
            <div class="doc-sub">
              <span v-if="row.pmid" class="mz-mono">PMID {{ row.pmid }}</span>
              <span v-else class="mz-light">指南原文 PDF</span>
              <span class="dot-sep">·</span>
              <span>{{ row.journal }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="disease" label="疾病分类" width="100" />
        <el-table-column prop="docType" label="文献类型" width="86" />
        <el-table-column prop="source" label="数据来源" width="104" />
        <el-table-column label="发布时间" width="82">
          <template #default="{ row }">{{ String(row.publishDate).slice(0, 4) }}</template>
        </el-table-column>
        <el-table-column prop="chunkCount" label="文本块" width="72" align="right" />
        <el-table-column prop="collectedAt" label="采集时间" width="128" />
        <el-table-column label="数据状态" width="88">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="操作" width="164" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="openDetail(row); drawer.tab = 'chunk'">文本块</el-button>
            <el-dropdown trigger="click" style="margin-left: 8px">
              <el-button link type="primary" size="small">更多<el-icon><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEdit(row)">编辑元数据</el-dropdown-item>
                  <el-dropdown-item @click="reprocess(row)">重新处理</el-dropdown-item>
                  <el-dropdown-item @click="copyDoi(row)">复制 DOI</el-dropdown-item>
                  <el-dropdown-item divided @click="remove(row)">删除文献</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
        <template #empty>
          <EmptyState text="没有匹配的文献" desc="请调整筛选条件后重试" icon="Document" />
        </template>
      </el-table>

      <div class="mz-table-foot">
        <span class="mz-total">共 {{ total }} 条 · 当前第 {{ page }} 页</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next, jumper"
          background
          @current-change="load"
          @size-change="search"
        />
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawer.visible" title="文献详情" size="620px">
      <template v-if="drawer.row.id">
        <div class="d-title">{{ drawer.row.title }}</div>
        <div class="d-meta">
          <el-tag size="small" effect="light">{{ drawer.row.docType }}</el-tag>
          <el-tag size="small" type="info" effect="light">{{ drawer.row.disease }}</el-tag>
          <StatusTag :status="drawer.row.status" />
        </div>

        <el-tabs v-model="drawer.tab" class="d-tabs">
          <el-tab-pane label="元数据" name="meta">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="文献 ID">{{ drawer.row.id }}</el-descriptions-item>
              <el-descriptions-item label="PMID">{{ drawer.row.pmid || '—' }}</el-descriptions-item>
              <el-descriptions-item label="作者">{{ drawer.row.authors }}</el-descriptions-item>
              <el-descriptions-item label="来源">{{ drawer.row.journal }}（{{ drawer.row.source }}）</el-descriptions-item>
              <el-descriptions-item label="DOI / 原文链接">
                <span v-if="drawer.row.doi" class="mz-link" @click="copyDoi(drawer.row)">{{ drawer.row.doi }}</span>
                <span v-else-if="drawer.row.url" class="mz-link">{{ drawer.row.url }}</span>
                <span v-else class="mz-light">暂无</span>
              </el-descriptions-item>
              <el-descriptions-item label="发布时间">{{ drawer.row.publishDate }}</el-descriptions-item>
              <el-descriptions-item label="采集时间">{{ drawer.row.collectedAt }}</el-descriptions-item>
              <el-descriptions-item label="文本块数量">{{ drawer.row.chunkCount }} 块</el-descriptions-item>
            </el-descriptions>

            <div class="d-block-title">摘要</div>
            <div class="d-abstract">{{ drawer.row.abstract || '该文献未提供摘要，需重新采集或人工补录。' }}</div>

            <div v-if="drawer.row.mesh?.length" class="d-block-title">MeSH 主题词</div>
            <div v-if="drawer.row.mesh?.length" class="mesh-wrap">
              <el-tag v-for="m in drawer.row.mesh" :key="m" size="small" type="info" effect="plain" class="mesh-tag">{{ m }}</el-tag>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`文本切片（${drawer.chunks.length}）`" name="chunk">
            <div class="chunk-note">切块策略：300 字滑动窗口，重叠 50 字；用于向量库检索与 RAG 证据引用。</div>
            <div v-if="!drawer.chunks.length">
              <EmptyState text="该文献暂无文本切片" desc="可能尚未完成清洗与分块" icon="Tickets" />
            </div>
            <div v-for="c in drawer.chunks" :key="c.id" class="chunk">
              <div class="chunk-head">
                <span class="mz-mono">#{{ c.chunkIdx ?? c.id }}</span>
                <span class="mz-light">{{ c.textLen }} 字符</span>
              </div>
              <div class="chunk-text">{{ c.text }}</div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>

    <!-- 编辑元数据 -->
    <el-dialog v-model="editDlg.visible" title="编辑文献元数据" width="540px">
      <el-form :model="editDlg.row" label-width="96px">
        <el-form-item label="文献标题">
          <el-input v-model="editDlg.row.title" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="疾病分类">
          <el-select v-model="editDlg.row.disease" style="width: 100%">
            <el-option v-for="d in DISEASES" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="文献类型">
          <el-select v-model="editDlg.row.docType" style="width: 100%">
            <el-option v-for="t in DOC_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="发布时间">
          <el-date-picker v-model="editDlg.row.publishDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="DOI">
          <el-input v-model="editDlg.row.doi" placeholder="无则留空" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.doc-toolbar :deep(.el-input),
.doc-toolbar :deep(.el-select) {
  width: 132px !important;
}
.doc-title {
  font-size: 12.8px;
  color: var(--mz-text);
  line-height: 1.5;
  cursor: pointer;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.doc-title:hover {
  color: var(--mz-primary);
}
.doc-sub {
  font-size: 11px;
  color: var(--mz-text-light);
  margin-top: 3px;
}
.dot-sep {
  margin: 0 6px;
}
.d-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.6;
  color: var(--mz-text);
}
.d-meta {
  display: flex;
  gap: 6px;
  margin: 10px 0 4px;
}
.d-tabs {
  margin-top: 6px;
}
.d-block-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--mz-text);
  margin: 18px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.d-abstract {
  font-size: 12.5px;
  line-height: 1.9;
  color: #4b5563;
  background: #fafbfd;
  border: 1px solid #eef1f6;
  border-radius: 8px;
  padding: 12px 14px;
  max-height: 260px;
  overflow-y: auto;
}
.mesh-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.mesh-tag {
  margin: 0;
}
.chunk-note {
  font-size: 11.5px;
  color: var(--mz-text-light);
  background: #f5f8fe;
  border: 1px solid #e2ebfb;
  border-radius: 7px;
  padding: 8px 12px;
  margin-bottom: 12px;
  line-height: 1.6;
}
.chunk {
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
  background: #fff;
}
.chunk-head {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--mz-text-sub);
  margin-bottom: 6px;
}
.chunk-text {
  font-size: 12px;
  line-height: 1.85;
  color: #4b5563;
}
</style>
