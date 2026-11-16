<script setup lang="ts">
const props = defineProps<{ status: string }>()
const MAP: Record<string, string> = {
  已审核: 'success',
  已入库: 'success',
  已完成: 'success',
  启用: 'success',
  成功: 'success',
  待审核: 'warning',
  待清洗: 'warning',
  运行中: 'primary',
  已暂停: 'info',
  候选: 'info',
  已驳回: 'danger',
  失败: 'danger',
  禁用: 'danger'
}
</script>

<template>
  <el-tag :type="(MAP[props.status] as any) || 'info'" size="small" effect="light" round>{{ status }}</el-tag>
</template>
