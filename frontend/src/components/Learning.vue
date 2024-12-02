<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>单词学习</span>
        <div class="header-right">
          <span>进度: {{ currentIndex + 1 }}/{{ words.length }}</span>
          <el-button type="success" size="small" @click="saveProgress" :disabled="!currentWord">
            保存进度
          </el-button>
        </div>
      </div>
    </template>
    
    <div class="learning-content" v-if="currentWord">
      <div class="word-display">
        <h2>{{ mode === 'ch2en' ? currentWord.meaning : currentWord.word }}</h2>
      </div>
      
      <el-input
        v-model="answer"
        :placeholder="mode === 'ch2en' ? '请输入英文单词' : '请输入中文释义'"
        @keyup.enter="checkAnswer"
      ></el-input>
      
      <div class="button-group">
        <el-button type="primary" @click="checkAnswer">提交</el-button>
      </div>
    </div>

    <div v-else-if="words.length > 0" class="resume-section">
      <el-button type="primary" @click="resumeProgress" v-if="hasSavedProgress">
        继续上次学习
      </el-button>
    </div>
  </el-card>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

export default {
  name: 'Learning',
  props: {
    words: {
      type: Array,
      required: true
    },
    mode: {
      type: String,
      required: true,
      validator: value => ['ch2en', 'en2ch'].includes(value)
    }
  },
  
  emits: ['finish'],
  
  setup(props, { emit }) {
    const currentIndex = ref(0)
    const answer = ref('')
    const hasSavedProgress = ref(false)
    
    // Get saved progress key based on mode
    const getSaveKey = () => `learning_progress_${props.mode}`
    
    // Check for saved progress on mount
    onMounted(() => {
      const savedProgress = localStorage.getItem(getSaveKey())
      console.log('Checking saved progress on mount:', savedProgress)
      if (savedProgress) {
        const { index, timestamp } = JSON.parse(savedProgress)
        console.log('Checking saved progress on mount:', index, timestamp)
        // Only use saved progress if it's less than 24 hours old
        if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
          hasSavedProgress.value = true
          console.log('hasSavedProgress set to true')
        } else {
          // Clear old saved progress
          localStorage.removeItem(getSaveKey())
          console.log('Old saved progress removed')
        }
      }
    })
    
    const currentWord = computed(() => {
      // Ensure we don't go out of bounds
      if (currentIndex.value >= 0 && currentIndex.value < props.words.length) {
        return props.words[currentIndex.value]
      }
      return null
    })
    
    const saveProgress = () => {
      if (currentWord.value) {
        const progress = {
          index: currentIndex.value,
          timestamp: Date.now()
        }
        console.log('Saving progress:', progress)
        localStorage.setItem(getSaveKey(), JSON.stringify(progress))
        ElMessage.success('进度已保存')
      } else {
        console.warn('No current word to save progress for.')
      }
    }
    
    const resumeProgress = () => {
      const savedProgress = localStorage.getItem(getSaveKey())
      console.log('Attempting to resume progress:', savedProgress)
      if (savedProgress) {
        const { index, timestamp } = JSON.parse(savedProgress)
        console.log('Saved index:', index, 'Timestamp:', timestamp)
        if (index >= 0 && index < props.words.length && Date.now() - timestamp < 24 * 60 * 60 * 1000) {
          currentIndex.value = index
          hasSavedProgress.value = false
          console.log('Resumed progress, hasSavedProgress set to false')
          ElMessage.success('已恢复上次学习进度')
        } else {
          console.warn('Saved progress is too old or invalid.')
          localStorage.removeItem(getSaveKey())
        }
      } else {
        console.warn('No saved progress found.')
      }
    }
    
    const checkAnswer = async () => {
      // Validate input before submission
      if (!currentWord.value) {
        ElMessage.warning('没有可学习的单词')
        return
      }

      // Trim and validate answer
      const trimmedAnswer = answer.value.trim()
      if (!trimmedAnswer) {
        ElMessage.warning('请输入答案')
        return
      }

      // Determine correctness based on learning mode
      const isCorrect = props.mode === 'ch2en'
        ? trimmedAnswer.toLowerCase() === currentWord.value.word.toLowerCase()
        : trimmedAnswer === currentWord.value.meaning

      // Prepare submission data
      const submissionData = {
        word_id: currentWord.value.id,
        is_correct: isCorrect
      }

      try {
        // Retrieve and validate token
        const token = localStorage.getItem('token')
        if (!token) {
          ElMessage.error('登录凭证已过期，请重新登录')
          return
        }

        // Submit answer
        const response = await axios.post('/api/learn', submissionData, {
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })

        // Show feedback
        if (isCorrect) {
          ElMessage.success('回答正确！')
        } else {
          ElMessage.error(`回答错误。正确答案是: ${props.mode === 'ch2en' ? currentWord.value.word : currentWord.value.meaning}`)
        }

        // Clear input and move to next word
        answer.value = ''
        currentIndex.value++

        // Check if we've finished all words
        if (currentIndex.value >= props.words.length) {
          emit('finish')
          ElMessage.success('恭喜！你已完成所有单词的学习')
          // Clear saved progress when finished
          localStorage.removeItem(getSaveKey())
        }

      } catch (error) {
        console.error('Error submitting answer:', error)
        ElMessage.error('提交答案时出错，请重试')
      }
    }

    return {
      currentIndex,
      currentWord,
      answer,
      checkAnswer,
      saveProgress,
      resumeProgress,
      hasSavedProgress
    }
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.learning-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem;
}

.word-display {
  text-align: center;
}

.button-group {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}

.resume-section {
  display: flex;
  justify-content: center;
  padding: 2rem;
}
</style>
