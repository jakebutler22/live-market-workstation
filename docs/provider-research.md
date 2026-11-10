# Yahoo provider check — 9 November 2026 (New York)

Research used current primary documentation and the yfinance **1.8.0** tag. The probes below used Node.js 24.12.0's built-in WebSocket and `fetch`, with no installed packages. They establish provider behavior; they are **not** evidence that the application's yfinance adapter works. Application integration was subsequently captured separately in [app-live-trace.json](../evidence/app-live-trace.json); the direct probes remain a distinct evidence category.

## Verified interface and fields

- [AsyncWebSocket API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.AsyncWebSocket.html): construct with `verbose=False`; await `subscribe(symbols)`, `listen(async_handler)`, and `close()`. Default upstream is `wss://streamer.finance.yahoo.com/?version=2`.
- [Pinned implementation](https://github.com/ranaroussi/yfinance/blob/1.8.0/yfinance/live.py): incoming JSON contains base64 protobuf; `MessageToDict(..., preserving_proto_field_name=True)` produces snake_case. Protobuf int64 values can arrive as JSON strings. The library resubscribes every 15 seconds. Its default listener can retry indefinitely; `_connect()` only opens when `_ws is None`.
- [Pinned protobuf definition](https://github.com/ranaroussi/yfinance/blob/1.8.0/yfinance/pricing.proto) lists `id`, `price`, `time`, `day_volume`, `last_size`, and `vol_24hr`. It contains no trade identifier, sequence, or correction identifier. Actual samples establish that `id` is the requested ticker and `time` is Unix **milliseconds**, not seconds. Preserve all useful decoded fields; do not call an application fingerprint a Yahoo ID.

A sample source time `1794268534000` becomes `2026-11-09T23:55:34.000Z`. Backend receipt was `2026-11-10T00:15:35.834Z`; those times must remain separate.

## Actual bounded probes

[First probe](../evidence/provider-sample.json) connected at `2026-11-10T00:14:37Z`, subscribed to AAPL, BTC-USD, ES=F, GC=F, and EURUSD=X, and resubscribed every 15 seconds for 45 seconds. Received BTC-USD (9) and EURUSD=X (25); no AAPL, ES=F, or GC=F messages arrived in that window. Absence during one window does not establish permanent unsupported status.

[Alternate probe](../evidence/alternate-provider-sample.json) connected at `2026-11-10T00:15:35Z` for 35 seconds. Received BHP.AX (9) and 7203.T (20). BHP.AX supplied price, valid source time, exchange ASX, day volume, and last size; observed price changed from approximately AUD 59.87 to 59.90. Tokyo messages omitted `price`, so they must be rejected as price observations rather than filled with a prior price.

Both files retain raw base64, decoded fields, UTC receipt/source times, subscription events, and actual Yahoo 1-minute chart responses. They contain public market data only.

## Instrument and volume decision

**BHP.AX** is the strongest instrument observed during this evening New York session. Yahoo chart metadata identifies an equity quoted in AUD. Historical 1-minute rows contain usable positive volumes, including 9,283 and 4,018 shares. [Yahoo's exchange-delay table](https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html) specifies a **20-minute** delay for `.AX`; the stream showed approximately 1,201–1,202 seconds of source age. [Yahoo's BHP.AX page](https://au.finance.yahoo.com/quote/BHP.AX/) labels the ASX quote delayed and currency AUD. [ASX's educational volume explanation](https://game.asx.com.au/static/images/17_ssmg_supplementary_lesson1_asxcharts_st.pdf) defines equity volume in shares traded over a time interval.

Use genuine Yahoo chart **1-minute interval volume**, with explicit vendor provenance and reconciliation lag. Never sum stream `day_volume` or `last_size`: the stream is sampled and does not establish a complete trade tape. For BTC-USD the actual sample had `day_volume = last_size = vol_24hr = 27459139584`; those fields cannot safely be interpreted as interval traded BTC volume. EURUSD=X supplied no volume. ES=F historical 1-minute volumes were positive but its stream did not produce observations during the probe.

Keep interval volume nullable. Preserve raw null; do not turn unknown volume into zero. Do not interpret a non-minute-aligned final chart point with zero volume as a completed minute. Historical retrieval may revise a prior interval; store each accepted revision and retain its receipt time. Stream-derived sampled OHLC and vendor interval volume must remain distinguishable in the inspector.

[The pinned quote parser](https://github.com/ranaroussi/yfinance/blob/1.8.0/yfinance/utils.py#L501) maps Yahoo `indicators.quote[0].volume` to Volume and reads history timestamps as Unix **seconds**. [The pinned historical implementation](https://github.com/ranaroussi/yfinance/blob/1.8.0/yfinance/scrapers/history.py#L586) fills missing Volume with zero. A small bounded backend request to Yahoo's same `/v8/finance/chart/{symbol}?interval=1m&range=1d` endpoint preserves nulls losslessly. Use unadjusted prices and no synthetic gap-filling.

## Adapter recommendation

Create one provider task per configured application capture, independent of browser WebSocket connections. Pin the package version. Set the supported `yf.config.debug.hide_exceptions = False` so listener errors propagate, then own a finite attempt count, bounded exponential backoff, subscription deadline, no-observation watchdog, and bounded close in the adapter. Always construct a fresh `AsyncWebSocket` per attempt; do not rely on its internal reconnect behavior. Ensure cancellation and shutdown also cancel its heartbeat task.

Report actual source age continuously. BHP.AX can be receiving normally while quotes are 20 minutes delayed: expose both facts and the raw age. A receipt heartbeat never updates source time. Detect additional staleness beyond the declared delay and source silence separately. Do not infer market closure solely from absent messages or undocumented `market_hours` numeric codes.

Without a provider trade identity, fingerprint the complete normalized useful observation for exact deduplication; retain different observations sharing a timestamp. Document deterministic event-time ties. Do not infer a Yahoo correction solely because timestamps match. Stable historical interval identity provides a real correction/revision path without inventing a provider correction ID.
