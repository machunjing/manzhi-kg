import { defineStore } from 'pinia'

const KEY = 'mz-token'
const PROFILE = 'mz-profile'

export interface Profile {
  name: string
  account: string
  role: string
  dept: string
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(KEY) || '',
    profile: JSON.parse(localStorage.getItem(PROFILE) || 'null') as Profile | null
  }),
  getters: {
    isLogin: (s) => !!s.token,
    displayName: (s) => s.profile?.name || '未登录',
    roleName: (s) => s.profile?.role || '游客'
  },
  actions: {
    login(account: string, password: string, remember: boolean) {
      if (account !== 'admin' || password !== 'demo1234') {
        throw new Error('账号或密码错误，请使用演示账号 admin / demo1234')
      }
      this.token = 'demo-token-' + Date.now()
      this.profile = { name: '演示管理员', account: 'admin', role: '管理员', dept: '知识工程组' }
      if (remember) {
        localStorage.setItem(KEY, this.token)
        localStorage.setItem(PROFILE, JSON.stringify(this.profile))
      }
      sessionStorage.setItem(KEY, this.token)
    },
    logout() {
      this.token = ''
      this.profile = null
      localStorage.removeItem(KEY)
      localStorage.removeItem(PROFILE)
      sessionStorage.removeItem(KEY)
    }
  }
})
