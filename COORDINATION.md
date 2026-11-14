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
| T0 | Repo/branch review, irregularity log, scaffold | done | `64164906` | `arena/64164906-x3` | `README.md`, `docs/` |
| T1 | COORDINATION.md board + protocol | done | `64164906` | `arena/64164906-x3` | `COORDINATION.md` |
| T2 | Official-source fetch layer + provenance (hash, timestamp, URL) | done | `64164906` | `arena/64164906-x3` | `scripts/lib/official.py`, `scripts/fetch_official.py` |
| T3 | Verified dataset build (injuries, schedule, standings, stats, depth) | done | `64164906` | `arena/64164906-x3` | `scripts/lib/parsers.py`, `scripts/build_datasets.py`, `data/datasets/` |
| T4 | Requirements register (collect → organize → analyze) | done | `64164906` | `arena/64164906-x3` | `data/content/requirements.json` |
| T5 | Questions / Information Needed (known vs unknown, Q&A) | done | `64164906` | `arena/64164906-x3` | `data/content/questions.json` |
| T6 | Suggestions & Decision Paths (reviewable, ranked, not auto-applied) | done | `64164906` | `arena/64164906-x3` | `data/content/suggestions.json` |
| T7 | Strategy R&D (single bet, parlay, player props; gates; correlation) | done | `64164906` | `arena/64164906-x3` | `data/content/strategies.json` |
| T8 | Leaderboard competition spec + scoring | done | `64164906` | `arena/64164906-x3` | `data/content/leaderboard.json` |
| T9 | Executive summary | done | `64164906` | `arena/64164906-x3` | `scripts/build_site.py` (executive summary section) |
| T10 | Flagged for Review registry | done | `64164906` | `arena/64164906-x3` | `scripts/build_site.py` (flag register), `flagged.html` |
| T11 | Site generator + UI (landing + subpages, tables, nav) | done | `64164906` | `arena/64164906-x3` | `scripts/build_site.py`, `scripts/assets/`, site pages at repo root |
| T12 | CI: fetch → build → validate → deploy GitHub Pages | done | `64164906` | `arena/64164906-x3` | `.github/workflows/data-pipeline.yml`, `scripts/validate_site.py` |
| T13 | Final integration: merge branches, re-verify line by line, PR → main, publish | in progress | `64164906` | `arena/64164906-x3` | all (integration session only) |

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


### 2026-11-14 — session `64164906` (continued)

- **T2 (done):** `scripts/lib/official.py` — the official-source registry (NFL.com, NFL Football Operations, NFL Communications and all 32 official club domains) and a concurrent fetcher that records, per source: URL, final URL, HTTP status, byte count, **SHA-256** and UTC fetch timestamp. `scripts/fetch_official.py` is the CLI. No third-party line, projection or injury feed appears anywhere in the registry.
- **T3 (done):** `scripts/lib/parsers.py` + `scripts/build_datasets.py` — parsers for the official injury report, standings, schedules, player statistics and club depth charts, plus the official **historical injury archive** (`/injuries/league/<season>/reg<week>`), which makes a multi-season availability back-test possible. `scripts/lib/diagnostics.py` writes a structural report of every parsed payload into `data/datasets/`, so a parser can be repaired from the repository alone.
- **T4–T8 (done):** the curated content registers: 32 requirements with acceptance criteria and status, 28 questions with known/unknown/how-to-obtain, 20 suggestions each with alternative decision paths, 10 strategies with a 10-gate validation table, and the leaderboard competition specification.
- **T9–T12 (done):** `scripts/build_site.py` renders 16 pages at the repository root (required because GitHub Pages is locked to the legacy Jekyll build from `main`; `_config.yml` excludes `data/`, `scripts/` and `docs/` from publication). `scripts/validate_site.py` fails the build on a broken internal link, a dataset row without an official `source_url`, or an external link to a non-official host. `.github/workflows/data-pipeline.yml` runs fetch → fixtures → self-test → datasets → signals → site → validate on every push and on a twice-daily schedule.
- **Self-tests:** `scripts/selftest.py` runs 40 offline checks over the parsers, the depth-string resolver, the skill-share metric, correlation and scoring, using fixtures captured from the live official pages by `scripts/capture_fixtures.py`.

