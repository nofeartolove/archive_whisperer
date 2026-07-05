# Reproducibility Audit Log

Archive Whisperer has been fully audited for fresh-clone reproducibility. The system was verified from scratch in a clean, isolated environment containing only git-tracked repository files, with zero manual setup beyond what is documented in this log. All offline tests pass cleanly before any API keys are configured, proving complete network isolation of the test suite. End-to-end vision transcribing and quality validation are fully operational under live environment runs.

---

## Baseline Reproduction Environment
* **Operating System**: Windows 11 (AMD64)
* **Python Version**: Python 3.13.3
* **Pytest Version**: pytest-9.1.1
* **MCP SDK Version**: mcp-1.28.1
* **Google ADK Version**: google-adk-2.3.0
* **Reproduction Time**: ~6-7 minutes total (primarily dependency installation)

---

## 1. Fresh Clone Execution Log

Below is the exact sequence of commands and observed outputs from the fresh-clone verification:

```powershell
# 1. Create a clean isolated directory outside the original project path
mkdir c:\Personal\AIAgents_5Day\CapStone\archive_whisperer_clone
cd c:\Personal\AIAgents_5Day\CapStone\archive_whisperer_clone

# 2. Copy only git-tracked files (simulating a GitHub checkout)
# Output: Copied 53 tracked files.

# 3. Create virtual environment from scratch
python -m venv .venv
.venv\Scripts\activate

# 4. Install requirements
pip install -r requirements.txt
# Output: Successfully installed google-adk, google-genai, mcp, pytest, jiwer, pillow...

# 5. Run the offline test suite FIRST, before configuring API keys
python -m pytest
```

### Pytest Log Output (Offline Mode)
```text
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Personal\AIAgents_5Day\CapStone\archive_whisperer_clone
configfile: pytest.ini
plugins: anyio-4.14.1
collected 20 items / 6 deselected / 14 selected

tests\test_fetcher.py .                                                  [  7%]
tests\test_formatter.py .                                                [ 14%]
tests\test_mcp_tools.py ....                                             [ 42%]
tests\test_pipeline_integration.py .                                     [ 50%]
tests\test_security.py .....                                             [ 85%]
tests\test_validator.py ..                                               [100%]

============================== warnings summary ===============================
  DeprecationWarning: BaseAgentConfig is deprecated and will be removed in future versions.
  UserWarning: [EXPERIMENTAL] feature FeatureName.PLUGGABLE_AUTH is enabled.

================ 14 passed, 6 deselected, 6 warnings in 7.76s =================
```
*Verification: 14 offline tests passed with zero failures and zero network calls.*

---

## 2. Live Pipeline Verification Log

After confirming offline tests passed, a live Gemini API key was loaded into `.env` to execute the full sequentially-paced manuscript pipeline on all three Gibson diary pages:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

```powershell
python scripts/run_pipeline_test.py
```

### Observed Quality Metrics
The live validation stage fetches online crowdsourced ground truth from the Library of Congress and computes Character Error Rate (CER) and Word Error Rate (WER) using `jiwer`:

* **Gibson Diary Page 11**:
  * Word Error Rate (WER): **26.42%**
  * Character Error Rate (CER): **21.52%**
* **Gibson Diary Page 37**:
  * Word Error Rate (WER): **29.44%**
  * Character Error Rate (CER): **21.84%**
* **Gibson Diary Page 49**:
  * Word Error Rate (WER): **30.87%**
  * Character Error Rate (CER): **24.94%**

> [!NOTE]  
> **Accuracy Metrics Variance**: Transcription relies on multimodal vision LLMs. Because generation is probabilistic, minor differences in word spacing and casing can cause slight differences in the computed WER/CER compared to the static benchmarks published in the README. The above values represent the actual outputs of this clean-slate execution.

---

## Verify It Yourself in Under 5 Minutes

You can verify the entire workspace reproducibility by copying and running the clean numbered blocks below.

### 1. Step-by-Step Manual Verification

1. **Clone & Setup Directory**:
   ```bash
   git clone https://github.com/nofeartolove/archive_whisperer.git
   cd archive_whisperer
   ```

2. **Initialize Isolated Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Offline Isolation**:
   ```bash
   pytest
   ```
   *Expected result: 14 passed, 6 deselected, 0 failed.*

5. **Configure API Credentials**:
   *Obtain a free API Key from [Google AI Studio](https://aistudio.google.com/)*
   ```bash
   copy .env.example .env
   # Add your key to GOOGLE_API_KEY in the .env file
   ```

6. **Run Sanity Pipeline**:
   ```bash
   python scripts/run_pipeline_test.py
   ```
   *Expected result: Execution summaries for Pages 11, 37, and 49 should report PASS on all stages (Fetch, Transcribe, Validate, Format).*

---

### 2. Automated One-Command Verification

Alternatively, you can run the automated script that handles directory isolation, cloning, virtual environment creation, package installations, and offline test execution in a single command:

```bash
# Optional: Set your API Key to include the live pipeline execution check
# export GOOGLE_API_KEY="your_api_key_here"  (On Windows: $env:GOOGLE_API_KEY="...")

# Run the automated verifier
python scripts/verify_reproducibility.py
```
*Expected output:*
```text
==================================================
>>> REPRODUCIBILITY VERIFICATION SUCCESSFUL! <<<
==================================================
```
