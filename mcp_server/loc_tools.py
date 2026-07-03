import pathlib
import sys
import json
from urllib.parse import urlparse

# Add project root to sys.path to allow importing security.guards
project_root = pathlib.Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from security.guards import rate_limited_get, validate_loc_url
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("LOC Tools Server")

@mcp.tool()
def fetch_loc_page(url: str) -> str:
    """
    Downloads an image from the Library of Congress (LOC) after enforcing the domain allowlist.
    Saves the image locally under data/images/ and returns a JSON string with metadata.
    """
    # Enforce URL allowlist
    validate_loc_url(url)
    
    # Download the image using rate-limited GET
    response = rate_limited_get(url)
    response.raise_for_status()
    
    # Extract MIME type
    mime_type = response.headers.get("Content-Type", "")
    
    # Extract size
    size_bytes = len(response.content)
    
    # Determine a unique filename based on the URL path
    parsed = urlparse(url)
    path_segments = parsed.path.split("/")
    filename = None
    
    # Find segments containing IIIF identifiers (often contain colons like service:mss:...)
    for segment in path_segments:
        if ":" in segment:
            filename = segment.replace(":", "_") + ".jpg"
            break
            
    if not filename:
        # Fallback to a hash of the URL
        filename = f"loc_{hash(url) & 0xffffffff:08x}.jpg"
        
    images_dir = project_root / "data" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    local_file = images_dir / filename
    local_file.write_bytes(response.content)
    
    # Relativize path for workspace portability
    rel_path = str(local_file.relative_to(project_root))
    
    result = {
        "local_path": rel_path,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "url": url
    }
    
    return json.dumps(result)

@mcp.tool()
def get_bythepeople_transcript(item_id: str) -> str:
    """
    Retrieves the crowdsourced "By the People" transcript for a page from the LOC JSON API.
    Enforces URL allowlist and returns a JSON string containing {"transcript": str, "available": bool}.
    """
    # Parse item_id: e.g. "mss5241.mss5241_01_001_089_sp11" -> resource = "mss5241.mss5241_01_001_089", sp = "11"
    if "_sp" in item_id:
        parts = item_id.split("_sp")
        resource_id = parts[0]
        page_num = parts[1]
        url = f"https://www.loc.gov/resource/{resource_id}/?sp={page_num}&fo=json"
    else:
        url = f"https://www.loc.gov/item/{item_id}/?fo=json"
        
    validate_loc_url(url)
    
    try:
        response = rate_limited_get(url)
        response.raise_for_status()
        data = response.json()
        
        # Traverse LOC JSON API structure to find fulltext transcript
        # We verified that the transcript lives inside data['page'] -> element with 'fulltext' key
        page_list = data.get("page", [])
        for page_data in page_list:
            if "fulltext" in page_data:
                transcript = page_data["fulltext"]
                if transcript:
                    return json.dumps({
                        "transcript": transcript.strip(),
                        "available": True
                    })
                    
        return json.dumps({
            "transcript": "",
            "available": False
        })
    except Exception as e:
        return json.dumps({
            "transcript": "",
            "available": False,
            "error": str(e)
        })

@mcp.tool()
def save_transcript(text: str, metadata: dict) -> str:
    """
    Saves the transcription output and metadata into output/ in JSON format.
    Filename pattern is {item_id}_{page:03d}.json
    """
    item_id = metadata.get("item_id", "unknown_item")
    page_num = metadata.get("page", 1)
    try:
        page_num = int(page_num)
    except (ValueError, TypeError):
        page_num = 1
        
    filename = f"{item_id}_{page_num:03d}.json"
    output_dir = project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / filename
    
    data_to_save = {
        "transcription": text,
        "metadata": metadata
    }
    
    output_file.write_text(json.dumps(data_to_save, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return f"Saved transcript and metadata to output/{filename}"

if __name__ == "__main__":
    # Start FastMCP server using stdio transport
    mcp.run()
