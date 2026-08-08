import asyncio
import subprocess


def send_desktop_notification(title: str, message: str) -> None:
    script = (
        f'display notification "{_escape(message)}" '
        f'with title "{_escape(title)}" sound name "Glass"'
    )
    subprocess.run(["osascript", "-e", script], check=False)


async def play_alert_sound(times: int = 5) -> None:
    for _ in range(times):
        subprocess.run(["afplay", "/System/Library/Sounds/Sosumi.aiff"], check=False)
        await asyncio.sleep(0.4)


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
