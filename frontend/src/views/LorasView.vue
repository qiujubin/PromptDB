<script setup lang="ts">
defineOptions({ name: 'LorasView' })
import { computed, onActivated, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  Folder,
  DocumentCopy,
  Position,
  Plus,
  Delete,
} from '@element-plus/icons-vue'
import {
  deleteLoraEntry,
  fetchLoraConfig,
  fetchLoras,
  updateLoraConfig,
  updateLoraEntry,
  type LoraItemOut,
  type LoraTriggerGroup,
} from '@/api/loras'
import LoraCard from '@/components/LoraCard.vue'

const items = ref<LoraItemOut[]>([])
const folderPath = ref<string | null>(null)
const configLoaded = ref(false)
const loading = ref(false)
const savingConfig = ref(false)

const search = ref('')
const minRating = ref<number | null>(null)
const selectedBaseModel = ref<string | null>(null)
const selectedType = ref<string | null>(null)

const folderDraft = ref('')
const folderDialogOpen = ref(false)

const editing = ref<LoraItemOut | null>(null)
const editDialogOpen = ref(false)
const editForm = ref({
  nickname: '',
  rating: 0,
  comment: '',
  lora_type: '',
})
const editSaving = ref(false)

const triggerEditing = ref<LoraItemOut | null>(null)
const triggerDialogOpen = ref(false)
const triggerWordsDraft = ref('')
const triggerGroupsDraft = ref<LoraTriggerGroup[]>([])
const triggerNewWordInputs = ref<Record<number, string>>({})
const triggerSaving = ref(false)

const baseModelOptions = computed(() => {
  const set = new Set<string>()
  for (const it of items.value) {
    const m = it.meta.base_model?.trim()
    if (m) set.add(m)
  }
  return Array.from(set).sort()
})

const typeOptions = computed(() => {
  const set = new Set<string>()
  for (const it of items.value) {
    const t = it.lora_type?.trim()
    if (t) set.add(t)
  }
  return Array.from(set).sort()
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return items.value.filter((it) => {
    if (q) {
      const groupHay = (it.trigger_groups || [])
        .flatMap((g) => [g.name, ...g.words])
        .join(' ')
      const hay = [
        it.file_name,
        it.nickname ?? '',
        it.meta.trigger_words ?? '',
        it.trigger_words_user ?? '',
        groupHay,
        it.meta.base_model ?? '',
        it.lora_type ?? '',
        it.comment ?? '',
      ]
        .join(' ')
        .toLowerCase()
      if (!hay.includes(q)) return false
    }
    if (minRating.value !== null && it.rating < minRating.value) return false
    if (selectedBaseModel.value && it.meta.base_model !== selectedBaseModel.value)
      return false
    if (selectedType.value && (it.lora_type ?? '') !== selectedType.value)
      return false
    return true
  })
})

const totalLabel = computed(() => {
  const total = items.value.length
  if (filtered.value.length === total) return `${total}`
  return `${filtered.value.length} / ${total}`
})

