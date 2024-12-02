<template>
  <el-card class="multiple-choice-panel">
    <template #header>
      <div class="card-header">
        <span>多选题</span>
      </div>
    </template>
    <el-row :gutter="20">
      <el-col :span="24">
        <div v-loading="loading">
          <template v-if="question">
            <h3>请选择单词 "{{ question }}" 的中文含义：</h3>
            <el-radio-group v-model="selectedOption">
              <el-radio v-for="(option, index) in options" :label="option" :key="index">
                {{ option }}
              </el-radio>
            </el-radio-group>
            <div class="button-group">
              <el-button type="primary" @click="checkAnswer" :disabled="!selectedOption">提交</el-button>
              <el-button @click="fetchNewQuestion">跳过</el-button>
            </div>
            <el-alert
              v-if="feedback"
              :type="isCorrect ? 'success' : 'error'"
              :title="feedback"
              show-icon
            />
          </template>
          <template v-else>
            <el-empty description="暂无题目" />
          </template>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import useMultipleChoice from '../composables/useMultipleChoice'

const {
  question,
  options,
  selectedOption,
  feedback,
  isCorrect,
  loading,
  checkAnswer,
  fetchNewQuestion
} = useMultipleChoice()
</script>

<style scoped>
.multiple-choice-panel {
  max-width: 700px;
  margin: 3rem auto;
  padding: 2.5rem;
  background-color: #f9f9f9;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  font-size: 1.8rem;
  font-weight: bold;
  text-align: center;
  margin-bottom: 1.5rem;
}

h3 {
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
}

.el-radio {
  margin-bottom: 1rem;
  font-size: 1.2rem;
  display: block;
}

.button-group {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
}

.el-alert {
  margin-top: 1.5rem;
  font-size: 1.2rem;
}
</style>
