#!/usr/bin/env python3
"""Read-only scheduled reachability/schema heartbeat for official NFL sources.

This never downloads raw material into the public tree. It reports upstream
availability changes; a human-reviewed capture is still required to alter data.
"""
from __future__ import annotations
import csv, re, sys, urllib.request
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parent
rows=list(csv.DictReader((ROOT/'data/week11_fixtures.csv').open(encoding='utf-8')))
urls=['https://www.nfl.com/schedules/2026/by-week/week-11','https://www.nfl.com/injuries/league/2026/reg10','https://www.nfl.com/injuries/league/2026/reg11']+[r['official_game_center'] for r in rows]
ua={'User-Agent':'Mozilla/5.0 (compatible; X3-verdict-source-check/1.0)'}
fail=[]
warnings=[]
for url in urls:
    try:
        req=urllib.request.Request(url,headers=ua)
        with urllib.request.urlopen(req,timeout=20) as response:
            text=response.read(2_000_000).decode('utf-8','replace')
            if response.status != 200: fail.append(f'HTTP {response.status}: {url}')
            if 'nfl.com' not in response.url: fail.append(f'unexpected redirect: {url} -> {response.url}')
            if '/games/' in url and not re.search(r'Stadium|STADIUM|Game Info',text,re.I):
                fail.append(f'Game Center required fields absent (schema drift): {url}')
            if '/schedules/' in url and 'Week 11' not in text and 'week-11' not in text.lower():
                fail.append(f'weekly schedule marker absent (schema drift): {url}')
            if url.endswith('/reg10') and ('Injury Report' not in text or 'WEEK 10' not in text):
                fail.append(f'Week-10 injury report title/week marker absent (schema drift): {url}')
            if url.endswith('/reg11') and 'WEEK 11' not in text:
                msg='Week-11 injury endpoint still serves prior-week content; no capture was overwritten.'
                if date.today() >= date(2026, 11, 18): fail.append(msg+' Recheck is due after the Wednesday report window.')
                else: warnings.append(msg)
    except Exception as e:
        fail.append(f'{type(e).__name__}: {url}: {e}')
for warning in warnings: print('WARN — '+warning)
if fail:
    print('FAIL — official source heartbeat; no data was overwritten:')
    print('\n'.join(' - '+x for x in fail));sys.exit(1)
print(f'PASS — official NFL schedule and {len(rows)} Game Center sources are reachable and contain expected page markers; no data was overwritten.')
