# Assignment 4.1 verification

The actual local application runs at **http://127.0.0.1:5173/**, with FastAPI at **http://127.0.0.1:8000** and canonical capture in `data/market.sqlite3`. The final audit observed real Yahoo observations in the rendered Vue chart and matched a visible record/candle directly to SQLite. The curated [browser audit](../evidence/browser-audit.md) separates screenshots, measurements, genuine provider integration, and remaining manual checks. Raw timestamps are UTC; the working date was November 9, 2026 in New York.

## Requirement-to-evidence matrix

| Check | Actual result / evidence |
|---|---|
| Repository and prerequisites | Confirmed project root and scoped `codex/assignment-4-1` branch. No initial commits or Git remote. Python 3.14.7, Node 24.12.0, npm 11.6.2. Repository URL/full tested SHA/video remain external submission inputs. |
| Project-local dependencies | Previously approved installation in `.venv` and `frontend/node_modules`; exact resolutions in `requirements.lock` and `frontend/package-lock.json`. FastAPI 0.162.2, Uvicorn 0.54.0, yfinance 1.8.0, pytest 9.2.0, httpx 0.28.1; Vue 3.5.45, Lightweight Charts 5.2.1 and Vite 8.3.7. `pip check`/`npm ls` passed. No additional dependencies installed for the final audit. |
| Market rules, storage, replay and APIs | **29 tests and 14 subtests passed**, no skips. [Actual output](../evidence/runtime-tests.txt); synthetic fixtures/disposable databases. One Starlette TestClient/httpx deprecation warning is preserved. Backend unchanged during the final browser fixes, so these results were reused. |
| Build/static checks | Production frontend build passed after the two demonstrated frontend fixes. Earlier Python compilation, JS/SFC syntax and Git whitespace checks passed. [Build evidence](../evidence/frontend-build.txt). Final source hashes will be frozen before personal review/commit. |
| Real Yahoo → rendered frontend → SQLite | Visible **quote 545**, source `1794271054000`, receipt `1794272256702`, **AUD 59.96**, and displayed **00:37–00:38 UTC candle v12** matched SQLite exactly: O 59.94 / H 59.96 / L 59.93 / C 59.96. [Browser fields](../evidence/browser/visible-live-trace.json), [direct SQL/integrity](../evidence/browser/trace-sql.json), [screenshot](../evidence/browser/visible-record.jpg). Earlier [event 104 transport trace](../evidence/app-live-trace.json) remains supporting evidence, rather than browser proof. |
| Genuine corresponding volume | Keyboard-selected **00:36–00:37 UTC** displayed **5,451 shares**, vendor event **541** / candle **v20**, with visible focus. [Fields](../evidence/browser/keyboard-volume.json), [screenshot](../evidence/browser/selected-volume-keyboard.jpg). Earlier [same-interval reconciliation](../evidence/app-volume-reconciliation.json) traces quote 104's interval to bar 123 / 7,296 shares. Unknown current volume stayed unknown. |
| Induced unavailable source and rising age | Actual UI showed **UNAVAILABLE · INDUCED**, application socket connected, retained chart/history and unchanged source/receipt timestamps while age grew **20m 11s → 20m 25s**. [Initial state](../evidence/browser/unavailable.json), [later age](../evidence/browser/unavailable-later.json), [screenshot](../evidence/browser/unavailable.jpg). This is a controlled upstream pause, not an accidental outage or browser disconnect. |
| Recovery | Resume restored **RECEIVING** and saved Yahoo quote **621**, source 00:42:11 UTC / receipt 01:02:12 UTC. [Actual browser result](../evidence/browser/recovered.json). Earlier [same-socket recovery trace](../evidence/app-recovery.json) also remains applicable. |
| Browser replay controls and isolation | Start/pause/resume/restart worked; original recording time and REPLAY label visible. Paused at **244/576**, restart at **85/576**. While Yahoo was paused, replay reached **307/606** and canonical event count stayed **606**. [Paused](../evidence/browser/replay-paused.json), [restart](../evidence/browser/replay-restarted.json), [offline isolation](../evidence/browser/replay-while-source-paused.json). Earlier full [129-event replay](../evidence/app-failure-replay.json) reached the end without changing storage. |
| Actual persistence/process restart | Stopped and restarted actual servers. **129** earlier events and **127** candle versions retained exact SHA-256 digests; SQLite integrity `ok`; new Yahoo quotes resumed and duplicate seed data was ignored. [Before](../evidence/restart-before.json), [after](../evidence/restart-after.json). Capture was not cleared. |
| Browser layout/keyboard | Observed **1440×900** and **1280×800** layouts; chart/volume readable, numeric columns stable, keyboard interval selection and 2 px focus worked. Measured essential controls were at least 24 px high. No horizontal document overflow at 1280. [Screenshots/measurements](../evidence/browser-audit.md). |
| Equivalent 150% reflow | At **853×533 CSS pixels**, corresponding approximately to a 1280×800 window at 150%, layout became one column, with vertical scroll, no horizontal document overflow and controls at least 24 px high. [Measurements](../evidence/browser/reflow-150-equivalent.json), [screenshot](../evidence/browser/reflow-853x533.jpg). Literal zoom setting remains unverified. |
| Console and performance observations | Browser warning/error log inspection returned an empty result. Captured footer samples showed **0.00–0.20 ms local chart-update call duration**, not completed render/paint. Earlier eight backend-receipt→proxied-socket samples had **3 ms median / 8 ms max**; excludes Yahoo delay, prior network travel and browser work. [Trace measurements](../evidence/app-live-trace.json), [browser audit](../evidence/browser-audit.md). |
| Recorded demonstration | Actual **55-second**, **1440×900**, H.264 fast-start MP4, **no audio**, from **205 genuine browser-page screenshots at real capture timestamps**, encoded using existing system AVFoundation. [MP4](../evidence/demo-4-1.mp4), [metadata](../evidence/demo-video.json), [actual sequence](demo-run-sheet.md). Accessible upload URL/instructor access remain missing. |
| Contrast/static accessibility | Calculated text contrast at least 6.37:1 against raised surface; control boundary 3.44:1 and focus 8.78:1 against panel. Reduced-motion rules are implemented. Actual screen-reader behavior was not tested. |

