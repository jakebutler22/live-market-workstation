# Current handoff — Assignment 4.2

Branch: `codex/assignment-4-2`. Repository: https://github.com/jakebutler22/live-market-workstation. Tested implementation: **18f89d505464d704a73b485dc03b4cebdd1baed2**. [Actual push run](https://github.com/jakebutler22/live-market-workstation/actions/runs/44425505313): **SUCCESS**, attempt 1. Later commits contain publication/report documentation only.

The user delegated the review to Codex and requested a more natural presentation. That review and visual pass are complete. No new approval is pending. The existing compact terminal now uses clearer headings, readable text, expandable records and a four-step signal/order/fill/account explanation. AI assistance and delegated review remain disclosed.

## What works

- Shared Decimal SMA5/20, full-window warm-up, equality memory and confirmed crossovers. Forming candles cannot order; gaps reset windows.
- Durable long-only SIMULATED paper account using original quote availability, with a later quote fill. Historical backtests use a checksum-verified offline final-bar snapshot and a separate account. Revisions cannot rewrite earlier decisions/fills.
- Real BHP.AX snapshot: 358 one-minute bars, November 9 at 23:00 through November 11 at 03:22 UTC. Default historical result: AUD 9,990.74999237060544 equity, −0.0925000762939456%, 11 fills, five round trips, ten shares open, AUD 11 fees. No forced liquidation.
- Exact first historical buy: 59.875 ×10 +1 fee = 599.75 basis, leaving 9,400.25 cash. Original quote-paper confirmation event 2206 cannot fill; later event 2207 fills 10 at 60.24 +1.
- Existing Yahoo streaming, candles/volume, source/receipt age/status, SQLite and recorded replay remain. Original 4.1 root report/evidence/video/provider/market/store files are unchanged; captured databases remain local and intact.

## Verification

Local: 45 tests +19 subtests (1.16s); three pandas cases and 14 prefixes, zero mismatches/max error 1.4210854715202004e-14 below 1e-10; build 290.11kB JS/97.60kB gzip; two real frontend/backend browser tests (2.5s). Hosted: same checks pass, backend 2.04s/browser 4.8s. One non-failing test-client warning is preserved.

Actual 1440×900 and 1280×800 visual checks passed; laptop has no horizontal page overflow and essential controls are 24px or larger. Exact execution disclosure and keyboard End access to final equity rows were exercised; console errors/warnings empty. Literal zoom, screen-reader use and full network-to-paint latency were not measured.

The final silent 55.000s H.264 video uses 160 actual screenshots over 55.185s. All images and final assumptions scene survive encoding; public bytes/hash/range match. [Video](https://raw.githubusercontent.com/jakebutler22/live-market-workstation/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/demo.mp4). Evidence: `submissions/4.2/evidence/README.md`, hosted-actions.json and publication-access.json.

## Startup and next step

Start with `.venv/bin/python -m scripts.start`; frontend http://127.0.0.1:5173/ and backend 8000. Keep the launcher running; do not start duplicate capture processes or erase captured data. Existing Python 3.14.7 / Node 24.12.0 / approved local Playwright 1.65.1 are installed.

Finish/check the final standalone `submissions/4.2/report.md` publication and remote hash. The user's only remaining submission action is to upload that file to Canvas with filename **report.md**. Do not upload a ZIP, submit to Canvas for the user, change repository visibility or begin Part 4.3.
