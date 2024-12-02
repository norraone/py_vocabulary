import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import axios from 'axios'
import App from './App.vue'
import router from './router'

// Remove the baseURL since we're using Vite's proxy
// axios.defaults.baseURL = 'http://localhost:5000'

const app = createApp(App)

app.use(ElementPlus)
app.use(router)

app.mount('#app')
