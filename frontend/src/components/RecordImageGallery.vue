<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import {
  deleteRecordImage,
  reorderRecordImages,
  uploadRecordImages,
  type RecordImageOut,
} from '@/api/records'

const props = defineProps<{
  recordId: number
  images: RecordImageOut[]
  editable?: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const uploading = ref(false)
const reordering = ref(false)
const localOrder = ref<RecordImageOut[]>([])

const previewList = computed(() =>
  (localOrder.value.length ? localOrder.value : props.images)
    .map((i) => i.url)
    .filter((u): u is string => !!u),
)

const workingImages = computed(() =>
  localOrder.value.length ? localOrder.value : [...props.images],
)

const isDirty = computed(() => {
  if (localOrder.value.length !== props.images.length) return false
  return localOrder.value.some((img, idx) => img.id !== props.images[idx]?.id)
})

function syncLocalFromProps() {
  localOrder.value = []
}

function moveLeft(idx: number) {
  if (idx <= 0) return
  const arr = [...workingImages.value]
  ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
  localOrder.value = arr
}
function moveRight(idx: number) {
  if (idx >= workingImages.value.length - 1) return
  const arr = [...workingImages.value]
  ;[arr[idx], arr[idx + 1]] = [arr[idx + 1], arr[idx]]
  localOrder.value = arr
}

async function persistOrder() {
  if (!isDirty.value) {
    ElMessage.info('顺序未变')
    return
  }
  reordering.value = true
  try {
    const ids = localOrder.value.map((i) => i.id)
    await reorderRecordImages(props.recordId, ids)
    ElMessage.success('顺序已保存')
    emit('changed')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    reordering.value = false
  }
}

async function onUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  uploading.value = true
  try {
    await uploadRecordImages(props.recordId, Array.from(input.files))
    ElMessage.success('上传完成')
    syncLocalFromProps()
    emit('changed')
  } catch (err) {
    ElMessage.error((err as Error).message)
  } finally {
    input.value = ''
    uploading.value = false
  }
}

async function onRemove(img: RecordImageOut) {
  try {
    await ElMessageBox.confirm('删除该图片?', '提示', { type: 'warning' })
    await deleteRecordImage(props.recordId, img.id)
    ElMessage.success('已删除')
    syncLocalFromProps()
    emit('changed')
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  }
}
</script>

<template>
  <div class="gallery" v-loading="uploading || reordering">
    <div v-for="(img, idx) in workingImages" :key="img.id" class="cell">
      <el-image
        :src="img.url ?? ''"
        :preview-src-list="previewList"
        :initial-index="idx"
        fit="cover"
        class="thumb"
        loading="lazy"
      >
        <template #error>
          <div class="img-error">加载失败</div>
        </template>
      </el-image>
      <div v-if="editable" class="actions">
        <el-button
          size="small"
          link
          :disabled="idx === 0"
          @click="moveLeft(idx)"
        >
          ←
        </el-button>
        <el-button
          size="small"
          link
          type="danger"
          @click="onRemove(img)"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button
          size="small"
          link
          :disabled="idx === workingImages.length - 1"
          @click="moveRight(idx)"
        >
          →
        </el-button>
      </div>
    </div>
    <label v-if="editable" class="add">
      <el-icon><Plus /></el-icon>
      <span>上传</span>
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple
        hidden
        @change="onUpload"
      />
    </label>
    <div v-if="editable && isDirty" class="order-bar">
      <el-button size="small" type="primary" @click="persistOrder">
        保存图片顺序
      </el-button>
      <el-button size="small" @click="syncLocalFromProps">取消</el-button>
    </div>
  </div>
</template>

<style scoped>
.gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: flex-start;
  position: relative;
}
.cell {
  position: relative;
  width: 72px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.thumb {
  width: 72px;
  height: 72px;
  border-radius: 4px;
  object-fit: cover;
  background: var(--el-fill-color-light);
}
.img-error {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}
.actions {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.actions :deep(.el-button) {
  padding: 0 2px;
}
.add {
  width: 72px;
  height: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-blank);
  border: 1px dashed var(--el-border-color);
  border-radius: 4px;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.add:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.add :deep(.el-icon) {
  font-size: 18px;
}
.order-bar {
  flex-basis: 100%;
  display: flex;
  gap: 6px;
  margin-top: 4px;
}
</style>
