<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import MarketChart from './MarketChart.vue'

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
let socket, ageTimer, reconnectTimer, generation = 0, retry = 0, destroyed = false

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
  if (mode.value === 'replay') return `Replay · ${replay.value.state || 'ready'}`
  const value = status.value.state
  if (['unavailable', 'disconnected', 'paused', 'connecting'].includes(value)) return value === 'paused' ? 'Unavailable · induced' : value
  if (sourceAgeMs.value != null && sourceAgeMs.value > staleThresholdMs.value) return 'stale'
  return value || 'connecting'
})
const stateClass = computed(() => mode.value === 'replay' ? 'replay' : feedState.value === 'receiving' ? 'receiving' : 'warning')
const captureLabel = computed(() => inspected.value ? inspected.value.partial || inspected.value.gap ? 'Partial coverage' : 'Observed coverage' : 'No observations')
const volumeLabel = computed(() => inspected.value?.volume == null ? 'Unavailable for selected interval' : `${inspected.value.volume_source || 'Yahoo 1m reconciliation'} · may lag`)
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
function merge(changed, reset = false) {
  const map = new Map((reset ? [] : candles.value).map(c => [c.time, c]))
  for (const candle of changed || []) map.set(candle.time, candle)
  candles.value = [...map.values()].sort((a, b) => a.time - b.time).slice(-600)
  if (reset) chart.value?.snapshot(candles.value)
  else chart.value?.update(changed || [])
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
})
onBeforeUnmount(() => { destroyed = true; generation++; clearInterval(ageTimer); clearTimeout(reconnectTimer); socket?.close() })
</script>

