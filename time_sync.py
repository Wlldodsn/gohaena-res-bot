import time
from dataclasses import dataclass

from playwright.async_api import Page

PROXY_METHOD_JS = """
() => new Promise((resolve, reject) => {
    jQuery.ajax({
        type: "POST",
        url: window.helperKnssGoHaenaShuttleParkingParkEntry.phpApiProxyUrl,
        cache: false,
        data: { method: "getServerDateTime" },
        success: (resp) => resolve(resp),
        error: (xhr, status, err) => reject(new Error(status + ": " + err)),
    });
})
"""


@dataclass
class ServerTimeOffset:
    offset_seconds: float
    round_trip_seconds: float

    def now(self) -> float:
        return time.time() + self.offset_seconds


async def measure_server_offset(page: Page, timezone: str = "Pacific/Honolulu") -> ServerTimeOffset:
    t0 = time.time()
    result = await page.evaluate(PROXY_METHOD_JS)
    t1 = time.time()
    rtt = t1 - t0

    server_epoch = _extract_epoch_seconds(result, timezone)
    local_at_response_midpoint = t0 + rtt / 2
    offset = server_epoch - local_at_response_midpoint
    return ServerTimeOffset(offset_seconds=offset, round_trip_seconds=rtt)


def _extract_epoch_seconds(response, timezone: str) -> float:
    import datetime as dt
    from zoneinfo import ZoneInfo

    payload = response
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict) or "year" not in payload:
        raise ValueError(f"Could not parse server time from response: {response!r}")

    moment = dt.datetime(
        payload["year"],
        payload["month"],
        payload["day"],
        payload["hour"],
        payload["minute"],
        payload["second"],
        payload.get("millisecond", 0) * 1000,
        tzinfo=ZoneInfo(timezone),
    )
    return moment.timestamp()
