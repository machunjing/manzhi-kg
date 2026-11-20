<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { queryEntities, fetchEntityRelations, DISEASES, ENTITY_TYPES, TYPE_COLOR, REVIEW_STATUS } from '@/api'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const q = reactive({ keyword: '', type: '', disease: '', status: '' })

const dlg = reactive({ visible: false, mode: 'add' as 'add' | 'edit', form: {} as any })
const drawer = reactive({ visible: false, row: {} as any, rels: [] as any[] })
const mergeDlg = reactive({ visible: false, source: {} as any, target: '' })

async function load() {
  loading.value = true
  const r = await queryEntities({ ...q, page: page.value, pageSize: pageSize.value })
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
  Object.assign(q, { keyword: '', type: '', disease: '', status: '' })
  search()
}

function openAdd() {
  dlg.mode = 'add'
  dlg.form = { name: '', type: '症状', standardName: '', aliases: [], diseases: [], source: '人工录入', status: '待审核' }
  dlg.visible = true
}
function openEdit(row: any) {
  dlg.mode = 'edit'
  dlg.form = { ...row, aliases: [...(row.aliases || [])], diseases: [...(row.diseases || [])] }
  dlg.visible = true
}
function submit() {
  if (!dlg.form.name) return ElMessage.warning('请填写实体名称')
  dlg.form.standardName = dlg.form.standardName || dlg.form.name
  if (dlg.mode === 'add') {
    list.value.unshift({ ...dlg.form, id: 'E' + Math.floor(1000 + Math.random() * 9000), relCount: 0, createdAt: '2026-11-04' })
    total.value++
    ElMessage.success('实体已新增（演示环境，仅前端生效）')
  } else {
    const i = list.value.findIndex((e) => e.id === dlg.form.id)
    if (i > -1) list.value[i] = { ...dlg.form, relCount: list.value[i].relCount }
    ElMessage.success('实体已更新')
  }
  dlg.visible = false
}
async function openDetail(row: any) {
  drawer.row = row
  drawer.rels = []
  drawer.visible = true
  try {
    drawer.rels = await fetchEntityRelations(row.id, row.name)
  } catch (e: any) {
    ElMessage.error(e?.message || '关联关系加载失败')
  }
}
async function remove(row: any) {
  try {
    await ElMessageBox.confirm(
      `删除实体「${row.name}」将同时移除其 ${row.relCount} 条关联关系，确认删除？`,
      '删除实体',
      { type: 'error', confirmButtonText: '确认删除' }
    )
    list.value = list.value.filter((e) => e.id !== row.id)
    total.value--
    ElMessage.success('实体已删除')
  } catch {
    /* cancelled */
  }
}
function openMerge(row: any) {
  mergeDlg.source = row
  mergeDlg.target = ''
  mergeDlg.visible = true
}
function doMerge() {
  if (!mergeDlg.target) return ElMessage.warning('请选择合并目标实体')
  ElMessage.success(`已将「${mergeDlg.source.name}」合并至「${mergeDlg.target}」，关联关系同步迁移（演示操作）`)
  mergeDlg.visible = false
}
const mergeCandidates = ref<any[]>([])
async function loadCandidates(name: string) {
  const r = await queryEntities({ keyword: name.slice(0, 3), pageSize: 20 })
  mergeCandidates.value = r.list.filter((e) => e.name !== name)
}
</script>

