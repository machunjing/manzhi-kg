<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { qaSessions, askQuestion, DISEASES } from '@/api'

const list = ref<any[]>(qaSessions.map((s) => ({ ...s })))
const q = reactive({ keyword: '', disease: '' })
const page = ref(1)
const pageSize = ref(10)
const drawer = reactive({ visible: false, row: {} as any, result: null as any })

const filtered = computed(() =>
  list.value.filter(
    (s) => (!q.keyword || s.title.includes(q.keyword)) && (!q.disease || s.disease === q.disease)
  )
)
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

onMounted(() => {})

async function openDetail(row: any) {
  drawer.row = row
  drawer.result = null
  drawer.visible = true
  drawer.result = await askQuestion(row.title)
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`删除会话「${row.title}」？`, '删除记录', { type: 'warning' })
    list.value = list.value.filter((x) => x.id !== row.id)
    ElMessage.success('已删除')
  } catch {
    /* cancelled */
  }
}

const stats = computed(() => [
  { title: '累计问答会话', value: list.value.length, unit: '个', icon: 'ChatDotRound', color: '#2563EB' },
  { title: '累计问答轮次', value: list.value.reduce((a, s) => a + s.rounds, 0), unit: '轮', icon: 'ChatLineSquare', color: '#0891B2' },
  { title: '覆盖疾病', value: new Set(list.value.map((s) => s.disease)).size, unit: '类', icon: 'FirstAidKit', color: '#7C3AED' },
  { title: '平均检索耗时', value: 1.08, unit: '秒', icon: 'Timer', color: '#16A34A', trend: '演示值' }
])
</script>

<template>
  <div>
    <PageHeader title="问答历史" desc="查看历史会话记录与每次回答的检索链路。演示环境不持久化完整对话内容，点击「检索链路」可复现该问题的检索过程。">
      <template #actions>
        <el-button type="primary" @click="$router.push('/qa/chat')"><el-icon><ChatDotRound /></el-icon>新建对话</el-button>
      </template>
    </PageHeader>

    <div class="mz-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 16px">
      <StatCard v-for="s in stats" :key="s.title" v-bind="s" />
    </div>

    <div class="mz-card">
      <div class="mz-toolbar">
        <el-input v-model="q.keyword" placeholder="问题关键词" clearable style="width: 220px" @keyup.enter="page = 1">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="q.disease" placeholder="关联疾病" clearable>
          <el-option v-for="d in DISEASES" :key="d" :label="d" :value="d" />
        </el-select>
        <el-button type="primary" @click="page = 1">查询</el-button>
        <el-button @click="q.keyword = ''; q.disease = ''; page = 1">重置</el-button>
        <div class="mz-toolbar-spacer" />
        <span class="mz-total">共 {{ filtered.length }} 条记录</span>
      </div>

      <el-table :data="paged" style="width: 100%">
        <el-table-column prop="id" label="会话ID" width="90" />
        <el-table-column prop="title" label="问题" min-width="300" show-overflow-tooltip />
        <el-table-column prop="disease" label="关联疾病" width="110" />
        <el-table-column prop="rounds" label="轮次" width="76" align="center" />
        <el-table-column prop="user" label="提问用户" width="100" />
        <el-table-column prop="createdAt" label="时间" width="136" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">检索链路</el-button>
            <el-button link type="primary" size="small" @click="$router.push('/qa/chat')">继续对话</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="mz-table-foot">
        <span class="mz-total">第 {{ page }} 页</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="filtered.length"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next"
          background
        />
      </div>
    </div>

    <el-drawer v-model="drawer.visible" title="检索链路回溯" size="640px">
      <div v-if="drawer.row.id">
        <div class="hd-q">{{ drawer.row.title }}</div>
        <div class="hd-meta">
          <el-tag size="small" effect="light">{{ drawer.row.disease }}</el-tag>
          <span class="mz-light">{{ drawer.row.createdAt }} · {{ drawer.row.user }}</span>
        </div>

        <template v-if="drawer.result">
          <div class="hd-sub">五阶段检索过程</div>
          <div class="steps">
            <div v-for="(s, i) in drawer.result.steps" :key="i" class="step">
              <div class="step-no">{{ i + 1 }}</div>
              <div>
                <div class="step-name">{{ s.name }}<span class="ms">{{ s.ms }} ms</span></div>
                <div class="step-detail">{{ s.detail }}</div>
              </div>
            </div>
          </div>

          <div class="hd-sub">引用文献（{{ drawer.result.citations.length }}）</div>
          <div v-for="c in drawer.result.citations" :key="c.id" class="cite">
            <span class="c-no">[{{ c.citeNo }}]</span>
            <div>
              <div class="c-title">{{ c.title }}</div>
              <div class="c-meta">{{ c.journal }} · {{ String(c.publishDate).slice(0, 4) }} · {{ c.id }}</div>
            </div>
          </div>

          <div class="hd-sub">图谱路径（{{ drawer.result.path.length }}）</div>
          <div v-for="(p, i) in drawer.result.path" :key="i" class="path">
            <span class="p-node">{{ p.head }}</span>
            <span class="p-rel">{{ p.relation }}</span>
            <span class="p-node">{{ p.tail }}</span>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.hd-q {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.6;
}
.hd-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 8px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--mz-border);
}
.hd-sub {
  font-size: 12.5px;
  font-weight: 600;
  margin: 18px 0 10px;
  padding-left: 8px;
  border-left: 3px solid var(--mz-primary);
}
.steps {
  background: #fbfcff;
  border: 1px solid var(--mz-border);
  border-radius: 8px;
  padding: 10px 14px;
}
.step {
  display: flex;
  gap: 10px;
  padding: 7px 0;
}
.step-no {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #eff4ff;
  color: #2563eb;
  font-size: 10.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 18px;
}
.step-name {
  font-size: 12px;
  font-weight: 600;
  display: flex;
  gap: 8px;
  align-items: center;
}
.ms {
  font-weight: 400;
  font-size: 10.5px;
  color: var(--mz-text-light);
}
.step-detail {
  font-size: 11.5px;
  color: var(--mz-text-sub);
  line-height: 1.7;
  margin-top: 2px;
}
.cite {
  display: flex;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px dashed #f0f2f6;
}
.c-no {
  color: #2563eb;
  font-family: Consolas, monospace;
  font-size: 11.5px;
}
.c-title {
  font-size: 12px;
  color: var(--mz-text);
  line-height: 1.5;
}
.c-meta {
  font-size: 10.5px;
  color: var(--mz-text-light);
  margin-top: 3px;
}
.path {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  background: #f8fafe;
  border: 1px solid #eef2f9;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 6px;
  width: fit-content;
}
.p-node {
  font-weight: 600;
  color: #173b70;
}
.p-rel {
  color: #2563eb;
  background: #eff4ff;
  padding: 1px 7px;
  border-radius: 3px;
  font-size: 10.5px;
}
</style>
