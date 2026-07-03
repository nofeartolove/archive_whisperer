"""
Transcriber Agent for Archive Whisperer
"""

import os
import pathlib
import dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

# Load env variables (automatically walks up to find .env in project root)
dotenv.load_dotenv()

# Define the transcriber agent using gemini-3.5-flash
transcriber = LlmAgent(
    name="transcriber_agent",
    model="gemini-3.5-flash",
    instruction="""
    You are an expert paleographer specializing in 19th-century American handwriting.
    Transcribe the handwritten text in the provided image exactly as written.
    Rules: preserve original spelling/punctuation, mark illegible words as [illegible],
    note line breaks with |, return ONLY the transcription — no commentary.
    """,
)

def transcribe_image_file(image_path: str | pathlib.Path, retries: int = 3, delay: float = 10.0) -> str:
    """Helper function to run the transcriber agent on an image file with fallback models on failure."""
    import time
    path = pathlib.Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at {path}")
        
    img_bytes = path.read_bytes()
    
    # Construct the multimodal message
    message = types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            types.Part.from_text(text="Transcribe this manuscript.")
        ]
    )
    
    fallback_models = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    
    for attempt in range(retries):
        current_model = fallback_models[attempt % len(fallback_models)]
        transcriber.model = current_model
        
        try:
            # Initialize in-memory runner
            runner = InMemoryRunner(agent=transcriber)
            
            # Create a unique session ID per attempt
            session_id = f"session_{path.stem}_{attempt}"
            runner.session_service.create_session_sync(
                app_name=runner.app_name,
                user_id="default_user",
                session_id=session_id
            )
            
            # Run the agent and extract the response text
            response_text = ""
            for event in runner.run(user_id="default_user", session_id=session_id, new_message=message):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text
                            
            if not response_text.strip():
                raise ValueError("Transcriber Agent returned empty response (possibly due to API 429).")
                
            return response_text
        except Exception as e:
            print(f"[Transcriber] Attempt {attempt + 1} with {current_model} failed: {e}")
            if attempt < retries - 1:
                print(f"[Transcriber] Waiting {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                raise e

if __name__ == "__main__":
    # Ensure output directory exists
    output_dir = pathlib.Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Test on the 3 Gibson diary sample images
    gibson_pages = ["011", "037", "049"]
    for page in gibson_pages:
        img_name = f"gibson_page{page}.jpg"
        img_path = pathlib.Path("data/images") / img_name
        
        print(f"\nTranscribing {img_name}...")
        try:
            transcript = transcribe_image_file(img_path)
            
            # Save the transcription output
            out_file = output_dir / f"transcription_page{page}.txt"
            out_file.write_text(transcript, encoding="utf-8")
            print(f"Saved transcript to {out_file}")
            print("-" * 40)
            print(transcript[:300] + ("..." if len(transcript) > 300 else ""))
            print("-" * 40)
        except Exception as e:
            print(f"Failed to transcribe {img_name}: {e}")
