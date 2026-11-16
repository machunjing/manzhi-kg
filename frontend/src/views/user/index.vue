<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { queryUsers } from '@/api'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const q = reactive({ keyword: '', role: '', status: '' })

const stats = ref({ total: 0, admin: 0, normal: 0, today: 0 })

const dialog = reactive({ visible: false, mode: 'add' as 'add' | 'edit' })
const formRef = ref<FormInstance>()
const form = reactive({ id: '', name: '', account: '', role: '普通用户', phone: '', email: '', dept: '知识工程组', status: '启用' })

const drawer = reactive({ visible: false, row: {} as any })

async function load() {
  loading.value = true
  const r = await queryUsers({ ...q, page: page.value, pageSize: pageSize.value })
  list.value = r.list
  total.value = r.total
  loading.value = false
  const all = await queryUsers({ page: 1, pageSize: 999 })
  stats.value = {
    total: all.total,
    admin: all.list.filter((u: any) => u.role === '管理员').length,
    normal: all.list.filter((u: any) => u.role === '普通用户').length,
    today: 3
  }
}

onMounted(load)

function search() {
  page.value = 1
  load()
}
function reset() {
  q.keyword = ''
  q.role = ''
  q.status = ''
  search()
}

function openAdd() {
  dialog.mode = 'add'
  Object.assign(form, { id: '', name: '', account: '', role: '普通用户', phone: '', email: '', dept: '知识工程组', status: '启用' })
  dialog.visible = true
}
function openEdit(row: any) {
  dialog.mode = 'edit'
  Object.assign(form, row)
  dialog.visible = true
}
function submit() {
  if (!form.name || !form.account) {
    ElMessage.warning('请填写用户名称与登录账号')
    return
  }
  if (dialog.mode === 'add') {
    list.value.unshift({ ...form, id: 'U' + Math.floor(1000 + Math.random() * 9000), createdAt: '2026-11-04 10:20', lastLogin: '-' })
    total.value++
    ElMessage.success('新增用户成功（演示数据，仅前端生效）')
  } else {
    const i = list.value.findIndex((u) => u.id === form.id)
    if (i > -1) list.value[i] = { ...list.value[i], ...form }
    ElMessage.success('用户信息已更新')
  }
  dialog.visible = false
}

