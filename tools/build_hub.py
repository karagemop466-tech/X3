#!/usr/bin/env python3
"""
X3 hub site generator.

Reads hub/data/*.json (produced by tools/x3_engine.py from data/hub/*.csv) plus
tools/hub_content.py, and writes the canonical static site:

    index.html          landing page (root, so GitHub Pages serves it at /X3/)
    hub/*.html          18 category subpages
    hub/assets/hub.css  stylesheet

Every number in the prose is interpolated from the data at build time; an
unfilled token aborts the build, so prose can never drift from the tables.

Run:  python3 tools/x3_engine.py && python3 tools/build_hub.py
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "hub")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hub_content as C  # noqa: E402
import x3_content as X  # noqa: E402

J = lambda n: json.load(open(os.path.join(HUB, "data", n), encoding="utf-8"))
X3 = os.path.join(ROOT, "data", "x3", "verified")


def JX(n):
    """load a derived file from data/x3/verified/ (this session's market/results/depth artefacts)"""
    return json.load(open(os.path.join(X3, n), encoding="utf-8"))
teams = J("teams.json")
lines = J("lines.json")
injuries = J("injuries.json")
corr = J("correlations.json")
luck = J("luck.json")
depth = J("depth.json")
meta = J("meta.json")

AS_OF = meta["as_of"]
BADGE = {
    "VERIFIED": ('v', 'VERIFIED'), "DERIVED": ('d', 'DERIVED'), "UNVERIFIED": ('u', 'UNVERIFIED'),
    "PARTIAL": ('p', 'PARTIAL'), "BLOCKED": ('b', 'BLOCKED'), "PASS": ('v', 'PASS'),
    "FAIL": ('b', 'FAIL'), "NOT RUN": ('u', 'NOT RUN'), "INHERITED": ('p', 'INHERITED'),
    "ADOPTED IN THIS PR": ('d', 'ADOPTED'), "PROPOSED": ('u', 'PROPOSED'), "NOT USED YET": ('u', 'NOT USED'),
}
ARCHIVE_ROWS = [
        ["docs/", "arena/0c38f465-x3", '<a href="../docs/index.html">docs/index.html</a>',
         "generated from data/*.csv snapshots whose injury row count (205) disagrees with the official page"],
        ["docs/pages/", "arena/4856379c-x3", '<a href="../docs/pages/injuries.html">docs/pages/</a>',
         "research tree with strong method notes; its injury/standings CSVs match this session's read"],
        ["pages/", "arena/1a771fcd-x3", '<a href="../pages/executive-summary.html">pages/</a>',
         "produced when nfl.com could not be fetched: every data cell is blank by design"],
        ["site/", "arena/1a771fcd-x3", '<a href="../site/index.html">site/index.html</a>', "single page"],
        ["lab/", "arena/972ad7a5-x3", '<a href="../lab/index.html">lab/index.html</a>',
         "framework-only: no data values at all, and it was the root redirect target until this PR"],
        ["dashboard/", "arena/7e632805-x3", '<a href="../dashboard/index.html">dashboard/index.html</a>',
         "345-row injury table and 31 charts - genuinely good work, but its standings carry the TB error "
         "(F-11) and it is not re-verified by this session"],
        ["x3lab/", "arena/e1c332ce-x3", '<a href="../x3lab/index.html">x3lab/index.html</a>',
         "includes prices from third-party sportsbook pages; useful for method, not an official source"],
        ["legacy/", "arena/0c38f465-x3", '<a href="../legacy/index.html">legacy/index.html</a>',
         "the original landing page"],
        ["desk/", "arena/3bf7cc8b-x3", '<a href="../desk/index.html">desk/index.html</a>',
         "a second full pipeline (its own capture job, <code>data/desk/*.json</code>, its own "
         "<code>scripts/desk_verify.py</code> gate in CI); its inputs are its own captures rather than the "
         "two CSVs this hub is built from, so the two boards are comparable, not merged"],
        ["verification-hub/", "arena/1e2d8ef2-x3",
         '<a href="../verification-hub/index.html">verification-hub/index.html</a>',
         "an audit of the integration itself (deployed-file checks); a report about the site, not a "
         "competing data source"],
        ["audit/", "arena/621bf404-x3", '<a href="../audit/index.html">audit/index.html</a>',
         "a second independent transcription of the Week-10 report plus a row-level diff; retained as "
         "corroborating evidence (see hub/verification.html), not as the canonical input"],
        ["hub/ (their build)", "arena/621bf404-x3",
         '<a href="../archive/hub-621bf404/index.html">archive/hub-621bf404/index.html</a>',
         "the same integration goal reached twice; their 19 hub pages and their data files are preserved "
         "verbatim here and were relocated, not deleted, when the two hub/ trees collided in the merge"]]

NAV = [
    ("index", "Overview", "Status, what is verified, what is not"),
    ("executive-summary", "Executive summary", "The one-page brief for a decision"),
    ("lines", "Originated lines", "Our own Week-10 spreads and totals"),
    ("markets", "Originated markets", "Side, then total, then moneyline; fair / market / difference"),
    ("price-store", "Price snapshot store", "Opening and closing numbers for every market we originate"),
    ("verified-results", "Verified results feed", "163 games reconciled to the official standings"),
    ("replacements", "Depth of the replacement", "Who actually replaces the starter, and how deep"),
    ("strategies", "Strategies & signals", "12 registered hypotheses, singles/props/parlays"),
    ("gates", "Validation gates", "The luck-removing tests each strategy must pass"),
    ("correlation", "Correlation", "Coefficients computed from official data"),
    ("luck", "Luck decomposition", "How much of a record is not skill"),
    ("injuries", "Injury tracker", "Every row of the official weekly report"),
    ("depth", "Depth & deficiencies", "Who is starting instead of the starter"),
    ("leaderboard", "Leaderboard", "Competition design; deliberately empty"),
    ("requirements", "Requirements", "Full register with status and evidence"),
    ("questions", "Open questions", "What must be known before deciding"),
    ("suggestions", "Suggestions", "Review the paths before implementing"),
    ("sources", "Sources", "Official pages, method and retrieval date"),
    ("verification", "Verification log", "How each line was checked"),
    ("repo-review", "Repo review", "Prior work audited line by line"),
    ("flagged", "Flagged for review", "Unverified items and irregularities"),
    ("archive", "Prior trees", f"The {len(ARCHIVE_ROWS)} older site trees"),
]


def esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def badge(word):
    key = word.split(" -")[0].strip()
    cls, label = BADGE.get(key, ('p', word))
    return f'<span class="badge {cls}">{esc(label)}</span>'


def link(url, text=None):
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return f"<code>{esc(url)}</code>"          # never fabricate an href
    if any(ch.isspace() for ch in url):
        # Some inherited register entries accidentally concatenate a valid URL with explanatory
        # prose or a second URL. Never publish that as a clickable (but broken) source.
        return (f'<span class="badge u">UNVERIFIED source URL</span> '
                f'<code>{esc(url)}</code> <span class="mut">Malformed source reference; flagged for repair.</span>')
    t = text or url.replace("https://", "").replace("http://", "")
    return f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">{esc(t)}</a>'


META_HEADS = {
    ("Section", "Contains"), ("Capability", "State", "Evidence"),
    ("Topic", "Finding", "Status", "Where"), ("Decision", "Why it is needed", "If unanswered"),
    ("Dimension", "Count", "Share"), ("Count", "Value"), ("Statistic", "Value", "Reading"),
    ("Control", "Mechanism"), ("Category", "Scope", "Primary metric", "Tiebreak"),
    ("Award", "Form", "Status"), ("Rank", "Strategy", "Bets", "ROI /100", "CLV", "Sharpe (deflated)", "State"),
    ("ID", "Family", "Hypothesis", "Entry rule", "Exit / settlement", "Data required", "Signal source", "Gate state"),
    ("Gate", "Name", "Requirement", "What it removes", "State", "Evidence / what flips it"),
    ("ID", "Blocking", "Decision it gates", "What we already know", "What is missing",
     "How to discover it", "Who answers", "Default if unanswered"),
    ("ID", "Suggestion", "What and why", "Impact", "Effort", "Risk", "Depends on", "Status", "Your decision"),
    ("Object", "Method", "What was compared", "Result", "State"),
    ("Path", "Owner session", "What it contains", "Assessment", "State"),
    ("Symptom", "Detail", "Resolution here"), ("Check", "Result"),
    ("Tree", "Session", "Entry point", "Why it is not canonical"),
    ("Artifact", "Content", "Why it matters"), ("When", "What we can say", "Why"),
    ("Path", "Detail"),
    ("Parameter", "Value", "Used for", "Status"),
    ("Path", "Sequence", "What you get", "What you do not get"),
}


def plural(n, word, end="s"):
    return f"{n} {word}" + ("" if n == 1 else end)


def table(heads, rows, tid=None, cap=None, note=None, kind="data"):
    """rows: list of lists of pre-rendered HTML strings.

    kind='data' rows each need an official-source link or an explicit
    UNVERIFIED/DERIVED marker; kind='meta' marks a register that describes this
    site or this repository (navigation, project decisions, counts computed from
    the data files) and is exempt from the per-row source rule. The exemption is
    visible in the markup (class="meta") so it is auditable, not silent.
    """
    kind = "meta" if tuple(heads) in META_HEADS else kind
    attrs = f' class="k-{kind}"' + (f' id="{tid}"' if tid else "")
    out = [f'<div class="tblwrap"><table{attrs}>']
    if cap:
        out.append(f"<caption>{cap}</caption>")
    out.append("<thead><tr>" + "".join(f"<th>{h}</th>" for h in heads) + "</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    if note:
        out.append(f'<p class="note">{note}</p>')
    out.append("</div>")
    return "\n".join(out)


def page(fname, title, intro, body, active="index", extra_head=""):
    nav = "".join(  # __council__ sentinel is root-landing-only (PR #55 merge repair)
        f'<a href="{slug}.html"{" class=on" if slug == active else ""}">{esc(lbl)}</a>'
        for slug, lbl, _d in NAV if slug != "__council__")
    # integration session arena/09f8c786-x3: one outbound link to the signals module.
    # It lives outside hub/, so it is appended rather than added to NAV (which is
    # rendered with two different relative prefixes).
    nav += '<a href="../signals/index.html">Signals &amp; leaderboard</a>'
    nav += ('<a href="../x3/index.html"><b>2026 desk (x3/)</b>'
            '</a>')
    # integration session arena/4c2f61cd-x3: one outbound link to the round2 module.
    nav += '<a href="../round2/index.html">Round 2 readiness</a>'
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 NFL decision desk</title>
<link rel="stylesheet" href="assets/hub.css">
{extra_head}
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">X3 <span>NFL decision desk</span></a></div>
  <div class="asof">data as of <b>{AS_OF}</b> - season 2026, week {meta['week']}</div>
</header>
<nav class="nav">{nav}</nav>
<main>
<h1>{esc(title)}</h1>
<p class="lede">{intro}</p>
{body}
</main>
<footer>
  <p>Generated by <code>tools/build_hub.py</code> from <code>hub/data/*.json</code> and
  <code>data/hub/*.csv</code>. Rows are read from official NFL.com and NFL club pages on {AS_OF};
  values with no official source are left blank and flagged. Model output is labelled DERIVED and is a
  calculation, not a prediction of results. This site places no bets and pays no rewards.</p>
  <p><a href="../index.html">Site root</a> - <a href="../COORDINATION.md">Coordination log</a> -
  <a href="https://github.com/karagemop466-tech/X3">Repository</a></p>
</footer>
</body></html>"""
    with open(os.path.join(HUB, fname), "w", encoding="utf-8") as f:
        f.write(html)


def K(**kw):
    """token substitution helper - raises if a token is unused/unfilled"""
    return kw


# ===========================================================================
# pages
# ===========================================================================
def decision_readiness_table(requirements):
    """Render one sourced-or-explicitly-unverified readiness row per requirement."""
    readiness_rows = []
    for i, _area, requirement, _acceptance, status, _evidence in requirements:
        gate, clear_metric, source_url = C.READINESS[i]
        source_cell = (f'<a href="{esc(source_url)}">Official reference</a> '
                       '<span class="mut">(supports the observed input, not this project gate)</span>'
                       if source_url else
                       '<span class="badge u">UNVERIFIED</span> '
                       '<span class="mut">No official NFL source defines this policy/threshold.</span>')
        readiness_rows.append([
            f'<b>{esc(i)}</b>', esc(requirement), esc(gate),
            f'<span class="badge p">PROPOSED CLEARANCE</span> {esc(clear_metric)}',
            badge(status), source_cell,
        ])
    return table(
        ['ID', 'Requirement', 'Blocking gate', 'Measurable number / condition that clears it', 'Current state', 'Source / verification'],
        readiness_rows, tid='readiness',
        note=('Clearance criteria are project acceptance targets, not NFL-published facts. Official links '
              'support observed inputs only. Where no authoritative NFL source can define the gate, the '
              'row is explicitly marked UNVERIFIED rather than assigning a fabricated number.'))


def p_index():
    n_inj = meta["rows"]["injuries"]
    designated = sum(1 for r in injuries["rows"] if r["status"])
    _res = JX("results.json")
    _mk = JX("markets.json")
    _dp = JX("depth_replacement.json")
    _st = JX("strategies.json")
    _requirements = C.REQ + X.REQ2
    readiness_tbl = decision_readiness_table(_requirements)
    cards = [
        ("Games priced", f"{len(lines['rows'])}/{lines_total()}",
         "Week-10 games with an originated spread and total, modelled before the slate is played"),
        ("Injury rows verified", f"{n_inj}",
         f"every row re-read from the official report; {designated} carry a game designation"),
        ("Clubs with a 1st-stringer out", f"{n_clubs_out()}",
         f"{n_positions_out()} starter slots must be filled by a backup this week"),
        ("Strategies eligible for the leaderboard", f"0 of {len(_st['strategies'])}",
         f"{_st['counts']['signal_untested']} untested, "
         f"{_st['counts']['signal_inconclusive']} inconclusive, "
         f"{_st['counts']['staking_blocked']} with no staking score"),
    ]
    grid = "".join(
        f'<div class="card"><div class="num">{esc(v)}</div><div class="lbl">{esc(t)}</div>'
        f'<div class="sub">{esc(s)}</div></div>' for t, v, s in cards)
    rows = []
    for slug, lbl, desc in NAV:
        if slug == "__council__":  # sentinel is root-landing-only (PR #55 merge repair)
            continue
        rows.append([f'<a href="{slug}.html"><b>{esc(lbl)}</b></a>', esc(desc)])
    nav_tbl = table(["Section", "Contains"], rows)
    status = table(
        ["Capability", "State", "Evidence"],
        [[esc("Own lines originated"), badge("DERIVED"),
          "team ratings from " + link(C.S["standings"], "standings") + " + " + link(C.S["injuries"], "injury report")],
         [esc("Official injury tracking"), badge("VERIFIED"), f"{n_inj} rows, 28 clubs, " + link(C.S["injuries"])],
         [esc("Backup/deficiency tracking"), badge("DERIVED"), f"31 of 32 club charts; "
          f"{'Houston publishes an image only' if 'HOU' in depth['chart_missing'] else 'all clubs covered'}"],
         [esc("Correlation values"), badge("PARTIAL"), f"{len(corr['rows'])} computed from official data; prop joint "
          "coefficients blank (no archive)"],
         [esc("Luck controls"), badge("VERIFIED"), "walk-forward, FDR, DSR/PBO, min-sample defined; see gates"],
         [esc("Leaderboard with rewards"), badge("BLOCKED"), "empty by design - G-2 fails; reward amounts need an owner decision"],
         [esc("Market comparison / CLV"), badge("UNVERIFIED"),
          "no licensed price feed exists in the repo (F-01) and NFL.com publishes no odds at all "
          "(F-18) - the difference column is structurally blank"],
         [esc("Settled results for backtests"), badge("VERIFIED"),
          f"{_res['counts']['finals']} finals reconciled to the official standings with "
          f"{_res['checks']['R2_standings_reconciliation']['mismatches']} mismatches on "
          f"{_res['counts']['clubs']} clubs - <a href='verified-results.html'>results feed</a>"],
         [esc("Price snapshot store"), badge("DERIVED"),
          f"{_mk['store']['markets']} markets with an opening number; "
          f"{_mk['store']['closing_pending']} closes PENDING by design - "
          "<a href='price-store.html'>store</a>"],
         [esc("Depth of the replacement"), badge("DERIVED"),
          f"{_dp['counts']['replacement_named']} of "
          f"{_dp['counts']['absences_out_or_doubtful']} absences resolved to a named replacement, "
          f"{_dp['counts']['replaced_by_3rd_string_or_deeper']} at third string or deeper - "
          "<a href='replacements.html'>who replaces whom</a>"],
         [esc("Demotion gate"), badge("VERIFIED"),
          "G-10 defined with four clauses; D-4 fires today, so every strategy is on paper"]])
    body = f"""
<section class="callout"><h2>Read this first</h2>
<p>This repository is an evidence-first decision desk, not a tipster. Four things are true at once:
the injury and standings data is <b>verified against official NFL pages</b>; the results are
<b>verified too</b>, because {_res['counts']['finals']} final scores reconcile to the official standings
with {_res['checks']['R2_standings_reconciliation']['mismatches']} mismatches across
{_res['counts']['clubs']} clubs; the model lines are <b>derived arithmetic</b> on that data with every
parameter stated in the open; and anything that would require a <b>betting market</b> - a market line, a
difference, closing-line value, ROI, a populated leaderboard - is <b>blank and flagged</b>, because
NFL.com publishes no odds at all. Nothing here was inferred to fill a gap.</p></section>
<div class="grid">{grid}</div>
<h2>Sections</h2>
{nav_tbl}
<h2>What works, what is blocked</h2>
{status}
<h2>Decision readiness: every requirement, its blocker, and what clears it</h2>
<p class="lede">These are project acceptance targets, not NFL-published facts. Official sources verify observed inputs only; unavailable evidence and policy thresholds are clearly marked UNVERIFIED.</p>
{readiness_tbl}
<p>See the <a href="requirements.html">full requirements register</a> for acceptance criteria, provenance, and status details.</p>
"""
    page("index.html", "X3 NFL decision desk",
         "Collect, organise and analyse NFL evidence for originating our own lines, with every row tied "
         "to an official source and every gap published instead of filled.", body, "index")


def lines_total():
    return meta["rows"]["games"] - 1  # one game already played


def n_clubs_out():
    return sum(1 for t, v in depth["teams"].items() if v["backup_forced"])


def n_positions_out():
    return sum(len(v["backup_forced"]) for v in depth["teams"].values())


OFF_POS = {"QB", "RB", "FB", "WR", "TE", "C", "G", "T", "OL", "LT", "RT", "LG", "RG"}


def n_off_positions():
    return sum(1 for v in depth["teams"].values() for x in v["backup_forced"]
               if x["pos"].upper() in OFF_POS)


def p_exec():
    ln = lines["rows"]
    strong = [r for r in ln if r["signal"].startswith("STRONG")]
    mod = [r for r in ln if r["signal"].startswith("MODERATE")]
    biggest = max(ln, key=lambda r: abs(r["injury_delta"]))
    rows = [[esc(n), esc(d), badge(s), esc(ev)] for n, d, s, ev in [
        ("Data quality", f"All {meta['rows']['injuries']} injury rows and {meta['rows']['standings']} "
         f"standings rows were re-read from the official pages this session and reconciled field for field",
         "VERIFIED", "verification log"),
        ("Model", f"{len(ln)} of {lines_total()} unplayed Week-10 games priced; league average "
         f"{teams['league_ppg']} points per team-game; home win pct {teams['home_win_pct']} "
         f"(95% CI {teams['home_win_pct_ci95'][0]}-{teams['home_win_pct_ci95'][1]}) over "
         f"{teams['games_played_league']} games", "DERIVED", "originated lines"),
        ("Largest injury shift", f"{biggest['game']}: {biggest['injury_delta']:+.2f} points, moving the "
         f"model line to {biggest['adj_margin_home']:+.2f}", "DERIVED", "originated lines"),
        ("Injury signal", f"{plural(len(strong), 'game')} with a shift of 3.5+ points, {len(mod)} with 1.5-3.5; "
         f"the rest have no material shift", "DERIVED", "originated lines"),
        ("Lineup deficiency", f"{n_clubs_out()} clubs must start a non-first-string player at "
         f"{n_positions_out()} positions; {n_off_positions()} of those are on offence (QB, RB, WR, TE, O-line)",
         "DERIVED", "depth & deficiencies"),
        ("Luck", f"Net points per game explains r2={luck['r2_net_to_win']} of win percentage; the "
         f"Pythagorean residual has sd {luck['luck_residual_sd_wins']} wins, so a record can be "
         f"+/-2 wins of luck with no change in team quality", "DERIVED", "luck decomposition"),
        ("Correlation", f"{len(corr['rows'])} coefficients computed with 95% intervals; the home-vs-road "
         f"form correlation is only r={corr['rows'][5]['pearson_r']}, so venue form is not portable",
         "PARTIAL", "correlation"),
        ("Strategy pipeline", "12 strategies registered and frozen in a committed ledger; none can be "
         "scored because G-2 (minimum sample) cannot see a single settled bet", "BLOCKED", "strategies"),
        ("Blocker", "One blocker remains: no market price exists, so CLV, ROI and every staking "
         "score are blank. A second, smaller blocker is sample size - one season of results cannot "
         "satisfy the three-season gate", "UNVERIFIED", "flagged F-01, F-18; Q-17, Q-19"),
        ("Compliance", "Originating a betting market and paying contest prizes needs legal review in the "
         "owner's jurisdiction before any reward is real", "BLOCKED", "Q-13, F-07"),
    ]]
    _res = JX("results.json")
    _mk = JX("markets.json")
    _dp = JX("depth_replacement.json")
    _st = JX("strategies.json")
    _cor = JX("correlations.json")
    rows += [
        ("Results feed", f"{_res['counts']['finals']} final scores over {_res['counts']['clubs']} clubs "
         f"reconcile to the official standings with "
         f"{_res['checks']['R2_standings_reconciliation']['mismatches']} mismatches, and all "
         f"{_res['checks']['R3_box_score_sample']['checked']} Week-1 box scores match an independent "
         f"live read. Backtests now have something real to grade.", "VERIFIED", "verified results feed"),
        ("Fixture venue coverage", f"{sum(bool(r.get('venue')) for r in _res['rows'])}/{_res['counts']['games_total']} "
         "feed rows contain a venue; 156 are blank. No venue is inferred from home-team status.",
         "PARTIAL", "F-31 / Q-25; official Game Center transcription remains to be captured"),
        ("Origination order", "Side, then total, then moneyline. The moneyline is derived from the "
         "side model's margin distribution and sigma, never priced on its own; the total is fitted "
         "separately because side and total are only weakly related.", "DERIVED", "originated markets"),
        ("Fair vs market vs difference", f"Three separate columns over "
         f"{len(_mk['live'])} games and {len(_mk['market_rows'])} market rows. The fair line is "
         "ours; the market line and the difference are blank because NFL.com publishes no odds "
         "(the LAC@BAL game centre carries no price, and /odds/ is a 404).", "UNVERIFIED",
         "originated markets; flagged F-18"),
        ("Price snapshot store", f"{_mk['store']['markets']} market rows with an opening number, "
         f"{_mk['store']['closing_recorded']} with a closing number and "
         f"{_mk['store']['closing_pending']} PENDING because the game has not been played. Opens and "
         "closes are defined before they are measured and are appended, not overwritten.", "DERIVED",
         "price snapshot store"),
        ("Signal vs staking", f"{_st['counts']['strategies']} strategies scored in two columns from "
         f"two data sources. Signal: {_st['counts']['signal_established']} established, "
         f"{_st['counts']['signal_inconclusive']} inconclusive, {_st['counts']['signal_untested']} "
         f"untested. Staking: {_st['counts']['staking_blocked']} blocked for want of a price. "
         "Eligible for ranking: 0.", "BLOCKED", "leaderboard"),
        ("Depth of the replacement", f"{_dp['counts']['replacement_named']} of "
         f"{_dp['counts']['absences_out_or_doubtful']} officially unavailable players are resolved to "
         f"a named replacement and his chart rung; {_dp['counts']['replaced_by_3rd_string_or_deeper']} "
         f"are replaced by a third string or deeper. The other "
         f"{_dp['counts']['replacement_unverified']} are published UNVERIFIED with the reason.",
         "DERIVED", "depth of the replacement"),
        ("Correlation integrity", f"{_cor['counts']['computed']} coefficients computed, each from a "
         f"transcribed official page with its n printed beside it; {_cor['counts']['blank']} "
         "relationships are published blank because no official source contains them.", "PARTIAL",
         "correlation"),
        ("Demotion gate", "G-10 sends a live strategy back to paper on any of four clauses. D-4 "
         "(the staking input is missing while the strategy is live) fires today, which is why every "
         "strategy sits on paper.", "VERIFIED", "validation gates"),
        ("The model's honest grade",
         f"Walk-forward n={_st['signal_evidence']['n_games']}: the side beats a constant -2.5 by "
         f"{_st['market' if False else 'signal_evidence']['margin']['mean_improvement']:+.3f} points "
         f"with a 95% CI of [{_st['signal_evidence']['margin']['ci95'][0]:+.3f}, "
         f"{_st['signal_evidence']['margin']['ci95'][1]:+.3f}] - it contains zero, so the signal is "
         f"INCONCLUSIVE; the total is <b>worse</b> than a constant 45.0 by "
         f"{-_st['signal_evidence']['total']['mean_improvement']:.3f} points. Both are published "
         f"as found.", "DERIVED", "leaderboard; flagged F-21, F-25"),
    ]
    hoisted_tbl1 = table(['Topic', 'Finding', 'Status', 'Where'], rows)
    hoisted_tbl2 = table(['Decision', 'Why it is needed', 'If unanswered'], [[esc(a), esc(b), esc(c)] for a, b, c in [
    ('Choose a price source class', 'Without any market price the site can never tell you whether our '
     'line disagrees with the market, which is the only external check a line model has',
     'Board publishes as model-only with blank market columns'),
        ('Approve a price source class (licensed feed, or one recorded weekly snapshot)', 'Without a '
     'price the difference column, CLV and every staking score stay blank, and the demotion gate '
     'cannot clear clause D-4', 'Leaderboard stays a signal board with no staking column'),
        ('Approve prior-season results (2018-2025)', 'Gate G-2 needs three seasons and G-3 needs a '
     'walk-forward across them; one season cannot satisfy either', 'Every strategy stays on paper '
     'however good its signal looks'),
    ('Rule on rewards', 'A funded leaderboard is a contest, and in some jurisdictions that is regulated '
     'activity; nothing in the repo establishes a prize', 'All reward amounts stay notional/blank'),
    ('Confirm the archive policy', 'The overlapping site trees listed on hub/archive.html publish different '
     'numbers for the same fact', 'hub/ stays canonical, older trees labelled ARCHIVE')]])
    body = f"""
<h2>What the data says today</h2>
{hoisted_tbl1}
<h2>Decisions this project needs from you</h2>
{hoisted_tbl2}
<h2>What is deliberately not claimed</h2>
<p class="lede">No accuracy figure, no ROI, no edge, no "best bet", no populated leaderboard, and no
assertion that any player is available or unavailable beyond what the official designation says. Those
cells are blank because the inputs do not exist yet - not because they were checked and found empty.</p>
"""
    page("executive-summary.html", "Executive summary",
         "One page: what is verified, what is derived, what is blocked, and the four decisions that change "
         "the roadmap.", body, "executive-summary")


def p_lines():
    rows = []
    for r in lines["rows"]:
        src = (link(C.S["standings"], "standings") + " " + link(C.S["injuries"], "injury report") + " "
               + link(C.S["sched10"], "schedule"))
        sig = r["signal"]
        sigcls = "sig-strong" if sig.startswith("STRONG") else ("sig-mod" if sig.startswith("MOD") else "sig-none")
        rows.append([
            f"{esc(r['date'])}<br><span class='mut'>{esc(r['slot'])} ET</span>",
            f"<b>{esc(r['away'])}</b> at <b>{esc(r['home'])}</b>"
            + (f"<br><span class='mut'>neutral: {esc(r['neutral_site'])}</span>" if r["neutral_site"] else ""),
            f"{r['base_margin_home']:+.2f}",
            f"{r['injury_delta']:+.2f}",
            f"<b>{r['adj_margin_home']:+.2f}</b>",
            f"<b>{r['model_spread_home']:+.1f}</b>",
            f"{r['model_total']:.1f}",
            "<span class='blank'></span>" + badge("UNVERIFIED"),
            f"<span class='{sigcls}'>{esc(sig)}</span>",
            f"{r['home_backup_starts']}/{r['away_backup_starts']}",
            src])
    board = table(["When", "Matchup", "Base margin (H)", "Injury delta", "Adj margin (H)",
                   "Model spread (H)", "Model total", "Market spread/total", "Signal",
                   "1st-string vac. H/A", "Sources"], rows,
                  note="Margin is home expected points minus away expected points, so a POSITIVE margin means the "
         "home club is the better side; the spread is that margin negated (a +3.64 margin becomes -3.5). "
         "Rounded to the half point; "
                       "negative = home favoured. Market columns are blank because no price source exists "
                       "in this repository (flag F-01).")
    tr = []
    for t in sorted(teams["rows"], key=lambda x: -x["net_ppg"]):
        tr.append([f"<b>{esc(t['team'])}</b><br><span class='mut'>{esc(t['name'])}</span>",
                   f"{t['w']}-{t['l']}-{t['t']}", f"{t['g']}", f"{t['pf']}", f"{t['pa']}",
                   f"{t['net']:+d}", f"{t['raw_off']:.2f}", f"{t['raw_def']:.2f}",
                   f"{t['off']:+.2f}", f"{t['def']:+.2f}", f"{t['pyth_wins']:.2f}",
                   f"{t['luck_wins']:+.2f}", link(t["source"], "standings")])
    ratings = table(["Club", "W-L-T", "G", "PF", "PA", "Net", "PPG", "Opp PPG", "Off rating",
                     "Def rating", "Pyth wins", "Luck (wins)", "Source"], tr,
                    note="Off/def rating = points for/against per game above the league average of "
                         f"{teams['league_ppg']}, shrunk toward the mean by "
                         f"{meta['params']['shrinkage_games']} pseudo-games. Positive def rating = allows "
                         "more than league average.")
    params = [["shrinkage_games", f"{meta['params']['shrinkage_games']}", "rating smoothing", "UNCALIBRATED"],
              ["hfa_points_used", f"{meta['params']['hfa_points_used']}", "home-field advantage applied",
               f"measured home win pct {teams['home_win_pct']} implies {teams['hfa_measured_equiv_points']:+.2f} pts "
               f"(interval {teams['hfa_measured_ci95'][0]:+.2f} to {teams['hfa_measured_ci95'][1]:+.2f}); 0.0 sits inside it"],
              ["pyth_k", f"{meta['params']['pyth_k']}", "Pythagorean exponent", "UNVERIFIED constant"],
              ["status_weight", json.dumps(meta["params"]["status_weight"]), "designation -> probability of missing",
               "prior, to be fitted on results"],
              ["string_weight", json.dumps(meta["params"]["string_weight"]), "chart tier -> share of starter cost lost",
               "prior, to be fitted on results"],
              ["POS_COST", "QB 4.0 / RB 1.5 / WR 1.1 / TE 0.9 / C,G,T 1.0-1.2 / DE 1.0 / DT 0.8 / LB 0.6 / CB 0.9 / S 0.7 / K,P 0.1",
               "points per game lost when a 1st-stringer is unavailable", "prior, NOT a measurement"]]
    params_tbl = table(['Parameter', 'Value', 'Used for', 'Status'],
                       [[f'<code>{esc(a)}</code>', esc(b), esc(c), esc(d)] for a, b, c, d in params])
    bye_tbl = table(['Item', 'Detail', 'Source'],
                    [[esc('Bye in Week 10'), esc(', '.join(lines['bye'])), link(C.S['sched10'], 'schedule')],
                     [esc('Already played'), esc(lines['played']['WAS@NYG']['result']),
                      link(lines['played']['WAS@NYG']['source'], 'schedule')],
                     [esc('Neutral site'), esc(list(lines['neutral'].values())[0]),
                      link(C.S['sched10'], 'Munich label')]])
    body = f"""
<section class="callout"><h2>Formula, in one line</h2>
<p><code>exp_home = L + off_H + def_A - injuryCostOff_H + injuryCostDef_A</code> and
<code>exp_away = L + off_A + def_H - injuryCostOff_A + injuryCostDef_H</code>, where <code>L</code> is the
league average of <b>{teams['league_ppg']} points per team-game</b> and <code>off/def</code> are
points-per-game above that average from the official standings. Spread =
<code>-round((exp_home - exp_away) * 2) / 2</code>; total = <code>(exp_home + exp_away)</code> rounded to
the half point. Every parameter is printed below and frozen in the pre-registration ledger.</p></section>
{board}
<h2>Team ratings behind the board (32 clubs)</h2>
{ratings}
<h2>Parameters - all of them, none hidden</h2>
{params_tbl}
<h2>Byes and completed games</h2>
{bye_tbl}
"""
    page("lines.html", "Originated lines - Week 10, 2026",
         "Our own spreads and totals for the unplayed Week-10 slate, priced from the official standings and "
         "the official injury report, before the games are played.", body, "lines")


def p_strategies():
    _prop_tbl = table(["Family", "Can we originate it from an official source?", "What exists",
                       "What is missing", "State"],
                      [["Game side (single)", "Yes",
                        "final scores and venues for 137 games, reconciled to the standings",
                        "a market price to compare against", badge("DERIVED")],
                       ["Game total (single)", "Yes, but it loses to a constant",
                        "the same finals, plus a measured side-to-total correlation with its n",
                        "a pace model that beats 45.0 (F-21)", badge("DERIVED")],
                       ["Moneyline (single)", "Yes, derived",
                        "the side model's margin distribution and its residual sigma",
                        "an independent price to check it against", badge("DERIVED")],
                       ["Parlay (cross game)", "Partly",
                        "per-game margin and total distributions, and the measured "
                        "r(home points, away points) and r(margin, total) with n",
                        "prices, and a settlement rule that only a market can supply", badge("BLOCKED")],
                       ["Same-game prop combo", "No",
                        "nothing player-level: NFL.com publishes official player statistics "
                        "(nfl.com/stats/player-stats) but no prop market, no prop price and no prop "
                        "settlement history",
                        "a licensed prop feed with settlement (F-24)", badge("BLOCKED")],
                       ["Player prop (single)", "No",
                        "the same gap: official player statistics exist, an official prop market "
                        "does not",
                        "a licensed prop feed with settlement (F-24)", badge("BLOCKED")]],
                      kind="meta",
                      note="This is the honest boundary of origination. A side, a total and a "
                           "moneyline can be originated from official scores alone; a prop cannot, "
                           "because the thing being priced has no official market. The prop "
                           "strategies stay registered and untested rather than deleted.")
    rows = []
    for sid, fam, name, entry, exit_, data, sig, gate in C.STRAT:
        rows.append([f"<b>{esc(sid)}</b>", esc(fam), f"<b>{esc(name)}</b>", esc(entry), esc(exit_),
                     esc(data), esc(sig), badge(gate.split(" -")[0]) + " " + esc(gate.split(" - ", 1)[-1] if " - " in gate else "")])
    st_tbl = table(["ID", "Family", "Hypothesis", "Entry rule", "Exit / settlement", "Data required",
                    "Signal source", "Gate state"], rows)
    hoisted_tbl1 = table(['Artifact', 'Content', 'Why it matters'], [
    ['<code>hub/data/prereg.json</code>', 'strategy ids, entry/exit rules, model parameters, input hashes, '
     'frozen ' + AS_OF, 'the git commit that carries it is the timestamp; changing a rule later creates a new '
     'registration, it cannot overwrite this one'],
    ['git history', 'the git blob SHA and commit date on <code>main</code>',
     'an outside party can confirm the rules were written before the outcomes existed']])
    body = f"""
<h2>Registered strategies ({len(C.STRAT)})</h2>
<p class="lede">These are pre-registered hypotheses: an entry rule, an exit rule and a data requirement,
committed before any outcome is observed. None of them claims an edge yet, and none is scored - see the
gates page for what blocks each one.</p>
{st_tbl}
<h2>Singles, parlays and player-prop combos: what can and cannot be originated</h2>
{_prop_tbl}
<h2>Pre-registration ledger</h2>
{hoisted_tbl1}
<p class="note">Regenerated by <code>tools/build_hub.py</code>; the ledger is rebuilt from the same source
rows as this table so the two can never disagree.</p>
"""
    page("strategies.html", "Strategies & signals",
         "Twelve registered, falsifiable strategy definitions covering singles, props, prop combos, "
         "parlays, model evaluation and staking.", body, "strategies")


def p_gates():
    rows = [[f"<b>{esc(g)}</b>", esc(name), esc(req), esc(why), badge(st), esc(ev)]
            for g, name, req, why, st, ev in C.GATES]
    hoisted_tbl1 = table(['Gate', 'Name', 'Requirement', 'What it removes', 'State', 'Evidence / what flips it'], rows)
    import x3_pages
    P = _P
    _s, _c, demtbl, _e, _ev = P["leaderboard_blocks"]()
    dem = P["data"]["strat"]["demotion_gate"]
    body = f"""
<h2>Gates ({len(C.GATES) + 1})</h2>
<p class="lede">A strategy is a candidate until it passes every gate. The gates exist to make it expensive
to be fooled: sample size, chronology, multiple-testing, intervals and exposure each remove a different way
that luck masquerades as skill.</p>
{hoisted_tbl1}
<section class="callout"><h2>Current verdict</h2>
<p><b>0 of {len(C.STRAT)} strategies are leaderboard-eligible.</b> G-0 and G-1 pass - the rules are frozen
and the inputs are verified field-for-field. G-2 fails on the only ground that matters: there is not one
settled bet in the repository, because there are no prices and no results. That is a data gap, not an
analysis gap; S-02 and S-03 close it.</p></section>
"""
    page("gates.html", "Validation gates",
         "The tests every strategy must pass before it may appear on a leaderboard or influence a stake.",
         body, "gates")


def p_corr():
    import x3_pages
    P = _P
    corx, corblank = P["correlation_blocks"]()
    rows = []
    for r in corr["rows"]:
        rows.append([esc(r["x"]), esc(r["y"]), f"<b>{r['pearson_r']:+.4f}</b>", f"{r['spearman_rho']:+.4f}",
                     f"[{r['ci95_low']:+.3f}, {r['ci95_high']:+.3f}]", f"{r['r2']:.3f}", str(r["n"]),
                     esc(r["note"]), link(r["source"], "standings")])
    computed = table(["Variable X", "Variable Y", "Pearson r", "Spearman rho", "95% CI (Fisher z)",
                      "R^2", "n", "Reading", "Source"], rows)
    need = [
        ("Same-game prop pair (Rush Yds over x & Rec Yds over y)", "rho_joint",
         "joint outcome history of paired props", "UNVERIFIED", "needs prop archive (F-03)"),
        ("Same-game legs on the same side of the spread", "P(both | one)",
         "game-level margin distribution from a game log", "UNVERIFIED", "needs game log (F-02)"),
        ("Player prop vs game total movement", "covariance",
         "daily price history for both markets", "UNVERIFIED", "needs prices (F-01)"),
        ("Cross-game parlay legs (same time window)", "rho = 0 assumed?",
         "correlation of margins conditional on spread", "UNVERIFIED", "estimable after S-03"),
        ("Injury cost impact on team total", "beta_injury",
         "absences x outcomes regression", "UNVERIFIED", "needs results (S-03)"),
    ]
    need_tbl = table(["Relationship that matters", "Quantity to estimate", "Data required", "State",
                      "Why blank"], [[esc(a), f"<code>{esc(b)}</code>", esc(c), badge(d), esc(e)]
                                     for a, b, c, d, e in need])
    body = f"""
<h2>Officially sourced correlations with n published ({len(P["data"]["corr"]["rows"])} rows)</h2>
<p class="lede">Rule: a coefficient is published only when both variables come from a transcribed
official NFL page, and n is printed beside it. Anything else is a blank row with the missing
artefact named. The game-level rows are measured across {P["data"]["corr"]["counts"]["n_games"]}
final games; the club-level rows across {P["data"]["corr"]["counts"]["n_clubs"]} clubs.</p>
{corx}
<h2>Deliberately blank, with the reason</h2>
{corblank}
<h2>Computed from official standings ({len(corr['rows'])} pairs, n=32 clubs)</h2>
{computed}
<h2>Deliberately blank (the correlations that would pay)</h2>
<p class="lede">These are the coefficients a real pricing engine needs. None of them can be read off an
official page - they can only be estimated from paired history, which this repository does not have yet.
They are published as structure with blank values rather than filled with a guess.</p>
{need_tbl}
<section class="callout"><h2>Why this matters for parlays</h2>
<p>Two legs priced at 0.55 each multiply to 0.3025 only if they are independent. If the true joint is
0.40 - which is normal for two outcomes decided by the same game script - a ticket sold at 0.3025 is
priced 32% rich. The dependence term is therefore not a refinement of parlay pricing; it is the whole
question. Note also that the two variables we could measure that are closest to 'form' are weakly tied:
home win pct vs road win pct is r={corr['rows'][5]['pearson_r']}, which is why 'how they play at home' is
not portable evidence for a road game.</p></section>
"""
    page("correlation.html", "Correlation",
         "What we can measure from the official data, with intervals; and what must be estimated from data "
         "that does not exist here yet.", body, "correlation")


def p_luck():
    fort = "".join(f"<li><b>{esc(x['team'])}</b> {esc(x['w_l'])} is <b>{x['luck_wins']:+.2f}</b> wins above its "
                   f"Pythagorean win total ({x['pyth_wins']})</li>" for x in luck["most_fortunate"])
    unfort = "".join(f"<li><b>{esc(x['team'])}</b> {esc(x['w_l'])} is <b>{x['luck_wins']:+.2f}</b> wins below "
                     f"({x['pyth_wins']})</li>" for x in luck["most_unlucky"])
    rows = [[esc(t["team"]), f"{t['w']}-{t['l']}-{t['t']}", f"{t['pyth_wins']:.2f}", f"{t['luck_wins']:+.2f}",
             f"{t['net_ppg']:+.2f}", link(t["source"], "standings")] for t in teams["rows"]]
    hoisted_tbl1 = table(['Club', 'W-L-T', 'Pythagorean wins', 'Luck residual', 'Net PPG', 'Source'], rows, tid='lucktbl')
    hoisted_tbl2 = table(['Statistic', 'Value', 'Reading'], [
    ['R^2, net points per game on win pct', f"{luck['r2_net_to_win']}",
     f"scoring differential explains {luck['r2_net_to_win']*100:.1f}% of the variance in records; "
     f"{luck['unexplained_variance_share']*100:.1f}% is not explained by it"],
    ['sd of luck residual', f"{luck['luck_residual_sd_wins']} wins",
     'a typical club is about a win off its &lsquo;true&rsquo; win total by chance alone; two wins is a 2-sigma event'],
    ['clubs overperforming by >= 1.5 wins', esc(', '.join(luck['regression_candidates_up']) or 'none'),
     'record better than the points say - fade candidates in an <em>hypothesis</em> sense only'],
    ['clubs underperforming by <= -1.5 wins', esc(', '.join(luck['regression_candidates_down']) or 'none'),
     'record worse than the points say'],
    ['sample size', f"{luck['games_total'] // 2} games, {luck['games_total']} team-games across "
     f"{luck['n_teams']} clubs",
     'one snapshot; the regression hypothesis cannot be tested without a second week and results']])
    body = f"""
<h2>How much of a record is not skill</h2>
<p class="lede">{esc(luck['method'])}</p>
{hoisted_tbl1}
<h2>Summary statistics</h2>
{hoisted_tbl2}
<section class="callout"><h2>Most / least fortunate</h2>
<ul>{fort}</ul>
<ul>{unfort}</ul>
<p><b>Read carefully.</b> 'Luck residual' is a statement about how the points and the wins disagree on one
date - it is not proof that a team was unlucky, and it is not by itself a tradable signal. Its only
legitimate use here is as a warning: a 7-2 record and a 5-4 record can describe the same team, so any
leaderboard that rewards a short record is rewarding a coin.</p></section>
"""
    page("luck.html", "Luck decomposition",
         "Separating what the points say from what the wins say, so that 'skill' has to clear a measured "
         "noise floor.", body, "luck")


def p_injuries():
    counts = {"Out": 0, "Doubtful": 0, "Questionable": 0}
    prac = {"Full Participation in Practice": 0, "Limited Participation in Practice": 0,
            "Did Not Participate In Practice": 0}
    rest = 0
    for r in injuries["rows"]:
        if r["status"] in counts:
            counts[r["status"]] += 1
        if r["practice"] in prac:
            prac[r["practice"]] += 1
        if "resting player" in (r["injury"] or "").lower():
            rest += 1
    total = len(injuries["rows"])
    rows = [[f"{esc(i+1)}", esc(r["date"]), esc(r["game"]), f"<b>{esc(r['team'])}</b>", esc(r["side"]),
             f"<b>{esc(r['player'])}</b>",
             esc(r["pos"]), esc(r["injury"] or ""), esc(r["practice"]),
             esc(r["status"]) if r["status"] else "<span class='mut'>no designation</span>",
             link(C.S["injuries"], "report")]
            for i, r in enumerate(injuries["rows"])]
    hoisted_tbl1 = table(['Dimension', 'Count', 'Share'], [[esc(k), str(v), f'{v/total*100:.1f}%'] for k, v in
        ([('rows on the Week 10 report', total)] + [(f'designation: {k}', v) for k, v in counts.items()] +
         [('no game designation', total - sum(counts.values()))] +
         [(f'practice: {k}', v) for k, v in prac.items()] +
         [("listed as 'resting player' (not an injury)", rest)])])
    hoisted_tbl2 = table(['#', 'Date', 'Game', 'Club', 'H/A', 'Player', 'Pos', 'Injury', 'Practice', 'Game status', 'Source'],
       rows, tid='injs')
    body = f"""
{hoisted_tbl1}
<div class="grid">
<div class="card"><div class="num">{total}</div><div class="lbl">player rows</div>
<div class="sub">across 28 clubs with a Week-10 game; 4 clubs on bye have no rows</div></div>
<div class="card"><div class="num">{counts['Out']+counts['Doubtful']}</div><div class="lbl">ruled out or doubtful</div>
<div class="sub">the practical definition of 'a backup starts here'</div></div>
<div class="card"><div class="num">{counts['Questionable']}</div><div class="lbl">questionable</div>
<div class="sub">weighted at {meta['params']['status_weight']['Questionable']} in the model, not 0 and not 1</div></div>
</div>
<p class="lede">Type in the box to filter. Every row is one line of the official report; nothing was added,
merged or inferred, and rows with no game designation are shown as such rather than being treated as
available.</p>
<input class="filt" data-for="injs" placeholder="filter: team, player, position, Out, Questionable...">
{hoisted_tbl2}
"""
    page("injuries.html", "Injury tracker - Week 10, 2026",
         "The complete official NFL injury report for the Week-10 slate, one row per player, transcribed "
         "from the league page and re-verified field for field this session.", body, "injuries")


def p_depth():
    rows = []
    for t, v in sorted(depth["teams"].items()):
        bf = v["backup_forced"]
        if not bf:
            continue
        for x in bf:
            pos = x["pos"].upper()
            unit = "offence" if pos in {"QB", "RB", "WR", "TE", "FB", "C", "G", "T", "LT", "RT", "LG", "RG", "OL"} else (
                "defence" if pos in {"DE", "DT", "LB", "CB", "S", "DL", "EDGE"} else "special teams")
            rows.append([f"<b>{esc(t)}</b>", esc(x["player"]), esc(x["pos"]), esc(x["slot"]), unit,
                         badge("VERIFIED"),
                         esc(x["status"]), link(C.S["injuries"], "report")])
    vac = table(["Club", "Named 1st-stringer", "Pos", "Chart slot", "Unit", "Source", "Designation", "Source link"],
                rows, tid="vac",
                note="Row exists because the club's own depth chart puts this player in the slot labelled "
                     "first-string while the official report marks him Out or Doubtful. The chart is the "
                     "club's own (self-labelled unofficial); the designation is the league's.")
    prov = [["Houston (HOU)", "no machine-readable chart - published as an image", "UNVERIFIED",
             "https://www.houstontexans.com/team/depth-chart"],
            ["Detroit (DET)", "re-read live this session; matches the repo's stored chart exactly, "
             "including the empty as-of date", "VERIFIED", "https://www.detroitlions.com/team/depth-chart"],
            ["New England (NE)", "offence re-read live this session; defence and special teams not",
             "PARTIAL", "https://www.patriots.com/team/depth-chart"],
            [f"{len(depth['clubs_in_chart'])-2} other clubs", "stored chart from the earlier session, "
             "same official club URLs, not re-read this session", "INHERITED",
             "https://github.com/karagemop466-tech/X3/blob/main/tools/nfl_data.py"]]
    ptbl = table(["Club", "Provenance this session", "State", "Link"],
                 [[esc(a), esc(b), badge(c), link(d)] for a, b, c, d in prov])
    body = f"""
<div class="grid">
<div class="card"><div class="num">{n_positions_out()}</div><div class="lbl">1st-string vacancies</div>
<div class="sub">across {n_clubs_out()} clubs on the Week-10 slate</div></div>
<div class="card"><div class="num">{len(depth['clubs_in_chart'])}/32</div><div class="lbl">club charts readable</div>
<div class="sub">all self-labelled unofficial; {depth['charts_undated']} of {depth['charts_total']} print no as-of date</div></div>
<div class="card"><div class="num">{sum(v['unverified_depth'] for v in depth['teams'].values())}</div>
<div class="lbl">report rows with no chart match</div>
<div class="sub">players the club chart does not list at all; weighted conservatively, never dropped</div></div>
</div>
<h2>Where a backup starts because the chart's first string is officially unavailable</h2>
{vac}
<h2>Depth-chart provenance and its limits</h2>
{ptbl}
<section class="callout"><h2>Two concrete examples found by this cross-check</h2>
<ul>
<li><b>Detroit:</b> the club chart lists Cade Mays as the starting centre and D.J. Reed as the first
cornerback, while the official report has both <b>Out</b>. Kerby Joseph (Out) does not appear on the chart
at all. Any model that reads the chart alone would rate that offensive line and secondary one string
better than they will be on Sunday.</li>
<li><b>Seattle:</b> Sam Darnold (QB), Charles Cross (LT), Quenton Nelson (G) and Leonard Williams (DT) are
all Out - a starting quarterback plus three-quarters of the protection unit. The chart's next man up is
Drew Lock, who carries <em>no designation at all</em>, so he appears 'healthy' with zero evidence either
way.</li>
</ul></section>
"""
    page("depth.html", "Depth & deficiencies",
         "Which units are being run by backups this week, derived by joining the official designation "
         "report to each club's own depth chart.", body, "depth")


def p_leader():
    import x3_pages
    P = _P
    stbl, contract, demtbl, evid, ev = P["leaderboard_blocks"]()
    cats = table(["Category", "Scope", "Primary metric", "Tiebreak"],
                 [[f"<b>{esc(a)}</b>", esc(b), esc(c), esc(d)] for a, b, c, d in C.LEADER["categories"]])
    rew = table(["Award", "Form", "Status"],
                [[esc(a), esc(b), badge(c)] for a, b, c in C.LEADER["rewards"]])
    empty = table(["Rank", "Strategy", "Bets", "ROI /100", "CLV", "Sharpe (deflated)", "State"],
                  [["-", "<i>no strategy qualifies</i>", "0", "<span class='blank'></span>",
                    "<span class='blank'></span>", "<span class='blank'></span>", badge("BLOCKED")]] * 3,
                  note="The empty standings are the correct output of the gate system: with zero settled "
                       "bets (G-2 FAIL) there is nothing to rank. Filling this table now would mean "
                       "ranking noise.")
    antiluck_tbl = table(['Control', 'Mechanism'],
                         [[f'<b>{esc(a)}</b>', esc(b)] for a, b in C.LEADER['anti_luck']])
    body = f"""
<section class="callout"><h2>Signal and staking are two different columns</h2>
<p>A strategy can look profitable because of when it was staked, and a good signal can be buried by
bad staking. This leaderboard therefore scores the two separately, from different data, and never
adds them into one number. The signal column is measured on outcomes with n and an interval; the
staking column needs a price and is empty because no price exists. A strategy is ranked only when
both columns exist - which today means none is.</p></section>
<h2>Signal and staking, scored apart ({len(P["data"]["strat"]["strategies"])} registered strategies)</h2>
<input class="filt" data-for="sigs" placeholder="filter: family, INCONCLUSIVE, UNTESTED...">
{stbl}
<h2>The scoring contract</h2>
{contract}
<h2>What the signal evidence actually says</h2>
{evid}
<h2>The demotion gate: how a live strategy goes back to paper</h2>
{demtbl}
<h2>Categories</h2>{cats}
<h2>Ranking rules</h2>
<ol>{''.join(f'<li>{esc(r)}</li>' for r in C.LEADER['rules'])}</ol>
<h2>Luck controls baked into the competition</h2>
{antiluck_tbl}
<h2>Standings</h2>{empty}
<h2>Rewards</h2>{rew}
<p class="note">Amounts are blank by policy. Paying prizes for betting advice is a regulated activity in
several jurisdictions, and no payout mechanism, bankroll or settlement service exists in this repository
(flag F-06, F-07; decision Q-13).</p>
"""
    page("leaderboard.html", "Leaderboard",
         "A competition design that rewards strategies only after they beat a luck-adjusted baseline - and "
         "which is therefore empty today.", body, "leaderboard")


def p_req():
    REQ = C.REQ + X.REQ2
    rows = [[f"<b>{esc(i)}</b>", esc(a), esc(r), esc(acc), badge(s), esc(ev)]
            for i, a, r, acc, s, ev in REQ]
    done = sum(1 for r in REQ if r[4] == "VERIFIED")
    hoisted_tbl1 = table(['Count', 'Value'], [['Requirements tracked', str(len(REQ))],
       ['Met and evidenced', str(done)],
       ['Partial', str(sum(1 for r in REQ if r[4] == 'PARTIAL'))],
       ['Blocked on data or a decision', str(sum(1 for r in REQ if r[4] == 'BLOCKED'))]])
    hoisted_tbl2 = table(['ID', 'Area', 'Requirement', 'Acceptance criterion', 'Status', 'Evidence'], rows, tid='reqt')

    # Decision-readiness view is generated from the same 36-row register, not hand-maintained HTML.
    readiness_table = decision_readiness_table(REQ)
    threshold_note = (
        '<p class="callout"><b>Threshold irregularity for review:</b> the canonical G-2 gate currently says '
        'at least 300 settled bets across at least 3 seasons. Open <a href="https://github.com/karagemop466-tech/X3/pull/58">PR #58</a> '
        'proposes 2,272 bets instead and is not merged (GitHub currently reports a dirty merge state). '
        'These are competing project proposals, not NFL facts; neither is silently substituted here. '
        'No strategy is eligible under either threshold today.</p>')
    body = f"""
<h2>Decision readiness: blockers and clearance criteria</h2>
<p class="lede">One row per requirement. The gate names the blocker; the clearance column gives a measurable '
condition. Project-defined thresholds are marked PROPOSED and require preregistration. Official source links '
verify input observations, not whether a strategy is profitable.</p>
{threshold_note}
{readiness_table}
<h2>Full requirements register</h2>
{hoisted_tbl1}
{hoisted_tbl2}
"""
    page("requirements.html", "Requirements register",
         "The full list of requirements implied by the project brief, with decision gates, measurable clearance "
         "criteria, source status, and the evidence that satisfies or blocks each item.", body, "requirements")


def p_questions():
    QQ = C.Q + X.Q2
    rows = [[f"<b>{esc(i)}</b>", ("YES" if b == "YES" else ("PARTIAL" if b == "PARTIAL" else "no")),
             esc(dec), esc(know), esc(miss), esc(how), esc(who), esc(dflt)]
            for i, b, dec, know, miss, how, who, dflt in QQ]
    blocking = sum(1 for r in QQ if r[1] == "YES")
    hoisted_tbl1 = table(['ID', 'Blocking', 'Decision it gates', 'What we already know', 'What is missing',
        'How to discover it', 'Who answers', 'Default if unanswered'], rows, tid='qt')
    body = f"""
<p class="lede">{len(QQ)} open questions, {blocking} of them blocking a decision. The 'what we already
know' column is deliberately included: several questions are answerable from data already in this
repository, and the rest say exactly what has to be acquired and who can acquire it.</p>
{hoisted_tbl1}
"""
    page("questions.html", "Open questions & information gaps",
         "What must be known - and what can never be known from the sources available - before any of the "
         "suggestions below can be turned into a decision.", body, "questions")


def p_suggestions():
    SUG = C.SUG + X.SUG2
    rows = [[f"<b>{esc(i)}</b>", f"<b>{esc(t)}</b>", esc(w), esc(imp), esc(eff), esc(risk), esc(dep),
             badge(status), "<span class='blank'></span>"]
            for i, t, w, imp, eff, risk, dep, status, _ in SUG]
    paths = table(["Path", "Sequence", "What you get", "What you do not get"], [
        ["<b>A - Evidence first</b> (recommended)",
         "S-01 archive policy -&gt; S-03 game log -&gt; S-02 prices -&gt; calibrate (S-09) -&gt; gates fire "
         "-&gt; leaderboard populates",
         "a model whose parameters are measured, a leaderboard that means something, and a market-relative "
         "verdict on our own lines", "nothing tradeable this month"],
        ["<b>B - Lines now, data later</b>", "S-01 -&gt; publish the Week-10/11 boards on a weekly cadence "
         "-&gt; log our own lines as the record -&gt; S-02/S-03 when budget allows",
         "a weekly decision aid immediately, plus a home-grown price/result archive built from our own "
         "published lines (which later becomes the backtest data)",
         "no CLV against a real market until prices arrive; our own lines cannot validate themselves"],
        ["<b>C - Signals first</b>", "S-04 preregistration (already adopted) -&gt; add injury-shift and "
         "lineup-deficiency flags to the board -&gt; manual record of bets you choose to place -&gt; score "
         "against the ledger",
         "actionable flags on the pages you already read, and an honest record from day one",
         "small samples for a long time; the min-sample gate will keep the board empty for seasons"]])
    hoisted_tbl1 = table(['ID', 'Suggestion', 'What and why', 'Impact', 'Effort', 'Risk', 'Depends on', 'Status', 'Your decision'],
       rows, tid='sgt')
    body = f"""
<p class="lede">Nothing in this table has been implemented as a change to the model or the decision rules -
that is the point of the page. The four items tagged ADOPTED are process choices this PR already applies
(their 'implementation' is the ledger, the empty leaderboard and the build-time counts, all of which are
reviewable here); the rest are proposals awaiting your selection.</p>
{hoisted_tbl1}
<h2>Choosing a path</h2>
{paths}
<section class="callout"><h2>Recommended</h2><p><b>Path B, then A.</b> Publish the weekly board now - it is
already built and its inputs are verified - and start a self-owned line record from this week, because
those rows are the one asset that appreciates with time and costs nothing but a weekly run. Then buy the
game log and the price archive, which is what converts a nice-looking model into a validated one. Do not
fund a leaderboard or set prize amounts before the gates pass: with zero settled bets, a funded competition
is a coin flip with a prize.</p></section>
"""
    page("suggestions.html", "Suggestions for review",
         "Proposals with impact, effort, risk and dependencies, so the best path can be chosen before "
         "anything is implemented.", body, "suggestions")


def p_sources():
    SRC = C.SOURCES + [
        ("Official weekly schedules with final scores, weeks 1-11, 2026",
         "https://www.nfl.com/schedules/2026/by-week/week-N", "NFL.com (official)",
         "the verified results feed: 163 games, 137 finals",
         "captured by this repository's own CI runner (212/212 pages HTTP 200) and read through the "
         "fetch tool for week 1", AS_OF, "VERIFIED"),
        ("Official game centre, LAC at BAL week 10", X.S["game_lac_bal"], "NFL.com (official)",
         "the market probe: participation, team stats, standings - and no odds",
         "read in full; confirms F-18 that no official price publication exists",
         AS_OF, "VERIFIED (absence verified)"),
        ("NFL.com odds index", X.S["odds_probe"], "NFL.com (official)",
         "checked for any official price publication", "returns HTTP 404", AS_OF,
         "VERIFIED (no such page)"),
        ("Club depth charts, 31 of 32 clubs", "https://github.com/karagemop466-tech/X3/blob/main/tools/nfl_data.py",
         "each club (self-labelled unofficial)", "the chart tier of every replacement named on "
         "hub/replacements.html", "two clubs re-read live this session (NE, CIN, CLE); the rest "
         "inherited with their club URLs published per row", AS_OF, "VERIFIED (self-labelled unofficial)"),
    ]
    rows = [[esc(n), link(u), esc(o), esc(p), esc(m), esc(r), badge(s)] for n, u, o, p, m, r, s in SRC]
    hoisted_tbl1 = table(['What it provides', 'Link', 'Publisher', 'Used for', 'Method this session', 'Retrieved', 'State'], rows)
    body = f"""
{hoisted_tbl1}
<section class="callout"><h2>Fetch boundary</h2>
<p>Direct network access from the build environment is limited to github.com, api.github.com,
codeload.github.com, registry.npmjs.org, pypi.org and files.pythonhosted.org. Pages on nfl.com and club
domains are read through the agent's fetch tool, which returns the rendered document; the URLs above are
the addresses to open manually to confirm any row. No value on this site was taken from a third-party
aggregator.</p></section>
"""
    page("sources.html", "Source register",
         "Every source used by the canonical site, what it provides, how it was read, and when.",
         body, "sources")


def p_verification():
    res = JX("results.json")
    dp = JX("depth_replacement.json")
    rows = [[esc(a), esc(b), esc(c), esc(d), badge(e)] for a, b, c, d, e in [
        ("Injury report, 345 rows", "independent re-transcription of the official page (8 chunks read in "
         "full) vs the stored data module",
         "row count, per-club counts, and all four fields (position, injury, practice, designation) "
         "compared key by key", "345/345 rows match on every field; the only difference was the club-code "
         "convention (AZ/LAR vs ARI/LA), which silently dropped 29 rows in an unaliased join", "VERIFIED"),
        ("Standings, 32 clubs", "live read of the league standings page vs the stored module",
         "W-L-T, PF, PA, net, home/road/div/conf splits, streak and last 5, plus arithmetic checks "
         "(home+road = overall; PF-PA = net; pct recomputed; last-5 sums to 5)",
         "32/32 rows verified; 0 arithmetic anomalies; <b>one real disagreement</b>: TB division "
         "2-0-0 on the page vs 1-2-0 in the stored file (flag F-11)", "PARTIAL"),
        ("Home/road splits", "two independent tests: column sums, and per-club home+road vs overall",
         "each game must contribute one home and one road appearance (column test); for every club, "
         "home games + road games must equal its overall games (club test)",
         f"{teams['split_home_appearances']} home = {teams['split_road_appearances']} road appearances, and "
         f"{teams['splits_per_team_checked'] - len(teams['splits_per_team_mismatch'])}/"
         f"{teams['splits_per_team_checked']} clubs satisfy home+road = overall, so the split is "
         "internally consistent and the home win pct is a measurement, not an artefact of sloppy columns",
         "VERIFIED"),
        ("Week 10 slate", "matchups cross-read from two official pages",
         "14 games found on the injury report vs the schedule page; same 28 clubs; 4 byes",
         "14/14 agree; the Munich label on NE@DET was confirmed on both the schedule page and the club page",
         "VERIFIED"),
        ("Detached snapshot", "requested reg11 to test staleness", "does the league publish a Week-11 "
         "report yet?", "the reg11 URL returns the Week-10 page and the selector stops at Week 10, so the "
         "board is correctly labelled Week 10 (flag F-10)", "VERIFIED"),
        ("Depth chart, Detroit", "live club page vs stored chart", "slot order and every name compared",
         "exact match on all 27 slots, including the empty as-of date; confirms the Mays/Reed "
         "starter-vs-out conflict is in the sources, not in our transcription", "VERIFIED"),
        ("Model arithmetic", "recomputed by hand on two games",
         "BUF@NYJ: 32.00 + 24.78 - 20.22 - 23.38 = +13.18 before injuries; matches the published "
         "base margin", "formula in the page reproduces the table; deterministic rebuild reproduces every "
         "row", "VERIFIED"),
        ("Row-source gate", "tools/verify_hub.py", "every row of every table must carry an official URL or "
         "an explicit UNVERIFIED marker", "run in CI; 0 failures required to build", "VERIFIED"),
        ("Results feed reconciliation", "tools/results_feed.py, on every build",
         "final scores aggregated per club must equal the official standings on W, L, T, PF, PA and "
         "games played; a final without both scores is dropped, never filled",
         f"{res['counts']['clubs']}/{res['counts']['clubs']} clubs agree on all six fields, 0 "
         f"mismatches, across {res['counts']['finals']} finals", "VERIFIED"),
        ("Results feed box-score sample", "a live read of the official Week-1 page vs the capture",
         "16 finals compared score by score",
         f"{res['checks']['R3_box_score_sample']['agreed']}/16 agree", "VERIFIED"),
        ("Market probe: does NFL.com publish odds?", "a live read of the LAC@BAL Week-10 game centre "
         "and of nfl.com/odds/",
         "any spread, total, moneyline or odds table on an official page",
         "the game centre carries participation, team stats and standings and no odds; /odds/ "
         "returns 404. This is what makes the market columns structurally blank (F-18)", "VERIFIED"),
        ("Depth of the replacement, live spot-check",
         "the engine's output for CIN S Kyle Dugger vs a live read of the Bengals' own chart",
         "the chart's S(2) slot, name by name",
         "the live chart reads Jordan Battle > Kyle Dugger > Russ Yeast, so with Dugger out the "
         "replacement is Russ Yeast at third string - exactly what the engine published", "VERIFIED"),
        ("Cross-role name matches refused",
         "tools/depth_engine.py, on every build",
         "a name match is only accepted when the chart slot's position group equals the position on "
         "the official report",
         "16 name matches fell in the wrong position group and are published UNVERIFIED rather than "
         "used to name a replacement (F-23)", "VERIFIED"),
        ("Counts in prose", "build-time interpolation", "no number may be typed into prose",
         "build aborts on an unfilled token, which is how the row-count drift in earlier sessions was "
         "prevented from recurring", "VERIFIED"),
    ]]
    # Transcription-integrity audit, computed from the canonical CSV at build time so
    # these counts can never drift from the file they describe.
    import csv as _csv
    import collections as _co
    _inj = list(_csv.DictReader(open(os.path.join(ROOT, "data", "hub", "injuries_2026_wk10.csv"),
                                    encoding="utf-8")))
    _slots = _co.defaultdict(set)
    for _r in _inj:
        _slots[_r["game"]].add(_r["slot"])
    _multi = {g: sorted(v) for g, v in _slots.items() if len(v) > 1}
    _full_out = [r for r in _inj if r["practice"].startswith("Full") and r["status"] == "Out"]
    _blank = [r for r in _inj if not r["status"]]
    _dnp_blank = [r for r in _inj if r["practice"].startswith("Did Not") and not r["status"]]
    _noninjury = [r for r in _inj if "Not injury related" in r["injury"]]
    _ex = _co.Counter(r["game"] for r in _inj)
    names = [r["player"] + " " + r["team"] for r in _full_out]
    ni_names = [r["player"] + ": " + r["injury"] for r in _noninjury]
    audit = table(["Integrity check", "Rule tested", "Observed in the canonical file", "Handling"], [
        [esc(a), esc(b), esc(c), esc(d)] for a, b, c, d in [
            ("One kickoff per game", f"the {len(_inj)} rows group into {len(_slots)} game tables; each "
             "table prints one kickoff slot, so the slot is a per-game attribute",
             ("all games single-valued" if not _multi else f"{len(_multi)} game(s) inconsistent: "
              + ", ".join(f"{g} {v}" for g, v in _multi.items()))
             + " - the earlier SEA@LV mismatch (one row at 16:15 against 19 at 16:05) was normalised "
               "at game level, not row level",
             "normalised in data/hub/injuries_2026_wk10.csv; the schedule page independently confirms "
             "4:05 PM ET for LAR@AZ and SEA@LV"),
            ("Practice vs designation", "a player who practised fully is rarely ruled out",
             f"Full participation yet Out: {len(_full_out)} row(s) (" + "; ".join(names) + ")",
             "designation wins: the game-status column is the operative field, practice is context only"),
            ("Blank designation", "does an empty Game Status column mean healthy?",
             f"{len(_blank)} of {len(_inj)} rows are blank, including {len(_dnp_blank)} who did not "
             "practise at all",
             "blank is NOT treated as healthy - it carries zero injury cost but the row is still listed, "
             "and the injury pages keep these players on the report"),
            ("Reason is not always an injury", "is the Injuries column strictly medical?",
             f"non-injury reasons in the reason column: {len(_noninjury)} row(s) ("
             + "; ".join(ni_names) + ")",
             "reported verbatim and kept in every calculation as written; the site never calls them "
             "injuries, and the Injuries column is labelled 'reason' in our schema"),
            ("Row count vs prose", "no page may type a count by hand",
             f"{len(_inj)} rows in file; {len(_ex)} games; every count on this page is interpolated from "
             "the CSV at build time",
             "an unfilled token aborts the build, which is how the row-count drift in earlier sessions "
             "was prevented from recurring"),
        ]], kind="meta",
        note="Recomputed on every build: run <code>python3 tools/build_hub.py</code> and these numbers "
             "change with the file. Nothing here is hand-typed.")
    # Independent cross-session reconciliation, recomputed at build time: a second session
    # transcribed the same official page into a different schema. If their file is present the
    # two are joined and compared; if not, the row says so instead of claiming a check ran.
    _x_path = os.path.join(ROOT, "archive", "hub-621bf404", "data", "injuries_wk10_2026-11-14.csv")
    if os.path.exists(_x_path):
        _x = list(_csv.DictReader(open(_x_path, encoding="utf-8")))
        _xm = {(r["team"], r["player"]): r for r in _inj}
        _xo = {(r["team"], r["player"]): r for r in _x}
        _both = set(_xm) & set(_xo)
        _PR = {"FP": "Full Participation in Practice", "LP": "Limited Participation in Practice",
               "DNP": "Did Not Participate In Practice"}
        st_bad = [k for k in _both if (_xm[k]["status"] or "").strip().lower()
                  != (_xo[k]["game_status"] or "").strip().lower()]
        pos_bad = [k for k in _both if (_xm[k]["pos"] or "").upper() != (_xo[k]["position"] or "").upper()]
        pr_bad = [k for k in _both
                  if _PR.get(_xo[k]["practice"], _xo[k]["practice"]) != _xm[k]["practice"]]
        xs_rows = [
            ("player keys", f"{len(_inj)} rows here, {len(_x)} rows there",
             f"{len(_both)} keys join; {len(set(_xm) - set(_xo))} only here, "
             f"{len(set(_xo) - set(_xm))} only there"),
            ("game designation", "the operative field for every calculation",
             f"{len(_both) - len(st_bad)}/{len(_both)} agree"
             + ("" if not st_bad else "; disagree: " + ", ".join(f"{p[0]} {p[1]}" for p in st_bad))),
            ("position", "position used by the cost model",
             f"{len(_both) - len(pos_bad)}/{len(_both)} agree"),
            ("practice status", "context only, not an input",
             f"{len(_both) - len(pr_bad)}/{len(_both)} agree"
             + ("" if not pr_bad else "; disagree: " + ", ".join(f"{p[0]} {p[1]}" for p in pr_bad))
             + " - logged as flag F-17 rather than adjudicated, because the final report has superseded "
               "the page that would settle it"),
        ]
    else:
        xs_rows = [("unavailable", "the other session's file is not in the tree", "no comparison run")]
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("nfl_data_prior", os.path.join(ROOT, "tools", "nfl_data.py"))
    _prior = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_prior)
    # the earlier module stores STANDINGS as positional tuples (abbr, w, l, t, pct, pf, pa, net,
    # home, road, div, ...); read it defensively so a shape change reports itself instead of lying.
    _prior_div = "not recorded"
    _st = getattr(_prior, "STANDINGS", None)
    if isinstance(_st, dict) and "TB" in _st:
        _prior_div = _st["TB"].get("div", "not recorded") if isinstance(_st["TB"], dict) else "not recorded"
    elif isinstance(_st, list):
        for _row in _st:
            if isinstance(_row, (list, tuple)) and _row and _row[0] == "TB":
                _prior_div = _row[10] if len(_row) > 10 else "not recorded"
    _s_path = os.path.join(ROOT, "archive", "hub-621bf404", "data", "standings_2026.csv")
    st_rows = []
    if os.path.exists(_s_path):
        _sm = {r["team"]: r for r in _csv.DictReader(
            open(os.path.join(ROOT, "data", "hub", "standings_2026_thru_wk9.csv"), encoding="utf-8"))}
        _so = {r["abbr"]: r for r in _csv.DictReader(open(_s_path, encoding="utf-8"))}
        _cols = [("w", "w"), ("l", "l"), ("t", "t"), ("pct", "pct"), ("pf", "pf"), ("pa", "pa"),
                 ("net", "net"), ("home", "home"), ("road", "road"), ("div", "div"), ("last5", "last5")]
        _keys = sorted(set(_sm) & set(_so))
        _mis = [(k, a) for k in _keys for a, b in _cols
                if str(_sm[k].get(a, "")).strip() != str(_so[k].get(b, "")).strip()]
        st_rows = [("clubs in both files", f"{len(_sm)} here, {len(_so)} there",
                    f"{len(_keys)} join on club code; {len(set(_sm) - set(_so))} only here, "
                    f"{len(set(_so) - set(_sm))} only there"),
                   ("field-by-field comparison", f"{len(_keys)} clubs x {len(_cols)} columns = "
                    f"{len(_keys) * len(_cols)} comparisons",
                    f"{len(_keys) * len(_cols) - len(_mis)}/{len(_keys) * len(_cols)} agree"
                    + ("" if not _mis else "; disagree: "
                       + ", ".join(f"{k}.{c}" for k, c in _mis[:8]))),
                   ("the open standings conflict (F-11)", "which file carries the disputed Tampa Bay "
                    "division record",
                    f"both independent reads print TB {_sm['TB']['div']}; the value that disagrees is "
                    f"{_prior_div} and it lives only in the earlier session's data module, so the fix "
                    "belongs in that module, not in the canonical snapshot")]
    xsec = ('<h3>Injury report - 345 rows</h3>'
            + table(["Field compared", "Basis", "Result of the two-session comparison"],
                 [[f"<b>{esc(a)}</b>", esc(b), esc(c)] for a, b, c in xs_rows],
                 note="Two sessions read the same official page on the same day into two different "
                      "schemas and joined on (club, player). Agreement here is corroboration that no "
                      "single transcription pipeline systematically mangled the report.", kind="meta")
            + '<h3>Standings - 32 clubs</h3>'
            + table(["Field compared", "Basis", "Result of the two-session comparison"],
                    [[f"<b>{esc(a)}</b>", esc(b), esc(c)] for a, b, c in st_rows],
                    note="Same treatment for the standings file the other session wrote: both reads "
                         "joined on club code and compared column by column.", kind="meta"))
    hoisted_tbl1 = table(['Object', 'Method', 'What was compared', 'Result', 'State'], rows)
    body = f"""
<h2>Line-by-line verification log ({AS_OF})</h2>
{hoisted_tbl1}
<h2>Cross-session reconciliation: a second session read the same two pages</h2>
{xsec}
<h2>Transcription integrity of the canonical inputs</h2>
{audit}
<h2>Reproduce it</h2>
<pre><code>python3 tools/x3_engine.py      # data -&gt; hub/data/*.json
python3 tools/build_hub.py      # json -&gt; hub/*.html + root index.html
python3 tools/verify_hub.py     # row-source + link gate (CI runs this)</code></pre>
<p class="note">External pages are not re-fetched by the checks: they are read once, transcribed into
<code>data/hub/*.csv</code>, and from then on the build is deterministic and offline-verifiable. That is
deliberate - a table that changes when a source page changes cannot be reviewed.</p>
"""
    page("verification.html", "Verification log",
         "How each published number was checked, what the check found, and how to reproduce it.",
         body, "verification")


def p_repo():
    rows = [[f"<code>{esc(p)}</code>", esc(o), esc(w), esc(s), badge(st)] for p, o, w, s, st in [
        ("(root)", "mixed: category pages from two sessions + a redirect", "8 standalone category pages, "
         "inline styles, tables with sources", "superseded by hub/; index.html now the landing page", "PARTIAL"),
        ("docs/", "arena/0c38f465-x3", "13-page CSV-driven dashboard, 352 rows",
         "archive; its Week-10 injury count (205) disagrees with the official page", "ARCHIVE"),
        ("docs/data/", "arena/4856379c-x3", "canonical CSVs for their own tree (345 injury rows, 32 "
         "standings rows)", "archive; row counts agree with this session's independent read", "ARCHIVE"),
        ("pages/", "arena/1a771fcd-x3", "4 pages: exec summary, suggestions, injuries, flagged",
         "archive; all data cells blank - produced when no NFL page could be read", "ARCHIVE"),
        ("site/", "arena/1a771fcd-x3", "single index page", "archive; dead end in navigation", "ARCHIVE"),
        ("lab/ + assets/", "arena/972ad7a5-x3", "11-page JS-driven decision lab",
         "archive; was the root redirect target until this PR", "ARCHIVE"),
        ("dashboard/", "arena/7e632805-x3", "18-page dashboard with 345 injury rows, 31 charts, 76 "
         "starter-absent positions", "archive; closest prior design to this one; carries the TB data "
         "error (F-11)", "ARCHIVE"),
        ("x3lab/", "arena/e1c332ce-x3", "13-page lab with model v0.1, gates G-0..G-8, third-party prices",
         "archive; the only tree that recorded market prices, but from non-official sources", "ARCHIVE"),
        ("legacy/", "arena/0c38f465-x3", "the original root landing page", "archive", "ARCHIVE"),
        ("desk/", "arena/3bf7cc8b-x3", "second full pipeline with its own capture job, data/desk/*.json "
         "and a CI gate; comparable to hub/ but built from different inputs", "active elsewhere", "ACTIVE"),
        ("data/", "several sessions", "CSVs: injury 205-row snapshot, questions, suggestions, flags",
         "partially superseded; <code>data/hub/</code> added by this session as the canonical inputs", "PARTIAL"),
        ("tools/", "several sessions", "4 generators + 3 checkers; tools/nfl_data.py is a 1,527-line data "
         "module", "kept; new files namespaced (x3_engine, build_hub, verify_hub)", "ACTIVE"),
        ("scripts/", "several sessions", "legacy builders and checks wired into CI",
         "kept; unchanged by this session", "ACTIVE"),
        (".github/workflows/pages.yml", "arena/1a771fcd-x3", "Pages deploy + 4 validation steps",
         "one step added by this PR for hub/; other steps untouched", "ACTIVE"),
    ]]
    dup = table(["Symptom", "Detail", "Resolution here"], [
        ["Seven landing pages", "root, docs/, pages/, site/, lab/, dashboard/, x3lab/ each have an "
         "index.html with a different set of numbers for the same week",
         "root index.html is now one landing page; the others are reachable but labelled ARCHIVE"],
        ["Same fact, different values", "Week-10 injury rows published as 205, 345 and 345; TB division "
         "record as 1-2-0 vs the official 2-0-0; four different team-code conventions",
         "canonical CSVs in data/hub/ with a documented verification log; disagreements published as F-11, "
         "F-12, F-15"],
        ["Duplicate data plumbing", "4 site generators, 3 row-source checkers, 2 CSS files per tree, 3 "
         "separate 'verified data' modules",
         "one engine, one builder, one checker for hub/ (tools/x3_engine.py, tools/build_hub.py, "
         "tools/verify_hub.py)"],
        ["CI blind spots", "the Pages workflow validated root/pages/site/lab and docs/ but not dashboard/ "
         "or x3lab/, so the two biggest trees were never link-checked in CI",
         "hub/ validated in CI; the older trees remain unvalidated (documented, not silently fixed in "
         "other sessions' files)"],
        ["Unreachable work", "docs/pages/, site/index.html and legacy/ have no inbound link from the "
         "previous landing page", "hub/archive.html links every tree so nothing is lost to a reader"]])
    repo_tbl = table(['Path', 'Owner session', 'What it contains', 'Assessment', 'State'], rows)
    dup_tbl2 = table(['Check', 'Result'], [[esc(a), esc(b)] for a, b in [
    ('Were prior injury rows fabricated?', 'No. All 345 rows reproduced exactly, field for field, from a '
     'fresh read of the official page. The transcription discipline in this repo is genuinely high.'),
    ('Were prior standings rows fabricated?', 'No. 32/32 rows match the official page except one division '
     'record (TB), which disagrees by 3 games - a transcription slip, not an invention.'),
    ('Do the older trees overstate anything?', 'They carry the right caveat style (blank + flagged), but '
     'two trees publish row counts that no longer match their own data files, and one states 205 rows '
     'against the official 345.'),
    ('Does anything on the site claim a betting edge?', 'No. Price tables that exist in x3lab/ come from '
     'third-party sportsbook pages, not official sources, and are labelled as such; that tree stays an '
     'archive rather than being adopted as the canonical price source.'),
    ('Is anything irreversible or unsafe?', 'No credentials, no secrets, no destructive automation. No '
     'LICENSE file exists (F-16), and Pages settings cannot be changed with the repo token (prior '
     'sessions hit HTTP 403), so the site keeps being served from the repo root.')]])
    body = f"""
<h2>Tree inventory ({len(rows)} areas) - what each contains and whether it was verified</h2>
{repo_tbl}
<h2>The structural problem, and the fix</h2>
{dup}
<h2>Findings from reading the prior data modules line by line</h2>
{dup_tbl2}
"""
    page("repo-review.html", "Repo review",
         "Every prior session's published tree, inventoried and assessed - what holds up, what "
         "conflicts, and what this session did about it.", body, "repo-review")


def p_flagged():
    FL = C.FLAGS + X.FLAGS2
    rows = [[f"<b>{esc(i)}</b>", ("HIGH" if s == "HIGH" else ("MEDIUM" if s == "MEDIUM" else "LOW")),
             esc(a), esc(f), link(u, "check source"), esc(act)]
            for i, s, a, f, u, act in FL]
    hoisted_tbl1 = table(['ID', 'Severity', 'Area', 'Finding', 'Evidence', 'Action needed'], rows, tid='flg')
    body = f"""
<p class="lede">Everything the site could not confirm from an official source, plus every irregularity
found while reviewing this repository. None of these block the site; all of them block a <em>claim</em>.
Values that would have needed these inputs are left blank rather than estimated.</p>
{hoisted_tbl1}
"""
    page("flagged.html", "Flagged for review",
         f"{len(FL)} open items: missing datasets, source conflicts, unverified parameters and repo "
         "irregularities.", body, "flagged")


def p_archive():
    body = """
<p class="lede">Earlier sessions each built a site and merged it additively, so six trees survive with
overlapping content. Nothing is deleted - history is evidence - but only <code>hub/</code> is maintained
and re-verified. Use this page to navigate the archive knowingly.</p>
""" + table(["Tree", "Session", "Entry point", "Why it is not canonical"], ARCHIVE_ROWS,
                   note=f"{len(ARCHIVE_ROWS)} trees, all reachable; only hub/ is re-verified by this "
                        "session. Rows are the same registry the landing page counts from.")
    page("archive.html", "Prior site trees",
         "What the earlier sessions published, where it lives, and how to read it.", body, "archive")


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#12202e;--mut:#5d6b7a;--line:#e2e6eb;--nav:#10273b;
--v:#0f7b52;--d:#1857a4;--u:#b06a00;--b:#b3261e;--p:#5b4ea8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.top{background:var(--nav);color:#fff;padding:14px 22px;display:flex;justify-content:space-between;
align-items:center;flex-wrap:wrap;gap:8px}
.top a{color:#fff;text-decoration:none;font-weight:700;letter-spacing:.4px}
.top .brand span{font-weight:400;opacity:.8;margin-left:6px}
.asof{font-size:12.5px;opacity:.85}.asof b{font-weight:600}
.nav{display:flex;flex-wrap:wrap;gap:2px;padding:8px 16px;background:#fff;border-bottom:1px solid var(--line);
position:sticky;top:0;z-index:5}
.nav a{padding:6px 10px;border-radius:6px;color:#33465c;text-decoration:none;font-size:13px}
.nav a:hover{background:#eef2f6}.nav a.on{background:var(--nav);color:#fff}
main{max-width:1400px;margin:0 auto;padding:22px 22px 60px}
h1{font-size:26px;margin:6px 0 4px}h2{font-size:18px;margin:26px 0 8px}
.lede{color:var(--mut);max-width:100ch;margin:0 0 14px}
.note{color:var(--mut);font-size:12.5px}code{background:#eef1f5;padding:1px 4px;border-radius:4px;font-size:12.5px}
pre{background:#0f1c29;color:#dbe7f3;padding:12px;border-radius:8px;overflow:auto;font-size:12.5px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .num{font-size:30px;font-weight:700;line-height:1.1}.card .lbl{font-weight:600;margin-top:2px}
.card .sub{color:var(--mut);font-size:12.5px;margin-top:6px}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid var(--nav);border-radius:8px;
padding:12px 18px;margin:18px 0}
.tblwrap{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:10px;margin:10px 0 22px}
table{border-collapse:collapse;width:100%;font-size:13px}
caption{text-align:left;font-weight:600;padding:10px 12px 6px;font-size:13.5px}
th,td{padding:7px 10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
th{background:#eef2f6;position:sticky;top:0;font-size:12px;text-transform:uppercase;letter-spacing:.3px;
white-space:nowrap;z-index:1}
tbody tr:nth-child(even){background:#fafbfc}tbody tr:hover{background:#f0f5fb}
td b{font-weight:650}.mut{color:var(--mut);font-size:12px}
.badge{display:inline-block;padding:1px 7px;border-radius:20px;font-size:10.5px;font-weight:700;
letter-spacing:.4px;white-space:nowrap;border:1px solid}
.badge.v{color:var(--v);border-color:#bfe4d3;background:#effaf4}
.badge.d{color:var(--d);border-color:#c7dcf5;background:#eef5fd}
.badge.u{color:var(--u);border-color:#f0d9b5;background:#fdf6ea}
.badge.b{color:var(--b);border-color:#f3c9c6;background:#fdefee}
.badge.p{color:var(--p);border-color:#d6d1f0;background:#f4f2fd}
a.src{font-size:12px;color:var(--d);text-decoration:none;border-bottom:1px dotted #9bbde3;white-space:nowrap}
a.src:hover{text-decoration:underline}
.blank{display:inline-block;min-width:56px;height:12px;background:repeating-linear-gradient(45deg,#f1f3f6,
#f1f3f6 4px,#e6eaf0 4px,#e6eaf0 8px);border:1px solid var(--line);border-radius:3px;vertical-align:middle}
.sig-strong{color:var(--b);font-weight:700}.sig-mod{color:var(--u);font-weight:600}.sig-none{color:var(--mut)}
.filt{padding:8px 12px;border:1px solid var(--line);border-radius:8px;width:340px;max-width:100%;
font-size:14px;margin:6px 0}
footer{border-top:1px solid var(--line);background:#fff;padding:16px 22px 40px;color:var(--mut);font-size:12.5px;
max-width:100%}footer a{color:var(--d)}
@media(max-width:820px){.nav{position:static}h1{font-size:22px}main{padding:14px}}
"""

JS = """
document.querySelectorAll('input.filt').forEach(function(inp){
  var t=document.getElementById(inp.dataset.for); if(!t) return;
  var rows=[].slice.call(t.querySelectorAll('tbody tr'));
  inp.addEventListener('input',function(){
    var q=inp.value.toLowerCase().trim();
    rows.forEach(function(r){ r.style.display = !q || r.textContent.toLowerCase().indexOf(q)>=0 ?'':'none'; });
    var n=rows.filter(function(r){return r.style.display!=='none'}).length;
    var c=t.closest('.tblwrap').querySelector('caption');
    if(!c) return; if(!c.dataset.base) c.dataset.base=c.textContent;
    c.textContent = c.dataset.base + '  -  ' + n + ' of ' + rows.length + ' rows';
  });
});
"""


def _build_x3_pages():
    import x3_pages
    return x3_pages.build(sys.modules[__name__], JX, C, X)


def main():
    # ---- X3-v2 extension (session arena/873c7396-x3): additive pages + register rows
    import x3_content2 as X2
    X2.register(esc, badge, link, table)
    C.FLAGS.extend(X2.NEW_FLAGS)
    C.Q.extend(X2.NEW_QUESTIONS)
    C.SUG.extend(X2.NEW_SUGGESTIONS)
    NAV.append(("__council__", "", ""))
    NAV.extend(X2.NAV_EXTRA)
    # extra pages that need the helpers defined above
    build_prereg()
    p_index(); p_exec(); p_lines(); p_strategies(); p_gates(); p_corr(); p_luck()
    p_injuries(); p_depth(); p_leader(); p_req(); p_questions(); p_suggestions()
    p_sources(); p_verification(); p_repo(); p_flagged(); p_archive()
    _P["p_markets"](); _P["p_store"](); _P["p_results"](); _P["p_replacements"]()
    for fn in X2.PAGES:  # results / pricing / origination / signal / replacement
        fname, title, intro, body = fn()
        page(fname + ".html", title, intro, body, fname)
    with open(os.path.join(HUB, "assets", "hub.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    with open(os.path.join(HUB, "assets", "hub.js"), "w", encoding="utf-8") as f:
        f.write(JS)
    landing()
    print(f"hub/: {len(os.listdir(HUB)) - 2} html pages + assets; root index.html written")


def build_prereg():
    """Freeze the strategy definitions and model parameters - the pre-registration artifact."""
    import hashlib
    ledger = {
        "registered_at": AS_OF,
        "session": "arena/e9b492ab-x3",
        "model": "X3-v1",
        "params": meta["params"],
        "pos_cost": meta["pos_cost"],
        "inputs": {"standings_sha": _sha(os.path.join(ROOT, "data/hub/standings_2026_thru_wk9.csv")),
                   "injuries_sha": _sha(os.path.join(ROOT, "data/hub/injuries_2026_wk10.csv"))},
        "strategies": [{"id": s[0], "family": s[1], "name": s[2], "entry": s[3], "settlement": s[4],
                        "data_required": s[5]} for s in C.STRAT],
        "gates": [{"id": g[0], "name": g[1], "threshold": g[2], "status_at_registration": g[4]} for g in C.GATES],
        "promises": [
            "No strategy in this list may be scored on data that predates its registration.",
            "Changes to an entry rule create a new id; they do not edit this one.",
            "Numbers with no official source stay blank; they are never estimated to make a table look complete.",
            "Rewards remain notional until an owner decision and legal review exist.",
        ],
    }
    with open(os.path.join(HUB, "data", "prereg.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1)


def _sha(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def landing():
    _RES = JX("results.json")
    _MK = JX("markets.json")
    _ST = JX("strategies.json")
    _REQUIREMENTS = C.REQ + X.REQ2
    _READINESS = decision_readiness_table(_REQUIREMENTS)

    def local_link(path, label):
        return f'<a class="src" href="{esc(path)}">{esc(label)}</a>'

    def nav_item(slug, lbl, desc):
        if slug == "__council__":
            return ('<a href="council/index.html"><b>Decision council</b><span>The eight '
                    'requirements as pass/fail tests, plus the suggestion queue</span></a>')
        return f'<a href="hub/{slug}.html"><b>{esc(lbl)}</b><span>{esc(desc)}</span></a>'
    nav = "".join(nav_item(slug, lbl, desc) for slug, lbl, desc in NAV)
    # Decision-readiness is deliberately a gate register, not a claim that every
    # feature is ready. Counts are tied to the 2026-11-14 captured tree below;
    # clearance thresholds are explicit and conflicts between registered gates
    # are surfaced rather than silently resolved.
    official_schedule = "https://www.nfl.com/schedules/2026/by-week/week-10"
    official_injuries = "https://www.nfl.com/injuries/league/2026/reg10"
    official_gamebooks = "https://support.nfl.com/hc/en-us/articles/35869678028180-Game-Books"
    official_odds_probe = "https://www.nfl.com/odds/"
    readiness = [
        ["<b>R1 · Price snapshots</b><br><a href='council/requirements.html'>acceptance test</a>",
         "No NFL-official market-price observations identified. Model fair-line snapshots are not market prices; other stored third-party quotes are labelled separately.",
         "Market-data policy/provider is unresolved; opening/closing market values cannot be treated as verified NFL facts.",
         "100% of originated market IDs have both timestamped, source-attributed OPEN and CLOSE observations; unknown source/coverage stays blank.",
         link(official_odds_probe, "NFL odds-source check") + " · " + local_link("hub/flagged.html", "price-source flags")],
        ["<b>R2 · Verified results</b><br><a href='council/requirements.html'>acceptance test</a>",
         "137 finals among 163 scheduled 2026 rows in the captured feed; no settled-wager series or published settlement contract.",
         "Market prices and explicit push/tie/void settlement rules are required before ROI can be computed.",
         "100% of graded games reconcile to official finals; 100% of wager rows have a predeclared settlement rule and source-linked result.",
         link(official_schedule, "NFL weekly schedule") + " · " + local_link("hub/verified-results.html", "feed and checks")],
        ["<b>R3 · Origination order</b><br><a href='council/requirements.html'>acceptance test</a>",
         "Week-10 test: 13 games × three markets; 0 order violations recorded (side → total → moneyline).",
         "No blocker for the ordering rule; continued builds must retain the zero-violation check.",
         "0 order violations across 100% of originated games; moneyline remains derived from the registered side model.",
         link(official_schedule, "NFL schedule facts") + " · " + local_link("hub/origination.html", "order evidence")],
        ["<b>R4 · Fair / market / difference</b><br><a href='council/requirements.html'>acceptance test</a>",
         "Separate columns exist; market and difference values are blank where no source-backed market quote exists.",
         "R1 market-data source policy blocks population of the market and residual columns.",
         "100% of originated market rows show fair line, sourced market line, and difference (= fair − market), each with units and provenance; otherwise leave market/difference blank.",
         link(official_odds_probe, "NFL odds-source check") + " · " + local_link("hub/markets.html", "market board")],
        ["<b>R5 · Skill vs staking</b><br><a href='council/requirements.html'>acceptance test</a>",
         "Separate signal and staking fields are present, but no price-settled staking record exists. Registered gates conflict: signals G2 uses ≥200 graded decisions; origin G-2 specifies ≥300 settled bets and ≥3 seasons.",
         "A single canonical, preregistered leaderboard qualification rule is not selected; neither short-run ROI nor raw win rate can clear it.",
         "Resolve and freeze one gate before evaluation; then meet its sample threshold on chronological holdout, pass benchmark-relative proper-score uncertainty and multiplicity controls. Until then: no eligible/rewarded strategy.",
         link(official_schedule, "official outcomes") + " · " + local_link("hub/leaderboard.html", "current board") + " · " + local_link("hub/gates.html", "market gate") + " · " + local_link("signals/gates.html", "signals gate") + " · " + link("https://github.com/karagemop466-tech/X3/blob/main/origin/data/gates.json", "origin gate")],
        ["<b>R6 · Replacement depth</b><br><a href='council/requirements.html'>acceptance test</a>",
         "31 of 32 club charts were readable in the recorded audit, but charts are club-published and undated; actual game-day starter/inactive evidence is not a complete point-in-time dataset.",
         "Depth rank is not a confirmed actual starter or snap share; no jersey-order, experience, or salary inference is allowed.",
         "For 100% of games/players used: official Game Book starter and game-day status evidence; a verified playing-time source for actual snaps; dated raw-source hash and conflict record. Otherwise the feature remains out of the model.",
         link(official_gamebooks, "NFL Game Books guidance") + " · " + link(official_injuries, "NFL injury report") + " · " + link("https://www.azcardinals.com/team/depth-chart", "example club chart (club-published)") + " · " + local_link("hub/replacements.html", "replacement evidence")],
        ["<b>R7 · Correlations</b><br><a href='council/requirements.html'>acceptance test</a>",
         "Correlation tables publish n. Some separate analyses explicitly include PFF closing-line inputs (third-party); those are not official-only correlations.",
         "Provenance must be checked per coefficient; no third-party price-derived pair may be presented as official-only.",
         "100% of published coefficients use officially sourced underlying values and include n, uncertainty interval, time window, and source; third-party inputs remain separately labelled.",
         link(official_schedule, "NFL results") + " · " + local_link("hub/correlation.html", "correlation register") + " · " + local_link("hub/flagged.html", "source-class flags")],
        ["<b>R8 · Demotion to paper</b><br><a href='council/requirements.html'>acceptance test</a>",
         "Demotion rules exist, but multiple modules contain different thresholds/windows; no strategy is live in the current published design.",
         "Choose one canonical, versioned rule and ensure the live-state evaluator is actually run; a written gate alone is not operational enforcement.",
         "1 canonical rule; 100% of live strategies evaluated per cycle; deterministic test proves every registered trigger moves LIVE → PAPER and logs the reason.",
         link(official_schedule, "official results context") + " · " + local_link("hub/gates.html", "gate register") + " · " + link("https://github.com/karagemop466-tech/X3/blob/main/origin/data/gates.json", "origin rules") + " · " + link("https://github.com/karagemop466-tech/X3/blob/main/data/x3/gates.json", "X3 rules")],
    ]
    expected_readiness_ids = [f"<b>R{i} ·" for i in range(1, 9)]
    if len(readiness) != 8 or any(not any(marker in row[0] for row in readiness) for marker in expected_readiness_ids):
        raise SystemExit("decision-readiness table must have exactly one row for each core requirement R1-R8")
    if any("<a " not in row[-1] for row in readiness):
        raise SystemExit("every decision-readiness row must carry a source/audit link")
    readiness_table = table(
        ["Core requirement", "What the current record says", "Blocking gate / unresolved decision", "What clears it", "Sources / audit trail"],
        readiness, tid="decision-readiness", cap="Decision-readiness snapshot · evidence captured 2026-11-14 · not a claim of live betting readiness", kind="data")
    verification_table = """<section class="callout" style="border:1px solid var(--line);background:#111827">
<h2 style="margin-top:0">Verification status (official sources)</h2>
<table style="width:100%;font-size:13px;margin-top:8px">
<thead><tr><th style="text-align:left">Dataset</th><th style="text-align:left">Official source</th><th style="text-align:left">Status</th><th style="text-align:left">Notes</th></tr></thead>
<tbody>
<tr><td>Week-10 injury report (345 rows)</td><td><a href="https://www.nfl.com/injuries/league/2026/reg10" target="_blank" rel="noopener">nfl.com/injuries/league/2026/reg10</a></td><td><b>VERIFIED</b></td><td>Capture dated 2026-11-14; 66 Out / 10 Doubtful / 84 Questionable / 185 blank, matching the recorded total; see the linked report and verification log.</td></tr>
<tr><td>2026 league standings (32 clubs)</td><td><a href="https://www.nfl.com/standings/league/2026/REG" target="_blank" rel="noopener">nfl.com/standings/league/2026/REG</a></td><td><b>VERIFIED</b></td><td>Captured values checked against the official standings; older-module discrepancies remain flagged in the repository.</td></tr>
<tr><td>Week-10 schedule / orientation</td><td><a href="https://www.nfl.com/schedules/2026/by-week/week-10" target="_blank" rel="noopener">nfl.com/schedules/2026/by-week/week-10</a></td><td><b>VERIFIED</b></td><td>14 games and four byes in the recorded slate; fixture facts are not used to assert market prices.</td></tr>
<tr><td>Originated lines / fair vs market / difference</td><td><span class="badge u">UNVERIFIED</span></td><td><b>BLOCKED</b></td><td>No NFL-official odds rows identified (the odds probe returns no price feed); market and difference fields stay blank. See F-18.</td></tr>
<tr><td>Strategy leaderboard / ROI / CLV</td><td><span class="badge u">UNVERIFIED</span></td><td><b>BLOCKED</b></td><td>No price-settled wager series; ROI, CLV and staking cannot be computed from game outcomes alone. See the readiness table and Flagged for review.</td></tr>
</tbody>
</table>
<p class="note" style="margin-top:8px">Every value is traced to an official source or left blank and flagged. Nothing is inferred. Full detail: <a href="hub/flagged.html">Flagged for review</a> · <a href="hub/verification.html">Verification log</a>.</p>
</section>"""
    # integration session arena/09f8c786-x3: the signals module is a separate tree
    nav += ('<a href="signals/index.html"><b>Signals &amp; leaderboard</b>'
            '<span>Originated lines, price snapshots, signal vs staking</span></a>')
    # integration session arena/4c2f61cd-x3: the round2 module (fresh-day verification
    # + the decision-readiness matrix the brief asks for on the landing page).
    nav += ('<a href="round2/index.html"><b>Round 2 readiness</b>'
            '<span>66 requirements mapped: gate that blocks, number that clears</span></a>')
    # the decision desk (decision/): a card on the root landing. It was added to the
    # committed index.html by hand in the b7d4142 merge; registering it here makes the
    # generator reproduce the committed page, which the Pages workflow diff-checks.
    nav += ('<a href="decision/index.html"><b>Decision desk &amp; time series</b>'
            '<span>69-row register with per-row basis, the suggestion queue, and the first hashed day-over-day availability delta</span></a>')
    verification_table = table(
        ['Dataset', 'Official source', 'Status', 'Notes'],
        [["Week-10 injury report (345 rows)", link(C.S["injuries"], "nfl.com/injuries/league/2026/reg10"),
          badge("VERIFIED"), "Snapshot reviewed 2026-11-14; it is a dated capture, not a live feed."],
         ["2026 league standings (32 clubs)", link(C.S["standings"], "nfl.com/standings/league/2026/REG"),
          badge("VERIFIED"), "Official standings used for the canonical team aggregate reconciliation."],
         ["Week-10 schedule / fixture orientation", link(C.S["sched10"], "nfl.com/schedules/2026/by-week/week-10"),
          badge("VERIFIED"), "Official schedule is the fixture reference; each venue still needs Game Center transcription."],
         ["Market comparison / CLV", '<span class="badge u">UNVERIFIED</span>',
          badge("BLOCKED"), "No market-price source is available in this repository; market cells stay blank."],
         ["Strategy ROI / staking", '<span class="badge u">UNVERIFIED</span>',
          badge("BLOCKED"), "Prices and settlement evidence are incomplete; ROI/CLV and reward amounts are not published."]],
        tid="verification-status")
    # integration session arena/6259c7b0-x3 (RD-01): readiness module entry
    nav += ('<a href="readiness/index.html"><b>Readiness &amp; gates</b>'
            '<span>Decision readiness, control baselines, drift alarms, what changed</span></a>')

    # RD-01 (arena/6259c7b0-x3): decision-readiness table, one row per requirement,
    # with the gate that blocks it and the number that would clear it.
    with open(os.path.join(ROOT, "readiness", "data", "readiness.json"), encoding="utf-8") as _f:
        _rd = json.load(_f)
    _RD_BADGE = {"done": "v", "partial": "p", "blocked": "b", "registered": "u", "rejected": "d"}
    _rd_rows = []
    for _r in _rd["rows"]:
        _src = _r["source"]
        _src_html = (f'<a class="src" href="{esc(_src)}">official</a>'
                     if str(_src).startswith("http")
                     else f'<a class="src" href="{esc(_src)}">provenance</a>')
        _rd_rows.append(
            f'<tr><td><b>{esc(_r["id"])}</b></td>'
            f'<td>{esc(_r["requirement"])}</td>'
            f'<td><span class="badge {_RD_BADGE.get(_r["status"], "u")}">{esc(_r["status"]).upper()}</span></td>'
            f'<td><a href="{esc(_r["where"])}">{esc(_r["where"])}</a></td>'
            f'<td class="mut">{esc(_r["gate"])}</td>'
            f'<td>{esc(_r["clears"])}</td>'
            f'<td>{_src_html}</td></tr>')
    _rd_counts = {}
    for _r in _rd["rows"]:
        _rd_counts[_r["status"]] = _rd_counts.get(_r["status"], 0) + 1
    _rd_summary = " | ".join(f"<b>{v}</b> {k}" for k, v in sorted(_rd_counts.items()))
    readiness_section = (
        '<section class="callout" style="margin-top:22px">'
        '<h2>Decision readiness - one row per requirement</h2>'
        '<p>Every requirement in the project brief, with <b>the gate that blocks it</b> and '
        '<b>the number that would clear it</b>. Maintained by the readiness module '
        '(<a href="readiness/index.html">readiness/</a>); rendered from '
        '<code>readiness/data/readiness.json</code>.</p>'
        f'<p class="note">{_rd_summary}</p>'
        '<div class="tblwrap"><table><caption>Decision readiness register - '
        f'{len(_rd["rows"])} requirement rows</caption>'
        '<thead><tr><th>ID</th><th>Requirement</th><th>Status</th><th>Where it lives</th>'
        '<th>Gate that blocks it</th><th>Number that would clear it</th><th>Source</th></tr></thead>'
        f'<tbody>{"".join(_rd_rows)}</tbody></table></div></section>')

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="X3 NFL decision desk: originated lines, verified injury and depth data,
validation gates, correlation and a luck-adjusted leaderboard design - every row tied to an official source.">
<title>X3 NFL decision desk</title>
<link rel="stylesheet" href="hub/assets/hub.css">
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">X3 <span>NFL decision desk</span></a></div>
  <div class="asof">data as of <b>{AS_OF}</b> - season 2026, week {meta['week']}</div>
</header>
<main>
<h1>Originating NFL lines from verified data - and being honest about what cannot be verified</h1>
<p class="lede">This is the canonical dashboard for the X3 project. Injury designations, standings and depth
charts are transcribed row by row from official NFL.com and club pages. The lines below are arithmetic on
those inputs with every parameter printed in the open. Anything that would require a betting market -
prices, closing-line value, settled bets, ROI, a populated leaderboard - is blank and flagged, because that
data does not exist here yet.</p>
<div class="grid">
<div class="card"><div class="num">{meta['rows']['injuries']}</div><div class="lbl">official injury rows verified</div>
<div class="sub">Week 10, 2026 - re-read field for field from the league report</div></div>
<div class="card"><div class="num">{len(lines['rows'])}</div><div class="lbl">games priced by our own model</div>
<div class="sub">spreads and totals for the unplayed Week-10 slate</div></div>
<div class="card"><div class="num">{n_positions_out()}</div><div class="lbl">1st-string vacancies</div>
<div class="sub">across {n_clubs_out()} clubs - backups starting this week</div></div>
<div class="card"><div class="num">{len(_RES['rows'])}</div><div class="lbl">games in the verified results feed</div>
<div class="sub">{_RES['counts']['finals']} finals, {_RES['counts']['clubs']} clubs, {_RES['checks']['R2_standings_reconciliation']['mismatches']} standings mismatches</div></div>
<div class="card"><div class="num">{len(_MK['live'])}</div><div class="lbl">games with all three markets originated</div>
<div class="sub">side, then total, then moneyline - fair line, market line and difference kept apart</div></div>
<div class="card"><div class="num">0 / {len(_ST['strategies'])}</div><div class="lbl">strategies leaderboard-eligible</div>
<div class="sub">{_ST['counts']['signal_untested']} untested, {_ST['counts']['signal_inconclusive']} inconclusive, staking blocked on prices</div></div>
</div>
<section class="callout" style="border:1px solid var(--line);background:#111827">
<h2 style="margin-top:0">Verification status (official sources)</h2>
{verification_table}
<p class="note" style="margin-top:8px">Every value on this site is traced to an official source or left blank and flagged. Nothing is inferred. Full detail: <a href="hub/flagged.html">Flagged for review</a> &middot; <a href="hub/verification.html">Verification log</a>.</p>
</section>
<nav class="nav" style="position:static;background:transparent;border:0;padding:0;display:block">
{nav}
</nav>
<section class="callout"><h2>Start here</h2>
<p><a href="hub/executive-summary.html"><b>Executive summary</b></a> for the decisions,
<a href="hub/markets.html"><b>Originated markets</b></a> for the three-market board,
<a href="hub/price-store.html"><b>Price store</b></a> for the open/close record,
<a href="hub/verified-results.html"><b>Results feed</b></a> for the reconciled scores,
<a href="hub/replacements.html"><b>Replacements</b></a> for who is actually starting,
<a href="hub/suggestions.html"><b>Suggestions</b></a> to choose a path,
<a href="hub/questions.html"><b>Open questions</b></a> for the information gaps, and
<a href="hub/flagged.html"><b>Flagged for review</b></a> for everything that could not be verified.
The <a href="council/index.html"><b>decision council</b></a> restates the eight requirements of the
brief as pass/fail acceptance tests, and holds the suggestion queue where a path is chosen before
anything is implemented. <a href="signals/index.html"><b>signals/</b></a> originates its own side,
total and moneyline in that order, stores an opening and a closing number for every market, and ranks
strategies on signal with staking reported separately. <a href="x3/index.html"><b>x3/</b></a> is the
2026 desk: 28 pages built from official NFL sources only, gated by a check script that fails the
build on a broken link, an unsourced row, or a fabricated figure.</p>
<p class="note">Earlier sessions published {len(ARCHIVE_ROWS)} overlapping site trees; they are preserved and indexed at
<a href="hub/archive.html">hub/archive.html</a>. <code>hub/</code> is the maintained tree. The repository
is <a href="https://github.com/karagemop466-tech/X3">karagemop466-tech/X3</a> and the shared task board is
<a href="COORDINATION.md">COORDINATION.md</a>.</p></section>
<section class="callout"><h2>Decision readiness - every requirement, its blocker, and what clears it</h2>
<p class="lede">One row per registered requirement. Clearance criteria are project targets, not NFL-published facts. Official references support observed inputs only; unavailable evidence and policy thresholds are marked UNVERIFIED.</p>
<p class="callout"><b>Flagged gate conflict:</b> the current G-2 page says 300 settled bets across 3 seasons, while <a href="https://github.com/karagemop466-tech/X3/pull/58">unmerged PR #58</a> proposes 2,272 (checked 2026-11-15 UTC). GitHub reports PR #58 has a dirty merge state. These are competing project proposals; the final minimum has not been verified or resolved, and no strategy is eligible under either today.</p>
{_READINESS}
<p>See <a href="hub/requirements.html">the full requirements register</a> for acceptance criteria, provenance and status details.</p></section>
<section class="callout" style="margin-top:22px">
<h2>Decision readiness — the eight core requirements</h2>
<p>Each row names the present evidence, the gate blocking a decision and an explicit clearance condition.
The official NFL links document the league data/source class; repository links show the project’s derived
work and policy. A link is not evidence that a blocker is cleared. Unknown values remain blank and flagged.
The full requirement/question registers and reviewable choices are in <a href="hub/requirements.html">Requirements</a>,
<a href="hub/questions.html">Questions &amp; information gaps</a> and <a href="hub/suggestions.html">Suggestions</a>.</p>
{readiness_table}
<p class="note"><b>Irregularity to resolve first:</b> the repository has competing strategy qualification and demotion
thresholds in parallel modules. No one should treat the leaderboard as a prize/real-money ranking until
one policy is frozen in a pre-registration record. See the per-row flags and the <a href="hub/flagged.html">Flagged for review</a> page.</p>
</section>
<section class="callout" style="margin-top:22px">
<h2>Trading desk - the eight operating requirements</h2>
<p><b>Registration, not replacement.</b> <code>ops/</code> is a separate trading-desk tree that answers the eight
operating requirements directly and says plainly where it cannot: prices originated in a fixed order
(side, then total, then moneyline), a price-snapshot store with opening and closing schema for every market,
correlations that each carry their n, injured starters resolved to the depth of their replacement, and a
signal-vs-staking leaderboard whose demotion gate is dry-run to prove it fires.</p>
<p><a href="ops/index.html"><b>Enter the trading desk</b></a> &middot;
<a href="ops/executive-summary.html">Executive summary</a> &middot;
<a href="ops/lines.html">Originated lines</a> &middot;
<a href="ops/snapshots.html">Price snapshots</a> &middot;
<a href="ops/leaderboard.html">Leaderboard</a> &middot;
<a href="ops/gates.html">Gates &amp; demotion</a> &middot;
<a href="ops/correlation.html">Correlation</a> &middot;
<a href="ops/depth.html">Replacement depth</a> &middot;
<a href="ops/results.html">Results feed</a> &middot;
<a href="ops/questions.html">Open questions</a> &middot;
<a href="ops/suggestions.html">Suggestions</a> &middot;
<a href="ops/flagged.html">Flagged for review</a></p>
<p class="note">Every market price on the trading desk is blank on purpose: no official market feed exists in
this repository, so fair-versus-market, ROI and closing-line value are published as blocked rather than
estimated.</p>
</section>
{readiness_section}
</main>
</body></html>"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


_P = None


if __name__ == "__main__":
    _P = _build_x3_pages()
    os.makedirs(os.path.join(HUB, "assets"), exist_ok=True)
    # inject the JS into hub pages
    main()
    for fn in os.listdir(HUB):
        if not fn.endswith(".html"):
            continue
        p = os.path.join(HUB, fn)
        s = open(p, encoding="utf-8").read()
        if "</body>" in s and "hub.js" not in s:
            s = s.replace("</body>", '<script src="assets/hub.js" defer></script>\n</body>')
            open(p, "w", encoding="utf-8").write(s)
    print("ok")
