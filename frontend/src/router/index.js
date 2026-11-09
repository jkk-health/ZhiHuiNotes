import { createRouter, createWebHistory } from 'vue-router'
import { auth, fetchMe } from '../stores/auth'

// 路由表：登录页独立，工作台页面共享三栏布局（侧边导航 + 内容区）
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/',
    component: () => import('../layouts/WorkbenchLayout.vue'),
    children: [
      { path: '', redirect: '/notes' },
      { path: 'notes', name: 'notes', component: () => import('../views/NotesView.vue') },
      { path: 'todos', name: 'todos', component: () => import('../views/TodosView.vue') },
      { path: 'mindmaps', name: 'mindmaps', component: () => import('../views/MindmapsView.vue') },
      { path: 'bills', name: 'bills', component: () => import('../views/BillsView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/notes' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (!auth.ready) await fetchMe()
  if (to.name !== 'login' && !auth.user) return { name: 'login', query: { redirect: to.fullPath } }
})

export default router
