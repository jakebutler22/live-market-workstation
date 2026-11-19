# Assignment 4.2 — Indicators, Simulated Trading, and Backtesting

Jake Butler · IST 402 · Live Market Workstation

## Submission links

- [GitHub repository — Assignment 4.2 branch](https://github.com/jakebutler22/live-market-workstation/tree/codex/assignment-4-2)
- Tested implementation: [18f89d505464d704a73b485dc03b4cebdd1baed2](https://github.com/jakebutler22/live-market-workstation/commit/18f89d505464d704a73b485dc03b4cebdd1baed2)
- [Passing push-triggered GitHub Actions run](https://github.com/jakebutler22/live-market-workstation/actions/runs/44425505313) for that exact commit
- [55-second demonstration — download/open MP4](https://raw.githubusercontent.com/jakebutler22/live-market-workstation/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/demo.mp4)

## What I added

I extended the existing Vue, FastAPI and SQLite workstation with two moving averages, a long-only simulated account, and a historical backtest. The Yahoo feed, candles, volume, source-age labels, persistence and recorded replay remain available. All trading activity is labeled **SIMULATED**.

| Requirement | Working result and evidence |
|---|---|
| Two SMAs and crossovers | SMA(5) and SMA(20) share the candle axes. Confirmed arrows and later fill squares are distinct. [Finished screen](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/historical-screen.jpg). |
| Simulated trading | Linked signals, orders and fills show the resulting cash, holdings, basis, fees and P&L. The ledger survives refresh/restart. [Recorded quote-to-fill trace](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/paper-availability-trace.json). |
| Historical backtest | A genuine 358-bar snapshot runs offline, with trades and a chronological equity table. Historical runs stay separate from paper mode. [Saved result](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/historical-result.json). |
| Independent reference | Three pandas comparisons had no mismatches. Maximum difference was 1.4210854715202004e-14, below the 1e-10 tolerance. [Inputs and comparison](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/numerical-verification.json). |
| Batch versus incremental | Separate direct-window and deque calculations agreed at all 14 tested prefixes, including warm-up, ties, gaps and crossings. [Detailed checks](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/numerical-verification.json). |
| Accounting and causality | 45 tests plus 19 subtests passed, covering the supplied example and failure cases. [Backend results](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/backend-tests.txt), [strategy tests](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/tests/test_strategy.py). |
| Browser and push automation | Both real frontend/backend browser tests passed after the design changes. The clean GitHub runner also passed tests, numerical checks, build and browser checks. [Browser results](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/browser-tests.txt), [workflow](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/.github/workflows/verify.yml), [actual run](https://github.com/jakebutler22/live-market-workstation/actions/runs/44425505313). |

## Rules I used

Each SMA averages a full trailing window of eligible closes, including the candle that just closed. This follows [Fidelity's SMA definition](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma). The first valid fast/slow side initializes without a trade. Equality keeps the previous side; a later switch confirms one crossover. Forming candles cannot order, and missing minutes reset warm-up.

The default account starts with **AUD 10,000** and buys **ten shares** on an UP while flat. A DOWN sells the holding. Each fill costs **AUD 1**, with zero slippage. Money uses Decimal. Entry fees join cost basis; exit fees reduce sale proceeds once. Affordability includes fees, and rejected or unfilled orders change neither cash nor shares.

Historical processing fills an already-pending order at the next eligible open, then reveals that candle's close. A final signal without a later price expires. Open holdings remain marked rather than force-sold. Paper mode follows original quote availability: the quote that confirms an interval cannot also fill its new order. Later corrections do not rewrite past decisions or fills. Current marks carry their own source and timing.

## My historical result

The dataset is **358 BHP.AX one-minute bars**, from **November 9, 2026 at 23:00 through November 11 at 03:22 UTC**, extracted read-only from the existing Yahoo/SQLite capture. It uses raw Yahoo OHLC without application adjustment. The published [snapshot and its checksum](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/fixtures/historical/bhp-4-1.json) are identified as `yahoo-4-1`.

With the default settings, the account ended at **AUD 9,990.75**, losing about **AUD 9.25**, or **−0.0925%**. It produced **14 signals/orders, 11 fills and five completed round trips**. Ten shares remained open, with AUD 11 in fees. Realized P&L was about −11.10 and unrealized P&L +1.85. The [full result](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/historical-result.json) preserves unrounded values and parameters.

One trade is easy to follow. The **23:27–23:28 UTC** candle confirmed an UP with fast **59.8560** and slow **59.8485**. The buy filled at the next open at **59.875**. Ten shares cost 598.75; adding the one-dollar fee gives **599.75 cost basis** and leaves **9,400.25 cash**. The chart, four-step trade story and expandable execution record show the same sequence.

## Checks and limits

The independent calculation uses [pandas trailing rolling means](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html), separate from production Decimal arithmetic. The supplied eight-bar check uses SMA(2)/SMA(3), $1,000, two shares and $1 fees. It ends at **$990 equity, −$10 realized P&L, zero shares and $2 fees**: two fills, one round trip and −1%. This synthetic example is clearly separated from the genuine historical result.

Tests also cover forming reversals, duplicate completions, fee-inclusive cash rejection, final unfilled signals, future-data changes, late revisions and account isolation. [Direct database inspection](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/database-inspection.json) found SQLite integrity `ok`; both saved backtests matched persisted JSON and HTTP retrieval after a real backend restart. [Live regression evidence](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/live-regression-trace.json) traces genuine Yahoo observations into SQLite and candle versions. The final [laptop screen](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/laptop-screen.jpg) has no horizontal page overflow, and keyboard controls were exercised.

To reproduce the result, start the app using the [README](https://github.com/jakebutler22/live-market-workstation/blob/8640b231f0993b6b216919309274f74312382950/README.md), choose **BHP.AX · recorded Yahoo session**, and select **Run backtest**. The saved snapshot works without Yahoo. The [design notes](https://github.com/jakebutler22/live-market-workstation/blob/8640b231f0993b6b216919309274f74312382950/docs/design-pipeline.md) explain the schema and processing rules; [verification notes](https://github.com/jakebutler22/live-market-workstation/blob/8640b231f0993b6b216919309274f74312382950/docs/verification-4-2.md) give commands and observed results.

This is one small simulation, not evidence of future profitability. Yahoo data is sampled and delayed. Final historical bars are assumed available at close; original vendor revision arrival is not reconstructed. Next-open fills simplify execution, and gaps reduce usable history. The video is a silent recording of the real app using timestamped browser screenshots, with no invented market motion; [capture metadata](https://github.com/jakebutler22/live-market-workstation/blob/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/video-metadata.json) records its method and duration. [AI-USE.md](https://github.com/jakebutler22/live-market-workstation/blob/8640b231f0993b6b216919309274f74312382950/AI-USE.md) describes the actual assistance and delegated review.

## Supporting access and upload

Repository, commit, screenshot, numerical evidence and the complete video were checked anonymously over HTTPS. The public video's hash matches the verified local 55-second file. The MP4 link offers download/open; instructor-specific network restrictions were not tested. [Anonymous access record](https://github.com/jakebutler22/live-market-workstation/blob/8640b231f0993b6b216919309274f74312382950/submissions/4.2/evidence/publication-access.json) and [hosted run metadata](https://github.com/jakebutler22/live-market-workstation/blob/8640b231f0993b6b216919309274f74312382950/submissions/4.2/evidence/hosted-actions.json) preserve the checks.

Only this file goes to Canvas, named **report.md**. Source stays in the linked repository; no ZIP is required.
