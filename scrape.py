"""HRTC scraper - decodes entities, divides per-quintal prices by 100"""
import html as htmllib
import json, os, re, urllib.request
from datetime import datetime, timezone, timedelta

URL = 'https://rubberboard.gov.in/public'
PRICES_FILE = 'data/prices.json'
DEBUG_FILE = 'data/raw_page.html'
UA = 'Mozilla/5.0 (compatible; HRTC-bot/1.0)'

# The page lists prices per quintal (100 kg). We divide by 100 to get INR/kg.
GRADES = [
    {'code': 'RSS4',   'aliases': ['RSS4', 'RSS-4', 'RSS 4'],     'lo': 100, 'hi': 500},
    {'code': 'RSS5',   'aliases': ['RSS5', 'RSS-5', 'RSS 5'],     'lo': 100, 'hi': 500},
    {'code': 'ISNR20', 'aliases': ['ISNR20', 'ISNR-20', 'ISNR 20'],'lo': 100, 'hi': 400},
    {'code': 'Latex',  'aliases': ['Latex60', 'Latex-60', 'Latex 60', 'Latex60% DRC', 'Latex(60)', 'CenLatex'], 'lo': 80, 'hi': 350},
]

os.makedirs('data', exist_ok=True)

try:
    req = urllib.request.Request(URL, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    print(f'Got {len(html)} bytes from {URL}')
except Exception as e:
    print(f'FETCH FAILED: {e}')
    html = f'<!-- fetch failed: {e} -->'

with open(DEBUG_FILE, 'w') as f:
    f.write(html)

# Strip tags, decode entities, collapse whitespace
text = re.sub(r'<[^>]+>', ' ', html)
text = htmllib.unescape(text)               # &nbsp;, &#160; -> real spaces
text = re.sub(r'[\s\u00a0]+', ' ', text)    # collapse all whitespace types

# Restrict to the price section (after "Category" word) to avoid false matches
m = re.search(r'Category\s*INR.*?USD', text, re.IGNORECASE)
section = text[m.start():m.start()+3000] if m else text

found = {}
for g in GRADES:
    for name in g['aliases']:
        pat = re.escape(name) + r'\s+([\d,]+\.?\d*)'
        for hit in re.finditer(pat, section, re.IGNORECASE):
            try:
                raw = float(hit.group(1).replace(',', ''))
            except ValueError:
                continue
            # If it's a per-quintal price (typical 8000-50000), divide by 100
            v = raw / 100 if raw > 1000 else raw
            if g['lo'] <= v <= g['hi']:
                found[g['code']] = round(v, 2)
                break
        if g['code'] in found:
            break

# Page date
ist = timezone(timedelta(hours=5, minutes=30))
m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', text)
if m:
    try:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        page_date = datetime(y, mo, d).date().isoformat()
        # If far from today, use today
        today = datetime.now(ist).date()
        if abs((datetime(y, mo, d).date() - today).days) > 7:
            page_date = today.isoformat()
    except ValueError:
        page_date = datetime.now(ist).strftime('%Y-%m-%d')
else:
    page_date = datetime.now(ist).strftime('%Y-%m-%d')

print(f'Date: {page_date}')
print(f'Found: {found}')

# Save
prices = {}
if os.path.exists(PRICES_FILE):
    try:
        prices = json.load(open(PRICES_FILE))
    except Exception:
        prices = {}
prices.setdefault('days', {})
if found:
    prices['days'].setdefault(page_date, {}).update(found)
prices['last_update'] = datetime.now(timezone.utc).isoformat()
prices['source'] = URL
with open(PRICES_FILE, 'w') as f:
    json.dump(prices, f, indent=2, sort_keys=True)
print(f'Saved. Total days in file: {len(prices["days"])}')
