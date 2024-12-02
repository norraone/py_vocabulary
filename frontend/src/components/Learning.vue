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
      return currentIndex.value < props.words.length ? props.words[currentIndex.value] : null
    })
    
    const checkAnswer = async () => {
      if (!currentWord.value) return
      
      const isCorrect = props.mode === 'ch2en'
        ? answer.value.toLowerCase() === currentWord.value.word.toLowerCase()
        : answer.value === currentWord.value.meaning
      
      try {
        const token = localStorage.getItem('token')
        await axios.post('/api/learning', {
          word_id: currentWord.value.id,
          is_correct: isCorrect
        }, {
          headers: { Authorization: `Bearer ${token}` }
        })
        
        if (isCorrect) {
          alert('回答正确！+10分')
        } else {
          alert(`回答错误！-10分\n正确答案是：${props.mode === 'ch2en' ? currentWord.value.word : currentWord.value.meaning}`)
        }
        
        answer.value = ''
        currentIndex.value++
        
        if (currentIndex.value >= props.words.length) {
          alert('本轮学习完成！')
          emit('finish')
        }
      } catch (error) {
        console.error('Error submitting answer:', error)
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
