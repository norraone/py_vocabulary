<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>单词学习</span>
        <span>进度: {{ currentIndex + 1 }}/{{ words.length }}</span>
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
  </el-card>
</template>

<script>
import { ref, computed } from 'vue'
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
    
    const currentWord = computed(() => {
      console.log('Current Index:', currentIndex.value)
      console.log('Total Words:', props.words.length)
      console.log('Words:', props.words)
      
      // Ensure we don't go out of bounds
      if (currentIndex.value >= 0 && currentIndex.value < props.words.length) {
        return props.words[currentIndex.value]
      }
      return null
    })
    
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

        // Detailed axios configuration
        const response = await axios.post('/api/learn', submissionData, {
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000  // 10 second timeout
        })

        // Comprehensive logging
        console.group('Learning Submission')
        console.log('Submission Data:', submissionData)
        console.log('Response:', response.data)
        console.log('Current Word:', currentWord.value)
        console.log('Current Index:', currentIndex.value)
        console.log('Total Words:', props.words.length)
        console.log('Answer:', trimmedAnswer)
        console.log('Is Correct:', isCorrect)
        console.groupEnd()

        // Handle response
        if (response.data.is_correct) {
          ElMessage.success({
            message: `回答正确！+${response.data.score_change}分`,
            duration: 2000
          })
        } else {
          ElMessage.error({
            message: `回答错误！-${Math.abs(response.data.score_change)}分\n正确答案是：${
              props.mode === 'ch2en' 
                ? response.data.correct_word.word 
                : response.data.correct_word.meaning
            }`,
            duration: 3000
          })
        }

        // Reset answer and move to next word
        answer.value = ''
        
        // Safely increment index
        if (currentIndex.value < props.words.length - 1) {
          currentIndex.value++
        } else {
          ElMessage.success('本轮学习完成！')
          emit('finish')
        }
      } catch (error) {
        // Comprehensive error handling
        console.group('Submission Error')
        console.error('Full Error:', error)
        
        // Network or request setup error
        if (!error.response) {
          console.error('Network Error:', error.message)
          ElMessage.error({
            message: error.message.includes('timeout') 
              ? '请求超时，请检查网络连接' 
              : '网络错误，无法连接到服务器',
            duration: 3000
          })
          return
        }

        // Server responded with an error
        const errorResponse = error.response
        console.log('Error Response:', {
          status: errorResponse.status,
          data: errorResponse.data
        })

        // Specific error handling
        let errorMessage = '提交失败，请重试'
        switch (errorResponse.status) {
          case 400:
            errorMessage = '无效的请求参数'
            break
          case 401:
            errorMessage = '认证失败，请重新登录'
            break
          case 403:
            errorMessage = '没有权限执行此操作'
            break
          case 404:
            errorMessage = '资源未找到'
            break
          case 500:
            errorMessage = '服务器内部错误'
            break
        }

        // Display error message
        ElMessage.error({
          message: errorMessage,
          duration: 3000
        })

        console.groupEnd()
      }
    }
    
    return {
      currentIndex,
      currentWord,
      answer,
      checkAnswer
    }
  }
}
</script>

<style scoped>
.learning-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 20px;
}

.word-display {
  text-align: center;
  margin-bottom: 20px;
}

.button-group {
  margin-top: 20px;
}

.el-input {
  width: 300px;
}
</style>
