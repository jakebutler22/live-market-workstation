# Live Market Workstation design and data pipeline

The preserved Assignment 4.1 foundation records Yahoo Finance observations, builds one-minute candles, and replays the recorded availability sequence. The original 4.1 implementation had no trading/account features. Assignment 4.2 adds a simulated SMA strategy and historical engine as described in the final section; AI features remain out of scope. The default instrument is **BHP.AX**, an ASX equity quoted in AUD, with volume measured in shares. The captured source was active but approximately 20 minutes delayed. Receiving delayed messages is not evidence of fresh prices; the interface keeps source age visible.

## File responsibilities

| File | Responsibility |
| --- | --- |
| `backend/config.py` | Validated startup symbol and SQLite path. One symbol per backend process; fixed 60-second interval. |
| `backend/provider.py` | The single application-owned `yfinance.AsyncWebSocket`, valid-message watchdog, bounded retries, cleanup, and separate Yahoo minute-bar reconciliation. |
| `backend/market.py` | Validation, normalization, deterministic event-time candle reduction, corrections, interval completion, and coverage/provenance fields. No networking or wall-clock reads. |
| `backend/store.py` | SQLite schema initialization, accepted-event identity/deduplication, append-only revisions, atomic event/candle-version writes, and latest-state retrieval. |
| `backend/service.py` | Serialized ingestion, capture clock events, source status, persist-before-publish, and bounded per-browser queues. |
| `backend/replay.py` | A private reducer and frozen recording per browser. Replay controls and timing never write to capture storage. |
| `backend/main.py` | FastAPI lifespan, bounded retrieval routes, application WebSockets, and induced upstream interruption/resume. |
| `frontend/src/App.vue` | Live/replay state, socket lifecycle, source-age clock, accessible inspectors/table, and controls. |
| `frontend/src/MarketChart.vue` | One Lightweight Charts instance with candlestick and volume panes, incremental updates, older-candle corrections, resize handling, and cleanup. |
| `frontend/src/tokens.css`, `frontend/src/style.css` | Recorded design tokens and responsive financial-terminal layout. |
| `frontend/vite.config.js` | Local frontend on `127.0.0.1:5173`; `/api` and `/ws` proxy to FastAPI on `127.0.0.1:8000`. |

## Live path and boundaries

```mermaid
flowchart LR
  Y[Yahoo WebSocket] --> P[yfinance provider adapter]
  H[Yahoo 1-minute chart endpoint] --> P
  P --> N[Validate and normalize]
  N --> S[SQLite accepted events]
  S --> R[Deterministic candle reducer]
  R --> V[SQLite candle versions]
  V --> W[Application WebSocket]
  W --> U[Vue chart and inspectors]
  S --> Q[Per-browser replay reducer]
  Q --> U
```

Ingestion is serialized. An accepted event and its resulting candle versions are committed in one SQLite transaction before the service publishes the saved update. Published events include the internal `id`; candles include `last_event_id`, `last_quote_event_id`, and `volume_event_id` so source, receipt, database, and display can be traced. These are application identifiers, not Yahoo trade IDs.

The provider belongs to application startup, not a browser connection. Opening more browser tabs does not start more source listeners. The pinned yfinance1.8 compatibility wrapper `FiniteSocket` turns normal iterator exhaustion into a connection error (avoiding a library busy loop), and errors propagate with `yf.config.debug.hide_exceptions=False`. Listener cleanup is bounded as well as socket closure. A listener attempt has finite subscribe/quiet-source timeouts; five attempts use backoff capped at 16 seconds. Exhaustion remains visibly unavailable until an explicit resume. Shutdown cancels source/history/clock tasks and closes sockets and SQLite.

`/ws/live` registers its bounded queue and obtains the saved snapshot without yielding between those operations. The snapshot followed by queued updates prevents an HTTP-history/stream handoff gap. A slow browser receives a resync/close and reconnects for a fresh saved snapshot; capture does not wait for the browser. The frontend merges candles by interval key and protects mode changes with a connection-generation token so an old live response cannot enter a replay view.

