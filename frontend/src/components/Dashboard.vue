<template>
  <div class="dashboard">
    <el-container>
      <el-header>
        <div class="header-content">
          <h2>个性化背词系统</h2>
          <div class="user-info">
            <span>得分: {{ score }}</span>
            <el-button @click="logout">退出</el-button>
            <el-button @click="resetProgress">重置进度</el-button>
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
                <el-menu-item @click="showOverviewPanel">
                  <span>学习总览</span>
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
            
            <!-- 学习总览 -->
            <overview-panel 
              v-if="currentView === 'overview'"
              :total-words="words.length"
              :score="score"
              :wrong-words-count="wrongWordsCount"
              :learning-stats="learningStats"
            />
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import WordList from './WordList.vue'
import Learning from './Learning.vue'
import OverviewPanel from './OverviewPanel.vue'

export default {
  name: 'Dashboard',
  components: {
    WordList,
    Learning,
    OverviewPanel
  },
  
  setup() {
    const router = useRouter()
    const currentView = ref('wordList')
    const words = ref([])
    const learningWords = ref([])
    const learningMode = ref('')
    const score = ref(0)
    const wrongWordsCount = ref(0)
    const learningStats = ref({
      totalLearned: 0,
      correctRate: 0,
      lastLearningDate: null
    })

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
        if (!token) {
          ElMessage.error('登录凭证已过期，请重新登录')
          return
        }

        const response = await axios.get('/api/score', {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 5000  // 5-second timeout
        })

        console.log('Score Response:', response.data)

        if (response.data && response.data.score !== undefined) {
          score.value = response.data.score
        } else {
          console.warn('Unexpected score response:', response.data)
          ElMessage.warning('获取分数时出现异常')
        }
      } catch (error) {
        console.error('Error fetching score:', error)
        
        if (error.response) {
          const errorData = error.response.data
          ElMessage.error({
            message: errorData.message || '获取分数失败',
            duration: 3000
          })
        } else if (error.request) {
          ElMessage.error({
            message: '网络错误，无法获取分数',
            duration: 3000
          })
        } else {
          ElMessage.error({
            message: '请求发送失败',
            duration: 3000
          })
        }
      }
    }

    const fetchWrongWords = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/wrong-words', {
          headers: { Authorization: `Bearer ${token}` }
        })
        wrongWordsCount.value = response.data.length
      } catch (error) {
        console.error('Error fetching wrong words:', error)
      }
    }

    const fetchLearningStats = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/learning-stats', {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 5000  // 5秒超时
        })
        
        learningStats.value = response.data
        
        // 如果没有数据，显示默认值
        if (!learningStats.value.totalLearned) {
          console.warn('No learning stats available')
          learningStats.value = {
            totalLearned: 0,
            correctRate: 0,
            lastLearningDate: null
          }
        }
      } catch (error) {
        console.error('Error fetching learning stats:', error)
        
        // 详细的错误处理
        if (error.response) {
          // 服务器返回错误
          const errorData = error.response.data
          console.error('Server error details:', errorData)
          
          ElMessage.error({
            message: errorData.message || '获取学习统计失败',
            description: errorData.error_type 
              ? `错误类型：${errorData.error_type}\n详细信息：${errorData.error}`
              : '',
            duration: 5000
          })
        } else if (error.request) {
          // 网络错误或请求未发送
          ElMessage.error({
            message: '网络错误，无法获取学习统计',
            description: '请检查您的网络连接并重试',
            duration: 3000
          })
        } else {
          // 其他未知错误
          ElMessage.error({
            message: '未知错误，获取学习统计失败',
            description: error.message,
            duration: 3000
          })
        }
        
        // 设置默认值
        learningStats.value = {
          totalLearned: 0,
          correctRate: 0,
          lastLearningDate: null
        }
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

    const showOverviewPanel = () => {
      currentView.value = 'overview'
      fetchWrongWords()
      fetchLearningStats()
    }

    const finishLearning = () => {
      currentView.value = 'wordList'
      fetchScore()
    }

    const logout = () => {
      localStorage.removeItem('token')
      router.push('/login')
    }

    const resetProgress = async () => {
      try {
        // 显示确认对话框
        const confirmReset = await ElMessageBox.confirm(
          '确定要重置所有学习进度吗？这将清除您的所有学习记录和分数。', 
          '重置确认', 
          {
            confirmButtonText: '确定重置',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        if (confirmReset) {
          const token = localStorage.getItem('token')
          const response = await axios.post('/api/reset', {}, {
            headers: { 
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json'
            },
            timeout: 5000  // 5秒超时
          })
          
          // 重置本地状态
          score.value = 0
          words.value = []
          learningWords.value = []
          wrongWordsCount.value = 0
          learningStats.value = {
            totalLearned: 0,
            correctRate: 0,
            lastLearningDate: null
          }
          
          // 重新获取单词列表和统计信息
          await Promise.all([
            fetchWords(),
            fetchWrongWords(),
            fetchLearningStats()
          ])
          
          // 显示成功消息和详细信息
          ElMessage.success({
            message: response.data.message,
            description: response.data.details 
              ? `单词进度重置：${response.data.details.word_progress_reset} 行\n用户分数重置：${response.data.details.user_score_reset} 行`
              : '',
            duration: 3000
          })
        }
      } catch (error) {
        console.error('Error resetting progress:', error)
        
        // 更详细的错误处理
        if (error.response) {
          // 服务器返回错误
          const errorData = error.response.data
          ElMessage.error({
            message: errorData.message || '重置失败',
            description: errorData.error_type 
              ? `错误类型：${errorData.error_type}\n详细信息：${errorData.error}`
              : '',
            duration: 5000
          })
        } else if (error.request) {
          // 网络错误或请求未发送
          ElMessage.error({
            message: '网络错误，无法重置进度',
            description: '请检查您的网络连接并重试',
            duration: 3000
          })
        } else {
          // 其他未知错误
          ElMessage.error({
            message: '未知错误，重置失败',
            description: error.message,
            duration: 3000
          })
        }
      }
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
      wrongWordsCount,
      learningStats,
      startLearning,
      reviewWrongWords,
      showOverviewPanel,
      finishLearning,
      logout,
      resetProgress
    }
  }
}
</script>

<style scoped>
.dashboard {
  height: 100vh;
  background-color: #f5f5f5;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.menu-card {
  margin-bottom: 20px;
}
</style>
