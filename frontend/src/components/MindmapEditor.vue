<script setup>
import { nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import jsMind from 'jsmind'
import 'jsmind/draggable-node'
import 'jsmind/style/jsmind.css'
import AppDialog from './AppDialog.vue'
const props=defineProps({ modelValue:{type:Object,required:true} })
const emit=defineEmits(['update:modelValue','error'])
const host=ref(null), dialog=ref(null), zoom=ref(100), count=ref(0), selectedTopic=ref(''), expanded=ref(false)
const palette=[['#0d7a6f','#e9f5f1'],['#556bb0','#eef1fb'],['#b57a35','#fbf2e5'],['#8764a5','#f4eef9'],['#288b9b','#e8f5f8'],['#b25c79','#fbedf2']]
let instance, observer, last='', syncing=false, stopped=false, frame=0, autoFit=true, previousSize=''
function appearance(node) {
  let branch=node, depth=0
  while(branch.parent) {depth++; if(branch.parent.isroot) break; branch=branch.parent}
  const index=node.isroot ? 0 : Math.max(0,branch.parent.children.indexOf(branch))
  return {depth,colors:palette[index % palette.length]}
}
function styleNode(element,node) {
  const {depth,colors}=appearance(node)
  element.dataset.depth=String(depth)
  element.style.setProperty('--branch-color',colors[0])
  element.style.setProperty('--branch-soft',colors[1])
  element.title=node.topic
  element.setAttribute('role','treeitem')
  element.setAttribute('aria-level',String(depth+1))
}
function renderNode(_mind,element,node) {
  // Set text and size-affecting styles before jsMind measures the node.
  element.textContent=node.topic; styleNode(element,node); return true
}
function decorate() {
  if(!instance?.mind || stopped) return
  const nodes=Object.values(instance.mind.nodes), lines=host.value.querySelectorAll('svg.jsmind path')
  let lineIndex=0
  for(const node of nodes) {
    const element=node._data.view.element
    styleNode(element,node)
    element.setAttribute('aria-selected',String(instance.get_selected_node()?.id === node.id))
    if(!node.isroot && instance.is_node_visible(node)) {
      lines[lineIndex]?.setAttribute('stroke',appearance(node).colors[0])
      lines[lineIndex]?.setAttribute('stroke-linecap','round'); lineIndex++
    }
  }
  count.value=nodes.length; zoom.value=Math.round(instance.view.zoom_current*100)
  selectedTopic.value=instance.get_selected_node()?.topic || ''
}
function centerContents() {
  if(!instance?.mind) return
  const nodes=[...host.value.querySelectorAll('jmnode[nodeid]')].filter(el => el.style.display !== 'none')
  if(!nodes.length) return
  const left=Math.min(...nodes.map(el => parseFloat(el.style.left)))
  const top=Math.min(...nodes.map(el => parseFloat(el.style.top)))
  const right=Math.max(...nodes.map(el => parseFloat(el.style.left)+el.offsetWidth))
  const bottom=Math.max(...nodes.map(el => parseFloat(el.style.top)+el.offsetHeight))
  const panel=host.value.querySelector('.jsmind-inner'), scale=instance.view.zoom_current
  panel.scrollTo((left+right)*scale/2-panel.clientWidth/2,(top+bottom)*scale/2-panel.clientHeight/2)
}
function fit() {
  if(!instance?.mind || stopped) return
  autoFit=true
  const panel=host.value.querySelector('.jsmind-inner'), size=instance.layout.get_min_size()
  const scale=Math.max(0.2,Math.min(1,Math.floor(Math.min(panel.clientWidth/(size.w+128),panel.clientHeight/(size.h+96))*100)/100))
  setScale(scale)
}
function setScale(scale) {
  const panel=host.value.querySelector('.jsmind-inner'), size=instance.layout.get_min_size()
  // A zoomed canvas must still fill the viewport. Otherwise a short diagram
  // sticks to the top after zooming out and cannot be centered by scrolling.
  instance.view.opts.hmargin=Math.max(64,(panel.clientWidth/scale-size.w)/2+1)
  instance.view.opts.vmargin=Math.max(48,(panel.clientHeight/scale-size.h)/2+1)
  instance.resize();instance.view.set_zoom(scale);centerContents();decorate()
}
function scheduleFit() {cancelAnimationFrame(frame);frame=requestAnimationFrame(() => {if(!stopped) fit()})}
function show(value) {
  if(!instance) return
  syncing=true
  last=JSON.stringify(value)
  try {
    const value=JSON.parse(last)
    // New note-generated maps have no directions. Spread those branches on
    // both sides; preserve every direction that was explicitly saved.
    value.data.children?.forEach((node,index) => {if(!node.direction) node.direction=index % 2 ? 'left' : 'right'})
    instance.show(value);decorate();scheduleFit()
  } catch(e) {emit('error',e.message)}
  syncing=false
}
function publish() {
  if(syncing || stopped || !instance) return
  const value=instance.get_data('node_tree')
  last=JSON.stringify(value)
  emit('update:modelValue',value)
  decorate()
}
async function add(sibling=false) {
  const selected=instance.get_selected_node() || instance.get_root()
  const parent=sibling && !selected.isroot ? selected.parent : selected
  const topic=await dialog.value.open({type:'prompt',title:sibling ? '新增同级节点' : '新增子节点',label:'节点文字'})
  if(topic?.trim() && !stopped) {
    const node=sibling && !selected.isroot ? instance.insert_node_after(selected,crypto.randomUUID(),topic.trim()) : instance.add_node(parent,crypto.randomUUID(),topic.trim())
    if(node) instance.select_node(node); publish()
  }
}
async function rename() {
  const node=instance.get_selected_node() || instance.get_root()
  const topic=await dialog.value.open({type:'prompt',title:'编辑节点',value:node.topic})
  if(topic?.trim() && !stopped) {instance.update_node(node.id,topic.trim()); publish()}
}
async function remove() {
  const node=instance.get_selected_node()
  if(!node || node.isroot) {await dialog.value.open({type:'alert',title:'选择节点',message:'请选择一个非根节点。'}); return}
  if(await dialog.value.open({title:'删除节点',message:'将同时删除它的子节点。'})) {if(!stopped) {instance.remove_node(node.id); publish()}}
}
function editDoubleClick(event) {
  const element=event.target.closest('jmnode[nodeid]')
  if(element && instance) {instance.select_node(element.getAttribute('nodeid'));rename()}
}
function changeZoom(step) {autoFit=false;setScale(Math.max(0.2,Math.min(2,Math.round((instance.view.zoom_current+step)*100)/100)))}
function resetZoom() {autoFit=false;setScale(1)}
function zoomWheel(event) {if(event.ctrlKey || event.metaKey) {event.preventDefault();changeZoom(event.deltaY < 0 ? 0.1 : -0.1)}}
function centerRoot() {instance.scroll_node_to_center(instance.get_root())}
function fold(collapse) {if(collapse) instance.collapse_all();else instance.expand_all();scheduleFit()}
async function toggleExpanded() {expanded.value=!expanded.value;await nextTick();scheduleFit()}
function escapeExpanded(event) {if(event.key === 'Escape' && expanded.value && !event.target.closest('.zh-dialog-mask')) toggleExpanded()}
watch(() => props.modelValue, value => {if(JSON.stringify(value) !== last) show(value)}, {deep:true,flush:'post'})
onMounted(async () => {
  await nextTick();if(stopped) return
  instance=new jsMind({container:host.value,editable:true,support_html:false,theme:'zhihui',shortcut:{enable:false},
    default_event_handle:{enable_dblclick_handle:false,enable_mousewheel_handle:false},
    view:{engine:'svg',draggable:true,node_overflow:'wrap',hmargin:64,vmargin:48,line_width:2,line_color:'#b4cdc8',custom_node_render:renderNode,zoom:{min:0.2,max:2,step:0.1}},
    layout:{hspace:48,vspace:24,pspace:20,cousin_space:12},log_level:'error'})
  instance.add_event_listener(type => {if(type === jsMind.event_type.edit) publish();else decorate()})
  show(props.modelValue)
  observer=new ResizeObserver(entries => {
    const rect=entries[0].contentRect, size=rect.width+':'+rect.height
    if(size === previousSize || !instance || stopped) return
    previousSize=size; if(autoFit) scheduleFit();else setScale(instance.view.zoom_current)
  })
  observer.observe(host.value)
  document.fonts?.ready.then(() => {if(!stopped) show(props.modelValue)})
  window.addEventListener('keydown',escapeExpanded)
})
onBeforeUnmount(() => {
  stopped=true;observer?.disconnect();cancelAnimationFrame(frame)
  window.removeEventListener('keydown',escapeExpanded);instance?.clear_event_listener()
  // jsMind has no dispose API. Its handlers are attached to the detached panel.
  // End a pending drag before removing that panel to clear plugin timers.
  host.value?.querySelector('.jsmind-inner')?.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}))
  host.value?.replaceChildren(); instance=null
})
</script>
<template>
  <div class="mind-editor" :class="{'mind-editor-expanded':expanded}">
    <div class="mind-toolbar">
      <div class="mind-tools" role="group" aria-label="节点编辑">
        <button class="btn btn-sm mind-add" @click="add()"><span aria-hidden="true">＋</span> 新增子节点</button>
        <button class="btn btn-sm mind-tool" @click="add(true)">新增同级</button>
        <span class="mind-divider"></span>
        <button class="btn btn-sm mind-tool" @click="rename">编辑节点</button>
        <button class="btn btn-sm mind-tool mind-delete" @click="remove">删除节点</button>
      </div>
      <div class="mind-tools">
        <button class="btn btn-sm mind-tool" @click="fold(false)">展开全部</button>
        <button class="btn btn-sm mind-tool" @click="fold(true)">收起分支</button>
        <button class="btn btn-sm mind-tool mind-expand" :aria-label="expanded ? '退出全屏' : '全屏编辑'" :title="expanded ? '退出全屏（Esc）' : '全屏编辑'" @click="toggleExpanded">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" /></svg>
        </button>
      </div>
    </div>
    <div class="mind-canvas-wrap">
      <div ref="host" class="zh-mindmap" aria-label="思维导图编辑区" @dblclick="editDoubleClick" @click="decorate" @wheel="zoomWheel"></div>
      <div class="mind-canvas-hint"><span class="mind-hint-dot"></span> 双击编辑 · 拖动节点调整层级</div>
      <div class="mind-navigation" role="group" aria-label="画布视图">
        <button aria-label="缩小" title="缩小" :disabled="zoom <= 20" @click="changeZoom(-0.1)">−</button>
        <button class="mind-zoom-value" aria-label="恢复100%" title="恢复100%" @click="resetZoom">{{ zoom }}%</button>
        <button aria-label="放大" title="放大" :disabled="zoom >= 200" @click="changeZoom(0.1)">＋</button>
        <span class="mind-divider"></span>
        <button class="mind-navigation-text" @click="fit">适应画布</button>
        <button class="mind-navigation-text" @click="centerRoot">回到中心</button>
      </div>
    </div>
    <div class="mind-status"><span>{{ count }} 个节点<span class="mind-status-separator">·</span>Ctrl + 滚轮缩放</span><span class="mind-selection">{{ selectedTopic ? '已选中：'+selectedTopic : '点击节点开始整理思路' }}</span></div>
    <AppDialog ref="dialog" />
  </div>
