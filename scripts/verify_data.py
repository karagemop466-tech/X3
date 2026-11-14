#!/usr/bin/env python3
"""verify_data.py - line-by-line verification gate.

Enforces the repository's core integrity rules:
  1. Every fact-table row carries a source URL (row-level, or file-level default),
     or is explicitly marked unverified.
  2. Structural invariants of the verified data hold (32 teams, records reconcile,
     PF-PA == diff, game counts, injury row shape).
  3. Every file the site fetches exists; every HTML page links the shared assets.

Run: python3 scripts/verify_data.py   (exit code 0 = all checks pass)
"""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
DATA = os.path.join(ROOT, 'docs', 'data')
DOC = os.path.join(ROOT, 'docs')
fails = []
checks = 0

def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)

def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)

def row_source_ok(row, file_src):
    if row.get('unverified') is True:
        return True
    if isinstance(row.get('source'), str) and row['source'].strip():
        return True
    return bool(isinstance(file_src, str) and file_src.strip())

# Per-table exemptions for rows that are source-lists or review flags themselves:
#   sources.json  - each row IS a source; it must carry a non-empty 'url'
#   flagged.json  - each row is a review flag; a null source is allowed only with
#                   status 'needs review' (e.g. legal questions with no URL)

# ---------- 1. JSON validity + row/source audit ----------
FACT_TABLES = {
    'standings.json': ['teams'],
    'week9.json': ['games', 'games_week10_played'],
    'week10.json': ['games'],
    'odds_week10.json': ['games'],
    'odds_week11.json': ['games', 'super_bowl_futures'],
    'injuries.json': ['game_day', 'season_impact'],
    'deficiencies.json': ['rows'],
    'luck.json': ['teams'],
    'lines_week10.json': ['games'],
    'correlation.json': ['values'],
    'flagged.json': ['rows'],
    'sources.json': ['sources'],
    'strategies.json': ['signals', 'strategies'],
    'questions.json': ['answered', 'open'],
    'suggestions.json': ['suggestions'],
}
files = sorted(os.listdir(DATA))
for fn in files:
    if not fn.endswith('.json'):
        continue
    try:
        d = load(fn)
    except Exception as e:
        check(False, f'{fn}: invalid JSON ({e})')
        continue
    file_src = d.get('source')
    for key in FACT_TABLES.get(fn, []):
        rows = d.get(key, [])
        check(isinstance(rows, list) and rows, f'{fn}:{key}: missing or empty')
        for i, row in enumerate(rows):
            if fn == 'sources.json':
                ok = bool(str(row.get('url', '')).strip())
            elif fn == 'flagged.json':
                ok = row_source_ok(row, None) or row.get('status') == 'needs review'
            else:
                ok = row_source_ok(row, file_src)
            check(ok, f'{fn}:{key}[{i}]: no source link and not marked unverified')
    if fn == 'depth.json':
        for team, chart in d.get('teams', {}).items():
            check(bool(str(chart.get('source', '')).strip()), f'depth.json:{team}: missing chart source')
            for grp in ('offense', 'defense'):
                for i, row in enumerate(chart.get(grp, [])):
                    check(bool(row.get('pos')) and bool(row.get('s1')),
                          f'depth.json:{team}:{grp}[{i}]: malformed chart row')

# ---------- 2. Structural invariants ----------
st = load('standings.json')
check(len(st['teams']) == 32, 'standings.json: expected 32 teams')
wsum = lsum = tsum = pfsum = pasum = 0
for t in st['teams']:
    wsum += t['w']; lsum += t['l']; tsum += t['t']
    pfsum += t['pf']; pasum += t['pa']
    check(t['pf'] - t['pa'] == t['diff'], f"standings {t['team']}: PF-PA != diff")
    g = t['w'] + t['l'] + t['t']
    hg = sum(map(int, t['home'].split('-')))
    rg = sum(map(int, t['road'].split('-')))
    check(hg + rg == g, f"standings {t['team']}: home+road != total games")
    div_g = sum(map(int, t['div'].split('-')))
    conf_g = sum(map(int, t['conf'].split('-')))
    nc_g = sum(map(int, t['non_conf'].split('-')))
    check(conf_g + nc_g == g,
          f"standings {t['team']}: conf + non_conf != total games (F-02 mapping)")
    check(div_g <= conf_g,
          f"standings {t['team']}: div games exceed conf games")
