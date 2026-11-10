# Assignment 4.1 — 55-second demonstration

**Recorded locally: [demo-4-1.mp4](../evidence/demo-4-1.mp4).** Duration **55 seconds**, H.264 MP4, **1440×900**, **no audio**, fast-start, **3,295,740 bytes**. [Recording metadata](../evidence/demo-video.json). The accessible hosting URL is still **MISSING**, so the report is not ready to submit.

## What was recorded

Codex captured **205 genuine browser-only page screenshots** from the actual running application during a real 55-second sequence, retaining their actual irregular capture timestamps. The system AVFoundation encoder assembled those real-time frames into the MP4; this was not a native screen-recorder API. No price movement, UI state or source data was generated for the recording. Only the app page was captured, excluding chat, desktop accounts and unrelated windows. The source was resumed after the final induced outage.

| Actual elapsed time | Screen/action in the recording |
|---|---|
| 0–15.349s | LIVE market view, actual Yahoo capture, candlesticks/aligned volume, source/feed/age information. BHP.AX's published 20-minute delay remains visible. |
| 15.349–27.815s | Open actual saved-event payload, with its identity and separate source/receipt timestamps. The direct SQL/UI trace is supplied separately in the evidence. |
| 27.815s | Switch to REPLAY. |
| 28.265s | Start the recorded session at 60×, with REPLAY and original recording time visible. |
| 36.298s / 39.397s | Pause and resume playback. |
| 42.947–55s | Return to LIVE and induce upstream interruption. Show the unavailable-source state, connected application socket, retained chart/history and aging source timestamp. |

The recording has no spoken narration. Browser screenshots and direct SQL evidence provide longer verification details; a separate development-process recording is not required. Native Codex application control was restricted, while normal browser screenshot/interaction APIs were available. Local encoding used the existing system framework without installing another dependency.

Actual MP4 frames decoded around 0, 20, 33 and 50 seconds were inspected upright and readable. They show the live source/volume, expanded saved quote **894**, replay/original recording time and induced outage respectively. The quote's SQLite candle v11 matches O 59.96 / H 59.97 / L 59.96 / C 59.97; induced feed event **905** preserves the gap revision. Metadata reports one H.264 video track, no audio, nominal approximately **3.74 fps** with genuine irregular capture timing, and fast-start ordering. SHA-256: `ff7dacef30b44ffb1e6dfb32230759c2fbd109c5be6fc1a359d6edd80fdc5961`.

## Publish and check access

1. Preview the local MP4 and confirm the live → saved payload → replay → induced outage sequence is readable.
2. Upload this existing file to the confirmed GitHub repository or another service the user already uses, with instructor-accessible sharing. No new recording is required unless the user wants to replace it.
3. Supply the actual accessible video URL. Codex can insert it into `report.md` and check the link as far as the available tools allow. Authenticated owner access does not prove instructor access; check signed-out or instructor-equivalent access where appropriate.
4. Keep the verified duration **55 seconds** and the precise capture method with the video evidence. Do not imply an audio narration exists.

## Repeat only if replacing the recording

Run `python3 scripts/start.py` if the app is stopped; keep its terminal open and visit `http://127.0.0.1:5173/`. At approximately 1440×900, use LIVE until Yahoo is receiving an actual new quote, show genuine historical volume, inspect a saved payload, use REPLAY → 60× → Start/Pause/Resume, then return to LIVE and click **Interrupt Yahoo feed**. End between 30 and 60 seconds; resume Yahoo afterward. Never substitute invented motion or replay for live Yahoo evidence.

Literal 150% browser zoom and screen-reader behavior remain manual checks; equivalent 853×533 reflow and keyboard/focus/laptop layouts are already observed. The user has explicitly approved the reviewed implementation's commit and push; reuse that approval. The real repository URL, verified remote implementation SHA, accessible video URL and instructor access remain publication inputs. Canvas receives only `report.md`.