| Interface | Meaning and bounds |
| --- | --- |
| `GET /api/health` | Backend/SQLite readiness, with upstream state reported separately. |
| `GET /api/status` | Source status, maximum accepted source timestamp, separate receipt time, saved counts, and errors. |
| `GET /api/history?limit=360` | Latest saved candles in time order; limit 1–600. |
| `GET /api/observations?limit=20` | Recent saved events; limit 1–100. |
| `GET /api/replay` | Recording bounds and replay availability. |
| `WS /ws/live` | Saved snapshot, committed event/candle updates, and status. |
| `WS /ws/replay` | Frozen recording; `start`, `pause`, `resume`, and `restart`, with bounded playback speed. |
| `POST /api/feed/pause`, `/api/feed/resume` | Induced Yahoo interruption/recovery. The application socket remains connected. |

The symbol accepts 1–20 uppercase letters/digits and Yahoo punctuation `. ^ = -`; requests cannot inject arbitrary URLs or database queries. Retrieval size is bounded. Change the startup `SYMBOL` and restart to capture another instrument; price/volume semantics must be verified for that instrument before relying on it.

## Provider fields and volume policy

Yahoo stream `id` identifies the symbol; it is not a unique observation/trade identifier. `price` is the quoted price in the instrument's currency. `time` is Unix milliseconds and may arrive as a protobuf int64 string. The backend validates a finite positive price, the configured symbol, and a plausible source timestamp. It preserves the decoded original payload inside normalized quote `payload.raw`.

The stream is a sampled quote feed. `day_volume` is a session-level cumulative counter, and `last_size` is not a complete interval trade-volume feed. Both are retained as source evidence and **neither is summed, differenced, or plotted as minute volume**. Consequently the application does not need a speculative cumulative-counter baseline/reset algorithm. Duplicates, counter resets, late counters, or counter corrections cannot inflate volume because those counters do not determine it.

Corresponding volume comes from Yahoo's **one-minute historical chart aggregates**, polled every 30 seconds, with a bounded initial history and the latest five bars reconciled thereafter. Raw chart JSON is read with Python's standard-library HTTP client to preserve JSON `null`: yfinance history conversion can coerce missing volume to zero. An OHLC row missing required prices is skipped; a missing volume remains `None`, appears as “—”, and produces chart whitespace rather than an invented zero-volume bar. Genuine reported zero remains zero. BHP.AX minute volume is share quantity, not AUD turnover.

Reconciliation records each accepted bar with the time it became available to this application. It does not retroactively pretend that the aggregate was available at its source interval. `volume_source`, `volume_event_id`, and `volume_asof_ms` identify this path and its lag. Polling lag is additional to Yahoo's instrument/source delay. A volume bar may remain unavailable or partial until Yahoo supplies it.

Price precedence is explicit: sampled quotes determine an observed candle when quotes exist until its vendor aggregate is finalized; an elapsed interval with a finalized vendor aggregate uses that aggregate's OHLC. A vendor-only interval uses vendor OHLC, including provisional OHLC when that is all Yahoo has supplied. Every displayed candle says whether its price came from sampled Yahoo quotes or the Yahoo one-minute aggregate. Volume always comes from the corresponding vendor interval, independently of price precedence. A later changed vendor aggregate creates a revision; it does not add to the earlier volume.

The newest vendor bar is provisional even if its interval precedes the local wall clock, because a delayed feed can still be reporting an unfinished source interval. A bar becomes vendor-finalized when a later source bucket is present. “Elapsed” and “finalized vendor aggregate” remain distinct. The application does not claim exchange-complete OHLC or trades from the stream.

## Time, identity, and candle rules

All stored times are UTC Unix milliseconds. Chart time keys use Unix seconds; the display explicitly labels **UTC**. Minute buckets are half-open: `[start, start + 60,000)`. An observation exactly at 09:31:00 belongs to the 09:31 interval, never the 09:30 interval. No empty candles are manufactured.

For sampled quotes, the reducer sorts by `(source_ms, fingerprint)`. Open is the first price, close the last, high the maximum, and low the minimum in that order. The hash is a deterministic application tie-breaker for distinct messages with equal source time; it does not assert an exchange execution order. Arrival order cannot move a late observation into the wrong bucket. An accepted explicit quote correction must retain its source timestamp; it removes the superseded active quote before recomputing that interval.

