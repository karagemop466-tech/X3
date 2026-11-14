(function () {
  "use strict";

  const data = window.NFL_LAB;
  const view = document.body.dataset.view || "home";
  const insidePages = /\/pages\//.test(window.location.pathname);
  const base = insidePages ? "../" : "./";
  const navItems = [
    ["home", "Overview"],
    ["executive-summary", "Executive summary"],
    ["strategies", "Strategy lab"],
    ["validation", "Validation gates"],
    ["lineups", "Injuries & lineups"],
    ["correlations", "Correlation lab"],
    ["leaderboard", "Leaderboard"],
    ["questions", "Open questions"],
    ["suggestions", "Suggestions"],
    ["flagged", "Flagged for review"],
    ["sources", "Sources"]
  ];
  const pageMeta = {
    home: {
      title: "NFL Decision Lab",
      subtitle: "An evidence-first workspace for originating, testing, and reviewing NFL lines.",
      eyebrow: "Decision dashboard"
    },
    "executive-summary": {
      title: "Executive summary",
      subtitle: "What the official-source review supports today—and what remains unmeasured.",
      eyebrow: "Briefing"
    },
    strategies: {
      title: "Strategy lab",
      subtitle: "Research hypotheses for game lines, single bets, player props, combos, and parlays.",
      eyebrow: "Research design"
    },
    validation: {
      title: "Validation gates",
      subtitle: "A proposed evidence ladder designed to separate repeatable signal from noise.",
      eyebrow: "Quality controls"
    },
    lineups: {
      title: "Injuries & lineups",
      subtitle: "A source-first plan for tracking availability, replacements, and defensive/offensive depth.",
      eyebrow: "Availability intelligence"
    },
    correlations: {
      title: "Correlation lab",
      subtitle: "Define the joint events that matter before estimating any number.",
      eyebrow: "Dependence & combos"
    },
    leaderboard: {
      title: "Leaderboard",
      subtitle: "Separate candidate scorecards by market; no unverified strategy is ranked.",
      eyebrow: "Competition"
    },
    questions: {
      title: "Open questions",
      subtitle: "The questions, current answers, and missing information required for a defensible decision.",
      eyebrow: "Decision checklist"
    },
    suggestions: {
      title: "Suggestions",
      subtitle: "Review trade-offs and choose a planning path before any product or model change is implemented.",
      eyebrow: "Review board"
    },
    flagged: {
      title: "Flagged for review",
      subtitle: "Unverified inputs and source irregularities are visible here instead of being filled in by inference.",
      eyebrow: "Exceptions"
    },
    sources: {
      title: "Source register",
      subtitle: "Official NFL and statistical-method references checked for this research framework.",
      eyebrow: "Evidence index"
    }
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char];
    });
  }

  function hrefFor(slug) {
    return slug === "home" ? base + "index.html" : base + "pages/" + slug + ".html";
  }

  function sourceLinks(ids) {
    if (!Array.isArray(ids) || ids.length === 0) {
      return '<span class="source-missing">Source not recorded</span>';
    }
    return ids.map(function (id) {
      const source = data.sources[id];
      if (!source) return '<span class="source-missing">Unknown source</span>';
      return '<a class="source-link" href="' + escapeHtml(source.url) + '" target="_blank" rel="noopener noreferrer" title="' + escapeHtml(source.title) + '">' + escapeHtml(source.label) + '</a>';
    }).join('<span class="source-separator"> · </span>');
  }

  function renderTable(headers, rows, caption, options) {
    const opts = options || {};
    const tableId = "table-" + Math.random().toString(36).slice(2, 9);
    const search = opts.search ? '<label class="table-search">Filter rows <input type="search" data-filter-target="' + tableId + '" placeholder="Type to filter" autocomplete="off"></label>' : "";
    const searchStatus = opts.search ? '<p class="filter-status" data-filter-status="' + tableId + '" aria-live="polite"></p>' : "";
    const body = rows.map(function (row) {
      const cells = row.cells.map(function (cell, index) {
        const value = cell == null ? "" : String(cell);
        const isBlank = value === "";
        const cellContent = isBlank ? "" : escapeHtml(value);
        if (index === 0) {
          return '<th scope="row">' + cellContent + '</th>';
        }
        return '<td' + (isBlank ? ' class="blank-value" aria-label="Unverified; intentionally blank"' : "") + '>' + cellContent + '</td>';
      }).join("");
      const searchable = row.cells.join(" ").toLowerCase();
      return '<tr data-search-row="' + escapeHtml(searchable) + '">' + cells + '<td class="source-cell">' + sourceLinks(row.sources) + '</td></tr>';
    }).join("");
    const empty = rows.length ? "" : '<div class="empty-state"><span class="empty-icon" aria-hidden="true">—</span><p>' + escapeHtml(opts.emptyMessage || "No verified records are available yet.") + '</p></div>';
    const table = rows.length ? '<div class="table-scroll"><table id="' + tableId + '"><caption class="visually-hidden">' + escapeHtml(caption) + '</caption><thead><tr>' + headers.map(function (header, index) {
      return '<th scope="col"' + (index === headers.length - 1 ? ' class="source-heading"' : "") + '>' + escapeHtml(header) + '</th>';
    }).join("") + '<th scope="col" class="source-heading">Official source(s)</th></tr></thead><tbody>' + body + '</tbody></table></div>' : "";
    return '<div class="table-tools">' + search + searchStatus + '</div>' + table + empty;
  }

  function statusPill(text, tone) {
    return '<span class="status-pill ' + escapeHtml(tone || "neutral") + '">' + escapeHtml(text) + '</span>';
  }

  function section(title, content, note) {
    return '<section class="content-section"><div class="section-heading"><h2>' + escapeHtml(title) + '</h2>' + (note ? '<p>' + escapeHtml(note) + '</p>' : "") + '</div>' + content + '</section>';
  }

  function pageHeader(meta) {
    return '<div class="page-heading"><div class="eyebrow">' + escapeHtml(meta.eyebrow) + '</div><h1>' + escapeHtml(meta.title) + '</h1><p>' + escapeHtml(meta.subtitle) + '</p></div>';
  }

  function sourceList(ids) {
    return '<div class="source-list">' + sourceLinks(ids) + '</div>';
  }

  function statusCard(label, value, detail, tone) {
    return '<article class="status-card ' + escapeHtml(tone || "") + '"><div class="status-card-top"><span>' + escapeHtml(label) + '</span>' + statusPill(tone === "warning" ? "Open" : "Not measured", tone || "neutral") + '</div><strong>' + escapeHtml(value) + '</strong><p>' + escapeHtml(detail) + '</p></article>';
  }

  function renderHome() {
    const proposed = data.strategies.length;
    const summaryCards = '<div class="status-grid">' +
      statusCard("Live NFL data", "Not configured", "No player, team, injury, lineup, or odds values are loaded.", "warning") +
      statusCard("Model-generated lines", "Not issued", "A fair line requires a dated dataset, a locked model, and out-of-sample validation.", "neutral") +
      statusCard("Correlations", "Not measured", "Every numerical estimate is intentionally blank until paired market outcomes exist.", "warning") +
      statusCard("Strategy research", proposed + " hypotheses", "Ideas only; none has a measured performance result or leaderboard rank.", "neutral") +
      '</div>';
    const hero = '<section class="hero-panel"><div class="hero-copy"><div class="hero-kicker">NFL • EVIDENCE FIRST</div><h2>Build a line you can explain.<br><span>Validate before you reward it.</span></h2><p>This repository began as an empty scaffold. The site now provides an official-source research map, a proposed strategy and validation framework, and a visible list of missing evidence. It does not publish picks, prices, or performance claims.</p><div class="hero-actions"><a class="button button-primary" href="' + hrefFor("executive-summary") + '">Read the executive summary</a><a class="button button-secondary" href="' + hrefFor("suggestions") + '">Review suggestions</a></div></div><div class="hero-mark" aria-hidden="true"><span>NL</span><small>RESEARCH<br>NOT A LIVE FEED</small></div></section>';
    const cards = [
      ["Strategy lab", "Proposed signals across game lines, single bets, player props, combos, and parlays.", "strategies", "01"],
      ["Injuries & lineups", "Track what is officially reported; keep replacement rank blank until sourced.", "lineups", "02"],
      ["Validation gates", "Freeze hypotheses, test later games, quantify uncertainty, and control repeated trials.", "validation", "03"],
      ["Correlation lab", "Define paired bet events and report uncertainty before any parlay is ranked.", "correlations", "04"],
      ["Open questions", "See what is known, what is missing, and which decisions remain open.", "questions", "05"],
      ["Flagged for review", "Review source/feed gaps and the specific injury-page label mismatch.", "flagged", "06"]
    ];
    const cardHtml = '<div class="card-grid">' + cards.map(function (card) {
      return '<a class="feature-card" href="' + hrefFor(card[2]) + '"><span class="feature-index">' + card[3] + '</span><h3>' + escapeHtml(card[0]) + '</h3><p>' + escapeHtml(card[1]) + '</p><span class="feature-arrow" aria-hidden="true">↗</span></a>';
    }).join("") + '</div>';
    const sequence = '<div class="sequence-grid"><article><span>01</span><h3>Source & rights</h3><p>Secure permitted, versioned game, injury, roster, and market inputs.</p></article><article><span>02</span><h3>Baseline</h3><p>Lock a simple prediction target and timestamp before adding complex features.</p></article><article><span>03</span><h3>Prove signal</h3><p>Use later, untouched outcomes; report calibration, uncertainty, and every tested variant.</p></article><article><span>04</span><h3>Compete fairly</h3><p>Rank separate market families only after validation and policy review.</p></article></div>';
    const alert = '<aside class="callout callout-amber"><div class="callout-icon" aria-hidden="true">!</div><div><strong>Decision status: research only</strong><p>Current official pages are useful evidence sources, but historical price snapshots, an approved odds feed, complete lineup history, and a verified depth-chart source are not available in this repository. No numerical NFL values have been guessed.</p><a href="' + hrefFor("flagged") + '">See all flagged items →</a></div></aside>';
    return pageHeader(pageMeta.home) + hero + summaryCards + section("Research workflow", sequence, "A proposed order of work; no model or reward rule is active.") + section("Explore the workspace", cardHtml) + alert;
  }

  function renderExecutiveSummary() {
    const intro = '<div class="summary-banner"><div><span class="eyebrow">Bottom line</span><h2>The framework is ready; the evidence is not.</h2><p>Official NFL sources for schedules, statistics, weekly injury reports, team rosters, gamebooks, and tracking-data descriptions were reviewed. The repository contains no NFL observations or odds history, so an independent line, numeric correlation, model win rate, or leaderboard winner cannot honestly be produced yet.</p></div>' + statusPill("No picks or rankings published", "warning") + '</div>';
    const knownRows = [
      { cells: ["Player and team statistics", "NFL.com publishes player- and team-stat pages with season/category navigation. No figures were transcribed into this project."], sources: ["nflPlayerStats", "nflTeamStats"] },
      { cells: ["Weekly injury reporting", "The official report page shows player, position, injury text, practice participation, and game status. It is a snapshot source, not a confirmed future role."], sources: ["nflInjuries"] },
      { cells: ["Schedule and game context", "NFL.com provides schedule and game-center pages for event identity and timing. No schedule/results table has been ingested."], sources: ["nflSchedules"] },
      { cells: ["Historical lineup evidence", "The reviewed official gamebook sample has lineups, substitutions, inactive/did-not-play sections, statistics, and play-by-play. One sample is not a complete archive."], sources: ["nflGamebook"] },
      { cells: ["Roster and backups", "NFL roster pages and team-directory links exist. They do not by themselves confirm an ordinal second-/third-/fourth-string depth chart."], sources: ["nflRosterExample", "nflTeamDirectory"] },
      { cells: ["Tracking data", "NFL Football Operations describes player/ball tracking and derived metrics; the reviewed page does not establish project access rights for raw data."], sources: ["nflNextGen"] },
      { cells: ["Statistical validation", "NIST references cover validation, uncertainty, correlation, residual checks, and multiple comparisons; scikit-learn documentation lists probability scoring approaches."], sources: ["nistCrossValidation", "nistConfidence", "nistCorrelation", "nistMultiple", "sklearnMetrics"] }
    ];
    const unknownRows = [
      { cells: ["Model lines / probabilities", "Not calculated — no verified historical modeling dataset or locked model."], sources: ["nflSchedules", "nflPlayerStats", "nistCrossValidation"] },
      { cells: ["Odds, market margin, and settlement", "Not verified — no price feed, market snapshot history, or operator settlement definition is in the repository."], sources: ["nflSchedules", "nflRulebook"] },
      { cells: ["Injury impact / backup order", "Not measured — no snapshots or team-level depth evidence archive. Unknown rank remains blank."], sources: ["nflInjuries", "nflTeamDirectory", "nflGamebook"] },
      { cells: ["Correlation values / parlays", "Blank — exact leg definitions and paired outcomes are missing."], sources: ["nistCorrelation", "nflGamebook", "nistBootstrap"] },
      { cells: ["Leaderboard / rewards", "Empty — no validated entrants, score history, sample floor, prize rules, or target jurisdiction."], sources: ["nistMultiple", "nistConfidence", "nflRulebook"] }
    ];
    const next = '<div class="next-step-list"><div><span class="step-number">1</span><div><strong>Approve the data and rights plan</strong><p>Set source coverage, reuse terms, odds source, time cutoffs, and a versioned schema.</p></div></div><div><span class="step-number">2</span><div><strong>Lock a transparent baseline</strong><p>Choose one target and one benchmark before evaluating later games.</p></div></div><div><span class="step-number">3</span><div><strong>Validate before ranking</strong><p>Keep singles, player props, same-game combos, and cross-game parlays separate; show uncertainty and repeated-testing controls.</p></div></div></div>';
    return pageHeader(pageMeta[view]) + intro + section("What official-source review supports", renderTable(["Area", "Verified observation"], knownRows, "Official source review observations", { search: true })) + section("What remains unknown", renderTable(["Output", "Current answer"], unknownRows, "Unmeasured outputs and missing inputs")) + section("Recommended next decisions", next) + '<p class="disclaimer">This summary separates source availability from model performance. A source page is not evidence that a proposed signal is predictive.</p>';
  }

  function renderStrategies() {
    const note = '<div class="callout callout-blue"><div class="callout-icon" aria-hidden="true">i</div><div><strong>Research hypotheses only</strong><p>These are candidate mechanisms to test, not picks or evidence of an edge. No strategy has been run on historical NFL data in this repository.</p></div></div>';
    const rows = data.strategies.map(function (item) {
      return { cells: [item.id, item.name, item.market, item.signal, item.validation, item.status], sources: item.sources };
    });
    const table = renderTable(["ID", "Hypothesis", "Market", "Candidate signal", "How to test", "Current state"], rows, "NFL strategy hypotheses and source references", { search: true });
    const sequence = '<div class="card-grid card-grid-3"><article class="info-card"><span class="mini-label">Game lines</span><h3>Predict distributions</h3><p>Estimate outcome probabilities and margin/total distributions from pre-game information; compare against a simple, frozen baseline.</p>' + sourceList(["nflSchedules", "nflTeamStats", "sklearnMetrics"]) + '</article><article class="info-card"><span class="mini-label">Player props</span><h3>Separate opportunity from output</h3><p>Model attempts, targets, carries, or participation separately from yards and scoring. Require dated role and availability evidence.</p>' + sourceList(["nflPlayerStats", "nflGamebook", "nflInjuries"]) + '</article><article class="info-card"><span class="mini-label">Parlays & combos</span><h3>Model the joint event</h3><p>Estimate dependence on the exact defined legs; do not assume leg independence or present a guessed correlation.</p>' + sourceList(["nistCorrelation", "nistBootstrap", "nflGamebook"]) + '</article></div>';
    return pageHeader(pageMeta[view]) + note + section("Candidate signals", table, "Each row is explicitly labeled as untested or blocked; source links point to official data/method references, not to performance proof.") + section("How to stage the research", sequence) + '<div class="callout callout-amber"><div class="callout-icon" aria-hidden="true">!</div><div><strong>Cannot remove randomness</strong><p>The realistic objective is to identify a repeatable out-of-sample signal and quantify its uncertainty—not to claim that luck has been eliminated.</p>' + sourceList(["sklearnMetrics", "nistConfidence", "nistMultiple"]) + '</div></div>';
  }

  function renderValidation() {
    const rows = data.validationGates.map(function (item) {
      return { cells: [item.gate, item.requirement, item.passRule, item.state], sources: item.sources };
    });
    const table = renderTable(["Gate", "Requirement", "Proposed pass rule", "State"], rows, "Proposed NFL strategy validation gates", { search: true });
    const metrics = '<div class="metric-explainer"><article><span class="metric-tag">Probability</span><h3>Brier score / log loss</h3><p>Use a scoring rule that matches the target and compare to the same frozen baseline. A probability score evaluates predictions; it does not by itself prove profit or calibration.</p>' + sourceList(["sklearnMetrics"]) + '</article><article><span class="metric-tag">Uncertainty</span><h3>Intervals & sample floor</h3><p>Choose a smallest meaningful improvement first, then plan data volume and interval width. Do not invent a minimum sample size before defining the target and noise.</p>' + sourceList(["nistConfidence", "nistBootstrap"]) + '</article><article><span class="metric-tag">Selection</span><h3>Repeated trial control</h3><p>Keep failed variants in the registry. Repeatedly searching many strategies and reporting only the best result can overstate evidence.</p>' + sourceList(["nistMultiple", "nistCrossValidation"]) + '</article></div>';
    const chronology = '<div class="timeline"><div><span>01</span><strong>Timestamp</strong><p>Freeze features as known at prediction time.</p></div><div><span>02</span><strong>Hold out</strong><p>Test on later games not used in model fitting.</p></div><div><span>03</span><strong>Score</strong><p>Report probability quality, calibration, and baseline lift.</p></div><div><span>04</span><strong>Quantify</strong><p>Show uncertainty, sample coverage, and multiplicity controls.</p></div><div><span>05</span><strong>Shadow</strong><p>Track prospective predictions before competition rewards.</p></div></div>';
    return pageHeader(pageMeta[view]) + '<div class="callout callout-blue"><div class="callout-icon" aria-hidden="true">✓</div><div><strong>No candidate has passed a gate</strong><p>The gates below are a proposed protocol. They will stay open until a reproducible dataset and locked forecasts exist.</p></div></div>' + section("Validation gates", table) + section("Core evaluation components", metrics) + section("Prospective sequence", chronology) + '<p class="disclaimer">A backtest can be misleading when it leaks future information, uses an unreported search process, or is evaluated only on the same observations used to tune it.</p>';
  }

  function renderLineups() {
    const rows = data.lineupFields.map(function (item) {
      return { cells: [item.field, item.purpose, item.state], sources: item.sources };
    });
    const workflow = '<div class="lineup-workflow"><div><span class="workflow-icon">01</span><h3>Capture the report</h3><p>Store official source URL, selected season/week, retrieval time, and the exact published status.</p></div><div><span class="workflow-icon">02</span><h3>Confirm the role</h3><p>Join a player to an official dated roster/depth chart or gamebook lineup. If no source establishes order, rank stays blank.</p></div><div><span class="workflow-icon">03</span><h3>Measure the change</h3><p>Use opportunity/participation and later outcomes to test impact separately for offense and defense.</p></div><div><span class="workflow-icon">04</span><h3>Suppress uncertainty</h3><p>Flag stale or conflicting reports; do not turn uncertainty into an assumed starter or an asserted weakness.</p></div></div>';
    const note = '<div class="callout callout-amber"><div class="callout-icon" aria-hidden="true">!</div><div><strong>Important distinction: availability is not depth order</strong><p>An injury report status, roster entry, and gamebook lineup answer different questions. A second-/third-/fourth-string designation requires direct, dated evidence; it must not be inferred from a list order.</p>' + sourceList(["nflInjuries", "nflRosterExample", "nflTeamDirectory", "nflGamebook"]) + '</div></div>';
    return pageHeader(pageMeta[view]) + note + section("Required lineup data fields", renderTable(["Field", "Purpose", "Current state"], rows, "NFL injury and lineup data requirements", { search: true })) + section("How the injury signal should work", workflow) + '<p class="disclaimer">Do not infer medical severity or future availability from injury text. Preserve the source&#39;s published status and the time it was observed.</p>';
  }

  function renderCorrelations() {
    const rows = data.correlations.map(function (item) {
      return { cells: [item.id, item.pair, item.estimand, item.estimate, item.status], sources: item.sources };
    });
    const method = '<div class="method-grid"><article class="info-card"><span class="mini-label">Define</span><h3>Exact events</h3><p>Specify the market, threshold, game/player, prediction cutoff, and settlement rule before pairing outcomes.</p>' + sourceList(["nflGamebook", "nflPlayerStats", "nflRulebook"]) + '</article><article class="info-card"><span class="mini-label">Estimate</span><h3>Joint probability first</h3><p>For parlays, report both leg probabilities and the exact joint event probability; a coefficient alone does not price a combo.</p>' + sourceList(["nistCorrelation", "nistGlossary"]) + '</article><article class="info-card"><span class="mini-label">Uncertainty</span><h3>Resample by context</h3><p>Report the number of paired observations and an interval. Account for repeated games/players and avoid treating dependent records as fresh independent evidence.</p>' + sourceList(["nistBootstrap", "nistConfidence"]) + '</article></div>';
    return pageHeader(pageMeta[view]) + '<div class="callout callout-blue"><div class="callout-icon" aria-hidden="true">i</div><div><strong>Numeric values are intentionally blank</strong><p>No paired bet-leg outcomes, exact historical thresholds, or market lines are stored here. The table records what should be estimated; it does not imply a value.</p></div></div>' + section("Candidate dependence questions", renderTable(["ID", "Paired events", "Decision-relevant quantity", "Estimated value", "Status"], rows, "NFL prop and parlay correlation estimates", { search: true }), "Blank estimate cells are unverified by design; see the matching review flags.") + section("Estimation protocol", method) + '<p class="formula-note"><strong>Do not equate statistical correlation with a parlay price.</strong> The required quantity is the probability that all specified legs settle as wins under the defined rules, with uncertainty and context shown. Any coefficient should be calculated from matched, time-stamped outcomes—not supplied from intuition.</p>';
  }

  function renderLeaderboard() {
    const rows = data.leaderboardCategories.map(function (item) {
      return { cells: [item.category, item.ranking, item.reward], sources: item.sources };
    });
    const scorecard = '<div class="leaderboard-empty"><div class="leaderboard-trophy" aria-hidden="true">★</div><div><span class="eyebrow">No qualified strategies yet</span><h2>Nothing is ranked until it passes the gates.</h2><p>There are no submitted prediction logs, evaluated returns, or validated entrants in this repository. This is an empty leaderboard—not a zero-win result.</p><a class="text-link" href="' + hrefFor("validation") + '">Review qualification rules →</a></div></div>';
    const guardrails = '<div class="card-grid card-grid-3"><article class="info-card"><span class="mini-label">Skill signal</span><h3>Forecast quality</h3><p>Use a proper probabilistic score and calibration summary on untouched games; do not rank by hit rate alone.</p>' + sourceList(["sklearnMetrics", "nistCrossValidation"]) + '</article><article class="info-card"><span class="mini-label">Noise control</span><h3>Uncertainty & attempts</h3><p>Show sample size and interval; keep all tested variants visible and adjust for repeated comparisons.</p>' + sourceList(["nistConfidence", "nistMultiple"]) + '</article><article class="info-card"><span class="mini-label">Competition integrity</span><h3>Separate categories</h3><p>Do not combine singles, player props, same-game combos, and cross-game parlays into one unqualified score.</p>' + sourceList(["nflSchedules", "nistMultiple"]) + '</article></div>';
    return pageHeader(pageMeta[view]) + scorecard + section("Category scoring proposal", renderTable(["Category", "Proposed ranking basis", "Reward status"], rows, "Proposed NFL leaderboard categories", { search: true })) + section("Leaderboard guardrails", guardrails) + '<div class="callout callout-amber"><div class="callout-icon" aria-hidden="true">!</div><div><strong>Rewards are not approved</strong><p>No money, prize amount, or claim of eligibility is offered. Competition rules and any jurisdiction-specific requirements must be resolved before a reward is announced.</p><a href="' + hrefFor("flagged") + '">Review the open policy flag →</a></div></div>';
  }

  function renderQuestions() {
    const rows = data.questions.map(function (item) {
      return { cells: [item.id, item.question, item.known, item.answer, item.decision], sources: item.sources };
    });
    return pageHeader(pageMeta[view]) + '<div class="callout callout-blue"><div class="callout-icon" aria-hidden="true">i</div><div><strong>No response is required to use this research site</strong><p>Open decisions are listed rather than guessed. The system remains research-only and does not execute bets or request personal data.</p></div></div>' + section("Questions that block a reasonable decision", renderTable(["ID", "Question", "What is verified now", "Current answer", "Information still needed"], rows, "Open NFL modeling and competition questions", { search: true }), "Every answer is limited to the sources reviewed; open items are not filled by assumption.") + '<p class="disclaimer">The question set is a requirements checklist. Any future answer should be recorded with the chosen definition, effective date, owner, and source.</p>';
  }

  function renderSuggestions() {
    const rows = data.suggestions.map(function (item) {
      return { cells: [item.id, item.title, item.priority, item.suggestion, item.decisionImpact, item.tradeoff], sources: item.sources };
    });
    const cards = [
      { id: "data-foundation", title: "A — Data foundation first", label: "Recommended", detail: "Resolve source terms, historical coverage, price feed, timestamps, and schema before any edge claim.", tone: "recommended" },
      { id: "baseline-first", title: "B — Baseline model first", label: "Conditional", detail: "Prototype a transparent model only after the permitted historical game data and a genuine holdout are available; do not call it a betting edge without prices.", tone: "conditional" },
      { id: "rewards-now", title: "C — Rewards first", label: "Not recommended now", detail: "Launching rewards before validation, prize rules, jurisdiction, and anti-manipulation policy are defined is blocked by open questions.", tone: "blocked" }
    ];
    const pathCards = '<div class="decision-cards">' + cards.map(function (card) {
      return '<article class="decision-card ' + card.tone + '" data-path-card="' + card.id + '"><div class="decision-card-head"><span>' + escapeHtml(card.label) + '</span><span class="decision-check" aria-hidden="true">✓</span></div><h3>' + escapeHtml(card.title) + '</h3><p>' + escapeHtml(card.detail) + '</p><button type="button" class="button button-small" data-path-choice="' + card.id + '" aria-pressed="false">Select for planning</button></article>';
    }).join("") + '</div>';
    const reviewNote = '<div class="review-controls-note"><strong>Review controls are local only.</strong> A selection is saved in this browser to support discussion; it is not sent to GitHub, shared with other reviewers, or used to change code or data. <button type="button" class="text-button" id="reset-review">Clear my local choices</button><span class="local-status" id="local-status" aria-live="polite"></span></div>';
    const reviewRows = data.suggestions.map(function (item) {
      return { cells: [item.id, item.title, "Proposed — no implementation decision recorded", item.decisionImpact], sources: item.sources };
    });
    return pageHeader(pageMeta[view]) + '<div class="callout callout-blue"><div class="callout-icon" aria-hidden="true">↗</div><div><strong>Review before implementation</strong><p>These are options and trade-offs, not changes that will be applied automatically. Compare their evidence and risk before choosing a planning path.</p></div></div>' + section("Choose a planning path", pathCards + reviewNote, "A browser-local choice is a preference only; it does not approve or implement a change.") + section("Suggestion register", renderTable(["ID", "Suggestion", "Priority", "Proposal", "Decision impact", "Trade-off"], rows, "Suggestions for NFL decision support", { search: true })) + section("Decision record", renderTable(["ID", "Suggestion", "Current decision state", "Why it matters"], reviewRows, "Suggestion review status", { search: true }));
  }

  function renderFlagged() {
    const rows = data.flagged.map(function (item) {
      return { cells: [item.id, item.issue, item.detail, item.impact], sources: item.sources };
    });
    return pageHeader(pageMeta[view]) + '<div class="callout callout-amber"><div class="callout-icon" aria-hidden="true">!</div><div><strong>Unverified items do not block this research framework</strong><p>They do block numerical NFL lines, measured correlations, market-value claims, and prize awards. Unknown values are kept blank and are not inferred.</p></div></div>' + section("Open flags", renderTable(["ID", "Issue", "Evidence / limitation", "Decision impact"], rows, "Flagged NFL data and source review items", { search: true })) + '<p class="disclaimer">An official source link documents where a reviewer can check the record; it does not convert an unverified field into a verified value.</p>';
  }

  function renderSources() {
    const rows = Object.keys(data.sources).map(function (id) {
      const source = data.sources[id];
      return { cells: [source.label, source.publisher, source.use, source.reviewed], sources: [id] };
    });
    const note = '<div class="callout callout-blue"><div class="callout-icon" aria-hidden="true">↗</div><div><strong>Source policy</strong><p>NFL outcome, roster, injury, and schedule references are official NFL/NFL Football Operations pages. NIST and scikit-learn links support general statistical-method descriptions. No third-party odds or scraped values have been added.</p></div></div>';
    return pageHeader(pageMeta[view]) + note + section("Reviewed source register", renderTable(["Source", "Publisher", "What it is used for / limitation", "Review note"], rows, "Official and technical source register", { search: true }), "The register records source purpose and limitations; it is not a downloaded dataset.") + '<p class="source-date">Source review recorded: ' + escapeHtml(data.asOf) + ' (UTC). Pages that change by season or week must be checked again before ingestion.</p>';
  }

  const renderers = {
    home: renderHome,
    "executive-summary": renderExecutiveSummary,
    strategies: renderStrategies,
    validation: renderValidation,
    lineups: renderLineups,
    correlations: renderCorrelations,
    leaderboard: renderLeaderboard,
    questions: renderQuestions,
    suggestions: renderSuggestions,
    flagged: renderFlagged,
    sources: renderSources
  };

  function renderShell(content) {
    const nav = navItems.map(function (item) {
      const active = item[0] === view;
      return '<a href="' + hrefFor(item[0]) + '"' + (active ? ' aria-current="page" class="active"' : "") + '><span class="nav-dot" aria-hidden="true"></span>' + escapeHtml(item[1]) + '</a>';
    }).join("");
    const meta = pageMeta[view] || pageMeta.home;
    document.title = meta.title + " | NFL Decision Lab";
    return '<a class="skip-link" href="#main-content">Skip to content</a><div class="app-shell"><header class="topbar"><a class="brand" href="' + hrefFor("home") + '"><span class="brand-mark" aria-hidden="true">NFL</span><span class="brand-copy"><strong>Decision Lab</strong><small>Research workspace</small></span></a><div class="topbar-status"><span class="pulse-dot" aria-hidden="true"></span>Research only <span class="status-separator">·</span> no live feed</div></header><div class="layout"><aside class="sidebar"><div class="sidebar-label">Workspace</div><nav aria-label="Main navigation">' + nav + '</nav><div class="sidebar-foot"><span class="tiny-shield" aria-hidden="true">✓</span><span>Source-backed<br>or flagged</span></div></aside><main id="main-content" class="main-content">' + content + '</main></div><footer class="site-footer"><div><strong>NFL Decision Lab</strong><span>Strategy proposals are not picks; no bet execution or reward is active.</span></div><div class="footer-links"><a href="' + hrefFor("sources") + '">Sources</a><a href="' + hrefFor("flagged") + '">Flagged items</a><span>Reviewed ' + escapeHtml(data.asOf) + '</span></div></footer></div>';
  }

  function initFilters() {
    document.querySelectorAll("[data-filter-target]").forEach(function (input) {
      const tableId = input.dataset.filterTarget;
      const table = document.getElementById(tableId);
      const status = document.querySelector('[data-filter-status="' + tableId + '"]');
      if (!table) return;
      const rows = Array.from(table.querySelectorAll("tbody tr"));
      function update() {
        const query = input.value.trim().toLowerCase();
        let shown = 0;
        rows.forEach(function (row) {
          const matches = !query || row.dataset.searchRow.indexOf(query) !== -1;
          row.hidden = !matches;
          if (matches) shown += 1;
        });
        if (status) status.textContent = query ? shown + " matching row" + (shown === 1 ? "" : "s") : rows.length + " rows";
      }
      input.addEventListener("input", update);
      update();
    });
  }

  function readLocalReview() {
    try {
      return JSON.parse(localStorage.getItem("nfl-decision-lab-review-v1") || "{}");
    } catch (error) {
      return {};
    }
  }

  function writeLocalReview(state) {
    try {
      localStorage.setItem("nfl-decision-lab-review-v1", JSON.stringify(state));
      return true;
    } catch (error) {
      return false;
    }
  }

  function initSuggestionControls() {
    const choices = readLocalReview();
    const status = document.getElementById("local-status");
    function setStatus(message) {
      if (status) status.textContent = message;
    }
    document.querySelectorAll("[data-path-choice]").forEach(function (button) {
      const pathId = button.dataset.pathChoice;
      const selected = choices.selectedPath === pathId;
      button.setAttribute("aria-pressed", String(selected));
      if (selected) button.textContent = "Selected for planning";
      button.addEventListener("click", function () {
        const state = readLocalReview();
        state.selectedPath = pathId;
        const saved = writeLocalReview(state);
        document.querySelectorAll("[data-path-choice]").forEach(function (other) {
          const active = other.dataset.pathChoice === pathId;
          other.setAttribute("aria-pressed", String(active));
          other.textContent = active ? "Selected for planning" : "Select for planning";
          const card = other.closest(".decision-card");
          if (card) card.classList.toggle("selected", active);
        });
        setStatus(saved ? "Saved in this browser only." : "Browser storage is unavailable; choice was not saved.");
      });
      const card = button.closest(".decision-card");
      if (card) card.classList.toggle("selected", selected);
    });
    const reset = document.getElementById("reset-review");
    if (reset) {
      reset.addEventListener("click", function () {
        const saved = writeLocalReview({});
        document.querySelectorAll("[data-path-choice]").forEach(function (button) {
          button.setAttribute("aria-pressed", "false");
          button.textContent = "Select for planning";
          const card = button.closest(".decision-card");
          if (card) card.classList.remove("selected");
        });
        setStatus(saved ? "Local choice cleared." : "Browser storage is unavailable.");
      });
    }
  }

  if (!data) {
    document.getElementById("app").innerHTML = '<main class="main-content"><h1>Research data did not load</h1><p>Refresh the page or review the static site files.</p></main>';
    return;
  }
  const render = renderers[view] || renderHome;
  document.getElementById("app").innerHTML = renderShell(render());
  initFilters();
  if (view === "suggestions") initSuggestionControls();
})();
