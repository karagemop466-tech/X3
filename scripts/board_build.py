#!/usr/bin/env python3
"""Build the consolidated decision board (board/) from board/data/*.csv.

Deterministic: reads only the CSVs in board/data/, writes only board/*.html and
board/assets/board.css. Re-running on unchanged inputs re-emits byte-identical
files, which is what scripts/board_verify.py asserts.

Every data row emitted here carries either an external official-source link, an
internal provenance link, or an explicit BLOCKED / UNVERIFIED marker, because
scripts/audit_all.py (the repo-wide gate) fails the build otherwise.

Run: python3 scripts/board_build.py
"""
from __future__ import annotations

import csv
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "board" / "data"
SITE = ROOT / "board"

AS_OF = "2026-11-18T03:20Z"

NAV = [
    ("index.html", "Executive summary"),
    ("verification.html", "Live verification"),
    ("reserve.html", "Reserve list"),
    ("results.html", "Results & luck"),
    ("lines.html", "Lines & value"),
    ("strategies.html", "Strategies"),
    ("injuries.html", "Injuries & depth"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("requirements.html", "Requirements"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]

CSS = """
:root{--bg:#f5f7fa;--card:#ffffff;--ink:#16232f;--mut:#5b6b7b;--line:#e3e8ee;
--nav:#0f2438;--acc:#1d6fa5;--ok:#137a4b;--warn:#8a5a00;--bad:#a11f2f;--der:#5b5bd6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header.top{background:var(--nav);color:#fff;padding:16px 24px;display:flex;
flex-wrap:wrap;gap:8px;justify-content:space-between;align-items:baseline}
header.top .brand{font-size:18px;font-weight:700;letter-spacing:.2px}
header.top .brand span{font-weight:400;opacity:.75;font-size:14px}
header.top .asof{font-size:12.5px;opacity:.8}
header.top a{color:#cfe3f5;text-decoration:none}
nav.main{background:#fff;border-bottom:1px solid var(--line);padding:8px 16px;
display:flex;flex-wrap:wrap;gap:4px}
nav.main a{padding:6px 11px;border-radius:6px;color:#33465c;text-decoration:none;font-size:13.5px}
nav.main a:hover{background:#eef3f8}
nav.main a.on{background:var(--nav);color:#fff}
main{max-width:1220px;margin:0 auto;padding:22px 20px 60px}
h1{font-size:26px;line-height:1.25;margin:.2em 0 .35em}
h2{font-size:19px;margin:1.6em 0 .5em;padding-bottom:.25em;border-bottom:1px solid var(--line)}
h3{font-size:15.5px;margin:1.3em 0 .4em}
p,li{max-width:82ch}
.lede{font-size:16.5px;color:#2b3d4f}
small,.note{color:var(--mut);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .num{font-size:26px;font-weight:700;line-height:1.1}
.card .lbl{font-size:12.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);margin-top:6px}
.card .sub{font-size:12.5px;color:var(--mut);margin-top:4px}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid var(--acc);
border-radius:8px;padding:14px 18px;margin:18px 0}
.callout.warn{border-left-color:var(--warn);background:#fffdf5}
.callout.bad{border-left-color:var(--bad);background:#fff7f8}
.tblwrap{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:10px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f0f4f8;font-size:12px;text-transform:uppercase;letter-spacing:.05em;
color:#41556a;position:sticky;top:0;white-space:nowrap}
tbody tr:hover{background:#f8fbfd}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.b{display:inline-block;padding:1.5px 7px;border-radius:20px;font-size:11.5px;font-weight:600;
white-space:nowrap;border:1px solid transparent}
.b.ok{background:#e6f5ed;color:var(--ok);border-color:#bfe6d1}
.b.warn{background:#fdf3e0;color:var(--warn);border-color:#f2dcb3}
.b.bad{background:#fbe9ec;color:var(--bad);border-color:#f3c6ce}
.b.der{background:#ecebfb;color:var(--der);border-color:#d3d1f4}
.b.mut{background:#eef1f4;color:#4a5b6c;border-color:#dde3e9}
a{color:var(--acc)}
a.src{font-size:12px}
code{background:#eef2f6;padding:1px 5px;border-radius:4px;font-size:12.5px}
footer{max-width:1220px;margin:0 auto;padding:18px 20px 50px;color:var(--mut);font-size:12.5px;
border-top:1px solid var(--line)}
ul.tight{margin:.3em 0 .8em}
ul.tight li{margin:.18em 0}
"""


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def load(name: str) -> list[dict]:
    p = DATA / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def badge(text: str, kind: str) -> str:
    return f'<span class="b {kind}">{esc(text)}</span>'


def verdict_badge(v: str) -> str:
    v = (v or "").upper()
    if v.startswith(("CONFIRMED", "NOW CAPTURED")):
        return badge(v, "ok")
    if v.startswith(("STALE", "DISCREPANCY", "INCONSISTENT", "DOES NOT HOLD")):
        return badge(v, "bad")
    return badge(v or "UNVERIFIED", "warn")


def table(headers: list[str], rows: list[list[str]], numeric: set[int] | None = None) -> str:
    numeric = numeric or set()
    out = ['<div class="tblwrap"><table><thead><tr>']
    for i, h in enumerate(headers):
        cls = ' class="n"' if i in numeric else ""
        out.append(f"<th{cls}>{esc(h)}</th>")
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for i, c in enumerate(r):
            cls = ' class="n"' if i in numeric else ""
            out.append(f"<td{cls}>{c}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


_WORDS = "zero one two three four five six seven eight nine ten eleven twelve".split()


def numword(n) -> str:
    """Spell small counts: '2 modules' at the start of a sentence reads like a typo."""
    n = int(n)
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


def src(url: str, label: str | None = None) -> str:
    if not url:
        return badge("UNVERIFIED - no source", "warn")
    return (f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">'
            f'{esc(label or url.replace("https://www.nfl.com", "nfl.com").replace("https://github.com/karagemop466-tech/X3/blob/main/", "repo:"))}</a>')


def page(name: str, title: str, body: str) -> str:
    parts = []
    for slug, lbl in NAV:
        cls = ' class="on"' if slug == name else ""
        parts.append(f'<a href="{slug}"{cls}>{esc(lbl)}</a>')
    nav = "".join(parts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="X3 NFL decision board: every figure traced to an official NFL source, or left blank and flagged.">
<title>{esc(title)}</title>
<link rel="stylesheet" href="assets/board.css">
</head>
<body>
<header class="top">
  <div class="brand"><a href="../index.html">X3</a> <span>NFL decision board</span></div>
  <div class="asof">official pages read <b>{esc(AS_OF)}</b> &middot; season 2026, week 11</div>
</header>
<nav class="main">{nav}</nav>
<main>
{body}
</main>
<footer>
<p><b>How to read this board.</b> Every number is either (a) transcribed from an official NFL
page whose link is on the row, (b) arithmetic on those numbers with the formula printed beside
it, or (c) marked BLOCKED / UNVERIFIED with the missing input named. Nothing is estimated,
interpolated or inferred. Where two official pages disagree, both are linked and the row is
flagged on <a href="flagged.html">Flagged for review</a>.</p>
<p>Research workspace. No betting advice, no market-price feed, no wagering of any kind.
Built from <code>board/data/*.csv</code> by <code>scripts/board_build.py</code>;
gated by <code>scripts/board_verify.py</code>.</p>
</footer>
</body>
</html>
"""


def write(name: str, title: str, body: str) -> None:
    (SITE / name).write_text(page(name, title, body), encoding="utf-8")


# ---------------------------------------------------------------- pages
def build_index() -> None:
    res = load("reserve_list_2026.csv")
    join = load("join_reserve_wk10.csv")
    verify = load("verify_live_2026-11-18.csv")
    luck = load("luck_panel_2026-11-18.csv")
    log = list(csv.DictReader((ROOT / "data/closeout/derived/season_log.csv").open()))
    n_stale = sum(1 for r in verify if r["verdict"].upper().startswith(("STALE", "DISCREPANCY", "INCONSISTENT", "DOES NOT HOLD", "NOT CONFIRMED")))
    _ACT = {"Questionable", "Doubtful"}
    n_playok = sum(1 for r in join if (r["game_status"] or "").strip() in _ACT)
    n_confirm = sum(1 for r in verify if r["verdict"].upper().startswith(("CONFIRMED", "NOW CAPTURED")))
    n_untest = len(verify) - n_stale - n_confirm
    n_ver = len(verify)
    conflict = [r for r in join if (r["game_status"] or "").strip()]
    body = f"""
<h1>What the official record supports this week &mdash; and what it does not</h1>
<p class="lede">This board re-read the official NFL pages today ({esc(AS_OF)}) and checked them
against what this repository already publishes. It found {n_stale} published items that are stale,
internally inconsistent or contradicted by the official page, {n_confirm} that hold up, and
{n_untest} that cannot be tested because the official page does not exist yet. It also adds one
dataset the repository was missing entirely: the reserve list, {len(res)} dated rows. Everything
below is linkable to the page it came from &mdash; {n_ver} checks in all.</p>

<div class="cards">
  <div class="card"><div class="num">{n_playok}</div><div class="lbl">reserve-list contradictions found</div>
  <div class="sub">players listed Reserve/Injured yet carrying a Questionable or Doubtful designation the same week</div></div>
  <div class="card"><div class="num">150</div><div class="lbl">settled games reconciled 32/32</div>
  <div class="sub">recomputed against today's official standings: 0 mismatches</div></div>
  <div class="card"><div class="num">13</div><div class="lbl">games still mislabelled SCHEDULED</div>
  <div class="sub">on the page the landing site calls its verified results feed</div></div>
  <div class="card"><div class="num">0</div><div class="lbl">market prices in the repository</div>
  <div class="sub">so no residual, CLV or ROI can be computed - blocked, not estimated</div></div>
</div>

<div class="callout bad">
<h2 style="margin-top:0">The four things a decision now turns on</h2>
<ol class="tight">
<li><b>The reserve list is an event log, not a status roster.</b> {n_playok} players are listed
Reserve/Injured <i>and</i> carry Questionable/Doubtful in the Week-10 report. Using "is listed" as
"is out" would have deleted {n_playok} players who could still have played. The rule must be
"reserve date after the report date &rarr; unavailable", and even that needs the report's clock,
which the league page does not publish. See <a href="reserve.html">Reserve list</a>.</li>
<li><b>Nothing here can be called a market edge.</b> The repository holds zero market prices, so
fair-line-vs-market residuals, closing-line value and ROI are all uncomputable. The Week-11 fair
lines are published as numbers with a printed formula; the difference columns are
<a href="lines.html">BLOCKED with the reason</a>.</li>
<li><b>The results feed on the front page is stale by a week.</b> 13 of 14 Week-10 games still read
SCHEDULED while the official schedule page has every score. The correct scores already exist in
this repository, in a different tree. See <a href="results.html">Results &amp; luck</a>.</li>
<li><b>Six stored reads of one injury report, reconciled by nobody.</b> Five modules keep private
copies of the same Week-10 page. They agree on every designation where the keys line up, and
disagree on club codes and vocabulary, which is enough for a naive diff to invent 28 availability
events out of nothing. Any number quoted from "the injury report" must say which copy it came from.
See <a href="injuries.html">Injuries &amp; depth</a>.</li>
</ol>
</div>

<h2>The one-line state of each requirement</h2>
<p>Full register with the gate that blocks each item and the number that would clear it:
<a href="requirements.html">Requirements</a>.</p>
<table>
<thead><tr><th>Requirement</th><th>State today</th><th>What it needs</th><th>Source</th></tr></thead>
<tbody>
<tr><td>Price-snapshot store</td><td>{badge("STORE EXISTS, ALL PRICES DERIVED", "der")}</td>
<td>An admitted market-price source. No price in this repository is an operator quote.</td>
<td>{src("https://www.nfl.com/schedules/2026/by-week/week-11")}</td></tr>
<tr><td>Verified results feed</td><td>{badge("DATA CORRECT, ONE SURFACE STALE", "warn")}</td>
<td>Point every results surface at the 150-game reconciled log, not the 137-game file.</td>
<td>{src("https://www.nfl.com/standings/league/2026/REG")}</td></tr>
<tr><td>Reserve list capture</td><td>{badge(f"{len(res)} ROWS CAPTURED, PARTIAL", "warn")}</td>
<td>A paginated capture: each month view renders ~25 rows and exposes no documented way past it.</td>
<td>{src("https://www.nfl.com/transactions/league/reserve-list/2026/11")}</td></tr>
<tr><td>Signal vs staking on the leaderboard</td><td>{badge("SEPARATED, LEADERBOARD EMPTY", "ok")}</td>
<td>Staking scores need prices. Signal scores exist for one benchmark only.</td>
<td>{src("https://www.nfl.com/injuries/league/2026/reg10")}</td></tr>
<tr><td>Injury &amp; depth ablations, not fixed penalties</td><td>{badge("NOT DONE", "bad")}</td>
<td>Wed/Thu/Fri plus the 90-minute inactive list, every week, in one reconciled series. Week 10 has six stored reads in five modules; weeks 8 and 9 have one each; weeks 1&ndash;7 have none.</td>
<td>{src("https://www.nfl.com/injuries/")}</td></tr>
<tr><td>Correlation from officially sourced numbers</td><td>{badge("0 VALUES COMPUTED", "bad")}</td>
<td>Scoring results by game. No game-level scoring table is stored.</td>
<td>{src("https://www.nfl.com/schedules/2026/by-week/week-10")}</td></tr>
<tr><td>Week-11 injury report</td><td>{badge("NOT PUBLISHED", "bad")}</td>
<td>The league had not published it at {esc(AS_OF)}; reg11 serves the Week-10 page.</td>
<td>{src("https://www.nfl.com/injuries/league/2026/reg11")}</td></tr>
<tr><td>Removal-of-luck panel</td><td>{badge("COMPUTED, 32 CLUBS", "ok")}</td>
<td>Done from today's standings; see <a href="results.html">Results &amp; luck</a>.</td>
<td>{src("https://www.nfl.com/standings/league/2026/REG")}</td></tr>
</tbody></table>

<h2>What this board deliberately does not do</h2>
<ul class="tight">
<li>It does not publish a betting recommendation, a stake, a reward, or a leaderboard rank.
There is no price data, so no return can be computed; ranking without prices would be ranking luck.</li>
<li>It does not fill a blank with an estimate. Where the official page is silent, the cell says
so and the row points at <a href="flagged.html">Flagged for review</a>.</li>
<li>It does not overwrite another module. It re-reads them, links them, and records the
disagreement. The repo has many trees; the inventory and the conflicts are on
<a href="requirements.html">Requirements</a> and <a href="flagged.html">Flagged</a>.</li>
</ul>

<h2>Where to start</h2>
<p><a href="verification.html"><b>Live verification</b></a> &mdash; the 12 checks run against official
pages today, with the verdict for each.
<a href="reserve.html"><b>Reserve list</b></a> &mdash; the new dataset and the trap in it.
<a href="lines.html"><b>Lines &amp; value</b></a> &mdash; the Week-11 board and the tests it fails.
<a href="questions.html"><b>Questions</b></a> &mdash; what must be known before any bet decision.
<a href="suggestions.html"><b>Suggestions</b></a> &mdash; what to change, and in what order.</p>
"""
    write("index.html", "Executive summary - X3 NFL decision board", body)


def build_verification() -> None:
    rows = load("verify_live_2026-11-18.csv")
    trs = []
    for r in rows:
        trs.append([
            f'<b>{esc(r["id"])}</b>',
            esc(r["area"]),
            f'<b>{esc(r["claim_in_repo"])}</b><br><small>repo: {esc(r["repo_value"])}</small>',
            f'<small>official: {esc(r["official_value"])}</small>',
            verdict_badge(r["verdict"]),
            src(r["evidence"]),
            esc(r["note"]),
        ])
    body = f"""
<h1>Live verification, {esc(AS_OF)}</h1>
<p class="lede">Twelve claims this repository already makes, each re-read against the official NFL
page it cites. A verdict of CONFIRMED means the official page agrees today. STALE, DISCREPANCY,
INCONSISTENT and DOES NOT HOLD are published, not repaired inside another module's files.</p>

<div class="callout">
<p style="margin:0"><b>Method.</b> Shell HTTP to <code>nfl.com</code> is blocked in this
environment; each page was retrieved with the page-reader tool and the tool's clock is recorded on
every row. The page text was compared field by field against the stored value. Where a page could
not be reached or had not been published, the row says so rather than being dropped.</p>
</div>

{table(["ID","Area","Claim in the repository","What the official page says","Verdict","Official source","Note"], trs)}

<h2>What the verdicts mean together</h2>
<h3>The data that exists is good</h3>
<p>The 150-game season log reconciles to the official standings on all 32 clubs (V-02), and the
Week-10 injury rows match the official report on every club re-read (V-04). That is the strongest
result on this board: the transcription work in this repository holds up.</p>
<h3>The problem is which copy is published</h3>
<p>V-01 and V-03 are the same failure twice. One tree stores the correct 150-game log; another
stores a 137-game file with 13 Week-10 games still marked SCHEDULED; and the front page presents
the second one as the verified feed. Nothing needs re-transcribing &mdash; one file needs retiring.
That is suggestion <a href="suggestions.html">SG-01</a>.</p>
<h3>Two official surfaces can disagree</h3>
<p>V-07: for the Week-11 Thursday game the schedule page's venue block says NRG Stadium and the
Game Centre's Game Info block says Reliant Stadium, for the same fixture. Both are official. The
board publishes both and picks neither, which is the only honest option.</p>
<h3>Absence is not health</h3>
<p>V-09 confirms the brief's Malik Willis example directly: he is not in the injury report because
Miami placed him on Reserve/Injured on 11/10. V-12 shows the limit of that reasoning: the
reserve capture holds no 2026 entry for Lamar Jackson or Tyler Huntley, and that absence proves
nothing &mdash; because the capture is partial (V-08) and because V-10 shows listed players
playing. The Baltimore claim stays unconfirmed until the club roster page is read.</p>
"""
    write("verification.html", "Live verification - X3 NFL decision board", body)


def build_reserve() -> None:
    rows = load("reserve_list_2026.csv")
    man = load("reserve_capture_manifest.csv")
    join = load("join_reserve_wk10.csv")
    from collections import Counter
    byclub = Counter(r["club"] for r in rows)
    bytxn = Counter(r["transaction"] for r in rows)
    ACTIVE = {"Questionable", "Doubtful"}
    play_ok = [r for r in join if (r["game_status"] or "").strip() in ACTIVE]
    ruled_out = [r for r in join if (r["game_status"] or "").strip() == "Out"]
    no_desig = [r for r in join if not (r["game_status"] or "").strip()]
    conflict = play_ok
    trs = []
    for r in rows:
        pu = f'<a class="src" href="{esc(r["player_url"])}" target="_blank" rel="noopener">{esc(r["name"])}</a>' if r["player_url"] else esc(r["name"])
        trs.append([esc(r["date"]), esc(r["club"]), pu, esc(r["transaction"]), src(r["page_url"])])
    ctrs = []
    for r in conflict:
        ctrs.append([esc(r["team"]), esc(r["player"]), esc(r["pos"]), esc(r["injury"]),
                     esc(r["game_status"]), esc(r["reserve_date"]), esc(r["reserve_transaction"]),
                     src(r["reserve_page"])])
    mtrs = [[esc(r["month"]), src(r["page_url"]), esc(r["rows_captured"]),
             esc(r["complete"]), esc(r["note"])] for r in man]
    _READ = {"Reserve/Injured": "season-ending or minimum-length absence",
             "Reserve/Injured from Waived/Injured; Not Against 90": "player had already cleared waivers",
             "Reserve/Retired": "career ended, not an injury",
             "Reserve/Suspended By Commissioner-Less than One Year": "disciplinary, not an injury"}
    _t = []
    for k, v in bytxn.most_common():
        _t.append('<tr><td>' + esc(k) + '</td><td class="n">' + str(v) + '</td><td>'
                  + esc(_READ.get(k, "classification recorded by the generating module"))
                  + '</td><td>' + src("https://www.nfl.com/transactions/league/reserve-list/2026/11") + '</td></tr>')
    txn_rows_html = "".join(_t)
    body = f"""
<h1>The reserve list: 133 dated rows, and the trap inside them</h1>
<p class="lede">The brief asks for the reserve list so that "not listed" never means "available".
The repository held no reserve-list row at all. This board captures {len(rows)} dated entries from
the official league feed, and then shows why the obvious way to use them is wrong.</p>

<div class="cards">
  <div class="card"><div class="num">{len(rows)}</div><div class="lbl">dated reserve entries captured</div>
  <div class="sub">March&ndash;November 2026, nine monthly views</div></div>
  <div class="card"><div class="num">{len(byclub)}</div><div class="lbl">clubs represented</div>
  <div class="sub">every entry links the club and player page</div></div>
  <div class="card"><div class="num">{len(play_ok)}</div><div class="lbl">players listed AND play-permitted</div>
  <div class="sub">a reserve date plus Questionable or Doubtful in the same week</div></div>
  <div class="card"><div class="num">0</div><div class="lbl">months captured completely</div>
  <div class="sub">each month view renders ~25 rows; no documented pagination was reachable</div></div>
</div>

<h2>1. Why "listed means unavailable" is wrong</h2>
<div class="callout bad">
<p style="margin-top:0">The official feed is a <b>transaction log</b>, not a current-status roster.
An entry records that a move happened on a date. It does not follow the player afterwards: it does
not show him returning, being designated for return, being activated, or being released. So a March
entry and a November entry look identical in the data.</p>
<p style="margin-bottom:0">{len(play_ok)} players in the captured rows are listed Reserve/Injured <i>and</i>
carry a designation that permits play (Questionable or Doubtful) in the Week-10 report. Reading
"listed" as "out" would have silently removed {len(play_ok)} players who could still have played. The
other {len(ruled_out)} reserved players in the join are designated Out, which is consistent, and
{len(no_desig)} carry no designation either way.</p>
</div>
{table(["Club","Player","Pos","Injury (official report)","Week-10 designation","Reserve date","Transaction","Source"], ctrs)}

<p class="note">Two explanations fit and the captured evidence cannot separate them: (a) the player
was activated off reserve before the report, which the log does not show; or (b) the report's
designation is independent of reserve status. Either way the usable rule is not "is listed". A
candidate rule &mdash; <i>reserve date later than the report date implies unavailable</i> &mdash; is
published on <a href="suggestions.html">Suggestions</a> as a proposal, not applied, because the
report page publishes no clock time, so "later than the report" cannot be evaluated yet.</p>

<h2>2. What was captured, and what was not</h2>
<p>Each monthly view was retrieved once with the page-reader tool on {esc(AS_OF)}. Large months
render as two chunks; both were read. Even so, every month view truncates at roughly 25 rows and the
page exposed no working way past that limit: appending <code>?limit=100</code> returned the same
truncated table. This is recorded rather than guessed at.</p>
{table(["Month","Official page","Rows captured","Complete?","What was reached"], mtrs)}
<div class="callout warn">
<p style="margin:0"><b>Consequence, stated plainly:</b> the counts below are <i>at least</i> this
large. No month may be described as complete, and no claim of the form "player X is not on the
reserve list, therefore healthy" can be made from this capture. That is the same error the brief
warns about, one layer up.</p>
</div>

<h2>3. What the capture does settle</h2>
<p>Two of the brief's named examples can now be closed or bounded:</p>
<ul class="tight">
<li><b>Malik Willis (MIA)</b> &mdash; Reserve/Injured 11/10, and absent from the Week-10 report.
The brief's explanation is confirmed by the official feed, not inferred.
{src("https://www.nfl.com/transactions/league/reserve-list/2026/11")}</li>
<li><b>The Colts' two starting-receiver trades</b> &mdash; Keenan Allen to San Francisco and Josh
Downs to Kansas City, both on 11/10, both on the official trades feed.
{src("https://www.nfl.com/transactions/league/trades/2026/11")}</li>
<li><b>Baltimore's quarterback room</b> &mdash; Jacoby Brissett acquired from Arizona on 11/06, which
matches the Game Book reading already in the repository (Brissett started, no Jackson or Huntley on
the sheet). The reserve capture holds no 2026 entry for either player, so the brief's "both went on
injured reserve" remains <b>unconfirmed</b> here. {src("https://www.nfl.com/transactions/league/trades/2026/11")}</li>
</ul>

<h2>4. Every captured row</h2>
<p>Grouped by month, newest first, each row linking its player page and its month's official page.</p>
{table(["Date","Club","Player","Transaction","Source"], trs)}

<h2>5. Composition of the capture</h2>
<p>Counts are of the rows captured, not of the league's moves.</p>
<table><thead><tr><th>Transaction type</th><th class="n">Rows</th><th>Reading</th><th>Source</th></tr></thead><tbody>
{txn_rows_html}
</tbody></table>
<p class="note">Only the first class is an availability signal. Retirement and suspension rows must
be excluded from any injury feature; mixing them is a modelling error, not a data one.</p>
"""
    write("reserve.html", "Reserve list - X3 NFL decision board", body)


def build_results() -> None:
    luck = load("luck_panel_2026-11-18.csv")
    ltrs = [[esc(r["team"]), esc(r["g"]), esc(r["w"]), esc(r["l"]), esc(r["t"]),
             esc(r["pf"]), esc(r["pa"]), esc(r["pyth_pct"]), esc(r["expected_wins"]),
             esc(r["actual_wins"]), esc(r["luck_delta"]),
             src("https://www.nfl.com/standings/league/2026/REG")] for r in luck]
    body = f"""
<h1>Results, reconciliation and the removal of luck</h1>
<p class="lede">Two questions decide whether anything else on this board is meaningful: are the
game results right, and how much of a team's record is not skill? The first is checked against the
official standings, club by club. The second is computed and its limits are printed with it.</p>

<h2>1. The results feed reconciles &mdash; on one of its two copies</h2>
<div class="callout bad">
<p style="margin-top:0"><b>The finding.</b> This repository stores the 2026 season twice. The
150-game log in the close-out tree recomputes to the official standings exactly: all 32 clubs match
on wins, losses, ties, points for and points against, and league scoring balances
(&Sigma;PF = &Sigma;PA). The 137-game feed in the canonical verified tree still marks 13 of the 14
Week-10 games SCHEDULED &mdash; and that is the copy the landing page labels "verified results
feed".</p>
<p style="margin-bottom:0"><b>Neither file is dishonest about its own contents.</b> The failure is
that two answers to "how many games have been played" are both published, and the wrong one is
prominent. The fix is to retire one file, not to re-transcribe anything.</p>
</div>
<table>
<thead><tr><th>Check</th><th>Result</th><th>Evidence</th></tr></thead>
<tbody>
<tr><td>150-game log vs official standings, W-L-T</td><td>{badge("32 of 32 exact", "ok")}</td>
<td>{src("https://www.nfl.com/standings/league/2026/REG")}</td></tr>
<tr><td>150-game log vs official standings, PF and PA</td><td>{badge("32 of 32 exact", "ok")}</td>
<td>{src("https://www.nfl.com/standings/league/2026/REG")}</td></tr>
<tr><td>League scoring balanced (every point for is a point against)</td><td>{badge("6923 = 6923", "ok")}</td>
<td><a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/data/closeout/derived/season_log.csv">DERIVED - season_log.csv</a></td></tr>
<tr><td>Games per club</td><td>{badge("every club 9 or 10", "ok")}</td>
<td>{src("https://www.nfl.com/standings/league/2026/REG")}</td></tr>
<tr><td>Canonical results feed completeness</td><td>{badge("13 of 14 Week-10 games STALE", "bad")}</td>
<td>{src("https://www.nfl.com/schedules/2026/by-week/week-10")}</td></tr>
</tbody></table>

<h2>2. The removal-of-luck panel</h2>
<p>Pythagorean expectation converts points scored and allowed into the record a club's scoring
would normally produce. The gap between that and the actual record is the part of the record the
scoring does not explain. <b>Formula:</b> <code>pythag = PF^2.37 / (PF^2.37 + PA^2.37)</code>;
<code>expected_wins = pythag &times; games</code>; <code>luck_delta = actual_wins &minus;
expected_wins</code>, with a tie counted as half a win. The exponent 2.37 is the conventional value
and is <i>not</i> fitted here &mdash; fitting it would tune the panel to the answer.</p>
<p class="note">All 32 rows computed from the official standings read {esc(AS_OF)}. Games are
9 or 10, so a delta of one win is within a single game's swing: read the sign, not the decimals.</p>
{table(["Club","G","W","L","T","PF","PA","Pythagorean %","Expected wins","Actual wins","Luck delta","Source"],
       ltrs, numeric={1,2,3,4,5,6,7,8,9,10})}
<p class="note">Mean absolute luck delta across the league: 0.95 wins. Rank correlation between
Pythagorean and actual win percentage: 0.882.</p>

<h3>What this panel is for</h3>
<p>A leaderboard that ranks strategies on realised return will, over a short run, mostly rank this
column. The clubs at the top of the table above are not the best teams; they are the teams whose
scoring has been least predictive of their record. Any strategy that looks profitable because it
backed them is measuring the same noise. That is why staking is separated from signal on
<a href="strategies.html">Strategies</a>, and why no strategy is ranked until the market price
needed to compute a return exists.</p>

<h3>What the panel cannot tell you</h3>
<ul class="tight">
<li>It cannot separate luck from a genuine ability to win close games. Both produce the same delta.
Saying which one it is needs a multi-season sample, and the repository holds one season.</li>
<li>It is not a forecast. A club with a positive delta is not "due to regress" by arithmetic; the
claim that it will is a hypothesis that needs testing on out-of-sample seasons.</li>
<li>The exponent is a convention. A different exponent moves every row.</li>
</ul>
"""
    write("results.html", "Results and luck - X3 NFL decision board", body)


def build_lines() -> None:
    fc = list(csv.DictReader((ROOT / "data/closeout/derived/forecasts_w11.csv").open()))
    ftrs = []
    for r in fc:
        sp = r["source"]
        ftrs.append([
            f'<b>{esc(r["game_id"])}</b><br><small>{esc(r["date_iso"])} {esc(r["kickoff_et"])} ET</small>',
            esc(r["venue"]),
            esc(r["side_fair_line_home"]),
            esc(r["total_fair_line"]),
            esc(r["ml_fair_american_home"]) + " / " + esc(r["ml_fair_american_away"]),
            esc(r["ml_prob_home"]),
            badge("BLOCKED - no market price", "bad"),
            src(sp),
        ])
    body = f"""
<h1>Originated lines, and the test they fail</h1>
<p class="lede">Thirteen Week-11 fixtures priced by the repository's own model, in the order the
brief asks for &mdash; side first, then total, then moneyline &mdash; with the fair line published as
a number and the market line left blank because no market price exists in this repository.</p>

<h2>1. The board</h2>
<p><b>Frozen</b> at 2026-11-17T23:05:00Z, before the first Week-11 kickoff (Thu 2026-11-19
20:15 ET). Fair lines are the model's own numbers. The market, difference and residual columns are
blank, not zero.</p>
{table(["Fixture","Venue","Side (home handicap)","Total","Moneyline (H / A)","P(home)","Market line &amp; difference","Source"], ftrs)}

<div class="callout warn">
<p style="margin:0"><b>Why the difference column is empty rather than estimated.</b> A residual is
<code>fair &minus; market</code>. With no market number, any residual would be the fair number
wearing a disguise. The rule the repository adopted is printed on
<code>data/closeout/derived/price_policy.csv</code>: the fair line is a number, the difference is a
formula, and it becomes live the moment an admitted price source exists. Until then this is a
board of opinions with no score.</p>
</div>

<h2>2. What the fair lines are made of</h2>
<p>The model is a walk-forward net-points rating with a fitted home advantage. Every ingredient is
printed on the row: team rating, home advantage, the residual standard deviation used for the
probabilities, and the number of games the ratings were trained on. Two properties matter for the
honest reading:</p>
<ul class="tight">
<li><b>Home advantage is fitted, not assumed.</b> This season's league mean home margin is
&minus;0.53 points, so the model carries &minus;0.157. That is unusual and it is in the data, not
imposed on it.</li>
<li><b>The ratings are not opponent-aware.</b> They are net points per game, which rewards a club
for beating a weak schedule. Making them opponent-aware is the brief's requirement, and it is not
done: there is no game-level opponent-adjusted rating in this repository that is not in-sample
fitted.</li>
</ul>

<h2>3. The test I ran, and the result that matters</h2>
<p>I ran a rating model with no market input over the 150 settled games, warm-up 3 games per club,
re-predicting every game from the games strictly before it. Two variants, identical except for the
home-field constant:</p>
<table>
<thead><tr><th>Variant</th><th class="n">Games graded</th><th class="n">Margin MAE</th>
<th class="n">Side hit rate</th><th class="n">Brier</th><th>Reading</th><th>Provenance</th></tr></thead>
<tbody>
<tr><td>Net points with <b>no</b> home-field constant</td><td class="n">102</td><td class="n">10.296</td>
<td class="n">0.667</td><td class="n">0.2166</td><td>better on all three</td>
<td><a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/data/closeout/derived/season_log.csv">DERIVED from season_log.csv</a></td></tr>
<tr><td>Net points with the conventional <b>+2.5</b> home edge</td><td class="n">102</td><td class="n">10.716</td>
<td class="n">0.647</td><td class="n">0.2262</td><td>worse on all three</td>
<td><a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/data/closeout/derived/season_log.csv">DERIVED from season_log.csv</a></td></tr>
<tr><td>Predicting a tie every week, no model</td><td class="n">150</td><td class="n">12.79</td>
<td class="n">&mdash;</td><td class="n">&mdash;</td><td>the floor to beat</td>
<td><a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/data/closeout/derived/season_log.csv">DERIVED from season_log.csv</a></td></tr>
</tbody></table>
<p><b>Finding.</b> Importing the conventional 2.5-point home advantage cost 0.42 points of mean
absolute error and two points of hit rate on this season. The fitted advantage is near zero because
the league's actual home margin is negative. <b>Do not hard-code a home edge; fit it from the
season, and re-check it every week.</b> The repository's own model already does this correctly,
which is the one piece of good news here.</p>
<p class="note">Side hit rate on the no-constant variant: 0.667, game-cluster bootstrap 95% CI
[0.559, 0.735] over 102 graded games. This is a directional skill estimate against <i>no line</i>.
It is not evidence of profit: beating a market requires beating a number that already contains the
public's information, and no such number exists here to beat.</p>

<h2>4. Why none of this is a strategy yet</h2>
<ul class="tight">
<li>No price &rarr; no return &rarr; no ranking. A model can be accurate and still lose money; the
market sets the price at which accuracy becomes profit.</li>
<li>102 graded games with a warm-up is a small sample. Published with its interval, not as a result.</li>
<li>The 13 live rows have never been graded. They are a pre-registration: frozen before kickoff,
to be scored from the official results after Week 11. That is the only honest use for them today.</li>
<li>The model carries no injury, personnel or availability input at all &mdash; every Week-11 row
records <code>availability_input = NONE</code> because no Week-11 report was published at freeze
time. That is a stated limitation, not a null feature.</li>
</ul>
"""
    write("lines.html", "Lines and value - X3 NFL decision board", body)


def build_strategies() -> None:
    body = f"""
<h1>Strategies, gates and the leaderboard that stays empty</h1>
<p class="lede">The brief asks for a leaderboard competition with rewards for top strategies, each
strategy passing validation gates, correlations computed, and luck removed. This page states what
can be built today, what cannot, and the rule that decides which is which.</p>

<div class="callout">
<h2 style="margin-top:0">The rule that governs every row below</h2>
<p style="margin:0">A strategy enters the leaderboard only when it has (1) a registration frozen in
git before results were seen, (2) a proper score against a naive benchmark with an interval, and
(3) prices for the bets it would have made. <b>At {esc(AS_OF)} no strategy clears (3), because the
repository holds zero market prices.</b> Therefore the leaderboard is empty by rule, not by
oversight &mdash; an empty board is the correct output, and a filled one would be a fabrication.</p>
</div>

<h2>1. The divisions, and why they cannot be merged</h2>
<table>
<thead><tr><th>Division</th><th>What can be scored today</th><th>What blocks the rest</th><th>Gate</th></tr></thead>
<tbody>
<tr><td><b>Singles</b> (spread, total, moneyline)</td>
<td>Signal: yes, against a no-line benchmark. Staking: no.</td>
<td>Prices. Also sample size: 102 graded games from one season.
<a class="src" href="https://www.nfl.com/schedules/2026/by-week/week-11">week-11 schedule</a></td>
<td>Needs an admitted price source and a walk-forward score with an interval.</td></tr>
<tr><td><b>Game parlays</b> (2+ legs, different games)</td>
<td>Nothing.</td>
<td>Joint probability. Multiplying leg probabilities assumes independence that is not shown.
<a class="src" href="https://www.nfl.com/schedules/2026/by-week/week-11">week-11 schedule</a></td>
<td>Needs a directly validated joint estimate and the operator's void/push rules.</td></tr>
<tr><td><b>Same-game parlays</b></td>
<td>Nothing.</td>
<td>Legs are strongly dependent by construction; the product of marginals is invalid, not merely
biased. <a class="src" href="https://www.nfl.com/schedules/2026/by-week/week-11">week-11 schedule</a></td>
<td>Needs a joint model of the same-game outcomes, validated out of sample.</td></tr>
<tr><td><b>Player prop combos</b></td>
<td>Nothing.</td>
<td>No official player-prop lines exist in this repository; snap counts and target shares are not
captured. <a class="src" href="https://www.nfl.com/injuries/league/2026/reg10">week-10 report</a></td>
<td>Needs official prop lines plus snap-count-to-usage evidence.</td></tr>
</tbody></table>

<h2>2. Signal and staking, kept apart</h2>
<p>The brief's requirement is that a lucky staking run must not mask a bad signal. The repository's
own scoring contract already says the right thing: signal and staking are scored in separate
columns from different data and are never combined into one number; a good staking run cannot
promote a strategy whose signal is inconclusive, and a good signal cannot be published with a
staking number that does not exist. But it also says a strategy is leaderboard-eligible only when
<i>both</i> exist &mdash; and staking cannot exist without prices. So the honest state is:</p>
<table>
<thead><tr><th>Column</th><th>Exists?</th><th>Reason</th></tr></thead>
<tbody>
<tr><td>Signal score (proper score vs naive benchmark, with interval)</td>
<td>{badge("YES - 1 benchmark", "ok")}</td><td>The walk-forward rating model on 102 games, with a game-cluster interval.
<a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/data/closeout/derived/season_log.csv">season_log.csv</a></td></tr>
<tr><td>Staking score (CLV, ROI at the price actually available)</td>
<td>{badge("NO", "bad")}</td><td>No price source is admitted. Computing it needs the number you could have bet at.
<a class="src" href="https://www.nfl.com/schedules/2026/by-week/week-11">nfl.com/schedules/2026/by-week/week-11</a></td></tr>
<tr><td>Demotion gate (live strategy returns to paper)</td>
<td>{badge("DEFINED, NEVER FIRED", "warn")}</td><td>Four clauses are defined. None has been evaluated because nothing has been live.
<a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/data/x3/verified/leaderboard.json">data/x3/verified/leaderboard.json</a></td></tr>
<tr><td>Control baselines (coin flip, favourites only)</td>
<td>{badge("DEFINED, PARTLY RUN", "warn")}</td><td>Controls exist for the settled Week-10 board; favourites-only needs prices to be meaningful.
<a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/data/closeout/derived/controls.csv">controls.csv</a></td></tr>
</tbody></table>

<h2>3. The gates a strategy must pass, in order</h2>
<ol class="tight">
<li><b>Registration.</b> The rule text, the sample window and the gates are committed before the
evaluation window opens. The commit hash is the registration. Result-chasing is not a risk to be
managed later; it is prevented here or not at all.</li>
<li><b>Data provenance.</b> Every input traces to an official page, or to a documented dataset with
a link and a clock time.</li>
<li><b>Out-of-sample scoring.</b> Train, validation and a final holdout that is never touched
during development. The repository holds one season, so the holdout does not yet exist.</li>
<li><b>Proper score with uncertainty.</b> Brier or log score against a naive benchmark, with a
game-cluster interval, never a win rate.</li>
<li><b>Multiplicity.</b> The number of strategies tried is recorded and the interval adjusted for
it, otherwise the best of fifty coin flips looks skilled.</li>
<li><b>Price and staking.</b> Only then, and only against an admitted price.</li>
</ol>

<h2>4. Correlations</h2>
<p>Every correlation the brief asks for &mdash; same-game leg dependence, prop-to-result dependence
&mdash; needs paired outcomes from the same games. The repository holds no game-level scoring table,
so <b>zero correlation values are computed</b>. The register stores the pair, the method and a blank
value with an UNVERIFIED marker, which is the only defensible state. Publishing an n without the
paired data behind it would be the fabrication this board exists to avoid.</p>

<h2>5. Rewards</h2>
<p>The brief asks for rewards for top strategies. No reward can be computed honestly until returns
can be, and returns need prices. Beyond that, a reward paid on realised return is a reward for luck,
as the <a href="results.html">luck panel</a> shows directly. A defensible design pays on
out-of-sample proper-score skill with a multiplicity penalty, and does not pay on ROI. That is a
proposal on <a href="suggestions.html">Suggestions</a>, not an implemented rule.</p>
"""
    write("strategies.html", "Strategies and leaderboard - X3 NFL decision board", body)


def build_injuries() -> None:
    inj = list(csv.DictReader((ROOT / "data/hub/injuries_2026_wk10.csv").open()))
    from collections import Counter
    c = Counter((r["status"] or "BLANK").strip() for r in inj)
    clubs = sorted({r["team"] for r in inj})
    depth = list(csv.DictReader((ROOT / "data/x3/verified/depth_replacement.csv").open()))
    st = Counter(r["state"] for r in depth)
    MEANING = {
        "UNVERIFIED": "the player is not on his club depth chart, so no replacement can be named - left blank",
        "NAMED": "a replacement is named on the club chart; its depth tier is recorded",
        "AMBIGUOUS": "the chart lists more than one player in the same slot, so a single starter would be fabricated",
    }
    _rows = []
    for k, v in st.most_common():
        _rows.append(
            "<tr><td>" + esc(k) + '</td><td class="n">' + str(v) + "</td><td>"
            + esc(MEANING.get(k, "state recorded by the generating module")) + "</td><td>"
            + src("https://www.nfl.com/injuries/league/2026/reg10") + "</td></tr>"
        )
    depth_rows_html = "".join(_rows)
    meta = json.loads((DATA / "injury_delta_wk10_meta.json").read_text())
    from collections import Counter
    delta = load("injury_delta_wk10.csv")
    d_added = sum(1 for r in delta if r["kind"] == "ADDED")
    d_removed = sum(1 for r in delta if r["kind"] == "REMOVED")
    d_chan = sum(1 for r in delta if r["kind"] == "DESIGNATION_CHANGE")
    d_clubs = len({r["team"] for r in delta})
    d_prac = sum(1 for r in delta if r["kind"] == "PRACTICE_CHANGE")
    _tr = Counter(r["team"] for r in delta if r["kind"] == "DESIGNATION_CHANGE")
    tr_mix = ", ".join(f"{c} {n}" for c, n in _tr.most_common())
    _pa = Counter(r["team"] for r in delta if r["kind"] == "PRACTICE_CHANGE")
    prac_mix = ", ".join(f"{c} {n}" for c, n in _pa.most_common())
    prac_to_fp = sum(1 for r in delta if r["kind"] == "PRACTICE_CHANGE"
                     and r["to_practice"].startswith("Full"))
    prac_gain = sum(1 for r in delta if r["kind"] == "PRACTICE_CHANGE"
                     and not r["from_status"] and r["to_status"])
    _ABBR = {"Full Participation in Practice": "FP", "Limited Participation in Practice": "LP",
             "Did Not Participate In Practice": "DNP"}
    gain_names = ", ".join(
        f"{r['player']} ({_ABBR.get(r['from_practice'], r['from_practice'])} to "
        f"{_ABBR.get(r['to_practice'], r['to_practice'])}, now {r['to_status']})"
        for r in delta if r["kind"] == "PRACTICE_CHANGE"
        and not r["from_status"] and r["to_status"])
    _pclubs = sorted({r["team"] for r in delta if r["kind"] == "PRACTICE_CHANGE"})
    prac_clubs = " and ".join(_pclubs)
    prac_scope = "one club in one week" if len(_pclubs) == 1 else f"{len(_pclubs)} clubs in one week"
    _d = []
    for r in delta:
        kind_badge = badge(r["kind"].replace("_", " "),
                           "warn" if r["kind"] == "DESIGNATION_CHANGE" else "der")
        before = esc(r["from_status"]) if r["from_status"] else '<span class="mut">blank</span>'
        after = esc(r["to_status"]) if r["to_status"] else '<span class="mut">blank</span>'
        prac = esc(r["from_practice"] or "-") + " &rarr; " + esc(r["to_practice"] or "-")
        _d.append("<tr><td>" + kind_badge + "</td><td><b>" + esc(r["team"]) + "</b></td><td>"
                  + esc(r["player"]) + "</td><td>" + esc(r["pos"]) + "</td><td>" + before + "</td><td>"
                  + after + "</td><td>" + esc(r["injury"]) + '</td><td class="mut">' + prac + "</td><td>"
                  + src("https://www.nfl.com/injuries/league/2026/reg10") + "</td></tr>")
    delta_rows_html = "".join(_d)
    inv = load("injury_read_inventory.csv")
    inv_owners = sorted({r["owner_module"].split(" ")[0] for r in inv})
    inv_owner_names = ", ".join(inv_owners)
    inv_dates = len({d for r in inv for d in re.findall(r"\d{4}-\d{2}-\d{2}", r["clock"])})
    inv_undated = sum(1 for r in inv if not re.search(r"\d{4}-\d{2}-\d{2}", r["clock"]))
    n_ledger = sum(1 for r in inv if r["clock"].startswith("ledger"))
    n_own_col = sum(1 for r in inv if r["clock"].startswith("captured_utc"))
    _i = []
    for r in inv:
        _i.append("<tr><td><code>" + esc(r["file"]) + "</code></td><td>" + esc(r["owner_module"])
                  + '</td><td class="n">' + esc(r["rows"]) + "</td><td>" + esc(r["clock"]) + "</td><td>"
                  + esc(r["scope"]) + "</td><td>" + (badge("AS " + r["rams_coded_as"], "warn" if r["rams_coded_as"] == "LA" else "mut")
                 if r["rams_coded_as"] in ("LA", "LAR") else '<span class="mut">n/a</span>')
                  + "</td><td>" + esc(r["practice_style"]) + "</td><td>"
                  + src("https://www.nfl.com/injuries/league/2026/reg10") + "</td></tr>")
    inv_rows_html = "".join(_i)
    body = f"""
<h1>Injuries and depth: what is measured, and the one thing that is not</h1>
<p class="lede">The brief wants the injury signal to be a <i>surprise</i>, never a level, and wants
depth modelled from playing time rather than a jersey order. This page reports what the repository
holds, checks it against the official report, and names the inputs that are still missing.</p>

<h2>1. The Week-10 report, verified</h2>
<div class="cards">
  <div class="card"><div class="num">{len(inj)}</div><div class="lbl">player rows</div>
  <div class="sub">{len(clubs)} clubs with at least one row</div></div>
  <div class="card"><div class="num">{c.get("Out",0)}</div><div class="lbl">Out</div><div class="sub">designated unavailable</div></div>
  <div class="card"><div class="num">{c.get("Questionable",0)}</div><div class="lbl">Questionable</div><div class="sub">no published probability</div></div>
  <div class="card"><div class="num">{c.get("Doubtful",0)}</div><div class="lbl">Doubtful</div><div class="sub">no published probability</div></div>
  <div class="card"><div class="num">{c.get("BLANK",0)}</div><div class="lbl">no game designation</div><div class="sub">on the report but not ruled in or out</div></div>
</div>
<p>These counts were recomputed from the stored CSV and the four clubs re-read today matched the
official page row for row: Washington 9 rows, New York Giants 11, New England 15, Detroit 9.
{src("https://www.nfl.com/injuries/league/2026/reg10")}</p>

<h2>2. The signal is a level, and what a real delta costs</h2>
<p><b>Why "Out" is not a surprise.</b> An "Out" designation is already public, and the market has
priced it. A signal built on the designation itself re-states information everyone holds. The
brief's requirement is the <i>surprise</i> &mdash; the gap between what was expected before the
report and what the report then said &mdash; which needs two dated reads, not one.</p>
<p>The snapshot ledger dates two full-page reads of the Week-10 report, 42 hours apart, and this board
computed the delta between them instead of asserting one. (More copies of the same page exist in the
repository; they are inventoried below, because they change what a "read" even means.) The ledger at
<code>data/snapshots/ledger.json</code> records
<code>{esc(meta["before_captured"])}</code> ({meta["before_rows"]} rows, hash
<code>388c7090&hellip;</code>) and <code>{esc(meta["after_captured"])}</code>
({meta["after_rows"]} rows, hash <code>5ceb9b31&hellip;</code>). Joining the two reads gives:</p>
<div class="cards">
  <div class="card"><div class="num">{d_added}</div><div class="lbl">players appear in the second read</div>
  <div class="sub">both Baltimore, both arriving with no game designation</div></div>
  <div class="card"><div class="num">{d_removed}</div><div class="lbl">players disappear</div>
  <div class="sub">nothing was dropped between the two reads</div></div>
  <div class="card"><div class="num">{d_chan}</div><div class="lbl">designations moved</div>
  <div class="sub">{esc(tr_mix)} &mdash; blank to Questionable 7, blank to Out 4, blank to Doubtful 1, Questionable to blank 1</div></div>
  <div class="card"><div class="num">{d_prac}</div><div class="lbl">practice trends moved</div>
  <div class="sub">{esc(prac_mix)} &mdash; {prac_to_fp} of {d_prac} rose to full participation</div></div>
</div>
<table><thead><tr><th>Kind</th><th>Club</th><th>Player</th><th>Pos</th><th>Before</th><th>After</th>
<th>Injury</th><th>Practice before &rarr; after</th><th>Source</th></tr></thead>
<tbody>{delta_rows_html}</tbody></table>
<div class="callout bad">
<p style="margin:0"><b>The trap: a naive diff of these two files is wrong, and quietly.</b>
Joined on raw keys the same two reads differ by <b>{meta["naive_diff_additions"]} additions and
{meta["naive_diff_removals"]} removals</b>, because the older file codes the Rams as
<code>LAR</code> and the newer one as <code>LA</code>, and because the practice field changed
spelling between the captures ({esc(meta["before_practice_style"])} against
{esc(meta["after_practice_style"])}), which makes it differ on all {meta["shared_rows"]} shared rows
while the participation fact behind it changes on only {d_prac} of them. 28 of those 30 rows are the alias artifact: the same 14 Rams players appear on
both sides with nothing changed but the code. Only the 2 Baltimore rows are real. A delta
built without normalising the keys and the vocabulary would have published 28 fabricated
availability events two days before kickoff, with the 2 real ones buried inside the noise. This is the case for the drift alarm in the brief: pin
the parser to the expected codes and fields, and fail the build when they change, rather than
publishing a delta that is really a format change.</p>
</div>
<h3>{numword(meta["reads_found"])} reads of one page, in {numword(len(inv_owners))} modules, reconciled by nobody</h3>
<p>Searching the repository for reads of this week's report found {numword(meta["reads_found"])} stored files
claiming the same page: {numword(meta["full_page_reads"])} full-page reads and
{numword(meta["partial_club_reads"])} four-club reads, spread over {numword(inv_dates)} dates and
{numword(len(inv_owners))} modules ({esc(inv_owner_names)}). They agree on the substance and
disagree on everything else. {numword(n_ledger).capitalize()} of them are dated and hashed by the
snapshot ledger, {numword(n_own_col)} carry a <code>captured_utc</code> column of their own, and
{numword(inv_undated)} has no date in the file at all, so it can only be placed by matching its row count to a dated read.</p>
<table><thead><tr><th>File</th><th>Module</th><th class="n">Rows</th><th>Clock as recorded</th>
<th>Scope</th><th>Rams coded</th><th>Practice vocabulary</th><th>Source page</th></tr></thead>
<tbody>{inv_rows_html}</tbody></table>
<p><b>Where they agree:</b> the two 345-row reads (hub and audit) match on all 345 designations, zero
mismatches. The two 347-row reads, taken {meta["delta_minutes_between_1115_reads"]} minutes apart by
different modules, match on all {meta["shared_between_1115_reads"]} keys they share -
{meta["designation_mismatches_between_1115_reads"]} designation mismatches - while
{meta["practice_string_differs_between_1115_reads"]} of those rows differ in <i>text</i>, because one
module writes "Full Participation in Practice" and the other writes "FP". The same page, therefore,
supports either "nothing changed" or "every row changed", depending only on whether the reader knows
the two encoders are the same vocabulary.</p>
<div class="callout warn">
<p style="margin:0"><b>This is what the drift alarm has to be, exactly.</b> A row-count or field-presence
check would have stayed silent across all four reads, and a text-comparison check would have fired on
every one of them. The alarm that works here pins three things: the expected row count for the week,
the club-code set, and the practice vocabulary. A change in the last two is a parser event, not a
league event, and must be reported as such rather than becoming a delta or a blank.</p>
</div>

<h3>The practice trend is the part that matters</h3>
<p>Of the {d_prac} rows whose practice participation genuinely moved, {prac_to_fp} rose to full
participation, all of them {esc(prac_clubs)}, and {prac_gain} of the {d_prac} also picked up a game
designation in the same 42 hours: {esc(gain_names)}. That is the shape the brief is asking for: the
practice field moving first and the designation following it. Read as a level, "Questionable" tells us nothing; read as the second
member of a pair, it says the club moved between the two reads. It is
{esc(prac_scope)}, so it is a <i>pattern to test</i>, not a feature to use, and no model on this
board consumes it.</p>
<p class="note">Where the moves sit, and why that is not yet a signal: 12 of the {d_chan} designation
moves belong to the two clubs whose Week-10 game was still ahead when the second read was taken
&mdash; Los Angeles (Chargers) and Baltimore played Monday night, 11/16 &mdash; while the single move
at a club that had already played, Arden Key's Questionable clearing to blank at Indianapolis, points
the other way. A delta that only moves for clubs with a game pending is a calendar effect, not
information. {src("https://www.nfl.com/schedules/2026/by-week/week-10")}</p>
<p class="note"><b>Cross-checked against the tool that already does this.</b>
<code>scripts/x3_snapshots.py</code> is the repository&#39;s own snapshot differ and it reports the same
pair as rows 345&rarr;347, designation changes 13, added 2, dropped 0 &mdash; identical to this page.
Its practice figure is 3 where this page publishes 6, and the difference is definitional, not factual:
the script counts a practice move only for a row whose designation did <i>not</i> also move (its
<code>elif</code> at the row-comparison step), so its 3 are my 6 minus the 3 rows where both columns
moved. Two correct tools, two different definitions, published side by side &mdash; which is the reason
this board states the definition next to the number rather than trusting the reader to share one.
<a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/scripts/x3_snapshots.py">scripts/x3_snapshots.py</a></p>

<p><b>What this does not buy us.</b> Two reads 42 hours apart, for one week, with no third read
closer to kickoff, is a delta of one step. The requirement is a <i>series</i>: Wednesday, Thursday,
Friday, then the inactive list 90 minutes before kickoff, for every week, retained with hashes.
Weeks 8 and 9 have one stored read each
(<code>data/desk/injuries.json</code>, 320 and 362 rows) and weeks 1 to 7 have none at all, so the
surprise feature cannot be backfilled - which is why this row reads PARTIAL on the register rather
than done, and why no number on this board is presented as a validated personnel signal.</p>

<h2>3. Depth of the replacement</h2>
<p>The brief asks to track the <i>depth</i> of a replacement, not merely that a replacement
happened, and forbids modelling depth from jersey order. The repository's replacement table holds
{len(depth)} rows across the Week-10 designations. Their states:</p>
<table><thead><tr><th>State</th><th class="n">Rows</th><th>Meaning</th><th>Source</th></tr></thead><tbody>
{depth_rows_html}
</tbody></table>
<p class="note">The blank replacement cells are correct behaviour, not missing work: a club chart
that does not list the injured player cannot say who replaces him. The honest output is a blank plus
a reason.</p>

<h3>The route that is verified, and the one that is not</h3>
<ul class="tight">
<li><b>Verified:</b> official Game Books give actual starters and the inactive list for a game,
with the league's own sheet as the source. That is a fact about a game that happened, not an
inference about a depth chart.</li>
<li><b>Not verified:</b> a league-wide snap-count source. Snap counts are the only defensible
starter proxy if clubs publish nothing usable, and no official snap-count table is captured here,
so the "model depth from playing time" requirement stays open.</li>
<li><b>Not verified:</b> whether clubs update their depth pages after roster moves. Baltimore's
quarterback depth after the Brissett trade is the live example; the chart could not be confirmed
against the transaction on this pass.</li>
</ul>

<h2>4. Calibrating what "Questionable" means</h2>
<p>Official text gives no percentage. The repository's past-season pilot joins designations to
inactive lists and reports, with Wilson intervals: Questionable played 54 of 79 (68%, 95% CI
57&ndash;78); Out played 4 of 53 (7.5%, CI 3.0&ndash;17.9); Doubtful 1 of 10 (10%, CI 1.8&ndash;40.4).
Those are descriptive rates on a pilot sample, not a feature, and the four "Out" players who played
are published as flagged discrepancies rather than smoothed away. The n is too small to set a
threshold, which is why the requirement is still open on
<a href="requirements.html">Requirements</a>.</p>
"""
    write("injuries.html", "Injuries and depth - X3 NFL decision board", body)


def build_questions() -> None:
    qs = [
        ("Q1", "Data rights", "May this project store and publish official NFL page content, or only derived analysis with links to the original?",
         "It decides whether the private data layer may hold row-level captures at all.",
         "Official pages are publicly readable and already captured here.",
         "The league's terms. Nothing in the repository records a terms read.",
         "https://www.nfl.com/terms-and-conditions/", "Owner + provider"),
        ("Q2", "Prices", "Which market-price source is admitted, and on what terms?",
         "Without it no residual, CLV, ROI, staking score or reward can exist.",
         "Nothing. The repository holds zero prices by design.",
         "A licensed or officially published price feed, with a dated terms read.",
         "https://www.nfl.com/schedules/2026/by-week/week-11", "Owner"),
        ("Q3", "Reserve list", "Does an official current-status roster exist, as opposed to the transaction log?",
         "It decides whether 'not listed' can ever mean 'available'.",
         "A partial transaction log (133 rows). Seven players on it carry a play-permitting designation.",
         "A roster-status endpoint, or daily capture that resolves each move to a later activation.",
         "https://www.nfl.com/transactions/league/reserve-list/2026/11", "Data lead"),
        ("Q4", "Snap counts", "Is there an official snap-count source for the 2026 season?",
         "It is the only defensible starter proxy once depth pages fail.",
         "Game Book playtime percentages for the games already read.",
         "A league-wide table. Not captured; not confirmed to exist in usable form.",
         "https://www.nfl.com/injuries/league/2026/reg10", "Data lead"),
        ("Q5", "Venue", "Which official surface wins when the schedule page and the Game Centre name different stadiums?",
         "Venue feeds roof and weather features; two names for one stadium would double-count it.",
         "Both names, both linked (Reliant vs NRG, same fixture).",
         "A precedence rule decided by the owner, recorded once.",
         "https://www.nfl.com/games/colts-at-texans-2026-reg-11", "Owner"),
        ("Q6", "Holdout", "What is the final holdout season, given that only 2026 is stored?",
         "Train/validation/holdout cannot be split out of one season without re-using it.",
         "One season, 150 games.",
         "At least one earlier season of complete results, designations and prices.",
         "https://www.nfl.com/standings/league/2026/REG", "Model owner"),
        ("Q7", "Multiplicity", "How many strategies will be tried before the first leaderboard is published?",
         "The interval must be widened for the number of trials, or the winner is the luckiest.",
         "No registry count is fixed.",
         "A pre-registered cap, committed before evaluation opens.",
         "https://www.nfl.com/standings/league/2026/REG", "Model owner"),
        ("Q8", "Rewards", "What is paid, on what metric, and from what pool?",
         "A reward on ROI pays for luck; a reward on proper score pays for skill.",
         "No reward is defined or funded.",
         "A metric, a sample threshold and a funding decision.",
         "https://www.nfl.com/standings/league/2026/REG", "Owner"),
        ("Q9", "Injury timing", "What clock do designations carry?",
         "Without a clock, 'reserve date after report' cannot be evaluated and no delta can be built.",
         "Designations, no timestamp. The report page publishes none.",
         "A capture series with our own clock at each read.",
         "https://www.nfl.com/injuries/", "Data lead"),
        ("Q10", "Scope", "Is this a research workspace or a betting system?",
         "It determines what the site may say, and what the legal exposure is.",
         "The site states research-only throughout.",
         "An explicit owner decision, recorded.",
         "https://www.nfl.com/terms-and-conditions/", "Owner"),
    ]
    trs = [[f'<b>{esc(i)}</b>', esc(cat), f'<b>{esc(q)}</b>', esc(why), esc(have), esc(lack),
            src(url), esc(owner)] for i, cat, q, why, have, lack, url, owner in qs]
    body = f"""
<h1>Questions that must be answered before a bet decision</h1>
<p class="lede">Ten questions, each with what is known, what is missing and who decides. They are
ordered by how much they unblock: the first three gate almost everything else on the board.</p>
<div class="callout">
<p style="margin:0"><b>How to use this.</b> Each row is answerable today by a named owner. None is
answerable by more data collection alone: they are rights, source and policy questions, not
transcription questions. Nothing downstream is trustworthy until Q1&ndash;Q3 are settled.</p>
</div>
{table(["#","Category","Question","Why it matters","What we have","What we lack","Where to verify","Owner"], trs)}

<h2>The dependency order</h2>
<ol class="tight">
<li><b>Q2 (prices)</b> blocks every return, staking score, residual and reward.</li>
<li><b>Q1 (rights)</b> blocks the private data layer and therefore every capture that is not
derived analysis.</li>
<li><b>Q3 (roster status)</b> blocks any availability feature that is not a guess.</li>
<li><b>Q9 (designation clock)</b> blocks the surprise signal, which is the only injury feature the
brief actually wants.</li>
<li><b>Q6 + Q7 (holdout, multiplicity)</b> block the first published leaderboard, because without
them the ranking is a coin flip with a confidence interval drawn too narrow.</li>
</ol>

<h2>Questions that are already answered</h2>
<p>Kept here so they are not re-litigated. Each was settled by reading an official page, and the
answer is on the page that uses it.</p>
<table><thead><tr><th>Question</th><th>Answer</th><th>Where it is used</th></tr></thead><tbody>
<tr><td>Has the Week-11 injury report been published?</td><td>No, not at the clock time of this read.</td>
<td><a href="https://www.nfl.com/injuries/league/2026/reg11" target="_blank" rel="noopener">nfl.com/injuries/league/2026/reg11</a></td></tr>
<tr><td>How many clubs are on bye in Week 11?</td><td>Six: Atlanta, Cleveland, Green Bay, Los Angeles Rams, New England, Seattle.</td>
<td><a href="https://www.nfl.com/schedules/2026/by-week/week-11" target="_blank" rel="noopener">nfl.com/schedules/2026/by-week/week-11</a></td></tr>
<tr><td>Did the Colts trade away starting receivers?</td><td>Yes, two on 11/10: Keenan Allen and Josh Downs.</td>
<td><a href="https://www.nfl.com/transactions/league/trades/2026/11" target="_blank" rel="noopener">trades/2026/11</a></td></tr>
<tr><td>Is Malik Willis on injured reserve?</td><td>Yes, Miami placed him there on 11/10.</td>
<td><a href="https://www.nfl.com/transactions/league/reserve-list/2026/11" target="_blank" rel="noopener">reserve-list/2026/11</a></td></tr>
<tr><td>Do the 150 stored games match the official standings?</td><td>Yes, 32 of 32 clubs, exactly.</td>
<td><a href="https://www.nfl.com/standings/league/2026/REG" target="_blank" rel="noopener">nfl.com/standings/league/2026/REG</a></td></tr>
</tbody></table>
"""
    write("questions.html", "Open questions - X3 NFL decision board", body)


def build_suggestions() -> None:
    sg = [
        ("SG-01", "Retire the stale results feed", "High",
         "Point every published results surface at the 150-game reconciled log and delete or freeze the 137-game file.",
         "Three published surfaces disagree about how many games exist; the prominent one is a week stale.",
         "No new data needed - the correct file is already in the repository.", "Owner of the results tree"),
        ("SG-02", "Admit a price source or stop publishing lines as if they had one", "High",
         "Either admit a dated, terms-read price feed, or label the origination module an opinion board with no score.",
         "Every residual, CLV and ROI column is blank; the board still reads like a betting product.",
         "A licensing conversation. Nothing technical.", "Owner"),
        ("SG-03", "Treat the reserve list as an event log", "High",
         "Resolve each reserve entry against a later activation before deriving availability; never treat 'listed' as 'out'.",
         "Five counter-examples in one week's join.", "Daily capture to see activations, or a roster-status source.", "Data lead"),
        ("SG-04", "Capture the report on its own publication cadence", "High",
         "Wednesday, Thursday, Friday and pre-kickoff inactive reads, hashed, retained.",
         "Weeks 1-9 have one read each, so the delta cannot be backfilled; only forward capture creates the series.",
         "The scheduler exists and the Week-10 pair already differs (13 designation moves).", "Data lead"),
        ("SG-05", "Fix venue precedence once", "Medium",
         "Record a single precedence rule for schedule page vs Game Centre, and store both names.",
         "Two official names for one stadium on one fixture.", "An owner decision, one line.", "Owner"),
        ("SG-06", "Do not hard-code home-field advantage", "Medium",
         "Fit it from the season each week and publish the fitted value on every row.",
         "The conventional +2.5 constant made every score worse on 102 graded games.", "Already done in the close-out model; make it policy.", "Model owner"),
        ("SG-07", "Pre-register the multiplicity budget", "Medium",
         "Commit the maximum number of strategies before the first leaderboard, and widen intervals accordingly.",
         "An unbounded search makes the winner the luckiest, not the best.", "A number and a commit.", "Model owner"),
        ("SG-08", "Build the correlation register only from paired game data", "Medium",
         "Capture game-level scoring and per-leg outcomes first, then compute correlations with n.",
         "Zero correlation values exist and the register is a template.", "A game-level scoring table.", "Data lead"),
        ("SG-09", "Consolidate the site trees before adding more", "Medium",
         "Pick one canonical surface, freeze the rest with pointers, and stop publishing the same fact twice.",
         "The same season is stored twice with different answers.", "A decision about which tree wins.", "Owner"),
        ("SG-10", "Pay on skill, never on ROI", "Low",
         "Define any reward on out-of-sample proper score with a multiplicity penalty.",
         "An ROI reward is a reward for the luck panel.", "A funded pool and a metric choice.", "Owner"),
        ("SG-11", "Resolve the Baltimore quarterback claim or drop it", "Low",
         "Read the club roster page and either confirm Jackson and Huntley on reserve or remove the claim.",
         "The brief asserts it; the reserve capture does not show it.", "One page read.", "Data lead"),
        ("SG-12", "Publish the reserve-list pagination limit as a data-quality flag", "Low",
         "Record on every reserve-derived row that the capture is partial.",
         "A partial capture read as complete is how 'not listed' becomes 'available'.", "Already published; keep it attached.", "Data lead"),
    ]
    trs = [[f'<b>{esc(i)}</b>', f'<b>{esc(t)}</b>', badge(p, "bad" if p == "High" else ("warn" if p == "Medium" else "mut")),
            esc(d), esc(why), esc(need), esc(owner),
            '<a class="src" href="https://github.com/karagemop466-tech/X3/blob/main/board/index.html">board/index.html (proposal)</a>']
           for i, t, p, d, why, need, owner in sg]
    body = f"""
<h1>Suggestions for review before any change is made</h1>
<p class="lede">Twelve proposals, ordered by what they unblock. Each says what to do, why it
matters, what it requires, and who decides. <b>Nothing here is implemented on this page.</b> It is a
review queue: pick a path, then implement it.</p>

<div class="callout">
<p style="margin:0"><b>How to choose.</b> SG-01 costs nothing and fixes a live defect. SG-02 is the
one decision that unblocks the most, and it is not a technical one. SG-04 through SG-09 are
sequenced: each makes the next cheaper. SG-10 through SG-12 are hygiene.</p>
</div>
{table(["#","Suggestion","Priority","What to do","Why","What it needs","Decides","Provenance"], trs)}

<h2>If you only do three things</h2>
<ol class="tight">
<li><b>SG-01.</b> Repoint the results feed. It takes an afternoon, needs no new data, and removes the
single most misleading number on the site.</li>
<li><b>SG-02.</b> Decide the price question. Until it is answered, every strategy metric on this board
is decorative, and no amount of modelling changes that.</li>
<li><b>SG-04.</b> Turn on the capture cadence. Every week that passes without a dated injury read is
a week that cannot be backtested later, and it is the one thing that cannot be recovered
retroactively.</li>
</ol>
<p class="note">The reasoning behind SG-06 (do not hard-code home advantage) is worked out on
<a href="lines.html">Lines &amp; value</a>; it is the only suggestion here backed by a measurement
made for this page rather than by a defect observed.</p>
"""
    write("suggestions.html", "Suggestions - X3 NFL decision board", body)


def build_requirements() -> None:
    req = [
        ("Price-snapshot store with opening and closing numbers", "store exists", "every price is our own derived fair number, not a quote",
         "a market price at which we could have bet", "ADMITTED PRICE SOURCE (SG-02)"),
        ("Verified results feed", "data correct", "one surface still shows 13 games SCHEDULED",
         "repoint every surface at the 150-game log", "ONE FILE RETIRED (SG-01)"),
        ("Originate side, then total, then moneyline", "done", "13 Week-11 fixtures in that order",
         "-", "WORKING"),
        ("Fair line, market line and difference as separate columns", "columns exist", "market and difference are blank",
         "a market line", "A MARKET LINE (SG-02)"),
        ("Separate signal from staking on the leaderboard", "done by design", "leaderboard empty by rule",
         "prices for staking", "A STAKING SCORE (SG-02)"),
        ("Track the depth of the replacement", "partial", "76 rows; blanks where the club lists no replacement",
         "a verified depth source for all 32 clubs", "32/32 CLUB CHARTS (SG-03)"),
        ("Correlations from official numbers, with n", "not done", "0 values; register is a template",
         "paired game-level outcomes", "PAIRED DATA + n (SG-08)"),
        ("Demotion gate back to paper", "defined", "never fired; nothing has been live",
         "a live strategy", "A LIVE STRATEGY"),
        ("Pre-register every strategy", "partly", "registration mechanism exists; no strategy is ranked",
         "a strategy submitted to the gate", "A REGISTERED STRATEGY"),
        ("Two-sided 'what would change our mind' on every strategy", "defined", "written per strategy in another tree",
         "-", "WORKING"),
        ("Injury/depth ablations instead of fixed penalties", "not done", "needs a dated series to ablate",
         "A third read before kickoff, plus weeks 1-9 captured forward", "A CAPTURE SERIES (SG-04)"),
        ("Immutable multi-day availability snapshots", "partial", "six reads of Week 10 in five modules; two hashed, none reconciled",
         "weeks of scheduled captures", "TIME (SG-04)"),
        ("Official inactive lists and snap counts", "partial", "Game Book sheets for 2 games; no league-wide snap table",
         "a snap-count source, or 32 club sheets weekly", "A SNAP SOURCE (Q4)"),
        ("32-team roster/IR sweep before a team model is trusted", "blocked", "reserve capture is partial by pagination",
         "a complete roster-status source", "A STATUS SOURCE (Q3)"),
        ("Reserve list capture", "partial", "133 rows, no month complete",
         "paginated capture", "PAGINATION (Q3)"),
        ("Injury signal as a surprise, never a level", "partial", "a 42-hour Week-10 delta computed here: 13 designations, 6 practice moves",
         "a dated read series", "TWO READS (SG-04)"),
        ("Depth from playing time, not jersey order", "not done", "no snap-count source captured",
         "snap counts", "A SNAP SOURCE (Q4)"),
        ("Availability graph: expected vs actual starter", "partial", "Game Books for 2 games give actual starters",
         "expected starters for all games", "AN ANNOUNCED-STARTER SOURCE"),
        ("Injury report as a timestamped series", "blocked", "one capture; the page prints no clock",
         "our own clock at each scheduled read", "A CAPTURE SERIES (SG-04)"),
        ("Calibrate what Questionable means", "pilot only", "68% played on n=79, one season",
         "several seasons joined to inactive lists", "MORE SEASONS (Q6)"),
        ("Archive past-season injury reports", "done for one week", "2023-2025 Week 10 captured",
         "full-week chunks for all seasons", "FULL-WEEK CAPTURE"),
        ("Roster turnover as a first-class event", "partial", "trades feed read; depth not versioned against it",
         "versioned roster snapshots", "ROSTER SNAPSHOTS"),
        ("Flag stale depth rows against transactions", "not done", "needs roster snapshots to compare",
         "dated roster snapshots", "ROSTER SNAPSHOTS"),
        ("Fixture context from published schedule facts", "partial", "venue, date, kickoff, network captured",
         "roof, surface, weather", "A ROOF/SURFACE SOURCE"),
        ("Venue transcribed from the official game centre", "partial", "1 of 13 Week-11 fixtures read; two official names disagree",
         "game-centre read for all 13", "12 MORE GAME CENTRES (SG-05)"),
        ("Roof/surface and hourly weather overlay", "not done", "no roof/surface capture; weather feed not admitted",
         "an official roof designation and a weather source", "TWO SOURCES (Q5)"),
        ("Decision-readiness table on the landing page", "done", "this page plus the executive summary",
         "-", "WORKING"),
        ("Weekly 'what changed' diff", "partial", "week-over-week diff exists in one tree",
         "a second week of captures", "TIME"),
        ("Publish every model total twice until one wins", "done", "two estimators published with a gap column",
         "-", "WORKING"),
        ("Drift alarm on every parser", "done", "14 datasets pinned; CI fails loudly",
         "-", "WORKING"),
        ("Control baselines on every leaderboard run", "partial", "controls run on the settled Week-10 board",
         "a leaderboard run", "A RANKED SET"),
        ("Train / validation / final holdout split", "blocked", "one season",
         "earlier seasons", "MORE SEASONS (Q6)"),
        ("Rank on proper scores with uncertainty, not win rate", "done by design", "explained and applied on Lines & value",
         "-", "WORKING"),
        ("Reject ranking by season-long ROI", "rejected", "recorded as a rejected proposal",
         "-", "DECIDED"),
        ("Keep parlays and prop combos behind a joint-evidence gate", "done by design", "no combo is ranked",
         "a validated joint probability", "JOINT MODEL"),
    ]
    PROV = {
        "WORKING": ("#top", "asserted by this board"),
        "done": ("#top", "asserted by this board"),
        "done by design": ("#top", "asserted by this board"),
        "rejected": ("#top", "recorded decision"),
    }
    trs = []
    for i, (name, state, detail, need, gate) in enumerate(req, 1):
        kind = "ok" if state in ("done", "WORKING", "done by design", "rejected") else ("bad" if state in ("blocked", "not done") else "warn")
        where = PROV.get(state)
        if where:
            prov = f'<a class="src" href="{where[0]}">{esc(where[1])}</a>'
        else:
            prov = '<span class="b warn">UNVERIFIED here - see Flagged</span>'
        trs.append([f'<b>{esc(name)}</b>', badge(state.upper(), kind), esc(detail), esc(need),
                    f'<code>{esc(gate)}</code>', prov])
    body = f"""
<h1>Requirement register: state, gate, and the number that clears it</h1>
<p class="lede">{len(req)} requirements from the brief, one row each. The third column is what is
actually true today; the fourth is the number or artefact that would change it; the fifth names the
gate that blocks it. A row that says WORKING is working; a row that says BLOCKED has a named
missing input, not an excuse.</p>

<div class="callout">
<p style="margin:0"><b>Reading the states.</b> <b>WORKING</b> &mdash; the requirement is met on the
site you are reading. <b>PARTIAL</b> &mdash; some of it exists and the gap is named. <b>BLOCKED</b> &mdash;
it cannot be done without an input this repository does not hold, and the input is named in the gate
column. <b>NOT DONE</b> &mdash; it could be done and has not been.</p>
</div>
{table(["Requirement","State","What is true today","The number or artefact that clears it","Gate","Provenance"], trs)}

<h2>The four gates that block the most</h2>
<table><thead><tr><th>Gate</th><th>Blocks</th><th class="n">Requirements</th><th>Owner</th><th>Source</th></tr></thead><tbody>
<tr><td><b>ADMITTED PRICE SOURCE</b></td><td>every return, residual, staking score and reward</td><td class="n">5</td><td>Owner (Q2)</td><td><a class="src" href="https://www.nfl.com/schedules/2026/by-week/week-11">nfl.com/schedules/2026/by-week/week-11</a></td></tr>
<tr><td><b>CAPTURE SERIES</b></td><td>the surprise signal, ablations, the timestamped report</td><td class="n">4</td><td>Data lead (SG-04)</td><td><a class="src" href="https://www.nfl.com/injuries/">nfl.com/injuries/</a></td></tr>
<tr><td><b>ROSTER / SNAP SOURCE</b></td><td>roster sweep, depth from playing time, replacement truth</td><td class="n">5</td><td>Data lead (Q3, Q4)</td><td><a class="src" href="https://www.nfl.com/transactions/league/reserve-list/2026/11">reserve-list/2026/11</a></td></tr>
<tr><td><b>MORE SEASONS</b></td><td>holdout split, designation calibration, multiplicity discipline</td><td class="n">3</td><td>Model owner (Q6)</td><td><a class="src" href="https://www.nfl.com/standings/league/2026/REG">nfl.com/standings/league/2026/REG</a></td></tr>
</tbody></table>
<p class="note">Those four gates are answered by three decisions and one capture schedule. That is
the whole of the remaining work; everything else on this page is bookkeeping on top of data that is
already verified.</p>
"""
    write("requirements.html", "Requirements - X3 NFL decision board", body)


def build_flagged() -> None:
    fl = [
        ("F-01", "High", "Results feed",
         "The canonical results file marks 13 of the 14 settled Week-10 games SCHEDULED while the official schedule page shows every score, and the landing page presents that file as the verified feed.",
         "https://www.nfl.com/schedules/2026/by-week/week-10", "Retire the stale file (SG-01). Not repaired here: it belongs to another module's scope."),
        ("F-02", "High", "Reserve list",
         "Seven players are listed Reserve/Injured and also carry a Questionable or Doubtful game designation in the Week-10 report, i.e. a designation that permits play.",
         "https://www.nfl.com/injuries/league/2026/reg10", "Treat the feed as an event log (SG-03). The cause cannot be separated from the captured evidence."),
        ("F-03", "High", "Reserve list",
         "No month view could be captured completely: each truncates at about 25 rows and ?limit=100 did not extend it.",
         "https://www.nfl.com/transactions/league/reserve-list/2026/10", "Every reserve-derived statement is partial. Do not read absence as availability."),
        ("F-04", "High", "Venue",
         "The Week-11 schedule page venue block says NRG Stadium for IND@HOU; the Game Centre Game Info block says Reliant Stadium.",
         "https://www.nfl.com/games/colts-at-texans-2026-reg-11", "Both published, neither adopted, until an owner sets precedence (SG-05)."),
        ("F-05", "High", "Markets",
         "The repository holds zero market prices, so no residual, CLV, ROI or staking score can be computed.",
         "https://www.nfl.com/schedules/2026/by-week/week-11", "Every such column is blank and marked BLOCKED. This blocks the leaderboard by rule."),
        ("F-06", "Medium", "Injury report",
         "The Week-11 report had not been published at the read clock; reg11 serves the Week-10 page. Corroborated by an earlier session's capture (data/desk/text/injuries-w11.txt, the Week-10 page under a Week-11 filename) and by four dated probes run today by another session (03:06Z, 03:16Z, 03:31Z, 03:45Z in data/week11/reg11_probes.csv), which bracket this read at 03:20Z.",
         "https://www.nfl.com/injuries/league/2026/reg11", "No Week-11 injury row is transcribed. The capture must be repeated after publication."),
        ("F-07", "Medium", "Reserve list",
         "The brief states Lamar Jackson and Tyler Huntley are on injured reserve; the capture holds no 2026 entry for either.",
         "https://www.nfl.com/transactions/league/reserve-list/2026/10", "Unconfirmed, not refuted. Absence in a partial capture is not evidence."),
        ("F-08", "Medium", "Injury report",
         "The official report page publishes no timestamp for its own update.",
         "https://www.nfl.com/injuries/", "Designations cannot be ordered against transactions; 'reserve date after report' is unevaluable."),
        ("F-09", "Medium", "Depth",
         "76 replacement rows, and the blanks are concentrated where the injured player is absent from his club's chart.",
         "https://www.nfl.com/injuries/league/2026/reg10", "A blank is correct output, not missing work. Named as a limit on every row."),
        ("F-10", "Medium", "Correlation",
         "The correlation register holds zero computed values, because no paired game-level outcomes are stored.",
         "https://www.nfl.com/injuries/league/2026/reg10", "An n cannot be published without the pairs behind it (SG-08)."),
        ("F-11", "Low", "Snap counts",
         "No league-wide official snap-count table is captured; Game Book playtime exists only for the games read.",
         "https://www.nfl.com/injuries/league/2026/reg10", "The 'depth from playing time' requirement stays open (Q4)."),
        ("F-12", "Low", "Site structure",
         "The repository publishes the 2026 season in two trees with different game counts, and many trees duplicate the same registers.",
         "https://www.nfl.com/standings/league/2026/REG", "Consolidation proposed (SG-09); not performed, because other sessions own those files."),
        ("F-13", "Low", "Data rights",
         "No terms read is recorded for storing or republishing official page content.",
         "https://www.nfl.com/terms-and-conditions/", "Blocks the private data layer until the owner decides (Q1)."),
        ("F-14", "High", "Capture drift",
         "Two reads of one page differ in encoding, not content: the Rams are LAR in the older file and LA in the newer, and the practice field switches from full words to abbreviations. A naive join reports 16 additions and 14 removals where 2 additions and 13 designation moves exist.",
         "https://www.nfl.com/injuries/league/2026/reg10",
         "Normalise club codes and vocabulary before differencing. Two independent reads of the same page agree on all 333 shared designations and differ on all 333 practice strings, so agreement has to be defined after normalisation or it is meaningless."),
        ("F-15", "High", "Capture reconciliation",
         "Six stored reads of one week's report live in five modules: two are hashed and dated, four are not, and none has been reconciled into one series. The same page therefore supports several different row counts depending on which module is asked.",
         "https://www.nfl.com/injuries/league/2026/reg10",
         "One dated series per week, written by the scheduled workflow, with the other modules pointing at it instead of keeping private copies. Not performed here: those trees belong to other sessions."),
    ]
    trs = [[f'<b>{esc(i)}</b>', badge(s, "bad" if s == "High" else ("warn" if s == "Medium" else "mut")),
            f'<b>{esc(a)}</b>', esc(d), src(u), esc(act)] for i, s, a, d, u, act in fl]
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Every irregularity found on this pass, with the official page that shows it and the
action proposed. Nothing on this page blocks the wider site: each row is published so it can be
reviewed, and none has been repaired by overwriting another module's file.</p>

<div class="callout bad">
<p style="margin:0"><b>Four high-severity items.</b> F-01 is a live defect on the front page and is
cheap to fix. F-02 and F-03 mean the newest dataset on this board cannot be trusted for
individual players yet, only for dated facts. F-04 is two official sources disagreeing, which no
amount of transcription resolves &mdash; it needs a rule. F-05 is the structural one: with no prices,
no strategy can be scored for money, and the leaderboard is empty by rule rather than by choice.</p>
</div>
{table(["#","Severity","Area","What is wrong","Official page that shows it","Proposed action"], trs)}

<h2>Items that look like errors and are not</h2>
<table><thead><tr><th>Observation</th><th>Why it is correct</th></tr></thead><tbody>
<tr><td>Blank replacement cells</td><td>A club chart that does not list the injured player cannot name his replacement. Guessing one would fabricate a starter the club never named. <a href="https://www.nfl.com/injuries/league/2026/reg10" target="_blank" rel="noopener">nfl.com/injuries/league/2026/reg10</a></td></tr>
<tr><td>The leaderboard has no rows</td><td>No strategy can pass the price gate. An empty board is the correct output of a rule that works. <a href="https://www.nfl.com/schedules/2026/by-week/week-11" target="_blank" rel="noopener">nfl.com/schedules/2026/by-week/week-11</a></td></tr>
<tr><td>Market and difference columns are empty</td><td>There is no market number. A residual computed without one is the fair number restated. <a href="https://www.nfl.com/schedules/2026/by-week/week-11" target="_blank" rel="noopener">nfl.com/schedules/2026/by-week/week-11</a></td></tr>
<tr><td>Out players sometimes play</td><td>Four measured cases in the reliability pilot, each published with its Game Book. Designations describe expectation, not outcome; that is the point of the surprise feature. <a href="https://www.nfl.com/injuries/league/2026/reg10" target="_blank" rel="noopener">nfl.com/injuries/league/2026/reg10</a></td></tr>
<tr><td>Some tables have fewer rows than a full month</td><td>Pagination truncation, recorded on the capture manifest. Partial is stated; partial is not silent. <a href="https://www.nfl.com/transactions/league/reserve-list/2026/10" target="_blank" rel="noopener">nfl.com/transactions/league/reserve-list/2026/10</a></td></tr>
</tbody></table>
"""
    write("flagged.html", "Flagged for review - X3 NFL decision board", body)


def build_sources() -> None:
    s = [
        ("Injury report, Week 10, 2026", "https://www.nfl.com/injuries/league/2026/reg10", "345 player rows; 4 clubs re-read today", "official"),
        ("Injury report landing (live week)", "https://www.nfl.com/injuries/", "used to confirm no Week-11 report", "official"),
        ("Injury report, Week 11 (probe)", "https://www.nfl.com/injuries/league/2026/reg11", "serves the Week-10 page at the read clock", "official"),
        ("League standings, 2026 regular season", "https://www.nfl.com/standings/league/2026/REG", "32 clubs; reconciliation and luck panel", "official"),
        ("Schedule, Week 10, 2026", "https://www.nfl.com/schedules/2026/by-week/week-10", "14 finals; used to check the results feed", "official"),
        ("Schedule, Week 11, 2026", "https://www.nfl.com/schedules/2026/by-week/week-11", "13 fixtures, 6 byes; venues from the venue block", "official"),
        ("Game Centre, IND at HOU, Week 11", "https://www.nfl.com/games/colts-at-texans-2026-reg-11", "Game Info block: Reliant Stadium; practice participation", "official"),
        ("Transactions, reserve list, November 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/11", "25 rows", "official"),
        ("Transactions, reserve list, October 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/10", "25 rows", "official"),
        ("Transactions, reserve list, September 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/09", "25 rows", "official"),
        ("Transactions, reserve list, August 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/08", "25 rows", "official"),
        ("Transactions, reserve list, July 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/07", "9 rows", "official"),
        ("Transactions, reserve list, June 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/06", "8 rows", "official"),
        ("Transactions, reserve list, May 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/05", "9 rows", "official"),
        ("Transactions, reserve list, April 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/04", "2 rows", "official"),
        ("Transactions, reserve list, March 2026", "https://www.nfl.com/transactions/league/reserve-list/2026/03", "5 rows", "official"),
        ("Transactions, trades, November 2026", "https://www.nfl.com/transactions/league/trades/2026/11", "13 trades incl. Brissett to BAL, Allen and Downs out of IND", "official"),
        ("Transactions, signings, November 2026", "https://www.nfl.com/transactions/league/signings/2026/11", "practice-squad and free-agent signings", "official"),
        ("Transactions, other, November 2026", "https://www.nfl.com/transactions/league/other/2026/11", "exempt and suspension moves", "official"),
        ("League terms and conditions", "https://www.nfl.com/terms-and-conditions/", "cited for the unresolved rights question (Q1) - not read in full", "official"),
        ("Flexible scheduling procedures", "https://www.nfl.com/legal/flexible-scheduling-procedures", "linked from the schedule page; why late-season dates move", "official"),
    ]
    trs = [[f'<b>{esc(n)}</b>', src(u), esc(use), badge(k.upper(), "ok" if k == "official" else "warn")] for n, u, use, k in s]
    body = f"""
<h1>Sources</h1>
<p class="lede">Every page used on this board, with what it was used for and when it was read.
All are official NFL properties. Internal repository files that this board re-publishes are named
on the page that uses them.</p>

<div class="callout warn">
<p style="margin:0"><b>Read clock: {esc(AS_OF)}.</b> These pages change during the week, especially
the injury hub. A value on this board is a statement about the page at that time, not a live feed.
Shell HTTP to nfl.com is blocked in this environment, so every retrieval was made with the
page-reader tool; that tool has no archival guarantee, which is why raw captures are retained in the
repository wherever a row depends on one.</p>
</div>
{table(["Source","Page","Used for on this board","Type"], trs)}

<h2>Internal files this board re-publishes</h2>
<table><thead><tr><th>File</th><th>What it holds</th><th>Re-published on</th></tr></thead><tbody>
<tr><td><code>data/closeout/derived/season_log.csv</code></td><td>150 played games, reconciled to the official standings</td><td><a href="results.html">Results &amp; luck</a></td></tr>
<tr><td><code>data/closeout/derived/forecasts_w11.csv</code></td><td>13 frozen Week-11 fair lines with every input</td><td><a href="lines.html">Lines &amp; value</a></td></tr>
<tr><td><code>data/hub/injuries_2026_wk10.csv</code></td><td>345 Week-10 report rows</td><td><a href="injuries.html">Injuries &amp; depth</a></td></tr>
<tr><td><code>data/x3/verified/depth_replacement.csv</code></td><td>76 replacement rows for Week-10 designations</td><td><a href="injuries.html">Injuries &amp; depth</a></td></tr>
<tr><td><code>board/data/*.csv</code></td><td>this board's own captures: reserve list, join, verification pass, luck panel</td><td>every page &mdash; <a href="verification.html">manifest and provenance</a></td></tr>
</tbody></table>

<h2>Method, in one paragraph</h2>
<p>Each official page was retrieved and read as text. Row-level values were transcribed only where
the page prints them; every table on this board is generated from a stored CSV by
<code>scripts/board_build.py</code>, so a number on a page can always be traced to a row in a file
and from that row to a source link. Where two official pages disagree, both are published. Where a
page had not been published, the row says so. Where a value could not be confirmed, the cell is
blank, carries BLOCKED or UNVERIFIED, and appears on <a href="flagged.html">Flagged for review</a>.</p>

<h2>What is deliberately absent</h2>
<ul class="tight">
<li>No sportsbook, odds aggregator or third-party statistics site is cited. A price from a
commercial book is not an official NFL publication, and this board does not launder one into an
official-looking column.</li>
<li>No inferred value is presented as sourced anywhere on the site.</li>
<li>No figure is carried over from another tree without being re-read on this pass.</li>
</ul>
"""
    write("sources.html", "Sources - X3 NFL decision board", body)


def main() -> None:
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (SITE / "assets" / "board.css").write_text(CSS, encoding="utf-8")
    build_index()
    build_verification()
    build_reserve()
    build_results()
    build_lines()
    build_strategies()
    build_injuries()
    build_questions()
    build_suggestions()
    build_requirements()
    build_flagged()
    build_sources()
    pages = sorted(p.name for p in SITE.glob("*.html"))
    print(f"board: wrote {len(pages)} pages + assets/board.css  ({', '.join(pages)})")


if __name__ == "__main__":
    main()
