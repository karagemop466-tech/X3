# NFL Decision Lab

An evidence-first, static GitHub Pages research workspace for NFL line modeling, injury/lineup analysis, correlation, strategy validation, and a proposed leaderboard. The root page is a landing directory for every module on the site; the primary research dashboard lives in `lab/`.

Earlier material integrated on `main` is preserved under `docs/`, `data/`, `pages/`, and other root files. It is not imported into the new dashboard's source-first data module; re-verify those historical tables and assumptions before treating them as current facts.

> **Current status:** the new `assets/data.js` research module is a framework, not a live feed. The repository also retains a legacy 2026 Week 10 injury-report snapshot (205 rows) and 2026 key-dates CSV under `data/` and `docs/`; these are not connected to the new module or used for model results. No historical odds/prop-price archive, measured strategy performance, or validated leaderboard exists. Unsupported values remain blank and source gaps are published on **Flagged for review**. The site does not place bets or promise rewards.

## Site sections

- **Overview** — project status and recommended research sequence.
- **Executive summary** — verified source availability, what is not measured, and the next decisions.
- **Strategy lab** — hypotheses for game lines, singles, player props, combos, and parlays.
- **Validation gates** — proposed chronological testing, calibration, uncertainty, and multiple-testing controls.
- **Injuries & lineups** — official-source requirements for injury reports, game availability, and backup/depth evidence.
- **Correlation lab** — paired-event quantities to estimate; unverified numeric cells remain blank.
- **Leaderboard** — empty until strategies pass the documented gates; categories and reward proposal are separated.
- **Open questions** — known information, missing information, and unresolved decisions.
- **Suggestions** — review proposals and select a planning path. Local browser choices are not shared and do not implement changes.
- **Flagged for review** — missing datasets, feed/rights questions, source irregularities, and other unverified items.
- **Sources** — official NFL/NFL Football Operations pages and technical statistical-method references.
- **Prior data archive** — [2026 Week 10 injury snapshot](docs/injuries.html), [2026 key dates](docs/schedule.html), and [legacy flags](docs/flagged.html); these rows are separate from the new module and should be rechecked before reuse.

## Run locally

This is plain HTML, CSS, and JavaScript; no package install or build step is required.

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080/` in a browser. On GitHub Pages, relative links support the repository path under `https://karagemop466-tech.github.io/X3/`.

## Verify the static site

```bash
python3 scripts/build_site.py
python3 scripts/check_site.py
python3 tools/check_links.py
python3 scripts/check_dashboard.py
python3 scripts/audit_all.py
python3 tools/verify_site.py
python3 scripts/verify_data.py
node --check assets/data.js
node --check assets/app.js
node scripts/check_data.js
node scripts/check_render.js
```

`scripts/audit_all.py` is the repo-wide gate: it checks **every** HTML page in the
repository (root, `docs/`, `docs/pages/`, `dashboard/`, `lab/`, `x3lab/`, `site/`,
`pages/`, `legacy/`) for broken internal links, for source-column table rows that
neither link an official source nor flag UNVERIFIED, and for flagged-page rows
missing a marker. It runs in CI on every push and pull request.

The checks validate local navigation/assets, JavaScript syntax, source IDs, approved official-source hosts, and the rule that each published data row references at least one source. External sources are not fetched by the test scripts; the source register records pages reviewed on 2026-11-14 UTC and links each claim to the official page for manual review.

## Evidence and modeling policy

1. Separate official observations from hypotheses. A linked NFL page is a data source, not proof that a signal predicts outcomes.
2. Preserve season/week, source URL, retrieval time, prediction cutoff, and version before automated ingestion.
3. Never infer player availability, backup-string rank, injury severity, market prices, or model performance. Leave unknowns blank and flag them.
4. Treat same-game props and parlays as joint-probability problems. Do not multiply marginal probabilities unless independence is demonstrated for the defined events.
5. Keep candidate strategies out of the leaderboard until they beat a preregistered baseline on later, untouched outcomes with uncertainty and repeated-testing controls.
6. Luck cannot be eliminated from NFL outcomes. The goal is to test whether a signal is repeatable and quantify its uncertainty.
7. No market-price feed, settlement rules, real-money execution, jurisdiction-specific contest review, or reward payout is configured.

