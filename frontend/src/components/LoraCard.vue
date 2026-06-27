<script setup lang="ts">
import { computed, ref, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  ArrowUp,
  DocumentCopy,
  EditPen,
  RefreshRight,
} from '@element-plus/icons-vue'
import type { LoraItemOut } from '@/api/loras'

const props = defineProps<{ lora: LoraItemOut }>()
const emit = defineEmits<{
  edit: [lora: LoraItemOut]
  reset: [lora: LoraItemOut]
  'edit-triggers': [lora: LoraItemOut]
  rename: [payload: { file_path: string; nickname: string | null }]
}>()

const displayName = computed(() => props.lora.nickname?.trim() || '未命名')
const placeholder = computed(() => !props.lora.nickname?.trim())

const isUserTrigger = computed(
  () => (props.lora.trigger_words_user ?? '').trim().length > 0,
)
const effectiveTriggerWords = computed(
  () => (props.lora.trigger_words_user ?? '').trim() || props.lora.meta.trigger_words?.trim() || '',
)

const triggerList = computed(() =>
  effectiveTriggerWords.value
    .split(/[,\n，]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0),
)

const hasGroups = computed(() => props.lora.trigger_groups.length > 0)
const hasFlatTrigger = computed(() => triggerList.value.length > 0)
const hasAnyTrigger = computed(() => hasGroups.value || hasFlatTrigger.value)

const TRIGGER_LEN_THRESHOLD = 60
const TRIGGER_COUNT_THRESHOLD = 6

const triggerExpanded = ref(false)

const triggerOverflow = computed(
  () =>
    effectiveTriggerWords.value.length > TRIGGER_LEN_THRESHOLD ||
    triggerList.value.length > TRIGGER_COUNT_THRESHOLD,
)

watch(
  () => props.lora.file_path,
  () => {
    triggerExpanded.value = false
  },
)

