# COORDINATION.md — Shared Task Board

**Repository:** `karagemop466-tech/X3`
**Purpose:** NFL decision-support platform — requirements register, evidence/verification ledger, strategy research (self-originated lines), injury & depth tracking, leaderboard, and a published GitHub Pages dashboard.

> **How to use this file.** Every parallel agent session must read this file *before* starting work. Claim a task by writing your session ID into the **Owner** column and the files you touch into **File scope**, then `git commit` and `git push` that claim immediately. Never start a task that already has an owner. Keep scopes non-overlapping. If you need a file owned by another session, add a row to **Change Requests** instead of editing it. When a task is finished, record its sources, the verification performed, and any irregularities in the **Log**, then set the status to `done`.
>
> Statuses: `unclaimed` → `in progress` → `needs review` → `done`. `needs review` means the item is published on the site's **Flagged for Review** page and blocks nothing.

---

## Task Board

| # | Task | Status | Owner session | Branch | File scope |
|---|------|--------|---------------|--------|-----------|
| T0 | Repo/branch review, irregularity log, scaffold | in progress | `64164906` | `arena/64164906-x3` | `README.md`, `docs/`, `scripts/`, `data/` |
| T1 | COORDINATION.md board + protocol | done | `64164906` | `arena/64164906-x3` | `COORDINATION.md` |
| T2 | Official-source fetch layer + provenance (hash, timestamp, URL) | unclaimed | — | — | `scripts/fetch_*.py`, `data/raw/` |
| T3 | Verified dataset build (injuries, schedule, standings, stats, depth) | unclaimed | — | — | `data/datasets/*.json`, `data/verified/*.csv` |
| T4 | Requirements register (collect → organize → analyze) | unclaimed | — | — | `data/content/requirements.json` |
| T5 | Questions / Information Needed (known vs unknown, Q&A) | unclaimed | — | — | `data/content/questions.json` |
| T6 | Suggestions & Decision Paths (reviewable, ranked, not auto-applied) | unclaimed | — | — | `data/content/suggestions.json` |
| T7 | Strategy R&D (single bet, parlay, player props; gates; correlation) | unclaimed | — | — | `data/content/strategies.json` |
| T8 | Leaderboard competition spec + scoring | unclaimed | — | — | `data/content/leaderboard.json` |
| T9 | Executive summary | unclaimed | — | — | `data/content/executive_summary.json` |
| T10 | Flagged for Review registry | unclaimed | — | — | `data/content/flagged.json` |
| T11 | Site generator + UI (landing + subpages, tables, nav) | unclaimed | — | — | `scripts/build_site.py`, `site/` |
| T12 | CI: fetch → build → validate → deploy GitHub Pages | unclaimed | — | — | `.github/workflows/*.yml` |
| T13 | Final integration: merge branches, re-verify line by line, PR → main, publish | unclaimed | — | — | all (integration session only) |

---

## Change Requests

| # | Requested by | Target owner | File | Reason | Status |
|---|--------------|--------------|------|--------|--------|
| — | — | — | — | — | — |

---

## Log

### 2026-11-14 — session `64164906`

- **T1 (done):** Created `COORDINATION.md`. No prior board existed; repo contained only `README.md` (`# X3`, 1 commit `e124230`).
- **T0 (in progress):** Repo reviewed. Findings recorded in `docs/irregularities.md`. Network note: shell egress in this sandbox is restricted to `github.com`, `api.github.com`, `codeload.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. `www.nfl.com` is **not** reachable from the shell (TLS EOF), so live official-source pulls are executed in GitHub Actions, and a **verified snapshot** committed under `data/` is the reproducible, reviewable artifact. Every snapshot record carries `source_url`, `fetched_at`, and `sha256`.

### Rules of engagement (binding)

1. One session = one branch: `session-<id>/<task>`. Never edit another session's branch.
2. Never edit a file listed in another session's **File scope**. Log a Change Request instead.
3. Small, frequent commits. `git pull --rebase` before every push.
4. A merge conflict must be resolved **without discarding** the other side's work; record it in the Log.
5. **Never** mark anything verified without checking it against an official source **and** linking that source.
6. A value that cannot be confirmed from an official source is left **blank** and flagged `unverified` — never inferred, never filled in.
7. Shared outputs (site `index`/navigation, combined table data) are changed only by the final integration session (T13).
8. A claim with no commit for 60 minutes may be taken over; note the handoff in the Log.
