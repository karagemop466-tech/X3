#!/usr/bin/env python3
"""Deterministic builder for the ledger module (session arena/a60a2bf7-x3).

Inputs (read only):
  data/desk/games.json          official week-page captures (games, scores, source URL per game)
  data/desk/deficiencies.json   official injury-report rows joined to club depth charts
  hub/data/lines.json           model lines (DERIVED; market columns blank by policy)

Outputs:
  data/ledger/results_feed.csv        one row per FINAL game, source URL per row
  data/ledger/spot_checks.csv         live re-checks performed against official pages
  data/ledger/price_snapshots.csv     opening/closing price store (schema only; no source yet)
  data/ledger/lines_fair_market.csv   fair line, market line, difference (separate columns)
  data/ledger/replacement_depth.csv   injury-report rows with replacement depth
  ledger/*.html                       category pages

Rules: nothing is inferred. A value that is not in an input file is written blank.
Run:  python3 tools/build_ledger.py   (then python3 tools/verify_ledger.py)
"""
import csv
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEASON = 2026
DESK = ROOT / "data" / "desk"
OUT_DATA = ROOT / "data" / "ledger"
OUT_HTML = ROOT / "ledger"
REPO_URL = "https://github.com/karagemop466-tech/X3"
CAPTURED = "2026-11-14"
MODEL_SRC = "https://github.com/karagemop466-tech/X3/blob/arena/a60a2bf7-x3/hub/data/lines.json"

# Official host list used by the row-level gate (tools/verify_ledger.py).
APPROVED_HOSTS = {"www.nfl.com", "nfl.com", "operations.nfl.com", "www.houstontexans.com"}


def club_hosts_from_depth(depth_rows):
    hosts = set()
    for r in depth_rows:
        src = r.get("depth_source", "")
        if src.startswith("https://"):
            hosts.add(src.split("/")[2])
    return hosts


def fisher_ci(r, n):
    if n <= 3 or abs(r) >= 1:
        return None, None
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    return math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def esc(v):
    return html.escape("" if v is None else str(v))


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(["" if r.get(h) is None else r.get(h) for h in header])


def build_results(games):
    finals = [g for g in games if g["status"] == "FINAL"]
    finals.sort(key=lambda g: (g["week"], g["date_iso"], g["away"]))
    header = ["game_id", "season", "week", "date_iso", "away", "home", "away_score", "home_score",
              "home_margin", "total_points", "winner", "source_url", "verification"]
    rows = []
    for g in finals:
        a, h = int(g["away_score"]), int(g["home_score"])
        winner = g["home"] if h > a else (g["away"] if a > h else "TIE")
        gid = f"{SEASON}-W{g['week']:02d}-{g['away']}@{g['home']}"
        rows.append({
            "game_id": gid,
            "season": SEASON, "week": g["week"], "date_iso": g["date_iso"],
            "away": g["away"], "home": g["home"], "away_score": a, "home_score": h,
            "home_margin": h - a, "total_points": a + h, "winner": winner,
            "source_url": g["source"],
            "verification": ("LIVE_MATCH " + CAPTURED + " (official page re-fetched)" if gid in SPOT_IDS
                             else "CAPTURED_OFFICIAL_PAGE (desk CI " + CAPTURED + "; not re-fetched)"),
        })
    return header, rows


