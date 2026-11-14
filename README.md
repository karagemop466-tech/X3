# X3 — NFL Research, Line Origination & Strategy Validation

A research-and-analysis project that collects official NFL data, originates independent betting
lines, designs skill-based betting strategies (single bets, parlays, player-prop combos), separates
skill from luck through statistical validation gates, and tracks injuries and roster deficiencies —
presented on a transparent dashboard where **every data row carries an official source link and
every unverifiable value is left blank and flagged** (never inferred).

## Live site

The GitHub Pages dashboard is published from `docs/` on `main`: start at `docs/index.html`
(Dashboard → Executive Summary → Requirements → Line Origination → Validation → Correlation →
Leaderboard → Injuries → Standings → Questions → Suggestions → Flagged → Sources → Repo Audit).

## Repository layout

| Path | What it is |
|---|---|
| `docs/` | GitHub Pages site (`index.html`, `style.css`, `pages/`, `data/`) |
| `docs/data/` | Canonical verified datasets (Week-10 2026 injuries, standings snapshots) with per-row source URLs |
| `research/` | Research notes backing each site page (line origination, validation, correlation, leaderboard, injury tracking, repo audit) |
| `tools/` | `build_data_pages.py` (CSV → data pages) and `verify_site.py` (line-by-line source-link verification) |
| `COORDINATION.md` | Shared task board for parallel sessions: claims, log, verification record, irregularities |

## Verification policy

1. Every table row links to an official/official-hosted source, or the value is blank and marked
   `UNVERIFIED`. No values are ever inferred or filled in.
2. Source tiers (Official / Academic / Trusted-secondary / Industry-secondary) are labeled on the
   Sources page.
3. Conflicts between sources are published on the **Flagged for Review** page with links —
   never silently resolved.
4. `python3 tools/verify_site.py` re-checks every row after any change.

## Data status (2026-11-14)

- Week 10, 2026 official injury report: 345 player rows, 28 teams (nfl.com/injuries).
- 2026 standings: all 32 teams (nfl.com/standings).
- Depth-chart ranks (starter/backup): **unverified** — official depth-chart URLs return 404
  (Flagged F-04); those columns are intentionally blank.
- Correlation coefficients for parlays/prop combos: **blank** — no official numeric source exists;
  an estimation pipeline is specified instead (see `research/correlation.md`).

## Owner decisions still open

See `docs/pages/questions.html`: Q-01 (leaderboard reward budget), Q-02 (jurisdiction/legal scope),
Q-07 (odds-feed choice). Everything else runs without manual input.
