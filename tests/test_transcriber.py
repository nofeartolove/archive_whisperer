import pathlib
import pytest
import jiwer
from agents.transcriber import transcribe_image_file

# Define the paths
IMAGES_DIR = pathlib.Path("data/images")
GROUND_TRUTH_DIR = pathlib.Path("data/ground_truth")

def check_file_exists(path: pathlib.Path, file_description: str):
    if not path.exists():
        pytest.fail(f"ERROR: Required {file_description} is missing at {path}")

@pytest.mark.live
def test_transcriber_returns_nonempty_output():
    # Arrange
    image_path = IMAGES_DIR / "gibson_page011.jpg"
    check_file_exists(image_path, "sample image (page 11)")
    
    # Act
    result = transcribe_image_file(image_path)
    
    # Assert
    assert isinstance(result, str)
    assert len(result.strip()) > 0

@pytest.mark.live
def test_transcriber_output_format():
    # Arrange
    image_path = IMAGES_DIR / "gibson_page011.jpg"
    check_file_exists(image_path, "sample image (page 11)")
    
    # Act
    result = transcribe_image_file(image_path)
    result_clean = result.strip()
    
    # Assert
    # 1. No conversational preamble/commentary
    preamble_triggers = ["here is", "sure,", "the transcription is", "transcription:", "here's", "this is"]
    for trigger in preamble_triggers:
        assert not result_clean.lower().startswith(trigger), f"Output contains conversational preamble trigger: '{trigger}'"
        
    # 2. Strict bracket format for illegible text
    # Checks that any mention of "illegible" is formatted exactly as [illegible]
    if "illegible" in result_clean.lower():
        # Ensure we only have exact match of "[illegible]" case-insensitively
        assert "[illegible]" in result_clean.lower(), "Illegible text found but not formatted exactly as '[illegible]'"
        assert "(illegible)" not in result_clean.lower(), "Found incorrect format '(illegible)'"
        
    # Checks that common alternative words are not used
    assert "unclear" not in result_clean.lower(), "Found forbidden word 'unclear' instead of '[illegible]'"
    
    # 3. Line breaks represented with | if it spans multiple lines
    lines = [l for l in result_clean.split("\n") if l.strip()]
    if len(lines) > 1:
        assert "|" in result_clean, "Output spans multiple lines but does not contain '|' line break separators"

@pytest.mark.live
@pytest.mark.parametrize("page_str", ["011", "037", "049"])
def test_transcriber_accuracy_against_ground_truth(page_str):
    # Arrange
    image_path = IMAGES_DIR / f"gibson_page{page_str}.jpg"
    truth_path = GROUND_TRUTH_DIR / f"gibson_page{page_str}.txt"
    
    check_file_exists(image_path, f"sample image (page {page_str})")
    check_file_exists(truth_path, f"ground truth transcript (page {page_str})")
    
    truth_text = truth_path.read_text(encoding="utf-8").strip()
    
    # Act
    hypothesis_text = transcribe_image_file(image_path).strip()
    
    # Remove the line break symbols '|' to allow a fair word-level comparison
    # as the ground truth does not contain them.
    hypothesis_clean = hypothesis_text.replace("|", " ")
    
    # Calculate Word Error Rate (WER) using jiwer
    wer_value = jiwer.wer(truth_text, hypothesis_clean)
    
    # Print the value on standard output (visible during pytest -s)
    print(f"\nPage {page_str} WER: {wer_value:.4f}")
    
    # Assert
    assert wer_value < 0.20, (
        f"Page {page_str} transcription accuracy check failed! "
        f"WER: {wer_value:.4f} (exceeds threshold 0.20)\n"
        f"Ground Truth:\n{truth_text}\n"
        f"Hypothesis:\n{hypothesis_clean}"
    )