_W1 = [  # (away, home, away_pts, home_pts) transcribed from nfl.com/schedules/2026/by-week/week-1, chunk 1 of 2
    ("NE", "SEA", 10, 13), ("SF", "LA", 27, 7), ("CHI", "CAR", 59, 37), ("TB", "CIN", 27, 33),
    ("NO", "DET", 30, 31), ("BUF", "HOU", 36, 31), ("BAL", "IND", 41, 23), ("CLE", "JAX", 10, 34),
    ("ATL", "PIT", 13, 20), ("NYJ", "TEN", 23, 10), ("ARI", "LAC", 26, 14), ("MIA", "LV", 13, 27),
]
SPOT_CHECKS = [
    {"game_id": f"{SEASON}-W10-WAS@NYG", "url": "https://www.nfl.com/schedules/2026/by-week/week-10",
     "fetched_utc": CAPTURED, "observed": "Commanders 24, Giants 21, FINAL, Thursday, November 12th",
     "result": "MATCH (away WAS 24, home NYG 21)"},
] + [
    {"game_id": f"{SEASON}-W01-{a}@{h}", "url": "https://www.nfl.com/schedules/2026/by-week/week-1",
     "fetched_utc": CAPTURED, "observed": f"page lists {a} {ap}, {h} {hp}, FINAL",
     "result": f"MATCH (away {a} {ap}, home {h} {hp})"}
    for (a, h, ap, hp) in _W1
]


SPOT_IDS = {s["game_id"] for s in SPOT_CHECKS}


def build_prices_schema():
    header = ["snapshot_id", "game_id", "market", "side", "snapshot_type", "line", "price_american",
              "captured_at_utc", "book", "source_url", "verification"]
    return header, []  # no official price source identified; store is empty by policy


ALIAS = {"LAR": "LA", "AZ": "ARI"}  # model abbreviation -> official schedule abbreviation


def build_lines(games, lines_doc):
    """Join model lines to the official schedule. Orientation (away/home) is taken from the
    official schedule. If the model's home side differs, the model's spread is sign-ambiguous
    and is blanked; the total is orientation-independent and is kept."""
    header = ["game", "week", "date", "kickoff_slot_et", "away", "home", "fair_spread_home",
              "market_spread_home", "diff_spread_fair_minus_market", "fair_total", "market_total",
              "diff_total_fair_minus_market", "moneyline_home", "source_url", "verification"]
    rows = []
    for r in lines_doc["rows"]:
        ma, mh = ALIAS.get(r["away"], r["away"]), ALIAS.get(r["home"], r["home"])
        match = [g for g in games if g["week"] in (10, 11) and g["status"] != "FINAL"
                 and {g["away"], g["home"]} == {ma, mh}]
        if len(match) != 1:
            raise SystemExit(f"line row {r['game']} does not match exactly one scheduled game")
        g = match[0]
        conflict = g["home"] != mh
        mk_s = r.get("market_spread")
        mk_t = r.get("market_total")
        fair_s = "" if conflict else r["model_spread_home"]
        diff_s = round(fair_s - float(mk_s), 2) if (fair_s != "" and mk_s not in ("", None)) else ""
        diff_t = round(r["model_total"] - float(mk_t), 2) if mk_t not in ("", None) else ""
        ver = "DERIVED model X3-v1 (hub/data/lines.json); market blank: UNVERIFIED"
        if conflict:
            ver += "; IRREGULAR: model home/away reversed vs official schedule, spread blanked"
        rows.append({
            "game": f"{g['away']}@{g['home']}", "week": g["week"], "date": g["date_iso"],
            "kickoff_slot_et": r["slot"], "away": g["away"], "home": g["home"],
            "fair_spread_home": fair_s, "market_spread_home": mk_s if mk_s is not None else "",
            "diff_spread_fair_minus_market": diff_s, "fair_total": r["model_total"],
            "market_total": mk_t if mk_t is not None else "",
            "diff_total_fair_minus_market": diff_t, "moneyline_home": "",
            "source_url": g["source"], "verification": ver,
        })
    return header, rows


