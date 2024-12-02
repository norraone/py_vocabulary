<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2>{{ isLogin ? '登录' : '注册' }}</h2>
      </template>
      
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名"></el-input>
        </el-form-item>
        
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码"></el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit">{{ isLogin ? '登录' : '注册' }}</el-button>
          <el-button @click="toggleMode">{{ isLogin ? '去注册' : '去登录' }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const isLogin = ref(true)
    const form = reactive({
      username: '',
      password: ''
    })

    const handleSubmit = async () => {
      try {
        if (!form.username || !form.password) {
          ElMessage.warning('请输入用户名和密码')
          return
        }

        // Log form submission
        console.log('%c[Request] Form Submission', 'color: #4CAF50; font-weight: bold')
        console.log('Form state:', { 
          mode: isLogin.value ? 'login' : 'register',
          username: form.username,
          password: '****'
        })

        // Use relative path for API endpoints
        const url = isLogin.value ? '/api/auth/login' : '/api/auth/register'
        console.log('%c[Request] Endpoint', 'color: #2196F3; font-weight: bold', url)

        // Log request configuration
        const config = {
          method: 'POST',
          url: url,
          data: {
            username: form.username,
            password: form.password
          },
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          withCredentials: false
        }
        console.log('%c[Request] Configuration', 'color: #2196F3; font-weight: bold', {
          ...config,
          data: { ...config.data, password: '****' }
        })

        // Make request
        console.log('%c[Request] Sending...', 'color: #FFC107; font-weight: bold')
        const response = await axios(config)
        
        // Log successful response
        console.log('%c[Response] Success', 'color: #4CAF50; font-weight: bold', {
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
          data: response.data
        })
        
        if (isLogin.value) {
          localStorage.setItem('token', response.data.token)
          console.log('%c[Auth] Token stored', 'color: #9C27B0; font-weight: bold')
          ElMessage.success('登录成功')
          router.push('/dashboard')
        } else {
          isLogin.value = true
          form.password = ''  // Clear password after registration
          ElMessage.success('注册成功，请登录')
        }
      } catch (error) {
        // Log error details
        console.log('%c[Error] Request Failed', 'color: #f44336; font-weight: bold')
        console.error('Error details:', {
          name: error.name,
          message: error.message,
          status: error.response?.status,
          statusText: error.response?.statusText,
          headers: error.response?.headers,
          data: error.response?.data,
          config: {
            ...error.config,
            data: error.config?.data ? JSON.parse(error.config.data) : undefined
          }
        })
        
        if (error.response?.status === 403) {
          console.error('%c[Error] CORS Issue Detected', 'color: #f44336; font-weight: bold')
          ElMessage.error('请求被拒绝，可能是CORS问题')
        } else {
          ElMessage.error(error.response?.data?.message || '操作失败，请稍后重试')
        }
      }
    }

    const toggleMode = () => {
      isLogin.value = !isLogin.value
    }

    return {
      isLogin,
      form,
      handleSubmit,
      toggleMode
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}

.login-card {
  width: 400px;
}
</style>
