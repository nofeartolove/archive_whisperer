import json
import pytest
from unittest.mock import MagicMock, patch
from agents.validator import run_validator

# Test validator computes WER when ground truth is available
def test_validator_computes_wer_when_ground_truth_available():
    # Arrange
    item_id = "test_item_id"
    transcription = "this is the transcribed text"
    
    mock_payload = {
        "available": True,
        "ground_truth": "this is the ground truth text"
    }
    
    mock_event = MagicMock()
    mock_event.content = MagicMock()
    mock_part = MagicMock()
    mock_part.text = json.dumps(mock_payload)
    mock_event.content.parts = [mock_part]
    
    with patch("agents.validator.InMemoryRunner.run", return_value=[mock_event]):
         
        # Act
        res = run_validator(item_id, transcription, retries=1)
        
        # Assert
        assert res["available"] is True
        assert res["wer"] > 0.0  # Transcription has "transcribed" vs Ground Truth "ground truth"
        assert res["cer"] > 0.0
        assert res["ground_truth"] == "this is the ground truth text"

# Test validator handles missing ground truth gracefully
def test_validator_handles_missing_ground_truth():
    # Arrange
    item_id = "test_item_id"
    transcription = "this is the transcribed text"
    
    mock_payload = {
        "available": False,
        "ground_truth": ""
    }
    
    mock_event = MagicMock()
    mock_event.content = MagicMock()
    mock_part = MagicMock()
    mock_part.text = json.dumps(mock_payload)
    mock_event.content.parts = [mock_part]
    
    with patch("agents.validator.InMemoryRunner.run", return_value=[mock_event]):
         
        # Act
        res = run_validator(item_id, transcription, retries=1)
        
        # Assert
        assert res["available"] is False
        assert res["wer"] is None
        assert res["cer"] is None
        assert res["ground_truth"] == ""
