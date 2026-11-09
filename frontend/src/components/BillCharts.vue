<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])
const props=defineProps({stats:{type:Object, required:true}})
const trend=ref(null), pie=ref(null)
let lineChart, pieChart, observer
function render() {
  if(!lineChart) return
  const s=props.stats
  lineChart.setOption({animation:false,color:['#0d7a6f','#ef8a54'], tooltip:{trigger:'axis'}, legend:{top:0,data:['收入','支出']}, grid:{top:40,left:55,right:20,bottom:35}, xAxis:{type:'category',data:s.daily.map(d => d.date.slice(5))},yAxis:{type:'value'},series:[{name:'收入',type:'line',smooth:true,data:s.daily.map(d => d.income)},{name:'支出',type:'line',smooth:true,data:s.daily.map(d => d.expense)}]}, true)
  pieChart.setOption({animation:false,color:['#0d7a6f','#35b8a9','#ef8a54','#879cc8','#d5b16c'],tooltip:{trigger:'item'},legend:{bottom:0},series:[{type:'pie',radius:['38%','65%'],center:['50%','43%'],data:s.categories,label:{formatter:'{b}: {c}'}}]}, true)
}
watch(() => props.stats, render)
onMounted(() => { lineChart=echarts.init(trend.value); pieChart=echarts.init(pie.value); observer=new ResizeObserver(() => {lineChart.resize(); pieChart.resize()}); observer.observe(trend.value); observer.observe(pie.value); render() })
onBeforeUnmount(() => {observer?.disconnect(); lineChart?.dispose(); pieChart?.dispose()})
</script>
<template><div class="row g-3"><section class="col-lg-7"><div class="zh-card p-3"><h2 class="h6">每日收支趋势</h2><div ref="trend" class="zh-chart" aria-label="每日收支趋势图"></div></div></section><section class="col-lg-5"><div class="zh-card p-3"><h2 class="h6">支出分类</h2><p v-if="!stats.categories.length" class="text-muted small">本月没有支出记录。</p><div ref="pie" class="zh-chart" aria-label="支出分类图"></div></div></section></div></template>
<style>.zh-chart { height:300px; width:100%; }</style>