</template>
<style>
.mind-editor { min-width:0; display:flex; flex-direction:column; }
.mind-toolbar { display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; margin:0 0 12px; }
.mind-tools { display:flex; align-items:center; flex-wrap:wrap; gap:4px; }
.mind-tool { color:#58676c; border:1px solid transparent; padding:7px 10px; font-size:12px; }
.mind-tool:hover { color:#0d7a6f; background:#edf5f2; }
.mind-add { color:#096e60; background:#e8f4ee; padding:7px 12px; font-size:12px; font-weight:600; border:1px solid #d2e7de; }
.mind-add:hover { color:#095c54; background:#dcefe5; border-color:#b3d4c6; }
.mind-delete:hover { color:#b34b55; background:#fff0f1; }
.mind-divider { width:1px; height:18px; background:#e0e7e5; margin:0 5px; flex-shrink:0; }
.mind-expand { display:flex; align-items:center; padding:8px; }
.mind-canvas-wrap { position:relative; flex:1; min-height:0; border:1px solid #dfe8e3; border-radius:12px; overflow:hidden; background:#f8faf8; }
.zh-mindmap { height:clamp(420px,calc(100vh - 285px),680px); min-height:360px; overflow:hidden; background-image:radial-gradient(#dce6e0 0.8px,transparent 0.8px); background-size:20px 20px; }
.zh-mindmap .jsmind-inner { scrollbar-width:thin; scrollbar-color:#cddcd3 transparent; }
/* Stable intrinsic width is necessary while jmnodes is initially empty.
   max-content + wrap mode prevents measuring a zero-width parent. */
.zh-mindmap jmnodes.theme-zhihui jmnode { box-sizing:content-box; width:max-content; min-width:52px; max-width:210px; padding:11px 16px; border:0; border-radius:9px; font:600 14px/1.5 'Segoe UI','Microsoft YaHei',sans-serif; white-space:pre-wrap; overflow-wrap:anywhere; color:#34493f; background:#fff; box-shadow:inset 3px 0 0 var(--branch-color),inset 0 0 0 1px #e0e8e2,0 2px 5px #203b2810; text-align:left; }
.zh-mindmap jmnodes.theme-zhihui jmnode[data-depth="1"] { background:var(--branch-soft); color:var(--branch-color); }
.zh-mindmap jmnodes.theme-zhihui jmnode.root { max-width:250px; min-width:100px; padding:18px 24px; border-radius:14px; font-size:20px; font-weight:700; color:#fff; background:linear-gradient(135deg,#0e7c69,#075e52); box-shadow:0 6px 16px #0d7a6f25; }
.zh-mindmap jmnodes.theme-zhihui jmnode:hover { outline:1px solid var(--branch-color); outline-offset:2px; }
.zh-mindmap jmnodes.theme-zhihui jmnode.selected { outline:2px solid var(--branch-color); outline-offset:3px; }
.zh-mindmap jmnodes.theme-zhihui jmexpander { box-sizing:content-box; width:14px; height:14px; border:1px solid #c1d5ca; border-radius:50%; background:#fff; color:#628370; font:12px/14px 'Segoe UI',sans-serif; }
.zh-mindmap svg.jsmind { pointer-events:none; }
.mind-canvas-hint { pointer-events:none; position:absolute; z-index:3; top:16px; left:18px; display:flex; align-items:center; gap:8px; color:#8a9c90; font-size:11px; }
.mind-hint-dot { width:6px; height:6px; border-radius:50%; background:#8bafa0; }
.mind-navigation { position:absolute; z-index:3; bottom:16px; right:16px; display:flex; align-items:center; padding:5px; border:1px solid #e0e8e2; border-radius:10px; background:#fffffff2; box-shadow:0 3px 12px #29442c0c; }
.mind-navigation button { border:0; background:transparent; color:#516659; min-width:30px; height:30px; padding:0 7px; border-radius:6px; font-size:17px; }
.mind-navigation button:hover { background:#edf4ee; color:#0d7a6f; }
.mind-navigation button:disabled { opacity:.35; }
.mind-navigation .mind-zoom-value { min-width:49px; font-size:12px; font-variant-numeric:tabular-nums; }
.mind-navigation .mind-navigation-text { font-size:12px; white-space:nowrap; }
.mind-status { display:flex; justify-content:space-between; gap:14px; color:#8a9790; font-size:11px; padding:10px 2px 0; }
.mind-status-separator { padding:0 10px; }
.mind-selection { max-width:45%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.mind-editor-expanded { position:fixed; inset:16px; z-index:1040; padding:20px; background:#fff; border:1px solid #dce7df; border-radius:16px; box-shadow:0 0 0 30px #20362dcc; }
.mind-editor-expanded .zh-mindmap { height:100%; min-height:0; }
@media (max-width:575px) {
  .mind-toolbar { gap:6px; }
  .mind-tool { padding:6px 7px; }
  .mind-add { padding:6px 8px; }
  .mind-canvas-hint { top:12px; left:12px; font-size:10px; }
  .mind-navigation { bottom:10px; left:10px; right:auto; padding:3px; }
  .mind-navigation button { padding:0 5px; min-width:26px; }
  .mind-navigation .mind-navigation-text { font-size:11px; }
  .mind-status { font-size:10px; }
  .mind-selection { display:none; }
  .mind-editor-expanded { inset:6px; padding:12px; }
}
</style>
