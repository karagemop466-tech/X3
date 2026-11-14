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
| 2 | Data collection from official sources | in progress | session-arena-3dbc4678-x3 | `data/*.json`, `tools/data.py` | Verified standings, injuries, schedule from NFL.com. Lines/correlations/leaderboard values pending. |
| 3 | Site build (landing + subpages + styles) | in progress | session-arena-3dbc4678-x3 | `index.html`, `css/style.css`, subpages | Static dashboard-style site, tables with per-row source links. |
| 4 | Executive summary | in progress | session-arena-3dbc4678-x3 | `executive-summary.html` | Key details, scope, status, risks. |
| 5 | Requirements & questions/answers | in progress | session-arena-3dbc4678-x3 | `requirements.html` | Clear list of questions, information, answers needed before decisions; gaps. |
| 6 | Suggestions section | in progress | session-arena-3dbc4678-x3 | `suggestions.html` | Dedicated suggestions for review before implementation. |
| 7 | Lines, signals, strategies, validation gates, correlations | in progress | session-arena-3dbc4678-x3 | `lines.html`, `leaderboard.html` | Strategy designs + gates; live line/correlation values unverified/pending. |
| 8 | Injuries & lineup/depth deficiencies | in progress | session-arena-3dbc4678-x3 | `injuries.html` | Injury tracking + 2nd/3rd/4th-string backup context. |
| 9 | Flagged for Review page | in progress | session-arena-3dbc4678-x3 | `flagged.html` | Irregularities + unverified items with source links. |
| 10 | Verification log (line-by-line) | in progress | session-arena-3dbc4678-x3 | `verification.html` | Each row → official source link + verification status. |
| 11 | Build/link verification + integration + deploy + PR | pending | session-arena-3dbc4678-x3 | `tools/check_links.py`, `verification.html` | Link check, merge to main, GitHub Pages deploy, PR record. |

## Claim log

- **2026-11-14** — `session-arena-3dbc4678-x3` claims all tasks (no other sessions
  present; no competing claims). Branch is fixed to `arena/3dbc4678-x3` by the
  platform, so all tasks are executed sequentially on this one branch with
  non-overlapping file scopes. Claim committed and pushed.

## Verified sources (official / trusted)

- NFL standings: https://www.nfl.com/standings/league/2026/reg (fetched 2026-11-14)
- NFL injury report: https://www.nfl.com/injuries/ (fetched 2026-11-14)
- NFL schedule: https://www.nfl.com/schedules/ (fetched 2026-11-14)
- NFL stats: https://www.nfl.com/stats/ (referenced)

## Irregularities flagged for review

- **Repo is a blank skeleton** (`README.md` contained only `# X3`); there was no prior
  code, data, or documentation to review. See `flagged.html`.
- **Betting lines are not published by the NFL.** No "official" NFL source publishes
  betting lines, so line values are left blank and flagged `unverified` on `lines.html`.
- **Correlation values and leaderboard performance** require a data pipeline and
  backtest that does not yet exist; values are left blank and flagged `unverified`.
- **Fetched page titles contain unrendered template placeholders** (`$year$`,
  `$displayname$`) on the standings page; table data was verified from the page body.
