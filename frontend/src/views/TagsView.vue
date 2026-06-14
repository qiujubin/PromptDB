<script setup lang="ts">
import { computed, onMounted, ref, type Directive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, EditPen, Delete, MagicStick, Refresh } from '@element-plus/icons-vue'
import {
  bulkAutoTag,
  createTag,
  deleteTag,
  fetchTags,
  updateTag,
  type TagTreeNode,
  type TagTreeResponse,
} from '@/api/tags'

const router = useRouter()

const vFocus: Directive = {
  mounted(el) {
    const input = (el as HTMLElement).querySelector('input')
    if (input) {
      ;(input as HTMLInputElement).focus()
      ;(input as HTMLInputElement).select()
    }
  },
}

const tree = ref<TagTreeResponse>({ categories: [] })
const loading = ref(false)
const bulkWorking = ref(false)

const editingCatId = ref<number | null>(null)
const editingLeafId = ref<number | null>(null)
const editDraft = ref<string>('')

const newCategoryDialog = ref(false)
const newCategoryName = ref('')

const newLeafDialog = ref(false)
const newLeafName = ref('')
const newLeafCategoryId = ref<number | null>(null)

const totalLeaves = computed(() =>
  tree.value.categories.reduce((sum, c) => sum + c.children.length, 0),
)

const totalUsage = computed(() =>
  tree.value.categories.reduce((sum, c) => sum + c.usage_count, 0),
)

