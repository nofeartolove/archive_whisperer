import json
import pytest
from unittest.mock import MagicMock, patch
from agents.formatter import run_formatter

def test_formatter_writes_outputs():
    # Arrange
    text = "Transcribed transcription text content"
    metadata = {
        "item_id": "test_item_formatter",
        "page": 15,
        "wer": 0.12,
        "cer": 0.08,
        "mime_type": "image/jpeg",
        "size_bytes": 1024,
        "source_url": "https://www.loc.gov/item/test_item_formatter/"
    }
    
    # Mock event loop inside runner
    mock_event = MagicMock()
    mock_event.content = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Saved transcript and metadata to output/test_item_formatter_015.json"
    mock_event.content.parts = [mock_part]
    
    mock_runner_instance = MagicMock()
    mock_runner_instance.run.return_value = [mock_event]
    
    with patch("agents.formatter.InMemoryRunner", return_value=mock_runner_instance) as mock_runner_class, \
         patch("pathlib.Path.write_text") as mock_write_text, \
         patch("pathlib.Path.mkdir") as mock_mkdir:
         
        # Act
        summary = run_formatter(text, metadata, retries=1)
        
        # Assert
        assert "Saved files" in summary
        assert "test_item_formatter_015.md" in summary
        assert "test_item_formatter_015.txt" in summary
        
        # Verify that both Markdown (.md) and plain text (.txt) files were written
        assert mock_write_text.call_count == 2
        
        # First call is MD
        args_md, _ = mock_write_text.call_args_list[0]
        md_content = args_md[0]
        assert "# Transcription Report - test_item_formatter" in md_content
        assert "- **Validation WER**: 12.00%" in md_content
        assert "- **Validation CER**: 8.00%" in md_content
        assert text in md_content
        
        # Second call is TXT
        args_txt, _ = mock_write_text.call_args_list[1]
        txt_content = args_txt[0]
        assert txt_content == text
