<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import PromptOutputCard from '@/components/PromptOutputCard.vue'
import { generatePrompt } from '@/api/generate'

const PRESET_SYSTEM_PROMPT =
  '你是一个 AI 绘图提示词助手。用户会给你一段中文描述，请把它改写成可以直接用于 Midjourney / Stable Diffusion / DALL·E 的英文提示词。要求：\n' +
  '1) 输出为一行连续的英文关键词短语，关键词之间用英文逗号加一个空格分隔；\n' +
  '2) 风格、质量、镜头、光照、构图等通用关键词放在最前；\n' +
  '3) 主题、动作、场景、细节放在其后；\n' +
  '4) 必要时补充负面提示词（用 --no xxx 的形式追加在末尾）；\n' +
  '5) 不要解释、不要换行、不要加引号，只返回英文提示词本身。'

const systemPrompt = ref<string>(PRESET_SYSTEM_PROMPT)
const userInput = ref<string>('')
const output = ref<string>('')
const loading = ref(false)

async function onGenerate() {
  if (!userInput.value.trim()) {
    ElMessage.warning('请先输入画面描述')
    return
  }
  loading.value = true
  output.value = ''
  try {
    const resp = await generatePrompt({
      system_prompt: systemPrompt.value,
      user_input: userInput.value,
    })
    output.value = resp.text
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
      <div class="title">生成英文提示词</div>
    </template>

    <el-form label-position="top">
      <el-form-item label="系统提示词（可修改）">
        <el-input
          v-model="systemPrompt"
          type="textarea"
          :rows="6"
          resize="vertical"
        />
      </el-form-item>

      <el-form-item label="画面描述（中文）">
        <el-input
          v-model="userInput"
          type="textarea"
          :rows="4"
          resize="vertical"
          placeholder="例如：一只戴帽子的猫坐在窗台上看着夕阳"
        />
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          :icon="MagicStick"
          :loading="loading"
          @click="onGenerate"
        >
          生成提示词
        </el-button>
      </el-form-item>
    </el-form>

    <PromptOutputCard :text="output" :loading="loading" />
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
</style>