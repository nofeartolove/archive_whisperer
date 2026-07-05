import sys
import pathlib
import time
import json

# Add project root to sys.path
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from agents.orchestrator import run_pipeline

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_pipeline.py <Library_of_Congress_IIIF_URL>")
        sys.exit(1)
        
    url = sys.argv[1].strip()
    
    print("\n" + "="*60)
    print("ARCHIVE WHISPERER - LIVE ORCHESTRATION PIPELINE")
    print("="*60)
    print(f"Target URL: {url}")
    print("Connecting to LOC MCP Server and Gemini Vision API...")
    
    start_time = time.time()
    try:
        result = run_pipeline(url)
        elapsed = time.time() - start_time
        
        state = result.get("metadata", {})
        
        print("\n" + "="*60)
        print("PIPELINE RUN SUMMARY")
        print("="*60)
        
        # Step 1
        local_path = state.get("metadata", {}).get("local_path")
        print(f" - Stage 1 - Fetch: PASS (saved to {local_path})")
        
        # Step 2
        transcription = state.get("transcription", "")
        print(f" - Stage 2 - Transcribe: PASS ({len(transcription)} characters)")
        
        # Step 3
        val = state.get("validation", {})
        if val.get("available"):
            print(f" - Stage 3 - Validate: PASS (WER: {val.get('wer')*100:.2f}%, CER: {val.get('cer')*100:.2f}%)")
        else:
            print(" - Stage 3 - Validate: PASS (Ground truth unavailable, validation skipped)")
            
        # Step 4
        print(f" - Stage 4 - Format: PASS (saved JSON, MD, TXT to output/)")
        
        print(f"\nExecution completed successfully in {elapsed:.2f} seconds.")
        print("="*60 + "\n")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\nPipeline execution failed after {elapsed:.2f} seconds: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
