# Assignment4.2 — final55second demonstration

The finished interface is recorded in [demo.mp4](evidence/demo.mp4): **55.000seconds**, 1440×900 H.264, silent, 1,949,799bytes. [Metadata](evidence/video-metadata.json), [timing verification](evidence/video-timing-verification.json), [poster](evidence/demo-poster.jpg), [decoded final frame](evidence/demo-final-frame.jpg).

The video uses160 actual browser screenshots over55.185seconds with their irregular acquisition times. No synthetic market motion, altered UI, narration or overlays were added. All160 screenshots survive encoding; duration and decoded start/detail/final-stage content were checked. Maximum timestamp quantization difference is0.000667seconds. Source frames stayed temporary.

| Time | Actual content |
|---|---|
|0–12s| Genuine BHP.AX historical chart; labeled5/20SMAs, confirmed UP and separate later BUY fill. The plain-language story shows9,400.25cash after10shares andonefee. |
|12.591s| Open execution records: original IDs, unrounded59.875fill,599.75basis and original times. |
|23.525s| Return to the readable crossover/order/fill/account story. |
|29.860s| Run the same historical backtest again and fit all recorded bars. Result remains9,990.75equity,−0.0925%,11fills/five round trips/ten shares held. |
|40.274s| Open equity history and use the keyboard End key to reach the final balances. |
|48.609s| Open session details and scroll to provenance/assumptions. First screenshot of this stage is50.093s; final-bar availability and next-open fill limits remain visible to55s. |

In class: explain the23:27–23:28UTC crossover, next-open fill59.875×10+1=599.75basis, and9,400.25cash. The final position is marked rather than force-sold. This one losing run does not establish future performance. The synthetic eight-bar check is separate from this genuine358-bar snapshot.

SHA256:`5b95acd7ba1eed72bdb03face9dac1da8d07cc0575a8ca67f4d65d74475f9c36`.

The reviewed implementation must be pushed and its exact Actions run/publication verified before the report is ready. Only the completed4.2report.md goes to Canvas; do not submit it automatically. The original4.1video is preserved.
