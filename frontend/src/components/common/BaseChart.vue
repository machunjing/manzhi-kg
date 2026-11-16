<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  option: any
  height?: string | number
  loading?: boolean
  autoResize?: boolean
}>()

const emit = defineEmits<{ (e: 'chart-click', p: any): void; (e: 'ready', c: any): void }>()

const el = ref<HTMLDivElement>()

const cssHeight = computed(() => {
  const h = props.height
  if (h === undefined || h === null || h === '') return '280px'
  if (typeof h === 'number') return `${h}px`
  return /^\d+(\.\d+)?$/.test(String(h)) ? `${h}px` : String(h)
})
const chart = shallowRef<echarts.ECharts>()
let ro: ResizeObserver | null = null

function render() {
  if (!el.value) return
  if (!chart.value) {
    chart.value = echarts.init(el.value, undefined, { renderer: 'canvas' })
    chart.value.on('click', (p: any) => emit('chart-click', p))
    emit('ready', chart.value)
  }
  chart.value.setOption(props.option || {}, true)
  chart.value.resize()
}

onMounted(async () => {
  await nextTick()
  render()
  if (props.autoResize !== false && el.value) {
    ro = new ResizeObserver(() => chart.value?.resize())
    ro.observe(el.value)
  }
})

watch(
  () => props.option,
  () => render(),
  { deep: true }
)

onBeforeUnmount(() => {
  ro?.disconnect()
  chart.value?.dispose()
})

defineExpose({ chart })
</script>

<template>
  <div
    ref="el"
    v-loading="loading"
    class="mz-chart"
    :style="{ height: cssHeight }"
  />
</template>

<style scoped>
.mz-chart {
  width: 100%;
}
</style>
