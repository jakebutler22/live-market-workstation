<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { CandlestickSeries, ColorType, CrosshairMode, HistogramSeries, LineSeries, LineStyle, createChart, createSeriesMarkers } from 'lightweight-charts'

const emit = defineEmits(['inspect', 'performance'])
const container = ref(null)
let chart, priceSeries, volumeSeries, fastSeries, slowSeries, markers, observer
let overlay = { points: [], signals: [], fills: [], config: {} }
let fastPoints = new Map(), slowPoints = new Map(), markerKey = ''
let candleMap = new Map()
let fitted = false
let snapshots = 0
let incrementalUpdates = 0
const MAX_CANDLES = 600
const colors = { up: '#53C6A5', down: '#E6818A', neutral: '#9AA7B5' }

function direction(candle) {
  return candle.close > candle.open ? colors.up : candle.close < candle.open ? colors.down : colors.neutral
}
function pricePoint(candle) {
  const color = direction(candle)
  return { time: candle.time, open: candle.open, high: candle.high, low: candle.low, close: candle.close, color, borderColor: color, wickColor: color }
}
function volumePoint(candle) {
  // Whitespace preserves the shared time axis without inventing a zero bar.
  return candle.volume == null ? { time: candle.time } : { time: candle.time, value: candle.volume, color: direction(candle) }
}
function sorted() { return [...candleMap.values()].sort((a, b) => a.time - b.time) }
function publishMetrics(start) {
  emit('performance', { snapshots, incrementalUpdates, lastRenderMs: Math.round((performance.now() - start) * 100) / 100, visibleCandles: candleMap.size })
}
function snapshot(candles = []) {
  const start = performance.now()
  candleMap = new Map(candles.slice().sort((a, b) => a.time - b.time).slice(-MAX_CANDLES).map(c => [c.time, c]))
  snapshots++
  if (!chart) return
  const values = sorted()
  priceSeries.setData(values.map(pricePoint))
  volumeSeries.setData(values.map(volumePoint))
  syncStrategy(true)
  fitted = false
  if (values.length) { chart.timeScale().fitContent(); fitted = true }
  publishMetrics(start)
}
function update(candles = []) {
  const start = performance.now()
  for (const candle of candles.slice().sort((a, b) => a.time - b.time)) {
    const times = [...candleMap.keys()]
    const last = times.length ? Math.max(...times) : -Infinity
    const first = times.length ? Math.min(...times) : -Infinity
    // Corrections outside the bounded display remain preserved by SQLite.
    if (candleMap.size >= MAX_CANDLES && candle.time < first) continue
    const historical = candle.time < last
    const exists = candleMap.has(candle.time)
    candleMap.set(candle.time, candle)
    if (!chart) continue
    if (historical && !exists) {
      // A new, late interval needs a sorted reset; preserve the user's range.
      const range = chart.timeScale().getVisibleRange()
      const values = sorted()
      priceSeries.setData(values.map(pricePoint))
      volumeSeries.setData(values.map(volumePoint))
      if (range) chart.timeScale().setVisibleRange(range)
    } else {
      priceSeries.update(pricePoint(candle), historical)
      volumeSeries.update(volumePoint(candle), historical)
      incrementalUpdates++
    }
  }
  if (candleMap.size > MAX_CANDLES + 30) {
    const range = chart.timeScale().getVisibleRange()
    const values = sorted().slice(-MAX_CANDLES)
    candleMap = new Map(values.map(c => [c.time, c]))
    priceSeries.setData(values.map(pricePoint))
    volumeSeries.setData(values.map(volumePoint))
    if (range) chart.timeScale().setVisibleRange(range)
  }
  if (!fitted && candleMap.size) { chart?.timeScale().fitContent(); fitted = true }
  publishMetrics(start)
}
function lineData(point, key) { return point[key] == null ? { time: point.time } : { time: point.time, value: Number(point[key]) } }
function syncLine(series, prior, values, key, reset) {
  const next = new Map(values.map(point => [point.time, point[key]]))
  const previousTimes = [...prior.keys()]
  const nextTimes = [...next.keys()]
  const rebuild = reset || previousTimes.some((time, index) => time !== nextTimes[index]) || nextTimes.length < previousTimes.length
  if (rebuild) series.setData(values.map(point => lineData(point, key)))
  else {
    const lastTime = previousTimes.at(-1) ?? -Infinity
    for (const point of values) {
      if (!prior.has(point.time) || prior.get(point.time) !== point[key]) series.update(lineData(point, key), point.time < lastTime)
    }
  }
  return next
}
function syncStrategy(reset = false) {
  if (!fastSeries || !slowSeries) return
  const points = overlay.points.filter(point => candleMap.has(point.time)).sort((a, b) => a.time - b.time)
  fastPoints = syncLine(fastSeries, fastPoints, points, 'fast', reset)
  slowPoints = syncLine(slowSeries, slowPoints, points, 'slow', reset)
  const signals = overlay.signals.map(signal => ({ time: Number(signal.time ?? signal.candle_time), id: String(signal.id), position: signal.direction === 'UP' ? 'belowBar' : 'aboveBar', shape: signal.direction === 'UP' ? 'arrowUp' : 'arrowDown', color: signal.direction === 'UP' ? colors.up : colors.down, text: signal.direction, size: 1 }))
  const fills = overlay.fills.map(fill => ({ time: Math.floor(Number(fill.execution_ms ?? Number(fill.time) * 1000) / 60000) * 60, id: String(fill.id), position: fill.side === 'BUY' ? 'belowBar' : 'aboveBar', shape: 'square', color: '#8FB4FF', text: `${fill.side} FILL`, size: 0.75 }))
  const visible = [...signals, ...fills].filter(marker => candleMap.has(marker.time)).sort((a, b) => a.time - b.time || a.id.localeCompare(b.id))
  const nextMarkerKey = JSON.stringify(visible)
  if (reset || markerKey !== nextMarkerKey) { markers.setMarkers(visible); markerKey = nextMarkerKey }
}
function strategy(points = [], signals = [], fills = [], config = {}) {
  overlay = { points, signals, fills, config }
  syncStrategy()
}
function clearStrategy() { strategy([], [], [], {}) }
function fit() { chart?.timeScale().fitContent() }
function focus(time) {
  if (!chart || !Number.isFinite(time) || !candleMap.size) return
  const times = [...candleMap.keys()]
  const from = Math.max(Math.min(...times), time - 20 * 60)
  const to = Math.min(Math.max(...times), time + 12 * 60)
  if (from < to) chart.timeScale().setVisibleRange({ from, to })
}
function inspect(param) { emit('inspect', typeof param.time === 'number' ? param.time : null) }

