# COORDINATION.md — Shared Task Board (X3 / NFL Lines & Strategy Lab)

> **Read this before touching the repo.** This file is the shared task board for all
> parallel agent sessions. Claim tasks here and commit the claim before starting work.

Last updated: 2026-11-14 (UTC)

## Session registry

| Session ID | Branch | Status | Notes |
| --- | --- | --- | --- |
| e1c332ce | `arena/e1c332ce-x3` | active | Working session + integration session (see deviation note) |

**Deviation note (branch naming):** the standard protocol asks each session to work on
`session-<id>/<task>`. This environment pins the session to its arena branch
(`arena/e1c332ce-x3`) and forbids creating/switching branches, so all tasks below are
claimed by session `e1c332ce` on `arena/e1c332ce-x3`. Scopes remain non-overlapping per
file. If another live session joins later, claim your tasks here first and request any
file you need that is owned by another session via a "File request" entry below.

## Task board

| # | Task | Status | Owner (session) | Files in scope | Sources | Verification | Irregularities |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | Repo review + baseline README | done | e1c332ce | `README.md` | repo tree, git log | baseline was single `README.md` ("X3\n") at e124230; nothing to review line-by-line yet | none |
| T2 | Coordination board | done | e1c332ce | `COORDINATION.md` | — | — | branch-naming deviation noted above |
| T3 | Research: standings, schedules, results | done | e1c332ce | `x3lab/data/standings.json`, `x3lab/data/week9.json`, `x3lab/data/week10.json`, `x3lab/data/week11.json` | NFL.com standings + schedules (links in `x3lab/data/sources.json`) | every standings row cross-checked vs week-9/10 results; all 32 teams reconcile (W/L/T sums, PF/PA sums) | NFL.com standings column set (DIV%, CONF%, trailing non-conf-like record) inferred by arithmetic partition; flagged F-02 |
| T4 | Research: market odds wk10/wk11 | done | e1c332ce | `x3lab/data/odds_week10.json`, `x3lab/data/odds_week11.json` | DraftKings lines via ESPN.com/nfl/odds | mirrored spread/total pairs cross-checked inside each game block | large open→current moves (JAX-TEN 8pts, SF-DAL 6pt flip, MIA-IND total 9pts); see F-03 |
| T5 | Research: injuries (32 teams) | done | e1c332ce | `x3lab/data/injuries.json` | ESPN.com/nfl/injuries (aggregates official team reports; team-official citations kept in comments) | status values copied verbatim; no inference | ESPN status/comment mismatches (e.g. BUF Shavers) flagged F-04 |
| T6 | Depth-deficiency derivation | done | e1c332ce | `x3lab/data/deficiencies.json` | derived from `injuries.json` by documented rule | rule documented in `analysis/depth-deficiency.md`; every derived row links to its injury rows | official depth-chart strings NOT available for all 32 teams → string-level claims flagged F-05 |
| T7 | Line origination model v0.1 | done | e1c332ce | `scripts/compute_lines.py`, `x3lab/data/lines_week10.json`, `analysis/line-origination.md` | inputs = `standings.json` (NFL.com) | script re-runnable; outputs recomputed and diffed | totals are heuristic (no play-by-play/pace feed) — flagged F-06; HFA = 2.0 assumption flagged F-07 |
| T8 | Strategy library + validation gates + correlation + leaderboard design | done | e1c332ce | `x3lab/data/strategies.json`, `x3lab/data/validation_gates.json`, `x3lab/data/correlation.json`, `x3lab/data/leaderboard.json`, `analysis/*.md` | design docs; pilot stats computed from `week9.json` | pilot correlations computed by `scripts/compute_analysis.py` (n shown on every value) | production correlation values require play-by-play feed — flagged F-08 |
| T9 | Questions / information-gaps register | done | e1c332ce | `x3lab/data/questions.json`, `analysis/questions.md` | — | every gap has a discovery suggestion | none |
| T10 | Suggestions review section | done | e1c332ce | `x3lab/data/suggestions.json`, `analysis/suggestions.md` | — | each suggestion has status for human review | none |
| T11 | Executive summary | done | e1c332ce | `x3lab/executive-summary.html`, `analysis/executive-summary.md` | derived from data above | numbers re-checked against JSON data files | — |
| T12 | Site build (dashboard + subpages) | done | e1c332ce | `x3lab/*.html`, `x3lab/styles.css`, `x3lab/app.js` | renders `x3lab/data/*.json` | every table renders a Source cell or an UNVERIFIED badge | — |
| T13 | Verification pass (line by line) | done | e1c332ce | `scripts/verify_data.py`, `analysis/verification-log.md` | all of the above | `verify_data.py` gate: every data row carries `source` or `unverified: true`; site link check | results in verification-log |
| T14 | Integration + PR + Pages deploy | done | e1c332ce | repo root, `x3lab/` | GitHub | PR #1 merged to `main`; Pages enabled on `main` /docs; deploy confirmed | recorded below |

## File requests (cross-session)

_None._

## Log

- 2026-11-14 e1c332ce: board created; T1–T14 claimed by e1c332ce (single active session; arena branch constraint documented).
- 2026-11-14 e1c332ce: research complete (NFL.com standings/schedules; DraftKings odds via ESPN; ESPN injuries covering all 32 teams).
- 2026-11-14 e1c332ce: data written to `x3lab/data/`, model + verification scripts added and executed.
- 2026-11-14 e1c332ce: site built; `verify_data.py` passed; internal link check passed.
- 2026-11-14 e1c332ce: PR opened and merged (see "Integration record" below). GitHub Pages enabled; deploy confirmed.

## Integration record

- PR: https://github.com/karagemop466-tech/X3/pull/1 (branch `arena/e1c332ce-x3` → `main`)
- Merge result: merged (squash-free merge), 2026-11-14
- GitHub Pages: enabled, source = `main` /docs, site URL: https://karagemop466-tech.github.io/X3/
- Post-merge verification: site deploy checked 2026-11-14 (see `analysis/verification-log.md`).

## Verification policy (all sessions)

1. Never mark anything verified without a link to an official/trusted source and a fetch date.
2. Never infer or fill values. Unconfirmed values stay blank and carry `unverified: true` + a flag ID on the Flagged for Review page.
3. Every JSON data row must have `source` (URL) or `unverified: true`. `scripts/verify_data.py` enforces this.
4. Flags do not block merges. They are published on `x3lab/flagged.html` for human review.
