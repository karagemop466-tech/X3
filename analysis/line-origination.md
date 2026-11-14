# Line origination model v0.1

Reproducible: `python3 scripts/compute_lines.py` → `x3lab/data/lines_week10.json`.
Inputs (all official, linked in `x3lab/data/sources.json`): NFL.com standings (PF/PA,
records) and the official Week-10 schedule. Market comparison via DraftKings (ESPN).

## Method

- `margin_rating(t) = (PF − PA) / games` — raw season scoring margin.
- `spread_away = margin_rating(home) − margin_rating(away) + HFA` (market convention:
  favorite negative from the away team's perspective).
- `total = 50% · mean(team game-total rates) + 50% · league mean (45.92)` — shrunk to
  the league mean because no pace/play-by-play data exists in-repo.

## Assumptions (labeled, unverified)

| ID | Value | Note |
| --- | --- | --- |
| A-01 | HFA = 2.0 pts | conventional league-average value; not fitted to 2026 |
| A-02 | neutral HFA = 0.0 | applies to Munich (NE-DET); Mexico City game in Week 11 |
| A-03 | totals shrink 50% | heuristic until a pace feed exists (F-06) |

## Known limitations (why the model is unvalidated)

1. **No injury inputs.** The LAC-BAL gap (+4.5) exists because the model prices the
   pre-Lamar-Jackson Ravens. Injury adjustment is model v0.2 work (SUG-09).
2. **No opponent adjustment.** Raw margins exaggerate team strength differences;
   JAX-TEN's −8.0 gap is mostly this.
3. **Totals are heuristic** and are the weakest output (F-06).
4. **Validation gates G-1..G-7 not passed.** Outputs are published for transparency
   and gap analysis, never as recommendations.

## How this becomes a validated origination

Walk-forward backtest on a timestamped archive (Q-03), opponent-adjusted ratings,
injury/deficiency weights from `x3lab/data/deficiencies.json`, CLV tracking (started
2026-11-14), then the G-6/G-7 bar (vig-adjusted CI, deflated Sharpe).
