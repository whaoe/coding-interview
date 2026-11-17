// 前端 REST API 通信封装层
const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let errText = '请求失败'
    try {
      const data = await res.json()
      errText = data.detail || data.message || errText
    } catch {
      // ignore
    }
    throw new Error(errText)
  }
  return res.json()
}

export const api = {
  getBootstrap: () => request('/bootstrap'),
  listSessions: () => request('/sessions'),
  createSession: (data = {}) =>
    request('/sessions', { method: 'POST', body: JSON.stringify(data) }),
  updateSession: (sessionId, data) =>
    request(`/sessions/${sessionId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSession: (sessionId) =>
    request(`/sessions/${sessionId}`, { method: 'DELETE' }),
  clearSession: (sessionId) =>
    request(`/sessions/${sessionId}/clear`, { method: 'POST' }),
  sendChat: (data) =>
    request('/chat', { method: 'POST', body: JSON.stringify(data) }),
  toggleFavorite: (question) =>
    request('/favorites/toggle', { method: 'POST', body: JSON.stringify({ question }) }),
  getConfig: () => request('/config'),
  updateConfig: (data) =>
    request('/config', { method: 'PUT', body: JSON.stringify(data) }),
  getModels: () => request('/models'),
  setActiveModel: (modelId) =>
    request('/models/active', { method: 'PUT', body: JSON.stringify({ modelId }) }),
  testModel: (data) =>
    request('/models/test', { method: 'POST', body: JSON.stringify(data) }),
  addModel: (data) =>
    request('/models', { method: 'POST', body: JSON.stringify(data) }),
  updateSources: (sources) =>
    request('/sources', { method: 'PUT', body: JSON.stringify({ sources }) }),
  listFeedbacks: () => request('/feedbacks'),
  createFeedback: (data) =>
    request('/feedbacks', { method: 'POST', body: JSON.stringify(data) }),
  updateFeedback: (id, data) =>
    request(`/feedbacks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getSchema: () => request('/schema'),
}
