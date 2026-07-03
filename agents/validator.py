import sys
import json
import pathlib
import dotenv
import jiwer
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import McpToolset
from mcp import StdioServerParameters

# Load environment variables
dotenv.load_dotenv()

# Find project root
project_root = pathlib.Path(__file__).parent.parent.resolve()

from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Instantiate the local MCP Toolset using StdioConnectionParams to avoid warnings
loc_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[str(project_root / "mcp_server" / "loc_tools.py")]
        ),
        timeout=60.0
    )
)

validator = LlmAgent(
    name="validator_agent",
    model="gemini-3.5-flash",
    tools=[loc_toolset],
    instruction="""
    You are a validation agent for historical manuscript transcriptions.
    Your task is to call the `get_bythepeople_transcript` tool with the provided `item_id`
    to retrieve the official crowdsourced ground truth transcription.
    
    Once you call the tool:
    1. If the tool indicates the transcript is not available, output: {"available": false, "ground_truth": ""}
    2. If the tool returns a transcript, output a clean JSON object containing the ground truth:
       {"available": true, "ground_truth": "<insert transcription text here>"}
       Do not add any preamble, markdown code blocks, or conversational text.
    """,
)

def run_validator(item_id: str, transcription: str, retries: int = 3, delay: float = 10.0) -> dict:
    """
    Runs the validator agent to fetch ground truth, then computes WER and CER.
    Reuses the line break normalization logic.
    """
    import time
    
    fallback_models = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    
    for attempt in range(retries):
        current_model = fallback_models[attempt % len(fallback_models)]
        validator.model = current_model
        
        try:
            runner = InMemoryRunner(agent=validator)
            # Create unique session ID per attempt
            session_id = f"val_session_{hash(item_id) & 0xffffffff}_{attempt}"
            runner.session_service.create_session_sync(
                app_name=runner.app_name,
                user_id="system_user",
                session_id=session_id
            )
            
            from google.genai import types
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Find transcription for item_id: {item_id}")]
            )
            
            response_text = ""
            for event in runner.run(user_id="system_user", session_id=session_id, new_message=message):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
                            
            response_clean = response_text.strip()
            if not response_clean:
                raise ValueError(f"Validator Agent returned empty response using {current_model} (possibly due to API 429).")
                
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()
                
            try:
                data = json.loads(response_clean)
            except json.JSONDecodeError:
                data = {"available": False, "ground_truth": ""}
                if "available" in response_clean.lower() and "true" in response_clean.lower():
                    data["available"] = True
                    
            available = data.get("available", False)
            ground_truth = data.get("ground_truth", "").strip()
            
            if not available or not ground_truth:
                return {
                    "available": False,
                    "wer": None,
                    "cer": None,
                    "ground_truth": ""
                }
                
            # Clean up transcription for calculation
            # Strip '|' formatting characters from the agent's transcription to perform a fair comparison
            hyp_clean = transcription.replace("|", " ").strip()
            ref_clean = ground_truth.strip()
            
            # Compute WER and CER using jiwer
            wer_val = jiwer.wer(ref_clean, hyp_clean)
            cer_val = jiwer.cer(ref_clean, hyp_clean)
            
            return {
                "available": True,
                "wer": wer_val,
                "cer": cer_val,
                "ground_truth": ground_truth
            }
        except Exception as e:
            print(f"[Validator] Attempt {attempt + 1} of {retries} with {current_model} failed: {e}")
            if attempt < retries - 1:
                print(f"[Validator] Waiting {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                raise e

if __name__ == "__main__":
    # Test validator locally (requires internet connection for the MCP server)
    test_item = "mss5241.mss5241_01_001_089_sp11"
    test_transcription = "January, MONDAY, 4. 1864. | Plymouth N.C. This morning gloomy | & threatens rain. There is nothing new"
    print(f"Testing Validator Agent with: {test_item}")
    try:
        results = run_validator(test_item, test_transcription)
        print("Success! Validation Results:")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}")
