"""
Archive Whisperer — LOC sample image downloader

Uses the official Library of Congress JSON API (documented at loc.gov/apis)
to resolve real image URLs for each item, then downloads them.

Run this INSIDE Antigravity (or any environment with internet access) —
it will NOT work in a network-sandboxed environment.
"""

import requests
import pathlib
import time
import json

OUT_IMAGES = pathlib.Path("data/images")
OUT_GROUND_TRUTH = pathlib.Path("data/ground_truth")
OUT_IMAGES.mkdir(parents=True, exist_ok=True)
OUT_GROUND_TRUTH.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "ArchiveWhisperer-Capstone/1.0 (educational research project)"}

# ── Verified real Lincoln Papers items (confirmed to exist via LOC search) ──
LINCOLN_ITEMS = [
    ("mal1723200", "Preliminary Draft of the Emancipation Proclamation, July 22, 1862"),
    ("mal0773800", "First Inaugural Address, Final Version, March 1861"),
    ("mal4233400", "Lincoln to Horace Greeley, August 22, 1862"),
    ("mal0007400", "Lincoln to Congress re: Mexican War, January 12, 1848"),
    ("mal1728600", "Lincoln to Cuthbert Bullitt, July 28, 1862"),
    ("mal0843200", "Cassius M. Clay to Lincoln, March 28, 1861"),
    ("mal1310600", "Nevada Territory Legislature Resolution, November 25, 1861"),
    ("mal1284500", "British Newspaper Clippings, November 5, 1861"),
]

# ── Gibson Civil War Diary — multi-page item, access via ?sp=N ──────────────
GIBSON_RESOURCE_ID = "mss5241.mss5241_01_001_089"
GIBSON_PAGES = [11, 37, 49]  # sample page numbers found via search; add more as desired


def fetch_item_json(item_id: str) -> dict:
    """Query LOC's JSON API for a single item."""
    url = f"https://www.loc.gov/item/{item_id}/?fo=json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_resource_page_json(resource_id: str, page: int) -> dict:
    """Query LOC's JSON API for a specific page of a multi-page resource."""
    url = f"https://www.loc.gov/resource/{resource_id}/?sp={page}&fo=json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def best_image_url(item_json: dict) -> str | None:
    """Extract the highest-resolution image URL from LOC JSON response."""
    # If this is a page-specific resource, page details are under the 'page' key
    page_formats = item_json.get("page", [])
    if page_formats:
        # Filter for JPEG images and extract URLs
        jpeg_urls = [f.get("url") for f in page_formats if f.get("mimetype") == "image/jpeg" and f.get("url")]
        if jpeg_urls:
            # Sort by pct: resolution percentage if available
            def pct_value(url):
                if "pct:" in url:
                    try:
                        return float(url.split("pct:")[1].split("/")[0])
                    except ValueError:
                        pass
                return 0
            return sorted(jpeg_urls, key=pct_value)[-1]

    # Otherwise, fallback to the standard item image_url list
    image_urls = item_json.get("item", {}).get("image_url", [])
    if image_urls:
        return image_urls[-1]  # last = highest resolution

    # Fallback 2: check resources[0].files for IIIF service URLs
    resources = item_json.get("resources", [])
    if resources and "files" in resources[0]:
        files = resources[0]["files"]
        if files and isinstance(files[0], list):
            # nested per-page file list — take first page, largest file
            candidates = [f for f in files[0] if f.get("mimetype", "").startswith("image")]
            if candidates:
                return sorted(candidates, key=lambda f: f.get("width", 0))[-1].get("url")
    return None


def download_image(url: str, out_path: pathlib.Path) -> bool:
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            return True
        except Exception as e:
            print(f"  FAILED (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(2)
    return False


def main():
    manifest = []  # for README citation table

    print("=" * 60)
    print("LINCOLN PAPERS")
    print("=" * 60)
    for item_id, description in LINCOLN_ITEMS:
        print(f"\n[{item_id}] {description}")
        try:
            data = fetch_item_json(item_id)
            img_url = best_image_url(data)
            if not img_url:
                print("  No image URL found in JSON response — skipping")
                continue

            out_file = OUT_IMAGES / f"lincoln_{item_id}.jpg"
            if download_image(img_url, out_file):
                print(f"  Saved: {out_file}")
                manifest.append({
                    "filename": out_file.name,
                    "collection": "Abraham Lincoln Papers",
                    "item_id": item_id,
                    "description": description,
                    "source_url": f"https://www.loc.gov/item/{item_id}/",
                    "image_url": img_url,
                })
        except Exception as e:
            print(f"  ERROR fetching item JSON: {e}")

        time.sleep(1.5)  # be polite to LOC servers

    print("\n" + "=" * 60)
    print("GIBSON CIVIL WAR DIARY")
    print("=" * 60)
    for page in GIBSON_PAGES:
        print(f"\n[Page {page}] Gibson Diary")
        try:
            data = fetch_resource_page_json(GIBSON_RESOURCE_ID, page)
            img_url = best_image_url(data)
            if not img_url:
                print("  No image URL found — skipping")
                continue

            out_file = OUT_IMAGES / f"gibson_page{page:03d}.jpg"
            if download_image(img_url, out_file):
                print(f"  Saved: {out_file}")
                manifest.append({
                    "filename": out_file.name,
                    "collection": "Samuel J. Gibson Diary and Correspondence",
                    "item_id": f"{GIBSON_RESOURCE_ID}_sp{page}",
                    "description": f"Gibson diary, page {page}",
                    "source_url": f"https://www.loc.gov/resource/{GIBSON_RESOURCE_ID}/?sp={page}",
                    "image_url": img_url,
                })
        except Exception as e:
            print(f"  ERROR fetching page JSON: {e}")

        time.sleep(1.5)

    # ── Save manifest for README citations ──────────────────────────────────
    manifest_path = pathlib.Path("data/manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n\nSaved {len(manifest)} images. Manifest written to {manifest_path}")

    print("\n" + "=" * 60)
    print("GROUND TRUTH — Gibson Diary Transcription Dataset")
    print("=" * 60)
    print("Download the full verified transcription dataset manually from:")
    print("  https://www.loc.gov/item/2019667238/")
    print("This gives you human-verified transcripts for all 90 Gibson diary")
    print("images in one dataset — save it to data/ground_truth/")
    print("This is your answer key for computing real accuracy (CER) scores.")


if __name__ == "__main__":
    main()
