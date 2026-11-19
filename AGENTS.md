# Live Market Workstation agent instructions

## Boundary

Current authorized scope is Assignment **4.2**, Indicators, Simulated Trading, and Backtesting, on the existing Vue/FastAPI/SQLite localhost application. The new explicit user brief supersedes the earlier 4.1-only restriction. Preserve Yahoo capture, candlesticks/volume, source/receipt/freshness labels, persistence and replay. Keep the submitted 4.1 root `report.md`, original `evidence/`, video, canonical captures and frozen implementation `a176567c9ff06ac131d08f142269e8a7d5b2bd0e` unchanged. Put 4.2 report/evidence/video under `submissions/4.2/`; its Canvas filename is still exactly `report.md`.

Build only two SMAs and confirmed crossovers, a long-only **SIMULATED** account/ledger, causal bounded historical backtesting, independent numerical checks, deterministic browser tests and push-triggered GitHub Actions. No EMA/MACD/RSI/optimization, real-money trading, leverage, shorting, broker integration, authentication, deployment, CSV import, docking framework, or Part 4.3 AI/chat/vision/audio.

## Responsibilities

- `backend/provider.py`: Yahoo communication, finite retry/watchdog, minute reconciliation; one application-owned upstream session.
- `backend/market.py`: validated normalized market rules and pure replayable candle reduction.
- `backend/store.py`: immutable accepted observations, dedup/revision policy, transactional SQLite event/candle versions.
- `backend/service.py`: capture lifecycle and persist-before-publish orchestration.
- `backend/main.py`, `backend/replay.py`: bounded APIs, browser sockets and isolated recorded replay.
- `backend/strategy.py`: authoritative Decimal SMA/crossover/accounting rules shared by batch/incremental and paper/historical paths; no provider or Vue dependencies.
- `backend/trading.py`: availability-ordered paper adapter, bounded snapshot selection, isolated historical runs and durable `strategy_runs` results. Preserve paper, historical and 4.1 replay isolation.
- `frontend/src`: existing chart plus backend SMA/signal/fill/account/backtest presentation and accessible inspectors; no independent trading authority or provider network access.
- `tests/`: synthetic deterministic edge cases, independent reference comparison, actual local frontend/backend end-to-end tests and separate disposable databases. Synthetic fixtures must stay visibly distinct from real historical results.
- `.github/workflows/`: clean-runner backend/build/browser checks triggered on pushes to the submitted branch; no Yahoo availability or personal credentials required.
- `docs/`, `submissions/4.2/`, `handoffs/current.md`: concise truthful current evidence and next actions. Never invent tests, historical results, Actions runs, recordings, model versions, commits or access checks. Original 4.1 submission artifacts remain frozen.

## Strategy and causality contract

Use trailing arithmetic means of full eligible close windows (default 5/20); incomplete windows return null. Forming candles cannot order. The first nonzero fast/slow side initializes; equality retains the previous nonzero side; only a subsequent opposite side emits one confirmed crossover. Validate integer windows `1 ≤ fast < slow`; changed settings create a new run/configuration, not rewritten trade history.

The long-only account buys the fixed quantity while flat on UP and sells to close while long on DOWN. Use Decimal/fixed-precision money; include fees in affordability. Capitalize entry fees in basis and subtract exit fees once. Cash/holdings change only on actual simulated fills. Persist ledger identity across refresh and reject duplicate completion/order/fill events. Late source revisions may update corrected chart history but cannot rewrite issued signals, orders, fills or equity snapshots. A finalized vendor bar may update only the current account mark when its source interval end is known by its receipt time; expose mark source/event/availability provenance and preserve prior ledger snapshots.

Historical final-bar runs execute an existing pending order at the next eligible bar open, then reveal that bar's close and compute its confirmed decision. Disclose the assumption that final vendor bars were available at close. Recorded/paper processing follows original receipt/availability order with stable IDs. The quote used to confirm the prior interval cannot also fill the newly created order; wait for a later eligible observed quote. Exclude initial capture-partial and flagged outage intervals; otherwise confirmed sampled-quote intervals may be eligible without claiming exchange-complete coverage. Reset warm-up at missing-minute gaps, never manufacture gap prices and leave a final signal unfilled when no later execution exists. Preserve the exact policy actually implemented and tested in the design notes.

Verify equity = cash + marked holdings and equity − starting cash = realized + unrealized P&L. Keep completed round trips distinct from orders/fills. The mandatory eight-bar fixture expects $990 equity, −$10 realized P&L, zero holdings, $2 fees, two fills and one completed round trip; expected values must not be generated by production code.

## CHECK → TAKE ACTION → VERIFY

Inspect repository root/branch/status/remotes, README, these instructions, current handoff, relevant docs/source/manifests/locks. Check runtime/dependency versions before changes. Before any new dependency installation not already approved in this session, show missing packages, exact commands and project-local target environments, then obtain the course checkpoint approval. Reuse prior approval. Keep secrets, test DBs and environments out of Git. Keep captured DB files intact locally.

Implement backend configuration/provider/routes first. Inspect actual running backend responses; prove a frontend/backend round trip before extending integration. Verify actual provider fields and units; cumulative or rolling volume must never be summed as interval volume. Preserve nulls, original times, revisions, gaps and limitations.

## SmokeTest

**SmokeTest runs verification without editing application code.** Run appropriate existing tests/builds/health checks and inspect results. Tests may use disposable databases and evidence output. Report failures and unverified behavior; do not silently fix application code during this mode.

## AutoLoop

**AutoLoop runs the agreed check, inspects its failure, makes the smallest in-scope fix and reruns it.** Stop on success, after five correction cycles, or at a genuine blocker. Keep a cycle count and report remaining failures/unverified checks. Do not expand scope or install unapproved dependencies.

## Git milestone / personal review

Work on scoped `codex/assignment-4-2` and preserve uncommitted changes. Never reset/switch blindly, initialize Git in another directory or guess a remote. Prepare the complete scoped diff, actual verification results and a short review checklist before publishing. The user explicitly delegated the 4.2 review to Codex: “Do my review yourself and make it look more human looking and appealing.” This replaces the pending human personal-review checkpoint and authorizes the reviewed 4.2 milestone publication. Perform and record the agent review, verify the finished interface, then continue with the authorized commit/push. Do not request that review again or claim that the user personally inspected the result. Confirm the pushed commit and actual hosted push-triggered Actions result for that exact tested implementation SHA. Never change repository visibility or submit to Canvas.

`submissions/4.2/report.md` is the only 4.2 Canvas artifact, uploaded with filename `report.md`. It must identify the real repository, frozen tested implementation SHA, exact Actions run/result, real historical result, independent/reference/accounting/browser evidence and accessible 30–60-second video. Use full immutable GitHub supporting URLs in the standalone upload. Freeze the implementation/evidence commit before adding its SHA to a later report-only commit. Missing required items remain unmistakably **NOT READY**. Do not overwrite or resubmit the root 4.1 report.
