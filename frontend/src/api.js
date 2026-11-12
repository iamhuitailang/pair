const BASE = '/api'

async function request(path, options = {}) {
  const resp = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`${resp.status}: ${text}`)
  }
  if (resp.status === 204) return null
  return resp.json()
}

export const api = {
  listRules: () => request('/rules'),
  createRule: (data) => request('/rules', { method: 'POST', body: JSON.stringify(data) }),
  updateRule: (id, data) => request(`/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRule: (id) => request(`/rules/${id}`, { method: 'DELETE' }),
  startRun: (ruleId) => request(`/rules/${ruleId}/run`, { method: 'POST' }),
  listRuns: (ruleId) => request(ruleId ? `/runs?rule_id=${ruleId}` : '/runs'),
  getRun: (id) => request(`/runs/${id}`),
  runPages: (id, status) => request(`/runs/${id}/pages${status ? `?status=${status}` : ''}`),
  runDiff: (id, compareTo) =>
    request(`/runs/${id}/diff${compareTo ? `?compare_to=${compareTo}` : ''}`),
  exportUrl: (id, format) => `${BASE}/runs/${id}/export?format=${format}`,
}
