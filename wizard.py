import asyncio
import datetime as dt

from playwright.async_api import Page

from browser import dismiss_info_dialog

SERVICE_TYPE_PARKING = "parking_and_park_entry"
SERVICE_TYPE_WAIPA_SHUTTLE = "shuttle"
SERVICE_TYPE_PRINCEVILLE_SHUTTLE = "shuttle_princeville"
SERVICE_TYPE_ENTRY_ONLY = "park_entry"


async def set_party_size(page: Page, adults: int, children: int = 0) -> None:
    adult_input = page.locator('input[placeholder="1"]').first
    current = int((await adult_input.input_value()) or "1")
    diff = adults - current
    label = "Increase adult quantity" if diff > 0 else "Decrease adult quantity"
    for _ in range(abs(diff)):
        await page.locator(f'[aria-label="{label}"]').click()
        await asyncio.sleep(0.05)

    if children:
        for _ in range(children):
            await page.locator('[aria-label="Increase child quantity"]').click()
            await asyncio.sleep(0.05)


async def select_date(page: Page, target: dt.date) -> None:
    # jQuery UI datepicker's setDate() does not fire onSelect, so the widget's
    # internal model never updates that way -- a real click is required.
    await page.locator("#date-picker-step-2").click()
    await page.wait_for_selector(".ui-datepicker-calendar", state="visible", timeout=5000)
    for _ in range(24):
        title = await page.locator(".ui-datepicker-title").inner_text()
        current = dt.datetime.strptime(title.strip(), "%B %Y")
        if current.year == target.year and current.month == target.month:
            break
        await page.locator(".ui-datepicker-next").click()
        await asyncio.sleep(0.1)
    else:
        raise RuntimeError(f"Could not navigate calendar to {target:%B %Y}")

    day_cells = page.locator(".ui-datepicker-calendar td a", has_text=str(target.day))
    await day_cells.first.click()


async def click_check_availability(page: Page) -> None:
    await page.get_by_role("button", name="CHECK AVAILABILITY").click()
    await dismiss_info_dialog(page, timeout_ms=4000)
    await page.wait_for_selector(
        ".orderStepContainer.step-3.active", state="attached", timeout=15000
    )


def _row_tile_locator(page: Page, target: dt.date, service_type: str):
    date_int = f"{target.year}{target.month:02d}{target.day:02d}"
    row = page.locator(f'.v_row:has(.tile--date[data-date-int="{date_int}"])')
    return row.locator(f'[data-service-type="{service_type}"]')


async def wait_for_slot_available(
    page: Page, target: dt.date, timeout_seconds: float, service_type: str = SERVICE_TYPE_PARKING
) -> bool:
    end = asyncio.get_event_loop().time() + timeout_seconds
    while asyncio.get_event_loop().time() < end:
        locator = _row_tile_locator(page, target, service_type)
        if await locator.count() > 0:
            available = await locator.get_attribute("data-available")
            if available == "true":
                return True
        await asyncio.sleep(0.15)
    return False


async def select_grid_tile(
    page: Page, target: dt.date, service_type: str = SERVICE_TYPE_PARKING
) -> None:
    await _row_tile_locator(page, target, service_type).click()
    await page.get_by_role("button", name="CONTINUE").click()
    await dismiss_info_dialog(page, timeout_ms=600)
    await page.wait_for_selector(
        ".orderStepContainer.step-4.active", state="attached", timeout=15000
    )


async def _click_slot_tile(active, slot_name: str) -> bool:
    candidates = [
        active.get_by_role("button", name=slot_name),
        active.get_by_role("radio", name=slot_name),
        active.locator(f'[class*="tile"]:has-text("{slot_name}")'),
        active.get_by_text(slot_name, exact=False),
    ]
    for locator in candidates:
        try:
            if await locator.count() > 0:
                await locator.first.click(timeout=3000)
                return True
        except Exception:
            continue
    return False


async def choose_time_slot_and_reserve(page: Page, slot_name: str) -> None:
    active = page.locator(".orderStepContainer.active")

    if await _click_slot_tile(active, slot_name):
        pass
    else:
        select_el = active.locator("select")
        if await select_el.count() > 0:
            options = await select_el.first.locator("option").all_inner_texts()
            match = next((o for o in options if slot_name.lower() in o.lower()), None)
            if match:
                await select_el.first.select_option(label=match)
            else:
                raise RuntimeError(f"Could not find a way to select slot '{slot_name}'")
        else:
            raise RuntimeError(f"Could not find a way to select slot '{slot_name}'")

    await page.get_by_role("button", name="RESERVE YOUR SPOT").click()
    await dismiss_info_dialog(page, timeout_ms=600)


async def hold_secured(page: Page, timeout_ms: int = 8000) -> bool:
    try:
        await page.wait_for_selector(
            ".orderStepContainer.step-5.active", state="attached", timeout=timeout_ms
        )
        return True
    except Exception:
        return False


async def fill_contact_info(
    page: Page, email: str, phone: str, visitor_names: list[str]
) -> None:
    active = page.locator(".orderStepContainer.active")
    await active.locator('input[placeholder="Email Address*"]').fill(email)
    await active.locator('input[placeholder="Confirm Email Address*"]').fill(email)
    await active.locator('input[placeholder="Phone*"]').fill(phone)

    name_inputs = active.locator('input[placeholder*="VISITOR"]')
    count = await name_inputs.count()
    for i in range(min(count, len(visitor_names))):
        await name_inputs.nth(i).fill(visitor_names[i])
