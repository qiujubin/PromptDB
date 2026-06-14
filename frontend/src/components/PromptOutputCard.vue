<script setup lang="ts">
import CopyButton from './CopyButton.vue'

const props = defineProps<{ text: string; loading?: boolean }>()
</script>

<template>
  <el-card shadow="hover" class="output-card">
    <template #header>
      <div class="header">
        <span>生成的英文提示词</span>
        <CopyButton :text="props.text" />
      </div>
    </template>
    <el-skeleton v-if="props.loading" :rows="4" animated />
    <el-input
      v-else
      :model-value="props.text"
      type="textarea"
      :rows="6"
      readonly
      resize="none"
      placeholder="生成结果会显示在这里..."
    />
  </el-card>
</template>

<style scoped>
.output-card {
  margin-top: 16px;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>