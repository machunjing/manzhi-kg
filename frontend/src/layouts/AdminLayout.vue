<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import { menuRoutes } from '@/router'

const app = useAppStore()
const user = useUserStore()
const route = useRoute()
const router = useRouter()

const groupIcon: Record<string, string> = {
  首页总览: 'Odometer',
  用户与权限管理: 'UserFilled',
  慢性病知识数据管理: 'Files',
  慢性病知识图谱管理: 'Share',
  慢性病智能问答: 'ChatDotRound',
  慢性病关联分析: 'DataAnalysis',
  系统统计与运行管理: 'Setting'
}

const menus = computed(() =>
  (menuRoutes as any[]).map((r) => {
    const first = r.children ? r.children[0] : r
    return {
      path: r.path,
      title: r.meta.title,
      icon: groupIcon[r.meta.title] || 'Menu',
      single: !r.children,
      entry: first.path,
      children: (r.children || []).map((c: any) => ({ path: c.path, title: c.meta.title }))
    }
  })
)

const activeMenu = computed(() => route.path)
const breadcrumb = computed(() => {
  const g = route.meta.group as string
  const t = route.meta.title as string
  return g && g !== t ? ['慢知平台', g] : ['慢知平台']
})

const notices = ref([
  { id: 1, title: '关系审核队列新增 12 条待审核关系', time: '10 分钟前', type: 'warning' },
  { id: 2, title: '采集任务 T2026004 已完成，入库 486 篇', time: '1 小时前', type: 'success' },
  { id: 3, title: '数据质量检查发现 7 条重复实体', time: '3 小时前', type: 'danger' }
])

function go(path: string) {
  router.push(path)
}

function toggleFull() {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen()
  else document.exitFullscreen()
}

async function onCommand(cmd: string) {
  if (cmd === 'logout') {
    try {
      await ElMessageBox.confirm('确认退出当前登录账号？', '退出登录', {
        type: 'warning',
        confirmButtonText: '退出',
        cancelButtonText: '取消'
      })
      user.logout()
      ElMessage.success('已退出登录')
      router.replace('/login')
    } catch {
      /* cancelled */
    }
  }
}
</script>