<template>
  <div>
    <PageHeader title="实体管理" desc="管理知识图谱中的疾病、症状、危险因素、并发症、药物类别、检查指标与生活方式实体。当前为图谱演示子集，完整 MeSH 实体共 4,793 个。">
      <template #actions>
        <el-button type="primary" @click="openAdd"><el-icon><Plus /></el-icon>新增实体</el-button>
      </template>
    </PageHeader>

    <div class="mz-card">
      <div class="mz-toolbar">
        <el-input v-model="q.keyword" placeholder="实体名称 / 别名" clearable style="width: 190px" @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="q.type" placeholder="实体类型" clearable>
          <el-option v-for="t in ENTITY_TYPES" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="q.disease" placeholder="所属疾病" clearable>
          <el-option v-for="d in DISEASES" :key="d" :label="d" :value="d" />
        </el-select>
        <el-select v-model="q.status" placeholder="审核状态" clearable style="width: 130px">
          <el-option v-for="s in REVIEW_STATUS" :key="s" :label="s" :value="s" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <div class="mz-toolbar-spacer" />
        <span class="mz-total">共 {{ total }} 个实体</span>
      </div>

      <el-table v-loading="loading" :data="list" style="width: 100%">
        <el-table-column prop="id" label="实体ID" width="88" />
        <el-table-column label="实体名称" min-width="160">
          <template #default="{ row }">
            <span class="e-dot" :style="{ background: TYPE_COLOR[row.type] }" />
            <span class="mz-link" @click="openDetail(row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="实体类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :color="TYPE_COLOR[row.type] + '12'" style="border: none; color: #374151">
              {{ row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="standardName" label="标准名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="别名" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mz-light">{{ row.aliases?.length ? row.aliases.join(' / ') : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="relCount" label="关联关系" width="92" align="right" />
        <el-table-column prop="source" label="数据来源" width="110" />
        <el-table-column label="审核状态" width="92">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="操作" width="196" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="openMerge(row); loadCandidates(row.name)">合并</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState text="没有匹配的实体" desc="请调整筛选条件" icon="Coin" /></template>
      </el-table>

      <div class="mz-table-foot">
        <span class="mz-total">第 {{ page }} 页 · 共 {{ total }} 条</span>
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

    <!-- 新增/编辑 -->
    <el-dialog v-model="dlg.visible" :title="dlg.mode === 'add' ? '新增实体' : '编辑实体'" width="540px">
      <el-form :model="dlg.form" label-width="88px">
        <el-form-item label="实体名称" required><el-input v-model="dlg.form.name" /></el-form-item>
        <el-form-item label="实体类型">
          <el-select v-model="dlg.form.type" style="width: 100%">
            <el-option v-for="t in ENTITY_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="标准名称"><el-input v-model="dlg.form.standardName" placeholder="留空则与实体名称一致" /></el-form-item>
        <el-form-item label="别名">
          <el-select v-model="dlg.form.aliases" multiple filterable allow-create default-first-option placeholder="输入后回车添加" style="width: 100%" />
        </el-form-item>
        <el-form-item label="所属疾病">
          <el-select v-model="dlg.form.diseases" multiple style="width: 100%">
            <el-option v-for="d in DISEASES" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="审核状态">
          <el-select v-model="dlg.form.status" style="width: 100%">
            <el-option v-for="s in REVIEW_STATUS" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 合并 -->
    <el-dialog v-model="mergeDlg.visible" title="合并重复实体" width="480px">
      <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 14px">
        合并后源实体的关联关系将迁移至目标实体，源实体标记为已合并，操作不可撤销。
      </el-alert>
      <el-form label-width="96px">
        <el-form-item label="源实体">
          <el-input :model-value="mergeDlg.source.name" disabled />
        </el-form-item>
        <el-form-item label="合并至">
          <el-select v-model="mergeDlg.target" filterable placeholder="选择目标实体" style="width: 100%">
            <el-option v-for="e in mergeCandidates" :key="e.id" :label="`${e.name}（${e.type}）`" :value="e.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mergeDlg.visible = false">取消</el-button>
        <el-button type="primary" @click="doMerge">确认合并</el-button>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-drawer v-model="drawer.visible" title="实体详情" size="520px">
      <div v-if="drawer.row.id">
        <div class="d-head">
          <span class="e-dot big" :style="{ background: TYPE_COLOR[drawer.row.type] }" />
          <div>
            <div class="d-name">{{ drawer.row.name }}</div>
            <div class="mz-muted">{{ drawer.row.type }} · {{ drawer.row.source }}</div>
          </div>
          <StatusTag :status="drawer.row.status" style="margin-left: auto" />
        </div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="实体 ID">{{ drawer.row.id }}</el-descriptions-item>
          <el-descriptions-item label="标准名称">{{ drawer.row.standardName }}</el-descriptions-item>
          <el-descriptions-item label="别名">{{ drawer.row.aliases?.join(' / ') || '—' }}</el-descriptions-item>
          <el-descriptions-item label="所属疾病">{{ drawer.row.diseases?.join('、') || '通用实体' }}</el-descriptions-item>
          <el-descriptions-item label="关联关系数">{{ drawer.row.relCount }}</el-descriptions-item>
          <el-descriptions-item label="抽取置信度">{{ ((drawer.row.confidence || 0) * 100).toFixed(1) }}%</el-descriptions-item>
        </el-descriptions>
        <div class="d-sub">关联关系（{{ drawer.rels.length }}）</div>
        <div class="rel-list">
          <div v-for="r in drawer.rels" :key="r.id" class="rel-item">
            <span class="ri-h">{{ r.head }}</span>
            <span class="ri-r">{{ r.relation }}</span>
            <span class="ri-t">{{ r.tail }}</span>
          </div>
        </div>
        <el-button type="primary" plain size="small" style="width: 100%; margin-top: 14px" @click="$router.push('/kg/graph')">
          在知识图谱中查看
        </el-button>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.e-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 7px;
  vertical-align: middle;
}
.e-dot.big {
  width: 11px;
  height: 11px;
  margin-right: 0;
  margin-top: 7px;
}
.d-head {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--mz-border);
}
.d-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}
.d-sub {
  font-size: 12.5px;
  font-weight: 600;
  margin: 16px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.rel-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 300px;
  overflow-y: auto;
}
.rel-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  padding: 7px 10px;
  background: #fafbfd;
  border: 1px solid #f0f3f8;
  border-radius: 6px;
}
.ri-h,
.ri-t {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ri-r {
  color: #2563eb;
  background: #eff4ff;
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
  font-size: 10.5px;
}
</style>
