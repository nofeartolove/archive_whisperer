import os
import json
import pathlib
import sys
import datetime
import dotenv

# Add project root to sys.path to allow imports from agents package
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from google.adk import Workflow
from google.adk.workflow._base_node import START
from google.adk.runners import InMemoryRunner
from google.genai import types

# Load environment variables
dotenv.load_dotenv()

# Import the sub-agents and runner functions
from agents.fetcher import run_fetcher
from agents.transcriber import transcribe_image_file
from agents.validator import run_validator
from agents.formatter import run_formatter
from security.guards import sanitize_user_input

# Setup directories
project_root = pathlib.Path(__file__).parent.parent.resolve()

def step_fetch(ctx) -> str:
    """Node that sanitizes the URL, downloads the image, and extracts metadata."""
    # Find the input message containing the URL
    url = ""
    if ctx.user_content and ctx.user_content.parts:
        for part in ctx.user_content.parts:
            if part.text:
                url = part.text.strip()
                break
                
    if not url:
        raise ValueError("Fetcher node failed: No input URL found in context.")
        
    # Enforce prompt injection and length cap guards
    url = sanitize_user_input(url)
    print(f"[Orchestrator] Step 1: Fetching LOC page: {url}")
    
    # Run fetcher
    metadata = run_fetcher(url)
    print(f"[Orchestrator] Fetch completed. Metadata: {metadata}")
    
    # Save metadata to context state for access by downstream nodes
    ctx.state["metadata"] = metadata
    
    # Return formatted string for session history log
    return json.dumps({"step": "fetch", "status": "success", "metadata": metadata})

def step_transcribe(ctx) -> str:
    """Node that reads the image path and runs the paleographer transcriber agent."""
    metadata = ctx.state.get("metadata", {})
    local_path = metadata.get("local_path")
    
    if not local_path:
        raise ValueError("Transcriber node failed: No local image path found in context state.")
        
    abs_image_path = project_root / local_path
    print(f"[Orchestrator] Step 2: Transcribing image: {local_path}")
    
    # Run transcriber
    transcription = transcribe_image_file(abs_image_path)
    print(f"[Orchestrator] Transcription completed. length: {len(transcription)} chars.")
    
    ctx.state["transcription"] = transcription
    
    # Return raw transcript so it is logged in history
    return transcription

def resolve_item_details_from_url(url: str, local_path: str = "") -> tuple[str, int]:
    """Resolves the proper item_id and page number directly from the source URL."""
    import re
    import pathlib
    
    # Default fallbacks
    item_id = None
    page = 1
    
    if not url:
        # Fallback to local_path parsing if URL is somehow empty (should not happen in real workflow)
        if local_path:
            if "mss5241" in local_path:
                for p in ["011", "037", "049"]:
                    if p in local_path:
                        page = int(p)
                        return f"mss5241.mss5241_01_001_089_sp{page}", page
                return "mss5241.mss5241_01_001_089", 1
            else:
                return pathlib.Path(local_path).stem, 1
        return "unknown_item", 1

    # Try parsing Gibson URL pattern
    # e.g., service:mss:mss5241:01:011
    gibson_match = re.search(r'service:mss:mss5241:01:(\d+)', url)
    if gibson_match:
        page_str = gibson_match.group(1)
        page = int(page_str)
        item_id = f"mss5241.mss5241_01_001_089_sp{page}"
        return item_id, page
    
    # General/other URLs fallback
    # Extract last path segment to form a unique stem
    parsed_path = pathlib.Path(url)
    stem = parsed_path.stem
    if ":" in stem:
        parts = stem.split(":")
        for part in parts:
            if "mss" in part:
                item_id = part
                break
    if not item_id:
        item_id = stem or "unknown_item"
        
    return item_id, page