async function loadConfig() {
  try {
    const cfg = await fetchLoraConfig()
    folderPath.value = cfg.folder_path
    folderDraft.value = cfg.folder_path ?? ''
    configLoaded.value = true
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function reload() {
  if (!folderPath.value) {
    items.value = []
    return
  }
  loading.value = true
  try {
    const resp = await fetchLoras()
    folderPath.value = resp.folder_path
    items.value = resp.items
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function openFolderDialog() {
  folderDraft.value = folderPath.value ?? ''
  folderDialogOpen.value = true
}

async function saveFolder() {
  const next = folderDraft.value.trim() || null
  savingConfig.value = true
  try {
    const cfg = await updateLoraConfig(next)
    folderPath.value = cfg.folder_path
    folderDialogOpen.value = false
    ElMessage.success(next ? '目录已更新，正在扫描…' : '已清除目录')
    await reload()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    savingConfig.value = false
  }
}

async function clearFolder() {
  try {
    await ElMessageBox.confirm(
      '确认清除当前 LoRA 目录配置？（不会删除任何文件）',
      '清除目录',
      { type: 'warning' },
    )
    savingConfig.value = true
    const cfg = await updateLoraConfig(null)
    folderPath.value = cfg.folder_path
    folderDraft.value = ''
    items.value = []
    folderDialogOpen.value = false
    ElMessage.success('已清除')
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  } finally {
    savingConfig.value = false
  }
}

function openEdit(lora: LoraItemOut) {
  editing.value = lora
  editForm.value = {
    nickname: lora.nickname ?? '',
    rating: lora.rating ?? 0,
    comment: lora.comment ?? '',
    lora_type: lora.lora_type ?? '',
  }
  editDialogOpen.value = true
}

async function saveEdit() {
  if (!editing.value) return
  editSaving.value = true
  try {
    const updated = await updateLoraEntry(editing.value.file_path, {
      nickname: editForm.value.nickname.trim() || null,
      rating: editForm.value.rating,
      comment: editForm.value.comment.trim() || null,
      lora_type: editForm.value.lora_type.trim() || null,
    })
    const idx = items.value.findIndex((it) => it.file_path === updated.file_path)
    if (idx !== -1) items.value[idx] = updated
    ElMessage.success('已保存')
    editDialogOpen.value = false
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    editSaving.value = false
  }
}

async function resetLora(lora: LoraItemOut) {
  try {
    await ElMessageBox.confirm(
      '确认清除该 LoRA 的自定义信息（昵称/评分/评价/类型）？',
      '重置自定义',
      { type: 'warning' },
    )
    await deleteLoraEntry(lora.file_path)
    ElMessage.success('已重置')
    await reload()
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  }
}

async function onCardRename(payload: {
  file_path: string
  nickname: string | null
}) {
  try {
    const updated = await updateLoraEntry(payload.file_path, {
      nickname: payload.nickname,
    })
    const idx = items.value.findIndex((it) => it.file_path === updated.file_path)
    if (idx !== -1) items.value[idx] = updated
  } catch (e) {
    ElMessage.error((e as Error).message)
    await reload()
  }
}

function clearFilters() {
  search.value = ''
  minRating.value = null
  selectedBaseModel.value = null
  selectedType.value = null
}

async function copyAllTriggers() {
  const withTrig = filtered.value.filter(
    (it) =>
      it.meta.trigger_words?.trim() ||
      it.trigger_words_user?.trim() ||
      (it.trigger_groups && it.trigger_groups.some((g) => g.words.length)),
  )
  if (withTrig.length === 0) {
    ElMessage.warning('当前结果中没有可复制的触发词')
    return
  }
  const text = withTrig
    .map((it) => {
      const words =
        (it.trigger_words_user ?? '').trim() || it.meta.trigger_words?.trim() || ''
      return `${it.nickname?.trim() || it.file_name}\n  ${words}`
    })
    .join('\n\n')
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`已复制 ${withTrig.length} 条触发词`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

function openTriggerEditor(lora: LoraItemOut) {
  triggerEditing.value = lora
  triggerWordsDraft.value = lora.trigger_words_user ?? ''
  triggerGroupsDraft.value = lora.trigger_groups.map((g) => ({
    name: g.name,
    words: [...g.words],
  }))
  triggerNewWordInputs.value = {}
  triggerDialogOpen.value = true
}

function addGroup() {
  triggerGroupsDraft.value.push({ name: `分组${triggerGroupsDraft.value.length + 1}`, words: [] })
}

function removeGroup(idx: number) {
  triggerGroupsDraft.value.splice(idx, 1)
  delete triggerNewWordInputs.value[idx]
}

function addWordToGroup(idx: number) {
  const raw = triggerNewWordInputs.value[idx] ?? ''
  if (!raw.trim()) return
  const parts = raw
    .split(/[,\n，]/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (!parts.length) return
  const group = triggerGroupsDraft.value[idx]
  const existing = new Set(group.words)
  for (const p of parts) {
    if (!existing.has(p)) {
      group.words.push(p)
      existing.add(p)
    }
  }
  triggerNewWordInputs.value[idx] = ''
}

function onAddWordKeydown(e: KeyboardEvent, idx: number) {
  if (e.isComposing || e.shiftKey) return
  if (e.key === 'Enter') {
    e.preventDefault()
    addWordToGroup(idx)
  }
}

function removeWordFromGroup(idx: number, wi: number) {
  triggerGroupsDraft.value[idx].words.splice(wi, 1)
}

function resetTriggerToOriginal() {
  triggerWordsDraft.value = ''
  triggerGroupsDraft.value = []
  triggerNewWordInputs.value = {}
  ElMessage.info('已重置为自动抽取的触发词（保存后生效）')
}

async function saveTriggers() {
  if (!triggerEditing.value) return
  triggerSaving.value = true
  try {
    const userWords = triggerWordsDraft.value.trim() || null
    const groups = triggerGroupsDraft.value
      .map((g) => ({
        name: g.name.trim(),
        words: g.words.map((w) => w.trim()).filter((w) => w.length > 0),
      }))
      .filter((g) => g.name.length > 0)
    const updated = await updateLoraEntry(triggerEditing.value.file_path, {
      trigger_words_user: userWords,
      trigger_groups: groups,
    })
    const idx = items.value.findIndex((it) => it.file_path === updated.file_path)
    if (idx !== -1) items.value[idx] = updated
    ElMessage.success('触发词已保存')
    triggerDialogOpen.value = false
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    triggerSaving.value = false
  }
}

let activatedOnce = false
onMounted(async () => {
  await loadConfig()
  if (folderPath.value) await reload()
})
onActivated(async () => {
  if (!activatedOnce) {
    activatedOnce = true
    return
  }
  await loadConfig()
  if (folderPath.value) await reload()
})
</script>

<template>
  <div class="page">
    <div class="header">
      <div class="title">LoRA 管理</div>
      <div class="toolbar">
        <el-input
          v-model="search"
          placeholder="搜索文件名/昵称/触发词/类型..."
          clearable
          @keyup.enter="reload"
        >
          <template #append>
            <el-button :icon="Search" @click="reload" />
          </template>
        </el-input>
        <el-select
          v-model="minRating"
          placeholder="最低评分"
          clearable
          style="width: 130px"
        >
          <el-option :value="0" label="不限" />
          <el-option :value="1" label="≥ 1 星" />
          <el-option :value="2" label="≥ 2 星" />
          <el-option :value="3" label="≥ 3 星" />
          <el-option :value="4" label="≥ 4 星" />
          <el-option :value="5" label="5 星" />
        </el-select>
        <el-select
          v-model="selectedBaseModel"
          placeholder="底模"
          clearable
          filterable
          :disabled="!baseModelOptions.length"
          style="width: 160px"
        >
          <el-option
            v-for="m in baseModelOptions"
            :key="m"
            :label="m"
            :value="m"
          />
        </el-select>
        <el-select
          v-model="selectedType"
          placeholder="类型"
          clearable
          filterable
          allow-create
          :disabled="!typeOptions.length"
          style="width: 140px"
        >
          <el-option
            v-for="t in typeOptions"
            :key="t"
            :label="t"
            :value="t"
          />
        </el-select>
        <el-button :icon="Refresh" @click="reload">刷新</el-button>
        <el-button :icon="Position" @click="clearFilters">清筛选</el-button>
        <el-button
          type="primary"
          :icon="DocumentCopy"
          :disabled="!filtered.some((it) => it.meta.trigger_words)"
          @click="copyAllTriggers"
        >
          批量复制触发词
        </el-button>
      </div>
    </div>

    <div class="folder-bar">
      <el-icon class="folder-icon"><Folder /></el-icon>
      <span class="folder-label">目录：</span>
      <span class="folder-path" :title="folderPath ?? '尚未设置'">
        {{ folderPath || '（尚未设置目录）' }}
      </span>
      <span class="folder-count">共 {{ totalLabel }} 个 LoRA</span>
      <div class="folder-actions">
        <el-button size="small" type="primary" @click="openFolderDialog">
          {{ folderPath ? '更换目录' : '设置目录' }}
        </el-button>
      </div>
    </div>

    <div v-if="!folderPath" class="empty-state">
      <el-empty description="尚未设置 LoRA 目录">
        <el-button type="primary" @click="openFolderDialog">设置目录</el-button>
      </el-empty>
    </div>

    <div v-else v-loading="loading" class="grid">
      <el-empty v-if="!loading && filtered.length === 0" description="当前筛选下没有 LoRA" />
      <LoraCard
        v-for="lora in filtered"
        :key="lora.file_path"
        :lora="lora"
        @edit="openEdit"
        @reset="resetLora"
        @edit-triggers="openTriggerEditor"
        @rename="onCardRename"
      />
    </div>

    <el-dialog
      v-model="folderDialogOpen"
      title="设置 LoRA 目录"
      width="560px"
      :close-on-click-modal="false"
    >
      <div class="dialog-body">
        <p class="hint">
          请输入本机 ComfyUI 的 LoRA 模型存放文件夹绝对路径，例如
          <code>D:\ComfyUI\models\loras</code>。目录不存在或不可访问会被拒绝。
        </p>
        <el-input
          v-model="folderDraft"
          placeholder="例如 D:\ComfyUI\models\loras"
          clearable
        />
      </div>
      <template #footer>
        <el-button v-if="folderPath" type="danger" link @click="clearFolder">
          清除当前目录
        </el-button>
        <el-button @click="folderDialogOpen = false">取消</el-button>
        <el-button
          type="primary"
          :loading="savingConfig"
          @click="saveFolder"
        >
          保存并扫描
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="editDialogOpen"
      title="编辑 LoRA 信息"
      width="520px"
      :close-on-click-modal="false"
    >
      <div v-if="editing" class="edit-body">
        <div class="edit-file">
          <el-icon><svg viewBox="0 0 1024 1024" width="14" height="14"><path fill="currentColor" d="M704 256H448c-17.7 0-32 14.3-32 32v448c0 17.7 14.3 32 32 32h320c17.7 0 32-14.3 32-32V352l-96-96zm-32 64l64 64v352H448V320h224z"/></svg></el-icon>
          <span :title="editing.file_name">{{ editing.file_name }}</span>
        </div>
        <el-form label-position="top">
          <el-form-item label="我给它起的名字">
            <el-input
              v-model="editForm.nickname"
              maxlength="255"
              show-word-limit
              placeholder="给它起个名字..."
            />
          </el-form-item>
          <el-form-item label="类型">
            <el-input
              v-model="editForm.lora_type"
              maxlength="64"
              placeholder="例如 角色 / 风格 / 姿势"
            />
          </el-form-item>
          <el-form-item label="评分">
            <el-rate
              v-model="editForm.rating"
              :max="5"
              show-text
              :texts="['待定', '一般', '还行', '不错', '好用', '必备']"
            />
          </el-form-item>
          <el-form-item label="评价">
            <el-input
              v-model="editForm.comment"
              type="textarea"
              :rows="3"
              maxlength="2000"
              show-word-limit
              placeholder="写下你对这个 LoRA 的使用心得..."
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="editDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="triggerDialogOpen"
      :title="`编辑触发词 - ${triggerEditing?.file_name ?? ''}`"
      width="760px"
      :close-on-click-modal="false"
    >
      <div v-if="triggerEditing" class="trigger-edit-body">
        <p class="hint">
          「触发词」是直接覆盖原始元数据的整段文本（用英文逗号或换行分隔词）。
          「触发词分组」是按场景分组管理（如「基础」「高强度」），每个分组可单独一键复制。
          清空「触发词」并保存后将恢复显示原始元数据中的触发词。
        </p>

        <div v-if="triggerEditing.meta.trigger_words" class="meta-hint">
          <strong>原始触发词：</strong>
          <span>{{ triggerEditing.meta.trigger_words }}</span>
        </div>

        <el-form label-position="top">
          <el-form-item label="触发词（覆盖原始）">
            <el-input
              v-model="triggerWordsDraft"
              type="textarea"
              :rows="3"
              maxlength="8000"
              show-word-limit
              placeholder="例如：mychar, mychar_face, mychar_outfit"
            />
          </el-form-item>

          <el-form-item label="触发词分组">
            <div class="groups">
              <div
                v-for="(g, gi) in triggerGroupsDraft"
                :key="gi"
                class="group-card"
              >
                <div class="group-card-head">
                  <el-input
                    v-model="g.name"
                    size="small"
                    placeholder="分组名（如 基础 / 高强度）"
                    maxlength="64"
                    class="group-name-input"
                  />
                  <el-tooltip content="删除此分组" placement="top">
                    <el-button
                      :icon="Delete"
                      size="small"
                      link
                      type="danger"
                      @click="removeGroup(gi)"
                    />
                  </el-tooltip>
                </div>
                <div class="group-words">
                  <el-tag
                    v-for="(w, wi) in g.words"
                    :key="wi"
                    closable
                    size="small"
                    effect="plain"
                    class="word-chip"
                    @close="removeWordFromGroup(gi, wi)"
                  >
                    {{ w }}
                  </el-tag>
                  <el-input
                    v-model="triggerNewWordInputs[gi]"
                    type="textarea"
                    :autosize="{ minRows: 1, maxRows: 4 }"
                    size="small"
                    resize="none"
                    placeholder="可粘贴多个词（逗号 / 换行分隔，回车添加）"
                    class="add-word-input"
                    @keydown="onAddWordKeydown($event, gi)"
                  />
                  <el-button size="small" @click="addWordToGroup(gi)">添加</el-button>
                </div>
              </div>
              <el-button :icon="Plus" size="small" @click="addGroup">
                + 新增分组
              </el-button>
            </div>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button type="warning" link @click="resetTriggerToOriginal">
          恢复为原始
        </el-button>
        <el-button @click="triggerDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="triggerSaving" @click="saveTriggers">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1760px;
  margin: 0 auto;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.toolbar .el-input {
  flex: 1 1 280px;
  min-width: 200px;
  max-width: 420px;
}

.folder-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 8px;
  flex-wrap: wrap;
}
.folder-icon {
  color: var(--el-color-primary);
  font-size: 18px;
}
.folder-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.folder-path {
  flex: 1;
  min-width: 0;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 13px;
  color: var(--el-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.folder-count {
  font-size: 13px;
  color: var(--el-text-color-regular);
  background: var(--el-color-primary-light-7);
  padding: 2px 10px;
  border-radius: 12px;
}
.folder-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  padding: 40px 0;
}

.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 0;
  line-height: 1.6;
}
.hint code {
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  background: var(--el-fill-color-light);
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.edit-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.edit-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.grid {
  column-count: 1;
  column-gap: 18px;
  min-height: 240px;
}
.grid > * {
  break-inside: avoid;
  -webkit-column-break-inside: avoid;
  page-break-inside: avoid;
  margin-bottom: 18px;
  display: inline-block;
  width: 100%;
}
@media (min-width: 720px)  { .grid { column-count: 2; } }
@media (min-width: 1080px) { .grid { column-count: 3; } }
@media (min-width: 1500px) { .grid { column-count: 4; } }
@media (min-width: 1860px) { .grid { column-count: 5; } }

.trigger-edit-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.meta-hint {
  font-size: 12px;
  padding: 8px 10px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  color: var(--el-text-color-secondary);
  word-break: break-word;
  white-space: pre-wrap;
}
.meta-hint strong {
  color: var(--el-text-color-regular);
  margin-right: 4px;
}
.groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.group-card {
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.group-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.group-name-input {
  flex: 1;
}
.group-words {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.word-chip {
  font-family: 'SF Mono', Menlo, Consolas, monospace;
}
.add-word-input {
  width: 180px;
}
</style>
