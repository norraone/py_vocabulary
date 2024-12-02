import { ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

export default function useMultipleChoice() {
  const question = ref('')
  const options = ref([])
  const correctAnswer = ref('')
  const selectedOption = ref('')
  const feedback = ref('')
  const isCorrect = ref(false)
  const loading = ref(false)
  const currentWordId = ref(null)

  const fetchNewQuestion = async () => {
    try {
      loading.value = true
      const token = localStorage.getItem('token')
      const response = await axios.get('/api/multiple-choice', {
        headers: { Authorization: `Bearer ${token}` }
      })

      currentWordId.value = response.data.id
      question.value = response.data.question
      options.value = response.data.options
      correctAnswer.value = response.data.correct_answer
      selectedOption.value = ''
      feedback.value = ''
      isCorrect.value = false
    } catch (error) {
      console.error('获取题目失败:', error)
      ElMessage.error(error.response?.data?.message || '获取题目失败')
    } finally {
      loading.value = false
    }
  }

  const checkAnswer = async () => {
    if (!selectedOption.value) {
      ElMessage.warning('请选择一个选项')
      return
    }

    if (!currentWordId.value) {
      ElMessage.error('题目ID缺失，请重新加载题目')
      return
    }

    isCorrect.value = selectedOption.value === correctAnswer.value
    
    try {
      // 提交学习记录
      const token = localStorage.getItem('token')
      await axios.post('/api/learn', {
        word_id: currentWordId.value,
        is_correct: isCorrect.value
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })

      feedback.value = isCorrect.value ? '回答正确！' : `回答错误。正确答案是: ${correctAnswer.value}`
      
      // 短暂延迟后加载新题目
      setTimeout(() => {
        fetchNewQuestion()
      }, 1500)
    } catch (error) {
      console.error('提交答案失败:', error)
      ElMessage.error(error.response?.data?.message || '提交答案失败')
    }
  }

  // 初始加载一道题目
  fetchNewQuestion()

  return {
    question,
    options,
    selectedOption,
    feedback,
    isCorrect,
    loading,
    checkAnswer,
    fetchNewQuestion
  }
}