## Repeatable checks

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run build
python3 -m compileall -q backend scripts tests
git diff --check
```

The tests cover hand-calculated OHLCV/boundaries, exact duplicates, explicit correction chains, same-time ties, late arrivals, raw null versus genuine zero volume, vendor provisional versus elapsed state, gaps, forced transaction rollback, actual child-process reconstruction, finite provider closure/cancellation, replay against immutable candle revisions and API/WebSocket behavior. Stream cumulative volume is intentionally unused, so speculative counter-baseline/reset logic does not apply. The earlier [24-pass dependency-free run](../evidence/unit-test-results.txt) is retained as historical evidence and superseded by the installed-dependency run.

For a live database inspection, preserve `data/market.sqlite3` and query it read-only:

```sql
SELECT id,kind,symbol,source_ms,received_ms,revision,supersedes_id,payload
FROM events ORDER BY id DESC LIMIT 12;
SELECT symbol,start_ms,revision,event_id,candle
FROM latest_candles ORDER BY start_ms DESC LIMIT 5;
PRAGMA integrity_check;
```

For a browser recheck, follow the [curated browser audit](../evidence/browser-audit.md): show an identifiable saved event, compare its immutable SQL event/candle version, select an interval with reconciled volume, exercise replay, interrupt Yahoo, observe retained data and rising source age, then resume and wait for a genuine quote. Browser disconnect/reconnect is distinct from the induced upstream pause. Live capture retains unknown volume and its actual published exchange delay.

## Genuine failures and corrections

- Framework Python initially lacked a configured CA path; the existing `/etc/ssl/cert.pem` trust bundle resolved Yahoo HTTPS while keeping certificate verification enabled.
- A yfinance 1.8.0 normally exhausted iterator could loop; the finite-close wrapper and cancellation tests bound that behavior.
- Dependency-enabled tests exposed normal WebSocket-disconnect cleanup handling; the focused backend fix passed the full test run.
- The site initially could not be reached because local dependencies/services were absent. The approved installation and readiness-checked one-command launcher resolved startup.
- An earlier browser attempt failed. During the final audit, normal inventory and tab selection reached the actual running localhost page without changing or bypassing a security policy. Browser screenshots and controls are now genuinely observed.
- Actual browser inspection found global `td` styles widening a chart-internal divider from 1 px to 29 px; scoped record-table styles restored 1 px.
- Returning from replay briefly retained old replay status until the new live snapshot. A mode reset now shows unknown/connecting/zero until genuine data arrives. Both frontend fixes were verified in the browser and followed by a production build.

## Remaining verification/submission limits

- Literal browser zoom could not be set through available controls; the shortcut had no effect. Equivalent viewport reflow is verified, explicitly not literal zoom. An assistive-technology screen-reader session remains unperformed.
- Permitted browser tools expose no native recording API and native app control was blocked. The normal screenshot APIs did allow a real-time browser-only sequence: 205 actual app frames over 55 seconds, encoded with system AVFoundation into the local MP4. No audio or synthetic market motion was added. The existing video needs an accessible upload URL and instructor-access check; another recording is not required.
- The user explicitly approved the reviewed implementation's commit and push; reuse that authorization. No Git remote or commit exists yet. A real repository URL, verified pushed SHA, accessible video URL and instructor repository/video access are still needed. The [report](../report.md) stays **NOT READY TO SUBMIT** until required links and access checks are resolved. Canvas receives only `report.md`.
