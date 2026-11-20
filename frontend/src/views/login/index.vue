<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const user = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ account: 'admin', password: 'demo1234', remember: true })
const rules: FormRules = {
  account: [{ required: true, message: '请输入登录账号', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入登录密码', trigger: 'blur' },
    { min: 6, message: '密码长度不少于 6 位', trigger: 'blur' }
  ]
}

async function submit() {
  if (!formRef.value) return
  const ok = await formRef.value.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    await new Promise((r) => setTimeout(r, 520))
    user.login(form.account.trim(), form.password, form.remember)
    ElMessage.success('登录成功，正在进入工作台')
    router.replace((route.query.redirect as string) || '/dashboard')
  } catch (e: any) {
    ElMessage.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- 左：品牌与主张 -->
    <section class="login-left">
      <svg class="net" viewBox="0 0 620 620" preserveAspectRatio="xMidYMid slice">
        <defs>
          <radialGradient id="glow" cx="50%" cy="45%" r="55%">
            <stop offset="0%" stop-color="#2f6fd0" stop-opacity="0.42" />
            <stop offset="100%" stop-color="#0b2547" stop-opacity="0" />
          </radialGradient>
        </defs>
        <rect width="620" height="620" fill="url(#glow)" />
        <g stroke="#8fb6ee" stroke-opacity="0.28" stroke-width="1">
          <line x1="310" y1="300" x2="180" y2="200" />
          <line x1="310" y1="300" x2="450" y2="215" />
          <line x1="310" y1="300" x2="205" y2="420" />
          <line x1="310" y1="300" x2="455" y2="410" />
          <line x1="310" y1="300" x2="310" y2="140" />
          <line x1="180" y1="200" x2="310" y2="140" />
          <line x1="450" y1="215" x2="310" y2="140" />
          <line x1="205" y1="420" x2="455" y2="410" />
          <line x1="180" y1="200" x2="205" y2="420" />
          <line x1="450" y1="215" x2="455" y2="410" />
          <line x1="310" y1="300" x2="470" y2="300" />
          <line x1="310" y1="300" x2="150" y2="310" />
        </g>
        <g>
          <circle cx="310" cy="300" r="13" fill="#ffffff" />
          <circle cx="310" cy="300" r="24" fill="none" stroke="#ffffff" stroke-opacity="0.32" />
          <circle cx="180" cy="200" r="6.5" fill="#9ec6f7" />
          <circle cx="450" cy="215" r="6.5" fill="#9ec6f7" />
          <circle cx="205" cy="420" r="6.5" fill="#9ec6f7" />
          <circle cx="455" cy="410" r="6.5" fill="#9ec6f7" />
          <circle cx="310" cy="140" r="5" fill="#cfe2fb" />
          <circle cx="470" cy="300" r="5" fill="#cfe2fb" />
          <circle cx="150" cy="310" r="5" fill="#cfe2fb" />
        </g>
      </svg>

      <div class="left-inner">
        <div class="brand-row">
          <div class="logo-lg">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 3v18M3 12h18" stroke="#fff" stroke-width="1.6" stroke-linecap="round" />
              <circle cx="12" cy="12" r="3.2" fill="#fff" />
              <circle cx="12" cy="3" r="1.9" fill="#BFD3FF" />
              <circle cx="12" cy="21" r="1.9" fill="#BFD3FF" />
              <circle cx="3" cy="12" r="1.9" fill="#BFD3FF" />
              <circle cx="21" cy="12" r="1.9" fill="#BFD3FF" />
            </svg>
          </div>
          <span class="brand-name">慢知</span>
        </div>

        <div class="hero">
          <h1 class="hero-title">慢性病<br />智能问答系统</h1>
          <div class="hero-rule" />
          <p class="hero-sub">每个结论，都能查回原文</p>
        </div>

        <div class="left-foot">仅提供医学知识查询，不提供临床诊断与处方建议</div>
      </div>
    </section>

    <!-- 右：登录表单 -->
    <section class="login-right">
      <div class="form-box">
        <h2>欢迎登录</h2>
        <p class="form-sub">请输入账号信息以进入平台工作台</p>

        <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="submit">
          <el-form-item prop="account">
            <el-input v-model="form.account" placeholder="登录账号" clearable>
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="登录密码"
              show-password
              @keyup.enter="submit"
            >
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>

          <div class="form-row">
            <el-checkbox v-model="form.remember">记住登录状态</el-checkbox>
            <span class="forget">忘记密码？请联系管理员</span>
          </div>

          <el-button type="primary" class="login-btn" :loading="loading" @click="submit">
            登 录
          </el-button>
        </el-form>

        <div class="demo-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>演示账号：<b>admin</b> ／ 密码：<b>demo1234</b></span>
        </div>

        <div class="form-foot">慢知 · 慢性病智能问答系统</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
.login-left {
  position: relative;
  flex: 1 1 58%;
  background: linear-gradient(150deg, #173b70 0%, #14315c 45%, #0f2544 100%);
  color: #fff;
  overflow: hidden;
}
.net {
  position: absolute;
  right: -170px;
  bottom: -210px;
  width: 860px;
  height: 860px;
  opacity: 0.5;
  pointer-events: none;
}
.login-left::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(15, 37, 68, 0) 45%, rgba(15, 37, 68, 0.5) 100%);
  pointer-events: none;
}
.left-inner {
  position: relative;
  z-index: 2;
  height: 100%;
  padding: 60px 76px 52px;
  display: flex;
  flex-direction: column;
}
.brand-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.logo-lg {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.24);
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-name {
  font-size: 23px;
  font-weight: 700;
  letter-spacing: 8px;
}

.hero {
  margin: auto 0;
  max-width: 640px;
}
.hero-title {
  margin: 0;
  font-size: clamp(42px, 4.6vw, 66px);
  line-height: 1.22;
  font-weight: 700;
  letter-spacing: 3px;
}
.hero-rule {
  width: 64px;
  height: 3px;
  border-radius: 2px;
  background: #4d8be0;
  margin: 34px 0 26px;
}
.hero-sub {
  margin: 0;
  font-size: clamp(17px, 1.55vw, 22px);
  font-weight: 400;
  letter-spacing: 2px;
  color: rgba(255, 255, 255, 0.76);
}
.left-foot {
  font-size: 12.5px;
  letter-spacing: 0.4px;
  color: rgba(255, 255, 255, 0.4);
}

.login-right {
  flex: 0 0 42%;
  min-width: 440px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.form-box {
  width: 100%;
  max-width: 352px;
}
.form-box h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #173b70;
  letter-spacing: 1px;
}
.form-sub {
  margin: 8px 0 32px;
  font-size: 12.5px;
  color: var(--mz-text-sub);
}
.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2px 0 22px;
}
.forget {
  font-size: 12px;
  color: var(--mz-text-light);
}
.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  letter-spacing: 4px;
  background: #2563eb;
  border-color: #2563eb;
}
.demo-tip {
  margin-top: 22px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4b5563;
  background: #f5f8fe;
  border: 1px solid #e2ebfb;
  border-radius: 7px;
  padding: 9px 12px;
}
.demo-tip b {
  color: #173b70;
  font-family: Consolas, monospace;
}
.form-foot {
  margin-top: 40px;
  font-size: 11px;
  color: #b6bcc7;
  text-align: center;
  line-height: 1.7;
}

@media (max-width: 1280px) {
  .left-inner {
    padding: 48px 56px 44px;
  }
}
@media (max-width: 980px) {
  .login-left {
    display: none;
  }
  .login-right {
    flex: 1 1 100%;
    min-width: 0;
  }
}
</style>
