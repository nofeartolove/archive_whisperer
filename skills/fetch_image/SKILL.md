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
