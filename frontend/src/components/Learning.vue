<template>
  <div class="learning-container">
    <el-card class="word-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>{{ mode === 'review' ? '错题复习' : '单词背诵' }}</span>
          <div class="header-right">
            <el-tag type="info" size="small">
              已学: {{ currentIndex + 1 }}/{{ words.length }}
            </el-tag>
          </div>
        </div>
      </template>

      <template v-if="currentWord">
        <div class="word-content" :class="{ 'show-meaning': showMeaning }">
          <div class="word-front">
            <h2>{{ currentWord.word }}</h2>
            <p class="part-of-speech">{{ currentWord.part_of_speech }}</p>
          </div>
          <div class="word-back">
            <h3>{{ currentWord.meaning }}</h3>
          </div>
        </div>

        <div class="button-group">
          <el-button 
            type="primary" 
            @click="toggleMeaning" 
            :icon="showMeaning ? 'Hide' : 'View'"
          >
            {{ showMeaning ? '隐藏释义' : '查看释义' }}
          </el-button>
          
          <template v-if="showMeaning">
            <el-button 
              type="success" 
              @click="markAsKnown"
              :disabled="isSubmitting"
            >
              认识
            </el-button>
            <el-button 
              type="danger" 
              @click="markAsUnknown"
              :disabled="isSubmitting"
            >
              不认识
            </el-button>
          </template>
        </div>

        <div class="stats-info" v-if="currentWord">
          <el-tag type="success" size="small">正确: {{ currentWord.correct_times }}</el-tag>
          <el-tag type="danger" size="small">错误: {{ currentWord.wrong_times }}</el-tag>
        </div>
      </template>

      <template v-else>
        <el-empty :description="mode === 'review' ? '错词已全部复习完成' : '本组单词已学习完成'">
          <el-button type="primary" @click="loadWords">
            {{ mode === 'review' ? '重新复习' : '加载新单词' }}
          </el-button>
        </el-empty>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const props = defineProps({
  words: {
    type: Array,
    default: () => []
  },
  mode: {
    type: String,
    default: 'normal'
  }
})

const emit = defineEmits(['finish'])

const loading = ref(false)
const isSubmitting = ref(false)
const localWords = ref([])
const currentIndex = ref(0)
const showMeaning = ref(false)

const currentWord = computed(() => {
  return currentIndex.value < localWords.value.length ? localWords.value[currentIndex.value] : null
})

const loadWords = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('token')
    
    if (props.mode === 'review') {
      // 错题复习模式
      const response = await axios.get('/api/wrong-words', {
        headers: { Authorization: `Bearer ${token}` }
      })
      localWords.value = response.data
    } else {
      // 普通学习模式
      const response = await axios.get('/api/random-word', {
        headers: { Authorization: `Bearer ${token}` }
      })
      localWords.value = response.data
    }
    
    currentIndex.value = 0
    showMeaning.value = false
  } catch (error) {
    console.error('加载单词失败:', error)
    ElMessage.error(error.response?.data?.message || '加载单词失败')
  } finally {
    loading.value = false
  }
}

// 如果传入了words，直接使用
if (props.words.length > 0) {
  localWords.value = props.words
}

const toggleMeaning = () => {
  showMeaning.value = !showMeaning.value
}

const submitAnswer = async (isCorrect) => {
  if (!currentWord.value || isSubmitting.value) return

  try {
    isSubmitting.value = true
    const token = localStorage.getItem('token')
    await axios.post('/api/learn', {
      word_id: currentWord.value.id,
      is_correct: isCorrect
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })

    // 更新本地统计数据
    if (isCorrect) {
      currentWord.value.correct_times++
    } else {
      currentWord.value.wrong_times++
    }

    // 延迟后进入下一个单词
    setTimeout(() => {
      currentIndex.value++
      showMeaning.value = false
      
      // 如果已经学完所有单词
      if (currentIndex.value >= localWords.value.length) {
        const message = props.mode === 'review' 
          ? '错词复习完成！' 
          : '本组单词学习完成！'
        ElMessage.success(message)
        emit('finish')
      }
    }, 500)

  } catch (error) {
    console.error('提交答案失败:', error)
    ElMessage.error(error.response?.data?.message || '提交答案失败')
  } finally {
    isSubmitting.value = false
  }
}

const markAsKnown = () => submitAnswer(true)
const markAsUnknown = () => submitAnswer(false)

// 初始加载单词
if (localWords.value.length === 0) {
  loadWords()
}
</script>

<style scoped>
.learning-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 0 1rem;
}

.word-card {
  background-color: #f9f9f9;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1.5rem;
  font-weight: bold;
}

.header-right {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.word-content {
  text-align: center;
  padding: 2rem;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.word-front h2 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.part-of-speech {
  font-size: 1.2rem;
  color: #666;
  margin-bottom: 1rem;
}

.word-back {
  opacity: 0;
  transform: translateY(20px);
  transition: all 0.3s ease;
}

.show-meaning .word-back {
  opacity: 1;
  transform: translateY(0);
}

.word-back h3 {
  font-size: 1.8rem;
  color: #42b983;
  margin-top: 1rem;
}

.button-group {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin: 1.5rem 0;
}

.stats-info {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}

.el-empty {
  padding: 2rem;
}
</style>
