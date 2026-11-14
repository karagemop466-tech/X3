# COORDINATION.md — Shared Task Board

This is the shared task board for the **X3** NFL analytics project. Multiple agent
sessions may work on this repo at the same time; this file is the single source of
truth for task ownership and status. **Read it before starting any task.**

## Session registry

- Current session ID: **`session-arena-3dbc4678-x3`**
- Session branch: **`arena/3dbc4678-x3`** (fixed by the Arena platform — all work for
  this session is committed and pushed to this branch only; the branch is not
  renamed and no other branch is created for this session).
- Base commit (branch point from `main`): `e12423044baef53c007fce7d1d3f45eeaf0a7e29`
- Date of work: **2026-11-14**

## Conventions

- **Claim a task** by writing your session ID and the exact file scope here, then
  `git commit` and `git push` that claim **immediately**. Never start a task another
  session has claimed.
- **Keep scopes non-overlapping.** If a task requires editing a file owned by another
  session, log the request here instead of editing it.
- **Status values:** `unclaimed`, `in progress`, `done`, `needs review`.
  `needs review` = published on the *Flagged for Review* page and does not block work.
- **Make small, frequent commits.** Run `git pull --rebase` before every push.
- **Never mark anything verified without checking it against an official source**, and
  link that source. Every data table row carries a source link; unverifiable values are
  left blank and flagged as `unverified`.
- **Shared outputs** (the site's index/navigation and the consolidated data tables) are
  changed only by the **final integration session** once all other tasks are done.
- **Handoff:** if a session crashes or a claim is older than 60 minutes with no commits,
  any other session may take over and must note the handoff here.

## Task board

| # | Task | Status | Owner (session) | File scope | Notes |
|---|------|--------|-----------------|------------|-------|
| 1 | Repo review & coordination setup | done | session-arena-3dbc4678-x3 | `COORDINATION.md`, `README.md` | Repo was a blank skeleton (`# X3` only). Irregularity flagged: no prior content to verify. |
| 2 | Data collection from official sources | done | session-arena-3dbc4678-x3 | `tools/build_site.py` (data) | Verified standings, injuries, schedule from NFL.com; Lions depth chart from official team site. Lines/correlations/leaderboard values left blank + unverified. |
| 3 | Site build (landing + subpages + styles) | done | session-arena-3dbc4678-x3 | `index.html`, `css/`, subpages, `tools/` | Static dashboard-style site, tables with per-row source links. 9 pages. |
| 4 | Executive summary | done | session-arena-3dbc4678-x3 | `executive-summary.html` | Key details, scope, status, risks. |
| 5 | Requirements & questions/answers | done | session-arena-3dbc4678-x3 | `requirements.html` | Pre-decision checklist + have/do-not-have gaps. |
| 6 | Suggestions section | done | session-arena-3dbc4678-x3 | `suggestions.html` | Dedicated suggestions for review before implementation. |
| 7 | Lines, signals, strategies, validation gates, correlations | done | session-arena-3dbc4678-x3 | `lines.html`, `leaderboard.html` | Strategy designs + gates; live line/correlation values unverified/blank. |
| 8 | Injuries & lineup/depth deficiencies | done | session-arena-3dbc4678-x3 | `injuries.html` | Injury tracking + 2nd/3rd/4th-string backup analysis (verified). |
| 9 | Flagged for Review page | done | session-arena-3dbc4678-x3 | `flagged.html` | Irregularities + unverified items with source links. |
| 10 | Verification log (line-by-line) | done | session-arena-3dbc4678-x3 | `verification.html` | Each row → official source link + status. |
| 11 | Build/link verification + integration + deploy + PR | in progress | session-arena-3dbc4678-x3 | `tools/check_links.py`, `COORDINATION.md` | Link check passed (297 links, no broken). Merge + Pages deploy + PR record pending. |

## Claim log

- **2026-11-14** — `session-arena-3dbc4678-x3` claims all tasks (no other sessions
  present; no competing claims). Branch is fixed to `arena/3dbc4678-x3` by the
  platform, so all tasks are executed sequentially on this one branch with
  non-overlapping file scopes. Claim committed and pushed.

## Verified sources (official / trusted)

| Source | URL | Used for | Fetched |
|--------|-----|----------|---------|
| NFL standings | https://www.nfl.com/standings/league/2026/reg | 32-team standings, PF/PA, net pts | 2026-11-14 |
| NFL injury report | https://www.nfl.com/injuries/league/2026/reg | Week 10 injuries (player/practice/game status) | 2026-11-14 |
| NFL schedule | https://www.nfl.com/schedules/ | Week 10 games, dates/times/networks | 2026-11-14 |
| Detroit Lions depth chart | https://www.detroitlions.com/team/depth-chart | Lions offense/defense starter→4th string | 2026-11-14 |

## Verification performed

- Each data table row was fetched from the official source listed and checked against
  the page content. Only values present on the official page were recorded; nothing was
  inferred or filled in.
- `python3 tools/check_links.py` → **OK**: 9 pages, 297 links checked, no broken
  internal links.
- Unverifiable data types (betting lines, correlation values, leaderboard performance)
  are left **blank** and flagged `unverified`; no values were inferred.

## Irregularities flagged for review

1. **Repository was a blank skeleton** (`README.md` contained only `# X3`); there was no
   prior code, data, or documentation to review.
2. **Betting lines are not published by the NFL.** No official source confirms line
   values; all line values are left blank and flagged `unverified`.
3. **Correlation values and leaderboard performance** require a data pipeline and
   backtest that does not yet exist; values are left blank and flagged `unverified`.
4. **Injury extraction inconsistency.** During fetch, a non-Vikings player (Kyler Murray)
   appeared under the Minnesota Vikings block, and the KC/IND blocks were only partially
   captured. Those blocks were excluded to avoid inaccuracy; re-pull required.
5. **Depth chart is labeled "Unofficial."** The Lions depth chart on the official team
   site is titled "2026 Unofficial Depth Chart Compiled by Lions Football Communications."
   It is the team's official published depth chart but carries an unofficial label;
   game-day inactives remain authoritative.
6. **Standings page title had unrendered template placeholders** (`$year$`,
   `$displayname$`); the standings table data itself was verified from the page body.
7. **Kerby Joseph depth-chart role needs confirmation.** Listed Out on the injury report
   but not a listed starter on the Lions depth chart; exact role requires confirmation.

All items above are published on the *Flagged for Review* page with source links.

## PR & merge record

- **PR #7**: https://github.com/karagemop466-tech/X3/pull/7
  - Title: "X3: NFL lines, signals & strategy analytics site"
  - Base: `main` · Head: `arena/3dbc4678-x3`
  - Created: 2026-11-14
  - Status: created; merge in progress (do not auto-merge; merge explicitly).
