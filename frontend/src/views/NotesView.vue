<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import { api } from '../api'
import RichTextEditor from '../components/RichTextEditor.vue'
import AppDialog from '../components/AppDialog.vue'
import { useUnsaved } from '../composables/useUnsaved'

marked.setOptions({ gfm:true, breaks:true })
const route = useRoute(), router = useRouter(), dialog = ref(null)
const notes = ref([]), trashed = ref([]), notebooks = ref([]), tags = ref([])
const activeId = ref(null), blank = ref(true), mode = ref('normal')
const search = ref(''), notebookFilter = ref(-1), tagFilter = ref(''), managingTags = ref(false)
const saving = ref(false), loading = ref(false), detailLoading = ref(false), error = ref('')
const todos = ref([]), maps = ref([]), todoTitle = ref(''), action = ref('')
const ai = ref(null), chosenTags = ref([])
const emptyDraft = () => ({ title:'', content_html:'', content_md:'', notebook_id:null, tags:[] })
const draft = ref(emptyDraft()), baseline = ref('')
const snapshot = (d = draft.value) => JSON.stringify([d.title, d.content_html, d.notebook_id, d.tags])
const dirty = computed(() => !blank.value && mode.value === 'normal' && baseline.value !== snapshot())
const discard = () => { baseline.value = snapshot() }
const checkLeave = useUnsaved(dirty, dialog, save, discard)
const activeNote = computed(() => notes.value.find(n => n.id === activeId.value))
let detailSequence = 0, listSequence = 0
const ask = (options) => dialog.value.open(options)
async function attempt(work) { error.value = ''; try { return await work() } catch(e) { error.value = e.message; return null } }
async function loadNotes() {
  const sequence = ++listSequence
  loading.value = true
  const params = new URLSearchParams()
  if(notebookFilter.value >= 0) params.set('notebook_id', notebookFilter.value)
  if(tagFilter.value) params.set('tag', tagFilter.value)
  if(search.value.trim()) params.set('q', search.value.trim())
  try { const rows = await api.get(`/api/notes?${params}`); if(sequence === listSequence) notes.value = rows }
  finally { if(sequence === listSequence) loading.value = false }
}
async function reload() {
  const [trashRows, nbRows, tagRows] = await Promise.all([api.get('/api/notes?trash=1'), api.get('/api/notebooks'), api.get('/api/tags'), loadNotes()])
  trashed.value = trashRows; notebooks.value = nbRows; tags.value = tagRows
}
async function loadRelated() {
  const id = activeId.value
  if(!id) { todos.value=[]; maps.value=[]; return }
  const [todoRows, mapRows] = await Promise.all([api.get(`/api/todos?note_id=${id}`), api.get(`/api/mindmaps?note_id=${id}`)])
  if(id === activeId.value) { todos.value=todoRows; maps.value=mapRows }
}
async function select(id) {
  if(id === activeId.value || saving.value || !(await checkLeave())) return
  const sequence = ++detailSequence
  detailLoading.value = true
  await attempt(async () => {
    const note = await api.get(`/api/notes/${id}`)
    if(sequence !== detailSequence) return
    activeId.value=id; blank.value=false; mode.value='normal'
    draft.value={ title:note.title, content_html:note.content_html || marked.parse(note.content_md || ''), content_md:note.content_md, notebook_id:note.notebook_id, tags:note.tags }
    baseline.value=snapshot(); ai.value=null
    await loadRelated()
  })
  if(sequence === detailSequence) detailLoading.value=false
}
async function startNew() {
  if(saving.value || !(await checkLeave())) return
  ++detailSequence; detailLoading.value=false; mode.value='normal'; blank.value=false; activeId.value=null
  draft.value={...emptyDraft(), notebook_id:notebookFilter.value > 0 ? notebookFilter.value : null, tags:tagFilter.value ? [tagFilter.value] : []}
  baseline.value=snapshot(); ai.value=null; todos.value=[]; maps.value=[]
}
async function switchMode() {
  if(saving.value || !(await checkLeave())) return
  ++detailSequence; detailLoading.value=false; mode.value=mode.value === 'trash' ? 'normal' : 'trash'
  blank.value=true; activeId.value=null; draft.value=emptyDraft(); baseline.value=snapshot()
  await attempt(reload)
}
async function save() {
  if(saving.value || detailLoading.value) return false
  if(!draft.value.title.trim()) { error.value='标题不能为空'; return false }
  saving.value=true
  const submitted=JSON.parse(JSON.stringify(draft.value)), submittedSnapshot=snapshot(submitted)
  const result=await attempt(async () => {
    const saved=activeId.value ? await api.put(`/api/notes/${activeId.value}`, submitted) : await api.post('/api/notes', submitted)
    activeId.value=saved.id
    if(snapshot() === submittedSnapshot) {
      draft.value={title:saved.title, content_html:saved.content_html, content_md:saved.content_md, notebook_id:saved.notebook_id, tags:saved.tags}
      baseline.value=snapshot()
    } else baseline.value=submittedSnapshot
    await reload(); await loadRelated(); return !dirty.value
  })
  saving.value=false; return Boolean(result)
}
async function ensureSaved() { return activeId.value && !dirty.value ? !detailLoading.value : save() }
async function remove() {
  if(saving.value || !(await checkLeave()) || !(await ask({title:'移入回收站', message:'关联待办和导图会保留。确定移入回收站？'}))) return
  await attempt(async () => { await api.del(`/api/notes/${activeId.value}`); ++detailSequence; activeId.value=null; blank.value=true; draft.value=emptyDraft(); await reload(); if(notes.value[0]) await select(notes.value[0].id) })
}
async function restore(note) { await attempt(async () => { await api.post(`/api/notes/${note.id}/restore`, {}); await reload() }) }
async function pin(note) { await attempt(async () => { await api.put(`/api/notes/${note.id}`, {is_top:!note.is_top}); await reload() }) }
async function editNotebook(kind) {
  const nb=notebooks.value.find(n => n.id === notebookFilter.value)
  if(kind === 'delete') {
    if(!(await ask({title:'删除笔记本', message:'笔记会归入未分组，不会丢失。'}))) return
    await attempt(async () => { await api.del(`/api/notebooks/${nb.id}`); if(draft.value.notebook_id === nb.id) draft.value.notebook_id=null; notebookFilter.value=-1; await reload() })
  } else {
    const name=await ask({type:'prompt', title:kind === 'new' ? '新建笔记本' : '重命名笔记本', label:'笔记本名称', value:nb?.name || ''})
    if(!name?.trim()) return
    await attempt(async () => { if(kind === 'new') await api.post('/api/notebooks', {name:name.trim()}); else await api.put(`/api/notebooks/${nb.id}`, {name:name.trim()}); await reload() })
  }
}
async function manageTag(tag, removeTag=false) {
  const value=await ask(removeTag ? {title:'删除标签', message:`删除「${tag.name}」？笔记会保留。`} : {type:'prompt', title:'重命名标签', value:tag.name})
  if(!value) return
  await attempt(async () => {
    if(removeTag) { await api.del(`/api/tags/${tag.id}`); draft.value.tags=draft.value.tags.filter(t => t !== tag.name); if(tagFilter.value === tag.name) tagFilter.value='' }
    else { if(!value.trim()) return; await api.put(`/api/tags/${tag.id}`, {name:value.trim()}); draft.value.tags=draft.value.tags.map(t => t === tag.name ? value.trim() : t); if(tagFilter.value === tag.name) tagFilter.value=value.trim() }
    await reload()
  })
}
function filterTag(name) { tagFilter.value=tagFilter.value === name ? '' : name; attempt(loadNotes) }
function setTags(event) { draft.value.tags=[...new Set(event.target.value.split(/[,，]/).map(s => s.trim()).filter(Boolean))] }
async function addTodo() {
  if(!todoTitle.value.trim() || !(await ensureSaved())) return
  await attempt(async () => { await api.post('/api/todos', {title:todoTitle.value, note_id:activeId.value}); todoTitle.value=''; await loadRelated() })
}
async function generateMap() {
  if(!(await ensureSaved())) return
  action.value='map'
  await attempt(async () => { const map=await api.post(`/api/notes/${activeId.value}/to-mindmap`, {}); await router.push(`/mindmaps?id=${map.id}`) })
  action.value=''
}
async function runAi(kind) {
  if(!(await ensureSaved())) return
  const id=activeId.value; action.value=kind; ai.value=null
  await attempt(async () => { const result=await api.post(`/api/ai/${kind}`, {note_id:id}); if(id === activeId.value) { ai.value=result; chosenTags.value=result.tags || [] } })
  action.value=''
}
async function adoptTags() {
  if(!(await ensureSaved())) return
  await attempt(async () => { const latest=await api.get(`/api/notes/${activeId.value}`); draft.value.tags=[...new Set([...latest.tags, ...chosenTags.value])]; if(await save()) ai.value=null })
}
async function copySummary() {
  try { await navigator.clipboard.writeText(ai.value.summary); await ask({type:'alert', title:'已复制', message:'摘要已复制。'}) }
  catch { await ask({type:'alert', title:'摘要', message:ai.value.summary}) }
}
watch(() => route.query.id, id => { if(id) select(Number(id)) })
onMounted(() => attempt(async () => { await reload(); if(route.query.id) await select(Number(route.query.id)); else if(notes.value[0]) await select(notes.value[0].id) }))
</script>

