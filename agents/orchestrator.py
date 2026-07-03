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

def step_validate(ctx) -> str:
    """Node that retrieves crowdsourced transcripts and calculates WER/CER accuracy metrics."""
    metadata = ctx.state.get("metadata", {})
    transcription = ctx.state.get("transcription", "")
    
    # Derive item_id. If not directly in metadata, try to extract from local_path
    item_id = metadata.get("item_id")
    local_path = metadata.get("local_path", "")
    
    # If item_id is missing, parse it from the filename (e.g. service_mss_mss52410_001_0011.jpg)
    # The Gibson diary item ID pattern is mss5241.mss5241_01_001_089
    # Suffix for sub-pages is _sp11, _sp37, _sp49
    if not item_id and "mss5241" in local_path:
        # Match a page pattern from file name
        # We know we downloaded to gibson_page011.jpg etc. or service_mss_mss52410_001_0011.jpg
        # Let's map Gibson images to their proper LOC API item IDs:
        if "page011" in local_path or "001_0011" in local_path:
            item_id = "mss5241.mss5241_01_001_089_sp11"
        elif "page037" in local_path or "001_0037" in local_path:
            item_id = "mss5241.mss5241_01_001_089_sp37"
        elif "page049" in local_path or "001_0049" in local_path:
            item_id = "mss5241.mss5241_01_001_089_sp49"
        else:
            item_id = "mss5241.mss5241_01_001_089"
            
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
    local_path = metadata.get("local_path", "")
    
    # Extract page number
    page = 1
    for p in ["011", "037", "049"]:
        if p in local_path:
            page = int(p)
            break
            
    if not item_id:
        if "mss5241" in local_path:
            item_id = "mss5241.mss5241_01_001_089"
        else:
            item_id = pathlib.Path(local_path).stem
            
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
    # Test on one page (page 11)
    test_url = "https://tile.loc.gov/image-services/iiif/service:mss:mss52410:001:0011/full/pct:25/0/default.jpg"
    try:
        res = run_pipeline(test_url)
        print("\nPipeline execution summary:")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Pipeline error: {e}")
