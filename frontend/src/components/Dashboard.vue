<template>
  <div class="dashboard">
    <el-container>
      <el-header>
        <div class="header-content">
          <h2>个性化背词系统</h2>
          <div class="user-info">
            <span>得分: {{ score }}</span>
            <el-button @click="logout">退出</el-button>
          </div>
        </div>
      </el-header>
      
      <el-main>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card class="menu-card">
              <template #header>
                <div class="card-header">
                  <span>功能菜单</span>
                </div>
              </template>
              <el-menu>
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
      } catch (error) {
        console.error('Error fetching score:', error)
      }
    }

    const startLearning = async () => {
      try {
        currentView.value = 'learning'
        learningMode.value = 'normal'
        learningWords.value = words.value.slice(0, 10)
      } catch (error) {
        console.error('Error starting learning:', error)
      }
    }

    const reviewWrongWords = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/wrong-words', {
          headers: { Authorization: `Bearer ${token}` }
        })
        learningWords.value = response.data
        learningMode.value = 'review'
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
  min-height: 100vh;
}

.el-header {
  background-color: var(--surface);
  box-shadow: var(--elevation-1);
  position: fixed;
  width: 100%;
  z-index: 1000;
  padding: 0;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-content h2 {
  margin: 0;
  color: var(--primary-color);
  font-weight: 500;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 24px;
}

.user-info span {
  font-size: 14px;
  color: var(--on-surface);
  display: flex;
  align-items: center;
  gap: 4px;
}

.el-main {
  padding-top: 84px;
  background-color: #f5f5f5;
  min-height: calc(100vh - 60px);
}

.el-row {
  max-width: 1400px;
  margin: 0 auto !important;
}

.menu-card .el-card__header {
  padding: 16px;
  border-bottom: none;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 500;
  color: var(--primary-color);
}

.el-menu-item {
  margin: 4px 0;
}

.el-menu-item span {
  font-size: 14px;
}

.content-card {
  margin-bottom: 20px;
  border-radius: 8px;
  box-shadow: var(--elevation-1);
}

@media (max-width: 768px) {
  .el-header {
    padding: 0 16px;
  }
  
  .header-content {
    padding: 0;
  }
  
  .user-info {
    gap: 16px;
  }
  
  .el-main {
    padding: 76px 16px 16px;
  }
}
</style>
