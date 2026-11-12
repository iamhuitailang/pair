<template>
  <div>
    <div class="filters">
      <label>
        开始日期
        <input type="date" v-model="filters.date_from" />
      </label>
      <label>
        结束日期
        <input type="date" v-model="filters.date_to" />
      </label>
      <label>
        玩家 ID
        <input type="text" v-model="filters.player_id" placeholder="如 p1" />
      </label>
      <label>
        对局状态
        <select v-model="filters.status">
          <option value="">全部</option>
          <option value="finished">已结束</option>
          <option value="in_progress">进行中</option>
        </select>
      </label>
      <button @click="search">查询</button>
      <a class="btn secondary" :href="exportUrl(apiFilters(), 'csv')" download>导出 CSV</a>
      <a class="btn secondary" :href="exportUrl(apiFilters(), 'json')" download>导出 JSON</a>
    </div>

    <table>
      <thead>
        <tr>
          <th>对局 ID</th>
          <th>开始时间</th>
          <th>玩家</th>
          <th>状态</th>
          <th>时长</th>
          <th>胜者</th>
          <th>完整率</th>
          <th>事件数</th>
          <th>异常</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in items"
          :key="s.session_id"
          class="clickable"
          @click="$router.push(`/sessions/${s.session_id}`)"
        >
          <td>{{ s.session_id }}</td>
          <td>{{ fmtTime(s.started_at) }}</td>
          <td>{{ s.players.join(", ") }}</td>
          <td>
            <span class="badge" :class="s.status === 'finished' ? 'ok' : 'warn'">
              {{ s.status === "finished" ? "已结束" : "进行中" }}
            </span>
          </td>
          <td>{{ fmtDuration(s.duration_seconds) }}</td>
          <td>{{ s.winner_player_id ?? "-" }}</td>
          <td>{{ (s.completeness * 100).toFixed(1) }}%</td>
          <td>{{ s.event_count }}</td>
          <td>
            <span v-if="s.has_anomalies" class="badge err">{{ s.anomaly_count }}</span>
            <span v-else class="badge ok">无</span>
          </td>
        </tr>
        <tr v-if="!items.length">
          <td colspan="9" style="text-align: center; color: #999">暂无数据</td>
        </tr>
      </tbody>
    </table>

    <div class="pager">
      <button class="secondary" :disabled="page <= 1" @click="go(page - 1)">上一页</button>
      <span>第 {{ page }} 页 / 共 {{ total }} 条</span>
      <button class="secondary" :disabled="page * pageSize >= total" @click="go(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { exportUrl, fetchSessions, type Filters, type SessionSummary } from "../api";

const filters = reactive<Filters>({ date_from: "", date_to: "", player_id: "", status: "" });
const items = ref<SessionSummary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;

function toIso(date: string, endOfDay: boolean): string | undefined {
  return date ? `${date}T${endOfDay ? "23:59:59" : "00:00:00"}+00:00` : undefined;
}

function apiFilters(): Filters {
  return {
    date_from: toIso(filters.date_from ?? "", false),
    date_to: toIso(filters.date_to ?? "", true),
    player_id: filters.player_id || undefined,
    status: filters.status || undefined,
  };
}

async function load() {
  const resp = await fetchSessions(apiFilters(), page.value, pageSize);
  items.value = resp.items;
  total.value = resp.total;
}

function search() {
  page.value = 1;
  load();
}

function go(p: number) {
  page.value = p;
  load();
}

function fmtTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : "-";
}

function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}分${s}秒`;
}

onMounted(load);
</script>
