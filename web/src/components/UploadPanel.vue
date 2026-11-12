<script setup>
import { ref } from 'vue';
import { api } from '../api.js';

const emit = defineEmits(['changed']);
const dragging = ref(false);
const busy = ref(false);
const results = ref([]); // 本轮上传的逐条结论
const error = ref('');
const inputRef = ref(null);

async function handleFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  busy.value = true;
  error.value = '';
  results.value = [];
  for (const file of files) {
    try {
      const body = await api.upload(file);
      results.value.push({
        name: file.name,
        ok: body.status === 'approved',
        reason: body.file?.rejectReason,
        id: body.file?.id
      });
    } catch (e) {
      results.value.push({ name: file.name, ok: false, reason: e.message });
    }
  }
  busy.value = false;
  emit('changed');
}

function onDrop(e) {
  dragging.value = false;
  handleFiles(e.dataTransfer.files);
}
function onPick(e) {
  handleFiles(e.target.files);
  e.target.value = '';
}
</script>

<template>
  <section
    class="dropzone"
    :class="{ dragging, busy }"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
    @click="inputRef?.click()"
  >
    <input ref="inputRef" type="file" multiple hidden @change="onPick" />
    <p class="dz-title">{{ busy ? '正在检查上传文件…' : '拖拽文件到此处，或点击选择（支持多选）' }}</p>
    <p class="dz-hint">允许 PNG / JPEG / GIF / WebP / ZIP，单文件 ≤ 10 MiB；文件名与 MIME 均不参与信任判定</p>

    <ul v-if="results.length" class="upload-results">
      <li v-for="r in results" :key="r.name + r.id" :class="r.ok ? 'ok' : 'bad'">
        <span class="badge" :class="r.ok ? 'badge-green' : 'badge-red'">
          {{ r.ok ? '通过' : '隔离' }}
        </span>
        <span class="fname">{{ r.name }}</span>
        <span v-if="!r.ok" class="reason">{{ r.reason }}</span>
      </li>
    </ul>
    <p v-if="error" class="reason">{{ error }}</p>
  </section>
</template>
