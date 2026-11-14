# NFL Decision Lab

An evidence-first, static GitHub Pages research workspace for NFL line modeling, injury/lineup analysis, correlation, strategy validation, and a proposed leaderboard. The root page is the current dashboard; its research subpages live in `lab/`.

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
node --check assets/data.js
node --check assets/app.js
node scripts/check_data.js
node scripts/check_render.js
```

The checks validate local navigation/assets, JavaScript syntax, source IDs, approved official-source hosts, and the rule that each published data row references at least one source. External sources are not fetched by the test scripts; the source register records pages reviewed on 2026-11-14 UTC and links each claim to the official page for manual review.

## Evidence and modeling policy

1. Separate official observations from hypotheses. A linked NFL page is a data source, not proof that a signal predicts outcomes.
2. Preserve season/week, source URL, retrieval time, prediction cutoff, and version before automated ingestion.
3. Never infer player availability, backup-string rank, injury severity, market prices, or model performance. Leave unknowns blank and flag them.
4. Treat same-game props and parlays as joint-probability problems. Do not multiply marginal probabilities unless independence is demonstrated for the defined events.
5. Keep candidate strategies out of the leaderboard until they beat a preregistered baseline on later, untouched outcomes with uncertainty and repeated-testing controls.
6. Luck cannot be eliminated from NFL outcomes. The goal is to test whether a signal is repeatable and quantify its uncertainty.
7. No market-price feed, settlement rules, real-money execution, jurisdiction-specific contest review, or reward payout is configured.

See [`COORDINATION.md`](COORDINATION.md) for scope, source review, verification performed, and flagged irregularities.


---

## NFL Lines & Strategy Lab (session e1c332ce)

A separate, additive lab at [`x3lab/`](x3lab/index.html) — live at https://karagemop466-tech.github.io/X3/x3lab/.

Originate our own Week-10 NFL lines (model v0.1, deterministic), run strategies through luck-removing validation gates (G-0…G-8: pre-registration, sample size, walk-forward, FDR, CLV, vig-adjusted CIs, deflated Sharpe, correlation integrity), and track injuries with 2nd/3rd/4th-string deficiency flags. Every table row links to an official or trusted source; unconfirmable values stay blank and flagged.

- Data: `x3lab/data/*.json` · Notes: `analysis/` · Gate: `python3 scripts/verify_data.py` (must PASS)
- Model: `scripts/compute_lines.py` · Pilots (correlations, Pythagorean luck): `scripts/compute_analysis.py`
- Review before anything changes: `x3lab/suggestions.html` (12 proposals) · `x3lab/questions.html` (15 open) · `x3lab/flagged.html` (10 flags)
