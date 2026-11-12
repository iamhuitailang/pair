<script setup>
import { reactive, ref } from 'vue'
import { api } from '../api'

const props = defineProps({ rules: { type: Array, default: () => [] } })
const emit = defineEmits(['refresh', 'started'])

const blank = {
  name: '',
  start_url: 'http://127.0.0.1:8080/index.html',
  allowed_domain: '',
  title_selector: 'h1',
  content_selector: '.content',
  time_selector: '.updated',
  next_selector: '',
  link_scope: 'all',
  max_pages: 200,
  max_depth: 5,
  delay_seconds: 0.5,
  timeout_seconds: 10,
  max_retries: 2,
  enabled: true,
}

const showForm = ref(false)
const editingId = ref(null)
const form = reactive({ ...blank })
const error = ref('')

function openCreate() {
  Object.assign(form, blank)
  editingId.value = null
  error.value = ''
  showForm.value = true
}

function openEdit(rule) {
  Object.assign(form, blank, rule, { enabled: !!rule.enabled })
  editingId.value = rule.id
  error.value = ''
  showForm.value = true
}

async function save() {
  error.value = ''
  try {
    if (editingId.value) {
      await api.updateRule(editingId.value, { ...form })
    } else {
      await api.createRule({ ...form })
    }
    showForm.value = false
    emit('refresh')
  } catch (e) {
    error.value = e.message
  }
}

async function remove(rule) {
  if (!confirm(`删除规则「${rule.name}」？历史运行记录会保留。`)) return
  await api.deleteRule(rule.id)
  emit('refresh')
}

async function startRun(rule) {
  const run = await api.startRun(rule.id)
  emit('started', run.id)
}
</script>

<template>
  <section>
    <div class="section-head">
      <h2>采集规则</h2>
      <button class="primary" @click="openCreate">新建规则</button>
    </div>

    <table v-if="rules.length" class="table">
      <thead>
        <tr>
          <th>ID</th><th>名称</th><th>起始地址</th><th>间隔(s)</th>
          <th>页数上限</th><th>启用</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rules" :key="r.id">
          <td>{{ r.id }}</td>
          <td>{{ r.name }}</td>
          <td class="mono">{{ r.start_url }}</td>
          <td>{{ r.delay_seconds }}</td>
          <td>{{ r.max_pages }}</td>
          <td>{{ r.enabled ? '是' : '否' }}</td>
          <td>
            <button class="primary" @click="startRun(r)">运行</button>
            <button @click="openEdit(r)">编辑</button>
            <button class="danger" @click="remove(r)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">还没有规则，点击「新建规则」开始。</p>

    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal">
        <h3>{{ editingId ? `编辑规则 #${editingId}` : '新建规则' }}</h3>
        <div class="form-grid">
          <label>名称<input v-model="form.name" placeholder="例如：本地资料站" /></label>
          <label>起始地址<input v-model="form.start_url" /></label>
          <label>允许域名（留空 = 起始地址同域）<input v-model="form.allowed_domain" placeholder="http://127.0.0.1:8080" /></label>
          <label>标题选择器<input v-model="form.title_selector" placeholder="h1（留空用 <title>）" /></label>
          <label>正文选择器<input v-model="form.content_selector" placeholder=".content（留空用 <body>）" /></label>
          <label>更新时间选择器<input v-model="form.time_selector" placeholder=".updated" /></label>
          <label>下一页选择器（分页）<input v-model="form.next_selector" placeholder="a.next-page" /></label>
          <label>链接范围
            <select v-model="form.link_scope">
              <option value="all">页面内全部链接</option>
              <option value="next">仅跟随「下一页」</option>
            </select>
          </label>
          <label>页数上限<input v-model.number="form.max_pages" type="number" min="1" /></label>
          <label>深度上限<input v-model.number="form.max_depth" type="number" min="0" /></label>
          <label>请求间隔（秒）<input v-model.number="form.delay_seconds" type="number" step="0.1" min="0" /></label>
          <label>超时（秒）<input v-model.number="form.timeout_seconds" type="number" min="1" /></label>
          <label>重试次数<input v-model.number="form.max_retries" type="number" min="0" /></label>
          <label class="checkbox"><input v-model="form.enabled" type="checkbox" /> 启用</label>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="modal-actions">
          <button class="primary" @click="save">保存</button>
          <button @click="showForm = false">取消</button>
        </div>
      </div>
    </div>
  </section>
</template>