def build_depth(def_doc):
    header = ["week", "team", "player", "pos", "status", "injury", "group", "unit", "slot",
              "starter_depth_string", "replacement", "replacement_depth", "chart_size", "join",
              "chart_unofficial", "chart_as_of", "injury_source", "depth_source", "verification"]
    rows = []
    for r in def_doc["rows"]:
        rows.append({
            "week": r["week"], "team": r["team"], "player": r["player"], "pos": r["pos"],
            "status": r["status"], "injury": r["injury"], "group": r["group"], "unit": r["unit"],
            "slot": r["slot"], "starter_depth_string": r["depth_string"],
            "replacement": r["replacement"], "replacement_depth": r["replacement_depth"],
            "chart_size": r["chart_size"], "join": r["join"],
            "chart_unofficial": "yes" if r["chart_unofficial"] else ("" if r["chart_as_of"] == "" else "no"),
            "chart_as_of": r["chart_as_of"], "injury_source": r["injury_source"],
            "depth_source": r["depth_source"],
            "verification": "INJURY ROW OFFICIAL; CHART CLUB-PUBLISHED" + (
                "; replacement UNVERIFIED (no join)" if r["join"] != "matched" else ""),
        })
    return header, rows


def page(title, active, body, extra_head=""):
    nav = [("index.html", "Overview"), ("results.html", "Results feed"), ("prices.html", "Lines & prices"),
           ("depth.html", "Replacement depth"), ("governance.html", "Gates & correlation")]
    navhtml = "".join(
        f'<a href="{h}"{" class=active" if h == active else ""}>{esc(t)}</a>' for h, t in nav)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · X3 Ledger</title>
<link rel="stylesheet" href="ledger.css">{extra_head}
</head><body>
<header class="top"><div class="brand"><a href="index.html">X3 Ledger</a><span>NFL 2026 · data captured {CAPTURED}</span></div>
<nav>{navhtml}<a href="../hub/index.html">Canonical hub</a><a href="../hub/flagged.html">Flagged</a></nav></header>
<main>
<h1>{esc(title)}</h1>
{body}
</main>
<footer>Every row carries a link to an official source or is marked UNVERIFIED / DESIGN. Source repo: <a href="{REPO_URL}">{REPO_URL.split('github.com/')[1]}</a>. Blank cells are unverified on purpose.</footer>
<script src="ledger.js"></script>
</body></html>
"""


def table(headers, rows, cls="t"):
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = []
        for c in r:
            if isinstance(c, tuple) and c and c[0] == "HTML":
                tds.append(f"<td>{c[1]}</td>")
            else:
                tds.append(f"<td>{esc(c)}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return (f'<input class="filter" placeholder="Filter rows…" aria-label="Filter rows">'
            f'<div class="scroll"><table class="{cls}"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def link(url, label="source"):
    return ("HTML", f'<a href="{esc(url)}" rel="noopener">{esc(label)}</a>')


def blank_flag():
    return ("HTML", '<span class="unv">UNVERIFIED</span>')


def main():
    games = json.loads((DESK / "games.json").read_text())["games"]
    def_doc = json.loads((DESK / "deficiencies.json").read_text())
    lines_doc = json.loads((ROOT / "hub" / "data" / "lines.json").read_text())

    res_h, res_rows = build_results(games)
    pr_h, pr_rows = build_prices_schema()
    ln_h, ln_rows = build_lines(games, lines_doc)
    dp_h, dp_rows = build_depth(def_doc)

    write_csv(OUT_DATA / "results_feed.csv", res_h, res_rows)
    write_csv(OUT_DATA / "price_snapshots.csv", pr_h, pr_rows)
    write_csv(OUT_DATA / "lines_fair_market.csv", ln_h, ln_rows)
    write_csv(OUT_DATA / "replacement_depth.csv", dp_h, dp_rows)
    write_csv(OUT_DATA / "spot_checks.csv",
              ["game_id", "url", "fetched_utc", "observed", "result"], SPOT_CHECKS)

    # ---- correlations: only official finals; n published with each value
    x_home = [r["home_score"] for r in res_rows]
    x_away = [r["away_score"] for r in res_rows]
    tot = [r["total_points"] for r in res_rows]
    absm = [abs(r["home_margin"]) for r in res_rows]
    wk = [r["week"] for r in res_rows]
    corr_defs = [
        ("Home points vs away points", x_home, x_away),
        ("Total points vs absolute home margin", tot, absm),
        ("Week number vs total points (scoring trend)", wk, tot),
    ]
    corr_rows = []
    for label, a, b in corr_defs:
        n = len(a)
        r = pearson(a, b)
        lo, hi = fisher_ci(r, n)
        corr_rows.append((label, n, round(r, 3), round(lo, 3), round(hi, 3)))

    # ---- depth rollups (computed, not typed)
    matched = [r for r in dp_rows if r["join"].startswith("matched")]
    depth_counts = {}
    for r in matched:
        k = str(r["replacement_depth"]) or "blank"
        depth_counts[k] = depth_counts.get(k, 0) + 1
    unmatched_n = len(dp_rows) - len(matched)

    # ---- html pages
    fin_n = len(res_rows)
    weeks = sorted({r["week"] for r in res_rows})
    week_urls = sorted({r["source_url"] for r in res_rows})
    total_games = len(games)
    sched_n = total_games - fin_n

    # results.html
    res_table_rows = []
    for r in res_rows:
        res_table_rows.append([r["game_id"], r["week"], r["date_iso"], r["away"], r["away_score"],
                               r["home"], r["home_score"], r["home_margin"], r["total_points"],
                               r["winner"], link(r["source_url"], "nfl.com week page"),
                               "live match 2026-11-14" if r["game_id"] in SPOT_IDS else "captured (not re-fetched)"])
    res_body = f"""
