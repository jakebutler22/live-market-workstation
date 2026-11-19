Work in my **currently selected Live Market Workstation folder and Codex chat**. This is Jake Butler’s individual IST 402 Assignment 4.2, **Indicators, Simulated Trading, and Backtesting**, due Thursday, November 19, 2026 at 11:59 p.m. Use this prompt as the complete implementation brief even if you cannot see the Canvas screenshots.

**Your job is to finish the working application and give me the actual `report.md` I upload to Canvas.** Start by inspecting what 4.1 actually built. Give me a short gap list and implementation sequence, then carry out the work. Continue through testing, browser verification, GitHub Actions, and submission preparation. Do not stop after planning or building the UI.

## 1. Protect the existing project and establish the scope

Read `README.md`, `AGENTS.md`, `handoffs/current.md`, the existing reports and design notes, dependency manifests, tests, Git status, branch, and remotes. Locate the actual Vue chart, FastAPI routes, SQLite schema, replay engine, candle identifiers, source/receipt timestamps, revision policy, and existing workflows. Find the submitted 4.1 commit if recorded. Distinguish working behavior from claims in a handoff.

Preserve the 4.1 dashboard, Yahoo Finance feed, WebSocket updates, candlesticks, volume, data-age/status labels, persistence, and replay. Protect the original market captures and the submitted 4.1 report, recording, evidence, and commit. **Give 4.2 its own report path**, preferably `submissions/4.2/report.md` unless the project already has a clear convention. The final upload filename must be exactly `report.md`.

Follow the class Vibe Checks. Inspect before editing. Use **CHECK → TAKE ACTION → VERIFY**. Reuse approved tools and dependencies. Before an unapproved installation, explain what is missing, the exact command, and its target environment. Use a scoped branch where appropriate. SmokeTest is read-only. AutoLoop may make the smallest relevant fix and rerun the check, stopping after success, five correction cycles, or a genuine blocker. Respect the course’s personal review checkpoint before committing unless I have already authorized it.

**Build only what Part 4.2 needs:**

- Two simple moving averages of different lengths and their crossover.
- A paper account that automatically applies the crossover strategy and tracks actual simulated orders, fills, cash, positions, and realized/unrealized P&L.
- A historical backtest using only information available at each decision time.
- Independent numerical verification, batch versus incremental comparison, browser tests, and automated checks on GitHub pushes.
- A concise report, supporting evidence, a real submitted commit, and one accessible 30–60-second video.

One instrument is enough. Skip optional EMA, MACD, RSI, optimization, authentication, deployment, real-money trading, broker connections, and all Part 4.3 AI, chat, vision, and audio features.

## 2. Implement and display the two SMAs correctly

Overlay both SMAs on the **existing candlestick chart**, sharing its price scale and time axis. Label the lines with their actual windows. Show their values for the inspected candle and visibly mark confirmed upward and downward crossovers. A reasonable default is **5 and 20 completed bars**. Use another existing, sensible default if documented. Use windows 2 and 3 for the worked test below.

Use the arithmetic mean of the most recent `N` eligible closing prices. On confirmed bar `t`, include that bar’s close. Return `null` and leave a gap until a full window is available. No partial-window averages, centered windows, forward-filled fictional candles, or calculations from display-rounded prices. Explain which bars qualify and how the implementation treats gaps and partial coverage.

Define crossover precisely. Use this rule unless the existing strategy has an equally explicit, tested convention:

- The first valid nonzero fast-versus-slow relationship establishes the starting side. It does not generate a trade.
- Equality keeps the last nonzero side. Touching the other line and returning to the same side generates no crossover.
- A move to the opposite side produces exactly one confirmed UP or DOWN event.
- Compare consistently at calculation precision so rounding noise does not create a signal.

**An unfinished candle cannot place an order.** Either show a clearly labeled provisional preview or state “Forming candle excluded; signals confirmed on close.” Repeated updates to the same forming candle must not count as additional closes. Distinguish a confirmed signal marker from the later fill marker.

If windows are editable, validate integer values with `1 ≤ fast < slow`. A settings change starts a new strategy configuration or run. It cannot rewrite the rationale for trades that already occurred.

## 3. Connect the strategy to an actual simulated account

Use an authoritative backend strategy and accounting implementation shared by the workstation’s paper mode and the historical engine. Vue should display the backend result. Make it possible to select or inspect **one crossover and trace it through the order, fill or skip, and resulting account balance**.

