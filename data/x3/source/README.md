# Source data (fetched 2026-11-14T19:21Z)

From `nflverse/nfldata` @ master commit `d9772e4e83ab349de144bf6d7a4fc9fb3ee7b066`
(2026-11-14T19:05:17Z), via api.github.com raw (files <=100MB served directly by the API):

| file | bytes | sha256 (first 16) |
|------|-------|-------------------|
| games.csv | 2190038 | 7d791bb4776e81a3 |
| closing_lines.csv | 942229 | 3571e1c9fc8d7396 |
| initial_lines.csv | 45068 | 654770173d11fdb2 |
| sc_lines.csv | 140765 | 384039e92630831e |
| standings.csv | 56873 | a955694cba054283 |

Provenance policy:
- Scores/game results in `games.csv` mirror the official NFL record (gamebooks / GSIS ids). Spot-checked
  against NFL.com week pages by this session and by prior sessions (desk capture, 137 finals).
- `spread_line`, `total_line`, home/away moneylines in `games.csv` are MARKET data compiled by PFF and
  published through nflverse. They are third-party market prices, NOT league-official data, and every
  table using them is labelled MARKET.
- `initial_lines.csv` (openers) covers 2021 only (Westgate/WSGT). No 2026 opening-line source exists in
  this sandbox -> opening snapshots stay blank and flagged.
- Release-asset copies of injuries/depth charts (nflverse-data releases) redirect to a CDN host that this
  sandbox cannot reach; injury/depth data therefore comes from the in-repo verified NFL.com transcription
  (data/hub/injuries_2026_wk10.csv) and the club depth charts under
  data/x3/raw/club_depth_charts_2026_wk10/ (31 of 32 clubs read; HOU chart did not render - flagged).
