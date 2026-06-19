<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import RecordImageGallery from './RecordImageGallery.vue'
import { updateRecord, type RecordOut } from '@/api/records'

const props = defineProps<{
  modelValue: boolean
  record: RecordOut | null
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  saved: []
}>()

const saving = ref(false)

const form = ref({
  name: '',
  text_zh: '',
  text_en: '',
  rating: 0,
  comment: '',
  is_favorite: false,
})

watch(
  () => props.record,
  (r) => {
    if (r) {
      form.value = {
        name: r.name ?? '',
        text_zh: r.text_zh ?? '',
        text_en: r.text_en ?? '',
        rating: r.rating,
        comment: r.comment ?? '',
        is_favorite: r.is_favorite,
      }
    }
  },
  { immediate: true },
)

function close() {
  emit('update:modelValue', false)
}

async function onSave() {
  if (!props.record) return
  saving.value = true
  try {
    await updateRecord(props.record.id, {
      name: form.value.name.trim() || null,
      text_zh: form.value.text_zh.trim() || null,
      text_en: form.value.text_en.trim() || null,
      rating: form.value.rating,
      comment: form.value.comment.trim() || null,
      is_favorite: form.value.is_favorite,
    })
    ElMessage.success('已保存')
    emit('saved')
    close()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="record ? `编辑历史记录 #${record.id}` : '编辑'"
    width="720px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="record" class="dlg-body">
      <el-form label-position="top">
        <el-form-item label="名称 (≤255 字)">
          <el-input
            v-model="form.name"
            maxlength="255"
            show-word-limit
            placeholder="给这张卡片起个名字（留空则显示默认）"
          />
        </el-form-item>
        <el-form-item label="中文原文">
          <el-input
            v-model="form.text_zh"
            type="textarea"
            :rows="3"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="英文提示词">
          <el-input
            v-model="form.text_en"
            type="textarea"
            :rows="4"
            maxlength="20000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="评分 (0-5, 整数)">
          <el-rate
            v-model="form.rating"
            :max="5"
            :allow-half="false"
            show-score
          />
        </el-form-item>
        <el-form-item label="评价 (≤1000 字)">
          <el-input
            v-model="form.comment"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="收藏/置顶">
          <el-switch
            v-model="form.is_favorite"
            active-text="收藏"
            inactive-text="普通"
          />
        </el-form-item>

        <el-divider>图片</el-divider>
        <RecordImageGallery
          :record-id="record.id"
          :images="record.images"
          editable
          @changed="emit('saved')"
        />
      </el-form>
    </div>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dlg-body { padding-right: 4px; }
</style>
