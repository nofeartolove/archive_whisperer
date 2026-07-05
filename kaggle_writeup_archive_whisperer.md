# Archive Whisperer
## An AI-Powered Multi-Agent System for Transcribing Historical Handwritten Manuscripts

---

> **A note on the demo:** No live public demo is hosted for this submission. Per the Submission Requirements, this Writeup instead links to a public GitHub repository containing the full source code, a step-by-step setup guide, and an independently reproducible fresh-clone verification log (`REPRODUCIBILITY.md`) — including a captured pytest run and a one-command verifier script — so judges can run Archive Whisperer themselves rather than take the results on faith.

---

### The Problem

More than 175 million handwritten pages sit in U.S. archives, and fewer than 5% are machine-readable today. Standard OCR engines are built for uniform, printed typefaces — they rely on segmenting individual characters from clean, consistent shapes. Nineteenth-century cursive breaks every one of those assumptions: letters connect into ligatures with no clear boundaries, ink fades unevenly across a page, slant and pressure vary letter to letter within the same word, and writers used period-specific abbreviations (`&` for "and," hyphenated line-endings, dropped punctuation) that no modern OCR training set has ever seen.

The result is that most of this material is functionally invisible. Historians, genealogists, and educators either pay for slow manual transcription or simply don't use documents that aren't already transcribed. A letter from the Lincoln presidential papers or a Civil War soldier's diary might sit online as a digitized image for over a decade without a single searchable word coming out of it.

Archive Whisperer exists to close that gap using an agentic pipeline rather than a single, brittle OCR call.

### Why Agents, Specifically

A single vision-model prompt can transcribe a clean manuscript page reasonably well, but it can't validate its own output, can't recover cleanly from a rate-limited API call mid-run, and gives no way to measure whether it's actually correct. Those three problems — validation, resilience, and measurement — are exactly what an agentic architecture is for.

Archive Whisperer splits the work across four specialized agents, each with a narrow, well-defined responsibility, coordinated by an orchestrator:

- A **Fetcher** agent that retrieves manuscript images from the Library of Congress and enforces security checks on what comes back
- A **Transcriber** agent, a dedicated paleographer persona, that produces the raw transcription
- A **Validator** agent that retrieves crowdsourced, human-verified ground truth from LOC's "By the People" program and computes real Word Error Rate (WER) and Character Error Rate (CER) — not a guess, an actual measured accuracy score
- A **Formatter** agent that produces the final structured output (JSON, Markdown, plain text) with full provenance metadata

Splitting the work this way means each responsibility can be tested, retried, and improved independently — and it means the system can tell you, honestly, how accurate its own output is.

Just as importantly, agent decomposition let us make a deliberate reliability decision: not every one of these four steps benefits from live LLM reasoning, and we designed the system to reflect that honestly rather than routing everything through an agent for appearances.

### System Architecture

```
User Request (LOC manuscript URL)
        │
        ▼
┌───────────────────────┐
│ Orchestrator Workflow │  (Google ADK graph-based workflow)
└───────────────────────┘
        │
        ├──► Fetcher Agent ──────► FastMCP LOC Server ──► downloads & validates image
        │
        ├──► Transcriber Agent ──► Gemini Vision ──► raw paleographic transcription
        │
        ├──► Validator Agent ────► FastMCP LOC Server ──► fetches By-the-People ground truth
        │                                              ──► computes WER / CER via jiwer
        │
        └──► Formatter Agent ────► FastMCP LOC Server ──► saves JSON + Markdown + TXT report
```

All four agents are declared using **Google's Agent Development Kit (ADK)**, each with its own model and its own instruction loaded dynamically from a versioned `SKILL.md` file — so an agent's capability documentation and its actual behavior are the same artifact, not two things that can drift apart. The orchestrator coordinates them through a graph-based `Workflow` that chains Fetch → Transcribe → Validate → Format as sequential, stateful steps.

A custom **FastMCP server** (`loc_tools.py`) exposes three tools — `fetch_loc_page`, `get_bythepeople_transcript`, and `save_transcript` — over the Model Context Protocol, giving the system a standardized, auditable interface to the outside world instead of ad hoc HTTP calls scattered through agent code.

**A deliberate design distinction:** Reading ambiguous historical cursive is a genuine reasoning task, so the Transcriber agent calls Gemini's vision models live, in full, for every transcription. Fetching a record by URL, looking up ground truth by ID, and saving a file are not reasoning tasks — there is exactly one correct action given the input, with no decision for an LLM to make. During development, routing these three operations through ADK's agent runner introduced real reliability problems (intermittent empty responses and tool-call formatting errors on purely mechanical round-trips). So in live execution, the Fetcher, Validator, and Formatter agents call the FastMCP server directly through a genuine MCP client session, while remaining fully declared as ADK agents — with their `LlmAgent` + MCP toolset wiring exercised in full inside the automated test suite. MCP itself is identical in both paths; what changes is whether an LLM or a direct client is the one invoking it. We consider this the right engineering tradeoff: reserve agentic reasoning for the step that actually needs judgment, and use deterministic calls everywhere the outcome is already fully determined by the input.

