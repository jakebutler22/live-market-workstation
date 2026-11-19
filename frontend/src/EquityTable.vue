<script setup>
defineProps({ result: Object, mode: String })
function number(value) { return value == null ? '—' : Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function utc(value) { return value == null ? '—' : new Date(Number(value)).toISOString().slice(0, 19).replace('T', ' ') }
</script>

<template>
  <div class="table-scroll equity-table" data-testid="equity-table"><table><caption class="sr-only">Simulated account equity through time in chronological order, including cash, position and both realized and unrealized profit and loss. Currency follows the selected account.</caption><thead><tr><th>Mark source · UTC</th><th>Equity</th><th>Cash</th><th>Shares</th><th>Mark</th><th>Realized</th><th>Unrealized</th><th>Fees</th></tr></thead><tbody><tr v-for="(point, index) in result?.equity || []" :key="`${point.time}-${index}`"><td>{{ utc(point.source_ms) }}</td><td>{{ number(point.equity) }}</td><td>{{ number(point.cash) }}</td><td>{{ point.quantity }}</td><td>{{ number(point.mark) }}</td><td>{{ number(point.realized_pnl) }}</td><td>{{ number(point.unrealized_pnl) }}</td><td>{{ number(point.fees) }}</td></tr><tr v-if="!result?.equity?.length"><td colspan="8" class="table-empty">{{ mode === 'replay' ? 'Replay is indicator-only. No simulated account history is created.' : 'Equity history appears as confirmed observations are processed.' }}</td></tr></tbody></table></div>
</template>
