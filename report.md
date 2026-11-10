# Assignment 4.1 — Market Data and the Dashboard

**READY TO SUBMIT.** The implementation, recorded demonstration and supporting evidence are published. Repository, commit and video access were checked without authentication.

## Assignment and project

**Live Market Workstation** is a localhost application using Vue, Python/FastAPI and SQLite. It captures Yahoo Finance observations, displays updating one-minute candles with corresponding volume, preserves their history and replays recorded observations. This submission covers Assignment 4.1 only.

## Repository and submitted version

- Repository: [jakebutler22/live-market-workstation](https://github.com/jakebutler22/live-market-workstation).
- Tested implementation: **`a176567c9ff06ac131d08f142269e8a7d5b2bd0e`** — [direct commit](https://github.com/jakebutler22/live-market-workstation/commit/a176567c9ff06ac131d08f142269e8a7d5b2bd0e).
- [Verified source manifest](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/tested-source-manifest.json) matches all 26 application, test and dependency files in that commit.

Publication documents were updated afterward without changing application code. Documentation links below are pinned to that later documentation snapshot; recorded market evidence and video remain pinned to the tested implementation.

## Demonstration video

[Download/open the 55-second demonstration (MP4)](https://raw.githubusercontent.com/jakebutler22/live-market-workstation/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/demo-4-1.mp4).

The video shows actual Yahoo updates and freshness, an expanded saved observation, replay with pause/resume and original recording time, then an induced upstream interruption with history retained. It is a silent 1440×900 H.264 recording, 3.3 MB. Codex captured 205 real browser frames over 55 seconds and encoded their actual elapsed timing, approximately 3.74 frames/second. No market motion or UI state was generated for the video.

Decoded MP4 frames were inspected. The anonymously downloaded file exactly matches the duration-verified local file: [video metadata and database trace](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/evidence/demo-video.json), [public-access checks](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/evidence/publication-access.json). GitHub serves the MP4 as a downloadable file; open it in a video player if it does not play in the browser.

## Completed work

| Part 4.1 requirement | Status | Result and evidence |
|---|---|---|
| Real Yahoo streaming and frontend WebSocket | Verified | yfinance observations reach the backend, SQLite and rendered Vue chart. Displayed quote **545** and candle **v12** match [direct SQL records](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/browser/trace-sql.json). |
| Candlesticks and corresponding volume | Verified | Lightweight Charts renders aligned candle/volume panes. Keyboard selection displayed **5,451 shares** for 00:36–00:37 UTC; unknown current volume remains unavailable. [Rendered evidence](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/browser/selected-volume-keyboard.jpg). |
| Source, data age and feed/completion states | Verified | Yahoo source, source/receipt times, source-derived age, published delay, separate upstream/application states and elapsed/partial coverage are visible. [Live screen](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/browser/live-final.jpg). |
| Durable SQLite observations and candle revisions | Verified | Immutable events and versioned candles preserve identity, useful payloads, original times, revisions and coverage. An actual restart retained exact digests of **129 events/127 versions**. [Restart result](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/restart-after.json). |
| Recorded replay | Verified | Start/pause/resume/restart use original recording times. Replay while Yahoo was paused left **606 canonical events** unchanged. [Replay isolation](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/browser/replay-while-source-paused.json). |
| Duplicates, revisions and out-of-order observations | Verified | **29 tests plus 14 subtests** passed, including hand-calculated candles, interval boundaries, correction chains, equal-time ties and late arrivals. [Test output](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/runtime-tests.txt). Edge cases use labeled fixtures. |
| Live trace, unavailable feed and recovery | Verified | An induced UI interruption retained history and application connectivity while age rose **20m 11s→20m 25s**. Resume recovered actual quote **621**. [Browser audit](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/evidence/browser-audit.md). |
| Startup, schema and agent documentation | Verified | Locked installation, ports, SQLite initialization, responsibilities and limitations are documented in the [README](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/README.md), [design notes](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/docs/design-pipeline.md) and [AGENTS](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/AGENTS.md). |
| Repository, submitted commit and video access | Verified | Public repository and exact commit returned HTTP 200 without authentication. The full video and byte-range retrieval returned HTTP 200/206. [Access evidence](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/evidence/publication-access.json). |

## Key design decisions

The path is **Yahoo → provider adapter → validation → SQLite/candle processing → application WebSocket → Vue chart**. One backend-owned upstream session serves all browsers. Observations and candle versions commit together before saved updates publish. An immutable event log and versioned candle records retain earlier accepted states; bounded retrieval reads the latest saved view.

Times are UTC and intervals are `[start,end)`. Sampled quote open/close follow source chronology with a deterministic fingerprint tie-breaker. Late observations can revise elapsed candles; elapsed time does not establish complete trade coverage. Candle and volume colors follow that candle's own close/open; equal prices are neutral.

Yahoo exposes no genuine trade/correction ID here. Normalized useful-payload fingerprints suppress indistinguishable duplicates; differing same-time messages remain separate observations. Explicit application correction links and stable Yahoo minute-bar identities preserve revisions. Finalized Yahoo minute aggregates reconcile historical OHLC and supply interval volume. Stream session counters are never summed, and null volume stays unknown. Replay uses immutable availability order and recorded clock events, excluding future revisions and canonical writes.

The compact terminal provides numeric/source inspectors, an accessible candle table and small replay controls. Default **BHP.AX** uses AUD prices and share volume with a published **20-minute ASX delay**. LIVE means an actual subscription, not instantaneous exchange data. See the [file/data-flow/schema map and design tokens](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/docs/design-pipeline.md).

## Verification results

Actual browser/SQL tracing matched quote **545**: source **00:37:34 UTC**, receipt **00:57:36.702 UTC**, price **AUD 59.96**. Candle v12 matched displayed O 59.94 / H 59.96 / L 59.93 / C 59.96. An earlier captured interval reconciled to **7,296 shares** through Yahoo bar 123: [volume reconciliation](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/app-volume-reconciliation.json). The video's saved quote **894** also matches SQLite and candle v11.

The unchanged backend retains the **29-test/14-subtest** passing result. The frontend production build passed after two browser-demonstrated fixes: scoping record-table CSS restored the chart divider, and mode switches clear prior-session status before the new snapshot. [Build result](https://github.com/jakebutler22/live-market-workstation/blob/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/frontend-build.txt). Actual restart, replay and induced outage/recovery checks are separate from synthetic tests.

Browser checks covered 1440×900 and 1280×800 layouts, controls at least 24 px, visible keyboard focus, arrow-key selection, narrow reflow and pan preservation during updates. Captured console warning/error logs were empty. Eight backend-receipt-to-proxied-consumer samples measured median **3 ms**, maximum **8 ms**; these exclude external provider delay and completed browser paint. [Full verification results](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/docs/verification.md).

## Limitations

Yahoo observations are sampled, delayed and potentially unavailable. Stream OHLC is not exchange-complete; interval volume can lag, and unknown values stay unavailable. Automatic same-time correction inference is impossible without provider identity.

Equivalent 150% reflow passed at 853×533 CSS pixels; literal browser zoom and screen-reader behavior remain unverified. Complete browser paint latency was not measured. A non-failing Starlette TestClient deprecation warning is retained in the test output. The demonstration is silent and uses the actual irregular screenshot cadence described above.

## Supporting documentation and evidence

- [README/startup](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/README.md), [AGENTS/SmokeTest/AutoLoop](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/AGENTS.md), [design/data/schema notes](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/docs/design-pipeline.md), [AI-use disclosure](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/AI-USE.md).
- [Verification](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/docs/verification.md), [curated evidence index](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/evidence/README.md), [browser audit](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/evidence/browser-audit.md), [demo sequence](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/docs/demo-run-sheet.md), [publication/access evidence](https://github.com/jakebutler22/live-market-workstation/blob/8ddf6d60ece9310a8020a78019cb91b414e9adf0/evidence/publication-access.json).

**Canvas receives only this file, named exactly `report.md`. Source files and ZIP archives are not uploaded to Canvas.**
