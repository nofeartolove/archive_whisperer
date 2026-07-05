"""
Transcriber Agent for Archive Whisperer
"""

import os
import pathlib
import dotenv
from google.adk.agents import LlmAgent
from google.genai import types

# Load env variables (automatically walks up to find .env in project root)
dotenv.load_dotenv()

# Add project root to sys.path if not present (to import security.guards)
import sys
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from security.guards import load_skill_instruction

# LlmAgent retained for ADK architecture documentation — transcribe_image_file
# calls the Gemini API directly to avoid ADK InMemoryRunner empty-response instability.
transcriber = LlmAgent(
    name="transcriber_agent",
    model="gemini-3.5-flash",
    instruction=load_skill_instruction("transcribe_image"),
)


def transcribe_image_file(image_path: str | pathlib.Path, retries: int = 4, delay: float = 10.0) -> str:
    """Transcribes a manuscript image using the Gemini vision API directly.

    Calls google.genai.Client.models.generate_content() directly instead of
    routing through ADK's InMemoryRunner, eliminating the 'model output must
    contain either output text or tool calls' error that the ADK runner raises
    when it loses the model's text response internally.
    """
    import time
    import google.genai as genai

    path = pathlib.Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at {path}")

    img_bytes = path.read_bytes()

    # Load the paleography instruction from the skill file
    instruction = load_skill_instruction("transcribe_image")

    fallback_models = [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
    ]

    client = genai.Client()

    for attempt in range(retries):
        current_model = fallback_models[attempt % len(fallback_models)]
        try:
            print(f"[Transcriber] Attempt {attempt + 1}: transcribing {path.name} with {current_model}")

            response = client.models.generate_content(
                model=current_model,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    types.Part.from_text(text=f"{instruction}\n\nTranscribe this manuscript page exactly."),
                ],
            )

            response_text = response.text if response.text else ""

            if not response_text.strip():
                raise ValueError(f"Transcriber got empty response from {current_model}.")

            print(f"[Transcriber] Success: {len(response_text)} chars transcribed.")
            return response_text

        except Exception as e:
            # Truncate raw exception output to keep stdout clean on screen
            err_msg = str(e)
            if len(err_msg) > 150:
                err_msg = err_msg[:150] + "..."
            print(f"[Transcriber] Attempt {attempt + 1} with {current_model} failed: {err_msg}")
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

            out_file = output_dir / f"transcription_page{page}.txt"
            out_file.write_text(transcript, encoding="utf-8")
            print(f"Saved transcript to {out_file}")
            print("-" * 40)
            print(transcript[:300] + ("..." if len(transcript) > 300 else ""))
            print("-" * 40)
        except Exception as e:
            print(f"Failed to transcribe {img_name}: {e}")
