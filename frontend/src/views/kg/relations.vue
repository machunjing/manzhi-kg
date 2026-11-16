<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { queryRelations, relations, DISEASES, RELATION_TYPES, REVIEW_STATUS, RELATION_COLOR } from '@/api'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const q = reactive({ keyword: '', relation: '', status: '', disease: '' })

const drawer = reactive({ visible: false, row: {} as any })

async function load() {
  loading.value = true
  const r = await queryRelations({ ...q, page: page.value, pageSize: pageSize.value })
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
  Object.assign(q, { keyword: '', relation: '', status: '', disease: '' })
  search()
}

const typeStat = computed(() =>
  RELATION_TYPES.map((t) => ({ name: t, count: relations.filter((r) => r.relation === t).length, color: RELATION_COLOR[t] })).sort(
    (a, b) => b.count - a.count
  )
)

async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`删除关系「${row.head} → ${row.relation} → ${row.tail}」？删除后图谱中该连线将消失。`, '删除关系', {
      type: 'error',
      confirmButtonText: '确认删除'
    })
    list.value = list.value.filter((r) => r.id !== row.id)
    total.value--
    ElMessage.success('关系已删除')
  } catch {
    /* cancelled */
  }
}
</script>

<template>
  <div>
    <PageHeader title="关系管理" desc="查看与管理知识图谱中的三元组明细。关系类型按实际数据字典动态展示，未虚构不存在的关系类型。">
      <template #actions>
        <el-button @click="$router.push('/kg/review')"><el-icon><EditPen /></el-icon>关系审核</el-button>
        <el-button type="primary" @click="search"><el-icon><Refresh /></el-icon>刷新</el-button>
      </template>
    </PageHeader>

    <div class="type-bar">
      <div v-for="t in typeStat" :key="t.name" class="type-chip">
        <span class="chip-line" :style="{ background: t.color }" />
        <span class="chip-name">{{ t.name }}</span>
        <span class="chip-count">{{ t.count }}</span>
      </div>
    </div>

    <div class="mz-card">
      <div class="mz-toolbar">
        <el-input v-model="q.keyword" placeholder="关系ID / 主体 / 客体" clearable style="width: 200px" @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="q.relation" placeholder="关系类型" clearable>
          <el-option v-for="t in RELATION_TYPES" :key="t" :label="t" :value="t" />
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
        <span class="mz-total">共 {{ total }} 条关系</span>
      </div>

      <el-table v-loading="loading" :data="list" style="width: 100%">
        <el-table-column prop="id" label="关系ID" width="82" />
        <el-table-column prop="head" label="主体实体" min-width="132" show-overflow-tooltip />
        <el-table-column label="关系类型" width="96">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :color="(RELATION_COLOR[row.relation] || '#2563EB') + '14'" style="border: none; color: #374151">
              {{ row.relation }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tail" label="客体实体" min-width="132" show-overflow-tooltip />
        <el-table-column prop="source" label="来源文献 / 指南" min-width="170" show-overflow-tooltip />
        <el-table-column prop="evidenceLevel" label="证据等级" width="94" />
        <el-table-column label="置信度" width="86" align="right">
          <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="审核状态" width="88">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="操作" width="178" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="drawer.row = row; drawer.visible = true">详情</el-button>
            <el-button link type="primary" size="small" @click="$router.push('/kg/graph')">图谱定位</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty><EmptyState text="没有匹配的关系" desc="请调整筛选条件" icon="Connection" /></template>
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

    <el-drawer v-model="drawer.visible" title="关系详情" size="520px">
      <div v-if="drawer.row.id">
        <div class="d-claim">
          <span class="dc-node">{{ drawer.row.head }}</span>
          <span class="dc-rel">{{ drawer.row.relation }}</span>
          <span class="dc-node">{{ drawer.row.tail }}</span>
        </div>
        <el-descriptions :column="1" border size="small" style="margin-top: 14px">
          <el-descriptions-item label="关系 ID">{{ drawer.row.id }}</el-descriptions-item>
          <el-descriptions-item label="所属疾病">{{ drawer.row.disease }}</el-descriptions-item>
          <el-descriptions-item label="来源">{{ drawer.row.source }}</el-descriptions-item>
          <el-descriptions-item label="章节">{{ drawer.row.section }}</el-descriptions-item>
          <el-descriptions-item label="证据等级">{{ drawer.row.evidenceLevel }}</el-descriptions-item>
          <el-descriptions-item label="置信度">{{ (drawer.row.confidence * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="审核状态"><StatusTag :status="drawer.row.status" /></el-descriptions-item>
          <el-descriptions-item label="审核人">{{ drawer.row.reviewer || '—' }}</el-descriptions-item>
          <el-descriptions-item label="提取时间">{{ drawer.row.createdAt }}</el-descriptions-item>
        </el-descriptions>
        <div class="d-sub">证据片段</div>
        <div class="d-snippet">{{ drawer.row.snippet }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.type-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.type-chip {
  display: flex;
  align-items: center;
  gap: 7px;
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: 20px;
  padding: 5px 13px;
  font-size: 12px;
  box-shadow: var(--mz-shadow);
}
.chip-line {
  width: 12px;
  height: 3px;
  border-radius: 2px;
}
.chip-name {
  color: var(--mz-text);
}
.chip-count {
  color: var(--mz-text-sub);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.d-claim {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 16px;
  background: #f7f9fd;
  border-radius: 8px;
  flex-wrap: wrap;
}
.dc-node {
  font-size: 14px;
  font-weight: 600;
  color: #173b70;
}
.dc-rel {
  font-size: 11.5px;
  color: #fff;
  background: #2563eb;
  padding: 3px 10px;
  border-radius: 4px;
}
.d-sub {
  font-size: 12.5px;
  font-weight: 600;
  margin: 16px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.d-snippet {
  font-size: 12.5px;
  line-height: 1.95;
  color: #4b5563;
  background: #fafbfd;
  border: 1px solid #eef1f6;
  border-radius: 8px;
  padding: 12px 14px;
}
</style>
