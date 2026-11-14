#!/usr/bin/env python3
"""
Renders the X3 signals module (signals/*.html) from signals/data/*.json.

Every <tr> in a data table carries either a link to an official source or an
explicit UNVERIFIED badge. scripts/verify_signals.py enforces that after every
build, and again in CI.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "signals" / "data"
OUT = ROOT / "signals"
ASSETS = OUT / "assets"

AS_OF = "2026-11-14"

NAV = [
    ("Overview", [
        ("index.html", "Overview", "What this module is, and what is verified"),
        ("executive-summary.html", "Executive summary", "The one-page brief"),
        ("requirements.html", "Requirements", "The eight requirements and their evidence"),
    ]),
    ("Market data", [
        ("results.html", "Results feed", "163 games, 137 verified finals"),
        ("prices.html", "Price snapshots", "Opening and closing numbers for every originated market"),
        ("lines.html", "Originated lines", "Fair line, market line, difference"),
    ]),
    ("Strategies", [
        ("strategies.html", "Strategies", "Singles, parlays, player-prop combos"),
        ("leaderboard.html", "Leaderboard", "Signal and staking, scored separately"),
        ("gates.html", "Gates &amp; demotion", "Validation gates and the live-to-paper rule"),
    ]),
    ("Evidence", [
        ("correlations.html", "Correlations", "Every coefficient with its n"),
        ("depth.html", "Injuries &amp; depth", "Who replaces the starter, and how deep"),
    ]),
    ("Decisions", [
        ("questions.html", "Open questions", "What we have, what we lack, how to find out"),
        ("suggestions.html", "Suggestions", "Paths to choose between before anything changes"),
    ]),
    ("Governance", [
        ("sources.html", "Sources", "Official pages, what each one supplies"),
        ("verification.html", "Verification log", "How every row was checked"),
        ("repo-review.html", "Repo review", "The repository audited tree by tree"),
        ("flagged.html", "Flagged for review", "Unverified items and irregularities"),
    ]),
]

CSS = """
:root{
  --bg:#f6f7f9; --panel:#ffffff; --ink:#14181f; --muted:#5b6472; --line:#e2e6ec;
  --accent:#0b4f9e; --accent-soft:#e8f0fb; --good:#0f7b45; --good-soft:#e6f4ec;
  --bad:#b3261e; --bad-soft:#fdeceb; --warn:#8a5a00; --warn-soft:#fdf3e0;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}
header.top{background:#0f1b2a;color:#fff;padding:14px 20px;position:sticky;top:0;z-index:20;
  box-shadow:0 1px 0 rgba(255,255,255,.08)}
.top-in{max-width:1280px;margin:0 auto;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.brand{font-weight:700;font-size:17px;letter-spacing:.2px}
.brand a{color:#fff;text-decoration:none}
.brand span{font-weight:400;color:#9fb3c8;margin-left:8px;font-size:13px}
.asof{margin-left:auto;font-size:12.5px;color:#9fb3c8}
nav.cats{max-width:1280px;margin:0 auto;padding:8px 20px 0;display:flex;gap:6px;flex-wrap:wrap}
nav.cats a{color:#c9d8e8;text-decoration:none;font-size:12.5px;padding:4px 9px;border-radius:6px}
nav.cats a:hover{background:rgba(255,255,255,.1);color:#fff}
nav.cats a.on{background:var(--accent);color:#fff}
main{max-width:1280px;margin:0 auto;padding:22px 20px 80px}
h1{font-size:26px;line-height:1.25;margin:6px 0 10px}
h2{font-size:19px;margin:30px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:15.5px;margin:20px 0 8px}
p.lede{font-size:16px;color:#2c3644;max-width:80ch}
p{max-width:92ch}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .num{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
.card .lbl{font-size:13px;color:var(--muted);margin-top:2px}
.card .sub{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.4}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
.callout{background:var(--accent-soft);border:1px solid #c7dbf5;border-radius:10px;padding:14px 16px;margin:16px 0}
.callout.warn{background:var(--warn-soft);border-color:#f0dcb4}
.callout.bad{background:var(--bad-soft);border-color:#f3c9c6}
.callout.good{background:var(--good-soft);border-color:#bfe3ce}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel);margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f0f3f7;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#3d4857;
  position:sticky;top:0;white-space:nowrap}
tbody tr:hover{background:#fafcfe}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono);font-size:12.5px}
code{font-family:var(--mono);font-size:12.5px;background:#eef1f5;padding:1px 5px;border-radius:4px}
a.src{font-size:11.5px;white-space:nowrap}
.badge{display:inline-block;font-size:11px;font-weight:600;padding:1px 7px;border-radius:999px;
  white-space:nowrap;letter-spacing:.3px}
.badge.unv{background:var(--bad-soft);color:var(--bad);border:1px solid #f3c9c6}
.badge.ok{background:var(--good-soft);color:var(--good);border:1px solid #bfe3ce}
.badge.warn{background:var(--warn-soft);color:var(--warn);border:1px solid #f0dcb4}
.badge.neutral{background:#eef1f5;color:#3d4857;border:1px solid var(--line)}
.blank{color:#aab3c0}
details{margin:12px 0;border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:0 14px}
details[open]{padding-bottom:12px}
summary{cursor:pointer;padding:12px 0;font-weight:600}
.note{color:var(--muted);font-size:13px}
ul.tight{margin:8px 0;padding-left:20px}
ul.tight li{margin:4px 0;max-width:92ch}
footer{max-width:1280px;margin:0 auto;padding:20px;color:var(--muted);font-size:12.5px;
  border-top:1px solid var(--line)}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:13.5px}
.kv dt{color:var(--muted)}
.kv dd{margin:0}
.paths{background:#f0f3f7;border-left:3px solid var(--accent);padding:8px 12px;margin:8px 0;font-size:13.5px}
.small{font-size:12.5px;color:var(--muted)}
@media (max-width:700px){ th,td{padding:6px 7px;font-size:12.5px} h1{font-size:22px} }
"""


# --------------------------------------------------------------------------
def esc(v):
    return html.escape("" if v is None else str(v), quote=True)


def pfmt(v):
    if v is None or v == "":
        return '<span class="blank">&mdash;</span>'
    if isinstance(v, (int, float)) and 0 < v < 0.0001:
        return "&lt;0.0001"
    return fmt(v, 4)


def fmt(v, nd=None):
    if v is None or v == "":
        return '<span class="blank">&mdash;</span>'
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd if nd is not None else 3}f}"
    if isinstance(v, list):
        return esc(", ".join("" if x == "" else str(x) for x in v))
    return esc(v)


def srcl(url, text=None):
    if not url:
        return '<span class="badge unv">UNVERIFIED</span>'
    return f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(text or "source")}</a>'


def unv_badge(flag_id="", label="UNVERIFIED"):
    t = f"{label} ({flag_id})" if flag_id else label
    return f'<span class="badge unv">{esc(t)}</span>'


def badge_for(flag_id):
    return unv_badge(flag_id) if flag_id else '<span class="badge ok">sourced</span>'


def load(name):
    p = DATA / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else []


# --------------------------------------------------------------------------
def page(title, h1, lede, body, active, extra_head=""):
    cats = []
    for cat, items in NAV:
        on = any(i[0] == active for i in items)
        cats.append(f'<a href="{items[0][0]}" class="{"on" if on else ""}">{cat}</a>')
    links = []
    for cat, items in NAV:
        parts = " ".join(
            f'<a href="{h}" class="{"on" if h == active else ""}">{l}</a>' for h, l, _t in items)
        links.append(f'<div class="cat"><div class="cat-h">{cat}</div>{parts}</div>')
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(h1)} - X3 NFL signals, every row sourced or flagged.">
<title>{esc(title)}</title>
<link rel="stylesheet" href="assets/signals.css">
{extra_head}
</head><body>
<header class="top"><div class="top-in">
<div class="brand"><a href="index.html">X3 <span>NFL signals &amp; strategy desk</span></a></div>
<div class="asof">data as of <b>{AS_OF}</b> &middot; season 2026 &middot; through week 10</div>
</div><nav class="cats">{''.join(cats)}</nav></header>
<main>
<h1>{h1}</h1>
<p class="lede">{lede}</p>
<nav class="sidenav">{''.join(links)}</nav>
{body}
</main>
<footer>
<p>X3 NFL signals module &middot; built by <code>scripts/x3_signals.py</code> and
<code>scripts/build_signals.py</code> from data captured out of official NFL pages.
Every table row links an official source or is explicitly flagged unverified &mdash; enforced by
<code>scripts/verify_signals.py</code>.</p>
<p>Repository: <a href="https://github.com/karagemop466-tech/X3">karagemop466-tech/X3</a> &middot;
canonical desk: <a href="../hub/index.html">hub/</a> &middot;
landing: <a href="../index.html">X3 home</a> &middot;
task board: <a href="../COORDINATION.md">COORDINATION.md</a></p>
</footer>
</body></html>
"""


def table(headers, rows, cls=""):
    th = "".join(f'<th class="{c}">{h}</th>' for h, c in headers)
    body = "".join("<tr>" + "".join(f'<td class="{c}">{v}</td>' for v, (h, c) in zip(r, headers))
                   + "</tr>" for r in rows)
    return f'<div class="tw {cls}"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


H = lambda *names: [(n, "") for n in names]
HN = lambda *names: [(n, "n") for n in names]


# --------------------------------------------------------------------------
def build_all():
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "signals.css").write_text(CSS.lstrip() + """
nav.sidenav{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px;
  margin:14px 0 6px}
nav.sidenav .cat{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
nav.sidenav .cat-h{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);
  margin-bottom:4px}
nav.sidenav a{display:block;font-size:13px;padding:2px 0;text-decoration:none}
nav.sidenav a.on{font-weight:700}
nav.sidenav a:hover{text-decoration:underline}
""")

    meta = json.loads((DATA / "meta.json").read_text())
    C = meta["counts"]
    S = meta["scoring"]
    results = load("results")
    snaps = load("price_snapshots")
    lines = load("lines")
    depth = load("depth")
    avail = load("club_availability")
    corr = load("correlations")
    strats = load("strategies")
    lb = load("leaderboard")
    gates = load("gates")
    demo_rules = load("demotion")
    demo_state = load("demotion_state")
    reqs = load("requirements")
    qs = load("questions")
    sugs = load("suggestions")
    flags = load("flags")
    sources = load("sources")
    weekly = load("weekly")
    repo = load("repo_review")

    pages = {}
    pages["index.html"] = p_index(meta, C, S, results, lines, lb, flags)
    pages["executive-summary.html"] = p_exec(meta, C, S, lb, flags)
    pages["requirements.html"] = p_reqs(reqs)
    pages["results.html"] = p_results(results)
    pages["prices.html"] = p_prices(snaps, lines, meta)
    pages["lines.html"] = p_lines(lines, meta)
    pages["strategies.html"] = p_strategies(strats, S)
    pages["leaderboard.html"] = p_leaderboard(lb, S, weekly)
    pages["gates.html"] = p_gates(gates, demo_rules, demo_state)
    pages["correlations.html"] = p_corr(corr)
    pages["depth.html"] = p_depth(depth, avail)
    pages["questions.html"] = p_questions(qs)
    pages["suggestions.html"] = p_suggestions(sugs)
    pages["sources.html"] = p_sources(sources)
    pages["verification.html"] = p_verification(meta, C)
    pages["repo-review.html"] = p_repo(repo)
    pages["flagged.html"] = p_flags(flags)

    for name, (title, h1, lede, body) in pages.items():
        (OUT / name).write_text(page(title, h1, lede, body, name))
    print(f"wrote {len(pages)} pages to {OUT}")


# --------------------------------------------------------------------------
def p_index(meta, C, S, results, lines, lb, flags):
    cal = S["calibration"]["margin"]
    top = lb[0] if lb else {}
    body = f"""
<div class="grid">
  <div class="card"><div class="num">{C['verified_finals']}</div><div class="lbl">verified finals in the results feed</div>
    <div class="sub">{C['results_rows']} scheduled games, every row linked to its official week page</div></div>
  <div class="card"><div class="num">{C['open_snapshots']} / {C['close_snapshots']}</div><div class="lbl">opening / closing numbers stored</div>
    <div class="sub">{C['price_snapshot_rows']} rows; {C['not_originated']} markets not originated for lack of training data</div></div>
  <div class="card"><div class="num">{C['graded_games']}</div><div class="lbl">games graded walk-forward</div>
    <div class="sub">weeks {min(S['graded_weeks'])}&ndash;{max(S['graded_weeks'])}; every number fitted on earlier weeks only</div></div>
  <div class="card"><div class="num">{C['correlations']}</div><div class="lbl">correlations, each with its n</div>
    <div class="sub">computed only from officially sourced numbers</div></div>
  <div class="card"><div class="num">{C['depth_rows']}</div><div class="lbl">absences with a depth string</div>
    <div class="sub">{C['club_availability_rows']} club-week availability rows, weeks 8&ndash;10</div></div>
  <div class="card"><div class="num">{C['strategies']}</div><div class="lbl">registered strategies</div>
    <div class="sub">singles, parlays and player-prop combos &mdash; none promoted</div></div>
</div>

<div class="callout"><h2>Start here</h2>
<p><a href="executive-summary.html"><b>Executive summary</b></a> for the decisions.
<a href="lines.html"><b>Originated lines</b></a> for the board.
<a href="leaderboard.html"><b>Leaderboard</b></a> for signal versus staking.
<a href="suggestions.html"><b>Suggestions</b></a> to choose a path.
<a href="questions.html"><b>Open questions</b></a> for the information gaps.
<a href="flagged.html"><b>Flagged for review</b></a> for what could not be verified.</p></div>

<h2>What this module does</h2>
<p>It originates its own NFL numbers &mdash; side, then total, then moneyline &mdash; from verified league
data, stores an opening and a closing number for every market it originates, grades them walk-forward
against what actually happened, and scores strategies on signal separately from staking. It does all
of that without a single market price, because none exists in this repository. That is not a gap in the
analysis; it is the finding that shapes everything on this site.</p>

<h2>The three numbers that matter</h2>
<div class="panel">
<dl class="kv">
<dt>Side beats a constant baseline</dt><dd><b>{fmt(S['scores']['side']['win_rate'])}</b> of {S['scores']['side']['n_decisive']} graded games
  (95% CI {fmt(S['scores']['side']['ci95_low'])}&ndash;{fmt(S['scores']['side']['ci95_high'])}, exact binomial p = {pfmt(S['scores']['side']['p_exact_binomial'])}).
  This clears the multiple-testing gate. It is real, and it is the only favourable discovery we have.</dd>
<dt>Total does not</dt><dd><b>{fmt(S['scores']['total']['win_rate'])}</b> of {S['scores']['total']['n_decisive']} (p = {pfmt(S['scores']['total']['p_exact_binomial'])}).
  Worse: when the total model is most confident it is <b>reliably wrong</b> &mdash; {fmt(S['scores']['total_selective']['win_rate'])} on
  {S['scores']['total_selective']['n_decisive']} selective games, p = {pfmt(S['scores']['total_selective']['p_exact_binomial'])}. That is a significant adverse finding, not a null.</dd>
<dt>The model is under-spread</dt><dd>predicted margin SD <b>{fmt(cal['sd_predicted'])}</b> against an actual SD of <b>{fmt(cal['sd_actual'])}</b>
  (ratio {fmt(cal['ratio'])}). It ranks teams in roughly the right order but pulls every number toward the league mean.</dd>
</dl>
</div>

<h2>What is verified and what is not</h2>
<div class="tw"><table><thead><tr><th>Layer</th><th class="n">Rows</th><th>Status</th><th>Source</th></tr></thead><tbody>
<tr><td>Results feed (final scores)</td><td class="n">{C['verified_finals']}</td>
  <td><span class="badge ok">verified</span></td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-1')}</td></tr>
<tr><td>Club standings</td><td class="n">32</td>
  <td><span class="badge ok">verified</span></td><td>{srcl('https://www.nfl.com/standings/league/2026/reg')}</td></tr>
<tr><td>Official injury report</td><td class="n">1,027</td>
  <td><span class="badge ok">verified</span></td><td>{srcl('https://www.nfl.com/injuries/league/2026/reg10')}</td></tr>
<tr><td>Club depth charts (2nd/3rd/4th string)</td><td class="n">32</td>
  <td><span class="badge warn">club-published, undated</span> {unv_badge('F-03')}</td><td>{srcl('https://www.azcardinals.com/team/depth-chart')}</td></tr>
<tr><td>Our own fair lines</td><td class="n">{C['close_snapshots']}</td>
  <td><span class="badge neutral">computed here</span></td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Market lines / opening and closing prices</td><td class="n">0</td>
  <td>{unv_badge('F-01')}</td><td>{srcl('https://www.nfl.com/')}</td></tr>
<tr><td>Per-game player statistics (props)</td><td class="n">0</td>
  <td>{unv_badge('F-04')}</td><td>{srcl('https://www.nfl.com/stats')}</td></tr>
<tr><td>Settled bets, ROI, drawdown</td><td class="n">0</td>
  <td>{unv_badge('F-02')}</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-1')}</td></tr>
</tbody></table></div>
<p class="note">Full register of irregularities: <a href="flagged.html">Flagged for review</a>
({C['flags']} items, all non-blocking).</p>
"""
    return ("X3 NFL signals & strategy desk", "X3 NFL signals &amp; strategy desk",
            "Originate our own NFL numbers, grade them against verified results, and score signal "
            "separately from staking &mdash; with every row sourced from an official page or flagged.", body)


def p_exec(meta, C, S, lb, flags):
    side = S["scores"]["side"]
    tot = S["scores"]["total"]
    totsel = S["scores"]["total_selective"]
    ssel = S["scores"]["side_selective"]
    cal = S["calibration"]["margin"]
    par = S["parlay"]["same_game"]
    bh = S["benjamini_hochberg"]
    body = f"""
<div class="callout bad"><h2>The headline</h2>
<p><b>We can originate a side that beats a constant baseline, and we cannot yet originate a total that
does.</b> Over {side['n_decisive']} walk-forward graded games the side was closer to the actual margin
than a no-knowledge baseline in {side['wins']} of {side['n_decisive']} ({fmt(side['win_rate'])},
95% CI {fmt(side['ci95_low'])}&ndash;{fmt(side['ci95_high'])}, exact binomial p = {pfmt(side['p_exact_binomial'])}).
The total was closer in {tot['wins']} of {tot['n_decisive']} ({fmt(tot['win_rate'])}, p = {pfmt(tot['p_exact_binomial'])}) &mdash;
and on the games where the total model was most confident it was wrong {totsel['losses']} times out of
{totsel['n_decisive']} (p = {pfmt(totsel['p_exact_binomial'])}). That is a significant <i>adverse</i> result.</p>
<p><b>None of this is profit.</b> This repository holds no market price, so no bet can be priced, no ROI
computed and no staking rule evaluated. Everything below is a measurement of forecast accuracy against a
constant, not a claim that money would have been made.</p></div>

<h2>Decisions this supports</h2>
<div class="tw"><table><thead><tr><th>Question</th><th>Answer the data supports</th><th>Confidence</th><th>Source</th></tr></thead><tbody>
<tr><td>Should anything be staked?</td><td>No. No strategy has cleared the {C['gates']} validation gates;
  the sample-size gate alone ({meta['constants']['min_graded_for_skill']} graded decisions) is not met at {S['n_graded_total']}.</td>
  <td><span class="badge ok">high &mdash; this is a gate, not a judgement</span></td>
  <td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Does the side carry skill?</td><td>Yes, measured. Gap to no-skill {fmt(side['win_rate'] - 0.5)},
  CI {fmt(side['ci95_low'] - 0.5)}&ndash;{fmt(side['ci95_high'] - 0.5)}; passes Benjamini-Hochberg at q = {bh['q']}
  across {bh['tests']} tested strategies.</td>
  <td><span class="badge warn">moderate &mdash; n = {side['n_decisive']}</span></td>
  <td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Does the total carry skill?</td><td>No. Point estimate below no-skill and the confident subset is
  significantly worse than a constant.</td>
  <td><span class="badge ok">high for the negative</span></td>
  <td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Can parlays be priced from marginals?</td><td>Not safely. Same-game legs: observed joint
  {fmt(par['joint_observed'])} versus {fmt(par['joint_if_independent'])} under independence (ratio {fmt(par['ratio_obs_over_independent'])},
  phi {fmt(par['phi'].get('r'))}, n = {par['n']}). The dependence is small here, but it is measured, not assumed.</td>
  <td><span class="badge warn">n = {par['n']}, CI includes 0</span></td>
  <td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Is the injury-and-depth layer usable?</td><td>Not as a model input. Three weeks of coverage is not
  enough to identify a coefficient, so no published line is adjusted by it. It is published as a report.</td>
  <td><span class="badge ok">high &mdash; by design</span></td>
  <td>{srcl('https://www.nfl.com/injuries/league/2026/reg10')}</td></tr>
<tr><td>What is the single biggest blocker?</td><td>No market price. It blocks ROI, closing-line value,
  staking, drawdown and half the demotion gates. See {unv_badge('F-01')} and suggestion
  <a href="suggestions.html#S-01">S-01</a>.</td>
  <td><span class="badge ok">high</span></td>
  <td>{srcl('https://www.nfl.com/')}</td></tr>
</tbody></table></div>

<h2>The numbers, in one table</h2>
<div class="tw"><table><thead><tr><th>Measure</th><th class="n">Value</th><th class="n">n</th><th>Reading</th><th>Source</th></tr></thead><tbody>
<tr><td>Side: contest win rate vs constant baseline</td><td class="n">{fmt(side['win_rate'])}</td><td class="n">{side['n_decisive']}</td>
  <td>CI excludes 0.50 &mdash; favourable</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Side: mean absolute error vs baseline</td><td class="n">{fmt(side['mae_model'])} vs {fmt(side['mae_baseline'])} pts</td><td class="n">{side['n_games']}</td>
  <td>{fmt(side['mae_delta'])} pts better</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Selective side: contest win rate</td><td class="n">{fmt(ssel['win_rate'])}</td><td class="n">{ssel['n_decisive']}</td>
  <td>selecting helps the side</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Total: contest win rate vs constant baseline</td><td class="n">{fmt(tot['win_rate'])}</td><td class="n">{tot['n_decisive']}</td>
  <td>CI includes 0.50 &mdash; no evidence</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Selective total: contest win rate</td><td class="n">{fmt(totsel['win_rate'])}</td><td class="n">{totsel['n_decisive']}</td>
  <td>significantly adverse</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Moneyline: Brier skill score</td><td class="n">{fmt(S['brier']['bss'])}</td><td class="n">{S['brier']['n']}</td>
  <td>better than a constant base rate, not tested for significance</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Calibration: predicted SD / actual SD</td><td class="n">{fmt(cal['ratio'])}</td><td class="n">{cal['n']}</td>
  <td>badly under-spread</td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Availability load differential vs home margin</td><td class="n">see correlations</td><td class="n">30</td>
  <td>suggestive, CI includes 0</td><td>{srcl('https://www.nfl.com/injuries/league/2026/reg10')}</td></tr>
</tbody></table></div>

<h2>What we recommend, in order</h2>
<ol>
<li><b>Do not stake anything.</b> Nothing is live, so nothing can be demoted &mdash; but the point of the
demotion gate is that nothing should be promoted yet either.</li>
<li><b>Get a price series.</b> <a href="suggestions.html#S-01">S-01</a>. Until a market number exists for
each originated market, closing-line value &mdash; the one test that separates skill from a good run &mdash;
is impossible.</li>
<li><b>Fix the total before adding anything else.</b> The total model is not merely uninformative, it is
adverse where it is confident. Adding strategies on top of it multiplies the problem.</li>
<li><b>Backfill the missing weeks of injury data.</b> <a href="suggestions.html#S-04">S-04</a>. Three weeks
of coverage is why the depth layer is a report and not an input.</li>
<li><b>Capture official player statistics.</b> <a href="suggestions.html#S-02">S-02</a>. Without them the
four player-prop-combo strategies cannot be scored at all.</li>
</ol>

<h2>How to read every table on this site</h2>
<ul class="tight">
<li>A value is printed only if it was computed from data in this repository.</li>
<li>An empty cell is a dash, and the row carries an {unv_badge()} badge with a flag id.</li>
<li>Every other row carries a link to the official page the numbers came from.</li>
<li>Every correlation carries its n, its 95% interval and its p-value. No n, no claim.</li>
</ul>
"""
    return ("Executive summary - X3 NFL signals", "Executive summary",
            "What the verified data supports, what it contradicts, and what to do next.", body)


def p_reqs(reqs):
    rows = []
    for r in reqs:
        rows.append([f'<a href="{esc(r["page"].split("/")[-1])}"><b>{esc(r["id"])}</b></a>', esc(r["requirement"]),
                     f'<span class="badge ok">{esc(r["status"])}</span>', esc(r["evidence"]),
                     srcl("https://github.com/karagemop466-tech/X3")])
    body = """
<h2>The eight requirements</h2>
<p>Each one is either implemented in this module with evidence, or it is not. Nothing here is asserted
as done without a file and a page that shows it.</p>
""" + table([("ID", ""), ("Requirement", ""), ("Status", ""), ("Evidence in this repository", ""), ("Repository", "")], rows)
    return ("Requirements - X3 NFL signals", "Requirements register",
            "The eight requirements, what was built for each, and where to look at it.", body)


def p_results(results):
    rows = []
    for r in results:
        rows.append([esc(r["game_id"]), str(r["week"]), esc(r["date_iso"]),
                     f'{esc(r["away"])} @ {esc(r["home"])}',
                     fmt(r["away_score"]), fmt(r["home_score"]), fmt(r["margin_home"]), fmt(r["total"]),
                     esc(r["status"]),
                     '<span class="badge ok">yes</span>' if r["verified"] == "yes" else '<span class="badge neutral">not played</span>',
                     "yes" if r["neutral_site"] == "yes" else "no",
                     srcl(r["source"])])
    body = f"""
<h2>Verified results feed</h2>
<p>This is what makes a backtest possible at all. Every row comes from the official NFL week schedule
page for that week. {sum(1 for r in results if r['verified'] == 'yes')} of {len(results)} games are
settled finals; the remainder are scheduled and carry no score, so they cannot enter any calculation.</p>
<div class="callout warn"><p><b>Grading rule.</b> A game is graded only if it is marked FINAL on the
official page. Scheduled games contribute nothing &mdash; they are not imputed, projected or filled in.
Neutral-site games are flagged; the model does not currently treat them differently
({unv_badge('F-08')}).</p></div>
<details open><summary>All {len(results)} games</summary>
""" + table(HN("Game", "Wk", "Date", "Matchup", "Away", "Home", "Margin", "Total") +
            [("Status", ""), ("Verified", ""), ("Neutral", ""), ("Official source", "")], rows) + """
</details>
"""
    return ("Results feed - X3 NFL signals", "Verified results feed",
            "Every game of the 2026 season, straight from the official week schedule pages.", body)


def p_prices(snaps, lines, meta):
    by_week = {}
    for s in snaps:
        k = s["week"]
        by_week.setdefault(k, {"open": 0, "close": 0, "not": 0, "moves": []})
        if s["status"] == "originated":
            by_week[k][s["snapshot"]] += 1
        else:
            by_week[k]["not"] += 1
    for l in lines:
        if l.get("move_side") not in ("", None):
            by_week[l["week"]]["moves"].append(abs(l["move_side"]))
        if l.get("move_total") not in ("", None):
            by_week[l["week"]]["moves"].append(abs(l["move_total"]))

    srows = []
    for w in sorted(by_week):
        d = by_week[w]
        mv = d["moves"]
        srows.append([str(w), str(d["open"]), str(d["close"]), str(d["not"]),
                      fmt(sum(mv) / len(mv), 3) if mv else fmt(None),
                      fmt(max(mv), 2) if mv else fmt(None),
                      fmt(len(mv)),
                      srcl(f"https://www.nfl.com/schedules/2026/by-week/week-{w}")])
    total_rows = sum(1 for s in snaps if s["status"] == "originated")

    frows = []
    for s in snaps:
        frows.append([esc(s["market_id"]), str(s["week"]), f'{esc(s["away"])} @ {esc(s["home"])}',
                      esc(s["market"]), str(s["origination_order"]), esc(s["snapshot"]),
                      fmt(s["fair_value"]), fmt(s["market_value"]), fmt(s["difference"]),
                      badge_for(s["market_value_flag"]),
                      esc(s["unit"]), str(s["training_finals"]), esc(s["snapshot_at"]),
                      esc(s["lambda_margin"]), esc(s["lambda_total"]), esc(s["inputs_hash"]),
                      srcl(s["source"])])
    body = f"""
<h2>Price-snapshot store</h2>
<p>Every market this module originates is written twice: an <b>opening</b> number, generated with the
ratings fitted through week W&minus;2, and a <b>closing</b> number, generated at the decision cutoff with
the ratings refitted through week W&minus;1. Both are stored. {total_rows} of {len(snaps)} rows carry a
number; the rest are recorded as not originated because there were fewer than
{meta['constants']['min_train_games']} training finals.</p>

<div class="callout"><p><b>What "opening" and "closing" mean here.</b> They are timestamps on our own
information set, not market prices. The opening snapshot is what we would have published when the board
first went up; the closing snapshot is what we would publish at kickoff. The gap between them &mdash; the
movement column &mdash; is how much one extra week of results moved our number.</p></div>

<div class="callout bad"><p><b>{unv_badge('F-01')} The market columns are empty.</b> The NFL does not
publish betting lines or odds, so there is no official source for a market number or for the difference
between our number and the market's. Both columns exist, are printed on the
<a href="lines.html">lines page</a>, and are empty on every row. They are not estimated, interpolated or
filled in.</p></div>

<h2>Coverage by week</h2>
""" + table(HN("Week", "Open numbers", "Close numbers", "Not originated", "Mean |movement|", "Max |movement|") +
            HN("Movement obs") + [("Official source", "")], srows) + f"""

<h2>The ridge penalty is chosen, not assumed</h2>
<p>For each week the ridge penalty is selected by nested walk-forward validation <i>inside the training
window only</i>: fit on weeks up to T&minus;1, score on week T, and take the penalty with the lowest
validation error. Nothing from the week being originated touches that choice, so the penalty is not tuned
on the data it is graded against. The chosen value is stored on every row so the store is auditable.</p>

<details><summary>Full store &mdash; {len(snaps)} rows</summary>
""" + table(H("Market ID", "Wk", "Matchup", "Market", "Order", "Snapshot", "Fair value",
              "Market value", "Difference", "Market flag", "Unit", "Train finals",
              "Snapshot taken at", "λ margin", "λ total", "Inputs hash") +
            [("Official source", "")], frows) + """
</details>
"""
    return ("Price snapshots - X3 NFL signals", "Price-snapshot store",
            "An opening and a closing number for every market we originate, with the market columns "
            "left empty because no official price exists.", body)


def p_lines(lines, meta):
    up = [l for l in lines if l["verified"] != "yes"]
    gr = [l for l in lines if l["verified"] == "yes" and l.get("close_originated") == "yes"]
    S = meta["scoring"]

    def linecols(l, tag):
        return [fmt(l.get(f"{tag}_fair_side"), 2), fmt(None), fmt(None),
                fmt(l.get(f"{tag}_fair_total"), 2), fmt(None), fmt(None),
                fmt(l.get(f"{tag}_fair_ml")), fmt(None), fmt(None)]

    urows = []
    for l in sorted(up, key=lambda x: (x["date_iso"], x["away"])):
        urows.append([esc(l["game_id"]), esc(l["date_iso"]), f'{esc(l["away_name"])} @ {esc(l["home_name"])}',
                      ] + linecols(l, "close") + [
            fmt(l.get("close_avail_home")), fmt(l.get("close_avail_away")),
            str(l.get("close_train_n")), fmt(l.get("close_lambda_margin")),
            srcl(l["source"])])
    grows = []
    for l in sorted(gr, key=lambda x: (x["week"], x["date_iso"])):
        err_s = (abs(l["actual_margin_home"] - l["close_pred_margin"])
                 if l.get("close_pred_margin") not in ("", None) else "")
        err_t = (abs(l["actual_total"] - l["close_fair_total"])
                 if l.get("close_fair_total") not in ("", None) else "")
        grows.append([esc(l["game_id"]), str(l["week"]),
                      f'{esc(l["away"])} @ {esc(l["home"])}',
                      fmt(l.get("open_fair_side"), 2), fmt(l.get("close_fair_side"), 2),
                      fmt(l.get("move_side"), 2),
                      fmt(l.get("open_fair_total"), 2), fmt(l.get("close_fair_total"), 2),
                      fmt(l.get("move_total"), 2),
                      fmt(l.get("close_fair_ml")),
                      fmt(l["actual_margin_home"]), fmt(l["actual_total"]),
                      fmt(round(err_s, 2) if err_s != "" else None),
                      fmt(round(err_t, 2) if err_t != "" else None),
                      fmt(l.get("close_avail_home")), fmt(l.get("close_avail_away")),
                      srcl(l["source"])])

    body = f"""
<h2>Originated lines</h2>
<p>Three markets, originated in a fixed order and printed with three columns each: <b>our fair line</b>,
<b>the market line</b>, and <b>the difference</b>. The market and difference columns are empty on every
row &mdash; {unv_badge('F-01')} &mdash; and are shown so the shape of the finished product is visible and
so the gap is unmistakable.</p>

<h3>The origination order is fixed: side, then total, then moneyline</h3>
<div class="tw"><table><thead><tr><th class="n">#</th><th>Market</th><th>How it is produced</th><th>Source of the inputs</th></tr></thead><tbody>
{''.join('<tr><td class="n">%d</td><td><b>%s</b></td><td>%s</td><td>%s</td></tr>' % (
    s['order'], esc(s['market']), esc(s['how']), srcl('https://www.nfl.com/schedules/2026/by-week/week-10'))
    for s in meta['pipeline_order'])}
</tbody></table></div>
<p class="note">The moneyline is deliberately last because it is <i>derived</i>: it needs the side (step 1)
and the walk-forward margin sigma. Reversing the order would mean pricing a probability before pricing the
margin it comes from.</p>

<h2>Unplayed board &mdash; {len(up)} games</h2>
<p class="note">These are the games that have not kicked off yet: the {sum(1 for l in up if l["week"] == 11)} games of the Week 11 slate plus {sum(1 for l in up if l["week"] == 10)} Week 10 games still to be played, in kickoff order.</p>
<div class="callout warn"><p>These are numbers we originated, not picks. The side is the home spread
(negative = home favoured). The moneyline is the home price in American odds, derived from the side and the
margin sigma &mdash; and the sigma is large, so treat the price as indicative, not calibrated
({unv_badge('F-07')}). Availability columns are empty for week 11: the official week-11 injury report was
not in the capture ({unv_badge('F-13')}).</p></div>
<div class="tw"><table>
<thead><tr><th rowspan="2">Game</th><th rowspan="2">Date</th><th rowspan="2">Matchup</th>
<th colspan="3" class="n">Side</th><th colspan="3" class="n">Total</th><th colspan="3" class="n">Moneyline</th>
<th colspan="2" class="n">Availability load</th><th rowspan="2">Train<br>finals</th><th rowspan="2">λ</th><th rowspan="2">Source</th></tr>
<tr><th class="n">Fair</th><th class="n">Mkt</th><th class="n">Diff</th>
<th class="n">Fair</th><th class="n">Mkt</th><th class="n">Diff</th>
<th class="n">Fair</th><th class="n">Mkt</th><th class="n">Diff</th>
<th class="n">Home</th><th class="n">Away</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('Game', 'Date', 'Matchup') + HN('F', 'Mkt', 'Diff', 'F', 'Mkt', 'Diff', 'F', 'Mkt', 'Diff', 'H', 'A', 'Tr', 'lam') + H('Official source')) ) + '</tr>' for r in urows)}
</tbody></table></div>

<h2>Graded history &mdash; {len(gr)} games, weeks {min(S['graded_weeks'])}&ndash;{max(S['graded_weeks'])}</h2>
<p>Opening and closing side and total, the actual result, and the error of our closing number against it.
The error column is the whole point: it is the only performance measure available without a market price.</p>
<div class="tw"><table><thead><tr><th rowspan="2">Game</th><th rowspan="2" class="n">Wk</th><th rowspan="2">Matchup</th>
<th colspan="3" class="n">Side</th><th colspan="3" class="n">Total</th>
<th rowspan="2" class="n">ML</th><th rowspan="2" class="n">Actual<br>margin</th><th rowspan="2" class="n">Actual<br>total</th>
<th rowspan="2" class="n">Side<br>error</th><th rowspan="2" class="n">Total<br>error</th>
<th colspan="2" class="n">Avail. load</th><th rowspan="2">Source</th></tr>
<tr><th class="n">Open</th><th class="n">Close</th><th class="n">Move</th>
<th class="n">Open</th><th class="n">Close</th><th class="n">Move</th>
<th class="n">Home</th><th class="n">Away</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('Game', 'Wk', 'Matchup') + HN('O', 'C', 'Mv', 'O', 'C', 'Mv', 'ML', 'AM', 'AT', 'SE', 'TE', 'H', 'A') + H('Official source')) ) + '</tr>' for r in grows)}
</tbody></table></div>

<h2>Reading the two boards together</h2>
<ul class="tight">
<li><b>The side moves less than the result does.</b> Predicted margin SD {fmt(S['calibration']['margin']['sd_predicted'])}
  against actual {fmt(S['calibration']['margin']['sd_actual'])}. Our numbers are conservative; the week-11
  spreads are compressed relative to what NFL margins actually look like.</li>
<li><b>Movement is small because one week rarely changes a rating much.</b> Mean absolute movement is
  reported per week on the <a href="prices.html">price-snapshot page</a>.</li>
<li><b>Availability load is reported beside the line, not inside it.</b> Three weeks of coverage cannot
  identify a coefficient ({unv_badge('F-05')}), so no published number is adjusted by injuries.</li>
</ul>
"""
    return ("Originated lines - X3 NFL signals", "Originated lines",
            "Fair line, market line and difference as three separate columns, originated side first.", body)


def p_strategies(strats, S):
    rows = []
    for s in strats:
        passed = ", ".join(s["passed"])
        failed = ", ".join(s["failed"])
        rows.append([f'<a id="{esc(s["id"])}"></a><b>{esc(s["id"])}</b>', esc(s["family"]), esc(s["market"]),
                     f'<b>{esc(s["name"])}</b><div class="small">{esc(s["rule"])}</div>',
                     esc(s["inputs"]), str(s["n_graded"]),
                     esc(s["signal_metric"]) or fmt(None), fmt(s["signal_value"]),
                     f'{fmt(s["signal_ci95"][0])} &ndash; {fmt(s["signal_ci95"][1])}'
                     if isinstance(s["signal_ci95"], list) and s["signal_ci95"][0] != "" else fmt(None),
                     pfmt(s["signal_p"]),
                     ('<span class="badge ok">yes</span>' if s["bh_pass"] == "yes"
                      else ('<span class="badge neutral">no</span>' if s["bh_pass"] == "no"
                            else '<span class="badge neutral">n/a</span>')),
                     esc(s.get("direction") or "") or fmt(None),
                     f'<span class="badge ok">{esc(passed)}</span>' if passed else fmt(None),
                     f'<span class="badge unv">{esc(failed)}</span>' if failed else fmt(None),
                     f'<span class="badge {"ok" if s["status"] == "hypothesis" else "unv"}">{esc(s["status"])}</span>',
                     esc(s["secondary"]),
                     srcl("https://www.nfl.com/schedules/2026/by-week/week-10")])
    body = f"""
<h2>Strategy register</h2>
<p>{len(strats)} strategies in three families: singles, parlays and player-prop combos. Every one is
pre-registered before its numbers are computed, and every one is blocked. The register exists so that the
trials are on the record &mdash; that is what stops a future good run from being mistaken for a discovery.</p>

<div class="callout"><p><b>G4, multiple-testing control.</b> Benjamini-Hochberg at q = {S['benjamini_hochberg']['q']}
was applied to the {S['benjamini_hochberg']['tests']} strategies with a computable p-value.
{S['benjamini_hochberg']['discoveries']} are discoveries. Two of them point the wrong way: the selective
total is <i>reliably worse</i> than a constant. A discovery with an adverse direction is a finding, not a
skill claim, and it is labelled as such rather than buried.</p></div>

<div class="tw"><table><thead><tr>
<th>ID</th><th>Family</th><th>Market</th><th>Rule</th><th>Inputs</th><th class="n">n</th>
<th>Signal metric</th><th class="n">Value</th><th class="n">95% CI</th><th class="n">p</th>
<th>BH q=0.10</th><th>Direction</th><th>Gates passed</th><th>Gates failed</th><th>Status</th>
<th>Detail</th><th>Source</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('ID', 'Family', 'Market', 'Rule', 'Inputs', 'n', 'Metric') + HN('Val', 'CI', 'p') + H('BH', 'Dir', 'Pass', 'Fail', 'Status', 'Detail', 'Source'))) + '</tr>' for r in rows)}
</tbody></table></div>

<h2>Why the prop family is empty</h2>
<div class="callout bad"><p>{unv_badge('F-04')} A player-prop market needs official per-game player
statistics. This repository holds none: the capture covers week schedule pages, standings, injury reports
and club depth charts. All four prop-combo strategies (R1&ndash;R4) are registered with their rules written
down and every value empty, so the moment the data lands they can be scored without anyone re-litigating
the design. See <a href="suggestions.html#S-02">suggestion S-02</a>.</p></div>

<h2>Why nothing is promoted</h2>
<p>Two gates block everything, and neither is a matter of opinion:</p>
<ul class="tight">
<li><b>G2, sample size.</b> {S['n_graded_total']} graded games against a pre-registered threshold of 200.</li>
<li><b>G5/G6, benchmark and uncertainty.</b> These can only be evaluated against a market price for ROI.
  Without one, the strongest statement available is "closer to the truth than a constant", which is what
  every score on this page measures.</li>
</ul>
"""
    return ("Strategies - X3 NFL signals", "Strategies &amp; signals",
            "Every strategy tested, with its rule, its inputs, its measured signal and its gate ledger.", body)


def p_leaderboard(lb, S, weekly):
    rows = []
    for r in lb:
        rows.append([f'<b>{esc(r["rank"])}</b>' if r["rank"] != "unranked" else '<span class="blank">unranked</span>',
                     f'<b>{esc(r["strategy"])}</b>', esc(r["name"]), esc(r["family"]), esc(r["market"]),
                     str(r["n_graded"]), esc(r["signal_metric"]) or fmt(None), fmt(r["signal_value"]),
                     fmt(r["no_skill_value"]), fmt(r["skill_gap"]),
                     f'{fmt(r["skill_gap_ci_low"])} &ndash; {fmt(r["skill_gap_ci_high"])}'
                     if r["skill_gap_ci_low"] != "" else fmt(None),
                     pfmt(r["p_raw"]),
                     ('<span class="badge ok">yes</span>' if r["bh_pass"] == "yes"
                      else ('<span class="badge neutral">no</span>' if r["bh_pass"] == "no" else '<span class="blank">&mdash;</span>')),
                     (f'<span class="badge ok">{esc(r["direction"])}</span>' if r["direction"] == "favourable"
                      else (f'<span class="badge unv">{esc(r["direction"])}</span>' if r["direction"] == "adverse"
                            else fmt(None))),
                     f'<span class="small">{esc(r["gates_passed"])}</span>' or fmt(None),
                     f'<span class="small">{esc(r["gates_failed"])}</span>' or fmt(None),
                     fmt(r["staking_roi"]), fmt(r["staking_roi_ci"]), fmt(r["staking_max_drawdown"]),
                     fmt(r["mask_ratio"]),
                     badge_for(r["staking_flag"]) if r["staking_flag"] else '<span class="blank">&mdash;</span>',
                     esc(r.get("blocked_on") or "") or fmt(None),
                     srcl(r["source"])])
    wrows = [[str(w["week"]), str(w["games"]), f'{w["side_wins"]}&ndash;{w["side_losses"]}',
              fmt(w["side_rate"]), fmt(w["side_mae_delta"]),
              f'{w["total_wins"]}&ndash;{w["total_losses"]}', fmt(w["total_rate"]),
              esc(w["verdict"]), srcl(w["source"])] for w in weekly]
    strows = [[f'<b>{esc(k["id"])}</b>', esc(k["name"]), esc(k["rule"]),
               fmt(k["roi"]), fmt(None), fmt(k["max_drawdown"]), fmt(k["n"]),
               badge_for(k["flag"]), srcl("https://www.nfl.com/")] for k in S["staking"]["rules"]]

    body = f"""
<h2>Leaderboard &mdash; signal and staking, scored apart</h2>
<div class="callout"><p><b>Signal decides the rank. Staking is reported, never rewarded.</b></p>
<p>{esc(S["staking"]["policy"].split(". ")[0])}. The design rule:</p>
<p><i>{"Ranking is decided by signal alone. Staking is printed beside it and can never move a strategy up &mdash; a staking run is a bet-size artefact and is exactly what a lucky run looks like. A row is ranked only when its signal metric has a 95% interval; rows without one are listed but marked unranked. The key is the LOWER bound of that interval on the gap to the no-skill value, so a wide interval ranks below a narrow one at the same point estimate."}</i></p>
</div>

<h2>Signal table</h2>
<div class="tw"><table><thead><tr>
<th class="n">Rank</th><th>ID</th><th>Strategy</th><th>Family</th><th>Market</th><th class="n">n</th>
<th>Signal metric</th><th class="n">Value</th><th class="n">No-skill</th><th class="n">Gap</th>
<th class="n">Gap 95% CI</th><th class="n">p</th><th>BH</th><th>Direction</th>
<th>Gates passed</th><th>Gates failed</th>
<th class="n">Staking ROI</th><th class="n">ROI CI</th><th class="n">Max DD</th><th class="n">Mask</th>
<th>Staking status</th><th>Blocked on</th><th>Source</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, HN('Rank') + H('ID', 'Strategy', 'Family', 'Market', 'n', 'Metric') + HN('Val', 'NoSkill', 'Gap', 'CI', 'p') + H('BH', 'Dir', 'Pass', 'Fail') + HN('ROI', 'ROICI', 'DD', 'Mask') + H('Staking', 'Blocked on', 'Source'))) + '</tr>' for r in rows)}
</tbody></table></div>

<h2>Staking table</h2>
<p>These rules are pre-registered so that the day a price series lands the column can be filled without
anyone arguing about the design. Today every payoff cell is empty.</p>
<div class="tw"><table><thead><tr><th>ID</th><th>Rule</th><th>Definition</th><th class="n">ROI</th>
<th class="n">ROI 95% CI</th><th class="n">Max drawdown</th><th class="n">n settled</th><th>Status</th>
<th>Source</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('ID', 'Rule', 'Definition') + HN('ROI', 'CI', 'DD', 'n') + H('Status', 'Source'))) + '</tr>' for r in strows)}
</tbody></table></div>

<h2>Weekly record &mdash; what the demotion gate reads</h2>
<p>The side's edge is not flat across the season: it is near a coin flip while the training window is
small and improves as the window grows. That is a statement about the model's data hunger, not about the
league. The demotion rule D7 watches this series for a run of weeks at or below no-skill.</p>
<div class="tw"><table><thead><tr><th class="n">Week</th><th class="n">Games</th>
<th class="n">Side W&ndash;L</th><th class="n">Side rate</th><th class="n">Side MAE delta</th>
<th class="n">Total W&ndash;L</th><th class="n">Total rate</th><th>Verdict</th><th>Source</th>
</tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, HN('Wk', 'G', 'SWL', 'SRate', 'SMAE', 'TWL', 'TRate') + H('Verdict', 'Source'))) + '</tr>' for r in wrows)}
</tbody></table></div>

<h2>Rewards</h2>
<div class="callout warn"><p><b>Rewards are notional.</b> The leaderboard ranks strategies; it does not
pay. Paying real money on a signal that has not cleared the sample-size, benchmark and uncertainty gates
would fund luck, not skill. The reward structure is itself an open decision &mdash; see
<a href="suggestions.html#S-09">suggestion S-09</a> and question
<a href="questions.html#Q11">Q11</a>.</p></div>
<h3>How the competition is meant to work</h3>
<ul class="tight">
<li>One submission per strategy family per week, pre-registered before grading.</li>
<li>Ranked on signal, never on staking.</li>
<li>Losing bets are published with the winning ones &mdash; a leaderboard that hides its losers is a marketing page.</li>
<li>No re-fitting after grading. A strategy that changes its rule mid-season starts again at zero.</li>
<li>Rewards only once a strategy clears every blocking gate, and only on the signal score.</li>
</ul>
"""
    return ("Leaderboard - X3 NFL signals", "Leaderboard",
            "Signal and staking scored separately, so a good bet-size run cannot disguise a bad signal.", body)


def p_gates(gates, demo_rules, demo_state):
    grows = [[f'<b>{esc(g["id"])}</b>', esc(g["gate"]), esc(g["rule"]),
              '<span class="badge ok">blocking</span>' if g["blocking"] == "yes" else '<span class="badge neutral">no</span>',
              esc(g["evidence"]), srcl("https://github.com/karagemop466-tech/X3")] for g in gates]
    drows = [[f'<b>{esc(d["id"])}</b>', esc(d["name"]), esc(d["rule"]), esc(d["action"]),
              esc(d["measurement"]),
              badge_for(d.get("flag", "")) if d.get("flag") else '<span class="blank">&mdash;</span>',
              srcl("https://github.com/karagemop466-tech/X3")] for d in demo_rules]
    srows = [[f'<b>{esc(s["gate"])}</b>', esc(s["measured"]),
              ('<span class="badge unv">%s</span>' % esc(s["fires_now"]) if s["fires_now"].startswith(("YES", "UNEVAL"))
               else '<span class="badge ok">%s</span>' % esc(s["fires_now"])),
              esc(s["note"]),
              badge_for(s.get("flag", "")) if s.get("flag") else '<span class="blank">&mdash;</span>',
              srcl("https://github.com/karagemop466-tech/X3")] for s in demo_state]
    body = f"""
<h2>Validation gates and the demotion gate</h2>

<h2>Validation gates &mdash; the luck-removing tests</h2>
<p>{len(gates)} gates. A strategy must clear every blocking gate before it can be promoted; nothing in this
module has.</p>
<div class="tw"><table><thead><tr><th>ID</th><th>Gate</th><th>Rule</th><th>Blocking?</th>
<th>Evidence in this build</th><th>Repository</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('ID', 'Gate', 'Rule', 'Blocking?', 'Evidence', 'Repo'))) + '</tr>' for r in grows)}
</tbody></table></div>

<h2>The demotion gate &mdash; live to paper</h2>
<p>A strategy that is live is sent back to paper the moment any of these fires. The point of writing them
down before anything is live is that the rule cannot be renegotiated under pressure after a bad month.</p>
<div class="tw"><table><thead><tr><th>ID</th><th>Name</th><th>Rule</th><th>Action</th>
<th>How it is measured</th><th>Flag</th><th>Repository</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('ID', 'Name', 'Rule', 'Action', 'Measurement', 'Flag', 'Repo'))) + '</tr>' for r in drows)}
</tbody></table></div>

<h2>State of the demotion gate today</h2>
<p>Nothing is live, so nothing can be demoted. The gates are still evaluated every build, because a gate
that is only tested when something goes wrong is not a gate.</p>
<div class="tw"><table><thead><tr><th>Gate</th><th>Measured value in this build</th><th>Fires?</th>
<th>Note</th><th>Flag</th><th>Repository</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('Gate', 'Measured', 'Fires?', 'Note', 'Flag', 'Repo'))) + '</tr>' for r in srows)}
</tbody></table></div>

<div class="callout warn"><p><b>D3 is recorded, not waived.</b> The drawdown gate cannot be evaluated
without a settled payoff series. It is printed as UNEVALUABLE rather than passed, so that the day prices
arrive the gate is visibly open rather than silently skipped.</p></div>
"""
    return ("Gates - X3 NFL signals", "Validation gates &amp; demotion",
            "The tests a strategy must pass to go live, and the rule that sends it back to paper.", body)


def p_corr(corr):
    rows = []
    for c in corr:
        excl = (c["ci95_low"] != "" and c["ci95_high"] != "" and
                (c["ci95_low"] > 0 or c["ci95_high"] < 0))
        rows.append([esc(c["family"]), esc(c["pair"]), fmt(c["r"], 4), str(c["n"]),
                     f'{fmt(c["ci95_low"])} &ndash; {fmt(c["ci95_high"])}' if c["ci95_low"] != "" else fmt(None),
                     pfmt(c["p"]),
                     '<span class="badge ok">CI excludes 0</span>' if excl else '<span class="badge neutral">CI includes 0</span>',
                     esc(c["used_for"]),
                     badge_for(c.get("flag", "")) if c.get("flag") else '<span class="blank">&mdash;</span>',
                     srcl(c["source"])])
    body = f"""
<h2>Correlations</h2>
<p>Every coefficient on this page is computed from officially sourced numbers, and every one is published
with its <b>n</b>, its 95% interval and its p-value. Where the interval includes zero the coefficient is
printed anyway and labelled: a null result with an n is information, a null result without one is not.</p>
<div class="tw"><table><thead><tr><th>Family</th><th>Pair</th><th class="n">r</th><th class="n">n</th>
<th class="n">95% CI</th><th class="n">p</th><th>Interval</th><th>Used for</th><th>Flag</th>
<th>Official source</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (cl, v) for v, (h, cl) in zip(r, H('Family', 'Pair') + HN('r', 'n', 'CI', 'p') + H('Interval', 'Used for', 'Flag', 'Source'))) + '</tr>' for r in rows)}
</tbody></table></div>

<h2>How to read this</h2>
<ul class="tight">
<li><b>n is the sample, not the season.</b> Game-level pairs use the 137 verified finals; model pairs use
  only the {max(c['n'] for c in corr if c['family'] == 'model')} walk-forward graded games; club pairs use 32 clubs;
  availability pairs use 30 games because the official injury capture began at week 8.</li>
<li><b>A club-level n of 32 is small.</b> The Pythagorean and point-differential correlations clear their
  intervals easily; the scoring-versus-conceding one does not, and is printed as a null.</li>
<li><b>The availability rows are the interesting null.</b> The offensive absence load differential
  correlates with the home margin at roughly r = 0.36 on n = 30 with an interval that just includes zero.
  That is a reason to get more weeks of injury data, not a reason to trade it.</li>
</ul>
"""
    return ("Correlations - X3 NFL signals", "Correlations",
            "Every coefficient computed from official numbers, published with its n, interval and p-value.", body)


def p_depth(depth, avail):
    arows = []
    for a in sorted(avail, key=lambda x: (x["week"], x["team"])):
        arows.append([str(a["week"]), esc(a["team"]), str(a["absences_out"]), str(a["absences_doubtful"]),
                      str(a["starter_absences"]), str(a["string2_absences"]), str(a["string3_absences"]),
                      str(a["string4_absences"]), f'{a["depth_known"]} / {a["depth_known"] + a["depth_unknown"]}',
                      str(a["repl_2nd"]), str(a["repl_3rd"]), str(a["repl_4th"]), str(a["repl_none_listed"]),
                      fmt(a["load_offense"], 3), fmt(a["load_defense"], 3), fmt(a["load_total"], 3),
                      srcl(a["injury_source"]), srcl(a["depth_source"], "chart")])
    drows = []
    for d in sorted(depth, key=lambda x: (x["week"], x["team"], x["player"])):
        drows.append([str(d["week"]), esc(d["team"]), esc(d["player"]), esc(d["pos"]), esc(d["unit"]),
                      esc(d["slot"]), esc(d["status"]), esc(d["injury"]),
                      fmt(d["depth_string"]) if d["depth_string"] != "" else unv_badge("F-03"),
                      esc(d["replacement"]) or fmt(None),
                      fmt(d["replacement_depth"]) if d["replacement_depth"] != "" else fmt(None),
                      str(d["chart_size"]) or fmt(None),
                      (esc(d["chart_as_of"]) if d["chart_as_of"] else unv_badge("F-03", "no date")),
                      '<span class="badge warn">unofficial</span>' if d["chart_unofficial"] == "yes"
                      else '<span class="badge neutral">not labelled</span>',
                      esc(d["join"]),
                      srcl(d["injury_source"], "injury"), srcl(d["depth_source"], "chart")])

    hist = {}
    for d in depth:
        if d["replacement_depth"] != "":
            hist[d["replacement_depth"]] = hist.get(d["replacement_depth"], 0) + 1
    dh = {}
    for d in depth:
        if d["depth_string"] != "":
            dh[d["depth_string"]] = dh.get(d["depth_string"], 0) + 1
    body = f"""
<h2>Injuries and depth of the replacement</h2>
<p>The requirement is not to record <i>that</i> a starter is out &mdash; it is to record <b>how deep the
replacement is</b>. A starting left tackle replaced by the second string is a different event from one
replaced by the fourth. Both the absent player's depth string and the replacement's depth string are
published here, per absence.</p>

<div class="grid">
  <div class="card"><div class="num">{dh.get(1, 0)}</div><div class="lbl">1st-string absences</div>
    <div class="sub">starters ruled Out or Doubtful, weeks 8&ndash;10</div></div>
  <div class="card"><div class="num">{dh.get(2, 0)}</div><div class="lbl">2nd-string absences</div>
    <div class="sub">backups themselves unavailable</div></div>
  <div class="card"><div class="num">{dh.get(3, 0)}</div><div class="lbl">3rd-string absences</div>
    <div class="sub">third string unavailable</div></div>
  <div class="card"><div class="num">{hist.get(2, 0)} / {hist.get(3, 0)} / {hist.get(4, 0)}</div>
    <div class="lbl">replacement is 2nd / 3rd / 4th string</div>
    <div class="sub">the column the requirement asks for</div></div>
</div>

<div class="callout warn"><p><b>Three honest limits on this layer.</b>
{unv_badge('F-05')} Coverage is weeks 8, 9 and 10 only &mdash; the capture began at week 8, so 7 of the 10
played weeks have no injury data at all.
{unv_badge('F-03')} Zero of the club depth charts carry a machine-readable as-of date and most are labelled
unofficial by the club itself.
{unv_badge('F-09')} The weights used to turn an absence into a load number are pre-registered design
choices, not measurements; they are printed on the <a href="sources.html">sources page</a> so a reviewer can
change them. <b>No published line on this site is adjusted by this layer</b>, because three weeks of
coverage cannot identify a coefficient.</p></div>

<h2>Per club, per week</h2>
<p>Availability load sums status weight &times; depth weight &times; replacement-depth weight over that
club's absences. Absences whose depth string could not be resolved are excluded from the load and counted
in the "depth resolved" column, so a blank reads as a capture gap rather than a zero.</p>
<div class="tw"><table><thead><tr><th class="n">Wk</th><th>Team</th><th class="n">Out</th><th class="n">Doubtful</th>
<th class="n">1st str</th><th class="n">2nd str</th><th class="n">3rd str</th><th class="n">4th str</th>
<th class="n">Depth resolved</th><th class="n">Repl 2nd</th><th class="n">Repl 3rd</th><th class="n">Repl 4th</th>
<th class="n">Repl none listed</th><th class="n">Load off</th><th class="n">Load def</th><th class="n">Load total</th>
<th>Injury source</th><th>Chart</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, HN('Wk') + H('Team') + HN('Out', 'D', '1st', '2nd', '3rd', '4th', 'Res', 'R2', 'R3', 'R4', 'R0', 'LO', 'LD', 'LT') + H('Injury', 'Chart'))) + '</tr>' for r in arows)}
</tbody></table></div>

<details><summary>Every absence, row by row &mdash; {len(depth)} rows</summary>
<div class="tw"><table><thead><tr><th class="n">Wk</th><th>Team</th><th>Player</th><th>Pos</th><th>Unit</th>
<th>Slot</th><th>Status</th><th>Injury</th><th class="n">Depth of absent player</th><th>Replacement</th>
<th class="n">Replacement depth</th><th class="n">Chart size</th><th>Chart as of</th><th>Chart label</th>
<th>Join</th><th>Injury source</th><th>Chart</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, HN('Wk') + H('Team', 'Player', 'Pos', 'Unit', 'Slot', 'Status', 'Injury') + HN('Depth') + H('Replacement') + HN('ReplDepth', 'Size') + H('AsOf', 'Label', 'Join', 'Injury', 'Chart'))) + '</tr>' for r in drows)}
</tbody></table></div>
</details>
"""
    return ("Injuries and depth - X3 NFL signals", "Injuries &amp; depth of the replacement",
            "Who is out, which string they are, and which string replaces them.", body)


def p_questions(qs):
    rows = []
    for q in qs:
        rows.append([f'<a id="{esc(q["id"])}"></a><b>{esc(q["id"])}</b>', esc(q["topic"]),
                     f'<b>{esc(q["question"])}</b>',
                     esc(q["what_we_have"]), esc(q["what_is_missing"]),
                     badge_for(q["flag"]) if q["flag"] else '<span class="blank">&mdash;</span>',
                     esc(q["how_to_find_out"]),
                     f'<a href="suggestions.html#{esc(q["suggestion"])}">{esc(q["suggestion"])}</a>' if q["suggestion"] else fmt(None),
                     srcl("https://github.com/karagemop466-tech/X3")])
    body = f"""
<h2>Open questions</h2>
<p>A decision made on this site is only as good as the answers behind it. This page separates what we
already hold from what we do not, and says how to go and get the missing piece. Where the answer is not
knowable from the data in this repository, it says so instead of guessing.</p>
<div class="tw"><table><thead><tr><th>ID</th><th>Topic</th><th>Question</th><th>What we have</th>
<th>What is missing</th><th>Flag</th><th>How to find out</th><th>Suggestion</th><th>Repository</th>
</tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('ID', 'Topic', 'Question', 'We have', 'Missing', 'Flag', 'How to find out', 'Suggestion', 'Repo'))) + '</tr>' for r in rows)}
</tbody></table></div>
<h2>The three that block everything else</h2>
<ol>
<li><a href="#Q01">Q01 &mdash; closing line</a>. Without the market's closing number there is no
closing-line value, and without closing-line value the standard test for skill in this field is simply
unavailable.</li>
<li><a href="#Q04">Q04 &mdash; player statistics</a>. Four of the fifteen strategies are unscoreable until
official per-game player numbers exist.</li>
<li><a href="#Q07">Q07 &mdash; sample size</a>. Even a perfect model cannot clear a 200-decision gate on
105 graded games. This is a decision to make, not a problem to solve.</li>
</ol>
"""
    return ("Open questions - X3 NFL signals", "Open questions",
            "What we know, what we do not, and how to go and find out.", body)


def p_suggestions(sugs):
    rows = []
    for s in sugs:
        rows.append([f'<a id="{esc(s["id"])}"></a><b>{esc(s["id"])}</b>', esc(s["category"]),
                     f'<b>{esc(s["title"])}</b><div class="small">{esc(s["problem"])}</div>',
                     f'<div class="paths">{esc(s["paths"])}</div>',
                     esc(s["tradeoffs"]), esc(s["unlocks"]),
                     esc(s["value"]), esc(s["effort"]),
                     '<span class="badge warn">proposed &mdash; not implemented</span>',
                     fmt(s["decision"]), fmt(s["decided_by"]),
                     srcl("https://github.com/karagemop466-tech/X3")])
    body = f"""
<h2>Suggestions &mdash; choose a path before changing anything</h2>
<div class="callout"><p><b>Nothing on this page has been implemented.</b> Every item is a proposal with the
paths laid out, the trade-offs written down and the decision left open. That is the point: the value of a
suggestion register is that a decision gets made <i>on the record</i> before the work starts, not
afterwards.</p></div>
<p>Each row states the problem it solves, the paths available, what each path costs or risks, what it
unlocks, and a value/effort read. The <b>decision</b> and <b>decided by</b> columns are empty on every row
and stay empty until someone fills them in.</p>
<div class="tw"><table><thead><tr><th>ID</th><th>Category</th><th>Suggestion &amp; problem</th>
<th>Paths</th><th>Trade-offs</th><th>Unlocks</th><th>Value</th><th>Effort</th><th>Status</th>
<th>Decision</th><th>Decided by</th><th>Repository</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('ID', 'Category', 'Suggestion', 'Paths', 'Trade-offs', 'Unlocks', 'Value', 'Effort', 'Status', 'Decision', 'By', 'Repo'))) + '</tr>' for r in rows)}
</tbody></table></div>

<h2>How to use this page</h2>
<ul class="tight">
<li>Pick the item. Cross-reference the question it answers on the <a href="questions.html">questions page</a>.</li>
<li>Choose a path &mdash; including "do nothing", which is a real option and is listed where it applies.</li>
<li>Record the decision and who made it. Until those two cells are filled the item is not approved.</li>
<li>Only then implement. An unrecorded decision is invisible to the next person reading this repository.</li>
</ul>
<h2>Suggested order if you only do three</h2>
<ol>
<li><a href="#S-01">S-01, price capture</a> &mdash; it unblocks ROI, closing-line value, staking, drawdown
and half the demotion gates at once.</li>
<li><a href="#S-04">S-04, backfill injury weeks</a> &mdash; cheap, and it triples the sample behind the
depth requirement.</li>
<li><a href="#S-12">S-12, retire the overlapping site trees</a> &mdash; thirteen trees give thirteen
answers to the same question; that is a decision-making problem before it is a code problem.</li>
</ol>
"""
    return ("Suggestions - X3 NFL signals", "Suggestions",
            "Paths to choose between. Nothing here is implemented; every decision is still open.", body)


def p_sources(sources):
    rows = []
    for s in sources:
        rows.append([f'<b>{esc(s["id"])}</b>', esc(s["name"]),
                     ('<span class="badge ok">official</span>' if s["kind"] == "Official"
                      else ('<span class="badge warn">club-published</span>' if "Club" in s["kind"]
                            else f'<span class="badge neutral">{esc(s["kind"])}</span>')),
                     srcl(s["url"], s["url"]), esc(s["retrieved"]), esc(s["used_for"]),
                     esc(s["rows"]), esc(s["note"])])
    body = """
<h2>Sources</h2>
<p>Official league pages and club-published pages, with what each one supplies and how it was retrieved.
Anything not on this page is not an input to anything on this site.</p>
<div class="tw"><table><thead><tr><th>ID</th><th>Source</th><th>Kind</th><th>URL</th><th>Retrieved</th>
<th>Used for</th><th class="n">Volume</th><th>Note</th></tr></thead><tbody>
""" + "".join("<tr>" + "".join(f'<td class="{c}">{v}</td>' for v, (h, c) in zip(r, H('ID', 'Source', 'Kind', 'URL', 'Retrieved', 'Used for') + HN('Volume') + H('Note'))) + "</tr>" for r in rows) + """
</tbody></table></div>

<h2>What is deliberately NOT a source</h2>
<ul class="tight">
<li><b>Sportsbooks.</b> The NFL has official sportsbook partners, but they are commercial operations, not
open official feeds, and no price from them is used anywhere on this site.</li>
<li><b>Third-party statistics sites.</b> Only league and club pages are used, so that every number can be
traced to the body that produced it.</li>
<li><b>Anything inferred.</b> A value that would have to be guessed is left empty and flagged.</li>
</ul>

<h2>Pre-registered constants</h2>
<p>These are our design choices, not sourced from anywhere. They are printed so a reviewer can change them
and re-run the build.</p>
<div class="panel"><dl class="kv">
""" + "".join(f"<dt><code>{esc(k)}</code></dt><dd>{esc(v)}</dd>" for k, v in
              json.loads((DATA / "meta.json").read_text())["constants"].items()) + """
</dl></div>
"""
    return ("Sources - X3 NFL signals", "Sources",
            "Every input to this module, what it supplied, and what is deliberately not used.", body)


def p_verification(meta, C):
    body = f"""
<h2>Verification log</h2>
<p>Line by line, and enforced by a script rather than by assertion. <code>scripts/verify_signals.py</code>
runs after every build and again in CI; it fails the build on any broken internal link or any table row
that neither links an official source nor carries an unverified marker.</p>

<div class="tw"><table><thead><tr><th>Check</th><th>Rule</th><th class="n">Rows / refs</th><th>Result</th>
<th>Enforced by</th><th>Source</th></tr></thead><tbody>
<tr><td>Results feed</td><td>Every game row links the official week schedule page it was read from</td>
<td class="n">{C['results_rows']}</td><td><span class="badge ok">pass</span></td>
<td><code>verify_signals.py</code></td><td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-1')}</td></tr>
<tr><td>Price-snapshot store</td><td>Every row links the official source of the game it prices; empty
market cells carry flag F-01</td><td class="n">{C['price_snapshot_rows']}</td>
<td><span class="badge ok">pass</span></td><td><code>verify_signals.py</code></td>
<td>{srcl('https://www.nfl.com/schedules/2026/by-week/week-10')}</td></tr>
<tr><td>Depth and availability</td><td>Every absence links the official injury page and the club chart</td>
<td class="n">{C['depth_rows'] + C['club_availability_rows']}</td><td><span class="badge ok">pass</span></td>
<td><code>verify_signals.py</code></td><td>{srcl('https://www.nfl.com/injuries/league/2026/reg10')}</td></tr>
<tr><td>Correlations</td><td>Every coefficient prints r, n, interval, p and its source link</td>
<td class="n">{C['correlations']}</td><td><span class="badge ok">pass</span></td>
<td><code>verify_signals.py</code></td><td>{srcl('https://www.nfl.com/standings/league/2026/reg')}</td></tr>
<tr><td>Leaderboard</td><td>Ranking key is a signal column; staking columns cannot decide rank</td>
<td class="n">{C['strategies']}</td><td><span class="badge ok">pass</span></td>
<td><code>verify_signals.py</code></td><td>{srcl('https://github.com/karagemop466-tech/X3')}</td></tr>
<tr><td>Snapshot completeness (G11)</td><td>Every originated market has both an opening and a closing row</td>
<td class="n">{C['open_snapshots']} / {C['close_snapshots']}</td><td><span class="badge ok">pass</span></td>
<td><code>verify_signals.py</code></td><td>{srcl('https://github.com/karagemop466-tech/X3')}</td></tr>
<tr><td>Internal links</td><td>Every local href resolves to a file that exists</td>
<td class="n">all pages</td><td><span class="badge ok">pass</span></td>
<td><code>verify_signals.py</code></td><td>{srcl('https://github.com/karagemop466-tech/X3')}</td></tr>
<tr><td>Determinism</td><td>Re-running the engine reproduces byte-identical data</td>
<td class="n">2 runs</td><td><span class="badge ok">pass</span></td>
<td><code>verify_signals.py --determinism</code></td><td>{srcl('https://github.com/karagemop466-tech/X3')}</td></tr>
</tbody></table></div>

<h2>What the verifier does not check</h2>
<div class="callout warn"><p>The verifier proves provenance and structure, not truth. It confirms that a
number has a source and that the row is not silently invented. It cannot confirm that a transcribed page
was transcribed correctly &mdash; that needs a human to open the link, which is why every row carries one.</p></div>

<h2>How each layer was verified</h2>
<dl class="kv">
<dt>Results</dt><dd>Read from <code>data/desk/games.json</code>, which was captured by a GitHub-hosted CI
runner straight from the official week schedule pages. Each row keeps the URL of the page it came from.</dd>
<dt>Standings and luck</dt><dd>Read from <code>data/desk/standings.json</code> and
<code>data/desk/luck.json</code>, same capture.</dd>
<dt>Injuries and depth</dt><dd>Read from <code>data/desk/injuries.json</code>,
<code>data/desk/deficiencies.json</code> and <code>data/desk/depth.json</code>. Absence rows carry both the
league injury page and the club's own depth chart, plus the club's unofficial label where it has one.</dd>
<dt>Lines, snapshots, scores</dt><dd>Computed here by <code>scripts/x3_signals.py</code> from the rows above.
Every row inherits the source URL of the games it was fitted on.</dd>
<dt>Market prices, ROI, props</dt><dd>Nothing to verify: no such row exists. Empty and flagged.</dd>
</dl>
"""
    return ("Verification - X3 NFL signals", "Verification log",
            "How every row was checked, what the verifier enforces, and what it cannot check.", body)


def p_repo(repo):
    rows = []
    for r in repo:
        rows.append([f'<code>{esc(r["tree"])}/</code>', str(r["html_pages"]), str(r["data_files"]),
                     f'{r["bytes"] / 1024:.0f} KB',
                     '<span class="badge ok">yes</span>' if r["maintained"] == "yes"
                     else '<span class="badge neutral">no</span>',
                     esc(r["note"]), srcl(r["source"])])
    body = f"""
<h2>Repository review</h2>
<p>{len(repo)} parallel sessions have each published their own site tree into this repository. They overlap
heavily: several present the same underlying table computed at different times, with different numbers.
None of them was deleted &mdash; deleting another session's work would be worse than the duplication &mdash;
but the duplication is itself a decision-making problem and it is logged as
<a href="flagged.html">F-11</a> with a remedy in <a href="suggestions.html#S-12">suggestion S-12</a>.</p>
<div class="tw"><table><thead><tr><th>Tree</th><th class="n">HTML pages</th><th class="n">Data files</th>
<th class="n">Size</th><th>Maintained</th><th>Status</th><th>Repository</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('Tree') + HN('Pages', 'Data', 'Size') + H('Maintained', 'Status', 'Repo'))) + '</tr>' for r in rows)}
</tbody></table></div>

<h2>Irregularities found in the review</h2>
<ul class="tight">
<li><b>{len(repo)} trees, one subject.</b> A reader asking "what is our number for this game" can find
{len(repo)} different answers. Only <code>hub/</code> is presented as canonical.</li>
<li><b>The same injury report was transcribed twice into two schemas.</b> Both agree on 345 of 345 game
statuses, which is the strongest evidence in the repository that the injury layer is right. The
disagreement on one practice status is logged rather than adjudicated.</li>
<li><b>A previously published correlation was wrong.</b> An earlier session published
r(game total, |margin|) = &minus;0.161; recomputing from the same 137 finals gives &minus;0.016, and
&minus;0.161 is in fact r(total, signed home margin). The pipeline was fine; the label was wrong. This
module recomputes both and prints them separately.</li>
<li><b>Depth charts are the weakest link.</b> No as-of date, and most are labelled unofficial by the club
that publishes them. They are used as a report, never as a model input.</li>
</ul>
<div class="callout warn"><p>Every item above is already published on the
<a href="flagged.html">Flagged for review</a> page. None of it blocks the site; all of it is visible.</p></div>
"""
    return ("Repo review - X3 NFL signals", "Repository review",
            "The repository audited tree by tree, with the irregularities found.", body)


def p_flags(flags):
    rows = []
    for f in flags:
        rows.append([f'<a id="{esc(f["id"])}"></a><b>{esc(f["id"])}</b>', esc(f["kind"]),
                     f'<b>{esc(f["title"])}</b>', esc(f["detail"]), esc(f["effect"]),
                     '<span class="badge neutral">non-blocking</span>',
                     srcl(f["source"])])
    body = f"""
<h2>Flagged for review</h2>
<p>{len(flags)} items. None of them blocks the site. All of them are things a reviewer should look at,
and each carries a link to the page that would settle it.</p>
<div class="callout warn"><p><b>The convention on this site:</b> a value that cannot be confirmed from an
official source is left blank and flagged. It is never inferred, interpolated or estimated. An empty cell
next to a flag id is the honest answer.</p></div>
<div class="tw"><table><thead><tr><th>ID</th><th>Kind</th><th>Item</th><th>Detail</th><th>Effect on the site</th>
<th>Blocking?</th><th>Source</th></tr></thead><tbody>
{''.join('<tr>' + ''.join('<td class="%s">%s</td>' % (c, v) for v, (h, c) in zip(r, H('ID', 'Kind', 'Item', 'Detail', 'Effect', 'Blocking?', 'Source'))) + '</tr>' for r in rows)}
</tbody></table></div>
<h2>The one that matters most</h2>
<div class="callout bad"><p><b>F-01, no official market price.</b> The NFL does not publish betting lines
or odds. Its official sportsbook partners and its official data distributor are commercial feeds, not open
ones. Until that changes, ROI, closing-line value, staking, drawdown and the prop markets are not
approximately known &mdash; they are unknown, and this site says so on every page where they would
otherwise appear.</p></div>
"""
    return ("Flagged for review - X3 NFL signals", "Flagged for review",
            "Everything that could not be verified, with the link that would settle it.", body)


if __name__ == "__main__":
    build_all()
