<script setup>
// 所见即所得编辑器（Quill）：用户直接打字，不再手写 Markdown 语法。
// 对外：v-model 收富文本 HTML；@text-change 抛纯文本（给全文搜索当副本）。
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Quill from 'quill'
import 'quill/dist/quill.snow.css'
import DOMPurify from 'dompurify'

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'text-change', 'alert'])

const host = ref(null)
let quill = null
let syncing = false // true = 程序在写入内容，此时不要把变更回抛给父组件（防死循环）

const MAX_IMAGE_BYTES = 2 * 1024 * 1024 // 单图上限 2MB（base64 内嵌，再大笔记会很肥）

const TOOLBAR = [
  [{ header: [1, 2, 3, false] }],
  [{ size: ['small', false, 'large', 'huge'] }],
  ['bold', 'italic', 'underline', 'strike'],
  [{ color: [] }, { background: [] }],
  [{ list: 'ordered' }, { list: 'bullet' }],
  [{ align: [] }],
  ['blockquote', 'code-block'],
  ['link', 'image'],
  ['clean'],
]

// ---------------------------------------------------------- 插入图片 --
// 图片转 base64 直接内嵌进正文（不依赖后端上传接口）
function pickImage() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = () => {
    const file = input.files && input.files[0]
    if (!file) return
    if (file.size > MAX_IMAGE_BYTES) {
      // 走自定义模态框（@alert），不能用原生 window.alert：
      // 原生同步对话框关闭后 Quill 编辑器会失去焦点恢复能力，表现为“卡死不能输入”
      emit('alert', `图片不能超过 2MB，当前 ${(file.size / 1024 / 1024).toFixed(1)}MB`)
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      const range = quill.getSelection(true)
      quill.insertEmbed(range.index, 'image', reader.result, 'user')
      quill.setSelection(range.index + 1)
    }
    reader.readAsDataURL(file)
  }
  input.click()
}

// ---------------------------------------------------------- 工具栏中文化 --
const LABELS = {
  'ql-size': { '': '正常', small: '小', large: '大', huge: '特大' },
  'ql-header': { '': '正文', 1: '标题 1', 2: '标题 2', 3: '标题 3' },
  'ql-align': { '': '左对齐', center: '居中', right: '右对齐', justify: '两端对齐' },
}

const TITLES = {
  'ql-bold': '加粗',
  'ql-italic': '斜体',
  'ql-underline': '下划线',
  'ql-strike': '删除线',
  'ql-color': '字体颜色',
  'ql-background': '背景色',
  'ql-blockquote': '引用',
  'ql-code-block': '代码块',
  'ql-link': '插入链接',
  'ql-image': '插入图片',
  'ql-clean': '清除格式',
}

function localizeToolbar(root) {
  Object.entries(LABELS).forEach(([cls, map]) => {
    root.querySelectorAll(`select.${cls} option`).forEach((opt) => {
      if (opt.value in map) opt.textContent = map[opt.value]
    })
  })
  Object.entries(TITLES).forEach(([cls, title]) => {
    root.querySelector(`button.${cls}`)?.setAttribute('title', title)
  })
  root.querySelector('.ql-color')?.setAttribute('title', '字体颜色')
  root.querySelector('.ql-background')?.setAttribute('title', '背景色')
  Object.entries(LABELS).forEach(([cls, map]) => {
    root.querySelectorAll(`.${cls} .ql-picker-item, .${cls} .ql-picker-label`).forEach((item) => {
      const value = item.getAttribute('data-value') || ''
      if (value in map) item.setAttribute('data-label', map[value])
    })
  })
}

// ---------------------------------------------------------- 内容读写 --

function setHtml(html) {
  if (!quill) return
  syncing = true
  quill.setText('')
  quill.clipboard.dangerouslyPasteHTML(0, DOMPurify.sanitize(html || ''), 'silent')
  syncing = false
}

onMounted(() => {
  quill = new Quill(host.value, {
    theme: 'snow',
    placeholder: '像 Word 一样直接写：选中文字就能改字号、加粗、插图片…',
    modules: { toolbar: { container: TOOLBAR, handlers: { image: pickImage } } },
  })
  localizeToolbar(quill.getModule('toolbar').container)
  setHtml(props.modelValue)

  quill.on('text-change', () => {
    if (syncing) return
    const html = quill.root.innerHTML
    const clean = DOMPurify.sanitize(html) // 存库前先消毒，挡掉脚本/事件属性
    emit('update:modelValue', clean === '<p><br></p>' ? '' : clean)
    emit('text-change', quill.getText())
  })
})

// 切换到另一篇笔记时，父组件换了 modelValue -> 灌进编辑器
watch(
  () => props.modelValue,
  (v) => {
    if (!quill || syncing) return
    if ((v || '') !== quill.root.innerHTML) setHtml(v)
  },
)

onBeforeUnmount(() => {
  quill = null
})
</script>

<template>
  <!-- Quill 会在这里面自己插工具栏 + 编辑区 -->
  <div class="zh-rich"><div ref="host"></div></div>
</template>

<style>
/* 注意：Quill 的节点是运行时生成的，scoped 样式打不到，只能用全局 */
.zh-rich .ql-toolbar.ql-snow {
  border-color: #e4e9eb;
  border-radius: 8px 8px 0 0;
  background: #fbfcfc;
}

.zh-rich .ql-container.ql-snow {
  border-color: #e4e9eb;
  border-radius: 0 0 8px 8px;
  background: #fff;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
}

.zh-rich .ql-editor {
  min-height: 52vh;
  font-size: 1rem;
  line-height: 1.8;
  color: #1f2933;
}

.zh-rich .ql-editor.ql-blank::before {
  color: #9aa5b1;
  font-style: normal;
}

/* Quill 的字号是 class 控制的，这里定成中文阅读习惯的档位 */
.zh-rich .ql-size-small {
  font-size: 0.85rem;
}

.zh-rich .ql-size-large {
  font-size: 1.2rem;
}

.zh-rich .ql-size-huge {
  font-size: 1.5rem;
}

.zh-rich .ql-editor img {
  max-width: 100%;
  border-radius: 6px;
}
</style>
