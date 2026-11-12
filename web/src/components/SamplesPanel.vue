<script setup>
import { api, formatBytes } from '../api.js';

defineProps({ samples: { type: Array, default: () => [] } });
</script>

<template>
  <section>
    <div class="section-head">
      <h2>合法样例</h2>
      <p class="muted">均由后端脚本现场合成（无第三方版权），可直接下载后上传体验检查流程</p>
    </div>
    <div v-if="samples.length" class="sample-grid">
      <div v-for="s in samples" :key="s.file" class="sample-card">
        <div class="sample-name">{{ s.file }}</div>
        <div class="muted">{{ s.description }}</div>
        <div class="muted">{{ formatBytes(s.sizeBytes) }} · {{ s.kind }}</div>
        <a class="btn btn-small" :href="api.sampleDownloadUrl(s.file)">下载样例</a>
      </div>
    </div>
    <p v-else class="empty">样例尚未生成，请在 server 目录执行 npm run samples</p>
  </section>
</template>
