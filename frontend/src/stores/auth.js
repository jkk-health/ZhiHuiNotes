// 登录态：模块级 reactive 单例（课程规模无需引入 pinia）
import { reactive } from 'vue'
import { api } from '../api'

export const auth = reactive({
  user: null, // { id, username, created_at } | null
  ready: false, // 是否已向后端确认过登录态（防刷新后闪跳）
})

/** 页面刷新后调用一次，向后端确认会话是否仍有效。 */
export async function fetchMe() {
  try {
    auth.user = await api.get('/api/auth/me')
  } catch {
    auth.user = null
  }
  auth.ready = true
}

/** 登录/注册成功后写入。 */
export function setUser(user) {
  auth.user = user
  auth.ready = true
}

/** 退出登录后清空。 */
export function clearUser() {
  auth.user = null
}