async function reload() {
  loading.value = true
  try {
    tree.value = await fetchTags()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

async function onBulkAutoTag() {
  try {
    await ElMessageBox.confirm(
      '将为所有未打标签的提示词自动调用 AI 打标，可能需要数十秒。是否继续？',
      '批量补打标签',
      { type: 'info' },
    )
  } catch {
    return
  }
  bulkWorking.value = true
  try {
    const resp = await bulkAutoTag()
    if (resp.scanned === 0) {
      ElMessage.info('所有提示词都已有标签，无需补打')
    } else {
      ElMessage.success(
        `扫描 ${resp.scanned} 条，成功 ${resp.tagged} 条，失败 ${resp.failed} 条`,
      )
    }
    reload()
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    bulkWorking.value = false
  }
}

async function submitNewCategory() {
  const name = newCategoryName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分类名')
    return
  }
  try {
    await createTag({ name, parent_id: null })
    ElMessage.success(`已创建分类「${name}」`)
    newCategoryName.value = ''
    newCategoryDialog.value = false
    reload()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function submitNewLeaf() {
  const name = newLeafName.value.trim()
  if (!name) {
    ElMessage.warning('请输入子标签名')
    return
  }
  if (newLeafCategoryId.value === null) {
    ElMessage.warning('请选择分类')
    return
  }
  try {
    await createTag({ name, parent_id: newLeafCategoryId.value })
    ElMessage.success(`已创建子标签「${name}」`)
    newLeafName.value = ''
    newLeafCategoryId.value = null
    newLeafDialog.value = false
    reload()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function openNewLeafDialog(catId: number) {
  newLeafCategoryId.value = catId
  newLeafName.value = ''
  newLeafDialog.value = true
}

function startEditCat(cat: TagTreeNode) {
  editingCatId.value = cat.id
  editingLeafId.value = null
  editDraft.value = cat.name
}

function startEditLeaf(leaf: TagTreeNode) {
  editingLeafId.value = leaf.id
  editingCatId.value = null
  editDraft.value = leaf.name
}

async function commitEdit() {
  const name = editDraft.value.trim()
  if (!name) {
    cancelEdit()
    return
  }
  try {
    if (editingCatId.value !== null) {
      await updateTag(editingCatId.value, { name })
      ElMessage.success('已更新')
    } else if (editingLeafId.value !== null) {
      await updateTag(editingLeafId.value, { name })
      ElMessage.success('已更新')
    }
    cancelEdit()
    reload()
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

function cancelEdit() {
  editingCatId.value = null
  editingLeafId.value = null
  editDraft.value = ''
}

async function onDeleteCat(cat: TagTreeNode) {
  if (cat.children.length > 0) {
    ElMessage.warning('该分类下还有子标签，请先删除子标签')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除分类「${cat.name}」？相关提示词关联也会一并解除。`,
      '删除分类',
      { type: 'warning' },
    )
    await deleteTag(cat.id)
    ElMessage.success('已删除')
    reload()
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  }
}

async function onDeleteLeaf(leaf: TagTreeNode) {
  try {
    await ElMessageBox.confirm(
      `确认删除子标签「${leaf.name}」？`,
      '删除子标签',
      { type: 'warning' },
    )
    await deleteTag(leaf.id)
    ElMessage.success('已删除')
    reload()
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  }
}

function viewLeafInLibrary(leaf: TagTreeNode) {
  if (leaf.usage_count === 0) {
    ElMessage.info(`标签「${leaf.name}」暂无提示词引用`)
    return
  }
  router.push({ name: 'library', query: { tag_id: String(leaf.id) } })
}

let leafClickTimer: number | null = null

function onLeafClick(leaf: TagTreeNode) {
  if (leafClickTimer !== null) clearTimeout(leafClickTimer)
  leafClickTimer = window.setTimeout(() => {
    leafClickTimer = null
    viewLeafInLibrary(leaf)
  }, 250)
}

function onLeafDblClick(leaf: TagTreeNode) {
  if (leafClickTimer !== null) {
    clearTimeout(leafClickTimer)
    leafClickTimer = null
  }
  startEditLeaf(leaf)
}

onMounted(reload)
</script>

<template>
  <div class="page">
    <div class="header">
      <div>
        <div class="title">标签管理</div>
        <div class="subtitle">
          共 {{ tree.categories.length }} 个分类 / {{ totalLeaves }} 个子标签 / 被引用 {{ totalUsage }} 次
        </div>
      </div>
      <div class="toolbar">
        <el-button :icon="Refresh" @click="reload">刷新</el-button>
        <el-button
          type="primary"
          :icon="MagicStick"
          :loading="bulkWorking"
          @click="onBulkAutoTag"
        >
          批量补打标签
        </el-button>
        <el-button type="success" :icon="Plus" @click="newCategoryDialog = true">
          新建分类
        </el-button>
      </div>
    </div>

    <el-empty
      v-if="!loading && tree.categories.length === 0"
      description="还没有任何标签，去保存一些提示词让 AI 自动创建吧"
    />

    <div v-loading="loading" class="cat-list">
      <div v-for="cat in tree.categories" :key="cat.id" class="cat-card">
        <div class="cat-head">
          <div class="cat-title">
            <el-input
              v-if="editingCatId === cat.id"
              v-model="editDraft"
              size="default"
              style="max-width: 220px"
              @blur="commitEdit"
              @keyup.enter="commitEdit"
              @keyup.esc="cancelEdit"
              v-focus
            />
            <span v-else class="cat-name" @dblclick="startEditCat(cat)">{{ cat.name }}</span>
            <el-tag size="small" type="info" effect="plain">{{ cat.usage_count }} 次引用</el-tag>
          </div>
          <div class="cat-actions">
            <el-tooltip content="重命名" placement="top">
              <el-button :icon="EditPen" size="small" link @click="startEditCat(cat)" />
            </el-tooltip>
            <el-tooltip content="新建子标签" placement="top">
              <el-button :icon="Plus" size="small" link type="primary" @click="openNewLeafDialog(cat.id)" />
            </el-tooltip>
            <el-tooltip content="删除分类" placement="top">
              <el-button :icon="Delete" size="small" link type="danger" @click="onDeleteCat(cat)" />
            </el-tooltip>
          </div>
        </div>

        <div v-if="cat.children.length === 0" class="cat-empty">
          该分类下暂无子标签
        </div>

        <div v-else class="leaf-grid">
          <div v-for="leaf in cat.children" :key="leaf.id" class="leaf-item">
            <el-input
              v-if="editingLeafId === leaf.id"
              v-model="editDraft"
              size="small"
              @blur="commitEdit"
              @keyup.enter="commitEdit"
              @keyup.esc="cancelEdit"
              v-focus
            />
            <span
              v-else
              class="leaf-name"
              :class="{ 'leaf-name-clickable': leaf.usage_count > 0 }"
              :title="leaf.usage_count > 0 ? '点击查看使用此标签的提示词' : '尚无提示词引用'"
              @click="onLeafClick(leaf)"
              @dblclick="onLeafDblClick(leaf)"
            >
              {{ leaf.name }}
            </span>
            <el-tooltip
              v-if="leaf.usage_count > 0"
              content="点击查看使用此标签的提示词"
              placement="top"
            >
              <span class="leaf-count leaf-count-clickable" @click="onLeafClick(leaf)">
                {{ leaf.usage_count }}
              </span>
            </el-tooltip>
            <span v-else class="leaf-count">{{ leaf.usage_count }}</span>
            <el-tooltip content="重命名" placement="top">
              <el-button :icon="EditPen" size="small" link @click="startEditLeaf(leaf)" />
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button :icon="Delete" size="small" link type="danger" @click="onDeleteLeaf(leaf)" />
            </el-tooltip>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="newCategoryDialog" title="新建分类" width="420px">
      <el-form @submit.prevent="submitNewCategory">
        <el-form-item label="分类名">
          <el-input
            v-model="newCategoryName"
            placeholder="例如：姿势、表情、背景"
            maxlength="64"
            show-word-limit
            @keyup.enter="submitNewCategory"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newCategoryDialog = false">取消</el-button>
        <el-button type="primary" @click="submitNewCategory">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="newLeafDialog" title="新建子标签" width="420px">
      <el-form @submit.prevent="submitNewLeaf">
        <el-form-item label="所属分类">
          <el-select v-model="newLeafCategoryId" placeholder="选择分类" style="width: 100%">
            <el-option
              v-for="cat in tree.categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="子标签名">
          <el-input
            v-model="newLeafName"
            placeholder="例如：手部姿势、夜景"
            maxlength="64"
            show-word-limit
            @keyup.enter="submitNewLeaf"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newLeafDialog = false">取消</el-button>
        <el-button type="primary" @click="submitNewLeaf">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}

.header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.title {
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.cat-card {
  padding: 14px 16px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.cat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.cat-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cat-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-color-primary);
  cursor: text;
  padding: 2px 4px;
  border-radius: 4px;
}

.cat-name:hover {
  background: var(--el-fill-color-light);
}

.cat-actions {
  display: flex;
  gap: 4px;
}

.cat-empty {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  padding: 8px 0;
}

.leaf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
}

.leaf-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  transition: border-color 0.15s ease;
}

.leaf-item:hover {
  border-color: var(--el-color-primary-light-5);
}

.leaf-name {
  flex: 1;
  font-size: 13px;
  cursor: text;
}

.leaf-name-clickable {
  cursor: pointer;
  padding: 1px 4px;
  margin: -1px -4px;
  border-radius: 4px;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.leaf-name-clickable:hover {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.leaf-count {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color-light);
  padding: 1px 6px;
  border-radius: 8px;
}

.leaf-count-clickable {
  cursor: pointer;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  transition: background-color 0.12s ease;
}

.leaf-count-clickable:hover {
  background: var(--el-color-primary-light-7);
}
</style>