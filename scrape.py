"""
HRTC Daily Rubber Board Price Scraper (v2)
==========================================
Runs in a GitHub Action every day at 18:30 IST. Fetches
indiannaturalrubber.com (the Rubber Board's own marketing arm, which
publishes same-day prices in a stable table — unlike the main public
page whose CDN serves inconsistent cached snapshots).

Extracts daily prices for RSS4, RSS5, ISNR20, Latex from the Kottayam
table (falls back to Cochin for any grade marked ~ / * / #), figures
out the "As on DD/MM/YYYY" page date, and merges them into
data/prices.json which is then committed to the repo.

The HTML app reads from this file on every load.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

URL = os.environ.get('RUBBER_BOARD_URL', 'http://www.indiannaturalrubber.com/')
PRICES_FILE = os.environ.get('PRICES_FILE', 'data/prices.json')
TIMEOUT_SEC = 25
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-IN,en;q=0.9',
    'Accept-Encoding': 'identity',   # avoid gzip; urllib doesn't auto-decode
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=BROWSER_HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
        return resp.read().decode('utf-8', errors='replace')


def parse_page_date(html: str) -> str | None:
    """Pull 'As on DD/MM/YYYY' heading (the Kottayam section's own stamp)."""
    m = re.search(r'As\s+on\s+(\d{1,2})/(\d{1,2})/(\d{4})', html, re.IGNORECASE)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{y:04d}-{mo:02d}-{d:02d}"
        except ValueError:
            pass
    return None


# Grade label patterns. \b word boundaries + the trailing digit prevent
# "Rss4Chn" (Cochin section image alt text) from matching "RSS[\s-]*4".
GRADE_PATTERNS = {
    'RSS4':   [r'\bRSS[\s-]*4\b'],
    'RSS5':   [r'\bRSS[\s-]*5\b'],
    'ISNR20': [r'\bISNR[\s-]*20\b'],
    'Latex':  [r'\bLatex\b'],
}

# Per-100kg price range: ₹5,000 - ₹60,000. Requiring 5 digits filters out
# noise like "60" from "60% DRC", "5" from "RSS-5", "20" from "ISNR-20".
PRICE_MIN = 5000
PRICE_MAX = 60000

# No-trade markers that the page uses in place of a price
NO_TRADE_RE = re.compile(r'(?:^|[>\s])([~*#])(?:$|[<\s])')


def _after(html: str, start_idx: int, window: int = 2000) -> str:
    return html[start_idx:start_idx + window]


def _parse_price_after(chunk: str):
    """From the HTML after a grade label, extract (price_per_100kg | None, no_trade_flag).

    We strip tags, then scan tokens. First we check for a no-trade marker very
    close to the start (within ~80 chars); if found, return (None, True).
    Otherwise we return the first number in the valid per-100kg range.
    """
    text = re.sub(r'<[^>]+>', ' ', chunk)
    text = re.sub(r'[\xa0\s]+', ' ', text).strip()
    # Explicit no-trade marker close to the grade label
    head = text[:80]
    if re.search(r'(^|\s)[~*#](\s|$)', head):
        # But only if there's no valid price BEFORE the marker
        m_marker = re.search(r'(^|\s)[~*#](\s|$)', head)
        pre = head[:m_marker.start()]
        if not re.search(r'\b[1-9][0-9]{3,4}(?:\.[0-9]+)?\b', pre):
            return (None, True)
    # Scan tokens left-to-right for the first valid per-100kg price
    for m in re.finditer(r'\b([1-9][0-9]{0,2}(?:,?[0-9]{3})+(?:\.[0-9]+)?|[1-9][0-9]{3,4}(?:\.[0-9]+)?)\b', text):
        try:
            val = float(m.group(1).replace(',', ''))
        except ValueError:
            continue
        if PRICE_MIN <= val <= PRICE_MAX:
            return (val, False)
    return (None, False)


def parse_prices_table(html: str):
    """Scan the whole HTML. For each grade, find its label and the next valid
    per-100kg price nearby. Simple, robust against section-boundary games."""
    out = {}
    no_trade = {}
    for grade, patterns in GRADE_PATTERNS.items():
        for pat in patterns:
            # Find ALL matches of this grade label; take the first that yields a price.
            for m in re.finditer(pat, html, re.IGNORECASE):
                price, is_no_trade = _parse_price_after(_after(html, m.end()))
                if price is not None:
                    out[grade] = price
                    break
                if is_no_trade and grade not in no_trade:
                    no_trade[grade] = True
            if grade in out:
                break
    return out, no_trade


def load_prices() -> dict:
    if not os.path.exists(PRICES_FILE):
        return {'last_update': None, 'days': {}}
    with open(PRICES_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {'last_update': None, 'days': {}}


def save_prices(prices: dict) -> None:
    os.makedirs(os.path.dirname(PRICES_FILE) or '.', exist_ok=True)
    with open(PRICES_FILE, 'w') as f:
        json.dump(prices, f, indent=2, sort_keys=True)


def main() -> int:
    print(f'Fetching {URL} ...')
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f'FAILED to fetch: {e}', file=sys.stderr)
        return 1
    print(f'Got {len(html)} bytes of HTML')

    page_date = parse_page_date(html)
    if not page_date:
        # Fallback: today's date in IST (page probably has a different stamp format)
        ist = timezone(timedelta(hours=5, minutes=30))
        page_date = datetime.now(ist).strftime('%Y-%m-%d')
        print(f'No "As on" date header found; defaulting to today IST: {page_date}')
    else:
        print(f'Page date: {page_date}')

    found, no_trade = parse_prices_table(html)
    print(f'Found: {found} (no-trade flagged: {sorted(no_trade.keys())})')

    if not found:
        print('ERROR: No prices parsed. Page format may have changed.', file=sys.stderr)
        return 2

    # Convert per-100kg → per-kg for the JSON file (that's what the app expects).
    per_kg = {g: round(v / 100.0, 2) for g, v in found.items()}
    print(f'Final prices (per kg): {per_kg}')

    prices = load_prices()
    if 'days' not in prices:
        prices['days'] = {}
    if page_date not in prices['days']:
        prices['days'][page_date] = {}
    prices['days'][page_date].update(per_kg)
    prices['last_update'] = datetime.now(timezone.utc).isoformat()
    prices['source'] = URL
    save_prices(prices)
    print(f'Saved to {PRICES_FILE}')
    print(f'Total days in file: {len(prices["days"])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
