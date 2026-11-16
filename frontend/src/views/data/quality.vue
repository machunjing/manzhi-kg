<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { fetchOverview, queryEntities, queryRelations, queryDocuments } from '@/api'

const ov = ref<any>({})
const tab = ref('entity')
const loading = ref(false)

const entList = ref<any[]>([])
const relList = ref<any[]>([])
const txtList = ref<any[]>([])
const selectedRels = ref<any[]>([])

const evidenceDlg = ref(false)
const currentRel = ref<any>({})

const sources = [
  { name: 'PubMed E-utilities', type: 'API 接口', docs: 5026, ok: 5026, issue: 3, rate: 99.9, note: '3 篇缺失摘要，需补采' },
  { name: 'MedlinePlus', type: 'API 接口', docs: 31, ok: 31, issue: 0, rate: 100, note: '主题摘要完整' },
  { name: '本地指南 PDF', type: '文件解析', docs: 6, ok: 6, issue: 1, rate: 98.2, note: '1 份 PDF 存在表格跨页，抽取待校验' },
  { name: 'DiaKG', type: '图谱导入', docs: 41, ok: 41, issue: 0, rate: 100, note: 'JSON 结构规范' },
  { name: 'OpenCMKG', type: '图谱导入', docs: 1, ok: 1, issue: 2, rate: 96.5, note: '2 处实体边界歧义' }
]

onMounted(async () => {
  ov.value = await fetchOverview()
  await loadTab()
})

async function loadTab() {
  loading.value = true
  if (tab.value === 'entity') {
    const r = await queryEntities({ status: '待审核', pageSize: 20 })
    entList.value = r.list
  } else if (tab.value === 'relation') {
    const r = await queryRelations({ status: '待审核', pageSize: 20 })
    relList.value = r.list
  } else if (tab.value === 'text') {
    const r = await queryDocuments({ pageSize: 20, status: '待清洗' })
    txtList.value = r.list
  }
  loading.value = false
}

const stats = computed(() => [
  { title: '实体总数', value: ov.value.entityMeshTotal?.toLocaleString(), unit: '个', icon: 'Coin', color: '#2563EB' },
  { title: '实体待审核数', value: ov.value.entityStatus?.['待审核'] || 0, unit: '个', icon: 'Clock', color: '#F59E0B' },
  { title: '候选关系总数', value: ov.value.kgRelationTotal, unit: '条', icon: 'Connection', color: '#7C3AED' },
  { title: '关系待审核数', value: ov.value.kgPending, unit: '条', icon: 'EditPen', color: '#0891B2' },
  { title: '重复数据数', value: 7, unit: '组', icon: 'CopyDocument', color: '#DB2777' },
  { title: '异常数据数', value: 22, unit: '条', icon: 'WarningFilled', color: '#DC2626' }
])

function approveEnt(row: any) {
  row.status = '已审核'
  entList.value = entList.value.filter((e) => e.id !== row.id)
  ElMessage.success(`实体「${row.name}」已通过审核`)
}
function rejectEnt(row: any) {
  row.status = '已驳回'
  entList.value = entList.value.filter((e) => e.id !== row.id)
  ElMessage.warning(`实体「${row.name}」已驳回`)
}

function openEvidence(row: any) {
  currentRel.value = row
  evidenceDlg.value = true
}
function approveRel(row: any) {
  row.status = '已审核'
  relList.value = relList.value.filter((r) => r.id !== row.id)
  ElMessage.success('关系已通过审核')
}
async function rejectRel(row: any) {
  try {
    await ElMessageBox.prompt('请填写驳回理由（将记录到审核日志）', '驳回关系', {
      inputPlaceholder: '例如：原文证据不支持该关系方向',
      inputValidator: (v) => (!!v && v.length >= 4) || '理由不少于 4 个字'
    })
    relList.value = relList.value.filter((r) => r.id !== row.id)
    ElMessage.success('关系已驳回并记录理由')
  } catch {
    /* cancelled */
  }
}

