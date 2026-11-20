import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 统一 API 请求封装
 * - VITE_USE_MOCK = 'true'（默认）时走本地 Mock 服务，不发真实请求
 * - 接入后端后设置 VITE_USE_MOCK=false 并配置 VITE_API_BASE，页面代码无需修改
 */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 120000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('mz-token') || sessionStorage.getItem('mz-token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    ElMessage.error(err?.response?.data?.message || err.message || '请求失败')
    return Promise.reject(err)
  }
)

export default http
