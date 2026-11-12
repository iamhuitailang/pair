// 所有接口走同源 /api；DTO 中不含本机绝对路径
async function request(url, options = {}) {
  const res = await fetch(url, options);
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* 非 JSON 响应 */
  }
  if (!res.ok) {
    const message = body?.error || body?.file?.rejectReason || `请求失败 (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

export const api = {
  health: () => request('/api/health'),
  listApproved: () => request('/api/files').then((r) => r.files),
  listQuarantine: () => request('/api/quarantine').then((r) => r.files),
  listAudit: (limit = 100) => request(`/api/audit?limit=${limit}`).then((r) => r.logs),
  listSamples: () => request('/api/samples').then((r) => r.samples),

  async upload(file) {
    const form = new FormData();
    form.append('file', file);
    // 超限被截断时 multer 拿不到 originalname，附加头仅供留档展示，服务端不采信
    const res = await fetch('/api/upload', {
      method: 'POST',
      headers: { 'x-filename': encodeURIComponent(file.name) },
      body: form
    });
    const body = await res.json();
    if (!res.ok && res.status !== 413) {
      throw new Error(body?.error || `上传失败 (${res.status})`);
    }
    return body;
  },

  deleteQuarantine: (id) => request(`/api/quarantine/${id}`, { method: 'DELETE' }),
  purgeQuarantine: () => request('/api/quarantine/purge', { method: 'POST' }),

  downloadUrl: (id) => `/api/files/${id}/download`,
  sampleDownloadUrl: (name) => `/api/samples/${encodeURIComponent(name)}/download`
};

export function formatBytes(n) {
  if (n == null) return '—';
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB'];
  let v = n;
  let i = -1;
  do {
    v /= 1024;
    i += 1;
  } while (v >= 1024 && i < units.length - 1);
  return `${v.toFixed(v >= 10 ? 1 : 2)} ${units[i]}`;
}
