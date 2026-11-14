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
| T11 | Flagged for Review page | done | `dashboard/flagged.html` | 11 flags, all non-blocking |
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
- **Pages deploy**: workflow run
  [43549974941](https://github.com/karagemop466-tech/X3/actions/runs/43549974941)
  ("Deploy X3 NFL site to GitHub Pages") — build **success**, deploy **success**.
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
