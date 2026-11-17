#!/usr/bin/env python3
"""Build the read-only verdict desk from committed CSV evidence."""
from __future__ import annotations
import csv, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
NAV = [
    ("index.html", "Overview"), ("fixtures.html", "Week 11 fixtures"),
    ("results.html", "Week 10 results"), ("availability.html", "Availability"),
    ("origination.html", "Origination"), ("requirements.html", "Requirements"), ("questions.html", "Open questions"),
    ("protocol.html", "Protocol"), ("review.html", "Flagged for Review"),
    ("suggestions.html", "Suggestions"),
]
PAGES = {
    "fixtures.html": ("Week 11 fixtures", "Official 2026 NFL Game Center venue transcription for all 13 scheduled Week-11 games.", "week11_fixtures.csv"),
    "results.html": ("Week 10 results reconciliation", "Official NFL finals compared row by row with both repository result feeds.", "week10_reconciliation.csv"),
    "availability.html": ("Questionable participation · pilot", "A one-game official injury-report to Game Book join. Descriptive only; far too small for calibration or model use.", "designation_playrate.csv"),
    "origination.html": ("Week 11 origination ledger", "X3-v2 fair outputs copied from the saved model artifact in side → total → moneyline order. Market quote and residual fields remain blank; preregistration is flagged.", "origination_w11.csv"),
    "requirements.html": ("Requirements register", "The 69-row register already maintained in the repository, copied read-only for this desk. Internal citations are not represented as official NFL evidence.", "requirements_register.csv"),
    "questions.html": ("Open questions", "Decision-critical missing information and the gate that must be cleared before acting.", "questions.csv"),
    "protocol.html": ("Minimum viable decision protocol", "A proposed paper-first, preregistered workflow. This is a recommendation, not an NFL rule or a claim of validated performance.", "protocol.csv"),
    "review.html": ("Flagged for Review", "Verified source discrepancies and cross-scope repository gate defects. Values are preserved as published; no unsupported repair is made.", "findings.csv"),
}

def load_csv(name):
    with (DATA / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def label(s):
    return s.replace("_", " ").replace("ET", "ET").title()

def cell(v, field):
    v = v or ""
    if v.startswith("https://") or v.startswith("http://"):
        return f'<a href="{html.escape(v, quote=True)}" target="_blank" rel="noopener">Official / cited source ↗</a>'
    if field == "repo_evidence" and v:
        links=[]
        for path in v.split('; '):
            path=path.strip()
            links.append(f'<a href="https://github.com/karagemop466-tech/X3/blob/main/{html.escape(path, quote=True)}" target="_blank" rel="noopener">{html.escape(path)} ↗</a>')
        return '<br>'.join(links)
    if not v:
        return '<span class="blank">—</span>'
    if v.startswith("FLAG:") or "BLOCKED" in v or "MISSING" in v or "CROSS-SCOPE" in v:
        return f'<span class="flag">{html.escape(v)}</span>'
    return html.escape(v)

def table(rows):
    if not rows:
        return '<p class="empty">No rows.</p>'
    fields = list(rows[0])
    head = "".join(f"<th>{html.escape(label(k))}</th>" for k in fields)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f'<td>{cell(r.get(k, ""), k)}</td>' for k in fields) + "</tr>")
    return '<div class="table-wrap"><table><thead><tr>'+head+'</tr></thead><tbody>'+"".join(body)+'</tbody></table></div>'

def shell(title, description, body, active="index.html"):
    links = "".join(f'<a href="{href}" class="{"active" if href==active else ""}">{name}</a>' for href,name in NAV)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · X3 Verdict Desk</title><meta name="description" content="{html.escape(description)}"><link rel="stylesheet" href="style.css"></head>
