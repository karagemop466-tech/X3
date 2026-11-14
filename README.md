# X3 — NFL Lines & Strategy Lab (2026 season)

Originate our own NFL lines, validate strategies behind luck-removing gates, and track
injuries/depth deficiencies — with every number linked to an official or trusted source.

**Live site (GitHub Pages):** https://karagemop466-tech.github.io/X3/

## What's here

| Path | What it is |
| --- | --- |
| `docs/` | The GitHub Pages site: dashboard + category subpages, all tables source-linked |
| `docs/data/` | Single sources of truth: standings, weeks 9–11, odds, injuries, depth, deficiencies, model outputs, strategy/gate/leaderboard/question/suggestion/flag registries |
| `analysis/` | Working notes: verification log, line-origination method, depth-deficiency rule |
| `scripts/verify_data.py` | Verification gate: every fact row must carry a source (or `unverified: true`), plus data invariants and site wiring |
| `scripts/compute_lines.py` | Line origination model v0.1 (deterministic; assumptions labeled) |
| `scripts/compute_analysis.py` | Pilot correlations + Pythagorean luck table |
| `COORDINATION.md` | Shared task board for parallel sessions (claims, scopes, logs, integration record) |

## Principles

1. **No hallucinations.** Every table row links to a source; unconfirmable values stay
   blank and get an `UNVERIFIED` badge — never inferred, never filled.
2. **Model output ≠ fact.** Assumptions (HFA, totals shrink, …) are labeled and flagged.
3. **Luck is designed out.** Strategies pass gates G-0…G-8 (pre-registration, sample
   size, walk-forward, FDR, CLV, vig-adjusted CIs, deflated Sharpe, correlation
   integrity) before anything is scored on the leaderboard.
4. **Flags are published,** not buried: see the Flagged for Review page.

## Verify

```bash
python3 scripts/verify_data.py   # must PASS before merge
python3 scripts/compute_lines.py # regenerate originated lines
python3 scripts/compute_analysis.py
```

Data snapshot: 2026-11-14 (NFL Week 10 in progress). Session: e1c332ce.