#### Sources verified

| Source | URL | Verified |
|---|---|---|
| Official injury report | `https://www.nfl.com/injuries/` | HTTP 200, 182 rows across 14 games |
| Official injury archive | `https://www.nfl.com/injuries/league/<season>/reg<week>` | HTTP 200, weekly weeks exposed |
| League standings | `https://www.nfl.com/standings/league/2026/REG` | HTTP 200, 32 teams |
| Weekly schedule | `https://www.nfl.com/schedules/2026/REG<week>/` | HTTP 200 |
| Player statistics | `https://www.nfl.com/stats/player-stats/category/<cat>/<year>/reg/all/<metric>/desc` | HTTP 200, 11 categories |
| 2026 Rulebook | `https://operations.nfl.com/rules-officiating/2026-nfl-rulebook` | HTTP 200 |
| Official Playing Rules PDF | `https://media.nfl.com/content/dam/communications/Official%20Playing%20Rules/2026%20Official%20Playing%20Rules.pdf` | HTTP 200 |
| Official club depth charts | `https://www.<club>.com/team/depth-chart` | HTTP 200 for 30 of 32 clubs |

#### Irregularities found and their resolution

Recorded in full in `docs/irregularities.md`. Summary: (1) the repository contained only a one-line README and one commit, so there was nothing to migrate; (2) shell egress cannot reach `nfl.com`, so retrieval runs in CI and the committed datasets are the verified snapshot of that run; (3) `operations.nfl.com/rules/` and `nfl.com/news/nfl-communications` both 404 and were replaced with verified URLs; (4) the Texans and Titans club domains were transposed and were corrected; (5) several club sites return the same application shell for every path, so a depth chart is accepted only when the page genuinely contains one; (6) the official injury archive is current-state rather than point-in-time, which is stated as a back-test limitation; (7) `nfl.com/games/<slug>/boxscore` 404s, so per-game player logs are not yet available; (8) the Pages API returns 403, so the legacy `main`/root build is used.

#### Method decisions worth recording

- **Own-line circularity.** The platform originates its own lines, so scoring a strategy against them measures agreement, not skill. Three mitigations are in place (distinct signal per strategy, the line model published as a *benchmark* rather than a competitor, and suggestion S-002 proposing a separately specified evaluation reference). The issue is stated on the Strategies page, in `docs/methodology.md` §9 and on the Findings page.
- **Skill share.** The share of a strategy's outperformance that its own model explains rather than sampling variation, measured against a fair-coin null at the same prices, with a block-bootstrap interval and a permutation test. A strategy with no edge scores exactly 0, so luck cannot inflate it.
- **Unverified rendering.** A blank official cell renders as an explicit `unverified` marker; a statistic that cannot be computed because its dataset is missing is *omitted* and the omission is listed with its reason on the Flagged for Review page.

### Rules of engagement (binding)

1. One session = one branch: `session-<id>/<task>`. Never edit another session's branch.
2. Never edit a file listed in another session's **File scope**. Log a Change Request instead.
3. Small, frequent commits. `git pull --rebase` before every push.
4. A merge conflict must be resolved **without discarding** the other side's work; record it in the Log.
5. **Never** mark anything verified without checking it against an official source **and** linking that source.
6. A value that cannot be confirmed from an official source is left **blank** and flagged `unverified` — never inferred, never filled in.
7. Shared outputs (site `index`/navigation, combined table data) are changed only by the final integration session (T13).
8. A claim with no commit for 60 minutes may be taken over; note the handoff in the Log.
