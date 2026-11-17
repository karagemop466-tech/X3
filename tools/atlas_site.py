#!/usr/bin/env python3
"""Build the atlas/ decision desk from data/atlas/*.csv (session arena/dbb50f8c-x3).

Rules held by this renderer:
  * every data row carries an official-source link, or is rendered blank with an
    explicit UNVERIFIED / BLOCKED / DERIVED marker;
  * no value is invented - a cell is either read from a CSV that was transcribed
    from an official page, or it is empty;
  * links are page-relative, because GitHub Pages serves this repo under /X3/.
"""
from __future__ import annotations

import csv
import html
from pathlib import Path

import atlas_data as D
import atlas_engine as E

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "atlas"
SITE = ROOT / "atlas"
COMMITTED_INJURY = ROOT / "data" / "hub" / "injuries_2026_wk10.csv"

NAV = [
    ("index.html", "Overview"),
    ("executive-summary.html", "Executive summary"),
    ("standings.html", "Standings"),
    ("results.html", "Results feed"),
    ("fixtures.html", "Week 11 fixtures"),
    ("team-stats.html", "Team stats"),
    ("injuries.html", "Injury report"),
    ("injury-rows.html", "Injury rows"),
    ("availability.html", "Availability events"),
    ("origination.html", "Originated lines"),
    ("prices.html", "Price store"),
    ("strategy.html", "Strategies"),
    ("leaderboard.html", "Leaderboard"),
    ("gates.html", "Validation gates"),
    ("correlation.html", "Correlation"),
    ("luck.html", "Luck removed"),
    ("depth.html", "Depth &amp; deficiency"),
    ("readiness.html", "Readiness"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("repo-review.html", "Repo review"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
]

CSS = """
:root{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f7f9fc;--card:#fff;
--ok:#047857;--bad:#b91c1c;--warn:#b45309;--info:#1d4ed8;--chip:#eef2ff}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
header.top{background:#0f172a;color:#fff;padding:14px 22px;display:flex;flex-wrap:wrap;
gap:12px;align-items:baseline;justify-content:space-between}
header.top a{color:#fff;text-decoration:none}
header.top .brand{font-weight:700;font-size:17px}
header.top .asof{color:#cbd5e1;font-size:13px}
.wrap{display:flex;align-items:flex-start;gap:0;max-width:1500px;margin:0 auto}
nav.side{width:230px;flex:0 0 230px;background:#fff;border-right:1px solid var(--line);
padding:12px 0;position:sticky;top:0;max-height:100vh;overflow:auto}
nav.side a{display:block;padding:7px 16px;color:#334155;text-decoration:none;font-size:13.5px;
border-left:3px solid transparent}
nav.side a:hover{background:var(--chip)}
nav.side a.on{background:var(--chip);border-left-color:var(--info);font-weight:600;color:var(--info)}
main{flex:1;min-width:0;padding:20px 26px 60px}
h1{font-size:25px;margin:0 0 6px}
h2{font-size:18px;margin:26px 0 8px;padding-bottom:5px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:18px 0 6px}
p{margin:8px 0}
.lede{color:#475569;font-size:14.5px;margin:0 0 4px}
.note{color:var(--mut);font-size:13px}
.mut{color:var(--mut)}
code{background:#eef2f7;padding:1px 5px;border-radius:3px;font-size:12.5px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:13px}
.card .num{font-size:24px;font-weight:700;line-height:1.1}
.card .lbl{font-size:12.5px;color:#334155;margin-top:3px}
.card .sub{font-size:11.5px;color:var(--mut);margin-top:5px}
.tblwrap{overflow:auto;border:1px solid var(--line);border-radius:8px;background:#fff;margin:10px 0 6px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f1f5f9;font-weight:600;position:sticky;top:0;font-size:12.5px;white-space:nowrap}
tbody tr:hover{background:#f8fafc}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;font-size:10.5px;font-weight:700;padding:2px 6px;border-radius:4px;
letter-spacing:.02em}
.v{background:#dcfce7;color:var(--ok)}
.u{background:#fef3c7;color:var(--warn)}
.b{background:#fee2e2;color:var(--bad)}
.d{background:#e0e7ff;color:#3730a3}
.p{background:#f1f5f9;color:#475569}
.unverif{color:var(--mut);font-style:italic}
a.src{color:var(--info);text-decoration:none;font-size:12.5px}
a.src:hover{text-decoration:underline}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid var(--info);
border-radius:6px;padding:12px 14px;margin:14px 0}
.warnbox{background:#fff;border:1px solid var(--line);border-left:4px solid var(--warn);
border-radius:6px;padding:12px 14px;margin:14px 0}
ul,ol{margin:8px 0 8px 20px;padding:0}
li{margin:4px 0}
footer{max-width:1500px;margin:0 auto;padding:16px 26px 40px;color:var(--mut);font-size:12.5px;
border-top:1px solid var(--line)}
@media(max-width:900px){.wrap{flex-direction:column}nav.side{width:100%;flex:none;position:static;
max-height:none;border-right:0;border-bottom:1px solid var(--line)}}
"""


def esc(v):
    return html.escape("" if v is None else str(v), quote=True)


def short_url(u):
    u = u.replace("https://www.", "").replace("https://", "")
    return u if len(u) <= 46 else u[:43] + "..."


def cell_html(value, numeric=False, link=True):
    v = "" if value is None else str(value)
    if v.startswith("http") and link:
        return f'<a class="src" href="{esc(v)}" target="_blank" rel="noopener">{esc(short_url(v))}</a>'
    if v == "":
        return '<span class="unverif">UNVERIFIED - no official source</span>'
    if numeric:
        return f'<td class="num">{esc(v)}</td>'
    return esc(v)


def table(csv_name, cols, headers, numeric=(), max_rows=None, cls="k-data"):
    path = DATA / csv_name
    if not path.exists():
        return '<p class="note">table source missing</p>'
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    if max_rows:
        rows = rows[:max_rows]
    out = [f'<div class="tblwrap"><table class="{cls}"><thead><tr>']
    for i, h in enumerate(headers):
        out.append(f'<th class="num">{esc(h)}</th>' if i in numeric else f"<th>{esc(h)}</th>")
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for i, c in enumerate(cols):
            val = r.get(c, "")
            if i in numeric:
                out.append(f'<td class="num">{esc(val) if not str(val).startswith("http") else cell_html(val)}</td>')
            else:
                out.append(f"<td>{cell_html(val)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def badge(text, kind="d"):
    return f'<span class="badge {kind}">{esc(text)}</span>'


def page(name, title, body, active=None):
    active = active or name
    nav = "".join(
        f'<a href="{esc(href)}" class="{"on" if href == active else ""}">{lbl}</a>'
        for href, lbl in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 atlas</title>
<link rel="stylesheet" href="assets/atlas.css">
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">X3 <span>atlas</span></a> - NFL decision desk</div>
  <div class="asof">verified data as of <b>{D.AS_OF}</b> - 2026 season, week {D.WEEK_COMPLETE} complete, week {D.WEEK_NEXT} ahead</div>
</header>
<div class="wrap">
<nav class="side">{nav}</nav>
<main>
<h1>{esc(title)}</h1>
{body}
</main>
</div>
<footer>
X3 atlas - module of <a href="https://github.com/karagemop466-tech/X3">karagemop466-tech/X3</a>.
Built by session <code>arena/dbb50f8c-x3</code>. Every row on every page either links the official
page it was transcribed from, or is marked UNVERIFIED / BLOCKED / DERIVED. Nothing is inferred.
Shared task board: <a href="https://github.com/karagemop466-tech/X3/blob/main/COORDINATION.md">COORDINATION.md</a>.
</footer>
</body>
</html>
"""


def cards(items):
    out = ['<div class="cards">']
    for num, lbl, sub in items:
        out.append(f'<div class="card"><div class="num">{esc(num)}</div>'
                   f'<div class="lbl">{esc(lbl)}</div><div class="sub">{esc(sub)}</div></div>')
    out.append("</div>")
    return "".join(out)


def write(name, title, body):
    (SITE / name).write_text(page(name, title, body), encoding="utf-8")


# --------------------------------------------------------------------------
# derived numbers used in prose
# --------------------------------------------------------------------------
def build():
    rates, outs, orig, pyth, corr, S = E.build()
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (SITE / "assets" / "atlas.css").write_text(CSS, encoding="utf-8")

    # full injury table, copied from the committed capture with a source column
    inj_rows = []
    if COMMITTED_INJURY.exists():
        with COMMITTED_INJURY.open() as fh:
            for r in csv.DictReader(fh):
                inj_rows.append({**r, "source": D.SOURCES["injuries"]["url"]})
    if inj_rows:
        with (DATA / "injury_report_2026_wk10.csv").open("w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(inj_rows[0].keys()))
            wr.writeheader()
            wr.writerows(inj_rows)

    src_std = D.SOURCES["standings"]["url"]
    src_wk10 = D.SOURCES["wk10"]["url"]
    src_wk11 = D.SOURCES["wk11"]["url"]
    src_inj = D.SOURCES["injuries"]["url"]
    src_news = D.SOURCES["news1117"]["url"]
    src_odds = D.SOURCES["odds404"]["url"]

    # ================================================== index / landing
    readiness_rows = "".join(
        f'<tr><td><b>{esc(r[0])}</b></td><td>{esc(r[1])}</td>'
        f'<td>{badge(r[2], {"DONE": "v", "PARTIAL": "u", "BLOCKED": "b", "NOT STARTED": "p"}.get(r[2], "d"))}</td>'
        f'<td><code>{esc(r[3])}</code></td><td>{esc(r[4])}</td></tr>'
        for r in D.REQUIREMENTS
    )
    body = f"""
<p class="lede">A dated, source-first NFL decision desk. Every number below was transcribed from an
official NFL page on {D.AS_OF} or computed from those transcriptions by a rule that is printed on
the page. Where the league publishes nothing - market prices above all - the cell is blank and
marked, not estimated.</p>
{cards([("150", "games in the official standings", "32 clubs, 300 club-games, through Week 10"),
        ("14", "Week 10 finals transcribed", "plus 4 clubs on bye"),
        ("13", "Week 11 fixtures with venues", "each venue read from that game's own game centre"),
        ("345", "Week 10 injury rows", "66 Out, 10 Doubtful, 84 Questionable, 185 with no designation"),
        ("0", "market prices", "nfl.com/odds is a 404 - every market cell is blank and blocked"),
        ("0", "strategies ranked", "the leaderboard is a scoring design, not a result")])}
<h2>What is verified, what is derived, what is blocked</h2>
<div class="callout"><p><b>VERIFIED</b> means this session read the value on the official page and
copied it. <b>DERIVED</b> means arithmetic on verified values, with the rule shown.
<b>BLOCKED</b> means the input does not exist in any official source this session could read -
most importantly a market price. <b>UNVERIFIED</b> means the cell is empty on purpose.</p></div>
<h2>Decision readiness - one row per requirement</h2>
<p class="note">One row for every requirement in the project brief. The clearing number is a project
target set by this desk, not a figure published by the NFL. 68 requirements registered;
{sum(1 for r in D.REQUIREMENTS if r[2] == 'DONE')} done,
{sum(1 for r in D.REQUIREMENTS if r[2] == 'PARTIAL')} partial,
{sum(1 for r in D.REQUIREMENTS if r[2] == 'BLOCKED')} blocked,
{sum(1 for r in D.REQUIREMENTS if r[2] == 'NOT STARTED')} not started.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>ID</th><th>Requirement</th><th>Status</th><th>Gate that blocks it</th>
<th>Number that would clear it</th></tr></thead>
<tbody>{readiness_rows}</tbody></table></div>
<h2>Start here</h2>
<ul>
<li><a href="executive-summary.html">Executive summary</a> - the one-page read.</li>
<li><a href="origination.html">Originated lines</a> - our own side, total and moneyline for Week 11,
pre-registered before the Thursday kickoff.</li>
<li><a href="injuries.html">Injury report</a> - what the league published for Week 10, counted live
and reconciled to the committed capture.</li>
<li><a href="questions.html">Questions</a> - what we know, what we do not, and what would answer it.</li>
<li><a href="suggestions.html">Suggestions</a> - proposals to review before anything is implemented.</li>
<li><a href="flagged.html">Flagged for review</a> - every irregularity found, each with its source.</li>
</ul>
"""
    write("index.html", "Overview", body)

    # ================================================== executive summary
    body = f"""
<p class="lede">One page: what the official data says today, what the model says about Week 11, and
the four decisions that gate everything else.</p>
{cards([(str(S["games_implied"]), "games played in 2026", "implied by the official standings (300 club-games)"),
        (f'{S["league_ppg"]:.2f}', "points per club-game", "league average, official standings"),
        (f'{S["luck_sd"]:.2f}', "wins of luck (1 SD)", "Pythagorean residual across 32 clubs"),
        ("0", "market prices available", "nfl.com/odds returns 404")])}
<h2>What the official data says</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Finding</th><th>Number</th><th>Basis</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Season games played through Week 10</td><td class="num">{S["games_implied"]}</td>
<td>300 club-games in the standings / 2</td><td>{cell_html(src_std)}</td></tr>
<tr><td>League points per club-game</td><td class="num">{S["league_ppg"]:.2f}</td>
<td>6,923 total points / 300 club-games</td><td>{cell_html(src_std)}</td></tr>
<tr><td>Week 10 finals transcribed</td><td class="num">{S["wk10_games"]}</td>
<td>Thursday through Monday night; 4 clubs on bye</td><td>{cell_html(src_wk10)}</td></tr>
<tr><td>Week 10 absolute margin, SD</td><td class="num">{S["wk10_margin_sd"]:.2f}</td>
<td>n=14 finals - one week, so a thin basis</td><td>{cell_html(src_wk10)}</td></tr>
<tr><td>Luck spread in the standings</td><td class="num">{S["luck_sd"]:.2f} wins</td>
<td>SD of (actual wins - Pythagorean expected wins), n=32</td><td>{cell_html(src_std)}</td></tr>
<tr><td>Pythagorean fit to actual win %</td><td class="num">r = {S["luck_r"]:.3f} (r&#178; = {S["luck_r2"]:.3f})</td>
<td>exponent {D.MODEL["pythagorean_exponent"]}, n=32</td><td>{cell_html(src_std)}</td></tr>
<tr><td>Week 10 injury rows in the committed capture</td><td class="num">345</td>
<td>28 club sections; 160 carry a game designation</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>Week 10 injury rows counted live today</td><td class="num">347</td>
<td>27 of 28 club counts match the capture; Ravens differ</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>Week 11 designations published</td><td>{badge("NONE", "u")}</td>
<td>Every Week 11 game centre reads "Injury Report is not available at this time"</td>
<td>{cell_html(src_wk11)}</td></tr>
<tr><td>Week 10 games the standings page credits</td><td class="num">13 of 14</td>
<td>26 clubs moved, 4 on bye, and 2 - Washington and the Giants - did not move at all</td>
<td>{cell_html(src_std)}</td></tr>
<tr><td>Market prices published by the league</td><td>{badge("NONE", "b")}</td>
<td>nfl.com/odds returns 404 - Flag on the Play</td><td>{cell_html(src_odds)}</td></tr>
</tbody></table></div>
<h2>What the model says about Week 11</h2>
<div class="warnbox"><p><b>Pre-registered, not graded.</b> Model
<code>{D.MODEL["id"]}</code> and its constants were committed on {D.MODEL["declared"]}, before the
first Week 11 kickoff ({D.MODEL["kickoff_first"]}). No Week 11 result exists yet, so every forecast
on this site is ungraded. It will be scored against the official Week 11 box scores after they are
published, and the score will be posted next to the forecast, not in place of it.</p></div>
<h2>The four decisions that gate everything else</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Decision</th><th>Why it blocks</th><th>If it is not taken</th></tr></thead>
<tbody>
<tr><td>Approve a price source class</td><td>Without any market price, fair-vs-market, CLV, ROI and
every staking score are structurally impossible, not merely missing</td>
<td>The board stays a signal board; no staking column can ever be filled</td></tr>
<tr><td>Approve an automated capture schedule</td><td>Designations are a series, and one capture
cannot produce a delta, so the injury signal can never be a surprise rather than a level</td>
<td>Injury stays a stale level and the availability graph stays empty</td></tr>
<tr><td>Approve a depth-order source (chart or snap counts)</td><td>"Second-string cornerback facing
a number one receiver" cannot be computed without a verified depth rank for all 32 clubs</td>
<td>The deficiency matrix stays blocked; it is not approximated</td></tr>
<tr><td>Rule on rewards and on storing raw rows</td><td>A funded leaderboard is a regulated contest in
some jurisdictions, and league terms govern republication of row-level data</td>
<td>Rewards stay notional and raw rows stay private</td></tr>
</tbody></table></div>
"""
    write("executive-summary.html", "Executive summary", body)

    # ================================================== standings
    body = f"""
<p class="lede">All 32 clubs, transcribed field for field from the official league standings on
{D.AS_OF}. Points per game and points allowed per game are arithmetic on the published PF, PA and
games played.</p>
"""
    body += table("standings_2026_thru_wk10.csv",
                  ["team", "name", "w", "l", "t", "pct", "pf", "pa", "net", "home", "road",
                   "div", "conf", "nonconf", "streak", "last5", "games", "ppg", "papg", "win_pct", "source"],
                  ["Team", "Club", "W", "L", "T", "PCT", "PF", "PA", "Net", "Home", "Road",
                   "Div", "Conf", "Non-conf", "Streak", "Last 5", "G", "PPG", "PAPG", "Win %", "Source"],
                  numeric={2, 3, 4, 5, 6, 7, 8, 16, 17, 18, 19})
    body += f"""
<h2>The standings page is missing one Week 10 game</h2>
<div class="warnbox"><p><b>Verified on {D.AS_OF}.</b> The official league standings page has folded
in {S["clubs_credited_wk10"]} of the 28 clubs that played in Week 10. Four clubs
({esc(", ".join(D.WEEK10_BYES))}) were on bye and correctly show no change. The remaining two,
<b>Washington</b> and the <b>New York Giants</b>, played each other on Thursday 12 November - Washington
won 24-21 - and neither club's row has moved: Washington still reads 3-5-1 with 196 points for, and
the Giants still read 5-3-1 with 203 points for, exactly as they did in the capture taken three days
earlier on 2026-11-14. Their streak and last-5 columns also read 1W and 1L respectively in both
captures.</p>
<p>Two consequences follow, and both matter. First, the standings imply
{S["games_implied"]} games played, while the official schedule page lists 14 Week 10 finals on top of
the 137 the earlier capture implies - 151, not {S["games_implied"]}. Any check that reconciles a
results feed to the standings on games played will fail by one game until the league corrects this.
Second, every per-game rate for Washington and the Giants on this module is computed over nine games,
not ten, because the published points-for and points-against are one game short. Those two clubs play
in Week 11 (Cincinnati at Washington, Jacksonville at the Giants), so this affects the originated
lines on the next page and is flagged there too.</p>
<p>This is stated as an observation about two official pages. The cause is not published, so it is not
asserted here.</p></div>
<h3>Club-by-club: what moved between the two captures</h3>
<p class="note">Left half from the capture taken 2026-11-14; right half read live on {D.AS_OF}. Both
come from the same official page.</p>
"""
    body += table("standings_reconciliation_2026.csv",
                  ["team", "name", "record_2026_11_14", "record_2026_11_17", "pf_before", "pf_after",
                   "pa_before", "pa_after", "week_10_game_credited", "source_live"],
                  ["Team", "Club", "Record on 11-14", "Record on 11-17", "PF before", "PF after",
                   "PA before", "PA after", "Week 10 game credited?", "Source"],
                  numeric={4, 5, 6, 7})
    write("standings.html", "Standings through Week 10", body)

    # ================================================== results
    body = f"""
<p class="lede">Every Week 10 final, transcribed from the official schedule page. These 14 games are
the most recent completed round and the only round this module has transcribed end to end.</p>
<div class="callout"><p><b>Results feed status: PARTIAL.</b> The official standings imply
{S["games_implied"]} games have been played in 2026; this module has transcribed
{S["wk10_games"]} of them ({S["wk10_games"] * 100 // S["games_implied"]}%). Weeks 1 to 9 have not been
re-read from an official page by this session, so they are not published here. A results feed is only
as good as its weakest row, and a feed that publishes 14 rows while implying 150 is not a backtest
corpus yet.</p>
<p>One caution for anyone extending this feed: the standings count of {S["games_implied"]} is itself
one short of the schedule page, because the league has not credited the Thursday 12 November
Washington-New York Giants game to either club (F-16). Reconciling on games played will therefore not
balance until the league corrects it, and the shortfall is the league's, not the feed's.</p></div>
"""
    body += table("results_2026_wk10.csv",
                  ["game", "date", "away", "home", "away_pts", "home_pts", "home_margin",
                   "winner", "slot", "source"],
                  ["Game", "Date", "Away", "Home", "Away pts", "Home pts", "Home margin",
                   "Winner", "Slot", "Source"],
                  numeric={4, 5, 6})
    body += f"""
<h3>Clubs on bye in Week 10</h3>
<p>{esc(", ".join(D.WEEK10_BYES))} - {cell_html(src_wk10)}</p>
<h3>What a verified results row requires</h3>
<ol>
<li>The score comes from an official NFL box score or schedule page, never from a live-score widget.</li>
<li>The row is appended, never overwritten, and keeps the date it was read.</li>
<li>A pending game is published as pending; a live score is never treated as a result.</li>
<li>Each round is reconciled back to the official standings: wins, losses, ties, points for and
points against must add up.</li>
</ol>
"""
    write("results.html", "Verified results feed", body)

    # ================================================== fixtures
    conflicts = [f for f in D.WEEK11_FIXTURES if f[7].split()[0].upper() not in f[8].upper()]
    body = f"""
<p class="lede">All 13 Week 11 fixtures with kickoff date, time, network, and the venue transcribed
from each game's own official game centre. The schedule page carries a second venue string in its
hotel link; both are published and the {len(conflicts)} disagreements are flagged, because two
official pages naming the same stadium differently is exactly the sort of drift this desk exists to
catch.</p>
"""
    body += table("fixtures_2026_wk11.csv",
                  ["game", "date", "time_et", "network", "away", "home", "location",
                   "stadium_game_centre", "stadium_schedule_page", "venue_flag", "source_gc"],
                  ["Game", "Date (ET)", "Time (ET)", "Network", "Away", "Home", "Location",
                   "Stadium (game centre)", "Stadium (schedule page)", "Venue flag", "Source"],
                  numeric=())
    body += f"""
<h3>Clubs on bye in Week 11</h3>
<p>{esc(", ".join(D.WEEK11_BYES))} - {cell_html(src_wk11)}</p>
<h3>Schedule changes already published for Week 12</h3>
<p>Cleveland's Week 12 game against Las Vegas has been flexed to Sunday Night Football at 8:20pm ET
on Nov 29, and Jacksonville's Week 12 game at Tennessee has been flexed to 1:00pm ET on FOX -
{cell_html(src_news)}. This is why fixture context is captured as a dated series and not read once.</p>
"""
    write("fixtures.html", "Week 11 fixtures and venues", body)

    # ================================================== team stats
    body = f"""
<p class="lede">Official season team stats for the 26 clubs playing in Week 11, transcribed from each
game centre's "Regular season at a glance" panel. These are the only opponent-facing inputs this
module uses, and they are season-to-date through Week 10 - no future information leaks into them.</p>
"""
    body += table("team_stats_2026_thru_wk10.csv",
                  ["team", "name", "ppg", "ypg", "top_per_game", "def_sacks", "def_ints",
                   "turnover_diff", "source"],
                  ["Team", "Club", "Points/game", "Yards/game", "Time of possession",
                   "Def sacks", "Def INTs", "Turnover diff", "Source"],
                  numeric={2, 3, 5, 6, 7})
    body += """
<p class="note">Six clubs on bye in Week 11 (ATL, CLE, GB, LAR, NE, SEA) have no Week 11 game centre,
so no stats row is published for them here. Their standings row on the standings page remains
available and verified.</p>
"""
    write("team-stats.html", "Official team stats", body)

    # ================================================== injuries
    body = f"""
<p class="lede">The official Week 10 injury report: what the league published, how many rows it has,
and how many of them actually carry a game designation. Counted live on {D.AS_OF} across all eight
pages of the report, then reconciled club by club against the capture committed by an earlier
session on 2026-11-14.</p>
{cards([("345", "rows in the committed capture", "28 club sections, read 2026-11-14"),
        ("347", "rows counted live today", "eight pages read on 2026-11-17"),
        ("160", "designated rows in the capture", "66 Out, 10 Doubtful, 84 Questionable"),
        ("185", "rows with no designation", "no game status published for these players"),
        ("27 / 28", "club counts that agree", "Ravens is the one club that differs"),
        ("0", "Week 11 designations", "the league has not published them")])}
<h3>The claim in the brief, tested</h3>
<div class="callout"><p>The project brief states that "only 6 of 254 report rows carry a game
designation". That is not what the official page says. The committed capture holds 345 rows of which
160 carry a game designation; this session's independent live count is 347 rows. Neither number is
close to 254 or to 6. The brief's figure is wrong and should not be used as a planning assumption.</p></div>
<h3>Designation totals from the committed capture (exact, computed from the rows)</h3>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Game status</th><th>Rows</th><th>Share of 345</th><th>Basis</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Out</td><td class="num">66</td><td class="num">19.1%</td><td>counted from the capture file</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>Doubtful</td><td class="num">10</td><td class="num">2.9%</td><td>counted from the capture file</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>Questionable</td><td class="num">84</td><td class="num">24.3%</td><td>counted from the capture file</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>No designation published</td><td class="num">185</td><td class="num">53.6%</td><td>counted from the capture file</td><td>{cell_html(src_inj)}</td></tr>
</tbody></table></div>
<h3>Per-club reconciliation: live count versus committed capture</h3>
"""
    body += table("injury_counts_2026_wk10.csv",
                  ["team", "name", "rows_live_2026_11_17", "rows_committed_2026_11_14",
                   "designated_live", "designated_committed", "flag", "source"],
                  ["Team", "Club", "Rows live (11-17)", "Rows committed (11-14)",
                   "Designated live", "Designated committed", "Flag", "Source"],
                  numeric={2, 3, 4, 5})
    body += f"""
<h3>The one club that differs</h3>
<div class="warnbox"><p><b>Ravens.</b> The live report lists 10 Baltimore rows; the committed capture
holds 8. The two rows absent from the capture are <b>Calais Campbell</b> (DT, did not participate)
and <b>Ronnie Stanley</b> (T, did not participate). Two designations are also absent from the
capture: <b>Jaylinn Hawkins</b> is shown with no game status in the capture but is <b>Out</b> on the
live page, and <b>Adam Randall</b> is blank in the capture but <b>Questionable</b> live. Flagged as
F-02. {cell_html(src_inj)}</p></div>
<h3>How to read a designation</h3>
<ul>
<li>A designation is a level, not a signal. Out, Doubtful and Questionable are what the club
published on a given day, and this desk will not convert them into a probability until the league's
own designations have been joined to inactives over several seasons (requirement R-53, not started).</li>
<li>The signal is the <b>change</b> between two dated reads. That needs at least two captures a week,
which is requirement R-54 and is not yet implemented - one capture is not a series.</li>
<li>A player absent from the report is not healthy. He may be on injured reserve: Malik Willis does
not appear in the Week 10 report because Miami placed him on IR on 2026-11-11, not because he is
available. {cell_html(src_inj)}</li>
</ul>
<p>See the full 345-row table on the <a href="injury-rows.html">injury rows</a> page.</p>
"""
    write("injuries.html", "Injury report - Week 10", body)

    # ================================================== injury rows
    body = f"""
<p class="lede">Every row of the official Week 10 injury report as captured on 2026-11-14 by an
earlier session and re-read club by club on {D.AS_OF}. This page publishes the capture as captured;
the Ravens difference is documented on the <a href="injuries.html">injury report</a> page and flagged
on <a href="flagged.html">flagged for review</a>.</p>
"""
    body += table("injury_report_2026_wk10.csv",
                  ["date", "game", "team", "player", "pos", "injury", "practice", "status", "source"],
                  ["Date", "Game", "Club", "Player", "Pos", "Injury", "Practice", "Game status", "Source"],
                  numeric=())
    write("injury-rows.html", "Injury report - every row", body)

    # ================================================== availability events
    body = f"""
<p class="lede">Dated roster and availability events read from official NFL pages. This is the
availability graph in its current, admittedly partial, form: one row per event, each with the date
the league published it and the page it came from.</p>
<div class="callout"><p><b>Why this page exists.</b> Depth charts go stale. A club can list a player
at a position weeks after he went on injured reserve and a replacement was traded in. Availability
evidence has to be versioned against the last official roster event, otherwise "listed as the
starter" quietly becomes a false statement. This register is the versioning spine.</p></div>
"""
    body += table("roster_events_2026.csv",
                  ["date", "club", "kind", "player", "detail", "source"],
                  ["Date", "Club", "Kind", "Player", "What the official page says", "Source"],
                  numeric=())
    body += """
<h3>What is missing from this register</h3>
<ul>
<li>It is ad hoc: 16 of 32 clubs appear, because this session read the roundups it could and the
report pages that exist. The 32-club sweep (R-13) is not done.</li>
<li>There is no inactive list and no snap share yet (R-29), so a backup replacing a starter can be
suspected but not confirmed.</li>
<li>Only one capture exists, so no delta can be published. The injury signal must be a surprise, not
a level, and a surprise needs two reads.</li>
</ul>
"""
    write("availability.html", "Availability and roster events", body)

    # ================================================== origination
    body = f"""
<p class="lede">Our own line for every Week 11 game: the side first, then the total, then the
moneyline - in that order, because the moneyline is derived from the side model and must never be
priced on its own.</p>
<div class="warnbox"><p><b>PRE-REGISTERED, UNGRADED.</b> Model <code>{D.MODEL["id"]}</code> was
committed on {D.MODEL["declared"]}, before the first Week 11 kickoff. The constants are declared, not
fitted to Week 11, because no Week 11 result exists. Every number on this page is DERIVED from
official standings and official injury rows; none of it is a result.</p></div>
<h2>The model, printed in the open</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Part</th><th>Rule or constant</th><th>Value</th><th>Basis</th></tr></thead>
<tbody>
<tr><td>Inputs</td><td>{esc(D.MODEL["inputs"])}</td><td>{badge("VERIFIED", "v")}</td>
<td>{cell_html(src_std)}</td></tr>
<tr><td>Home-field constant</td><td>Points added to the home side</td>
<td class="num">{D.MODEL["hfa_points"]:.2f}</td>
<td>Declared before kickoff, not fitted. The league publishes no points-based home-field figure.</td></tr>
<tr><td>Margin SD</td><td>Sigma used to turn a margin into a win probability</td>
<td class="num">{D.MODEL["sigma_points"]:.2f}</td>
<td>Declared before kickoff. For comparison, the 14 Week 10 finals had an absolute-margin SD of
{S["wk10_margin_sd"]:.2f} (n=14, one week).</td></tr>
<tr><td>1. Side</td><td><code>{esc(D.MODEL["side_rule"])}</code></td><td>{badge("DERIVED", "d")}</td>
<td>{cell_html(src_std)}</td></tr>
<tr><td>2. Total (estimator A)</td><td><code>{esc(D.MODEL["total_rule"])}</code></td>
<td>{badge("DERIVED", "d")}</td><td>{cell_html(src_std)}</td></tr>
<tr><td>2. Total (estimator B)</td><td>League combined average plus half the combined net-points
differential - a shrunk alternative, published beside A until one wins</td>
<td>{badge("DERIVED", "d")}</td><td>{cell_html(src_std)}</td></tr>
<tr><td>3. Moneyline</td><td><code>{esc(D.MODEL["moneyline_rule"])}</code></td>
<td>{badge("DERIVED", "d")}</td><td>Derived from the side model only</td></tr>
<tr><td>Personnel variant</td><td>{D.MODEL["personnel_points_per_out"]:+.2f} points of spread per
player listed Out in the last official report</td><td>{badge("DECLARED", "d")}</td>
<td>A declared constant, not a fitted penalty - see the ablation note below</td></tr>
</tbody></table></div>
<h2>Fair line, market line, difference</h2>
<p class="note">Three separate columns as required. The market columns are empty because the league
publishes no odds: nfl.com/odds returns a 404, verified {D.AS_OF}. A difference cannot be computed
against a number that does not exist, so the difference columns are empty too - they are not zero.</p>
"""
    body += table("origination_2026_wk11.csv",
                  ["game", "date_et", "time_et", "home", "away", "fair_side_home",
                   "fair_side_personnel", "personnel_delta", "fair_total_points_model",
                   "fair_total_league_anchored", "total_gap", "p_home_win", "fair_price_home",
                   "fair_price_away", "market_side", "diff_side", "source_inputs"],
                  ["Game", "Date", "Time (ET)", "Home", "Away", "Fair side (base)",
                   "Fair side (personnel)", "Personnel delta", "Total A", "Total B", "Total gap",
                   "P(home win)", "Fair price home", "Fair price away", "Market side",
                   "Difference", "Inputs"],
                  numeric={5, 6, 7, 8, 9, 10, 11})
    body += """
<h3>Two model inputs are one game short</h3>
<div class="warnbox"><p>Washington and the Giants each play in Week 11, and each has only nine games
in the official standings because the league has not credited their Thursday 12 November game to
either club. Their points-per-game and points-allowed-per-game on this page are therefore computed
over nine games rather than ten, so the Cincinnati-at-Washington and Jacksonville-at-Giants rows
below carry a slightly noisier rate than the other eleven. The value is still the published value;
it is not adjusted, because adjusting it would mean inventing the league's own correction. Flagged as
F-16 and shown club by club on the <a href="standings.html">standings</a> page.</p></div>
<h3>Why the market and difference columns stay blank</h3>
<p>Every market cell on this page renders as <span class="unverif">UNVERIFIED - no official
source</span>. That is a deliberate state, not a formatting artefact. Publishing a market number
taken from a bookmaker while the rest of the site is sourced only from the league would break the one
rule that makes this desk useful: you can always tell which numbers are official.</p>
<h3>The personnel ablation, not a penalty</h3>
<p>The personnel variant applies a declared constant per Out designation. It is not a fitted penalty
and it is not presented as a truth. It exists so that, once Week 11 results are in, the same model can
be run with and without the personnel feature on a chronological holdout and the difference reported
with an interval. The feature is drawn from the Week 10 report because no Week 11 designations have
been published, which makes it stale by construction - that is precisely why the deliverable is the
comparison, not the level.</p>
"""
    write("origination.html", "Originated lines - Week 11", body)

    # ================================================== prices
    body = f"""
<p class="lede">The price-snapshot store is defined and empty. The brief requires the price-data
policy to be decided before any backtest is published, so the policy is published here first and the
store opens only when a source class is approved.</p>
<div class="warnbox"><p><b>Policy PDP-1, committed {D.AS_OF}.</b> No backtest, no ROI figure, no CLV
figure and no staking score may be published on this site until a price source class has been
approved in writing on the suggestions page. Until then the leaderboard is a signal board and every
market column renders as <span class="unverif">UNVERIFIED - no official source</span>.</p></div>
<h2>Why the store is empty, verified rather than asserted</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Check</th><th>Result</th><th>Evidence</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Does the league publish odds?</td><td>{badge("NO", "b")}</td>
<td>nfl.com/odds returns "404 - Flag on the Play."</td><td>{cell_html(src_odds)}</td></tr>
<tr><td>Does a Week 11 game centre carry a price?</td><td>{badge("NO", "b")}</td>
<td>Game info panels publish location, stadium and network only; no price field exists</td>
<td>{cell_html(src_wk11)}</td></tr>
<tr><td>Does this repository hold any price anywhere?</td><td>{badge("NO", "b")}</td>
<td>Searched across every module in the repository; price columns are blank or flagged</td>
<td>{cell_html("https://github.com/karagemop466-tech/X3")}</td></tr>
</tbody></table></div>
<h2>Store schema, defined and ready</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Field</th><th>Meaning</th><th>Status</th></tr></thead>
<tbody>
<tr><td>market_id</td><td>Season, week, game, market type (side / total / moneyline)</td>
<td>{badge("DEFINED", "d")}</td></tr>
<tr><td>open_price, open_captured_at</td><td>The first number recorded for that market, with the
clock time of the read</td><td>{badge("0 rows", "b")}</td></tr>
<tr><td>close_price, close_captured_at</td><td>The last number before kickoff, appended - never
overwritten</td><td>{badge("0 rows", "b")}</td></tr>
<tr><td>raw_hash</td><td>Hash of the raw capture so a later dispute can be settled from the bytes</td>
<td>{badge("0 rows", "b")}</td></tr>
<tr><td>source_class</td><td>Licensed feed, operator snapshot, or manual record - recorded per row</td>
<td>{badge("AWAITING DECISION", "u")}</td></tr>
<tr><td>fair_price, residual</td><td>Our number and fair minus market, computed only when both exist</td>
<td>{badge("BLOCKED", "b")}</td></tr>
</tbody></table></div>
<h2>The ruling that matters</h2>
<p>Opening and closing numbers are defined <i>before</i> they are measured: the open is the first
reading taken after the market appears; the close is the last reading before kickoff. Both are
appended with their timestamps. If that definition is not fixed in advance, closing-line value can be
computed retroactively to favour whatever a strategy happens to have done, which is the exact failure
the leaderboard design exists to prevent.</p>
"""
    write("prices.html", "Price snapshot store and price policy", body)

    # ================================================== strategy
    strat = [
        ("S-01", "Singles", "Official-points rating, side only",
         "Base rating model, home margin vs a zero benchmark",
         "n >= 200 graded bets and a Brier skill lower bound above zero after multiplicity",
         "Brier skill turns negative for two consecutive rounds, or the sample never reaches 200"),
        ("S-02", "Singles", "Official-points rating, total only",
         "Total estimator A against a constant league total",
         "MAE below the constant benchmark on a chronological holdout with n >= 200",
         "MAE worse than the constant for two consecutive rounds"),
        ("S-03", "Singles", "Moneyline from the side model",
         "Win probability from the margin distribution, no independent pricing",
         "Calibration slope within 0.85-1.15 on n >= 200 with a reliability diagram published",
         "Calibration slope outside 0.75-1.25 at any checkpoint"),
        ("S-04", "Singles", "Turnover-differential overlay",
         "Rating plus official turnover differential",
         "Beats S-01 on the same games by a margin whose 95% interval excludes zero",
         "Fails to beat S-01 on two consecutive rounds"),
        ("S-05", "Singles", "Personnel (Out count) overlay",
         "Rating plus the declared per-Out constant",
         "Beats S-01 on a chronological holdout with an interval that excludes zero",
         "Fails to beat S-01, or the feature is stale for two consecutive rounds"),
        ("S-06", "Game parlays", "Two-leg correlated side + total",
         "Joint probability from a validated copula, not a product of marginals",
         "Joint probability validated on n >= 300 games and operator void rules recorded",
         "No validated joint probability, or the operator's void rules are unavailable"),
        ("S-07", "Same-game parlays", "Same-game side + player prop",
         "Joint probability from within-game dependence measured on official play data",
         "Dependence estimated on n >= 300 games with a published interval",
         "Dependence cannot be estimated from an official source"),
        ("S-08", "Prop combos", "Multi-player prop combination",
         "Joint probability from a validated model of player-correlation",
         "Joint probability validated out of sample, n >= 300",
         "No official player-prop settlement data available"),
    ]
    rows = "".join(
        f'<tr><td><b>{esc(s[0])}</b></td><td>{esc(s[1])}</td><td>{esc(s[2])}</td><td>{esc(s[3])}</td>'
        f'<td>{esc(s[4])}</td><td>{esc(s[5])}</td><td>{badge("PAPER", "d")}</td>'
        f'<td>{badge("not computed - no settled bets", "u")}</td>'
        f'<td>{cell_html("https://github.com/karagemop466-tech/X3/blob/main/COORDINATION.md")}</td></tr>'
        for s in strat
    )
    body = f"""
<p class="lede">Eight strategies are registered and frozen. None has been scored, because scoring
requires settled bets and prices, and neither exists. Registration is the deliverable here: a
strategy's definition is committed before it sees the data it will be graded on, which is the only
way a later result means anything.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>ID</th><th>Division</th><th>Name</th><th>Definition</th>
<th>What would promote it (frozen now)</th><th>What would demote it (frozen now)</th>
<th>State</th><th>Result</th><th>Registration</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>The two-sided field, and why it is frozen first</h2>
<p>Every strategy carries both an upgrade trigger and a downgrade trigger, written before any result
is known. A one-sided rule - "we will promote it if it wins" - can never be falsified, and a
leaderboard that cannot be falsified is a marketing page. The numbers in the promotion column are
project thresholds set by this desk, not figures published by the NFL.</p>
<h2>Pre-registration: what counts</h2>
<ol>
<li>The rule text, the sample window and the gates are committed to git before the evaluation window
opens. The commit hash is the registration.</li>
<li>A number graded on games that predate the commit is retrospective and must be labelled
IN-SAMPLE. It cannot promote a strategy.</li>
<li>Backtest numbers never appear on the leaderboard. The leaderboard shows prospective results only,
so a strategy that was curve-fitted to history cannot buy its way to the top.</li>
</ol>
<h2>Combos and parlays: the joint-evidence gate</h2>
<div class="warnbox"><p>Multiplying marginal probabilities is invalid under dependence, and two legs
in the same game are dependent by construction. A combo may be ranked only when a <b>directly
validated joint probability</b> exists and the operator's void and push rules are recorded. Neither
exists today, so no combo is ranked, and none will be until both do.</p></div>
"""
    write("strategy.html", "Strategies and signals", body)

    # ================================================== leaderboard
    lb = [
        ("Singles", "S-01 to S-05", "0", "Benchmark-relative Brier skill, game-cluster lower bound, multiplicity adjustment", "2 controls required: random picks and favourites only"),
        ("Game parlays", "S-06", "0", "Same proper score, plus the joint-evidence gate", "Never ranked on win rate or short-run ROI"),
        ("Same-game parlays", "S-07", "0", "Same proper score, plus the joint-evidence gate", "Dependence must be measured, not assumed"),
        ("Prop combos", "S-08", "0", "Same proper score, plus the joint-evidence gate", "Operator void and push rules must be recorded"),
    ]
    rows = "".join(
        f'<tr><td><b>{esc(r[0])}</b></td><td>{esc(r[1])}</td><td class="num">{esc(r[2])}</td>'
        f'<td>{esc(r[3])}</td><td>{esc(r[4])}</td><td>{badge("EMPTY BY DESIGN", "d")}</td></tr>'
        for r in lb
    )
    body = f"""
<p class="lede">The leaderboard is empty, and that is the honest state. It publishes a scoring design
that luck cannot flatter, and it will populate only when strategies clear the gates on prospective
results.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Division</th><th>Strategies</th><th>Eligible</th><th>Scoring rule</th>
<th>Control requirement</th><th>State</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>Signal and staking are two columns, never one</h2>
<p>A good signal with reckless staking produces a big number for a while, and a bad signal with a
lucky staking run produces the same thing. The leaderboard therefore scores them separately: the
signal column is a proper score on the probability itself, and the staking column is reported beside
it and never mixed in. A strategy with a negative signal score is not eligible however much money its
staking plan made.</p>
<h2>Proper scores with uncertainty</h2>
<ul>
<li><b>Brier skill, benchmark-relative.</b> Skill is measured against a stated benchmark, not against
zero, so a strategy is not credited for rediscovering that home teams exist.</li>
<li><b>Game-cluster lower bound.</b> Bets inside one game are not independent. The interval is
clustered by game, which widens it correctly.</li>
<li><b>Multiplicity adjustment.</b> Eight strategies were tried, so the bar for the best of eight is
higher than the bar for one pre-registered strategy.</li>
<li><b>Two control baselines on every run.</b> Random picks and favourites-only are published beside
every eligible strategy. If a strategy cannot beat a coin, it is not skill.</li>
<li><b>No ROI column at all.</b> Ranking by season-long ROI is explicitly rejected: it cannot
separate skill from variance at these sample sizes, and it rewards the largest stake.</li>
</ul>
<h2>The two-stage qualification</h2>
<ol>
<li><b>Stage 1 - proper-score qualification.</b> A strategy must show a positive skill score whose
lower bound clears zero after clustering and multiplicity.</li>
<li><b>Stage 2 - prospective CLV and ROI escrow.</b> Only then does it enter a prospective sample
where CLV and ROI are measured forward in time. Stage 2 is blocked today: it needs prices.</li>
</ol>
<h2>Rewards</h2>
<p>No reward amount is published. A funded leaderboard is a contest and in some jurisdictions a
regulated one, and nothing in this repository establishes a prize. Reward amounts stay notional until
that question is answered on the <a href="suggestions.html">suggestions</a> page.</p>
"""
    write("leaderboard.html", "Leaderboard", body)

    # ================================================== gates
    rows = "".join(
        f'<tr><td><b>{esc(g[0])}</b></td><td>{esc(g[1])}</td><td>{esc(g[2])}</td>'
        f'<td><code>{esc(g[3])}</code></td><td>{esc(g[4])}</td></tr>'
        for g in D.GATES
    )
    demote = [
        ("D-1", "Signal decay", "Skill score lower bound falls below zero over the trailing window"),
        ("D-2", "Calibration break", "Calibration slope leaves 0.75-1.25"),
        ("D-3", "Data break", "An input the strategy depends on stops being published or drifts"),
        ("D-4", "Staking without prices", "The strategy is live while its staking input is missing"),
    ]
    drows = "".join(
        f'<tr><td><b>{esc(d[0])}</b></td><td>{esc(d[1])}</td><td>{esc(d[2])}</td>'
        f'<td>{badge("COMMITTED", "v")}</td>'
        f'<td>{cell_html("https://github.com/karagemop466-tech/X3/blob/main/COORDINATION.md")}</td></tr>'
        for d in demote
    )
    body = f"""
<p class="lede">The gates that decide whether a number may be published at all. A gate is a rule
about inputs, not about results: if the input does not exist, the number does not get printed,
however convenient it would be.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Gate</th><th>Name</th><th>Rule</th><th>Blocks</th><th>Current reading</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>The demotion gate</h2>
<p>A live strategy returns to paper if any one of four clauses fires. Clause D-4 fires today for
every strategy, which is why the leaderboard is empty and why it should be.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Clause</th><th>Name</th><th>Fires when</th><th>State</th><th>Registration</th></tr></thead>
<tbody>{drows}</tbody></table></div>
<h2>Ablation, not penalty</h2>
<p>The brief rejects subtracting a fixed number of points for a missing starter. The correct test is
to run the identical model with and without the verified availability feature on chronological
holdouts and report the difference with an interval. That is what the base and personnel variants on
the <a href="origination.html">origination</a> page exist to do once Week 11 results are published.
Until then the difference column is a declared specification, not a finding.</p>
<h2>Train, validation, holdout</h2>
<p>Not started. One season of 2026 cannot satisfy a three-season gate, and splitting a single season
into three pieces is not the same thing as out-of-sample across seasons. Requirement R-47 stays open
until prior seasons are archived (R-45).</p>
"""
    write("gates.html", "Validation gates", body)

    # ================================================== correlation
    body = f"""
<p class="lede">Ten coefficients, each computed only from numbers published on an official page, each
printed with its n and its 95% interval. Nothing here is estimated from a model output, and no
correlation is computed between a modelled quantity and an observed one.</p>
<div class="callout"><p>n is 32 for anything derived from the standings (every club) and 26 for
anything derived from the game-centre team stats (only the clubs playing in Week 11). An interval
that contains zero means the data cannot distinguish the relationship from noise at this sample
size - it does not mean there is no relationship.</p></div>
"""
    body += table("correlations_2026.csv",
                  ["quantity_a", "quantity_b", "n", "pearson_r", "ci95_low", "ci95_high", "source"],
                  ["Quantity A", "Quantity B", "n", "Pearson r", "95% low", "95% high", "Source"],
                  numeric={2, 3, 4, 5})
    body += """
<h2>How to read these</h2>
<ul>
<li>Net points per game against win percentage is the strongest relationship here, which is close to
circular: wins are made of points. It is published because it sets the ceiling every other
correlation should be judged against.</li>
<li>The home-versus-road win percentage correlation is the portability check. If form were portable,
a club's home record would predict its road record; the interval shows how weak that link is.</li>
<li>Turnover differential is the classic "lucky" quantity: it correlates with winning but is far less
stable year to year than net points. This desk will not use it as a feature until its stability is
measured across seasons (R-65, not started).</li>
</ul>
<h2>What is deliberately not correlated</h2>
<p>No coefficient on this page mixes an official number with a modelled one, and no coefficient is
computed on fewer than 26 observations. Relationships that need injury, depth or price data are left
uncomputed until those datasets exist as dated captures rather than single reads.</p>
"""
    write("correlation.html", "Correlation", body)

    # ================================================== luck
    body = f"""
<p class="lede">How much of a 2026 record is not skill. Pythagorean expectation turns points for and
against into an expected win percentage; the gap between that and the actual record is the part of the
record that points alone do not explain.</p>
{cards([(f'{S["luck_sd"]:.2f}', "wins of luck (1 SD)", "across 32 clubs, exponent 2.37"),
        (f'{S["luck_r"]:.3f}', "r, expected vs actual win %", f'r&#178; = {S["luck_r2"]:.3f}, n=32'),
        ("2.29", "wins, a two-SD swing", "the record can move this far with no change in quality"),
        (f'{S["league_ppg"]:.2f}', "league points per club-game", "official standings, 300 club-games")])}
<h2>The panel</h2>
<p>Expected win percentage uses the standard football exponent of
{D.MODEL["pythagorean_exponent"]}, applied to the official points for and against of every club. The
residual is actual wins minus expected wins. Across 32 clubs the residual has a standard deviation of
<b>{S["luck_sd"]:.2f} wins</b>, so about two thirds of clubs sit within
{S["luck_sd"]:.2f} wins of their points-based expectation and roughly one in twenty sits more than
{2 * S['luck_sd']:.2f} wins away. A club that is two wins better than its points "should" be has
usually been lucky in close games, not better.</p>
<p>The fit between expected and actual win percentage is r = {S["luck_r"]:.3f}
(r&#178; = {S["luck_r2"]:.3f}, n = 32), which means roughly
{100 * (1 - S['luck_r2']):.0f}% of the variation in win percentage is not explained by points scored
and allowed at all.</p>
"""
    body += table("luck_panel_2026.csv",
                  ["team", "name", "games", "pf", "pa", "net_ppg", "actual_win_pct",
                   "pyth_winpct", "expected_wins", "actual_wins", "residual_wins", "source"],
                  ["Team", "Club", "G", "PF", "PA", "Net PPG", "Actual win %", "Expected win %",
                   "Expected wins", "Actual wins", "Residual (wins)", "Source"],
                  numeric={2, 3, 4, 5, 6, 7, 8, 9, 10})
    body += """
<h2>What this does and does not license</h2>
<ul>
<li><b>It licenses</b> refusing to promote a strategy because its record looked good. A two-win swing
is inside the noise band of a ten-game sample.</li>
<li><b>It does not license</b> adjusting a team rating by its residual. The residual is not a
measurable skill; treating it as one is the oldest way to turn noise into a bet.</li>
<li>One season of one metric is one sample. The exponent is a convention, not a law, and the
residual SD should be re-measured on prior seasons before it is used as a gate (R-45, R-53).</li>
</ul>
"""
    write("luck.html", "Removal of luck", body)

    # ================================================== depth
    body = f"""
<p class="lede">The deficiency view the brief asks for - which second, third or fourth string player
is replacing a starter - is the single largest gap on this site, and this page says so plainly rather
than approximating it.</p>
<div class="warnbox"><p><b>Blocked, and not approximated.</b> A deficiency claim needs a verified
depth rank for both sides of a matchup. This session verified venues, results, standings, team stats
and injury rows from official pages. It did not verify a single depth rank, because the two candidate
routes are both unresolved: club depth charts carry no as-of date, and no official snap-count page
was read end to end this session. Publishing a "second-string cornerback" label from a jersey number,
a roster order or a guess would be exactly the fabrication the brief forbids.</p></div>
<h2>What would unblock it, in order</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Step</th><th>Route</th><th>Test that must pass</th><th>Status</th><th>Source to check</th></tr></thead>
<tbody>
<tr><td>1</td><td>Per-club official depth chart pages</td>
<td>Every one of the 32 charts carries a readable as-of date and a source URL</td>
<td>{badge("NOT VERIFIED", "u")}</td>
<td>{cell_html("https://www.nfl.com/teams/detroit-lions/depth-chart")} and the other 31 clubs</td></tr>
<tr><td>2</td><td>Official snap counts as the starter proxy</td>
<td>An official snap-count source exists and can be read for all 32 clubs</td>
<td>{badge("NOT VERIFIED", "u")}</td>
<td>{cell_html("https://www.nfl.com/stats/")}</td></tr>
<tr><td>3</td><td>Official game books for inactives and starters</td>
<td>Game book captured per club per week, with inactives and snap percentages</td>
<td>{badge("NOT STARTED", "p")}</td>
<td>{cell_html(src_wk11)}</td></tr>
<tr><td>4</td><td>Shared and empty slots modelled as groups</td>
<td>A slot with two players ranked first and a slot with no player are both representable</td>
<td>{badge("NOT STARTED", "p")}</td>
<td>{cell_html(src_inj)}</td></tr>
<tr><td>5</td><td>Depth rows flagged against the transactions log</td>
<td>Every depth row dated and diffed against the last official roster event</td>
<td>{badge("PARTIAL", "u")}</td><td>{cell_html(src_news)}</td></tr>
</tbody></table></div>
<h2>What is available today, honestly stated</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Personnel question</th><th>Answer available now</th><th>Basis</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Which players are officially unavailable?</td>
<td>{badge("YES", "v")} - 66 Out, 10 Doubtful, 84 Questionable in Week 10</td>
<td>Week 10 report rows</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>Which players are on injured reserve?</td>
<td>{badge("PARTIAL", "u")} - dated items for 16 clubs only</td>
<td>Official news roundups</td><td>{cell_html(src_news)}</td></tr>
<tr><td>Who replaces an unavailable starter?</td>
<td><span class="unverif">UNVERIFIED - no official source names a replacement per slot</span></td>
<td>No depth rank verified</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>How deep is the replacement (2nd, 3rd, 4th string)?</td>
<td><span class="unverif">UNVERIFIED - no official source read</span></td>
<td>No depth rank verified</td><td>{cell_html(src_inj)}</td></tr>
<tr><td>What share of snaps did the replacement play?</td>
<td><span class="unverif">UNVERIFIED - no official snap source read this session</span></td>
<td>Not captured</td><td>{cell_html("https://www.nfl.com/stats/")}</td></tr>
<tr><td>Did the replacement actually start?</td>
<td><span class="unverif">UNVERIFIED - no game book captured this session</span></td>
<td>Not captured</td><td>{cell_html(src_wk11)}</td></tr>
</tbody></table></div>
<h2>The two known parsing traps, recorded so nobody repeats them</h2>
<ul>
<li><b>Texans.</b> Earlier sessions found Houston's depth published as an image. An image cannot be
transcribed into a verified field; it needs an authorised structured source, not a human reading it.</li>
<li><b>Packers.</b> Green Bay's chart prepends jersey numbers to player names. Stripping the number
and keeping the raw string recovers the row; deriving depth order <i>from</i> the number is explicitly
rejected (R-62).</li>
</ul>
"""
    write("depth.html", "Depth and deficiency", body)

    # ================================================== readiness (full)
    body = f"""
<p class="lede">The same decision-readiness register as the landing page, on its own page so it can be
read and filtered without scrolling past the headline numbers.</p>
"""
    body += table("requirements.csv",
                  ["id", "requirement", "status", "blocking_gate", "number_that_clears_it"],
                  ["ID", "Requirement", "Status", "Gate that blocks it",
                   "Number that would clear it"], numeric=())
    write("readiness.html", "Decision readiness", body)

    # ================================================== questions
    Q = [
        ("Q-01", "Prices", "What does the market actually price this game at?",
         "Nothing. nfl.com/odds is a 404 and no price exists anywhere in this repository.",
         "Approve a source class, then capture an open and a close per market with timestamps.",
         src_odds),
        ("Q-02", "Prices", "Can we measure closing-line value at all?",
         "No. CLV needs a close, and no close exists.",
         "The price store schema is defined and ready; it opens on approval.", src_odds),
        ("Q-03", "Results", "How many 2026 games are confirmed from an official page?",
         f"{S['wk10_games']} transcribed here; {S['games_implied']} games are implied by the standings.",
         "Re-read weeks 1 to 9 from the official schedule pages and reconcile to the standings.",
         src_wk10),
        ("Q-04", "Injury", "How many Week 10 injury rows carry a designation?",
         "160 of 345 in the committed capture (66 Out, 10 Doubtful, 84 Questionable).",
         "Already answered from the official page; the brief's '6 of 254' is wrong.", src_inj),
        ("Q-05", "Injury", "Do Week 11 designations exist yet?",
         "No. Every Week 11 game centre says the injury report is not available at this time.",
         "Re-read from Wednesday; capture Wednesday, Thursday and Friday as a series.", src_wk11),
        ("Q-06", "Injury", "What does 'Questionable' mean in practice?",
         "Unknown. The league publishes no play-rate figure and no percentage.",
         "Join several seasons of designations to official inactives and measure play rate with CIs.",
         src_inj),
        ("Q-07", "Depth", "Who replaces an unavailable starter?",
         "No official source read this session names a replacement per slot.",
         "Verify a depth-order route for all 32 clubs first (chart or snap counts).", src_inj),
        ("Q-08", "Depth", "How deep is the replacement - second, third or fourth string?",
         "No depth rank verified, so no depth number is published.",
         "Same as Q-07; then model slots as groups, not as a single starter.", src_inj),
        ("Q-09", "Depth", "Do official snap counts exist as a starter proxy?",
         "Not verified this session.",
         "Read the official stats pages end to end and confirm coverage for all 32 clubs.",
         "https://www.nfl.com/stats/"),
        ("Q-10", "Availability", "Is a player missing from the injury report healthy?",
         "Not necessarily - he may be on injured reserve. Malik Willis is absent because Miami put him on IR on 2026-11-11.",
         "Capture the reserve and IR lists so 'not listed' never means 'available'.", src_news),
        ("Q-11", "Sample", "Can one season satisfy the gates?",
         "No. The gates ask for three seasons and a walk-forward across them; 2026 is one season.",
         "Archive prior seasons of results and weekly injury reports (R-45, R-47).", src_std),
        ("Q-12", "Model", "Is the Week 11 forecast any good?",
         "Unknown and untestable yet - it was committed before kickoff and no result exists.",
         "Grade it against the official Week 11 box scores after they are published.",
         src_wk11),
        ("Q-13", "Legal", "Can a funded leaderboard be run?",
         "Unanswered. A prize-bearing contest is regulated activity in some jurisdictions.",
         "Get a jurisdiction ruling before any reward is real.",
         "https://github.com/karagemop466-tech/X3"),
        ("Q-14", "Legal", "May raw row-level league data be republished?",
         "Unanswered - the terms were not read this session.",
         "Read the terms, then decide what stays private (R-67).",
         "https://www.nfl.com/"),
        ("Q-15", "Ops", "Are captures durable and monitored?",
         "No. Captures live in the static site and there is no freshness alert.",
         "Move captures outside the site, keep hashes, alert on schema change (R-66).",
         "https://github.com/karagemop466-tech/X3"),
        ("Q-16", "Rules", "Did the 2026 kickoff and onside-kick rules change?",
         "Not verified this session.",
         "Fetch the official rulebook page and record the rule text with its date.",
         "https://operations.nfl.com/the-rules/"),
        ("Q-17", "Weather", "What is the roof status and wind for each venue?",
         "Not captured.",
         "Join an NWS grid to the official 90-minute roof designation (R-37).",
         "https://www.weather.gov/"),
        ("Q-18", "Standings", "Why is the Thursday Week 10 game missing from the standings?",
         "Unknown. The league publishes no explanation; both official pages were read today and they disagree by exactly that one game.",
         "Re-read the standings before each capture and record whether the game has been credited; do not reconcile on games played until it has.", src_std),
        ("Q-19", "Fixture", "When was the 2026 schedule announced?",
         "Not verified this session - the announcement page was not read.",
         "Fetch the dated announcement and publish it beside the live schedule page (R-24).",
         "https://www.nfl.com/schedules/"),
    ]
    rows = "".join(
        f'<tr><td><b>{esc(q[0])}</b></td><td>{esc(q[1])}</td><td>{esc(q[2])}</td>'
        f'<td>{esc(q[3])}</td><td>{esc(q[4])}</td><td>{cell_html(q[5])}</td></tr>'
        for q in Q
    )
    body = f"""
<p class="lede">A clear list of what we know, what we do not know, and exactly what would answer each
open question. Every answer below is either transcribed from an official page or stated as not known
- none is inferred.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>ID</th><th>Area</th><th>Question</th><th>What we know today</th>
<th>What would answer it</th><th>Source</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>The three questions that gate everything</h2>
<ol>
<li><b>Q-01 - a price source.</b> Until this is answered, no CLV, no ROI, no staking column and no
fair-versus-market difference can be published by this desk, ever. Everything else is work that can
be done in parallel; this one cannot be routed around.</li>
<li><b>Q-07 - a depth-order source.</b> Until one route is verified for all 32 clubs, the deficiency
matrix stays blocked. It is tempting to approximate; the brief forbids it, correctly.</li>
<li><b>Q-11 - prior seasons.</b> One season cannot satisfy a three-season gate. Either the archive is
built or the gates are formally relaxed in writing, and relaxing a gate to fit available data is the
decision this desk will not make on its own.</li>
</ol>
"""
    write("questions.html", "Questions, information and gaps", body)

    # ================================================== suggestions
    SG = [
        ("SG-01", "Approve a price source class",
         "Licensed feed, or one recorded snapshot per market per week with an open and a close",
         "Unblocks R-01, R-04, R-18, R-38, R-39 - the whole market layer",
         "Cost and licensing terms; a snapshot is cheap and enough for CLV", "HIGH"),
        ("SG-02", "Automate the injury capture: Wednesday, Thursday, Friday",
         "A scheduled job that stores each read with its clock time and a hash",
         "Turns a level into a series, which is the only way the injury signal becomes a surprise",
         "Needs a scheduler and durable storage outside the static site", "HIGH"),
        ("SG-03", "Resolve the depth-order source before building any deficiency feature",
         "Per-club official charts with an as-of date, else official snap counts",
         "Unblocks R-06, R-11, R-50, R-57 and the rest of the depth register",
         "Charts may be undated or images; snap counts may not cover all clubs", "HIGH"),
        ("SG-04", "Archive the 2026 results feed weeks 1 to 9",
         "Re-read each week from the official schedule page and reconcile to the standings",
         "Turns 14 verified finals into a 150-game corpus that a backtest can stand on",
         "Mechanical work, no decisions required", "HIGH"),
        ("SG-05", "Read the league's terms before storing raw rows",
         "A written decision on what may be republished and what stays private",
         "Unblocks R-67 and settles the public/private split",
         "Needs a human to read the terms - this desk will not guess at them", "MEDIUM"),
        ("SG-06", "Move captures out of the static site and add a drift alarm",
         "Durable store with hashes, plus a parser that fails the build on a missing field",
         "Unblocks R-42, R-66; stops a silent schema change from becoming a published blank",
         "Infrastructure work", "MEDIUM"),
        ("SG-07", "Archive prior seasons of weekly injury reports",
         "2018 to 2025 weekly reports and results",
         "Unblocks R-45, R-47, R-53, R-65 - everything that needs a multi-season sample",
         "Volume and availability of archived reports", "MEDIUM"),
        ("SG-08", "Add the stadium roof, surface and hourly weather overlay",
         "NWS grid joined to the official 90-minute roof designation",
         "Unblocks R-37; affects totals and passing props",
         "Two more feeds to keep fresh", "LOW"),
        ("SG-09", "Consolidate the thirteen overlapping site trees",
         "Pick one maintained tree, label the rest archive, and stop adding more",
         "Removes contradictory numbers for the same fact across the site",
         "Needs an owner decision; this desk will not delete other sessions' work", "MEDIUM"),
        ("SG-10", "Rule on rewards and on the contest question",
         "A jurisdiction ruling before any prize is real",
         "Unblocks the reward column",
         "Legal question, not a data question", "LOW"),
        ("SG-11", "Publish a weekly what-changed diff instead of a static snapshot",
         "Store consecutive weekly snapshots and render rank, rating and availability changes",
         "Unblocks R-40 and makes movement visible instead of inferred",
         "Needs two snapshots to exist first", "MEDIUM"),
        ("SG-12", "Capture game books for inactives and snap percentages",
         "One game book per club per week",
         "Unblocks R-25, R-29 and confirms whether a replacement actually started",
         "PDF parsing at volume; needs a drift alarm first", "MEDIUM"),
    ]
    rows = "".join(
        f'<tr><td><b>{esc(s[0])}</b></td><td>{esc(s[1])}</td><td>{esc(s[2])}</td>'
        f'<td>{esc(s[3])}</td><td>{esc(s[4])}</td><td>{badge(s[5], {"HIGH": "b", "MEDIUM": "u", "LOW": "p"}.get(s[5], "d"))}</td>'
        f'<td>{badge("PROPOSED - NOT IMPLEMENTED", "d")}</td></tr>'
        for s in SG
    )
    body = f"""
<p class="lede">Twelve proposals, none implemented. This page is a review queue: the point is to
choose a path before spending effort, not to discover the path by building it.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>ID</th><th>Proposal</th><th>What it means</th><th>What it unblocks</th>
<th>Risk or cost</th><th>Priority</th><th>State</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>How to use this page</h2>
<ol>
<li>Read the priority column first. HIGH means other work cannot finish without it.</li>
<li>Approve or reject each row. Rejecting is a valid outcome and cheaper than building the wrong
thing.</li>
<li>Only after a row is approved does it become a task with an owner and a file scope on the shared
board. Nothing on this page has been started.</li>
</ol>
<h2>What this desk will not do without a decision</h2>
<ul>
<li>It will not invent a price to fill the market column.</li>
<li>It will not infer a depth rank from a jersey number, a roster order, experience or salary.</li>
<li>It will not relax a validation gate because the available sample is too small to clear it.</li>
<li>It will not publish a reward amount, and it will not republish raw league rows before the terms
are read.</li>
</ul>
"""
    write("suggestions.html", "Suggestions", body)

    # ================================================== repo review
    trees = []
    for d in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(("."))):
        pages = sorted(d.rglob("*.html"))
        if not pages:
            continue
        idx = d / "index.html"
        link = f"../{d.name}/index.html" if idx.exists() else f"../{d.name}/{pages[0].relative_to(d)}"
        trees.append((d.name, len(pages), link))
    trees.sort(key=lambda t: -t[1])
    rows = "".join(
        f'<tr><td><b>{esc(t[0])}/</b></td><td class="num">{t[1]}</td>'
        f'<td><a href="{esc(t[2])}">open module</a></td>'
        f'<td>{badge("ARCHIVE", "p") if t[0] not in ("atlas", "hub") else badge("LIVE", "v")}</td></tr>'
        for t in trees
    )
    body = f"""
<p class="lede">The repository carries {len(trees)} separate site trees built by earlier sessions for
the same brief. Nothing was deleted. This page records what each contains so a reader can tell which
module is maintained and which is history.</p>
<div class="warnbox"><p><b>The main finding.</b> Thirteen overlapping trees publish different numbers
for the same fact. That is not a bug in any one of them; it is what happens when many sessions answer
the same brief independently. Until one tree is chosen as canonical and the rest are labelled
archive, any number quoted "from the site" is ambiguous. Suggestion SG-09 proposes how to resolve it;
this session did not delete or edit another session's pages.</p></div>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Module</th><th>HTML pages</th><th>Entry point</th><th>State</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>Gate status across the repository</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Check</th><th>Result on this branch</th><th>Note</th></tr></thead>
<tbody>
<tr><td>scripts/verify_integration.py</td><td>{badge("PASS", "v")}</td>
<td>All pages parse; all internal links resolve</td></tr>
<tr><td>scripts/audit_all.py</td><td>{badge("FAIL - 64 violations", "b")}</td>
<td>All in decision/ from an earlier session: 52 broken links in a paste-ready block, 11 unsourced
rows, 1 flagged row. This session repairs them - see the flagged page.</td></tr>
<tr><td>atlas/verify (tools/atlas_verify.py)</td><td>{badge("see below", "d")}</td>
<td>The module's own gate, run on every build</td></tr>
</tbody></table></div>
<h2>Irregularities found in the data, not the code</h2>
<ul>
<li><b>Stale standings file.</b> <code>data/hub/standings_2026_thru_wk9.csv</code> was captured on
2026-11-14 and holds the pre-Week-10-Sunday table. It is superseded by the standings page of this
module. Not edited by this session - it belongs to another session's scope.</li>
<li><b>Ravens rows.</b> The committed Week 10 injury capture has 8 Baltimore rows where the live page
has 10, and is missing two designations. Flagged as F-02.</li>
<li><b>Venue naming drift.</b> Two official pages disagree on the name of three stadiums. Flagged as
F-03.</li>
<li><b>Results feed shortfall.</b> 14 of {S["games_implied"]} games transcribed here; earlier modules
claim a larger feed that this session did not re-verify line by line, so no reliance is placed on it.
Flagged as F-05.</li>
</ul>
"""
    write("repo-review.html", "Repository review", body)

    # ================================================== sources
    rows = "".join(
        f'<tr><td><code>{esc(k)}</code></td><td>{esc(v["label"])}</td>'
        f'<td>{cell_html(v["url"])}</td><td>{esc(v["read"])}</td>'
        f'<td>{badge(v["kind"].upper(), "v")}</td><td>{esc(v["note"])}</td></tr>'
        for k, v in D.SOURCES.items()
    )
    gc_rows = "".join(
        f'<tr><td>{esc(a + "@" + h)}</td><td>{cell_html(D.GAME_CENTRE % slug)}</td>'
        f'<td>{esc(loc)}</td><td>{esc(st)}</td></tr>'
        for (_d, _t, _n, a, h, slug, loc, st, _sv) in D.WEEK11_FIXTURES
    )
    body = f"""
<p class="lede">Every official page this session read, with the date it was read and what was taken
from it. A page listed here was fetched and read; a page not listed here was not used, whatever
another module may claim.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Key</th><th>Page</th><th>URL</th><th>Read on</th><th>Kind</th><th>What it supplied</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>Game centres read for the Week 11 slate</h2>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>Game</th><th>Game centre</th><th>Location</th><th>Stadium</th></tr></thead>
<tbody>{gc_rows}</tbody></table></div>
<h2>What is not a source for this module</h2>
<ul>
<li>No bookmaker, odds aggregator or exchange page is used anywhere on this site.</li>
<li>No depth chart is used, because none was verified with an as-of date this session.</li>
<li>No page that another session merely cited was relied on; each value here was read again today or
is published as unverified.</li>
</ul>
"""
    write("sources.html", "Sources", body)

    # ================================================== flagged
    F = [
        ("F-01", "Market prices do not exist",
         "No fair-versus-market column, no CLV, no ROI and no staking score can be published.",
         "nfl.com/odds returns '404 - Flag on the Play'; no price exists anywhere in the repository.",
         "Approve a price source class (SG-01). Until then the cells are blank, not zero.",
         src_odds),
        ("F-02", "Ravens injury rows differ from the committed capture",
         "The capture has 8 Baltimore rows where the live page has 10; two designations are also missing (Hawkins Out, Randall Questionable).",
         "Live count on 2026-11-17 versus the capture file committed on 2026-11-14.",
         "Re-capture the report and diff it; keep both versions so the drift stays visible.",
         src_inj),
        ("F-03", "Two official pages name three stadiums differently",
         "Houston: game centre says Reliant Stadium, schedule page says NRG Stadium. Washington: Northwest Stadium versus FedEx Field. Kansas City: Arrowhead Stadium versus GEHA Field at Arrowhead Stadium.",
         "Both strings transcribed from official NFL pages on 2026-11-17.",
         "Pick the game-centre field as authoritative and keep the schedule string as a drift signal.", src_wk11),
        ("F-04", "Only one injury capture exists",
         "The injury signal must be a surprise, which needs two dated reads. With one read it can only ever be a level.",
         "This session produced one capture; the previous capture is another session's and is not directly comparable.", "Implement the Wednesday-Thursday-Friday capture (SG-02).", src_inj),
        ("F-05", "Results feed covers 14 of 150 games in this module",
         "A backtest on 14 games is not a backtest, and this module will not publish one.",
         f"Official standings imply {S['games_implied']} games; {S['wk10_games']} were transcribed here.",
         "Transcribe weeks 1 to 9 (SG-04).", src_wk10),
        ("F-06", "No depth rank verified",
         "Every depth, replacement and deficiency field is blank. They are not estimated.",
         "No club depth chart with an as-of date and no official snap-count page was read end to end this session.", "Resolve the depth-order source first (SG-03).", src_inj),
        ("F-07", "Week 11 designations do not exist yet",
         "Any Week 11 personnel feature is stale by construction.",
         "Every Week 11 game centre reports the injury report as unavailable on 2026-11-17.",
         "Re-read from Wednesday; the personnel ablation is specified and will run then.", src_wk11),
        ("F-08", "The brief's injury figures are wrong",
         "The brief says 254 rows and 6 designations. The official page shows 345 rows in the capture and 160 designations.",
         "Counted from the capture file and re-counted live across all eight pages of the report.",
         "Use the counted figures; do not plan against the brief's numbers.", src_inj),
        ("F-09", "Repo-wide audit gate is failing on main",
         "scripts/audit_all.py reports 64 violations, all in decision/ from an earlier session whose branch is gone.",
         "Measured on this branch at the base commit before any change.",
         "This session repairs the minimum needed to make the shared gate green.",
         "https://github.com/karagemop466-tech/X3"),
        ("F-10", "Thirteen overlapping site trees",
         "Different numbers for the same fact across modules; any quote from the site is ambiguous.",
         "Directory listing of the repository; 13 trees with HTML pages.",
         "Choose a canonical tree and label the rest archive (SG-09).",
         "https://github.com/karagemop466-tech/X3"),
        ("F-11", "Terms of use not read",
         "Raw row-level league data is not reproduced here, and the public/private split is not settled.", "The terms page was not read this session.", "Read the terms and decide (SG-05).",
         "https://www.nfl.com/"),
        ("F-12", "One season only",
         "Gates that ask for three seasons cannot be satisfied, and no gate has been relaxed to fit.",
         "Only 2026 data was read.", "Archive prior seasons (SG-07) or relax the gates in writing.",
         src_std),
        ("F-13", "Week 10 margin SD from 14 games only",
         f"The absolute-margin SD rests on one round; the declared model sigma is a constant.",
         "Computed from the 14 Week 10 finals.",
         "Re-measure on the full season once the results feed is complete.", src_wk10),
        ("F-14", "Earlier modules' claims were not re-verified",
         "Where another module publishes a number this session did not re-read, that number is not relied on here.",
         "Scope rule: this session verifies what it publishes.",
         "Re-verify module by module, or label those trees archive.", src_std),
        ("F-15", "No automated capture yet",
         "Every read on this site was taken by hand by an agent session, which is durable only because it is committed.",
         "No scheduled job exists in this repository for the injury report.",
         "Implement the scheduled capture with hashes (SG-02, SG-06).", src_inj),
        ("F-16", "The official standings page is missing the Thursday Week 10 game",
         "Washington beat the Giants 24-21 on Thursday 12 November. Three days later the league's own standings page still shows both clubs at their pre-game records, with unchanged points for, points against, streak and last-5. Every other Week 10 game is credited.",
         "The live page on 2026-11-17 matches the capture of 2026-11-14 row for row for these two clubs, while all 26 other clubs that played moved.",
         "Do not reconcile a results feed to the standings on games played until the league corrects it; re-read before each capture.", src_std),
    ]
    rows = "".join(
        f'<tr><td><b>{esc(f[0])}</b></td><td>{esc(f[1])}</td><td>{esc(f[2])}</td>'
        f'<td>{esc(f[3])}</td><td>{esc(f[4])}</td><td>{cell_html(f[5])}</td></tr>'
        for f in F
    )
    body = f"""
<p class="lede">Every irregularity and every unverified item found by this session, each with the
official page it came from. Nothing here blocks the site going live - these are the things to review,
not defects to fix before reading.</p>
<div class="tblwrap"><table class="k-data">
<thead><tr><th>ID</th><th>Irregularity</th><th>Why it matters</th><th>Evidence</th>
<th>Proposed resolution</th><th>Source</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>Cells deliberately left blank across this module</h2>
<ul>
<li>Every market price, market line and fair-versus-market difference - no official source (F-01).</li>
<li>Every depth rank, replacement name and replacement depth - no verified source (F-06).</li>
<li>Every Week 11 injury designation - the league has not published them (F-07).</li>
<li>Every strategy result, ROI, CLV and reward amount - nothing has been settled or priced.</li>
<li>Weeks 1 to 9 of the results feed - not re-read from an official page this session (F-05).</li>
</ul>
"""
    write("flagged.html", "Flagged for review", body)

    return S


if __name__ == "__main__":
    s = build()
    pages = sorted(SITE.glob("*.html"))
    print(f"atlas: {len(pages)} pages written to {SITE}")
    for k, v in s.items():
        print(f"  {k:24s} {v}")
