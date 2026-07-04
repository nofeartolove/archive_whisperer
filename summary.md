# Capstone Issues Summary - Archive Whisperer

This document details the code review issues fixed in the **Archive Whisperer** repository prior to recording the capstone demonstration video.

---

## 1. Summary of Issue Resolutions

### Issue 1 (Critical): Filename/item_id Mismatch & Live Validation
* **Root Cause**: The orchestrator was resolving `item_id` by matching substrings like `"page011"` or `"001_0011"` in the local filename string, which failed when using real Library of Congress filenames (e.g., `service_mss_mss5241_01_011.jpg`).
* **Fix**: Implemented a regex-based URL parser `resolve_item_details_from_url()` in `agents/orchestrator.py` that extracts the page number segment directly from the source IIIF URL, strips leading zeros, and resolves the correct sub-page `item_id` (e.g. `mss5241.mss5241_01_001_089_sp11`).
* **Cleanup**: Although planned earlier, the three duplicate image files (`service_mss_mss5241_01_011.jpg`, `service_mss_mss5241_01_037.jpg`, and `service_mss_mss5241_01_049.jpg`) were fully deleted from `data/images/` during the final code review session (Fix 3), leaving exactly 11 files (8 Lincoln, 3 Gibson).

### Issue 2: Incorrect Document Reference in README
* **Fix**: Corrected the reference to "William T. Sherman Civil War Diaries (1864)" in Section 5 of `README.md` to **"Samuel J. Gibson Civil War Diary (1864)"**.

### Issue 3: Standardized API Key Environment Variables
* **Fix**: Standardized on `GOOGLE_API_KEY` across both `README.md` and `.env.example`.
* **Commentary**: Added a comment explaining that `LOC_API_KEY` is optional and only used for bulk extraction/download scripts. Verified `.env` is ignored by Git.

### Issue 4: Dynamic Agent Prompt Loading from Skills
* **Fix**: Refactored all 4 agents (`fetcher.py`, `transcriber.py`, `validator.py`, and `formatter.py`) to read their instructions dynamically from their corresponding `SKILL.md` under `skills/<skill_name>/SKILL.md`. Added a `## Instructions` heading to isolate prompts.

### Issue 5: Missing `mcp` Dependency in requirements.txt
* **Fix**: Added the exact installed version `mcp==1.28.1` directly to `requirements.txt`.

### Issue 6: Deprecated Fallback Model & Chain Expansion
* **Fix**: Replaced the deprecated `"gemini-1.5-flash"` model in all agent fallback lists with `"gemini-3.1-flash-lite"` and appended `"gemini-2.5-flash-lite"`. Increased default retries count from 3 to 4.

---

## 2. Live Validation Results

The pipeline was executed end-to-end on all three Gibson pages:
```powershell
python agents/orchestrator.py
```

All runs completed successfully, fetching ground truth transcripts online (`available: True`) and computing the following Word Error Rates (WER) and Character Error Rates (CER):

| Gibson Page | Resolved Item ID | Available | Word Error Rate (WER) | Character Error Rate (CER) | Output File Stem |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Page 11** | `mss5241.mss5241_01_001_089_sp11` | **True** | **52.16%** | **27.35%** | `mss5241.mss5241_01_001_089_sp11_011` |
| **Page 37** | `mss5241.mss5241_01_001_089_sp37` | **True** | **32.26%** | **20.64%** | `mss5241.mss5241_01_001_089_sp37_037` |
| **Page 49** | `mss5241.mss5241_01_001_089_sp49` | **True** | **22.46%** | **17.28%** | `mss5241.mss5241_01_001_089_sp49_049` |

### Fallback Resilience Log (Page 49)
During the Page 49 execution, the primary model (`gemini-3.5-flash`) hit a free-tier rate limit (429 RESOURCE_EXHAUSTED). The dynamic rotation mechanism automatically caught the exception, paced for 10 seconds, swapped to `gemini-2.5-flash`, and completed the transcription and validation stages with 100% success.

---

## 3. Final Code Review Fixes (Final Verification Round)

A second round of target fixes was applied and verified to ensure maximum repository hygiene and test performance:

### Fix 1: Reconciled WER/CER Numbers
* **Issue**: The `README.md`, `summary.md`, and sample reports previously showed mismatched metrics from older development runs.
* **Fix**: Ran a single, canonical pipeline execution to capture identical error rates across all files and copied the true generated files into `sample_output/`.

### Fix 2: Metadata Key Alignment (`source_url` vs `url`)
* **Issue**: The formatter looked for `source_url` in metadata while other components passed it as `url`, resulting in `"Source URL: N/A"` on reports.
* **Fix**: Fixed `agents/formatter.py` to read `metadata.get('url')`. All reports now correctly show the Library of Congress page URL.

### Fix 3: Duplicate Image Files Deletion
* **Issue**: Three duplicate image files (`service_mss_mss5241_01_*.jpg`) remained in `data/images/`.
* **Fix**: Deleted the duplicates, leaving exactly **11 clean images** in the evaluations folder.

### Fix 4: Isolated Live Network Tests
* **Issue**: `tests/test_transcriber.py` was executing live, unmocked Gemini API calls during default `pytest` runs, burning rate limits and causing offline runs to fail.
* **Fix**: Marked the live tests with `@pytest.mark.live`. Default `pytest` execution now skips them automatically, passing cleanly with zero network hits.
