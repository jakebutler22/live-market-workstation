# Live Market Workstation agent instructions

## Boundary

Complete Assignment 4.1 only: Vue, Python/FastAPI, SQLite on localhost; one configurable symbol, one-minute candles, Yahoo WebSocket capture, corresponding genuine interval volume, provenance/freshness, persistence, deterministic replay, evidence and submission documents. Preserve existing unrelated work. No signals, moving averages, trading/orders/positions/P&L, backtesting, AI/chat/vision/audio, authentication, broker integration, CSV import, deployment, docking framework or new CI.

## Responsibilities

- `backend/provider.py`: Yahoo communication, finite retry/watchdog, minute reconciliation; one application-owned upstream session.
- `backend/market.py`: validated normalized market rules and pure replayable candle reduction.
- `backend/store.py`: immutable accepted observations, dedup/revision policy, transactional SQLite event/candle versions.
- `backend/service.py`: capture lifecycle and persist-before-publish orchestration.
- `backend/main.py`, `backend/replay.py`: bounded APIs, browser sockets and isolated recorded replay.
- `frontend/src`: presentation, controls, chart updates and accessible candle inspector; no provider network access.
- `tests/`: synthetic deterministic edge cases and separate disposable integration databases.
- `docs/`, `evidence/`, `report.md`, `handoffs/current.md`: concise truthful evidence and next actions. Never invent live proof, video URLs, model versions, commits or accessible links.

## CHECK → TAKE ACTION → VERIFY

Inspect repository root/branch/status/remotes, README, these instructions, current handoff, relevant docs/source/manifests/locks. Check runtime/dependency versions before changes. Before any new dependency installation not already approved in this session, show missing packages, exact commands and project-local target environments, then obtain the course checkpoint approval. Reuse prior approval. Keep secrets, test DBs and environments out of Git. Keep captured DB files intact locally.

Implement backend configuration/provider/routes first. Inspect actual running backend responses; prove a frontend/backend round trip before extending integration. Verify actual provider fields and units; cumulative or rolling volume must never be summed as interval volume. Preserve nulls, original times, revisions, gaps and limitations.

## SmokeTest

**SmokeTest runs verification without editing application code.** Run appropriate existing tests/builds/health checks and inspect results. Tests may use disposable databases and evidence output. Report failures and unverified behavior; do not silently fix application code during this mode.

## AutoLoop

**AutoLoop runs the agreed check, inspects its failure, makes the smallest in-scope fix and reruns it.** Stop on success, after five correction cycles, or at a genuine blocker. Keep a cycle count and report remaining failures/unverified checks. Do not expand scope or install unapproved dependencies.

## Git milestone / personal review

Work on a scoped `codex/` branch and preserve uncommitted changes. Never reset/switch blindly, initialize Git in another directory or guess a remote. Before the required personal review, prepare the complete scoped diff, actual verification results and a short review checklist. Ask the user for personal review/commit/push authorization only once the result is concrete and reviewable. Do not commit or push without that authorization; reuse authorization already given. Confirm the remote commit after pushing. Never change repository visibility or submit to Canvas.

`report.md` is the only Canvas artifact. It must identify the real repository URL, exact submitted implementation commit and accessible 30–60-second video link. Missing items remain unmistakably draft; never describe the package as submission-ready until resolved.
