<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{ text: string; disabled?: boolean; compact?: boolean }>(),
  { disabled: false, compact: false },
)

async function copy() {
  if (!props.text) return
  try {
    await navigator.clipboard.writeText(props.text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}
</script>

<template>
  <el-button
    v-if="compact"
    type="primary"
    size="small"
    :icon="DocumentCopy"
    :disabled="disabled || !text"
    class="copy-btn-compact"
    @click="copy"
  >
    复制
  </el-button>
  <el-button
    v-else
    type="primary"
    :icon="DocumentCopy"
    :disabled="disabled || !text"
    @click="copy"
  >
    一键复制
  </el-button>
</template>

<style scoped>
.copy-btn-compact {
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(64, 158, 255, 0.3);
}
.copy-btn-compact:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(64, 158, 255, 0.45);
}
</style>