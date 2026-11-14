# Verification log — session e1c332ce (2026-11-14)

Machine gate: `python3 scripts/verify_data.py` — **PASS** (2,134 checks).
Every fact-table row in `docs/data/*.json` carries a source link or an explicit
`unverified: true` marker; structural invariants and site wiring pass.

## Sources fetched this session (all 2026-11-14)

| Source | Class | What was verified against it |
| --- | --- | --- |
| nfl.com/standings/league/2026/REG | OFFICIAL | 32-team table: W/L/T, PCT, PF/PA/DIFF, home/road/div/conf/non-conf splits, streak, L5 |
| nfl.com/standings/conference/2026/REG | OFFICIAL | Current playoff seeds (all 32) |
| nfl.com/schedules/2026/by-week/week-9 | OFFICIAL | 15 final scores + byes (PIT, TEN) |
| nfl.com/schedules/2026/by-week/week-10 | OFFICIAL | 14-game slate incl. TNF final, Munich note, byes (CHI/DEN/PHI/TB) |
| nfl.com/schedules/2026/by-week/week-11 | OFFICIAL | 13-game slate, Mexico City SNF, 6 byes (ATL/CLE/GB/LAR/NE/SEA) |
| espn.com/nfl/injuries | TRUSTED | All 32 teams' game-day designations + IR rows |
| espn.com/nfl/odds (DraftKings) | MARKET | Weeks 10-11 spreads/totals/ML + opens + Super Bowl futures |
| espn.com/nfl/team/depth (RotoWire) | TRUSTED | PIT + BAL string-level depth charts |
| ESPN report (Seahawks-Raiders Wk10) | TRUSTED | SEA starter note: Drew Lock starts for Darnold |

## Line-by-line reconciliation performed

1. **Standings internal consistency (all 32 rows):** PF−PA = DIFF ✓; home+road = games ✓;
   conf + non-conf = games ✓; div ⊆ conf ✓; league PF = league PA ✓; league W = league L ✓.
   (This arithmetic partition is also what validated the column mapping flagged as F-02.)
2. **Standings vs results:** every Week-9 loser's record vs winner's record reconciles
   against the game scores (checked for all 15 games + TNF); week-10 TNF (WAS 24 @ NYG 21)
   is reflected in WAS 3-5-1 and NYG 5-3-1.
3. **Odds mirrored pairs:** every game's spread_away = −spread_home; totals in 30–70 range;
   every game block cross-checked between the two team rows on the source page.
4. **Injury rows:** every row has team/player/pos/status; statuses restricted to the four
   source values; status/comment contradictions preserved verbatim and tagged F-04.
5. **Model outputs:** `compute_lines.py` and `compute_analysis.py` are deterministic and
   re-runnable; outputs carry their input sources; assumptions A-01..A-03 labeled unverified.
6. **Site wiring:** every `fetch()` target exists; every page links `styles.css`/`app.js`;
   no broken internal links (one typo found by the checker on the executive summary and fixed).

## Irregularities (published on Flagged for Review)

F-01 schedule URL redirect · F-02 standings split mapping (inferred by arithmetic partition)
· F-03 odds open timestamps unknown + extreme moves · F-04 ESPN status/comment mismatches
· F-05 depth charts incomplete + third-party · F-06 totals heuristic · F-07 HFA assumptions
· F-08 pilot-only correlations · F-09 legal status of wagering in owner jurisdiction
· F-10 2026 roster assignments recorded as-reported.

## What was NOT verified (and left blank/flagged accordingly)

- Replacement-string claims for 30 of 32 teams (only PIT/BAL chart-verified) — F-05.
- Player prop lines — no verified source exists; prop strategies blocked (Q-06).
- The cause of each large odds move — plausible news alignment noted only where a
  dated announcement exists (e.g., Lamar Jackson IR, Nov 13); no causes invented.
- Neutral-site HFA values — assumption A-02 flagged (F-07).
