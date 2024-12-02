<template>
  <div class="dashboard">
    <el-container>
      <el-header>
        <div class="header-content">
          <h2>个性化背词系统</h2>
          <div class="user-info">
            <span>得分: {{ score }}</span>
            <span>连续打卡: {{ streakDays }}天</span>
            <el-button @click="logout">退出</el-button>
          </div>
        </div>
      </el-header>
      
      <el-main>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card>
              <template #header>
                <div class="card-header">
                  <span>功能菜单</span>
                </div>
              </template>
              <el-menu>
                <el-menu-item @click="currentView = 'wordList'">
                  <span>单词预览</span>
                </el-menu-item>
                <el-menu-item @click="startLearning">
                  <span>背诵单词</span>
                </el-menu-item>
                <el-menu-item @click="reviewWrongWords">
                  <span>错题复习</span>
                </el-menu-item>
              </el-menu>
            </el-card>
          </el-col>
          
          <el-col :span="18">
            <!-- 单词列表 -->
            <word-list v-if="currentView === 'wordList'" :words="words" />
            
            <!-- 学习界面 -->
            <learning v-if="currentView === 'learning'"
                     :words="learningWords"
                     :mode="learningMode"
                     @finish="finishLearning" />
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import WordList from './WordList.vue'
import Learning from './Learning.vue'

export default {
  name: 'Dashboard',
  components: {
    WordList,
    Learning
  },
  
  setup() {
    const router = useRouter()
    const currentView = ref('wordList')
    const words = ref([])
    const learningWords = ref([])
    const learningMode = ref('')
    const score = ref(0)
    const streakDays = ref(0)

    const fetchWords = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/words', {
          headers: { Authorization: `Bearer ${token}` }
        })
        words.value = response.data
      } catch (error) {
        console.error('Error fetching words:', error)
      }
    }

    const fetchScore = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/score', {
          headers: { Authorization: `Bearer ${token}` }
        })
        score.value = response.data.score
        streakDays.value = response.data.streak_days
      } catch (error) {
        console.error('Error fetching score:', error)
      }
    }

    const startLearning = () => {
      learningWords.value = words.value
      learningMode.value = 'ch2en'
      currentView.value = 'learning'
    }

    const reviewWrongWords = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/words/wrong', {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (response.data.length === 0) {
          alert('没有错题，继续保持！')
          return
        }
        learningWords.value = response.data
        learningMode.value = 'ch2en'
        currentView.value = 'learning'
      } catch (error) {
        console.error('Error fetching wrong words:', error)
      }
    }

    const finishLearning = () => {
      currentView.value = 'wordList'
      fetchScore()
    }

    const logout = () => {
      localStorage.removeItem('token')
      router.push('/login')
    }

    onMounted(() => {
      fetchWords()
      fetchScore()
    })

    return {
      currentView,
      words,
      learningWords,
      learningMode,
      score,
      streakDays,
      startLearning,
      reviewWrongWords,
      finishLearning,
      logout
    }
  }
}
</script>

<style scoped>
.dashboard {
  height: 100vh;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 20px;
}

.el-header {
  background-color: #fff;
  border-bottom: 1px solid #dcdfe6;
  padding: 0 20px;
}

.el-main {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>