<p class="lede">{fin_n} FINAL games from the official NFL week schedule pages (weeks {weeks[0]}–{weeks[-1]}).
{sched_n} scheduled games are excluded until they are final. Each row links the official week page it was taken from.
{len(SPOT_CHECKS)} rows (Week 1: 12 of 16 games, plus Week 10 WAS@NYG) were re-fetched live from nfl.com and matched.
The other rows were captured by the desk pipeline from the same official pages and are <em>not</em> re-verified line by line here.</p>
<div class="cards"><div><b>{fin_n}</b>finals</div><div><b>{len(week_urls)}</b>official week pages</div><div><b>{len(SPOT_CHECKS)}</b>rows re-fetched live and matched</div></div>
<h2>Final results</h2>
{table(["Game ID","Wk","Date","Away","Pts","Home","Pts","Home margin","Total","Winner","Source","Check"], res_table_rows)}
<h2>Spot checks (this session)</h2>
{table(["Game ID","Official page","Fetched (UTC)","Observed on page","Result"],
       [[s["game_id"], link(s["url"], s["url"]), s["fetched_utc"], s["observed"], s["result"]] for s in SPOT_CHECKS])}
"""
    # prices.html
    line_rows = []
    for r in ln_rows:
        line_rows.append([r["game"], r["week"], r["date"], r["kickoff_slot_et"],
                          r["fair_spread_home"], r["market_spread_home"] or blank_flag(),
                          r["diff_spread_fair_minus_market"] or blank_flag(),
                          r["fair_total"], r["market_total"] or blank_flag(),
                          r["diff_total_fair_minus_market"] or blank_flag(),
                          r["moneyline_home"] or blank_flag(),
                          link(r["source_url"], "schedule page")])
    origination = [
        ["1", "Side (spread)", "Fair spread from model X3-v1 (DERIVED)", f"Available for {len(ln_rows)} unplayed games", link(MODEL_SRC, "hub/data/lines.json")],
        ["2", "Total", "Fair total from model X3-v1 (DERIVED)", f"Available for {len(ln_rows)} unplayed games", link(MODEL_SRC, "hub/data/lines.json")],
        ["3", "Moneyline", "Derived after side and total are fixed; no moneyline model exists", "NOT ORIGINATED (UNVERIFIED)", link(MODEL_SRC, "hub/data/lines.json")],
    ]
    prices_body = f"""
