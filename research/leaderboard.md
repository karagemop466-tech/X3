# Leaderboard Competition — design notes (T6)

**Session:** arena-4856379c · **Date:** 2026-11-14 · Precedent/prize facts verified on Kaggle (official competition host).

## 1. Verified precedent: NFL Big Data Bowl (official NFL × Kaggle competition)

| Fact | Source (official host) |
|---|---|
| NFL Big Data Bowl is a skills-based competition; submissions scored/ranked by stated metric; public leaderboard visible during the competition | https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/rules |
| BDB 2021 judging rubric: Innovation ("actionable? novel? creative?") + Accuracy ("correct? claims backed by data? models appropriate?"); judged by NFL/team analytics staff | https://www.kaggle.com/c/nfl-big-data-bowl-2021 |
| BDB 2021 prizes: 5 × $15,000 (open), plus a $10,000 live-presentation prize; college category existed | https://www.kaggle.com/c/nfl-big-data-bowl-2021 |
| BDB 2022 prizes: college 3 × $5,000 + $10,000 presentation prize; open-source winner license required | https://www.kaggle.com/c/nfl-big-data-bowl-2022/rules |
| Team prize money split evenly unless the team unanimously agrees otherwise | https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/rules |

## 2. Competition design — "X3 NFL Strategy Leaderboard" (proposal)

### 2.1 Entry format (a strategy is a spec, not a bet slip)
- **ID + name + class:** single bet / parlay (≤4 legs) / player-prop combo.
- **Rules block:** exact market(s), selection rule, timing rule (when the bet fires relative to the
  week), stake rule, exit/void handling. Must be mechanically executable — no "discretion".
- **Declared trials:** how many strategy variants were tried before submission (feeds DSR; falsifying
  this disqualifies — Gate G0/G3).
- **Data manifest:** every input feed + version.

### 2.2 Scoring (composite; every component already defined in validation.md)
| Component | Weight (proposal) | Why |
|---|---|---|
| Luck-adjusted ROI (Monte Carlo null-corrected) | 40% | Removes luck directly |
| Mean CLV (no-vig closing consensus) | 30% | Skill visible early; hard to fake |
| DSR (multiplicity-corrected Sharpe probability) | 20% | Punishes data mining |
| Stability (season-over-season sign consistency) | 10% | Anti-overfit |
Rank = Bayesian-shrunken composite (shrinkage ∝ 1/sample size). Small samples hover at the pool mean.

### 2.3 Seasons & cadence (proposal)
- Two-week rolling evaluation windows within an NFL season; season leaderboard + all-time leaderboard.
- Bets graded at closing consensus prices (theoretical scoring) + optional verified sportsbook P&L.
- Reward snapshot: end of regular season; rewards paid only to strategies that pass gates G0–G8
  **at snapshot time**.

### 2.4 Rewards (proposal — amounts blank until a budget is set; see questions page Q-01)
| Award | Basis | Amount |
|---|---|---|
| Season champion | Top shrunken composite | (blank — UNVERIFIED until budget) |
| 2nd / 3rd | Top shrunken composite | (blank) |
| Best single-bet class / Best parlay class / Best prop-combo class | Class leaders | (blank) |
| Innovation prize | BDB-style rubric: novelty + actionability + accuracy | (blank) |
| Gates-clearing bonus | Paid per strategy clearing G0–G8 even if unranked | (blank) |
Precedent scale: BDB paid $15k × 5 (2021) — https://www.kaggle.com/c/nfl-big-data-bowl-2021 (use as
the anchor when the budget question is answered).

### 2.5 Anti-gaming & fairness rules
1. Timestamped, immutable submissions before the first kickoff the strategy touches.
2. No editing after kickoff; versioned amendments create new entries (and new trials count).
3. Max 25 live entries per participant per week; round-robin spam across correlated tickets does not
   create independent samples (bets across entries sharing a game are grouped for DSR/PBO).
4. Public rules, public metric, public leaderboard during play (BDB model).
5. Post-season audit: re-verification of every logged price against archived consensus; any
   unreconcilable bet voided for scoring.
6. Disqualification triggers: look-ahead, falsified trials count, price sourcing violations (G0).

### 2.6 "Remove luck" in the ranking — worked example of the mechanism
A 20-bet entry at 60% win rate sounds elite — but at −110 prices a no-skill coin has a wide ROI
distribution over 20 bets. The Monte Carlo null (validation.md G6) shows the 95th percentile of
luck; the entry only ranks if it clears it, and shrinkage pulls its displayed score toward the pool
mean until its sample supports the claim. DSR further deflates entries selected from many tries.

## 3. Implementation status
| Component | Status |
|---|---|
| Rules + scoring spec | Drafted (this document) — open for review on Suggestions page |
| Bet/price logging + consensus archive | Not built — data gap Q-07 (Questions page) |
| Monte Carlo + DSR/PBO engine | Not built — requires logged entries first |
| Prize funding | Not set — Q-01 (Questions page) |
