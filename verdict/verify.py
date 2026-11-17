#!/usr/bin/env python3
"""Structural/source-integrity checks for the read-only verdict desk."""
from __future__ import annotations
import csv, re, hashlib, json
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'

def rows(name):
    with (DATA/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def require(test,message):
    if not test: raise SystemExit('FAIL: '+message)

fixtures=rows('week11_fixtures.csv')
results=rows('week10_reconciliation.csv')
markets=rows('origination_w11.csv')
reqs=rows('requirements_register.csv')
availability=rows('designation_playrate.csv')
require(len(fixtures)==13,'expected 13 Week-11 official fixtures')
require(len({r['away']+'@'+r['home'] for r in fixtures})==13,'duplicate Week-11 matchup')
require(all(r['status']=='SCHEDULED' for r in fixtures),'unexpected Week-11 fixture status')
require(all(r['official_game_center'].startswith('https://www.nfl.com/games/') for r in fixtures),'fixture missing direct NFL Game Center source')
require(len(results)==14,'expected 14 Week-10 official finals')
require(sum(r['x3_feed_reconciliation']!='MATCH' for r in results)==12,'expected exactly 12 Week-10 games absent from x3 result feed')
require(sum(r['verified_feed_status']=='SCHEDULED' for r in results)==13,'verified feed should show 13 stale Week-10 scheduled rows including NE@DET')
require(len(markets)==39,'expected side/total/moneyline rows for all 13 Week-11 games')
artifact=ROOT.parent/'data/x3/verified/markets.json'
artifact_hash=hashlib.sha256(artifact.read_bytes()).hexdigest()
model_doc=json.loads(artifact.read_text(encoding='utf-8'))
live={f"{g['away']}@{g['home']}":g for g in model_doc['live'] if int(g['week'])==11}
require(all(r['model_artifact_sha256']==artifact_hash for r in markets),'model artifact hash mismatch')
require({r['game'] for r in markets}=={r['away']+'@'+r['home'] for r in fixtures}==set(live),'origination games do not match the official Week-11 slate and saved model')
for i,r in enumerate(markets,1):
    require(int(r['seq'])==i,'origination sequence is not contiguous')
    require(r['market_type']==('side','total','moneyline')[(i-1)%3],'market order must be side, total, moneyline')
    require(bool(r['fair_line']) and bool(r['probability']),'saved X3-v2 fair output/probability is absent')
    require(not r['market_line'].strip() and not r['difference'].strip() and not r['market_source'].strip(),'unverified external market data was populated')
    require('DERIVED' in r['status'] and 'UNVERIFIED' in r['pre_registration'] and 'UNVERIFIED' in r['status'] and r['official_source'].startswith('https://www.nfl.com/'),'model output lacks derivation/preregistration/market-gap disclosure or official fixture source')
    g=live[r['game']]
    if r['market_type']=='side': expected=float(g['side_fair_line']); expected_p=float(g['side_cover_prob_home'])
    elif r['market_type']=='total': expected=float(g['total_fair_line']); expected_p=float(g['total_over_prob'])
    else:
        expected=f"home {g['ml_fair_american_home']:+d} / away {g['ml_fair_american_away']:+d}"
        expected_p=float(g['ml_home_prob'])
    if r['market_type']=='moneyline': require(r['fair_line']==expected,'moneyline fair odds do not match saved model artifact')
    else: require(abs(float(r['fair_line'])-expected)<1e-9,'fair line does not match saved model artifact')
    require(abs(float(r['probability'])-expected_p)<1e-9,'model probability does not match saved model artifact')
require(len(reqs)==69,'expected verbatim 69-row repo requirements register')
require(len(availability)==1,'expected one explicitly limited availability pilot row')
a=availability[0]
require((int(a['report_rows']),int(a['gamebook_played_confirmed']),int(a['gamebook_not_active']),int(a['participation_unresolved']))==(11,8,2,1),'availability pilot counts changed')
require(a['play_rate_among_resolved']=='0.800' and a['injury_report_source'].startswith('https://www.nfl.com/') and a['game_book_source'].startswith('https://static.www.nfl.com/'),'availability pilot missing official sources or rate')

for p in DATA.glob('*.csv'):
    data=rows(p.name)
    require(bool(data),f'{p.name} is empty')
    source_cols=[c for c in data[0] if 'source' in c or c in ('official_game_center','official_schedule')]
    require(bool(source_cols),f'{p.name} has no source column')
    for n,r in enumerate(data,1):
        has_url=any(re.match(r'https?://',r.get(c,'')) for c in source_cols)
        explicit_flag=any(token in str(v).upper() for v in r.values() for token in ('UNVERIFIED','BLOCKED','FLAG:','CROSS-SCOPE REQUEST'))
        require(has_url or explicit_flag,f'{p.name} row {n} lacks a source link or explicit flag')

class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,t,attrs):
        for k,v in attrs:
            if k=='href':self.hrefs.append(v)
for page in ROOT.glob('*.html'):
    parser=Links();parser.feed(page.read_text(encoding='utf-8'))
    for href in parser.hrefs:
        if href.startswith(('http://','https://','#','mailto:','javascript:','data:','tel:')):continue
        target=(page.parent/href.split('#',1)[0].split('?',1)[0])
        require(target.exists(),f'{page.name} has broken local link {href}')
print(f'PASS — {len(fixtures)} Week-11 fixtures; {len(results)} W10 finals (12 x3-feed omissions, 13 verified-feed scheduled); {len(availability)} limited designation pilot; {len(markets)} ordered fair outputs (market quotes left blank); {len(reqs)} requirement rows; CSV citations and local links checked.')
