<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  desc?: string
  icon?: string
  value?: string | number
  unit?: string
  trend?: string
  trendType?: 'up' | 'down' | 'flat'
  color?: string
  hint?: string
}>(), { value: '—', unit: '', color: '#2563EB' })
</script>

<template>
  <div class="stat-card">
    <div class="stat-main">
      <div class="stat-label">
        {{ title }}
        <el-tooltip v-if="hint" :content="hint" placement="top">
          <el-icon class="stat-hint"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
      <div class="stat-value">
        {{ value }}<span v-if="unit" class="stat-unit">{{ unit }}</span>
      </div>
      <div v-if="trend" class="stat-trend" :class="'is-' + (trendType || 'flat')">
        <el-icon v-if="trendType === 'up'"><CaretTop /></el-icon>
        <el-icon v-else-if="trendType === 'down'"><CaretBottom /></el-icon>
        <span>{{ trend }}</span>
      </div>
    </div>
    <div class="stat-icon" :style="{ background: (color || '#2563EB') + '14', color: color || '#2563EB' }">
      <el-icon :size="20"><component :is="icon || 'DataLine'" /></el-icon>
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  background: #fff;
  border: 1px solid var(--mz-border);
  border-radius: var(--mz-radius);
  padding: 16px 18px;
  box-shadow: var(--mz-shadow);
  transition: box-shadow 0.18s, transform 0.18s;
  min-height: 96px;
}
.stat-card:hover {
  box-shadow: var(--mz-shadow-hover);
  transform: translateY(-1px);
}
.stat-label {
  font-size: 12.5px;
  color: var(--mz-text-sub);
  display: flex;
  align-items: center;
  gap: 4px;
}
.stat-hint {
  font-size: 12px;
  color: #c0c6d0;
  cursor: help;
}
.stat-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 600;
  line-height: 1.1;
  color: #111827;
  letter-spacing: -0.4px;
  font-variant-numeric: tabular-nums;
}
.stat-unit {
  font-size: 12px;
  font-weight: 400;
  color: var(--mz-text-sub);
  margin-left: 4px;
}
.stat-trend {
  margin-top: 8px;
  font-size: 11.5px;
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--mz-text-light);
}
.stat-trend.is-up {
  color: var(--mz-success);
}
.stat-trend.is-down {
  color: var(--mz-danger);
}
.stat-icon {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 38px;
}
</style>
