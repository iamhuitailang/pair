<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import { api } from './api.js';
import UploadPanel from './components/UploadPanel.vue';
import ApprovedTable from './components/ApprovedTable.vue';
import QuarantineTable from './components/QuarantineTable.vue';
import AuditLog from './components/AuditLog.vue';
import SamplesPanel from './components/SamplesPanel.vue';

const tab = ref('approved'); // approved | quarantine | audit | samples
const approved = ref([]);
const quarantine = ref([]);
const logs = ref([]);
const samples = ref([]);
const health = ref(null);
const loading = ref(false);

async function refresh() {
  loading.value = true;
  try {
    const [a, q, l, s, h] = await Promise.all([
      api.listApproved(),
      api.listQuarantine(),
      api.listAudit(100),
      api.listSamples(),
      api.health()
    ]);
    approved.value = a;
    quarantine.value = q;
    logs.value = l;
    samples.value = s;
    health.value = h;
  } finally {
    loading.value = false;
  }
}

let timer = null;
onMounted(() => {
  refresh();
  timer = setInterval(refresh, 5000); // 轻量轮询，保证多窗口状态可见
});
onUnmounted(() => clearInterval(timer));

const tabs = [
  { key: 'approved', label: '已通过' },
  { key: 'quarantine', label: '隔离区' },
  { key: 'audit', label: '状态记录' },
  { key: 'samples', label: '合法样例' }
];
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <h1>本地文件接收与隔离工作台</h1>
      <div v-if="health" class="limits">
        <span>单文件 ≤ {{ (health.limits.maxUploadBytes / 1048576).toFixed(0) }} MiB</span>
        <span>ZIP ≤ {{ health.limits.zipMaxEntries }} 条</span>
        <span>解压总量 ≤ {{ (health.limits.zipMaxTotalBytes / 1048576).toFixed(0) }} MiB</span>
        <span>允许: {{ health.allowedTypes.join(' / ') }}</span>
      </div>
    </header>

    <UploadPanel @changed="refresh" />

    <nav class="tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
      >
        {{ t.label }}
        <span v-if="t.key === 'approved'" class="pill pill-green">{{ approved.length }}</span>
        <span v-if="t.key === 'quarantine'" class="pill pill-red">{{ quarantine.length }}</span>
        <span v-if="t.key === 'audit'" class="pill">{{ logs.length }}</span>
      </button>
      <button class="tab refresh" :disabled="loading" @click="refresh">刷新</button>
    </nav>

    <main class="content">
      <ApprovedTable v-show="tab === 'approved'" :files="approved" />
      <QuarantineTable v-show="tab === 'quarantine'" :files="quarantine" @changed="refresh" />
      <AuditLog v-show="tab === 'audit'" :logs="logs" />
      <SamplesPanel v-show="tab === 'samples'" :samples="samples" />
    </main>

    <footer class="footer muted">
      类型判定基于文件头魔数；存储名由服务端随机生成；页面与接口均不暴露本机绝对路径。
    </footer>
  </div>
</template>