Exact quote duplicates use SHA-256 of canonical normalized useful payload, including the retained decoded source payload. Equal source timestamps alone never cause deduplication. Identical useful messages can collapse even if Yahoo emitted two indistinguishable observations, and changed payloads without a genuine provider identity cannot be automatically recognized as corrections. These are documented limits of this source. The backend supports explicit `supersedes_id` corrections for tests/integration contracts; it never infers that Yahoo supplied that ID. Corrections must reference the same source, symbol, and kind and supersede an active revision.

Minute-bar identity is `(source, symbol, kind='bar', start_ms)`. An identical normalized bar is ignored. A changed bar for that key is a new accepted revision that links to its predecessor. Repeated quote/bar duplicates do not alter candle OHLCV, create a false candle revision, or add another canonical observation. Lifecycle/feed/clock occurrences preserve their recorded order so repeated interruptions remain replayable.

A candle version changes only when its material displayed state changes. It preserves OHLCV, `revision`, ending boundary, elapsed/partial/capture/gap flags, quote count, price/volume provenance, and trace IDs. Up candles use their own `close > open`; down candles use `close < open`; equal open and close uses neutral muted gray. The volume bar always uses the same direction as its candle.

The reducer's clock advances monotonically from recorded receipt times. In live capture, the service records clock events when needed to close observed forming intervals; it does not create empty intervals. Replay sees those same close events. Ending an interval marks `elapsed`, not complete observation coverage. Sampled candles remain partial; capture beginning after a bucket boundary and source interruptions are separately flagged. Recovery preserves the affected gap flags. Late observations or reconciliations may revise an elapsed candle.

## SQLite and reconstruction

`Store` creates the configured parent directory and schema at startup. The default database is `data/market.sqlite3`; disposable tests use separate temporary or in-memory databases. WAL mode and foreign keys are enabled. Capture survives restarts and is not cleared for a clean Git tree.

| Object | Preserved data and constraints |
| --- | --- |
| `events` | `id INTEGER PRIMARY KEY AUTOINCREMENT`; source, symbol, kind; source and receipt timestamps; application identity and fingerprint; revision and nullable `supersedes_id` foreign key; canonical JSON payload. Unique `(source,symbol,kind,identity,revision)`. |
| `events_symbol_time` | Index on `(symbol,source_ms,id)` for trace/time access. |
| `events_kind_time` | Index on `(symbol,kind,source_ms,id)` for quote-status retrieval. |
| `events_fingerprint` | Index on `(source,symbol,kind,fingerprint)` for exact quote-repeat lookup. |
| `events_available` | Index on `(received_ms,id)` for availability inspection. |
| `candle_versions` | `(symbol,start_ms,revision)` primary key, triggering `event_id` foreign key, and complete candle JSON. Earlier versions remain available. |
| `latest_candles` | Latest revision for each symbol/interval; used by bounded history retrieval. |

Receipt IDs are the stable processing order, including ties and a possible operating-system clock adjustment. Original receipt values are preserved; the reducer clock never reverses. On restart, a new engine replays the accepted event log by ID. The latest saved candle view remains independently queryable; reconstruction must yield the same candle state. The duplicate-receipt counter is a process diagnostic, not an immutable total of every rejected network repeat.

## Replay and failure behavior

A replay connection freezes the saved event list at connection time and creates a fresh `CandleEngine`. It starts empty, applies each accepted observation/revision/feed/clock event in ID order, and spaces playback by nonnegative differences in original receipt times divided by speed. It never reads future candle revisions from `latest_candles`, uses today's clock to close every interval, or reinserts replay events into canonical live capture. Original source and receipt times and the original recording start are visible. Pause/resume retains position; restart reconstructs from zero; an empty recording and finished playback have explicit states. Live capture may continue independently while the display is in replay.

