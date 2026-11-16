<script setup lang="ts">
withDefaults(defineProps<{ text?: string; desc?: string; icon?: string; size?: number }>(), {
  text: '暂无数据',
  desc: '',
  icon: 'Box',
  size: 64
})
</script>

<template>
  <div class="empty">
    <div class="empty-icon">
      <el-icon :size="size"><component :is="icon" /></el-icon>
    </div>
    <div class="empty-text">{{ text }}</div>
    <div v-if="desc" class="empty-desc">{{ desc }}</div>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  padding: 46px 20px;
  text-align: center;
  color: var(--mz-text-sub);
}
.empty-icon {
  color: #d5dbe5;
  margin-bottom: 10px;
  display: flex;
  justify-content: center;
}
.empty-text {
  font-size: 13px;
  color: var(--mz-text-sub);
}
.empty-desc {
  margin-top: 6px;
  font-size: 12px;
  color: var(--mz-text-light);
}
</style>
