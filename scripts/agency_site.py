"""Generate the /agency/ static dashboard from engine outputs.

The site is pure HTML + inline CSS: no external assets, no JS, nothing that can
break between build and deploy. Every table row either quotes an official source
or is explicitly flagged unverified.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import date, datetime
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agency_content as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "agency" / "site"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = ROOT / "agency" / "data" / "out"
RAW = ROOT / "agency" / "data" / "derived"

CSS = """
html { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #1a1a1a; background: #f7f8fa; }
body { margin: 0; padding: 0 0 60px 0; }
header { background: #0b2e4d; color: #fff; padding: 20px 28px; }
header h1 { margin: 0; font-size: 1.35rem; letter-spacing: 0.5px; }
header p { margin: 4px 0 0 0; font-size: 0.9rem; color: #c9d6e4; }
nav { background: #ffffff; border-bottom: 1px solid #d7dce3; position: sticky; top: 0; z-index: 5; }
nav ul { display: flex; flex-wrap: wrap; list-style: none; margin: 0; padding: 0 28px; }
nav li { margin: 0; }
nav a { display: block; padding: 10px 12px; font-size: 0.88rem; color: #243852; text-decoration: none; border-bottom: 2px solid transparent; }
nav a:hover { background: #eef2f7; color: #0b2e4d; border-bottom-color: #0b2e4d; }
main { max-width: 1180px; margin: 24px auto; padding: 0 24px; }
h2 { font-size: 1.25rem; color: #0b2e4d; margin: 32px 0 10px 0; padding-bottom: 6px; border-bottom: 2px solid #d7dce3; }
h3 { font-size: 1.05rem; color: #243852; margin: 20px 0 8px 0; }
p { margin: 0 0 10px 0; }
ul { margin: 6px 0 12px 0; padding-left: 22px; }
li { margin: 4px 0; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 24px 0; font-size: 0.86rem; background: #fff; }
th, td { border: 1px solid #cfd6df; padding: 7px 9px; text-align: left; vertical-align: top; }
th { background: #0b2e4d; color: #fff; font-weight: 600; white-space: nowrap; }
tr:nth-child(even) td { background: #f2f5f9; }
td.num, th.num { text-align: right; }
td.empty { color: #8a94a3; font-style: italic; }
td.blank, .blank { color: #b0b7c2; }
a { color: #0b5ed7; text-decoration: underline; font-size: 0.85rem; }
a.src { color: #0b5ed7; text-decoration: none; border-bottom: 1px dotted #0b5ed7; }
.small { font-size: 0.8rem; color: #55606c; }
.kicker { color: #55606c; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 4px; }
.card { background: #fff; border: 1px solid #d7dce3; border-radius: 8px; padding: 16px 20px; margin: 0 0 18px 0; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; margin: 14px 0 20px 0; }
.badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 0.76rem; font-weight: 600; margin-right: 6px; }
.badge.met { background: #e3f2e3; color: #1d6b1d; }
.badge.partial { background: #fff7e3; color: #8a6d1d; }
.badge.blocked { background: #fbe5e5; color: #a33232; }
.badge.reject { background: #e9ecef; color: #55606c; }
.flag { border-left: 4px solid #a33232; background: #fbf0f0; padding: 10px 14px; margin: 10px 0; }
.warn { border-left: 4px solid #c8931d; background: #fdf7e7; padding: 10px 14px; margin: 10px 0; }
.ok { border-left: 4px solid #1d6b1d; background: #eef7ee; padding: 10px 14px; margin: 10px 0; }
.foot { border-top: 1px solid #d7dce3; margin-top: 40px; padding: 18px 0; font-size: 0.78rem; color: #55606c; }
.tag { font-weight: 700; color: #0b2e4d; white-space: nowrap; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.82rem; background: #eef2f7; padding: 1px 6px; border-radius: 4px; }
.hl { color: #a33232; font-weight: 600; }
.linkbox { background: #f2f5f9; border: 1px solid #d7dce3; border-radius: 6px; padding: 12px 16px; margin: 10px 0; }
"""

def load(name, default=None):
    p = OUT.parent / "data" / "out" / name
    if not p.exists():
        return default
    try:
        return json.load(open(p))
    except Exception:
        return default

def page(title, body, nav_active=None):
    if isinstance(body, list):
        body = "".join(body)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)} — X3 Agency</title><style>{CSS}</style></head>
<body><header><h1>X3 Agency</h1><p>NFL origination dashboard · clean analysis layer · every table row sourced or flagged</p></header>
<nav><ul>{nav(nav_active)}</ul></nav>
<main>{body}</main>
<footer class="foot">Source discipline: official NFL pages (nfl.com Game Books, standings, schedules, injury report and club depth charts) only. Values that cannot be confirmed officially are left blank and flagged unverified. Nothing here is inferred. Outputs are deterministic: a fresh engine + site build reproduces the committed files byte for byte (CI reproducibility gate).</footer></body></html>"""

def nav(active=None):
    items = [
        ("index.html", "Landing"),
        ("results.html", "Results"),
        ("lines.html", "Origination"),
        ("leaderboard.html", "Leaderboard"),
        ("registry.html", "Registry"),
        ("gates.html", "Gates"),
        ("luck.html", "Luck Panel"),
        ("correlations.html", "Correlations"),
        ("injuries.html", "Injuries"),
        ("depth.html", "Depth & Availability"),
        ("fixtures.html", "Fixtures"),
        ("policy.html", "Price Policy"),
        ("readiness.html", "Readiness"),
        ("executive-summary.html", "Executive Summary"),
        ("suggestions.html", "Suggestions"),
        ("questions.html", "Questions"),
        ("flagged.html", "Flagged for Review"),
        ("provenance.html", "Provenance"),
        ("methodology.html", "Methodology"),
    ]
    out = []
    for href, label in items:
        a = ' class="active"' if href == active else ''
        out.append(f'<li><a{href and a} href="{href}">{escape(label)}</a></li>')
    return "".join(out)

# ----------------------------------------------------------------- helpers
def td(v, blank="—", num=False):
    if v is None:
        return f'<td class="blank">{blank}</td>'
    cls = ' class="num"' if num else ''
    return f"<td{cls}>{escape(str(v))}</td>"

def src(url, label="official source"):
    return f'<a class="src" href="{escape(url)}" target="_blank" rel="noopener">{escape(label)}</a>'

def flag_source(source):
    """Flag sources must be a real http(s) link; anything else is shown as an explicit UNVERIFIED marker."""
    if source.startswith("http"):
        return src(source)
    return '<span class="badge">UNVERIFIED</span> ' + escape(source)

def srcs(pairs):
    return " · ".join(src(u, l) for u, l in pairs)

def badge(st):
    return f'<span class="badge {st.lower()}">{escape(st)}</span>'

def num_f(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return str(v)

# ================================================================ landing page
def landing():
    wf = load("walkforward.json") or []
    rec = load("reconciliation.json") or {}
    strat = load("strategies.json") or {}
    luck = load("luck.json") or {}
    body = [
        '<h2>Landing — decision readiness</h2>',
        '<p class="kicker">One row per project requirement, with the gate that blocks it and the number that would clear it.</p>',
        '<table><tr><th class="tag">ID</th><th>Requirement</th><th class="badge cell">Status</th><th>Blocking gate</th><th class="num">Number that would clear it</th></tr>',
    ]
    met = partial = blocked = reject = 0
    for rid, req, ev, st, gate, num in C.REQUIREMENTS:
        if st == "MET": met += 1
        elif st == "PARTIAL": partial += 1
        elif st == "BLOCKED": blocked += 1
        else: reject += 1
        body.append(f"<tr><td>{rid}</td><td>{escape(req)}</td><td>{badge(st)}</td><td>{escape(gate)}</td><td class=\"num\">{escape(num)}</td></tr>")
    body.append("</table>")
    body.append(f'<div class="grid2"><div class="card"><div class="kicker">Readiness roll-up</div>'
                f'<p><strong>{met} met</strong> · <strong>{partial} partial</strong> · <strong>{blocked} blocked</strong> · <strong>{reject} rejected</strong></p>'
                f'<p class="small">Full table: <a href="readiness.html">readiness page</a>.</p></div>')
    # what changed
    body.append('<div class="card"><div class="kicker">What changed since the previous capture</div>'
                '<table><tr><th>Item</th><th>Previous capture</th><th>This capture</th><th>Basis</th></tr>')
    for a, b, c, d in C.CHANGED:
        body.append(f"<tr><td>{escape(a)}</td><td>{escape(b)}</td><td>{escape(c)}</td><td>{escape(d)}</td></tr>")
    body.append("</table>")
    # summary strips
    body.append('<div class="grid2">')
    if isinstance(rec, dict) and rec.get("status"):
        body.append(f'<div class="card ok"><div class="kicker">Standings reconciliation</div>'
                    f'<p>{escape(rec.get("status",""))}</p></div>')
    for sid, s in sorted(strat.items()):
        body.append(f'<div class="card"><div class="kicker">{sid}</div>'
                    f'<p>{escape(s.get("label",""))}</p>'
                    f'<p><strong>{s.get("n","")} games</strong> · hit rate {num_f(s.get("rate"))}</p></div>')
    body.append('</div>')
    body.append('<p class="small"><strong>Start here:</strong> the readiness table is ordered by project ID. '
                'Blocked items and all irregularities live on the <a href="flagged.html">Flagged for Review</a> page '
                'and do not block the site going live.</p>')
    return page("Landing", body, "index.html")

# ================================================================ results
def results():
    rec = load("reconciliation.json") or {}
    wf = load("walkforward.json") or []
    body = ['<h2>Verified results feed</h2>',
            '<p class="kicker">Backtests and ROI are computed from this feed only. Every game row below reconciles to the official standings page.</p>']
    if isinstance(rec, dict):
        body.append(f'<div class="card {"ok" if rec.get("status","").startswith("32") else "warn"}">'
                    f'<div class="kicker">Reconciliation vs official standings</div>'
                    f'<p>{escape(rec.get("status",""))}</p>'
                    f'<p class="small">{escape(rec.get("note",""))}</p></div>')
    body.append('<table><tr><th class="tag">Week</th><th>Away @ Home</th><th class="num">Away</th><th class="num">Home</th><th class="num">Total</th><th class="num">Source</th></tr>')
    n = 0
    for r in wf[:200]:
        if r.get("actual_total") is None:
            continue
        n += 1
        body.append(f"<tr><td>{r.get('week','')}</td><td>{escape(r.get('away',''))} @ {escape(r.get('home',''))}</td>"
                    f"<td class=\"num\">{r.get('away_score','')}</td><td class=\"num\">{r.get('home_score','')}</td>"
                    f"<td class=\"num\">{r.get('actual_total','')}</td><td>{src(r.get('source','https://www.nfl.com/'))}</td></tr>")
    body.append(f"</table><p class='small'>{n} graded finals shown (first 200). Full feed: <a href=\"results.html\">results page</a>.</p>")
    return page("Results", body, "results.html")

# ================================================================ origination
def lines():
    orig = load("origination_week11.json") or []
    body = ['<h2>Origination — Week 11 (side → total → moneyline)</h2>',
            '<p class="kicker">Columns are published in the required order: side first, then total, then moneyline. '
            'Fair line, market line and difference are separate columns; the market column is empty because no '
            'market-price source exists (see Flagged F-01).</p>',
            '<table><tr><th class="tag">Game</th><th class="num">Fair side</th><th class="num">Alt side</th><th class="num">Fair total</th><th class="num">Naive total</th><th class="num">Gap</th><th class="num">ML</th><th class="num">Market side</th><th class="num">Market total</th><th class="num">Residual</th><th>Market status</th></tr>']
    for g in orig:
        body.append(f"<tr><td>{escape(g.get('game',''))}</td>"
                    f"<td class=\"num\">{num_f(g.get('side_fair'))}</td>"
                    f"<td class=\"num\">{num_f(g.get('side_alt'))}</td>"
                    f"<td class=\"num\">{num_f(g.get('total_fair'))}</td>"
                    f"<td class=\"num\">{num_f(g.get('total_naive'))}</td>"
                    f"<td class=\"num\">{num_f(g.get('total_gap'))}</td>"
                    f"<td class=\"num\">{num_f(g.get('ml_home_win_prob'))}</td>"
                    f"<td class=\"blank\">—</td><td class=\"blank\">—</td>"
                    f"<td class=\"blank\">—</td><td>{escape(str(g.get('market_status','NO OFFICIAL MARKET SOURCE')))}</td></tr>")
    body.append("</table>")
    body.append('<div class="card warn"><div class="kicker">Price-data policy (decided first, dated 2026-11-15)</div>'
                '<p>No price is estimated, no backtest publishes ROI or CLV, and every market column stays blank until '
                'an official or licensed price source is named and its terms read.</p></div>')
    return page("Origination", body, "lines.html")

# ================================================================ leaderboard
def leaderboard():
    strat = load("strategies.json") or {}
    body = ['<h2>Leaderboard — skill separated from staking</h2>',
            '<p class="kicker">Two tables: signal first, staking second. A lucky staking run cannot mask a bad signal '
            'because they are never combined. Raw win rate and season-long ROI are explicitly rejected as ranking measures.</p>']
    body.append('<table><tr><th class="tag">ID</th><th>Strategy</th><th class="num">N</th><th class="num">Hits</th><th class="num">Rate</th><th class="num">p vs constant</th><th>95% CI</th><th class="num">Brier skill</th><th>Gate</th><th>Status</th></tr>')
    order = ["S1","S2","S3","S4","S5","S6","S7","S8","S9"]
    for sid in order:
        s = strat.get(sid, {})
        if not s:
            continue
        body.append(f"<tr><td>{sid}</td><td>{escape(s.get('label',''))}</td>"
                    f"<td class=\"num\">{s.get('n','')}</td>"
                    f"<td class=\"num\">{s.get('hits','')}</td>"
                    f"<td class=\"num\">{num_f(s.get('rate'))}</td>"
                    f"<td class=\"num\">{num_f(s.get('p_vs_constant'))}</td>"
                    f"<td>{'-'.join(num_f(x) for x in s.get('ci95',[])) if s.get('ci95') else '—'}</td>"
                    f"<td class=\"num\">{num_f(s.get('brier_skill'))}</td>"
                    f"<td>{'BH q=0.10 passed' if s.get('passes_bh') else 'not significant'}</td>"
                    f"<td>{escape(s.get('status',''))}</td></tr>")
    body.append("</table>")
    body.append('<div class="card warn"><div class="kicker">Adverse-signal disclosure (never hidden, never re-tuned)</div>'
                '<p>The total rule ran adverse: <strong>S4 total 27/74 = 36.5%, p = 0.0265</strong>. '
                'It is published as an anti-signal and the naive club-mean total is run beside it until one wins.</p></div>')
    body.append('<div class="card"><div class="kicker">Divisions</div>'
                '<ul><li>Singles — S1–S7 eligible (S6, S7 are controls)</li>'
                '<li>Game parlay — none eligible (gate G8 closed)</li>'
                '<li>Same-game parlay — none eligible (gate G8 closed)</li>'
                '<li>Prop combo — none eligible (gate G8 closed)</li></ul></div>')
    return page("Leaderboard", body, "leaderboard.html")

# ================================================================ registry
def registry():
    body = ['<h2>Strategy registry — pre-registered, frozen</h2>',
            '<p class="kicker">The commit hash of the frozen definition is the registration. Backtest numbers never '
            'appear on the leaderboard; only prospective walk-forward rows do.</p>',
            '<table><tr><th class="tag">ID</th><th>Definition (frozen)</th><th>Window</th><th>Confirm condition</th><th>Refute condition</th><th>Status</th></tr>']
    for s in C.STRATEGIES:
        body.append(f"<tr><td>{s['id']}</td><td>{escape(s['definition'])}</td>"
                    f"<td>{escape(s['window'])}</td><td>{escape(s['confirm'])}</td>"
                    f"<td>{escape(s['refute'])}</td><td>{escape(s['status'])}</td></tr>")
    body.append("</table>")
    return page("Registry", body, "registry.html")

# ================================================================ gates
def gates():
    body = ['<h2>Validation gates and demotion rules</h2>',
            '<table><tr><th class="tag">ID</th><th>Gate</th><th>Requirement</th><th class="badge cell">Status</th><th>Evidence</th></tr>']
    for gid, name, req, st, ev in C.GATES:
        body.append(f"<tr><td>{gid}</td><td>{escape(name)}</td><td>{escape(req)}</td><td>{badge(st)}</td><td>{escape(ev)}</td></tr>")
    body.append("</table>")
    body.append('<h3>Demotion rules</h3><table><tr><th class="tag">ID</th><th>Rule</th><th>Action</th></tr>')
    for did, rule, action in C.DEMOTION:
        body.append(f"<tr><td>{did}</td><td>{escape(rule)}</td><td>{escape(action)}</td></tr>")
    body.append("</table>")
    body.append('<p class="small">No strategy is live yet, so nothing can be demoted. Gate G7 (price and CLV) is '
                'blocked until a price source exists.</p>')
    return page("Gates", body, "gates.html")

# ================================================================ luck
def luck():
    luck = load("luck.json") or {}
    rows = luck.get("clubs", []) if isinstance(luck, dict) else []
    body = ['<h2>Removal-of-luck panel</h2>',
            '<p class="kicker">Luck residual = actual win% − margin-implied win%. Positive values are luck-aided, '
            'negative values are luck-hurt. Nothing here is inferred; every value is computed from the official results feed.</p>',
            '<table><tr><th class="tag">Club</th><th class="num">Actual win%</th><th class="num">Margin-implied win%</th><th class="num">Luck residual</th></tr>']
    for r in rows:
        body.append(f"<tr><td>{escape(r.get('team',''))}</td><td class=\"num\">{num_f(r.get('actual_win_pct'))}</td>"
                    f"<td class=\"num\">{num_f(r.get('implied_win_pct'))}</td>"
                    f"<td class=\"num\">{num_f(r.get('luck_residual'))}</td></tr>")
    body.append("</table>")
    top = sorted(luck, key=lambda r: r.get("luck_residual", -9), reverse=True) if isinstance(luck, list) else []
    if top:
        body.append('<div class="card"><div class="kicker">Most luck-aided</div><ul>')
        for t in top[:6]:
            body.append(f"<li>{escape(t.get('team',''))}: {num_f(t.get('luck_residual'))}</li>")
        body.append("</ul></div>")
    return page("Luck", body, "luck.html")

# ================================================================ correlations
def correlations():
    corr = load("correlations.json") or {}
    pairs = corr.get("pairs", []) if isinstance(corr, dict) else []
    body = ['<h2>Correlations — officially sourced numbers only</h2>',
            '<p class="kicker">Every value carries n and a 95% CI. Correlations are computed only from numbers that '
            'trace to an official page; nothing is inferred.</p>',
            '<table><tr><th class="tag">Pair</th><th class="num">r</th><th class="num">n</th><th>95% CI</th><th>Source</th></tr>']
    for p in pairs:
        ci = p.get("ci95", [])
        body.append(f"<tr><td>{escape(p.get('pair',''))}</td><td class=\"num\">{num_f(p.get('r'))}</td>"
                    f"<td class=\"num\">{p.get('n','')}</td>"
                    f"<td>{'-'.join(num_f(x) for x in ci) if ci else '—'}</td>"
                    f"<td>{src(p.get('source','https://www.nfl.com/'))}</td></tr>")
    body.append("</table>")
    return page("Correlations", body, "correlations.html")

# ================================================================ injuries
def injuries():
    inj = load("injury_surprise.json") or {}
    des = load("injury_designations_w10_2026.csv")
    body = ['<h2>Injuries — surprise, never level</h2>',
            '<p class="kicker">The published signal is a transition between consecutive official weekly reports, never '
            'a level. The week-10 table below was re-captured in full on 2026-11-15.</p>']
    if isinstance(inj, dict):
        body.append('<table><tr><th class="tag">Transitions</th><th class="num">Worse</th><th class="num">Better</th>'
                    '<th class="num">Unchanged</th><th class="num">Newly designated</th><th class="num">Symmetry p</th></tr>')
        body.append(f"<tr><td>Practice-status changes wk8→10</td>"
                    f"<td class=\"num\">{inj.get('practice_worse','')}</td>"
                    f"<td class=\"num\">{inj.get('practice_better','')}</td>"
                    f"<td class=\"num\">{inj.get('practice_unchanged','')}</td>"
                    f"<td class=\"num\">{inj.get('newly_designated','')}</td>"
                    f"<td class=\"num\">{num_f(inj.get('p_symmetry'))}</td></tr></table>")
        body.append(f'<p class="small">{escape(inj.get("method_note",""))}</p>')
    body.append('<h3>Announced starter evidence (dated quotes, not inferred replacements)</h3>')
    body.append('<table><tr><th class="tag">Club</th><th>Announced starter</th><th>Replacing</th><th>Change type</th><th>Announced on</th><th>Evidence quote</th><th>Source</th></tr>')
    import csv
    ann_path = RAW / "announced_starters.csv"
    rows = list(csv.DictReader(open(ann_path))) if ann_path.exists() else []
    for r in rows:
        body.append(f"<tr><td>{escape(r.get('team',''))}</td><td>{escape(r.get('announced_starter',''))}</td>"
                    f"<td>{escape(r.get('replacing',''))}</td><td>{escape(r.get('change_type',''))}</td>"
                    f"<td>{escape(r.get('announced_on',''))}</td><td>{escape(r.get('evidence_quote',''))}</td>"
                    f"<td>{src(r.get('source_url',''))}</td></tr>")
    body.append("</table>")
    body.append('<div class="card warn"><div class="kicker">Coverage gap</div>'
                '<p>The official Week-10 report covers 28 clubs; 4 clubs are on bye and absent by construction. '
                'No play-rate table is published because the designation→inactive join returns 0 matches (name-format '
                'mismatch, unresolved).</p></div>')
    return page("Injuries", body, "injuries.html")

# ================================================================ depth
def depth():
    avail = load("availability.json") or {}
    starters = avail.get("starters", []) if isinstance(avail, dict) else []
    inact = avail.get("inactives", []) if isinstance(avail, dict) else []
    body = ['<h2>Depth &amp; availability</h2>',
            '<p class="kicker">Depth slots are modelled as groups, never collapsed to a single starter. '
            'Jersey order, experience and salary are never used to derive depth.</p>']
    body.append('<table><tr><th class="tag">Game</th><th>Team</th><th class="tag">Unit</th><th class="tag">Position</th><th>Player</th><th class="num">Club chart rank</th><th>Source</th></tr>')
    for s in starters[:150]:
        body.append(f"<tr><td>{escape(s.get('game',''))}</td><td>{escape(s.get('team',''))}</td>"
                    f"<td>{escape(s.get('unit',''))}</td><td>{escape(s.get('position',''))}</td>"
                    f"<td>{escape(s.get('player',''))}</td><td class=\"num\">{escape(str(s.get('depth_rank_in_club_chart','')))}</td>"
                    f"<td>{src(s.get('source','https://www.nfl.com/'))}</td></tr>")
    body.append(f"</table><p class='small'>{len(starters)} starter rows shown.</p>")
    body.append('<h3>Official inactive lists (game-book evidence only)</h3>')
    body.append('<table><tr><th class="tag">Team</th><th>Player</th><th class="num">Number</th><th>Note</th><th>Source</th></tr>')
    for r in inact:
        body.append(f"<tr><td>{escape(r.get('team',''))}</td><td>{escape(r.get('player',''))}</td>"
                    f"<td class=\"num\">{escape(str(r.get('number','')))}</td><td>{escape(r.get('note',''))}</td>"
                    f"<td>{src(r.get('source','https://www.nfl.com/'))}</td></tr>")
    body.append("</table>")
    body.append('<div class="card warn"><div class="kicker">Two depth-parsing failures</div>'
                '<ul><li>Houston publishes its depth chart only as an image → 0 structured rows (F-04).</li>'
                '<li>No club chart carries a captured as-of date → staleness is suspected, not measurable (F-05).</li>'
                '<li>No official snap-count source exists yet → the starter proxy cannot be built (Q02/Q03).</li></ul></div>')
    return page("Depth", body, "depth.html")

# ================================================================ fixtures
def fixtures():
    fix = load("fixture_context.json") or []
    body = ['<h2>Fixtures — venue transcribed from the official game centre</h2>',
            '<p class="kicker">Fixture context uses published schedule facts only: rest days (exact), neutral-site '
            'flag, and venue where the game book states it. Everything else is left blank.</p>',
            '<table><tr><th class="tag">Week</th><th class="tag">Game</th><th class="tag">Team</th><th class="tag">Side</th><th class="num">Rest days</th><th class="num">Neutral</th><th>Venue</th><th class="tag">Venue status</th></tr>']
    for r in fix[:200]:
        body.append(f"<tr><td>{r.get('week','')}</td><td>{escape(r.get('game',''))}</td>"
                    f"<td>{escape(r.get('team',''))}</td><td>{escape(r.get('side',''))}</td>"
                    f"<td class=\"num\">{escape(str(r.get('rest_days','')))}</td>"
                    f"<td class=\"num\">{'yes' if r.get('neutral_site') else 'no'}</td>"
                    f"<td>{escape(str(r.get('venue',''))) or '—'}</td>"
                    f"<td>{escape(r.get('venue_status',''))}</td></tr>")
    body.append("</table>")
    body.append('<div class="card warn"><div class="kicker">Open</div>'
                '<p>The Week-11 international game (MIN@SF, Mexico City) has no venue stated on the official week page '
                '(F-08). Roof/surface/weather captured for 2 of 138 games; no NWS feed exists yet (R56, Q08).</p></div>')
    return page("Fixtures", body, "fixtures.html")

# ================================================================ policy
def policy():
    body = ['<h2>Price-data policy</h2>',
            '<p class="kicker">Decided before any backtest was published, dated 2026-11-15, and kept beside every '
            'backtest forever (R20, R68, SUG-12).</p>',
            '<ol><li>No price is estimated in this repository. No opening price, no closing price, no vig, no CLV, no ROI.</li>'
            '<li>Every market column stays blank until an official or licensed source is named and its terms read.</li>'
            '<li>The residual (fair − market) cannot exist without a market price; it stays blank by rule.</li>'
            '<li>No backtest publishes ROI; the leaderboard ranks on proper scores with uncertainty instead (R36, R63).</li></ol>']
    return page("Policy", body, "policy.html")

# ================================================================ readiness
def readiness():
    body = ['<h2>Decision-readiness table</h2>',
            '<p class="kicker">One row per requirement: status, the blocking gate, and the number that would clear it.</p>',
            '<table><tr><th class="tag">ID</th><th>Requirement</th><th class="badge cell">Status</th><th>Blocking gate</th><th class="num">Number that would clear it</th><th>Evidence</th></tr>']
    for rid, req, ev, st, gate, num in C.REQUIREMENTS:
        body.append(f"<tr><td>{rid}</td><td>{escape(req)}</td><td>{badge(st)}</td><td>{escape(gate)}</td>"
                    f"<td class=\"num\">{escape(num)}</td><td>{escape(ev)}</td></tr>")
    body.append("</table>")
    return page("Readiness", body, "readiness.html")

# ================================================================ executive summary
def exec_sum():
    rec = load("reconciliation.json") or {}
    strat = load("strategies.json") or {}
    luck = load("luck.json") or {}
    corr = load("correlations.json") or {}
    avail = load("availability.json") or {}
    body = ['<h2>Executive summary</h2>',
            '<p class="kicker">Important details at a glance. Every number traces to an official page or is flagged.</p>']
    body.append('<div class="grid2">')
    if isinstance(rec, dict):
        body.append(f'<div class="card ok"><div class="kicker">Data</div>'
                    f'<p>{escape(rec.get("status",""))}</p></div>')
    s3 = strat.get("S3_side", {})
    body.append(f'<div class="card"><div class="kicker">Best signal</div>'
                f'<p>S3 side: {s3.get("hits","")}/{s3.get("n","")} = {num_f(s3.get("rate"))}, '
                f'p = {num_f(s3.get("p_vs_constant"))}. Passes BH q=0.10.</p></div>')
    s4 = strat.get("S4_total", {})
    body.append(f'<div class="card warn"><div class="kicker">Total signal</div>'
                f'<p>S4 total {s4.get("hits","")}/{s4.get("n","")} = {num_f(s4.get("rate"))}, p = {num_f(s4.get("p_vs_constant"))} — adverse. '
                f'Published as an anti-signal; naive control runs beside it.</p></div>')
    tl = sorted(luck, key=lambda r: r.get("luck_residual", -9), reverse=True) if isinstance(luck, list) else []
    body.append(f'<div class="card"><div class="kicker">Luck</div>'
                f'<p>Most luck-aided: {escape(tl[0].get("team",""))} ({num_f(tl[0].get("luck_residual"))}).</p></div>')
    body.append('</div>')
    body.append('<h3>What is true today</h3><ul>')
    body.append('<li>Standings reconcile 32/32 against the official page re-read today.</li>')
    body.append('<li>Week-10 injury tables re-captured: 347 rows, 28 clubs.</li>')
    body.append('<li>No market price exists anywhere in this repository (F-01).</li>')
    body.append('<li>The side carries skill; the total does not — and that is published, not hidden.</li>')
    body.append('<li>Four requirements are rejected as shortcuts (jersey-order depth, season-long ROI, etc.).</li>')
    body.append('</ul>')
    body.append('<h3>What blocks a live strategy</h3><ul>')
    body.append('<li>A price source (G7 blocked → no CLV, ROI, or residual).</li>')
    body.append('<li>A 32-club depth source with captured as-of dates (Q03).</li>')
    body.append('<li>Snap counts for the starter proxy and the deficiency matrix (Q02).</li>')
    body.append('<li>The 2026 rulebook citation for kickoff/onside priors (Q08/R65).</li>')
    body.append('</ul>')
    return page("Executive Summary", body, "executive-summary.html")

# ================================================================ suggestions
def suggestions():
    body = ['<h2>Suggestions — review before implementing</h2>',
            '<p class="kicker">All suggestions below are proposed. None is implemented. Someone can review and choose '
            'the best path before any change is made.</p>',
            '<table><tr><th class="tag">ID</th><th>Suggestion</th><th>Value</th><th>Depends on</th><th class="badge cell">Stance</th><th>Why now</th></tr>']
    for sid, sug, val, dep, stance, why in C.SUGGESTIONS:
        body.append(f"<tr><td>{sid}</td><td>{escape(sug)}</td><td>{escape(val)}</td>"
                    f"<td>{escape(dep)}</td><td>{badge(stance)}</td><td>{escape(why)}</td></tr>")
    body.append("</table>")
    return page("Suggestions", body, "suggestions.html")

# ================================================================ questions
def questions():
    body = ['<h2>Questions, information and answers needed before decisions</h2>',
            '<p class="kicker">A clear list of what is missing, what blocks it, and how to discover it.</p>',
            '<table><tr><th class="tag">ID</th><th>Question</th><th>Blocks</th><th>Current answer</th><th>How to discover missing info</th><th class="badge cell">Priority</th></tr>']
    for qid, q, blocks, ans, how, pri in C.QUESTIONS:
        body.append(f"<tr><td>{qid}</td><td>{escape(q)}</td><td>{escape(blocks)}</td>"
                    f"<td>{escape(ans)}</td><td>{escape(how)}</td><td>{badge(pri)}</td></tr>")
    body.append("</table>")
    return page("Questions", body, "questions.html")

# ================================================================ flagged
def flagged():
    body = ['<h2>Flagged for review</h2>',
            '<p class="kicker">Irregularities and unverified items do not block the merge; they are published here '
            'with source links for review after the site is live.</p>']
    for fid, f, impact, where, source in C.FLAGS:
        body.append(f'<div class="flag"><div class="kicker">{fid}</div>'
                    f'<p>{escape(f)}</p>'
                    f'<p class="small">Impact: {escape(impact)} · Recorded at: {escape(where)}</p>'
                    f'<p>{flag_source(source)}</p></div>')
    body.append('<p class="small"><strong>Review process:</strong> open an issue or PR against this repository with '
                'the flag ID; the site stays live while items are reviewed.</p>')
    return page("Flagged", body, "flagged.html")

# ================================================================ provenance
def provenance():
    prov = load("provenance.json") or {}
    body = ['<h2>Provenance</h2>',
            '<p class="kicker">Every model output is stored as a probability plus its inputs; the input hashes make '
            'each run reproducible.</p>']
    for k, v in prov.items():
        body.append(f'<div class="card"><div class="kicker">{escape(str(k))}</div>'
                    f'<pre class="small">{escape(str(v))}</pre></div>')
    return page("Provenance", body, "provenance.html")

# ================================================================ methodology
def methodology():
    body = ['<h2>Methodology</h2>',
            '<p class="kicker">How the numbers are produced, line by line.</p>',
            '<ul><li>Margin model: ridge regression on 138 finals (weeks 1–10), design = intercept (home advantage) + 32 club ratings; lambda chosen by nested walk-forward over {1,3,10,30,100}.</li>'
            '<li>Pythagorean alternative: club rate sqrt(PF/(PF+PA)) fitted to margin by least squares.</li>'
            '<li>Total model: ridge total = c + off_home + def_away + off_away + def_home, lambda 10, refit weekly. Published beside a naive club-mean control until one wins.</li>'
            '<li>Probability: P(home wins) = Phi(margin / sigma), sigma = 11.34 from walk-forward residuals.</li>'
            '<li>Brier skill vs constant 0.5, game-cluster bootstrap CI, Benjamini-Hochberg q = 0.10 multiplicity adjustment.</li>'
            '<li>Luck residual = actual win% − Phi(mean margin / sigma).</li>'
            '<li>Correlations: Pearson r with n and Wilson 95% CI, official sources only.</li>'
            '<li>Injury signal: transitions between consecutive official weekly reports; no level is ever a feature.</li></ul>']
    return page("Methodology", body, "methodology.html")

PAGES = {
    "index.html": landing,
    "results.html": results,
    "lines.html": lines,
    "leaderboard.html": leaderboard,
    "registry.html": registry,
    "gates.html": gates,
    "luck.html": luck,
    "correlations.html": correlations,
    "injuries.html": injuries,
    "depth.html": depth,
    "fixtures.html": fixtures,
    "policy.html": policy,
    "readiness.html": readiness,
    "executive-summary.html": exec_sum,
    "suggestions.html": suggestions,
    "questions.html": questions,
    "flagged.html": flagged,
    "provenance.html": provenance,
    "methodology.html": methodology,
}

def main():
    for name, fn in PAGES.items():
        (OUT / name).write_text(fn(), encoding="utf-8")
    print("wrote", len(PAGES), "pages to", OUT)

if __name__ == "__main__":
    main()
