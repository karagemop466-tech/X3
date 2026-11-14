/*
 * NFL Decision Lab: source-first research content.
 * No player, team, odds, injury, lineup, correlation, or performance values are
 * embedded here. Strategy records are research hypotheses, not recommendations.
 */
(function (root) {
  "use strict";

  root.NFL_LAB = {
    asOf: "2026-11-14",
    projectStatus: "Research framework — no live data ingestion",
    sources: {
      nflPlayerStats: {
        label: "NFL player statistics",
        title: "NFL.com Player Stats",
        publisher: "National Football League",
        url: "https://www.nfl.com/stats/player-stats/",
        use: "Official player-stat category and season pages. The site is dynamic; the project has not copied any current values.",
        reviewed: "Opened 2026-11-14; source page and category navigation reviewed."
      },
      nflTeamStats: {
        label: "NFL team statistics",
        title: "NFL.com Team Stats — Offense / Passing (2026 page)",
        publisher: "National Football League",
        url: "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all",
        use: "Official team-stat page with offense, defense, and season/category navigation. No values were imported or analyzed.",
        reviewed: "Opened 2026-11-14; page structure reviewed; season-specific contents are dynamic."
      },
      nflInjuries: {
        label: "NFL injury reports",
        title: "NFL.com Official Injury Report",
        publisher: "National Football League",
        url: "https://www.nfl.com/injuries/",
        use: "Official weekly report pages expose player, position, injury text, practice status, and game status. Each snapshot must retain its retrieval time and selected season/week.",
        reviewed: "Opened 2026-11-14; current portal and report fields reviewed. No player values were copied."
      },
      nflSchedules: {
        label: "NFL schedule and game center",
        title: "NFL.com Schedules",
        publisher: "National Football League",
        url: "https://www.nfl.com/schedules/",
        use: "Official schedule and game-center entry point for event identity and timing. The project has not imported a schedule or result.",
        reviewed: "Opened 2026-11-14; page and navigation reviewed."
      },
      nflTeamDirectory: {
        label: "Official team directory",
        title: "NFL.com Official Sites of all 32 NFL Teams",
        publisher: "National Football League",
        url: "https://www.nfl.com/teams/",
        use: "NFL directory links to team profiles and official club websites. It is a starting point for checking team-published depth charts; it is not itself a verified league-wide depth-chart feed.",
        reviewed: "Opened 2026-11-14; team-directory page reviewed."
      },
      nflRosterExample: {
        label: "NFL roster page example",
        title: "NFL.com Team Roster (example page)",
        publisher: "National Football League",
        url: "https://www.nfl.com/teams/dallas-cowboys/roster",
        use: "Example of an official team roster view. Roster membership or roster status alone does not establish second-, third-, or fourth-string order.",
        reviewed: "Opened 2026-11-14; roster page structure reviewed. No player values were copied."
      },
      nflGamebook: {
        label: "NFL official gamebook (sample PDF)",
        title: "NFL Gamebook: Raiders at Patriots — 2025-09-07",
        publisher: "National Football League",
        url: "https://static.www.nfl.com/image/upload/v1757360321/gamecenter/f5919f8e-311e-11f0-b670-ae1250fadad1.pdf",
        use: "The reviewed official gamebook contains lineups, substitutions, players listed as did not play/not active, box-score statistics, and play-by-play. This is a historical example, not a live feed or a complete season archive.",
        reviewed: "Opened 2026-11-14; document sections reviewed. No game values were copied."
      },
      nflRosterRules: {
        label: "NFL roster / practice-squad rules",
        title: "NFL Football Operations — Contract Language",
        publisher: "NFL Football Operations",
        url: "https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language",
        use: "Official operations reference for roster and practice-squad terminology and transactions. Rules are season-dependent; this project does not hard-code roster limits.",
        reviewed: "Opened 2026-11-14; roster, practice-squad, and elevation sections reviewed."
      },
      nflRulebook: {
        label: "NFL rulebook",
        title: "NFL Football Operations — 2026 NFL Rulebook",
        publisher: "NFL Football Operations",
        url: "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
        use: "Official, season-versioned football rules. Market settlement and jurisdiction-specific contest law are outside the scope of this rulebook.",
        reviewed: "Opened 2026-11-14; current rulebook landing page reviewed."
      },
      nflNextGen: {
        label: "NFL Next Gen Stats information",
        title: "NFL Football Operations — Performance Tracking Data (Next Gen Stats)",
        publisher: "NFL Football Operations",
        url: "https://operations.nfl.com/game-operations-logistics/technology/performance-tracking-data-next-gen-stats",
        use: "Official description of player/ball tracking and examples of derived metrics. The page reviewed does not establish that raw tracking data is publicly downloadable or licensed for this project.",
        reviewed: "Opened 2026-11-14; tracking overview reviewed."
      },
      nflInjuryPermalinkCheck: {
        label: "NFL historical injury permalink checked",
        title: "NFL.com Injury Report — 2025 / reg1 URL checked for a page-label mismatch",
        publisher: "National Football League",
        url: "https://www.nfl.com/injuries/league/2025/reg1",
        use: "Review-only link for the mismatch documented on Flagged for Review. Do not ingest records from this URL until the season/week selection and page heading are independently confirmed.",
        reviewed: "Opened 2026-11-14; retrieved title and body heading did not agree."
      },
      nistGlossary: {
        label: "NIST statistics glossary",
        title: "NIST / ITL Engineering Statistics Handbook — Glossary",
        publisher: "National Institute of Standards and Technology (U.S. Department of Commerce)",
        url: "https://www.itl.nist.gov/div898/handbook/glossary.htm",
        use: "Statistical terminology reference, including correlation and cross-validation. It does not provide NFL data or a measured NFL correlation.",
        reviewed: "Opened 2026-11-14; glossary reviewed."
      },
      nistCrossValidation: {
        label: "NIST cross-validation definition",
        title: "NIST / ITL Engineering Statistics Handbook — Cross-validation glossary entry",
        publisher: "National Institute of Standards and Technology (U.S. Department of Commerce)",
        url: "https://www.itl.nist.gov/div898/handbook/glossary.htm#cross-validation",
        use: "Defines validation using observations not used to build the predictive model. Applied here as support for locked out-of-sample testing; NFL-specific thresholds remain a proposal.",
        reviewed: "Opened 2026-11-14; glossary and cross-validation entry reviewed."
      },
      nistCorrelation: {
        label: "NIST correlation definition",
        title: "NIST / ITL Engineering Statistics Handbook — Correlation glossary entry",
        publisher: "National Institute of Standards and Technology (U.S. Department of Commerce)",
        url: "https://www.itl.nist.gov/div898/handbook/glossary.htm#correlation",
        use: "Reference for correlation terminology. It does not supply NFL outcomes or any correlation estimates for this project.",
        reviewed: "Opened 2026-11-14; NIST glossary reviewed."
      },
      nistBootstrap: {
        label: "NIST bootstrap uncertainty reference",
        title: "NIST / ITL Engineering Statistics Handbook — Bootstrap Plot",
        publisher: "National Institute of Standards and Technology (U.S. Department of Commerce)",
        url: "https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm",
        use: "Explains bootstrap resampling as one way to estimate uncertainty and notes that bootstrap methods are not appropriate for every statistic or distribution.",
        reviewed: "Opened 2026-11-14; purpose, use, and cautions reviewed."
      },
      nistConfidence: {
        label: "NIST confidence-interval reference",
        title: "NIST / ITL Engineering Statistics Handbook — Confidence Limits",
        publisher: "National Institute of Standards and Technology (U.S. Department of Commerce)",
        url: "https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm",
        use: "Explains interval estimates and uncertainty. The project has no sample on which to calculate an NFL interval.",
        reviewed: "Opened 2026-11-14; confidence-interval discussion reviewed."
      },
      nistMultiple: {
        label: "NIST multiple-comparison reference",
        title: "NIST / ITL Engineering Statistics Handbook — Multiple Comparisons",
        publisher: "National Institute of Standards and Technology (U.S. Department of Commerce)",
        url: "https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm",
        use: "Warns that repeated pairwise testing can change the overall significance level and describes multiple-comparison procedures. Supports preregistration and family-wise strategy review; it is not a sport-specific threshold.",
        reviewed: "Opened 2026-11-14; multiple-comparison guidance reviewed."
      },
      nistResiduals: {
        label: "NIST model-diagnostic reference",
        title: "NIST / ITL Engineering Statistics Handbook — Model Validation and Residuals",
        publisher: "National Institute of Standards and Technology (U.S. Department of Commerce)",
        url: "https://www.itl.nist.gov/div898/handbook/pri/section6/pri619.htm",
        use: "Discusses checking residuals and time/run sequence for model structure. Applied as a proposed diagnostic, not as evidence of an NFL signal.",
        reviewed: "Located through the NIST handbook; page available for manual review."
      },
      sklearnMetrics: {
        label: "Official scikit-learn scoring documentation",
        title: "scikit-learn — Metrics and Scoring",
        publisher: "scikit-learn project documentation",
        url: "https://scikit-learn.org/stable/modules/model_evaluation.html",
        use: "Project documentation describes probabilistic prediction and scoring functions including Brier score and log loss. These are candidate evaluation metrics, not measured project results.",
        reviewed: "Opened 2026-11-14; scoring-function guidance and metric list reviewed."
      }
    },
    strategies: [
      {
        id: "H-01",
        name: "Team-strength baseline",
        market: "Game result, margin, and total",
        signal: "Build a simple, opponent-aware baseline from dated team/game outcomes and schedule context; publish distributions or probabilities rather than a single unsupported pick.",
        validation: "Freeze the feature cutoff before each game; compare with a simple historical/base-rate benchmark on later games only; report uncertainty and calibration.",
        status: "Hypothesis — not backtested",
        sources: ["nflSchedules", "nflTeamStats", "nflGamebook", "nistCrossValidation", "sklearnMetrics"]
      },
      {
        id: "H-02",
        name: "Confirmed-lineup availability adjustment",
        market: "Game line and team/player projections",
        signal: "Add a lineup feature only when the official report and a dated source confirm status and role. Separate out, questionable, active, and unconfirmed; do not infer a player's impact from a status label alone.",
        validation: "Compare the same base model with and without the feature on an as-of-time test; require confirmed replacement identity and usage evidence; report role uncertainty.",
        status: "Blocked — historical snapshots and role data absent",
        sources: ["nflInjuries", "nflRosterExample", "nflGamebook", "nflRosterRules"]
      },
      {
        id: "H-03",
        name: "Offense-versus-defense profile",
        market: "Game margin/total; team totals",
        signal: "Test offense and opposing-defense passing/rushing profiles jointly, with opponent and game context. Do not use a raw season rank as an injury or matchup conclusion.",
        validation: "Use pre-game-only team statistics, chronological holdouts, minimum-data rules, and residual diagnostics; declare which metric and direction before testing.",
        status: "Hypothesis — no values or thresholds selected",
        sources: ["nflTeamStats", "nflSchedules", "nflGamebook", "nistResiduals"]
      },
      {
        id: "H-04",
        name: "Player-prop opportunity model",
        market: "Pass/rush/receive yards, receptions, attempts, and touchdowns",
        signal: "Model the opportunity process (attempts, targets, carries or documented participation) separately from conversion/output; condition on role, opponent, and confirmed availability.",
        validation: "Forecast distributions on later games; compare against a pre-registered baseline; score both probability quality and numerical forecast error; check role changes and sample size.",
        status: "Blocked — no event-level historical dataset loaded",
        sources: ["nflPlayerStats", "nflGamebook", "nflInjuries", "sklearnMetrics", "nistConfidence"]
      },
      {
        id: "H-05",
        name: "Replacement-player / backup impact",
        market: "Game lines and affected player props",
        signal: "Estimate a replacement effect only when a primary player's absence and the replacement's actual role are officially documented; evaluate offense and defense separately, including position groups and multiple absences.",
        validation: "Require a dated official depth-chart/coach source or a gamebook-confirmed lineup, time-on-field evidence where licensed, and an opponent-adjusted comparison. Unknown string order stays blank.",
        status: "Blocked — no unified depth-chart source verified",
        sources: ["nflInjuries", "nflTeamDirectory", "nflRosterExample", "nflGamebook", "nflNextGen"]
      },
      {
        id: "H-06",
        name: "Single-leg probability/value screen",
        market: "Single spread, total, moneyline, or player prop",
        signal: "Generate an independent fair probability/distribution, then compare only with timestamped, licensed market prices after defining vig, settlement, and price timing.",
        validation: "No ROI or market edge can be calculated until market prices, timestamps, settlement rules, and source rights are present; use a holdout and uncertainty interval.",
        status: "Blocked — no market-price data or price definition",
        sources: ["nflSchedules", "nflPlayerStats", "nistConfidence", "sklearnMetrics"]
      },
      {
        id: "H-07",
        name: "Same-game player-prop combinations",
        market: "Player prop combos / same-game parlays",
        signal: "Estimate joint outcomes from shared game state, opportunity, and role; do not multiply marginal probabilities unless independence is tested and justified.",
        validation: "Use the exact market thresholds and settlement rules; evaluate joint calibration and paired outcomes out of sample; show sample size and interval for each combination family.",
        status: "Blocked — no paired outcomes or market rules loaded",
        sources: ["nflGamebook", "nflPlayerStats", "nistCorrelation", "nistBootstrap", "nflRulebook"]
      },
      {
        id: "H-08",
        name: "Parlay joint-probability model",
        market: "Two-or-more-leg parlays, separated by market family",
        signal: "Estimate the joint distribution for the selected legs and game context; quantify dependence and uncertainty, rather than treating each leg as independent by default.",
        validation: "Lock leg-selection rules before outcomes; compare joint forecasts with an independence benchmark; account for repeated testing and publish only held-out results.",
        status: "Blocked — no legs, prices, or joint history",
        sources: ["nflSchedules", "nflGamebook", "nistCorrelation", "nistMultiple", "nistBootstrap"]
      }
    ],
    correlations: [
      {
        id: "C-01",
        pair: "Quarterback passing-yard event ↔ receiver receiving-yard event (same game)",
        estimand: "Paired binary-event association and conditional joint probability at the exact selected thresholds",
        estimate: "",
        status: "Unverified — no paired event/line records",
        sources: ["nflPlayerStats", "nflGamebook", "nistCorrelation", "nistBootstrap"]
      },
      {
        id: "C-02",
        pair: "One player's receptions event ↔ receiving-yard event",
        estimand: "Paired event association, plus joint probability by role/availability context",
        estimate: "",
        status: "Unverified — no paired event/line records",
        sources: ["nflPlayerStats", "nflGamebook", "nistCorrelation", "nistBootstrap"]
      },
      {
        id: "C-03",
        pair: "Same-player rush attempts event ↔ rushing-yard event",
        estimand: "Paired event association with opportunity/role context kept explicit",
        estimate: "",
        status: "Unverified — no paired event/line records",
        sources: ["nflPlayerStats", "nflGamebook", "nistCorrelation", "nistBootstrap"]
      },
      {
        id: "C-04",
        pair: "Team scoring event ↔ quarterback or receiver prop event",
        estimand: "Conditional joint probability and residual association after pre-game context is locked",
        estimate: "",
        status: "Unverified — no paired event/line records",
        sources: ["nflTeamStats", "nflGamebook", "nistCorrelation", "nistBootstrap"]
      },
      {
        id: "C-05",
        pair: "Defensive pressure/sack event ↔ opposing passing-prop event",
        estimand: "Conditional joint probability by confirmed offensive/defensive lineup and game context",
        estimate: "",
        status: "Unverified — no paired event/line records",
        sources: ["nflTeamStats", "nflInjuries", "nflGamebook", "nistCorrelation"]
      }
    ],
    lineupFields: [
      {
        field: "Report snapshot / source timestamp",
        purpose: "Keep each injury or roster observation in the state known at the prediction cutoff; store source URL, retrieval time, season/week, and the original label.",
        state: "Not ingested",
        sources: ["nflInjuries", "nflSchedules"]
      },
      {
        field: "Reported player, team, position, practice status, game status",
        purpose: "Track only the fields shown by the official report; do not convert report labels into a medical diagnosis or a guaranteed participation claim.",
        state: "Source verified; no player rows copied",
        sources: ["nflInjuries"]
      },
      {
        field: "Official game availability / inactive status",
        purpose: "Confirm availability from an official game document at the relevant time; do not equate a roster entry with game participation.",
        state: "Historical sample only; archive ingestion absent",
        sources: ["nflGamebook", "nflRosterRules"]
      },
      {
        field: "Starting role or direct replacement",
        purpose: "Record a starter/replacement only from a dated official team source or gamebook lineup; preserve the evidence and timestamp.",
        state: "Not verified league-wide",
        sources: ["nflTeamDirectory", "nflRosterExample", "nflGamebook"]
      },
      {
        field: "Second-/third-/fourth-string rank",
        purpose: "Populate only when an official team depth chart or explicit team statement names the order. Never infer rank from roster order, injury status, or one game appearance.",
        state: "Blank — authoritative order not established",
        sources: ["nflTeamDirectory", "nflRosterExample"]
      },
      {
        field: "Participation / time on field",
        purpose: "Use official participation or tracking data only after data access, licensing, definition, and historical coverage are confirmed.",
        state: "Not ingested; public raw-data access not confirmed",
        sources: ["nflNextGen", "nflGamebook"]
      },
      {
        field: "Offensive and defensive position-group availability",
        purpose: "Track both sides independently and test clusters (for example, multiple linemen or defensive backs unavailable) without asserting a deficiency until model evidence supports one.",
        state: "No lineup data loaded",
        sources: ["nflInjuries", "nflRosterExample", "nflTeamStats", "nflGamebook"]
      }
    ],
    validationGates: [
      {
        gate: "1 — Provenance and as-of integrity",
        requirement: "Each input has an official source URL, season/game/player identity, retrieval timestamp, version, and allowed-use status. Reject unresolved identity or timestamp conflicts.",
        passRule: "Required provenance fields complete; conflicting sources are flagged, not silently reconciled.",
        state: "Not passed — no data ingestion",
        sources: ["nflSchedules", "nflInjuries", "nflPlayerStats", "nflGamebook"]
      },
      {
        gate: "2 — Preregistered hypothesis and market definition",
        requirement: "Freeze target, event definition, model version, feature cutoff, price/settlement definition, exclusions, and primary score before evaluation.",
        passRule: "A dated specification exists before a candidate sees holdout outcomes.",
        state: "Proposed — specification fields remain open",
        sources: ["nflSchedules", "nflRulebook", "nistMultiple"]
      },
      {
        gate: "3 — Chronological out-of-sample test",
        requirement: "Train only on information available earlier than the prediction; keep later games/seasons untouched; separately test prospective predictions.",
        passRule: "Reproducible time-ordered test with no future data leakage; report the evaluated event count and dates.",
        state: "Not passed — no dataset or predictions",
        sources: ["nistCrossValidation", "nflSchedules", "nflInjuries"]
      },
      {
        gate: "4 — Probability and forecast quality",
        requirement: "Use a proper score appropriate to the target (candidate: Brier/log loss for probabilities, an appropriate regression score for numeric outcomes) and show calibration separately.",
        passRule: "Beat a frozen baseline on the primary out-of-sample metric; report calibration and subgroup performance.",
        state: "Not passed — no forecasts",
        sources: ["sklearnMetrics", "nflPlayerStats", "nflTeamStats"]
      },
      {
        gate: "5 — Uncertainty and practical effect",
        requirement: "Show uncertainty intervals, event count, missingness, and effect size. Choose a minimum meaningful improvement and test power before viewing final results.",
        passRule: "The predeclared practical threshold and interval rule are met on an untouched sample; the exact threshold is not selected yet.",
        state: "Proposed — sample size and threshold not set",
        sources: ["nistConfidence", "nistBootstrap"]
      },
      {
        gate: "6 — Multiple-strategy / selection-bias control",
        requirement: "Maintain a strategy registry, preserve failed experiments, and account for the number of hypotheses/variants tested.",
        passRule: "The candidate survives the preregistered family-level comparison or an independent holdout; never rank only the best retrospective variant.",
        state: "Not passed — no strategy registry results",
        sources: ["nistMultiple", "nistCrossValidation"]
      },
      {
        gate: "7 — Market economics and settlement",
        requirement: "For betting-value claims, use licensed, time-stamped prices; define vig/fees, pushes/voids, market limits, and the exact settlement rules.",
        passRule: "Net performance is positive under the chosen predeclared rule on a later holdout, with uncertainty shown. NFL game-stat pages do not provide the missing price/settlement data.",
        state: "Blocked — market feed and terms absent",
        sources: ["nflSchedules", "nflPlayerStats", "nistConfidence"]
      },
      {
        gate: "8 — Operations, fairness, and rewards",
        requirement: "Test automated refreshes, source outages, version history, tie rules, anti-manipulation, eligibility, and any jurisdiction-specific prize requirements before a reward is offered.",
        passRule: "A documented operating and competition policy is approved; no reward is promised by this prototype.",
        state: "Blocked — policy and jurisdiction not defined",
        sources: ["nflTeamDirectory", "nistMultiple", "nflRulebook"]
      }
    ],
    leaderboardCategories: [
      {
        category: "Single bets",
        ranking: "Primary: preregistered out-of-sample probability score and calibration; secondary market return/closing comparison only if prices and settlement are licensed and timestamped.",
        reward: "No qualified strategies or reward amounts. Reward policy is not approved.",
        sources: ["sklearnMetrics", "nistConfidence", "nflSchedules"]
      },
      {
        category: "Player props",
        ranking: "Rank separately by prop family and target; include probability/forecast score, calibration, sample size, and uncertainty.",
        reward: "No qualified strategies or reward amounts. Role and market data are not loaded.",
        sources: ["nflPlayerStats", "nflGamebook", "sklearnMetrics", "nistConfidence"]
      },
      {
        category: "Same-game combos / parlays",
        ranking: "Rank on a joint-outcome score and held-out net result only after leg definitions, dependence, prices, and settlement rules are captured.",
        reward: "No qualified strategies or reward amounts. Correlation values remain blank.",
        sources: ["nflGamebook", "nistCorrelation", "nistBootstrap", "nistMultiple"]
      },
      {
        category: "Cross-game parlays",
        ranking: "Keep separate from same-game combinations; evaluate joint probability and portfolio-level risk rather than assuming independence.",
        reward: "No qualified strategies or reward amounts. No parlay history is present.",
        sources: ["nflSchedules", "nistCorrelation", "nistConfidence", "nistMultiple"]
      }
    ],
    questions: [
      {
        id: "Q-01",
        question: "Which seasons and game types are in scope (regular season, preseason, postseason, or all)?",
        known: "The official schedule and stats portals expose season-oriented pages; no project season window has been selected.",
        answer: "Open — do not mix seasons or game types until this is defined.",
        decision: "Choose the first training window, holdout window, and any excluded game types.",
        sources: ["nflSchedules", "nflPlayerStats", "nflTeamStats"]
      },
      {
        id: "Q-02",
        question: "Which markets count as an NFL line (moneyline, spread, total, team total, player prop, or combo), and how are pushes/voids settled?",
        known: "NFL sources establish football rules and game results, not a specific book's market wording or settlement terms.",
        answer: "Open — market names, thresholds, and settlement are not provided.",
        decision: "Define market schema and record the operator's exact rules for each market family.",
        sources: ["nflRulebook", "nflSchedules"]
      },
      {
        id: "Q-03",
        question: "What licensed source will provide historical and current prices, including open/close time, price format, and market limits?",
        known: "The official NFL stats, injury, and schedule pages reviewed here do not provide a verified odds-history feed.",
        answer: "Open — no market-price provider or license is verified.",
        decision: "Identify a permitted odds source and preserve immutable price snapshots before comparing model lines.",
        sources: ["nflSchedules", "nflPlayerStats", "nflInjuries"]
      },
      {
        id: "Q-04",
        question: "What is the approved historical data range and are reuse, storage, and redistribution permitted?",
        known: "Official statistics, reports, and gamebooks are accessible on official pages; rights, bulk access, and an ingestion interface were not confirmed in this review.",
        answer: "Open — no dataset, API terms, or reuse permissions are recorded in the repository.",
        decision: "Document source terms, retention, attribution, and refresh limits before automated collection.",
        sources: ["nflPlayerStats", "nflGamebook", "nflNextGen"]
      },
      {
        id: "Q-05",
        question: "How should a second-, third-, or fourth-string player be identified when a starter is unavailable?",
        known: "NFL roster pages identify roster information; gamebooks can show actual lineups and inactive players. Neither alone establishes a league-wide ordinal depth order.",
        answer: "Open — depth rank stays blank unless a dated official team chart or explicit team statement confirms it.",
        decision: "Set an acceptable source hierarchy per club and a stale-source cutoff; do not infer from roster order.",
        sources: ["nflTeamDirectory", "nflRosterExample", "nflGamebook", "nflInjuries"]
      },
      {
        id: "Q-06",
        question: "What qualifies as a defensive or offensive deficiency (which metric, opponent adjustment, and threshold)?",
        known: "The NFL publishes team/player statistics and gamebooks; no metric or deficiency cutoff has been chosen.",
        answer: "Open — no defense ranking or deficiency is asserted.",
        decision: "Choose the target metric and validation rule before reviewing which teams appear weak.",
        sources: ["nflTeamStats", "nflPlayerStats", "nflGamebook", "nistMultiple"]
      },
      {
        id: "Q-07",
        question: "Which correlation is decision-relevant: raw player outcomes, forecast residuals, or exact bet-leg wins/losses?",
        known: "Parlay pricing depends on joint event probabilities; no leg outcomes, threshold definitions, or paired observations are in the repository.",
        answer: "Open — all numerical estimates are intentionally blank.",
        decision: "Predefine each leg event, shared-game context, observation unit, coefficient/joint probability, and uncertainty method.",
        sources: ["nistCorrelation", "nflGamebook", "nflPlayerStats", "nistBootstrap"]
      },
      {
        id: "Q-08",
        question: "What will qualify a strategy as skillful rather than a lucky in-sample winner?",
        known: "NIST documents held-out validation, uncertainty, residual checks, and multiple-comparison cautions; no NFL candidate has been tested.",
        answer: "Open — proposed gates are listed; thresholds and a data-backed power plan are unset.",
        decision: "Pre-register a meaningful lift over baseline, chronological holdout, calibration, uncertainty, and multiple-testing rule.",
        sources: ["nistCrossValidation", "nistConfidence", "nistMultiple", "sklearnMetrics"]
      },
      {
        id: "Q-09",
        question: "How are leaderboard categories, ties, minimum sample size, and rewards defined?",
        known: "There is no entrant history, scoring policy, prize pool, tie rule, or approved competition policy in the repo.",
        answer: "Open — the leaderboard is empty and no reward is promised.",
        decision: "Specify separate scoring for singles, props, and parlays; set a power-based sample floor and rules before enrollment.",
        sources: ["nistMultiple", "nistConfidence", "sklearnMetrics"]
      },
      {
        id: "Q-10",
        question: "Are rewards non-cash, cash, or recognition only, and which jurisdiction governs participation?",
        known: "Neither the NFL rulebook nor statistical references resolve local competition or prize requirements; target jurisdiction is unspecified.",
        answer: "Open — no legal conclusion or payout amount is provided.",
        decision: "Keep the contest simulated until the target jurisdiction and official regulatory sources are identified and reviewed.",
        sources: ["nflRulebook", "nistMultiple"]
      },
      {
        id: "Q-11",
        question: "Will this system remain research/paper-only, or include any real-money execution?",
        known: "This repository contains no betting execution, account connection, payment system, or bankroll settings.",
        answer: "Default for this prototype: research-only; no bets are placed.",
        decision: "Keep execution explicitly out of scope unless separately specified, authorized, and reviewed.",
        sources: ["nflRulebook", "nflSchedules"]
      },
      {
        id: "Q-12",
        question: "What injury/lineup freshness cutoff and source-conflict precedence should apply?",
        known: "The NFL publishes weekly reports and the source pages are dynamic; an observed historical permalink mismatch is listed for review.",
        answer: "Open — no automated freshness or conflict policy exists.",
        decision: "Set update cadence, prediction cutoff, authoritative-source order, and a rule to suppress stale/conflicting rows.",
        sources: ["nflInjuries", "nflInjuryPermalinkCheck", "nflSchedules"]
      },
      {
        id: "Q-13",
        question: "May NFL Next Gen tracking or time-on-field data be used, and under what access/license terms?",
        known: "NFL Football Operations describes tracking and derived metrics; public bulk-data availability and project rights were not confirmed.",
        answer: "Open — do not assume the data are downloadable or licensed.",
        decision: "Confirm documented access, terms, coverage, stable identifiers, and historical backfill before relying on tracking features.",
        sources: ["nflNextGen", "nflPlayerStats"]
      },
      {
        id: "Q-14",
        question: "What timezone, odds timestamp, and late-injury cutoff will every prediction use?",
        known: "NFL schedules and injury reports publish event/report context; the project has not selected a canonical timezone or prediction lock.",
        answer: "Open — timestamps must be normalized and retain their original source timezone.",
        decision: "Choose a canonical storage timezone and freeze a per-market decision time before outcomes are known.",
        sources: ["nflSchedules", "nflInjuries"]
      }
    ],
    suggestions: [
      {
        id: "S-01",
        title: "Build the source and rights foundation first",
        priority: "Recommended first",
        suggestion: "Create versioned, timestamped adapters for official schedules, gamebooks/statistics, injury reports, roster status, and a separately licensed price feed. Keep raw source snapshots and attribution.",
        decisionImpact: "Prevents lookahead, supports reproducibility, and makes missing/conflicting records visible before a line is produced.",
        tradeoff: "Public pages are dynamic; bulk access, stable identifiers, retention, and use terms need confirmation. No automatic feed is configured here.",
        sources: ["nflSchedules", "nflPlayerStats", "nflInjuries", "nflGamebook", "nflNextGen"]
      },
      {
        id: "S-02",
        title: "Define a small, frozen baseline before adding complex signals",
        priority: "Next after data audit",
        suggestion: "Start with a transparent game-level probability/margin baseline and one target at a time. Freeze the definition and compare only on chronological held-out games.",
        decisionImpact: "Makes it possible to tell whether injury, matchup, or player features add information beyond a simple reference.",
        tradeoff: "A baseline is not itself a bet recommendation; no predictive edge can be claimed until a complete historical dataset and holdout exist.",
        sources: ["nflTeamStats", "nflSchedules", "nistCrossValidation", "sklearnMetrics"]
      },
      {
        id: "S-03",
        title: "Make injury and backup evidence point-in-time and explicit",
        priority: "Before injury-adjusted models",
        suggestion: "Store each injury report version, confirmed availability, official replacement evidence, side/position group, and actual participation where licensed. Keep string-rank blank unless officially documented.",
        decisionImpact: "Separates a reported issue from actual availability and avoids inventing impact for second-/third-/fourth-string players.",
        tradeoff: "Team sources may differ in timing and format; define source precedence and stale-data handling.",
        sources: ["nflInjuries", "nflTeamDirectory", "nflGamebook", "nflRosterRules", "nflNextGen"]
      },
      {
        id: "S-04",
        title: "Treat parlays as joint-probability models, not multiplied picks",
        priority: "After single-leg validation",
        suggestion: "Estimate exact leg co-occurrence and conditional dependence by market/context; report sample size and uncertainty. Keep player-combo and cross-game parlays in separate leaderboards.",
        decisionImpact: "Makes correlation a first-class value and avoids overstating combined probability when legs share a player, team, or game state.",
        tradeoff: "Sparse combinations have wide uncertainty; small samples should remain unranked rather than receive a guessed correlation.",
        sources: ["nistCorrelation", "nistBootstrap", "nistMultiple", "nflGamebook"]
      },
      {
        id: "S-05",
        title: "Use a skill-focused, uncertainty-aware competition score",
        priority: "Before leaderboard launch",
        suggestion: "Use pre-registered out-of-sample probability/forecast scores as the core; display calibration, event count, uncertainty, market return after fees, and a locked benchmark as separate columns.",
        decisionImpact: "Reduces incentives to chase short-run wins or select the luckiest backtest; supports apples-to-apples review by bet type.",
        tradeoff: "The ranking, sample floor, tie rules, and any reward still need predefinition; statistical significance alone is not economic value.",
        sources: ["sklearnMetrics", "nistConfidence", "nistMultiple"]
      },
      {
        id: "S-06",
        title: "Keep price comparison separate from NFL performance data",
        priority: "Before any value/ROI claim",
        suggestion: "Maintain independent model lines and time-stamped market snapshots in separate fields; identify the licensed market source and settlement rules before calculating edge or return.",
        decisionImpact: "Makes it clear whether a result is a football prediction or a claim about price/value.",
        tradeoff: "No odds provider, permission, or market history is verified in the sources reviewed.",
        sources: ["nflSchedules", "nflPlayerStats", "nistConfidence"]
      },
      {
        id: "S-07",
        title: "Delay cash or prize rewards until policy review",
        priority: "Required before rewards",
        suggestion: "Keep the leaderboard simulated until eligibility, jurisdiction, reward type, anti-manipulation, ties, appeals, and funding rules are defined and checked against official sources for the chosen region.",
        decisionImpact: "Avoids promising an unsupported reward and makes the contest fair and auditable.",
        tradeoff: "No jurisdiction, prize format, or competition rules were specified; no legal conclusion is made here.",
        sources: ["nflRulebook", "nistMultiple"]
      }
    ],
    flagged: [
      {
        id: "F-01",
        issue: "No NFL dataset is present in the repository",
        detail: "The starting repository contained only a README. No schedule/results archive, player/team statistics, injury snapshots, lineups, odds, strategy predictions, or performance history was present. Accordingly, no model line, measured edge, correlation, ranking, or reward result is published.",
        impact: "All numerical outputs remain blank; this is a research framework, not a functioning data feed.",
        sources: ["nflSchedules", "nflPlayerStats", "nflTeamStats", "nflInjuries", "nflGamebook"]
      },
      {
        id: "F-02",
        issue: "No licensed historical/live price source is verified",
        detail: "NFL game, stat, and injury sources reviewed do not establish a time-stamped odds feed or bookmaker settlement rules. This is a bounded source-review finding, not a claim that no such third-party service exists.",
        impact: "No market edge, vig-adjusted return, closing-line comparison, or parlay payout can be verified.",
        sources: ["nflSchedules", "nflPlayerStats", "nflRulebook"]
      },
      {
        id: "F-03",
        issue: "Ordinal depth-chart evidence is not established league-wide",
        detail: "Official NFL roster pages and gamebooks are useful for roster/lineup evidence, but the reviewed sources do not establish one reliable league-wide second-/third-/fourth-string feed. Do not infer the order from a roster list or injury report.",
        impact: "Backup rank and replacement-impact fields stay blank until an official, dated team source supports them.",
        sources: ["nflTeamDirectory", "nflRosterExample", "nflGamebook", "nflInjuries"]
      },
      {
        id: "F-04",
        issue: "Next Gen Stats data rights and raw-feed access are unconfirmed",
        detail: "NFL Football Operations describes player/ball tracking and derived metrics, but the page reviewed does not document public raw-data download access or permission for this project's intended storage/use.",
        impact: "Do not assume time-on-field/tracking features can be ingested until terms, coverage, and identifiers are confirmed.",
        sources: ["nflNextGen"]
      },
      {
        id: "F-05",
        issue: "Historical injury-report URL returned conflicting week labels",
        detail: "On 2026-11-14, the official URL ending /2025/reg1 returned a page title identifying Week 10 of the 2025 season while the body section began 'Injuries - WEEK 1'. This retrieval mismatch must be checked in the official page before any historical report is ingested.",
        impact: "No records from the disputed URL were copied; select season/week by verified page content and preserve the retrieval snapshot.",
        sources: ["nflInjuryPermalinkCheck", "nflInjuries"]
      },
      {
        id: "F-06",
        issue: "No correlation can be calculated without paired market-event records",
        detail: "A numeric correlation needs exact leg definitions, paired event outcomes, timestamps, and enough comparable observations. None are in this repository. The five candidate correlation cells are intentionally empty.",
        impact: "No parlay leg may be treated as independent or assigned a correlation number.",
        sources: ["nistCorrelation", "nistBootstrap", "nflGamebook", "nflPlayerStats"]
      },
      {
        id: "F-07",
        issue: "Prize rules and jurisdiction are unresolved",
        detail: "The jurisdiction, prize format, eligibility, scoring/tie rules, and anti-manipulation policy are unspecified. The linked NFL football rulebook is not a local contest-law source; no legal conclusion or payout amount is made.",
        impact: "Keep any leaderboard simulated and non-rewarding until the relevant official regulatory sources and written contest rules are identified.",
        sources: ["nflRulebook", "nistMultiple"]
      },
      {
        id: "F-08",
        issue: "Sports outcomes cannot be made deterministic by a model",
        detail: "A model can test for repeatable predictive skill and quantify uncertainty; it cannot guarantee the removal of random variation. Short-run wins alone do not establish skill.",
        impact: "Require prospective/held-out scoring, calibration, uncertainty intervals, and controls for repeated strategy trials.",
        sources: ["sklearnMetrics", "nistConfidence", "nistMultiple", "nistCrossValidation"]
      }
    ]
  };
})(typeof window === "undefined" ? globalThis : window);
