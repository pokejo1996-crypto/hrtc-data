"""HRTC Daily Rubber Board Price Scraper"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone, timedelta

URL = 'https://rubberboard.org.in/public'
PRICES_FILE = 'data/prices.json'
UA = 'Mozilla/5.0 (compatible; HRTC-bot/1.0)'

ALIASES = {
    'RSS4': ['RSS 4', 'RSS-4', 'RSS4'],
    'RSS5': ['RSS 5', 'RSS-5', 'RSS5'],
    'ISNR20': ['ISNR 20', 'ISNR-20', 'ISNR20'],
    'Latex': ['LATEX 60% DRC', 'LATEX (60% DRC)', '60% LATEX', 'LATEX'],
}

def fetch_html():
    req = urllib.request.Request(URL, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8', errors='replace')

def parse_prices(html):
    out = {}
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    for code, names in ALIASES.items():
        for name in names:
            pat = re.escape(name) + r'[^0-9]{1,60}([0-9]{2,4}(?:\.[0-9]+)?)'
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                try:
                    val = float(m.group(1))
                    if 50 <= val <= 1000:
                        out[code] = val
                        break
                except ValueError:
                    pass
    return out

def page_date(html):
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', html)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f'{y:04d}-{mo:02d}-{d:02d}'
        except ValueError:
            pass
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime('%Y-%m-%d')

def load_prices():
    if not os.path.exists(PRICES_FILE):
        return {'last_update': None, 'days': {}}
    with open(PRICES_FILE) as f:
        return json.load(f)

def save_prices(d):
    os.makedirs(os.path.dirname(PRICES_FILE), exist_ok=True)
    with open(PRICES_FILE, 'w') as f:
        json.dump(d, f, indent=2, sort_keys=True)

def main():
    print(f'Fetching {URL}...')
    try:
        html = fetch_html()
    except Exception as e:
        print(f'FAILED: {e}', file=sys.stderr)
        sys.exit(1)
    print(f'Got {len(html)} bytes')
    found = parse_prices(html)
    pd = page_date(html)
    print(f'Date: {pd}, Found: {found}')
    prices = load_prices()
    prices.setdefault('days', {})
    if found:
        prices['days'].setdefault(pd, {}).update(found)
    prices['last_update'] = datetime.now(timezone.utc).isoformat()
    prices['source'] = URL
    save_prices(prices)
    print(f'Saved. Total days: {len(prices["days"])}')

main()