check(wsum == lsum, 'standings: league wins != league losses')
check(pfsum == pasum, 'standings: league PF != league PA')
total_team_games = wsum + lsum + tsum
check(total_team_games % 2 == 0, 'standings: team-game total must be even')
check(250 <= total_team_games <= 290,
      f'standings: team-game total {total_team_games} out of plausible range for Weeks 1-9 + TNF')

wk9 = load('week9.json')
check(len(wk9['games']) == 15, 'week9.json: expected 15 games')
for g in wk9['games'] + wk9['games_week10_played']:
    check(isinstance(g['away_score'], int) and isinstance(g['home_score'], int),
          'week9.json: non-integer score')
    check(g['away_score'] != g['home_score'], 'week9.json: tie score needs explicit handling')

w10 = load('week10.json')
check(len(w10['games']) == 14, 'week10.json: expected 14 games (incl. played TNF)')
check(len(w10['byes_week10']) == 4, 'week10.json: expected 4 bye teams')

o10 = load('odds_week10.json')
check(len(o10['games']) == 13, 'odds_week10.json: expected 13 games')
for g in o10['games']:
    check(round(g['spread_away'], 1) == -round(g['spread_home'], 1),
          f"odds_week10 {g['away']}@{g['home']}: spreads not mirrored")
    check(g['total'] > 30 and g['total'] < 70, f"odds_week10 {g['away']}@{g['home']}: total out of range")

o11 = load('odds_week11.json')
check(len(o11['games']) == 13, 'odds_week11.json: expected 13 games')

inj = load('injuries.json')
check(len(inj['game_day']) >= 150, 'injuries.json: game_day table suspiciously small')
for r in inj['game_day'] + inj['season_impact']:
    for k in ('t', 'n', 'p', 's'):
        check(bool(r.get(k)), f"injuries row missing '{k}': {r}")
    check(r['s'] in ('Out', 'Doubtful', 'Questionable', 'Injured Reserve', 'Starter per report'),
          f"injuries row unexpected status: {r['s']}")

lines = load('lines_week10.json')
check(len(lines['games']) == 13, 'lines_week10.json: expected 13 model lines')
for g in lines['games']:
    check('model_inputs_source' in g and g['model_inputs_source'], 'lines row missing model source')
    check(abs(g['our_spread_away'] % 0.5) < 1e-9, 'lines row: spread not on half-point')

luck = load('luck.json')
check(len(luck['teams']) == 32, 'luck.json: expected 32 teams')

# ---------- 3. Site wiring ----------
expected_pages = ['index.html', 'executive-summary.html', 'requirements.html', 'lines.html',
                  'injuries.html', 'depth.html', 'strategies.html', 'leaderboard.html',
                  'questions.html', 'suggestions.html', 'results.html', 'flagged.html', 'sources.html']
for p in expected_pages:
    path = os.path.join(DOC, p)
    check(os.path.exists(path), f'missing page {p}')
    if not os.path.exists(path):
        continue
    html = open(path).read()
    check('styles.css' in html, f'{p}: missing stylesheet link')
    check('app.js' in html, f'{p}: missing app.js link')
    for m in re.findall(r"loadJSON\('([^']+)'\)", html):
        check(os.path.exists(os.path.join(DOC, m)), f'{p}: fetch target missing: {m}')
    for m in re.findall(r'href="([^"#:]+\.html)"', html):
        check(os.path.exists(os.path.join(DOC, m)), f'{p}: broken internal link {m}')

# ---------- summary ----------
print(f'checks run: {checks}')
if fails:
    print(f'FAIL ({len(fails)}):')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print('PASS: every fact-table row has a source or is explicitly unverified; invariants hold; site wiring intact.')