async function copyTrigger() {
  if (!effectiveTriggerWords.value) return
  try {
    await navigator.clipboard.writeText(effectiveTriggerWords.value)
    ElMessage.success(`已复制 ${triggerList.value.length} 个触发词`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function copyOriginalTriggers() {
  const text = props.lora.meta.trigger_words?.trim()
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制原始触发词')
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

async function copyOne(word: string) {
  try {
    await navigator.clipboard.writeText(word)
    ElMessage.success(`已复制: ${word}`)
  } catch {
    ElMessage.error('复制失败')
  }
}

async function copyGroupWords(group: { name: string; words: string[] }) {
  if (!group.words.length) return
  try {
    await navigator.clipboard.writeText(group.words.join(', '))
    ElMessage.success(`已复制「${group.name}」( ${group.words.length} 项)`)
  } catch {
    ElMessage.error('复制失败')
  }
}

function formatBytes(b: number) {
  if (!b) return '-'
  const u = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = b
  while (n >= 1024 && i < u.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(n >= 10 || i === 0 ? 0 : 1)} ${u[i]}`
}

function formatTime(s: string | null | undefined) {
  if (!s) return '-'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}

const editingName = ref(false)
const nameDraft = ref('')
const nameInput = ref<HTMLInputElement | null>(null)
const savingName = ref(false)

async function startEditName() {
  nameDraft.value = props.lora.nickname ?? ''
  editingName.value = true
  await nextTick()
  nameInput.value?.focus()
  nameInput.value?.select()
}

function cancelEditName() {
  editingName.value = false
  nameDraft.value = ''
}

async function commitEditName() {
  const next = nameDraft.value.trim()
  if (next === (props.lora.nickname ?? '')) {
    editingName.value = false
    return
  }
  savingName.value = true
  try {
    emit('rename', {
      file_path: props.lora.file_path,
      nickname: next || null,
    })
    editingName.value = false
  } finally {
    savingName.value = false
  }
}

function onNameKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commitEditName()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    cancelEditName()
  }
}
</script>

<template>
  <el-card class="lora-card" shadow="hover">
    <div class="head">
      <div class="head-tags">
        <el-tag
          v-if="lora.lora_type"
          type="success"
          size="small"
          effect="dark"
          round
        >
          {{ lora.lora_type }}
        </el-tag>
        <el-tag
          v-else-if="lora.meta.network_module"
          type="info"
          size="small"
          effect="plain"
          round
        >
          {{ lora.meta.network_module }}
        </el-tag>
        <el-tag
          v-if="lora.meta.base_model"
          type="primary"
          size="small"
          effect="plain"
          round
        >
          {{ lora.meta.base_model }}
        </el-tag>
        <el-rate
          v-if="lora.rating > 0"
          :model-value="lora.rating"
          disabled
          :max="5"
          size="small"
          show-score
          text-color="#ff9900"
        />
        <span v-if="!lora.has_meta" class="meta-warn" title="未识别到 safetensors metadata">
          无元数据
        </span>
      </div>
      <div class="head-actions">
        <el-tooltip content="重置自定义(恢复原始信息)" placement="top">
          <el-button
            :icon="RefreshRight"
            size="small"
            link
            type="info"
            @click="emit('reset', lora)"
          />
        </el-tooltip>
        <el-tooltip content="编辑昵称/评分/类型/评价" placement="top">
          <el-button
            :icon="EditPen"
            size="small"
            link
            type="primary"
            @click="emit('edit', lora)"
          />
        </el-tooltip>
      </div>
    </div>

    <div class="name-row">
      <template v-if="!editingName">
        <div
          class="name"
          :class="{ placeholder }"
          :title="lora.nickname || '点击给它起个名字'"
          @click="startEditName"
        >
          {{ displayName }}
        </div>
      </template>
      <template v-else>
        <input
          ref="nameInput"
          v-model="nameDraft"
          class="name-input"
          maxlength="255"
          placeholder="给它起个名字..."
          :disabled="savingName"
          @keydown="onNameKeydown"
          @blur="commitEditName"
        />
      </template>
    </div>

    <div class="file-name" :title="lora.file_name">
      <el-icon><svg viewBox="0 0 1024 1024" width="14" height="14"><path fill="currentColor" d="M704 256H448c-17.7 0-32 14.3-32 32v448c0 17.7 14.3 32 32 32h320c17.7 0 32-14.3 32-32V352l-96-96zm-32 64l64 64v352H448V320h224z" /></svg></el-icon>
      <span>{{ lora.file_name }}</span>
    </div>

    <div v-if="hasAnyTrigger" class="trigger">
      <div class="trigger-head">
        <div class="trigger-head-left">
          <span class="section-label">触发词</span>
          <span v-if="isUserTrigger" class="user-tag">自定义</span>
          <el-tooltip v-else-if="lora.meta.trigger_words" content="来自 safetensors 元数据" placement="top">
            <span class="auto-tag">原始</span>
          </el-tooltip>
        </div>
        <div class="trigger-head-right">
          <el-tooltip content="编辑触发词 / 分组" placement="top">
            <el-button
              link
              size="small"
              type="primary"
              :icon="EditPen"
              class="edit-trigger-btn"
              @click="emit('edit-triggers', lora)"
            />
          </el-tooltip>
          <el-tooltip v-if="lora.meta.trigger_words" content="复制 safetensors 里的初始触发词" placement="top">
            <el-button
              size="small"
              :icon="DocumentCopy"
              class="copy-original-btn"
              @click="copyOriginalTriggers"
            >
              复制原始
            </el-button>
          </el-tooltip>
          <el-button
            v-if="!hasGroups && triggerOverflow"
            link
            size="small"
            type="primary"
            class="expand-btn"
            :icon="triggerExpanded ? ArrowUp : ArrowDown"
            @click="triggerExpanded = !triggerExpanded"
          >
            {{ triggerExpanded ? '收起' : `展开 ${triggerList.length} 项` }}
          </el-button>
          <el-button
            v-if="!hasGroups"
            type="primary"
            size="small"
            :icon="DocumentCopy"
            class="copy-trigger-btn"
            @click="copyTrigger"
          >
            一键复制
          </el-button>
        </div>
      </div>

      <div v-if="hasGroups" class="trigger-groups">
        <div
          v-for="(g, gi) in lora.trigger_groups"
          :key="gi"
          class="trigger-group"
        >
          <div class="group-head">
            <span class="group-name">{{ g.name }}</span>
            <span class="group-count">{{ g.words.length }} 项</span>
            <el-button
              type="primary"
              size="small"
              :icon="DocumentCopy"
              class="copy-group-btn"
              :disabled="!g.words.length"
              @click="copyGroupWords(g)"
            >
              复制此组
            </el-button>
          </div>
          <div v-if="g.words.length" class="trigger-chips expanded">
            <span
              v-for="(w, wi) in g.words"
              :key="wi"
              class="trigger-chip"
              :title="`点击复制: ${w}`"
              @click="copyOne(w)"
            >
              {{ w }}
            </span>
          </div>
          <div v-else class="group-empty">此分组暂无触发词</div>
        </div>
      </div>

      <div
        v-else
        class="trigger-chips"
        :class="{
          collapsed: triggerOverflow && !triggerExpanded,
          expanded: triggerOverflow && triggerExpanded,
        }"
      >
        <span
          v-for="(w, idx) in triggerList"
          :key="idx"
          class="trigger-chip"
          :title="`点击复制: ${w}`"
          @click="copyOne(w)"
        >
          {{ w }}
        </span>
      </div>
    </div>

    <div v-if="lora.meta.description" class="description">
      <div class="section-label">描述</div>
      <div class="description-text">{{ lora.meta.description }}</div>
    </div>

    <div v-if="lora.comment" class="comment">
      <div class="section-label">评价</div>
      <div class="comment-text">{{ lora.comment }}</div>
    </div>

    <div class="foot">
      <span :title="lora.file_mtime ?? ''">
        文件：{{ formatTime(lora.file_mtime) }}
      </span>
      <span class="file-size">{{ formatBytes(lora.file_size) }}</span>
    </div>
  </el-card>
</template>

<style scoped>
.lora-card {
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  border: 2px solid transparent;
}
.lora-card:hover {
  transform: translateY(-2px);
  border-color: var(--el-color-primary-light-5);
}
.lora-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 24px;
}
.head-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  flex: 1;
  min-width: 0;
}
.head-actions {
  display: flex;
  gap: 4px;
}
.meta-warn {
  font-size: 11px;
  color: var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  padding: 1px 8px;
  border-radius: 10px;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.name {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-color-primary);
  cursor: pointer;
  border-bottom: 1px dashed transparent;
  transition: border-color 0.15s ease, color 0.15s ease;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.name:hover {
  border-bottom-color: var(--el-color-primary);
}
.name.placeholder {
  font-weight: 400;
  color: var(--el-text-color-placeholder);
  font-style: italic;
}
.name-input {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  padding: 4px 8px;
  border: 1px solid var(--el-color-primary);
  border-radius: 4px;
  background: var(--el-fill-color-blank);
  outline: none;
}
.name-input:focus {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.25);
}

.file-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trigger {
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.trigger-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.trigger-head-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.trigger-head-right {
  display: flex;
  align-items: center;
  gap: 4px;
}
.edit-trigger-btn {
  padding: 2px 6px;
}
.expand-btn {
  font-size: 12px;
}
.section-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--el-color-primary);
  letter-spacing: 1px;
}
.user-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 8px;
  color: #d81b60;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(216, 27, 96, 0.25);
}
.auto-tag {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 8px;
  color: var(--el-text-color-secondary);
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--el-border-color-lighter);
  cursor: help;
}
.copy-trigger-btn {
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(64, 158, 255, 0.3);
}
.copy-trigger-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(64, 158, 255, 0.45);
}

.trigger-groups {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.trigger-group {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(94, 53, 177, 0.18);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.group-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.group-name {
  font-size: 12px;
  font-weight: 700;
  color: #5e35b1;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.group-count {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  padding: 1px 6px;
  border-radius: 8px;
}
.copy-group-btn {
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(64, 158, 255, 0.25);
}
.copy-group-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(64, 158, 255, 0.4);
}
.group-empty {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  font-style: italic;
}

.trigger-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  position: relative;
}
.trigger-chips.collapsed {
  max-height: 64px;
  overflow: hidden;
}
.trigger-chips.collapsed::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 22px;
  background: linear-gradient(
    to bottom,
    rgba(243, 229, 245, 0) 0%,
    rgba(243, 229, 245, 0.95) 80%
  );
  pointer-events: none;
  border-radius: 0 0 8px 8px;
}
.trigger-chip {
  display: inline-block;
  padding: 4px 10px;
  font-size: 12px;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  color: #5e35b1;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(94, 53, 177, 0.25);
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease, background 0.12s ease;
  user-select: none;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trigger-chips.expanded .trigger-chip {
  max-width: 100%;
  white-space: normal;
  word-break: break-word;
}
.trigger-chip:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(94, 53, 177, 0.25);
}

.description,
.comment {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.description .section-label,
.comment .section-label {
  color: var(--el-text-color-regular);
}
.description-text,
.comment-text {
  font-size: 12px;
  line-height: 1.55;
  color: var(--el-text-color-regular);
  word-break: break-word;
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  padding-top: 6px;
  border-top: 1px dashed var(--el-border-color-lighter);
}
.file-size {
  font-family: 'SF Mono', Menlo, Consolas, monospace;
}
</style>
