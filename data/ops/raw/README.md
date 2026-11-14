# Raw captures — provenance

Every file in this directory is a **verbatim** copy of the content returned by the listed
official URL at the listed retrieval time. Nothing here is edited by hand: the tables and
bullets are exactly as published, including the league's own headers, so any later claim can
be re-checked line by line against the live page.

| File | Official URL | Retrieved (UTC) | What it is |
|------|--------------|-----------------|------------|
| `schedules_2026_week-10.md` | https://www.nfl.com/schedules/2026/by-week/week-10 | 2026-11-14 | Week 10 slate (14 games + 4 byes) |
| `schedules_2026_week-11.md` | https://www.nfl.com/schedules/2026/by-week/week-11 | 2026-11-14 | Week 11 slate (15 games + 6 byes) |
| `injuries_2026_reg11.html` | https://www.nfl.com/injuries/league/2026/reg11 | 2026-11-14 | **Redirect trap.** This URL returns the *Week 10* report, not Week 11 |
| `standings_2026_reg.md` | https://www.nfl.com/standings/league/2026/REG | 2026-11-14 | League standings, 32 clubs |
| `teamstats_offense_passing_2026.md` | https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all | 2026-11-14 | Team passing offense, 32 clubs |
| `teamstats_defense_passing_2026.md` | https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all | 2026-11-14 | Team passing defense, 32 clubs |
| `playerstats_receiving_2026.md` | https://www.nfl.com/stats/player-stats/category/receiving/2026/reg/all/receivingyards/desc | 2026-11-14 | Receiving leaders (per-player, season to date) |
| `depthchart_det_2026-11-14.md` | https://www.detroitlions.com/team/depth-chart | 2026-11-14 | Detroit depth chart, club-published "unofficial" |

Parsers that read these files live in `scripts/ops_parse.py`. A capture is only ever
replaced by a newer capture of the same URL, and the date in this table is updated then.