async function batchApprove() {
  if (!selectedRels.value.length) return ElMessage.warning('请先勾选待审核关系')
  try {
    await ElMessageBox.confirm(
      `将批量通过 ${selectedRels.value.length} 条关系。请注意：审核应基于原文证据，不应仅凭模型置信度判定医学关系是否正确。`,
      '批量审核确认',
      { type: 'warning', confirmButtonText: '确认通过' }
    )
    const ids = new Set(selectedRels.value.map((r) => r.id))
    relList.value = relList.value.filter((r) => !ids.has(r.id))
    selectedRels.value = []
    ElMessage.success('批量审核完成')
  } catch {
    /* cancelled */
  }
}

const textIssue = (d: any) => (!d.abstract ? '缺少摘要' : d.abstract.length < 200 ? '摘要过短' : '待重新分块')
</script>

<template>
  <div>
    <PageHeader title="数据质量管理" desc="从实体、关系、文本与数据来源四个维度治理数据质量。关系审核必须结合原文证据，不以模型置信度作为唯一依据。">
      <template #actions>
        <el-button @click="loadTab"><el-icon><Refresh /></el-icon>刷新</el-button>
        <el-button type="primary" @click="$router.push('/kg/review')"><el-icon><EditPen /></el-icon>进入关系审核</el-button>
      </template>
    </PageHeader>

    <div class="mz-grid" style="grid-template-columns: repeat(6, 1fr); margin-bottom: 16px">
      <StatCard v-for="s in stats" :key="s.title" v-bind="s" />
    </div>

    <div class="mz-card">
      <el-tabs v-model="tab" class="q-tabs" @tab-change="loadTab">
        <el-tab-pane label="实体质量检查" name="entity">
          <el-table v-loading="loading" :data="entList" size="small" style="width: 100%">
            <el-table-column prop="name" label="实体名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="type" label="实体类型" width="100" />
            <el-table-column prop="standardName" label="标准名称" min-width="150" show-overflow-tooltip />
            <el-table-column label="别名" min-width="150">
              <template #default="{ row }">
                <span class="mz-light">{{ row.aliases?.length ? row.aliases.join(' / ') : '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="110" />
            <el-table-column label="质量状态" width="100">
              <template #default="{ row }"><StatusTag :status="row.status" /></template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="success" size="small" @click="approveEnt(row)">通过</el-button>
                <el-button link type="danger" size="small" @click="rejectEnt(row)">驳回</el-button>
                <el-button link type="primary" size="small" @click="ElMessage.info('演示环境：实体编辑请在实体管理页面操作')">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="关系质量检查" name="relation">
          <div class="tab-toolbar">
            <el-button type="primary" size="small" :disabled="!selectedRels.length" @click="batchApprove">
              批量审核（{{ selectedRels.length }}）
            </el-button>
            <span class="mz-light">审核前请先查看原文证据，确认关系方向与医学语义正确</span>
          </div>
          <el-table
            v-loading="loading"
            :data="relList"
            size="small"
            style="width: 100%"
            @selection-change="(v: any[]) => (selectedRels = v)"
          >
            <el-table-column type="selection" width="42" />
            <el-table-column prop="head" label="主体实体" min-width="130" show-overflow-tooltip />
            <el-table-column label="关系类型" width="100">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.relation }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="tail" label="客体实体" min-width="130" show-overflow-tooltip />
            <el-table-column prop="source" label="来源文献 / 指南" min-width="180" show-overflow-tooltip />
            <el-table-column label="置信度" width="110">
              <template #default="{ row }">
                <el-progress :percentage="Math.round(row.confidence * 100)" :stroke-width="6" :show-text="false" color="#2563EB" />
                <span class="conf-text">{{ (row.confidence * 100).toFixed(1) }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="审核状态" width="94">
              <template #default="{ row }"><StatusTag :status="row.status" /></template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openEvidence(row)">证据</el-button>
                <el-button link type="success" size="small" @click="approveRel(row)">通过</el-button>
                <el-button link type="danger" size="small" @click="rejectRel(row)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="文本质量检查" name="text">
          <el-table v-loading="loading" :data="txtList" size="small" style="width: 100%">
            <el-table-column prop="id" label="文献ID" width="104" />
            <el-table-column prop="title" label="文献标题" min-width="280" show-overflow-tooltip />
            <el-table-column prop="disease" label="疾病" width="100" />
            <el-table-column label="摘要长度" width="100" align="right">
              <template #default="{ row }">{{ row.abstract?.length || 0 }} 字</template>
            </el-table-column>
            <el-table-column prop="chunkCount" label="文本块" width="80" align="right" />
            <el-table-column label="问题类型" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="!row.abstract ? 'danger' : 'warning'" effect="light">{{ textIssue(row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="$router.push('/data/documents')">查看</el-button>
                <el-button link type="warning" size="small" @click="ElMessage.success('已加入重新处理队列')">重新处理</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="数据来源检查" name="source">
          <el-table :data="sources" size="small" style="width: 100%">
            <el-table-column prop="name" label="数据来源" min-width="180" />
            <el-table-column prop="type" label="接入方式" width="110" />
            <el-table-column prop="docs" label="记录数" width="90" align="right" />
            <el-table-column prop="ok" label="有效记录" width="96" align="right" />
            <el-table-column prop="issue" label="异常数" width="86" align="right" />
            <el-table-column label="完整率" width="140">
              <template #default="{ row }">
                <el-progress :percentage="row.rate" :stroke-width="7" :show-text="false" :color="row.rate >= 99 ? '#16A34A' : '#F59E0B'" />
                <span class="conf-text">{{ row.rate }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="说明" min-width="220" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 证据弹窗 -->
    <el-dialog v-model="evidenceDlg" title="关系证据核验" width="640px">
      <div class="ev-claim">
        <span class="ev-ent">{{ currentRel.head }}</span>
        <span class="ev-rel">{{ currentRel.relation }}</span>
        <span class="ev-ent">{{ currentRel.tail }}</span>
      </div>
      <el-descriptions :column="2" border size="small" style="margin-top: 14px">
        <el-descriptions-item label="来源">{{ currentRel.source }}</el-descriptions-item>
        <el-descriptions-item label="章节">{{ currentRel.section }}</el-descriptions-item>
        <el-descriptions-item label="证据等级">{{ currentRel.evidenceLevel }}</el-descriptions-item>
        <el-descriptions-item label="置信度">{{ ((currentRel.confidence || 0) * 100).toFixed(1) }}%</el-descriptions-item>
        <el-descriptions-item label="提取时间" :span="2">{{ currentRel.createdAt }}</el-descriptions-item>
      </el-descriptions>
      <div class="ev-title">原文证据片段</div>
      <div class="ev-snippet">{{ currentRel.snippet }}</div>
      <el-alert type="warning" :closable="false" show-icon style="margin-top: 12px">
        置信度仅反映模型抽取把握程度，不代表医学正确性；请结合原文语义判断关系方向与因果性。
      </el-alert>
      <template #footer>
        <el-button @click="evidenceDlg = false">关闭</el-button>
        <el-button type="danger" @click="rejectRel(currentRel); evidenceDlg = false">驳回</el-button>
        <el-button type="primary" @click="approveRel(currentRel); evidenceDlg = false">审核通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.q-tabs {
  padding: 0 18px 12px;
}
.q-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}
.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0 12px;
  font-size: 11.5px;
}
.conf-text {
  font-size: 10.5px;
  color: var(--mz-text-light);
}
.ev-claim {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  padding: 16px;
  background: #f7f9fd;
  border-radius: 8px;
}
.ev-ent {
  font-size: 14px;
  font-weight: 600;
  color: #173b70;
}
.ev-rel {
  font-size: 11.5px;
  color: #fff;
  background: #2563eb;
  border-radius: 4px;
  padding: 3px 10px;
}
.ev-title {
  font-size: 12.5px;
  font-weight: 600;
  margin: 16px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.ev-snippet {
  font-size: 12.5px;
  line-height: 1.95;
  color: #4b5563;
  background: #fafbfd;
  border: 1px solid #eef1f6;
  border-radius: 8px;
  padding: 12px 14px;
}
</style>
