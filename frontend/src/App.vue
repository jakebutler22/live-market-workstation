<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import MarketChart from './MarketChart.vue'
import StrategyPanel from './StrategyPanel.vue'
import StrategyLedger from './StrategyLedger.vue'
import HistoricalPanel from './HistoricalPanel.vue'
import EquityTable from './EquityTable.vue'

const chart = ref(null)
const mode = ref('live')
const status = shallowRef({ source: 'Yahoo Finance', symbol: '—', interval: 60, state: 'connecting' })
const candles = shallowRef([])
const events = shallowRef([])
const selectedTime = ref(null)
const hoveredTime = ref(null)
const now = ref(Date.now())
const socketState = ref('connecting')
const replay = shallowRef({ state: 'ready', position: 0, total: 0, clock_ms: null })
const speed = ref(20)
const error = ref('')
const pending = ref(false)
const notice = ref('')
const metrics = shallowRef({ snapshots: 0, incrementalUpdates: 0, lastRenderMs: 0, visibleCandles: 0 })
const paperResult = shallowRef(null)
const liveIndicators = shallowRef(null)
const replayIndicators = shallowRef(null)
const historicalResult = shallowRef(null)
const datasets = shallowRef([])
const selectedDataset = ref('yahoo-4-1')
const backtestBusy = ref(false)
const recordsTab = ref('strategy')
let socket, ageTimer, reconnectTimer, indicatorTimer, indicatorAbort, generation = 0, retry = 0, destroyed = false, liveStrategyRevision = 0

const visibleResult = computed(() => mode.value === 'historical' ? historicalResult.value : mode.value === 'replay' ? replayIndicators.value : paperResult.value)
const overlayResult = computed(() => mode.value === 'live' ? liveIndicators.value || paperResult.value : visibleResult.value)
const inspectedPoint = computed(() => overlayResult.value?.points?.find(point => point.time === inspected.value?.time))
const strategyConfig = computed(() => visibleResult.value?.config || overlayResult.value?.config || { fast: 5, slow: 20 })
const fastWindow = computed(() => strategyConfig.value.fast ?? strategyConfig.value.fast_window ?? 5)
const slowWindow = computed(() => strategyConfig.value.slow ?? strategyConfig.value.slow_window ?? 20)
const historicalDataset = computed(() => historicalResult.value?.dataset)
const displaySymbol = computed(() => mode.value === 'historical' ? historicalDataset.value?.symbol || 'HISTORICAL' : status.value.symbol)

const latest = computed(() => candles.value.at(-1))
const inspected = computed(() => candles.value.find(c => c.time === (selectedTime.value ?? hoveredTime.value)) ?? latest.value)
const recent = computed(() => candles.value.slice(-8).reverse())
const lastEvent = computed(() => events.value.find(event => event.kind === 'quote') ?? events.value[0])
const sourceAgeMs = computed(() => {
  const source = status.value.last_source_ms
  const clock = mode.value === 'replay' ? replay.value.clock_ms : now.value
  return source && clock ? Math.max(0, clock - source) : null
})
const sourceAge = computed(() => sourceAgeMs.value == null ? 'Unknown' : sourceAgeMs.value < 1000 ? '<1s' : sourceAgeMs.value < 60000 ? `${Math.floor(sourceAgeMs.value / 1000)}s` : `${Math.floor(sourceAgeMs.value / 60000)}m ${Math.floor(sourceAgeMs.value / 1000) % 60}s`)
const staleThresholdMs = computed(() => (Number(status.value.expected_delay_seconds) || 0) * 1000 + 30000)
const feedState = computed(() => {
  if (mode.value === 'historical') return backtestBusy.value ? 'Historical · running' : historicalDataset.value?.synthetic ? 'Historical · synthetic fixture' : 'Historical · recorded Yahoo'
  if (mode.value === 'replay') return `Replay · ${replay.value.state || 'ready'}`
  const value = status.value.state
  if (['unavailable', 'disconnected', 'paused', 'connecting'].includes(value)) return value === 'paused' ? 'Unavailable · induced' : value
  if (sourceAgeMs.value != null && sourceAgeMs.value > staleThresholdMs.value) return 'stale'
  return value || 'connecting'
})
const stateClass = computed(() => mode.value !== 'live' ? 'replay' : feedState.value === 'receiving' ? 'receiving' : 'warning')
const captureLabel = computed(() => inspected.value ? inspected.value.partial || inspected.value.gap ? 'Partial coverage' : 'Observed coverage' : 'No observations')
const volumeLabel = computed(() => inspected.value?.volume == null ? 'Unavailable for selected interval' : `${inspected.value.volume_source || 'Yahoo 1m reconciliation'}${mode.value === 'historical' ? '' : ' · may lag'}`)
const replayPlaying = computed(() => replay.value.state === 'playing' || replay.value.state === 'running')
const replayPaused = computed(() => replay.value.state === 'paused')
const livePrice = computed(() => latest.value?.close)
const delta = computed(() => inspected.value ? inspected.value.close - inspected.value.open : null)

