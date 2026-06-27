<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface ChipItem {
  text_en: string
  text_zh?: string | null
}

const props = withDefaults(
  defineProps<{
    items: ChipItem[]
    mode?: 'plain' | 'rich'
  }>(),
  { mode: 'plain' },
)

const selected = ref<Set<number>>(new Set())

watch(
  () => props.items,
  () => {
    selected.value = new Set()
  },
)

function toggle(index: number) {
  const next = new Set(selected.value)
  if (next.has(index)) next.delete(index)
  else next.add(index)
  selected.value = next
}

const copyText = computed(() => {
  const picked = props.items.filter((_, i) => selected.value.has(i))
  const source = picked.length ? picked : props.items
  return source.map(it => it.text_en).join(', ')
})

defineExpose({
  copyText,
  selectedCount: computed(() => selected.value.size),
  clear: () => {
    selected.value = new Set()
  },
})
</script>

<template>
  <div v-if="items.length" class="chip-cloud">
    <div
      v-for="(it, i) in items"
      :key="i"
      class="chip"
      :class="{
        'is-selected': selected.has(i),
        'no-zh': mode === 'rich' && !it.text_zh,
      }"
      @click="toggle(i)"
    >
      <span class="en">{{ it.text_en }}</span>
      <span v-if="mode === 'rich'" class="zh">{{ it.text_zh || '翻译失败' }}</span>
    </div>
  </div>
</template>

<style scoped>
.chip-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  display: inline-flex;
  flex-direction: column;
  max-width: 260px;
  padding: 6px 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease, border-color 0.15s ease;
  user-select: none;
}
.chip:hover {
  transform: translateY(-1px);
  background: var(--el-color-primary-light-9);
}
.chip.is-selected {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-5) inset;
}
.en {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  word-break: break-word;
}
.zh {
  margin-top: 2px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  word-break: break-word;
}
.chip.no-zh .zh {
  color: var(--el-color-danger);
  font-style: italic;
}
</style>