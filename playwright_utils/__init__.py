"""Playwright utilities package for web automation and scraping."""

# Core classes
from .browser_manager import BrowserManager
from .page_helper import PageHelper

# Cookie utilities
from .cookie_utils import load_cookies_from_file, parse_cookie_string

# Quick action functions
from .quick_actions import extract_page_data, quick_screenshot

# Configuration (optional exports for advanced usage)
from .config import (
    SCREENSHOTS_DIR,
    DEFAULT_VIEWPORT,
    BrowserType,
    ElementState,
    WaitUntil,
    ensure_screenshots_dir,
    get_screenshot_path,
)

__all__ = [
    # Core classes
    "BrowserManager",
    "PageHelper",
    # Cookie utilities
    "parse_cookie_string",
    "load_cookies_from_file",
    # Quick actions
    "quick_screenshot",
    "extract_page_data",
    # Configuration
    "SCREENSHOTS_DIR",
    "DEFAULT_VIEWPORT",
    "BrowserType",
    "ElementState",
    "WaitUntil",
    "ensure_screenshots_dir",
    "get_screenshot_path",
]
