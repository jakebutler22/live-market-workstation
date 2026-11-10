<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { CandlestickSeries, ColorType, CrosshairMode, HistogramSeries, createChart } from 'lightweight-charts'

const emit = defineEmits(['inspect', 'performance'])
const container = ref(null)
let chart, priceSeries, volumeSeries, observer
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
function fit() { chart?.timeScale().fitContent() }
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
onBeforeUnmount(() => { observer?.disconnect(); chart?.unsubscribeCrosshairMove(inspect); chart?.remove() })
defineExpose({ snapshot, update, fit })
</script>

<template>
  <div ref="container" class="market-chart" role="img" aria-label="Candlestick chart with aligned volume pane. All times are UTC. The selected candle and recent candle table provide text values." />
</template>
