from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright

SITE_URL = "https://gohaena.com/"
USER_DATA_DIR = Path(__file__).parent / ".browser-profile"


async def launch_context(headless: bool) -> tuple[BrowserContext, Page]:
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        str(USER_DATA_DIR),
        headless=headless,
        viewport={"width": 1400, "height": 1000},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.pages[0] if context.pages else await context.new_page()
    return context, page


async def open_booking_widget(page: Page) -> None:
    await page.goto(SITE_URL, wait_until="domcontentloaded")
    await page.wait_for_selector("#date-picker-step-2", state="attached", timeout=30000)
    await page.locator("#date-picker-step-2").scroll_into_view_if_needed()


async def dismiss_info_dialog(page: Page, timeout_ms: int = 4000) -> bool:
    try:
        btn = page.locator(".close--info--message--dialog--button")
        await btn.wait_for(state="visible", timeout=timeout_ms)
        await btn.click()
        return True
    except Exception:
        return False