def step_validate(ctx) -> str:
    """Node that retrieves crowdsourced transcripts and calculates WER/CER accuracy metrics."""
    metadata = ctx.state.get("metadata", {})
    transcription = ctx.state.get("transcription", "")
    
    # Derive item_id. If not directly in metadata, try to extract from local_path or URL
    item_id = metadata.get("item_id")
    url = metadata.get("url", "")
    local_path = metadata.get("local_path", "")
    
    if not item_id:
        item_id, page = resolve_item_details_from_url(url, local_path)
            
    print(f"[Orchestrator] Step 3: Validating transcription for item_id: {item_id}")
    
    if not item_id:
        print("[Orchestrator] Warning: Could not resolve item_id for validation. Skipping.")
        val_results = {"available": False, "wer": None, "cer": None}
    else:
        # Run validator
        val_results = run_validator(item_id, transcription)
        
    print(f"[Orchestrator] Validation completed. Available: {val_results.get('available')}, WER: {val_results.get('wer')}")
    ctx.state["validation"] = val_results
    
    return json.dumps({"step": "validate", "status": "success", "results": val_results})

def step_format(ctx) -> str:
    """Node that structures output formats and writes text, markdown, and JSON files to output/."""
    metadata = ctx.state.get("metadata", {})
    transcription = ctx.state.get("transcription", "")
    val_results = ctx.state.get("validation", {})
    
    # Enrich metadata with validation results and timestamp
    metadata["wer"] = val_results.get("wer")
    metadata["cer"] = val_results.get("cer")
    metadata["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Determine item_id and page for formatting
    item_id = metadata.get("item_id")
    url = metadata.get("url", "")
    local_path = metadata.get("local_path", "")
    
    resolved_id, page = resolve_item_details_from_url(url, local_path)
    
    if not item_id:
        item_id = resolved_id
            
    metadata["item_id"] = item_id
    metadata["page"] = page
    
    print(f"[Orchestrator] Step 4: Formatting and saving transcription...")
    
    # Run formatter
    format_summary = run_formatter(transcription, metadata)
    print(f"[Orchestrator] Formatting completed: {format_summary}")
    
    return json.dumps({
        "step": "format",
        "status": "success",
        "saved_files_summary": format_summary
    })

# Define the graph-based workflow orchestrator
orchestrator = Workflow(
    name="archive_whisperer_orchestrator",
    description="Chains Fetch -> Transcribe -> Validate -> Format stages sequentially.",
    edges=[
        (START, step_fetch),
        (step_fetch, step_transcribe),
        (step_transcribe, step_validate),
        (step_validate, step_format)
    ]
)

def run_pipeline(url: str) -> dict:
    """Runs the full orchestration pipeline on the given LOC page URL."""
    runner = InMemoryRunner(node=orchestrator)
    
    session_id = f"pipeline_session_{hash(url) & 0xffffffff}"
    runner.session_service.create_session_sync(
        app_name=runner.app_name,
        user_id="pipeline_user",
        session_id=session_id
    )
    
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=url)]
    )
    
    print(f"\n========================================\n[Orchestrator] Starting pipeline for: {url}")
    
    # Run the workflow
    events = []
    for event in runner.run(user_id="pipeline_user", session_id=session_id, new_message=message):
        events.append(event)
        
    # Get final outputs from context state
    session = runner.session_service.get_session_sync(
        app_name=runner.app_name,
        user_id="pipeline_user",
        session_id=session_id
    )
    # We can retrieve state directly from the session
    return {
        "status": "COMPLETED",
        "session_id": session_id,
        "metadata": session.state
    }

if __name__ == "__main__":
    # Test on all 3 Gibson benchmark pages sequentially
    urls = [
        "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:011/full/pct:100/0/default.jpg",
        "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:037/full/pct:100/0/default.jpg",
        "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:049/full/pct:100/0/default.jpg"
    ]
    import time
    for i, url in enumerate(urls):
        if i > 0:
            print("\nPacing 15 seconds between page runs to respect API limits...")
            time.sleep(15)
        try:
            res = run_pipeline(url)
            print(f"\nPipeline execution summary for {url}:")
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Pipeline error for {url}: {e}")
