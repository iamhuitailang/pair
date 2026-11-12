<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'

const props = defineProps({ runId: { type: Number, required: true } })
const emit = defineEmits(['back'])

const run = ref(null)
const pages = ref([])
const statusFilter = ref('')
const diffData = ref(null)
const expandedUrl = ref('')
let timer = null

async function refresh() {
  run.value = await api.getRun(props.runId)
  pages.value = await api.runPages(props.runId, statusFilter.value || undefined)
  const active = run.value.status === 'pending' || run.value.status === 'running'
  if (active && !timer) timer = setInterval(refresh, 1500)
  if (!active && timer) {
    clearInterval(timer)
    timer = null
  }
}

async function setFilter(s) {
  statusFilter.value = s
  pages.value = await api.runPages(props.runId, s || undefined)
}

async function loadDiff() {
  diffData.value = await api.runDiff(props.runId)
}

function toggleDiff(url) {
  expandedUrl.value = expandedUrl.value === url ? '' : url
}

const diffFor = computed(() => {
  if (!diffData.value) return {}
  const map = {}
  for (const item of diffData.value.items) map[item.url] = item
  return map
})

function diffClass(line) {
  if (line.startsWith('+') && !line.startsWith('+++')) return 'diff-add'
  if (line.startsWith('-') && !line.startsWith('---')) return 'diff-del'
  if (line.startsWith('@@')) return 'diff-hunk'
  return ''
}

function fmtTime(ts) {
  return ts ? new Date(ts * 1000).toLocaleString() : '—'
}

onMounted(refresh)
onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <section v-if="run">
    <div class="section-head">
      <h2>运行 #{{ run.id }}</h2>
      <div>
        <a class="btn" :href="api.exportUrl(run.id, 'json')" download>导出 JSON</a>
        <a class="btn" :href="api.exportUrl(run.id, 'csv')" download>导出 CSV</a>
        <button @click="loadDiff">与上一轮对比</button>
        <button @click="emit('back')">返回列表</button>
      </div>
    </div>

    <div class="stat-cards">
      <div class="card"><b>{{ run.queued_count }}</b><span>排队</span></div>
      <div class="card"><b>{{ run.processing_count }}</b><span>处理中</span></div>
      <div class="card"><b>{{ run.done_count }}</b><span>完成</span></div>
      <div class="card st-new"><b>{{ run.new_count }}</b><span>新增</span></div>
      <div class="card st-modified"><b>{{ run.modified_count }}</b><span>修改</span></div>
      <div class="card"><b>{{ run.unchanged_count }}</b><span>未变</span></div>
      <div class="card st-disappeared"><b>{{ run.disappeared_count }}</b><span>消失</span></div>
      <div class="card st-error"><b>{{ run.error_count }}</b><span>错误</span></div>
    </div>
    <p class="meta">
      状态：<span class="badge" :class="`run-${run.status}`">{{ run.status }}</span>
      · 开始 {{ fmtTime(run.started_at) }} · 结束 {{ fmtTime(run.finished_at) }}
      <span v-if="diffData?.compare_to"> · 对比基线：运行 #{{ diffData.compare_to }}</span>
    </p>

    <div class="filter-bar">
      <button
        v-for="s in ['', 'new', 'modified', 'unchanged', 'disappeared', 'error']"
        :key="s"
        :class="{ active: statusFilter === s }"
        @click="setFilter(s)"
      >{{ s || '全部' }}</button>
    </div>

    <table class="table">
      <thead>
        <tr><th>URL</th><th>标题</th><th>状态</th><th>更新时间</th><th>HTTP</th><th>深度</th><th></th></tr>
      </thead>
      <tbody>
        <template v-for="p in pages" :key="p.id">
          <tr>
            <td class="mono break">{{ p.url }}</td>
            <td>{{ p.title }}</td>
            <td><span class="badge" :class="`st-${p.status}`">{{ p.status }}</span></td>
            <td>{{ p.updated_at_text || '—' }}</td>
            <td>{{ p.http_status ?? '—' }}</td>
            <td>{{ p.depth }}</td>
            <td>
              <button v-if="diffData" @click="toggleDiff(p.url)">
                {{ expandedUrl === p.url ? '收起' : 'diff' }}
              </button>
            </td>
          </tr>
          <tr v-if="expandedUrl === p.url && diffFor[p.url]" class="diff-row">
            <td colspan="7">
              <pre class="diff"><div
                v-for="(line, i) in diffFor[p.url].diff"
                :key="i"
                :class="diffClass(line)"
              >{{ line }}</div><div v-if="!diffFor[p.url].diff.length" class="diff-none">（内容无差异）</div></pre>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <p v-if="!pages.length" class="empty">暂无页面记录。</p>
  </section>
</template>
