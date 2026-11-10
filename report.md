# Assignment 4.1 — Market Data and the Dashboard

**NOT READY TO SUBMIT.** The application and core browser/data checks pass. The GitHub destination, verified pushed implementation commit, accessible video URL and instructor-access checks remain missing. Commit/push authorization has been received. No publication link or commit is invented.

## Assignment and project

**Live Market Workstation** is a local Vue/FastAPI/SQLite application for Yahoo Finance streaming, updating one-minute candles and volume, durable capture and recorded replay. This submission covers Part 4.1 only.

## Repository and submitted version

- **GitHub URL: MISSING.** The local repository has no remote. The connected account did not identify a matching project; the intended destination has been requested.
- **Full tested implementation SHA and direct commit URL: MISSING.** The user approved the reviewed commit and push. The local implementation commit is being frozen; remote confirmation awaits the actual repository destination.

Application, test and dependency file hashes are frozen in `evidence/tested-source-manifest.json`. That SHA-256 manifest is not a Git commit. After publication, this report will identify the frozen tested implementation commit explicitly, even if the completed report is committed separately.

## Demonstration video

**Accessible URL: MISSING. Verified duration: 55 seconds.** The real demonstration is saved as `evidence/demo-4-1.mp4` (H.264, 1440×900, 3.3 MB, silent). It shows live Yahoo updates, the saved observation payload, recorded replay with pause/resume, and an induced upstream interruption. It was captured as 205 real browser frames with their actual elapsed timing, then encoded with the system video framework. Decoded MP4 frames and database records were checked; `evidence/demo-video.json` records the results and file hash. Upload/access remain unverified pending the actual publication destination.

## Completed work

These evidence filenames identify prepared materials. Full commit-pinned GitHub links remain unavailable until the actual repository and implementation SHA exist; filenames are not presented as instructor-accessible links.

| Part 4.1 requirement | Observed behavior and evidence |
|---|---|
| Yahoo streaming and frontend WebSocket | Real yfinance observations reach the backend, SQLite and rendered Vue chart. Displayed quote **545** and candle **v12** match SQL exactly: `evidence/browser/trace-sql.json`. |
| Updating candlesticks and volume | Lightweight Charts renders aligned candles/volume. Keyboard selection displayed **5,451 shares** for 00:36–00:37 UTC. Current unknown volume stays unavailable: `evidence/browser/selected-volume-keyboard.jpg`. |
| Source, freshness and completion | Yahoo source, source/receipt timestamps, age, delay, independent upstream/app state, revisions and elapsed/partial coverage are visible: `evidence/browser/live-final.jpg`. |
| SQLite history and restart | Immutable events and versioned candles preserve identity, payloads, timestamps, revisions and coverage. A real restart retained exact digests of **129 events/127 versions**: `evidence/restart-after.json`. |
| Recorded replay | Start/pause/resume/restart and original recording time were observed. Replay while Yahoo was paused left canonical count **606** unchanged: `evidence/browser/replay-while-source-paused.json`. |
| Duplicates, revisions and late arrivals | **29 tests plus 14 subtests** pass, including hand-calculated candles, boundaries, duplicate/correction chains, equal-time ties, late arrivals and replay isolation: `evidence/runtime-tests.txt`. Edge cases use labeled fixtures. |
| Live trace and unavailable feed | An induced UI interruption retained history and app connectivity while age rose **20m 11s→20m 25s**. Resume recovered real quote **621**: `evidence/browser-audit.md`. |
| Documentation and startup | README, AGENTS, design/schema notes, verification, AI disclosure and prompts match the application. Locked local installation, one-command startup and automatic/explicit SQLite initialization are documented. |

## Key design decisions

The path is **Yahoo → provider adapter → validation → SQLite/candle processing → application WebSocket → Vue chart**. One backend-owned upstream session serves all browsers. Observations and candle versions commit together before saved updates publish. SQLite's immutable event log and versioned candle records retain the earlier accepted state; retrieval reads the latest saved view.

Times are UTC and minute intervals are `[start,end)`. Sampled quote open/close follow source chronology with a deterministic fingerprint tie-breaker. Late data can revise elapsed candles; elapsed time does not imply complete trade coverage. Colors follow each candle's own close/open, including its volume bar; equal prices are neutral.

Yahoo exposes no genuine trade/correction ID here. Exact normalized-payload fingerprints suppress indistinguishable duplicates; differing same-time messages remain separate observations. Explicit application correction links and stable vendor minute-bar identity preserve revisions. Raw Yahoo minute aggregates supply interval volume and finalized historical OHLC; stream session counters are never summed, and null volume remains unknown. Replay uses original availability order and recorded clock events, without future revisions or canonical writes.

The compact terminal uses the specified tokens, numeric/source inspectors, accessible candle table and small replay controls. Default **BHP.AX** has AUD prices, share volume and a published **20-minute ASX delay**. LIVE means an actual subscription, not instantaneous exchange data.

## Verification results

- **Actual live/browser/SQL:** quote 545 was received at **00:57:36.702 UTC**, source **00:37:34 UTC**, price **AUD 59.96**. Stored candle v12 matches displayed O 59.94 / H 59.96 / L 59.93 / C 59.96. The earlier event 104 interval also reconciled to genuine **7,296-share** volume through bar 123.
- **Rules, API, restart and replay:** the unchanged backend retains its 29-test/14-subtest passing result. Separate actual process-restart, offline replay and induced outage/recovery evidence supports the live implementation; fixtures are not represented as Yahoo captures.
- **Frontend/usability:** the final production build passed after two demonstrated fixes: record-table CSS no longer enlarges the chart divider, and mode switches clear previous-session status before loading the new snapshot. Browser checks covered 1440×900/1280×800, ≥24 px controls, visible keyboard focus, arrow-key selection, narrow reflow and pan preservation during updates. Captured console warning/error logs were empty.
- **Timing:** eight earlier backend-receipt-to-proxied-consumer samples measured median **3 ms**, maximum **8 ms**. Browser footer timing measures synchronous chart API work. Neither measures full paint or claims zero network/provider delay. A non-failing Starlette test-client deprecation warning is disclosed.

## Limitations

Yahoo is sampled, delayed and potentially unavailable. Stream OHLC is not exchange-complete; volume can lag, and missing values remain unknown. Automatic same-time correction inference is impossible without provider identity.

Equivalent 150% reflow passed at 853×533 CSS pixels; the literal browser zoom setting still needs the manual pre-recording check. A screen reader and complete paint latency were not measured. The actual video duration is verified at 55 seconds. Repository/video publication and instructor access remain unverified; authenticated owner access would not prove instructor access.

## Supporting documentation and evidence

**Full commit-pinned GitHub URLs: MISSING pending the real repository and implementation SHA.** Before submission, this section/table will link directly to:

- README, AGENTS, `docs/design-pipeline.md`, `docs/verification.md` and AI-USE.
- The curated `evidence/browser-audit.md`, its live/record/replay/outage screenshots and direct SQL trace.
- Runtime test results, volume reconciliation, restart results and tested-source manifest.

No local path, localhost page or relative Markdown link is presented as instructor evidence. The missing publication fields and access checks must be resolved before removing NOT READY. **Canvas receives only this file, named exactly `report.md`. Source files and ZIP archives are not uploaded to Canvas.**
