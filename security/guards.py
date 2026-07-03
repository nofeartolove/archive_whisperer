import time
import re
from urllib.parse import urlparse
import requests

# Track the timestamp of the last request to loc.gov to enforce rate limits
_last_request_time = 0.0

def validate_loc_url(url: str) -> str:
    """
    Validates that a URL belongs to the allowed Library of Congress domains.
    Returns the URL if valid, otherwise raises ValueError.
    """
    if not url:
        raise ValueError("URL cannot be empty.")
        
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    
    # Allowed domains (exact matches or subdomains)
    allowed_domains = ['loc.gov', 'tile.loc.gov', 'www.loc.gov']
    
    # Check if the domain matches exactly or ends with one of the allowed domains
    is_allowed = netloc in allowed_domains or any(netloc.endswith('.' + domain) for domain in allowed_domains)
    
    if not is_allowed:
        raise ValueError(f"URL domain '{netloc}' is not in the allowlist {allowed_domains}.")
        
    return url

def rate_limited_get(url: str, *args, **kwargs) -> requests.Response:
    """
    Enforces rate limits for LOC outbound requests.
    LOC JSON API allows 20 req/min (3.0s interval).
    LOC Media API allows 150 req/min (0.4s interval).
    We enforce a safe, conservative 3.0s delay between any consecutive requests.
    """
    global _last_request_time
    
    # Validate first
    validate_loc_url(url)
    
    min_interval = 3.0
    now = time.time()
    elapsed = now - _last_request_time
    
    if elapsed < min_interval:
        sleep_time = min_interval - elapsed
        time.sleep(sleep_time)
        
    headers = kwargs.get("headers", {})
    if "User-Agent" not in headers:
        # Standard polite User-Agent for research projects
        headers["User-Agent"] = "ArchiveWhispererPaleographyAgent/1.0 (contact: nallathambi@example.com)"
    kwargs["headers"] = headers
    
    response = requests.get(url, *args, **kwargs)
    _last_request_time = time.time()
    return response

def sanitize_user_input(text: str) -> str:
    """
    Sanitizes user input by:
    1. Truncating to a maximum of 2000 characters.
    2. Scanning for potential prompt injection patterns.
    """
    if not text:
        return ""
        
    # 1. Enforce 2000-char cap
    if len(text) > 2000:
        raise ValueError(f"Input length ({len(text)} chars) exceeds the security cap of 2000 characters.")
        
    # 2. Scanning for potential prompt injection patterns (case-insensitive)
    injection_patterns = [
        r"ignore\s+(?:all\s+)?previous\s+instructions",
        r"system\s+instructions\s+override",
        r"bypass\s+security",
        r"you\s+must\s+now\s+act\s+as",
        r"jailbreak",
        r"instruction\s+bypass"
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("Security Alert: Input contains potential prompt injection patterns.")
            
    return text
