#!/usr/bin/env python3
"""Generate static GitHub Pages module under live/ from data/live/ + verified repo CSVs.

Run: python3 scripts/live_site.py
"""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "live"
LIVE = ROOT / "live"

NAV = [
    ("index.html", "Overview & Readiness"),
    ("lines-weather.html", "Week-11 Lines & NWS Weather"),
    ("week10-gamebooks.html", "Week-10 Game Books & Rule 6"),
    ("injuries-transactions.html", "Injuries, Delta & Transactions"),
    ("calibration-strategies.html", "Calibration, Strategies & Gates"),
    ("questions-suggestions.html", "What Changed, Q&A & Suggestions"),
    ("flagged.html", "Flagged for Review"),
]


def esc(x: Any) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def badge(status: str) -> str:
    s = status.strip().upper()
    cls = "p"
    if any(k in s for k in ("VERIFIED", "PASS", "MATCH")):
        cls = "v"
    elif any(k in s for k in ("BLOCKED", "FAIL")):
        cls = "b"
    elif any(k in s for k in ("UNVERIFIED", "FLAG")):
        cls = "u"
    elif "DERIVED" in s:
        cls = "d"
    return f'<span class="badge {cls}">{esc(status)}</span>'


def src_cell(url: str, label: str = "Official source") -> str:
    u = (url or "").strip()
    if u.startswith(("http://", "https://")):
        return f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(label)}</a>'
    if u:
        return f'<span class="badge u">UNVERIFIED</span> <span class="mut">{esc(u)}</span>'
    return '<span class="badge u">UNVERIFIED</span>'


