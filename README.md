# Value Scanner

A clean, modular async Playwright utilities project for web automation and scraping.

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install
```

## Project Structure

```
value_scanner/
├── utils/                       # Modular Playwright utilities
│   ├── __init__.py             # Public API exports
│   ├── browser_manager.py      # Browser lifecycle management
│   ├── page_helper.py          # Page interaction helpers
│   ├── cookie_utils.py         # Cookie parsing utilities
│   ├── quick_actions.py        # Convenience functions
│   └── config.py               # Configuration and constants
├── screenshots/                 # Auto-generated screenshots folder
├── example.ipynb               # Example Jupyter notebook
├── main.py
└── pyproject.toml
```

## Utilities

The `utils/` package provides modular, clean utilities organized by functionality:

### Core Classes
- **BrowserManager** (`browser_manager.py`): Manages browser lifecycle with async context manager support
- **PageHelper** (`page_helper.py`): Helper class for common page operations (navigation, screenshots, interactions)

### Cookie Management
- **parse_cookie_string()** (`cookie_utils.py`): Parse cookie string in header format to Playwright cookies
- **load_cookies_from_file()** (`cookie_utils.py`): Load cookies from a file containing header-format cookie string

### Quick Actions
- **quick_screenshot()** (`quick_actions.py`): Utility function to quickly screenshot a URL
- **extract_page_data()** (`quick_actions.py`): Utility function to extract data from a page using CSS selectors

### Configuration
- **config.py**: Constants, default timeouts, and screenshot directory configuration

## Key Features

- **Modular Design**: Each module has a single responsibility
- **Auto Screenshot Management**: All screenshots automatically saved to `screenshots/` folder
- **Clean Imports**: Import everything from `utils` package
- **Full async/await support**: Modern Python async patterns
- **Context managers**: Automatic cleanup
- **Error handling**: Built-in error handling throughout
- **Type hints**: Full type annotation coverage
- **DRY principles**: No code duplication

## Usage

### Quick Screenshot

Screenshots are automatically saved to the `screenshots/` directory:

```python
from utils import quick_screenshot

# Take a screenshot - auto-saved to screenshots/screenshot.png
await quick_screenshot(
    url="https://example.com",
    output_path="screenshot.png",  # Saves to screenshots/screenshot.png
    full_page=True
)
```

### Advanced Usage with BrowserManager

```python
from utils import BrowserManager, PageHelper

async with BrowserManager(headless=True) as manager:
    async with manager.new_page() as page:
        helper = PageHelper(page)

        # Navigate
        await helper.navigate("https://example.com")

        # Interact with page
        await helper.fill_input("input[name='search']", "playwright")
        await helper.click_element("button[type='submit']")

        # Take screenshot - auto-saved to screenshots/results.png
        await helper.screenshot("results.png")
```

### Extract Page Data

```python
from utils import extract_page_data

data = await extract_page_data(
    url="https://example.com",
    selectors={
        "title": "h1",
        "description": "p",
    }
)
```

### Using Cookies

```python
from utils import (
    BrowserManager,
    parse_cookie_string,
    load_cookies_from_file,
)

# Method 1: Parse cookie string directly
cookie_string = "_ga=GA1.2.123456789.987654321; PHPSESSID=28f2d88e"
cookies = parse_cookie_string(cookie_string, domain=".example.com")

async with BrowserManager() as manager:
    async with manager.new_page(cookies=cookies) as page:
        await page.goto("https://example.com")

# Method 2: Load cookies from file
# File content: "_ga=GA1.2.123456789.987654321; PHPSESSID=28f2d88e"
async with BrowserManager() as manager:
    async with manager.new_page_with_cookies_from_file(
        cookie_file="cookies.txt",
        domain=".example.com"
    ) as page:
        await page.goto("https://example.com")
```

## Example Notebook

See `example.ipynb` for comprehensive examples including:
- Quick screenshots
- Page data extraction
- Cookie management (from strings and files)
- Form interactions
- JavaScript execution
- Multiple browser types

Run the notebook with:

```bash
uv run jupyter notebook example.ipynb
```

## Module Details

### browser_manager.py
Handles browser lifecycle management with support for:
- Multiple browser types (Chromium, Firefox, WebKit)
- Headless/headed modes
- Cookie injection
- Context management

### page_helper.py
Provides high-level page interactions:
- Navigation with error handling
- Screenshot capture (auto-saved to screenshots/)
- Element waiting and interaction
- Text and attribute extraction
- JavaScript execution

### cookie_utils.py
Cookie parsing and loading:
- Parse header-format cookie strings
- Load from files
- Automatic Playwright format conversion

### quick_actions.py
Convenience functions for common tasks:
- One-line screenshots
- Quick data extraction
- Simplified browser automation

### config.py
Configuration and constants:
- Default screenshot directory
- Timeout values
- Type definitions
