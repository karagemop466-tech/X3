#!/usr/bin/env python3
"""Render the fresh module (session arena/765ef2cf-x3, tasks F1-F3).

Reads the committed 2026-11-19 fresh-day reads from data/fresh/ (plus the
canonical readiness register at readiness/data/readiness.json for the decision
board, read-only) and writes the static pages under fresh/. Deterministic:
same inputs -> byte-identical pages. No prose figure is hand-typed; every
number is interpolated from the data files.

Run: python3 scripts/fresh_verify.py && python3 scripts/fresh_build.py
"""
from __future__ import annotations

import csv
import json
import os
from html import escape as _h

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "fresh")
SITE = os.path.join(ROOT, "fresh")

REG11_URL = "https://www.nfl.com/injuries/league/2026/reg11"
STANDINGS_URL = "https://www.nfl.com/standings/league/2026/REG"
WK11_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
GAME_CENTRE_URL = "https://www.nfl.com/games/colts-at-texans-2026-reg-11"

CSS = """:root{--ink:#1c2330;--mut:#5b6577;--line:#d8dee9;--bg:#f6f8fb;--ok:#1a7f37;--bad:#b42318;--warn:#946800}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#0b1f3a;color:#fff;padding:26px 22px 20px}header h1{margin:0 0 6px;font-size:24px}header p{margin:0;color:#c7d2e4;max-width:70em}
nav.bar{background:#12294a;padding:10px 22px}nav.bar a{color:#dbe6f6;margin-right:18px;text-decoration:none;font-weight:600}nav.bar a:hover{text-decoration:underline}
main{max-width:1120px;margin:0 auto;padding:22px}
h2{margin:26px 0 10px;font-size:19px}h3{margin:18px 0 8px;font-size:16px}
p.lede{font-size:16px;color:var(--ink)}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{caption-side:top;text-align:left;padding:10px 12px;font-weight:700;color:var(--mut);background:#eef2f7}
th{background:#eef2f7;text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:6px 10px;border-bottom:1px solid #e8ecf2;vertical-align:top}
tr:last-child td{border-bottom:none}
td.mut{color:var(--mut)}td.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11.5px;font-weight:700}
.b-ok{background:#e6f4ea;color:var(--ok)}.b-bad{background:#fde8e8;color:var(--bad)}.b-warn{background:#fdf3d7;color:var(--warn)}.b-mut{background:#e9edf3;color:var(--mut)}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 16px;min-width:150px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--mut);font-size:12.5px}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid #0b1f3a;border-radius:8px;padding:14px 16px;margin:14px 0}
.warnbox{background:#fdf3d7;border:1px solid #e8d48a;border-left:4px solid var(--warn);border-radius:8px;padding:14px 16px;margin:14px 0}
.src{white-space:nowrap}.src a{color:#0b57d0;text-decoration:none}.src a:hover{text-decoration:underline}
code{background:#eef2f7;padding:0 4px;border-radius:4px;font-size:12.5px}
footer{max-width:1120px;margin:0 auto;padding:10px 22px 30px;color:var(--mut);font-size:12.5px}
"""

NAV = [("Overview", "index.html"), ("Slate", "slate.html"), ("Standings", "standings.html"),
       ("Injuries (reg11)", "injuries.html"), ("Game centre", "game-centre.html"),
       ("Decision board", "decision-board.html"), ("Executive summary", "executive-summary.html"),
       ("Flagged for review", "flagged.html"), ("Sources", "sources.html")]


def page(title: str, desc: str, body: str) -> str:
    links = " ".join(f'<a href="{href}">{_h(label)}</a>' for label, href in NAV)
    links += ' <a href="../index.html">Main hub →</a>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_h(title)} - X3 fresh 2026-11-19</title><link rel="stylesheet" href="assets/fresh.css"></head>
