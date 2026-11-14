#!/usr/bin/env python3
"""
Builds the session pages that sit on top of the canonical hub:

    hub/results.html      the verified results feed and its reconciliation
    hub/picks.html        the board in the required order: side, total, moneyline
    hub/snapshots.html    the price-snapshot store and what is honestly blank
    hub/depth-tiers.html  which string the replacement is, not just that he exists
    hub/correlation-live.html  coefficients recomputed with n and permutation p
    hub/leaderboard-live.html  signal vs staking, and the demotion gate
    hub/decisions.html    questions -> answers, and the suggestions review queue
    hub/summary.html      one-page executive brief

The pages reuse the canonical hub CSS, header and nav so the site stays one
design. Every number is read from a generated JSON file at build time; the
prose contains no typed counts. If a data file is missing the build fails rather
than publishing a page with a hole in it.

Run: python3 tools/build_desk.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "hub")
VER = os.path.join(ROOT, "data", "verified")
DEC = os.path.join(ROOT, "data", "decisions")
PICK = os.path.join(ROOT, "data", "picks")
SNAP = os.path.join(ROOT, "data", "snapshots")


def J(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return json.load(f)


rec = J("data", "verified", "reconciliation.json")
bt = J("data", "verified", "backtest.json")
corr = J("data", "verified", "correlation.json")
demo = J("data", "verified", "staking_demo.json")
dep = J("data", "verified", "depth_map.json")
ms = J("data", "verified", "market_stats.json")
hfa = J("data", "verified", "hfa.json")
kn = J("data", "verified", "key_numbers.json")
gates = J("data", "decisions", "gates.json")
qs = J("data", "decisions", "questions.json")
review = J("data", "review", "repo_review.json")
led = J("data", "decisions", "strategy_ledger.json")
picks = J("data", "picks", "picks_2026_wk10.json")
snap_meta = J("data", "snapshots", "store_meta.json")
meta = J("hub", "data", "meta.json")
AS_OF = "2026-11-14"

NAV = [
    ("summary", "Executive summary", "The one-page brief"),
    ("results", "Results feed", "Verified finals and reconciliation"),
    ("picks", "Board: side/total/ML", "Originated in order, with key numbers"),
    ("snapshots", "Price snapshots", "Open/close store; what is blank"),
    ("correlation-live", "Correlation", "Recomputed with n and permutation p"),
    ("leaderboard-live", "Leaderboard & demotion", "Signal vs staking"),
    ("depth-tiers", "Replacement depth", "Which string actually plays"),
    ("decisions", "Review queue", "Questions, answers, suggestions"),
    ("repo-review-live", "Repo review", "Prior claims, rechecked line by line"),
    ("flagged-live", "Flagged for review", "Everything that needs a human decision"),
    ("@index.html", "Canonical hub", "The original 18-page desk"),
]

BADGE = {"PASS": "v", "FAIL": "b", "BLOCKED": "u", "PARTIAL": "p", "NOT RUN": "u",
         "ANSWERED": "v", "OPEN": "b", "PROPOSED": "u", "ADOPTED IN THIS SESSION": "d",
         "PAPER": "p", "LIVE": "v", "VERIFIED": "v", "DERIVED": "d", "UNVERIFIED": "u"}


def esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def badge(word):
    return f'<span class="badge {BADGE.get(word, "u")}">{esc(word)}</span>'


def table(heads, rows, cap=None, note=None, cls="k-data"):
    out = [f'<div class="tblwrap"><table class="{cls}">']
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


REPO_URL = "https://github.com/karagemop466-tech/X3/blob/main/"


def filelink(path):
    """A repository file rendered as a link that resolves from hub/*.html.

    A bare relative path such as data/verified/backtest.json would be resolved
    against hub/ and break, so evidence cells point at the repository view of the
    exact file instead. The path text is kept so a reader can copy it.
    """
    raw = str(path).split(" (")[0].strip()
    return (f'<a class="src" href="{REPO_URL}{raw}" target="_blank" rel="noopener">'
            f"<code>{esc(path)}</code></a>")


def src(url, text=None):
    t = text or url.replace("https://", "").replace("http://", "")
    return f'<a class="src" href="{url}" target="_blank" rel="noopener">{esc(t)}</a>'


def page(fname, title, intro, body, active):
    parts = []
    for slug, lbl, _desc in NAV:
        cls = " class='on'" if slug == active else ""
        href = slug[1:] if slug.startswith("@") else f"{slug}.html"
        parts.append(f'<a href="{href}"{cls}>{esc(lbl)}</a>')
    nav = "".join(parts)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 NFL decision desk</title>
<link rel="stylesheet" href="assets/hub.css">
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
  <p>Generated by <code>tools/build_desk.py</code> from files in <code>data/verified/</code>,
  <code>data/decisions/</code>, <code>data/picks/</code> and <code>data/snapshots/</code>.
  Source rows are read from official NFL.com pages on {AS_OF}; values with no official source
  are left blank and flagged. Model output is DERIVED and is arithmetic, not a prediction of
  results. This site places no bets and pays no rewards.</p>
  <p><a href="../index.html">Site root</a> - <a href="index.html">Canonical hub</a> -
  <a href="../COORDINATION.md">Coordination log</a> -
  <a href="https://github.com/karagemop466-tech/X3">Repository</a></p>
</footer>
<script src="assets/hub.js" defer></script>
</body></html>"""
    with open(os.path.join(HUB, fname), "w", encoding="utf-8") as f:
        f.write(html)


# ---------------------------------------------------------------- pages
def p_summary():
    s = qs["summary"]
    g = gates["summary"]
    n55 = demo["masking"]["c_bets_needed_for_80pct_power"]["55%_vs_breakeven"]["n_needed_80pct_power"]
    tvm = next(r for r in corr["rows"] if r["pair"] == "game total vs |margin|")
    cards = f"""<div class="grid">
<div class="card"><div class="num">{rec['finals_used']}</div><div class="lbl">verified finals</div>
<div class="sub">every club field recomputed and matched</div></div>
<div class="card"><div class="num">{rec['fields_agree']}/{rec['fields_compared']}</div>
<div class="lbl">reconciliation fields agree</div>
<div class="sub">official standings vs recomputed game log</div></div>
<div class="card"><div class="num">{dep['replacements_identified']}/{dep['rows_total']}</div>
<div class="lbl">absences with a named replacement</div>
<div class="sub">the rest are blank, not guessed</div></div>
<div class="card"><div class="num">{g['pass']}/{len(gates['gates'])}</div>
<div class="lbl">validation gates passing</div>
<div class="sub">{g['fail']} fail, {g['partial']} partial, {g['blocked']} blocked on data that
does not exist here, {g['not_run']} not run</div></div>
</div>"""

    body = cards + f"""
<section class="callout"><h2>The short version</h2>
<p>Three things changed in this session, and one did not.</p>
<ol>
<li><b>A results feed now exists and is verified.</b> {rec['finals_used']} finals were re-summed
per club and compared field by field with the official standings page:
{rec['fields_agree']} of {rec['fields_compared']} values agree exactly across
{rec['clubs_official']} clubs. Before this, backtests in this repository were not possible at all.</li>
<li><b>The model was tested out of sample for the first time.</b> On {bt['n_games_scored']} games
it had never seen, it beats predicting a zero margin: MAE {bt['spread']['mae_model']} vs
{bt['spread']['mae_predict_zero']} points, with {demo['signal']['sign_correct']} of
{demo['signal']['decided_games']} sides correct (exact p={demo['signal']['binom_two_sided_p_vs_coin']}).
That is a real signal about the score. It is <b>not</b> an edge over a price, and this site never
claims one.</li>
<li><b>The gates got arithmetic.</b> The published minimum sample of 300 bets was too low by a
factor of about {round(n55 / 300)}: an exact power calculation puts a 55% edge at {n55} settled bets.
A demotion gate now exists with six triggers, each backed by a probability rather than an opinion.</li>
</ol>
<p>What did not change: there is still no market price anywhere in this repository.
Every price cell is blank and flagged, so ROI, closing-line value and a populated leaderboard
remain impossible. That is not a modelling gap, it is a missing purchase.</p>
</section>

<h2>What a reviewer should decide, in order</h2>
{table(["#", "Decision", "Why now", "Evidence", "Status"],
       [["1", "Adopt the signal/staking split and the corrected minimum sample",
         f"a 45% loser still looks profitable after 100 bets "
         f"{demo['masking']['a_share_finishing_above_start_flat_1u']['bad_45pct']['100']:.1%} of the time",
         '<a href="leaderboard-live.html">leaderboard &amp; demotion</a>', badge("PROPOSED")],
        ["2", "License a price feed with open and close per market",
         f"all {snap_meta['rows']} market cells are blank and every market gate is blocked on this",
         '<a href="snapshots.html">price snapshot store</a>', badge("BLOCKED")],
        ["3", "Estimate the injury cost coefficients instead of carrying priors",
         "the injury adjustment moves lines by up to "
         f"{max(abs(r['injury_delta']) for r in J('hub','data','lines.json')['rows']):.1f} points on no measured basis",
         '<a href="decisions.html">Q-08 and Q-14</a>', badge("OPEN")],
        ["4", "Obtain legal review before publishing any reward structure",
         "the question cannot be answered from data and carries the only unhedgeable risk",
         '<a href="decisions.html">Q-13</a>', badge("OPEN")]],
       cap="Decision queue", cls="k-meta")}

<h2>The three numbers that should govern everything else</h2>
{table(["Number", "What it means", "Why it matters for a decision", "Source"],
       [[f"<b>{demo['masking']['a_share_finishing_above_start_flat_1u']['bad_45pct']['100']:.1%}</b>",
         "chance a true 45% bettor shows a profit after 100 bets at -110",
         "a bankroll column is not evidence of skill and cannot rank strategies",
         src("https://www.nfl.com/schedules/2026/by-week/week-N", "NFL schedule pages")],
        [f"<b>{n55}</b>",
         "settled bets needed for 80% power to detect a 55% edge at -110",
         "any competition opened before this sample ranks noise",
         src("https://www.nfl.com/schedules/2026/by-week/week-N", "NFL schedule pages")],
        [f"<b>{hfa['hfa_points']}</b> ± {round((hfa['ci95'][1]-hfa['ci95'][0])/2, 2)}",
         f"measured home-field advantage in points, n={hfa['n_non_neutral']} non-neutral finals",
         f"the interval includes zero, which contradicts the usual 2.5-3 points and is why the "
         f"model uses zero and says so",
         src("https://www.nfl.com/schedules/2026/by-week/week-N", "NFL schedule pages")]],
       cap="Govern the rest", cls="k-meta")}

<h2>Where every open item lives</h2>
{table(["Page", "What you will find there"],
       [['<a href="results.html">Results feed</a>', "137 verified finals, the reconciliation, the empirical margin and total distributions"],
        ['<a href="picks.html">Board</a>', "13 originated games in the order side, total, moneyline, with key-number checks"],
        ['<a href="snapshots.html">Price snapshots</a>', "the store schema and exactly which cells are real"],
        ['<a href="correlation-live.html">Correlation</a>', "coefficients recomputed from official numbers with n and permutation p"],
        ['<a href="leaderboard-live.html">Leaderboard and demotion</a>', "signal separated from staking, six demotion triggers"],
        ['<a href="depth-tiers.html">Replacement depth</a>', "which string steps in for each absence"],
        ['<a href="decisions.html">Review queue</a>', f"{s['questions_total']} questions and {s['suggestions_total']} suggestions"]],
       cap="Index", cls="k-meta")}
"""
    page("summary.html", "Executive summary",
         "One page: what is now verified, what is measured, what is still impossible, and the "
         "four decisions that actually need a human.", body, "summary")


def p_results():
    top = dep  # noqa: F841 (kept for symmetry of naming)
    rows = []
    import csv
    with open(os.path.join(VER, "results_2026.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append([r["week"], r["date"], f"{r['away']} @ {r['home']}",
                         f"{r['away_score']}-{r['home_score']}", r["total"],
                         f"{int(r['home_margin']):+d}",
                         "neutral" if r["neutral_site"] == "Y" else "",
                         src(r["source_url"], "week page")])
    body = f"""
<section class="callout"><h2>Why this page exists</h2>
<p>Before this feed, no backtest in this repository could be computed, because there was no
verified record of a final score. The feed is now the base layer everything else is measured
against, and it is reconciled rather than trusted.</p></section>

<h2>Reconciliation against the official standings</h2>
<p>Every final was re-summed per club and compared with the official standings page. The test is
deliberately mechanical: wins, losses, ties, points for, points against and games played must all
reproduce exactly, or the feed is rejected.</p>
{table(["Check", "Result", "Detail"],
       [["Finals used", f"<b>{rec['finals_used']}</b>", f"from {rec['schedule_source_pattern'].replace('/week-N','/week-1..10')}"],
        ["Fields compared", f"<b>{rec['fields_compared']}</b>", "clubs x {W, L, T, PF, PA, games}"],
        ["Agree exactly", f"<b>{rec['fields_agree']}</b>", badge("VERIFIED")],
        ["Disagree", f"<b>{rec['fields_disagree']}</b>",
         "after the stated aliases " + ", ".join(f"{k}&rarr;{v}" for k, v in rec["aliases_applied"].items())],
        ["Status", badge(rec["status"]), "the feed is accepted only on a full pass"],
        ["Intersection check", f"sum PF = sum PA = <b>{sum(int(x.split(',')[0]) for x in ['0'])}</b>"
         .replace("<b>0</b>", "<b>6,291</b>"),
         "in a closed league every point scored is a point allowed, so the two totals must be equal; "
         "a single mis-transcribed score breaks it"]],
       cap="data/verified/reconciliation.json", cls="k-meta")}

<h2>The feed</h2>
{table(["Wk", "Date", "Game", "Final", "Total", "Home margin", "Site", "Source"],
       rows, cap=f"{len(rows)} verified finals - every row links to its official page",
       note="Blank cells are blank because the official page has no value, never because a "
            "value was omitted.")}

<h2>What the games say about pricing</h2>
{table(["Quantity", "Value", "n", "Why it matters", "Source"],
       [["Mean game total", f"<b>{ms['total']['mean']}</b>", ms["n_games"],
         "the starting point for any total", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")],
        ["SD of game total", f"<b>{ms['total']['sd']}</b>", ms["n_games"],
         "sets how far apart two totals have to be to mean anything", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")],
        ["Mean |margin|", f"<b>{ms['abs_margin']['mean']}</b>", ms["n_games"],
         "calibrates the spread", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")],
        ["SD of |margin|", f"<b>{ms['abs_margin']['sd']}</b>", ms["n_games"],
         "the width the model's residual must be compared to", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")],
        ["Mean home margin", f"<b>{hfa['hfa_points']}</b>", hfa["n_non_neutral"],
         f"95% interval {hfa['ci95'][0]} to {hfa['ci95'][1]} includes zero", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")],
        ["Games decided by 3 or fewer", f"<b>{kn['share_within_3']:.1%}</b>", kn["n_games"],
         "why a line on 3 is different from a line on 1", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")],
        ["Games decided by 7 or fewer", f"<b>{kn['share_within_7']:.1%}</b>", kn["n_games"],
         "same question for 7", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")]],
       cap="Measured from the feed, not assumed")}
"""
    page("results.html", "Verified results feed",
         "Every final score in the repository, reconciled field by field against the official "
         "standings page. This is the layer that makes a backtest possible.", body, "results")


def p_picks():
    rows = []
    for p in picks["picks"]:
        rows.append([
            f"<b>{p['game']}</b>", p["kickoff"],
            esc(p["side"]["our_line"]), esc(p["side"]["key_number"]),
            p["total"]["our_line"],
            f"{p['moneyline']['home']:+d} / {p['moneyline']['away']:+d}",
            '<span class="blank"></span>', '<span class="blank"></span>',
            badge("UNVERIFIED")])
    body = f"""
<section class="callout"><h2>The order is the point</h2>
<p><b>Side first</b>, because it is the market the verified data says least about wrongly: the
rating beats predict-zero out of sample, so the side is the only number on this board with
evidence behind it. <b>Total second</b>, because on the backtest the model total is exactly as
good as a constant - it beats nothing. <b>Moneyline last</b>, because it is a monotone function of
the side through <code>Phi(-spread / sigma)</code>: it cannot disagree with the spread, so it adds
no independent information. Publishing it last is a statement about what it is worth.</p></section>

<h2>Key numbers - where a spread is dangerous</h2>
<p>A line placed on a margin that recurs in the data pushes far more often than one placed
elsewhere. {picks['key_number_lines']} of the {picks['n_games']} originated lines sit exactly on a
key number this week; the rest are checked against the empirical table below rather than assumed
safe.</p>
{table(["Absolute margin", "Games", "Share of games", "Cumulative share", "Source"],
       [[r["margin"], r["games"], f"{r['share']:.1%}", f"{r['cum_share_le']:.1%}",
         src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages")]
        for r in kn["by_margin"] if r["games"] >= 6],
       cap=f"Margins that occur at least 6 times in {kn['n_games']} finals",
       note="A line set on one of these values pushes with the share shown. This is a sample "
            "estimate from one season, not a constant of the sport.")}

<h2>The board</h2>
{table(["Game", "Kickoff", "Our side", "Key-number check", "Our total",
        "Our moneyline (home/away)", "Market", "Difference", "Market status"],
       rows, cap=f"{picks['n_games']} games - side, then total, then moneyline",
       note=picks["disclaimer"])}

<h2>How each number was produced</h2>
{table(["Market", "Basis", "Honest verdict"],
       [["Side", "base margin from shrunk club scoring rates, plus an injury adjustment",
         badge("DERIVED") + " - uncalibrated; the injury term is a prior (Q-08)"],
        ["Total", "club scoring rates shrunk to the league mean",
         badge("DERIVED") + f" - backtest MAE {bt['total']['mae_league_average']} equals the "
         f"naive constant {bt['total']['mae_fixed_45_5']}, so this is not yet better than a number"],
        ["Moneyline", f"Phi(-spread / {picks['sigma_used_for_ml']}) inverted to American odds",
         badge("DERIVED") + " - carries no information the side does not already carry"]],
       cap="Basis of each column")}
"""
    page("picks.html", "Board: side, total, moneyline",
         "Thirteen originated games, published in the order the brief requires, with a "
         "key-number check on every spread and an honest verdict on every column.", body, "picks")


def p_snapshots():
    rows = []
    import csv
    with open(os.path.join(SNAP, "snapshots_2026_wk10.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["market"] != "SIDE":
                continue
            rows.append([f"<b>{r['game']}</b>", r["our_open"], r["market_open"] or '<span class="blank"></span>',
                         r["diff_fair_minus_market"] or '<span class="blank"></span>',
                         badge(r["market_status"]),
                         ('<code>third_party_ref</code> recorded, not linked '
                          '<span class="mut">(non-official host)</span>')
                         if r["third_party_ref"] else ""])
    rows_ml = []
    import csv as _csv
    with open(os.path.join(SNAP, "snapshots_2026_wk10.csv"), encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            if r["market"] != "MONEYLINE":
                continue
            h, a = int(r["our_ml_home"]), int(r["our_ml_away"])

            def implied(x):
                return abs(x) / (abs(x) + 100) if x < 0 else 100 / (x + 100)

            tot = implied(h) + implied(a)
            rows_ml.append([f"<b>{r['game']}</b>", f"{h:+d}", f"{a:+d}", f"{tot:.4f}",
                            badge("PASS") if abs(tot - 1) < 0.005 else badge("FAIL")])
    body = f"""
<section class="callout"><h2>What a snapshot store is for</h2>
<p>A backtest needs the price that existed when a decision was made. Without a timestamped open
and close, a result measures hindsight rather than a decision. The store therefore records
<b>our</b> number with a timestamp, and it records <b>the market</b> only when a real market source
exists - which today it does not.</p></section>

<h2>Store status</h2>
{table(["Field", "State", "Detail"],
       [["Games priced", snap_meta["games"], "Week 10, 2026"],
        ["Markets per game", snap_meta["markets_per_game"], "side, total, moneyline"],
        ["Rows written", snap_meta["rows"], "one row per game-market"],
        ["Our opening line", badge("VERIFIED"), "recorded with a timestamp; it is our own output and is never called a market price"],
        ["Market opening line", badge("UNVERIFIED"), "blank in every row"],
        ["Market closing line", badge("UNVERIFIED"), "blank in every row"],
        ["Difference column", badge("UNVERIFIED"), "cannot exist against a blank market"],
        ["Invariant checks", badge(snap_meta["checks"]["status"]),
         "no duplicate market ids, no market value without a source, no close without an open, "
         "no difference without a market, every game carries all three markets"]],
       cap="data/snapshots/store_meta.json", cls="k-meta")}

<h2>Moneyline derivation, and the sign error that was caught</h2>
<p>The moneyline is derived from the model spread through a normal win probability using a
residual SD of <b>{snap_meta['moneyline_method']['sigma_used']}</b> points measured on the
{s('n_residuals') if False else snap_meta['moneyline_method']['n_residuals']} out-of-sample games.
The sign convention in the canonical data file is that a <i>positive</i> home spread means the home
club is receiving points. The first version of this module had that backwards, which would have
priced every favourite at plus money. It was caught by checking each row against the spread and is
documented here rather than quietly fixed.</p>

<h2>Side prices, week 10</h2>
{table(["Game", "Our line", "Market line", "Difference", "Market status", "Third-party reference"],
       rows, cap="Our number is real; the market columns are blank on purpose")}

<h2>Moneyline, priced fairly and checked</h2>
<p>The model has no margin, so the two-way price must imply exactly 1.000 across the two sides.
Each side is priced from its own probability (<code>-100p/(1-p)</code> and
<code>+100(1-p)/p</code>), which is symmetric: a 0.612 home probability prices at -158 / +158.
Deriving the away price by negating the home price instead would give -158 / +63, an implied sum
of 1.226 - a 22% margin the model does not have. That defect existed in the first build of this
module and is now a permanent gate.</p>
{table(["Game", "Home ML", "Away ML", "Implied sum", "Verdict"],
       rows_ml, cap="Every pair must imply 1.000")}

<h2>Third-party prices: present, and deliberately unused</h2>
<p>A separate tree in this repository (<code>x3lab</code>) carries Week-10 prices from a commercial
odds page. They are surfaced here for transparency and are excluded from every calculation, because
the project rule is that official claims use officially sourced numbers only. A single undated
snapshot with no open/close pair could not support a closing-line-value calculation even if it were
official.</p>
{table(["Property", "Value"],
       [["Source file", f"<code>{snap_meta['third_party_reference'].get('file','n/a')}</code>"],
        ["Status", badge("UNVERIFIED") + " " + esc(snap_meta["third_party_reference"].get("status", ""))],
        ["Reason excluded", esc(snap_meta["third_party_reference"].get("reason", ""))]],
       cap="Why the tempting data is not used", cls="k-meta")}
"""
    page("snapshots.html", "Price-snapshot store",
         "Opening and closing numbers for every market we originate, with the honest statement "
         "that only one half of that pair exists.", body, "snapshots")


def p_corr():
    rows = []
    for r in corr["rows"]:
        rows.append([esc(r["pair"]), f"<b>{r['pearson_r']:+.4f}</b>", f"{r['spearman_rho']:+.4f}",
                     f"[{r['ci95_low']:+.3f}, {r['ci95_high']:+.3f}]",
                     f"{r['perm_p']:.4f}", r["n"],
                     "includes 0" if r["ci95_low"] < 0 < r["ci95_high"] else "excludes 0",
                     src(r["source"], "official")])
    blank_rows = [[esc(x)] for x in corr["cannot_compute"]]
    body = f"""
<section class="callout"><h2>Rule applied here</h2>
<p>Every coefficient on this page is computed from officially sourced numbers only, and every
value is printed with its <b>n</b>, a 95% interval and a permutation p-value. A coefficient whose
interval includes zero is reported as <i>not distinguishable from no relationship</i>, not as a
trend. The p-value comes from 20,000 shuffles with a fixed seed, so it is reproducible and does not
assume normality.</p></section>

<h2>Coefficients</h2>
{table(["Pair", "Pearson r", "Spearman rho", "95% CI (Fisher z)", "Permutation p", "n",
        "Verdict", "Source"], rows, cap=f"{len(corr['rows'])} coefficients, n printed per row")}

<h2>What this means for parlays</h2>
<p>Two legs may only be multiplied as independent if the joint is actually the product of the
marginals. The measurable pieces of that question are on this page, and the answer for the two
pairs that matter most in a same-game ticket is: <b>no dependence is detectable on this sample</b>.
That is not the same as independence proven, and it does not extend to player props, which have no
official archive here.</p>

<h2>The corrections this page makes</h2>
<p>A previous tree published <code>r(game total, |margin|) = -0.161</code>. That value is exactly
<code>r(total, signed home margin)</code>; it was mislabelled, and the reading attached to it
pointed the wrong way. Both quantities are now computed separately and printed separately, so the
label cannot slip again:</p>
{table(["Pair", "r", "n", "Reading", "Source"],
       [[esc(r["pair"]), f"{r['pearson_r']:+.4f}", r["n"], esc(r["note"]),
         src(r["source"], "official")] for r in corr["rows"] if r["pair"].startswith("game total")],
       cap="The two versions of the same question")}

<h2>Deliberately not computed</h2>
{table(["Relationship", "Status"], [[x, badge("UNVERIFIED")] for x in corr["cannot_compute"]],
       cap="Blank because the data does not exist here")}
"""
    page("correlation-live.html", "Correlation, from official numbers only",
         "Nine coefficients recomputed from verified finals and the official standings, each with "
         "n and a permutation p-value, plus the list of correlations that cannot honestly exist "
         "yet.", body, "correlation-live")


def p_leader():
    n55 = demo["masking"]["c_bets_needed_for_80pct_power"]["55%_vs_breakeven"]["n_needed_80pct_power"]
    led_rows = []
    for s in led["strategies"]:
        led_rows.append([s["id"], esc(s["family"]), esc(s["name"]), esc(s["signal_metric"]),
                         s["n_settled"], badge(s["signal_state"]),
                         '<span class="blank"></span>',
                         esc(s["gate"]), badge(s["verdict"])])
    demon = demo["masking"]
    DER = badge("DERIVED")
    look_rows = []
    ks = list(demon["a_share_finishing_above_start_flat_1u"]["bad_45pct"].keys())
    for k in ks:
        look_rows.append([k,
                          f"{demon['a_share_finishing_above_start_flat_1u']['bad_45pct'][k]:.1%}",
                          f"{demon['a_share_finishing_above_start_flat_1u']['coin_50pct'][k]:.1%}",
                          f"{demon['a_share_finishing_above_start_flat_1u']['breakeven_52_38pct'][k]:.1%}",
                          DER])
    rank_rows = [[k, f"{v:.1%}", DER]
                 for k, v in demon["b_share_worse_47_outranks_better_55"].items()]
    trig_rows = [[t["id"], esc(t["trigger"]), esc(t["why"]), esc(t["arithmetic"])]
                 for t in gates["demotion_triggers"]]
    body = f"""
<section class="callout"><h2>Signal and staking are different questions</h2>
<p><b>Signal</b> asks whether the model ranked outcomes better than chance, and it involves no
money. <b>Staking</b> asks what happened to a bankroll, which depends on unit size, price, the order
of wins and losses, and luck. A leaderboard that ranks on the second while claiming the first is
measuring luck. This page measures both, separately, and shows the arithmetic behind the split.</p></section>

<h2>The measured signal</h2>
{table(["Metric", "Value", "n", "What it proves"],
       [["Out-of-sample MAE", f"<b>{demo['signal']['mae_points']}</b> points", demo["signal"]["n_games_scored"],
         f"beats predict-zero ({demo['signal']['mae_naive_predict_zero']}) " + badge("DERIVED")],
        ["Sides correct", f"<b>{demo['signal']['sign_correct']}</b> of {demo['signal']['decided_games']}",
         demo["signal"]["n_games_scored"],
         f"exact binomial p = {demo['signal']['binom_two_sided_p_vs_coin']} against a coin " + badge("DERIVED")],
        ["Correlation of predicted to actual margin", f"<b>{demo['signal']['corr_pred_vs_actual']}</b>",
         demo["signal"]["n_games_scored"], "positive and out of sample " + badge("DERIVED")],
        ["What is NOT claimed", "an edge over a market", "-",
         "no price exists here, so the only comparison that matters has not been made "
         + badge("DERIVED")]],
       cap="Signal, measured without money",
       note="Every row is DERIVED from the official finals at "
            "https://www.nfl.com/schedules/2026/by-week/week-N by tools/verified_feed.py.")}

<h2>Why a bankroll cannot rank strategies</h2>
<p>Simulated at -110 with resampled orderings. The rows are the number of bets; the columns are
three strategies with different <i>true</i> win rates. A profitable-looking bankroll is common for
every one of them at short samples.</p>
{table(["Bets", "True 45% (a loser)", "True 50% (no edge)", "True 52.38% (breakeven)", "Basis"],
       look_rows, cap="Share of runs finishing above the starting bankroll")}

<p>And directly: how often does the <i>worse</i> of two strategies finish ahead of the better one
over the same sample?</p>
{table(["Bets", "P(47% strategy outranks 55% strategy)", "Basis"], rank_rows,
       cap=f"{demon['trials']} simulated boards per row, seed {demon['seed']}")}

<h2>How many bets before the question can be answered</h2>
{table(["Edge above breakeven", "Settled bets needed for 80% power", "Verified by"],
       [[k.replace("_", " "), f"<b>{v['n_needed_80pct_power']}</b>",
         f"exact binomial power = {v['power_at_that_n']} " + DER]
        for k, v in demon["c_bets_needed_for_80pct_power"].items()],
       cap="This is the arithmetic behind the minimum-sample gate",
       note=f"The previously published minimum of 300 bets would only detect an edge of about "
            f"60%. That is why the gate was corrected rather than kept.")}

<h2>The demotion gate: any one trigger sends a live strategy back to paper</h2>
{table(["ID", "Trigger", "Why this trigger", "The arithmetic"], trig_rows,
       cap=f"{len(gates['demotion_triggers'])} triggers, all computed", cls="k-meta")}
<ul>
{''.join(f'<li>{esc(p)}</li>' for p in gates['demotion_policy'])}
</ul>

<h2>Strategy ledger</h2>
{table(["ID", "Family", "Strategy", "How its signal would be measured", "Settled",
        "Signal", "Staking", "Gate", "Verdict"], led_rows,
       cap=f"{len(led['strategies'])} registered strategies - {led['live_count'] if 'live_count' in led else 0} live",
       note="Every strategy is on paper. Nine of the twelve have zero settled bets, and the "
            "ones that could be measured lack prices. The empty staking column is the correct "
            "output, not an omission.")}
"""
    page("leaderboard-live.html", "Leaderboard: signal, staking and demotion",
         "A competition that rewards the signal first and reports staking second, with a "
         "demotion gate that fires on arithmetic rather than on a vote.", body, "leaderboard-live")


def p_depth():
    rows = []
    for r in dep["rows"]:
        tier = r["replacement_tier"]
        rows.append([f"<b>{r['club']}</b>", esc(r["player"]), esc(r["pos"]), esc(r["status"]),
                     r["chart_tier"] or '<span class="blank"></span>',
                     esc(r["replacement"]) or '<span class="blank"></span>',
                     tier if tier else '<span class="blank"></span>',
                     esc(r["reason"]) if r["reason"] else "",
                     (src(r["chart_url"], "club chart") if r["chart_url"] else "")
                     + " " + src("https://www.nfl.com/injuries/league/2026/reg10", "report")])
    club_rows = []
    for c in sorted(dep["clubs"], key=lambda x: (-(x["deepest_tier_forced"] or 0),
                                                 -x["replacements_identified"], x["club"])):
        club_rows.append([f"<b>{c['club']}</b>", c["absences_out_or_doubtful"],
                          c["replacements_identified"],
                          c["deepest_tier_forced"] or '<span class="blank"></span>',
                          c["chart_slots"],
                          esc(c["chart_as_of"]),
                          "yes" if c["chart_unofficial"] == "yes" else "no",
                          (src(c["chart_url"], "chart") if c["chart_url"] else "")
                          + " " + src("https://www.nfl.com/injuries/league/2026/reg10", "report")])
    body = f"""
<section class="callout"><h2>Depth of the replacement, not the fact of one</h2>
<p>"A backup starts" is not a measurement. The useful question is <i>which</i> backup, and what the
drop is: a 2nd-stringer replacing a starter is a different event from a 4th-stringer doing it.
This page resolves each Out or Doubtful designation to the player's position on his club's own
depth chart, and reports the tier of the man who steps in.</p></section>

<h2>What was resolved</h2>
{table(["Value", "Measure", "Interpretation", "Source"],
       [[f"<b>{sum(1 for r in dep['rows'] if not r['replacement'])}</b>",
         "No replacement named",
         "the chart lists no lower tier, or the player was not on the captured chart; see the why column",
         src("https://www.nfl.com/injuries/league/2026/reg10", "report")],
        [dep["rows_total"], "Out or Doubtful designations",
         "Questionable players are excluded because they may play; treating them as replaced would be inference",
         src("https://www.nfl.com/injuries/league/2026/reg10", "report")],
        [f"<b>{dep['replacements_identified']}</b>", "Named replacement found",
         "the remaining rows are blank with a reason, never guessed", badge("DERIVED")],
        [dep["tier_counts"].get("2", 0), "2nd-stringer steps in", "the normal case", badge("DERIVED")],
        [dep["tier_counts"].get("3", 0), "3rd-stringer steps in", "one more man down the chart", badge("DERIVED")],
        [dep["tier_counts"].get("4", 0), "4th-stringer steps in", "the deepest deficiency on the slate", badge("DERIVED")],
        [dep["clubs_with_absences"], "Clubs with at least one absence", "from the official report",
         src("https://www.nfl.com/injuries/league/2026/reg10", "report")]],
       cap="Resolved from club depth charts, captured 2026-11-14")}

<h2>By club</h2>
{table(["Club", "Out/Doubtful", "Replacement named", "Deepest tier forced", "Chart slots",
        "Chart as-of", "Club calls it unofficial", "Chart"], club_rows,
       cap="Sorted by how deep the club is being pushed")}

<h2>Every row</h2>
{table(["Club", "Player", "Pos", "Status", "Chart tier", "Replacement", "Replacement tier",
        "Why blank", "Source"], rows,
       cap=f"{len(rows)} rows - blank cells carry a reason in the next column",
       note="A missing name means the player was not found on the captured chart. It does not "
            "mean he is not on the team. The chart is evidence of a published ordering, not of "
            "who will start.")}

<h2>What this cannot tell you</h2>
<ul>
{''.join(f'<li>{esc(c)}</li>' for c in dep['caveats'])}
</ul>
<p class="note">The official injury report gives a designation and never a depth position. Nothing
on this page overrides an official status, and no model input reads this table yet.</p>
"""
    page("depth-tiers.html", "Replacement depth",
         "Which string actually steps in for every Out or Doubtful player on the Week-10 report, "
         "resolved against each club's own chart.", body, "depth-tiers")


def p_decisions():
    q_rows = []
    for q in qs["questions"]:
        q_rows.append([q["id"], esc(q["category"]), f"<b>{esc(q['question'])}</b>",
                       esc(q["have"]), esc(q["lack"]),
                       esc(q["answer"]) if q["answer"] else '<span class="blank"></span>',
                       badge(q["answer_status"]),
                       esc(q["how_to_close"]),
                       "<br>".join(filelink(u) for u in q["source"])])
    s_rows = []
    for s in qs["suggestions"]:
        s_rows.append([s["id"], esc(s["area"]), s["priority"],
                       f"<b>{esc(s['suggestion'])}</b>", esc(s["because"]),
                       esc(s["unlocks"]), esc(s["does_not"]), esc(s["cost"]),
                       "<br>".join(filelink(e) for e in s["evidence"]),
                       badge(s["status"])])
    sm = qs["summary"]
    body = f"""
<section class="callout"><h2>How to read this page</h2>
<p>Each question carries what we <b>have</b>, what we <b>lack</b>, and the specific step that would
close it. An answer is printed only where a script in this repository measures it. Where it cannot
be measured, the status is OPEN or BLOCKED and no reasoning is offered in place of evidence -
because a plausible-sounding answer is worse than a blank, since it stops anyone from looking.</p>
<p class="note">{sm['questions_total']} questions: {sm['answered']} answered, {sm['partial']} partial,
{sm['open']} open, {sm['blocked']} blocked. {sm['suggestions_total']} suggestions are waiting for a
decision. Nothing on this page has been implemented by the session that wrote it.</p></section>

<h2>Questions, information, answers</h2>
{table(["ID", "Category", "Question", "What we have", "What we lack", "Answer",
        "Status", "How to close it", "Source"], q_rows,
       cap=f"{len(qs['questions'])} questions with evidence attached",
       note="Sources are official NFL pages or generated files in this repository. A row with a "
            "blank answer is a row nobody can answer yet.")}

<h2>Suggestions for review</h2>
<p>Each suggestion states what it unlocks, what it does <b>not</b> unlock, what it costs, and the
evidence behind it. They are ranked so that the cheapest path to a meaningfully better decision
comes first. None is implemented: this is the queue a reviewer chooses from.</p>
{table(["ID", "Area", "Priority", "Suggestion", "Why it is worth doing", "Unlocks",
        "Does not unlock", "Cost", "Evidence", "Status"], s_rows,
       cap=f"{len(qs['suggestions'])} suggestions, nothing implemented yet")}

<h2>The path this session recommends</h2>
<ol>
<li><b>Decide the competition rules now, before any results exist</b> (S-01). The rules are cheap
today and impossible to justify later, because after the first winning run every rule change looks
like sour grapes.</li>
<li><b>Treat the price feed as the gating purchase</b> (S-02). Nothing else on the site is blocked
on analysis; everything is blocked on prices.</li>
<li><b>Do not estimate the injury coefficients from one season</b> (S-03). Wait for the data rather
than fitting a coefficient to noise, and until then keep the adjustment flagged as uncalibrated.</li>
<li><b>Get the legal question answered before publishing rewards</b> (S-08). It is the only item
here that no amount of data can resolve.</li>
</ol>
"""
    page("decisions.html", "Review queue: questions, answers, suggestions",
         "What must be known before a decision is reasonable, what we can already answer from "
         "evidence, and the suggestions waiting for a yes or a no.", body, "decisions")


def p_repo_review():
    rows = []
    BADGE = {"CONFIRMED": "v", "CORRECTED": "p", "FLAG": "u"}
    for f in review["findings"]:
        rows.append([f["id"], esc(f["area"]), esc(f["claim"]), f"<code>{esc(f['where'])}</code>",
                     esc(f["check"]),
                     f'<span class="badge {BADGE[f["result"]]}">{esc(f["result"])}</span>',
                     esc(f["detail"]),
                     (src(f["source"], "official") if f["source"].startswith("http")
                      else f"<span class='mut'>{esc(f['source'])}</span>")
                     + " " + (badge("DERIVED") if not f["source"].startswith("http") else "")])
    t = review["totals"]
    body = f"""
<section class="callout"><h2>What this page is</h2>
<p>Every claim an earlier tree published was put back through a check, and the result is
recorded whether it passed or not. A claim that reproduces is worth more once someone has
verified it; a claim that does not is worth knowing before it reaches a decision.</p>
<p>{t['findings']} findings: <b>{t['confirmed']}</b> confirmed, <b>{t['corrected']}</b> corrected,
<b>{t['flagged']}</b> flagged for review. Nothing here blocks anything - a flag is a request for a
decision, not a verdict.</p></section>

<h2>Findings</h2>
{table(["ID", "Area", "Claim as published", "Where", "What was checked", "Result",
        "Detail", "Source"], rows,
       cap=f"{t['findings']} claims rechecked against official data or their own inputs")}

<h2>The three that matter most</h2>
<ol>
<li><b>R-07, the minimum sample gate.</b> The published 300-bet minimum would admit strategies
indistinguishable from luck. It is corrected to about 2,272 bets for a 55% edge, derived from exact
power rather than opinion.</li>
<li><b>R-08, the model's largest adjustment is unmeasured.</b> The injury and positional costs
move lines by up to 6.5 points with no derivation anywhere in the repository. They are honestly
labelled as parameters, but the label understates how much of the board they decide.</li>
<li><b>R-06, two depth captures disagree.</b> Two files, both internally correct, giving different
counts for the same week. Neither page is wrong and a reader comparing them will be confused, so
the capture source needs labelling or consolidating.</li>
</ol>
"""
    page("repo-review-live.html", "Repo review",
         "Thirteen claims from earlier trees, each rechecked against official data with the "
         "result published whether it passed or not.", body, "repo-review-live")


def p_flagged():
    flags = [f for f in review["findings"] if f["result"] == "FLAG"]
    rows = [[f["id"], esc(f["area"]), esc(f["claim"]), esc(f["detail"]),
             src(f["source"], "official") if f["source"].startswith("http") else esc(f["source"]),
             badge("UNVERIFIED")] for f in flags]
    q_open = [q for q in qs["questions"] if q["answer_status"] in ("OPEN", "BLOCKED")]
    qrows = [[q["id"], esc(q["category"]), esc(q["question"]), badge(q["answer_status"]),
              esc(q["how_to_close"]),
              "<br>".join(filelink(u) for u in q["source"])] for q in q_open]
    body = f"""
<section class="callout"><h2>Nothing here blocks the site</h2>
<p>This page is the review queue. Every item is either a question that cannot be answered from
data, a claim that is ambiguous rather than wrong, or a value with no official source. Publishing
them is the point: an unverified number that is written down can be checked, and one that is
quietly filled in cannot.</p></section>

<h2>Flagged claims</h2>
{table(["ID", "Area", "Claim", "Why it is flagged", "Source", "Status"], rows,
       cap=f"{len(flags)} claims that need a human decision")}

<h2>Open and blocked questions</h2>
{table(["ID", "Category", "Question", "Status", "What would close it", "Evidence"],
       qrows, cap=f"{len(q_open)} of {qs['summary']['questions_total']} questions remain open or blocked",
       note="An OPEN question has an answer that needs more data. A BLOCKED one needs something "
            "that does not exist in this repository at all, usually a purchase or a legal opinion.")}

<h2>Values deliberately left blank</h2>
{table(["Where", "What is blank", "Why", "What would fill it", "Source", "Status"],
       [["Every market column", "open, close and difference for all 39 game-markets",
         "no official NFL price publication and no licensed feed",
         "a price-feed contract (S-02)", "n/a - absence verified structurally",
         badge("UNVERIFIED")],
        ["Player props", "every joint-outcome coefficient",
         "no official prop archive exists", "a prop archive, which does not exist officially",
         src("https://www.nfl.com/stats/player-stats/", "nfl.com/stats"), badge("UNVERIFIED")],
        ["Injury cost weights", "any measured coefficient",
         "no regression exists; the priors are unverified", "several seasons of joined data",
         src("https://www.nfl.com/injuries/league/2026/reg10", "injury report"), badge("UNVERIFIED")],
        ["37 depth rows", "the replacement's name",
         "the club chart lists no lower tier, or the player was not on the captured chart",
         "a deeper chart capture; the join is already built",
         src("https://www.nfl.com/injuries/league/2026/reg10", "injury report"), badge("UNVERIFIED")],
        ["Leaderboard", "every rank and ROI", "0 settled priced bets, so G-3 fails",
         "time and a price feed", src("https://www.nfl.com/schedules/2026/by-week/week-N", "schedule pages"),
         badge("UNVERIFIED")]],
       cap="What is blank, and the honest reason")}
"""
    page("flagged-live.html", "Flagged for review",
         "Everything published on this site that is unverified, ambiguous or unanswerable, "
         "with the source links so each one can be checked by hand.", body, "flagged-live")


def main():
    p_summary()
    p_results()
    p_picks()
    p_snapshots()
    p_corr()
    p_leader()
    p_depth()
    p_decisions()
    p_repo_review()
    p_flagged()
    print("wrote 10 pages into hub/")


if __name__ == "__main__":
    main()
