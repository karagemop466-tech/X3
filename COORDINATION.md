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
| T1 | Repo review & line-by-line audit (README, structure) | in progress | arena-4856379c | `docs/pages/repo-audit.html`, `README.md` | git history at `e124230`; file inventory | README is a single line `# X3` — no description, license, or contents |
| T2 | Requirements inventory (full list of requirements + status) | unclaimed | — | `docs/pages/requirements.html` | — | — |
| T3 | Research: line-origination strategies & signal generation | unclaimed | — | `research/line-origination.md`, `docs/pages/strategies.html` | — | — |
| T4 | Research: validation gates, luck vs skill methodology | unclaimed | — | `research/validation.md`, `docs/pages/validation.html` | — | — |
| T5 | Research: correlation values (parlays, player-prop combos) | unclaimed | — | `research/correlation.md`, `docs/pages/correlation.html` | — | — |
| T6 | Leaderboard competition design (rules, rewards, anti-overfitting) | unclaimed | — | `research/leaderboard.md`, `docs/pages/leaderboard.html` | — | — |
| T7 | Injury & depth-chart tracking system (deficiency detection) | unclaimed | — | `research/injury-tracking.md`, `docs/pages/injuries.html`, `docs/data/injury-*.csv` | — | — |
| T8 | Questions / information gaps + discovery suggestions | unclaimed | — | `docs/pages/questions.html` | — | — |
| T9 | Suggestions board (site + decision-making improvements) | unclaimed | — | `docs/pages/suggestions.html` | — | — |
| T10 | Executive summary | unclaimed | — | `docs/pages/executive-summary.html` | — | — |
| T11 | Site build (GitHub Pages dashboard, nav, tables) | unclaimed | — | `docs/**` | — | — |
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
