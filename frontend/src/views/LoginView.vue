<script setup>
// 登录/注册页：居中卡片式，真实接口对接（T1.1）
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { setUser } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const mode = ref('login') // 'login' | 'register'
const form = reactive({ username: '', password: '' })
const validated = ref(false)
const submitting = ref(false)
const errorMsg = ref('')

function switchMode(m) {
  mode.value = m
  errorMsg.value = ''
  validated.value = false
}

async function onSubmit() {
  validated.value = true
  // Bootstrap 5 原生校验样式：invalid-feedback 按需展示
  const formEl = document.querySelector('.needs-validation')
  if (!formEl.checkValidity()) return

  submitting.value = true
  errorMsg.value = ''
  try {
    const path = mode.value === 'login' ? '/api/auth/login' : '/api/auth/register'
    // 注册成功即登录（后端 201 并写入会话）
    const user = await api.post(path, {
      username: form.username,
      password: form.password,
    })
    setUser(user)
    const redirect = route.query.redirect
    router.push(typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//') && !redirect.startsWith('/login') ? redirect : '/notes')
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page d-flex align-items-center justify-content-center min-vh-100">
    <div class="zh-card login-card p-4 p-md-5">
      <div class="text-center mb-4">
        <span class="brand-badge-lg">智</span>
        <h1 class="h4 mt-3 mb-1">智汇笔记</h1>
        <p class="text-muted small mb-0">一处记录，多形态复用</p>
      </div>

      <ul class="nav nav-pills nav-justified mb-4">
        <li class="nav-item">
          <a
            class="nav-link"
            :class="{ active: mode === 'login' }"
            href="#"
            @click.prevent="switchMode('login')"
            >登 录</a
          >
        </li>
        <li class="nav-item">
          <a
            class="nav-link"
            :class="{ active: mode === 'register' }"
            href="#"
            @click.prevent="switchMode('register')"
            >注 册</a
          >
        </li>
      </ul>

      <div v-if="errorMsg" class="alert alert-danger py-2 small mb-3">{{ errorMsg }}</div>

      <form class="needs-validation" novalidate @submit.prevent="onSubmit">
        <div class="mb-3">
          <label class="form-label" for="username">用户名</label>
          <input
            id="username"
            v-model.trim="form.username"
            type="text"
            class="form-control"
            :class="{ 'is-invalid': validated && !form.username }"
            placeholder="请输入用户名"
            required
          />
          <div class="invalid-feedback">请输入用户名</div>
        </div>

        <div class="mb-4">
          <label class="form-label" for="password">密码</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            class="form-control"
            :class="{ 'is-invalid': validated && !form.password }"
            placeholder="至少 6 位"
            required
          />
          <div class="invalid-feedback">请输入密码（至少 6 位）</div>
        </div>

        <button type="submit" class="btn btn-primary w-100" :disabled="submitting">
          {{
            submitting
              ? '处理中…'
              : mode === 'login'
                ? '登 录'
                : '注册并进入'
          }}
        </button>

        <p v-if="mode === 'login'" class="text-center text-muted small mt-4 mb-0">
          演示账号 <code>demo</code> / <code>demo123456</code>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  background: linear-gradient(135deg, #e6f2f0 0%, #f5f7f8 60%);
}

.login-card {
  width: 100%;
  max-width: 400px;
}

.brand-badge-lg {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0d7a6f, #35b8a9);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
}

/* 选项卡主色跟随主题 */
.nav-pills .nav-link.active {
  background-color: var(--zh-brand);
}
</style>
