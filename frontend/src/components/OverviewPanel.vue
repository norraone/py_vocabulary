<template>
  <el-card class="overview-panel">
    <template #header>
      <div class="card-header">
        <span>学习总览</span>
      </div>
    </template>
    
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover" class="stats-card">
          <template #header>
            <div class="card-header">词汇统计</div>
          </template>
          <div class="stats-content">
            <div class="stat-item">
              <span>总单词数</span>
              <span class="stat-value">{{ totalWords }}</span>
            </div>
            <div class="stat-item">
              <span>错误单词数</span>
              <span class="stat-value error">{{ wrongWordsCount }}</span>
            </div>
            <div class="stat-item">
              <span>已学习单词数</span>
              <span class="stat-value">{{ learningStats.totalLearned }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover" class="score-card">
          <template #header>
            <div class="card-header">学习进度</div>
          </template>
          <div class="stats-content">
            <div class="stat-item">
              <span>当前得分</span>
              <span class="stat-value">{{ score }}</span>
            </div>
            <div class="stat-item">
              <span>正确率</span>
              <span class="stat-value">{{ (learningStats.correctRate * 100).toFixed(2) }}%</span>
            </div>
            <div class="stat-item">
              <span>最近学习</span>
              <span class="stat-value">{{ formatDate(learningStats.lastLearningDate) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-card shadow="hover" class="learning-chart">
      <template #header>
        <div class="card-header">学习趋势</div>
      </template>
      <div class="chart-container">
        <canvas ref="learningChart" height="200"></canvas>
      </div>
    </el-card>
  </el-card>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import Chart from 'chart.js/auto'
import { ElMessage } from 'element-plus'

export default {
  name: 'OverviewPanel',
  props: {
    totalWords: {
      type: Number,
      default: 0
    },
    score: {
      type: Number,
      default: 0
    },
    wrongWordsCount: {
      type: Number,
      default: 0
    },
    learningStats: {
      type: Object,
      default: () => ({
        totalLearned: 0,
        correctRate: 0,
        lastLearningDate: null
      })
    }
  },
  
  setup(props) {
    const learningChart = ref(null)
    const learningTrend = ref([])
    
    const formatDate = (dateString) => {
      if (!dateString) return '暂无记录'
      const date = new Date(dateString)
      return date.toLocaleDateString()
    }
    
    const fetchLearningTrend = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/learning-trend', {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 5000  // 5秒超时
        })
        
        learningTrend.value = response.data
        
        // 如果没有数据，显示空状态
        if (learningTrend.value.length === 0) {
          console.warn('No learning trend data available')
          initChart()  // 仍然调用初始化，显示空状态
        } else {
          initChart()
        }
      } catch (error) {
        console.error('Error fetching learning trend:', error)
        
        // 详细的错误处理
        if (error.response) {
          // 服务器返回错误
          const errorData = error.response.data
          console.error('Server error details:', errorData)
          
          ElMessage.error({
            message: errorData.message || '获取学习趋势失败',
            description: errorData.error_type 
              ? `错误类型：${errorData.error_type}\n详细信息：${errorData.error}`
              : '',
            duration: 5000
          })
        } else if (error.request) {
          // 网络错误或请求未发送
          ElMessage.error({
            message: '网络错误，无法获取学习趋势',
            description: '请检查您的网络连接并重试',
            duration: 3000
          })
        } else {
          // 其他未知错误
          ElMessage.error({
            message: '未知错误，获取学习趋势失败',
            description: error.message,
            duration: 3000
          })
        }
        
        // 即使出错也初始化图表，显示错误状态
        initChart()
      }
    }
    
    const initChart = () => {
      if (!learningChart.value) return
      
      const ctx = learningChart.value.getContext('2d')
      
      // 如果之前有图表实例，销毁它
      if (window.learningChartInstance) {
        window.learningChartInstance.destroy()
      }
      
      // 如果没有数据，显示空状态
      if (learningTrend.value.length === 0) {
        ctx.font = '16px Arial'
        ctx.fillStyle = '#999'
        ctx.textAlign = 'center'
        ctx.fillText('暂无学习数据', ctx.canvas.width / 2, ctx.canvas.height / 2)
        return
      }
      
      window.learningChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
          labels: learningTrend.value.map(item => item.week),
          datasets: [
            {
              label: '学习单词数',
              data: learningTrend.value.map(item => item.wordsLearned),
              borderColor: 'rgb(75, 192, 192)',
              tension: 0.1,
              backgroundColor: 'rgba(75, 192, 192, 0.2)'
            },
            {
              label: '正确率',
              data: learningTrend.value.map(item => item.accuracy * 100),
              borderColor: 'rgb(255, 99, 132)',
              tension: 0.1,
              backgroundColor: 'rgba(255, 99, 132, 0.2)'
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              display: true
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: '学习单词数 / 正确率(%)'
              }
            }
          }
        }
      })
    }
    
    // 添加重置方法
    const resetChart = () => {
      if (window.learningChartInstance) {
        window.learningChartInstance.destroy()
      }
      
      const ctx = learningChart.value.getContext('2d')
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
      
      ctx.font = '16px Arial'
      ctx.fillStyle = '#999'
      ctx.textAlign = 'center'
      ctx.fillText('暂无学习数据', ctx.canvas.width / 2, ctx.canvas.height / 2)
    }
    
    onMounted(() => {
      fetchLearningTrend()
    })
    
    return {
      learningChart,
      formatDate,
      resetChart  // 新增重置方法
    }
  }
}
</script>

<style scoped>
.overview-panel {
  margin-bottom: 20px;
}

.stats-card, .score-card {
  margin-bottom: 20px;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-value {
  font-weight: bold;
}

.stat-value.error {
  color: #f56c6c;
}

.chart-container {
  height: 200px;
}
</style>
