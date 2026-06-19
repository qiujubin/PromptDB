<script setup lang="ts">
defineOptions({ name: 'RecordsView' })
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Search,
  Refresh,
  Star,
  StarFilled,
  PriceTag,
} from '@element-plus/icons-vue'
import { fetchRecords, type RecordOut } from '@/api/records'
import { fetchTags, type TagTreeResponse } from '@/api/tags'
import RecordCard from '@/components/RecordCard.vue'
import RecordEditorDialog from '@/components/RecordEditorDialog.vue'

const records = ref<RecordOut[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const minRating = ref<number | null>(null)
const favoritesOnly = ref(false)
const tagTree = ref<TagTreeResponse>({ categories: [] })
const selectedCategoryId = ref<number | null>(null)
const selectedLeafId = ref<number | null>(null)

const pagination = reactive({ page: 1, pageSize: 30 })

const route = useRoute()
const router = useRouter()

const dialogOpen = ref(false)
const editingRecord = ref<RecordOut | null>(null)

const availableLeaves = computed(() => {
  if (selectedCategoryId.value === null) return []
  return (
    tagTree.value.categories.find((c) => c.id === selectedCategoryId.value)
      ?.children ?? []
  )
})

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
    const tagId = selectedLeafId.value ?? null
    const resp = await fetchRecords({
      page: pagination.page,
      page_size: pagination.pageSize,
      search: search.value.trim() || undefined,
      min_rating: minRating.value ?? undefined,
      favorites_only: favoritesOnly.value || undefined,
      tag_id: tagId ?? undefined,
      sort: 'favorites_first',
    })
    records.value = resp.items
    total.value = resp.total
  } catch (e) {
    ElMessage.error((e as Error).message)
  } finally {
    loading.value = false
  }
}

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
function onCategoryChange() {
  selectedLeafId.value = null
  pagination.page = 1
  applyTagFilterToRoute()
  reload()
}
function onLeafChange() {
  pagination.page = 1
  applyTagFilterToRoute()
  reload()
}
function clearTagFilter() {
  selectedCategoryId.value = null
  selectedLeafId.value = null
  pagination.page = 1
  applyTagFilterToRoute()
  reload()
}
function applyTagFilterToRoute() {
  const next = { ...route.query }
  if (selectedCategoryId.value !== null) {
    next.tag_category = String(selectedCategoryId.value)
  } else {
    delete next.tag_category
  }
  if (selectedLeafId.value !== null) {
    next.tag_leaf = String(selectedLeafId.value)
  } else {
    delete next.tag_leaf
  }
  router.replace({ name: 'records', query: next })
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
}

const activeFilterPath = computed(() => {
  if (selectedLeafId.value !== null) {
    for (const c of tagTree.value.categories) {
      for (const l of c.children) {
        if (l.id === selectedLeafId.value) return `${c.name} / ${l.name}`
      }
    }
  }
  if (selectedCategoryId.value !== null) {
    return (
      tagTree.value.categories.find((c) => c.id === selectedCategoryId.value)
        ?.name ?? ''
    )
  }
  return ''
})

function openEdit(rec: RecordOut) {
  editingRecord.value = rec
  dialogOpen.value = true
}

function onDialogSaved() {
  reload()
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
  await reload()
})
</script>

<template>
  <div class="page">
    <div class="header">
      <div class="title">生成历史记录</div>
      <div class="toolbar">
        <el-input
          v-model="search"
          placeholder="搜索中/英文关键词..."
          clearable
          @keyup.enter="onSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="onSearch" />
          </template>
        </el-input>

        <el-select
          v-model="minRating"
          placeholder="最低评分"
          clearable
          style="width: 130px"
          @change="() => { pagination.page = 1; reload() }"
        >
          <el-option :value="0" label="不限" />
          <el-option :value="1" label="≥ 1 星" />
          <el-option :value="2" label="≥ 2 星" />
          <el-option :value="3" label="≥ 3 星" />
          <el-option :value="4" label="≥ 4 星" />
          <el-option :value="5" label="5 星" />
        </el-select>

        <el-button
          :type="favoritesOnly ? 'warning' : 'default'"
          :icon="favoritesOnly ? StarFilled : Star"
          @click="favoritesOnly = !favoritesOnly; pagination.page = 1; reload()"
        >
          只看收藏
        </el-button>

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
      </div>
    </div>

    <div v-if="activeFilterPath" class="filter-bar">
      <span class="filter-label">当前筛选：</span>
      <el-tag type="primary" effect="dark" round :closable="true" @close="clearTagFilter">
        <el-icon><PriceTag /></el-icon>
        <span style="margin-left: 4px">{{ activeFilterPath }}</span>
      </el-tag>
    </div>

    <div v-loading="loading" class="grid">
      <el-empty v-if="!loading && records.length === 0" description="暂无历史记录" />
      <RecordCard
        v-for="r in records"
        :key="r.id"
        :record="r"
        @changed="reload"
        @edit="openEdit"
      />
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

    <RecordEditorDialog
      v-model="dialogOpen"
      :record="editingRecord"
      @saved="onDialogSaved"
    />
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
  flex: 1 1 240px;
  min-width: 200px;
  max-width: 360px;
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
@media (min-width: 720px) { .grid { column-count: 2; } }
@media (min-width: 1080px) { .grid { column-count: 3; } }
@media (min-width: 1500px) { .grid { column-count: 4; } }

.pager {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}
</style>
