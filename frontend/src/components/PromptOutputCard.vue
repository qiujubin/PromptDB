<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderAdd } from '@element-plus/icons-vue'
import CopyButton from './CopyButton.vue'
import { savePrompts } from '@/api/prompts'

const props = defineProps<{ text: string; loading?: boolean; recordZh?: string }>()

const saving = ref(false)

async function onSave() {
  if (!props.text.trim()) {
    ElMessage.warning('暂无可保存的提示词')
    return
  }
  saving.value = true
  try {
    const resp = await savePrompts({
      raw_text: props.text,
      source: 'generator',
      text_zh: props.recordZh?.trim() || undefined,
    })
    const parts: string[] = []
    if (resp.saved) parts.push(`新增 ${resp.saved} 条`)
    if (resp.incremented) parts.push(`已存在并累计 ${resp.incremented} 次`)
    if (resp.failed_translations) parts.push(`翻译失败 ${resp.failed_translations} 条`)
    if (resp.record_id) parts.push(`已记录到历史 #${resp.record_id}`)
    ElMessage.success(parts.length ? parts.join('，') : '已保存')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-card shadow="hover" class="output-card">
    <template #header>
      <div class="header">
        <span>生成的英文提示词</span>
        <div class="actions">
          <CopyButton :text="props.text" />
          <el-button
            type="success"
            :icon="FolderAdd"
            :disabled="!props.text"
            :loading="saving"
            @click="onSave"
          >
            一键保存
          </el-button>
        </div>
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
.actions {
  display: flex;
  gap: 8px;
}
</style>
