# Live Market Workstation — Assignment 4.1

A local Vue / FastAPI / SQLite terminal for Yahoo Finance market observations, one-minute candlesticks with corresponding vendor interval volume, durable capture and isolated replay. Default **BHP.AX**: equity prices in **AUD**, volume in **shares**, **20-minute ASX quote delay**. LIVE means an actual upstream subscription, not zero-delay exchange data. No trading features.

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

## Verification

```sh
.venv/bin/python -m pytest -q
npm --prefix frontend run build
python3 -m compileall -q backend scripts tests
```

Observed: **29 tests and 14 subtests passed**, production frontend build passed, and actual Yahoo observations traversed yfinance → SQLite → the rendered Vue chart. The browser's displayed quote **545** and candle **v12** matched canonical SQLite records. Keyboard selection exposed genuine interval volume; replay start/pause/resume/restart worked. An induced source interruption retained history and increased source age; recorded replay left canonical counts unchanged, and resumed Yahoo capture produced quote **621**. The final browser audit covered 1440×900, 1280×800, visible focus and equivalent 150% reflow at 853×533 CSS pixels, with no observed console warnings/errors or horizontal document overflow. Literal browser zoom and assistive-technology behavior remain manual checks. See [verification results](docs/verification.md), [curated browser audit](evidence/browser-audit.md), [evidence log](evidence/README.md), [demo run sheet](docs/demo-run-sheet.md) and [submission draft](report.md).

## Limits

Yahoo is an unofficial third-party source with availability, coverage and delay limits. No claim of exchange-complete trade capture or zero network latency is made. BHP.AX may be inactive outside ASX sessions. The ASX published delay is shown separately from measured source age; silence beyond 45 seconds triggers reconnect regardless of the expected exchange delay. Retained history remains useful during failure, and replay works offline from Yahoo.

See `report.md` for outstanding submission links and verification. No Canvas submission, repository visibility changes or public deployment are performed.
