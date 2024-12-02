import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import axios from 'axios'
import App from './App.vue'
import router from './router'

// 配置axios默认值
axios.defaults.baseURL = 'http://localhost:5000'

const app = createApp(App)

app.use(ElementPlus)
app.use(router)

app.mount('#app')