Use a simple long-only strategy. An upward cross while flat submits a buy for a documented fixed quantity. A downward cross while long submits a sell to close the position. No leverage, shorting, pyramiding, or manual order ticket is needed. Prevent duplicate orders from repeated WebSocket messages, reconnects, or duplicate candle-completion events.

Document initial cash, position sizing, fees, slippage, fill timing, cost-basis convention, and end-of-run treatment. A fixed fee and zero slippage are sufficient. Support the worked test settings internally without adding unnecessary UI controls.

Track and expose:

- **Signals:** symbol, direction, source candle, confirmation time, and associated SMA values.
- **Orders:** side, quantity, submission time, status, and a reason when skipped, rejected, or left unfilled.
- **Fills:** originating order, execution time, execution price, quantity, and fee.
- **Account:** cash, quantity held, cost basis, current mark and mark time, realized P&L, unrealized P&L, and equity.

Check affordability at fill time including fees. An unfilled or rejected order changes neither cash nor holdings. Capitalize entry fees in cost basis and deduct exit fees from sale proceeds for the worked example. Show fees separately for visibility without deducting them twice.

Use these reconciliation checks:

- Equity = cash + marked position value.
- With no deposits or withdrawals, equity minus starting cash = realized P&L + unrealized P&L.
- When the position is flat, unrealized P&L is zero.

Use decimal/fixed-precision money or a documented equivalent. Preserve the ledger across page refresh. Isolate historical runs from the active simulated account. Running the same backtest twice must not append duplicate trades to an existing paper account. Clearly label all account activity **SIMULATED**.

## 4. Build a historical backtest that does not see the future

Provide a working **Run backtest** flow over a bounded historical dataset. Prefer suitable real recordings captured in 4.1. If they lack enough bars, use another genuine historical dataset from the project’s Yahoo integration and state exactly where it came from. Reserve synthetic data for labeled deterministic checks. **The report needs at least one actual historical result**, even if it loses money or produces no trades.

Record the symbol, interval, date range/timezone, price-adjustment basis where applicable, dataset or snapshot identifier, SMA windows, starting cash, quantity, fees, slippage, and execution rule. Make the submitted run reproducible without an active market. Use a permitted snapshot or a documented acquisition path.

**Use an explicit sequence for historical OHLC bars.**

1. At the new bar’s open, execute an already-pending eligible order using the documented next-open assumption.
2. Only when that bar closes may its close enter the confirmed averages and produce a new crossover.
3. A new order remains pending until a subsequent eligible execution event. Mark end-of-bar equity using the known close.
4. A final-bar signal with no subsequent eligible price remains unfilled or expires under a documented rule. Do not force liquidation to improve the result.

The strategy must not see the next open, high, low, or close before its decision. Historical warm-up can use earlier bars but cannot generate trades before the selected run starts. Never manufacture prices in gaps.

**Respect the difference between final historical bars and captured WebSocket observations.** For a recorded stream, consume data in original availability/receipt order with a stable tie-breaker. If the first quote of the next interval was already consumed to learn that the previous interval closed, the new decision cannot retroactively fill at that quote. Use the next eligible observable price. Preserve previously issued decisions and fills when late revisions arrive.

If historical data contains only final vendor bars, describe the assumption that each completed bar was available at its close. Do not claim to reconstruct the vendor’s original revision history. If the chart displays corrected history, keep the ledger clear about what the simulated strategy actually used.

Show the historical trades, starting/ending equity, total P&L and return, and performance through time using an equity curve or readable equity table. Distinguish fills from completed round trips. Handle empty ranges, insufficient warm-up, no-cross runs, and open positions at the end. Explain what one run demonstrates about the strategy under these assumptions and what it cannot establish about future performance. Address data coverage, fill realism, and overfitting without adding a research project.

## 5. Prove the numbers with independent verification

The professor explicitly requires three different checks: **trusted reference comparison, batch versus incremental agreement, and known accounting examples**. Provide evidence for each.

**Independent reference.** Cite a trusted source for the SMA and crossover definitions. Compare actual numerical outputs on identical inputs to a reference calculation separate from production. For example, use pandas `Series.rolling(window=N, min_periods=N, center=False).mean()` in the verification environment. If production already uses pandas, use an independent exact-arithmetic direct-window calculation plus the known values below. Compare warm-up positions, indicator values, and exact crossover bars/directions. Record the input, reference, numerical tolerance, maximum observed difference, and mismatches. A documentation link by itself is not a verification result.