Backend source state, browser socket state, and source freshness are separate facts. A heartbeat does not change `last_source_ms`. Age is calculated from source time against the live browser clock, or against the recorded replay clock in replay. The full source age is always visible. For the verified delayed BHP.AX feed, stale status begins 30 seconds beyond its expected 20-minute delay; other symbols use 30 seconds unless their delay is explicitly verified and configured. The interface labels BHP.AX's published delay, so “receiving” does not imply real-time prices. Missing source time is unknown. Market closure is not inferred from silence or an old timestamp.

On an induced interruption, the backend stops Yahoo streaming and reconciliation, records the feed transition, retains saved candles, and leaves the browser/backend socket connected. The source time stays fixed while age rises. Resume starts one provider session; identity rules prevent exact repeats from double-counting. An application-socket failure has its own connection label and bounded frontend reconnect backoff. Neither failure erases the useful saved chart.

## Interface tokens, accessibility, and update cost

The actual tokens live in `frontend/src/tokens.css`. Long/short names are design-system terms; 4.1 had no trading controls, and 4.2 is long-only simulated accounting without a manual order ticket.

| Token | CSS variable | Value |
| --- | --- | --- |
| Background | `--background` | `#0B0E11` |
| Panel background | `--panel` | `#11161C` |
| Raised/control background | `--raised` | `#161D25` |
| Panel border | `--border` | `#29323D` |
| Hover/active divider | `--divider-active` | `#3B4858` |
| Interactive control boundary | `--control-boundary` | `#607286` |
| Primary text | `--text` | `#E7EDF4` |
| Muted text | `--muted` | `#9AA7B5` |
| Semantic up / long | `--up` | `#53C6A5` |
| Semantic down / short | `--down` | `#E6818A` |
| Focus / selection | `--focus` | `#8FB4FF` |
| Warning / stale | `--warning` | `#D8B36A` |

The shell uses CSS Grid/Flexbox, crisp one-pixel divisions, 0–2px corners, system sans-serif structure, and reliable local monospace numerals. Focus indicators, control boundaries, text labels alongside semantic colors, and keyboard-selectable interval rows make essential chart information available without hover. Status announcements are separate from ordinary tick updates. Small windows/zoom reflow or scroll without discarding controls. Reduced-motion preferences disable nonessential motion.

The chart is created once with one candlestick series and an aligned volume pane. Ordinary changes use `series.update`; corrections to existing older points use the library's historical-update flag. A newly appearing late interval requires a sorted reset with the visible range preserved. Bounded pruning also preserves the visible range. Initial snapshots/explicit Fit may fit content; ordinary updates do not repeatedly fit the chart. The frontend bounds displayed history while SQLite retains capture. Sockets, reconnect/age timers, crosshair listeners, resize observers, and charts are cleaned up on teardown.

The footer reports chart-update call duration measured with `performance.now`; backend status reports measured ingestion processing time. These measure local JavaScript/backend work, not completed screen paint or end-to-end Yahoo latency. During the actual browser audit, snapshot footers showed 0.00–0.20 ms chart-update calls; this is an observed sample, not a guaranteed frame budget. Actual verification results and remaining limits are in [verification.md](verification.md); source samples and browser/database evidence are in the repository's `evidence/` area.

The final browser audit caught two concrete defects: global table-cell styling widened a Lightweight Charts internal pane divider to 29 px, and mode reconnection briefly retained old replay status. Table styles are now scoped to the application's records table; the divider is 1 px. A mode reset clears previous status/timestamps/counts before its new snapshot, showing unknown/connecting rather than a stale replay value. Both fixes were checked in the actual browser and followed by a production build. [Curated browser observations](../evidence/browser-audit.md).

## Assignment 4.2 extension

The original root 4.1 report, recording, evidence and capture are preserved. The current implementation extends the same chart/feed/replay. Local numerical, independent-reference and browser outputs below are observed; exact hosted CI/publication verification remains in progress in [verification-4-2.md](verification-4-2.md).

### Responsibilities and storage