### Security and Responsible AI

Every outbound request is filtered through a strict domain allowlist (`loc.gov`, `tile.loc.gov`, `www.loc.gov`), preventing the system from being redirected to fetch arbitrary or malicious URLs — a real SSRF risk in any agent that accepts a URL as input. A rate limiter enforces a minimum 3-second interval between outbound LOC requests, so the system behaves as a polite, well-identified client rather than hammering a public archive's servers. User input is scanned against a set of prompt-injection patterns (script tags, `javascript:` URIs, "ignore previous instructions" style attempts) before it ever reaches an agent. Input length is hard-capped. And the codebase includes an automated pytest that scans every agent, MCP server, and security file for hardcoded API key patterns, so a credential leak would fail CI before it could ever reach GitHub.

### Resilience: Dynamic Model Rotation

Free-tier Gemini API quotas mean rate limiting (`429 RESOURCE_EXHAUSTED`) is a real, frequent condition during development and demos — not an edge case. Rather than fail on the first rate limit, every agent retries through a fallback chain of models (`gemini-3.5-flash` → `gemini-2.5-flash` → `gemini-3.1-flash-lite` → `gemini-2.5-flash-lite`), swapping models on failure rather than simply waiting out the same blocked quota. This turned out to matter in practice: during live testing, a rate limit on the primary model was caught and recovered from automatically mid-pipeline, with the run completing successfully on a fallback model rather than crashing.

### Quantitative Results

Archive Whisperer was benchmarked against real, human-verified transcripts from the Library of Congress's "By the People" crowdsourced transcription program for the Samuel J. Gibson Civil War Diary (1864) — not against a self-reported estimate, but against an independently produced ground truth.

| Document / Page | Word Error Rate (WER) | Character Error Rate (CER) |
|:---|:---:|:---:|
| Gibson Diary, Page 11 | **52.16%** | **27.35%** |
| Gibson Diary, Page 37 | **32.26%** | **20.64%** |
| Gibson Diary, Page 49 | **22.46%** | **17.28%** |

Character-level accuracy is consistently stronger than word-level accuracy, which reflects the actual nature of the remaining error: most discrepancies come from capitalization, punctuation attachment, and historical abbreviation style (`&` vs. "and," editorial bracket notation like `compl[ain]`) rather than genuine misreadings of the handwriting itself. In other words, the system is reading the ink correctly far more often than the raw word-error number alone would suggest. Because generation is probabilistic, an independent clean-slate run produces slightly different but comparable numbers — documented transparently in the project's `REPRODUCIBILITY.md`.

### Course Concepts Demonstrated

| Concept | Where |
|---|---|
| Multi-agent system (Google ADK) | `agents/` — four `LlmAgent` instances, each with its own model and skill-loaded instruction, coordinated by a graph-based `Workflow` orchestrator |
| MCP Server | `mcp_server/loc_tools.py` — a FastMCP server exposing three tools over stdio transport, used identically in both test (agent-invoked) and live (direct client) execution paths |
| Agent Skills | `skills/*/SKILL.md` — each agent's instruction set is loaded directly from its skill file at runtime, not duplicated in code |
| Security features | `security/guards.py` — domain allowlisting, rate limiting, prompt-injection filtering, and an automated hardcoded-secret scanner in the test suite |
| Antigravity | Demonstrated live in the submission video, running the full pipeline end-to-end inside Google's Antigravity environment |
| Deployability | Containerized via a Dockerfile (README Section 9), with the build independently verified on every push via GitHub Actions CI -- no manual local build required to trust this claim. Setup and reproducibility are also verified via a fresh-clone test documented in REPRODUCIBILITY.md. |

### The Build

Archive Whisperer is built entirely in Python on Google's Agent Development Kit, using Gemini's multimodal vision models for the actual transcription step and `jiwer` for standardized WER/CER computation. The full test suite uses mocked agent runners for fast, deterministic verification of tool-calling logic, security boundaries, and output formatting, with a separate live-network canary test to catch upstream changes in the Library of Congress's JSON API schema. Manuscript images and ground-truth transcripts come directly from the Library of Congress's public-domain digitized collections and its "By the People" crowdsourced transcription program.

### What's Next

The current system supports three curated Gibson diary pages and eight Lincoln Papers letters as a proof of concept. The natural next step is generalizing the Validator agent to work across any LOC manuscript collection with By-the-People coverage — not just Gibson — and adding a lightweight web front end so a historian could paste in any LOC manuscript URL and get a transcript back without touching the command line. Longer term, the same four-agent pattern (fetch → transcribe → validate → format) generalizes cleanly to other archives beyond the Library of Congress, including university special collections and international archives with their own digitization programs.

---

*Full source code, setup instructions, and test suite: [https://github.com/nofeartolove/archive_whisperer](https://github.com/nofeartolove/archive_whisperer)*
*Demo video: [YouTube link — add once uploaded]*
