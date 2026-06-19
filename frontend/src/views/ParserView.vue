<script setup lang="ts">
defineOptions({ name: 'ParserView' })
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderAdd, MagicStick } from '@element-plus/icons-vue'
import {
  importPrompts,
  parsePrompts,
  type ImportResponse,
  type ParseItem,
} from '@/api/prompts'

const rawText = ref<string>('')
const parsedItems = ref<ParseItem[]>([])
const parsing = ref(false)
const importing = ref(false)
const importResult = ref<ImportResponse | null>(null)

async function onParse() {
  if (!rawText.value.trim()) {
    ElMessage.warning('请先粘贴英文提示词')
    return
  }
  parsing.value = true
  importResult.value = null
  try {
    const resp = await parsePrompts({ raw_text: rawText.value })
    parsedItems.value = resp.items
    if (!resp.items.length) {
      ElMessage.warning('未解析出有效片段')
      return
    }
    const parts: string[] = []
    parts.push(`共 ${resp.split_count} 个片段`)
    if (resp.translation_failures) {
      parts.push(`翻译失败 ${resp.translation_failures} 条`)
    }
    ElMessage.success(parts.join('，'))
  } catch (e) {
    parsedItems.value = []
    ElMessage.error((e as Error).message)
  } finally {
    parsing.value = false
  }
}

async function onImport() {
  if (!parsedItems.value.length) {
    ElMessage.warning('请先解析提示词')
    return
  }
  importing.value = true
  try {
    const resp = await importPrompts({ items: parsedItems.value })
    importResult.value = resp
    const parts: string[] = []
    if (resp.saved) parts.push(`新增 ${resp.saved} 条`)
    if (resp.incremented) parts.push(`已存在并累计 ${resp.incremented} 次`)
    if (resp.tag_failures) parts.push(`标签失败 ${resp.tag_failures} 条`)
    if (parts.length) ElMessage.success(parts.join('，'))
    else ElMessage.info('没有需要保存的内容')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <el-card class="page" shadow="never">
    <template #header>
      <div class="title">解析英文提示词</div>
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
      <el-form-item>
        <el-button
          type="primary"
          :icon="MagicStick"
          :loading="parsing"
          @click="onParse"
        >
          解析
        </el-button>
      </el-form-item>
    </el-form>

    <div v-if="parsedItems.length" class="tag-cloud">
      <div
        v-for="(it, i) in parsedItems"
        :key="i"
        class="tag-chip"
        :class="{ 'no-zh': !it.text_zh }"
      >
        <span class="en">{{ it.text_en }}</span>
        <span class="zh">{{ it.text_zh || '翻译失败' }}</span>
      </div>
    </div>

    <div v-if="parsedItems.length" class="actions">
      <el-button
        type="success"
        :icon="FolderAdd"
        :loading="importing"
        @click="onImport"
      >
        保存到提示词库
      </el-button>
    </div>

    <el-alert
      v-if="importResult"
      class="result"
      :title="`本次处理：新增 ${importResult.saved} 条，累加 ${importResult.incremented} 次${importResult.tag_failures ? '，标签失败 ' + importResult.tag_failures + ' 条' : ''}`"
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
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.tag-chip {
  display: inline-flex;
  flex-direction: column;
  max-width: 240px;
  padding: 6px 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  transition: transform 0.15s ease, background 0.15s ease;
  cursor: default;
}
.tag-chip:hover {
  transform: translateY(-1px);
  background: var(--el-color-primary-light-9);
}
.en {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  word-break: break-word;
}
.zh {
  margin-top: 2px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  word-break: break-word;
}
.tag-chip.no-zh .zh {
  color: var(--el-color-danger);
  font-style: italic;
}
.actions {
  margin-top: 16px;
}
.result {
  margin-top: 16px;
}
</style>