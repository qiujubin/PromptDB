<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const activeIndex = computed(() => route.path)

const menus = [
  { path: '/generate', label: '生成提示词' },
  { path: '/saver', label: '保存提示词' },
  { path: '/library', label: '提示词库' },
]

function navigate(path: string) {
  if (path !== route.path) router.push(path)
}
</script>

<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="brand">AI 绘图提示词助手</div>
      <el-menu
        mode="horizontal"
        :default-active="activeIndex"
        :ellipsis="false"
        @select="navigate"
      >
        <el-menu-item
          v-for="m in menus"
          :key="m.path"
          :index="m.path"
        >
          {{ m.label }}
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  gap: 32px;
  border-bottom: 1px solid var(--el-border-color-light);
  padding: 0 24px;
}
.brand {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-color-primary);
  white-space: nowrap;
}
.main {
  padding: 24px;
  background: var(--el-bg-color-page);
}
:deep(.el-menu) {
  border-bottom: none;
}
</style>