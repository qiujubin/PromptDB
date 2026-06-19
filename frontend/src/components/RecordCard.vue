<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Star,
  StarFilled,
  EditPen,
  Delete,
  Promotion,
  Check,
  Close,
} from '@element-plus/icons-vue'
import CopyButton from './CopyButton.vue'
import TagChips from './TagChips.vue'
import {
  deleteRecord,
  updateRecord,
  type RecordOut,
} from '@/api/records'

const props = defineProps<{ record: RecordOut }>()
const emit = defineEmits<{
  changed: []
  edit: [record: RecordOut]
}>()

const router = useRouter()

const collectedTags = computed(() => {
  const seen = new Map<number, { id: number; name: string; parent_id: number | null }>()
  for (const p of props.record.prompts) {
    for (const t of p.tags) {
      if (!seen.has(t.id)) seen.set(t.id, t)
    }
  }
  return Array.from(seen.values())
})

const promptCount = computed(() => props.record.prompts.length)

function formatTime(s: string) {
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}

function preview(text: string | null | undefined, max = 100) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '…' : text
}

const bgImages = computed(() =>
  props.record.images.map((i) => i.url).filter((u): u is string => !!u),
)

const ROTATE_MS = 4500
const activeIdx = ref(0)
const hovered = ref(false)
let timer: number | null = null

function nextSlide() {
  if (bgImages.value.length <= 1) return
  activeIdx.value = (activeIdx.value + 1) % bgImages.value.length
}
function startTimer() {
  stopTimer()
  if (bgImages.value.length <= 1) return
  timer = window.setInterval(() => {
    if (hovered.value) return
    nextSlide()
  }, ROTATE_MS)
}
function stopTimer() {
  if (timer !== null) {
    clearInterval(timer)
    timer = null
  }
}
watch(bgImages, () => {
  activeIdx.value = 0
  startTimer()
})
onMounted(startTimer)
onBeforeUnmount(stopTimer)

const renaming = ref(false)
const nameDraft = ref('')
const nameInput = ref<HTMLInputElement | null>(null)
const savingName = ref(false)

async function startRename() {
  nameDraft.value = props.record.name ?? ''
  renaming.value = true
  await nextTick()
  nameInput.value?.focus()
  nameInput.value?.select()
}

function cancelRename() {
  renaming.value = false
  nameDraft.value = ''
}

async function commitRename() {
  const next = nameDraft.value.trim()
  if (next === (props.record.name ?? '')) {
    renaming.value = false
    return
  }
  savingName.value = true
  try {
    await updateRecord(props.record.id, { name: next || null })
    ElMessage.success('已重命名')
    renaming.value = false
    emit('changed')
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    savingName.value = false
  }
}

function onRenameKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commitRename()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    cancelRename()
  }
}

