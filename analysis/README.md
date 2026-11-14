# Analysis index

| Doc | What it contains |
| --- | --- |
| [verification-log.md](verification-log.md) | Line-by-line verification record: sources, reconciliation, irregularities |
| [line-origination.md](line-origination.md) | Model v0.1 method, assumptions, limitations, path to validation |
| [depth-deficiency.md](depth-deficiency.md) | Rule R-1 for 2nd/3rd/4th-string deficiency flags and string-claim policy |

The site's HTML pages are the primary presentation; these docs capture the working
notes behind them. Machine checks live in `scripts/`:

- `scripts/verify_data.py` — source-link + invariant gate (must PASS before merge).
- `scripts/compute_lines.py` — line origination (deterministic).
- `scripts/compute_analysis.py` — pilot correlations + Pythagorean luck table.

Key data files (single sources of truth): `x3lab/data/*.json` — standings, weeks 9/10/11,
odds, injuries, depth, deficiencies, lines, luck, correlation, strategies, validation
gates, leaderboard, questions, suggestions, flagged, sources.
