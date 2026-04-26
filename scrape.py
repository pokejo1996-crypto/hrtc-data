"""HRTC scraper - v3 with Asian markets attempt"""
import html as htmllib
import json, os, re, urllib.request
from datetime import datetime, timezone, timedelta

UA = 'Mozilla/5.0 (compatible; HRTC-bot/1.0)'
PRICES_FILE = 'data/prices.json'
DEBUG_FILE = 'data/raw_page.html'

INDIAN_URL = 'https://rubberboard.gov.in/public'
ASIAN_FALLBACK_URLS = ['https://rubberboard.gov.in/public']

INDIAN_GRADES = [
    {'code': 'RSS4',   'aliases': ['RSS4', 'RSS-4', 'RSS 4'],     'lo': 100, 'hi': 500},
    {'code': 'RSS5',   'aliases': ['RSS5', 'RSS-5', 'RSS 5'],     'lo': 100, 'hi': 500},
    {'code': 'ISNR20', 'aliases': ['ISNR20', 'ISNR-20', 'ISNR 20'],'lo': 100, 'hi': 400},
    {'code': 'Latex',  'aliases': ['Latex60', 'Latex-60', 'Latex 60', 'Latex(60', '60% Latex', 'CenLatex', 'Centrifuged'], 'lo': 80, 'hi': 350},
]

ASIAN_GRADES = [
    {'code': 'TOCOM',   'aliases': ['TOCOM', 'OSAKA RSS3', 'Osaka Rubber', 'JPX Rubber', 'Tokyo Rubber'], 'lo': 150, 'hi': 600, 'currency': 'JPY/kg'},
    {'code': 'SICOM',   'aliases': ['SICOM', 'TSR20', 'TSR-20', 'TSR 20', 'Singapore Rubber', 'SGX Rubber'], 'lo': 100, 'hi': 400, 'currency': 'cents/kg'},
    {'code': 'BANGKOK', 'aliases': ['Bangkok', 'Thai USS3', 'USS3', 'USS 3', 'Thai Rubber', 'Thailand RSS3'], 'lo': 30, 'hi': 150, 'currency': 'THB/kg'},
]

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='replace')

def normalise(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = htmllib.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text

def parse_indian(text):
    out = {}
    for g in INDIAN_GRADES:
        for name in g['aliases']:
            pat = re.escape(name) + r'\s+([\d,]+\.?\d*)'
            for hit in re.finditer(pat, text, re.IGNORECASE):
                try:
                    raw = float(hit.group(1).replace(',', ''))
                except ValueError:
                    continue
                v = raw / 100 if raw > 1000 else raw
                if g['lo'] <= v <= g['hi']:
                    out[g['code']] = round(v, 2)
                    break
            if g['code'] in out:
                break
    return out

def parse_asian(text):
    out = {}
    for g in ASIAN_GRADES:
        for name in g['aliases']:
            pat = re.escape(name) + r'[^\d]{1,80}([\d,]+\.?\d*)'
            for hit in re.finditer(pat, text, re.IGNORECASE):
                try:
                    raw = float(hit.group(1).replace(',', ''))
                except ValueError:
                    continue
                if g['lo'] <= raw <= g['hi']:
                    out[g['code']] = {'price': round(raw, 2), 'currency': g['currency']}
                    break
            if g['code'] in out:
                break
    return out

def page_date(text):
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).date()
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            parsed = datetime(y, mo, d).date()
            if abs((parsed - today).days) <= 7:
                return parsed.isoformat()
        except ValueError:
            pass
    return today.isoformat()

os.makedirs('data', exist_ok=True)
print(f'Fetching {INDIAN_URL}...')
try:
    html = fetch(INDIAN_URL)
    print(f'Got {len(html)} bytes')
    open(DEBUG_FILE, 'w').write(html)
except Exception as e:
    print(f'FETCH FAILED: {e}')
    html = ''

text = normalise(html) if html else ''
indian = parse_indian(text)
pd = page_date(text) if text else datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%Y-%m-%d')
print(f'Indian date: {pd}, found: {indian}')

asian = {}
for url in ASIAN_FALLBACK_URLS:
    try:
        h = fetch(url) if url != INDIAN_URL else html
        if not h: continue
        t = normalise(h)
        found = parse_asian(t)
        for code, data in found.items():
            if code not in asian:
                asian[code] = data
                print(f'Asian {code} via {url}: {data}')
    except Exception as e:
        print(f'Asian fetch failed for {url}: {e}')
print(f'Asian found: {asian}')

prices = {}
if os.path.exists(PRICES_FILE):
    try:
        prices = json.load(open(PRICES_FILE))
    except Exception:
        prices = {}
prices.setdefault('days', {})
prices.setdefault('asian', {})
if indian:
    prices['days'].setdefault(pd, {}).update(indian)
if asian:
    prices['asian'][pd] = asian
prices['last_update'] = datetime.now(timezone.utc).isoformat()
prices['source'] = INDIAN_URL
with open(PRICES_FILE, 'w') as f:
    json.dump(prices, f, indent=2, sort_keys=True)
print(f'Saved. Indian days: {len(prices["days"])}, Asian days: {len(prices["asian"])}')
