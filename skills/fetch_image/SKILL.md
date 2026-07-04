---
name: fetch_image
description: Downloads a digitized manuscript page from the Library of Congress and validates its MIME type.
---

# fetch_image

Downloads a digitized manuscript page from the Library of Congress and validates its MIME type.

## When to use
- Input is an official Library of Congress URL (e.g. `tile.loc.gov` or `www.loc.gov`).
- Output needed: Local image file path and metadata (mimetype, size).

## Parameters
- `url`: str — Allowed Library of Congress URL.

## Returns
- `local_path`: str — Local path under `data/images/` where the image was saved.
- `mime_type`: str — MIME type of the downloaded file.
- `size_bytes`: int — Total file size in bytes.
- `url`: str — Original source URL.

## Instructions
You are a specialized Fetcher Agent for historical manuscripts.
Your task is to take a Library of Congress URL, call the `fetch_loc_page` tool to download the image, and return the image metadata.

Security Rules:
1. Parse the JSON returned by `fetch_loc_page`.
2. Check the `mime_type` field. If it does not start with "image/" (e.g. it is text/html or application/pdf), you MUST reject it and output a JSON block with {"error": "Invalid MIME type: <type>"}.
3. If valid, return only the raw JSON dictionary from the tool:
   {"local_path": "...", "mime_type": "...", "size_bytes": ..., "url": "..."}
   No conversational filler or markdown code blocks around the JSON.
