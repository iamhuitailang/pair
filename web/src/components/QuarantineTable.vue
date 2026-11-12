<script setup>
import { ref } from 'vue';
import { api, formatBytes } from '../api.js';

const props = defineProps({ files: { type: Array, default: () => [] } });
const emit = defineEmits(['changed']);
const busyId = ref(null);
const purging = ref(false);
const message = ref('');

async function removeOne(f) {
  if (!window.confirm(`确认清理隔离文件「${f.originalName}」？该操作只作用于隔离区。`)) return;
  busyId.value = f.id;
  message.value = '';
  try {
    const r = await api.deleteQuarantine(f.id);
    message.value = `已清理，物理文件删除: ${r.removedPhysicalFile ? '是' : '否（记录留档场景）'}`;
    emit('changed');
  } catch (e) {
    message.value = `清理被拦截: ${e.message}`;
  } finally {
    busyId.value = null;
  }
}

async function purgeAll() {
  if (!props.files.length) return;
  if (!window.confirm(`确认清理全部 ${props.files.length} 条隔离记录？已通过检查的文件不受影响。`)) return;
  purging.value = true;
  message.value = '';
  try {
    const r = await api.purgeQuarantine();
    message.value = `批量清理完成：记录 ${r.deletedRecords} 条，物理文件 ${r.deletedPhysicalFiles} 个`;
    emit('changed');
  } catch (e) {
    message.value = e.message;
  } finally {
    purging.value = false;
  }
}
</script>

<template>
  <section>
    <div class="section-head">
      <h2>隔离区 <span class="count">{{ files.length }}</span></h2>
      <div class="head-actions">
        <span class="muted">隔离文件无下载入口，清理操作受 realpath 守卫保护</span>
        <button class="btn btn-danger" :disabled="!files.length || purging" @click="purgeAll">
          {{ purging ? '清理中…' : '一键清理隔离区' }}
        </button>
      </div>
    </div>
    <p v-if="message" class="notice">{{ message }}</p>

    <table v-if="files.length" class="table">
      <thead>
        <tr>
          <th>原始文件名</th><th>扩展名</th><th>实际识别类型</th><th>浏览器 MIME</th>
          <th>大小</th><th>拒收原因</th><th>隔离时间</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="f in files" :key="f.id" class="row-quarantine">
          <td class="fname">{{ f.originalName }}</td>
          <td>{{ f.extension || '—' }}</td>
          <td>
            <span v-if="f.detectedType" class="badge badge-blue">{{ f.detectedType.toUpperCase() }}</span>
            <span v-else class="muted">无法识别</span>
          </td>
          <td class="muted">{{ f.browserMime || '—' }}</td>
          <td>{{ formatBytes(f.sizeBytes) }}</td>
          <td class="reason-cell">{{ f.rejectReason }}</td>
          <td class="muted">{{ f.createdAt }}</td>
          <td>
            <button class="btn btn-small btn-danger" :disabled="busyId === f.id" @click="removeOne(f)">
              {{ busyId === f.id ? '…' : '清理' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">隔离区为空</p>
  </section>
</template>