<template>
  <div class="workstation">
    <header class="topbar">
      <a class="brand" href="#main"><span class="brand-mark" aria-hidden="true">▥</span><span>LIVE MARKET <strong>WORKSTATION</strong><small>MARKET DATA / ASSIGNMENT 4.1</small></span></a>
      <div class="instrument"><strong>{{ status.symbol }}</strong><span>1 MIN</span><span class="source-name">YAHOO FINANCE</span></div>
      <nav class="mode-switch" aria-label="Data mode">
        <button :aria-pressed="mode === 'live'" :class="{ active: mode === 'live' }" @click="changeMode('live')">LIVE</button>
        <button :aria-pressed="mode === 'replay'" :class="{ active: mode === 'replay' }" @click="changeMode('replay')">REPLAY</button>
      </nav>
      <span class="utc-label">ALL TIMES UTC</span>
    </header>

    <div class="connection-strip">
      <span class="sr-only" aria-live="polite" aria-atomic="true">{{ feedState }}. Application socket {{ socketState }}.</span>
      <span class="state-label" :class="stateClass"><span class="state-dot" aria-hidden="true"></span>{{ feedState }}</span>
      <span class="strip-divider"></span><span>App socket <strong>{{ socketState }}</strong></span>
      <span class="strip-divider"></span><span>SQLite <strong>{{ mode === 'replay' ? `${number(replay.position || 0, 0)} / ${number(replay.total || 0, 0)} replayed` : `${number(status.event_count || 0, 0)} saved events` }}</strong></span>
      <span class="strip-note">{{ mode === 'replay' ? 'RECORDED OBSERVATIONS · LIVE STATE ISOLATED' : status.data_label || 'SAMPLED QUOTES · PERSIST BEFORE PUBLISH' }}</span>
    </div>

    <main id="main" class="workspace">
      <section class="chart-panel panel" aria-labelledby="chart-title">
        <div class="panel-heading chart-heading">
          <div><h1 id="chart-title">{{ status.symbol }} <span>/ {{ mode === 'replay' ? 'Recorded market' : 'Market overview' }}</span></h1><p>Sampled quote candles <span class="dot-separator">·</span> Yahoo 1-minute volume <span v-if="status.expected_delay_seconds" class="delay-label">{{ Math.round(status.expected_delay_seconds / 60) }} MIN DELAYED</span></p></div>
          <div class="headline-price mono" :class="direction(latest)">{{ number(livePrice) }}<small>LAST OBSERVED PRICE{{ status.price_unit ? ` / ${status.price_unit}` : '' }}</small></div>
          <button class="quiet-button fit-button" @click="chart?.fit()" aria-label="Fit all displayed candles">Fit chart</button>
        </div>
        <div class="ohlcv-strip" aria-label="Selected candle values">
          <div class="inspection-time mono">{{ intervalTime(inspected) }} <small>{{ inspected ? utc(inspected.time * 1000).slice(0, 10) + ' · ' : '' }}UTC [start, end)</small></div>
          <div><span>O</span><strong class="mono">{{ number(inspected?.open) }}</strong></div>
          <div><span>H</span><strong class="mono">{{ number(inspected?.high) }}</strong></div>
          <div><span>L</span><strong class="mono">{{ number(inspected?.low) }}</strong></div>
          <div><span>C</span><strong class="mono" :class="direction(inspected)">{{ number(inspected?.close) }}</strong></div>
          <div><span>VOL</span><strong class="mono">{{ number(inspected?.volume, 0) }}</strong></div>
          <div class="candle-change mono" :class="direction(inspected)">{{ delta == null ? '—' : `${delta > 0 ? '+' : ''}${number(delta)}` }}</div>
        </div>
        <div class="chart-stage">
          <MarketChart ref="chart" @inspect="hoveredTime = $event" @performance="metrics = $event" />
          <div v-if="!candles.length" class="chart-empty"><span class="empty-reticle" aria-hidden="true">＋</span><strong>{{ mode === 'replay' ? 'Your recording, in sequence' : 'Waiting for market observations' }}</strong><p>{{ mode === 'replay' ? 'Start replay to rebuild candles from saved events.' : 'The chart will populate when Yahoo observations or reconciled history arrive.' }}</p><span>{{ mode === 'replay' ? `${replay.total || 0} recorded events available` : 'No synthetic prices or volume are displayed.' }}</span></div>
          <span class="volume-pane-label">VOLUME{{ status.volume_unit ? ` / ${status.volume_unit.toUpperCase()}` : '' }} <span>RECONCILED · MAY LAG</span></span>
        </div>
        <div class="chart-caption"><span><span class="legend-swatch up"></span>Close &gt; open <span class="legend-swatch down"></span>Close &lt; open <span class="legend-swatch neutral-swatch"></span>Equal</span><span>Unknown volume = no bar <span class="dot-separator">·</span> <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">TradingView Lightweight Charts™</a></span></div>
        <section class="candle-records" aria-labelledby="candles-title">
          <div class="subheading"><h2 id="candles-title">CANDLE RECORDS <span>Latest 8 · keyboard accessible</span></h2><button class="quiet-button" :disabled="selectedTime == null" @click="selectedTime = null">Follow latest</button></div>
          <div class="table-scroll">
            <table class="candle-table"><caption class="sr-only">Recent candles. Select an interval to inspect it. Arrow keys move between intervals. Times UTC.</caption><thead><tr><th>INTERVAL / UTC</th><th>OPEN</th><th>HIGH</th><th>LOW</th><th>CLOSE</th><th>VOLUME</th><th>STATE</th><th>REV</th><th>EVENT</th></tr></thead><tbody>
              <tr v-for="candle in recent" :key="candle.time" :class="{ selected: inspected?.time === candle.time }"><td><button :id="`candle-${candle.time}`" class="interval-button mono" :aria-label="`Inspect ${utc(candle.time * 1000)} UTC candle`" :aria-pressed="selectedTime === candle.time" @click="selectCandle(candle.time)" @keydown="tableKey($event, candle)">{{ intervalTime(candle) }}</button></td><td>{{ number(candle.open) }}</td><td>{{ number(candle.high) }}</td><td>{{ number(candle.low) }}</td><td :class="direction(candle)">{{ number(candle.close) }}</td><td>{{ number(candle.volume, 0) }}</td><td class="table-state">{{ candle.elapsed ? 'Elapsed' : 'Forming' }}<span v-if="candle.partial || candle.gap" class="partial-marker" title="Partial observation coverage"> · partial</span></td><td>v{{ candle.revision }}</td><td>#{{ candle.last_event_id }}</td></tr>
              <tr v-if="!recent.length"><td colspan="9" class="table-empty">No captured intervals in this view.</td></tr>
            </tbody></table>
          </div>
        </section>
      </section>

      <aside class="inspector" aria-label="Feed, capture and replay inspectors">
        <section class="panel feed-panel" aria-labelledby="feed-title">
          <div class="panel-heading compact-heading"><h2 id="feed-title">FEED / CAPTURE</h2><span class="mini-tag">{{ mode.toUpperCase() }}</span></div>
          <dl class="info-list"><div><dt>Source</dt><dd>Yahoo Finance</dd></div><div><dt>Upstream</dt><dd :class="stateClass">{{ feedState }}</dd></div><div><dt>Application socket</dt><dd>{{ socketState }}</dd></div><div v-if="status.expected_delay_seconds"><dt>Published delay</dt><dd class="warning">{{ Math.round(status.expected_delay_seconds / 60) }} minutes</dd></div><div class="source-age"><dt>{{ mode === 'replay' ? 'Age at replay clock' : 'Source-data age' }}</dt><dd class="mono" :class="sourceAgeMs == null || sourceAgeMs > staleThresholdMs ? 'warning' : ''">{{ sourceAge }}</dd></div></dl>
          <div class="time-block"><span>SOURCE EVENT / UTC</span><strong class="mono">{{ utc(status.last_source_ms) }}</strong><span>BACKEND RECEIPT / UTC</span><strong class="mono">{{ utc(status.last_received_ms) }}</strong></div>
          <p class="microcopy">Age uses source time. Socket heartbeats never refresh it. Session state is not inferred.</p>
          <div v-if="mode === 'live'" class="feed-controls"><button class="secondary-button" :disabled="pending" @click="interruptFeed">{{ pending ? 'Applying…' : status.state === 'paused' ? 'Resume Yahoo feed' : ['unavailable', 'disconnected'].includes(status.state) ? 'Reconnect Yahoo feed' : 'Interrupt Yahoo feed' }}</button><span>Controlled interruption for verification</span></div>
        </section>

        <section class="panel capture-panel" aria-labelledby="capture-title">
          <div class="panel-heading compact-heading"><h2 id="capture-title">SELECTED INTERVAL</h2><span class="mini-tag saved-tag">{{ inspected ? 'SAVED' : 'EMPTY' }}</span></div>
          <dl class="info-list"><div><dt>Completion</dt><dd>{{ inspected ? inspected.elapsed ? 'Elapsed interval' : 'Forming' : '—' }}</dd></div><div><dt>Coverage</dt><dd :class="{ warning: inspected?.partial || inspected?.gap }">{{ captureLabel }}</dd></div><div><dt>Candle revision</dt><dd class="mono">{{ inspected ? `v${inspected.revision}` : '—' }}</dd></div><div><dt>Last saved event</dt><dd class="mono">{{ inspected ? `#${inspected.last_event_id}` : '—' }}</dd></div><div><dt>Last quote event</dt><dd class="mono">{{ inspected?.last_quote_event_id ? `#${inspected.last_quote_event_id}` : '—' }}</dd></div><div><dt>Quote observations</dt><dd class="mono">{{ number(inspected?.quote_count, 0) }}</dd></div><div><dt>Volume event</dt><dd class="mono">{{ inspected?.volume_event_id ? `#${inspected.volume_event_id}` : '—' }}</dd></div><div><dt>Duplicate receipts</dt><dd class="mono">{{ number(status.duplicate_count || 0, 0) }}</dd></div></dl>
          <div class="provenance"><span>VOLUME PROVENANCE</span><p>{{ volumeLabel }}{{ inspected?.volume_asof_ms ? ` · received ${utc(inspected.volume_asof_ms, false)} UTC` : '' }}</p><span>PRICE PROVENANCE</span><p>{{ inspected?.price_source || 'No selected candle' }}</p></div>
          <p class="microcopy">Elapsed ≠ complete trade coverage. Late observations may revise closed intervals.</p>
        </section>

        <section class="panel replay-panel" aria-labelledby="replay-title">
          <div class="panel-heading compact-heading"><h2 id="replay-title">RECORDING / REPLAY</h2><span class="mini-tag">SQLITE</span></div>
          <template v-if="mode === 'replay'">
            <div class="recording-time"><span>ORIGINAL RECORDING / UTC</span><strong class="mono">{{ utc(replay.first_received_ms) }}</strong></div>
            <div class="replay-progress"><span class="mono">{{ replay.position || 0 }} / {{ replay.total || 0 }} events</span><span>{{ replay.state }}</span></div>
            <progress :value="replay.position || 0" :max="replay.total || 1" aria-label="Replay progress"></progress>
            <div class="replay-buttons"><button class="primary-button" :disabled="socketState !== 'connected' || !replay.total" @click="replayAction(replayPlaying ? 'pause' : replayPaused ? 'resume' : 'start')">{{ replayPlaying ? 'Pause' : replayPaused ? 'Resume' : 'Start replay' }}</button><button class="secondary-button" :disabled="socketState !== 'connected' || !replay.total" @click="replayAction('restart')">Restart</button><label class="speed-control"><span class="sr-only">Replay speed</span><select v-model="speed" aria-label="Replay speed"><option :value="1">1×</option><option :value="5">5×</option><option :value="20">20×</option><option :value="60">60×</option></select></label></div>
            <p class="microcopy">Original receipt order and source times. Replay clock: <span class="mono">{{ utc(replay.clock_ms, false) }}</span> UTC.</p>
          </template>
          <template v-else><p class="replay-intro">Revisit saved observations in their original order. Source capture continues independently.</p><button class="secondary-button full-width" @click="changeMode('replay')">Open recorded session <span aria-hidden="true">→</span></button></template>
        </section>
      </aside>

      <section class="panel event-panel" aria-labelledby="event-title"><div class="event-summary"><h2 id="event-title">SAVED EVENT <span class="mono">{{ eventLabel(lastEvent) }}</span></h2><span>{{ lastEvent?.kind || 'Awaiting capture' }}</span><span class="mono">Source {{ utc(lastEvent?.source_ms, false) }} UTC</span><span class="mono">Receipt {{ utc(lastEvent?.received_ms, false) }} UTC</span><span class="event-identity mono">{{ lastEvent?.identity || 'Immutable observation log' }}</span><details v-if="lastEvent"><summary>Inspect payload</summary><pre>{{ JSON.stringify(lastEvent, null, 2) }}</pre></details></div></section>
    </main>

    <footer class="statusbar"><div role="status">{{ error || status.error || notice || 'Ready · source timestamps and receipt order preserved in SQLite.' }}</div><span class="mono">{{ metrics.visibleCandles }} displayed <span class="dot-separator">·</span> {{ metrics.lastRenderMs.toFixed(2) }}ms chart update <span class="dot-separator">·</span> UTC {{ utc(now, false) }}</span></footer>
  </div>
</template>
