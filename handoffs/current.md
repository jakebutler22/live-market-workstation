# Current handoff — Assignment 4.1

Branch: `codex/assignment-4-1`. Frozen tested implementation commit (local): **`a176567c9ff06ac131d08f142269e8a7d5b2bd0e`**. It includes the verified app, evidence and 55-second video. There is no remote; push/access remain unverified. Later documentation-only commits do not replace this tested implementation identifier. Preserve all source/evidence and the live captured `data/market.sqlite3`. The exact application/test/dependency hashes are frozen in `evidence/tested-source-manifest.json`; its SHA-256 is not a Git commit.

## Run and current state

Run `.venv/bin/python -m scripts.start` from the repository root. Backend **8000**, Vue/Vite **5173**; open **http://127.0.0.1:5173/** and keep the terminal running. If ports are occupied by this app, use the existing site rather than starting duplicate capture. SQLite initializes automatically and survives restart. Project-local dependencies are installed under the prior approval; none are awaiting approval. Exact resolutions are in both lockfiles.

The app was returned to **LIVE**, with the induced pause removed and a genuine Yahoo quote received after recovery. BHP.AX is AUD/share data with a documented 20-minute delay. Do not infer market closure or treat LIVE as zero-delay data.

## Completed and observed

Implemented Yahoo `AsyncWebSocket`, bounded provider lifecycle, genuine nullable minute-volume reconciliation, deterministic candle rules, immutable SQLite events/versioned candles, bounded APIs, isolated recorded replay, a polished Vue/Lightweight Charts terminal and startup/docs/evidence. Assignment 4.1 only.

Existing dependency-enabled run: **29 tests + 14 subtests passed**, no skips; backend unchanged in final audit. Earlier actual restart retained digests of 129 events/127 candle versions and resumed Yahoo data. Eight receipt-to-proxy-consumer timings: median 3 ms/max 8 ms; not browser render timing. The final frontend build passed after the two demonstrated UI fixes.

Actual browser evidence now exists. Displayed Yahoo quote **545** and **00:37–00:38 UTC candle v12** matched SQLite exactly (O 59.94 / H 59.96 / L 59.93 / C 59.96); integrity `ok`. Keyboard-selected prior interval displayed **5,451 shares** and a 2 px focus outline. Observed 1440×900, 1280×800, controls ≥24 px and equivalent 150% reflow at 853×533 CSS pixels without horizontal document overflow. Browser warning/error log result was empty. Captured footer chart-update calls were 0.00–0.80 ms, excluding completed paint.

Replay start/pause/resume/restart worked with original recording time. During induced upstream unavailability the chart stayed visible, app socket stayed connected, source age rose **20m 11s → 20m 25s**, and replay did not change the **606** canonical events. Resume recovered actual quote **621**. [Curated browser audit](../evidence/browser-audit.md), [verification](../docs/verification.md), [evidence index](../evidence/README.md).

Two browser-demonstrated frontend fixes: scope table-cell styles so chart pane divider is 1 px instead of 29 px; clear previous replay status/times/counts on mode reset before new snapshot. Browser and production build checks passed after these fixes. No broader redesign or optional features added.

## Exact remaining work

A genuine local demo is recorded at `evidence/demo-4-1.mp4`: **55 seconds**, **1440×900**, H.264 fast-start MP4, **no audio**, **3,295,740 bytes**. The existing system AVFoundation encoder used **205 actual browser-page screenshots at their genuine irregular timestamps** over 55 real seconds; this was not a native screen recorder and no synthetic motion was added. See `evidence/demo-video.json` and `docs/demo-run-sheet.md` for metadata/actual sequence. Native app control was blocked, while normal browser screenshot APIs were available. The source was resumed after recording. Upload the existing file once its actual destination is confirmed, then verify the accessible URL/instructor access; no new recording is needed. Literal browser 150% zoom and screen-reader behavior remain unperformed; equivalent viewport reflow is explicitly distinguished.

The concrete report draft, complete scoped diff, exact 55-second run sheet and source hash manifest are prepared. The user has explicitly approved commit and push of the reviewed implementation; reuse this authorization without asking again. The actual GitHub repository URL remains missing, so no remote can yet be configured or pushed. The accessible video URL and instructor-access checks also remain outstanding. Configure only the user-confirmed repository, push the approved scoped branch containing the frozen implementation, verify that full implementation SHA on GitHub, and use full commit-pinned supporting links in `report.md`. Check instructor access separately from authenticated owner access. Until these external inputs and remote verification are resolved the report is **NOT READY TO SUBMIT**. Canvas receives only `report.md`; do not submit it or start Part 4.2.