This session added a parallel, self-contained static site (inline styles, per-row
source links) plus build tooling. It was merged into the integrated dashboard
without overwriting the shared `index.html` navigation or the integrated `docs/`
dashboard. Its standalone pages are served from the repo root:

- `index.html` — root landing directory linking every module (shared output; it replaced the earlier redirect to the dashboard in session `arena/35b167ca-x3`, which keeps the dashboard as its primary action).
- `executive-summary.html`, `requirements.html`, `suggestions.html`, `lines.html`,
  `leaderboard.html`, `injuries.html`, `verification.html`, `flagged.html`
  (root) — this session's category pages.
- `tools/build_site.py` — generates the standalone pages from verified data.
- `tools/check_links.py` — verifies no broken internal links (9 pages, 297 links).

All data rows link to official sources; betting lines, correlation values, and
leaderboard performance have no official source and are left blank + flagged
unverified. See `COORDINATION.md` (this session's section) for the full
verification log and irregularity flags.

---

## Verified-data dashboard (branch arena/7e632805-x3)

An 18-page dashboard built from data transcribed row by row from official sources.
Served at **`/dashboard/`** on the published Pages site. Added additively: no other
session's files were modified.

| Path | Contents |
|------|----------|
| `dashboard/` | 18-page dashboard: overview, executive summary, standings, schedule, injuries, depth & deficiencies, own lines, strategies, validation gates, correlation, leaderboard, open questions, suggestions, requirements, repo review, sources, flagged, coordination |
| `dashboard/data/` | Same content as JSON, emitted by the build |
| `tools/nfl_data.py` | Verified data: standings, schedule, injury report, depth charts. Sole source of fact |
| `tools/site_content.py` | Requirements, questions, suggestions, strategies, gates, leaderboard spec |
| `tools/build_dashboard.py` | Deterministic build → `dashboard/**` |

### Data verified this session

| Dataset | Official source | Rows |
|---------|-----------------|------|
| 2026 league standings | https://www.nfl.com/standings/league/2026/REG | 32 clubs |
| Week 10 injury report | https://www.nfl.com/injuries/ | 345 player rows |
| Week 10 schedule | https://www.nfl.com/schedules/2026/by-week/week-10 | 14 games + 4 byes |
| Club depth charts | `<club>.com/team/depth-chart` | 31 of 32 clubs |

### Rebuild

```bash
python3 tools/build_dashboard.py
```

Deterministic: reads only `tools/nfl_data.py` and `tools/site_content.py`.

### Known limits

* Houston's official depth chart is published only as an image, so it is recorded as a
  gap rather than filled in.
* All 31 readable depth charts are self-labelled "unofficial" by the publishing club.
* No market lines and no game log have been ingested, so the model runs with
  home-field advantage at 0.0 and no schedule-strength adjustment. Every model output is
  badged `DERIVED`.
* 12 items are on the Flagged for Review page. None blocks the site.

See `dashboard/questions.html` for the blocking unknowns and `dashboard/suggestions.html`
for the decision queue.

---

See [`COORDINATION.md`](COORDINATION.md) for scope, source review, verification performed, and flagged irregularities.

---

## Extended research tree & verified Week-10 dataset (branch `arena/4856379c-x3`)

| Path | Contents |
|------|----------|
| `docs/pages/` | Research subpages: Executive Summary · Requirements · Line Origination · Validation · Correlation · Leaderboard · Injuries · Standings · Questions · Suggestions · Flagged · Sources · Repo Audit |
| `docs/data/` | Canonical verified CSVs: `injury-2026-week10.csv` (345 rows, per-row official source URL) · `standings-2026-week10.csv` (32 teams) |
| `docs/style.css` | Stylesheet for the `docs/pages/` tree |
| `research/` | Backing research notes with source links (line origination, validation, correlation, leaderboard, injury tracking, repo audit) |
| `tools/build_data_pages.py` | Regenerates `docs/pages/injuries.html` + `docs/pages/standings.html` from the CSVs |
| `tools/verify_site.py` | Line-by-line verification: every source-table row must carry an official link or an UNVERIFIED flag (result at merge: 14 pages / 49 tables, 0 failures) |

Verification note for this session's data: fetched live from `nfl.com/injuries` (Week 10, 2026 —
8 chunks) and `nfl.com/standings` on 2026-11-14; team records were cross-checked between the two
official pages (all 28 non-bye teams match). Depth-chart ranks were left blank + flagged in this
session's tables (the official depth-chart URLs tested returned 404 — see the Flagged page F-01…F-12
for all irregularities), and correlation coefficients remain blank + flagged (no official numeric
source).

