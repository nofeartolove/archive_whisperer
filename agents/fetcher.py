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

fetcher = LlmAgent(
    name="fetcher_agent",
    model="gemini-3.5-flash",
    tools=[loc_toolset],
    instruction=load_skill_instruction("fetch_image"),
)

def run_fetcher(url: str, retries: int = 4, delay: float = 10.0) -> dict:
    """Runs the fetcher agent on the given URL, enforces security checks on the MIME type, and returns metadata."""
    import time
    
    fallback_models = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]
    
    for attempt in range(retries):
        current_model = fallback_models[attempt % len(fallback_models)]
        fetcher.model = current_model
        
        try:
            runner = InMemoryRunner(agent=fetcher)
            # Create a unique session ID per attempt to avoid session state collisions
            session_id = f"fetch_session_{hash(url) & 0xffffffff}_{attempt}"
            runner.session_service.create_session_sync(
                app_name=runner.app_name,
                user_id="system_user",
                session_id=session_id
            )
            
            from google.genai import types
            
            # Wrap string input in types.Content
            message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=url)]
            )
            
            response_text = ""
            for event in runner.run(user_id="system_user", session_id=session_id, new_message=message):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
                            
            response_clean = response_text.strip()
            if not response_clean:
                raise ValueError(f"Fetcher Agent returned empty response using {current_model} (possibly due to API 429).")
                
            # Strip markdown block formatting if LLM returned it
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_clean = "\n".join(lines).strip()
                
            data = json.loads(response_clean)
            if "error" in data:
                raise ValueError(f"Fetcher Agent rejection: {data['error']}")
                
            # Enforce MIME type validation in python (Stage 4 Security)
            mime_type = data.get("mime_type", "")
            if not mime_type.startswith("image/"):
                raise ValueError(f"Security Rejection: Downloaded file has non-image MIME type '{mime_type}'.")
                
            return data
        except Exception as e:
            print(f"[Fetcher] Attempt {attempt + 1} of {retries} with {current_model} failed: {e}")
            if attempt < retries - 1:
                print(f"[Fetcher] Waiting {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                raise e

if __name__ == "__main__":
    test_url = "https://tile.loc.gov/image-services/iiif/service:mss:mss52410:001:0011/full/pct:25/0/default.jpg"
    print(f"Testing Fetcher Agent with: {test_url}")
    try:
        meta = run_fetcher(test_url)
        print("Success! Metadata:")
        print(json.dumps(meta, indent=2))
    except Exception as e:
        print(f"Error: {e}")
