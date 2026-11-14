# X3 — NFL Decision Support

A decision-support platform for NFL markets, built on **official NFL sources
only**. It publishes a requirements register, an explicit register of what is
known and unknown, a reviewable suggestions board with alternative decision
paths, a research programme for self-originated lines and strategies with
machine-enforced validation gates, a competition that rewards skill rather
than luck, and continuous official injury and depth tracking.

**Live site:** <https://karagemop466-tech.github.io/X3/>

---

## The three rules the platform never breaks

1. **Every published number is traced to an official source.** Each table row
   carries a link to the exact official page it was read from, and each source
   payload is recorded with its SHA-256 and UTC fetch time.
2. **Nothing is inferred.** A value the official source does not publish is
   left blank and flagged. A statistic that cannot be computed because its
   dataset is missing is omitted, with the omission published and its reason
   recorded.
3. **Nothing is changed without a decision.** Suggestions are published with
   alternative paths, trade-offs and a recommendation, and each one stays in
   the *proposed* state until a reviewer chooses a path.

---

## Layout

```
COORDINATION.md            Shared task board for parallel agent sessions
_config.yml                Jekyll config for the legacy GitHub Pages build
requirements.txt           Python dependencies for the pipeline

data/
  content/                 Curated decision content (hand-authored, reviewed)
    requirements.json        the requirements register
    questions.json           the questions / information register
    suggestions.json         the suggestions and decision paths
    strategies.json          the strategy register and the validation gates
    leaderboard.json         the competition specification
  datasets/               Verified datasets generated from official sources
    fetch_manifest.json      provenance: URL, status, bytes, SHA-256, timestamp
    injuries.json            current official injury report
    injuries_history_*.json  the official weekly archive, by season
    standings_*.json         official standings by season
    schedule_*.json          official schedules and results by season
    player_stats_*.json       official player statistics by category and season
    depth_charts.json         official club depth charts, with coverage
    our_lines.json            the platform's own originated lines
    correlations.json         correlation matrices, with method and sample
    leaderboard_rows.json     back-test output for the leaderboard
    validation_report.json    the automated checks and their results
  raw/                    Raw official payloads (git-ignored; CI artefact)

scripts/
  lib/official.py           The official-source registry and the fetcher
  lib/parsers.py            HTML → flat, source-linked records
  lib/diagnostics.py        Build reports and structural summaries
  fetch_official.py         Fetch every official source with provenance
  build_datasets.py         Raw payloads → verified datasets
  compute_signals.py        Ratings, originated lines, correlations, back-test
  build_site.py             Render the site
  validate_site.py          Links, source links, unverified markers
  assets/                   style.css and app.js

docs/
  methodology.md            Exactly how every published number is computed
  irregularities.md         Repository review findings, open and resolved
  requirements-crosswalk.md  Brief statement → requirement → verification

index.html … validation.html   The generated site (published at the repo root)
```

The site is generated at the repository root because GitHub Pages is configured
for the legacy build from `main`; `_config.yml` excludes `data/`, `scripts/`
and `docs/` from the published output.

---

## Running the pipeline locally

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

.venv/bin/python scripts/fetch_official.py     # official payloads + provenance
.venv/bin/python scripts/build_datasets.py     # verified datasets
.venv/bin/python scripts/compute_signals.py    # lines, correlations, back-test
.venv/bin/python scripts/build_site.py         # the site
.venv/bin/python scripts/validate_site.py      # links, source links, markers
```

`scripts/validate_site.py --external` additionally requests every official URL
referenced by the site and fails the build if one does not answer. The same
sequence runs unattended in GitHub Actions on every push and on a twice-daily
schedule, so the published data stays current without any manual step.

---

## Working on this repository with other agent sessions

Read [`COORDINATION.md`](COORDINATION.md) first. It is the shared task board:
claim a task by writing your session ID and file scope into it, commit and push
that claim before you start, and never begin a task another session has
claimed. Keep file scopes non-overlapping. If you need a file owned by another
session, log a change request in the board rather than editing it.

---

## What is still open

The platform deliberately publishes what it does not know. See the
**Flagged for Review** page on the live site for every unverified value,
coverage gap and irregularity, with the source that was checked and what would
resolve it. The most consequential open items are the commercial-scope
questions (Q-001 to Q-003), the gate thresholds (Q-008, Q-009, Q-011) and the
per-game player-log acquisition that would unlock the player-prop strategy
classes (Q-005, S-013).

---

*Every statistic on the platform is computed from official NFL data. No
commercial betting line, projection service or third-party injury feed is
used anywhere in the pipeline.*
