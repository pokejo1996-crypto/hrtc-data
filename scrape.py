"""HRTC scraper - debug version that also saves raw HTML for inspection"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone, timedelta

URL = 'https://rubberboard.gov.in/public'
PRICES_FILE = 'data/prices.json'
DEBUG_FILE = 'data/raw_page.html'
UA = 'Mozilla/5.0 (compatible; HRTC-bot/1.0)'

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

def main():
    print(f'Fetching {URL}...')
    try:
        html = fetch_html()
    except Exception as e:
        print(f'FAILED: {e}', file=sys.stderr)
        sys.exit(1)
    print(f'Got {len(html)} bytes')

    # Save raw HTML so we can inspect it on GitHub
    os.makedirs(os.path.dirname(DEBUG_FILE), exist_ok=True)
    with open(DEBUG_FILE, 'w') as f:
        f.write(html)
    print(f'Saved raw HTML to {DEBUG_FILE}')

    # Print a snippet around each grade name so we can see what's near the prices
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    for g in GRADES:
        for name in g['aliases']:
            for m in re.finditer(re.escape(name), text, re.IGNORECASE):
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 100)
                print(f'  [{g["code"]}] near "{name}": ...{text[start:end]}...')
                break
            else:
                continue
            break

main()
