# COORDINATION.md

Shared task board for the X3 (NFL) project.
Branch: `arena/1a771fcd-x3` (branched from `main` @ e124230)
Session ID: `arena/1a771fcd-x3`

Status legend: unclaimed | in progress | done | needs review

## Tasks

| # | Task | Status | Owner (session ID) | File scope | Sources / verification | Irregularities |
|---|------|--------|--------------------|------------|------------------------|----------------|
| 1 | Create COORDINATION.md task board | done | arena/1a771fcd-x3 | COORDINATION.md | n/a | none |
| 2 | Review repo contents; flag irregularities | done | arena/1a771fcd-x3 | repo root | n/a | Repo was empty apart from README.md ("# X3"); no existing data, docs, or site config |
| 3 | Research NFL official sources (NFL.com, team sites) for lines/signals/injuries | done | arena/1a771fcd-x3 | docs/sources.md | nfl.com/injuries; Sportradar NFL feeds docs | Direct fetch of nfl.com blocked by sandbox network; row-level data not verified |
| 4 | Executive summary | done | arena/1a771fcd-x3 | pages/executive-summary.md | nfl.com/injuries; Sportradar docs | Betting lines & props: no official source identified |
| 5 | Suggestions & decision framework (questions, info, answers, missing-info discovery) | done | arena/1a771fcd-x3 | pages/suggestions.md | nfl.com/injuries; Sportradar docs | All data cells blank/unverified pending official fetch |
| 6 | "Flagged for Review" page content (unverified items + irregularities) | done | arena/1a771fcd-x3 | pages/flagged-for-review.md | nfl.com/injuries; Sportradar docs | I-01 empty repo, I-02 no NFL lines source, I-03 fetch blocked |
| 7 | NFL lines origination: strategies, signals, validation gates, correlations, single/parlay/prop combos, leaderboard design | done | arena/1a771fcd-x3 | pages/strategies.md | Sportradar docs; nfl.com/injuries (cycle only) | No strategy/correlation/reward value confirmed from official source |
| 8 | Injury & backup (depth-chart) tracking system design | done | arena/1a771fcd-x3 | pages/injuries.md | nfl.com/injuries; Sportradar docs | All depth values blank/unverified |
| 9 | GitHub Pages static site: landing page + category subpages, data tables with source links | done | arena/1a771fcd-x3 | site/** | n/a | HTML validated; no broken internal links |
| 10 | GitHub Actions Pages deploy workflow | done | arena/1a771fcd-x3 | .github/workflows/pages.yml | n/a | Deploy not yet triggered |
| 11 | Integration: re-verify combined data line by line, confirm site builds | in progress | arena/1a771fcd-x3 | all | n/a | Pending push + Pages build |
| 12 | Create PR from integration branch to main; merge; confirm Pages deploy; record PR link & result | unclaimed | arena/1a771fcd-x3 | COORDINATION.md | n/a | Pending |

## Claims log
- session `arena/1a771fcd-x3` claims tasks 1-12 on branch `arena/1a771fcd-x3` (single-session operation; no overlapping sessions detected)

## Notes
- Sandbox outbound network is restricted to github.com / api.github.com / codeload.github.com / registry.npmjs.org / pypi.org / files.pythonhosted.org. Official NFL sources (nfl.com, team sites) cannot be fetched directly with curl; verification is via web_search and cited by URL. Any value that cannot be confirmed from an official source is left blank and flagged "unverified" on the Flagged for Review page. No values are inferred or filled in.
