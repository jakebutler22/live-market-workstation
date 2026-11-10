You are my principal engineer and product designer for the Live Market Workstation in the currently selected Codex project.

Complete only Assignment 4.1, Market Data and the Dashboard. Deliver a working, polished local application and the materials needed for its submission. Prioritize complete rubric coverage, correct data handling, and verifiable behavior. Build the intended visual quality into the first working interface.

Inspect the project, make a short plan, and carry out the implementation. Do not stop at recommendations or a scaffold. Continue until the work is verified or a specific approval, unavailable service, or missing external input genuinely blocks it.

## 1. Scope and source of truth

The required stack is **Vue, Python with FastAPI, and SQLite, running on localhost**. Reuse the project's compatible structure and working code.

Part 4.1 requires:

- A real Yahoo Finance streaming connection and WebSocket communication to the frontend.
- A charting library displaying updating candlesticks and corresponding volume.
- Visible data source, source-data age, and feed status.
- SQLite persistence and retrieval of market observations, with identity, source and receipt times, revisions, and candle-completion information preserved.
- Replay of recorded observations.
- Defined and tested handling of duplicates, revisions, and out-of-order observations.
- Evidence tracing live source to backend, chart, and database, including an unavailable-feed condition.
- Current README, agent instructions, design/data-flow/schema notes, and documented database initialization and startup.
- A submission report named `report.md`, with the GitHub repository URL, exact submitted commit, supporting evidence links, and an accessible 30–60-second demonstration-video link.

Keep this milestone narrow. One well-supported symbol and one candle interval can satisfy it. Use a configurable symbol and default to a one-minute interval unless the existing implementation or verified provider behavior justifies another choice.

**Do not add moving averages, trading signals, orders, positions, P&L, backtesting, AI features, chat, vision, or audio.** Do not add deployment, authentication, broker connections, a CSV-import feature, or a new CI system. Those are outside this submission. Preserve unrelated existing work.

The instructor's candlestick lesson informs chart semantics. It does not require automated pattern recognition or a TradingView paper-trading integration.

## 2. Inspect first and follow the course workflow

Read `README.md`, `AGENTS.md`, `handoffs/current.md`, relevant docs, source files, dependency manifests, and lockfiles when present. Check the actual repository root, current branch, remote, and uncommitted work. Do not assume the folder is empty or that earlier work is correct.

Report a concise gap list mapping the 4.1 requirements to existing functionality. State the files you expect to change and the checks you will run. Make routine implementation decisions yourself.

Use **CHECK → TAKE ACTION → VERIFY**.

- CHECK the installed Python/Node versions and project dependencies.
- Before a new dependency installation that has not already been authorized, show the missing packages, exact commands, and target environments. Follow the course's approval checkpoint. Reuse approvals already given.
- VERIFY the resulting versions/imports and application behavior.

Keep dependencies local to this project. Prefer existing tools and a small implementation. Do not install unrelated skills, global packages, docking frameworks, or infrastructure.

Use a scoped feature branch where appropriate, preserving existing changes. Do not blindly switch to main, reset files, or overwrite another project. Initialize Git only if needed in the confirmed project root.

Implement in small verified steps. Establish the backend configuration, provider adapter, and routes before wiring the frontend. Inspect real backend responses at the actual running address. Then prove one frontend-to-backend round trip before extending the interface.

Preserve these meanings in `AGENTS.md`.

- **SmokeTest** runs verification without editing application code.
- **AutoLoop** runs the agreed check, inspects the failure, makes the smallest in-scope fix, and reruns it. Stop after success, five correction cycles, or a genuine blocker. Report what remains unverified.

Do not repeatedly request permission for routine edits or checks already authorized here. Follow the supplied Vibe Checks for dependency approval and personal review before commits. Prepare the complete diff, verification results, and a short personal review checklist before asking for that review. Reuse any commit/push authorization already given.

## 3. Build the real market-data path

