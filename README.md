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