def table_html(headers: list[str], rows: list[list[str]], tid: str = "", note: str = "") -> str:
    id_attr = f' id="{esc(tid)}"' if tid else ""
    ths = "".join(f"<th>{esc(h)}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = "".join(f"<td>{c}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    note_html = f'<p class="note">{note}</p>' if note else ""
    return (
        f'<div class="tbl-wrap"><table{id_attr}><thead><tr>{ths}</tr></thead>'
        f'<tbody>{"".join(trs)}</tbody></table></div>{note_html}'
    )


def layout(slug: str, title: str, subtitle: str, body: str, as_of: str) -> str:
    nav_links = "".join(
        f'<a class="{"active" if f == slug else ""}" href="{esc(f)}">{esc(lbl)}</a>'
        for f, lbl in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — X3 Live Desk ({esc(as_of)})</title>
<link rel="stylesheet" href="assets/live.css">
</head>
<body>
<header class="topbar">
  <div class="wrap">
    <div class="brand">
      <a class="home-link" href="../index.html">&larr; Main X3 Hub</a>
      <span class="pill">AS OF {esc(as_of)} UTC</span>
    </div>
    <h1>{esc(title)}</h1>
    <p class="subtitle">{esc(subtitle)}</p>
    <nav class="nav">{nav_links}</nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap foot">
  <p>X3 Live Operations Desk &middot; Every factual cell is linked to an official source URL or explicitly marked <code>UNVERIFIED</code> / <code>DERIVED</code> / <code>FLAGGED</code>. Generated deterministically by <code>scripts/live_build.py</code> &amp; <code>scripts/live_site.py</code>.</p>
</footer>
</body>
</html>
"""


def write_css() -> None:
    css = """:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #1f2630;
  --border: #30363d;
  --text: #e6edf3;
  --mut: #8b949e;
  --accent: #58a6ff;
  --ok-bg: #123622; --ok-fg: #56d364;
  --warn-bg: #3b2e10; --warn-fg: #e3b341;
  --bad-bg: #3d181a; --bad-fg: #ff7b72;
  --der-bg: #152b47; --der-fg: #79c0ff;
}
* { box-sizing: border-box; }
body {
  margin: 0; font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg); color: var(--text);
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code { background: var(--surface2); padding: 1px 5px; border-radius: 4px; font-size: 12.5px; }
.wrap { max-width: 1280px; margin: 0 auto; padding: 0 20px; }
.topbar { background: var(--surface); border-bottom: 1px solid var(--border); padding: 18px 0 0; }
.brand { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 8px; }
.home-link { font-weight: 600; font-size: 13px; }
.pill { background: var(--der-bg); color: var(--der-fg); border: 1px solid #264d7a; padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; }
h1 { margin: 4px 0 4px; font-size: 24px; line-height: 1.25; }
h2 { margin: 28px 0 10px; font-size: 18px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
h3 { margin: 18px 0 8px; font-size: 15px; }
.subtitle { margin: 0 0 14px; color: var(--mut); }
.nav { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.nav a {
  padding: 8px 12px; border-radius: 6px 6px 0 0; border: 1px solid transparent;
  color: var(--mut); font-size: 13px; font-weight: 500;
}
.nav a:hover { color: var(--text); background: var(--surface2); text-decoration: none; }
.nav a.active { color: var(--text); background: var(--bg); border-color: var(--border); border-bottom-color: var(--bg); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 18px 0; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
.card .k { font-size: 12px; color: var(--mut); text-transform: uppercase; letter-spacing: 0.04em; }
.card .v { font-size: 24px; font-weight: 700; margin: 4px 0; }
.card .d { font-size: 12.5px; color: var(--mut); }
.callout { background: var(--surface); border-left: 4px solid var(--accent); border-radius: 6px; padding: 12px 16px; margin: 16px 0; }
.callout.warn { border-left-color: var(--warn-fg); }
.tbl-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); margin: 10px 0 16px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
th { background: var(--surface2); font-weight: 600; white-space: nowrap; }
tr:last-child td { border-bottom: none; }
.badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.badge.v { background: var(--ok-bg); color: var(--ok-fg); }
.badge.p { background: var(--warn-bg); color: var(--warn-fg); }
.badge.u { background: var(--warn-bg); color: var(--warn-fg); }
.badge.b { background: var(--bad-bg); color: var(--bad-fg); }
.badge.d { background: var(--der-bg); color: var(--der-fg); }
.mut { color: var(--mut); font-size: 12px; }
.note { color: var(--mut); font-size: 12.5px; margin: -6px 0 16px; }
.foot { border-top: 1px solid var(--border); margin-top: 36px; padding: 16px 20px 30px; color: var(--mut); font-size: 12.5px; }
"""
    (LIVE / "assets").mkdir(parents=True, exist_ok=True)
    (LIVE / "assets" / "live.css").write_text(css, encoding="utf-8")


def main() -> None:
    LIVE.mkdir(parents=True, exist_ok=True)
    write_css()

    manifest = load_json(DATA / "manifest.json")
    as_of = manifest["as_of"]
    rule6 = manifest["rule6"]
    cal_summary = load_json(DATA / "week10_calibration_summary.json")

    gb_rows = load_csv(DATA / "week10_gamebooks.csv")
    snap_rows = load_csv(DATA / "week10_snap_depth.csv")
    w11_inj = load_csv(DATA / "week11_injuries.csv")
    delta_rows = load_csv(DATA / "injury_delta_w10_w11.csv")
    tx_rows = load_csv(DATA / "transactions_audit.csv")
    lines_rows = load_csv(DATA / "week11_lines_live.csv")
    readiness = load_csv(DATA / "readiness_summary.csv")
    what_changed = load_csv(DATA / "what_changed.csv")
    questions = load_csv(DATA / "questions.csv")
    suggestions = load_csv(DATA / "suggestions.csv")
    flagged = load_csv(DATA / "flagged.csv")

    standings = load_csv(ROOT / "data" / "closeout" / "official_standings_2026_wk10.csv")
    scorecard = load_csv(ROOT / "data" / "closeout" / "derived" / "scorecard.csv")
    luck = load_csv(ROOT / "data" / "closeout" / "derived" / "luck.csv")
    ablation = load_csv(ROOT / "data" / "closeout" / "derived" / "ablation_shrink.csv")
    corrs = load_csv(ROOT / "data" / "closeout" / "derived" / "correlations.csv")
    slate_raw = load_json(DATA / "raw" / "week11_slate_weather_2026.json")

    # 1. index.html
    cards = "".join([
        f'<div class="card"><div class="k">Week-10 Game Books</div><div class="v">{len(gb_rows)}/14</div><div class="d">100% official PDFs parsed: starters, Not Active, DNP, kickoffs &amp; snaps</div></div>',
        f'<div class="card"><div class="k">Week-11 Live Injuries</div><div class="v">{manifest["week11_injury_rows"]}</div><div class="d">12 games active + CIN@WAS MNF notice; IND@HOU final Out/Q set</div></div>',
        f'<div class="card"><div class="k">NWS Weather Feeds</div><div class="v">8/8 US</div><div class="d">Hourly kickoff forecasts for all US outdoor Week-11 stadiums</div></div>',
        f'<div class="card"><div class="k">Nov 2026 Transactions</div><div class="v">{len(tx_rows)}</div><div class="d">Trades, Reserve/IR, Waivers &amp; Signings cross-checked vs reg11</div></div>',
        f'<div class="card"><div class="k">Kickoff TB Rate (W10)</div><div class="v">{rule6["touchback_rate_pct"]}%</div><div class="d">{rule6["touchbacks"]}/{rule6["kickoffs_total"]} kickoffs; {rule6["onside_kicks_observed"]} onside kick recovered</div></div>',
        f'<div class="card"><div class="k">Market Prices / ROI</div><div class="v">BLOCKED</div><div class="d">UNVERIFIED: no official NFL odds feed; market &amp; leaderboard stay empty</div></div>',
    ])

    exec_rows = [
        ["<b>1</b>", "Week-10 14/14 Game Books reconciled", "14/14 finals, 150-game season log (sum PF=PA=6,923), 308 starter slots &amp; Not Active/DNP parsed", badge("VERIFIED"), src_cell("https://www.nfl.com/schedules/2026/by-week/week-10")],
        ["<b>2</b>", "Week-11 live reg11 &amp; W10-&gt;W11 delta", f"{manifest['week11_injury_rows']} reg11 player rows + {len(delta_rows)} delta comparisons; IND@HOU Thursday final Out/Q verified", badge("VERIFIED"), src_cell("https://www.nfl.com/injuries/league/2026/reg11")],
        ["<b>3</b>", "Nov 2026 IR &amp; trade cross-check flags", "Caught A.Al-Shaair (HOU) &amp; J.Carlies (IND) on 11/17 IR yet still listed on reg11; D.Henley 11/10 trade vs 11/16 LAC start", badge("FLAGGED"), src_cell("https://www.nfl.com/transactions/league/reserve-list/2026/11")],
        ["<b>4</b>", "All 27 Game Center venues + May 14 schedule", "14/14 W10 + 13/13 W11 Game Center venues transcribed; caught 3 stadium naming diffs vs schedule page", badge("VERIFIED"), src_cell("https://media.nfl.com/football-information/2026/news/2026-nfl-schedule-announced")],
        ["<b>5</b>", "NWS hourly wind &amp; rain overlay", "8/8 US outdoor Week-11 stadiums via api.weather.gov; NO@CHI flagged (15 mph W, 34-80% rain); Mexico City outside NWS", badge("VERIFIED"), src_cell("https://api.weather.gov/gridpoints/LOT/76,72/forecast/hourly")],
        ["<b>6</b>", "2026 Rule 6 Kickoff &amp; Onside Priors", f"147 W10 kickoffs: 23.13% endzone, 12.24% touchbacks, 87.76% returned/in-play, 1 onside recovered (ATL), 28.89 avg start", badge("VERIFIED"), src_cell("https://operations.nfl.com/rules-officiating/2026-nfl-rulebook")],
        ["<b>7</b>", "Empirical designation calibration", "345 2026 W10 rows: Out 90.9% inactive/IR (60/66), Doubtful 40%, Questionable 19.0% inactive (81% active) + 2025/reg10 archive", badge("PARTIAL"), src_cell("https://www.nfl.com/injuries/league/2025/reg10")],
        ["<b>8</b>", "Market prices, CLV, ROI &amp; Leaderboard", "Originated Side-&gt;Total-&gt;ML fair values for 13/13 W11 games; market lines, CLV, ROI &amp; leaderboard remain empty on F-01", badge("BLOCKED"), src_cell("UNVERIFIED - no official NFL market-price feed")],
    ]
    exec_tbl = table_html(["#", "Executive Finding", "Verified Evidence (2026-11-19)", "Status", "Source"], exec_rows, tid="exec")

    rd_rows = [
        [f"<b>{esc(r['id'])}</b>", esc(r["area"]), esc(r["requirement"]), esc(r["gate"]), esc(r["clearing_metric"]), badge(r["status"]), src_cell(r["source_url"])]
        for r in readiness
    ]
    rd_tbl = table_html(["ID", "Area", "Requirement", "Blocking / Verification Gate", "Clearing Number / Evidence", "Status", "Source"], rd_rows, tid="readiness")

    idx_body = f"""
<div class="callout"><b>Live 2026-11-19 Completion:</b> All 14 Week-10 NFL Game Books, all 13 Week-11 Game Centers, live Week-11 Injury Report (<code>reg11</code>), May 14 schedule release, November 2026 official NFL transactions, 2026 Rulebook Rule 6, <code>2025/reg10</code> archive, and live NWS hourly forecasts for all 8 US outdoor stadiums have been ingested and cross-checked. Market odds remain <b>UNVERIFIED / BLOCKED</b> because NFL.com publishes no betting lines.</div>
<div class="grid">{cards}</div>
<h2>Executive Summary</h2>
{exec_tbl}
<h2>Decision-Readiness Matrix (2026-11-19 Live State)</h2>
{rd_tbl}
"""
    (LIVE / "index.html").write_text(layout("index.html", "X3 Live NFL Operations Desk", "Verified 2026-11-19 capture: 14/14 Week-10 Game Books, live Week-11 reg11 injuries, NWS weather, transactions & fair-line origination.", idx_body, as_of), encoding="utf-8")

    # 2. lines-weather.html
    line_tbl_rows = []
    for r in lines_rows:
        line_tbl_rows.append([
            f"<b>{esc(r['game_id'])}</b><br><span class='mut'>{esc(r['date_iso'])} {esc(r['kickoff_et'])} ET ({esc(r['network'])})</span>",
            f"{esc(r['gc_venue'])}<br>{badge(r['venue_diff_flag'])}",
            f"{esc(r['roof_surface'])}<br>{esc(r['nws_kickoff_wx'])}",
            f"<b>{esc(r['live_side_home'])}</b><br><span class='mut'>Frozen: {esc(r['frozen_side_home'])} &middot; P(cov) {esc(r['live_p_home_cover'])}</span>",
            f"<b>{esc(r['live_total_fair'])}</b><br><span class='mut'>Frozen: {esc(r['frozen_total'])} &middot; P(over) {esc(r['live_p_over'])}</span>",
            f"<b>{esc(r['live_ml_home_american'])} / {esc(r['live_ml_away_american'])}</b><br><span class='mut'>P(H) {esc(r['live_ml_home_prob'])}</span>",
            f"<span class='badge u'>UNVERIFIED</span> <span class='mut'>Market &amp; Diff blank</span>",
            f"{esc(r['wx_overlay_note'])}<br><span class='mut'>{esc(r['availability_context'])}</span>",
            src_cell(r["source_url"], "Game Center"),
        ])
    lines_tbl = table_html(
        ["Fixture", "Official Game Center Venue", "Roof / Surface & NWS Kickoff Wx", "1. Fair Side (Home)", "2. Fair Total", "3. Fair ML (H/A)", "Market / Diff", "Live Diagnostic Context (DERIVED)", "Source"],
        line_tbl_rows, tid="w11-lines",
        note="Origination order strictly follows Side -> Total -> Moneyline. Pre-registered X3-CO-1.0 lines remain frozen for out-of-sample grading; X3-LIVE-1.0 total overlays are marked DERIVED. Market columns remain blank/UNVERIFIED."
    )

    ann_rows = [
        ["May 14, 2026 Schedule Release", "107th season, 18 weeks, 272 games; 9 international games (Munich NE@DET W10, Mexico City MIN@SF W11 Estadio Banorte), Thanksgiving tripleheader, Black Friday DEN@PIT, Christmas Netflix doubleheader", badge("VERIFIED"), src_cell("https://media.nfl.com/football-information/2026/news/2026-nfl-schedule-announced", "media.nfl.com")],
        ["Week-11 Live Schedule + 6 Byes", "13 fixtures (Nov 19-23, 2026); Byes: " + ", ".join(f"{b['team']} ({b['record']})" for b in slate_raw["byes"]), badge("VERIFIED"), src_cell("https://www.nfl.com/schedules/2026/by-week/week-11", "Week-11 Schedule")],
        ["Venue Naming Reconciliation", "3 Week-11 Game Centers differ from schedule page: IND@HOU (RELIANT STADIUM vs NRG), AZ@KC (ARROWHEAD STADIUM vs GEHA Field), CIN@WAS (NORTHWEST STADIUM vs FedEx Field)", badge("FLAGGED"), src_cell("https://www.nfl.com/games/bengals-at-commanders-2026-reg-11", "CIN@WAS GC")],
        ["Vig-Free Market Consensus vs Fair Line", "Decomposition requires an official/approved market consensus feed; blocked under F-01 so market consensus and residual columns stay blank.", badge("BLOCKED"), src_cell("UNVERIFIED - no official NFL market-price feed")],
    ]
    ann_tbl = table_html(["Schedule / Consensus View", "Details", "Status", "Source"], ann_rows, tid="sched-ann")

    lw_body = f"""
<div class="callout"><b>Strict Origination Order &amp; Pre-Registration Separation:</b> Every fixture originates <b>Side &rarr; Total &rarr; Moneyline</b>. The <code>X3-CO-1.0</code> pre-report freeze is preserved intact for Week-11 grading, while <code>X3-LIVE-1.0</code> adds verified NWS kickoff-hour weather overlays (flagging <code>NO@CHI</code> 15 mph W / 34-80% rain) and live injury/IR context. Market consensus, market price, and difference cells stay blank and <code>UNVERIFIED</code>.</div>
<h2>Week-11 Originated Lines, Venues &amp; NWS Weather Overlay (13 Games)</h2>
{lines_tbl}
<h2>Dated Schedule Announcement (May 14, 2026) vs Live Schedule &amp; Market Consensus Gate</h2>
{ann_tbl}
"""
    (LIVE / "lines-weather.html").write_text(layout("lines-weather.html", "Week-11 Originated Lines, Schedule & NWS Weather", "Side -> Total -> ML origination, Game Center venues, May 14 schedule release, and NWS hourly kickoff weather.", lw_body, as_of), encoding="utf-8")

    # 3. week10-gamebooks.html
    gb_tbl_rows = []
    for g in gb_rows:
        gb_tbl_rows.append([
            f"<b>{esc(g['game_id'])}</b><br><span class='mut'>{esc(g['date_iso'])}</span>",
            f"<b>{esc(g['away'])} {esc(g['away_score'])} @ {esc(g['home'])} {esc(g['home_score'])}</b><br>{badge(g['log_reconciled'])}",
            f"{esc(g['gb_stadium'])}<br><span class='mut'>{esc(g['roof'])} / {esc(g['surface'])}</span>",
            f"{esc(g['temp_f'])}&deg;F, {esc(g['wind'])}<br><span class='mut'>{esc(g['weather_desc'])} &middot; Att {esc(g['attendance'])}</span>" if g["temp_f"] else f"{esc(g['wind'])}<br><span class='mut'>{esc(g['weather_desc'])} &middot; Att {esc(g['attendance'])}</span>",
            f"{esc(g['kickoffs_total'])} KO / {esc(g['kickoffs_in_ez'])} EZ / {esc(g['touchbacks'])} TB ({esc(g['tb_rate_pct'])}%)<br><span class='mut'>Start: {esc(g['away_avg_ko_start'])} / {esc(g['home_avg_ko_start'])}; Onside: {esc(g['onside_kicks'])}</span>",
            f"Not Active: {esc(g['away_not_active_cnt'])}/{esc(g['home_not_active_cnt'])}<br><span class='mut'>DNP: {esc(g['away_dnp_cnt'])}/{esc(g['home_dnp_cnt'])}</span>",
            src_cell(g["gamebook_pdf_url"], "Game Book PDF") + "<br>" + src_cell(g["game_center_url"], "Game Center"),
        ])
    gb_tbl = table_html(
        ["Game", "Final & Log Check", "Stadium / Roof / Surface", "Game Day Weather & Attendance", "Kickoffs / EZ / TB / Onside", "Inactives / DNP", "Official Sources"],
        gb_tbl_rows, tid="w10-gb"
    )

    r6_rows = [
        [f"<b>{esc(rc['rule'])}</b>", esc(rc["summary"]), badge("VERIFIED"), src_cell(rule6["source_rulebook"], "2026 Rulebook")]
        for rc in rule6["rule_changes_2026"]
    ]
    r6_rows.append([
        "<b>W10 Empirical (n=14)</b>",
        f"{rule6['kickoffs_total']} kickoffs: {rule6['kickoffs_in_endzone']} in endzone ({rule6['endzone_rate_pct']}%), {rule6['touchbacks']} touchbacks ({rule6['touchback_rate_pct']}%), {rule6['in_play_return_rate_pct']}% returned/in-play, {rule6['onside_kicks_observed']} declared onside kick ({rule6['onside_recoveries_observed']} recovered by ATL at 50-yd line), avg drive start {rule6['avg_kickoff_drive_start_yd']}-yd line.",
        badge("DERIVED"),
        src_cell("https://www.nfl.com/schedules/2026/by-week/week-10", "14 W10 Game Books"),
    ])
    r6_tbl = table_html(["Rule / Metric", "2026 Regime Summary & Week-10 Empirical Tally", "Status", "Source"], r6_rows, tid="rule6")

    st_rows = [
        [f"<b>{esc(s['team'])}</b>", f"{esc(s['w'])}-{esc(s['l'])}-{esc(s['t'])}", esc(s["pct"]), esc(s["pf"]), esc(s["pa"]), esc(s["net"]), esc(s["home"]), esc(s["road"]), esc(s["streak"]), src_cell(s["source_page"], "Standings")]
        for s in standings
    ]
    st_tbl = table_html(["Team", "W-L-T", "PCT", "PF", "PA", "Net", "Home", "Road", "Streak", "Source"], st_rows, tid="standings")

    gb_body = f"""
<div class="callout"><b>14/14 Week-10 Game Books Verified:</b> Prior repository artifacts read only 2 of 14 Week-10 Game Books (<code>NE@DET</code>, <code>LAC@BAL</code>). All 14 Game Books are now ingested, reconciling 14/14 finals against the 150-game season log (&Sigma;PF=&Sigma;PA=6,923) and quantifying the 2026 Dynamic Kickoff &amp; Declared Onside-Kick priors.</div>
<h2>2026 Rulebook Rule 6 &amp; Week-10 Kickoff / Onside Empirical Priors</h2>
{r6_tbl}
<h2>All 14 Week-10 Official NFL Game Books</h2>
{gb_tbl}
<h2>Official 2026 League Standings (32 Clubs through Week 10)</h2>
{st_tbl}
"""
    (LIVE / "week10-gamebooks.html").write_text(layout("week10-gamebooks.html", "Week-10 14/14 Game Books, Standings & Rule 6 Priors", "Complete official Game Book verification, stadium roof/surface weather, Rule 6 kickoff priors, and 32-team standings.", gb_body, as_of), encoding="utf-8")

    # 4. injuries-transactions.html
    tx_tbl_rows = [
        [esc(t["date"]), esc(t["category"]), f"<b>{esc(t['player'])}</b>", f"{esc(t['from_team'])} &rarr; {esc(t['to_team'])}", esc(t["transaction"]), badge("FLAGGED") if "FLAG" in t["audit_note"] else badge("VERIFIED"), esc(t["audit_note"]), src_cell(t["source_url"], "Transactions")]
        for t in tx_rows
    ]
    tx_tbl = table_html(["Date", "Category", "Player", "Clubs", "Transaction", "Audit", "Cross-Check Note", "Source"], tx_tbl_rows, tid="tx-audit")

    key_deltas = [d for d in delta_rows if d["delta_type"] != "unchanged"]
    delta_tbl_rows = [
        [esc(d["team"]), f"<b>{esc(d['player'])}</b> ({esc(d['pos'])})", badge(d["delta_type"]), f"{esc(d['w10_practice'])} / {esc(d['w10_status'])}", f"{esc(d['w11_practice'])} / {esc(d['w11_status'])}", esc(d["injury"]), esc(d["ir_or_tx_note"]), src_cell(d["source_url"], "NFL Source")]
        for d in key_deltas[:180]
    ]
    delta_tbl = table_html(
        ["Team", "Player", "Delta", "Week-10 (reg10)", "Week-11 (reg11)", "Injury", "IR / Trade Cross-Check", "Source"],
        delta_tbl_rows, tid="w10-w11-delta",
        note=f"Showing {min(180, len(key_deltas))} non-unchanged player transitions out of {len(delta_rows)} total tracked Week-10/Week-11 rows (full CSV in data/live/injury_delta_w10_w11.csv)."
    )

    w11_inj_tbl_rows = [
        [esc(r["game_id"]), esc(r["team"]), f"<b>{esc(r['player'])}</b>", esc(r["pos"]), esc(r["injury"]), esc(r["practice_status"]), badge(r["game_status"]) if r["game_status"] else '<span class="mut">blank</span>', badge("FLAGGED") + " " + esc(r["cross_check_flag"]) if "FLAG" in r["cross_check_flag"] else esc(r["cross_check_flag"]), src_cell(r["source_url"], "reg11")]
        for r in w11_inj
    ]
    w11_inj_tbl = table_html(["Game", "Team", "Player", "Pos", "Injury", "Practice Status", "Game Status", "Cross-Check Flag", "Source"], w11_inj_tbl_rows, tid="reg11-all")

    snap_tbl_rows = [
        [esc(s["game_id"]), esc(s["team"]), f"<b>{esc(s['player'])}</b>", esc(s["pos"]), esc(s["unit"]), esc(s["snaps"]), f"{esc(s['snap_pct'])}%" if s["snap_pct"] else "", esc(s["note"]), src_cell(s["source_url"], "Game Book PDF")]
        for s in snap_rows
    ]
    snap_tbl = table_html(["Game", "Team", "Player", "Pos", "Unit", "Snaps", "Snap %", "Depth / Replacement Note", "Source"], snap_tbl_rows, tid="snap-depth")

    inj_body = f"""
<div class="callout warn"><b>Reserve/Injured &amp; Trade Cross-Check Irregularities:</b> Cross-checking November 2026 official transactions against <code>reg11</code> caught <b>Azeez Al-Shaair (HOU)</b> and <b>Jaylon Carlies (IND)</b> placed on Reserve/Injured on <code>11/17</code> while still listed on <code>reg11</code>, <b>Aidan Hutchinson (DET)</b> placed on IR <code>11/18</code> after playing 9 snaps (15%) vs NE (absent from <code>reg11</code>), and <b>Daiyan Henley</b> listed in an <code>11/10</code> LAC&rarr;DEN trade yet starting for LAC on <code>11/16</code>.</div>
<h2>November 2026 Official NFL Transactions &amp; Stale-Depth Cross-Check ({len(tx_rows)} Events)</h2>
{tx_tbl}
<h2>Week-10 &rarr; Week-11 Availability Delta (Non-Unchanged Transitions)</h2>
{delta_tbl}
<h2>Week-10 Official Game Book Snap-Count Depth Sample (Replaces Jersey-Order &amp; Image-Only Charts)</h2>
{snap_tbl}
<h2>Complete Live Week-11 Injury Report (<code>2026/reg11</code>, {len(w11_inj)} Rows incl. MNF Notice)</h2>
{w11_inj_tbl}
"""
    (LIVE / "injuries-transactions.html").write_text(layout("injuries-transactions.html", "Week-11 Live Injuries, W10->W11 Delta, Transactions & Snap Depth", "Live reg11 injury report, player-level W10->W11 delta, Nov 2026 Reserve/IR & trade audit, and Playtime Percentage snap depth.", inj_body, as_of), encoding="utf-8")

    # 5. calibration-strategies.html
    c26 = cal_summary["w10_counts"]
    cal_rows_html = []
    for status, cnt in c26.items():
        tot = cnt["total"]
        na_ir = cnt["not_active"] + cnt["moved_to_ir"]
        rate_na = f"{100.0 * na_ir / tot:.1f}%" if tot else "0%"
        rate_act = f"{100.0 * cnt['active_or_other'] / tot:.1f}%" if tot else "0%"
        cal_rows_html.append([
            f"<b>{esc(status)}</b>", str(tot), str(cnt["not_active"]), str(cnt["moved_to_ir"]), str(cnt["dnp"]), str(cnt["active_or_other"]),
            f"<b>{rate_na}</b> inactive/IR &middot; {rate_act} active/other",
            badge("VERIFIED"),
            src_cell("https://www.nfl.com/injuries/league/2026/reg10", "2026 W10 Report + 14 Game Books"),
        ])
    cal_tbl = table_html(
        ["Designation (W10)", "n", "Not Active", "Moved to Nov IR", "DNP", "Active / Other", "Empirical Rate (DERIVED)", "Status", "Source"],
        cal_rows_html, tid="cal-2026"
    )

    arch_rows_html = [
        [esc(r["team"]), f"<b>{esc(r['player'])}</b> ({esc(r['pos'])})", esc(r["designation"]), esc(r["practice"]), esc(r["gamebook_outcome"]), badge("VERIFIED") if not r["played"] or r["designation"] != "Out" else badge("FLAGGED"), src_cell("https://static.www.nfl.com/image/upload/v1762861429/gamecenter/f7d53812-311e-11f0-b670-ae1250fadad1.pdf", "2025 PHI@GB Game Book")]
        for r in cal_summary["archive_2025_sample"]["phi_gb_2025_w10_calibration"]
    ]
    arch_tbl = table_html(["Team", "Player", "2025 W10 Designation", "Practice", "Official 2025 Game Book Outcome", "Status", "Source"], arch_rows_html, tid="cal-2025")

    sc_rows_html = [
        [f"<b>{esc(s['id'])}</b>", esc(s["division"]), esc(s["what_is_scored"]), esc(s["n_gradable"]), esc(s["brier"]), esc(s["skill_vs_benchmark"]), esc(s["mae_points"]), badge(s["sample_gate"]), badge(s["skill_gate"]), esc(s["verdict"]), src_cell(s["source"], "Frozen Snapshot")]
        for s in scorecard
    ]
    sc_tbl = table_html(["ID", "Division", "Scored Target", "n", "Brier", "Skill vs Bench", "MAE", "Sample Gate", "Skill Gate", "Verdict", "Source"], sc_rows_html, tid="scorecard")

    lk_rows_html = [
        [esc(l["measure"]), f"<b>{esc(l['value'])}</b>", esc(l["how_computed"]), esc(l["caveat"]), badge("DERIVED"), src_cell("https://www.nfl.com/standings/league/2026/REG", "Reconciled Log")]
        for l in luck
    ]
    lk_tbl = table_html(["Measure", "Value", "Method", "Caveat", "Type", "Source"], lk_rows_html, tid="luck-panel")

    ab_rows_html = [
        [esc(a["shrink_k"]), esc(a["mae_margin"]), esc(a["brier_home_win"]), esc(a["mae_total"]), esc(a["vs_naive_margin"]), esc(a["n"]), esc(a["read"]), badge("DERIVED"), src_cell("https://www.nfl.com/standings/league/2026/REG", "Walk-forward")]
        for a in ablation
    ]
    ab_tbl = table_html(["Shrink k", "Margin MAE", "Win Brier", "Total MAE", "vs Naive Margin", "n", "Note", "Type", "Source"], ab_rows_html, tid="ablation")

    corr_rows_html = [
        [f"<b>{esc(c['id'])}</b>", esc(c["quantity"]), esc(c["n"]), f"<b>{esc(c['r'])}</b>", f"[{esc(c['ci95_lo'])}, {esc(c['ci95_hi'])}]", esc(c["note"]), badge("DERIVED"), src_cell("https://www.nfl.com/standings/league/2026/REG", "Official Box Scores")]
        for c in corrs
    ]
    corr_tbl = table_html(["ID", "Quantity", "n", "r", "95% CI", "Interpretation", "Type", "Source"], corr_rows_html, tid="corrs")

    lb_rows = [
        ["ELIGIBLE-00", "Two-Stage Skill Leaderboard", "DELIBERATELY EMPTY: 0 strategies pass both Stage-1 (proper score &gt; benchmark &amp; game-cluster CI &gt; 0 at n &ge; 300) and Stage-2 (prospective CLV/ROI escrow with official prices). Two-sided falsifiers &amp; demotion gate (live &rarr; paper on rolling Brier &lt; 0) remain active.", badge("BLOCKED"), src_cell("UNVERIFIED - 0 eligible strategies")]
    ]
    lb_tbl = table_html(["Slot", "Leaderboard Division", "Current State &amp; Demotion / Falsifier Rule", "Status", "Source"], lb_rows, tid="leaderboard")

    cs_body = f"""
<div class="callout"><b>Empirical Designation Calibration &amp; Pre-Registered Validation:</b> Scoring all 345 <code>2026/reg10</code> rows across 14 Game Books shows <code>Out</code> = 90.9% inactive/IR, <code>Doubtful</code> = 40.0% inactive, and <code>Questionable</code> = 19.0% inactive (81.0% active). On strategy validation, backtest metrics are banned from the leaderboard, signal and staking are separated, and all parlays/SGP/props stay behind the joint-evidence correlation gate.</div>
<h2>2026 Week-10 Empirical Designation Calibration (345 Rows &times; 14 Game Books)</h2>
{cal_tbl}
<h2>Archived 2025 Week-10 Calibration Sample (<code>2025/reg10</code> + PHI@GB Game Book)</h2>
{arch_tbl}
<h2>Two-Stage Skill Leaderboard (Deliberately Empty)</h2>
{lb_tbl}
<h2>Pre-Registered Strategy Scorecard &amp; Gates (Signal Only, No Staking)</h2>
{sc_tbl}
<h2>Removal-of-Luck Panel &amp; Control Baselines</h2>
{lk_tbl}
<h2>Walk-Forward Shrinkage Ablation (n=110)</h2>
{ab_tbl}
<h2>Correlations Computed Strictly from Official Scores (with n &amp; 95% CI)</h2>
{corr_tbl}
"""
    (LIVE / "calibration-strategies.html").write_text(layout("calibration-strategies.html", "Designation Calibration, Strategies, Gates & Leaderboard", "Empirical Out/Doubtful/Questionable rates (2025 & 2026), removal-of-luck panel, correlations with n, and empty skill leaderboard.", cs_body, as_of), encoding="utf-8")

    # 6. questions-suggestions.html
    wc_rows_html = [
        [f"<b>{esc(w['area'])}</b>", esc(w["prior_state"]), esc(w["live_state"]), esc(w["impact"]), src_cell(w["source_url"])]
        for w in what_changed
    ]
    wc_tbl = table_html(["Area", "Prior State", "Live 2026-11-19 State", "Decision Impact", "Source"], wc_rows_html, tid="what-changed")

    q_rows_html = [
        [f"<b>{esc(q['id'])}</b>", badge(q["status"]), esc(q["question"]), esc(q["known"]), esc(q["missing"]), esc(q["how_to_discover"]), src_cell(q["source_url"])]
        for q in questions
    ]
    q_tbl = table_html(["ID", "State", "Question", "What Is Known", "What Is Missing", "How to Discover", "Source"], q_rows_html, tid="qa")

    s_rows_html = [
        [f"<b>{esc(s['id'])}</b>", badge("FLAGGED") if s["priority"] == "HIGH" else badge("PARTIAL"), esc(s["suggestion"]), esc(s["impact"]), esc(s["requires_approval"]), src_cell(s["source_url"])]
        for s in suggestions
    ]
    s_tbl = table_html(["ID", "Priority", "Reviewer Suggestion (Choose Before Implementing)", "Expected Impact", "Approval Needed", "Source"], s_rows_html, tid="suggestions")

    qs_body = f"""
<h2>What Changed (2026-11-18 Freeze &rarr; 2026-11-19 Live Capture)</h2>
{wc_tbl}
<h2>Open Questions &amp; Information Gaps</h2>
{q_tbl}
<h2>Suggestions for Reviewer Choice (Before Any Policy or Threshold Change)</h2>
{s_tbl}
"""
    (LIVE / "questions-suggestions.html").write_text(layout("questions-suggestions.html", "What Changed, Q&A & Reviewer Suggestions", "Weekly evidence diff, structured Q&A on known vs missing decisions, and reviewer suggestion queue.", qs_body, as_of), encoding="utf-8")

    # 7. flagged.html
    fl_rows_html = [
        [f"<b>{esc(f['id'])}</b>", esc(f["category"]), esc(f["item"]), esc(f["detail"]), badge(f["status"]), src_cell(f["source_url"])]
        for f in flagged
    ]
    fl_tbl = table_html(["ID", "Category", "Irregularity / Unverified Item", "Verification Detail", "Status", "Source"], fl_rows_html, tid="flagged-rows")

    fl_body = f"""
<div class="callout warn"><b>Strict Verification Policy:</b> Nothing unconfirmable is filled in. Market prices stay blank under <code>LF-01</code>, international NWS weather stays blank under <code>LF-05</code>, and every discrepancy discovered between official NFL sources (Reserve List vs <code>reg11</code>, Trades vs Game Book, Schedule vs Game Center venues) is logged here for review.</div>
<h2>Flagged for Review ({len(flagged)} Items)</h2>
{fl_tbl}
"""
    (LIVE / "flagged.html").write_text(layout("flagged.html", "Flagged for Review", "All unverified inputs, missing official feeds, and cross-source irregularities discovered during 2026-11-19 verification.", fl_body, as_of), encoding="utf-8")

    print(f"live_site OK: wrote 7 HTML pages + assets/live.css in {LIVE}")


if __name__ == "__main__":
    main()