onMounted(() => {
  chart = createChart(container.value, {
    autoSize: false,
    layout: { background: { type: ColorType.Solid, color: '#11161C' }, textColor: '#9AA7B5', fontFamily: "'SFMono-Regular', Consolas, monospace", fontSize: 11, attributionLogo: true, panes: { separatorColor: '#29323D', separatorHoverColor: '#607286', enableResize: true } },
    grid: { vertLines: { color: '#1B232D' }, horzLines: { color: '#1B232D' } },
    crosshair: { mode: CrosshairMode.Normal, vertLine: { color: '#607286', labelBackgroundColor: '#29323D' }, horzLine: { color: '#607286', labelBackgroundColor: '#29323D' } },
    rightPriceScale: { borderColor: '#29323D', minimumWidth: 88 },
    timeScale: { borderColor: '#29323D', timeVisible: true, secondsVisible: false, rightOffset: 5, barSpacing: 9, shiftVisibleRangeOnNewBar: true },
    localization: { locale: 'en-US', timeFormatter: time => new Date(Number(time) * 1000).toISOString().slice(0, 16).replace('T', ' ') + ' UTC' },
  })
  priceSeries = chart.addSeries(CandlestickSeries, { upColor: colors.up, downColor: colors.down, borderVisible: false, wickUpColor: colors.up, wickDownColor: colors.down, priceFormat: { type: 'price', precision: 2, minMove: 0.01 }, lastValueVisible: true })
  volumeSeries = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceLineVisible: false, lastValueVisible: false }, 1)
  fastSeries = chart.addSeries(LineSeries, { color: '#8FB4FF', lineWidth: 2, lineStyle: LineStyle.Solid, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: true }, 0)
  slowSeries = chart.addSeries(LineSeries, { color: '#D8B36A', lineWidth: 2, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: true }, 0)
  markers = createSeriesMarkers(priceSeries, [], { autoScale: true })
  priceSeries.priceScale().applyOptions({ scaleMargins: { top: 0.08, bottom: 0.08 } })
  volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.22, bottom: 0 } })
  chart.subscribeCrosshairMove(inspect)
  observer = new ResizeObserver(entries => {
    const { width, height } = entries[0].contentRect
    if (width > 0 && height > 0) {
      chart.resize(Math.floor(width), Math.floor(height))
      const panes = chart.panes()
      if (panes.length > 1) panes[1].setHeight(Math.max(80, Math.round(height * 0.23)))
    }
  })
  observer.observe(container.value)
  if (candleMap.size) snapshot(sorted())
})
onBeforeUnmount(() => { observer?.disconnect(); chart?.unsubscribeCrosshairMove(inspect); markers?.detach(); chart?.remove() })
defineExpose({ snapshot, update, fit, focus, strategy, clearStrategy })
</script>

<template>
  <div ref="container" class="market-chart" role="img" aria-label="Candlestick chart, aligned volume, fast solid blue and slow dashed gold moving averages, confirmed crossover arrows and square simulated fills. All times are UTC. Inspector and ledger provide accessible text values." />
</template>
