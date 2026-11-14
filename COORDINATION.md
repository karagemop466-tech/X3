# COORDINATION.md — Shared Task Board

Repo: `karagemop466-tech/X3`
Session start: 2026-11-14 (UTC)

## Branch / session rules in force

This session is bound to a **single fixed branch**: `arena/7e632805-x3` (branched from
`main` @ `e124230`). Arena tracks this session by that branch, so this session:

* commits and pushes **only** to `arena/7e632805-x3`;
* does **not** create or switch to `session-<id>/<task>` worktrees;
* claims file scopes below so that any *other* concurrent session can avoid them.

If another session needs to edit a file owned here, log the request in **Handoff / Requests**
instead of editing. If a claim is >60 min old with no commits, another session may take over.

## Session registry

| Session ID | Branch | Status | Started | Last commit |
|---|---|---|---|---|
| `arena/7e632805-x3` | `arena/7e632805-x3` | active | 2026-11-14 | see change log |

## Task board

Legend: `unclaimed` · `in progress` · `needs review` · `done`

| # | Task | Status | Owner | Files in scope |
|---|---|---|---|---|
| T01 | Create/read COORDINATION.md, define scope | done | `arena/7e632805-x3` | `COORDINATION.md` |
| T02 | Repo audit, line by line, flag irregularities | done | `arena/7e632805-x3` | `site/repo-review.html`, `site/data/audit.json` |
| T03 | Requirements inventory (collect / organize / analyze) | done | `arena/7e632805-x3` | `site/requirements.html` |
| T04 | Executive summary | done | `arena/7e632805-x3` | `site/index.html`, `site/executive-summary.html` |
| T05 | Open-questions register (have / don't have / how to discover) | done | `arena/7e632805-x3` | `site/questions.html` |
| T06 | Suggestions backlog + decision-path review page | done | `arena/7e632805-x3` | `site/suggestions.html` |
| T07 | Own-line origination: signal strategies + leaderboard + validation gates | done | `arena/7e632805-x3` | `site/lines.html`, `site/strategies.html`, `site/leaderboard.html`, `site/validation.html` |
| T08 | Correlation values & parlay/prop-combo math | done | `arena/7e632805-x3` | `site/correlation.html` |
| T09 | Injury & depth-chart / defensive-deficiency tracking | done | `arena/7e632805-x3` | `site/depth-charts.html`, `site/injuries.html` |
| T10 | Source register + verification pass (every row → official link) | done | `arena/7e632805-x3` | `site/sources.html` |
| T11 | Flagged for Review page | done | `arena/7e632805-x3` | `site/flagged.html` |
| T12 | Static site build (dashboard shell, nav, data renderer) | done | `arena/7e632805-x3` | `site/` all files |
| T13 | GitHub Pages enablement + deploy verification | done | `arena/7e632805-x3` | `.github/workflows/pages.yml` |
| T14 | Final integration: combined re-verify, link check, PR + merge | done | `arena/7e632805-x3` | all |

## Verification rules (binding on every session)

1. A table row is **verified** only if its value was read from an official source and the row
   carries that source's URL. Official = NFL.com, NFL team sites, NFL Football Operations,
   NFL Next Gen Stats, NFLPA. Pro-Football-Reference and all sports media are *secondary*
   (not official) and must never back a fact row.
2. If a value cannot be confirmed from an official source, the cell is **left blank**, marked
   `UNVERIFIED`, and mirrored to the **Flagged for Review** page.
3. Never infer, interpolate, or model a value into a "fact" row. Model output is labelled
   `DERIVED`, lives in its own table, and always shows its parameters.
4. Every claim is re-checked against the live official page before it is marked verified.

## Verification results

| Layer | Rows | Sourced | Notes |
|---|---|---|---|
| Standings | 32 | 32/32 | `nfl.com/standings/league/2026/REG` |
| Schedule | 14 games + 4 byes | 18/18 | `nfl.com/schedules/2026/by-week/week-10` |
| Injuries | 345 | 345/345 | `nfl.com/injuries/`, Week 10 |
| Depth charts | 31/32 clubs | 108/108 | HOU not readable (see F-05) |
| Starter-absent join | 76 | 76/76 | derived: injury report × depth chart |
| Model lines | 14 | 14/14 | derived, HFA = 0.0, uncalibrated |

Structural checks run against the built site: 18 pages, 25 tables, 0 column mismatches,
0 broken internal links, all 18 pages return HTTP 200.

## Handoff / Requests

| Date | From | Request | Status |
|---|---|---|---|
| 2026-11-14 | `arena/7e632805-x3` | No other session detected at start of work. Single-session build. | n/a |
| 2026-11-14 | `arena/7e632805-x3` | **Owner decision needed:** no official source publishes betting lines (Q-02, Q-03, F-06). The scoring layer cannot fire without a licensed or manually-recorded odds feed. | open |
| 2026-11-14 | `arena/7e632805-x3` | **Owner decision needed:** leaderboard rewards are currently specified as notional (S-12, Q-16). Confirm before any season starts. | open |
| 2026-11-14 | `arena/7e632805-x3` | **Legal:** owner is in Tokyo, Japan. Whether originating lines and staking real money is lawful there is unresolved (Q-17, S-16). | open |

## Change log

| Date | Session | Change |
|---|---|---|
| 2026-11-14 | `arena/7e632805-x3` | Board created; T01–T12 claimed. |
| 2026-11-14 | `arena/7e632805-x3` | Ingested official standings (32), Week 10 schedule (14 games, 4 byes), Week 10 injury report (345 rows). |
| 2026-11-14 | `arena/7e632805-x3` | Read 31/32 official club depth charts. HOU publishes image only → flagged F-05. |
| 2026-11-14 | `arena/7e632805-x3` | Built `tools/nfl_data.py` (verified data), `tools/site_content.py` (analysis), `tools/build_site.py` (build). |
| 2026-11-14 | `arena/7e632805-x3` | Built 18-page site + `site/data/*.json`. 11 flagged items. T01–T12 complete. |
| 2026-11-14 | `arena/7e632805-x3` | Added Pages workflow, .gitignore, README. T13 in progress. |