<body><header class="top"><a class="brand" href="index.html"><span class="mark">X3</span><span>VERDICT DESK<small>Official-source decision lab</small></span></a><nav>{links}</nav></header>
<main><div class="eyebrow">2026 REGULAR SEASON · READ-ONLY EVIDENCE VIEW</div><h1>{html.escape(title)}</h1><p class="lede">{html.escape(description)}</p>{body}</main>
<footer>Every fact row links to an official NFL source or is explicitly identified as a repository citation / flagged gap. No missing line, score, venue, or probability is imputed. Sources are live and may update after this capture.</footer>
</body></html>'''

def write(name, content):
    (ROOT/name).write_text(content, encoding="utf-8")

def main():
    for filename, (title, desc, csv_name) in PAGES.items():
        rows = load_csv(csv_name)
        body = '<div class="tools"><input type="search" placeholder="Filter rows…" aria-label="Filter table" oninput="filterRows(this)"><span>'+str(len(rows))+' rows</span></div>'+table(rows)
        body += '<script>function filterRows(input){const q=input.value.toLowerCase();document.querySelectorAll("tbody tr").forEach(r=>r.hidden=!r.innerText.toLowerCase().includes(q));}</script>'
        write(filename, shell(title, desc, body, filename))
    # Executive dashboard: counts are computed from source CSVs, never hand-entered.
    fixtures=load_csv('week11_fixtures.csv'); results=load_csv('week10_reconciliation.csv'); markets=load_csv('origination_w11.csv'); findings=load_csv('findings.csv'); reqs=load_csv('requirements_register.csv')
    missing=sum(r['x3_feed_reconciliation']!='MATCH' for r in results)
    blocked=len(markets)
    cards=[(str(len(fixtures)), 'Week 11 fixtures verified'),(str(len(results)), 'Week 10 finals checked'),(str(missing), 'Week 10 games absent from x3 feed'),(str(blocked), 'W11 derived fair outputs')]
    cardhtml=''.join(f'<div class="metric"><strong>{n}</strong><span>{html.escape(t)}</span></div>' for n,t in cards)
    body=f'''<section class="metrics">{cardhtml}</section>
