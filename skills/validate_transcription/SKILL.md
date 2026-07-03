---
name: validate_transcription
description: Retrives crowdsourced ground truth transcripts from the Library of Congress and computes Word Error Rate (WER) and Character Error Rate (CER).
---

# validate_transcription

Retrieves crowdsourced ground truth transcripts from the Library of Congress and computes Word Error Rate (WER) and Character Error Rate (CER).

## When to use
- Verification of agent transcription quality is needed.
- Ground truth transcription is available in the LOC By the People dataset.

## Parameters
- `item_id`: str — Unique Library of Congress item ID.
- `transcription`: str — Agent generated transcript.

## Returns
- `available`: bool — True if ground truth transcript was successfully found.
- `wer`: float — Word Error Rate calculated via jiwer (null if not available).
- `cer`: float — Character Error Rate calculated via jiwer (null if not available).
- `ground_truth`: str — Cleaned ground truth transcript.