function number(value, precision = 2) { return value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString('en-US', { minimumFractionDigits: precision, maximumFractionDigits: precision }) }
function utc(value, full = true) {
  if (value == null || !Number.isFinite(Number(value))) return 'Unknown'
  try { const date = new Date(Number(value)).toISOString(); return full ? `${date.slice(0, 10)} ${date.slice(11, 23)}` : date.slice(11, 19) } catch { return 'Unknown' }
}
function intervalTime(candle) { return candle ? `${utc(candle.time * 1000, false).slice(0, 5)}–${utc(candle.end_ms ?? (candle.time + 60) * 1000, false).slice(0, 5)}` : '—' }
function direction(candle) { return !candle ? '' : candle.close > candle.open ? 'positive' : candle.close < candle.open ? 'negative' : 'neutral' }
function eventLabel(event) { return event ? `#${event.id ?? event.event_id ?? '—'}` : '—' }
function storedEventLabel(candle) {
  const id = candle?.last_event_id ?? candle?.source_event_id
  return id != null ? `#${id}` : mode.value === 'historical' && historicalDataset.value?.synthetic ? 'Fixture bar' : '—'
}
function merge(changed, reset = false) {
  const map = new Map((reset ? [] : candles.value).map(c => [c.time, c]))
  for (const candle of changed || []) map.set(candle.time, candle)
  candles.value = [...map.values()].sort((a, b) => a.time - b.time).slice(-600)
  if (reset) chart.value?.snapshot(candles.value)
  else chart.value?.update(changed || [])
}
function applyOverlays() {
  const overlay = overlayResult.value
  chart.value?.strategy(overlay?.points || [], overlay?.signals || visibleResult.value?.signals || [], mode.value === 'replay' ? [] : visibleResult.value?.fills || [], strategyConfig.value)
}
function requestReplayIndicators() {
  if (indicatorTimer || mode.value !== 'replay') return
  indicatorTimer = setTimeout(async () => {
    indicatorTimer = null
    const token = generation
    indicatorAbort?.abort()
    indicatorAbort = new AbortController()
    try {
      const response = await fetch('/api/indicators', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candles: candles.value, fast: 5, slow: 20 }), signal: indicatorAbort.signal })
      if (!response.ok) throw new Error(`Replay indicator calculation failed (${response.status})`)
      const result = await response.json()
      if (token === generation && mode.value === 'replay') { replayIndicators.value = result; applyOverlays() }
    } catch (problem) { if (problem.name !== 'AbortError' && token === generation) error.value = problem.message }
  }, 150)
}
function accept(message) {
  if (message.status) status.value = message.status
  if (message.replay) replay.value = { ...replay.value, ...message.replay }
  if (message.type === 'snapshot') {
    selectedTime.value = null
    merge(message.candles || [], true)
  } else if (message.candles) merge(message.candles)
  if (message.event) {
    events.value = [message.event, ...events.value.filter(e => e.id !== message.event.id)].slice(0, 20)
  }
  if (message.type === 'error') error.value = message.detail || message.error || 'The backend could not complete this operation.'
  if (mode.value === 'live') {
    if (message.strategy) { paperResult.value = message.strategy.paper || message.strategy; liveStrategyRevision++ }
    if (message.indicators) liveIndicators.value = message.indicators
    if (message.strategy || message.indicators) applyOverlays()
  } else if (mode.value === 'replay' && (message.type === 'snapshot' || message.candles?.length)) requestReplayIndicators()
}
async function loadStrategy() {
  const revision = liveStrategyRevision
  try {
    const response = await fetch('/api/strategy')
    if (!response.ok) throw new Error(`Strategy retrieval failed (${response.status})`)
    const result = await response.json()
    if (destroyed) return
    datasets.value = result.datasets || []
    if (!datasets.value.some(item => item.id === selectedDataset.value)) selectedDataset.value = datasets.value[0]?.id || ''
    if (mode.value === 'live' && revision === liveStrategyRevision) { paperResult.value = result.paper; liveIndicators.value = result.chart || result.paper; applyOverlays() }
  } catch (problem) { error.value = problem.message }
}
function historicalBars(result) {
  return (result.bars || []).map(bar => ({ ...bar, end_ms: bar.end_ms ?? (bar.time + 60) * 1000, elapsed: true, partial: false, revision: bar.revision ?? 1, price_source: bar.price_source || (result.dataset?.synthetic ? 'Synthetic worked fixture' : 'Recorded Yahoo history'), volume_source: bar.volume_source || (result.dataset?.synthetic ? 'Synthetic fixture' : 'Recorded Yahoo interval volume') }))
}
function showHistorical() {
  const result = historicalResult.value
  events.value = []
  selectedTime.value = null
  hoveredTime.value = null
  merge(result ? historicalBars(result) : [], true)
  applyOverlays()
}
async function runBacktest() {
  if (backtestBusy.value) return
  backtestBusy.value = true
  error.value = ''
  changeMode('historical')
  try {
    const response = await fetch('/api/backtests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dataset_id: selectedDataset.value }) })
    if (!response.ok) { const failure = await response.json(); throw new Error(failure.detail || `Backtest failed (${response.status})`) }
    const result = await response.json()
    historicalResult.value = result
    try { localStorage.setItem('lmw.lastBacktest', String(result.id)) } catch { /* An unavailable browser store does not invalidate a saved server run. */ }
    if (mode.value === 'historical') showHistorical()
    notice.value = `Backtest saved. Your live paper account is unchanged.`
  } catch (problem) { error.value = problem.message }
  finally { backtestBusy.value = false }
}
async function restoreBacktest() {
  let id
  try { id = localStorage.getItem('lmw.lastBacktest') } catch { return }
  if (!id) return
  try {
    const response = await fetch(`/api/backtests/${encodeURIComponent(id)}`)
    if (!response.ok) return
    const result = await response.json()
    if (!destroyed && !historicalResult.value) { historicalResult.value = result; if (mode.value === 'historical') showHistorical() }
  } catch { /* Prior local runs remain optional while the backend is unavailable. */ }
}
async function loadRecords(token) {
  try {
    const response = await fetch('/api/observations?limit=20')
    if (!response.ok) throw new Error(`Observation retrieval failed (${response.status})`)
    const result = await response.json()
    if (token === generation && mode.value === 'live') {
      const map = new Map([...(result.events || []), ...events.value].map(e => [e.id, e]))
      events.value = [...map.values()].sort((a, b) => b.id - a.id).slice(0, 20)
    }
  } catch (problem) { if (token === generation) error.value = problem.message }
}
function connect(reset = true) {
  clearTimeout(reconnectTimer)
  const token = ++generation
  if (socket) { socket.onclose = null; socket.close() }
  socketState.value = 'connecting'
  error.value = ''
  if (reset) {
    // A mode's timestamps and saved counts belong to its own snapshot. Keep
    // instrument metadata, but never show recorded state as a live feed.
    const { source, symbol, interval, expected_delay_seconds, data_label, price_unit, volume_unit } = status.value
    status.value = { source, symbol, interval, expected_delay_seconds, data_label, price_unit, volume_unit,
      state: 'connecting', last_source_ms: null, last_received_ms: null, last_event_id: null,
      event_count: 0, quote_count: 0, duplicate_count: 0, error: null }
    events.value = []
    replayIndicators.value = null
    chart.value?.clearStrategy()
    merge([], true)
    replay.value = { state: 'ready', position: 0, total: 0, clock_ms: null }
  }
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  socket = new WebSocket(`${protocol}//${location.host}/ws/${mode.value}`)
  socket.onopen = () => {
    if (token !== generation) return
    socketState.value = 'connected'; retry = 0
    if (mode.value === 'live') loadRecords(token)
  }
  socket.onmessage = event => {
    if (token !== generation) return
    try { accept(JSON.parse(event.data)) } catch (problem) { error.value = `Update could not be displayed: ${problem.message}` }
  }
  socket.onerror = () => { if (token === generation) error.value = 'Application socket unavailable. Retained data remains visible.' }
  socket.onclose = () => {
    if (token !== generation || destroyed) return
    socketState.value = 'disconnected'
    if (mode.value === 'live') reconnectTimer = setTimeout(() => connect(false), Math.min(1000 * 2 ** retry++, 8000))
  }
}
function changeMode(next) {
  if (mode.value === next) return
  mode.value = next
  clearTimeout(indicatorTimer); indicatorTimer = null; indicatorAbort?.abort()
  chart.value?.clearStrategy()
  if (next === 'historical') {
    generation++
    clearTimeout(reconnectTimer)
    if (socket) { socket.onclose = null; socket.close() }
    socketState.value = 'isolated'
    error.value = ''
    notice.value = 'This backtest uses a separate account. Your live paper ledger is unchanged.'
    showHistorical()
    return
  }
  notice.value = next === 'replay' ? 'Replay reads the recording without writing new capture records.' : 'Live capture restored. Loading the saved chart.'
  connect(true)
}
function replayAction(action) {
  if (socket?.readyState !== WebSocket.OPEN) { error.value = 'Connect the application socket before starting replay.'; return }
  socket.send(JSON.stringify({ action, speed: Number(speed.value) }))
  notice.value = `${action[0].toUpperCase() + action.slice(1)} requested · ${speed.value}× recorded time`
}
async function interruptFeed() {
  pending.value = true
  error.value = ''
  const resume = ['paused', 'unavailable', 'disconnected'].includes(status.value.state)
  try {
    const response = await fetch(`/api/feed/${resume ? 'resume' : 'pause'}`, { method: 'POST' })
    if (!response.ok) throw new Error(`Feed control failed (${response.status})`)
    const result = await response.json()
    if (result.status) status.value = result.status
    else if (result.state) status.value = result
    notice.value = resume ? 'Yahoo reconnection requested.' : 'Controlled interruption active. Source time continues to age.'
  } catch (problem) { error.value = problem.message }
  finally { pending.value = false }
}
function selectCandle(time) { selectedTime.value = selectedTime.value === time ? null : time }
function inspectStrategy(time) { selectedTime.value = time; chart.value?.focus(time) }
function tableKey(event, candle) {
  const index = candles.value.findIndex(c => c.time === candle.time)
  if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
    event.preventDefault()
    const next = candles.value[index + (event.key === 'ArrowUp' ? 1 : -1)]
    if (next) { selectedTime.value = next.time; document.getElementById(`candle-${next.time}`)?.focus() }
  }
}
onMounted(async () => {
  ageTimer = setInterval(() => { now.value = Date.now() }, 1000)
  connect()
  loadStrategy()
  restoreBacktest()
})
onBeforeUnmount(() => { destroyed = true; generation++; clearInterval(ageTimer); clearTimeout(reconnectTimer); clearTimeout(indicatorTimer); indicatorAbort?.abort(); socket?.close() })
</script>

