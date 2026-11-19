<script setup>
import { computed } from 'vue'

const props = defineProps({ result: Object, point: Object, mode: String })
const config = computed(() => props.result?.config || {})
const account = computed(() => props.result?.account || {})
const summary = computed(() => props.result?.summary || {})
const fast = computed(() => config.value.fast ?? config.value.fast_window ?? 5)
const slow = computed(() => config.value.slow ?? config.value.slow_window ?? 20)
const paper = computed(() => props.mode !== 'replay')
const currency = computed(() => props.result?.dataset?.currency || (account.value.currency && account.value.currency !== 'quote currency' ? account.value.currency : 'AUD'))
function number(value, precision = 2) { return value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('en-US', { minimumFractionDigits: precision, maximumFractionDigits: precision }) }
function signed(value) { return value == null ? '—' : `${Number(value) > 0 ? '+' : ''}${number(value)}` }
function tone(value) { return Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : 'neutral' }
function utc(value) { return value == null ? 'Unknown' : new Date(Number(value)).toISOString().slice(0, 19).replace('T', ' ') }
</script>

<template>
  <section class="panel strategy-panel" aria-labelledby="strategy-title" data-testid="strategy-panel">
    <div class="panel-heading compact-heading"><h2 id="strategy-title">SMA crossover</h2><span class="mini-tag simulated-tag">{{ paper ? 'SIMULATED' : 'REPLAY · INDICATORS' }}</span></div>
    <div class="strategy-policy"><strong>{{ fast }} / {{ slow }} minute averages</strong><span>Long or flat</span></div>
    <div class="indicator-values" aria-label="Selected candle indicator values">
      <div><span><i class="line-key fast-line"></i>Fast · SMA {{ fast }}</span><strong class="mono" data-testid="inspected-fast" :title="point?.fast_exact">{{ point?.fast == null ? 'Warming up' : number(point.fast, 4) }}</strong></div>
      <div><span><i class="line-key slow-line"></i>Slow · SMA {{ slow }}</span><strong class="mono" data-testid="inspected-slow" :title="point?.slow_exact">{{ point?.slow == null ? 'Warming up' : number(point.slow, 4) }}</strong></div>
    </div>
    <p class="strategy-basis">{{ mode === 'live' ? 'Forming candles are excluded. Signals confirm on the close of a sampled quote candle.' : mode === 'replay' ? 'Follow recorded candles and indicators. Replay places no orders and leaves the paper account unchanged.' : 'Signals use completed bars. Orders fill at a later bar’s open; any final position remains marked, not sold.' }}</p>
    <template v-if="paper">
      <div class="paper-equity" data-testid="paper-account"><div><span>{{ mode === 'live' ? 'Paper account' : 'Backtest account' }} · {{ currency }}</span><strong class="mono" data-testid="account-equity">{{ number(account.equity) }}</strong></div><div class="paper-return mono" :class="tone(summary.total_pnl)"><span>Net P&amp;L</span>{{ signed(summary.total_pnl) }}<small>{{ signed(summary.return_pct) }}%</small></div></div>
      <dl class="info-list account-list"><div><dt>Cash / {{ currency }}</dt><dd class="mono" data-testid="account-cash">{{ number(account.cash) }}</dd></div><div><dt>Position / shares</dt><dd class="mono" data-testid="account-quantity">{{ number(account.quantity, 0) }}</dd></div><div><dt>Realized P&amp;L</dt><dd class="mono" :class="tone(account.realized_pnl)">{{ signed(account.realized_pnl) }}</dd></div><div><dt>Unrealized P&amp;L</dt><dd class="mono" :class="tone(account.unrealized_pnl)">{{ signed(account.unrealized_pnl) }}</dd></div><div><dt>Fees paid / {{ currency }}</dt><dd class="mono">{{ number(account.fees) }}</dd></div></dl>
      <p class="account-mark">Marked at <strong class="mono">{{ number(account.mark) }}</strong><span class="mono">{{ utc(account.mark_source_ms ?? account.mark_ms) }} UTC</span></p>
      <p v-if="account.mark_source" class="mark-source">{{ account.mark_source }}</p>
      <details class="quiet-details strategy-details"><summary>Account rules &amp; records</summary><div class="paper-rules"><span>Starting cash <strong class="mono">{{ number(config.starting_cash ?? 10000) }}</strong></span><span>Fixed quantity <strong class="mono">{{ config.quantity ?? 10 }}</strong></span><span>Fee / fill <strong class="mono">{{ number(config.fee ?? 1) }} {{ currency }}</strong></span><span>Slippage <strong class="mono">{{ number(config.slippage_bps ?? 0, 0) }} bps</strong></span></div><p class="microcopy">{{ mode === 'live' ? 'Original quote inputs stay fixed when Yahoo later revises a candle. The paper ledger is saved locally; no broker is connected.' : 'This backtest has its own account. The live paper ledger is unchanged.' }}</p><div v-if="account.mark_source" class="mark-provenance" data-testid="mark-provenance"><span>Mark source and receipt</span><p>{{ account.mark_source }}</p><p v-if="account.mark_event_id != null" class="mono">Saved event #{{ account.mark_event_id }}<template v-if="account.mark_available_ms != null"> · available {{ utc(account.mark_available_ms) }} UTC</template></p></div></details>
    </template>
    <p v-else class="microcopy">Arrows show confirmed UP / DOWN crossovers. Blue squares show fills in simulated account modes.</p>
  </section>
</template>
