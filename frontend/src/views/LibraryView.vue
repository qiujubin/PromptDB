<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { deleteLibraryItem, fetchLibrary } from '@/api/library'
import type { LibraryItem } from '@/api/prompts'
import CopyButton from '@/components/CopyButton.vue'

const items = ref<LibraryItem[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')

const pagination = reactive({ page: 1, pageSize: 20 })

async function reload() {
  loading.value = true
  try {
    const resp = await fetchLibrary({
      page: pagination.page,
      page_size: pagination.pageSize,
      search: search.value.trim() || undefined,
    })
    items.value = resp.items
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

async function onDelete(row: LibraryItem) {
  try {
    await ElMessageBox.confirm(
      `确认删除 "${row.text_en}" ？此操作不可撤销。`,
      '删除提示词',
      { type: 'warning' },
    )
    await deleteLibraryItem(row.id)
    ElMessage.success('已删除')
    reload()
  } catch (e) {
    if ((e as Error).message !== 'cancel') {
      ElMessage.error((e as Error).message)
    }
  }
}

function formatTime(s: string | null) {
  if (!s) return '-'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}

onMounted(reload)
</script>

<template>
  <el-card class="page" shadow="never">
    <template #header>
      <div class="title">提示词库（按使用次数降序）</div>
    </template>

    <div class="toolbar">
      <el-input
        v-model="search"
        placeholder="搜索英文片段..."
        clearable
        style="max-width: 360px"
        @keyup.enter="onSearch"
      >
        <template #append>
          <el-button :icon="Search" @click="onSearch" />
        </template>
      </el-input>
      <el-button :icon="Refresh" @click="reload">刷新</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="items"
      stripe
      style="width: 100%"
      empty-text="暂无数据"
    >
      <el-table-column prop="id" label="ID" width="72" />
      <el-table-column label="英文片段" min-width="280">
        <template #default="{ row }">
          <el-tooltip :content="row.text_en" placement="top" :show-after="300">
            <span class="cell-ellipsis">{{ row.text_en }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="中文翻译" min-width="200">
        <template #default="{ row }">
          <span v-if="row.text_zh">{{ row.text_zh }}</span>
          <el-tag v-else type="info" size="small">未翻译</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="usage_count" label="使用次数" width="120" sortable>
        <template #default="{ row }">
          <el-tag type="primary">{{ row.usage_count }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="180">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <CopyButton compact :text="row.text_en" />
          <el-button type="danger" size="small" link @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="pagination.page"
        :page-size="pagination.pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, prev, pager, next, jumper"
        @current-change="onPageChange"
      />
    </div>
  </el-card>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.cell-ellipsis {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>