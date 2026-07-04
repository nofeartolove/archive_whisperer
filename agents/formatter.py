import sys
import json
import pathlib
import dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools import McpToolset
from mcp import StdioServerParameters

# Load environment variables
dotenv.load_dotenv()

# Find project root
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from security.guards import load_skill_instruction

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

formatter = LlmAgent(
    name="formatter_agent",
    model="gemini-3.5-flash",
    tools=[loc_toolset],
    instruction=load_skill_instruction("format_output"),
)

def run_formatter(text: str, metadata: dict, retries: int = 4, delay: float = 10.0) -> str:
    """
    Runs the formatter agent to save the JSON transcription via MCP,
    and writes Markdown (.md) and plain text (.txt) versions directly to output/.
    """
    import time
    
    fallback_models = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    item_id = metadata.get("item_id", "unknown_item")
    page_num = metadata.get("page", 1)
    try:
        page_num = int(page_num)
    except (ValueError, TypeError):
        page_num = 1
        
    for attempt in range(retries):
        current_model = fallback_models[attempt % len(fallback_models)]
        formatter.model = current_model
        
        try:
            runner = InMemoryRunner(agent=formatter)
            session_id = f"format_session_{hash(item_id) & 0xffffffff}_{attempt}"
            runner.session_service.create_session_sync(
                app_name=runner.app_name,
                user_id="system_user",
                session_id=session_id
            )
            
            from google.genai import types
            
            # Construct the instruction for the LLM to trigger the tool call
            payload = {
                "text": text,
                "metadata": metadata
            }
            
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Please format and save this transcript: {json.dumps(payload)}")]
            )
            
            response_text = ""
            for event in runner.run(user_id="system_user", session_id=session_id, new_message=message):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
                            
            if not response_text:
                raise ValueError(f"Formatter Agent returned empty response using {current_model} (possibly due to API 429).")
                
            break
        except Exception as e:
            print(f"[Formatter] Attempt {attempt + 1} of {retries} with {current_model} failed: {e}")
            if attempt < retries - 1:
                print(f"[Formatter] Waiting {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                raise e
                
    # Write Markdown (.md) file directly
    output_dir = project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    md_file = output_dir / f"{item_id}_{page_num:03d}.md"
    
    wer_val = metadata.get("wer")
    cer_val = metadata.get("cer")
    wer_str = f"{wer_val * 100:.2f}%" if wer_val is not None else "N/A"
    cer_str = f"{cer_val * 100:.2f}%" if cer_val is not None else "N/A"
    
    md_content = f"""# Transcription Report - {item_id} (Page {page_num:03d})

## Metadata
- **Item ID**: {item_id}
- **Page Number**: {page_num}
- **Source URL**: {metadata.get('url', 'N/A')}
- **MIME Type**: {metadata.get('mime_type', 'N/A')}
- **File Size**: {metadata.get('size_bytes', 'N/A')} bytes
- **Validation WER**: {wer_str}
- **Validation CER**: {cer_str}

## Transcription Text
```text
{text}
```
"""
    md_file.write_text(md_content, encoding="utf-8")
    
    # Write plain text (.txt) file directly
    txt_file = output_dir / f"{item_id}_{page_num:03d}.txt"
    txt_file.write_text(text, encoding="utf-8")
    
    return f"Saved files: JSON (via MCP), Markdown ({md_file.name}), and plain text ({txt_file.name})."

if __name__ == "__main__":
    test_text = "August. | FRIDAY, 19. | 1864\nWhat we sometimes | regard as a misfortune..."
    test_meta = {
        "item_id": "mss5241.mss5241_01_001_089",
        "page": 49,
        "url": "https://tile.loc.gov/image-services/iiif/service:mss:mss52410:001:0049/full/pct:25/0/default.jpg",
        "source_url": "https://tile.loc.gov/image-services/iiif/service:mss:mss52410:001:0049/full/pct:25/0/default.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 102400,
        "wer": 0.1804,
        "cer": 0.0824
    }
    print("Testing Formatter Agent...")
    try:
        summary = run_formatter(test_text, test_meta)
        print(summary)
    except Exception as e:
        print(f"Error: {e}")
