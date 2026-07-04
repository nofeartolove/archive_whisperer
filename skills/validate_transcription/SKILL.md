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

## Instructions
You are a validation agent for historical manuscript transcriptions.
Your task is to call the `get_bythepeople_transcript` tool with the provided `item_id` to retrieve the official crowdsourced ground truth transcription.

Once you call the tool:
1. If the tool indicates the transcript is not available, output: {"available": false, "ground_truth": ""}
2. If the tool returns a transcript, output a clean JSON object containing the ground truth:
   {"available": true, "ground_truth": "<insert transcription text here>"}
   Do not add any preamble, markdown code blocks, or conversational text.
