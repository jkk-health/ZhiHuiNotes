<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import AppDialog from '../components/AppDialog.vue'
import MindmapEditor from '../components/MindmapEditor.vue'
import { useUnsaved } from '../composables/useUnsaved'
const route=useRoute(), rows=ref([]), selected=ref(null), error=ref(''), busy=ref(false), loading=ref(false), dialog=ref(null), preview=ref(null)
const baseline=ref(''), snapshot=() => selected.value ? JSON.stringify([selected.value.title, selected.value.map_json]) : ''
const dirty=computed(() => snapshot() !== baseline.value)
const check=useUnsaved(dirty,dialog,save,() => {baseline.value=snapshot()})
let sequence=0
async function run(work) {error.value='';try {return await work()} catch(e) {error.value=e.message;return null}}
async function load() {rows.value=await api.get('/api/mindmaps')}
async function select(id) {
  if(selected.value?.id === id || busy.value || !(await check())) return
  const token=++sequence; loading.value=true
  await run(async () => {const map=await api.get(`/api/mindmaps/${id}`); if(token !== sequence) return; selected.value=map; baseline.value=snapshot(); preview.value=null})
  if(token === sequence) loading.value=false
}
async function create() {
  if(busy.value || loading.value || !(await check())) return
  ++sequence; loading.value=false; preview.value=null
  selected.value={id:null,title:'新导图',note_id:null,source_note:null,map_json:{meta:{name:'新导图',version:'1'},format:'node_tree',data:{id:'root',topic:'新导图',children:[]}}}; baseline.value=''
}
async function save() {
  if(!selected.value || busy.value || loading.value) return false
  busy.value=true
  const data=JSON.parse(JSON.stringify({title:selected.value.title,map_json:selected.value.map_json}))
  const submitted=snapshot(), id=selected.value.id
  const result=await run(async () => {
    const value=id ? await api.put(`/api/mindmaps/${id}`,data) : await api.post('/api/mindmaps',data)
    if(snapshot() === submitted) selected.value=value
    else {selected.value.id=value.id; selected.value.source_note=value.source_note}
    baseline.value=JSON.stringify([value.title,value.map_json])
    await load(); return !dirty.value
  })
  busy.value=false;return Boolean(result)
}
async function remove() {
  if(busy.value || loading.value || !selected.value?.id || !(await dialog.value.open({title:'删除导图',message:'删除此导图？来源笔记会保留。'}))) return
  await run(async () => {await api.del(`/api/mindmaps/${selected.value.id}`); selected.value=null; baseline.value=''; await load()})
}
async function regenerate() {
  if(busy.value || loading.value || !(await check())) return
  await run(async () => {preview.value=await api.post(`/api/notes/${selected.value.note_id}/to-mindmap?preview=1`,{})})
}
async function applyPreview() {
  if(!(await dialog.value.open({title:'覆盖导图',message:'用当前笔记重新生成的结构覆盖已编辑导图？'}))) return
  selected.value.map_json=preview.value.map_json; preview.value=null; await save()
}
watch(() => route.query.id,id => {if(id) select(Number(id))})
onMounted(() => run(async () => {await load(); if(route.query.id) await select(Number(route.query.id)); else if(rows.value[0]) await select(rows.value[0].id)}))
</script>
<template>
  <div class="zh-module mindmaps-page">
    <div class="mindmaps-page-head"><div><h1 class="h4 mb-2">思维导图</h1><p class="text-muted mb-0 small">把笔记的层级变成清晰的思路。</p></div><button class="btn btn-primary btn-sm" @click="create">＋ 新建导图</button></div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div><p v-if="loading" class="text-muted">正在打开导图…</p>
    <div class="mindmaps-layout">
      <aside class="zh-card mindmap-library">
        <div class="mindmap-library-head"><span>我的导图</span><span class="mindmap-library-count">{{ rows.length }}</span></div>
        <p v-if="!rows.length" class="small text-muted px-2">尚无导图，可新建或从笔记一键生成。</p>
        <div class="mindmap-library-list">
          <button v-for="row in rows" :key="row.id" class="mindmap-library-item" :class="{'active':selected?.id === row.id}" :title="row.title" @click="select(row.id)">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="9" width="6" height="6" rx="1.5"/><rect x="16" y="3" width="5" height="5" rx="1.5"/><rect x="16" y="16" width="5" height="5" rx="1.5"/><path d="M9 12h3V5.5h4M12 12v6.5h4"/></svg>
            <span>{{ row.title }}</span>
          </button>
        </div>
        <div class="mindmap-library-tip">笔记生成的导图可独立编辑。</div>
      </aside>
      <section class="mindmap-document">
        <div v-if="selected" class="zh-card mindmap-sheet" :class="{'pe-none opacity-75':loading}">
          <div class="mindmap-document-head">
            <input v-model="selected.title" class="form-control mindmap-document-title" aria-label="导图标题" maxlength="200" />
            <div class="d-flex gap-2 flex-shrink-0"><button class="btn btn-primary btn-sm" :disabled="busy || loading" @click="save">{{ busy ? '保存中…' : '保存导图' }}</button><button v-if="selected.id" class="btn btn-sm mindmap-delete" :disabled="busy || loading" @click="remove">删除导图</button></div>
          </div>
          <div class="mindmap-source"><span class="mindmap-save-state" :class="{'is-dirty':dirty}"><i></i>{{ dirty ? '有未保存的修改' : '内容已保存' }}</span><template v-if="selected.source_note"><span class="mindmap-source-divider">/</span><span v-if="selected.source_note.is_deleted">来源笔记在回收站</span><RouterLink v-else :to="`/notes?id=${selected.note_id}`">返回笔记：{{ selected.source_note.title }}</RouterLink></template></div>
          <p v-if="!selected.map_json.data.children?.length" class="small text-muted">当前只有根节点。可新增节点，或为来源笔记添加标题后重新生成。</p>
          <MindmapEditor :key="selected.id ?? 'new'" v-model="selected.map_json" @error="error=$event" />
          <button v-if="selected.note_id && !selected.source_note?.is_deleted" class="btn btn-sm btn-outline-secondary mt-3" @click="regenerate">从来源笔记重新生成（预览）</button>
        </div>
        <div v-else class="zh-card p-5 text-muted text-center">请选择导图或创建新的导图。</div>
      </section>
    </div>
    <div v-if="preview" class="zh-card p-3 mt-3"><h2 class="h6">重新生成预览</h2><MindmapEditor v-model="preview.map_json" @error="error=$event" /><div class="d-flex gap-2 mt-3"><button class="btn btn-primary" @click="applyPreview">确认覆盖并保存</button><button class="btn btn-outline-secondary" @click="preview=null">取消预览</button></div></div>
    <AppDialog ref="dialog" />
  </div>
