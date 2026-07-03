import sys
import pathlib
import json

# Add project root to sys.path
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from agents.orchestrator import run_pipeline

def test_page(page_name: str, url: str):
    print(f"\n==================================================")
    print(f"RUNNING PIPELINE FOR: {page_name}")
    print(f"URL: {url}")
    print(f"==================================================")
    
    stages = {
        "Stage 1 - Fetch": "PENDING",
        "Stage 2 - Transcribe": "PENDING",
        "Stage 3 - Validate": "PENDING",
        "Stage 4 - Format": "PENDING"
    }
    
    try:
        # Run pipeline (includes retry loops for 429 safety)
        result = run_pipeline(url)
        state = result.get("metadata", {})
        
        # Verify Stage 1 (Fetch)
        if "metadata" in state:
            stages["Stage 1 - Fetch"] = f"PASS (saved to {state['metadata'].get('local_path')})"
        else:
            stages["Stage 1 - Fetch"] = "FAIL"
            
        # Verify Stage 2 (Transcribe)
        if "transcription" in state and len(state["transcription"].strip()) > 0:
            stages["Stage 2 - Transcribe"] = f"PASS ({len(state['transcription'])} chars)"
        else:
            stages["Stage 2 - Transcribe"] = "FAIL"
            
        # Verify Stage 3 (Validate)
        if "validation" in state:
            val = state["validation"]
            if val.get("available"):
                stages["Stage 3 - Validate"] = f"PASS (WER: {val.get('wer') * 100:.2f}%, CER: {val.get('cer') * 100:.2f}%)"
            else:
                stages["Stage 3 - Validate"] = "PASS (Ground truth unavailable, validation skipped)"
        else:
            stages["Stage 3 - Validate"] = "FAIL"
            
        # Verify Stage 4 (Format)
        # Check if the output files exist
        item_id = state.get("metadata", {}).get("item_id", "mss5241.mss5241_01_001_089")
        page_num = 11
        for p in ["011", "037", "049"]:
            if p in url:
                page_num = int(p)
                
        json_file = project_root / "output" / f"{item_id}_{page_num:03d}.json"
        md_file = project_root / "output" / f"{item_id}_{page_num:03d}.md"
        txt_file = project_root / "output" / f"{item_id}_{page_num:03d}.txt"
        
        if json_file.exists() and md_file.exists() and txt_file.exists():
            stages["Stage 4 - Format"] = f"PASS (saved JSON, MD, TXT to output/)"
        else:
            stages["Stage 4 - Format"] = "FAIL (some output files missing)"
            
    except Exception as e:
        print(f"\nPipeline Error during execution: {e}")
        # Identify where it failed based on what is in state
        if 'state' in locals() or 'result' in locals():
            # Check progress
            pass
            
    print(f"\nExecution Summary for {page_name}:")
    for stage, status in stages.items():
        print(f" - {stage}: {status}")

def main():
    import time
    test_pages = {
        "Gibson Page 11": "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:011/full/pct:100/0/default.jpg",
        "Gibson Page 37": "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:037/full/pct:100/0/default.jpg",
        "Gibson Page 49": "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:049/full/pct:100/0/default.jpg"
    }
    
    for i, (name, url) in enumerate(test_pages.items()):
        if i > 0:
            print(f"\n[Test Runner] Waiting 15 seconds before starting next page to respect API rate limits...")
            time.sleep(15)
        test_page(name, url)

if __name__ == "__main__":
    main()