async function toggleStatus(row: any) {
  const next = row.status === '启用' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${next}用户「${row.name}」？${next === '禁用' ? '禁用后该账号将无法登录。' : ''}`, '状态变更', {
      type: 'warning',
      confirmButtonText: '确认' + next,
      cancelButtonText: '取消'
    })
    row.status = next
    ElMessage.success(`已${next}该用户`)
  } catch {
    /* cancelled */
  }
}

async function resetPwd(row: any) {
  try {
    await ElMessageBox.confirm(`将用户「${row.name}」的密码重置为初始密码？`, '重置密码', { type: 'warning' })
    ElMessage.success('密码已重置为 Mz@2026（演示操作）')
  } catch {
    /* cancelled */
  }
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`删除用户「${row.name}」后不可恢复，确认删除？`, '删除用户', {
      type: 'error',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消'
    })
    list.value = list.value.filter((u) => u.id !== row.id)
    total.value--
    ElMessage.success('用户已删除')
  } catch {
    /* cancelled */
  }
}

const roleOptions = ['管理员', '普通用户']
const depts = ['知识工程组', '数据治理组', '平台运维组', '医学审核组']
</script>

<template>
  <div>
    <PageHeader title="用户管理" desc="管理平台账号、角色与启用状态。演示环境中的新增 / 编辑 / 删除仅作用于前端状态，不会写入真实数据库。">
      <template #actions>
        <el-button type="primary" @click="openAdd"><el-icon><Plus /></el-icon>新增用户</el-button>
      </template>
    </PageHeader>

    <div class="mz-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 16px">
      <StatCard title="用户总数" :value="stats.total" unit="人" icon="User" color="#2563EB" />
      <StatCard title="管理员数量" :value="stats.admin" unit="人" icon="Avatar" color="#7C3AED" />
      <StatCard title="普通用户数量" :value="stats.normal" unit="人" icon="UserFilled" color="#0891B2" />
      <StatCard title="今日新增用户" :value="stats.today" unit="人" icon="Plus" color="#16A34A" trend="较昨日 +1" trend-type="up" />
    </div>

    <div class="mz-card">
      <div class="mz-toolbar">
        <el-input v-model="q.keyword" placeholder="用户名称 / 账号 / ID" clearable @keyup.enter="search">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="q.role" placeholder="用户角色" clearable>
          <el-option v-for="r in roleOptions" :key="r" :label="r" :value="r" />
        </el-select>
        <el-select v-model="q.status" placeholder="用户状态" clearable>
          <el-option label="启用" value="启用" />
          <el-option label="禁用" value="禁用" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <div class="mz-toolbar-spacer" />
        <span class="mz-total">共 {{ total }} 条记录</span>
      </div>

      <el-table v-loading="loading" :data="list" style="width: 100%" row-key="id">
        <el-table-column prop="id" label="用户ID" width="78" />
        <el-table-column label="头像" width="60" align="center">
          <template #default="{ row }">
            <el-avatar :size="26" class="row-avatar">{{ row.avatar || row.name.slice(0, 1) }}</el-avatar>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="用户名称" width="86" />
        <el-table-column prop="account" label="登录账号" width="96" />
        <el-table-column label="用户角色" width="88">
          <template #default="{ row }">
            <el-tag size="small" :type="row.role === '管理员' ? 'primary' : 'info'" effect="light">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="联系方式" width="104" />
        <el-table-column prop="dept" label="所属部门" width="98" />
        <el-table-column prop="createdAt" label="创建时间" width="126" />
        <el-table-column prop="lastLogin" label="最后登录" width="140" />
        <el-table-column label="状态" width="74">
          <template #default="{ row }"><StatusTag :status="row.status" /></template>
        </el-table-column>
        <el-table-column label="操作" width="176" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="drawer.row = row; drawer.visible = true">查看</el-button>
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-dropdown trigger="click" style="margin-left: 8px">
              <el-button link type="primary" size="small">更多<el-icon><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="toggleStatus(row)">{{ row.status === '启用' ? '禁用账号' : '启用账号' }}</el-dropdown-item>
                  <el-dropdown-item @click="resetPwd(row)">重置密码</el-dropdown-item>
                  <el-dropdown-item divided @click="remove(row)">删除用户</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <div class="mz-table-foot">
        <span class="mz-total">第 {{ page }} 页 · 每页 {{ pageSize }} 条</span>
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

    <!-- 新增 / 编辑 -->
    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'add' ? '新增用户' : '编辑用户'" width="520px">
      <el-form ref="formRef" :model="form" label-width="88px" label-position="right">
        <el-form-item label="用户名称" required>
          <el-input v-model="form.name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="登录账号" required>
          <el-input v-model="form.account" placeholder="字母或数字组合" :disabled="dialog.mode === 'edit'" />
        </el-form-item>
        <el-form-item label="用户角色">
          <el-radio-group v-model="form.role">
            <el-radio value="管理员">管理员</el-radio>
            <el-radio value="普通用户">普通用户</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="所属部门">
          <el-select v-model="form.dept" style="width: 100%">
            <el-option v-for="d in depts" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="form.phone" placeholder="手机号（演示数据脱敏展示）" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="用于接收系统通知" />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-switch v-model="form.status" active-value="启用" inactive-value="禁用" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawer.visible" title="用户详情" size="420px">
      <div v-if="drawer.row.id" class="detail">
        <div class="detail-head">
          <el-avatar :size="52" class="row-avatar">{{ drawer.row.name.slice(0, 1) }}</el-avatar>
          <div>
            <div class="detail-name">{{ drawer.row.name }}</div>
            <div class="mz-muted">{{ drawer.row.role }} · {{ drawer.row.dept }}</div>
          </div>
        </div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="用户 ID">{{ drawer.row.id }}</el-descriptions-item>
          <el-descriptions-item label="登录账号">{{ drawer.row.account }}</el-descriptions-item>
          <el-descriptions-item label="联系方式">{{ drawer.row.phone }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ drawer.row.email }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ drawer.row.createdAt }}</el-descriptions-item>
          <el-descriptions-item label="最后登录">{{ drawer.row.lastLogin }}</el-descriptions-item>
          <el-descriptions-item label="账号状态"><StatusTag :status="drawer.row.status" /></el-descriptions-item>
        </el-descriptions>
        <div class="drawer-note">该账号的问答记录、审核记录可在「问答历史」「系统日志」中按用户筛选查看。</div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.row-avatar {
  background: #e8effc;
  color: #2563eb;
  font-weight: 600;
  font-size: 12px;
}
.detail-head {
  display: flex;
  gap: 12px;
  align-items: center;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--mz-border);
}
.detail-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}
.drawer-note {
  margin-top: 16px;
  font-size: 12px;
  color: var(--mz-text-light);
  line-height: 1.7;
  background: #f8fafc;
  border: 1px dashed var(--mz-border);
  border-radius: 8px;
  padding: 10px 12px;
}
</style>
