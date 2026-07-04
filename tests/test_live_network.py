import pytest
import requests
from security.guards import validate_loc_url

@pytest.mark.live
def test_live_loc_api_canary():
    # Arrange
    # Known Gibson diary page 11 resource metadata JSON URL
    url = "https://www.loc.gov/resource/mss5241.mss5241_01_001_089/?sp=11&fo=json"
    
    # Act
    validate_loc_url(url)
    response = requests.get(url, timeout=15)
    
    # Assert
    # Verify connection and basic status code
    assert response.status_code == 200, f"LOC API returned status code {response.status_code}"
    
    # Verify the JSON response contains the fields we parse
    data = response.json()
    assert "page" in data, "LOC resource JSON does not contain 'page' field."
    assert isinstance(data["page"], list), "'page' field is not a list."
    assert len(data["page"]) > 0, "'page' list is empty."
    
    # Verify that 'fulltext' field exists in the page structure
    has_fulltext = any("fulltext" in page_data for page_data in data["page"])
    assert has_fulltext, "None of the pages in 'page' list contain 'fulltext' field."