async function toggleFavorite() {
  try {
    await updateRecord(props.record.id, { is_favorite: !props.record.is_favorite })
    ElMessage.success(props.record.is_favorite ? '已取消收藏' : '已收藏')
    emit('changed')
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onDelete() {
  try {
    await ElMessageBox.confirm('确认删除该历史记录？图片和关联会被一并清除。', '删除', {
      type: 'warning',
    })
    await deleteRecord(props.record.id)
    ElMessage.success('已删除')
    emit('changed')
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  }
}

function onRebake() {
  if (!props.record.text_zh) {
    ElMessage.warning('该记录没有中文原文，无法回炉')
    return
  }
  router.push({ path: '/generate', query: { prefill: props.record.text_zh } })
}

function onEdit() {
  emit('edit', props.record)
}
</script>

<template>
  <el-card
    class="record-card"
    :class="{ 'is-fav': record.is_favorite, 'has-bg': bgImages.length }"
    shadow="hover"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <div class="bg-layer" aria-hidden="true">
      <template v-if="bgImages.length">
        <div
          v-for="(src, i) in bgImages"
          :key="src"
          class="bg-slide"
          :class="{ active: i === activeIdx }"
          :style="{ backgroundImage: `url(${src})` }"
        />
      </template>
      <div v-else class="bg-fallback" />
      <div class="bg-scrim" />
    </div>

    <div class="content">
      <div class="head glass">
        <div class="head-left">
          <el-tooltip :content="record.is_favorite ? '取消收藏' : '收藏'">
            <el-button
              link
              :icon="record.is_favorite ? StarFilled : Star"
              :type="record.is_favorite ? 'warning' : 'default'"
              class="fav-btn"
              @click="toggleFavorite"
            />
          </el-tooltip>
          <span class="rid">#{{ record.id }}</span>
          <el-rate
            :model-value="record.rating"
            disabled
            :max="5"
            show-score
            text-color="#ff9900"
          />
          <el-tag v-if="record.is_favorite" type="warning" size="small" effect="dark" round>
            置顶
          </el-tag>
          <el-tag type="info" size="small" effect="plain">
            关联 {{ promptCount }} 段
          </el-tag>
        </div>
        <div class="head-right">
          <el-tooltip content="回炉(跳到生成页)">
            <el-button :icon="Promotion" size="small" link type="primary" @click="onRebake" />
          </el-tooltip>
          <el-tooltip content="编辑">
            <el-button :icon="EditPen" size="small" link type="primary" @click="onEdit" />
          </el-tooltip>
          <el-tooltip content="删除">
            <el-button :icon="Delete" size="small" link type="danger" @click="onDelete" />
          </el-tooltip>
        </div>
      </div>

      <div class="name-row glass">
        <template v-if="!renaming">
          <div
            class="name"
            :class="{ placeholder: !record.name }"
            title="点击重命名"
            @click="startRename"
          >
            {{ record.name || '点击给这张卡片起个名字…' }}
          </div>
        </template>
        <template v-else>
          <input
            ref="nameInput"
            v-model="nameDraft"
            class="name-input"
            maxlength="255"
            placeholder="给这张卡片起个名字…"
            :disabled="savingName"
            @keydown="onRenameKeydown"
            @blur="commitRename"
          />
          <el-button
            :icon="Check"
            size="small"
            type="primary"
            :loading="savingName"
            @mousedown.prevent="commitRename"
          />
          <el-button
            :icon="Close"
            size="small"
            @mousedown.prevent="cancelRename"
          />
        </template>
      </div>

      <div class="lang-block glass">
        <div class="lang-header">
          <span class="lang">中文</span>
          <CopyButton v-if="record.text_zh" compact :text="record.text_zh" />
        </div>
        <div class="text">{{ preview(record.text_zh, 220) || '(无)' }}</div>
      </div>

      <div class="lang-block glass">
        <div class="lang-header">
          <span class="lang">English</span>
          <CopyButton v-if="record.text_en" compact :text="record.text_en" />
        </div>
        <el-tooltip :content="record.text_en ?? ''" placement="top" :show-after="300">
          <div class="text">{{ preview(record.text_en, 260) || '(无)' }}</div>
        </el-tooltip>
      </div>

      <div v-if="record.comment" class="comment glass">
        <div class="lang">评价</div>
        <div class="comment-text">{{ record.comment }}</div>
      </div>

      <TagChips v-if="collectedTags.length" :tags="collectedTags" class="tags" />

      <div class="foot glass-soft">
        <span :title="record.updated_at">更新：{{ formatTime(record.updated_at) }}</span>
      </div>
    </div>

    <div class="idle-title">
      {{ record.name || '未命名' }}
    </div>
  </el-card>
</template>

<style scoped>
.record-card {
  position: relative;
  overflow: hidden;
  border: 2px solid transparent;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.record-card.is-fav {
  border-color: #faad14;
  box-shadow: 0 0 0 2px rgba(250, 173, 20, 0.18);
}
.record-card:hover {
  transform: translateY(-2px);
}
.record-card :deep(.el-card__body) {
  padding: 0;
}

.idle-title {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 14px;
  z-index: 2;
  max-width: calc(100% - 28px);
  padding: 8px 14px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  text-align: center;
  background: rgba(0, 0, 0, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 6px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: opacity 0.2s ease;
}
.record-card:hover .idle-title {
  opacity: 0;
  pointer-events: none;
}

.bg-layer {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.bg-slide {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  opacity: 0;
  transition: opacity 1.1s ease-in-out;
  transform: scale(1.04);
}
.bg-slide.active {
  opacity: 1;
}
.bg-fallback {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #e3f2fd 0%, #ede7f6 50%, #fff3e0 100%);
}
.bg-scrim {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(0, 0, 0, 0.18) 0%, rgba(0, 0, 0, 0.32) 100%);
}

.content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  text-align: center;
  transition: opacity 0.2s ease;
}
.record-card .content {
  opacity: 0;
  pointer-events: none;
}
.record-card:hover .content {
  opacity: 1;
  pointer-events: auto;
}

.glass {
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(14px) saturate(165%);
  -webkit-backdrop-filter: blur(14px) saturate(165%);
  border: 1px solid rgba(255, 255, 255, 0.42);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}
.glass-soft {
  background: rgba(255, 255, 255, 0.48);
  backdrop-filter: blur(10px) saturate(150%);
  -webkit-backdrop-filter: blur(10px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.36);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  text-align: left;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.head-right {
  display: flex;
  gap: 4px;
}
.fav-btn {
  font-size: 18px;
}
.rid {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.name-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
}
.name {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  cursor: pointer;
  border-bottom: 1px dashed transparent;
  transition: border-color 0.15s ease, color 0.15s ease;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.name:hover {
  border-bottom-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.name.placeholder {
  font-weight: 400;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  font-style: italic;
}
.name-input {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 15px;
  font-weight: 600;
  padding: 4px 8px;
  border: 1px solid var(--el-color-primary);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.85);
  outline: none;
}
.name-input:focus {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.25);
}

.lang-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  text-align: center;
}
.lang-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.lang {
  font-size: 11px;
  font-weight: 700;
  color: var(--el-text-color-secondary);
  letter-spacing: 1px;
}
.text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  word-break: break-word;
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-align: center;
}

.comment {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px;
  border-radius: 8px;
  border-left: 3px solid #faad14;
  text-align: center;
}
.comment-text {
  font-size: 12px;
  color: var(--el-text-color-regular);
  white-space: pre-wrap;
  word-break: break-word;
}

.tags {
  margin-top: 2px;
  padding: 4px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.foot {
  margin-top: auto;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  justify-content: space-between;
  text-align: left;
}
</style>
