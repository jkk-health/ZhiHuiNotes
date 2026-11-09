<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { today } from '../utils/dates'
import AppDialog from '../components/AppDialog.vue'
import BillCharts from '../components/BillCharts.vue'
import { useUnsaved } from '../composables/useUnsaved'
const month=ref(today().slice(0,7)), rows=ref([]), stats=ref(null), error=ref(''), busy=ref(false), editing=ref(null), dialog=ref(null)
const empty=() => ({type:'支', category:'餐饮', amount:'', bill_date:month.value === today().slice(0,7) ? today() : month.value+'-01', remark:''})
const form=ref(empty()), baseline=ref(JSON.stringify(form.value)), dirty=computed(() => JSON.stringify(form.value) !== baseline.value)
const clear=() => { editing.value=null; form.value=empty(); baseline.value=JSON.stringify(form.value) }
const check=useUnsaved(dirty, dialog, save, () => {baseline.value=JSON.stringify(form.value)})
let sequence=0
const money=value => Number(value).toFixed(2)
async function run(work) { error.value=''; try { await work() } catch(e) { error.value=e.message } }
async function load() { const id=++sequence; const [list, totals]=await Promise.all([api.get(`/api/bills?month=${month.value}`),api.get(`/api/bills/monthly?month=${month.value}`)]); if(id === sequence) {rows.value=list; stats.value=totals} }
async function save() {
  if(busy.value) return false
  busy.value=true; let ok=false
  await run(async () => { const data={...form.value}; if(editing.value) await api.put(`/api/bills/${editing.value}`,data); else await api.post('/api/bills',data); clear(); await load(); ok=true })
  busy.value=false; return ok
}
async function edit(row) { if(!(await check())) return; editing.value=row.id; form.value={type:row.type,category:row.category,amount:String(row.amount),bill_date:row.bill_date,remark:row.remark}; baseline.value=JSON.stringify(form.value) }
async function cancel() {if(await check()) clear()}
async function remove(row) {if(!(await dialog.value.open({title:'删除收支记录',message:`删除 ${row.bill_date} 的 ${money(row.amount)} 元记录？`}))) return; await run(async () => {await api.del(`/api/bills/${row.id}`); if(editing.value === row.id) clear(); await load()})}
onMounted(() => run(load))
</script>
<template>
  <div class="zh-module p-4">
    <div class="d-flex justify-content-between align-items-center mb-3"><div><h1 class="h4">轻记账</h1><p class="text-muted mb-0">记录日常收支，查看每月变化。</p></div><input v-model="month" type="month" class="form-control w-auto" aria-label="统计月份" @change="run(load)" /></div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="stats" class="row g-3 mb-3"><div v-for="(value,label) in {'本月收入':stats.income,'本月支出':stats.expense,'本月结余':stats.balance}" :key="label" class="col-md-4"><div class="zh-card p-3"><div class="small text-muted">{{ label }}</div><strong class="h3 d-block mt-2 mb-0">¥ {{ money(value) }}</strong></div></div></div>
    <form class="zh-card p-3 mb-3" @submit.prevent="save"><h2 class="h6">{{ editing ? '编辑记录' : '新增记录' }}</h2><div class="row g-2"><div class="col-md-2"><select v-model="form.type" class="form-select" aria-label="收支类型"><option>支</option><option>收</option></select></div><div class="col-md-2"><input v-model="form.category" class="form-control" placeholder="分类" aria-label="收支分类" maxlength="50" required /></div><div class="col-md-2"><input v-model="form.amount" type="number" min="0.01" max="99999999.99" step="0.01" class="form-control" placeholder="金额" aria-label="金额" required /></div><div class="col-md-3"><input v-model="form.bill_date" type="date" class="form-control" aria-label="账目日期" required /></div><div class="col-md-3"><input v-model="form.remark" class="form-control" placeholder="备注（可选）" aria-label="备注" maxlength="200" /></div></div><div class="d-flex gap-2 mt-3"><button class="btn btn-primary" :disabled="busy">{{ busy ? '保存中…' : editing ? '保存记录' : '新增记录' }}</button><button v-if="editing || dirty" type="button" class="btn btn-outline-secondary" @click="cancel">取消编辑</button></div></form>
    <BillCharts v-if="stats" :stats="stats" />
    <div class="zh-card p-3 mt-3"><h2 class="h6">本月明细</h2><div class="table-responsive"><table class="table align-middle"><thead><tr><th>日期</th><th>类型</th><th>分类</th><th>金额</th><th>备注</th><th>操作</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td>{{ row.bill_date }}</td><td>{{ row.type }}</td><td>{{ row.category }}</td><td :class="row.type === '收' ? 'text-success' : ''">{{ row.type === '收' ? '+' : '-' }}{{ money(row.amount) }}</td><td>{{ row.remark }}</td><td><div class="d-flex gap-2"><button class="btn btn-sm btn-outline-secondary" @click="edit(row)">编辑</button><button class="btn btn-sm btn-outline-danger" @click="remove(row)">删除</button></div></td></tr></tbody></table></div><p v-if="!rows.length" class="text-muted text-center">本月没有收支记录。</p></div>
    <AppDialog ref="dialog" />
  </div>
</template>
