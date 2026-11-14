# Line Origination & Signal Generation — research notes (T3)

**Session:** arena-4856379c · **Date:** 2026-11-14 · Every factual claim below carries its source URL.
Claims with no available source are marked **UNVERIFIED** and left numerically blank.

## 1. What "originating your own lines" means (operational definition)

Produce your own fair spread / fair total / fair moneyline probabilities **before** looking at the
market's final price, then compare. The gap ("your number − market number") is the raw signal.
Everything downstream (validation, staking, leaderboard scoring) is designed to tell real skill
from luck.

## 2. Verified market-context findings (what the research literature supports)

| Finding | Detail | Source (official host) |
|---|---|---|
| Books do not necessarily balance action; they price to exploit public bias | Levitt (2004), *The Economic Journal* 114(495):223–246, DOI 10.1111/j.1468-0297.2004.00207.x | https://pricetheory.uchicago.edu/levitt/Papers/LevittWhyAreGamblingMarkets2004.pdf |
| Late-week odds movement is driven by sharp action more than late injury news | Claremont Graduate University thesis (2025), NFL moneyline 2020–2024 high-frequency odds: movement predictability; AUC jump mostly between 6→3 days out | https://scholarship.claremont.edu/cgi/viewcontent.cgi?article=5145&context=cmc_theses |
| Home-field advantage appears overvalued in forecasted-close games (0.30–0.70 win prob band) | Same thesis: away-team system +46.16 units over 851 games sample (2020–2024), profits concentrated pre-2023 | https://scholarship.claremont.edu/cgi/viewcontent.cgi?article=5145&context=cmc_theses |
| Closing lines are generally efficient but have documented exceptions | Oswald (2022) as summarized in the same thesis (underdogs >7 in games with totals >50.5 covered 64.7% 2007–2022) — **treat as reported-by-secondary, flagged** | https://scholarship.claremont.edu/cgi/viewcontent.cgi?article=5145&context=cmc_theses |
| Historical profitable situational angles (in-sample only, 2013–2019) | Under in divisional games with high wind; home favorite + over parlay in prime-time non-divisional; home underdog + under parlay in divisional games with spread 10–13.5. Abstract itself warns results "unlikely to persist" | Skidmore College repository: https://digitalcoll.skidmore.edu/record/6451 |
| Break-even price for a standard −110 spread bet | 52.38% (cited in the Claremont thesis; also arithmetically 110/210) | https://scholarship.claremont.edu/cgi/viewcontent.cgi?article=5145&context=cmc_theses |
| Line movement carries information: opening→closing difference predicted divisional winners ≥75% (2002–2011 sample) | Published study of 2,560 games | https://www.academia.edu/34611270/The_Performance_of_Betting_Lines_for_Predicting_the_Outcome_of_NFL_Games (secondary index of the paper — flagged) |
| Favorite–longshot bias exists directionally in NFL prices | Independent replication (7,276 games 1999–2025): longshots −12.0% OOS vs heavy favorites −1.5%; closing line calibrated (Brier 0.210) | https://github.com/gouthamperavali4610-web/nfl-market-efficiency (community replication, trusted-secondary) |

## 3. The origination framework (proposal — design, not a data claim)

### 3.1 Inputs (each must be a versioned, timestamped, sourced feed)
1. **Team quality:** EPA/play, success rate, drive-quality splits (offense/defense/ST). Trusted data
   source: nflverse play-by-play (community-maintained, used league-wide): https://github.com/nflverse/nflverse-data
   (trusted-secondary, not NFL-official — flagged in sources ledger).
2. **QB + lineup state:** starter/baseline vs current QB on each team (see injury system, T7).
3. **Injury & depth deltas:** unit-level Out/Doubtful counts and starter-replacement flags (T7).
4. **Situational:** rest days, bye, travel distance, international games (e.g., Munich game in
   Week 10, 2026 — per official schedule context), altitude, prime-time splits.
5. **Weather:** wind speed/direction, precipitation, temperature at kickoff (wind ≥ 15 mph classically
   suppresses passing/total scoring — mechanism cited in the Skidmore thesis's high-wind under angle:
   https://digitalcoll.skidmore.edu/record/6451).
6. **Market anchors (only after own number is frozen):** opening line, current consensus, limits.

### 3.2 Core model (transparent, calibratable)
- Rating system: margin-of-victory–damped Elo, walk-forward only. Reference implementation with
  published parameters (K=20, HFA≈52 rating pts, ⅓ off-season mean reversion): community
  replication at https://github.com/gouthamperavali4610-web/nfl-market-efficiency (trusted-secondary).
  **Our own HFA and damping parameters must be calibrated on our own data — values blank until then
  (UNVERIFIED).**
- Rating gap → expected margin → win probability via a logistic/normal margin model.
  The margin-distribution σ is a calibration parameter; **value intentionally left blank** —
  it must be fit from our own play-by-play sample and bootstrapped (see validation gates).
- Fair total from pace × efficiency projections, adjusted for weather/pace scripts.
- De-vig market probabilities using the power method (solve Σpᵢᵏ = 1) rather than naive
  normalization (methodology implemented in the community replication above).

### 3.3 Signal catalog (what the leaderboard scores)

| ID | Signal | Skill mechanism | Primary validation gate |
|---|---|---|---|
| S1 | Model-vs-market gap beyond own uncertainty band | Better inputs/model | CLV + DSR |
| S2 | Early line-move / sharp-action confirmation (bet early in the week) | Timing (movement driven by sharp action, per Claremont thesis) | CLV |
| S3 | Injury/depth delta the market has not repriced (esp. secondary & OL units, backup QBs) | Information speed | CLV + injury-specific holdout |
| S4 | Weather/total mispricing (wind, cold, precipitation) | Public underweights weather | CLV |
| S5 | Key-number leverage (buy/sell around margins 3 and 7) | Pricing granularity | CLV at bought price |
| S6 | Situational (rest/bye/travel/international) | Schedule awareness | CLV + season-stability |
| S7 | Correlated combo structure (parlays/prop combos priced below joint probability) | Correlation modeling | Per-leg CLV + joint-probability gate |
| S8 | Contrarian fade of public bias (Levitt mechanism) | Structural market bias | CLV + PBO |

> Timing rule: S2/S3 are only credited when the bet is logged **before** the market moves
> (timestamped submission), otherwise it is hindsight, not skill.

## 4. "Selectively skill based" — what this means here
- **Skill components:** input quality, model specification, timing, selection filters, correlation
  estimation, staking discipline.
- **Luck components:** single-game variance, parlay binomial noise, small-sample ROI.
- The pipeline separates them mechanically: all ranking runs through the validation gates
  (research/validation.md) — CLV, Deflated Sharpe Ratio, Probability of Backtest Overfitting,
  Monte-Carlo luck baselines, walk-forward OOS. A strategy can only be labeled skill-based after
  clearing those gates; anything else is labeled **lucky until proven otherwise**.

## 5. Open research items (see questions page)
- Opening-line feeds and closing-consensus feeds (data licensing) — not yet available to this repo.
- Our own calibrated σ of margin distribution — needs play-by-play ingestion.
- Sportsbook-specific SGP correlation adjustments are proprietary and vary by book
  (practitioner claim, source: https://www.oddsshopper.com/articles/betting-101/nfl-parlay-betting —
  industry secondary, flagged); estimating *true* correlation is our job (research/correlation.md).
