# COORDINATION.md

Shared task board for the X3 (NFL) project.
Integrated branches: `arena/1a771fcd-x3` (this session) and `arena/d667d44d-x3` (prior session, merged to `main` via PR #1).
Status legend: unclaimed | in progress | done | needs review

## Sessions
- `arena/1a771fcd-x3` — current integration session (branch → main)
- `arena/d667d44d-x3` — prior session; root decision-lab site + Pages workflow merged to `main` (PR #1)

## Tasks (all done)

| # | Task | Status | Owner | File scope | Sources / verification | Irregularities |
|---|------|--------|-------|------------|------------------------|----------------|
| 1 | Repository audit / coordination board | done | arena/d667d44d-x3 | `COORDINATION.md` | Repo began with only a 4-byte README.md; no data, site, or board | none |
| 2 | NFL evidence & research (official sources) | done | arena/d667d44d-x3 | `docs/**`, root sources | nfl.com/injuries, nfl.com/stats, operations.nfl.com 2026 rulebook, docs.github.com/pages | Some candidate URLs 404'd; replaced with working official URLs |
| 3 | Landing page, navigation, data tables, Pages integration | done | arena/d667d44d-x3 | root site files | Six static pages parsed; all relative links verified | No deployed Pages URL asserted until GitHub confirms |
| 4 | GitHub Pages static site: landing page + category subpages (this session) | done | arena/1a771fcd-x3 | `site/`, `pages/` | All HTML validated; internal links checked | HTML pages parse cleanly |
| 5 | Executive summary | done | arena/1a771fcd-x3 | `pages/executive-summary.html` | nfl.com/injuries; Sportradar feeds docs | Betting lines & props: no official source identified |
| 6 | Suggestions & decision framework (questions, info, answers, missing-info discovery) | done | arena/1a771fcd-x3 | `pages/suggestions.html` | nfl.com/injuries; Sportradar feeds docs | All data cells blank/unverified pending official fetch |
| 7 | Flagged for Review page (unverified items + irregularities) | done | arena/1a771fcd-x3 | `pages/flagged-for-review.html` | nfl.com/injuries; Sportradar feeds docs | I-01 empty repo at branch point; I-02 no NFL lines source; I-03 fetch blocked |
| 8 | NFL lines origination: strategies, signals, validation gates, correlations, single/parlay/prop combos, leaderboard design | done | arena/1a771fcd-x3 | `pages/strategies.html` | Sportradar docs; nfl.com/injuries (cycle only) | No strategy/correlation/reward value confirmed from official source |
| 9 | Injury & backup (depth-chart) tracking system design | done | arena/1a771fcd-x3 | `pages/injuries.html` | nfl.com/injuries; Sportradar docs | All depth values blank/unverified |
| 10 | Sources page (official sources only) | done | arena/1a771fcd-x3 | `pages/sources.html` | nfl.com/injuries; Sportradar docs | No official NFL betting-lines or player-prop source identified |
| 11 | GitHub Actions Pages deploy workflow | done | arena/1a771fcd-x3 | `.github/workflows/pages.yml` | docs.github.com/pages | Initial branch run failed (no steps); main run succeeded |
| 12 | Integration: merge branches, re-verify combined data, confirm site builds with no broken links | done | arena/1a771fcd-x3 | all | 136 refs checked across root/pages/site; NO BROKEN LINKS | Merge conflicts resolved on 3 shared files without discarding either session |
| 13 | PR from integration branch to main; merge; confirm Pages deploy; record PR link & result | done | arena/1a771fcd-x3 | `COORDINATION.md` | PR #3 + PR #5 | See PR log below |

## PR log
- PR #3 (integration): https://github.com/karagemop466-tech/X3/pull/3 — `arena/1a771fcd-x3` → `main`, merged via `gh pr merge --merge`, merge commit `e1eb287`.
- PR #5 (link fix): https://github.com/karagemop466-tech/X3/pull/5 — `arena/1a771fcd-x3` → `main`, merged via `gh pr merge --merge`, merge commit `d67dee1`. Added root `assets/style.css`, fixed `site/index.html` nav links.
- Prior session PR #1: https://github.com/karagemop466-tech/X3/pull/1 — `arena/d667d44d-x3` → `main`, merged.

## Live site
- URL: https://karagemop466-tech.github.io/X3/
- Pages status: built (source: `main` branch root `/`, build_type: legacy)
- Last main workflow runs: "Deploy X3 NFL site to GitHub Pages" = success; "pages build and deployment" = success

## Verification performed
- Parsed all HTML pages; no unclosed tags.
- Link check: 136 refs checked across `*.html` in root/pages/site (anchors + CSS `<link>` + `<script src>`); NO BROKEN LINKS.
- Every table row carries a source link to an official site; unconfirmed values left blank and flagged unverified; nothing inferred.

## Notes / irregularities (published on Flagged for Review page)
- Sandbox outbound network restricted to github.com / api.github.com / codeload.github.com / registry.npmjs.org / pypi.org / files.pythonhosted.org; nfl.com not directly fetchable — verification via web_search, cited by URL.
- Repo was empty at branch point (only README.md).
- No official NFL betting-lines or player-prop publication identified (values left blank/unverified).
- Direct fetch of nfl.com blocked; row-level injury/depth data not confirmed.
- All strategy, correlation, depth, and reward values are blank/unverified pending official fetch.
- No manual input; all entries sourced or flagged unverified.

## Claims log
- `arena/d667d44d-x3` claimed root site files, `docs/**`, `COORDINATION.md` (PR #1, merged).
- `arena/1a771fcd-x3` claims `site/`, `pages/`, and integration (PR #3 + PR #5, merged). Shared files resolved without discarding either session's work.

---

---

## Session arena/0c38f465-x3 (integration, this branch)

Branch: `arena/0c38f465-x3`. Work is done only on this branch. The `session-<id>/<task>` naming in the brief was not used, because the platform requires this session's assigned branch.

### Status legend
unclaimed | in progress | done | needs review | blocked

### Task board (arena/0c38f465-x3)

| ID | Task | Status | Files / scope | Result |
|----|------|--------|---------------|--------|
| T01 | Repo review and irregularities | done | README.md, repo settings | Repo began with README only; irregularities in data/flags.csv (F12-F15) |
| T02 | Official Week 10 2026 injury report (designated rows) | done | data/injury_report_2026_wk10.csv | 205 rows: 66 Out, 10 Doubtful, 84 Questionable; source NFL.com |
| T03 | 2026 season key dates | done | data/schedule_2026_key_dates.csv | 12 verified items; 3 unverified left blank and flagged |
| T04 | Source registry | done | data/sources.csv | 11 entries with fetch status |
| T05 | Strategy framework, gates, leaderboard shell | done (no validated strategies) | data/strategies.csv, data/gates.csv | No historical odds/results data retrieved, so no ROI, CLV, sample or correlation values |
| T06 | Starter-to-backup (depth chart) mapping | blocked | none | Needs official team depth charts for 32 teams; not retrieved this session (Questions Q05, Suggestion S02) |
| T07 | Suggestions for review (nothing implemented) | done | data/suggestions.csv | 10 suggestions awaiting decision |
| T08 | Questions and information gaps | done | data/questions.csv | 12 open questions |
| T09 | Requirements tracker | done | data/requirements.csv | 16 items |
| T10 | Executive summary | done | docs/executive-summary.html | Generated from data/ |
| T11 | Dashboard site in docs/ and link/row check | done | docs/, scripts/build_site.py, scripts/check_site.py | 13 pages; 352 table rows; 0 rows without link or flag; 0 broken internal links |
| T12 | Flagged for Review page | done | data/flags.csv, docs/flagged.html | 16 flags; non-blocking |
| T13 | Integration: merge main, re-verify, PR, merge, Pages check | in progress | COORDINATION.md | See integration log |

### Repo review (T01)

| Item | Finding | Link |
|------|---------|------|
| Repo content at branch point | README.md (`# X3`) and one commit; no code, data, licence or .gitignore | https://github.com/karagemop466-tech/X3 |
| Pages | Enabled; build type legacy, source `main /` at branch point; the token cannot change Pages settings (HTTP 403) | https://karagemop466-tech.github.io/X3/ |
| Brief formatting | The `session-&amp;lt;id&amp;gt;` placeholders and the `http://COORDINATION.md` link are HTML-escaped; interpreted as `session-<id>/<task>` and `COORDINATION.md` | Flag F14 |
| Branch rule | The brief asks for `session-<id>/<task>` branches; the platform requires the assigned branch. The platform rule was followed | Flag F13 |

### Verification log (T02-T04)

- Injury report: all 8 chunks of https://www.nfl.com/injuries/league/2026/reg10 were read (accessed 2026-11-14). Rows were transcribed from that page. The NFL.com Week 10 news article (https://www.nfl.com/news/nfl-week-10-injury-report-2026-season) lists the Sunday designations for the teams it covers (Chiefs, Vikings, Dolphins, Bills, Titans, Rams, Cardinals, Packers and others); those match the transcribed Out, Doubtful and Questionable entries.
- Schedule: https://media.nfl.com/football-information/2026/news/2026-nfl-schedule-announced, chunk 1 read in full; chunk 2 not re-read.
- Legal: https://www.japaneselawtranslation.go.jp/en/laws/view/3581/tb (Penal Code). The TOC was fetched; Article 185 text comes from a search excerpt of the same page. Manual review recommended.

### Overlap notes

- `arena/64164906-x3` (in progress on main's history: official-source registry, fetcher and CI data validation) overlaps with `data/sources.csv` in this branch. Coordinate before merging; one registry is preferable.
- The earlier root-level site was not deleted. Its landing page moved unchanged to `legacy/index.html` (links fixed to `../`). `style.css` was copied to `legacy/style.css`. The root `index.html` is now a redirect to `docs/index.html`. Other root pages (`strategy.html`, `data.html`, etc.) are unchanged. `site/` and `pages/` (session 1a771fcd) are unchanged.
- `.github/workflows/pages.yml` is unchanged from main except one added step that runs `scripts/check_site.py`.

### Integration log (arena/0c38f465-x3)

- 2026-11-14: Tasks T01-T12 done on this branch (commit `2a4825e`).
- 2026-11-14: PR #4 (this branch to main) showed merge conflicts because `main` had advanced (PRs #1 and #3 from other sessions). Resolved by merging `origin/main` into this branch (no rebase, no history rewritten), commit `a3fdf3d`. Conflicts: `COORDINATION.md` (kept main's board and appended this section) and `README.md` (kept main's README and appended this session's layout).
- 2026-11-14: The first integration tried to change the Pages source to a workflow. The token returned HTTP 403 for the Pages settings change, so that approach was dropped. The Pages source stays legacy `main /`. The dashboard is served at `/docs/`, and the root `index.html` redirects there. Changing the source needs a repo admin (flag F15).
- 2026-11-14: `main` advanced again with PRs #5 and #6 from session `arena/1a771fcd-x3`. Merged into this branch without editing their files. COORDINATION.md keeps their full text, followed by this section.
- Pending: merge PR #4; confirm the Pages build from `main`; confirm `https://karagemop466-tech.github.io/X3/` redirects to `docs/` and that `/docs/` and `/legacy/` respond. Record the PR link and merge result below.

### PR and deploy log (this session)

- PR #4: https://github.com/karagemop466-tech/X3/pull/4 (`arena/0c38f465-x3` to `main`). Result: pending at the time of this entry; updated below after merge.

---

## Session `arena/3dbc4678-x3` (appended section)

Session ID: `session-arena-3dbc4678-x3`. Branch: `arena/3dbc4678-x3` (platform-fixed).
Claimed all tasks on 2026-11-14; no competing claims. Built a parallel self-contained
site and integrated it additively into `main` (did not overwrite the integrated
`docs/` dashboard or the shared root `index.html` navigation).

### This session's task board

| # | Task | Status | File scope |
|---|------|--------|------------|
| 1 | Repo review & coordination setup | done | `COORDINATION.md`, `README.md` |
| 2 | Data collection from official sources | done | `tools/build_site.py` (data) |
| 3 | Site build (landing + subpages + styles) | done | root category pages, `tools/` |
| 4 | Executive summary | done | `executive-summary.html` |
| 5 | Requirements & questions/answers | done | `requirements.html` |
| 6 | Suggestions section | done | `suggestions.html` |
| 7 | Lines, signals, strategies, gates, correlations | done | `lines.html`, `leaderboard.html` |
| 8 | Injuries & lineup/depth deficiencies | done | `injuries.html` |
| 9 | Flagged for Review page | done | `flagged.html` (root) |
| 10 | Verification log (line-by-line) | done | `verification.html` |
| 11 | Build/link verification + integration + deploy + PR | done | `tools/check_links.py`, `COORDINATION.md` |

### Verified sources (this session)

- NFL standings: https://www.nfl.com/standings/league/2026/reg (fetched 2026-11-14)
- NFL injury report: https://www.nfl.com/injuries/league/2026/reg (fetched 2026-11-14)
- NFL schedule: https://www.nfl.com/schedules/ (fetched 2026-11-14)
- Detroit Lions depth chart: https://www.detroitlions.com/team/depth-chart (fetched 2026-11-14)

### Verification performed (this session)

- Each data row fetched from the official source and checked against page content;
  nothing inferred. `python3 tools/check_links.py` → OK: 9 pages, 297 links, no broken
  internal links.
- Betting lines, correlation values, leaderboard performance left blank + `unverified`.

### Irregularities flagged (this session)

- Repo was a blank skeleton at start.
- Betting lines have no official NFL source → blank + unverified.
- Correlations / leaderboard performance require a data pipeline → blank + unverified.
- Injury fetch inconsistency (MIN block contamination; KC/IND partial) → excluded + flagged.
- Lions depth chart labeled "Unofficial" → flagged.
- Standings page title had unrendered template placeholders → data verified from body.
- Kerby Joseph depth-chart role needs confirmation → flagged.

### Merge conflict resolution (this session)

- PR #7 (`arena/3dbc4678-x3` → `main`) reported merge conflicts because `main` had
  advanced with PRs #4–#6 from other sessions and both sides touched shared files.
- Resolved **additively without discarding other sessions' work**: kept `main`'s
  integrated `index.html` (redirect), `README.md`, `COORDINATION.md`, and `flagged.html`,
  and appended this session's content/pages. My standalone category pages and `tools/`
  were added (no collision). Logged here per protocol.

### PR & merge record (this session)

- PR #7: https://github.com/karagemop466-tech/X3/pull/7
  - Title: "X3: NFL lines, signals & strategy analytics site"
  - Base: `main` · Head: `arena/3dbc4678-x3`
  - Created: 2026-11-14 · Merged: 2026-11-14 (merge commit `8f9e491`).
  - Merge conflict (shared `README.md`, `COORDINATION.md`, `index.html`, `flagged.html`)
    resolved additively: kept `main`'s integrated versions and appended this session's
    content/pages; nothing from other sessions discarded.
  - Result: **MERGED** into `main`. GitHub Pages status: **built** (source `main /`).
    Live site: https://karagemop466-tech.github.io/X3/ — root redirects to the
    dashboard; this session's pages served at
    `/executive-summary.html`, `/requirements.html`, `/suggestions.html`,
    `/lines.html`, `/leaderboard.html`, `/injuries.html`, `/verification.html`,
    `/flagged.html`. Verified live via HTTP fetch on 2026-11-14.

---

## Session `arena/7e632805-x3` (appended section)

Session ID: `session-arena-7e632805-x3`. Branch: `arena/7e632805-x3` (platform-fixed).
Branched from `main` @ `e124230`, which at branch time contained only `README.md`.
By the time this session pushed, `main` had advanced through PRs #1–#9 from four other
sessions. This session therefore integrated **additively**: no other session's file was
modified or deleted.

### File scope claimed (this session)

| Path | Purpose |
|------|---------|
| `tools/nfl_data.py` | Verified data transcribed from official pages. Sole source of fact. |
| `tools/site_content.py` | Requirements, questions, suggestions, strategies, gates, leaderboard spec. |
| `tools/build_dashboard.py` | Deterministic build → `dashboard/**` + `dashboard/data/*.json`. |
| `dashboard/**` | 18-page dashboard. Served at `/dashboard/` on GitHub Pages. |
| `.gitignore` | Python/cache ignores. |

**Deliberately not touched:** `index.html`, `docs/**`, `site/**`, `pages/**`, `legacy/**`,
`data/**`, `scripts/**`, `tools/build_site.py`, `tools/check_links.py`,
`.github/workflows/pages.yml`. A filename collision on `tools/build_site.py` was avoided by
naming this session's builder `tools/build_dashboard.py`, and a directory collision on
`site/` was avoided by emitting to `dashboard/`.

### Task board (arena/7e632805-x3)

| # | Task | Status | Files | Result |
|---|------|--------|-------|--------|
| T01 | Coordination board | done | `COORDINATION.md` | Board kept from main; this section appended |
| T02 | Repo audit line by line, flag irregularities | done | `dashboard/repo-review.html` | Base commit `e124230`: 1 file, 1 commit, 4 bytes |
| T03 | Requirements inventory | done | `dashboard/requirements.html` | 24 requirements with acceptance criteria; 19 done, 5 partial |
| T04 | Executive summary | done | `dashboard/index.html`, `dashboard/executive-summary.html` | 12 findings with source links |
| T05 | Open-questions register | done | `dashboard/questions.html` | 20 questions; 13 blocking |
| T06 | Suggestions + decision-path page | done | `dashboard/suggestions.html` | 16 suggestions; 2 adopted, 13 proposed, 1 deferred |
| T07 | Own-line origination, strategies, gates, leaderboard | done | `dashboard/lines.html`, `strategies.html`, `validation.html`, `leaderboard.html` | 10 strategies, 12 blocking gates |
| T08 | Correlation values | done | `dashboard/correlation.html` | 4 computed, 8 deliberately blank |
| T09 | Injury & depth-chart deficiency tracking | done | `dashboard/injuries.html`, `depth-charts.html` | 345 injury rows, 31/32 charts, 76 starter-absent positions |
| T10 | Source register + verification pass | done | `dashboard/sources.html` | 4 league sources + 32 club sources |
| T11 | Flagged for Review page | done | `dashboard/flagged.html` | 12 flags, all non-blocking |
| T12 | Static site build | done | `dashboard/**` | 18 pages, 25 tables |
| T13 | Pages enablement + deploy verification | done | (existing workflow reused) | See deploy log |
| T14 | Re-verify, link check, PR + merge | done | `COORDINATION.md` | See PR log |

### Verified sources (this session)

| Dataset | Official URL | Rows |
|---------|--------------|------|
| 2026 league standings | https://www.nfl.com/standings/league/2026/REG | 32 clubs |
| Week 10 injury report | https://www.nfl.com/injuries/ | 345 player rows |
| Week 10 schedule | https://www.nfl.com/schedules/2026/by-week/week-10 | 14 games + 4 byes |
| Team directory | https://www.nfl.com/teams/ | 32 clubs |
| Club depth charts | `<club>.com/team/depth-chart` | 31 of 32 clubs |

Every row in `dashboard/sources.html` links to the club's official site.

### Verification performed (this session)

- **Row-level sourcing.** Checked programmatically: every row in the data pages
  (standings 32/32, schedule 18/18, injuries 345/345, depth 108/108, lines 46/46,
  sources 36/36) carries either an external official URL or an explicit `UNVERIFIED`
  marker. Zero rows fall outside both categories.
- **Structure.** 18 pages, 25 tables, 0 column mismatches, 0 broken internal links,
  all 18 pages return HTTP 200 under a local server.
- **Depth-chart cross-checks.** Two internal consistency checks were run: 17 players
  ruled Out/Doubtful are absent from their own club's chart, and 0 players were matched
  to a different club's chart.
- **Nothing inferred.** Blank cells render `UNVERIFIED`. Model output is badged `DERIVED`
  and its parameters are printed on the page.

### Computed results (derived, not fact)

- Points for per game vs. win percentage: **r = +0.6984**
- Points against per game vs. win percentage: **r = −0.6636**
- Net points per game vs. win percentage: **r = +0.8781**
- Home win percentage vs. road win percentage: **r = +0.3501**
- All four are Pearson r across the 32 clubs from the official standings.
- 76 starter-absent positions identified; 17 defensive starters Out or Doubtful.

### Irregularities flagged (this session)

| ID | Severity | Item |
|----|----------|------|
| F-01 | Medium | All 31 readable depth charts are self-labelled "unofficial" by the club |
| F-02 | Medium | 27 of 32 charts print no as-of date, so freshness is unprovable |
| F-03 | High | Detroit lists Cade Mays as starting centre; official injury report lists him Out |
| F-04 | Medium | Philadelphia lists Hollywood Brown and Fred Johnson after waiving both on 2026-11-13 |
| F-05 | High | Houston publishes its depth chart only as an image; no rows readable |
| F-06 | High | No market lines exist anywhere in the system |
| F-07 | High | No game log ingested, so no HFA and no schedule adjustment |
| F-08 | Medium | All model lines produced with HFA = 0.0, uncalibrated |
| F-09 | Low | 185 of 345 injury rows have a blank game status; 21 of those also did not practise |
| F-11 | Medium | 17 Out/Doubtful players are absent from their own club's chart |
| F-12 | Low | Base commit has no licence, .gitignore, CI, tests or branch protection |

### Merge conflict resolution (this session)

- `main` had advanced through PRs #1–#9 from four sessions before this branch pushed.
- Resolved **additively without discarding other sessions' work**: kept `main`'s
  `COORDINATION.md` in full (all four prior session sections intact) and appended this
  section; kept `main`'s `README.md` and appended a marked section.
- Avoided collisions rather than resolving them: `tools/build_dashboard.py` (not
  `build_site.py`) and `dashboard/` (not `site/`).
- Reused `main`'s existing `.github/workflows/pages.yml` rather than adding a competing
  workflow; it uploads `path: '.'`, so `dashboard/` is published automatically.

### PR & merge record (this session)

- **PR #11**: https://github.com/karagemop466-tech/X3/pull/11
  - Title: "Verified-data NFL dashboard: 345 injury rows, 31 depth charts, 76 starter-absent positions"
  - Base: `main` · Head: `arena/7e632805-x3`
  - Created: 2026-11-14 · **Merged: 2026-11-14** (merge commit `c2d73b0`), via `gh pr merge --merge`, without waiting for approval.
  - Result: **MERGED**.
- **PR #14** (follow-up): https://github.com/karagemop466-tech/X3/pull/14
  - Title: "Correct prose counts that drifted from the data; make all counts computed at build time"
  - Created: 2026-11-14 · **Merged: 2026-11-14** (merge commit `a26e232`), via `gh pr merge --merge`.
  - Fixed three prose counts that had drifted from the tables (294→345 injury rows,
    4/6→5/5 strategy split, 8→7 pending correlations). All prose counts are now computed
    from the data at build time and the build aborts on any unfilled token.
- **Pages deploy**: workflow run
  [43550485139](https://github.com/karagemop466-tech/X3/actions/runs/43550485139)
  ("Deploy X3 NFL site to GitHub Pages", the run for PR #14) — build **success**, deploy **success**.
  (PR #11's own run [43549974941](https://github.com/karagemop466-tech/X3/actions/runs/43549974941)
  also succeeded.)
  Pages status: **built** (source `main /`, build_type legacy).
  This session's pages are served at **`/dashboard/`**; verified live at
  https://karagemop466-tech.github.io/X3/dashboard/index.html on 2026-11-14.
- **Conflicts resolved without discarding work**: `main` advanced twice during this PR
  (PR #8 from `arena/972ad7a5-x3`, and earlier PRs #1–#9). Both `COORDINATION.md` and
  `README.md` conflicts were resolved as a **union**, keeping every line from the other
  session. Verified programmatically: zero lines from `origin/main` missing from the
  merged result.

### Self-audit correction (this session)

A final read-through of the rendered site found three counts in the prose that had drifted
from the tables they described (injury rows stated as 294 vs the actual 345; strategy
split stated as 4/6 vs the actual 5/5; correlations stated as 8 pending vs the actual 7).
All prose counts are now **computed from the data at build time** via tokens, and the build
**fails** if any token is left unfilled, so this class of error cannot recur. Corrected
values: 345 injury rows, 5 registered / 5 blocked strategies, 4 computed / 7 pending
correlations, 19 done / 5 partial requirements, 13 blocking questions.

### Open items needing an owner decision

- **Q-02 / Q-03 / F-06:** No official source publishes betting lines. The scoring layer
  cannot fire without a licensed or manually-recorded odds feed.
- **Q-16 / S-12:** Leaderboard rewards are specified as notional. Confirm before any
  season starts.
- **Q-17 / S-16:** Owner is in Tokyo, Japan. Whether originating lines and staking real
  money is lawful there is unresolved.

---

## Session `arena/972ad7a5-x3` — source-first decision dashboard

- **Status:** in progress; all work is on Arena's fixed branch `arena/972ad7a5-x3`, originally based on `e12423044baef53c007fce7d1d3f45eeaf0a7e29`.
- **Claim:** official-source research framework, executive summary, strategy/validation/correlation/lineup design, suggestions and flagged-review pages, and a responsive GitHub Pages dashboard. New implementation scope: `assets/data.js`, `assets/app.js`, `assets/site.css`, `lab/`, root Pages entry point, README, and dedicated checks. Existing `docs/`, `data/`, `pages/`, root category pages, and their history are being retained rather than overwritten.
- **Integration context:** upstream `main` advanced after the first dashboard commit, including the legacy `docs/` data site and the additive PR #7 site (merge `8f9e491`; follow-up PR #9 confirmed its deployment). The branch was rebased onto `origin/main` at `6bff6ef`; conflicts were resolved additively. Existing `docs/`, `pages/`, root category pages, and source data were restored/preserved. The new dashboard lives under `lab/`, and the root URL now redirects there while keeping the previous data dashboard at `/docs/`. The root Pages source remains `main:/`.
- **Evidence boundary:** the new research module contains hypotheses and source metadata, not NFL outcome/odds/injury values or measured performance. Earlier merged work already retains a 2026 Week 10 injury-report snapshot (205 rows) and key-date CSV in `data/` and `docs/`; these remain separate and are linked as an archive, not silently treated as inputs to the new module. No historical market prices, paired prop-event history, or league-wide ordinal depth-chart dataset has been verified for the new analysis.
- **Sources reviewed:** official NFL player/team statistics, schedules, team directory/roster, the 2026 Week 10 injury report, NFL Football Operations roster/rulebook/Next Gen Stats pages; NIST statistics references and scikit-learn model-evaluation documentation. Full source register and uses are in `assets/data.js` and the site.
- **Irregularity:** the NFL permalink `https://www.nfl.com/injuries/league/2025/reg1` returned a page title naming Week 10 of 2025 while the body heading said Week 1. No rows from that URL were copied. The separate 2026 `reg10` injury page was checked and its title/body both identify Week 10.
- **Verification after integration:** `python3 scripts/build_site.py` built 13 legacy `docs/` files; `python3 scripts/check_site.py` passed with 352 archived table rows and 0 rows without a source link or explicit flag, and no broken internal links; `python3 tools/check_links.py` passed (13 prior root pages, 315 links); the GitHub Pages workflow's HTML/link audit passed locally (31 pages). `python3 scripts/check_dashboard.py` passed for 12 root/lab HTML pages; `node --check` passed for all four dashboard/test scripts; `node scripts/check_data.js` passed with 20 registered sources and 61 source-backed research rows; `node scripts/check_render.js` passed for all 11 dashboard views, with every rendered table row linking to an approved NFL/NIST/scikit-learn host. Local HTTP smoke checks returned 200 for `/`, `/lab/index.html`, `/lab/lineups.html`, `/docs/injuries.html`, `/docs/index.html`, and the CSS/JS assets. GitHub Actions PR run [43549692954](https://github.com/karagemop466-tech/X3/actions/runs/43549692954) passed all six build steps; deployment was skipped as intended for a pull request. External links are registered/reviewed but not fetched by the local scripts.
- **PR:** [#8 — Build NFL evidence-first decision dashboard](https://github.com/karagemop466-tech/X3/pull/8), `arena/972ad7a5-x3` → `main`. The rebased branch is pushed; GitHub Actions PR build passed all site, legacy-data, and new-dashboard checks (deploy correctly skipped for PRs). PR mergeability is clean; merge is pending.

---

## Session arena-4856379c-x3 (this session)

Branch: `arena/4856379c-x3` (platform-assigned; used instead of the `session-<id>/<task>` naming, as
with earlier sessions). Claimed scope: `research/**`, `docs/pages/**`, `docs/data/**`,
`docs/style.css`, `tools/build_data_pages.py`, `tools/verify_site.py`; integration edits to the
shared outputs `docs/index.html`, `README.md`, `COORDINATION.md` (sanctioned for the integration
role). No other session's files were modified.

### Task board (arena-4856379c-x3)

| Task | Status | Files | Sources / verification | Irregularities |
|---|---|---|---|---|
| T1 Repo line-by-line audit | done | `research/repo-audit.md`, `docs/pages/repo-audit.html` | git inventory at `e124230` (README only, `# X3`) | README rewritten; LICENSE absent (F-05) |
| T2 Requirements inventory (28 items) | done | `docs/pages/requirements.html` | each status checked against repo contents | — |
| T3 Line origination + signal catalog S1–S8 | done | `research/line-origination.md`, `docs/pages/strategies.html` | Levitt 2004 (EJ, uchicago.edu PDF); Claremont thesis 2025; Skidmore thesis (digitalcoll.skidmore.edu/record/6451); community replication (GitHub) | model σ/HFA parameters blank (UNVERIFIED until calibrated) |
| T4 Validation gates G0–G8 (luck removal) | done | `research/validation.md`, `docs/pages/validation.html` | DSR Bailey & López de Prado 2014 (SSRN 2460551); PBO Bailey et al. 2015 (SSRN 2326253) | DSR/PBO thresholds are paper conventions (F-08) |
| T5 Correlation research | done | `research/correlation.md`, `docs/pages/correlation.html` | Davis 2018 via bettoredge (secondary); Skidmore thesis; industry SGP-tax sources (flagged) | no official numeric coefficients exist → blank + UNVERIFIED (F-03); estimation pipeline published |
| T6 Leaderboard competition design | done | `research/leaderboard.md`, `docs/pages/leaderboard.html` | NFL Big Data Bowl prizes/rubric (Kaggle 2021/2022/2027) | reward amounts blank (Q-01) |
| T7 Injury & deficiency tracker | done | `docs/data/injury-2026-week10.csv` (345 rows), `docs/pages/injuries.html`, `research/injury-tracking.md` | nfl.com/injuries Week-10 2026 (8 chunks, 2026-11-14); nfl.com/news headlines; nfl.com important-dates page | F-01 Lamar timeline conflict; F-02 roster pairings vs historical knowledge; F-04 depth charts 404 at the URLs tested (depth ranks left blank); F-07 rest-outs; F-09 blank-status rows; F-12 Henley LAC/DEN conflict |
| T8 Questions (15) + discovery paths | done | `docs/pages/questions.html` | known answers cite the same sources as data pages | Q-01/Q-02/Q-07/Q-11/Q-13 OPEN (owner decisions / blocked sources) |
| T9 Suggestions board (14, review-before-implementation) | done | `docs/pages/suggestions.html` | proposal rows marked as such | — |
| T10 Executive summary | done | `docs/pages/executive-summary.html` | claims sourced inline | — |
| T11 Site build (dashboard + 13 subpages) | done | `docs/pages/**`, `docs/style.css`, `docs/data/standings-2026-week10.csv` (32 teams) | standings cross-checked vs injury-page records (all 28 non-bye teams match) | two source standings columns unlabeled (F-11, hidden) |
| T12 Line-by-line verification | done | `tools/verify_site.py` | 14 pages / 49 tables, 0 failures, 0 warnings; every source-table row has an official link or UNVERIFIED flag | — |
| T13 Integration | done (this merge) | shared outputs | merged `origin/main` twice (PRs #4–#9, then #8/#11 wave) without discarding other sessions' work | see conflict log below |

### Merge-conflict log (2026-11-14)
- First `gh pr merge 10 --merge` failed: `main` had advanced via PRs #4–#9. Stopped; merged
  `origin/main` into this branch; conflicts in `COORDINATION.md`, `README.md`, `docs/index.html`
  resolved by keeping the other sessions' content verbatim and appending this session's sections.
- Second `gh pr merge 10 --merge` failed: `main` had advanced again (PRs #8/#11,
  sessions `arena/972ad7a5-x3`, `arena/7e632805-x3`). Re-merged `origin/main`; conflicts in
  `COORDINATION.md`, `README.md` resolved the same way (theirs verbatim + this appended section);
  `docs/index.html` auto-merged and retains both the generated dashboard and the marked
  `arena-4856379c-x3` integration section. Nothing from any session was discarded.
- Note: `git pull --rebase` once tried to linearize the integration merge commit and stopped on
  conflicts; aborted with `git rebase --abort` (merge commit 53a0d97 preserved and pushed).
- `docs/index.html` is co-owned: generated by `scripts/build_site.py` from `data/` with the
  integration section added by this session. **Request to future sessions:** if
  `scripts/build_site.py` is re-run, re-apply the `arena-4856379c-x3` section or fold it into the
  generator.

### PR log (this session)
- PR #10: https://github.com/karagemop466-tech/X3/pull/10 — `arena/4856379c-x3` → `main` (merge
  result recorded in the follow-up record PR).

### Verification performed (this session)
- Injury data: 345 rows transcribed from 8 fetched chunks of nfl.com/injuries (Week 10, 2026) into
  `docs/data/injury-2026-week10.csv`, then generated into pages by `tools/build_data_pages.py`
  (no hand-keyed duplicates). Status counts: 66 Out, 10 Doubtful, 84 Questionable, 185 without
  game status.
- Standings: 32 teams from nfl.com/standings; records cross-checked against the injury page headers
  (all match).
- Academic references verified at SSRN/publisher/university hosts; Kaggle verified for BDB prizes.
- At merge time: `tools/verify_site.py` (this session) and `scripts/check_site.py` (arena/0c38f465
  session) both pass on the combined tree; the Pages workflow's link check replicated locally.

---

## Session `arena/e1c332ce-x3` — NFL Lines & Strategy Lab (appended section)

- **Status:** integration in progress. Session ID `e1c332ce`. Branch `arena/e1c332ce-x3` (platform-fixed; the `session-<id>/<task>` naming in the brief was not usable — deviation logged here per protocol).
- **Claim (committed before work, e48e046, 2026-11-14):** line-origination model + validation-gate framework + leaderboard design + injury/2nd-3rd-4th-string deficiency tracker + an additive site unit, owning `x3lab/**`, `scripts/compute_lines.py`, `scripts/compute_analysis.py`, `scripts/verify_data.py`, `analysis/**`, and this appended section. No files owned by other sessions were edited.
- **Live site (this session):** https://karagemop466-tech.github.io/X3/x3lab/ — dashboard + 12 category subpages; every table row carries a source link or an explicit UNVERIFIED badge. Data single-sourced in `x3lab/data/*.json`; machine gate `python3 scripts/verify_data.py` = PASS (2,134 checks).

### Task board (session e1c332ce)

| # | Task | Status | Files |
|---|------|--------|-------|
| T1 | Research: standings/seeds, weeks 9-11 schedules+results | done | `x3lab/data/standings.json`, `week9.json`, `week10.json`, `week11` in odds file |
| T2 | Research: market odds wk10/wk11 + futures | done | `x3lab/data/odds_week10.json`, `odds_week11.json` |
| T3 | Research: injuries, all 32 teams | done | `x3lab/data/injuries.json` |
| T4 | Depth charts + deficiency rule R-1 | done | `x3lab/data/depth.json`, `deficiencies.json`, `analysis/depth-deficiency.md` |
| T5 | Line origination model v0.1 | done (unvalidated) | `scripts/compute_lines.py`, `x3lab/data/lines_week10.json`, `analysis/line-origination.md` |
| T6 | Signals, strategies, validation gates G-0..G-8, correlation method + pilot values, leaderboard design | done (pending gates) | `x3lab/data/strategies.json`, `validation_gates.json`, `correlation.json`, `leaderboard.json`, `luck.json` |
| T7 | Questions/information-gap register + suggestions review queue | done | `x3lab/data/questions.json`, `suggestions.json` |
| T8 | Site: dashboard landing + category subpages | done | `x3lab/` |
| T9 | Verification gate + line-by-line log | done | `scripts/verify_data.py`, `analysis/verification-log.md` |

### Sources (all fetched 2026-11-14; full register at x3lab/sources.html)

NFL.com standings league+conference (OFFICIAL) · NFL.com schedules by-week week-9/10/11 (OFFICIAL) · NFL.com game pages (OFFICIAL) · ESPN NFL injuries, all 32 teams (TRUSTED — aggregates official team reports) · DraftKings lines via ESPN odds (MARKET) · ESPN/RotoWire depth charts PIT+BAL (TRUSTED, not official — flag F-05) · ESPN report SEA@LV starter note (TRUSTED).

### Irregularities (published at x3lab/flagged.html)

F-01 nfl.com schedule URL redirect quirk · F-02 standings split-column mapping inferred by arithmetic partition · F-03 odds open-column timestamps unknown + extreme moves (JAX-TEN 8 pts; LAC-BAL total 10 pts; two direction flips) · F-04 ESPN injury status/comment mismatches · F-05 depth charts third-party + PIT/BAL only (string claims blank elsewhere) · F-06 totals heuristic (no pace data) · F-07 HFA assumptions (neutral-site HFA unverified) · F-08 correlations pilot-only (n=16) · F-09 legal status of wagering/funded rewards in owner jurisdiction (consistent with the Penal Code note already on the docs dashboard) · F-10 2026 roster assignments recorded as-reported.

### Integration log (session e1c332ce)

- 2026-11-14: claim committed/pushed first (e48e046); research, data, model, site, verification built in small commits (d0d7cdc, 10992b7, f10ed41).
- 2026-11-14: `git pull --rebase` showed `main` had advanced with PRs #1-#9 from five sessions. Rebase stopped at an add/add conflict in `COORDINATION.md`; abandoned in favor of a merge (repo precedent).
- 2026-11-14: to avoid add/add collisions with session `arena/0c38f465-x3`'s `docs/` dashboard, this session's site was relocated to `x3lab/` (b1c260a). Nothing of other sessions was discarded or edited; root `index.html` (claimed by session `arena/972ad7a5-x3`) was NOT touched.
- 2026-11-14: merge of `origin/main` into this branch; conflicts in `COORDINATION.md` and `README.md` resolved **additively** (main's full content kept, this section appended), per the convention used by PRs #4 and #7.
- 2026-11-14: PR #13 **merged** into `main` (record below). `main` advanced concurrently with PRs #14 and #15 from other sessions; synced again without conflicts and without touching their files.

### PR & deploy record (session e1c332ce)

- **PR #13:** https://github.com/karagemop466-tech/X3/pull/13 — `arena/e1c332ce-x3` → `main`, "X3: NFL Lines & Strategy Lab — originated lines, validation gates, injury/depth tracker". Result: **MERGED** 2026-11-14, merge commit `059079d`. One fix-and-retry: the first merge attempt failed because `main` had advanced (PRs #10/#11); `origin/main` was merged in again with additive conflict resolution on `COORDINATION.md`/`README.md`, then the PR merged cleanly. Summary + sources + flagged irregularities were included in the PR body as required.
- **CI / Pages deploy:** workflow "Deploy X3 NFL site to GitHub Pages" run 43550431317 — build + deploy **success**, all six steps green (HTML/link audit; docs row-source check 356 rows/0 missing; root-page link check; dashboard checks; node data + render checks). Pages source remains `main /` (legacy; shared flag F15 — token cannot change Pages settings).
- **Live verification 2026-11-14:** https://karagemop466-tech.github.io/X3/x3lab/ — `lines.html` and `flagged.html` fetched live and render complete source-linked tables (model-vs-market board with gap highlighting, Week-11 look-ahead board, futures; F-01…F-10 incl. the UNVERIFIED badge behavior). The `index.html` URL intermittently returned a GitHub incident page ("Unicorn") during the incident window while sibling pages served correctly; the deploy itself is green and sibling pages prove the artifact is complete.

---

## Session arena-4856379c-x3 (this session)

Branch: `arena/4856379c-x3` (platform-assigned; used instead of the `session-<id>/<task>` naming, as
with earlier sessions). Claimed scope: `research/**`, `docs/pages/**`, `docs/data/**`,
`docs/style.css`, `tools/build_data_pages.py`, `tools/verify_site.py`; integration edits to the
shared outputs `docs/index.html`, `README.md`, `COORDINATION.md` (sanctioned for the integration
role). No other session's files were modified.

### Task board (arena-4856379c-x3)

| Task | Status | Files | Sources / verification | Irregularities |
|---|---|---|---|---|
| T1 Repo line-by-line audit | done | `research/repo-audit.md`, `docs/pages/repo-audit.html` | git inventory at `e124230` (README only, `# X3`) | README rewritten; LICENSE absent (F-05) |
| T2 Requirements inventory (28 items) | done | `docs/pages/requirements.html` | each status checked against repo contents | — |
| T3 Line origination + signal catalog S1–S8 | done | `research/line-origination.md`, `docs/pages/strategies.html` | Levitt 2004 (EJ, uchicago.edu PDF); Claremont thesis 2025; Skidmore thesis (digitalcoll.skidmore.edu/record/6451); community replication (GitHub) | model σ/HFA parameters blank (UNVERIFIED until calibrated) |
| T4 Validation gates G0–G8 (luck removal) | done | `research/validation.md`, `docs/pages/validation.html` | DSR Bailey & López de Prado 2014 (SSRN 2460551); PBO Bailey et al. 2015 (SSRN 2326253) | DSR/PBO thresholds are paper conventions (F-08) |
| T5 Correlation research | done | `research/correlation.md`, `docs/pages/correlation.html` | Davis 2018 via bettoredge (secondary); Skidmore thesis; industry SGP-tax sources (flagged) | no official numeric coefficients exist → blank + UNVERIFIED (F-03); estimation pipeline published |
| T6 Leaderboard competition design | done | `research/leaderboard.md`, `docs/pages/leaderboard.html` | NFL Big Data Bowl prizes/rubric (Kaggle 2021/2022/2027) | reward amounts blank (Q-01) |
| T7 Injury & deficiency tracker | done | `docs/data/injury-2026-week10.csv` (345 rows), `docs/pages/injuries.html`, `research/injury-tracking.md` | nfl.com/injuries Week-10 2026 (8 chunks, 2026-11-14); nfl.com/news headlines; nfl.com important-dates page | F-01 Lamar timeline conflict; F-02 roster pairings vs historical knowledge; F-04 depth charts 404 at the URLs tested (depth ranks left blank); F-07 rest-outs; F-09 blank-status rows; F-12 Henley LAC/DEN conflict |
| T8 Questions (15) + discovery paths | done | `docs/pages/questions.html` | known answers cite the same sources as data pages | Q-01/Q-02/Q-07/Q-11/Q-13 OPEN (owner decisions / blocked sources) |
| T9 Suggestions board (14, review-before-implementation) | done | `docs/pages/suggestions.html` | proposal rows marked as such | — |
| T10 Executive summary | done | `docs/pages/executive-summary.html` | claims sourced inline | — |
| T11 Site build (dashboard + 13 subpages) | done | `docs/pages/**`, `docs/style.css`, `docs/data/standings-2026-week10.csv` (32 teams) | standings cross-checked vs injury-page records (all 28 non-bye teams match) | two source standings columns unlabeled (F-11, hidden) |
| T12 Line-by-line verification | done | `tools/verify_site.py` | 14 pages / 49 tables, 0 failures, 0 warnings; every source-table row has an official link or UNVERIFIED flag | — |
| T13 Integration | done | shared outputs | merged `origin/main` waves (PRs #4–#9, #8/#11, #13/#14) without discarding other sessions' work | see merge-conflict log below |

### Merge-conflict log (2026-11-14)
- `gh pr merge 10` failed twice as `main` advanced mid-merge (PRs #4–#9 wave, then PRs #8/#11 wave).
  Each time: merged `origin/main` into this branch and resolved shared-file conflicts
  (`COORDINATION.md`, `README.md`, `docs/index.html`) by keeping the other sessions' content
  verbatim and appending this session's sections — nothing discarded. `docs/index.html` auto-merged
  in the second round and retains both the generated dashboard and the marked `arena-4856379c-x3`
  integration section.
- One `git pull --rebase` attempted to linearize the integration merge commit and stopped on
  conflicts; aborted with `git rebase --abort` (merge commit preserved).
- The record PR (#15) also met an advancing `main` (PRs #13/#14 wave); same additive resolution
  applied to `COORDINATION.md`.
- `docs/index.html` is co-owned: generated by `scripts/build_site.py` from `data/` with the
  integration section added by this session. **Request:** if `scripts/build_site.py` is re-run,
  re-apply the `arena-4856379c-x3` section or fold it into the generator.

### PR log (this session)
- PR #10: https://github.com/karagemop466-tech/X3/pull/10 — `arena/4856379c-x3` → `main` —
  **MERGED** 2026-11-14T03:11:11Z via `gh pr merge 10 --merge`, merge commit
  `ef24b334729895a757a1b27e1a10809575e8be6c`.
- **GitHub Pages deploy confirmed:** workflow "Deploy X3 NFL site to GitHub Pages" run 43550291709 =
  success (PR #10 merge); "pages build and deployment" run 43550290884 = success; Pages API status
  `built` (source `main` root `/`, build_type legacy). Live: https://karagemop466-tech.github.io/X3/
  — verified 2026-11-14: extended tree serves at /docs/pages/ (injuries.html renders the 345-row
  Week-10 tracker with source links; standings.html renders the 32-team snapshot).
- PR #15 (this record): https://github.com/karagemop466-tech/X3/pull/15 — merge result recorded
  here per protocol; merged immediately after CI-free checks pass locally.

### Verification performed (this session)
- Injury data: 345 rows transcribed from 8 fetched chunks of nfl.com/injuries (Week 10, 2026) into
  `docs/data/injury-2026-week10.csv`, then generated into pages by `tools/build_data_pages.py`
  (no hand-keyed duplicates). Status counts: 66 Out, 10 Doubtful, 84 Questionable, 185 without
  game status.
- Standings: 32 teams from nfl.com/standings; records cross-checked against the injury page headers
  (all match).
- Academic references verified at SSRN/publisher/university hosts; Kaggle verified for BDB prizes.
- At each merge: `tools/verify_site.py` (this session) and `scripts/check_site.py` (arena/0c38f465
  session) both pass on the combined tree; the Pages workflow's link check replicated locally.

### Request to current root-landing owners
- `lab/` module owners (sessions arena/972ad7a5-x3 / arena/7e632805-x3 / arena/64164906-x3): please
  link the extended research tree `docs/pages/` from `lab/index.html` (currently reachable via the
  `docs/` dashboard at `docs/index.html`). Logged here instead of editing `lab/` files, per the
  coordination protocol.

---

## Session `arena/d968fa97-x3` — independent official-source audit (claim)

- **Status:** in progress. Branch `arena/d968fa97-x3` (platform-assigned; the `session-<id>/<task>` naming in the brief is not usable on this session, per the platform rule; deviation logged here).
- **Claim (committed before work):** an independent, row-by-row re-verification of the 2026 Week 10 NFL injury report against the official page `https://www.nfl.com/injuries/league/2026/reg10`, plus a standalone audit page.
- **File scope claimed:** `audit/**` only (new folder). No other file is edited. Existing datasets (`data/`, `docs/`, `dashboard/`, `x3lab/`, `lab/`, `pages/`, `site/`, root HTML) are read, not changed.
- **Requests for integration (logged, not edited):** link `audit/index.html` from the root landing and the `docs/` dashboard navigation; reconcile the abbreviated practice-status labels in `docs/data/injury-2026-week10.csv` with the official wording (see audit page).

### Task board (arena/d968fa97-x3)

| # | Task | Status | Files |
|---|------|--------|-------|
| A1 | Claim + coordination record | in progress | `COORDINATION.md` |
| A2 | Transcribe official Week 10 2026 rows (8 chunks of nfl.com) | pending | `audit/official_injury_wk10_2026.csv` |
| A3 | Row-by-row diff against `docs/data/injury-2026-week10.csv` | pending | `audit/diff_report.csv`, `audit/summary.json` |
| A4 | Audit page + flagged irregularities | pending | `audit/index.html`, `audit/README.md` |
| A5 | Checks, PR, merge, Pages status | pending | — |
