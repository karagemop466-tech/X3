# COORDINATION.md

Shared task board for the X3 (NFL) project.
Integrated branches: `arena/1a771fcd-x3` (this session) and `arena/d667d44d-x3` (prior session, merged to `main` via PR #1).
Status legend: unclaimed | in progress | done | needs review

## Sessions
- `arena/1a771fcd-x3` — current integration session (this branch → main)
- `arena/d667d44d-x3` — prior session; work merged to `main` (PR #1): root decision-lab site + Pages workflow

## Tasks

| # | Task | Status | Owner | File scope | Sources / verification | Irregularities |
|---|------|--------|-------|------------|------------------------|----------------|
| 1 | Repository audit / coordination board | done | arena/d667d44d-x3 | `COORDINATION.md` | Repo began with only a 4-byte README.md; no data, site, or board | none |
| 2 | NFL evidence & research (official sources) | done | arena/d667d44d-x3 | `docs/**`, root sources | nfl.com/injuries, nfl.com/stats, operations.nfl.com 2026 rulebook, docs.github.com/pages | Some candidate URLs 404'd; replaced with working official URLs |
| 3 | Landing page, navigation, data tables, Pages integration | done | arena/d667d44d-x3 | root site files (`index.html`, `strategy.html`, `data.html`, `flagged.html`, `review.html`, `sources.html`, `style.css`, `.github/workflows/pages.yml`) | Six static pages parsed; all relative links verified | No deployed Pages URL asserted until GitHub confirms |
| 4 | GitHub Pages static site: landing page + category subpages (this session) | done | arena/1a771fcd-x3 | `site/`, `pages/` | All HTML validated; internal links checked | HTML pages parse cleanly |
| 5 | Executive summary | done | arena/1a771fcd-x3 | `pages/executive-summary.html` | nfl.com/injuries; Sportradar feeds docs | Betting lines & props: no official source identified |
| 6 | Suggestions & decision framework (questions, info, answers, missing-info discovery) | done | arena/1a771fcd-x3 | `pages/suggestions.html` | nfl.com/injuries; Sportradar feeds docs | All data cells blank/unverified pending official fetch |
| 7 | Flagged for Review page (unverified items + irregularities) | done | arena/1a771fcd-x3 | `pages/flagged-for-review.html` | nfl.com/injuries; Sportradar feeds docs | I-01 empty repo at branch point; I-02 no NFL lines source; I-03 fetch blocked |
| 8 | NFL lines origination: strategies, signals, validation gates, correlations, single/parlay/prop combos, leaderboard design | done | arena/1a771fcd-x3 | `pages/strategies.html` | Sportradar docs; nfl.com/injuries (cycle only) | No strategy/correlation/reward value confirmed from official source |
| 9 | Injury & backup (depth-chart) tracking system design | done | arena/1a771fcd-x3 | `pages/injuries.html` | nfl.com/injuries; Sportradar docs | All depth values blank/unverified |
| 10 | Sources page (official sources only) | done | arena/1a771fcd-x3 | `pages/sources.html` | nfl.com/injuries; Sportradar docs | No official NFL betting-lines or player-prop source identified |
| 11 | GitHub Actions Pages deploy workflow | in progress | arena/1a771fcd-x3 | `.github/workflows/pages.yml` | docs.github.com/pages | Deploy check not yet confirmed on merged `main` |
| 12 | Integration: merge branches, re-verify combined data, confirm site builds with no broken links | in progress | arena/1a771fcd-x3 | all | Internal link check in pages.yml | Merge conflicts resolved on 3 shared files |
| 13 | Create PR from integration branch to main; merge; confirm Pages deploy; record PR link & result | in progress | arena/1a771fcd-x3 | `COORDINATION.md` | PR #3 | PR #3 not yet merged |

## Claims log
- `arena/d667d44d-x3` claimed root site files, `docs/**`, `COORDINATION.md` (merged to main via PR #1).
- `arena/1a771fcd-x3` claims `site/`, `pages/`, and integration of both branches on `arena/1a771fcd-x3` → `main`. No overlap with root site files owned by `arena/d667d44d-x3`; shared files (`COORDINATION.md`, `README.md`, `.github/workflows/pages.yml`) resolved during integration without discarding either session's work.

## Notes
- Sandbox outbound network is restricted to github.com / api.github.com / codeload.github.com / registry.npmjs.org / pypi.org / files.pythonhosted.org. Official NFL sources (nfl.com, team sites) cannot be fetched directly with curl; verification is via web_search and cited by URL. Any value that cannot be confirmed from an official source is left blank and flagged "unverified" on the Flagged for Review page. No values are inferred or filled in.
- Live Pages source is `main` branch root (`/`). After merge, GitHub's legacy root build serves root HTML files; the Actions workflow also deploys the root artifact.
