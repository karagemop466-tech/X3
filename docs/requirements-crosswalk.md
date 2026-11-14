# Requirements crosswalk

Every sentence of the project brief, mapped line by line to the requirement
register, the artefact that satisfies it, and the verification performed.
Reviewed on 2026-11-14 by session `64164906`.

| # | Brief statement (quoted) | Requirement IDs | Satisfying artefact | Verification |
|---|---|---|---|---|
| 1 | "The goal of this project is to collect, organize, and analyze utilizing a full list of requirements." | REQ-PROG-001 | `requirements.html`, `data/content/requirements.json` | Every register row carries a rationale, acceptance criteria, priority, status and source. |
| 2 | "Make suggestions on how to improve the site to improve decision making" | REQ-PROG-002, REQ-SITE-003 | `suggestions.html` | Every suggestion states the problem it addresses and the expected impact on a decision. |
| 3 | "…and create a section dedicated for suggestions so someone can review suggestions and choose the best path before implementing any changes." | REQ-PROG-002, REQ-SITE-005 | `suggestions.html` | Each suggestion renders its decision paths side by side with cost, effort, risk and reversibility, and stays in the `proposed` state until a reviewer chooses. |
| 4 | "I want a clear list of questions, informations and answers that need to be addressed before any decision can be reasonably made bases upon the information that we already have and do not have." | REQ-PROG-003 | `questions.html`, `data/content/questions.json` | 28 questions, each with the decision blocked, what is known and sourced, what is missing, and an owner. |
| 5 | "Suggestions need to be made to discover missing information." | REQ-PROG-004 | `questions.html` | Every question carries a non-empty "Suggested actions to discover the missing information" list. |
| 6 | "I want to originate my own NFL lines." | REQ-STRAT-001 | `lines.html`, `data/datasets/our_lines.json`, `docs/methodology.md` §5 | Lines are produced by `scripts/compute_signals.py` from official standings and official final scores. No commercial line feed is ingested anywhere in the registry. |
| 7 | "Research and develop strategies for generating useful signals." | REQ-STRAT-002 | `strategies.html`, `data/content/strategies.json` | Ten strategies, each with a hypothesis, a computable signal definition and its official inputs. |
| 8 | "Treat it as a leaderboard competition that provides rewards for top performing strategies." | REQ-STRAT-003 | `leaderboard.html`, `data/content/leaderboard.json` | Entrant rules, a four-component weighted composite, tie-breaks, reward tiers and a transparency rule are published. |
| 9 | "Look at single bet, parlays, player prop bet combos." | REQ-STRAT-004 | `strategies.html` | All four classes are registered: single (ST-001 to ST-003), parlay (PL-001, PL-002), prop (PP-001 to PP-003), prop combo (PC-001, PC-002). |
| 10 | "Each strategy must pass validation gates." | REQ-STRAT-005 | `strategies.html` gate table G1–G10 | Each gate has a rule, a threshold, a status and a rationale; a strategy failing any gate is marked ineligible and excluded from reward. |
| 11 | "Determine correlation values." | REQ-STRAT-006 | `data.html` correlation matrices, `data/datasets/correlations.json` | Team-level and game-level Pearson matrices are computed from official standings and official final scores, each with unit, n and method. The player-prop matrix is listed as unavailable with its reason, not estimated. |
| 12 | "Remove luck from the equation and build strategies that are selectively skill based." | REQ-STRAT-007, REQ-STRAT-008 | `docs/methodology.md` §7, `leaderboard.html` | Skill share = model-implied variance ÷ observed variance, reported with a block-bootstrap interval and a permutation test against a pure-luck null. Only gate-passing strategies are eligible. |
| 13 | "The system should be tracking injuries" | REQ-INJ-001, REQ-INJ-005 | `injuries.html`, `data/datasets/injuries.json`, `data/datasets/injuries_history_<season>.json` | Every player row from the official report is published with practice status, game status and a source link; week, game date and fetch time are stored per row. |
| 14 | "…and know any deficiencies in defenses such as 2nd,3rd or 4th string backups having to replace starters due to lineups." | REQ-INJ-002 | `depth.html`, `data/datasets/depth_charts.json` | Depth strings are resolved only from official club depth charts, with a published coverage table. Unresolved rows are blank and flagged. |
| 15 | "Also same can be said for offenses using starters or backups." | REQ-INJ-003 | `depth.html` | The same resolution chain covers both units; the coverage gap is published rather than filled. |
| 16 | "Create an executive summary outlining important details." | REQ-PROG-005 | `executive-summary.html` | Purpose, current state, five blocking decisions, what is deliberately not done, and five recommended next actions, all linked from the landing page and from every subpage. |
| 17 | "There should be no manual input on my part." | REQ-PROG-006 | `.github/workflows/data-pipeline.yml` | Fetch → datasets → signals → site → validation runs unattended on push and on a twice-daily schedule, with no manual step. |
| 18 | "Work line by line, verify everything from official verified trusted sources, no hallucinations." | REQ-DATA-001, REQ-DATA-004, REQ-DATA-005, REQ-VER-001, REQ-VER-003 | `sources.html`, `data/datasets/fetch_manifest.json` | Only official NFL and official club domains appear in the registry. Every payload is recorded with URL, status, byte count, SHA-256 and UTC fetch time. |
| 19 | "Create a github page live site for this repo with a clean landing page and subpages organized by category." | REQ-SITE-001, REQ-SITE-002 | `index.html` and 14 subpages | Navigation is grouped into Overview, Requirements, Decision Support, Strategy, Data and Governance. |
| 20 | "The UI should be clean, user friendly, simple, and easy to use, like a simple dashboard." | REQ-SITE-003 | `assets/style.css`, `assets/app.js` | One shared stylesheet, sticky grouped navigation, KPI cards before tables, and client-side filter and sort on every table. |
| 21 | "It should contain all entries and findings in a simple, easy to read table format, and include any analysis and findings." | REQ-SITE-004 | Every data and register page | Each dataset and register renders as a table with a header row and a source column; the validator asserts this. |
| 22 | "Verify line by line. Every table row must have a source link to an official site." | REQ-DATA-002, REQ-VER-001 | `scripts/validate_site.py` check 2 and 3 | The build fails if any dataset row lacks an official `source_url` or if any published link points at a non-official host. |
| 23 | "If a value can't be confirmed from an official source, leave it blank and flag it as unverified." | REQ-DATA-003 | `flagged.html`, `unverified` markers | Blank official values render as an explicit `unverified` marker; the flag register is generated from the same dataset metadata that renders the tables. |
| 24 | "Never infer or fill in values." | REQ-DATA-003, REQ-STRAT-007 | `docs/methodology.md` §2, §8 | Statistics that cannot be computed are omitted and listed as unavailable with the reason; nothing is substituted from a proxy. |
| 25 | "Multiple agent sessions may work on this repo at the same time, so coordinate to avoid conflicts and duplicate work." | REQ-PROG-007 | `COORDINATION.md` | Task board with status, owner session, branch and file scope; claims committed and pushed before work starts. |
| 26 | "When all tasks are done and the final integration session has verified the combined data and confirmed the site builds with no broken links, create a pull request…" | REQ-PROG-008, REQ-VER-004 | `COORDINATION.md` log, pull request | Recorded in the coordination log with the validator output, the pull-request link and the merge result. |

---

## Coverage statement

* **Brief statements covered:** 26 of 26.
* **Requirements in the register:** 32, each traceable to one or more brief
  statements above.
* **Requirements fully implemented:** 27.
* **Requirements partially implemented:** 2 — `REQ-INJ-002` and `REQ-INJ-003`,
  because the depth string of a replacement can only be resolved where the
  club publishes an official depth chart. The remaining gap is published as
  coverage on the Depth page and as a flagged item; it is not filled in.
* **Requirements planned:** 0.
* **Requirements blocked:** 0 at the register level. Individual items inside
  the requirements are blocked by the open questions, which are recorded
  against the affected requirement rather than hidden.
