import os
import json
import pathlib
import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
import sys
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from agents.orchestrator import run_pipeline

@pytest.mark.integration
def test_full_pipeline_on_gibson_page011():
    # Arrange
    url = "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:011/full/pct:100/0/default.jpg"
    item_id = "mss5241.mss5241_01_001_089_sp11"
    page_num = 11
    
    mock_metadata = {
        "local_path": "data/images/service_mss_mss5241_01_011.jpg",
        "mime_type": "image/jpeg",
        "size_bytes": 943515,
        "url": url
    }
    mock_transcription = "January, MONDAY, 4. 1864. | Plymouth N.C. This morning gloomy | & threatens rain."
    mock_validation = {
        "available": True,
        "wer": 0.15,
        "cer": 0.10,
        "ground_truth": "January, MONDAY, 4. 1864. Plymouth N.C. This morning gloomy & threatens rain."
    }
    
    # We will let the real run_formatter execute so it writes the output files, 
    # but we will mock the agent session runner inside it to avoid LLM calls.
    # The output JSON filename matches the pattern {item_id}_{page_num:03d}.json
    json_output_file = project_root / "output" / f"{item_id}_{page_num:03d}.json"
    md_output_file = project_root / "output" / f"{item_id}_{page_num:03d}.md"
    txt_output_file = project_root / "output" / f"{item_id}_{page_num:03d}.txt"
    
    # Clean up any existing test output files before test
    for f in [json_output_file, md_output_file, txt_output_file]:
        if f.exists():
            f.unlink()
            
    # Mock the LLM helper functions to prevent any real model or network calls
    with patch("agents.orchestrator.run_fetcher", return_value=mock_metadata) as mock_fetch, \
         patch("agents.orchestrator.transcribe_image_file", return_value=mock_transcription) as mock_transcribe, \
         patch("agents.orchestrator.run_validator", return_value=mock_validation) as mock_validate:
         
        # Mock the formatter agent's runner class constructor specifically in the formatter module
        mock_runner_instance = MagicMock()
        mock_event = MagicMock()
        mock_event.content.parts = [MagicMock(text="Saved transcript and metadata to output/mss5241.mss5241_01_001_089_011.json")]
        mock_runner_instance.run.return_value = [mock_event]
        
        with patch("agents.formatter.InMemoryRunner", return_value=mock_runner_instance) as mock_formatter_runner_class:
            # Act
            pipeline_res = run_pipeline(url)
            
            # Assert
            # 1. Verify pipeline returned success
            assert pipeline_res["status"] == "COMPLETED"
            
            # 2. Verify all orchestration stages were called
            mock_fetch.assert_called_once_with(url)
            mock_transcribe.assert_called_once_with(project_root / mock_metadata["local_path"])
            mock_validate.assert_called_once_with(item_id, mock_transcription)
            
            # 3. Assert Markdown and TXT files were generated in output/
            assert md_output_file.exists(), "Markdown report was not created by the formatter stage"
            assert txt_output_file.exists(), "Text transcript was not created by the formatter stage"
            
            # Read the generated markdown content to verify fields
            md_content = md_output_file.read_text(encoding="utf-8")
            assert "- **Validation WER**: 15.00%" in md_content
            assert "- **Validation CER**: 10.00%" in md_content
            assert mock_transcription in md_content
        
        # Clean up output files created by the test
        for f in [md_output_file, txt_output_file]:
            if f.exists():
                f.unlink()