---

## NFL Lines & Strategy Lab (session e1c332ce)

A separate, additive lab at [`x3lab/`](x3lab/index.html) — live at https://karagemop466-tech.github.io/X3/x3lab/.

Originate our own Week-10 NFL lines (model v0.1, deterministic), run strategies through luck-removing validation gates (G-0…G-8: pre-registration, sample size, walk-forward, FDR, CLV, vig-adjusted CIs, deflated Sharpe, correlation integrity), and track injuries with 2nd/3rd/4th-string deficiency flags. Every table row links to an official or trusted source; unconfirmable values stay blank and flagged.

- Data: `x3lab/data/*.json` · Notes: `analysis/` · Gate: `python3 scripts/verify_data.py` (must PASS)
- Model: `scripts/compute_lines.py` · Pilots (correlations, Pythagorean luck): `scripts/compute_analysis.py`
- Review before anything changes: `x3lab/suggestions.html` (12 proposals) · `x3lab/questions.html` (15 open) · `x3lab/flagged.html` (10 flags)

---

## Consolidated review hub (branch `arena/1e2d8ef2-x3`, 2026-11-14)

Nine earlier sessions each shipped a site tree. This session adds one consolidated
review surface at [`hub/`](hub/index.html). The repository root is the landing hub built by
the final-integration session (`arena/621bf404-x3`); this branch registers `hub/` there
(one unit row, one card section, two cross-reference lines) rather than replacing it, so
the root page links both the data dashboard and this review hub. Nothing was deleted:
the older trees stay online and are indexed at [`hub/archive.html`](hub/archive.html).

**Pages:** overview · executive summary · requirements · questions & gaps · suggestions
queue · originated lines · signals & strategies · validation gates · correlations ·
injury report · depth & deficiencies · leaderboard · repo review · sources ·
verification log · flagged for review · archive.

**Data policy enforced by the build** (`scripts/build_hub.py`, audited by
`scripts/check_hub.py`):

- every rendered table row links to the source that documents it; the four data pages
  (injuries, deficiency, lines, correlations) must link to an official `nfl.com` host
  or carry an explicit `UNVERIFIED` marker — the build aborts otherwise;
- unknown values stay blank. No market price, depth string or performance figure was
  inferred, because no official source publishes them;
- every number in prose is injected from the data at build time through a token, and
  the build fails if a token is unfilled, so text cannot drift from its table;
- output is deterministic: two builds produce identical bytes (checked).

**Verified this session** (retrieved 2026-11-14, Week 10 of the 2026 season):

| Dataset | Official source | Result |
|---|---|---|
| Week 10 injury report, 345 rows / 28 clubs | https://www.nfl.com/injuries/ | transcribed row by row; reproduces the repo's earlier snapshot on all 345 players and game statuses, 1 practice-status drift |
| 2026 league standings, 32 clubs | https://www.nfl.com/standings/league/2026/REG | wins = losses, PF = PA, every home/road/division/conference split reconciles |
| Week 10 slate: 14 games + 4 byes | https://www.nfl.com/schedules/2026/by-week/week-10 | 32 clubs accounted for exactly once |
| WAS 24, NYG 21 (Thu) | https://www.nfl.com/games/commanders-at-giants-2026-reg-10 | confirmed, and included in the standings: reconciled against `data/desk/games.json` on all 32 clubs (192/192 values agree). This retracted a flag this session had published in error (FLG-02) |
| Club depth charts (desk capture) | https://github.com/karagemop466-tech/X3/blob/main/data/desk/deficiencies.json | 76 Week-10 absences: 41 resolve to a named replacement, 0 carry a chart as-of date → published only as an UNVERIFIED overlay |

