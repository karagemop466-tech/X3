# Week 10, 2026 injury report: official-source audit

Owner session: `arena/d968fa97-x3`. Scope: `audit/**` only. Nothing else in the repo was edited.

Live page (after merge and Pages deploy): https://karagemop466-tech.github.io/X3/audit/

## What was checked

| Item | Official source (fetched 2026-11-14) | Result |
|------|--------------------------------------|--------|
| 345 player rows, Week 10 | https://www.nfl.com/injuries/league/2026/reg10 | Transcribed in full; compared with `docs/data/injury-2026-week10.csv` |
| Game pairs, orientation, kickoff, network | https://www.nfl.com/schedules/2026/by-week/week-10 and per-game pages | 14 games checked; 13 orientations match; 1 does not (see F-A01) |
| Bye teams | same schedule page | CHI, DEN, PHI, TB |

## Results

- 294 of 345 rows match on every compared field.
- 51 rows differ, all on the game label (24 rows, NE/DET) or the TV list (27 rows, LAC/BAL).
- 0 mismatches in team record, position, injury text, practice status, or game status.
- Status counts from the official page: 66 Out, 10 Doubtful, 84 Questionable, 185 blank.

## Flags (published on `audit/index.html`)

- F-A01 Game label "NE vs DET (Munich)" should read "NE @ DET (Munich)"; the schedule lists "Patriots at Lions".
- F-A02 TV list for LAC @ BAL differs between the injury page and the schedule page; not changed.
- F-A03 Repo source column points to the generic `https://www.nfl.com/injuries/` index.
- F-A04 The Thursday game is already final on the schedule page; its rows are a pre-game snapshot.
- F-A05 Practice labels are abbreviated in the repo (Full / Limited / DNP); mapping is one-to-one.
- F-A06 No update timestamp on the page extract; re-check the live page before any decision.

## Files

- `official_injury_wk10_2026.raw.txt`: transcription of the official page, as printed.
- `official_injury_wk10_2026.csv`: the same data in repo column layout.
- `schedule_check_wk10.csv`: schedule orientation, time, and network check.
- `diff_report.csv`: one line per player with MATCH / DIFF and the fields that differ.
- `summary.json`: counts used on the page.
- `build_and_diff.py`: parses the raw file, runs the comparison, writes the CSV and JSON.
- `build_audit_page.py`: renders `index.html` from those outputs.

## Limits

- The sandbox cannot reach NFL.com directly. The official text was read through the fetch tool, then transcribed. The transcription was not checked against raw HTML byte for byte.
- The repo dataset was not modified. Corrections are proposed on the page for owner review.
- Re-run both scripts after any change to the raw file or the source dataset.
