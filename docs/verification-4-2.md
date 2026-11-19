# Assignment 4.2 verification

**Local implementation checks pass. NOT READY for submission yet:** the delegated review is complete; frozen implementation SHA, exact hosted push-triggered Actions result and public access to the recorded 4.2 video remain pending. Current branch is `codex/assignment-4-2`, based on `c8311ace2c955e95751960765266033b60d50913`, in the existing public [repository](https://github.com/jakebutler22/live-market-workstation). The root 4.1 report/evidence/video are preserved unchanged; canonical captured observations are retained.

## Observed requirement checks

| Requirement | Actual result/evidence |
|---|---|
| Backend rules, accounting, persistence and causality | **45 tests +19 subtests passed**, no skips, in 1.16s. [Actual output](../submissions/4.2/evidence/backend-tests.txt). One non-failing Starlette/httpx test-client deprecation warning is preserved. Includes original 4.1 tests plus new strategy/trading checks. |
| Independent numerical reference | **Three cases passed**, identical null warm-up and exact crossover bars/directions; maximum absolute SMA difference **1.4210854715202004e-14** at tolerance **1e-10**, zero mismatches. Separate pandas 3.1.1 trailing rolling means/crossover code versus production Decimal. [Inputs, reference/output and results](../submissions/4.2/evidence/numerical-verification.json). Cases are labeled synthetic: supplied eight bars, ties/gaps/precision, and a fixed series with default 5/20 windows. |
| Batch versus incremental | **14 prefixes passed**, zero mismatches, including warm-up/equality/opposite crosses/missing intervals/excluded gap/decimal closes. Incremental deque and separate batch direct-window arithmetic feed the shared account; compared points, signals, orders, fills, equity and account before end-of-run cleanup. [Detailed evidence](../submissions/4.2/evidence/numerical-verification.json). |
| Supplied accounting example | All independently supplied SMA/event/account checkpoints match. Bar 5 buy pending with $1,000/zero shares; bar 6 open buy at $14 gives $971 cash/$29 basis; bar 6 close gives $993 equity/−$7 unrealized; bar 7 sell pending; bar 8 open sell at $10 yields **$990 equity, −$10 realized, zero holdings, $2 fees, two orders/fills and one completed round trip, −1%**. [Numerical checkpoints](../submissions/4.2/evidence/numerical-verification.json), [stored synthetic result](../submissions/4.2/evidence/worked-eight-result.json). |
| Causality/failure cases | Passed forming-cross reversal/no orders, duplicate completion/no duplicate fill, insufficient cash including fee/no mutation, final signal/no later execution, future-appended/altered prices and late revision preserving prefix before cleanup, gap resets, selected-range warm-up and repeat-run isolation. [Tests](../tests/test_strategy.py), [numeric causality record](../submissions/4.2/evidence/numerical-verification.json). |
| Paper timing, restart and current mark | Quote event **2206** confirms UP but cannot fill; subsequent accepted quote **2207** fills 10 at 60.24 +1 fee, cash 9,396.6/basis 603.4. Durable paper/restart and independent backtest retrieval/isolation tests pass. A finalized vendor bar may update only current mark/provenance without rewriting prior signals/fills/equity; targeted regression passes. [Actual captured-quote trace](../submissions/4.2/evidence/paper-availability-trace.json), [tests](../tests/test_trading.py). |
| Actual SQLite/process restart | [Direct read-only inspection](../submissions/4.2/evidence/database-inspection.json) after the actual backend restart: integrity `ok`; both frozen historical/fixture JSON results match SQLite and the running HTTP retrieval exactly. Live capture remains separate. |
| Genuine historical result | [358-bar final Yahoo snapshot](../fixtures/historical/bhp-4-1.json); saved run **bt-1467499c08ac8d946575** returns **AUD 9,990.74999237060544 / −0.0925000762939456%**, 11 fills, five round trips, 10 shares open. [Full result](../submissions/4.2/evidence/historical-result.json). Observed through actual frontend/backend flow as well as engine output. |
| Real frontend/backend end-to-end tests | **Two tests passed in 2.5s** with genuine local Vite and FastAPI, disposable SQLite and no Yahoo dependency. Fixture backtest shows $990 account, inspected SMA 12.5000/11.0000, confirmed UP→BUY 2→later $14 fill→$971 cash, refresh result persistence and unchanged paper state. Genuine history/laptop keyboard flow shows 9,990.75/10 shares/14 signals; LIVE and 4.1 REPLAY remain usable. [Actual output](../submissions/4.2/evidence/browser-tests.txt), [test source](../frontend/e2e/workstation.spec.js). |
| Plotted/accessible interface | Actual screenshots were visually inspected: two distinguishable labeled SMA lines, UP/DOWN arrows and distinct square fill markers; linked ledger and account values are readable. [Historical screen](../submissions/4.2/evidence/historical-screen.jpg), [worked example](../submissions/4.2/evidence/worked-example-screen.jpg), [paper screen](../submissions/4.2/evidence/paper-screen.jpg). Laptop 1280×800 keyboard activation/no document-width overflow checked by end-to-end test; actual laptop screenshot has document width 1280 and controls 24–34 px high. [Laptop screen](../submissions/4.2/evidence/laptop-screen.jpg). The browser page-error list and inspected CUA console warnings/errors were empty. [Recorded browser measurements](../submissions/4.2/evidence/browser-observations.json). |
| Current real Yahoo and preserved 4.1 | During November 18 capture, actual Yahoo quotes resumed with the existing published 20-minute ASX delay and separate source/receipt times. [Live paper screen](../submissions/4.2/evidence/live-paper-screen.jpg) shows RECEIVING, app connected, genuine quote/SQLite capture and current mark provenance. [Exact observed quote trace](../submissions/4.2/evidence/live-regression-trace.json): event 2796 had source 23:09:36 UTC / receipt 23:29:38.235 UTC / 52.06, matching SQLite candle v15, integrity `ok`. The representative screenshot includes later live updates; subsequent paper-trace event 2801 marks 51.98 with original availability. This is distinct from final-bar historical data and offline browser fixtures. |
| Browser update-cost samples | Instrumented chart API work measured 0.10 ms for a live incremental update, 3.10 ms for a historical load and 26.10 ms for an explicit full rerun/fit. These are distinct contexts, not network-to-screen latency or full paint. [Measurements](../submissions/4.2/evidence/browser-observations.json). |
| Production build | **23 modules**, **290.11 kB JS / 97.60 kB gzip**, CSS 24.26 kB / 5.29 kB gzip; Vite build passed. [Actual output](../submissions/4.2/evidence/frontend-build.txt). |
| Hosted push automation | `.github/workflows/verify.yml` exists and triggers on **push to codex/assignment-4-2** (and PRs). Equivalent local commands above pass. Exact submitted-SHA hosted run is **PENDING**; workflow text/local pass is not hosted proof. |
| Video/publication | A genuine **55-second** [4.2 MP4](../submissions/4.2/evidence/demo.mp4) is recorded, 1440×900 H.264 / no audio / 1,949,799 bytes, from 160 actual screenshots over 55.185 seconds. Decoded frames visually verified; [metadata/hash](../submissions/4.2/evidence/video-metadata.json). Public URL/access remains **PENDING**. The 4.1 video is not substituted. |

## Reproduce the checks

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m scripts.verify_strategy
npm --prefix frontend run build
npm --prefix frontend run test:e2e
python3 -m compileall -q backend scripts tests
git diff --check
```

Environment: Python 3.14.7, pandas 3.1.1, Node 24.12.0, npm 11.6.2, project-local Playwright 1.65.1 / Chromium 159.0.8154.6. npm audit reported zero vulnerabilities. `frontend/playwright.config.js` starts disposable offline FastAPI on **8123** and real Vite on **5174** using `scripts/browser_server.py`. It refuses to reuse leftover servers, creates a temporary database, and preserves canonical capture. Browser cache uses an absolute project path derived from the config location. Clean hosted runners install locked dependencies and Chromium with system dependencies; no market, owner credentials or existing local process is required.

## Actual historical result and reproduction

Dataset `yahoo-4-1` is **358 genuine finalized BHP.AX one-minute bars**, UTC **2026-11-09 23:00 to 2026-11-11 03:22**, raw unadjusted Yahoo OHLC / share volume, extracted read-only from canonical 4.1 SQLite. Snapshot SHA-256: `919fe8716db104587c8f376b0552b865a61cd44f15cae0393b4c4f874bc5fa4d`. Final bars are assumed available at close; original vendor revision arrival is not reconstructed. Missing minutes reset windows.

Default run `bt-1467499c08ac8d946575` uses 5/20, AUD 10,000, 10-share entries, AUD 1 per fill, zero slippage, no forced liquidation. It ends at 9,990.74999237060544 equity, total P&L −9.25000762939456 / −0.0925000762939456%, 14 signals/orders, 11 fills, five completed round trips and 10 shares open. Cash 9,388.04998779296874 plus position value 602.7000045776367 equals equity. Realized −11.10000610351566 plus unrealized +1.8499984741211 equals total P&L. Final warm-up remaining 15 reflects a short segment after a gap.

The first UP belongs to the **23:27–23:28 UTC** candle (`1794266820`), confirming at close. Its pending BUY fills at the subsequent **23:28 open** (`1794266880`), **59.875 ×10 +1 fee**, cash **9,400.25**, basis **599.75**. Close-decision and next-open events can share a boundary timestamp while retaining explicit causal order. Saved historical run IDs include snapshot hash, strategy version `4.2-v1`, full configuration and range; repeating a request does not append to paper.

Offline reproduction without provider access or canonical database mutation:

```sh
.venv/bin/python - <<'PYCODE'
import json
from backend.strategy import run_backtest
from backend.trading import dataset
snapshot = dataset("yahoo-4-1")
print(json.dumps(run_backtest(snapshot["bars"], symbol=snapshot["symbol"])["summary"], indent=2))
PYCODE
```

For the actual UI: choose **Recorded dataset → YAHOO BHP.AX recorded history → Run backtest**. Inspect the confirmed UP and its linked later fill; the account shows 9,990.75 equity/−0.09% and 10 shares. `POST /api/backtests` with `{"dataset_id":"yahoo-4-1"}` reproduces the saved run; `worked-eight` reproduces **bt-380e3073f3fcc7d32d79**, the separate synthetic $990 example.

## Reference definitions

[Fidelity's SMA guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma) defines the period average and shorter/longer SMA crossover. Initialization/equality memory and long-only execution are explicit project rules. [pandas 3.1.1 rolling documentation](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html) defines `min_periods` and right-edge labeling; the independent calculation actually uses `rolling(window=N,min_periods=N,center=False).mean()` plus separate persistent-side crossing code. The [GitHub events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) and [Playwright CI](https://playwright.dev/docs/ci-intro) sources inform setup, while actual results above supply proof.

## Genuine failures and verified corrections

1. Playwright's relative browser cache resolved differently under the configured web-server working directory. The smallest fix derives an absolute project cache path; no new/global dependency was needed.
2. Initial cold navigation waited for full page `load`, consuming about 29 seconds of a test deadline despite API responses returning 200 in milliseconds. Trace inspection led to `waitUntil: 'domcontentloaded'` plus explicit actual-UI assertions, including reload. Both tests then passed. This harness AutoLoop stopped after **two correction cycles and success**.
3. A stale sampled-quote mark could misvalue an existing paper position after newer finalized vendor data became known. A mark-only adapter update now advances known current valuation and exposes source/event/availability provenance. It does not alter decisions/fills/prior snapshots; a targeted test and the final 45-test run passed.
4. Historical result identity originally omitted a version/full configuration. It now includes `strategy_version: 4.2-v1` and the full configuration; regenerated saved run IDs above replace the early IDs without changing economics. Snapshot checksum validation rejects modified data under the same identity.

## Remaining limits and submission step

The final vendor-bar availability/next-open assumption is not exchange execution or revision-history reconstruction. Paper decisions use sampled recorded quotes; gaps reset warm-up. New quotes/vendor aggregates may update the current account mark after the evidence capture, with provenance; earlier decisions/fills/equity snapshots stay immutable. One losing historical run does not establish future profitability or remove overfitting/coverage/fill-realism limits. Literal browser zoom, a screen-reader session and complete screen-paint latency were not measured.

The user delegated the review to Codex; the independent review found no material issue. Final presentation/build/browser checks pass and the finished interface has been recorded again. Continue with the authorized milestone: freeze/push the tested implementation, inspect the actual hosted push-triggered Actions result for that exact SHA, publish/check the already-recorded genuine 55-second 4.2 video, and finalize full immutable supporting URLs in [submissions/4.2/report.md](../submissions/4.2/report.md). A later report-only commit retains the tested implementation identifier. Only that file, named `report.md`, goes to Canvas.

The final visual pass and delegated review are recorded in `prompts/04-review-and-polish.md`, `submissions/4.2/review-checklist.md` and `submissions/4.2/evidence/engineering-review.json`. The final browser tests additionally open execution records and verify genuine unrounded fill 59.875 / basis599.75. Earlier live/paper screenshots remain labeled observations made before the presentation polish; the historical, worked-example and laptop screenshots show the final interface.
