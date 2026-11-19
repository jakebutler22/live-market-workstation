# Live Market Workstation — Assignments 4.1 and 4.2

A local Vue / FastAPI / SQLite terminal for Yahoo Finance market observations, one-minute candlesticks with corresponding vendor interval volume, durable capture and isolated replay. Default **BHP.AX**: equity prices in **AUD**, volume in **shares**, **20-minute ASX quote delay**. LIVE means an actual upstream subscription, not zero-delay exchange data. Assignment 4.2 extends the same terminal with confirmed SMA crossovers, an explicitly simulated account and historical backtesting; verification is recorded separately.

Public repository: [jakebutler22/live-market-workstation](https://github.com/jakebutler22/live-market-workstation). Frozen **4.1** tested implementation: [a176567c9ff06ac131d08f142269e8a7d5b2bd0e](https://github.com/jakebutler22/live-market-workstation/commit/a176567c9ff06ac131d08f142269e8a7d5b2bd0e); later documentation-only commits retain that implementation identifier. [Download/open the 55-second demonstration MP4](https://raw.githubusercontent.com/jakebutler22/live-market-workstation/a176567c9ff06ac131d08f142269e8a7d5b2bd0e/evidence/demo-4-1.mp4). Repository, commit and video access were verified anonymously; [publication evidence](evidence/publication-access.json). The submitted [4.1 Canvas report](https://github.com/jakebutler22/live-market-workstation/blob/codex/assignment-4-1/report.md), root `report.md`, original `evidence/` and 4.1 video are preserved. The current **4.2 Canvas file is [submissions/4.2/report.md](submissions/4.2/report.md)**; upload it with filename `report.md`. The final report identifies the tested implementation, actual hosted checks and accessible demonstration.

## Prerequisites and installation

Tested on this workstation: Python **3.14.7**, Node **24.12.0**, npm **11.6.2**. The course dependency checkpoint has been approved and project-local dependencies are installed. Reproduce the tested resolution with:

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
npm --prefix frontend ci
```

Verified Python direct dependencies: FastAPI 0.162.2, Uvicorn 0.54.0, yfinance 1.8.0, pytest 9.2.0 and httpx 0.28.1. Frontend dependencies are Vue 3.5.45, Lightweight Charts 5.2.1, Vite 8.3.7 and @vitejs/plugin-vue 6.0.10. `requirements.lock` and `frontend/package-lock.json` record the installed resolution. No global packages are needed.

## Initialize and start

```sh
.venv/bin/python -m scripts.start
```

Keep that terminal running. The launcher starts FastAPI on **8000** and Vite on **5173**, waits for both HTTP readiness checks, and prints the address. Open [the local workstation](http://127.0.0.1:5173/). Ctrl-C stops both servers. If either port is already occupied, the launcher reports it rather than starting another capture process.

Backend [health](http://127.0.0.1:8000/api/health) and [status](http://127.0.0.1:8000/api/status) are separate: a healthy application socket does not mean Yahoo is available. Use one Uvicorn worker; do not run multiple capture processes against the same symbol/database. To run the services separately for debugging:

```sh
# Terminal 1
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Terminal 2
npm --prefix frontend run dev -- --port 5173 --strictPort
```

SQLite is automatically initialized at `data/market.sqlite3` on first startup; `.venv/bin/python -m scripts.init_db` also initializes it explicitly. The database, WAL files and environment are ignored by Git and retained across restarts. Do not delete captured observations. Disposable tests use temporary databases, never this file.

`SYMBOL` and `DATABASE_PATH` are optional exported environment variables; see `.env.example`. The application does not implicitly read `.env`. Symbol is fixed for a process/session to avoid cross-symbol races; stop the backend, change the environment, then restart. Example:

```sh
SYMBOL=AAPL .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Only BHP.AX is the intended verified submission instrument. Other Yahoo symbols require checking exchange delays, units, streaming availability and volume semantics; a valid ticker string does not guarantee support. Candle interval is fixed at 60 seconds.

## Live capture and replay

The backend owns one yfinance `AsyncWebSocket` session independently of browser count. Valid observations commit to SQLite before publication. The dashboard shows source time/age, receipt time, event IDs, candle versions, coverage and source versus application connectivity. The source watchdog uses five attempts and bounded backoff, with a pinned-version clean-close guard. Framework Python without a configured CA path uses the existing system certificate bundle when available; verification remains enabled. **Interrupt source** induces an explicit upstream pause while keeping the application connection and saved chart; **Resume source** restarts capture/retries.

**REPLAY → Start** rebuilds candles from a frozen copy of recorded events, original receipt/source times, recorded clock ticks and revisions. Pause/resume/restart operate only this browser's replay. Live capture continues independently; replay never inserts canonical observations. Reconnect to replay to include newly captured records. Empty recordings and end-of-recording have explicit states.

Candles use UTC half-open intervals `[start, end)`. Stream OHLC describes sampled quote observations, not every exchange trade. Elapsed intervals can still have incomplete capture. Missing volume displays unavailable; it never becomes a fabricated zero. Raw cumulative stream fields are deliberately unused for volume. Yahoo one-minute aggregates reconcile OHLC of finalized historical minutes and provide corresponding interval volume; the newest vendor minute stays provisional. Polling adds up to 30 seconds plus provider delay. See [design/data/schema notes](docs/design-pipeline.md) and [provider evidence](docs/provider-research.md).

## Preserved 4.1 verification

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run build
python3 -m compileall -q backend scripts tests
```

Observed at the frozen 4.1 implementation: **29 tests and 14 subtests passed**, production frontend build passed, and actual Yahoo observations traversed yfinance → SQLite → the rendered Vue chart. The browser's displayed quote **545** and candle **v12** matched canonical SQLite records. Keyboard selection exposed genuine interval volume; replay start/pause/resume/restart worked. An induced source interruption retained history and increased source age; recorded replay left canonical counts unchanged, and resumed Yahoo capture produced quote **621**. The final browser audit covered 1440×900, 1280×800, visible focus and equivalent 150% reflow at 853×533 CSS pixels, with no observed console warnings/errors or horizontal document overflow. Literal browser zoom and assistive-technology behavior remain manual checks. See [verification results](docs/verification.md), [curated browser audit](evidence/browser-audit.md), [evidence log](evidence/README.md), [demo run sheet](docs/demo-run-sheet.md) and [current Canvas report](https://github.com/jakebutler22/live-market-workstation/blob/codex/assignment-4-1/report.md).

## Limits

Yahoo is an unofficial third-party source with availability, coverage and delay limits. No claim of exchange-complete trade capture or zero network latency is made. BHP.AX may be inactive outside ASX sessions. The ASX published delay is shown separately from measured source age; silence beyond 45 seconds triggers reconnect regardless of the expected exchange delay. Retained history remains useful during failure, and replay works offline from Yahoo.

See the [current Canvas report](https://github.com/jakebutler22/live-market-workstation/blob/codex/assignment-4-1/report.md) for the submitted implementation, direct video and supporting evidence links. No Canvas submission, repository visibility changes or public deployment are performed.

## Assignment 4.2 — current milestone

The complete brief is preserved in [prompt 03](prompts/03-assignment-4-2.md). The shared backend now implements two trailing SMAs and confirmed crossovers, a long-only **SIMULATED** ledger, a bounded genuine-history backtest and durable result retrieval. Local checks and the exact [hosted push run](https://github.com/jakebutler22/live-market-workstation/actions/runs/44425505313) pass. The [55-second demo](https://raw.githubusercontent.com/jakebutler22/live-market-workstation/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/demo.mp4) is published and anonymously verified. The user delegated the final review to Codex. No broker or real-money orders exist, and 4.1 capture/chart/replay is preserved.

Defaults are **SMA(5)/SMA(20), AUD 10,000 starting cash, 10 shares per entry, AUD 1 per fill and zero slippage** for BHP.AX. A full eligible trailing window is required; forming candles cannot order. The first nonzero side initializes without trading, equality retains the last nonzero side within `1e-10`, and an opposite side produces one crossover. Gaps reset warm-up. Recorded paper candles exclude the first capture-partial interval and flagged outages; other confirmed sampled intervals can qualify without claiming complete exchange-trade coverage.

Paper mode consumes immutable original quote availability/ID order. The first quote of a new interval confirms the prior interval; a subsequent non-late quote is the earliest eligible fill for its new order. Corrections remain in the market log but do not rewrite issued paper decisions. A finalized vendor aggregate may advance only the current valuation when its interval end was known at receipt; mark source, event ID and availability time stay visible. Signals, fills and prior equity snapshots remain unchanged. Corrected vendor chart closes can therefore differ from frozen paper inputs. The `paper-v1` run persists in the existing SQLite `strategy_runs` table; separate deterministic historical run IDs cannot append to that account.

The offline historical snapshot is [fixtures/historical/bhp-4-1.json](fixtures/historical/bhp-4-1.json): **358** genuine finalized Yahoo BHP.AX minute bars, **2026-11-09 23:00 through 2026-11-11 03:22 UTC**, raw/unadjusted Yahoo OHLC, snapshot `919fe8716db104587c8f376b0552b865a61cd44f15cae0393b4c4f874bc5fa4d`. It was extracted read-only from original 4.1 capture. Missing minutes reset windows; no candles are manufactured. Its explicit final-bar assumption is availability at close, with an already-pending order filled at a subsequent eligible open. Original vendor revision availability is not reconstructed.

Local engine execution of that snapshot returned **AUD 9,990.74999237060544 equity**, **−AUD 9.25000762939456 / −0.0925000762939456%**, **11 fills**, **5 completed round trips**, **10 shares still open** and **AUD 11 fees**. This is a genuine historical result, separate from the labeled eight-bar fixture. It does not predict future profitability. The result was also observed through the actual browser flow; see [verification-4-2.md](docs/verification-4-2.md).

| API | Purpose |
|---|---|
| `GET /api/strategy` | Durable paper account, chart indicator/marker data and available dataset metadata. |
| `POST /api/backtests` | Run/retrieve an isolated snapshot result; body `{"dataset_id":"yahoo-4-1"}`. Optional integer `fast`, `slow`, `start_ms`, `end_ms`; UTC range end is exclusive by candle start. |
| `GET /api/backtests/{id}` | Retrieve one stored historical result. |
| `POST /api/indicators` | Read-only batch indicators for up to 600 replay/display candles; never changes account state. |

The synthetic dataset `worked-eight` automatically uses windows 2/3, $1,000 starting cash, two shares and $1 fees. Its local result was $990 equity, −$10 realized P&L, $2 fees, two fills and one round trip; the independent numerical and browser checks passed, with labeled [4.2 evidence](submissions/4.2/evidence/README.md). Warm-up before a selected historical start can calculate averages but cannot create actionable pre-start trades. A final order expires if no later eligible price exists; positions are marked at the last close without forced liquidation.

Playwright **1.65.1** is installed locally with Chromium **159.0.8154.6** in `.cache/ms-playwright`; the user approved this addition. npm audit reported zero vulnerabilities. The existing runtime is Python 3.14.7 / pandas 3.1.1 / Node 24.12.0 / npm 11.6.2. For a fresh project-local browser-test setup after the locked `npm ci` above:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" ./frontend/node_modules/.bin/playwright install chromium
npm --prefix frontend run test:e2e
```

Observed final local checks: **45 backend tests +19 subtests passed**, **three pandas reference cases and 14 batch/incremental prefixes passed**, maximum reference difference **1.4210854715202004e-14** below **1e-10**, **two real frontend/backend browser tests passed in 2.5 seconds**, and the frontend production build passed (23 modules / 290.11 kB JS / 97.60 kB gzip). Reproduce with `.venv/bin/python -m pytest -q`, `.venv/bin/python -m scripts.verify_strategy`, `npm --prefix frontend run build`, and `npm --prefix frontend run test:e2e`. The push-triggered `.github/workflows/verify.yml` runs these checks on `codex/assignment-4-2`; the actual hosted run for the frozen implementation passed. 4.2 evidence is isolated under [submissions/4.2/evidence/](submissions/4.2/evidence/README.md). The delegated review is complete. Frozen implementation [18f89d505464d704a73b485dc03b4cebdd1baed2](https://github.com/jakebutler22/live-market-workstation/commit/18f89d505464d704a73b485dc03b4cebdd1baed2) passed [hosted Actions](https://github.com/jakebutler22/live-market-workstation/actions/runs/44425505313); the published video passed anonymous hash/range checks. [Video and metadata](submissions/4.2/demo-run-sheet.md).

The original 4.1 artifacts remain frozen. The 4.2 publication record is in `submissions/4.2/evidence/hosted-actions.json` and `publication-access.json`; local and hosted checks use disposable test databases. The user delegated the final review to Codex, as recorded in `prompts/04-review-and-polish.md`.
