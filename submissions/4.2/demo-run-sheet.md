# Assignment 4.2 — final 55-second demonstration

[Download/open the final MP4](https://raw.githubusercontent.com/jakebutler22/live-market-workstation/18f89d505464d704a73b485dc03b4cebdd1baed2/submissions/4.2/evidence/demo.mp4). It is **55.000 seconds**, 1440×900 H.264, silent, and 1,949,799 bytes. [Metadata](evidence/video-metadata.json), [timing verification](evidence/video-timing-verification.json), [poster](evidence/demo-poster.jpg), [decoded final frame](evidence/demo-final-frame.jpg).

The recording uses 160 actual browser screenshots over 55.185 seconds, preserving their irregular acquisition times. No invented market motion, altered UI, narration or overlays were added. Every screenshot survived encoding; duration and decoded detail/final-stage content were checked. Maximum timestamp quantization difference is 0.000667 seconds. Source frames stayed temporary.

| Time | Actual content |
|---|---|
| 0–12s | Genuine BHP.AX historical chart with labeled 5/20 SMAs, a confirmed UP and separate later BUY fill. The story shows 9,400.25 cash after ten shares and one fee. |
| 12.591s | Open execution records: original IDs, unrounded 59.875 fill, 599.75 basis and original times. |
| 23.525s | Return to the crossover/order/fill/account story. |
| 29.860s | Repeat the historical run and fit the whole dataset. The result remains 9,990.75 equity, −0.0925%, 11 fills, five round trips and ten shares held. |
| 40.274s | Open equity history and use the keyboard End key to reach the final balances. |
| 48.609s | Open session details and scroll to provenance/assumptions. The first screenshot of this stage is at 50.093s; availability and execution limits remain visible through the end. |

In class: explain the 23:27–23:28 UTC crossover, the next-open fill at 59.875 ×10 +1 fee =599.75 basis, and 9,400.25 cash. The final position is marked rather than force-sold. This one losing run does not establish future performance. The synthetic eight-bar check is separate from this genuine 358-bar snapshot.

SHA-256: `5b95acd7ba1eed72bdb03face9dac1da8d07cc0575a8ca67f4d65d74475f9c36`.

The reviewed implementation is `18f89d505464d704a73b485dc03b4cebdd1baed2`; its [actual push run](https://github.com/jakebutler22/live-market-workstation/actions/runs/44425505313) passed. Anonymous publication checks verified the complete video's hash and byte-range retrieval. Only the completed 4.2 report goes to Canvas, named **report.md**. The original 4.1 video is preserved.
