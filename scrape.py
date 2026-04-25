"""HRTC Daily Rubber Board Price Scraper - v2 with correct URL + tighter parser"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone, timedelta

URL = 'https://rubberboard.gov.in/public'
PRICES_FILE = 'data/prices.json'
UA = 'Mozilla/5.0 (compatible; HRTC-bot/1.0)'

# (Aliases for each grade, plus reasonable INR/kg price range so we ignore
# random numbers like percentages or years.)
GRADES = [
    {'code': 'RSS4',   'aliases': ['RSS 4', 'RSS-4', 'RSS4'],     'lo': 100, 'hi': 500},
    {'code': 'RSS5',   'aliases': ['RSS 5', 'RSS-5', 'RSS5'],     'lo': 100, 'hi': 500},
    {'code': 'ISNR20', 'aliases': ['ISNR 20', 'ISNR-20', 'ISNR20'],'lo': 100, 'hi': 400},
    {'code': 'Latex',  'aliases': ['Latex 60', 'LATEX (60', 'Centrifuged Latex', 'Latex'], 'lo': 80, 'hi': 350},
]

def fetch_html():
    req = urllib.request.Request(URL, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode('utf-8', errors='replace')

def parse_prices(html):
    out = {}
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    for g in GRADES:
        for name in g['aliases']:
            # Look for the alias label, then within 80 chars a number in the price range
            pat = re.escape(name) + r'[^\d]{1,80}(\d{2,4}(?:\.\d+)?)'
            for m in re.finditer(pat, text, re.IGNORECASE):
                try:
                    val = float(m.group(1))
                except ValueError:
                    continue
                if g['lo'] <= val <= g['hi']:
                    out[g['code']] = val
                    break
            if g['code'] in out:
                break
    return out

def page_date(html):
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', html)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
            parsed = datetime(y, mo, d).date()
            if abs((parsed - today).days) > 7:
                return today.isoformat()  # use today if extracted date is far off
            return parsed.isoformat()
        except ValueError:
            pass
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d')

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