Use a small, understandable architecture.

**Yahoo Finance → backend provider adapter → validation/normalization → SQLite and candle processing → application WebSocket → Vue chart.**

Use the supported yfinance streaming interface, such as `AsyncWebSocket`, after checking the installed version and current documentation. Historical Yahoo requests may seed or reconcile chart history, but they do not replace proof of real incoming Yahoo WebSocket observations.

Start by inspecting a small actual provider sample. Establish the meanings and units of its price, symbol, timestamps, volume fields, and any available identifiers. Do not invent fields or interpret session-level statistics as interval statistics.

Keep the provider integration in the backend. Give it finite connection/retry behavior, bounded backoff, clean shutdown, and clear error reporting. Avoid duplicate ingestion tasks when a browser reconnects. Validate requested symbols and bound retrieval ranges.

Keep provider communication, market-data rules, persistence, and presentation separated. Map these responsibilities to the actual files in the design notes. Use the smallest structure that makes them understandable.

Provide the necessary health/status, historical-data retrieval, replay, and streaming interfaces. Reuse sensible existing route names. A connected frontend socket must not imply a healthy Yahoo source. Track upstream availability separately from browser connectivity and data freshness.

Persist accepted observations before publishing corresponding updates as saved. Include enough identifiers in backend events to trace a displayed result to its database records. Ensure initial history loading and subsequent streaming updates do not lose or double-apply observations.

### Candle correctness

Store times consistently in UTC and label the chart's display timezone. Define explicit interval boundaries, such as `[09:30, 09:31)`. An observation at 09:31 belongs to the next interval.

Derive open/close from event chronology with a documented tie-breaker, and high/low from the relevant interval's observations. Do not let arrival order incorrectly determine a late observation's place in the candle.

A candle's color follows its own close versus its own open. Use the same direction for its volume bar. Choose and document a neutral treatment for equal open and close.

Distinguish forming candles from elapsed intervals. Also track incomplete observation coverage, missing data, or connection gaps. An interval ending does not prove that every trade in it was observed. Allow a late accepted correction to revise a previously closed candle.

If the stream provides sampled quote observations rather than a complete trade feed, describe the resulting candles accurately. Do not claim exchange-complete OHLC from incomplete observations. Label partial capture, especially when recording begins midway through an interval. Do not manufacture candles for periods without observations.

### Volume correctness

Verify volume semantics before coding the chart.

Use genuine interval volume when available. If deriving volume from a cumulative counter, preserve the baseline and handle duplicate messages, session resets, late arrivals, and corrections. Do not sum cumulative daily totals or put a session's full volume into every candle.

If a counter is rolling, its units are unclear, or an update cannot be assigned reliably to an interval, do not silently treat it as traded interval volume. Use a documented Yahoo interval-volume reconciliation where appropriate and label its timing or coverage limitations. Keep historical and stream-derived values distinguishable, with an explicit precedence policy.

Unknown volume is unknown, not zero. Display an unavailable/partial state where needed. Missing current volume is a limitation, not a reason to fabricate bars or declare the requirement complete. Demonstrate usable corresponding volume for the submitted instrument and disclose any live-volume lag.

### Freshness and failure states

Show Yahoo Finance as the data source, the symbol and interval, the source timestamp, and age derived from source time. Preserve backend receipt time separately. A browser heartbeat must never reset source-data age.

Represent connecting, receiving, stale, disconnected/unavailable, and replay states meaningfully. Show market-closed status only when supported by reliable instrument/session information; otherwise state what is actually known. If source time is absent or invalid, make that uncertainty explicit.

Retain useful chart history during failure while clearly identifying its age and status. Implement recovery without double-counting or mixing stale responses into the wrong symbol/session.

## 4. Persist and replay without losing history

Use the project's actual SQLite database with documented initialization. Restarting the application must retain captured observations. Keep disposable test databases separate.

