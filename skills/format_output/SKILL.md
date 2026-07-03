---
name: format_output
description: Saves transcription results to JSON, Markdown, and plain text formats in output/.
---

# format_output

Saves transcription results to JSON, Markdown, and plain text formats in output/.

## When to use
- Pipeline transcription and validation checks are completed.
- Saving output files for archiving and human review.

## Parameters
- `text`: str — Final transcription text.
- `metadata`: dict — Provenance metadata including page, item_id, source_url, wer, and cer.

## Returns
- `summary`: str — Confirmation of saved file paths.
