<script setup>
import { onMounted, ref } from 'vue'
import { api } from './api'
import RuleList from './components/RuleList.vue'
import RunList from './components/RunList.vue'
import RunDetail from './components/RunDetail.vue'

const view = ref('rules') // rules | runs | detail
const selectedRunId = ref(null)
const rules = ref([])

async function refreshRules() {
  rules.value = await api.listRules()
}

function openRun(runId) {
  selectedRunId.value = runId
  view.value = 'detail'
}

onMounted(refreshRules)
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <h1>网页采集与变更追踪</h1>
      <nav>
        <button :class="{ active: view === 'rules' }" @click="view = 'rules'">采集规则</button>
        <button :class="{ active: view === 'runs' }" @click="view = 'runs'">运行记录</button>
        <button v-if="view === 'detail'" class="active">运行详情 #{{ selectedRunId }}</button>
      </nav>
    </header>
    <main>
      <RuleList v-if="view === 'rules'" :rules="rules" @refresh="refreshRules" @started="openRun" />
      <RunList v-else-if="view === 'runs'" :rules="rules" @open="openRun" />
      <RunDetail v-else :run-id="selectedRunId" @back="view = 'runs'" />
    </main>
  </div>
</template>
