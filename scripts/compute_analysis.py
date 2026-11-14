#!/usr/bin/env python3
"""Analysis pass - computes only what the verified data supports.

Outputs docs/data/correlation.json (pilot correlation values with n shown)
and docs/data/luck.json (Pythagorean expected wins vs actual, i.e. a luck /
regression signal). Every number here is computed from the cited data files;
nothing is estimated or filled in.

Pilot correlations use n=15 Week-9 games + the Week-10 TNF final (n=16) from
docs/data/week9.json. Production-grade correlation values require play-by-play
data that is not available in this repo yet (flag F-08).
"""
import json, math, os

BASE = os.path.join(os.path.dirname(__file__), '..', 'x3lab', 'data')

def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return round(sxy / math.sqrt(sxx * syy), 3)

def main():
    wk9 = json.load(open(os.path.join(BASE, 'week9.json')))
    st = json.load(open(os.path.join(BASE, 'standings.json')))

    games = wk9['games'] + wk9.get('games_week10_played', [])
    totals = [g['away_score'] + g['home_score'] for g in games]
    margins = [abs(g['away_score'] - g['home_score']) for g in games]
    away_s = [g['away_score'] for g in games]
    home_s = [g['home_score'] for g in games]
    n = len(games)

    corr = {
        'description': 'Correlation values computed from verified game scores only. PILOT sample - NOT decision-grade (validation gate G-2 requires n>=200 games per market type).',
        'generated_by': 'scripts/compute_analysis.py',
        'source': 'https://www.nfl.com/schedules/2026/by-week/week-9',
        'source_class': 'official',
        'sample': f'n={n} games (Week 9 + Week-10 TNF final)',
        'values': [
            {'pair': 'game_total vs abs_margin', 'r': pearson(totals, margins), 'n': n,
             'reading': 'positive r would mean higher-scoring games also tend to be more lopsided in this sample'},
            {'pair': 'away_score vs home_score', 'r': pearson(away_s, home_s), 'n': n,
             'reading': 'game-level scoring correlation relevant for same-game parlay leg selection'},
        ],
        'policy_thresholds': {
            'parlay_leg_pair_max_abs_r': 0.3,
            'note': 'legs with |r| >= 0.3 may not be combined in a parlay under strategy policy S-PARLAY-1 until a validated correlation matrix exists',
        },
        'missing_for_production': [
            'play-by-play data (player props, drive outcomes)',
            'multi-season game logs (n>=200 per market type)',
            'closing lines with timestamps (CLV and correlation at close)',
        ],
        'flag': 'F-08',
    }
    with open(os.path.join(BASE, 'correlation.json'), 'w') as f:
        json.dump(corr, f, indent=2)

    teams = []
    for t in st['teams']:
        g = t['w'] + t['l'] + t['t']
        py = (t['pf'] ** 2.37) / (t['pf'] ** 2.37 + t['pa'] ** 2.37)
        exp_w = py * g
        teams.append({
            'team': t['team'], 'w': t['w'], 'g': g,
            'pythag_pct': round(py, 3),
            'expected_wins': round(exp_w, 2),
            'luck_delta': round(t['w'] - exp_w, 2),
            'source': t['source'],
        })
    pf = [t['pf'] for t in st['teams']]
    pa = [t['pa'] for t in st['teams']]
    luck = {
        'description': 'Pythagorean expectation (exponent 2.37 - conventional parameter, not fitted to 2026 data) vs actual wins. luck_delta > 0 = won more games than scoring margin implies (regression candidate). This is a SIGNAL definition, not a betting recommendation - see validation gates.',
        'generated_by': 'scripts/compute_analysis.py',
        'source': 'https://www.nfl.com/standings/league/2026/REG',
        'source_class': 'official (inputs); model output (derived columns)',
        'league_pf_pa_correlation': pearson(pf, pa),
        'teams': sorted(teams, key=lambda x: -x['luck_delta']),
    }
    with open(os.path.join(BASE, 'luck.json'), 'w') as f:
        json.dump(luck, f, indent=2)

    print('correlation.json + luck.json written; n =', n)

if __name__ == '__main__':
    main()
