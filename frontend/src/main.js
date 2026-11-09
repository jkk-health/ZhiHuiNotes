import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// Bootstrap 5 样式（JS 交互组件按需在后引入，仅用 CSS 已覆盖当前需求）
import 'bootstrap/dist/css/bootstrap.min.css'
import './assets/main.css'

createApp(App).use(router).mount('#app')
