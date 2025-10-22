# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Value Scanner is a modular async Playwright utilities library for web automation and scraping. The codebase follows strict architectural principles: modular design, DRY code, and single responsibility per module.

## Development Commands

### Setup
```bash
# Install dependencies (creates .venv automatically)
uv sync

# Install Playwright browsers (required for testing)
uv run playwright install
```

### Running Code
```bash
# Run Python scripts
uv run python script_name.py

# Run Jupyter notebook
uv run jupyter notebook example.ipynb
```

## Architecture

### Core Design Principles

1. **Import Pattern**: All public APIs are imported through `utils/__init__.py`. Users should import from `utils`, never from individual modules:
   ```python
   from utils import BrowserManager, PageHelper  # Correct
   from utils.browser_manager import BrowserManager  # Avoid
   ```

2. **Screenshot Auto-Routing**: All screenshots automatically save to `screenshots/` directory via `get_screenshot_path()` in `config.py`. This applies to both `PageHelper.screenshot()` and `quick_screenshot()`.

3. **Default Viewport**: Browser contexts default to 1920x1080 fullscreen viewport (set in `DEFAULT_VIEWPORT`). This is applied automatically in `BrowserManager.new_context()`.

4. **Cookie Format**: Cookies are parsed from header string format (`key1=value1; key2=value2`) to Playwright's dict format. Cookie utilities handle this conversion transparently.

### Module Dependencies

```
utils/
├── config.py           (no internal dependencies - pure configuration)
├── cookie_utils.py     (no internal dependencies - pure utilities)
├── browser_manager.py  (imports: config, cookie_utils)
├── page_helper.py      (imports: config)
├── quick_actions.py    (imports: browser_manager, page_helper, config)
└── __init__.py         (imports all modules for public API)
```

**Important**: This dependency hierarchy prevents circular imports. Never import from `quick_actions` or `browser_manager` in lower-level modules.

### Key Architectural Details

#### BrowserManager Flow
- `new_context()` automatically injects `DEFAULT_VIEWPORT` if viewport not specified
- `new_page()` wraps context creation and handles cookie injection
- `new_page_with_cookies_from_file()` is a convenience method combining file loading + page creation

#### PageHelper Screenshot Path Resolution
The `screenshot()` method calls `get_screenshot_path()` which:
1. Checks if path is absolute or has parent directory → uses as-is
2. Otherwise → automatically prepends `screenshots/` directory
3. Creates `screenshots/` directory if it doesn't exist

#### Cookie Utilities
- `parse_cookie_string()`: Converts `"key=val; key2=val2"` → `[{"name": "key", "value": "val", "domain": "...", "path": "/"}]`
- `load_cookies_from_file()`: Reads file → calls `parse_cookie_string()`
- Both functions are stateless and have no side effects

## Adding New Features

### Adding a New Utility Function
1. Determine the correct module based on responsibility:
   - Browser lifecycle → `browser_manager.py`
   - Page interactions → `page_helper.py`
   - Cookie operations → `cookie_utils.py`
   - Convenience wrappers → `quick_actions.py`
   - Constants/config → `config.py`

2. Add the function/class to the appropriate module

3. Export it in `utils/__init__.py`:
   ```python
   from .module_name import new_function

   __all__ = [
       # ... existing exports
       "new_function",
   ]
   ```

### Adding New Configuration
1. Add constant to `config.py` (e.g., `NEW_CONSTANT = value`)
2. Export in `utils/__init__.py` if it's part of public API
3. Import where needed: `from .config import NEW_CONSTANT`

## Important Constraints

- **Python Version**: Requires Python >=3.11 (for `X | Y` type syntax)
- **Async Only**: All browser operations are async; use `async/await` patterns
- **Type Hints**: All functions must have complete type annotations
- **Error Handling**: PageHelper methods return `bool` or `Optional[T]` rather than raising exceptions
- **Context Managers**: BrowserManager and page contexts must use `async with` for proper cleanup
- **No Playwright Direct Calls**: Users should use PageHelper methods, not call Playwright Page methods directly (except in advanced cases)

## Cookie File Format

Cookie files must use header string format (one line):
```
sessionid=abc123; token=xyz789; user_pref=dark_mode
```

Users paste cookies from browser DevTools Network tab → save to file → load with `load_cookies_from_file()`.

## Testing Patterns

When testing new utilities, follow this pattern:
```python
import asyncio
from utils import BrowserManager, PageHelper

async def test_feature():
    async with BrowserManager(headless=True) as manager:
        async with manager.new_page() as page:
            helper = PageHelper(page)
            # Test code here

if __name__ == "__main__":
    asyncio.run(test_feature())
```

Screenshots from tests will automatically go to `screenshots/` directory.
