import argparse
import asyncio
import datetime as dt
import sys
from zoneinfo import ZoneInfo

from browser import launch_context, open_booking_widget
from config import settings
import notify
import time_sync
import wizard

def compute_drop_datetime(
    target_date: dt.date, release_time: dt.time, timezone: str, days_before: int
) -> dt.datetime:
    release_date = target_date - dt.timedelta(days=days_before)
    return dt.datetime.combine(release_date, release_time, tzinfo=ZoneInfo(timezone))


async def wait_until(target_epoch: float, offset: time_sync.ServerTimeOffset) -> None:
    while True:
        remaining = target_epoch - offset.now()
        if remaining <= 0:
            return
        await asyncio.sleep(min(remaining, 5 if remaining > 10 else 0.05))


async def attempt_reservation(
    page, target_date: dt.date, slot: str, dry_run: bool, service_type: str
) -> bool:
    await wizard.select_date(page, target_date)
    await wizard.click_check_availability(page)

    available = await wizard.wait_for_slot_available(
        page, target_date, timeout_seconds=25, service_type=service_type
    )
    if not available:
        return False

    await wizard.select_grid_tile(page, target_date, service_type=service_type)

    if dry_run:
        print("[dry-run] Reached step 4 (Choose Options). Stopping before RESERVE YOUR SPOT.")
        return True

    await wizard.choose_time_slot_and_reserve(page, slot)
    return await wizard.hold_secured(page)


async def run(args: argparse.Namespace) -> None:
    target_date = (
        dt.date.fromisoformat(args.date) if args.date else settings.target_date
    )
    dry_run = args.dry_run or settings.dry_run
    slot = args.slot or settings.time_slot

    print(f"Target date: {target_date}, slot: {slot}, dry_run: {dry_run}")

    context, page = await launch_context(headless=args.headless or settings.headless)
    await open_booking_widget(page)
    await wizard.set_party_size(page, settings.party_size)

    offset = await time_sync.measure_server_offset(page, timezone=settings.release_timezone)
    print(
        f"Server offset: {offset.offset_seconds:+.3f}s (RTT {offset.round_trip_seconds*1000:.0f}ms)"
    )

    if not args.skip_wait:
        drop_dt = compute_drop_datetime(
            target_date,
            settings.release_time,
            settings.release_timezone,
            settings.release_days_before,
        )
        print(f"Waiting until {drop_dt.isoformat()} ({drop_dt.astimezone(dt.timezone.utc)} UTC)")

        while drop_dt.timestamp() - offset.now() > 90:
            await asyncio.sleep(30)

        offset = await time_sync.measure_server_offset(page, timezone=settings.release_timezone)
        print(
            f"Re-synced offset near T-0: {offset.offset_seconds:+.3f}s "
            f"(RTT {offset.round_trip_seconds*1000:.0f}ms)"
        )
        await wait_until(drop_dt.timestamp(), offset)
        print("T-0 reached, reloading page so it picks up the new day's date boundary...")
        # The datepicker's min/max bookable range is computed once at page load and
        # doesn't update just because wall-clock time crosses midnight on a page left
        # open for hours -- a fresh load is required for the new date to unlock.
        await open_booking_widget(page)
        await wizard.set_party_size(page, settings.party_size)
        print("Reload complete, executing...")

    success = False
    attempts = 0
    deadline = asyncio.get_event_loop().time() + settings.retry_window_seconds
    while attempts < settings.max_retry_attempts and asyncio.get_event_loop().time() < deadline:
        attempts += 1
        print(f"Attempt {attempts}...")
        try:
            success = await attempt_reservation(
                page, target_date, slot, dry_run, args.service_type
            )
        except Exception as e:
            print(f"Attempt {attempts} error: {e}")
            success = False
        if success:
            break
        await asyncio.sleep(1)

    if success and not dry_run:
        notify.send_desktop_notification(
            "Hāʻena hold secured!", f"{target_date} {slot} — complete payment now"
        )
        await notify.play_alert_sound()
        await page.bring_to_front()
        try:
            await wizard.fill_contact_info(
                page,
                settings.visitor_email,
                settings.visitor_phone,
                [f"{settings.visitor_first_name} {settings.visitor_last_name}"],
            )
        except Exception as e:
            print(f"Contact autofill failed (fill it manually): {e}")
        print("HOLD SECURED. Complete payment in the browser window now.")
    elif success and dry_run:
        print("Dry run completed successfully.")
    else:
        notify.send_desktop_notification(
            "Hāʻena reservation failed", f"No availability secured for {target_date}"
        )
        print("Failed to secure a reservation.")

    print("Leaving browser open. Press Ctrl+C to exit.")
    while True:
        await asyncio.sleep(3600)


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--date", help="Override target date (YYYY-MM-DD), for rehearsal")
    parser.add_argument(
        "--skip-wait", action="store_true", help="Run immediately, don't wait for T-0"
    )
    parser.add_argument(
        "--service-type",
        default=wizard.SERVICE_TYPE_PARKING,
        help="Override grid service type, e.g. 'shuttle' for rehearsal against open inventory",
    )
    parser.add_argument("--slot", help="Override time slot text to select, e.g. '7:00 AM'")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
