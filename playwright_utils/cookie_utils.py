"""Cookie parsing and loading utilities."""
from pathlib import Path


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
