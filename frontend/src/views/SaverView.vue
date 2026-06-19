<script setup lang="ts">
defineOptions({ name: 'SaverView' })
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderAdd } from '@element-plus/icons-vue'
import { savePrompts, type SaveResponse } from '@/api/prompts'

const rawText = ref<string>('')
const textZh = ref<string>('')
const result = ref<SaveResponse | null>(null)
const loading = ref(false)

async function onSave() {
  if (!rawText.value.trim()) {
    ElMessage.warning('请先粘贴英文提示词')
    return
  }
  loading.value = true
  result.value = null
  try {
    const resp = await savePrompts({
      raw_text: rawText.value,
      source: 'manual',
      text_zh: textZh.value.trim() || undefined,
    })
    result.value = resp
    const parts: string[] = []
    if (resp.saved) parts.push(`新增 ${resp.saved} 条`)
    if (resp.incremented) parts.push(`已存在并累计 ${resp.incremented} 次`)
    if (resp.failed_translations) parts.push(`翻译失败 ${resp.failed_translations} 条`)
    if (resp.record_id) parts.push(`已记录到历史 #${resp.record_id}`)
    if (parts.length) ElMessage.success(parts.join('，'))
    rawText.value = ''
    textZh.value = ''
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-card class="page" shadow="never">
    <template #header>
      <div class="title">保存英文提示词</div>
    </template>

    <el-form label-position="top">
      <el-form-item label="英文提示词（用英文逗号 , 分隔片段）">
        <el-input
          v-model="rawText"
          type="textarea"
          :rows="8"
          resize="vertical"
          placeholder="masterpiece, best quality, 1girl, red dress, sunset, soft lighting"
        />
      </el-form-item>
      <el-form-item label="中文描述（可选，填写后会在历史记录里建立一条带原文的归档）">
        <el-input
          v-model="textZh"
          type="textarea"
          :rows="3"
          resize="vertical"
          placeholder="例如：一位穿红裙的女孩在夕阳下"
          maxlength="2000"
          show-word-limit
        />
      </el-form-item>
      <el-form-item>
        <el-button
          type="success"
          :icon="FolderAdd"
          :loading="loading"
          @click="onSave"
        >
          保存到提示词库
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="result"
      class="result"
      :title="`本次处理：新增 ${result.saved} 条，累加 ${result.incremented} 条${result.failed_translations ? '，翻译失败 ' + result.failed_translations + ' 条' : ''}${result.record_id ? '，已建历史记录 #' + result.record_id : ''}`"
      type="success"
      show-icon
      :closable="false"
    />
  </el-card>
</template>

<style scoped>
.page {
  max-width: 960px;
  margin: 0 auto;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.result {
  margin-top: 16px;
}
</style>
