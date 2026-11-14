# X3 — NFL Decision Intelligence (NFL Decision Lab)

A source-first framework for building and evaluating NFL betting signals: originate NFL lines, generate and validate betting signals, track injuries and depth-chart deficiencies, and review improvement suggestions before any change is implemented. The site separates verified facts, methods to test, and missing information; it does not publish live lines, picks, injury assertions, or performance claims without verified data.

## Site
GitHub Pages site with landing page + category subpages (Executive Summary, Suggestions & Review, Flagged for Review, Strategies & Signals, Injuries & Depth, Sources), plus the root decision-lab pages (overview/executive summary, strategy validation, data & availability, suggestions/questions, flagged review, sources/methods). Every table row carries a source link to an official site; unverified values are left blank and flagged. Nothing is inferred or filled in.

## Verification standard
- Every table row must have a source link to an official site.
- If a value cannot be confirmed from an official source, leave it blank and flag it unverified.
- Never infer or fill in values.

## Contents
- `site/` — GitHub Pages static site (this session, `arena/1a771fcd-x3`)
- `pages/` — supplementary category pages (this session)
- root `index.html`, `strategy.html`, `data.html`, `flagged.html`, `review.html`, `sources.html`, `style.css` — prior session (`arena/d667d44d-x3`) decision-lab site
- `.github/workflows/pages.yml` — Pages deployment
- `COORDINATION.md` — shared task board (both sessions)
- `docs/` — (planned) detailed findings

## Run locally
Open `index.html` (root) or `site/index.html` in a browser, or serve the directory with any static HTTP server.

## Project status
The repository began with no NFL datasets or application. Live NFL odds, dated official injury reports, historical closing lines, play-by-play inputs, and validated strategy results are not present. Missing values are intentionally blank and clearly flagged, not inferred. See Flagged for Review and Sources & methods.

## Branch
`arena/1a771fcd-x3` (from `main` @ e124230); integrated with `arena/d667d44d-x3` work on `main`.

---

## Data, injuries, strategy validation and suggestions (branch arena/0c38f465-x3)

Published site (single Pages build): `docs/` at the site root, with the earlier root-level and `site/`/`pages/` sites preserved under `/legacy/`.

| Path | Contents |
|------|----------|
| `docs/` | Static site for the dashboard, injuries, schedule, strategies, correlations, questions, suggestions, requirements, sources, executive summary and Flagged for Review (generated) |
| `data/` | Source-of-truth CSVs: injury report (Week 10 2026), 2026 key dates, strategies, gates, correlations, questions, suggestions, requirements, flags, sources |
| `scripts/build_site.py` | Builds `docs/` from `data/` (Python standard library) |
| `scripts/check_site.py` | Checks internal links and that every table row has a source link or unverified flag |
| `COORDINATION.md` | Shared task board for all sessions |

Rebuild and check:

```bash
python3 scripts/build_site.py
python3 scripts/check_site.py
```

Rules: table values come only from official sources (linked); anything unconfirmed is left blank and flagged unverified; suggestions are not implemented until a decision is recorded.

**Research only, not betting advice.** Wagering with private bookmakers from Japan is criminal for the bettor under Penal Code Article 185 ([official text](https://www.japaneselawtranslation.go.jp/en/laws/view/3581/tb)).

## Session `arena/3dbc4678-x3` contributions

This session added a parallel, self-contained static site (inline styles, per-row
source links) plus build tooling. It was merged into the integrated dashboard
without overwriting the shared `index.html` navigation or the integrated `docs/`
dashboard. Its standalone pages are served from the repo root:

- `index.html` — root redirect to the dashboard (shared output, unchanged).
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
* 11 items are on the Flagged for Review page. None blocks the site.

See `dashboard/questions.html` for the blocking unknowns and `dashboard/suggestions.html`
for the decision queue.