</template>
<style scoped>
.mindmaps-page { padding:24px; }
.mindmaps-page-head { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:22px; }
.mindmaps-page-head h1 { font-weight:650; color:#233b31; }
.mindmaps-layout { display:grid; grid-template-columns:200px minmax(0,1fr); gap:16px; align-items:start; }
.mindmap-library { padding:16px 10px 12px; }
.mindmap-library-head { display:flex; align-items:center; justify-content:space-between; padding:0 8px 14px; font-size:12px; font-weight:600; color:#7b8c81; }
.mindmap-library-count { padding:1px 7px; border-radius:5px; background:#f0f4f1; color:#85958a; font-size:11px; }
.mindmap-library-list { display:flex; flex-direction:column; gap:5px; max-height:60vh; overflow:auto; }
.mindmap-library-item { display:flex; gap:9px; align-items:flex-start; text-align:left; width:100%; padding:11px 10px; border:1px solid transparent; border-radius:8px; background:transparent; color:#6c7c72; font-size:12px; line-height:1.6; }
.mindmap-library-item svg { margin-top:2px; flex-shrink:0; }
.mindmap-library-item span { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; overflow-wrap:anywhere; }
.mindmap-library-item:hover { background:#f6f9f6; color:#0d7a6f; }
.mindmap-library-item.active { color:#0c7764; background:#eaf5ee; border-color:#d5e9dd; font-weight:600; }
.mindmap-library-tip { margin:14px 8px 0; padding-top:13px; border-top:1px solid #edf1ee; font-size:10px; color:#97a39a; line-height:1.7; }
.mindmap-document { min-width:0; }
.mindmap-sheet { padding:20px; }
.mindmap-document-head { display:flex; align-items:center; gap:14px; }
.mindmap-document-title { flex:1; min-width:0; padding:6px 0; font-size:18px; font-weight:600; color:#2c4235; border-color:transparent; background:transparent; }
.mindmap-document-title:focus { padding-left:8px; border-color:#d3e6da; box-shadow:0 0 0 2px #eaf5ee; }
.mindmap-delete { color:#a68082; border:1px solid #f0e3e4; }
.mindmap-delete:hover { background:#fff0f1; color:#b34b55; }
.mindmap-source { display:flex; align-items:center; flex-wrap:wrap; gap:8px; padding:12px 0 18px; margin-bottom:16px; border-bottom:1px solid #edf1ee; color:#8c9a90; font-size:11px; }
.mindmap-source a { color:#648676; text-decoration:none; overflow-wrap:anywhere; }
.mindmap-source a:hover { color:#0d7a6f; text-decoration:underline; }
.mindmap-save-state { display:flex; align-items:center; gap:6px; }
.mindmap-save-state i { width:5px; height:5px; border-radius:50%; background:#75a489; }
.mindmap-save-state.is-dirty { color:#ad853d; }
.mindmap-save-state.is-dirty i { background:#c69a49; }
.mindmap-source-divider { color:#d4ded7; margin:0 2px; }
@media(max-width:1199px) { .mindmaps-layout { grid-template-columns:180px minmax(0,1fr); } }
@media(max-width:991px) {
  .mindmaps-layout { grid-template-columns:minmax(0,1fr); }
  .mindmap-library-list { flex-direction:row; max-height:110px; }
  .mindmap-library-item { width:190px; flex-shrink:0; }
  .mindmap-library-tip { display:none; }
}
@media(max-width:575px) {
  .mindmaps-page { padding:16px 12px; }
  .mindmaps-page-head { margin-bottom:16px; }
  .mindmap-sheet { padding:14px 12px; }
  .mindmap-document-head { flex-wrap:wrap; gap:8px; }
  .mindmap-document-title { flex-basis:100%; font-size:16px; }
}
</style>