**Irregularities found in existing data** (published at `hub/flagged.html`, all 21 non-blocking):
a prior tree's Tampa Bay division record (1-2-0) contradicts the official page (2-0-0);
`dashboard/data/model_lines.json` still publishes `model_home_spread` with the sign of the
expected margin instead of its negation (all 14 rows; 12 exactly double the margin), i.e. the
wrong side and the wrong scale in betting notation; a prior tree's Tampa Bay division record
(1-2-0) still contradicts the official page (2-0-0); published correlations from a prior tree
do not reproduce exactly and came from a different snapshot; two official pages disagree on
Freiermuth's designation and on Lamar Jackson's absence window. The `docs/data/` copies of the
same two tables were corrected by the integration session, so `dashboard/data/` and
`docs/data/` now disagree with each other — listed on the flags page rather than edited.

```bash
python3 scripts/build_hub.py && python3 scripts/check_hub.py   # rebuild + audit
```

## Consolidated decision desk — `/desk/` (session `arena/3bf7cc8b-x3`)

**Live:** https://karagemop466-tech.github.io/X3/desk/ — the repository root redirects here.
Eighteen pages, one verification gate, one capture pipeline.

### What it is

A single desk that answers four questions with linked evidence: what is verified, what the model
says, which strategies are allowed to compete, and who is missing from each lineup.

| Page | Contents |
|------|----------|
| `desk/index.html` | Executive dashboard |
| `desk/executive-summary.html` | Status, verified findings, what cannot be claimed, next decisions |
| `desk/lines.html` | Own originated spreads and totals (DERIVED) |
| `desk/model.html` | Club ratings, walk-forward calibration, limitations |
| `desk/strategies.html` | 10 strategy hypotheses with a 10-gate ledger |
| `desk/leaderboard.html` | Competition rules, anti-gaming, reward design (board empty by design) |
| `desk/correlations.html` | Measured coefficients with n and 95% CI |
| `desk/injuries.html` | Official injury reports, weeks 8-10 |
| `desk/lineups.html` | Out/Doubtful players joined to their depth string |
| `desk/questions.html` | 18 questions: known / missing / what each blocks |
| `desk/suggestions.html` | 12 suggestions to review before implementing anything |
| `desk/requirements.html` | 24 requirements with acceptance tests |
| `desk/games.html` | Verified game log (137 finals) |
| `desk/standings.html` | 2026 standings, reconciled against the game log |
| `desk/sources.html` | Source register and method references |
| `desk/repo-review.html` | Repository review and irregularities |
| `desk/flagged.html` | Flagged for review: every unverified item |
| `desk/archive.html` | Earlier session sites, preserved unchanged |

### How the data gets here without manual input

```
scripts/desk_capture.py      fetch official pages from a GitHub runner -> capture/
scripts/desk_extract.py      page text + nfl.com link maps
scripts/desk_parse.py        games / standings / injuries / depth charts -> data/desk/*.json
scripts/desk_join.py         injury report x depth chart -> deficiencies.json
scripts/desk_model.py        ratings, walk-forward backtest, correlations, strategies
scripts/desk_build.py        -> desk/**.html  (with desk_content.py for prose)
scripts/desk_verify.py       hard gate; CI fails if any check fails
```

The authoring sandbox cannot reach `nfl.com`, so `.github/workflows/desk-capture.yml` runs the
capture and parse on a GitHub-hosted runner and commits the structured result to the branch. The
parser self-test fails the run if a parser returns nothing, so an empty dataset cannot be committed
silently.

### Verification performed

| Check | Result |
|-------|--------|
| Standings vs game log | W-L-T, PF, PA match for all 32 clubs |
| Every dataset row has an official source URL | pass |
| Injury statuses inside the official vocabulary | pass |
| Correlation inside its own 95% CI | pass |
| Broken internal links | none |
| Table row without a source link or an explicit UNVERIFIED badge | none |
| Unfilled placeholder tokens | none |

Run `python3 scripts/desk_verify.py` to reproduce.

### Known limits (published, not hidden)

* **No market prices.** No official NFL source publishes spreads or totals, so every market column
  is blank and flagged, and no strategy can be graded. The leaderboard is empty by design.
* **No player-prop history.** The prop-combo strategy family is registered and blocked.
* **Small sample.** One season to date; the walk-forward correlation is around +0.20 on 121 games.
* **Club depth charts are club-published**; most are labelled unofficial, and Houston publishes an
  image, so its rows cannot be joined.
* **Luck is bounded, not removed.** Walk-forward testing, a Pythagorean residual and 95% CIs bound
  it; a single game stays mostly noise.