Choose a compact schema that preserves:

- A stable internal receipt/event identifier and deterministic processing order.
- Provider/source and symbol.
- Source event time, backend receipt time, and available provider identity.
- The original useful payload or sufficient lossless fields to explain normalization.
- The application's identity/deduplication policy and accepted revision history.
- Candle key, interval start/end, OHLCV, revision/version, completion state, and relevant coverage/provenance flags.

A practical design can use an immutable observation log and versioned candle records with a latest-state view. Adapt to existing code rather than introducing an elaborate event framework. Use transactions and appropriate uniqueness/index rules.

Do not assume timestamp alone uniquely identifies an observation. Use a provider identifier when genuinely available; otherwise document the deterministic fingerprint and its limits. Never silently claim an application-generated identifier came from Yahoo.

Explain and test each case.

1. An exact duplicate does not double-count price/volume or create a false revision.
2. An accepted correction preserves the earlier version and updates the affected chart result.
3. A late observation affects the correct interval, with stable event-time ordering and documented tie handling.
4. A restart reconstructs the same persisted state.

Replay must read persisted observations or immutable recorded revisions and reproduce the defined processing behavior. Keep the original source and receipt timestamps. Use a replay clock and stored availability order with a stable tie-breaker, rather than leaking future revisions from the final current-state table.

Record or deterministically reproduce any interval-close events needed for faithful replay. Do not use today's wall clock to mark every replayed candle complete immediately.

Provide simple start, pause/resume, and restart behavior, plus an unmistakable **REPLAY** label and original recording time. Isolate replay from live chart state and avoid reinserting replayed data into the canonical live capture.

Handle an empty database and the end of a replay cleanly. Replay must work while the live source is unavailable. A clearly labeled synthetic fixture may support automated tests, but it cannot be presented as a recorded Yahoo session or evidence of live streaming.

## 5. Build the polished 4.1 interface immediately

Act as a principal design engineer for a compact financial terminal. Make the initial implementation feel deliberate and professional.

Before implementing the UI, output a **Workstation Token Manifest** and record the actual tokens in the project. Use these exact starting values.

| Token | Hex |
| --- | --- |
| Background | `#0B0E11` |
| Panel background | `#11161C` |
| Raised/control background | `#161D25` |
| Panel border | `#29323D` |
| Hover/active divider | `#3B4858` |
| Interactive control boundary | `#607286` |
| Primary text | `#E7EDF4` |
| Muted text | `#9AA7B5` |
| Semantic up / long | `#53C6A5` |
| Semantic down / short | `#E6818A` |
| Focus / selection | `#8FB4FF` |
| Warning / stale | `#D8B36A` |

The long/short token names describe the design system; this milestone has no trading controls. Apply up/down colors to candle direction.

Use a flexible CSS Grid/Flexbox layout with constrained panels and correct overflow handling. Do not build a drag-and-drop docking framework or rely on a fixed absolute-positioned page that breaks on resize.

The essential surfaces are:

- A compact top bar with project identity, symbol/interval, and clear LIVE or REPLAY context.
- A dominant candlestick chart with aligned volume and a readable OHLCV/time inspector.
- A compact feed/capture inspector showing real source/receipt information, completion/revision details, and enough stored-record information to verify persistence.
- Small replay controls and a restrained status area.

Combine surfaces where useful. Do not create decorative order books, trade tapes, positions panels, giant KPI cards, or nonfunctional navigation.

Use sharp 0–2px corners, crisp 1px dividers, and mostly 4–8px internal spacing. No large-radius cards, oversized whitespace, ambient glow, gradient blobs, playful illustrations, or drop-shadow dashboard tiles. Do not use pure `#00FF00` or `#FF0000`.

Use Inter or a suitable system sans-serif for structural UI. Use JetBrains Mono, IBM Plex Mono, or a reliable monospace fallback for numbers, tickers, quantities, and timestamps. Reuse available fonts sensibly; do not block the interface on remote font loading.

