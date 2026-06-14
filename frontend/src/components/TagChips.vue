<script setup lang="ts">
import type { TagOut } from '@/api/tags'

defineProps<{
  tags: TagOut[]
  clickable?: boolean
  size?: 'small' | 'default' | 'large'
  closable?: boolean
}>()

const emit = defineEmits<{
  'tag-click': [tag: TagOut]
  'tag-close': [tag: TagOut]
}>()
</script>

<template>
  <div v-if="tags && tags.length" class="tag-chips">
    <el-tag
      v-for="tag in tags"
      :key="tag.id"
      :size="size ?? 'small'"
      :closable="closable"
      :type="clickable ? 'info' : 'info'"
      :effect="clickable ? 'light' : 'plain'"
      :class="{ clickable }"
      round
      @click="clickable && emit('tag-click', tag)"
      @close="emit('tag-close', tag)"
    >
      {{ tag.name }}
    </el-tag>
  </div>
</template>

<style scoped>
.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.clickable {
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.25);
}
</style>