# HRTC — Hindustan Rubber Trading Co.

A self-hosted rubber trading dashboard with daily auto-updating prices.

## How it works

1. **`scrape.py`** runs once a day on GitHub's servers (via the Action in `.github/workflows/daily-scrape.yml`).
2. It fetches the Rubber Board page and saves prices to **`data/prices.json`**.
3. **`index.html`** is opened locally on your laptop. On every load it reads `data/prices.json` from this repo via the GitHub raw URL.

## Files

- `index.html` — the trading app. Open in a browser.
- `scrape.py` — daily scraper run by GitHub Action.
- `.github/workflows/daily-scrape.yml` — schedules the scraper at 18:30 IST.
- `data/prices.json` — the daily prices, committed by the Action.
- `SETUP.md` — first-time setup walkthrough.

## See also

- `SETUP.md` for the full step-by-step.
