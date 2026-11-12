<script setup>
import { api, formatBytes } from '../api.js';

defineProps({ files: { type: Array, default: () => [] } });
</script>

<template>
  <section>
    <div class="section-head">
      <h2>已通过检查 <span class="count">{{ files.length }}</span></h2>
      <p class="muted">只有这里的文件可以通过普通下载接口取回</p>
    </div>
    <table v-if="files.length" class="table">
      <thead>
        <tr>
          <th>原始文件名</th><th>扩展名</th><th>实际识别类型</th><th>浏览器 MIME</th>
          <th>大小</th><th>SHA-256</th><th>ZIP 条目 / 解压量</th><th>上传时间</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="f in files" :key="f.id">
          <td class="fname">{{ f.originalName }}</td>
          <td>{{ f.extension || '—' }}</td>
          <td><span class="badge badge-blue">{{ (f.detectedType || '').toUpperCase() }}</span></td>
          <td class="muted">{{ f.browserMime || '—' }}</td>
          <td>{{ formatBytes(f.sizeBytes) }}</td>
          <td class="mono hash" :title="f.sha256">{{ f.sha256.slice(0, 12) }}…</td>
          <td v-if="f.detectedType === 'zip'">
            {{ f.zipEntries }} 条 / {{ formatBytes(f.zipTotalBytes) }}
          </td>
          <td v-else class="muted">—</td>
          <td class="muted">{{ f.createdAt }}</td>
          <td>
            <a class="btn btn-small" :href="api.downloadUrl(f.id)">下载</a>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">暂无通过检查的文件</p>
  </section>
</template>
