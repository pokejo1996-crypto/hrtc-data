"""
HRTC Daily Rubber Board Price Scraper
=====================================
Runs in a GitHub Action every day at 18:30 IST. Fetches rubberboard.org.in/public,
extracts daily prices for RSS4, RSS5, ISNR20, Latex, and merges them into
data/prices.json which is then committed to the repo.

The HTML app reads from this file on every load.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

URL = os.environ.get('RUBBER_BOARD_URL', 'https://rubberboard.org.in/public')
PRICES_FILE = os.environ.get('PRICES_FILE', 'data/prices.json')
USER_AGENT = 'Mozilla/5.0 (compatible; HRTC-bot/1.0; +https://github.com)'

# What the Rubber Board page calls each grade -> our internal code
ALIASES = {
    'RSS4': ['RSS 4', 'RSS-4', 'RSS4'],
    'RSS5': ['RSS 5', 'RSS-5', 'RSS5'],
    'ISNR20': ['ISNR 20', 'ISNR-20', 'ISNR20'],
    'Latex': ['LATEX 60% DRC', 'LATEX (60% DRC)', '60% LATEX', 'LATEX'],
}

def fetch_html() -> str:
    req = urllib.request.Request(URL, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8', errors='replace')

def parse_prices(html: str) -> dict:
    """For each grade, find any alias label followed within ~30 chars by a price-like number."""
    out = {}
    # Strip HTML tags for easier text matching, but keep newlines as separators
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    for code, names in ALIASES.items():
        for name in names:
            # Find any number 50-999 within 60 chars after the name
            pattern = re.escape(name) + r'[^0-9]{1,60}([0-9]{2,4}(?:\.[0-9]+)?)'
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 50 <= val <= 1000:
                        out[code] = val
                        break
                except ValueError:
                    continue
    return out

def parse_page_date(html: str) -> str:
    """Best-effort extraction of the date the page is published for. Falls back to today (IST)."""
    # Find DD/MM/YYYY or DD-MM-YYYY anywhere
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', html)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except ValueError:
            pass
    # Fallback: today in IST
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime('%Y-%m-%d')

def load_prices() -> dict:
    if not os.path.exists(PRICES_FILE):
        return {'last_update': None, 'days': {}}
    with open(PRICES_FILE) as f:
        return json.load(f)

def save_prices(prices: dict) -> None:
    os.makedirs(os.path.dirname(PRICES_FILE), exist_ok=True)
    with open(PRICES_FILE, 'w') as f:
        json.dump(prices, f, indent=2, sort_keys=True)

def main():
    print(f'Fetching {URL}...')
    try:
        html = fetch_html()
    except Exception as e:
        print(f'FAILED to fetch: {e}', file=sys.stderr)
        sys.exit(1)

    print(f'Got {len(html)} bytes of HTML')
    found = parse_prices(html)
    page_date = parse_page_date(html)
    print(f'Page date: {page_date}')
    print(f'Found {len(found)} prices: {found}')

    if not found:
        print('No prices parsed. Page format may have changed.')
        # Still write a status note so we know the run executed
        prices = load_prices()
        prices.setdefault('errors', []).append({
            'date': page_date,
            'reason': 'no prices parsed',
            'fetched_at': datetime.now(timezone.utc).isoformat(),
        })
        prices['last_update'] = datetime.now(timezone.utc).isoformat()
        save_prices(prices)
        sys.exit(0)

    prices = load_prices()
    if 'days' not in prices:
        prices['days'] = {}
    if page_date not in prices['days']:
        prices['days'][page_date] = {}
    prices['days'][page_date].update(found)
    prices['last_update'] = datetime.now(timezone.utc).isoformat()
    prices['source'] = URL
    save_prices(prices)
    print(f'Saved to {PRICES_FILE}')
    print(f'Total days in file: {len(prices["days"])}')

if __name__ == '__main__':
    main()
