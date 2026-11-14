# COORDINATION.md — Shared Task Board (X3 / NFL Research & Dashboard)

**Protocol:** See task board below. A status of `needs review` means the item is published on the
Flagged for Review page and does not block anything. Never mark anything `verified` without an
official source link. Log all irregularities in the LOG section.

**Session registry**

| Session ID | Branch | Notes |
|---|---|---|
| `arena-4856379c` | `arena/4856379c-x3` | Arena session branch (named by the platform; used in place of `session-<id>/<task>` since the platform binds work to this branch). Acts as integration session for this repo (no other sessions observed at first claim). |

---

## Task board

| Task | Description | Status | Owner session | File scope | Sources / Verification | Irregularities |
|---|---|---|---|---|---|---|
| T1 | Repo review & line-by-line audit (README, structure) | done | arena-4856379c | `docs/pages/repo-audit.html`, `research/repo-audit.md`, `README.md` | git history at `e124230`; `git ls-tree -r` file inventory | README was a single line `# X3` — no description, license, or contents (rewritten in T11) |
| T2 | Requirements inventory (full list of requirements + status) | done | arena-4856379c | `docs/pages/requirements.html` | 28 requirements transcribed from brief; statuses checked against repo contents via `tools/verify_site.py` | — |
| T3 | Research: line-origination strategies & signal generation | done | arena-4856379c | `research/line-origination.md`, `docs/pages/strategies.html` | Levitt 2004 (EJ, pricetheory.uchicago.edu PDF); Claremont thesis 2025 (scholarship.claremont.edu); Skidmore thesis (digitalcoll.skidmore.edu/record/6451); community replication (github.com/gouthamperavali4610-web/nfl-market-efficiency) | HFA/margin-σ parameters intentionally blank (UNVERIFIED until calibrated) |
| T4 | Research: validation gates, luck vs skill methodology | done | arena-4856379c | `research/validation.md`, `docs/pages/validation.html` | Bailey & López de Prado 2014 DSR (ssrn.com/abstract=2460551); Bailey/Borwein/López de Prado/Zhu 2015 PBO (ssrn.com/abstract=2326253) | DSR 0.95 / PBO 0.20 are paper conventions, not NFL-validated (F-08) |
| T5 | Research: correlation values (parlays, player-prop combos) | done | arena-4856379c | `research/correlation.md`, `docs/pages/correlation.html` | Davis 2018 via bettoredge (secondary); Skidmore thesis (digitalcoll.skidmore.edu/record/6451); industry SGP-tax descriptions (flagged secondary) | No official numeric correlation coefficients exist → values blank + UNVERIFIED (F-03); pipeline published instead |
| T6 | Leaderboard competition design (rules, rewards, anti-overfitting) | done | arena-4856379c | `research/leaderboard.md`, `docs/pages/leaderboard.html` | NFL Big Data Bowl prizes/rubric (kaggle.com/c/nfl-big-data-bowl-2021, 2022/rules, /competitions/nfl-big-data-bowl-2027/rules) | Reward amounts blank pending budget (Q-01) |
| T7 | Injury & depth-chart tracking system (deficiency detection) | done | arena-4856379c | `research/injury-tracking.md`, `docs/pages/injuries.html`, `docs/data/injury-2026-week10.csv` | nfl.com/injuries Week 10 2026 (8 chunks, 345 rows, captured 2026-11-14); nfl.com/news headlines; nfl.com/news/2024-2025-national-football-league-important-dates (deadlines) | Depth charts 404 → depth ranks blank (F-04); rest-outs separated (F-07); blank-status rows flagged (F-09); roster pairings vs historical knowledge flagged (F-02); Henley LAC/DEN conflict (F-12); Lamar timeline 6-9 vs 6-10 wks (F-01) |
| T8 | Questions / information gaps + discovery suggestions | done | arena-4856379c | `docs/pages/questions.html` | 15 questions; known answers cite the same sources as the data pages | Q-01/Q-02/Q-07/Q-11/Q-13 remain OPEN by nature (owner decisions or blocked sources) |
| T9 | Suggestions board (site + decision-making improvements) | done | arena-4856379c | `docs/pages/suggestions.html` | 14 proposals (S-01–S-14), all status PROPOSED awaiting review | — |
| T10 | Executive summary | done | arena-4856379c | `docs/pages/executive-summary.html` | All claims sourced inline | — |
| T11 | Site build (GitHub Pages dashboard, nav, tables) | done | arena-4856379c | `docs/**`, `README.md` | 14 pages, 49 tables; shared stylesheet; CSV→page generator `tools/build_data_pages.py` | README rewritten (was one line); LICENSE still absent (F-05, owner decision) |
| T12 | Line-by-line verification pass (every row sourced or flagged) | done | arena-4856379c | all `docs/pages/**` | `tools/verify_site.py` run 2026-11-14: 14 pages / 49 tables, 0 failures, 0 warnings; every source-table row has an official link or UNVERIFIED flag; internal links resolve | — |
| T13 | Integration: merge to main, PR record, Pages deploy confirmation | in progress | arena-4856379c | `COORDINATION.md`, `README.md` | — | — |

Shared outputs (`docs/index.html`, `docs/nav`, `docs/data/*.csv`) are changed only by the
integration pass (T11/T13) of the owning session. If a second session appears, it must not edit
`docs/index.html` or `docs/style.css` and must log requests here instead.

---

## LOG

- 2026-11-14 `arena-4856379c`: Created task board. Repo inventory at start: `README.md` only
  (content `# X3`), git root commit `e124230` ("Initial commit"). No `COORDINATION.md` existed.
  Claiming T1 now; other tasks claimed in batches as work proceeds. No other session branches
  observed (`git branch -a` shows only `main` and this session branch), so this session will also
  perform final integration (T13) and will re-verify combined data before merging.
- 2026-11-14 `arena-4856379c`: T1–T12 complete. Sources & verification recorded per-task above and on
  the site's Sources page (17 sources: 6 official NFL/ESPN, 5 academic (SSRN/JEJ/university repos),
  1 official competition host (Kaggle), 3 trusted-secondary (GitHub community projects), 2 industry
  secondary — flagged). Verification performed: `git ls-tree` repo audit; 8-chunk fetch of
  nfl.com/injuries (345 rows transcribed to CSV, then generated into pages by script — no hand
  duplicates); 32-team standings cross-checked against injury-page record headers (all match);
  academic references verified at SSRN/publisher/university hosts; `tools/verify_site.py` line check
  (49 tables, 0 failures). Irregularities: 12 flagged items (F-01…F-12) published on the site's
  Flagged for Review page with source links; none block merge. Unverified values left blank per
  policy: depth ranks (F-04), correlation coefficients (F-03), leaderboard reward amounts (Q-01),
  model calibration parameters.
