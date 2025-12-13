"""Cookie parsing and loading utilities."""
from pathlib import Path
import base64
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from utils.logger import get_logger

logger = get_logger()


def parse_cookie_string(cookie_string: str, domain: str = "") -> list[dict]:
    """
    Parse cookie string in header format to Playwright cookie format.

    Args:
        cookie_string: Cookie string in format "key1=value1; key2=value2"
        domain: Domain to set cookies for (e.g., ".example.com")

    Returns:
        list[dict]: List of cookie dictionaries in Playwright format

    Example:
        >>> cookies = parse_cookie_string(
        ...     "_ga=GA1.2.123456789.987654321; PHPSESSID=28f2d88e",
        ...     domain=".example.com"
        ... )
    """
    cookies = []
    cookie_string = cookie_string.strip()

    if not cookie_string:
        return cookies

    # Split by semicolon and parse each cookie
    for cookie_part in cookie_string.split(";"):
        cookie_part = cookie_part.strip()
        if not cookie_part or "=" not in cookie_part:
            continue

        name, value = cookie_part.split("=", 1)
        cookie = {
            "name": name.strip(),
            "value": value.strip(),
            "domain": domain,
            "path": "/",
        }
        cookies.append(cookie)

    return cookies


def load_cookies_from_file(file_path: str | Path, domain: str = "") -> list[dict]:
    """
    Load cookies from a file containing cookie string in header format.

    Args:
        file_path: Path to file containing cookie string
        domain: Domain to set cookies for (e.g., ".example.com")

    Returns:
        list[dict]: List of cookie dictionaries in Playwright format

    Example:
        File content: "_ga=GA1.2.123456789.987654321; PHPSESSID=28f2d88e"
        >>> cookies = load_cookies_from_file("cookies.txt", domain=".example.com")
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Cookie file not found: {file_path}")

    cookie_string = file_path.read_text().strip()
    return parse_cookie_string(cookie_string, domain=domain)


def validate_cookie(file_path: str | Path) -> bool:
    """
    Validate the cookie file content.
    Checks if:
    1. File exists and is not empty.
    2. Cookie string is parseable.
    3. 'sb-auth-auth-token' is present.
    4. Token is correctly formatted (base64 encoded JSON).
    5. Token contains required fields (access_token, expires_at).
    6. Token is not expired.
    
    Args:
        file_path: Path to cookie file.
        
    Returns:
        bool: True if cookie is strictly valid, False otherwise.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Cookie file does not exist: {path}")
        return False
        
    try:
        content = path.read_text().strip()
        if not content:
            logger.warning("Cookie file is empty.")
            return False
            
        # 1. Parse using the same logic as the loader
        cookies = parse_cookie_string(content)
        if not cookies:
            logger.warning("Failed to parse any cookies from file.")
            return False
            
        # 2. Find the auth token
        auth_cookie = next((c for c in cookies if c["name"] == "sb-auth-auth-token"), None)
        
        if not auth_cookie:
            logger.warning("No sb-auth-auth-token found in parsed cookies.")
            return False
            
        token_value = auth_cookie["value"]
        
        # 3. Check format (expects 'base64-' prefix)
        if not token_value.startswith("base64-"):
            logger.warning("Token value does not start with 'base64-'. Malformed.")
            return False
            
        b64_str = token_value[7:]
        
        # 4. Decode Base64
        # Add padding if needed
        b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
        
        try:
            json_str = base64.b64decode(b64_str).decode("utf-8")
            data = json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to decode token content: {e}")
            return False
            
        # 5. Check structural validity (required fields)
        if "access_token" not in data or "user" not in data:
            logger.warning("Token JSON missing required fields (access_token, user).")
            return False

        # 6. Check Expiration
        expires_at = data.get("expires_at")
        if not expires_at:
            logger.warning("Token has no expiration time.")
            return False
            
        exp_dt = datetime.fromtimestamp(expires_at)
        now = datetime.now()
        
        if now > exp_dt:
            logger.warning(f"Cookie expired at {exp_dt}")
            return False
            
        logger.info(f"Cookie valid until {exp_dt}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating cookie: {e}")
        return False


def save_cookies_from_browser(cookies: List[Dict[str, Any]], file_path: str | Path) -> None:
    """
    Convert browser cookies to header string format and save to file.
    
    Args:
        cookies: List of cookie dictionaries from Playwright
        file_path: Path to save the cookie string
    """
    cookie_parts = []
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value:
            cookie_parts.append(f"{name}={value}")
            
    cookie_string = "; ".join(cookie_parts)
    
    path = Path(file_path)
    path.write_text(cookie_string)
    logger.info(f"Saved {len(cookies)} cookies to {path}")
