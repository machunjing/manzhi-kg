<script setup lang="ts">
defineProps<{ title: string; desc?: string }>()
</script>

<template>
  <div class="mz-page-head">
    <div>
      <div class="mz-page-title">{{ title }}</div>
      <div v-if="desc" class="mz-page-desc">{{ desc }}</div>
    </div>
    <div class="head-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
</style>