<template>
  <div class="mz-layout">
    <!-- 左侧导航 -->
    <aside class="mz-aside" :class="{ 'is-collapsed': app.collapsed }">
      <div class="mz-brand">
        <div class="mz-brand-logo">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 3v18M3 12h18" stroke="#fff" stroke-width="1.6" stroke-linecap="round" />
            <circle cx="12" cy="12" r="3.2" fill="#fff" />
            <circle cx="12" cy="3" r="1.9" fill="#BFD3FF" />
            <circle cx="12" cy="21" r="1.9" fill="#BFD3FF" />
            <circle cx="3" cy="12" r="1.9" fill="#BFD3FF" />
            <circle cx="21" cy="12" r="1.9" fill="#BFD3FF" />
          </svg>
        </div>
        <div v-show="!app.collapsed" class="mz-brand-text">
          <b>慢知</b>
          <span>慢性病智能问答系统</span>
        </div>
      </div>

      <div class="mz-menu-wrap">
        <el-menu
          class="mz-menu"
          :collapse="app.collapsed"
          :default-active="activeMenu"
          :collapse-transition="false"
          unique-opened
          router
        >
          <template v-for="m in menus" :key="m.path">
            <el-menu-item v-if="m.single" :index="m.entry">
              <el-icon><component :is="m.icon" /></el-icon>
              <template #title>{{ m.title }}</template>
            </el-menu-item>
            <el-sub-menu v-else :index="m.path">
              <template #title>
                <el-icon><component :is="m.icon" /></el-icon>
                <span>{{ m.title }}</span>
              </template>
              <el-menu-item v-for="c in m.children" :key="c.path" :index="c.path">
                {{ c.title }}
              </el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>
      </div>

      <div v-show="!app.collapsed" class="aside-foot">
        <div class="foot-line">知识库版本 v1.4.2</div>
        <div class="foot-line">数据快照 2026-11-04</div>
      </div>
    </aside>

    <!-- 右侧主体 -->
    <div class="mz-main">
      <header class="mz-header">
        <div class="header-left">
          <el-button text class="collapse-btn" @click="app.toggleSidebar()">
            <el-icon :size="18"><component :is="app.collapsed ? 'Expand' : 'Fold'" /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="(b, i) in breadcrumb" :key="i">{{ b }}</el-breadcrumb-item>
          </el-breadcrumb>
          <span class="header-title">{{ route.meta.title }}</span>
        </div>

        <div class="header-right">
          <el-tooltip content="当前为前端原型，数据来自本地数据包" placement="bottom">
            <span class="mz-demo-badge">演示数据</span>
          </el-tooltip>

          <el-popover placement="bottom-end" :width="320" trigger="click">
            <template #reference>
              <button class="icon-btn">
                <el-badge :value="notices.length" :max="9">
                  <el-icon :size="17"><Bell /></el-icon>
                </el-badge>
              </button>
            </template>
            <div class="notice-head">消息通知</div>
            <div v-for="n in notices" :key="n.id" class="notice-item">
              <span class="dot" :class="'dot-' + n.type" />
              <div>
                <div class="notice-title">{{ n.title }}</div>
                <div class="notice-time">{{ n.time }}</div>
              </div>
            </div>
          </el-popover>

          <button class="icon-btn" @click="toggleFull">
            <el-icon :size="17"><FullScreen /></el-icon>
          </button>

          <el-dropdown trigger="click" @command="onCommand">
            <div class="user-box">
              <el-avatar :size="28" class="user-avatar">{{ user.displayName.slice(0, 1) }}</el-avatar>
              <div class="user-meta">
                <span class="user-name">{{ user.displayName }}</span>
                <span class="user-role">{{ user.roleName }}</span>
              </div>
              <el-icon :size="12" class="user-arrow"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>账号：{{ user.profile?.account || '-' }}</el-dropdown-item>
                <el-dropdown-item disabled>部门：{{ user.profile?.dept || '-' }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="mz-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.aside-foot {
  padding: 10px 16px 14px;
  border-top: 1px solid var(--mz-border);
}
.foot-line {
  font-size: 10.5px;
  color: #b3bac6;
  line-height: 1.7;
  white-space: nowrap;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.collapse-btn {
  padding: 4px;
  color: #6b7280;
}
.header-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--mz-text);
  padding-left: 12px;
  border-left: 1px solid var(--mz-border);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.icon-btn {
  width: 34px;
  height: 34px;
  border: none;
  background: transparent;
  border-radius: 7px;
  cursor: pointer;
  color: #4b5563;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.icon-btn:hover {
  background: #f3f5f9;
}
.user-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.user-box:hover {
  background: #f3f5f9;
}
.user-avatar {
  background: linear-gradient(135deg, #2563eb, #173b70);
  font-size: 12px;
  font-weight: 600;
}
.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.user-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--mz-text);
}
.user-role {
  font-size: 10.5px;
  color: var(--mz-text-light);
}
.user-arrow {
  color: #9ca3af;
}
.notice-head {
  font-size: 13px;
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--mz-border);
  margin-bottom: 4px;
}
.notice-item {
  display: flex;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px dashed #f0f2f6;
}
.notice-item:last-child {
  border-bottom: none;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 6px;
  flex: 0 0 6px;
}
.dot-warning {
  background: #f59e0b;
}
.dot-success {
  background: #16a34a;
}
.dot-danger {
  background: #dc2626;
}
.notice-title {
  font-size: 12.5px;
  color: var(--mz-text);
  line-height: 1.5;
}
.notice-time {
  font-size: 11px;
  color: var(--mz-text-light);
  margin-top: 2px;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.16s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
