import json
import pathlib
import pytest
from unittest.mock import MagicMock, patch

from mcp_server.loc_tools import (
    fetch_loc_page,
    get_bythepeople_transcript,
    save_transcript
)

# Test fetch_loc_page allows loc.gov domain
def test_fetch_loc_page_allows_loc_domain():
    # Arrange
    url = "https://tile.loc.gov/image-services/iiif/service:mss:mss5241:01:011/full/pct:100/0/default.jpg"
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "image/jpeg"}
    mock_response.content = b"fake_image_bytes"
    mock_response.raise_for_status = MagicMock()
    
    with patch("mcp_server.loc_tools.rate_limited_get", return_value=mock_response) as mock_get, \
         patch("pathlib.Path.write_bytes") as mock_write:
         
        # Act
        res_str = fetch_loc_page(url)
        res = json.loads(res_str)
        
        # Assert
        mock_get.assert_called_once_with(url)
        assert res["mime_type"] == "image/jpeg"
        assert res["size_bytes"] == len(b"fake_image_bytes")
        assert "service_mss_mss5241_01_011.jpg" in res["local_path"]

# Test fetch_loc_page rejects non-loc.gov domain
def test_fetch_loc_page_rejects_non_loc_domain():
    # Arrange
    url = "https://evil.com/malicious_image.jpg"
    
    with patch("mcp_server.loc_tools.rate_limited_get") as mock_get:
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            fetch_loc_page(url)
            
        assert "not in the allowlist" in str(excinfo.value)
        mock_get.assert_not_called()

# Test get_bythepeople_transcript parsing
def test_get_bythepeople_transcript_field_parsing():
    # Arrange
    item_id = "mss5241.mss5241_01_001_089_sp11"
    expected_url = "https://www.loc.gov/resource/mss5241.mss5241_01_001_089/?sp=11&fo=json"
    
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    # Mock the JSON structure containing fulltext inside 'page' list
    mock_response.json = MagicMock(return_value={
        "page": [
            {
                "fulltext": "Transcribed text for page 11."
            }
        ]
    })
    
    with patch("mcp_server.loc_tools.rate_limited_get", return_value=mock_response) as mock_get:
        # Act
        res_str = get_bythepeople_transcript(item_id)
        res = json.loads(res_str)
        
        # Assert
        mock_get.assert_called_once_with(expected_url)
        assert res["available"] is True
        assert res["transcript"] == "Transcribed text for page 11."

# Test save_transcript output filename and content
def test_save_transcript_writes_correct_filename():
    # Arrange
    text = "transcription content"
    metadata = {
        "item_id": "test_item",
        "page": 12
    }
    
    with patch("pathlib.Path.write_text") as mock_write, \
         patch("pathlib.Path.mkdir") as mock_mkdir:
         
        # Act
        res_message = save_transcript(text, metadata)
        
        # Assert
        assert "output/test_item_012.json" in res_message
        
        # Verify JSON content written matches inputs
        args, kwargs = mock_write.call_args
        written_data = json.loads(args[0])
        assert written_data["transcription"] == text
        assert written_data["metadata"]["item_id"] == "test_item"
        assert written_data["metadata"]["page"] == 12
