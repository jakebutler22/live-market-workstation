# Assignment 4.2 — Indicators, Simulated Trading, and Backtesting

Jake Butler · IST 402 · Live Market Workstation

**NOT READY TO SUBMIT:** local implementation and final visual review pass; the submitted commit, hosted Actions result and public video links are being completed. The user delegated the review to Codex. The original 4.1 submission is preserved.

## Submission links

- [GitHub repository](https://github.com/jakebutler22/live-market-workstation)
- Tested 4.2 commit and direct link: **pending**
- GitHub Actions run for that commit: **pending**
- Final 30–60-second video: **pending**; the finished interface has a verified 55-second local recording, awaiting publication

## What I built

I added a simple crossover strategy to the existing Vue, FastAPI and SQLite workstation. The Yahoo feed, candles, volume, data-age labels and replay still work. Everything in the new account is labeled **SIMULATED**.

| Requirement | Result so far |
|---|---|
| Two moving averages | SMA(5) and SMA(20) use the chart's price/time scale. Confirmed UP/DOWN arrows and later fill markers are separate. |
| Simulated trading | Signals lead to orders and later fills. The account keeps cash, holdings, cost basis, fees, marks and realized/unrealized P&L across refresh/restart. |
| Historical backtest | A genuine 358-bar Yahoo snapshot runs offline. Trades and equity history are shown, and historical runs stay separate from the paper account. |
| Independent comparison | Three pandas comparisons passed with no mismatches. Maximum difference: 1.4210854715202004e-14, below the 1e-10 tolerance. |
| Batch versus incremental | Separate algorithms agreed at all 14 tested prefixes, including warm-up, equality, gaps and crossings. |
| Accounting and causality | 45 tests plus 19 subtests passed. The supplied eight-bar example ends at $990, with −$10 realized P&L, $2 fees, two fills and one round trip. |
| Browser and automation | Two real frontend/backend browser tests passed after the visual polish, including exact execution records. The workflow runs on pushes; the final hosted run still needs verification. |

Final evidence links will be pinned to the tested commit. The final screen and recording are verified locally; public links and hosted verification are pending.

## How the strategy works

Each SMA is a trailing average of completed, eligible closes, consistent with [Fidelity's definition](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma). A full window is required. The first valid side sets the starting state without a trade; equal averages keep that side. A later switch confirms a crossover. Forming candles cannot place orders, and missing minutes reset warm-up.

The long-only account starts with **AUD 10,000**, buys **ten shares** on an UP while flat, and sells the holding on a DOWN. Each fill costs **AUD 1**, with zero slippage. Entry fees go into cost basis; exit fees reduce proceeds once. A rejected or unfilled order changes neither cash nor holdings.

The historical engine fills an earlier pending order at the next eligible bar's open, then reveals that bar's close. A final signal without another price expires; open holdings are marked, not force-sold. Paper mode instead uses original quote availability. The quote that confirms a candle cannot also fill its new order. Later corrections cannot rewrite past decisions or fills. New known data may update the current account mark, with its source and timing visible.

## My historical result

I used **358 recorded BHP.AX one-minute bars**, from **November 9, 2026 at 23:00 through November 11 at 03:22 UTC**. They came from the existing Yahoo/SQLite capture and use raw Yahoo prices without application adjustment. The saved dataset is `yahoo-4-1`.

With the default 5/20 settings, the account ended at **AUD 9,990.75**: a loss of about **AUD 9.25**, or **−0.0925%**. There were **11 fills, five completed round trips, ten shares still held and AUD 11 in fees**. Realized P&L was about −11.10 and unrealized P&L +1.85.

One trade is easy to follow: the 23:27–23:28 candle confirmed an UP. The buy filled at the next open at **59.875 per share**. Ten shares cost 598.75; adding the one-dollar fee gives **599.75 cost basis**, leaving **9,400.25 cash**. The linked signal, order and fill show this sequence in the app.

## Checks and limits

The independent [pandas calculation](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html) checks full-window averages, warm-up and crossover bars separately from production Decimal arithmetic. Tests also cover forming reversals, duplicate completions, insufficient cash, unfilled final signals, future-data changes, late revisions and account isolation. Browser tests checked the eight-bar account trace, refresh persistence, the real historical result, laptop keyboard use and the original replay.

To reproduce the historical result, choose **Recorded dataset → Yahoo BHP.AX history → Run backtest**. The snapshot also runs without Yahoo. The same run can also be retrieved from SQLite after a backend restart.

This is a small simulation, not evidence of future profitability. Yahoo data is sampled/delayed. Final historical bars are assumed available at close, and next-open fills simplify real execution. Gaps reduce usable history. The final video will disclose its actual capture method. Literal browser zoom, screen-reader use and full paint latency have not been measured.

## Supporting evidence

**Pending the frozen implementation SHA:** README, design notes, numerical checks, backend/browser results, the historical snapshot/result, one signal-to-fill trace, the exact Actions run and final video will have full immutable links here. Local paths and localhost pages are not instructor evidence.

Only this file goes to Canvas, named **`report.md`**. Source stays in GitHub; no ZIP is required.
