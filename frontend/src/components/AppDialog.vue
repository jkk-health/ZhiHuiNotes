<script setup>
import { nextTick, ref } from 'vue'
const state = ref(null)
const input = ref(null)
let resolve
function open(options) {
  if (resolve) resolve(null)
  state.value = { type: 'confirm', value: '', ...options }
  nextTick(() => input.value?.focus())
  return new Promise((r) => { resolve = r })
}
function close(value) {
  state.value = null
  const done = resolve
  resolve = null
  done?.(value)
}
defineExpose({ open })
</script>
<template>
  <div v-if="state" class="zh-dialog-mask" @click.self="close(null)" @keydown.esc="close(null)">
    <section class="zh-dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" tabindex="-1">
      <h2 id="dialog-title" class="h5">{{ state.title }}</h2>
      <p class="text-muted text-break" style="white-space: pre-line">{{ state.message }}</p>
      <input v-if="state.type === 'prompt'" ref="input" v-model="state.value" class="form-control" :placeholder="state.label" maxlength="200" @keyup.enter="close(state.value)" />
      <div class="d-flex justify-content-end gap-2 mt-3">
        <button v-if="state.type !== 'alert'" class="btn btn-outline-secondary" @click="close(null)">取消</button>
        <button v-if="state.type === 'unsaved'" class="btn btn-outline-danger" @click="close('discard')">放弃修改</button>
        <button class="btn btn-primary" @click="close(state.type === 'prompt' ? state.value : state.type === 'unsaved' ? 'save' : true)">{{ state.type === 'unsaved' ? '保存并继续' : '确定' }}</button>
      </div>
    </section>
  </div>
</template>
<style>
.zh-dialog-mask { position:fixed; inset:0; background:#0f172a70; z-index:1080; display:flex; align-items:center; justify-content:center; }
.zh-dialog { width:min(460px,94vw); background:white; color:#1f2933; padding:24px; border-radius:16px; box-shadow:0 20px 60px #0003; }
</style>
