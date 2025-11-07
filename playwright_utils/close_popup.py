from playwright.async_api import Page

async def close_popup(page: Page):
    # Check if popup exists and close it
    popup = page.locator('[aria-modal="true"]')
    if await popup.count() > 0:
        close_button = popup.locator('button[aria-label="Close"]')
        if await close_button.count() > 0:
            await close_button.click()