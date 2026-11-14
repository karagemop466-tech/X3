# X3 — NFL Lines, Signals & Strategy Analytics

A self-contained analytics site that collects, organizes, and analyzes NFL data to
support decision-making around **originating NFL betting lines** and **skill-based
betting strategies**. The site is a clean, dashboard-style static site with a landing
page and category subpages. Every data row carries a link to an **official source**;
any value that cannot be confirmed from an official source is left blank and flagged
as **unverified** on the *Flagged for Review* page.

## What's inside

| Page | Purpose |
|------|---------|
| [Landing](index.html) | Overview, key metrics, navigation. |
| [Executive Summary](executive-summary.html) | Key details, scope, status, risks. |
| [Requirements & Questions](requirements.html) | Questions / information / answers needed before any decision. |
| [Suggestions](suggestions.html) | Dedicated suggestions for review before implementation. |
| [Lines & Signals](lines.html) | NFL lines, signal generation, validation gates, correlation methodology. |
| [Strategy Leaderboard](leaderboard.html) | Strategy designs, validation gates, rewards framework. |
| [Injuries & Lineups](injuries.html) | Injury tracking + 2nd/3rd/4th-string backup deficiencies. |
| [Verification](verification.html) | Line-by-line verification log with official source links. |
| [Flagged for Review](flagged.html) | Irregularities and unverified items for review. |

## Method

- All data is pulled from **official / trusted sources** (NFL.com, official team sites).
- **No hallucinations.** Values that cannot be confirmed from an official source are
  left blank and flagged `unverified`.
- Betting lines are **not** published by the NFL; line values are left blank and
  flagged `unverified` until a confirmed source is provided.
- Correlation values and leaderboard performance require a data pipeline + backtest
  that does not yet exist; they are left blank and flagged `unverified`.

## Build & verify

```bash
python3 tools/build_site.py     # regenerate the static site from tools/site_data.py
python3 tools/check_links.py    # verify no broken internal links
```

## Coordination

Task ownership and the verification/irregularity log live in
[COORDINATION.md](COORDINATION.md).

## Live site

Published to GitHub Pages from `main` (source path `/`).
