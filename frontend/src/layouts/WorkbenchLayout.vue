<script setup>
// 三栏布局之「侧边导航列」：品牌 + 模块导航 + 用户信息（T1.1 接入真实登录态）
import { RouterLink, useRouter } from 'vue-router'
import { api } from '../api'
import { auth, clearUser } from '../stores/auth'
import { requestExit } from '../composables/useUnsaved'

const router = useRouter()

const navItems = [
  { to: '/notes', label: '笔记', icon: '📝' },
  { to: '/todos', label: '待办', icon: '✅' },
  { to: '/mindmaps', label: '思维导图', icon: '🗺️' },
  { to: '/bills', label: '记账', icon: '💰' },
]

async function logout() {
  if (!(await requestExit())) return
  try {
    await api.post('/api/auth/logout')
  } catch {
    // 退出接口失败也照常清理本地登录态
  }
  clearUser()
  router.push('/login')
}
</script>

<template>
  <div class="zh-workbench">
    <aside class="zh-sidebar">
      <div class="brand">
        <span class="brand-badge">智</span>
        <span>智汇笔记</span>
      </div>
      <nav>
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to">
          <span>{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="side-foot">
        <div class="d-flex align-items-center justify-content-between gap-2">
          <span class="text-truncate">👤 {{ auth.user?.username ?? '未登录' }}</span>
          <button class="btn btn-sm btn-outline-light" @click="logout">退出</button>
        </div>
      </div>
    </aside>

    <main class="zh-main">
      <RouterView />
    </main>
  </div>
</template>
