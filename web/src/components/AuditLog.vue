<script setup>
import { api, formatBytes } from '../api.js';

defineProps({ logs: { type: Array, default: () => [] } });

const EVENT_LABEL = {
  'upload.approved': '上传通过',
  'upload.quarantined': '上传隔离',
  'upload.error': '上传异常',
  'download.ok': '文件下载',
  'download.blocked': '下载拦截',
  'download.missing': '文件缺失',
  'download.error': '下载异常',
  'quarantine.cleanup.deleted': '隔离清理',
  'quarantine.cleanup.blocked': '清理拦截',
  'sample.download': '样例下载'
};
</script>

<template>
  <section>
    <div class="section-head">
      <h2>状态变化记录 <span class="count">{{ logs.length }}</span></h2>
      <p class="muted">所有上传结论、下载与清理动作均留痕；记录中不包含本机绝对路径</p>
    </div>
    <table v-if="logs.length" class="table">
      <thead>
        <tr><th>时间</th><th>事件</th><th>关联文件 ID</th><th>详情</th></tr>
      </thead>
      <tbody>
        <tr v-for="log in logs" :key="log.id">
          <td class="muted nowrap">{{ log.createdAt }}</td>
          <td>
            <span
              class="badge"
              :class="log.event.includes('quarantined') || log.event.includes('blocked')
                ? 'badge-red'
                : log.event.includes('approved') || log.event.includes('ok')
                  ? 'badge-green'
                  : 'badge-gray'"
            >{{ EVENT_LABEL[log.event] || log.event }}</span>
          </td>
          <td class="mono">{{ log.fileId ?? '—' }}</td>
          <td class="reason-cell">{{ log.detail || '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">暂无记录</p>
  </section>
</template>