<template>
  <div class="workstation">
    <header class="topbar">
      <a class="brand" href="#main"><span class="brand-mark" aria-hidden="true">▥</span><span>Live Market <strong>Workstation</strong><small>Market data &amp; paper research</small></span></a>
      <div class="instrument"><strong>{{ displaySymbol }}</strong><span>1 min</span><span class="source-name">{{ mode === 'historical' && historicalDataset?.synthetic ? 'Synthetic example' : 'Yahoo Finance' }}</span></div>
      <nav class="mode-switch" aria-label="Data mode">
        <button :aria-pressed="mode === 'live'" :class="{ active: mode === 'live' }" @click="changeMode('live')">LIVE</button>
        <button :aria-pressed="mode === 'replay'" :class="{ active: mode === 'replay' }" @click="changeMode('replay')">REPLAY</button>
        <button :aria-pressed="mode === 'historical'" :class="{ active: mode === 'historical' }" @click="changeMode('historical')" data-testid="historical-mode">HISTORICAL</button>
      </nav>
      <span class="utc-label">All times UTC</span>
    </header>

    <div class="connection-strip">
      <span class="sr-only" aria-live="polite" aria-atomic="true">{{ feedState }}. Application socket {{ socketState }}.</span>
      <span class="state-label" :class="stateClass"><span class="state-dot" aria-hidden="true"></span>{{ feedState }}</span>
      <span class="strip-divider"></span><span>App <strong>{{ socketState }}</strong></span>
      <template v-if="mode === 'live'"><span class="strip-divider"></span><span>Source age <strong class="mono">{{ sourceAge }}</strong></span></template>
      <span class="strip-divider"></span><span>Saved <strong>{{ mode === 'historical' ? historicalResult ? 'Historical run' : 'No run selected' : mode === 'replay' ? `${number(replay.position || 0, 0)} / ${number(replay.total || 0, 0)} replayed` : `${number(status.event_count || 0, 0)} saved events` }}</strong></span>
      <span class="strip-note">{{ mode === 'historical' ? 'Historical simulation · separate account' : mode === 'replay' ? 'Recorded observations · live account unchanged' : status.data_label || 'Yahoo sampled quotes' }}</span>
    </div>

    <main id="main" class="workspace">
      <section class="chart-panel panel" aria-labelledby="chart-title">
        <div class="panel-heading chart-heading">
          <div><h1 id="chart-title">{{ displaySymbol }} <span>/ {{ mode === 'historical' ? 'Historical simulation' : mode === 'replay' ? 'Recorded market' : 'Market overview' }}</span></h1><p>{{ mode === 'historical' ? historicalDataset?.synthetic ? 'Synthetic worked example · not market data' : 'Recorded Yahoo candles · historical simulation' : 'Sampled quote candles · Yahoo 1-minute volume' }} <span v-if="mode !== 'historical' && status.expected_delay_seconds" class="delay-label">{{ Math.round(status.expected_delay_seconds / 60) }} min delayed</span></p></div>
          <div class="headline-price mono" :class="direction(latest)">{{ number(livePrice) }}<small>{{ mode === 'historical' ? 'Last dataset close' : 'Last observed price' }}{{ mode === 'historical' ? historicalDataset?.currency ? ` / ${historicalDataset.currency}` : '' : status.price_unit ? ` / ${status.price_unit}` : '' }}</small></div>
          <button class="quiet-button fit-button" @click="chart?.fit()" aria-label="Fit all displayed candles">Fit chart</button>
        </div>
        <div class="ohlcv-strip" aria-label="Selected candle values">
          <div class="inspection-time mono">{{ intervalTime(inspected) }} <small>{{ inspected ? utc(inspected.time * 1000).slice(0, 10) + ' · ' : '' }}UTC</small></div>
          <div><span>O</span><strong class="mono">{{ number(inspected?.open) }}</strong></div>
          <div><span>H</span><strong class="mono">{{ number(inspected?.high) }}</strong></div>
          <div><span>L</span><strong class="mono">{{ number(inspected?.low) }}</strong></div>
          <div><span>C</span><strong class="mono" :class="direction(inspected)">{{ number(inspected?.close) }}</strong></div>
          <div><span>VOL</span><strong class="mono">{{ number(inspected?.volume, 0) }}</strong></div>
          <div class="candle-change mono" :class="direction(inspected)">{{ delta == null ? '—' : `${delta > 0 ? '+' : ''}${number(delta)}` }}</div>
        </div>
        <div class="strategy-chart-strip"><span><i class="line-key fast-line"></i>SMA {{ fastWindow }} <strong class="mono">{{ number(inspectedPoint?.fast, 4) }}</strong></span><span><i class="line-key slow-line"></i>SMA {{ slowWindow }} <strong class="mono">{{ number(inspectedPoint?.slow, 4) }}</strong></span><span class="marker-key positive">↑ UP</span><span class="marker-key negative">↓ DOWN</span><span class="marker-key fill-key">■ Simulated fill</span><span class="strategy-input-label">{{ mode === 'live' ? 'Original quote inputs' : mode === 'replay' ? 'Replay indicators · no trades' : 'Historical · later-bar fills' }}</span></div>
        <div class="chart-stage">
          <MarketChart ref="chart" @inspect="hoveredTime = $event" @performance="metrics = $event" />
          <div v-if="!candles.length" class="chart-empty"><span class="empty-reticle" aria-hidden="true">＋</span><strong>{{ mode === 'historical' ? backtestBusy ? 'Running historical simulation' : 'Choose a recorded dataset' : mode === 'replay' ? 'Your recording, in sequence' : 'Waiting for market observations' }}</strong><p>{{ mode === 'historical' ? 'Run a backtest to inspect indicators, signals and later simulated fills.' : mode === 'replay' ? 'Start replay to rebuild candles from saved events.' : 'The chart will populate when Yahoo observations or reconciled history arrive.' }}</p><span>{{ mode === 'historical' ? 'Historical results never change the live paper account.' : mode === 'replay' ? `${replay.total || 0} recorded events available` : 'No synthetic prices or volume are displayed.' }}</span></div>
          <span class="volume-pane-label">VOLUME{{ status.volume_unit ? ` / ${status.volume_unit.toUpperCase()}` : '' }} <span>{{ mode === 'historical' ? historicalDataset?.synthetic ? 'SYNTHETIC FIXTURE' : 'RECORDED INTERVAL VOLUME' : 'RECONCILED · MAY LAG' }}</span></span>
        </div>
        <div class="chart-caption"><span><span class="legend-swatch up"></span>Close &gt; open <span class="legend-swatch down"></span>Close &lt; open <span class="legend-swatch neutral-swatch"></span>Equal</span><span>Unavailable volume has no bar <span class="dot-separator">·</span> <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView Lightweight Charts™</a></span></div>
        <section class="candle-records" aria-labelledby="candles-title">
          <div class="subheading records-heading"><div class="records-tabs" aria-label="Chart data inspector"><button :aria-pressed="recordsTab === 'strategy'" :class="{ active: recordsTab === 'strategy' }" @click="recordsTab = 'strategy'" data-testid="ledger-tab">Strategy ledger <span>{{ visibleResult?.signals?.length || 0 }}</span></button><button :aria-pressed="recordsTab === 'equity'" :class="{ active: recordsTab === 'equity' }" @click="recordsTab = 'equity'" data-testid="equity-tab">Equity history</button><button :aria-pressed="recordsTab === 'candles'" :class="{ active: recordsTab === 'candles' }" @click="recordsTab = 'candles'">Candle records</button></div><button class="quiet-button" :disabled="selectedTime == null" @click="selectedTime = null">Follow latest</button></div>
          <h2 id="candles-title" class="sr-only">Chart data inspector</h2>
          <StrategyLedger v-if="recordsTab === 'strategy'" :result="visibleResult" :mode="mode" @inspect="inspectStrategy" />
          <EquityTable v-else-if="recordsTab === 'equity'" :result="visibleResult" :mode="mode" />
          <div v-else class="table-scroll">
            <table class="candle-table"><caption class="sr-only">Recent candles. Select an interval to inspect it. Arrow keys move between intervals. Times UTC.</caption><thead><tr><th>INTERVAL / UTC</th><th>OPEN</th><th>HIGH</th><th>LOW</th><th>CLOSE</th><th>VOLUME</th><th>STATE</th><th>REV</th><th>EVENT</th></tr></thead><tbody>
              <tr v-for="candle in recent" :key="candle.time" :class="{ selected: inspected?.time === candle.time }"><td><button :id="`candle-${candle.time}`" class="interval-button mono" :aria-label="`Inspect ${utc(candle.time * 1000)} UTC candle`" :aria-pressed="selectedTime === candle.time" @click="selectCandle(candle.time)" @keydown="tableKey($event, candle)">{{ intervalTime(candle) }}</button></td><td>{{ number(candle.open) }}</td><td>{{ number(candle.high) }}</td><td>{{ number(candle.low) }}</td><td :class="direction(candle)">{{ number(candle.close) }}</td><td>{{ number(candle.volume, 0) }}</td><td class="table-state">{{ candle.elapsed ? 'Elapsed' : 'Forming' }}<span v-if="candle.partial || candle.gap" class="partial-marker" title="Partial observation coverage"> · partial</span></td><td>v{{ candle.revision }}</td><td>{{ storedEventLabel(candle) }}</td></tr>
              <tr v-if="!recent.length"><td colspan="9" class="table-empty">No captured intervals in this view.</td></tr>
            </tbody></table>
          </div>
        </section>
      </section>

      <aside class="inspector" aria-label="Feed, capture and replay inspectors">
        <StrategyPanel :result="visibleResult" :point="inspectedPoint" :mode="mode" />
        <HistoricalPanel :datasets="datasets" :selected="selectedDataset" :busy="backtestBusy" :run="historicalResult" :mode="mode" @select="selectedDataset = $event" @run="runBacktest" @open="changeMode('historical')" />
        <section v-if="mode !== 'historical'" class="panel feed-panel" aria-labelledby="feed-title">
          <div class="panel-heading compact-heading"><h2 id="feed-title">Feed &amp; capture</h2><span class="mini-tag">{{ mode.toUpperCase() }}</span></div>
          <dl class="info-list"><div><dt>Source</dt><dd>Yahoo Finance</dd></div><div><dt>Upstream</dt><dd :class="stateClass">{{ feedState }}</dd></div><div><dt>Application socket</dt><dd>{{ socketState }}</dd></div><div v-if="status.expected_delay_seconds"><dt>Published delay</dt><dd class="warning">{{ Math.round(status.expected_delay_seconds / 60) }} minutes</dd></div><div class="source-age"><dt>{{ mode === 'replay' ? 'Age at replay clock' : 'Source-data age' }}</dt><dd class="mono" :class="sourceAgeMs == null || sourceAgeMs > staleThresholdMs ? 'warning' : ''">{{ sourceAge }}</dd></div></dl>
          <div class="time-block"><span>Source event · UTC</span><strong class="mono">{{ utc(status.last_source_ms) }}</strong><span>Received by backend · UTC</span><strong class="mono">{{ utc(status.last_received_ms) }}</strong></div>
          <p class="microcopy">Age uses source time. Socket heartbeats never refresh it. Session state is not inferred.</p>
          <div v-if="mode === 'live'" class="feed-controls"><button class="secondary-button" :disabled="pending" @click="interruptFeed">{{ pending ? 'Applying…' : status.state === 'paused' ? 'Resume Yahoo feed' : ['unavailable', 'disconnected'].includes(status.state) ? 'Reconnect Yahoo feed' : 'Interrupt Yahoo feed' }}</button><span>Temporarily stops the upstream connection</span></div>
        </section>

        <section class="panel capture-panel" aria-labelledby="capture-title">
          <div class="panel-heading compact-heading"><h2 id="capture-title">Selected candle</h2><span class="mini-tag saved-tag">{{ inspected ? mode === 'historical' ? 'RUN DATASET' : 'SAVED' : 'EMPTY' }}</span></div>
          <dl class="info-list"><div><dt>Completion</dt><dd>{{ inspected ? inspected.elapsed ? 'Elapsed interval' : 'Forming' : '—' }}</dd></div><div><dt>Coverage</dt><dd :class="{ warning: inspected?.partial || inspected?.gap }">{{ captureLabel }}</dd></div><div><dt>Candle revision</dt><dd class="mono">{{ inspected ? `v${inspected.revision}` : '—' }}</dd></div><div><dt>Last saved event</dt><dd class="mono">{{ storedEventLabel(inspected) }}</dd></div><div><dt>Last quote event</dt><dd class="mono">{{ inspected?.last_quote_event_id ? `#${inspected.last_quote_event_id}` : '—' }}</dd></div><div><dt>Quote observations</dt><dd class="mono">{{ number(inspected?.quote_count, 0) }}</dd></div><div><dt>Volume event</dt><dd class="mono">{{ inspected?.volume_event_id ? `#${inspected.volume_event_id}` : '—' }}</dd></div><div><dt>Duplicate receipts</dt><dd class="mono">{{ number(status.duplicate_count || 0, 0) }}</dd></div></dl>
          <div class="provenance"><span>Volume source</span><p>{{ volumeLabel }}{{ inspected?.volume_asof_ms ? ` · received ${utc(inspected.volume_asof_ms, false)} UTC` : '' }}</p><span>Price source</span><p>{{ inspected?.price_source || 'No selected candle' }}</p></div>
          <p class="microcopy">Elapsed ≠ complete trade coverage. Late observations may revise closed intervals.</p>
        </section>

        <section v-if="mode !== 'historical'" class="panel replay-panel" aria-labelledby="replay-title">
          <div class="panel-heading compact-heading"><h2 id="replay-title">Recording &amp; replay</h2><span class="mini-tag">SQLITE</span></div>
          <template v-if="mode === 'replay'">
            <div class="recording-time"><span>Original recording · UTC</span><strong class="mono">{{ utc(replay.first_received_ms) }}</strong></div>
            <div class="replay-progress"><span class="mono">{{ replay.position || 0 }} / {{ replay.total || 0 }} events</span><span>{{ replay.state }}</span></div>
            <progress :value="replay.position || 0" :max="replay.total || 1" aria-label="Replay progress"></progress>
            <div class="replay-buttons"><button class="primary-button" :disabled="socketState !== 'connected' || !replay.total" @click="replayAction(replayPlaying ? 'pause' : replayPaused ? 'resume' : 'start')">{{ replayPlaying ? 'Pause' : replayPaused ? 'Resume' : 'Start replay' }}</button><button class="secondary-button" :disabled="socketState !== 'connected' || !replay.total" @click="replayAction('restart')">Restart</button><label class="speed-control"><span class="sr-only">Replay speed</span><select v-model="speed" aria-label="Replay speed"><option :value="1">1×</option><option :value="5">5×</option><option :value="20">20×</option><option :value="60">60×</option></select></label></div>
            <p class="microcopy">Original receipt order and source times. Replay clock: <span class="mono">{{ utc(replay.clock_ms, false) }}</span> UTC.</p>
          </template>
          <template v-else><p class="replay-intro">Revisit saved observations in their original order. Source capture continues independently.</p><button class="secondary-button full-width" @click="changeMode('replay')">Open recorded session <span aria-hidden="true">→</span></button></template>
        </section>
      </aside>

      <section class="panel event-panel" aria-labelledby="event-title"><div v-if="mode === 'historical'" class="event-summary"><h2 id="event-title">Historical result <span class="mono">{{ historicalResult?.id || '—' }}</span></h2><span>{{ historicalDataset?.synthetic ? 'SYNTHETIC FIXTURE · NOT A YAHOO SESSION' : 'Recorded Yahoo dataset' }}</span><span class="mono">{{ historicalResult?.bars?.length || 0 }} bars</span><span>Orders {{ visibleResult?.summary?.orders ?? 0 }} · Fills {{ visibleResult?.summary?.fills ?? 0 }} · Round trips {{ visibleResult?.summary?.round_trips ?? 0 }}</span><span>No live account writes</span></div><div v-else class="event-summary"><h2 id="event-title">Latest capture <span class="mono">{{ eventLabel(lastEvent) }}</span></h2><span>{{ lastEvent?.kind || 'Awaiting capture' }}</span><span class="mono">Source {{ utc(lastEvent?.source_ms, false) }} UTC</span><span class="mono">Receipt {{ utc(lastEvent?.received_ms, false) }} UTC</span><span class="event-identity mono">{{ lastEvent?.identity || 'Immutable observation log' }}</span><details v-if="lastEvent"><summary>Record details</summary><pre>{{ JSON.stringify(lastEvent, null, 2) }}</pre></details></div></section>
    </main>

    <footer class="statusbar"><div role="status">{{ error || (mode === 'live' ? status.error : null) || notice || 'Ready · source timestamps and receipt order preserved in SQLite.' }}</div><span class="mono">{{ metrics.visibleCandles }} displayed <span class="dot-separator">·</span> {{ metrics.lastRenderMs.toFixed(2) }}ms chart update <span class="dot-separator">·</span> UTC {{ utc(now, false) }}</span></footer>
  </div>
</template>
