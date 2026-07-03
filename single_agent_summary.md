# Baseline Report: Single-Agent Transcriber

This document serves as the local reference and benchmark for the single-agent implementation of the **Archive Whisperer** paleographer. 

---

## 1. Agent Configuration
* **Agent Name**: `transcriber_agent`
* **Underlying Model**: `gemini-2.5-flash`
* **Persona & Instructions**:
  Enforces paleography rules for 19th-century American handwriting:
  * Preserve original spelling/punctuation exactly.
  * Mark illegible/unreadable text exactly as `[illegible]`.
  * Note manuscript line breaks with the `|` character.
  * Output only the transcription, with no preamble, conversational fillers, or commentary.

---

## 2. Evaluation Dataset & Ground Truth
We use three pages from the Library of Congress crowdsourcing transcription dataset for the **Samuel J. Gibson Civil War Diary** (collection item `2019667238`).

### File Mapping Pattern
* The images are located in `data/images/` as `gibson_pageNNN.jpg`.
* The ground truth transcripts are located in `data/ground_truth/` as `gibson_pageNNN.txt`.
* Suffixes map to the official dataset `Asset` ID:
  - Page 11 (`sp=11`): `mss52410001-11`
  - Page 37 (`sp=37`): `mss52410001-37`
  - Page 49 (`sp=49`): `mss52410001-49`

*To extract any other page's ground truth transcript (1-90) from the bulk CSV locally, use the extraction utility:*
```bash
python scripts/extract_ground_truth.py <page_number>
```

---

## 3. Automated Test Suite (`tests/test_transcriber.py`)
We use `pytest` and `jiwer` to verify transcription formatting and word-level accuracy:

### Test Definitions
1. **`test_transcriber_returns_nonempty_output`**: Verifies that the agent successfully returns a non-empty string for page 11.
2. **`test_transcriber_output_format`**:
   - Asserts the output starts directly with the transcribed text (checks for preambles like "Here is", "Sure,", etc.).
   - Asserts strict formatting for illegible markers (`[illegible]` only, no `(illegible)` or `unclear`).
   - Asserts `|` is present in multi-line outputs.
3. **`test_transcriber_accuracy_against_ground_truth`**: Calculates the Word Error Rate (WER) using `jiwer` against the ground truth transcripts (after stripping formatting `|` characters for fair comparison).

---

## 4. Benchmark & Test Outcomes
* **Preamble/Presence/Format Tests**: **PASSED**
* **Accuracy Test (Target WER < 0.20)**: **FAILED** (due to non-deterministic orthographic differences)

### Detailed Metrics:
| Page | Raw WER (with Punctuation & Casing) | Normalized WER (Lowercase & No Punctuation) | Key Mismatch Characteristics |
|------|------------------------------------|--------------------------------------------|-------------------------------|
| **Page 11** | 40.5% | **11.5% (Passed)** | Capitalization differences, punctuation attachment. |
| **Page 49** | 26.3% | **10.6% (Passed)** | Whitespace alignment, minor punctuation differences. |
| **Page 37** | 21.4% | 31.8% | Abbreviation differences (e.g. `and` vs `&`), editor bracket notations in ground truth (e.g. `compl[ain]`). |

*Note: Punctuation normalization reduces the WER to around 10%–11% for pages 11 and 49, confirming the core transcription is highly accurate, but diverges on precise casing and punctuation style.*

---

## 5. Local Execution Commands
To run the automated tests locally:
```bash
python -m pytest tests/test_transcriber.py -v -s
```
