"""Configuration and constants for Playwright utilities."""
from pathlib import Path
from typing import Literal

# Screenshot configuration
SCREENSHOTS_DIR = Path("screenshots")
DEFAULT_SCREENSHOT_FORMAT = "png"

# Timeout defaults (in milliseconds)
DEFAULT_TIMEOUT = 30000
DEFAULT_NAVIGATION_TIMEOUT = 30000

# Browser configuration
BrowserType = Literal["chromium", "firefox", "webkit"]
WaitUntil = Literal["load", "domcontentloaded", "networkidle", "commit"]
ElementState = Literal["attached", "detached", "visible", "hidden"]

# Default viewport size (fullscreen 1920x1080)
DEFAULT_VIEWPORT = {
    "width": 1920,
    "height": 1080,
}


def ensure_screenshots_dir() -> Path:
    """Ensure screenshots directory exists and return the path."""
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    return SCREENSHOTS_DIR


def get_screenshot_path(filename: str | Path) -> Path:
    """
    Get full path for screenshot, ensuring it's in the screenshots directory.

    Args:
        filename: Screenshot filename or path

    Returns:
        Path: Full path in screenshots directory
    """
    ensure_screenshots_dir()
    filename_path = Path(filename)

    # If already an absolute path or has parent directory, use as-is
    if filename_path.is_absolute() or str(filename_path.parent) != ".":
        return filename_path

    # Otherwise, put it in screenshots directory
    return SCREENSHOTS_DIR / filename_path.name
