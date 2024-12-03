<template>
  <div class="review-container">
    <div class="review-header">
      <h2>复习单词</h2>
      <div class="review-stats">
        <span>总复习次数: {{ totalReviewCount }}</span>
        <span>今日复习: {{ todayReviewCount }}</span>
      </div>
    </div>

    <div v-if="currentWord" class="review-word-card">
      <div class="word-details">
        <h3>{{ currentWord.word }}</h3>
        <p class="pronunciation">{{ currentWord.pronunciation }}</p>
        <p class="translation">{{ currentWord.translation }}</p>
        <p class="meaning" v-if="currentWord.meaning">{{ currentWord.meaning }}</p>
        <el-button @click="showEditDialog" size="small" type="primary">补充释义</el-button>
      </div>

      <div class="review-actions">
        <!-- 暂时注释掉复习功能
        <div class="quality-buttons">
          <el-button 
            v-for="(label, quality) in qualityLabels" 
            :key="quality"
            @click="submitReview(quality)"
            :type="getButtonType(quality)"
          >
            {{ label }}
          </el-button>
        </div>
        -->
        <div class="schedule-review">
          <el-button @click="showScheduleDialog">稍后复习</el-button>
        </div>
      </div>
    </div>
    <div v-else class="no-words-to-review">
      <p>暂无需要复习的单词</p>
    </div>

    <el-dialog
      v-model="scheduleDialogVisible"
      title="选择复习时间"
      width="30%"
    >
      <div class="schedule-options">
        <el-button
          v-for="days in [1, 3, 7]"
          :key="days"
          @click="scheduleReview(days)"
        >
          {{ days }}天后
        </el-button>
      </div>
    </el-dialog>

    <el-dialog
      v-model="editDialogVisible"
      title="补充释义"
      width="50%"
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="释义">
          <el-input
            v-model="editForm.meaning"
            type="textarea"
            :rows="4"
            placeholder="请输入补充释义"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit">确认</el-button>
        </span>
      </template>
    </el-dialog>

    <el-button @click="resetProgress" type="danger" style="position: absolute; top: 20px; right: 20px;">重置进度</el-button>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'

