<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { today } from '../utils/dates'
import AppDialog from '../components/AppDialog.vue'
import { useUnsaved } from '../composables/useUnsaved'
const route=useRoute(), dialog=ref(null), rows=ref([]), notes=ref([]), filter=ref(''), error=ref(''), busy=ref(false), editing=ref(null)
const empty=() => ({title:'', due_date:null, note_id:null})
const form=ref(empty()), baseline=ref(JSON.stringify(empty()))
const dirty=computed(() => JSON.stringify(form.value) !== baseline.value)
const clear=() => { editing.value=null; form.value=empty(); baseline.value=JSON.stringify(form.value) }
const check=useUnsaved(dirty, dialog, save, () => { baseline.value=JSON.stringify(form.value) })
const completed=computed(() => rows.value.filter(t => t.done).length)
const overdue=t => !t.done && t.due_date && t.due_date < today()
async function load() { rows.value=await api.get(`/api/todos${filter.value ? '?done='+filter.value : ''}`); notes.value=await api.get('/api/notes') }
async function run(work) { error.value=''; try { await work() } catch(e) { error.value=e.message } }
async function edit(row) {
  if(!(await check())) return
  editing.value=row.id; form.value={title:row.title, due_date:row.due_date, note_id:row.note_id}; baseline.value=JSON.stringify(form.value)
}
async function save() {
  if(busy.value) return false
  if(!form.value.title.trim()) { error.value='标题不能为空'; return false }
  busy.value=true; let ok=false
  await run(async () => { const data={...form.value, due_date:form.value.due_date || null}; if(editing.value) await api.put(`/api/todos/${editing.value}`, data); else await api.post('/api/todos', data); clear(); await load(); ok=true })
  busy.value=false; return ok
}
async function cancel() { if(await check()) clear() }
async function toggle(row) { await run(async () => { await api.put(`/api/todos/${row.id}`, {done:!row.done}); await load() }) }
async function remove(row) {
  if(!(await dialog.value.open({title:'删除待办', message:`删除「${row.title}」？`}))) return
  await run(async () => { await api.del(`/api/todos/${row.id}`); if(editing.value === row.id) clear(); await load() })
}
watch(() => route.query.id, id => { const row=rows.value.find(t => t.id === Number(id)); if(row) edit(row) })
onMounted(() => run(async () => { await load(); const row=rows.value.find(t => t.id === Number(route.query.id)); if(row) await edit(row) }))
</script>
<template>
  <div class="zh-module p-4">
    <div class="d-flex justify-content-between align-items-center mb-3"><div><h1 class="h4">待办</h1><p class="text-muted mb-0">把笔记变成行动，随时返回来源。</p></div><span class="badge bg-primary">已完成 {{ completed }}/{{ rows.length }} · {{ rows.length ? Math.round(completed / rows.length * 100) : 0 }}%</span></div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <form class="zh-card p-3 mb-3" @submit.prevent="save"><h2 class="h6">{{ editing ? '编辑待办' : '新增待办' }}</h2><div class="row g-2"><div class="col-md-5"><input v-model="form.title" class="form-control" placeholder="待办标题" aria-label="待办标题" maxlength="200" required /></div><div class="col-md-3"><input v-model="form.due_date" class="form-control" type="date" aria-label="截止日期" /></div><div class="col-md-4"><select v-model="form.note_id" class="form-select" aria-label="关联笔记"><option :value="null">独立待办 / 解除关联</option><option v-if="form.note_id && !notes.some(n => n.id === form.note_id)" :value="form.note_id">来源笔记在回收站（保留关联）</option><option v-for="note in notes" :key="note.id" :value="note.id">{{ note.title }}</option></select></div></div><div class="d-flex gap-2 mt-3"><button class="btn btn-primary" :disabled="busy">{{ busy ? '保存中…' : editing ? '保存待办' : '新增待办' }}</button><button v-if="editing || dirty" type="button" class="btn btn-outline-secondary" @click="cancel">取消编辑</button></div></form>
    <div class="d-flex gap-2 mb-3"><select v-model="filter" class="form-select w-auto" aria-label="完成状态筛选" @change="run(load)"><option value="">全部待办</option><option value="0">未完成</option><option value="1">已完成</option></select><span class="small text-muted align-self-center">完成率按当前筛选结果统计</span></div>
    <div class="zh-card p-3"><p v-if="!rows.length" class="text-muted text-center p-4">还没有待办，在上方创建第一项。</p><article v-for="row in rows" :key="row.id" class="py-3 border-bottom" :class="{'text-danger':overdue(row)}"><div class="d-flex align-items-center gap-3"><input type="checkbox" class="form-check-input" :checked="row.done" :aria-label="`完成${row.title}`" @change="toggle(row)" /><strong class="flex-grow-1 text-break" :class="{'text-decoration-line-through text-muted':row.done}">{{ row.title }}</strong><button class="btn btn-sm btn-outline-secondary" @click="edit(row)">编辑</button><button class="btn btn-sm btn-outline-danger" @click="remove(row)">删除</button></div><div class="small mt-2 ms-4"><span>{{ row.due_date ? `截止 ${row.due_date}` : '无截止日期' }}{{ overdue(row) ? ' · 已过期' : '' }}</span><template v-if="row.source_note"><span class="mx-2">·</span><span v-if="row.source_note.is_deleted" class="text-muted">{{ row.source_note.title }}（来源笔记在回收站）</span><RouterLink v-else :to="`/notes?id=${row.source_note.id}`">返回笔记：{{ row.source_note.title }}</RouterLink></template></div></article></div>
    <AppDialog ref="dialog" />
  </div>
</template>
