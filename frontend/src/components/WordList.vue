<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>单词列表</span>
      </div>
    </template>
    
    <el-table :data="words" style="width: 100%">
      <el-table-column prop="word" label="单词" />
      <el-table-column prop="part_of_speech" label="词性" />
      <el-table-column prop="meaning" label="释义" />
      <el-table-column prop="correct_times" label="正确次数" />
      <el-table-column prop="wrong_times" label="错误次数" />
      <el-table-column label="正确率">
        <template #default="scope">
          {{ calculateAccuracy(scope.row) }}%
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-button type="primary" size="small" @click="editWord(scope.row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="编辑单词">
      <el-form :model="editForm">
        <el-form-item label="单词">
          <el-input v-model="editForm.word" />
        </el-form-item>
        <el-form-item label="词性">
          <el-input v-model="editForm.part_of_speech" />
        </el-form-item>
        <el-form-item label="释义">
          <el-input v-model="editForm.meaning" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveWord">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </el-card>
</template>

<script>
import { ref } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'WordList',
  props: {
    words: {
      type: Array,
      required: true
    }
  },
  emits: ['word-updated'],
  
  setup(props, { emit }) {
    const dialogVisible = ref(false)
    const editForm = ref({})

    const calculateAccuracy = (word) => {
      const total = word.correct_times + word.wrong_times
      if (total === 0) return 0
      return ((word.correct_times / total) * 100).toFixed(1)
    }

    const editWord = (word) => {
      editForm.value = { ...word }
      dialogVisible.value = true
    }

    const saveWord = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          ElMessage.error('登录凭证已过期，请重新登录')
          return
        }

        console.log('Updating word with data:', {
          id: editForm.value.id,
          word: editForm.value.word,
          part_of_speech: editForm.value.part_of_speech,
          meaning: editForm.value.meaning
        })

        // Explicitly create a new object to avoid potential serialization issues
        const updateData = {
          word: editForm.value.word || undefined,
          part_of_speech: editForm.value.part_of_speech || undefined,
          meaning: editForm.value.meaning || undefined
        }

        // Remove undefined keys
        Object.keys(updateData).forEach(key => 
          updateData[key] === undefined && delete updateData[key]
        )

        const response = await axios.put(`/api/words/${editForm.value.id}`, updateData, {
          headers: { 
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          transformResponse: [function (data) {
            // Custom response transformer to handle potential serialization issues
            try {
              return JSON.parse(data)
            } catch (e) {
              console.error('Response parsing error:', e)
              return data
            }
          }]
        })
        
        // Safely access response data
        const responseData = response.data || response

        ElMessage.success(responseData.message || '单词更新成功')
        dialogVisible.value = false
        // Optionally emit an event to parent component to refresh word list
        emit('word-updated', editForm.value)
      } catch (error) {
        console.error('Failed to update word:', error)
        
        // Safely extract error message
        const errorMessage = 
          error.response?.data?.error_details || 
          error.response?.data?.message || 
          error.message || 
          '未知错误'
        
        ElMessage.error(`更新单词失败：${errorMessage}`)
        
        // Log full error details for debugging
        console.error('Full error response:', error.response)
        console.error('Full error:', error)
      }
    }

    return {
      calculateAccuracy,
      dialogVisible,
      editForm,
      editWord,
      saveWord
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
</style>