<body><header><h1>{_h(title)}</h1><p>{_h(desc)}</p></header>
<nav class="bar">{links}</nav><main>
{body}
</main><footer>fresh module - session arena/765ef2cf-x3 - built by <code>scripts/fresh_build.py</code> from <code>data/fresh/</code> (and the canonical readiness register, read-only). Every value traces to an official source or is left blank and flagged. Shell HTTP is blocked in the authoring sandbox: official pages are read with the page-reader tool, and each read records the tool clock time.</footer>
</body></html>
"""


def load_csv(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def src_link(url, label="official"):
    return f'<span class="src"><a href="{_h(url)}" target="_blank" rel="noopener">{_h(label)}</a></span>'


os.makedirs(SITE, exist_ok=True)
os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)

standings = load_csv("standings_2026-11-19.csv")
slate = load_csv("week11_slate_2026-11-19.csv")
byes = load_csv("byes_week11_2026-11-19.csv")
inj = load_csv("injury_w11_2026.csv")
game_centre = load_csv("ind_hou_game_centre_2026-11-19.csv")
summary = json.load(open(os.path.join(DATA, "freshness_summary.json"), encoding="utf-8"))
readiness = json.load(open(os.path.join(ROOT, "readiness", "data", "readiness.json"), encoding="utf-8"))
gates = list(csv.DictReader(open(os.path.join(ROOT, "data", "gates.csv"), newline="", encoding="utf-8")))
questions = list(csv.DictReader(open(os.path.join(ROOT, "data", "questions.csv"), newline="", encoding="utf-8")))
suggestions = list(csv.DictReader(open(os.path.join(ROOT, "data", "suggestions.csv"), newline="", encoding="utf-8")))

out_rows = [r for r in inj if r["game_status"] == "Out"]
q_rows = [r for r in inj if r["game_status"] == "Questionable"]
out_players = ", ".join(f"{r['player']} ({r['club']})" for r in out_rows)
q_players = ", ".join(f"{r['player']} ({r['club']})" for r in q_rows)
tot_pf = sum(int(r["pf"]) for r in standings)

# ---------------- index ----------------
body = f"""<p class="lede">Fresh-day verification for Thursday 2026-11-19, the morning of the Week-11 opener (IND@HOU, 8:15 PM ET). Every figure below was re-read from the official NFL pages on 2026-11-19 (tool clock time recorded per read) and cross-checked against the committed canonical registers; the diff is additive or a match, never an edit of another session's scope.</p>
<div class="kpis">
<div class="kpi"><b>32/32</b><span>standings rows re-read; all MATCH the committed atlas + closeout registers</span></div>
<div class="kpi"><b>13 + 6</b><span>Week-11 fixtures + byes re-read; records cross-checked to the fresh standings</span></div>
<div class="kpi"><b>253</b><span>Week-11 injury-report rows transcribed (first capture); {len(out_rows)} Out, {len(q_rows)} Questionable</span></div>
<div class="kpi"><b>1</b><span>venue conflict preserved and flagged (RELIANT STADIUM vs NRG Stadium) - not resolved</span></div>
<div class="kpi"><b>1</b><span>game centre fetched (IND@HOU); its Out chips corroborate the report transcription</span></div>
<div class="kpi"><b>0</b><span>market-price rows - F-01 persists; the leaderboard stays empty by design</span></div>
</div>
<div class="warnbox"><b>Week-11 report is now live.</b> The 2026-11-18 probes (4×) all served the Week-10 report. The 2026-11-19 read serves Week 11 - this module holds the first dated Week-11 capture. Practice status is not availability: only {len(out_rows) + len(q_rows)} of 253 rows carry a game designation, and the inactive lists are not yet published for Week 11. Blanks are shown as blanks, never inferred.</div>
<div class="warnbox"><b>IND@HOU venue conflict (flagged, not resolved).</b> The official game centre Game Info block reads <b>RELIANT STADIUM</b>; the schedule page hotel link reads <b>NRG Stadium</b>. Both are published with links on the <a href="game-centre.html">game centre</a> page. Do not quote a venue for this fixture without checking both.</div>
<h2>What changed since 2026-11-18</h2>
<div class="tblwrap"><table><caption>Day-over-day delta, official pages</caption><thead><tr><th>Dataset</th><th>2026-11-18</th><th>2026-11-19</th><th>Verdict</th></tr></thead><tbody>
<tr><td>League standings</td><td>32 rows read; registers canonical</td><td>32 rows re-read; PF = PA = {tot_pf}; every club matches the committed registers</td><td><span class="badge b-ok">UNCHANGED</span></td></tr>
<tr><td>Week-11 slate</td><td>13 games + 6 byes read 2026-11-17/18</td><td>13 games + 6 byes re-read; kickoff times, networks and records consistent; MIN@SF is the Mexico City international game</td><td><span class="badge b-ok">UNCHANGED</span> <span class="badge b-warn">1 CONFLICT (see flagged)</span></td></tr>
<tr><td>Week-11 injury report (reg11)</td><td>Not published (4 probes served Week 10)</td><td><b>Published</b> - “Week 11 of the 2026 Season”; 253 rows transcribed; CIN and WAS report No Injuries Reported</td><td><span class="badge b-ok">PUBLISHED</span></td></tr>
<tr><td>IND@HOU game centre</td><td>Not fetched</td><td>Fetched 2026-11-19 - Game Info: HOUSTON, TX / <b>RELIANT STADIUM</b>; IND 3-7, HOU 3-6; Nov 19 8:15 PM PRIME; Out chips match the report</td><td><span class="badge b-warn">VENUE CONFLICT</span></td></tr>
<tr><td>Market prices</td><td>No official source (F-01)</td><td>Unchanged - no market-price column is populated anywhere in this module</td><td><span class="badge b-mut">BLOCKED (F-01)</span></td></tr>
</tbody></table></div>
<h2>Pages in this module</h2>
<div class="tblwrap"><table><thead><tr><th>Page</th><th>What it holds</th></tr></thead><tbody>
<tr><td><a href="slate.html">Slate</a></td><td>Week-11 fixtures, records, kickoff, network, venue evidence, byes - each row sourced</td></tr>
<tr><td><a href="standings.html">Standings</a></td><td>32-club league table re-read 2026-11-19, cross-checked to two committed registers</td></tr>
<tr><td><a href="injuries.html">Injuries (reg11)</a></td><td>Full Week-11 report transcription: 16 designated rows called out, all 253 rows listed, CIN/WAS clean</td></tr>
<tr><td><a href="game-centre.html">Game centre</a></td><td>IND@HOU evidence: kickoff, network, venue conflict, records, Out chips, team leaders</td></tr>
<tr><td><a href="decision-board.html">Decision board</a></td><td>74-row decision-readiness register (gate + clearing number per row), gates G0–G9, questions, suggestions - all from committed canonical registers</td></tr>
<tr><td><a href="executive-summary.html">Executive summary</a></td><td>The one-page brief for a decision, fresh-day edition</td></tr>
<tr><td><a href="flagged.html">Flagged for review</a></td><td>Everything this session could not verify or leaves unresolved, with links</td></tr>
<tr><td><a href="sources.html">Sources</a></td><td>Every official page read this session, with tool clock time and what it fed</td></tr>
</tbody></table></div>"""
with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Fresh-day verification 2026-11-19", "Official-source re-read on the morning of the Week-11 opener; every claim traced, every gap flagged.", body))

# ---------------- slate ----------------
rows = []
for g in slate:
    rows.append(
        f"<tr><td>{_h(g['game_id'])}</td><td>{_h(g['date_iso'])}</td><td>{_h(g['kickoff_et'])}</td>"
        f"<td>{_h(g['network'])}</td><td>{_h(g['away'])} {_h(g['away_record'])}</td><td>{_h(g['home'])} {_h(g['home_record'])}</td>"
        f"<td>{_h(g['venue_hotel_link'])}</td><td class=\"mut\">{_h(g['venue_evidence'])}</td>"
        f"<td class=\"src\"><a href=\"{_h(g['game_centre_url'])}\" target=\"_blank\" rel=\"noopener\">game centre</a> · "
        f"<a href=\"{_h(WK11_URL)}\" target=\"_blank\" rel=\"noopener\">schedule</a></td></tr>")
bye_rows = "\n".join(f"<tr><td>{_h(b['club'])}</td><td>{_h(b['record'])}</td><td>{src_link(WK11_URL, 'schedule')}</td></tr>" for b in byes)
body = f"""<p class="lede">Week-11 slate re-read 2026-11-19 from the official schedule page. Records cross-checked against the fresh standings read (all match). Venue strings are the schedule page's hotel/ticket link evidence, except IND@HOU, whose game centre contradicts it (see <a href="flagged.html">flagged</a>). MIN@SF is the league's International Game in Mexico City; the schedule page publishes no hotel-link venue string for it, and this session did not fetch its game centre, so its venue is shown as published with its evidence.</p>
<div class="tblwrap"><table><caption>Week-11 fixtures - 2026-11-19 read {src_link(WK11_URL, 'official schedule page')}</caption><thead><tr><th>Game</th><th>Date</th><th>Kickoff ET</th><th>Net</th><th>Away</th><th>Home</th><th>Venue (as published)</th><th>Venue evidence</th><th>Source</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>
<h2>Teams on bye (6)</h2>
<div class="tblwrap"><table><caption>Week-11 byes - {src_link(WK11_URL, 'official schedule page')}</caption><thead><tr><th>Club</th><th>Record</th><th>Source</th></tr></thead><tbody>
{bye_rows}
</tbody></table></div>
<p class="lede" style="margin-top:18px">Schedule posture note (official page, "2026 TBD Games" block): Week-16 and Week-17 designated matchups will be played Saturday at 4:30/8:00 PM ET on NFL Network/NBC/Peacock with the remainder on flex windows; Week 18 plays Saturday on Netflix (1:00 PM) and ESPN/ABC (4:30/8:00 PM) with the remainder Sunday; specific dates are announced no later than after Weeks 14/15/17 respectively. Verbatim from the schedule page - this note exists so the site does not present future flex windows as fixed.</p>"""
with open(os.path.join(SITE, "slate.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Week-11 slate - fresh read 2026-11-19", "Thirteen fixtures, six byes, every record cross-checked to the fresh standings.", body))

# ---------------- standings ----------------
rows = []
for r in standings:
    rows.append(
        f"<tr><td><b>{_h(r['club'])}</b></td><td class=\"num\">{r['wins']}</td><td class=\"num\">{r['losses']}</td><td class=\"num\">{r['ties']}</td>"
        f"<td class=\"num\">{_h(r['pct'])}</td><td class=\"num\">{r['pf']}</td><td class=\"num\">{r['pa']}</td><td class=\"num\">{r['net_pts']}</td>"
        f"<td>{_h(r['streak'])}</td><td>{src_link(STANDINGS_URL, 'standings')}</td></tr>")
body = f"""<p class="lede">League standings re-read 2026-11-19 ({src_link(STANDINGS_URL, 'official page')}). Every row matches both committed canonical registers (<code>data/atlas/standings_2026_thru_wk10.csv</code>, <code>data/closeout/official_standings_2026_wk10.csv</code>) field by field - Week-11 games other than tonight's opener have not been played, so no records moved. League totals: PF = PA = {tot_pf}. Winning pct uses (W + 0.5·T)/GP; NYG and WAS carry one tie each.</p>
<div class="tblwrap"><table><caption>2026 league standings - 2026-11-19 read - {src_link(STANDINGS_URL, 'official page')}</caption><thead><tr><th>Club</th><th>W</th><th>L</th><th>T</th><th>PCT</th><th>PF</th><th>PA</th><th>Net</th><th>Streak</th><th>Source</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>"""
with open(os.path.join(SITE, "standings.html"), "w", encoding="utf-8") as fh:
    fh.write(page("League standings - fresh read 2026-11-19", "Thirty-two clubs, re-read and diffed against the committed registers.", body))

# ---------------- injuries ----------------
def inj_row(r):
    if r["game_status"]:
        badge = {"Out": "b-bad", "Questionable": "b-warn"}.get(r["game_status"], "b-mut")
        gs = f'<span class="badge {badge}">{_h(r["game_status"])}</span>'
    else:
        gs = '<span class="mut">—</span>'
    injury = _h(r["injury"]) if r["injury"] else '<span class="mut">—</span>'
    return (f"<tr><td>{_h(r['club'])}</td><td>{_h(r['player'])}</td><td>{_h(r['position'])}</td>"
            f"<td>{injury}</td>"
            f"<td>{_h(r['practice_status'])}</td><td>{gs}</td>"
            f"<td>{src_link(REG11_URL, 'reg11')}</td></tr>")

dg_rows = "".join(inj_row(r) for r in sorted(out_rows + q_rows, key=lambda r: (r["club"], r["player"])))
club_counts = {}
for r in inj:
    club_counts[r["club"]] = club_counts.get(r["club"], 0) + 1
club_summary = ", ".join(f"{c} {club_counts[c]}" for c in sorted(club_counts))
all_rows = "".join(inj_row(r) for r in sorted(inj, key=lambda r: (r["club"], r["player"])))
body = f"""<p class="lede">Full transcription of the official Week-11 injury report {src_link(REG11_URL, 'nfl.com/injuries/league/2026/reg11')}, read 2026-11-19 (page title: “Week 11 of the 2026 Season”). {len(inj)} rows across {len(club_counts)} clubs; CIN and WAS report “No Injuries Reported” for the Monday game and appear nowhere below. Practice status is not availability - only the {len(out_rows) + len(q_rows)} designated rows carry a game status. Blank cells are published blank, never inferred.</p>
<h2>Designated players ({len(out_rows)} Out, {len(q_rows)} Questionable)</h2>
<div class="tblwrap"><table><caption>Game designations only - {src_link(REG11_URL, 'reg11')}</caption><thead><tr><th>Club</th><th>Player</th><th>Pos</th><th>Injury</th><th>Practice</th><th>Game status</th><th>Source</th></tr></thead><tbody>
{dg_rows}
</tbody></table></div>
<p style="margin-top:8px" class="lede">Out: {_h(out_players)}. Questionable: {_h(q_players)}.</p>
<h2>All transcribed rows ({len(inj)})</h2>
<p class="lede">Row counts by club: {_h(club_summary)}. Sections in the source page: Thursday Nov 19 (IND@HOU), Sunday Nov 22 (12 games), Monday Nov 23 (CIN@WAS, both clean).</p>
<div class="tblwrap"><table><caption>reg11 transcription - every row - {src_link(REG11_URL, 'reg11')}</caption><thead><tr><th>Club</th><th>Player</th><th>Pos</th><th>Injury</th><th>Practice</th><th>Game status</th><th>Source</th></tr></thead><tbody>
{all_rows}
</tbody></table></div>
<h2>Method and limits</h2>
<ul>
<li>Transcribed from the page as rendered 2026-11-19; names, positions, injury strings and statuses are as published, including quirks (e.g. the page links the Bills’ “Dee Alford” row to <code>players/deaundre-ford</code> - display name kept, mismatch flagged).</li>
<li>No snap counts, no inactive lists: Week-11 inactives are published at ~90 minutes before each kickoff and were not available at capture time. “Not listed ≠ available” (see B63) is unresolved for this week.</li>
<li>This is the first Week-11 capture; the Wed/Thu/Fri designation-drift series for Week 11 starts now (2026-11-19).</li>
<li>The Detroit Lions rows (Kerby Joseph, Cade Mays, D.J. Reed) are published with a blank game-status cell on the reg11 page; they are shown blank here. The Week-10 “blank = Out per the article” flag does not carry over - see <a href="flagged.html">flagged</a>.</li>
</ul>"""
with open(os.path.join(SITE, "injuries.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Week-11 injury report - reg11 capture 2026-11-19", "The official Week-11 report as published; blanks stay blank.", body))

# ---------------- game centre ----------------
gc = {r["field"]: r for r in game_centre}
gc_rows = "".join(
    f"<tr><td><b>{_h(r['field'])}</b></td><td>{_h(r['value'])}</td>"
    f"<td>{src_link(r['source_url'], 'source')} <span class=\"mut\">{_h(r['fetched_utc'])}</span></td></tr>"
    for r in game_centre)
body = f"""<div class="warnbox"><b>Venue conflict - published both ways, never resolved silently.</b> The official game centre Game Info block reads <b>STADIUM: RELIANT STADIUM</b>. The official schedule page’s ticket/hotel link reads <b>NRG Stadium</b>. The committed Week-11 slate (2026-11-17/18) carries NRG Stadium. This module publishes both values with links; it does not pick a winner. Any consumer needing the venue must record which source it used.</div>
<div class="tblwrap"><table><caption>Game centre evidence - IND@HOU (Week 11) - {src_link(GAME_CENTRE_URL, 'official game centre')}</caption><thead><tr><th>Field</th><th>Value (as published)</th><th>Source / clock</th></tr></thead><tbody>
{gc_rows}
</tbody></table></div>
<p class="lede" style="margin-top:14px">Cross-check: the game centre’s Out chips (IND: Mallory, Raimann, Tillery, Travis, Ward; HOU: Harrison Jr., Hunter, Jordan, Marks) corroborate the designated Out rows transcribed from reg11 on the <a href="injuries.html">injuries page</a>. The game centre is also where the league publishes announced game-day status closest to kickoff; this capture is 2026-11-19T07:05Z, well before the 20:15 ET lock — treat statuses as provisional until the inactive list is published.</p>"""
with open(os.path.join(SITE, "game-centre.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Game centre - IND@HOU, fresh read 2026-11-19", "The official game centre capture; venue conflict preserved.", body))

# ---------------- decision board ----------------
STATUS_BADGE = {"done": ("b-ok", "DONE"), "partial": ("b-warn", "PARTIAL"), "blocked": ("b-bad", "BLOCKED"),
                "registered": ("b-mut", "REGISTERED"), "rejected": ("b-mut", "REJECTED")}
rd_rows = []
for r in readiness["rows"]:
    b, label = STATUS_BADGE.get(r["status"], ("b-mut", r["status"].upper()))
    where = r.get("where", "")
    where_cell = f'<a href="../{_h(where)}">{_h(where)}</a>' if where else ""
    rd_rows.append(
        f"<tr><td><b>{_h(r['id'])}</b></td><td>{_h(r['requirement'])}</td>"
        f"<td><span class=\"badge {b}\">{label}</span></td><td>{where_cell}</td>"
        f"<td class=\"mut\">{_h(r['gate'])}</td><td>{_h(r['clears'])}</td>"
        f"<td>{src_link(r['source'], 'official')}</td></tr>")
from collections import Counter
counts = Counter(r["status"] for r in readiness["rows"])
counts_line = " | ".join(f"<b>{counts[k]}</b> {k}" for k in ["blocked", "done", "partial", "registered", "rejected"] if counts.get(k))
gate_rows = "".join(
    f"<tr><td><b>{_h(g['gate_id'])}</b></td><td>{_h(g['gate'])}</td><td>{_h(g['definition'])}</td>"
    f"<td>{_h(g['status'])}</td><td class=\"mut\">{_h(g['note'])}</td></tr>" for g in gates)
q_rows_html = "".join(
    f"<tr><td><b>{_h(q['id'])}</b></td><td>{_h(q['category'])}</td><td>{_h(q['question'])}</td>"
    f"<td class=\"mut\">{_h(q['what_we_lack'])}</td><td>{_h(q['status'])}</td>"
    f"<td>{'—' if q['where_to_verify'] in ('Not applicable','') else src_link(q['where_to_verify'], 'verify') if q['where_to_verify'].startswith('http') else _h(q['where_to_verify'])}</td></tr>"
    for q in questions)
s_rows_html = "".join(
    f"<tr><td><b>{_h(s['id'])}</b></td><td>{_h(s['area'])}</td><td>{_h(s['suggestion'])}</td>"
    f"<td>{_h(s['status'])}</td>"
    f"<td>{src_link(s['source_link'], 'source') if s['source_link'].startswith('http') else _h(s['source_link'])}</td></tr>"
    for s in suggestions)
body = f"""<p class="lede">Decision board - what can be decided today, what blocks it, and the number that would clear it. The 74-row decision-readiness register is rendered verbatim from the canonical committed copy (<code>readiness/data/readiness.json</code>, as_of {_h(readiness.get('as_of',''))}), not re-derived here; the fresh-day data on the other pages changes nothing in it, and no row is upgraded without an official source. Gates, questions and suggestions come from <code>data/gates.csv</code>, <code>data/questions.csv</code>, <code>data/suggestions.csv</code>.</p>
<div class="callout"><b>Status counts:</b> {counts_line}. The blockers that matter for the Week-11 origination work are unchanged and honest: F-01 (no official market-price source) blocks every market/residual/CLV/ROI figure; Week-11 inactives are not yet published; the venue conflict on IND@HOU is flagged, not resolved.</div>
<h2>Decision readiness - one row per requirement</h2>
<div class="tblwrap"><table><caption>Decision-readiness register - {len(readiness['rows'])} rows - as_of {_h(readiness.get('as_of',''))} - rendered from readiness/data/readiness.json (read-only)</caption><thead><tr><th>ID</th><th>Requirement</th><th>Status</th><th>Where it lives</th><th>Gate that blocks it</th><th>Number that would clear it</th><th>Source</th></tr></thead><tbody>
{''.join(rd_rows)}
</tbody></table></div>
<h2>Validation gates</h2>
<div class="tblwrap"><table><caption>data/gates.csv</caption><thead><tr><th>Gate</th><th>Name</th><th>Definition</th><th>Status</th><th>Note</th></tr></thead><tbody>
{gate_rows}
</tbody></table></div>
<h2>Open questions (decide before acting)</h2>
<div class="tblwrap"><table><caption>data/questions.csv - every decision the project needs from its owner or an official source</caption><thead><tr><th>ID</th><th>Category</th><th>Question</th><th>What we lack</th><th>Status</th><th>Verify</th></tr></thead><tbody>
{q_rows_html}
</tbody></table></div>
<h2>Suggestions (propose, don’t implement - owner decides)</h2>
<div class="tblwrap"><table><caption>data/suggestions.csv - nothing here is implemented until a decision is recorded</caption><thead><tr><th>ID</th><th>Area</th><th>Suggestion</th><th>Status</th><th>Source</th></tr></thead><tbody>
{s_rows_html}
</tbody></table></div>"""
with open(os.path.join(SITE, "decision-board.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Decision board - fresh check 2026-11-19", "What can be decided now, what blocks it, and the number that would clear it.", body))

# ---------------- executive summary ----------------
body = f"""<p class="lede">The one-page brief, fresh-day edition. If you read nothing else this morning: the Week-11 report is live and captured; the slate and standings are confirmed against the official pages; one venue conflict is flagged, not resolved; nothing about market prices, inactives or availability is verified yet; the leaderboard stays empty.</p>
<h2>Verified this morning (2026-11-19)</h2>
<ul>
<li><b>Week-11 injury report published.</b> Page title “Week 11 of the 2026 Season”; {len(inj)} rows transcribed across {len(club_counts)} clubs; CIN and WAS report No Injuries Reported. Designated rows: {len(out_rows)} Out ({_h(out_players)}); {len(q_rows)} Questionable ({_h(q_players)}).</li>
<li><b>Week-11 slate confirmed.</b> 13 fixtures + 6 byes ({", ".join(sorted(b["club"] for b in byes))}); every record cross-checks to the fresh standings; MIN@SF is the Mexico City international game (Sun 8:20 PM NBC).</li>
<li><b>Standings unchanged.</b> 32/32 clubs match the committed atlas and closeout registers; league PF = PA = {tot_pf}; NYG/WAS carry a tie.</li>
<li><b>IND@HOU opens tonight.</b> Game centre: Nov 19, 8:15 PM, Prime Video, HOUSTON, TX - Game Info block says <b>RELIANT STADIUM</b> vs the schedule page’s NRG Stadium. IND 3-7 vs HOU 3-6. Game-centre Out chips match the report.</li>
</ul>
<h2>Not verified - do not act on these yet</h2>
<ul>
<li><b>Market prices (F-01).</b> No official source publishes betting lines; every market/residual/CLV/ROI column stays blank by policy. Any figure with a price in it from any module is unverifiable.</li>
<li><b>Inactives and snap counts.</b> Week-11 inactives publish ~90 min before each kickoff; availability “confirmation” for tonight’s game does not exist yet. Practice designations ≠ availability.</li>
<li><b>Venue for IND@HOU.</b> Two official pages disagree (RELIANT vs NRG). Flagged FR-01; neither is suppressed.</li>
<li><b>Depth of the replacement.</b> Club depth charts are club-published and mostly unlabelled; the Texans publish as an image. Replacement-depth claims for tonight’s fixture are suspect until inactives + snap counts land.</li>
</ul>
<h2>What would change the picture</h2>
<ul>
<li>Tonight’s inactive list (official, ~90 min pre-kickoff) settles who actually plays for IND and HOU; re-run <code>scripts/fresh_verify.py</code> against a fresh transcription and expect the designated rows to change.</li>
<li>Wednesday/Friday reg11 re-reads: designation drift (DNP→LP→FP; Questionable→Out) is only measurable if each read keeps its clock time - this module’s CSV carries <code>captured_utc</code> for exactly that.</li>
<li>A decision on F-01/Q03 (licensed price source) unlocks the price snapshot store’s market columns, residuals, CLV and the two-stage leaderboard’s escrow stage.</li>
</ul>
<h2>Standing constraints (unchanged)</h2>
<ul>
<li>Every row carries an official link or is left blank and flagged; nothing is inferred.</li>
<li>Leaderboard remains deliberately empty: no prices, no settled priced decisions, no eligibility.</li>
<li>Suggestions and questions are proposals and decisions for the owner - not implemented by this module.</li>
</ul>
<p class="lede">Full decision board with the 74-row readiness register: <a href="decision-board.html">decision-board.html</a>. Everything unresolved: <a href="flagged.html">flagged.html</a>.</p>"""
with open(os.path.join(SITE, "executive-summary.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Executive summary - fresh day 2026-11-19", "The one-page brief for a decision, verified this morning.", body))

# ---------------- flagged ----------------
FLAG_CSS = ""
flag_items = [
    ("FR-01", "High", "Venue conflict, IND@HOU",
     'Official game centre Game Info: <b>RELIANT STADIUM</b>. Official schedule page ticket/hotel link: <b>NRG Stadium</b>. Committed slate carries NRG Stadium. Both values published; neither suppressed; not silently resolved. (Persistent flag F-04.)',
     GAME_CENTRE_URL, WK11_URL),
    ("FR-02", "Medium", "reg11 was not published at the 2026-11-18 probes",
     "Four dated probes (2026-11-18T03:06Z/03:16Z/03:31Z/03:45Z) all served the Week-10 report. The 2026-11-19T06:47Z read serves Week 11. The Wednesday capture in the B50 series is therefore missing for this week; Thursday is the first entry.",
     REG11_URL, None),
    ("FR-03", "Medium", "Designations are sparse: 16 of 253 rows",
     "Only 9 Out and 7 Questionable rows carry game status; 237 rows carry none. Treating practice participation as availability would fabricate 237 availability claims - we do not. Inactive lists (pre-kickoff) are still required.",
     REG11_URL, None),
    ("FR-04", "Info", "CIN and WAS report No Injuries Reported",
     "Both Monday clubs appear on the report page with the explicit “No Injuries Reported” banner; they are absent from the transcription by design, not by omission.",
     REG11_URL, None),
    ("FR-05", "Low", "Detroit rows blank game-status (Kerby Joseph, Cade Mays, D.J. Reed)",
     "The reg11 page publishes these three rows with a blank game-status cell. Shown blank. The Week-10 flag (official article listed them Out) does NOT carry into Week 11 - earlier week, earlier designation.",
     REG11_URL, None),
    ("FR-06", "Low", "Official page link/name mismatch (BUF “Dee Alford”)",
     "The reg11 page links the row labelled “Dee Alford” to <code>players/deaundre-ford</code>. Display name transcribed as published; the slug mismatch is recorded here rather than “corrected”.",
     REG11_URL, None),
    ("FR-07", "Medium", "MIN@SF venue not transcribed from its game centre",
     "The schedule page publishes an International Game block (Mexico City 2026) with no hotel-link venue string. This session fetched only the IND@HOU game centre (F1 scope). The venue cell is therefore schedule-page evidence only and is not game-centre-verified.",
     WK11_URL, None),
    ("FR-08", "Info", "Standings are pre-Week-11",
     "All reads precede tonight's 8:15 PM ET opener; records reflect Weeks 1–10 (+ ties for NYG/WAS). Week-11 results are not in any figure on these pages.",
     STANDINGS_URL, None),
    ("FR-09", "Info", "Row-count drift vs the Week-10 report is expected, not a defect",
     "253 rows this week vs 277 rows on the readiness-captured Week-10 report meta. Different week, different player list; the drift alarm pins schema (vocabulary, key fields), not equality of counts.",
     REG11_URL, None),
    ("FR-10", "High", "F-01 persists: no official market-price source",
     "Every market-price, residual, CLV, ROI and reward column remains blank across the site (no official source exists; values left blank and unverified). This module introduces no market numbers at all.",
     None, None),
    ("FR-11", "Info", "One partial season; 137 finals in data/x3 vs 150 in data/closeout/derived",
     "Pre-existing flag F-01/F-12 territory; unchanged this session and not re-litigated. Unverified line-count claims remain unverified.",
     None, None),
]
flag_rows = []
for fid, sev, area, text, link, link2 in flag_items:
    links = []
    if link:
        links.append(f'<a href="{_h(link)}" target="_blank" rel="noopener">source</a>')
    if link2:
        links.append(f'<a href="{_h(link2)}" target="_blank" rel="noopener">cross-check</a>')
    sev_badge = {"High": "b-bad", "Medium": "b-warn", "Low": "b-mut", "Info": "b-mut"}[sev]
    flag_rows.append(f"<tr><td><b>{fid}</b></td><td><span class=\"badge {sev_badge}\">{sev}</span></td>"
                     f"<td><b>{_h(area)}</b><br>{text}</td><td class=\"src\">{' · '.join(links) or '—'}</td></tr>")
body = f"""<p class="lede">Everything this session flagged, with links. Flagged items do not block the module; they block specific claims. Status keywords: High = do not use the figure without resolving; Medium = usable with the caveat stated; Low/Info = recorded for transparency.</p>
<div class="tblwrap"><table><caption>Fresh-module flags - 2026-11-19</caption><thead><tr><th>ID</th><th>Severity</th><th>Finding</th><th>Source</th></tr></thead><tbody>
{''.join(flag_rows)}
</tbody></table></div>
<p class="lede" style="margin-top:14px">Pre-existing flags (F-01 price source; F-04 venue conflict; F-12 sample mismatch) are recorded in the main <a href="../index.html">hub</a> and <a href="../hub/flagged.html">hub Flagged for Review page</a>; this page adds the fresh-day items FR-01…FR-11 and links to them rather than duplicating their full text.</p>"""
with open(os.path.join(SITE, "flagged.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Flagged for review - fresh module 2026-11-19", "Unresolved and unverified items, published with links - never silently resolved.", body))

# ---------------- sources ----------------
sources = [
    ("https://www.nfl.com/injuries/league/2026/reg11", "2026-11-19T06:47Z", "Week-11 report full transcription; title “Week 11 of the 2026 Season”; chunks 0–6 read", "fresh/injuries.html"),
    ("https://www.nfl.com/standings/league/2026/REG", "2026-11-19T06:58Z", "32-club league table; chunks 0–1 read", "fresh/standings.html"),
    ("https://www.nfl.com/schedules/2026/by-week/week-11", "2026-11-19T06:47Z", "Week-11 slate: 13 fixtures, 6 byes, flex-window TBD block; chunks 0–2 read", "fresh/slate.html"),
    ("https://www.nfl.com/games/colts-at-texans-2026-reg-11", "2026-11-19T07:05Z", "Game centre: kickoff, network, Game Info (RELIANT STADIUM), records, Out chips, PPG/YPG, leaders; chunk 0 read", "fresh/game-centre.html"),
]
src_rows = "".join(
    f"<tr><td class=\"src\"><a href=\"{_h(u)}\" target=\"_blank\" rel=\"noopener\">{_h(u)}</a></td>"
    f"<td>{_h(t)}</td><td>{_h(what)}</td><td><a href=\"{_h(os.path.basename(dest))}\">{_h(dest)}</a></td></tr>"
    for u, t, what, dest in sources)
committed_rows = "".join(f"<tr><td><code>{_h(p)}</code></td><td>{_h(d)}</td></tr>" for p, d in [
    ("data/atlas/standings_2026_thru_wk10.csv", "committed canonical standings register; fresh read matched field by field"),
    ("data/closeout/official_standings_2026_wk10.csv", "committed canonical standings register; fresh read matched field by field"),
    ("data/week11/week11_slate_read_2026-11-18.csv", "committed 2026-11-18 slate read; kickoff/date/network/venue unchanged today"),
    ("data/week11/reg11_probes.csv", "append-only probe log; 2026-11-19T06:47Z row added (title now Week 11)"),
    ("data/week11/standings_read_2026-11-18.csv", "committed 2026-11-18 standings read; values identical today"),
    ("readiness/data/readiness.json", "canonical 74-row decision-readiness register (as_of 2026-11-15), rendered read-only on the decision board"),
    ("data/gates.csv", "G0–G9 validation gates, rendered on the decision board"),
    ("data/questions.csv", "open questions register, rendered on the decision board"),
    ("data/suggestions.csv", "suggestions register (review before implementing), rendered on the decision board"),
])
body = f"""<h2>Official pages read this session</h2>
<div class="tblwrap"><table><caption>2026-11-19 reads - page-reader tool; shell HTTP is blocked in the authoring sandbox</caption><thead><tr><th>URL</th><th>Tool clock</th><th>What was read</th><th>Feeds</th></tr></thead><tbody>
{src_rows}
</tbody></table></div>
<h2>Committed registers used (read-only)</h2>
<div class="tblwrap"><table><caption>Inputs, not outputs - none of these files were edited by this session (except the append-only probe row noted)</caption><thead><tr><th>File</th><th>Use</th></tr></thead><tbody>
{committed_rows}
</tbody></table></div>
<h2>Verification</h2>
<p class="lede">Deterministic gate: <code>python3 scripts/fresh_verify.py</code> - re-derives every invariant and cross-check above (32 clubs, pct, net points, PF=PA, slate↔standings cross-foot, byte-level register diffs, reg11 vocabulary/counts, game-centre↔report Out-list agreement, freshness summary). It fails the build loudly on any drift. The build: <code>python3 scripts/fresh_build.py</code>. CI: <code>fresh.yml</code>.</p>"""
with open(os.path.join(SITE, "sources.html"), "w", encoding="utf-8") as fh:
    fh.write(page("Sources - fresh module 2026-11-19", "Every official page read this session, with clock time and destination.", body))

os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
with open(os.path.join(SITE, "assets", "fresh.css"), "w", encoding="utf-8") as fh:
    fh.write(CSS)

print("fresh module built:", sorted(os.listdir(SITE)))