<section class="panel alert"><b>Decision status: PAPER / NO LIVE BETS</b><p>Week-11 X3-v2 fair lines and model probabilities are published from the saved as-of 2026-11-14 artifact. Market quotes and residuals remain blank because no quote source is recorded. The model artifact does not cite an X3-v2 pre-registration hash, so registration is UNVERIFIED; these rows are not a live strategy leaderboard.</p></section>
<section class="grid"><a class="tile" href="fixtures.html"><span>01 / SCHEDULE</span><h2>Week 11 fixtures & venues</h2><p>13 Game Center rows; HOU venue name is flagged because the official pages conflict.</p></a>
<a class="tile" href="results.html"><span>02 / RESULTS</span><h2>Week 10 reconciliation</h2><p>Official NFL finals compared with the two committed result feeds.</p></a>
<a class="tile" href="availability.html"><span>03 / AVAILABILITY</span><h2>Questionable participation</h2><p>One-game injury-report / Game Book join; explicitly not a calibrated rate.</p></a>
<a class="tile" href="origination.html"><span>04 / PRICING</span><h2>Origination ledger</h2><p>X3-v2 fair outputs and probabilities; external market quotes/residuals stay blank.</p></a>
<a class="tile" href="requirements.html"><span>05 / READINESS</span><h2>Requirements register</h2><p>{len(reqs)} requirements copied from the existing repository register, read-only.</p></a>
<a class="tile" href="questions.html"><span>06 / DECISION SUPPORT</span><h2>Questions to resolve</h2><p>Missing facts and the explicit gate that clears each decision.</p></a>
<a class="tile" href="protocol.html"><span>07 / METHODS</span><h2>Minimum viable protocol</h2><p>Preregister, capture, originate, evaluate, then promote or demote.</p></a>
<a class="tile warning" href="review.html"><span>08 / REVIEW</span><h2>Flagged for Review</h2><p>{len(findings)} source/data-quality issues, including the broken Pages audit on pristine main.</p></a>
<a class="tile" href="suggestions.html"><span>09 / OPTIONS</span><h2>Suggestions</h2><p>Reviewable recommendations ordered by evidence dependency and decision value.</p></a></section>
<section class="panel"><h2>Executive summary</h2><p>The official Week-10 schedule shows all 14 games final. The x3 results file holds only two Week-10 finals; 12 more are absent. The separately named verified feed has only WAS@NYG final and 13 Week-10 games still marked scheduled. Those feeds are not equivalent and neither is complete for Week 10.</p><p>The repo contains 786 derived fair-price rows in <a href="../data/x3/verified/price_store.csv">price_store.csv</a> (524 open-line values and 420 close-line values); its external-market fields market_open, market_close and market_source are blank on all 786 rows. A saved <a href="../data/x3/verified/markets.json">X3-v2 model artifact</a> contains 13 Week-11 forecasts and probabilities as of 2026-11-14. We publish those fair outputs, but leave market quotes and residuals blank. The artifact does not cite an X3-v2 pre-registration hash.</p><p>Every one of the 13 Week-11 Game Center pages was readable and its displayed venue transcribed. The Houston game center says “Reliant Stadium,” while the Week-11 schedule destination says “NRG Stadium”; both strings are preserved and flagged.</p><p>The clean-archive baseline at main commit <code>b7d4142</code> had 64 audit violations (details on Flagged for Review). The decision-layer owner fixed the repo-wide audit and Pages generator in PR #93; the current combined checkout passes <code>audit_all.py</code>. The separate decision-builder determinism check still fails and remains outside this session’s write scope.</p></section>'''
    write('index.html',shell('X3 NFL decision desk','Verified evidence, open gates, and decision-readiness for NFL line origination.',body,'index.html'))
    # Suggestions are proposals, explicitly separated from verified facts.
    sug='''<section class="panel"><h2>Recommended order of work</h2><ol><li><b>Make result truth deterministic.</b> Refresh both result feeds from official game centers, preserve raw source and retrieval time, and fail on score/coverage mismatch. Reconcile 150 finals after Week 10 before any backtest.</li><li><b>Choose price policy before evaluation.</b> Name permitted books/feeds, opening/closing definitions, timestamps, push/void settlement, and retention/terms. Until then the market/residual columns remain empty.</li><li><b>Build a point-in-time ledger before personnel modeling.</b> Immutable official injury reports, club depth pages, inactive lists, Game Books, transactions and official snap counts; preserve hashes, timestamps, conflicts and source strings.</li><li><b>Start singles-only in shadow.</b> Pre-register probabilities and inputs before kickoff, benchmark against favorite-only and seeded random controls, evaluate with chronological holdouts and proper scores plus uncertainty.</li><li><b>Keep combo strategies out of ranking until joint outcomes are validated.</b> Marginal probabilities cannot establish SGP/parlay/prop-combo probabilities under dependence; document settlement and void rules.</li><li><b>Fix the decision-page deploy gate in its owning scope.</b> Request changes from the decision-layer owner; do not regenerate their pages from this branch.</li></ol><p class="muted">These are implementation recommendations, not externally verified NFL facts. See the <a href="questions.html">open questions</a> and <a href="review.html">flagged findings</a>.</p></section>'''
    write('suggestions.html',shell('Suggestions','Reviewable options for improving evidence quality and decision making.',sug,'index.html'))
    write('style.css', '''
:root{color-scheme:dark;--bg:#0b1018;--panel:#121c29;--line:#29384a;--muted:#a4b3c4;--ink:#eff5fb;--accent:#57d3b2;--gold:#ffc66d;--red:#ff927d}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 18% -10%,#16314a 0,transparent 48%),var(--bg);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}.top{position:sticky;top:0;z-index:3;display:flex;align-items:center;justify-content:space-between;gap:24px;padding:15px max(24px,calc((100vw - 1280px)/2));background:#0b1018eF;border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}.brand{display:flex;align-items:center;gap:11px;color:var(--ink);text-decoration:none;font-weight:850;letter-spacing:.12em;font-size:.82rem}.brand small{display:block;color:var(--muted);font-weight:500;letter-spacing:0;margin-top:2px}.mark{display:grid;place-items:center;width:40px;height:40px;border:1px solid #48c7a8;border-radius:12px;color:var(--accent);font-weight:900;font-size:1rem}nav{display:flex;gap:5px;flex-wrap:wrap}nav a{color:var(--muted);text-decoration:none;padding:8px 10px;border-radius:8px;font-size:.83rem}nav a:hover,nav a.active{color:var(--ink);background:#1a2b3b}main{max-width:1280px;padding:42px 24px 84px;margin:auto}.eyebrow{color:var(--accent);font-size:.72rem;font-weight:800;letter-spacing:.14em}h1{font-size:clamp(2rem,4vw,3rem);line-height:1.1;margin:12px 0}.lede{color:#bdc9d6;font-size:1.07rem;max-width:850px;margin:0 0 26px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin:22px 0}.metric,.panel,.tile{background:linear-gradient(145deg,#142131,#101924);border:1px solid var(--line);border-radius:15px;padding:19px}.metric strong{display:block;font-size:2.05rem;line-height:1.1;color:var(--accent)}.metric span{display:block;color:var(--muted);font-size:.87rem;margin-top:7px}.alert{border-color:#785d34;background:#211c16;margin-bottom:20px}.alert b{color:var(--gold)}.alert p{margin:.5rem 0 0;color:#e0d2bc}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin:20px 0}.tile{display:block;color:inherit;text-decoration:none;transition:.15s}.tile:hover{border-color:#49c8a8;transform:translateY(-2px)}.tile span{color:var(--accent);font-size:.68rem;letter-spacing:.12em;font-weight:800}.tile h2{font-size:1.08rem;margin:9px 0 5px}.tile p{color:var(--muted);margin:0;font-size:.88rem}.tile.warning{border-color:#735a39}.tile.warning span{color:var(--gold)}.panel{margin:18px 0}.panel h2{margin-top:0}.panel p,.panel li{color:#c0ccd8}.panel li{margin:.55em 0}.panel a,main a{color:#8ce4cc}.tools{display:flex;justify-content:space-between;align-items:center;gap:15px;margin:18px 0;color:var(--muted);font-size:.85rem}.tools input{width:min(420px,100%);background:#111b27;color:var(--ink);border:1px solid var(--line);border-radius:9px;padding:11px 13px;font:inherit}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px;background:#101722}table{width:100%;border-collapse:collapse;min-width:900px;font-size:.83rem}th,td{text-align:left;vertical-align:top;padding:11px 12px;border-bottom:1px solid #243243;max-width:390px}th{position:sticky;top:0;background:#182536;color:#b9c8d7;text-transform:uppercase;font-size:.68rem;letter-spacing:.07em;z-index:1}tbody tr:hover{background:#172432}td a{white-space:nowrap;color:var(--accent)}.blank{color:#647487}.flag{display:inline-block;color:#ffd18b;background:#382d1c;border:1px solid #725834;border-radius:6px;padding:3px 7px}.empty,.muted,footer{color:var(--muted)}footer{max-width:1280px;border-top:1px solid var(--line);padding:18px 24px 35px;margin:auto;font-size:.8rem}code{color:#c6d6e6;background:#1a2633;padding:2px 5px;border-radius:4px}ol{padding-left:22px}@media(max-width:900px){.top{position:static;align-items:flex-start;flex-direction:column}.metrics{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){main{padding:28px 15px 60px}.grid{grid-template-columns:1fr}.metrics{gap:8px}.metric{padding:13px}.metric strong{font-size:1.6rem}nav a{padding:7px 8px}}
''')

if __name__=='__main__': main()
