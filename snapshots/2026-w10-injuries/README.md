# Week 10, 2026 official injury report: dated re-capture

Owner session: `arena/348a707c-x3`. Published page: `snapshots/2026-w10-injuries/index.html`.

## Official sources

- Injury report (captured): https://www.nfl.com/injuries/ (title: "Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season | NFL.com")
- Schedule cross-reference: https://www.nfl.com/schedules/2026/by-week/week-10

## Files

| File | What it is |
|---|---|
| `official_transcription.psv` | Pipe-delimited transcription of every row on the live page (347 rows, 14 games). The only hand-entered file. |
| `official_rows.csv` | Generated from the transcription; one row per player with the source URL. |
| `compare_hub.csv` | Field-by-field comparison with `hub/injuries.html`. One line per player that differs or is missing. |
| `summary.json` | Counts, transcription SHA-256, validation results, comparison totals. |
| `build_and_compare.py` | Validates the transcription, hashes it, writes the CSV/JSON outputs above. |
| `build_page.py` | Renders `index.html` from those outputs. |
| `index.html` | Published page: capture record, flagged items, differences, full table. |

## Re-run

```bash
python3 snapshots/2026-w10-injuries/build_and_compare.py
python3 snapshots/2026-w10-injuries/build_page.py
```

## Limits

- The sandbox shell cannot reach nfl.com. The text was read through the page-fetch tool and transcribed. The raw bytes were not retained, so only the transcription is hashed.
- The fetch tool did not return a clock time. The transcription date (2026-11-15, sandbox clock; last modified 18:31 UTC) is recorded instead.
- The official page changes until kickoff. This is a single dated capture, not a time series.