<p class="lede">Model lines are our own (DERIVED). Market columns are blank: no official NFL source publishes
2026 point spreads, totals or moneylines, so nothing is filled in. The difference column is computed only when
both fair and market values exist; with no market values it is blank.</p>
<p class="lede"><span class="unv">IRREGULAR</span> Three model rows (BUF@NYJ, CAR@NO, JAX@TEN) list the home and away teams the opposite way to the official schedule. Their fair spread is therefore blank. The fair total is kept, since a total does not depend on which side is home. Source: <a href="https://www.nfl.com/schedules/2026/by-week/week-10">nfl.com week 10 page</a> (e.g. "Bills at Jets", "Panthers at Saints", "Jaguars at Titans").</p>
<h2>Fair line, market line and difference (separate columns)</h2>
{table(["Game","Wk","Date","Slot (ET)","Fair spread (home)","Market spread (home)","Diff spread","Fair total","Market total","Diff total","Moneyline (home)","Source"], line_rows)}
<h2>Origination order: side → total → moneyline</h2>
{table(["Step","Market","Method","Status","Source"], origination)}
<h2>Price-snapshot store (opening and closing)</h2>
<p class="lede">Schema: <code>data/ledger/price_snapshots.csv</code>. Columns: snapshot_id, game_id, market, side,
snapshot_type (open/close), line, price_american, captured_at_utc, book, source_url, verification.
Current rows: <b>{len(pr_rows)}</b>. Opening and closing numbers cannot be recorded until the owner selects a price
source (no official NFL price feed was found, and the sandbox cannot reach third-party books).</p>
{table(pr_h, [], cls="t")}
"""
    # governance.html
    gate_rows = [
        ["D1", "Sample floor", "A strategy is evaluated only after N settled bets in the window (N proposed: 200; owner to set)", "PROPOSED", "not evaluable: 0 settled bets", ("HTML", '<span class="unv">DESIGN · UNVERIFIED</span>')],
        ["D2", "Signal test", "Demote to paper when the signal metric's 95% upper bound stays below 0 for 2 consecutive windows", "PROPOSED", "not evaluable", ("HTML", '<span class="unv">DESIGN · UNVERIFIED</span>')],
        ["D3", "Data integrity", "Freeze and demote to paper if any price snapshot in the window has no official-source link", "PROPOSED", "store empty", ("HTML", '<span class="unv">DESIGN · UNVERIFIED</span>')],
        ["D4", "Staking cannot promote or rescue", "Bankroll/staking results never change the signal rank or the gate state", "PROPOSED", "n/a", ("HTML", '<span class="unv">DESIGN · UNVERIFIED</span>')],
        ["D5", "Dependence", "Same-game parlay legs are scored as joint events; independence is never assumed", "PROPOSED", "n/a", ("HTML", '<span class="unv">DESIGN · UNVERIFIED</span>')],
    ]
    board_rows = [
        ["—", "No strategy has settled bets", "—", "blank", "blank", "blank", "blank", "UNVERIFIED: not evaluated"],
    ]
    corr_html = [[lab, n, r, lo, hi, link(f"https://github.com/karagemop466-tech/X3/blob/{'arena/a60a2bf7-x3'}/data/ledger/results_feed.csv", "results_feed.csv (COMPUTED from official rows)")]
                  for (lab, n, r, lo, hi) in corr_rows]
    gov_body = f"""
<p class="lede">The demotion gate and the signal/staking split are <strong>design proposals</strong>. Their thresholds are
not verified facts and must be set by the owner. Rows are marked DESIGN, not source-backed data.</p>
<h2>Demotion gate: live → paper</h2>
{table(["Gate","Name","Rule","Status","Current evaluation","Source"], gate_rows)}
<h2>Leaderboard: signal and staking shown separately</h2>
<p class="lede">The rank uses the signal metric only. Staking results are a separate column and cannot move a strategy up.</p>
{table(["Rank by signal","Strategy","Signal metric (CLV, n, CI)","Flat-stake result (n, CI)","Staking policy","Staking result (not ranked)","Gate state","Note"], board_rows)}
<h2>Correlations (official finals only; n published with each value)</h2>
<p class="lede">Pearson r with a Fisher-z 95% interval. Computed here from {fin_n} FINAL games in the results feed. Each
row's source is the results feed; the feed rows link the official week pages. These describe scoring only and
do not measure betting edge.</p>
{table(["Pair","n","r","95% CI low","95% CI high","Source"], corr_html)}
"""
    # depth.html
    dp_table = []
    for r in dp_rows:
        dp_table.append([r["week"], r["team"], r["player"], r["pos"], r["status"], r["injury"],
                         r["group"], r["unit"], r["slot"], r["starter_depth_string"], r["replacement"] or blank_flag(),
                         r["replacement_depth"] or blank_flag(), r["join"],
                         link(r["injury_source"], "injury report"),
                         link(r["depth_source"], "club depth chart") if r["depth_source"] else blank_flag()])
    dep_body = f"""
