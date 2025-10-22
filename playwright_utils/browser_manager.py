"""Browser lifecycle management for Playwright."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from .config import BrowserType, DEFAULT_VIEWPORT
from .cookie_utils import load_cookies_from_file


class BrowserManager:
    """Manages browser lifecycle with async context manager support."""

    def __init__(
        self,
        browser_type: BrowserType = "chromium",
        headless: bool = True,
        slow_mo: int = 0,
    ):
        """
        Initialize browser manager.

        Args:
            browser_type: Type of browser to launch
            headless: Whether to run browser in headless mode
            slow_mo: Slow down operations by specified milliseconds
        """
        self.browser_type = browser_type
        self.headless = headless
        self.slow_mo = slow_mo
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def __aenter__(self) -> "BrowserManager":
        """Start browser on context entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # noqa: ANN001
        """Close browser on context exit."""
        # Handle KeyboardInterrupt gracefully
        if exc_type is KeyboardInterrupt:
            print("\n\nInterrupted by user. Closing browser gracefully...")

        try:
            await self.close()
        except Exception:
            # Suppress errors during cleanup
            pass

        # Don't suppress KeyboardInterrupt - let it propagate but cleaned up
        return False

    async def start(self) -> Browser:
        """Start the browser instance."""
        self._playwright = await async_playwright().start()
        browser_launcher = getattr(self._playwright, self.browser_type)

        # Build launch args for window sizing (only for Chromium in headed mode)
        launch_args = {}
        if self.browser_type == "chromium" and not self.headless:
            launch_args["args"] = [
                "--start-fullscreen",  # Start in fullscreen mode
                "--force-device-scale-factor=1",  # Disable DPI scaling
                "--disable-blink-features=AutomationControlled",  # Hide automation detection
            ]

        self._browser = await browser_launcher.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            **launch_args,
        )
        return self._browser

    async def close(self):
        """Close browser and playwright instances."""
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            # Suppress browser close errors
            pass

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            # Suppress playwright stop errors
            pass

    @asynccontextmanager
    async def new_context(self, **kwargs) -> AsyncIterator[BrowserContext]:
        """
        Create a new browser context.

        Args:
            **kwargs: Additional context options (viewport, user_agent, etc.)
                     Default viewport is 1920x1080 (fullscreen in headless mode).
                     In headed mode with maximized window, viewport is set to None
                     to use actual window size.

        Yields:
            BrowserContext: New browser context
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")

        # Set default viewport if not specified
        if "viewport" not in kwargs and "no_viewport" not in kwargs:
            # For headed Chromium with fullscreen, disable viewport to use actual window size
            if self.browser_type == "chromium" and not self.headless:
                kwargs["no_viewport"] = True  # Use actual window size
            else:
                kwargs["viewport"] = DEFAULT_VIEWPORT

        context = await self._browser.new_context(**kwargs)
        try:
            yield context
        finally:
            try:
                await context.close()
            except Exception:
                # Suppress cleanup errors
                pass

    @asynccontextmanager
    async def new_page(
        self, cookies: Optional[list[dict]] = None, **context_kwargs
    ) -> AsyncIterator[Page]:
        """
        Create a new page with a new context.

        Args:
            cookies: Optional list of cookies to set in the context
            **context_kwargs: Context options to pass to new_context

        Yields:
            Page: New browser page
        """
        async with self.new_context(**context_kwargs) as context:
            # Add cookies if provided
            if cookies:
                await context.add_cookies(cookies)

            page = await context.new_page()
            try:
                yield page
            finally:
                try:
                    await page.close()
                except Exception:
                    # Suppress cleanup errors
                    pass

    @asynccontextmanager
    async def new_page_with_cookies_from_file(
        self,
        cookie_file: str | Path,
        domain: str,
        **context_kwargs,
    ) -> AsyncIterator[Page]:
        """
        Create a new page with cookies loaded from a file.

        Args:
            cookie_file: Path to file containing cookie string
            domain: Domain to set cookies for (e.g., ".example.com")
            **context_kwargs: Context options to pass to new_context

        Yields:
            Page: New browser page with cookies set

        Example:
            >>> async with manager.new_page_with_cookies_from_file(
            ...     "cookies.txt", domain=".example.com"
            ... ) as page:
            ...     await page.goto("https://example.com")
        """
        cookies = load_cookies_from_file(cookie_file, domain=domain)
        async with self.new_page(cookies=cookies, **context_kwargs) as page:
            yield page
