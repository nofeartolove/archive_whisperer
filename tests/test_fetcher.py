import json
import pytest
from unittest.mock import MagicMock, patch
from agents.fetcher import run_fetcher

def test_fetcher_rejects_non_image_mime():
    # Arrange
    url = "https://tile.loc.gov/somefile.txt"
    mock_payload = {
        "local_path": "data/images/somefile.txt",
        "mime_type": "text/plain",  # Non-image MIME type
        "size_bytes": 100,
        "url": url
    }
    
    # Mock InMemoryRunner execution events
    mock_event = MagicMock()
    mock_event.content = MagicMock()
    mock_part = MagicMock()
    mock_part.text = json.dumps(mock_payload)
    mock_event.content.parts = [mock_part]
    
    with patch("agents.fetcher.InMemoryRunner.run", return_value=[mock_event]):
         
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            run_fetcher(url, retries=1)
            
        assert "Security Rejection: Downloaded file has non-image MIME type" in str(excinfo.value)
