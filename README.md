# X3 — NFL Decision System

A verified-data NFL decision-support dashboard: official standings, schedule and injury data,
joined to official club depth charts to surface starter-absent deficiencies, feeding a
registered strategy book with hard validation gates.

**Live site:** GitHub Pages, built from the `site/` directory by
`.github/workflows/pages.yml`.

## Verification rule

Every row in a data table carries a link to the official source it was read from. A value that
could not be confirmed from an official source is left **blank**, marked `UNVERIFIED`, and
mirrored to the Flagged for Review page. Nothing is inferred. Model output is always labelled
`DERIVED` and shows its parameters.

Official means NFL.com and NFL club sites. Sports media and statistics aggregators are
secondary and never back a fact row.

## Layout

```
tools/nfl_data.py     Verified data, transcribed from official pages. The only source of fact.
tools/site_content.py Requirements, questions, suggestions, strategies, gates, leaderboard spec.
tools/build_site.py   Derives the joins and correlations, emits site/data/*.json and site/*.html.
site/                 Built site. Deployed by GitHub Pages.
COORDINATION.md       Shared task board for parallel agent sessions.
```

## Rebuild

```bash
python3 tools/build_site.py
```

Output goes to `site/`. The build is deterministic: it reads only `tools/nfl_data.py` and
`tools/site_content.py`.

## Pages

| Page | What it holds |
|---|---|
| Overview | Executive summary, KPI cards, Week 10 model board, blocking questions |
| Executive Summary | The important findings with source links |
| Standings | Official 2026 league standings, 32 clubs |
| Schedule | Official Week 10 schedule and bye week |
| Injuries | Official Week 10 injury report, 345 rows |
| Depth & Deficiencies | Depth-chart register plus the starter-absent join |
| Own Lines | Rating-derived spreads and totals, with parameters shown |
| Strategies | Ten registered strategies across singles, parlays, prop combos |
| Validation Gates | Twelve blocking gates and per-strategy state |
| Correlation | Computed correlations and the ones still unestimated |
| Leaderboard | Competition scoring, reward tiers, anti-gaming rules |
| Open Questions | What is known, what is not, and how to find out |
| Suggestions | Improvement options with paths and recommendations |
| Requirements | The decomposed requirement set |
| Repo Review | Line-by-line audit of the base commit |
| Sources | Every official source used |
| Flagged for Review | Unverified values and irregularities |
| Coordination | Mirror of COORDINATION.md |

## Current state

Data and governance layers are complete and verified. The betting layer is built but cannot
fire: no market lines have been ingested and no game log has been ingested, so the model runs
with home-field advantage at 0.0 and no schedule-strength adjustment. See the Open Questions
page for the blocking items.