<template>
  <div class="zh-panes h-100">
    <section class="zh-pane-list">
      <div class="d-flex justify-content-between align-items-center p-3 border-bottom"><strong>{{ mode === 'trash' ? '回收站' : '我的笔记' }}</strong><div class="d-flex gap-2"><button class="btn btn-sm btn-outline-secondary" @click="switchMode">{{ mode === 'trash' ? '返回笔记' : `回收站 ${trashed.length}` }}</button><button v-if="mode !== 'trash'" class="btn btn-sm btn-primary" @click="startNew">＋ 笔记</button></div></div>
      <div v-if="mode !== 'trash'" class="p-3 border-bottom">
        <form class="input-group input-group-sm mb-2" @submit.prevent="attempt(loadNotes)"><input v-model="search" class="form-control" placeholder="搜索标题 / 正文" aria-label="搜索笔记" /><button class="btn btn-outline-secondary">搜索</button></form>
        <select v-model.number="notebookFilter" class="form-select form-select-sm" aria-label="筛选笔记本" @change="attempt(loadNotes)"><option :value="-1">全部笔记本</option><option :value="0">未分组</option><option v-for="nb in notebooks" :key="nb.id" :value="nb.id">{{ nb.name }}（{{ nb.note_count }}）</option></select>
        <div class="d-flex gap-1 mt-2"><button class="btn btn-sm btn-outline-secondary" @click="editNotebook('new')">新建笔记本</button><template v-if="notebookFilter > 0"><button class="btn btn-sm btn-outline-secondary" @click="editNotebook('rename')">重命名</button><button class="btn btn-sm btn-outline-danger" @click="editNotebook('delete')">删除</button></template></div>
        <div class="d-flex flex-wrap gap-1 mt-2"><span v-for="tag in tags" :key="tag.id" class="zh-chip zh-chip-btn" :class="{active:tagFilter === tag.name}" @click="managingTags ? manageTag(tag) : filterTag(tag.name)">{{ tag.name }}<button v-if="managingTags" class="zh-tag-del" :aria-label="`删除标签${tag.name}`" @click.stop="manageTag(tag, true)">×</button></span><button v-if="tags.length" class="zh-chip zh-chip-btn" @click="managingTags=!managingTags">{{ managingTags ? '完成管理' : '管理标签' }}</button></div>
      </div>
      <div class="zh-pane-list-body">
        <template v-if="mode === 'trash'"><article v-for="note in trashed" :key="note.id" class="zh-note-item d-flex justify-content-between align-items-center gap-2"><span class="text-truncate">{{ note.title }}</span><button class="btn btn-sm btn-outline-primary" @click="restore(note)">恢复</button></article><p v-if="!trashed.length" class="text-muted text-center p-3">回收站是空的</p></template>
        <template v-else><article v-for="note in notes" :key="note.id" class="zh-note-item" :class="{active:activeId === note.id}" @click="select(note.id)"><div class="d-flex justify-content-between gap-2"><strong class="text-truncate">{{ note.is_top ? '📌 ' : '' }}{{ note.title }}</strong><button class="btn btn-sm py-0" :aria-label="note.is_top ? '取消置顶' : '置顶'" @click.stop="pin(note)">📌</button></div><div class="meta"><span>{{ note.updated_at?.slice(0,10) }}</span><span v-for="tag in note.tags" :key="tag" class="zh-chip">{{ tag }}</span></div></article><p v-if="!loading && !notes.length" class="text-muted text-center p-3">没有符合条件的笔记</p></template>
      </div>
    </section>
    <section class="zh-pane-editor p-4">
      <div v-if="error" class="alert alert-danger">{{ error }}</div>
      <p v-if="detailLoading" class="text-muted">正在打开笔记…</p>
      <div v-if="mode === 'trash'" class="zh-card p-5 text-center text-muted">恢复笔记后可继续编辑；关联待办和导图始终保留。</div>
      <div v-else-if="blank" class="zh-card p-5 text-center"><p>这里是你的笔记编辑区</p><button class="btn btn-primary" @click="startNew">写第一篇笔记</button></div>
      <template v-else>
        <div class="zh-card p-4" :class="{'pe-none opacity-75':detailLoading}">
          <input v-model="draft.title" class="form-control form-control-lg border-0 px-0 fw-bold mb-3" placeholder="无标题" aria-label="笔记标题" maxlength="200" />
          <div class="row g-2 mb-3"><div class="col-md-5"><select v-model="draft.notebook_id" class="form-select form-select-sm" aria-label="笔记所属笔记本"><option :value="null">未分组</option><option v-for="nb in notebooks" :key="nb.id" :value="nb.id">{{ nb.name }}</option></select></div><div class="col-md-7"><input :value="draft.tags.join(', ')" class="form-control form-control-sm" placeholder="标签（逗号分隔）" aria-label="笔记标签" @input="setTags" /></div></div>
          <div class="d-flex flex-wrap justify-content-end align-items-center gap-2 mb-3"><small class="text-muted me-auto">{{ dirty ? '有未保存的修改' : '内容已保存' }}</small><button v-if="activeNote" class="btn btn-sm btn-outline-secondary" @click="pin(activeNote)">{{ activeNote.is_top ? '取消置顶' : '置顶' }}</button><button v-if="activeId" class="btn btn-sm btn-outline-danger" @click="remove">移入回收站</button><button class="btn btn-sm btn-primary" :disabled="saving || detailLoading" @click="save">{{ saving ? '保存中…' : activeId ? '保存' : '创建' }}</button></div>
          <RichTextEditor :key="activeId ?? 'new'" v-model="draft.content_html" @text-change="draft.content_md=$event" @alert="message => ask({type:'alert', title:'提示', message})" />
        </div>
        <div class="zh-card p-3 mt-3">
          <h2 class="h6">多形态复用与 AI 助手</h2><p class="small text-muted">操作前会保存当前笔记。AI 结果先预览，由你决定是否采用。</p>
          <div class="d-flex flex-wrap gap-2"><button class="btn btn-sm btn-outline-primary" :disabled="!!action || saving" @click="generateMap">一键转导图</button><button class="btn btn-sm btn-outline-primary" :disabled="!!action || saving" @click="runAi('summary')">生成摘要</button><button class="btn btn-sm btn-outline-primary" :disabled="!!action || saving" @click="runAi('tags')">建议标签</button><span v-if="action" class="small text-muted align-self-center">处理中…</span></div>
          <div v-if="ai" class="mt-3 p-3 bg-light rounded"><p class="small text-muted mb-2">{{ ai.engine === 'api' ? '真实 API' : '本地规则引擎' }} <span v-if="ai.engine === 'local'">· {{ {no_key:'未配置 Key', timeout:'远程调用超时', api_error:'远程调用失败', invalid_response:'远程结果无效', api_busy:'远程请求繁忙'}[ai.reason] }}</span><span v-if="ai.input_truncated"> · 已截取前 10,000 字符</span></p><template v-if="ai.summary"><p class="text-break">{{ ai.summary }}</p><button class="btn btn-sm btn-outline-secondary" @click="copySummary">复制摘要</button></template><template v-else><div class="d-flex flex-wrap gap-3 mb-2"><label v-for="tag in ai.tags" :key="tag" class="form-check"><input v-model="chosenTags" class="form-check-input" type="checkbox" :value="tag" />{{ tag }}</label></div><p v-if="!ai.tags.length" class="small text-muted">没有匹配的候选标签。</p><button v-else class="btn btn-sm btn-primary" :disabled="!chosenTags.length || saving" @click="adoptTags">合并选中标签</button></template></div>
        </div>
        <div class="zh-card p-3 mt-3"><h2 class="h6">关联待办</h2><form class="input-group input-group-sm mb-3" @submit.prevent="addTodo"><input v-model="todoTitle" class="form-control" placeholder="从这篇笔记创建待办" maxlength="200" /><button class="btn btn-outline-primary" :disabled="saving">创建待办</button></form><div v-for="todo in todos" :key="todo.id" class="d-flex justify-content-between mb-2"><span>{{ todo.done ? '✓' : '○' }} {{ todo.title }}</span><RouterLink :to="`/todos?id=${todo.id}`">查看待办</RouterLink></div><p v-if="!todos.length" class="small text-muted mb-0">尚无关联待办。</p><h2 class="h6 mt-3">关联导图</h2><div v-for="map in maps" :key="map.id"><RouterLink :to="`/mindmaps?id=${map.id}`">{{ map.title }}</RouterLink></div><p v-if="!maps.length" class="small text-muted mb-0">尚无关联导图。</p></div>
      </template>
    </section>
    <AppDialog ref="dialog" />
  </div>
</template>