| File/object | 4.2 responsibility |
|---|---|
| `backend/strategy.py` | Pure Decimal configuration/validation, full-window SMA, equality-memory crossovers, pending orders, fills, fees/basis/P&L, audit/equity snapshots; no network/database/wall-clock dependency. |
| `backend/trading.py` | Original availability-ordered paper adapter, allowlisted dataset loading, deterministic isolated backtest IDs, SQLite results and chart/paper overview. |
| `backend/service.py` | Sends accepted stored events to the paper adapter and publishes account/indicator state alongside existing market updates. |
| `backend/main.py` | Strategy overview, bounded historical runs/retrieval and read-only replay indicator route. `CAPTURE_ENABLED=0` disables upstream startup for deterministic tests without disabling real local APIs. |
| `fixtures/historical/bhp-4-1.json` | Genuine read-only finalized Yahoo OHLC snapshot: 358 minute bars, immutable snapshot hash/provenance. |
| `fixtures/worked-eight.json` | Labeled synthetic assignment fixture with independent expected numerical/accounting values. |
| `strategy_runs` | SQLite `id TEXT PRIMARY KEY`, `kind`, `snapshot_id`, `last_event_id INTEGER`, `result TEXT` (JSON); stores `paper-v1` and isolated historical results in the existing configured database. |

`GET /api/strategy` returns paper state, datasets and chart points/signals/fills/config. `POST /api/backtests` accepts an allowlisted `dataset_id` (`yahoo-4-1` or `worked-eight`), optional fast/slow integers and UTC millisecond range. HTTP windows are bounded to `1 ≤ fast < slow ≤ 200`; engine configuration additionally validates its internal limits. Range end is exclusive by candle-start time. `GET /api/backtests/{id}` retrieves a stored historical result. `POST /api/indicators` accepts up to 600 candles and computes read-only batch indicator points; it cannot write orders or paper state. Historical engine inputs are bounded to 100,000 bars.

Historical run identity hashes snapshot SHA, strategy version `4.2-v1`, full configuration and selected range; cash/size/fees are fixed per allowlisted dataset. Repeating the same request returns its stored result, preserving economic determinism and keeping `paper-v1` isolated. The paper result is saved in the same SQLite file and rebuilt deterministically from original immutable market events on startup, so refresh/restart does not duplicate trades. The ledger is a frozen decision projection of original inputs, not a recomputation from corrected latest candles.

```mermaid
flowchart LR
  Q[Immutable quote event IDs] --> A[Availability-ordered paper adapter]
  H[Finalized Yahoo minute snapshot] --> B[Historical open then close adapter]
  A --> S[Shared Decimal SMA and ledger]
  B --> S
  S --> P[SQLite strategy_runs and isolated results]
  P --> V[Existing Vue chart and account/backtest inspectors]
  R[Independent pandas reference] --> T[Verification evidence]
  S --> T
```

### Indicator and accounting rules

Defaults for real BHP.AX paper/history are SMA(5)/SMA(20), AUD 10,000 starting cash, 10-share entry, AUD 1 per actual fill and zero slippage. The synthetic fixture uses 2/3, USD 1,000, two shares and USD 1 fees. Numeric inputs become Decimal from their stored string representation; calculations use precision 40. Indicator output keeps exact decimal strings plus floats for chart rendering. Display rounding never drives decisions. A fast/slow difference within `1e-10` is equal.

Each average includes its just-confirmed close and needs a full eligible window; otherwise it is null. The first nonzero side initializes without signaling. Equality retains that side; only a later opposite side emits one UP/DOWN. Gaps/ineligible bars reset windows and side. Duplicate completions, late revisions and older bars cannot rewrite emitted points or issue repeat orders. A new configuration/run keeps old rationale intact.

UP while flat creates a fixed-size BUY; DOWN while long sells the full position. Other signals create reasoned skipped orders (flat/no shorting, already long/no pyramiding, outside selected range or another pending order). Fill-time affordability includes the fee. Rejections change neither cash nor holdings. Entry fees are capitalized in total cost basis; exit fees reduce proceeds once. Marks preserve source time. Every snapshot exposes cash, held quantity, basis, mark/time, realized/unrealized P&L, fee total and equity; flat unrealized is zero. The invariants are equity = cash + marked holdings and equity − starting cash = realized + unrealized. Fills and completed round trips are separate counts.

### Paper availability versus historical final bars

