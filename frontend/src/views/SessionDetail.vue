<template>
  <div v-if="detail">
    <p><router-link to="/">← 返回列表</router-link></p>

    <div class="panel">
      <h2>对局 {{ detail.session_id ?? id }}</h2>
      <p>
        <span class="badge" :class="detail.status === 'finished' ? 'ok' : 'warn'">
          {{ detail.status === "finished" ? "已结束" : "进行中" }}
        </span>
        <span v-if="detail.has_anomalies" class="badge err">{{ detail.anomalies.length }} 个异常</span>
        <span v-else class="badge ok">无异常</span>
        <span class="badge">规则版本 {{ detail.rules_version }}</span>
      </p>
      <table>
        <tbody>
          <tr><th>开始时间</th><td>{{ fmtTime(detail.metrics.started_at) }}</td></tr>
          <tr><th>结束时间</th><td>{{ fmtTime(detail.metrics.ended_at) }}</td></tr>
          <tr><th>局时长</th><td>{{ fmtDuration(detail.metrics.duration_seconds) }}</td></tr>
          <tr><th>胜者</th><td>{{ detail.metrics.winner_player_id ?? "-" }}</td></tr>
          <tr><th>事件完整率</th><td>{{ (detail.metrics.completeness * 100).toFixed(1) }}%</td></tr>
          <tr>
            <th>关键行为次数</th>
            <td>
              <span v-for="(n, t) in detail.metrics.action_counts" :key="t" class="badge" style="margin-right:6px">
                {{ t }}: {{ n }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <p style="margin-top: 12px">
        <a class="btn secondary" :href="`/api/sessions/${id}`" :download="`${id}.json`">导出本局 JSON</a>
      </p>
    </div>

    <div class="panel" v-if="detail.anomalies.length">
      <h3>异常列表</h3>
      <table>
        <thead>
          <tr><th>类型</th><th>玩家</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr v-for="(a, i) in detail.anomalies" :key="i">
            <td><span class="badge warn">{{ anomalyLabel(a.type) }}</span></td>
            <td>{{ a.player_id ?? "-" }}</td>
            <td>{{ a.detail }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="panel">
      <h3>事件时间线（{{ detail.timeline.length }} 条）</h3>
      <table>
        <thead>
          <tr>
            <th>#</th><th>时间</th><th>玩家</th><th>类型</th><th>序号</th><th>标记</th><th>payload</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(e, i) in detail.timeline" :key="e.event_id">
            <tr :class="{ flagged: e.flags.length }" class="clickable" @click="toggle(e.event_id)">
              <td>{{ i + 1 }}</td>
              <td>{{ fmtTime(e.occurred_at) }}</td>
              <td>{{ e.player_id }}</td>
              <td>{{ e.event_type }}</td>
              <td>{{ e.sequence }}</td>
              <td>
                <span v-for="f in e.flags" :key="f" class="badge err" style="margin-right:4px">
                  {{ anomalyLabel(f) }}
                </span>
              </td>
              <td>{{ expanded.has(e.event_id) ? "▲ 收起" : "▼ 展开" }}</td>
            </tr>
            <tr v-if="expanded.has(e.event_id)">
              <td></td>
              <td colspan="6"><pre>{{ JSON.stringify(e.payload, null, 2) }}</pre></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
  <p v-else>加载中…</p>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchSessionDetail } from "../api";

const props = defineProps<{ id: string }>();
const detail = ref<any>(null);
const expanded = ref<Set<string>>(new Set());

const LABELS: Record<string, string> = {
  missing_sequence: "缺失序号",
  duplicate_sequence: "重复序号",
  time_regression: "时间倒退",
  unknown_event_type: "未知类型",
};

function anomalyLabel(t: string): string {
  return LABELS[t] ?? t;
}

function toggle(id: string) {
  if (expanded.value.has(id)) expanded.value.delete(id);
  else expanded.value.add(id);
}

function fmtTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : "-";
}

function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}分${s}秒`;
}

onMounted(async () => {
  detail.value = await fetchSessionDetail(props.id);
});
</script>

<style scoped>
tr.flagged {
  background: #fffaf0;
}
pre {
  margin: 4px 0;
  background: #f7f7f7;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 240px;
  overflow: auto;
}
h2 { font-size: 17px; margin-top: 0; }
h3 { font-size: 15px; }
</style>
