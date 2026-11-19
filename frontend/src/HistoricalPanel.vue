<script setup>
import { computed } from 'vue'
const props = defineProps({ datasets: { type: Array, default: () => [] }, selected: String, busy: Boolean, run: Object, mode: String })
const emit = defineEmits(['select', 'run', 'open'])
const dataset = computed(() => props.datasets.find(item => item.id === props.selected))
function utc(value) { return value == null ? '—' : new Date(Number(value)).toISOString().slice(0, 16).replace('T', ' ') }
function label(item) { return item.synthetic ? 'Eight-bar worked example · synthetic' : `${item.symbol} · recorded Yahoo session` }
</script>

<template>
  <section class="panel historical-panel" aria-labelledby="historical-title">
    <div class="panel-heading compact-heading"><h2 id="historical-title">Historical backtest</h2><span class="mini-tag">SEPARATE ACCOUNT</span></div>
    <div class="dataset-control"><label for="dataset-select">Choose a saved session</label><select id="dataset-select" :value="selected" :disabled="busy || !datasets.length" data-testid="dataset-select" @change="emit('select', $event.target.value)"><option v-if="!datasets.length" value="">Loading sessions…</option><option v-for="item in datasets" :key="item.id" :value="item.id">{{ label(item) }}</option></select></div>
    <div v-if="dataset" class="dataset-description"><span class="dataset-type" :class="dataset.synthetic ? 'warning' : ''">{{ dataset.synthetic ? 'Worked example · synthetic, not market data' : `${dataset.symbol} · recorded Yahoo data` }}</span><p>{{ dataset.bar_count }} candles <span class="dot-separator">·</span> {{ dataset.interval || 60 }}-second interval</p><details class="quiet-details dataset-details"><summary>Session details</summary><p class="mono">{{ utc(dataset.start_ms) }} → {{ utc(dataset.end_ms) }} UTC</p><p>{{ dataset.provenance }}</p></details></div>
    <button class="primary-button full-width" :disabled="busy || !dataset || !dataset.bar_count" :aria-busy="busy" data-testid="run-backtest" @click="emit('run')">{{ busy ? 'Running backtest…' : 'Run backtest' }}<span v-if="!busy" aria-hidden="true">→</span></button>
    <div v-if="run" class="backtest-run-info"><details class="quiet-details"><summary>Saved run details</summary><strong class="mono" data-testid="backtest-id">{{ run.id }}</strong></details><button v-if="mode !== 'historical'" class="quiet-button" @click="emit('open')">View run</button><span v-else class="mini-tag">HISTORICAL</span></div>
    <p class="microcopy">Orders fill from the next bar’s open. Any position still held at the end is marked to price, not sold.</p>
  </section>
</template>
