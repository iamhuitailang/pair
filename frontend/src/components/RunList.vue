<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'

const props = defineProps({ rules: { type: Array, default: () => [] } })
const emit = defineEmits(['open'])

const runs = ref([])
const filterRuleId = ref('')
let timer = null

async function refresh() {
  runs.value = await api.listRuns(filterRuleId.value || undefined)
  // 有进行中的运行时持续轮询
  const active = runs.value.some((r) => r.status === 'pending' || r.status === 'running')
  if (active && !timer) timer = setInterval(refresh, 1500)
  if (!active && timer) {
    clearInterval(timer)
    timer = null
  }
}

function fmtTime(ts) {
  return ts ? new Date(ts * 1000).toLocaleString() : '—'
}

onMounted(refresh)
onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <section>
    <div class="section-head">
      <h2>运行记录</h2>
      <div>
        <select v-model="filterRuleId" @change="refresh">
          <option value="">全部规则</option>
          <option v-for="r in rules" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
        <button @click="refresh">刷新</button>
      </div>
    </div>

    <table v-if="runs.length" class="table">
      <thead>
        <tr>
          <th>ID</th><th>规则</th><th>状态</th>
          <th>排队</th><th>处理中</th><th>完成</th>
          <th>新增</th><th>修改</th><th>未变</th><th>消失</th><th>错误</th>
          <th>开始时间</th><th>结束时间</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in runs" :key="r.id">
          <td>{{ r.id }}</td>
          <td>{{ r.rule_name }}</td>
          <td><span class="badge" :class="`run-${r.status}`">{{ r.status }}</span></td>
          <td>{{ r.queued_count }}</td>
          <td>{{ r.processing_count }}</td>
          <td>{{ r.done_count }}</td>
          <td class="st-new">{{ r.new_count }}</td>
          <td class="st-modified">{{ r.modified_count }}</td>
          <td>{{ r.unchanged_count }}</td>
          <td class="st-disappeared">{{ r.disappeared_count }}</td>
          <td class="st-error">{{ r.error_count }}</td>
          <td>{{ fmtTime(r.started_at) }}</td>
          <td>{{ fmtTime(r.finished_at) }}</td>
          <td><button @click="emit('open', r.id)">详情</button></td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">暂无运行记录。</p>
  </section>
</template>