<p class="lede">Every injury-report row for weeks 8–10 with its replacement depth. The depth of the replacement is shown
(depth 2 = second string, 3 = third, 4 = fourth). Blank means the join failed; blanks are unverified, not zero.
Club charts are club-published and most are labelled unofficial by the club. Player profile links were removed:
the desk pipeline built them by slug, which is not verified.</p>
<div class="cards"><div><b>{len(dp_rows)}</b>report rows</div><div><b>{len(matched)}</b>joined to a chart</div><div><b>{unmatched_n}</b>not joined (UNVERIFIED)</div></div>
<h2>Replacement depth among joined rows</h2>
{table(["Replacement depth","Rows","Basis"], [[k, v, "COMPUTED from the rows below"] for k, v in sorted(depth_counts.items())] + [["(not joined)", unmatched_n, "COMPUTED; UNVERIFIED replacement"]])}
<h2>All injury-report rows</h2>
{table(["Wk","Team","Player","Pos","Status","Injury","Group","Unit","Slot","Starter depth","Replacement","Replacement depth","Join","Injury source","Depth source"], dp_table)}
"""
    # index.html
    w10_all = sum(1 for g in games if g["week"] == 10)
    w10_fin = sum(1 for g in games if g["week"] == 10 and g["status"] == "FINAL")
    idx_body = f"""
<p class="lede">A ledger for the NFL project: what has been recorded, from which official page, and what is still blank.
Nothing is inferred. Empty means unverified.</p>
<div class="cards">
 <div><b>{fin_n}</b>verified-source finals</div>
 <div><b>{len(pr_rows)}</b>price snapshots (open/close)</div>
 <div><b>{len(ln_rows)}</b>model lines (fair only)</div>
 <div><b>0</b>market lines</div>
 <div><b>{len(dp_rows)}</b>injury-report rows with depth check</div>
</div>
<h2>Sections</h2>
<table class="t k-meta"><thead><tr><th>Page</th><th>What it shows</th><th>Blank or unverified</th></tr></thead><tbody>
<tr><td><a href="results.html">Results feed</a></td><td>{fin_n} final games, one official link per row</td><td>{fin_n - len(SPOT_CHECKS)} rows captured, not re-fetched</td></tr>
<tr><td><a href="prices.html">Lines &amp; prices</a></td><td>Fair vs market vs difference; origination order; price store schema</td><td>all market prices and moneylines</td></tr>
<tr><td><a href="depth.html">Replacement depth</a></td><td>Injury-report rows with the replacement's depth</td><td>{unmatched_n} rows not joined</td></tr>
<tr><td><a href="governance.html">Gates &amp; correlation</a></td><td>Demotion gate proposal, signal vs staking, correlations with n</td><td>all strategy performance</td></tr>
</tbody></table>
<h2>Irregularities (this session)</h2>
<ul>
<li>Desk pipeline built player profile URLs by slug (e.g. nfl.com/players/…) without verifying them. They are removed from this ledger. Source: <code>data/desk/deficiencies.json</code>.</li>
<li>Club depth charts carry no as-of date for most clubs and are labelled unofficial by the club. Replacement depth is shown as a club-published fact, not an official NFL fact.</li>
<li>Week 10 is in progress: {w10_fin} of {w10_all} games are FINAL. The rest are scheduled for 15–16 Nov 2026 per the official week page.</li>
<li>Market prices: no official source; price store has 0 rows by design.</li>
<li>Model lines: BUF@NYJ, CAR@NO and JAX@TEN have reversed home/away orientation in <code>hub/data/lines.json</code>; their fair spreads are blanked here (source: nfl.com week 10 page).</li>
<li>Full list of open items: <a href="../hub/flagged.html">Flagged for review (canonical hub)</a>.</li>
</ul>
"""
    ledger_css = """
