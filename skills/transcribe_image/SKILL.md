---
name: transcribe_image
description: Transcribes handwritten historical manuscript images using Gemini Vision.
---

# transcribe_image

Transcribes handwritten manuscript images using Gemini Vision.

## When to use
- Input is a JPG/PNG of a handwritten historical document.
- Output needed: plain text transcription conforming to paleographic guidelines.

## Parameters
- `image_path`: str — local path or base64 encoded image.
- `century_hint`: str — '18th', '19th', '20th' (helps model calibrate script style).

## Returns
- `transcript`: str — raw transcription.
- `confidence`: float — model self-reported confidence 0.0–1.0.
- `illegible_count`: int — number of [illegible] markers inserted.

## Instructions
You are an expert paleographer specializing in 19th-century American handwriting.
Transcribe the handwritten text in the provided image exactly as written.
Rules: preserve original spelling/punctuation, mark illegible words as [illegible], note line breaks with |, return ONLY the transcription - no commentary.
