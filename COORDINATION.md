# COORDINATION.md — X3 shared task board

Created: 2026-11-14 (UTC). Owner of all tasks in this file: session on branch `arena/0c38f465-x3`.

## Branch / session rules used

- The session branch is fixed by Arena: **`arena/0c38f465-x3`** (branched from `main` @ `e124230`). The
  `session-<id>/<task>` naming in the brief could not be used, because the platform instructs this session to work
  only on its assigned branch. All task claims, commits and pushes therefore happen on `arena/0c38f465-x3`.
- Only one session has worked this repo so far. No other session claims appear in this file, so no conflicts exist.
- Shared outputs (site index, navigation, combined data) were produced by the same session acting as the
  **final integration session**. Integration steps are logged in the Integration log below.

## Status legend

- `unclaimed` — nobody has started it
- `in progress` — claimed by a session
- `done` — finished, sources and verification recorded below
- `needs review` — published on the **Flagged for Review** page; does not block anything
- `blocked` — cannot proceed without missing data (listed in Questions page)

## Task board

| ID | Task | Status | Owner (session) | Files / scope | Notes |
|----|------|--------|-----------------|---------------|-------|
| T01 | Repo review, irregularities | done | arena/0c38f465-x3 | README.md, repo config | See "Repo review" below |
| T02 | Official 2026 Week 10 injury report capture (all designated rows) | done | arena/0c38f465-x3 | data/injury_report_2026_wk10.csv | 205 rows (66 Out, 10 Doubtful, 84 Questionable, 45 LP/DNP without designation); source NFL.com; cross-checked against NFL.com Week 10 news article designations |
| T03 | 2026 season official key dates | done | arena/0c38f465-x3 | data/schedule_2026_key_dates.csv | Official NFL press release |
| T04 | Source registry (official links + fetch status) | done | arena/0c38f465-x3 | data/sources.csv | |
| T05 | Strategy framework, validation gates, leaderboard shell | done (no validated strategies) | arena/0c38f465-x3 | data/strategies.csv, data/correlations.csv | No historical odds/results data was retrieved, so no performance or correlation values are published |
| T06 | Depth chart / starter-backup mapping (defense & offense) | blocked | — | data/depth_gaps.csv (planned) | Requires official team depth charts for 32 teams; not retrieved this session. Logged as a question. |
| T07 | Suggestions section for review (no implementation) | done | arena/0c38f465-x3 | data/suggestions.csv | Awaiting user decision |
| T08 | Questions / information gap list | done | arena/0c38f465-x3 | data/questions.csv | |
| T09 | Requirements tracker | done | arena/0c38f465-x3 | data/requirements.csv | |
| T10 | Executive summary | done | arena/0c38f465-x3 | docs/executive-summary.html (generated) | |
| T11 | GitHub Pages site build (docs/) + link check | done (scripts/check_site.py: 352 table rows, 0 without link/flag, 0 broken internal links) | arena/0c38f465-x3 | docs/, scripts/build_site.py | |
| T12 | Flagged for Review page | done | arena/0c38f465-x3 | data/flags.csv, docs/flagged.html | Published, does not block merge |
| T13 | Integration: re-verify combined data, build, PR, merge, Pages check | in progress | arena/0c38f465-x3 | COORDINATION.md | See Integration log |

## Repo review (T01)

Checked: `git status`, `git log`, `README.md`, remote config, GitHub Pages config.

| Item | Finding | Source / link |
|------|---------|---------------|
| Repo content | Only `README.md` (`# X3`) and one commit `e124230 Initial commit`. No code, data, license or `.gitignore`. | https://github.com/karagemop466-tech/X3 |
| Pages | GitHub Pages is already enabled: legacy build from `main` at `/` (root), status `built`. Live URL: https://karagemop466-tech.github.io/X3/ | GitHub API `repos/karagemop466-tech/X3/pages` |
| COORDINATION.md | Did not exist; created by this session. | — |
| Brief formatting | The brief's `session-&amp;lt;id&amp;gt;` placeholders are HTML-escaped and the link text is `http://COORDINATION.md`; both are garbled. Interpreted as `session-<id>/<task>` and `COORDINATION.md`. | Flagged |
| Branch rule conflict | Brief asks for `session-<id>/<task>` branches; platform rule requires the assigned branch. Platform rule followed. | Flagged |
| Pages source | Site is published from `docs/` after merge; Pages source must be switched from `/` to `/docs` (see Integration log). | Flagged |

## Integration log

- 2026-11-14: T02–T12 completed by the same session. Pending: T13 steps (build, link check, PR, merge, Pages verification).

### Verification log (T02, T03, T04)

- Injury report: fetched all 8 chunks of https://www.nfl.com/injuries/league/2026/reg10 (as accessed 2026-11-14). Rows transcribed from that page; a separate NFL.com news article (https://www.nfl.com/news/nfl-week-10-injury-report-2026-season) lists the Sunday designations for every team on the report (Chiefs, Vikings, Dolphins, Bills, Titans, Rams, Cardinals, Packers, etc.) and matches the transcribed Out, Doubtful and Questionable entries.
- Schedule: NFL Media 2026 schedule announcement (https://media.nfl.com/football-information/2026/news/2026-nfl-schedule-announced), chunk 1 read in full.
- Legal: Penal Code Art. 185 from the Ministry of Justice translation (https://www.japaneselawtranslation.go.jp/en/laws/view/3581/tb); TOC fetched, Article 185 text from the search excerpt of the same page. Manual review recommended.

### Irregularities (see docs/flagged.html)

- F01-F16 in data/flags.csv (legal exposure, conflicting NFL.com pages, injury field gaps, name/position variants, no odds/depth data, repo and branch-rule issues).

## Integration log

- 2026-11-14: T02-T12 completed by the same session. Site built from data/ with 0 broken internal links.
- Pending in this session: commit, push to arena/0c38f465-x3, pull request to main, merge, switch Pages source to main /docs, confirm Pages deploy.
