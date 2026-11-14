# Correlation Values — research notes (T5)

**Session:** arena-4856379c · **Date:** 2026-11-14

## 1. Verification outcome (the headline)

**No official or peer-reviewed source available to this session publishes a numeric pairwise
correlation matrix for NFL same-game legs (QB props × WR props, team total × moneyline, etc.).
Per the project rules, every numeric correlation value is left BLANK and flagged UNVERIFIED.
What we publish instead:** (a) verified directional/structural findings with sources,
(b) a complete, reproducible estimation pipeline to fill the matrix from official play-by-play
data, (c) the ready-to-fill table schema.

## 2. Verified structural findings about correlation in NFL betting

| Finding | Source (host) | Tier |
|---|---|---|
| Same-game legs are correlated; books apply a proprietary "correlation adjustment" (SGP tax) that shortens payouts vs independent multiplication; same SGP prices differ across books | https://www.oddsshopper.com/articles/betting-101/nfl-parlay-betting | Industry secondary — flagged |
| Directional examples: QB passing yards × top-WR receiving yards (positive); favorite covering × team total over (positive); blowout for A × high passing yards for B's QB (negative) | https://nfl-prop-bets.com/articles/nfl-same-game-parlay/ | Industry secondary — flagged |
| Empirical audit (practitioner): book correlation adjustments estimated 5–15 pts more aggressive than historical data supported; SGP hold 20–35% vs ~4.5% spread hold | https://bestnflfuturesbets.com/articles/nfl-same-game-parlays-futures-trap/ | Industry secondary — flagged |
| Cross-game parlay margin = compounding of leg holds (~13–14% for 3 legs at standard prices); correlation transparency is the key structural difference from SGPs | https://bestnflfuturesbets.com/articles/nfl-same-game-parlays-futures-trap/ | Industry secondary — flagged |
| Peer-reviewed-style finding: favorites covering (ATS) and game totals going over are positively correlated in college football → "correlated parlay" profitability analysis (Davis, 2018) | Cited via https://www.bettoredge.com/post/parlay-betting-strategy-tips-and-tricks-to-win-and-maximize-payouts (primary paper not directly retrievable this session — **flagged**) | Academic (via secondary) |
| NFL 2013–2019 OLS study found in-sample profits for: home favorite + over parlay (prime time, non-divisional); home underdog + under parlay (divisional, spread 10–13.5); under in divisional high-wind games. Abstract warns results "unlikely to persist" | Skidmore College official repository: https://digitalcoll.skidmore.edu/record/6451 | Academic (student thesis) |

## 3. The correlation matrix to be filled (values BLANK = UNVERIFIED)

Estimation spec: compute pairwise joint outcomes from ≥3 seasons of official play-by-play +
player-stats data (trusted pipeline: nflverse — https://github.com/nflverse/nflverse-data,
trusted-secondary; ultimate official source is NFL GSIS/Next Gen Stats,
https://www.nfl.com/stats/ — official). Report Pearson φ/tetrachoric correlation for binary legs,
rank correlation for continuous props, with block-bootstrap 95% CIs (game-level resampling).

| Leg A | Leg B | Expected sign (hypothesis) | Correlation value | 95% CI | Status |
|---|---|---|---|---|---|
| QB passing yards OVER | Primary WR receiving yards OVER | positive | (blank) | (blank) | UNVERIFIED — no official numeric source |
| QB passing yards OVER | Game total OVER | positive | (blank) | (blank) | UNVERIFIED |
| Team spread cover | Team total OVER | positive | (blank) | (blank) | UNVERIFIED (direction supported by Davis 2018 via secondary) |
| Favorite ML | Game total OVER | weak positive | (blank) | (blank) | UNVERIFIED |
| Home favorite spread + over parlay (prime time, non-divisional) | — (combo study) | positive EV in-sample 2013–2019 | (blank) | (blank) | UNVERIFIED as current value (study is dated) |
| RB anytime TD | Team win | positive | (blank) | (blank) | UNVERIFIED |
| Opposing QB passing yards OVER | Blowout for other team | negative | (blank) | (blank) | UNVERIFIED |
| Under 10–13.5 pt home underdog + under (divisional) | — (combo study) | positive EV in-sample 2013–2019 | (blank) | (blank) | UNVERIFIED as current value |

> Rule applied: **never infer or fill in values**. Signs marked "hypothesis" are testable claims for
> the estimation pipeline, not verified values; the direction claims that DO have sources are cited.

## 4. Estimation pipeline (to produce verified values in a later session)
1. Data: nflverse play-by-play + weekly rosters + player stats (https://github.com/nflverse/nflverse-data);
   official cross-check sample against https://www.nfl.com/stats/.
2. Unit of analysis: game × player × market leg, closing consensus lines required for EV work
   (data gap — see questions page Q-07).
3. For each leg pair: contingency table (binary) or copula/rank model (continuous); game-level
   block bootstrap (10,000 resamples) for CIs.
4. Publish value + CI + sample size + data version hash; any pair whose CI spans 0 is displayed blank.
5. Re-estimate each offseason; freeze within-season to prevent fit-to-week overfitting (Gate G8).

## 5. How this feeds the strategy competition
- Combo strategies (parlays, prop combos) score only when their joint-probability model beats the
  book's implied joint probability after vig removal (validation gate stack G0–G8 +
  parlay gates in research/validation.md).
- The leaderboard's correlation credit is binary: use published matrix (verified rows only) or
  submit your own estimate with CI + reproducible code.