Use tabular numerals and consistent numeric precision. Reserve adequate column width for changing prices, signs, timestamps, and status text. Keep the layout stable during updates. Do not solve density by shrinking all text into illegibility.

Prefer a maintained charting library already present. If none exists, use Lightweight Charts unless inspection identifies a concrete incompatibility. Check the installed-version API and preserve its required attribution.

### Usability and accessibility

All essential controls must work with the keyboard and have visible focus and accessible names. Avoid hover-only access to necessary information. Give chart data an accessible text/table representation, reusing the inspector where possible.

Maintain at least 4.5:1 contrast for ordinary text and 3:1 for essential non-text controls and focus indicators. Decorative dividers can remain subtle when they are not the sole way to identify a control.

Use at least 24-by-24 CSS-pixel pointer targets; 28–32px compact control heights are a useful default. Dense visual spacing does not require tiny clickable areas.

Pair state colors with text, signs, or other cues. Honor reduced-motion preferences. Announce connection/state changes appropriately without sending every tick to a screen-reader live region.

Check laptop-sized layouts and browser zoom. Reflow or permit sensible scrolling instead of clipping controls. A separate mobile app is outside this assignment.

### Performance self-audit

Create chart instances once and update them incrementally. Avoid rebuilding full series, deep reactive histories, or the entire dashboard for every observation. Use the chart library's supported historical-correction path for older revised candles.

Keep displayed history bounded while preserving captured records in SQLite. Any batching of visual updates must preserve the actual ingested observations and final displayed state.

Clean up sockets, listeners, timers, and resize observers. Resize charts correctly. Preserve user zoom/pan during normal updates instead of repeatedly fitting all content.

Use immediate control feedback. Optional tick highlights should be brief, restrained, and disabled for reduced motion. Treat zero latency as an interaction aspiration; report measured behavior rather than claiming impossible zero network delay.

## 6. Verify behavior and collect real evidence

Run meaningful checks targeted at the rubric and actual implementation. Do not inflate the test count with trivial assertions.

Cover:

- A hand-calculated OHLCV example and interval-boundary behavior.
- Exact duplicates, accepted revisions, and out-of-order arrivals.
- Applicable volume baseline/reset/correction behavior.
- Forming versus closed candles and partial coverage.
- SQLite retrieval after a process restart.
- Deterministic replay with correct chronology, revisions, and state isolation.
- Feed unavailability, increasing source-data age, recovery, and no double-counting.
- Real frontend rendering and essential control behavior.

Use fixtures for repeatable edge cases. Use an actual Yahoo connection separately for integration evidence. State which results are mocked, recorded, or live.

Operate the actual application in a browser. Confirm that incoming Yahoo observations update the candlestick/volume display and correspond to persisted records. Inspect the database directly with a viewer or SQL query. Trace at least one identifiable observation from provider receipt through the backend and into both the database and UI.

Exercise an unavailable-feed condition through the real application path. A controlled interruption is acceptable when labeled as induced. Verify the visible state, stale-data treatment, and recovery. Distinguish upstream failure from a browser/backend disconnection.

Capture relevant browser observations/screenshots and concise redacted logs in the repository's evidence area. Inspect the finished layout at approximately 1440×900 and 1280×800, plus increased zoom. Check keyboard use, focus, clipping, numeric stability, and obvious console errors. Fix concrete defects within scope.

If the market is closed, use real recorded observations for replay and investigate another Yahoo instrument only after verifying its price/volume semantics and availability. Never substitute invented motion for a live demonstration. If live proof remains unavailable, mark that requirement unverified and provide the exact remaining capture step.

If browser automation is unavailable, run every other possible check and provide a precise manual browser checklist. Do not claim to have observed a browser result you did not observe.

## 7. Finish the documentation and submission materials

Keep documentation concise and aligned with the system that actually exists. Reuse existing equivalents instead of duplicating files.

