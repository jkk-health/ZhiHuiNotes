// 统一请求封装：同源自动带 Cookie，JSON 序列化，错误统一抛 Error
async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  let data = {}
  try {
    data = await res.json()
  } catch {
    // 空响应体（如 204）
  }

  if (!res.ok) {
    // 会话过期：踢回登录页。/api/auth/* 的 401 是"账密错误"，不跳转
    if (res.status === 401 && !path.startsWith('/api/auth/')) {
      window.location.href = '/login'
    }
    throw new Error(data.error || `请求失败（${res.status}）`)
  }
  return data
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body }),
  put: (path, body) => request(path, { method: 'PUT', body }),
  del: (path) => request(path, { method: 'DELETE' }),
}
