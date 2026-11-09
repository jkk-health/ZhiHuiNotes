import { onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
let exitGuard = null
export const requestExit = () => exitGuard ? exitGuard() : Promise.resolve(true)
export function useUnsaved(dirty, dialog, save, discard) {
  async function check() {
    if (!dirty.value) return true
    const result = await dialog.value.open({ type: 'unsaved', title: '修改尚未保存', message: '保存当前修改后继续，或放弃修改。' })
    if (result === 'save') return Boolean(await save())
    if (result === 'discard') { discard(); return true }
    return false
  }
  const beforeUnload = (event) => { if (dirty.value) { event.preventDefault(); event.returnValue = '' } }
  onBeforeRouteLeave(check)
  onMounted(() => { exitGuard = check; window.addEventListener('beforeunload', beforeUnload) })
  onBeforeUnmount(() => { if (exitGuard === check) exitGuard = null; window.removeEventListener('beforeunload', beforeUnload) })
  return check
}