Paper follows original market event IDs. Vendor bars do not feed paper decisions or fills. Finalized vendor aggregates can update the current account mark only when their interval end is no later than their receipt time and no older than the current mark. `mark_source`, `mark_event_id`, `mark_available_ms` and source time disclose that valuation input; this cannot change prior signals/orders/fills/equity snapshots. Initial capture-partial and flagged outage intervals are excluded; other fully observed sampled intervals may qualify without claiming complete exchange-trade coverage. A new interval's first accepted quote confirms the preceding sampled close. That event has already been consumed and cannot fill a new decision; only a subsequent accepted non-late quote can. Quotes with a correction link or source time older than the last processed source time are retained by 4.1 but ignored by paper, with an audit reason. Existing pending orders can execute before this quote confirms a later bar. The current forming bar never orders.

Paper's original sampled closes can differ from the visible corrected/finalized vendor chart; the UI must label that distinction. Late corrections never rewrite issued signals, orders, fills or historical account snapshots. A missing-minute jump or marked outage resets warm-up rather than filling fictional prices.

The genuine snapshot `yahoo-4-1` contains **358** finalized vendor bars from **2026-11-09 23:00 through 2026-11-11 03:22 UTC**, AUD/share units, raw Yahoo OHLC without application adjustment. Snapshot SHA-256: `919fe8716db104587c8f376b0552b865a61cd44f15cae0393b4c4f874bc5fa4d`. It was extracted read-only from original canonical 4.1 capture; vendor revision receipt history is not reconstructed. Source event IDs are retained. Recorded capture gaps are provenance, while genuine final vendor bars can still supply historical data; structural missing-minute gaps reset historical windows.

Historical chronology is explicit: at a new eligible bar open fill an already-pending order; only then reveal its close, update confirmed SMA and create a later pending decision. Final OHLC is assumed available at close. Earlier bars may warm up a selected start but cannot create actionable pre-start trades. A final pending order expires without a subsequent eligible price. Open positions are marked at the final known close; no forced liquidation occurs.

### Observed local verification and publication boundary

The default genuine historical run returned **9,990.74999237060544 AUD equity**, total P&L **−9.25000762939456 AUD**, return **−0.0925000762939456%**, 14 signals/orders, 11 fills, five completed round trips, 10 shares open and 11 AUD fees. Cash was 9,388.04998779296874; open basis 600.8500061035156; mark 60.27000045776367; realized P&L −11.10000610351566 and unrealized +1.8499984741211. The first historical UP at source candle time `1794266820` created a buy filled at next open `1794266880`, 59.875 × 10 plus 1 fee, leaving cash 9,400.25 and basis 599.75. The same economic result was observed through the actual browser; saved run `bt-1467499c08ac8d946575` and its snapshot are reproducible offline. Hosted Actions still requires the final pushed implementation SHA.

The supplied eight-bar fixture returned 990 equity, −10 realized, zero shares, two fees/two fills and one completed round trip. Final local checks passed: 45 backend tests +19 subtests, three independent pandas cases (maximum difference 1.4210854715202004e-14 at 1e-10 tolerance, no mismatches), 14 exact batch/incremental prefixes, two actual frontend/backend browser tests and a production build. Browser inspection confirmed both labeled SMA lines, UP/DOWN arrows, separate square fill markers and the linked account trace. Tests cover forming reversals, duplicate completions, affordability, final unfilled orders, future-data/revision prefix immutability, isolated repeat runs/restart and mark-only vendor updates. The workflow triggers on pushes to the submitted branch and uses disposable offline services; its exact hosted result, the milestone review/commit and anonymous access to the already-recorded 55-second 4.2 video remain pending. Actual evidence and commands are in [verification-4-2.md](verification-4-2.md).

### Final presentation review

The user delegated the review and requested a more natural interface (`prompts/04-review-and-polish.md`). The final pass uses sentence-case headings, larger essential text, a readable four-step crossover/order/fill/account story and expandable source/execution records. IDs and full timestamps remain available; the record shows unrounded execution prices. The original tokens, chart semantics, backend accounting and live/replay separation are unchanged. The final 1440×900 and 1280×800 screens, keyboard access, build and browser checks were observed again after these edits. AI assistance remains disclosed in `AI-USE.md`.
