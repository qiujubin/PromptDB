<script setup lang="ts">
defineOptions({ name: 'LibraryView' })
import { computed, onActivated, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  Delete,
  DocumentCopy,
  Check,
  Close,
  PriceTag,
  EditPen,
} from '@element-plus/icons-vue'
import {
  bulkDeleteLibraryItems,
  deleteLibraryItem,
  fetchLibrary,
} from '@/api/library'
import type { LibraryItem } from '@/api/prompts'
import {
  createTag,
  fetchTags,
  setPromptTags,
  type TagOut,
  type TagTreeNode,
  type TagTreeResponse,
} from '@/api/tags'
import CopyButton from '@/components/CopyButton.vue'
import TagChips from '@/components/TagChips.vue'

const items = ref<LibraryItem[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')

const pagination = reactive({ page: 1, pageSize: 30 })

const route = useRoute()
const router = useRouter()

const multiSelect = ref(false)
const selected = ref<Set<number>>(new Set())
const bulkWorking = ref(false)

const selectedCount = computed(() => selected.value.size)
const allOnPageSelected = computed(
  () => items.value.length > 0 && items.value.every((r) => selected.value.has(r.id)),
)

const tagTree = ref<TagTreeResponse>({ categories: [] })
const selectedCategoryId = ref<number | null>(null)
const selectedLeafId = ref<number | null>(null)

const selectedCategory = computed(() => {
  if (selectedCategoryId.value === null) return null
  return tagTree.value.categories.find((c) => c.id === selectedCategoryId.value) ?? null
})

const availableLeaves = computed(() => selectedCategory.value?.children ?? [])

const drawerOpen = ref(false)
const editingPrompt = ref<LibraryItem | null>(null)
const draftTagIds = ref<Set<number>>(new Set())
const drawerLoading = ref(false)
const drawerSaving = ref(false)

const newLeafNameByCat = reactive<Record<number, string>>({})

const tagPathById = computed(() => {
  const map = new Map<number, string>()
  function walk(nodes: TagTreeNode[], prefix: string) {
    for (const n of nodes) {
      map.set(n.id, prefix ? `${prefix}/${n.name}` : n.name)
      walk(n.children, prefix ? `${prefix}/${n.name}` : n.name)
    }
  }
  walk(tagTree.value.categories, '')
  return map
})

const tagPathByIdFlat = computed(() => tagPathById.value)

async function loadTags() {
  try {
    tagTree.value = await fetchTags()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function reload() {
  loading.value = true
  try {
    const tagIds = collectTagIds()
    const resp = await fetchLibrary({
      page: pagination.page,
      page_size: pagination.pageSize,
      search: search.value.trim() || undefined,
      tag_ids: tagIds.length ? tagIds : undefined,
    })
    items.value = resp.items
    total.value = resp.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

function collectTagIds(): number[] {
  if (selectedLeafId.value !== null) return [selectedLeafId.value]
  if (selectedCategory.value) {
    return selectedCategory.value.children.map((c) => c.id)
  }
  return []
}

const activeFilterPath = computed(() => {
  if (selectedLeaf.value) {
    return tagPathByIdFlat.value.get(selectedLeaf.value.id) ?? selectedLeaf.value.name
  }
  if (selectedCategory.value) return selectedCategory.value.name
  return ''
})

const selectedLeaf = computed(() => {
  if (selectedLeafId.value === null) return null
  return availableLeaves.value.find((l) => l.id === selectedLeafId.value) ?? null
})

function onSearch() {
  pagination.page = 1
  reload()
}

function onPageChange(p: number) {
  pagination.page = p
  reload()
}

function onPageSizeChange(s: number) {
  pagination.pageSize = s
  pagination.page = 1
  reload()
}

function toggleMultiSelect() {
  multiSelect.value = !multiSelect.value
  if (!multiSelect.value) selected.value = new Set()
}

function isSelected(id: number) {
  return selected.value.has(id)
}

function toggleSelect(row: LibraryItem) {
  const next = new Set(selected.value)
  if (next.has(row.id)) next.delete(row.id)
  else next.add(row.id)
  selected.value = next
}

function toggleAllOnPage() {
  const next = new Set(selected.value)
  if (allOnPageSelected.value) {
    items.value.forEach((r) => next.delete(r.id))
  } else {
    items.value.forEach((r) => next.add(r.id))
  }
  selected.value = next
}

function clearSelection() {
  selected.value = new Set()
}

async function onDelete(row: LibraryItem) {
  try {
    await ElMessageBox.confirm('确认删除该提示词？此操作不可撤销。', '删除提示词', {
      type: 'warning',
    })
    await deleteLibraryItem(row.id)
    ElMessage.success('已删除')
    selected.value = new Set([...selected.value].filter((id) => id !== row.id))
    reload()
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  }
}

async function onBulkDelete() {
  if (selectedCount.value === 0) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedCount.value} 条提示词？此操作不可撤销。`,
      '批量删除',
      { type: 'warning' },
    )
    bulkWorking.value = true
    const ids = [...selected.value]
    const resp = await bulkDeleteLibraryItems(ids)
    ElMessage.success(`已删除 ${resp.deleted} 条`)
    selected.value = new Set()
    reload()
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  } finally {
    bulkWorking.value = false
  }
}

async function onBulkCopy() {
  if (selectedCount.value === 0) return
  const ids = [...selected.value]
  const text = items.value
    .filter((r) => ids.includes(r.id))
    .map((r) => r.text_en)
    .join('\n\n')
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`已复制 ${ids.length} 条到剪贴板`)
  } catch {
    ElMessage.error('复制失败，请手动复制')
  }
}

function applyTagFilter(categoryId: number | null, leafId: number | null = null) {
  const nextQuery = { ...route.query }
  if (categoryId === null) {
    delete nextQuery.tag_category
  } else {
    nextQuery.tag_category = String(categoryId)
  }
  if (leafId === null) {
    delete nextQuery.tag_leaf
  } else {
    nextQuery.tag_leaf = String(leafId)
  }
  router.replace({ name: 'library', query: nextQuery })
}

function syncTagFilterFromRoute() {
  const catRaw = route.query.tag_category
  const leafRaw = route.query.tag_leaf
  const catId = typeof catRaw === 'string' && catRaw ? Number(catRaw) : null
  const leafId = typeof leafRaw === 'string' && leafRaw ? Number(leafRaw) : null
  if (catId !== null && (Number.isNaN(catId) || catId <= 0)) return
  if (leafId !== null && (Number.isNaN(leafId) || leafId <= 0)) return
  selectedCategoryId.value = catId
  selectedLeafId.value = leafId
  pagination.page = 1
  reload()
}

function onCategoryChange(id: number | null) {
  selectedLeafId.value = null
  applyTagFilter(id, null)
}

function onLeafChange(id: number | null) {
  applyTagFilter(selectedCategoryId.value, id)
}

function clearTagFilter() {
  applyTagFilter(null, null)
}

function onTagChipClick(tag: TagOut) {
  const cat = tagTree.value.categories.find((c) =>
    c.children.some((l) => l.id === tag.id),
  )
  applyTagFilter(cat?.id ?? null, tag.id)
}

async function openTagDrawer(row: LibraryItem) {
  editingPrompt.value = row
  drawerOpen.value = true
  draftTagIds.value = new Set(row.tags.map((t) => t.id))
  if (tagTree.value.categories.length === 0) {
    drawerLoading.value = true
    await loadTags()
    drawerLoading.value = false
  }
}

function closeTagDrawer() {
  drawerOpen.value = false
  editingPrompt.value = null
  draftTagIds.value = new Set()
}

function toggleDraftTag(id: number) {
  const next = new Set(draftTagIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  draftTagIds.value = next
}

async function saveDrawer() {
  if (!editingPrompt.value) return
  drawerSaving.value = true
  try {
    await setPromptTags(editingPrompt.value.id, [...draftTagIds.value])
    ElMessage.success('标签已更新')
    closeTagDrawer()
    reload()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    drawerSaving.value = false
  }
}

async function createLeafInline(categoryId: number) {
  const name = (newLeafNameByCat[categoryId] || '').trim()
  if (!name) {
    ElMessage.warning('请输入子标签名')
    return
  }
  try {
    const created = await createTag({ name, parent_id: categoryId })
    ElMessage.success(`已创建「${created.name}」`)
    newLeafNameByCat[categoryId] = ''
    await loadTags()
    draftTagIds.value = new Set([...draftTagIds.value, created.id])
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function formatTime(s: string | null) {
  if (!s) return '-'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}

function preview(text: string, max = 80) {
  return text.length > max ? text.slice(0, max) + '…' : text
}

watch(
  () => [route.query.tag_category, route.query.tag_leaf],
  () => {
    syncTagFilterFromRoute()
  },
)

onMounted(async () => {
  await loadTags()
  syncTagFilterFromRoute()
})

let activatedOnce = false
onActivated(async () => {
  if (!activatedOnce) {
    activatedOnce = true
    return
  }
  await loadTags()
  await reload()
})
</script>

<template>
  <div class="page">
    <div class="header">
      <div class="title">提示词库（按使用次数降序）</div>
      <div class="toolbar">
        <el-input
          v-model="search"
          placeholder="搜索中英文关键词（空格分隔多个）"
          clearable
          @keyup.enter="onSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="onSearch" />
          </template>
        </el-input>
        <el-select
          v-model="selectedCategoryId"
          placeholder="大标签"
          clearable
          :disabled="!tagTree.categories.length"
          style="width: 160px"
          @change="onCategoryChange"
        >
          <el-option
            v-for="cat in tagTree.categories"
            :key="cat.id"
            :label="`${cat.name} (${cat.usage_count})`"
            :value="cat.id"
          />
        </el-select>
        <el-select
          v-model="selectedLeafId"
          placeholder="小标签"
          clearable
          :disabled="!availableLeaves.length"
          style="width: 160px"
          @change="onLeafChange"
        >
          <el-option
            v-for="leaf in availableLeaves"
            :key="leaf.id"
            :label="`${leaf.name} (${leaf.usage_count})`"
            :value="leaf.id"
          />
        </el-select>
        <el-button :icon="Refresh" @click="reload">刷新</el-button>
        <el-button
          :type="multiSelect ? 'warning' : 'default'"
          :icon="multiSelect ? Close : Check"
          @click="toggleMultiSelect"
        >
          {{ multiSelect ? '退出多选' : '多选' }}
        </el-button>
      </div>
    </div>

    <div v-if="activeFilterPath" class="filter-bar">
      <span class="filter-label">当前筛选：</span>
      <el-tag type="primary" effect="dark" round :closable="true" @close="clearTagFilter">
        <el-icon><PriceTag /></el-icon>
        <span style="margin-left: 4px">{{ activeFilterPath }}</span>
      </el-tag>
    </div>

    <transition name="slide">
      <div v-if="multiSelect" class="bulk-bar">
        <div class="bulk-info">
          已选 <strong>{{ selectedCount }}</strong> 项
        </div>
        <div class="bulk-actions">
          <el-button size="small" @click="toggleAllOnPage">
            {{ allOnPageSelected ? '取消全选本页' : '全选本页' }}
          </el-button>
          <el-button size="small" :disabled="selectedCount === 0" @click="clearSelection">
            清空选择
          </el-button>
          <el-button
            size="small"
            type="primary"
            :icon="DocumentCopy"
            :disabled="selectedCount === 0"
            @click="onBulkCopy"
          >
            批量复制
          </el-button>
          <el-button
            size="small"
            type="danger"
            :icon="Delete"
            :disabled="selectedCount === 0"
            :loading="bulkWorking"
            @click="onBulkDelete"
          >
            批量删除
          </el-button>
        </div>
      </div>
    </transition>

    <div v-loading="loading" class="grid">
      <el-empty v-if="!loading && items.length === 0" description="暂无数据" />

      <el-card
        v-for="row in items"
        :key="row.id"
        class="item"
        :class="{ 'is-selected': isSelected(row.id), 'selectable': multiSelect }"
        shadow="hover"
        @click="multiSelect && toggleSelect(row)"
      >
        <div class="item-head">
          <div class="item-meta">
            <el-checkbox
              v-if="multiSelect"
              :model-value="isSelected(row.id)"
              @click.stop
              @change="toggleSelect(row)"
            />
            <el-tag type="primary" size="small" effect="dark">
              <el-icon><DocumentCopy /></el-icon>
              <span style="margin-left: 4px">{{ row.usage_count }}</span>
            </el-tag>
            <span class="item-id">#{{ row.id }}</span>
          </div>
          <div v-if="!multiSelect" class="item-actions" @click.stop>
            <el-tooltip content="编辑标签" placement="top">
              <el-button
                :icon="EditPen"
                size="small"
                link
                type="primary"
                @click="openTagDrawer(row)"
              />
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button
                type="danger"
                :icon="Delete"
                size="small"
                link
                @click="onDelete(row)"
              />
            </el-tooltip>
          </div>
        </div>

        <el-tooltip :content="row.text_en" placement="top" :show-after="300">
          <div class="item-en">{{ preview(row.text_en, 140) }}</div>
        </el-tooltip>

        <div v-if="row.text_zh" class="item-zh">{{ preview(row.text_zh, 100) }}</div>
        <el-tag v-else type="info" size="small" effect="plain">未翻译</el-tag>

        <TagChips
          v-if="row.tags && row.tags.length"
          :tags="row.tags"
          clickable
          class="item-tags"
          @tag-click="onTagChipClick"
        />

        <div class="item-foot">
          <span class="item-time" :title="row.updated_at">
            更新：{{ formatTime(row.updated_at) }}
          </span>
          <div @click.stop>
            <CopyButton compact :text="row.text_en" />
          </div>
        </div>
      </el-card>
    </div>

    <div class="pager">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="total"
        :page-sizes="[30, 60, 120]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onPageSizeChange"
      />
    </div>

    <el-drawer
      v-model="drawerOpen"
      :title="`编辑标签 - ${editingPrompt?.id ?? ''}`"
      direction="rtl"
      size="420px"
      :before-close="closeTagDrawer"
    >
      <div v-if="editingPrompt" class="drawer-body" v-loading="drawerLoading">
        <div class="drawer-prompt-preview">
          {{ preview(editingPrompt.text_en, 200) }}
        </div>

        <div class="drawer-section">
          <div class="section-title">
            已选标签 ({{ draftTagIds.size }})
          </div>
          <div v-if="draftTagIds.size === 0" class="empty-tip">尚未选择任何标签</div>
          <TagChips
            v-else
            :tags="Array.from(draftTagIds).map((id) => {
              const path = tagPathByIdFlat.get(id) || ''
              const name = path.split('/').pop() || path
              return { id, name, parent_id: null }
            })"
            closable
            @tag-close="(tag) => toggleDraftTag(tag.id)"
          />
        </div>

        <el-divider />

        <div class="drawer-section">
          <div class="section-title">从已有标签选择</div>
          <el-empty
            v-if="!drawerLoading && tagTree.categories.length === 0"
            description="还没有任何标签"
            :image-size="60"
          />
          <div
            v-for="cat in tagTree.categories"
            :key="cat.id"
            class="cat-block"
          >
            <div class="cat-name">
              <span>{{ cat.name }}</span>
              <span class="cat-count">{{ cat.usage_count }}</span>
            </div>
            <div class="leaf-list">
              <el-tag
                v-for="leaf in cat.children"
                :key="leaf.id"
                :type="draftTagIds.has(leaf.id) ? 'primary' : 'info'"
                :effect="draftTagIds.has(leaf.id) ? 'dark' : 'plain'"
                size="small"
                round
                class="leaf-chip"
                @click="toggleDraftTag(leaf.id)"
              >
                {{ leaf.name }} <span class="leaf-count">{{ leaf.usage_count }}</span>
              </el-tag>
            </div>
            <div class="new-leaf-row">
              <el-input
                v-model="newLeafNameByCat[cat.id]"
                size="small"
                placeholder="新建子标签..."
                clearable
                @keyup.enter="createLeafInline(cat.id)"
              >
                <template #append>
                  <el-button size="small" @click="createLeafInline(cat.id)">添加</el-button>
                </template>
              </el-input>
            </div>
          </div>
        </div>

        <div class="drawer-footer">
          <el-button @click="closeTagDrawer">取消</el-button>
          <el-button type="primary" :loading="drawerSaving" @click="saveDrawer">
            保存
          </el-button>
        </div>
      </div>
    </el-drawer>
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
  flex-wrap: nowrap;
  min-width: 0;
}

.toolbar .el-input {
  flex: 1 1 280px;
  min-width: 200px;
  max-width: 420px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 14px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-5);
  border-radius: 6px;
}

.filter-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #fff7e6, #ffe7ba);
  border: 1px solid #ffd591;
  border-radius: 8px;
  box-shadow: 0 2px 6px rgba(255, 154, 0, 0.12);
}

.bulk-info {
  font-size: 14px;
  color: #874d00;
}

.bulk-info strong {
  font-size: 18px;
  color: #d4380d;
  margin: 0 4px;
}

.bulk-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  min-height: 240px;
}

@media (min-width: 720px) {
  .grid { grid-template-columns: repeat(3, 1fr); }
}
@media (min-width: 960px) {
  .grid { grid-template-columns: repeat(4, 1fr); }
}
@media (min-width: 1240px) {
  .grid { grid-template-columns: repeat(5, 1fr); }
}
@media (min-width: 1560px) {
  .grid { grid-template-columns: repeat(6, 1fr); }
}

.item {
  display: flex;
  flex-direction: column;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  border: 2px solid transparent;
}

.item:hover {
  transform: translateY(-2px);
}

.item.selectable {
  cursor: pointer;
}

.item.is-selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.item :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  height: 100%;
}

.item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-id {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.item-actions {
  display: flex;
  gap: 4px;
}

.item-en {
  font-size: 14px;
  line-height: 1.5;
  color: var(--el-text-color-primary);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  flex: 1;
}

.item-zh {
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
  padding: 8px 10px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}

.item-tags {
  margin-top: 2px;
}

.item-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.item-time {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.pager {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.drawer-prompt-preview {
  font-size: 13px;
  padding: 10px 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  color: var(--el-text-color-secondary);
  word-break: break-word;
}

.drawer-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-regular);
}

.empty-tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  padding: 4px 0;
}

.cat-block {
  padding: 10px 12px;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}

.cat-name {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--el-color-primary);
}

.cat-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--el-text-color-placeholder);
}

.leaf-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.leaf-chip {
  cursor: pointer;
  transition: transform 0.12s ease;
}

.leaf-chip:hover {
  transform: translateY(-1px);
}

.leaf-count {
  margin-left: 4px;
  font-size: 10px;
  opacity: 0.7;
}

.new-leaf-row {
  margin-top: 8px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 0;
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 12px;
}
</style>