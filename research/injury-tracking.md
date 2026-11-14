# Injury & Depth Tracking System — design + verified Week-10 snapshot (T7)

**Session:** arena-4856379c · **Date:** 2026-11-14 (data captured live this date)

## 1. Verified source map

| Feed | What it provides | Official source | Verified state (2026-11-14) |
|---|---|---|---|
| Weekly injury report | Player, position, injury, practice participation (Wed–Fri), game status (Out/Doubtful/Questionable) | https://www.nfl.com/injuries/ (year selector 1965–2026, week selector verified) | ✅ Live data captured for Week 10, 2026 (8 page chunks) |
| Report deadlines | Practice reports due 4:00 p.m. NY time on the three days before the game day; game status report due 2 days before kickoff (Fri for Sun games etc.) | https://www.nfl.com/news/2024-2025-national-football-league-important-dates | ✅ Verified |
| Game-status definitions | Out = will not play; Doubtful = unlikely; Questionable = uncertain ("probable" removed 2016) | Policy summary via https://www.espn.com/nfl/story/_/id/17361111/nfl-streamlines-injured-players-game-status-removes-probable-designation (ESPN official story on the league policy) | ✅ Verified |
| IR / transactions / starter news | IR placements, trades, who will start | https://www.nfl.com/news (e.g., "Dolphins place QB Malik Willis on IR", "Ravens officially place Lamar Jackson on injured reserve") | ✅ Verified (headline-level) |
| Inactives (game day) | Players ruled out ~90 min before kickoff | nfl.com news ("NFL Week 9 inactives: Players ruled out...") | ⚠️ Headline verified; the exact 90-minute policy text NOT verified this session → blank + flagged (F-06) |
| Depth charts (who is 1st/2nd/3rd string) | Starter vs backup rank — the key to "2nd/3rd/4th string replacing starters" | https://www.nfl.com/depthcharts/ and /teams/*/depth-chart/ both return **404** (tested 2026-11-14) | ❌ NOT retrievable at known official URLs → depth-rank columns blank + UNVERIFIED (F-04) |
| Snap counts (defacto depth evidence) | Who actually plays | NFL GSIS/Next Gen Stats https://www.nfl.com/stats/ (official) + nflverse https://github.com/nflverse/nflverse-data (trusted-secondary) | ⏳ Schema ready, not yet ingested (Q-09) |

## 2. Deficiency-detection model (how "2nd/3rd/4th string" is determined)

1. **Unit mapping:** QB, RB, WR, TE, OL (T/G/C), DL (DT/DE), EDGE/LB, CB, S, ST (K/P/LS).
2. **Starter flag:** from depth chart rank 1 (blocked — see F-04) → until then, starter-status is
   **never inferred**; the tracker shows unit-level loss counts only.
3. **Replacement inference:** when a starter is Out/Doubtful/IR, the next depth rank is the expected
   replacement. Replacement name + rank are blank until depth data exists. Never guess.
4. **Severity score (derived, computed only from verified rows):**
   `sev = Σ unit_weight × status_weight`, status_weight: Out=1.0, Doubtful=0.8, Questionable=0.4
   (weights are model parameters — proposals, tuned later; see Suggestions S-11).
   Unit weights must be calibrated from EPA/play deltas with vs without starters (needs snap data,
   Q-09) — **blank until calibrated**.
5. **Backup-QB alert:** any team with QB1 Out/Doubtful/IR triggers a standing alert flag (Baltimore,
   Minnesota, Seattle, Miami, Arizona situations this week — see snapshot).
6. **Rest-distortion filter:** "Not injury related - resting player" entries are excluded from
   injury severity (e.g., two Jaguars listed Out for rest — F-07) but tracked separately.

## 3. Verified Week-10 (2026) snapshot highlights

Full rows: `docs/data/injury-2026-week10.csv` (canonical) and the Injuries page (derived tables).
Every row's source: https://www.nfl.com/injuries/ (official). Cross-verified team records against
https://www.nfl.com/standings/ (all 28 non-bye teams match).

| Alert | Verified detail | Source |
|---|---|---|
| BAL QB room devastated | Lamar Jackson (right thumb) placed on IR; backup Tyler Huntley out for season (turf toe) → 3rd/4th-string QBs expected vs LAC | https://www.nfl.com/news/ravens-lamar-jackson-right-thumb-out-6-9-weeks-expects-to-return-this-season ; https://www.nfl.com/news/ravens-qb-tyler-huntley-out-for-season-turf-toe-injury |
| MIN QB1 out | Kyler Murray (hamstring) DNP + Out; Carson Wentz full participant (no status) | https://www.nfl.com/injuries/ |
| SEA QB1 out | Sam Darnold (ribs/quad) Out; Drew Lock to start ("no injury designation") | https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again |
| MIA QB on IR + C out | Malik Willis (groin) on IR, Kyle McCord in line for first start; Aaron Brewer (C) Out | https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start |
| ARI QB change | Carson Beck to start vs LAR | https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11 |
| CLE QB | Deshaun Watson to start vs HOU (was in concussion protocol week 9) | https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11 |
| DET secondary losses | Kerby Joseph (S) Out, D.J. Reed (CB) Out, Cade Mays (C) Out | https://www.nfl.com/injuries/ |
| GB run game | Josh Jacobs (RB) Out (finger surgery); Micah Parsons (LB) Out; Sean Rhyan (C) Out; Zaire Franklin Doubtful | https://www.nfl.com/injuries/ ; https://www.nfl.com/news/packers-rb-josh-jacobs-to-undergo-surgery-on-finger-this-week |
| NE backfield/secondary | TreVeyon Henderson (RB) Out; Carlton Davis III (CB) Out; Ben Brown (C) Out | https://www.nfl.com/injuries/ |
| HOU pass rush + WR | Danielle Hunter (DE) Out; Azeez Al-Shaair (LB) Out; Marvin Harrison Jr. (WR) Out | https://www.nfl.com/injuries/ |
| MIN pass catchers | T.J. Hockenson (TE) Out; Jauan Jennings (WR) Out; Blake Cashman (LB) Out | https://www.nfl.com/injuries/ |
| LAR availability | Puka Nacua (WR) likely IR (turf toe, MCL/PCL); Steve Avila (G) Out; Terrance Ferguson (TE) Out | https://www.nfl.com/news/rams-wr-puka-nacua-likely-to-be-placed-on-injured-reserve-with-turf-toe-sprained-mcl-and-pcl |
| LAC (0-8) | Justin Herbert avoids finger fracture (week 9 news) | https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-monday-nov-9 |

## 4. Weekly operating procedure (automation-ready; no manual input by the owner)
1. **Wed–Fri:** ingest practice reports (nfl.com/injuries) → diff vs prior day → store versioned CSV.
2. **Fri/Sat:** ingest game-status report → compute deficiency scores → publish snapshot.
3. **Game day:** ingest inactives & official "will start" news → final alert pass.
4. **Post-game:** ingest snap counts (once connected) → backtest severity weights → retrain.
5. All steps write `docs/data/injury-<season>-week-<n>.csv` + regenerate the Injuries page; every row
   keeps its `source_url` column.

## 5. Known data gaps (see Questions page for discovery paths)
- Depth-chart ranks (F-04): blocked at official URLs; alternatives to verify manually: official team
  sites' depth-chart pages, official transaction/personnel notices, beat-writer confirmations.
- Snap counts ingestion (Q-09), historical injury archive backfill (Q-10 — nfl.com year/week
  selectors make this possible), inactives policy text (F-06).
