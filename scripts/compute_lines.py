#!/usr/bin/env python3
"""Line origination model v0.1 - reproducible, deterministic.

Inputs:  docs/data/standings.json (NFL.com official, fetched 2026-11-14)
         docs/data/week10.json    (official schedule)
         docs/data/odds_week10.json (market comparison only)
Output:  docs/data/lines_week10.json

METHOD (documented in analysis/line-origination.md):
  margin_rating(team) = (PF - PA) / games_played          [season scoring margin, raw]
  spread_away         = margin_rating(away) - margin_rating(home) - HFA
  total               = 0.5 * ((PF+PA)/G_home + (PF+PA)/G_away)/1 ... see below
  totals are shrunk 50% toward the league mean total (no pace data available).

ASSUMPTIONS (flagged, NOT verified):
  A-01 HFA = 2.0 points (league-average home field advantage)
  A-02 Neutral-site games: HFA = 0.0 (Munich game)
  A-03 Totals heuristic: 50/50 shrink to league mean (no play-by-play/pace feed)

The script never invents values: every input comes from the data files above and
every output row carries a source link. Model outputs are labeled as model output.
"""
import json, os

BASE = os.path.join(os.path.dirname(__file__), '..', 'docs', 'data')

HFA = 2.0            # A-01 (assumption)
NEUTRAL_HFA = 0.0    # A-02 (assumption)
TOTAL_SHRINK = 0.5   # A-03 (assumption)

def rnd(x):
    # round to nearest 0.5, half-up
    import math
    return math.floor(x * 2 + 0.5) / 2

def main():
    st = json.load(open(os.path.join(BASE, 'standings.json')))
    wk10 = json.load(open(os.path.join(BASE, 'week10.json')))
    odds = json.load(open(os.path.join(BASE, 'odds_week10.json')))

    teams = {}
    total_games = 0
    total_pf = 0
    for t in st['teams']:
        g = t['w'] + t['l'] + t['t']
        teams[t['team']] = {
            'g': g,
            'margin_rating': (t['pf'] - t['pa']) / g,
            'total_rate': (t['pf'] + t['pa']) / g,
            'pythag': (t['pf'] ** 2.37) / (t['pf'] ** 2.37 + t['pa'] ** 2.37),
            'w': t['w'], 'l': t['l'], 't': t['t'],
            'pf': t['pf'], 'pa': t['pa'],
        }
        total_games += g
        total_pf += t['pf']
    league_avg_total = total_pf / (total_games / 2)  # points per game (both teams)

    odds_map = {}
    for g in odds['games']:
        odds_map[(g['away'], g['home'])] = g

    rows = []
    for g in wk10['games']:
        if g['status'] == 'FINAL':
            continue  # already played; model posts pre-game lines only
        a, h = g['away'], g['home']
        neutral = 'Munich' in (g.get('slot') or '')
        hfa = NEUTRAL_HFA if neutral else HFA
        # spread_away (market convention: favorite negative) equals the predicted
        # home margin: if home is predicted +3 (home wins by 3), away is +3 dog.
        pred_home_margin = teams[h]['margin_rating'] - teams[a]['margin_rating'] + hfa
        our_spread_away = rnd(pred_home_margin)
        raw_total = (teams[h]['total_rate'] + teams[a]['total_rate']) / 2
        our_total = rnd((1 - TOTAL_SHRINK) * raw_total + TOTAL_SHRINK * league_avg_total)

        o = odds_map.get((a, h))
        row = {
            'away': a, 'home': h, 'date': g['date'], 'time_et': g['time_et'],
            'neutral_site': neutral,
            'our_spread_away': our_spread_away,
            'our_total': our_total,
            'model_inputs_source': 'https://www.nfl.com/standings/league/2026/REG',
            'schedule_source': g['source'],
            'market_source': o['source'] if o else None,
            'source': (o['source'] if o else None) or g['source'],
            'market_spread_away': o['spread_away'] if o else None,
            'market_total': o['total'] if o else None,
            'spread_gap': rnd(our_spread_away - o['spread_away']) if o else None,
            'total_gap': rnd(our_total - o['total']) if o else None,
        }
        rows.append(row)

    out = {
        'description': 'Originated Week-10 lines from model v0.1 (model output, not market data). Spreads from away-team perspective (favorite negative). Re-run: python3 scripts/compute_lines.py',
        'generated_by': 'scripts/compute_lines.py',
        'generated_at_data_fetch': '2026-11-14',
        'assumptions': [
            {'id': 'A-01', 'value': HFA, 'text': 'Home field advantage = 2.0 points', 'verified': False, 'flag': 'F-07'},
            {'id': 'A-02', 'value': NEUTRAL_HFA, 'text': 'Neutral-site HFA = 0.0 (applied to Munich game)', 'verified': False, 'flag': 'F-07'},
            {'id': 'A-03', 'value': TOTAL_SHRINK, 'text': 'Totals shrunk 50% to league mean (no pace data)', 'verified': False, 'flag': 'F-06'},
        ],
        'league_avg_total_per_game': round(league_avg_total, 2),
        'model_class': 'unvalidated - fails validation gates until backtest + CLV tracking exist (see docs/data/validation_gates.json)',
        'games': rows,
    }
    with open(os.path.join(BASE, 'lines_week10.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print('lines_week10.json written:', len(rows), 'games; league avg total', round(league_avg_total, 2))

if __name__ == '__main__':
    main()