Maintain:

- `README.md` with purpose, stack, tested prerequisites, installation, startup, actual ports, database path/initialization, live/replay operation, verification commands, and limitations.
- `AGENTS.md` with the project boundaries, responsibilities, approval rules, SmokeTest, and AutoLoop.
- `docs/design-pipeline.md` with the file map, component responsibilities, data flow, SQLite schema, timestamp/identity/revision rules, candle/volume semantics, and design tokens.
- `docs/verification.md` with repeatable checks and results actually observed.
- A compact evidence log linking important prompt excerpts, changed files/commits, observations/tests, decisions, and unresolved limitations. Record genuine failures or revised approaches if they occur; never invent one.
- `prompts/01-assignment-4-1.md` containing this implementation prompt.
- `handoffs/current.md` with branch, last verified commit when available, completed/unfinished work, checks run, and the exact next step.
- `AI-USE.md` describing actual planning/coding tools and models used. Include this ChatGPT prompt-building assistance and the Codex setup actually used. Verify names when available; do not invent model versions or usage history.

Keep credentials and private information out of code, prompts, logs, screenshots, and recordings. Exclude local secrets and disposable environments from Git. Provide an example configuration only if configuration is needed. Do not erase captured observations to make the repository appear clean.

Create `report.md` for Assignment 4.1. It must include:

1. What was completed, mapped to the 4.1 requirements.
2. Key design decisions and how the real data path works.
3. Verification results with links to supporting evidence and documentation.
4. Remaining limitations and anything not yet verified.
5. The actual GitHub repository URL and exact commit identifying the submitted implementation.
6. An accessible link to one 30–60-second demonstration video.

Use plain, specific language that I can understand and explain. Distinguish implementation status from submission-package status.

Prepare a short demo run sheet using the actual app. A workable sequence is live updates and freshness, an identifiable persisted record, replay, and the unavailable-feed state. Keep the total between 30 seconds and one minute.

If recording tools are available, record the real application after it works. Otherwise prepare the exact recording steps and narration. Do not fabricate a recording or a URL. Part 4.1 does not need a separate process-screencast video.

Follow the reviewed Git milestone workflow. Before the required personal review, show the scoped diff and verification results. Once authorized, commit/push the verified work to the actual repository, confirm the remote version, and use its real commit identifier. Do not guess a remote or change repository visibility.

If a repository URL, recording, video link, instructor-access check, or review remains outstanding, finish everything else and identify only the remaining action. Draft placeholders must be unmistakable and must not appear in a report claimed to be submission-ready.

**Canvas receives only `report.md`.** Source code stays in the linked GitHub repository. The instructor must be able to access the repository and video. Do not submit to Canvas for me.

## 8. Final handoff and stopping condition

End with a concise handoff containing:

- What works and the local startup/address instructions.
- A 4.1 requirements matrix marked verified, partially verified, or blocked, with evidence paths.
- Actual automated, browser, database, live-feed, and performance observations.
- The report path, repository/commit information, and video status.
- Any precise action I still need to take before uploading `report.md`.

Do not declare submission readiness while live evidence or required accessible links are missing. Once the required 4.1 behavior and submission preparation are complete, stop. Do not begin Part 4.2 or add optional features.

## Technical references

Check current documentation against the versions actually installed.

- yfinance streaming: https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html
- yfinance AsyncWebSocket: https://ranaroussi.github.io/yfinance/reference/api/yfinance.AsyncWebSocket.html
- Lightweight Charts: https://tradingview.github.io/lightweight-charts/docs
- Series updates and historical corrections: https://tradingview.github.io/lightweight-charts/docs/api/interfaces/ISeriesApi
- Text contrast: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- Pointer target sizing: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html

**Begin by inspecting the selected project and reporting the 4.1 gap list, dependency needs, token manifest, and implementation sequence. Then proceed with the authorized work.**
