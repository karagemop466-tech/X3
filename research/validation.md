# Validation Gates & Luck Removal — research notes (T4)

**Session:** arena-4856379c · **Date:** 2026-11-14 · Academic references verified at official hosts (SSRN, publisher DOIs).

## 1. Verified statistical foundations

| Method | What it does | Verified source (official host) |
|---|---|---|
| Probabilistic Sharpe Ratio (PSR) | Probability the true Sharpe exceeds a benchmark, robust to non-normal returns (skew/kurtosis) | Bailey & López de Prado (2012), *Journal of Risk* 15(2):3–44 — described at https://dx.doi.org/10.2139/ssrn.2326253 (SSRN record of the follow-on PBO paper lists it in references) |
| Deflated Sharpe Ratio (DSR) | PSR whose benchmark is the expected max Sharpe of N random trials — corrects selection bias/backtest overfitting; DSR ≥ 0.95 ⇒ ≥95% chance the edge is real after multiplicity | Bailey & López de Prado (2014), *Journal of Portfolio Management* 40(5):94–107, DOI 10.3905/jpm.2014.40.5.094; preprint https://ssrn.com/abstract=2460551 |
| Probability of Backtest Overfitting (PBO) via CSCV | Probability that the "best" backtest strategy is actually worse than median out-of-sample | Bailey, Borwein, López de Prado, Zhu (2015), *Journal of Computational Finance*; preprint https://ssrn.com/abstract=2326253 (also https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) |
| False Strategy Theorem / winner's curse of backtests | After ~1,000 skill-free trials, the expected best Sharpe ≈ 3.26 — great backtests arise from noise alone | Bailey & López de Prado (2014), per https://dx.doi.org/10.2139/ssrn.2460551 (interpretation summarized at https://interactiveml.org/blog/deflated-sharpe-ratio — secondary) |
| MinTRL (minimum track record length) | Minimum observations for a Sharpe estimate to clear a confidence threshold | Bailey & López de Prado (2012), per https://ssrn.com/abstract=2326253 |

## 2. The gate stack (every strategy must pass ALL before it can earn leaderboard points)

| Gate | Requirement | Threshold policy | Basis |
|---|---|---|---|
| G0 Data integrity | Every input timestamped + sourced; no look-ahead; bet logged before kickoff & before move it claims to exploit | Hard fail on violation | Process rule (no external source needed) |
| G1 Minimum sample | ≥ 500 graded bets OR MinTRL satisfied at 95% confidence, whichever is stricter | 500 is a pragmatic floor — **UNVERIFIED as a formal standard (blank in data tables)**; MinTRL formula from Bailey & López de Prado (2012) | https://ssrn.com/abstract=2326253 |
| G2 Closing-line value | Mean CLV > 0 with two-sided t-test p < 0.05, computed at no-vig closing consensus | CLV is the process metric; practitioners treat a few hundred bets as the visibility floor | CLV framing: https://bodog.com/sports-betting/why-clv-matters (industry secondary — flagged); statistical test is standard |
| G3 Deflated Sharpe | DSR ≥ 0.95 given the true number of strategies tried (must be declared) | Multiplicity-corrected | https://ssrn.com/abstract=2460551 |
| G4 Backtest honesty | PBO ≤ 0.20 by CSCV on the full strategy-selection history | Prevents "best of many" illusions | https://ssrn.com/abstract=2326253 |
| G5 Walk-forward OOS | Parameters frozen on earlier seasons; final verdict only on later untouched seasons | Chronological splits only | Standard practice; methodology discipline per https://ssrn.com/abstract=2326253 |
| G6 Luck null (Monte Carlo) | Simulate ≥100,000 no-skill seasons: each bet graded at market-implied probability with same bet count and stake pattern. Strategy ROI must exceed the 95th percentile of the null distribution. Report **luck-adjusted ROI = ROI − E[null ROI]** | This is the "remove luck" mechanism | Construction: standard Monte Carlo; market-implied probabilities require de-vigged closing lines (power method) |
| G7 Bankroll safety | Fractional Kelly ≤ ¼ Kelly; max 2% bankroll per bet; max 25% weekly exposure | Proposal — tuned to competition stability | Kelly criterion (standard); sizing policy is a rules choice |
| G8 Stability | Same sign of edge across ≥2 seasons; parameter perturbation ±20% must not flip sign | Anti-overfit | Proposal, consistent with PBO logic |

## 3. Luck vs skill — labeling rules
- **Skill-based (provisional):** passes G0–G8, DSR ≥ 0.95, luck-adjusted ROI > 0.
- **Skill-based (confirmed):** provisional status maintained across two consecutive live seasons.
- **Lucky/unproven:** everything else. No shame — this is the default label until evidence arrives.
- **Disqualified:** G0 violation (look-ahead, unlogged bets), or declared-trials count found falsified.

## 4. Parlay-specific gates (single bets, parlays, prop combos all covered)
1. Every leg must independently pass G2 (positive CLV) before the combo can score.
2. Combo EV must be computed from an explicit **joint probability model** (correlation matrix —
   research/correlation.md), never from naive multiplication of independent prices.
3. Correlation estimates must come from ≥ 3 seasons of play-by-play with bootstrap confidence
   intervals; if the CI includes zero for a pair, that pair is treated as independent (blank value).
4. Max 4 legs per scoring entry (variance control); cross-game parlays favored over same-game
   parlays because the cross-game margin math is transparent (per industry analysis:
   https://bestnflfuturesbets.com/articles/nfl-same-game-parlays-futures-trap/ — industry secondary,
   flagged).
5. Same-game parlays must beat the book's own correlation adjustment, not just feel correlated —
   the "correlation tax" framing (https://www.oddsshopper.com/articles/betting-101/nfl-parlay-betting —
   industry secondary, flagged).

## 5. What "rewards for top performing strategies" requires (see leaderboard.md)
Rewards are distributed only to strategies that clear the gate stack at the reward snapshot date;
rank order uses luck-adjusted, shrinkage-corrected scores (Bayesian shrinkage toward the pool mean
proportional to sample size), so a 20-bet hot streak cannot out-rank a 500-bet verified edge.

## 6. Unverified / blank values (per no-inference rule)
| Item | Value | Status |
|---|---|---|
| Historical ROI of any specific angle in current market conditions | (blank) | UNVERIFIED — cited studies are in-sample & dated (2011–2024); none verified as currently profitable |
| Exact MinTRL numbers for our strategy classes | (blank) | UNVERIFIED until our return distribution (skew/kurt) is measured |
| Monte Carlo null percentiles for our leaderboard | (blank) | UNVERIFIED until the bet-volume and price structure of submissions are known |
| Suggested DSR/PBO thresholds proven optimal for NFL betting | (blank) | UNVERIFIED — DSR 0.95 / PBO 0.20 are the papers' conventions, not NFL-validated constants (flagged) |
