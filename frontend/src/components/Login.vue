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
          <el-button @click="handleCheckin">打卡</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

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
        const url = isLogin.value ? '/api/auth/login' : '/api/auth/register'
        const response = await axios.post(url, form)
        
        if (isLogin.value) {
          localStorage.setItem('token', response.data.token)
          router.push('/dashboard')
        } else {
          isLogin.value = true
        }
      } catch (error) {
        console.error('Error:', error)
      }
    }

    const toggleMode = () => {
      isLogin.value = !isLogin.value
    }

    const handleCheckin = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          alert('请先登录')
          return
        }
        
        const response = await axios.post('/api/checkin', null, {
          headers: { Authorization: `Bearer ${token}` }
        })
        alert(`打卡成功！连续打卡${response.data.streak_days}天`)
      } catch (error) {
        console.error('Error:', error)
      }
    }

    return {
      isLogin,
      form,
      handleSubmit,
      toggleMode,
      handleCheckin
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