---

## Trading desk — `/ops/` (session `arena/3b99e9ad-x3`)

**Live:** https://karagemop466-tech.github.io/X3/ops/ — 18 pages, one verification gate, one
dependency-ordered pipeline. Additive: no other session's file was edited.

It answers the eight operational requirements directly, and says where it cannot.

| Requirement | Where it is answered |
|---|---|
| Price-snapshot store, opening + closing per market | [`ops/snapshots.html`](ops/snapshots.html) — 78 markets, SHA-256 hash chain, market columns null with reason `NO_OFFICIAL_SOURCE` |
| Verified results feed | [`ops/results.html`](ops/results.html) — 137 finals, reconciled to official standings 32/32 clubs |
| Side → total → moneyline, in that order | [`ops/order.html`](ops/order.html) — ML = Φ(side/σ), so the markets cannot contradict |
| Fair / market / difference as separate columns | [`ops/lines.html`](ops/lines.html) — market blank by policy, never estimated |
| Signal vs staking split on the leaderboard | [`ops/leaderboard.html`](ops/leaderboard.html) — promotion reads signal only |
| Depth of the replacement | [`ops/depth.html`](ops/depth.html) — 45 named same-position backups, 8 holes published |
| Correlations, official numbers only, with n | [`ops/correlation.html`](ops/correlation.html) — 9 coefficients, each with n, CI, p |
| Demotion gate, live → paper | [`ops/gates.html`](ops/gates.html) — dry-run proves D-1 fires |

Plus [`ops/props.html`](ops/props.html) (receiver props with a 54-leg walk-forward backtest),
[`ops/executive-summary.html`](ops/executive-summary.html),
[`ops/questions.html`](ops/questions.html), [`ops/suggestions.html`](ops/suggestions.html) (10 proposals
awaiting a decision), [`ops/flagged.html`](ops/flagged.html) (14 flags) and
[`ops/verification.html`](ops/verification.html).

### Rebuild and verify

```bash
python3 scripts/ops_run.py     # 7 steps in dependency order, then the gate
```

The gate (`scripts/ops_verify.py`, one CI step) checks 10 things and fails the build on any of them:
links resolve; every table row links an official source or is explicitly badged; no unfilled token or
rendered `None`; published counts equal the data; player logs reconcile to official season totals;
snapshot hashes recompute and chain; passing offense and defense reconcile; the results feed reconciles
to the standings; no market price exists without a source; and a second build is byte-identical.

### What is deliberately blank

**No market price exists in this repository**, so fair-versus-market, ROI, closing-line value and the
whole staking column are blank with a stated reason. One partial season cannot support a 200-bet skill
claim, and club depth charts are mostly self-labelled unofficial. Those are findings, published on
[`ops/flagged.html`](ops/flagged.html) — not gaps hidden by a placeholder.

## X3 signals & strategy desk (`signals/`)

Added by session `arena/09f8c786-x3`. It originates its own NFL numbers, grades them against
verified results, and ranks strategies on signal with staking reported separately.

Live at **https://karagemop466-tech.github.io/X3/signals/**

### What it is built from

| Input | Rows | Official source |
|-------|------|-----------------|
| Verified results feed | 163 games / 137 finals | https://www.nfl.com/schedules/2026/by-week/week-N |
| Standings | 32 clubs | https://www.nfl.com/standings/league/2026/reg |
| Official injury report | 1,027 rows (weeks 8-10) | https://www.nfl.com/injuries/league/2026/regN |
| Club depth charts | 32 clubs | https://www.<club>.com/team/depth-chart |

`signals/` reads `data/desk/**` and **never writes to it**.

### The eight requirements

| ID | Requirement | Where |
|----|-------------|-------|
| X3-01 | Price-snapshot store (open + close per originated market) | `signals/prices.html`, `signals/data/price_snapshots.csv` |
| X3-02 | Verified results feed | `signals/results.html`, `signals/data/results.csv` |
| X3-03 | Origination order: side -> total -> moneyline | `signals/lines.html` (pipeline order printed) |
| X3-04 | Fair line / market line / difference as separate columns | `signals/lines.html` |
| X3-05 | Signal separated from staking | `signals/leaderboard.html` |
| X3-06 | Depth of the replacement (2nd/3rd/4th string) | `signals/depth.html` |
| X3-07 | Correlations from official numbers, n published | `signals/correlations.html` |
| X3-08 | Demotion gate (live -> paper) | `signals/gates.html` |

