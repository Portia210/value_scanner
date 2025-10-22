"""Page interaction helpers for Playwright."""
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    ElementHandle,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from .config import (
    DEFAULT_TIMEOUT,
    ElementState,
    WaitUntil,
    get_screenshot_path,
)


class PageHelper:
    """Helper class for common page operations."""

    def __init__(self, page: Page):
        """
        Initialize page helper.

        Args:
            page: Playwright page instance
        """
        self.page = page

    async def navigate(
        self,
        url: str,
        wait_until: WaitUntil = "load",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Navigate to URL with error handling.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation succeeded
            timeout: Maximum navigation time in milliseconds

        Returns:
            bool: True if navigation succeeded, False otherwise
        """
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            print(f"Timeout navigating to {url}")
            return False
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return False

    async def screenshot(
        self,
        path: str | Path,
        full_page: bool = False,
        element_selector: Optional[str] = None,
    ) -> bool:
        """
        Take a screenshot of the page or specific element.

        Screenshots are automatically saved to the screenshots/ directory
        unless an absolute path or path with parent directory is provided.

        Args:
            path: Path to save screenshot (auto-saved to screenshots/ folder)
            full_page: Capture full scrollable page
            element_selector: Optional CSS selector to screenshot specific element

        Returns:
            bool: True if screenshot succeeded, False otherwise
        """
        try:
            # Get proper screenshot path (will be in screenshots/ folder)
            screenshot_path = get_screenshot_path(path)

            if element_selector:
                element = await self.page.wait_for_selector(element_selector)
                if element:
                    await element.screenshot(path=str(screenshot_path))
            else:
                await self.page.screenshot(path=str(screenshot_path), full_page=full_page)
            return True
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return False

    async def wait_for_element(
        self,
        selector: str,
        state: ElementState = "visible",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Wait for element to reach specified state.

        Args:
            selector: CSS selector for element
            state: State to wait for
            timeout: Maximum wait time in milliseconds

        Returns:
            bool: True if element reached state, False otherwise
        """
        try:
            await self.page.wait_for_selector(selector, state=state, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            print(f"Timeout waiting for element: {selector}")
            return False
        except Exception as e:
            print(f"Error waiting for element: {e}")
            return False

    async def click_element(
        self,
        selector: str,
        timeout: int = DEFAULT_TIMEOUT,
        wait_for_nav: bool = False,
    ) -> bool:
        """
        Click an element with error handling.

        Args:
            selector: CSS selector for element
            timeout: Maximum wait time in milliseconds
            wait_for_nav: Whether to wait for navigation after click

        Returns:
            bool: True if click succeeded, False otherwise
        """
        try:
            if wait_for_nav:
                async with self.page.expect_navigation():
                    await self.page.click(selector, timeout=timeout)
            else:
                await self.page.click(selector, timeout=timeout)
            return True
        except Exception as e:
            print(f"Error clicking element {selector}: {e}")
            return False

    async def fill_input(
        self,
        selector: str,
        text: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Fill input field with text.

        Args:
            selector: CSS selector for input element
            text: Text to fill
            timeout: Maximum wait time in milliseconds

        Returns:
            bool: True if fill succeeded, False otherwise
        """
        try:
            await self.page.fill(selector, text, timeout=timeout)
            return True
        except Exception as e:
            print(f"Error filling input {selector}: {e}")
            return False

    async def get_text(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[str]:
        """
        Get text content of an element.

        Args:
            selector: CSS selector for element
            timeout: Maximum wait time in milliseconds

        Returns:
            Optional[str]: Element text content or None if not found
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                return await element.text_content()
            return None
        except Exception as e:
            print(f"Error getting text from {selector}: {e}")
            return None

    async def get_attribute(
        self,
        selector: str,
        attribute: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> Optional[str]:
        """
        Get attribute value of an element.

        Args:
            selector: CSS selector for element
            attribute: Attribute name
            timeout: Maximum wait time in milliseconds

        Returns:
            Optional[str]: Attribute value or None if not found
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                return await element.get_attribute(attribute)
            return None
        except Exception as e:
            print(f"Error getting attribute {attribute} from {selector}: {e}")
            return None

    async def evaluate_script(self, script: str) -> any:
        """
        Execute JavaScript in the page context.

        Args:
            script: JavaScript code to execute

        Returns:
            any: Result of script execution
        """
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            print(f"Error evaluating script: {e}")
            return None

    async def get_element(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[Locator]:
        """
        Get a Playwright Locator for an element.

        Args:
            selector: CSS selector for element
            timeout: Maximum wait time in milliseconds

        Returns:
            Optional[Locator]: Playwright Locator object or None if not found

        Example:
            >>> element = await helper.get_element("input[name='search']")
            >>> if element:
            ...     await element.fill("query")
            ...     await element.press("Enter")
        """
        try:
            locator = self.page.locator(selector)
            # Wait for element to be visible
            await locator.wait_for(state="visible", timeout=timeout)
            return locator
        except PlaywrightTimeoutError:
            print(f"Timeout waiting for element: {selector}")
            return None
        except Exception as e:
            print(f"Error getting element {selector}: {e}")
            return None

    async def press_key(
        self,
        key: str,
        selector: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Press a keyboard key on the page or on a specific element.

        Args:
            key: Key to press (e.g., "Enter", "Tab", "Escape", "ArrowDown")
                 See: https://playwright.dev/python/docs/api/class-keyboard#keyboard-press
            selector: Optional CSS selector to focus element before pressing key
            timeout: Maximum wait time in milliseconds

        Returns:
            bool: True if key press succeeded, False otherwise

        Example:
            >>> # Press Enter on the whole page
            >>> await helper.press_key("Enter")
            >>> # Press Enter on a specific input field
            >>> await helper.press_key("Enter", selector="input[name='search']")
        """
        try:
            if selector:
                # Focus element first, then press key
                await self.page.focus(selector, timeout=timeout)
            await self.page.keyboard.press(key)
            return True
        except Exception as e:
            print(f"Error pressing key {key}: {e}")
            return False

    async def type_text(
        self,
        selector: str,
        text: str,
        delay: int = 50,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> bool:
        """
        Type text into an element with realistic delays between keystrokes.

        This is different from fill_input() which instantly sets the value.
        Use this when you need to simulate realistic human typing.

        Args:
            selector: CSS selector for element
            text: Text to type
            delay: Delay between keystrokes in milliseconds (default: 50ms)
            timeout: Maximum wait time in milliseconds

        Returns:
            bool: True if typing succeeded, False otherwise

        Example:
            >>> # Type with 50ms delay between each character
            >>> await helper.type_text("input[name='search']", "Hello World")
            >>> # Type faster with 10ms delay
            >>> await helper.type_text("input", "Fast typing", delay=10)
        """
        try:
            await self.page.type(selector, text, delay=delay, timeout=timeout)
            return True
        except Exception as e:
            print(f"Error typing text into {selector}: {e}")
            return False

    async def is_disabled(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[bool]:
        """
        Check if an element is disabled.

        Args:
            selector: CSS selector for element
            timeout: Maximum wait time in milliseconds

        Returns:
            Optional[bool]: True if disabled, False if enabled, None if element not found

        Example:
            >>> is_disabled = await helper.is_disabled("button[type='submit']")
            >>> if is_disabled:
            ...     print("Button is disabled")
            >>> elif is_disabled is False:
            ...     print("Button is enabled")
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                # Check if element has disabled attribute
                disabled_attr = await element.get_attribute("disabled")
                # Also check if element is truly disabled using is_disabled()
                is_actually_disabled = await element.is_disabled()
                return is_actually_disabled or disabled_attr is not None
            return None
        except PlaywrightTimeoutError:
            print(f"Timeout waiting for element: {selector}")
            return None
        except Exception as e:
            print(f"Error checking if element {selector} is disabled: {e}")
            return None

    async def is_enabled(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[bool]:
        """
        Check if an element is enabled (opposite of is_disabled).

        Args:
            selector: CSS selector for element
            timeout: Maximum wait time in milliseconds

        Returns:
            Optional[bool]: True if enabled, False if disabled, None if element not found

        Example:
            >>> if await helper.is_enabled("button[type='submit']"):
            ...     await helper.click_element("button[type='submit']")
        """
        disabled = await self.is_disabled(selector, timeout)
        return None if disabled is None else not disabled

    async def is_visible(
        self, selector: str, timeout: int = DEFAULT_TIMEOUT
    ) -> Optional[bool]:
        """
        Check if an element is visible on the page.

        Args:
            selector: CSS selector for element
            timeout: Maximum wait time in milliseconds

        Returns:
            Optional[bool]: True if visible, False if hidden, None if element not found

        Example:
            >>> if await helper.is_visible("div.error-message"):
            ...     error_text = await helper.get_text("div.error-message")
        """
        try:
            element = await self.page.wait_for_selector(
                selector, state="attached", timeout=timeout
            )
            if element:
                return await element.is_visible()
            return None
        except PlaywrightTimeoutError:
            print(f"Timeout waiting for element: {selector}")
            return None
        except Exception as e:
            print(f"Error checking if element {selector} is visible: {e}")
            return None