export default {
  name: 'Review',
  setup() {
    const currentWord = ref(null)
    const totalReviewCount = ref(0)
    const todayReviewCount = ref(0)
    const scheduleDialogVisible = ref(false)
    const editDialogVisible = ref(false)
    const editForm = ref({
      meaning: ''
    })
    const checkinStatus = ref({
      todayStatus: null,
      stats: null
    })

    // 暂时注释掉复习功能相关的代码
    /*
    const qualityLabels = {
      0: '完全不会',
      1: '想起很少',
      2: '想起一些',
      3: '有点困难',
      4: '记得清楚',
      5: '非常熟悉'
    }

    const getButtonType = (quality) => {
      switch (quality) {
        case 0: return 'danger'
        case 1: return 'warning'
        case 2: return 'info'
        case 3: return 'primary'
        case 4: return 'success'
        case 5: return 'success'
        default: return 'default'
      }
    }

    const submitReview = async (quality) => {
      try {
        const token = localStorage.getItem('token')
        await axios.post('/api/review-words', {
          word_id: currentWord.value.id,
          quality: parseInt(quality, 10)  // 确保 quality 是整数
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })

        ElMessage.success(`复习完成，质量评分: ${qualityLabels[quality]}`)
        await fetchReviewWord()
      } catch (error) {
        console.error('提交复习结果失败:', error)
        ElMessage.error(error.response?.data?.message || '提交复习结果失败')
      }
    }
    */

    const fetchReviewWord = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await axios.get('/api/review-words', {
          headers: { Authorization: `Bearer ${token}` }
        })

        if (response.data && response.data.words && response.data.words.length > 0) {
          currentWord.value = response.data.words[0]
        } else {
          currentWord.value = null
        }
      } catch (error) {
        console.error('获取复习单词失败:', error)
        ElMessage.error('获取复习单词失败')
      }
    }

    const fetchCheckinStatus = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          console.error('No token found')
          return
        }

        console.log('Fetching checkin status...')
        const response = await axios.get('/api/checkin', {
          headers: { Authorization: `Bearer ${token}` }
        })

        console.log('Checkin status response:', response.data)
        
        // 处理可能的空数据情况
        const { today_status, stats } = response.data
        
        checkinStatus.value = {
          todayStatus: today_status || {
            checkin_type: 'not_checked_in',
            words_learned: 0,
            correct_count: 0,
            wrong_count: 0,
            streak_days: 0,
            created_at: null,
            checkin_date: new Date().toISOString().split('T')[0]
          },
          stats: stats || {
            total_days: 0,
            max_streak: 0,
            current_streak: 0,
            last_checkin: null
          }
        }

        console.log('Processed checkin status:', checkinStatus.value)
      } catch (error) {
        console.error('获取打卡状态失败:', error)
        
        // 详细记录错误信息
        if (error.response) {
          console.error('Error response:', error.response.data)
          console.error('Error status:', error.response.status)
          console.error('Error headers:', error.response.headers)
        } else if (error.request) {
          console.error('Error request:', error.request)
        } else {
          console.error('Error message:', error.message)
        }

        // 设置默认值
        checkinStatus.value = {
          todayStatus: {
            checkin_type: 'not_checked_in',
            words_learned: 0,
            correct_count: 0,
            wrong_count: 0,
            streak_days: 0,
            created_at: null,
            checkin_date: new Date().toISOString().split('T')[0]
          },
          stats: {
            total_days: 0,
            max_streak: 0,
            current_streak: 0,
            last_checkin: null
          }
        }

        ElMessage.error('获取打卡状态失败：' + (error.response?.data?.message || error.message))
      }
    }

    const showScheduleDialog = () => {
      scheduleDialogVisible.value = true
    }

    const scheduleReview = async (days) => {
      try {
        const token = localStorage.getItem('token')
        await axios.post('/api/schedule-review', {
          word_id: currentWord.value.id,
          days: days
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })

        ElMessage.success(`已安排${days}天后复习`)
        scheduleDialogVisible.value = false
        await fetchReviewWord()
      } catch (error) {
        console.error('安排复习失败:', error)
        ElMessage.error(error.response?.data?.message || '安排复习失败')
      }
    }

    const showEditDialog = () => {
      editForm.value.meaning = currentWord.value.meaning || ''
      editDialogVisible.value = true
    }

    const submitEdit = async () => {
      try {
        const token = localStorage.getItem('token')
        await axios.put(`/api/words/${currentWord.value.id}`, {
          meaning: editForm.value.meaning
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })

        // 更新当前显示的释义
        currentWord.value.meaning = editForm.value.meaning
        ElMessage.success('释义更新成功')
        editDialogVisible.value = false
      } catch (error) {
        console.error('更新释义失败:', error)
        ElMessage.error(error.response?.data?.message || '更新释义失败')
      }
    }

    const resetProgress = async () => {
      try {
        // 显示确认对话框
        const confirmReset = await ElMessageBox.confirm(
          '你确定要重置所有学习进度吗？这将删除所有学习记录、复习记录和打卡记录。此操作不可撤销。', 
          '重置进度确认', 
          {
            confirmButtonText: '确定重置',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        // 如果用户确认
        if (confirmReset) {
          // 显示加载中状态
          const loadingInstance = ElLoading.service({
            lock: true,
            text: '正在重置进度...',
            background: 'rgba(0, 0, 0, 0.7)'
          })

          try {
            const token = localStorage.getItem('token')
            if (!token) {
              throw new Error('未找到用户认证信息')
            }

            // 发送重置请求
            const response = await axios.post('/api/reset-progress', {}, {
              headers: { Authorization: `Bearer ${token}` }
            })

            // 关闭加载状态
            loadingInstance.close()

            // 重置本地状态
            checkinStatus.value = {
              todayStatus: {
                checkin_type: 'not_checked_in',
                words_learned: 0,
                correct_count: 0,
                wrong_count: 0,
                streak_days: 0,
                created_at: null,
                checkin_date: new Date().toISOString().split('T')[0]
              },
              stats: {
                total_days: 0,
                max_streak: 0,
                current_streak: 0,
                last_checkin: null
              }
            }

            // 显示成功消息
            ElMessage.success({
              message: '成功重置所有学习进度',
              duration: 3000
            })

            // 重新获取复习单词
            await fetchReviewWord()
          } catch (error) {
            // 关闭加载状态
            loadingInstance.close()

            // 详细的错误处理
            console.error('重置进度失败:', error)
            
            // 显示错误消息
            ElMessage.error({
              message: error.response?.data?.message || '重置进度失败，请稍后重试',
              duration: 3000
            })
          }
        }
      } catch (error) {
        // 处理取消操作
        if (error === 'cancel') {
          ElMessage.info('已取消重置')
        }
      }
    }

    onMounted(async () => {
      await fetchReviewWord()
      await fetchCheckinStatus()
    })

    return {
      currentWord,
      totalReviewCount,
      todayReviewCount,
      // qualityLabels,  // 注释掉
      // submitReview,   // 注释掉
      // getButtonType,  // 注释掉
      scheduleDialogVisible,
      showScheduleDialog,
      scheduleReview,
      editDialogVisible,
      editForm,
      showEditDialog,
      submitEdit,
      checkinStatus,
      resetProgress
    }
  }
}
</script>

<style scoped>
.review-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  text-align: center;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.review-word-card {
  background-color: #f5f5f5;
  border-radius: 10px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.word-details {
  text-align: center;
  margin-bottom: 20px;
}

.word-details h3 {
  font-size: 24px;
  margin-bottom: 10px;
}

.word-details p {
  margin: 8px 0;
}

.word-details .el-button {
  margin-top: 10px;
}

.review-actions {
  margin-top: 20px;
}

.quality-buttons {
  display: flex;
  justify-content: space-around;
}

.schedule-review {
  margin-top: 10px;
}

.no-words-to-review {
  text-align: center;
  color: #888;
  font-size: 1.2em;
}
</style>
