# gohaena-res-bot

A bot that helps you grab a reservation at [Hāʻena State Park](https://gohaena.com) (Kauaʻi) the moment one opens up.

Hāʻena releases new reservation dates **30 days in advance, at 12:00 AM HST**, and the Parking + Entry Pass in particular is described by the site itself as "very limited availability" — it routinely sells out within seconds to minutes of release. This bot automates the booking flow so it can act the instant a date unlocks, instead of relying on manually refreshing the page at midnight.

## How it works

gohaena.com's booking flow is a JavaScript widget (from a ticketing vendor called SmartStubs) that's gated by Google reCAPTCHA v3 at nearly every step. A reCAPTCHA v3 token can only be produced by Google's real script running in a real browser on the real page — it can't be faked with plain HTTP requests. So instead of hitting the site's API directly, this bot drives an actual Chromium browser (via [Playwright](https://playwright.dev)) through the real page, the same way a person would, just automated and precisely timed.

The booking flow itself is a "hold, then pay" model: clicking **Reserve Your Spot** creates a temporary hold on the slot (about a 15-minute window, based on testing) *before* any payment info is collected. This bot's job ends at securing that hold — it deliberately does **not** enter or store any payment information. Once a hold is secured, it sends a desktop notification and brings the browser window to the front so you can complete payment yourself within the hold window.

```
Prewarm (load page, set party size)
   -> Wait until the exact release moment (server-time-synced, not local clock)
   -> Reload the page (the site's date picker computes its bookable range once
      at page load, so a page left open since before the release won't see
      the new date unlock without a fresh load)
   -> Select date -> check availability -> pick the target pass/date cell
      -> pick a time slot -> click Reserve Your Spot
   -> On success: notify you + bring browser to front + autofill contact info
      -> you complete payment manually
```

## Setup

Requires Python 3.11+.

```bash
git clone https://github.com/Wlldodsn/gohaena-res-bot.git
cd gohaena-res-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp config.env.example config.env
# edit config.env with your target date, party size, and contact info
```

## Usage

Run it before the release time and it will wait on its own until the exact moment, then act:

```bash
python -u main.py
```

(`-u` keeps Python's stdout unbuffered so you see progress in real time.)

Keep the machine awake and connected — on macOS, `caffeinate -d` in another terminal tab prevents sleep for the duration.

### Flags

| Flag | Purpose |
|---|---|
| `--dry-run` | Run the full flow but stop right before clicking "Reserve Your Spot" — no hold is created. |
| `--skip-wait` | Run immediately instead of waiting for the release time. Useful for testing against dates that are already open. |
| `--date YYYY-MM-DD` | Override the target date from `config.env`, e.g. for testing against currently-open inventory. |
| `--service-type` | Override which pass type to target (`parking_and_park_entry`, `shuttle`, `shuttle_princeville`, `park_entry`). Defaults to Parking + Entry. |
| `--slot` | Override the time-slot text to select (e.g. `"Afternoon"`, `"7:00 AM"`). |
| `--headless` | Run without a visible browser window. Not recommended for the real attempt — you want to see and be ready to act on the hold. |

**Example — test the mechanics against real, currently-open Shuttle inventory** (creates a real ~15-minute hold, so let it expire or complete it intentionally, but never enter payment info you don't mean to use):

```bash
python -u main.py --skip-wait --service-type shuttle --date 2026-08-15
```

## Configuration (`config.env`)

| Variable | Meaning |
|---|---|
| `TARGET_DATE` | The reservation date you want. |
| `TIME_SLOT` | Which slot to select once a pass/date is available (e.g. `Afternoon`). |
| `PARTY_SIZE` | Number of adults. |
| `VISITOR_*` | Name, email, and phone used to fill the contact step. |
| `RELEASE_TIMEZONE` / `RELEASE_DAYS_BEFORE` / `RELEASE_TIME` | When the target date actually unlocks — as of this writing, `Pacific/Honolulu`, `30` days out, at `00:00:00`. Adjust if the park's release policy changes. |
| `MAX_RETRY_ATTEMPTS` / `RETRY_WINDOW_SECONDS` | How hard to retry if the first attempt doesn't land (e.g. a slow reCAPTCHA round-trip or a sold-out response). |
| `HEADLESS` | Run without a visible window. |
| `DRY_RUN` | Default dry-run behavior (can be overridden per-run with `--dry-run`). |

## Known limitations

- **reCAPTCHA v3 is score-based, not a guarantee.** Automated behavior at the exact release moment could plausibly score differently than an organic user. The bot mitigates this by warming up the real page for several minutes beforehand and interacting at human-plausible speed, but there's no way to guarantee a favorable score.
- **No payment automation, by design.** This avoids ever storing or transmitting card details, and avoids the added complexity/fragility of automating a payment form. You complete checkout yourself within the hold window.
- **This is specific to gohaena.com's current booking widget.** The DOM selectors and API shape in `wizard.py` are tied to the SmartStubs-powered widget this site uses today; if the site changes its booking flow, the selectors will need updating.
- Automating a purchase ahead of other visitors doing it manually is a real tradeoff worth being aware of. This project is intended for genuine personal/family trip planning, not resale or high-volume use.

## License

MIT — see [LICENSE](LICENSE).