:root{--ink:#1b2430;--mut:#5b6573;--line:#dfe4ea;--bg:#f7f9fb;--acc:#1f5fa8;--warn:#b35c00}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header.top{background:#fff;border-bottom:1px solid var(--line);padding:10px 22px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
.brand a{font-weight:700;color:var(--ink);text-decoration:none;font-size:17px}.brand span{color:var(--mut);margin-left:10px;font-size:13px}
nav a{margin-left:12px;color:var(--acc);text-decoration:none;font-size:14px}nav a.active{font-weight:700;text-decoration:underline}
main{max-width:1200px;margin:0 auto;padding:18px 22px}h1{font-size:24px;margin:8px 0}h2{font-size:18px;margin:24px 0 8px}
.lede{color:var(--mut);max-width:900px}.cards{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.cards div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 14px;min-width:150px;color:var(--mut);font-size:13px}
.cards b{display:block;font-size:22px;color:var(--ink)}
.filter{width:100%;max-width:340px;padding:7px 9px;border:1px solid var(--line);border-radius:6px;margin:6px 0}
.scroll{overflow:auto;max-height:620px;border:1px solid var(--line);border-radius:8px;background:#fff}
table.t{border-collapse:collapse;width:100%;font-size:13px}table.t th,table.t td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
table.t thead th{position:sticky;top:0;background:#eef3f8;z-index:1}table.t tr:hover td{background:#fafcff}
.unv{background:#fff1e0;color:var(--warn);border-radius:4px;padding:1px 6px;font-size:12px;font-weight:600}
code{background:#eef1f5;padding:1px 4px;border-radius:4px}footer{color:var(--mut);font-size:12px;max-width:1200px;margin:24px auto;padding:0 22px}
a{color:var(--acc)}
"""
    ledger_js = """
document.querySelectorAll('input.filter').forEach(function(inp){
  inp.addEventListener('input',function(){
    var q=inp.value.toLowerCase();
    var t=inp.parentElement.querySelector('table');
    if(!t)return;
    t.querySelectorAll('tbody tr').forEach(function(tr){
      tr.style.display=tr.textContent.toLowerCase().indexOf(q)>-1?'':'none';
    });
  });
});
"""
    OUT_HTML.mkdir(parents=True, exist_ok=True)
    (OUT_HTML / "ledger.css").write_text(ledger_css.lstrip(), encoding="utf-8")
    (OUT_HTML / "ledger.js").write_text(ledger_js.lstrip(), encoding="utf-8")
    pages = {
        "index.html": ("X3 Ledger — overview", "index.html", idx_body),
        "results.html": ("Results feed", "results.html", res_body),
        "prices.html": ("Lines & price store", "prices.html", prices_body),
        "depth.html": ("Replacement depth", "depth.html", dep_body),
        "governance.html": ("Demotion gate, signal vs staking, correlation", "governance.html", gov_body),
    }
    for fname, (title, active, body) in pages.items():
        (OUT_HTML / fname).write_text(page(title, active, body), encoding="utf-8")
    print("built ledger:", fin_n, "results;", len(ln_rows), "lines;", len(dp_rows), "depth rows;",
          len(pr_rows), "price rows")
    print("correlations:", [(c[0], c[1], c[2]) for c in corr_rows])


if __name__ == "__main__":
    main()