**Batch versus incremental.** Run the production batch calculation over a fixed series. Then feed the incremental implementation one update at a time. Compare the outputs at each available prefix, including warm-up, ties, and confirmed crossover timing. Do not call the same function twice and present that as independent agreement.

**Mandatory eight-bar test.** Turn the following into an executable fixture. These are expected values supplied independently of your implementation. Do not generate the expected values using the code under test.

| Bar | Open | Close | SMA(2) | SMA(3) | Expected event at close |
|---|---:|---:|---:|---:|---|
| 1 | 12 | 12 | null | null | None |
| 2 | 12 | 10 | 11 | null | None |
| 3 | 10 | 8 | 9 | 10 | Initialize below; no signal |
| 4 | 8 | 12 | 10 | 10 | Equal; no signal |
| 5 | 12 | 13 | 12.5 | 11 | UP; submit buy |
| 6 | 14 | 11 | 12 | 12 | Equal; no signal |
| 7 | 11 | 9 | 10 | 11 | DOWN; submit sell |
| 8 | 10 | 9 | 9 | 29/3 | None |

If the schema requires them, use `high = max(open, close)`, `low = min(open, close)`, and fixed positive test volume. For this example, start with **$1,000**, trade **2 shares**, charge **$1 per fill**, assume zero slippage, and execute at the next bar’s open.

| Checkpoint | Expected account result |
|---|---|
| Bar 5 closes | Buy order pending. Still $1,000 cash and zero shares. |
| Bar 6 opens at $14 | Buy 2 for $28 plus $1 fee. Cash $971; total position basis $29. |
| Bar 6 closes at $11 | Market value $22; equity $993; realized P&L $0; unrealized P&L −$7. |
| Bar 7 closes | Sell order pending. Still holding 2 shares. |
| Bar 8 opens at $10 | Sell both for $20 less $1 fee. Net proceeds $19. |
| Final | Cash/equity **$990**; shares **0**; realized P&L **−$10**; unrealized **$0**; fees **$2**; return **−1.00%**. Two orders, two fills, one completed round trip. |

Also test the failures this example cannot reveal by itself:

- An unfinished candle temporarily crosses, then reverses before close. It produces zero confirmed orders.
- A duplicate completion is delivered. It does not duplicate the order or fill.
- Cash is insufficient at execution. The rejected order leaves the ledger unchanged.
- A final-bar signal has no later eligible fill.
- **Future-data test:** run a prefix, then append or alter later prices or reveal a late revision. Compare outputs through the original cutoff, before end-of-run cleanup. Earlier signals, orders, fills, and equity snapshots must remain unchanged.
- Repeating the same run yields the same economic results and leaves other accounts untouched.

## 6. Integrate the design and test it in the browser

Extend my existing terminal. Preserve the compact dark surfaces, sharp dividers, muted mint/coral palette, accessible focus treatment, and tabular monospace numerals. Keep the chart dominant. Add only what helps the user inspect the strategy, paper account, or historical results.

Give the SMA lines distinguishable styles and explicit window labels. Pair color with text or shapes for crosses and fills. Clearly distinguish **live data, recorded replay, simulated account activity, and historical backtest results**. Show warm-up, forming-candle, no-trade, unavailable, and insufficient-history states in plain language. Keep the chart stable during updates and avoid resetting user zoom/pan. Check the layout on a laptop viewport with keyboard navigation.

Preserve existing browser tests. Add a deterministic end-to-end browser test using the **real local frontend and backend**. Exercise the backtest flow, inspect the two SMA values and confirmed signal, follow it to a later fill, and check the reported account result. If the chart is canvas-based, assert its accessible values or linked ledger entries and **also visually inspect** the plotted lines and markers in the running browser.

Smoke-test that the 4.1 chart and replay still work. Capture a small amount of useful evidence: a readable screenshot of the integrated screen, the independent comparison results, and a trace from one crossover to one fill and its account effect. Label fixtures, recorded market data, and live observations accurately.

## 7. Run automated checks on GitHub pushes

Inspect `.github/workflows/` first. Extend the current setup or create a workflow that **actually runs on `push` for the branch being submitted**. A manual-only or pull-request-only workflow does not meet the assignment.

On a clean runner, install from the project’s dependency files and run the relevant backend tests, frontend build/checks, and deterministic headless browser tests. Use test data and a disposable SQLite database. CI must not require Yahoo to be available, a market to be open, personal credentials, or a locally running service left over from development. Reuse the existing browser framework, such as Playwright.

