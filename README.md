# NFL Decision Lab

An evidence-first, static GitHub Pages research workspace for NFL line modeling, injury/lineup analysis, correlation, strategy validation, and a proposed leaderboard.

> **Current status:** research framework only. No NFL data, odds, injuries, lineups, correlations, model results, or leaderboard entries are loaded. The site deliberately leaves unsupported values blank and publishes source gaps on **Flagged for review**. It does not place bets or promise rewards.

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

## Run locally

This is plain HTML, CSS, and JavaScript; no package install or build step is required.

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080/` in a browser. On GitHub Pages, relative links support the repository path under `https://karagemop466-tech.github.io/X3/`.

## Verify the static site

```bash
python3 scripts/check_site.py
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
