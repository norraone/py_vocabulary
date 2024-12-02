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
    </el-table>
  </el-card>
</template>

<script>
export default {
  name: 'WordList',
  props: {
    words: {
      type: Array,
      required: true
    }
  },
  
  setup() {
    const calculateAccuracy = (word) => {
      const total = word.correct_times + word.wrong_times
      if (total === 0) return 0
      return ((word.correct_times / total) * 100).toFixed(1)
    }

    return {
      calculateAccuracy
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