### Headline findings

- The **side beats a constant baseline**: 67/105 walk-forward graded games, 95% CI 0.543-0.724,
  exact binomial p = 0.006. It clears Benjamini-Hochberg at q = 0.10.
- The **total does not** (47/105, p = 0.329), and on its confident subset it is *significantly
  adverse* (8/29, p = 0.024).
- The model is **badly under-spread**: predicted margin SD 4.28 vs actual 12.74 (ratio 0.34).
- **No market price exists** in this repository, so ROI, closing-line value, staking and drawdown
  are empty and flagged (F-01). Nothing is staked and nothing is promoted.

### Rebuild and verify

```sh
python3 scripts/x3_signals.py     # recompute signals/data/*
python3 scripts/build_signals.py  # render signals/*.html
python3 scripts/verify_signals.py # rows, links, gates, determinism
```

`scripts/verify_signals.py` fails the build on any table row that neither links an official source
nor carries an UNVERIFIED marker, on any broken internal link, on a missing snapshot (G11) and on a
leaderboard ranked by anything other than a signal column (G12).


---

## Round 2: fresh-day verification & decision readiness (branch arena/4c2f61cd-x3, 2026-11-15)

Session `arena/4c2f61cd-x3` re-verified the whole repository against official NFL sources on Week-10
game day (2026-11-15) and added the `round2/` module (additive; no other module's files edited):

- `round2/readiness.html` — the decision-readiness matrix: one row per requirement line of the brief,
  with the implementing page, the gate that blocks it and the number that would clear it
  (32 done / 20 partial / 13 not covered / 1 blocked).
- `round2/verification.html` — fresh-day line-by-line verification: official standings reconciled
  against the repo (30/32 identical; the 2 diffs are exactly the 2026-11-15 Munich final DET 35, NE 10),
  the Week-10 slate captured live, and the official NFL Game Book transcribed (starters, Not Active,
  venue, weather, roof/surface, officials, attendance).
- `round2/audit.html` — every repo gate re-run on 2026-11-15, all passing.
- `round2/flagged.html`, `round2/suggestions.html` — 7 new flags (incl. the Kerby Joseph Game-Book
  discrepancy and the Munich venue naming difference) and 10 suggestions awaiting reviewer decision.

Rebuild and gate: `python3 scripts/build_round2.py && python3 scripts/verify_round2.py`.
Data: `round2/data/*.csv` (standings, slate, results delta, game-book facts/starters/inactives,
requirements matrix, audit results, flags, suggestions, sources). The module is gated in CI by
`.github/workflows/round2.yml` and covered by the repo-wide `scripts/audit_all.py`.

## Decision layer and point-in-time availability series (2026-11-15)

- `decision/index.html` - readiness register (69 requirements, each with the gate that blocks it,
  the number that clears it and how the status was established), the suggestion queue, the open
  questions, the tree-overlap matrix, sources, verification log and flagged irregularities.
- `data/snapshots/` - sealed, clock-stamped reads of the official availability report. Two reads of
  Week 10 2026 exist, one day apart; `delta.json` publishes what moved between them, with a
  corroboration verdict per row against the independent prior reads retained in the repository.
- Rebuild and gate (offline, deterministic):

  ```bash
  python3 scripts/x3_snapshots.py && python3 scripts/x3_snapshots_verify.py
  python3 scripts/build_decision.py && python3 scripts/verify_decision.py
  ```

- Rules: a capture never changes; the filename encodes its clock time; two reads that hash equal
  are one read; an unmapped official club code fails the build; a row with no source fails the build.
## 2026 desk (`x3/`)

A 2026 in-season desk built from official NFL sources only: 28 static pages, 18 data files, and an
18-check gate (`python3 tools/x3_desk_verify.py`) that fails the build on a broken link, an
unsourced table row, a stale cross-reference, or a fabricated figure.

Start at [`x3/index.html`](x3/index.html). Every number on it is labelled **in-sample**; nothing on
it is live, and the market columns are empty because no official price source exists.

## Readiness module — `/readiness/` (session `arena/6259c7b0-x3`)

Closes the ten brief requirements no earlier session had implemented. Live at
**https://karagemop466-tech.github.io/X3/readiness/**

| Task | Where |
|---|---|
| RD-01 Decision-readiness table on the landing page (74 rows: gate that blocks it, number that clears it) | root `index.html` section + `readiness/decision-readiness.html` |
| RD-02 Two-sided "what would change our mind" field on every strategy entry (42 entries across 4 trees) | `readiness/change-our-mind.html` |
| RD-03 Drift alarm on every parser: 14 datasets pinned; CI fails loudly | `readiness/drift-alarms.html`, `scripts/drift_alarm.py` |
| RD-04 Control baselines (coin flip; favourites only) on the identical graded set and metric | `readiness/control-baselines.html` |
| RD-05 Weekly what-changed diff (rank / rating / availability) + stored weekly snapshots | `readiness/what-changed.html`, `readiness/data/history/2026/` |
| RD-06 Scheduled immutable snapshots (cron Wed/Thu/Fri + Sun), SHA-256 manifest, freshness alert | `readiness/snapshots.html`, `.github/workflows/availability-snapshots.yml` |
| RD-07 Availability-feature ablation with uncertainty (verdict: inconclusive at n=16, CI published) | `readiness/ablations.html` |
| RD-08 Announced-starter evidence field (5 dated official announcements, week 10) | `readiness/announced-starters.html` |
| RD-09 Offense-vs-defence matchup deficiency matrix, 1st–4th string | `readiness/matchup-matrix.html` |
| RD-10 Every model total published twice with a gap column (collapse deferred by rule) | `readiness/two-totals.html` |

### Rebuild and verify

```sh
python3 scripts/readiness_compute.py   # controls, what-changed, ablation, two totals (deterministic, seeded)
python3 scripts/drift_alarm.py         # RD-03 gate: fails loudly on any pinned drift
python3 scripts/build_readiness.py     # render the 11 pages
python3 scripts/verify_readiness.py    # links, sourcing, determinism, controls reproduce
```

Everything the module publishes is either linked to an official source, a provenance
link, or an explicit UNVERIFIED/BLOCKED marker. No market price, inactive list, snap
count or venue is invented; those stay blocked with the number that would clear them.

## Past-season injury archive and designation reliability (`reliability/`, 2026-11-17)

Session `arena/73e6752d-x3` closed two gap-register rows that had no coverage anywhere in the
repository: **Q43** (archive weekly injury reports for past seasons) and **Q44/Q45** (score
injury-designation reliability — join designations to the official inactive lists and measure the
play rate per designation with confidence intervals).

- `reliability/raw/injuries/<season>/reg10_chunk*.md` - verbatim captures of the official Week-10
  report for 2023, 2024 and 2025 (chunks 0-1, the sampled games' rows complete), sealed with sha256
  in `reliability/manifest.csv` with source URL and fetch clock.
- `reliability/raw/games/<season>/*.md` - per-game evidence from the official Game Book: centre
  facts, the Not Active / Did Not Play sections verbatim, and the Playtime Percentage rows used by
  the join, each with its source URL.
- `reliability/data/*.csv` - `designations.csv` (144 designated rows), `join.csv` (per-player
  outcome with evidence and reasons for every unresolved row), `rates.csv` (play and inactive rate
  per designation with Wilson 95% intervals and n), `games.csv`, `row_flags.csv`.
- Pages: `reliability/index.html` (overview, suggestions, questions/answers), `archive.html`,
  `reliability.html`, `join.html`, `flagged.html`, `sources.html`, `methods.html`.

Pilot headline (sample descriptive, Wilson 95% CI): Questionable played 54/79 = 68% [57-78];
Out played 4/53 = 7.5% [3.0-17.9] with every played row published as a flagged discrepancy;
Doubtful played 1/10 = 10% [1.8-40.4]. Rows that the captured evidence cannot settle are
`unresolved` and excluded from rates - never guessed.

Rebuild and gate (offline, deterministic):

```bash
python3 scripts/reliability_build.py && python3 scripts/reliability_verify.py
```

Rules: captures never change once sealed; a name match needs initial + surname + position family;
games whose Game Book render drops the Not Active labels are excluded from the inactive rate
rather than parsed by guess; every join row carries links to its official report page and Game Book.
