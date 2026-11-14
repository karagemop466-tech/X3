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
| T2 | Requirements inventory (full list of requirements + status) | in progress | arena-4856379c | `docs/pages/requirements.html` | — | — |
| T3 | Research: line-origination strategies & signal generation | in progress | arena-4856379c | `research/line-origination.md`, `docs/pages/strategies.html` | Levitt 2004 (EJ, uchicago.edu PDF); Claremont thesis 2025 (scholarship.claremont.edu); Gray & Gray ref via thesis; Oswald 2022 via thesis | — |
| T4 | Research: validation gates, luck vs skill methodology | in progress | arena-4856379c | `research/validation.md`, `docs/pages/validation.html` | Bailey & López de Prado 2014 DSR (JPM; ssrn.com/abstract=2460551); Bailey/Borwein/López de Prado/Zhu 2015 PBO (ssrn.com/abstract=2326253) | — |
| T5 | Research: correlation values (parlays, player-prop combos) | in progress | arena-4856379c | `research/correlation.md`, `docs/pages/correlation.html` | Davis 2018 CFB correlated parlays (cited via bettoredge); Skidmore thesis "An Analysis of NFL Betting Strategies" (digitalcoll.skidmore.edu/record/6451) | Exact numeric correlation coefficients NOT found in any verified source → value cells left blank + flagged per rules |
| T6 | Leaderboard competition design (rules, rewards, anti-overfitting) | in progress | arena-4856379c | `research/leaderboard.md`, `docs/pages/leaderboard.html` | NFL Big Data Bowl Kaggle rules/prizes (kaggle.com/c/nfl-big-data-bowl-2021, 2022, /competitions/nfl-big-data-bowl-2027/rules) | — |
| T7 | Injury & depth-chart tracking system (deficiency detection) | in progress | arena-4856379c | `research/injury-tracking.md`, `docs/pages/injuries.html`, `docs/data/injury-2026-week10.csv` | nfl.com/injuries (Week 10, 2026 — 8 chunks fetched 2026-11-14); nfl.com/news injury headlines; nfl.com/news/2024-2025-national-football-league-important-dates (report deadlines) | nfl.com/depthcharts and /teams/*/depth-chart return 404 → depth-rank columns blank + flagged; Lamar Jackson timeline 6-9 vs 6-10 wks mismatch across two official headlines |
| T8 | Questions / information gaps + discovery suggestions | in progress | arena-4856379c | `docs/pages/questions.html` | — | — |
| T9 | Suggestions board (site + decision-making improvements) | in progress | arena-4856379c | `docs/pages/suggestions.html` | — | — |
| T10 | Executive summary | in progress | arena-4856379c | `docs/pages/executive-summary.html` | — | — |
| T11 | Site build (GitHub Pages dashboard, nav, tables) | in progress | arena-4856379c | `docs/**` | — | — |
| T12 | Line-by-line verification pass (every row sourced or flagged) | unclaimed | — | all `docs/pages/**` | — | — |
| T13 | Integration: merge to main, PR record, Pages deploy confirmation | unclaimed | — | `COORDINATION.md`, `README.md` | — | — |

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