Run the equivalent checks locally. After the required review and authorized push, inspect the **actual hosted GitHub Actions run for the submitted implementation commit**. Record the run URL, SHA, and result. If it fails, investigate the logs, fix the relevant issue, and verify the corrected commit. A workflow file, a passing local run, or a successful run for an older commit does not establish that the submitted commit passed. If remote access or Actions is blocked, finish all independent work and identify the remaining step.

## 8. Create the actual submission and demo

Update the existing README, design/schema notes, verification notes, numbered prompt record, handoff, and `AI-USE.md` as needed. Describe the system that exists. Keep a concise, redacted evidence log connecting decisions to actual code and observed results. Record a genuine failure or revised approach if one occurred. Give me a short explanation of one signal, its later fill, and its account effect that I can reproduce in class.

**Create the actual Part 4.2 `report.md`.** Write it in plain language that sounds like a student explaining a project they understand. Include:

1. **Submission links:** actual GitHub repository URL, full tested implementation SHA, direct commit link, and accessible video link.
2. **Completed work:** map each Canvas requirement to working functionality and supporting evidence. Include independent reference verification, batch/incremental agreement, accounting checks, causal backtesting, browser tests, and the push-triggered Actions run.
3. **Key design decisions:** explain the windows, equality rule, warm-up, unfinished candles, timing of signals and fills, fees, position sizing, and historical data source.
4. **Actual historical result:** include symbol, period, parameters, starting/ending equity, return, and trade count. Trace one trade if there was one. If there were no trades, say why. Keep this result clearly separate from the synthetic eight-bar test.
5. **Verification and limitations:** report what actually ran, what it showed, and what remains uncertain. Explain how to reproduce the submitted run.
6. **Supporting links:** use full URLs that work from a standalone Markdown upload. Link to the relevant GitHub files/evidence at an immutable commit and to the actual Actions run. Local paths and localhost addresses are not instructor evidence links.

Freeze the tested implementation/evidence commit before inserting its SHA into the Canvas report. If you later commit the report separately, keep the tested implementation SHA explicit. Do not guess a GitHub remote, change repository visibility, or claim the instructor has access just because my account does.

**Produce one 30–60-second demonstration video** if the available tools allow. Aim for about 50–55 seconds using the working app:

- **0–12s:** Show the two labeled SMAs on the price chart and point out a confirmed crossover.
- **12–28s:** Open its order and later fill. Show how the fill affected cash, position, or P&L.
- **28–47s:** Run or open the reproducible historical backtest. Show its trades, ending equity, and return.
- **47–55s:** Explain one actual limitation or execution assumption using the result on screen.

Adapt the narration to the **real** data and actual UI. A recorded historical session is fine when its provenance is clearly labeled. No separate process video is required for 4.2. If I have to record or host it, complete everything else first, leave the app ready, give me the exact clicks and a short narration using the actual result, and request only the missing video URL. Check the duration and link where possible. Identify any instructor-access check only I can perform.

## 9. Final handoff and stop condition

End your response with:

- **Submission status:** `READY TO SUBMIT` or `NOT READY`, with exact blockers.
- **Canvas file:** clickable local path to the 4.2 `report.md`.
- **Repository:** actual GitHub URL, tested implementation SHA, and direct commit link.
- **GitHub Actions:** actual run URL and status for that SHA.
- **Video:** actual link and duration, or the precise remaining recording/upload step.
- **Verification:** the actual historical result, independent SMA comparison, eight-bar accounting result, and browser-test outcome.
- **My remaining actions:** only what I personally still need to do.

Never fabricate a test result, historical run, recording, URL, permission check, or commit. If an external input is missing, prepare the most complete draft possible and mark it **NOT READY** until that input is supplied. If the last step is mine, tell me exactly what to do.

**Only `report.md` goes to Canvas.** Source stays in the linked GitHub repository. Do not submit to Canvas for me, upload a ZIP, or begin Part 4.3.

Technical references when needed: [Fidelity’s SMA and crossover guide](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/sma), [pandas trailing rolling windows](https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html), [GitHub Actions workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), and [Playwright CI](https://playwright.dev/docs/ci-intro). The Canvas requirements above govern the assignment.

**Start now. Inspect the existing project, identify the shortest path to a verified 4.2 submission, and execute it.**