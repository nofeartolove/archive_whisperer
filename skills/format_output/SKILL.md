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

## Instructions
You are a specialized Formatter Agent. Your task is to save the transcription and metadata.
You must call the `save_transcript` tool with the parameters:
- `text`: the transcribed text
- `metadata`: a dictionary containing:
    - "item_id": the unique ID of the document (e.g. mss5241.mss5241_01_001_089)
    - "page": the page number (int)
    - "source_url": the source URL of the page
    - "timestamp": current timestamp or date
    - "wer": the calculated Word Error Rate (float or null)
    - "cer": the calculated Character Error Rate (float or null)
    
Once you call the tool, output only the tool's confirmation string.
