<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { queryLogs, users } from '@/api'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const q = reactive({ keyword: '', module: '', user: '', result: '' })
const drawer = reactive({ visible: false, row: {} as any })

const modules = ['用户管理', '文献管理', '实体管理', '关系审核', '智能问答', '数据采集', '系统设置']
const userNames = users.slice(0, 20).map((u) => u.name)

async function load() {
  loading.value = true
  const r = await queryLogs({ ...q, page: page.value, pageSize: pageSize.value })
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
  Object.assign(q, { keyword: '', module: '', user: '', result: '' })
  search()
}
</script>

<template>
  <div>
    <PageHeader title="系统日志" desc="记录用户在平台内的关键操作，用于审计与问题追溯。IP 地址与用户信息为模拟脱敏数据。">
      <template #actions>
        <el-button @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
        <el-button type="primary" @click="ElMessage.success('日志已导出为 CSV（演示操作）')"><el-icon><Download /></el-icon>导出日志</el-button>
      </template>
    </PageHeader>

    <div class="mz-card">
      <div class="mz-toolbar">
        <el-input v-model="q.keyword" placeholder="操作内容 / 用户 / 日志ID" clearable style="width: 220px" @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="q.module" placeholder="操作模块" clearable>
          <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
        </el-select>
        <el-select v-model="q.user" placeholder="操作用户" clearable filterable>
          <el-option v-for="u in userNames" :key="u" :label="u" :value="u" />
        </el-select>
        <el-select v-model="q.result" placeholder="执行结果" clearable style="width: 120px">
          <el-option label="成功" value="成功" />
          <el-option label="失败" value="失败" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <div class="mz-toolbar-spacer" />
        <span class="mz-total">共 {{ total }} 条日志</span>
      </div>

      <el-table v-loading="loading" :data="list" style="width: 100%">
        <el-table-column prop="id" label="日志ID" width="96" />
        <el-table-column prop="user" label="操作用户" width="96" />
        <el-table-column prop="module" label="操作模块" width="104" />
        <el-table-column prop="action" label="操作内容" min-width="260">
          <template #default="{ row }">
            <div class="act-main">{{ row.action }}</div>
            <div class="act-sub">{{ row.detail }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP 地址" width="126">
          <template #default="{ row }"><span class="mz-mono">{{ row.ip }}</span></template>
        </el-table-column>
        <el-table-column prop="time" label="操作时间" width="152" />
        <el-table-column label="执行结果" width="92">
          <template #default="{ row }"><StatusTag :status="row.result" /></template>
        </el-table-column>
        <el-table-column label="操作" width="86" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="drawer.row = row; drawer.visible = true">详情</el-button>
          </template>
        </el-table-column>
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

    <el-drawer v-model="drawer.visible" title="日志详情" size="480px">
      <el-descriptions v-if="drawer.row.id" :column="1" border size="small">
        <el-descriptions-item label="日志 ID">{{ drawer.row.id }}</el-descriptions-item>
        <el-descriptions-item label="操作用户">{{ drawer.row.user }}</el-descriptions-item>
        <el-descriptions-item label="操作模块">{{ drawer.row.module }}</el-descriptions-item>
        <el-descriptions-item label="操作内容">{{ drawer.row.action }}</el-descriptions-item>
        <el-descriptions-item label="IP 地址">{{ drawer.row.ip }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ drawer.row.time }}</el-descriptions-item>
        <el-descriptions-item label="执行结果"><StatusTag :status="drawer.row.result" /></el-descriptions-item>
        <el-descriptions-item label="详细信息">{{ drawer.row.detail }}</el-descriptions-item>
      </el-descriptions>
      <div class="log-note">日志为演示数据，真实环境由后端审计服务写入 MySQL。</div>
    </el-drawer>
  </div>
</template>

<style scoped>
.act-main {
  font-size: 13px;
  color: var(--mz-text);
  line-height: 1.4;
}
.act-sub {
  font-size: 11px;
  color: var(--mz-text-light);
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.log-note {
  margin-top: 14px;
  font-size: 11.5px;
  color: var(--mz-text-light);
}
</style>
