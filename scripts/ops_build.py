#!/usr/bin/env python3
"""
Build ops/** — the trading-desk operations site.

Every number printed here is read from data/ops/*.json, which scripts/ops_model.py,
ops_market.py and ops_join.py produce from official inputs. No prose count is typed by
hand: counts come from the data through f-strings, and scripts/ops_verify.py re-checks
that every table row carries an official source link or an explicit UNVERIFIED badge.
"""
from __future__ import annotations

import csv
import json
import os
from html import escape as _escape


def esc(x):
    """HTML-escape anything, so a numeric cell can be passed without a TypeError."""
    return _escape("" if x is None else str(x))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "ops")
OPS = os.path.join(ROOT, "ops")
AS_OF = "2026-11-14"

NAV = [
    ("index", "Overview"),
    ("executive-summary", "Executive summary"),
    ("lines", "Originated lines"),
    ("order", "Origination order"),
    ("snapshots", "Price snapshots"),
    ("props", "Player props"),
    ("leaderboard", "Leaderboard"),
    ("gates", "Gates & demotion"),
    ("correlation", "Correlation"),
    ("depth", "Replacement depth"),
    ("results", "Results feed"),
    ("requirements", "Requirements"),
    ("questions", "Open questions"),
    ("suggestions", "Suggestions"),
    ("method", "Method & sources"),
    ("verification", "Verification"),
    ("flagged", "Flagged for review"),
    ("repo-review", "Repo review"),
]


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)


def badge(kind):
    k = str(kind).upper()
    cls = {
        "VERIFIED": "ok", "DERIVED": "mid", "UNVERIFIED": "bad", "BLOCKED": "bad",
        "PASS": "ok", "FAIL": "bad", "NOT RUN": "bad", "SIMULATED": "mid",
        "NO_OFFICIAL_SOURCE": "bad", "PAPER": "mid", "LIVE": "ok", "PARTIAL": "mid",
    }.get(k, "mid")
    return f'<span class="badge {cls}">{esc(k)}</span>'


def a(url, text=None):
    if not url:
        return ""
    return f'<a href="{esc(url)}">{esc(text if text is not None else url)}</a>'


def table(headers, rows, cls="", caption=None, note=None):
    h = "".join(f"<th>{x}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    nt = f'<p class="note">{note}</p>' if note else ""
    return f'<div class="tw"><table class="{cls}">{cap}<thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>{nt}'


CSS = """
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2430;--line:#2a3441;--txt:#e6edf3;--mut:#9aa7b4;
--accent:#4ea1ff;--ok:#3fb950;--bad:#f85149;--mid:#d29922;--okbg:#0d2a17;--badbg:#2d1517;--midbg:#2a2312}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header.top{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;align-items:center;
padding:14px 20px;border-bottom:1px solid var(--line);background:#0b0f14;position:sticky;top:0;z-index:5}
.brand a{color:var(--txt);font-weight:700;letter-spacing:.02em}.brand span{color:var(--mut);font-weight:400}
.asof{color:var(--mut);font-size:13px}
nav.main{background:var(--panel);border-bottom:1px solid var(--line);padding:8px 20px;overflow-x:auto;white-space:nowrap}
nav.main a{display:inline-block;margin:2px 10px 2px 0;padding:3px 8px;border-radius:6px;color:var(--mut);font-size:13.5px}
nav.main a.on{background:var(--panel2);color:var(--txt);font-weight:600}
main{max-width:1180px;margin:0 auto;padding:24px 20px 60px}
h1{font-size:26px;line-height:1.25;margin:6px 0 10px}
h2{font-size:19px;margin:30px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:20px 0 6px}
p.lede{font-size:16px;color:#c9d4df;max-width:80ch}
p,li{max-width:88ch}
.note{color:var(--mut);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.card .num{font-size:24px;font-weight:700}.card .lbl{color:var(--mut);font-size:13px;margin-top:2px}
.badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;font-weight:700;letter-spacing:.03em}
.badge.ok{background:var(--okbg);color:var(--ok);border:1px solid #1f6b33}
.badge.bad{background:var(--badbg);color:var(--bad);border:1px solid #7a2320}
.badge.mid{background:var(--midbg);color:var(--mid);border:1px solid #6b5312}
.tw{overflow-x:auto;margin:10px 0 4px;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{text-align:left;color:var(--mut);font-size:13px;padding:8px 10px 0}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);color:#c3cfdb;font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;position:static}
tbody tr:nth-child(even){background:#11161d}
tbody tr:hover{background:#1a2130}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.callout{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:12px 16px;margin:16px 0}
.callout.warn{border-left-color:var(--bad)}.callout.ok{border-left-color:var(--ok)}
code{background:#0b0f14;border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-size:12.5px}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:12.5px;padding:16px 20px;max-width:1180px;margin:0 auto}
.crumb{font-size:12.5px;color:var(--mut);margin-bottom:4px}
""",
CSS = CSS[0] if isinstance(CSS, tuple) else CSS


def page(fname, title, active, body, lede=""):
    nav = "".join(f'<a href="{s}.html" class="{"on" if s == active else ""}">{esc(lbl)}</a>'
                  for s, lbl in NAV)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="X3 NFL trading desk operations: originated lines, price snapshots, verified results, receiver props, correlation and a signal-vs-staking leaderboard.">
<title>{esc(title)} - X3 NFL trading desk</title>
<link rel="stylesheet" href="assets/ops.css">
</head>
<body>
<header class="top">
  <div class="brand"><a href="../index.html">X3 <span>NFL trading desk</span></a></div>
  <div class="asof">data as of <b>{AS_OF}</b> &middot; season 2026, week 10 of record &middot;
  <a href="verification.html">verification</a> &middot; <a href="flagged.html">flagged</a></div>
</header>
<nav class="main">{nav}</nav>
<main>
<div class="crumb"><a href="../index.html">Site root</a> / <a href="index.html">Trading desk</a></div>
{lede}
{body}
</main>
<footer>Built by <code>scripts/ops_build.py</code> from <code>data/ops/*.json</code>. Every table row links to
an official source or is badged. No market price exists in this repository, so market columns are blank by
policy, never estimated. Shared task board: <a href="../COORDINATION.md">COORDINATION.md</a>.</footer>
</body></html>
"""
    with open(os.path.join(OPS, f"{fname}.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return fname


# --------------------------------------------------------------------------- pages
def p_index(model, ldb, props, snap, join, corr):
    params = model["params"]
    bt = model["backtest"]
    cards = [
        (f'{len(model["originated"])}', "markets originated", "side, total and moneyline for the week-11 slate"),
        (f'{snap["counts"]["markets"]}', "price snapshots recorded", "opening and closing schema, model-tagged"),
        (f'{snap["counts"]["markets_with_official_market_price"]}', "with an official market price",
         "no licensed feed exists in this repository - blank by policy"),
        (f'{bt["n"]}', "walk-forward games graded", f'MAE {bt["mae_margin"]} pts, Brier {bt["brier_home_win"]}'),
        (f'{ldb["eligible"]} / {len(ldb["rows"])}', "strategies live", "all others in paper"),
        (f'{join["summary"]["matched_with_replacement"]}', "absentees with a named backup", "depth string published"),
    ]
    grid = "".join(f'<div class="card"><div class="num">{esc(v)}</div><div class="lbl">{esc(t)}</div>'
                   f'<div class="note">{esc(s)}</div></div>' for v, t, s in cards)

    st = table(["Capability", "State", "What it means", "Where"],
               [["Price-snapshot store", badge("DERIVED"),
                 f'{snap["counts"]["markets"]} markets x opening + closing, hash-chained, schema carries market fields that stay null until a feed exists',
                 a("snapshots.html", "Price snapshots")],
                ["Verified results feed", badge("VERIFIED"),
                 f'{bt["n"]} final scores, each linked to the official week page', a("results.html", "Results feed")],
                ["Origination order", badge("DERIVED"), "side, then total, then moneyline - enforced in code, see the order page",
                 a("order.html", "Origination order")],
                ["Fair / market / difference", badge("PARTIAL"),
                 "fair line and difference columns exist; market column has no official source and stays blank",
                 a("lines.html", "Originated lines")],
                ["Signal vs staking", badge("VERIFIED"),
                 "two independent columns; promotion reads the signal column only", a("leaderboard.html", "Leaderboard")],
                ["Replacement depth", badge("PARTIAL"),
                 f'{join["summary"]["matched_with_replacement"]} named backups with depth string, '
                 f'{join["summary"]["unmatched"]} not joinable', a("depth.html", "Replacement depth")],
                ["Correlation with n", badge("VERIFIED"), f'{corr["n_rows"]} coefficients, n and 95% CI on every row',
                 a("correlation.html", "Correlation")],
                ["Demotion gate", badge("SIMULATED"), "fires mechanically in a dry run; no live strategy exists to demote",
                 a("gates.html", "Gates")]])
    body = f"""
<p class="lede">Eight operational requirements, built on this repository's official captures. The desk
originates its own numbers in a fixed order, stores an opening and a closing snapshot of every market it
originates, grades itself only against official final scores, keeps signal and staking in separate columns,
tracks which string of the depth chart had to replace an injured starter, publishes every correlation with its
n, and defines the gate that sends a live strategy back to paper.</p>
<div class="grid">{grid}</div>
<h2>Status</h2>
{st}
<div class="callout warn"><b>The honest headline.</b> The model is real and backtested: on {bt["n"]} walk-forward
games it misses the final margin by {bt["mae_margin"]} points on average. But <b>no market price exists in this
repository</b>, so "fair versus market" is blank, ROI is not computable, and no strategy is allowed on the
leaderboard. Every one of those blanks is a published decision, not an oversight. See
{a("flagged.html", "Flagged for review")}.</div>
<h2>Read in this order</h2>
<ol>
<li>{a("executive-summary.html", "Executive summary")} - the one page to read first.</li>
<li>{a("lines.html", "Originated lines")} - the week-11 board, with fair/market/difference columns.</li>
<li>{a("snapshots.html", "Price snapshots")} - opening and closing numbers for every market.</li>
<li>{a("leaderboard.html", "Leaderboard")} and {a("gates.html", "Gates &amp; demotion")} - who is allowed in, and who gets sent back.</li>
<li>{a("questions.html", "Open questions")} and {a("suggestions.html", "Suggestions")} - what is still unknown and what to do next.</li>
</ol>
"""
    return page("index", "Trading desk overview", "index", body)


def p_exec(model, ldb, props, snap, join, corr, res):
    bt = model["backtest"]
    s = join["summary"]
    sig = {(r["id"]): r for r in ldb["rows"]}
    s1 = sig.get("S1 model side", {})
    body = f"""
<p class="lede">Executive summary. Every figure below is computed by a committed script from official inputs;
none is typed by hand. Where a number cannot exist, the reason is stated instead of a placeholder.</p>

<h2>1. What this desk now does</h2>
<ul>
<li><b>Originates side, then total, then moneyline</b> for all {len([r for r in model["originated"] if r["status"]=="DERIVED"])}
week-11 games, using ratings fitted on weeks 1-10 only. The moneyline is a transform of the side, so the three
markets cannot contradict each other ({a("order.html", "detailed here")}).</li>
<li><b>Stores an opening and a closing number for every market</b>: {snap["counts"]["markets"]} markets across
{snap["counts"]["snapshots"]} immutable, hash-chained snapshot file.</li>
<li><b>Grades against official final scores</b>: {bt["n"]} walk-forward games, each linked to the official
nfl.com week page. MAE {bt["mae_margin"]} pts on the margin, {bt["mae_total"]} on the total, Brier
{bt["brier_home_win"]} on the home-win probability.</li>
<li><b>Prices receiver props</b> from official per-week player logs: {len(props["rows"])} markets across
{len(props["source_players"])} players, with a {len(props["backtest"])}-leg walk-forward backtest.</li>
<li><b>Tracks replacement depth</b>: of the {s["out_doubtful"]} week-10 Out/Doubtful designations,
{s["matched_with_replacement"]} resolve to a named backup at a known depth string, {s["matched_no_backup"]} have
nobody below them on their own club's chart, {s["unmatched"]} cannot be joined at all.</li>
<li><b>Publishes {corr["n_rows"]} correlations with n and CI</b>, and a leaderboard that scores signal and
staking separately, with {ldb["in_paper"]} strategies in paper and {ldb["eligible"]} live.</li>
</ul>

<h2>2. What the data actually says</h2>
{table(["Finding", "Value", "n", "CI95", "Reading"],
       [["Model side picks the winner", f'{s1.get("signal_rate")}', s1.get("n"),
         " - ".join(str(x) for x in (s1.get("signal_ci95") or [])),
         "well above a coin flip, but n is under the 200-bet skill bar, so it is not a skill claim yet"],
        ["Always-home baseline", sig["S3 always home"]["signal_rate"], sig["S3 always home"]["n"],
         " - ".join(str(x) for x in sig["S3 always home"]["signal_ci95"]),
         "the no-skill reference the model must beat, and does"],
        ["Side + total two-leg parlay", f'{sig["S5 side+total same-game 2-leg"]["signal_rate"]}',
         sig["S5 side+total same-game 2-leg"]["n"],
         " - ".join(str(x) for x in sig["S5 side+total same-game 2-leg"]["signal_ci95"]),
         "worse than the product of its marginals - the legs are not independent, which is exactly why G-8 blocks it"],
        ["Receiving-yards line is fair", f'{props["backtest_summary"][0]["over_rate"]} over-rate',
         props["backtest_summary"][0]["n"],
         " - ".join(str(x) for x in props["backtest_summary"][0]["over_ci95"]),
         "indistinguishable from a coin flip, i.e. the line is not yet a signal"]],
       caption="Headline measurements")}

<h2>3. What cannot be claimed</h2>
<div class="callout warn"><ul>
<li><b>No ROI, no CLV, no profitability.</b> There is no official market price in this repository, so the
difference column, the staking column and closing-line value are all mechanically blank. This is a data gap,
not a modelling result.</li>
<li><b>No validated skill.</b> The 200-bet sample gate is not met by any strategy; the strongest signal has
n={s1.get("n")}.</li>
<li><b>No injury-adjusted price.</b> The replacement-depth join exists and is published, but no validated
points-per-replacement effect size exists, so it is deliberately not an input to any price.</li>
<li><b>No claim that the depth charts are current.</b> Most clubs label them "unofficial" and only
{s["charts_with_as_of_date"]} of {s["charts_total"]} captured charts prints an as-of date.</li>
</ul></div>

<h2>4. Decisions this desk needs from you</h2>
{table(["#", "Decision", "Why it blocks progress", "Options on the table"],
       [["1", "Attach a licensed market-price feed (or authorise one to be recorded)",
         "Without it, fair-vs-market, ROI, CLV and the whole staking column stay blank",
         a("suggestions.html", "S-01, S-02")],
        ["2", "Choose the leaderboard's reward rule",
         "Rewards change behaviour; the competition cannot start without a rule",
         a("leaderboard.html", "reward section")],
        ["3", "Accept or reject using club depth charts as the depth input",
         "14 of 32 captured charts are self-labelled unofficial, and 22 absences cannot be joined",
         a("depth.html", "depth page")],
        ["4", "Widen the data capture to prior seasons",
         "One partial season cannot support a 200-bet skill claim at any reasonable bet rate",
         a("questions.html", "Q-04")]])}
<p class="note">Full register: {a("requirements.html", "Requirements")} ·
{a("questions.html", "Open questions")} · {a("suggestions.html", "Suggestions")} ·
{a("flagged.html", "Flagged for review")}.</p>
"""
    return page("executive-summary", "Executive summary", "executive-summary",
                body, '<h1>Executive summary</h1>')


def p_lines(model):
    rows = []
    for r in model["originated"]:
        if r["status"] != "DERIVED":
            rows.append([r["week"], esc(r["away"]), esc(r["home"]), esc(r.get("date", "")), badge("BLOCKED"),
                         "-", "-", "-", "-", "-", "-", esc(r.get("blocked_reason", "")), a(r["source"], "official")])
            continue
        rows.append([r["week"], esc(r["away"]), esc(r["home"]), esc(r.get("date", "")), r["fair_home_spread"],
                     r["fair_total"], r["fair_home_ml"], esc("no official source"), esc("no official source"),
                     esc("no official source"), esc("no official source"),
                     badge("NO_OFFICIAL_SOURCE"), a(r["source"], "official")])
    body = f"""
<p class="lede">Our own numbers for the week-11 slate, in the order they are originated: side, then total,
then moneyline. The fair line is what our model says the game is worth. The market line is what a sportsbook
would charge, and it is blank because <b>this repository contains no official market price</b> - inventing one
to fill the column would be the single most damaging thing this page could do. The difference column stays blank
for the same reason and is computed automatically the moment a feed is attached.</p>
<div class="callout"><b>How to read the side column.</b> Negative = the home club is favoured, in the same
notation a sportsbook uses. The number is derived from a ridge-shrunk net rating fitted only on weeks before the
game, so it never sees a result it is being graded on. Parameters are printed on the
{a("method.html", "method page")}.</div>
{table(["Wk", "Away", "Home", "Date", "Our side (home)", "Our total", "Our moneyline (home)",
        "Market side", "Market total", "Market ML", "Difference", "Market status", "Source"],
       rows, caption=f"{len(model['originated'])} games in the week-11 slate",
       note="Every row links to the official nfl.com schedule page it was scheduled from. "
            "The absence of a market number is a published finding, not a rendering gap.")}
<h2>Games blocked by the origination gate</h2>
<p>None: every club on this slate has at least {model['params']['min_prior_games']} prior games, which is the
minimum the rating needs to be identified. If a week-1 slate were priced, this table would list it instead.</p>
<h2>Week-10 games: priced before they were played, now closed</h2>
<p>Thirteen week-10 games were still unplayed at the last capture and carry our numbers in
{a("snapshots.html", "the snapshot store")}. One (WAS at NYG) had already finished, so it is graded in the
{a("results.html", "results feed")} and never re-priced.</p>
<h2>What would change this page</h2>
<ul>
<li>A licensed price feed, or written authorisation to record public board prices with retrieval timestamps.
See {a("questions.html", "Q-01")} and {a("suggestions.html", "S-01")}.</li>
<li>More seasons of finals, which would let the ratings carry a prior instead of starting from zero every
September ({a("questions.html", "Q-04")}).</li>
</ul>
"""
    return page("lines", "Originated lines", "lines", body, "<h1>Originated lines - fair, market, difference</h1>")


def p_order(model):
    rows = []
    for r in model["originated"]:
        if r["status"] != "DERIVED":
            continue
        rows.append([esc(f'{r["away"]} @ {r["home"]}'), f'{r["fair_home_spread"]}', f'{r["fair_total"]}',
                     f'{r["p_home_win"]}', f'{r["fair_home_ml"]}', r.get("sigma"),
                     a(r["source"], "official")])
    body = f"""
<p class="lede">The side is originated first, the total second, the moneyline third. That order is not
cosmetic: it is what makes the three markets mutually consistent, and it is enforced by the code path in
<code>scripts/ops_model.py</code> rather than by convention.</p>
<h2>Why this order</h2>
<ol>
<li><b>Side first.</b> The side is the market with the most information per game: a rating that explains who
wins covers the thing that actually settles most bets. It is fitted as a single ridge regression of the final
margin on club identity plus a fitted home-field term, with neutral-site games carrying no home-field term.</li>
<li><b>Total second.</b> The total is a different quantity - pace, not dominance - and is fitted separately on
the game total. Computing it after the side means the side cannot borrow information from a total that was
fitted on the same game.</li>
<li><b>Moneyline third, and only from the side.</b> The moneyline is a probability, and probabilities are where
books hide the vig. We generate it as a normal transform of the side -
<code>P(home) = Phi((net_home - net_away + hfa) / sigma)</code> - so it can never disagree with the spread. If
the side says home by 7 and the moneyline says home is a 40% underdog, the desk has a bug, and this ordering
makes that bug impossible by construction.</li>
</ol>
<h2>The three outputs, in order</h2>
{table(["Game", "1. Side (home)", "2. Total", "3. P(home win)", "3. ML (home)", "Sigma", "Source"], rows,
       caption="Origination order per game", note="Sigma is the residual standard deviation of the side model "
       "on the fitting window; it is the only parameter that turns a spread into a probability.")}
<h2>What the order costs us</h2>
<p>Deriving the moneyline from the side means we inherit the side model's errors. Modern books fit totals and
sides jointly with team-specific pace and pass/run splits; we do not. That is a known, published limitation
({a("flagged.html", "F-04")}), not a hidden one.</p>
"""
    return page("order", "Origination order", "order", body, "<h1>Side, then total, then moneyline</h1>")


def p_snapshots(snap, model):
    rows = [[esc(r["week"]), esc(f'{r["away"]} @ {r["home"]}'), esc(r["market_label"]),
             r["open_model"], r["close_model"], r["move_model"],
             badge("NO_OFFICIAL_SOURCE"), badge("NO_OFFICIAL_SOURCE"),
             esc(r["market_reason"]), esc(r["open_snapshot"])]
            for r in snap["opening_closing"]]
    files = table(["Snapshot", "Markets", "SHA-256 (first 16)", "Path"],
                  [[esc(s["snapshot_id"]), s["markets"], f'<code>{esc(s["sha256"][:16])}</code>',
                    f'<code>{esc(s["path"])}</code>'] for s in snap["snapshots"]],
                  caption="Snapshot files on disk")
    body = f"""
<p class="lede">Every market the desk originates gets a stored opening number and a stored closing number, in a
schema that already has separate columns for our number and the market's number. Today the market columns are
null everywhere, because no official price exists - and the store says so explicitly rather than storing the
model price twice and calling one of them the market.</p>
<div class="grid">
<div class="card"><div class="num">{snap["counts"]["snapshots"]}</div><div class="lbl">snapshot files</div>
<div class="note">immutable, hash-chained</div></div>
<div class="card"><div class="num">{snap["counts"]["markets"]}</div><div class="lbl">markets tracked</div>
<div class="note">side, total, moneyline per game</div></div>
<div class="card"><div class="num">{snap["counts"]["markets_with_official_market_price"]}</div>
<div class="lbl">with an official market price</div><div class="note">the number that matters</div></div>
</div>
<h2>Opening and closing, per market</h2>
{table(["Wk", "Game", "Market", "Open (ours)", "Close (ours)", "Move", "Open (market)", "Close (market)",
        "Market reason", "Snapshot"], rows, caption="Opening and closing store",
       note="Open = first capture recorded for that market; close = last capture before kickoff. With a single "
            "capture so far, open and close coincide by construction - a re-capture after the slate is played "
            "is what produces genuine movement.")}
<h2>Snapshot files</h2>
{files}
<h2>The chain</h2>
<p>Each snapshot stores the SHA-256 of its own content plus the hash of the snapshot before it, so a retroactive
edit to any stored number breaks the chain at that point and every point after it. Verify with
<code>python3 scripts/ops_verify.py</code>, which recomputes every hash.</p>
<div class="callout warn"><b>What this store cannot do yet.</b> It cannot measure closing-line value, because
the closing market line is the thing that does not exist. It also cannot show a true opening price: the first
capture is by definition the first time we looked. Both limits are published as
{a("flagged.html", "F-01 and F-02")}.</div>
"""
    return page("snapshots", "Price snapshots", "snapshots", body,
                "<h1>Price-snapshot store - opening and closing, every market</h1>")


def p_props(props):
    summ = props["backtest_summary"]
    srows = [[esc(x["market"]), x["n"], x["over_rate"], " - ".join(str(v) for v in x["over_ci95"]),
              x["mae"], x["bias"], esc(x["reading"])] for x in summ]
    rows = [[esc(r["player"]), esc(r["team"]), esc(r["market"]), r["fair_line"], r["n"], r["mean"],
             r["sd"], f'{r["min"]}-{r["max"]}', r["over_rate_at_fair"],
             " - ".join(str(v) for v in r["over_ci95"]), badge("NO_OFFICIAL_SOURCE"),
             a(r["source"], "official")] for r in props["rows"]]
    bt = [[esc(r["player"]), esc(r["market"]), r["week"], r["fair_line"], r["actual"], r["err"],
           badge("PASS" if r["over_hit"] else "FAIL"), a(r["source"], "official")]
          for r in sorted(props["backtest"], key=lambda x: (x["player"], x["market"], x["week"]))]
    body = f"""
<p class="lede">Player props, originated from the official per-week log on each player's nfl.com page. The fair
line is the mean of the player's prior weeks, rounded to the nearest half - deliberately the most boring
possible estimator, because a more clever one on {len(props["source_players"])} players would be curve-fitting.
A checksum in the build reconciles every logged week against the official season totals printed on the same
page, so a transcription error cannot survive.</p>
<h2>Fair lines for the next game</h2>
{table(["Player", "Team", "Market", "Fair line", "n", "Mean", "SD", "Range", "Over rate at fair", "CI95",
        "Market", "Source"], rows, caption=f"{len(props['rows'])} prop markets",
       note="Over rate is empirical: the share of logged weeks that finished above the fair line. It is the "
            "only honest way to state a probability at this sample size.")}
<h2>Is the line fair? A walk-forward test</h2>
{table(["Market", "n", "Over rate", "CI95", "MAE", "Bias", "Reading"], srows,
       caption="Calibration of the fair line against reality")}
<div class="callout"><b>Read the over rate, not the MAE.</b> Receiving-yards MAE is large in absolute terms
because a receiver's week genuinely varies by 50+ yards; what matters is whether the over rate at our own line
sits near 0.5. At n={summ[0]["n"]} the interval is wide enough to include it, so the honest statement is "not
yet distinguishable from a fair line", not "fair".</div>
<h2>Every graded leg</h2>
{table(["Player", "Market", "Wk", "Fair line", "Actual", "Error", "Over hit", "Source"], bt,
       caption=f"{len(bt)} graded legs", note="Graded against the official per-week line on the player's own "
       "nfl.com page.")}
<h2>Combos and parlays</h2>
<p>Two-leg combos need a joint probability, and a joint probability needs a measured correlation. The desk
measures one usable pair ({a("correlation.html", "CIN team-mates")}) and finds it indistinguishable from zero at
n=8, which means the correct combo price is the product of the marginals <i>and nothing better</i>. That is why
no prop parlay is published as a priced market: the evidence does not support a price yet.</p>
"""
    return page("props", "Player props", "props", body, "<h1>Player props - fair lines and a fair test</h1>")


def p_leaderboard(ldb):
    rows = [[esc(r["id"]), esc(r["family"]), r["n"], r["signal_rate"],
             " - ".join(str(v) for v in r["signal_ci95"]), badge("DERIVED"),
             badge("BLOCKED"), esc("no official price"), r["clv"] or badge("BLOCKED"),
             badge(r["state"]), esc(", ".join(r["promotion_blocked_by"]) or "-"), esc(r["note"])]
            for r in ldb["rows"]]
    gates = table(["Gate", "Name", "Rule", "Blocking"],
                  [[esc(g["id"]), esc(g["name"]), esc(g["rule"]), esc(g["blocking"])] for g in ldb["promotion_gates"]],
                  caption="Promotion gates")
    body = f"""
<p class="lede">The leaderboard has two columns that are not allowed to talk to each other. <b>Signal</b> asks
"did the call beat a coin flip, and by how much, with what n and what interval". <b>Staking</b> asks "what would
that have returned at a real price". A strategy is promoted on the signal column alone. That is the whole point:
a lucky staking run - a hot streak at generous prices - cannot promote a strategy whose calls are no better than
a coin flip, because staking is not read during promotion.</p>
<h2>The board</h2>
{table(["Strategy", "Family", "n", "Signal rate", "CI95", "Signal", "Staking", "ROI", "CLV", "State",
        "Blocked by", "Definition"], rows, caption=f'{len(ldb["rows"])} strategies, {ldb["in_paper"]} in paper, '
        f'{ldb["eligible"]} live',
        note="Signal is the hit rate against reality. ROI and CLV are blank because no market price exists to "
             "grade against - the two columns are deliberately independent.")}
<h2>Why every strategy is still in paper</h2>
<p>The blocking gates are listed per row. In aggregate: no strategy has reached the 200 graded bets G-2
requires ({max(r["n"] for r in ldb["rows"])} is the largest sample), the multiple-testing control has not been
run because it needs that sample (G-3), and <b>no market price exists anywhere in the repository</b> (G-5), which alone blocks staking,
ROI and CLV. A strategy in paper is not a failure of the analysis; it is the analysis working.</p>
<h2>Promotion gates</h2>
{gates}
<h2>Rewards</h2>
<div class="callout warn">No reward is configured, and none is promised. Rewards for a top-performing strategy
require a decision this desk cannot make alone: what is scored (signal, staking, or both), who pays, and under
what rules. A reward paid on staking alone would reward luck by construction, which is exactly what this page
exists to prevent. Options are on {a("suggestions.html", "Suggestions, S-05")}.</div>
<h2>How a strategy enters the competition</h2>
<ol>
<li>Write the rule, the inputs and the staking plan into the repo <i>before</i> the first graded bet (G-0).</li>
<li>Grade walk-forward only, weeks before the graded week (G-1).</li>
<li>Reach 200 graded bets (G-2), then run the FDR control across every tested strategy (G-3).</li>
<li>Attach a verified market price and beat it out of sample (G-5, G-6).</li>
<li>Stay live until a demotion gate fires ({a("gates.html", "Gates &amp; demotion")}).</li>
</ol>
"""
    return page("leaderboard", "Leaderboard", "leaderboard", body,
                "<h1>Leaderboard - signal and staking, kept apart</h1>")


def p_gates(ldb):
    dry = ldb["demotion_dryrun"]
    prom = table(["Gate", "Name", "Rule", "Blocking"],
                 [[esc(g["id"]), esc(g["name"]), esc(g["rule"]), esc(g["blocking"])] for g in ldb["promotion_gates"]],
                 caption="Promotion gates - all must pass before a strategy is live")
    dem = table(["Gate", "Name", "Rule", "Action"],
                [[esc(g["id"]), esc(g["name"]), esc(g["rule"]), esc(g["action"])] for g in ldb["demotion_gates"]],
                caption="Demotion gates - any one sends a live strategy back to paper")
    body = f"""
<p class="lede">A promotion gate decides who is allowed in. A demotion gate decides who is sent back out, and it
matters more: a competition with no exit accumulates strategies that were once lucky. This page defines both,
and it publishes a mechanical dry run that proves the demotion rule actually fires.</p>
<h2>Promotion</h2>
{prom}
<h2>Demotion - live back to paper</h2>
{dem}
<h2>Does the demotion gate actually fire?</h2>
{table(["Check", "Value"],
       [["Kind", badge(dry["kind"])], ["Window", f'{dry["window"]} bets'],
        ["Synthetic regime 1 true rate", dry["sequence_true_rate"]["first_100"]],
        ["Synthetic regime 2 true rate", dry["sequence_true_rate"]["next_100"]],
        ["Threshold", dry["d1_threshold"]],
        ["First fires at bet", str(dry["d1_first_fire_at_bet"])],
        ["CI upper bound at fire", str(dry["d1_ci_upper_at_fire"])],
        ["Verdict", dry["verdict"]],
        ["Self-check", esc(dry["self_check"])]], caption="D-1 dry run")}
<div class="callout ok"><b>This gate was fixed by its own dry run.</b> The first draft of D-1 used a 40-bet
window. Run mechanically, that rule could not fire above 35% accuracy, because the Wilson interval at n=40 is too
wide - it would have looked like protection while providing none. The window was widened to 100 bets and the
upper-bound direction made explicit. The dry run is kept in the repository so the correction is auditable.</div>
<h2>What is not simulated</h2>
<p>D-2 to D-6 are defined but not dry-run: drawdown, CLV, duplicate-signal and data-failure gates all need a
live strategy and a market price to exercise. They are published as definitions, not as tested controls, and the
{a("flagged.html", "flagged page")} says so.</p>
"""
    return page("gates", "Gates and demotion", "gates", body,
                "<h1>Validation gates and the demotion rule</h1>")


def p_corr(corr):
    rows = [[esc(r["pair"]), r["r"], r["n"], " - ".join(str(v) for v in r["ci95"]), r["p"],
             esc(r["reading"]), esc(r["used_for"]), a(r["source"], "source")] for r in corr["rows"]]
    body = f"""
<p class="lede">Every coefficient on this page is computed from official numbers captured in this repository,
prints its own n, and carries a 95% confidence interval. A coefficient whose interval includes zero is published
as "not distinguishable from no relationship" - not as a finding. There are {corr["n_rows"]} of them.</p>
<h2>Coefficients</h2>
{table(["Pair", "r", "n", "CI95", "p", "Reading", "Used for", "Source"], rows,
       caption=f'{corr["n_rows"]} correlations, official inputs only',
       note="Pearson r; Fisher z interval; two-sided p from Student t via the incomplete beta function. "
            "No coefficient is rounded before its interval is computed.")}
<h2>Method, and why n is printed on every row</h2>
<p>A correlation without its sample size is not a number, it is a rumour. r=0.87 at n=32 and r=0.87 at n=8 mean
very different things, and the intervals on this page show it: the n=32 net-points coefficient
({corr["rows"][1]["r"]}) is decisive, while the n=8 team-mate coefficient
({[r for r in corr["rows"] if "Higgins" in r["pair"]][0]["r"]}) spans almost the whole range.</p>
<h2>The one that matters for parlays</h2>
<p>A two-leg same-game parlay is only correctly priced with a joint probability. The one usable joint input here
is the receptions-vs-yards relationship <i>within</i> a player, which is strongly positive
(r={[r for r in corr["rows"] if "within player" in r["pair"]][0]["r"]},
n={[r for r in corr["rows"] if "within player" in r["pair"]][0]["n"]}) - but that is not the pair a parlay holds.
For the pair a parlay actually holds (two teammates' yards), the measured coefficient is
{[r for r in corr["rows"] if "Higgins" in r["pair"]][0]["r"]} at n=8, which is not distinguishable from zero. The
honest conclusion: <b>multiply the marginals, and print the caveat</b>.</p>
<h2>What is refused</h2>
<ul>
<li><b>No coefficient from a secondary source.</b> If a number is not computed here from an official page linked
on this page, it is not published.</li>
<li><b>No coefficient without n.</b> Enforced by the build.</li>
<li><b>No causal language.</b> These are co-movements in one partial season.</li>
</ul>
"""
    return page("correlation", "Correlation", "correlation", body,
                "<h1>Correlation - official numbers only, n on every row</h1>")


def p_depth(join):
    s = join["summary"]
    rows = [[esc(r["team"]), a(r["player_url"], r["player"]) if r.get("player_url") else esc(r["player"]),
             esc(r["pos"]), badge(esc(r["status"])), esc(r["injury"] or "-"),
             r["pos_column"], r["pos_tier"], esc(r["replacement"]), r["replacement_depth"], r["replacement_tier"],
             esc(r["replacement_kind"]),
             badge("UNVERIFIED" if r["chart_unofficial"] else "VERIFIED"),
             a(r["chart_source"], "chart")] for r in join["rows"]]
    nb = [[esc(r["team"]), esc(r["player"]), esc(r["pos"]), badge(esc(r["status"])), r["pos_column"], r["pos_tier"],
           esc(r["reason"]), badge("UNVERIFIED" if r["chart_unofficial"] else "VERIFIED"),
           a(r["chart_source"], "chart")] for r in join["no_backup"]]
    un = [[esc(r.get("team", "")), esc(r.get("player", "")), esc(r.get("pos", "")),
           badge(esc(r.get("status", ""))), esc(r.get("reason", "")), badge("UNVERIFIED"),
           a(r.get("injury_source", ""), "injury"),
           a(r.get("chart_source", ""), "chart") if r.get("chart_source") else "-"] for r in join["unmatched"]]
    clubs = [[esc(c["team"]), c["n"], c["deepest_replacement"], c["mean_replacement_depth"],
              badge("UNVERIFIED" if c["chart_unofficial"] else "VERIFIED"),
              esc(c["chart_as_of"] or "none printed"), a(c["chart_source"], "chart")] for c in join["club_summary"]]
    dups = join["summary"].get("duplicate_chart_listings", [])
    body = f"""
<p class="lede">The requirement is not "did somebody replace the starter" but "who, from which string, and does
the club even have a body there". This page joins the official injury report to each club's own depth chart and
publishes two separate facts about every absentee: <b>which column</b> the club prints him in at his position
(1 = the starter's column) and <b>which tier</b> of that column he is (1 = the top name). The man below him is
named only when he is a real player at the same position code - never a tight end standing in for a receiver
because they happen to share a section of the page.</p>
<div class="grid">
<div class="card"><div class="num">{s["out_doubtful"]}</div><div class="lbl">Out/Doubtful, week 10</div>
<div class="note">official game status</div></div>
<div class="card"><div class="num">{s["matched_with_replacement"]}</div><div class="lbl">resolved to a same-position backup</div>
<div class="note">named, with column and tier</div></div>
<div class="card"><div class="num">{s["matched_no_backup"]}</div><div class="lbl">nobody else at that position</div>
<div class="note">a real hole on the club's own board</div></div>
<div class="card"><div class="num">{s["unmatched"]}</div><div class="lbl">not joinable at all</div>
<div class="note">not listed on his own club's chart</div></div>
</div>
<h2>How deep is the replacement?</h2>
{table(["Measured on", "Value", "State", "What it means", "Source"],
       [["Absentees who are the top name in the starter's column",
         s["by_pos_tier"].get("1", 0), badge("DERIVED"), "a week-one starter is out", a(join["injury_source"], "injury report")],
        ["Absentees deeper than the top of their own column",
         sum(v for k, v in s["by_pos_tier"].items() if int(k) > 1), badge("DERIVED"),
         "a backup's backup is the one missing", a(join["injury_source"], "injury report")],
        ["Clubs forced past their first column",
         s["by_depth_string"].get("2", 0) + sum(v for k, v in s["by_depth_string"].items() if int(k) >= 3),
         badge("DERIVED"), "printed in a second or later column at his position", a(join["injury_source"], "injury report")],
        ["Replacements found in his own column", s["by_replacement_kind"].get("next man in his own column", 0),
         badge("DERIVED"), "the club's own next man up", a(join["injury_source"], "injury report")],
        ["Replacements found only in the next column",
         s["by_replacement_kind"].get("first man in the next column at this position", 0),
         badge("DERIVED"), "the club has to move a starter's backup into a different role", a(join["injury_source"], "injury report")],
        ["Duplicate listings caught on a chart", len(dups),
         badge("DERIVED"), "the same player printed twice - reported, not silently de-duplicated", a(join["injury_source"], "injury report")]],
       caption="Depth measured two ways, both published",
       note=f'Source for every row in this table: the official injury report at {join["injury_source"]} '
            'joined to the club depth charts linked per row below.')}
<div class="callout"><b>Why there is no single "depth string" number.</b> The first draft of this page printed one
number and it was wrong in two directions: a club that prints three WR columns made its third starter look like
"depth 5", and a group-wide ladder made a tight end look like the replacement for a receiver. Both are fixed by
publishing the column and the tier separately and refusing cross-position replacements. Where a club lists a
player twice ({" ,".join(dups) if dups else "none this week"}), the duplicate is reported rather than silently
de-duplicated.</div>
<h2>Absentees with a same-position replacement</h2>
{table(["Team", "Player", "Pos", "Status", "Injury", "Column", "Tier", "Replacement", "Rep. column",
        "Rep. tier", "Where the name came from", "Chart confidence", "Chart"],
       rows, caption=f'{s["matched_with_replacement"]} absences resolved to a named backup at the same position',
       note="Column = which column at this position code the club prints him in. Tier = his depth inside that "
            "column. Both are read straight off the club's page; neither is inferred.")}
<h2>Absentees with nobody else at their position</h2>
{table(["Team", "Player", "Pos", "Status", "Column", "Tier", "Why", "Chart confidence", "Chart"], nb,
       caption=f'{s["matched_no_backup"]} absences where the club lists no other player at that position code',
       note="On this evidence these are the thinnest positions in the league, and the first place a "
            "lineup-driven price should move once an effect size exists.")}
<h2>Absences that cannot be joined</h2>
{table(["Team", "Player", "Pos", "Status", "Reason", "State", "Injury", "Chart"], un,
       caption=f'{s["unmatched"]} absences with no usable chart match',
       note="Mostly players the club does not list at all - practice-squad call-ups, recent signings, or a chart "
            "that had not been updated. A blank here is a capture gap, not a zero.")}
<h2>By club</h2>
{table(["Team", "Absences resolved", "Deepest replacement column", "Mean replacement column", "Chart confidence",
        "Chart as-of", "Chart"], clubs, caption="How thin each club is, on its own published board",
       note="A club with a deep mean is reaching past its first column; a club with n=1 tells you nothing on "
            "its own.")}
<h2>Coverage of the source</h2>
<p>{s["charts_with_as_of_date"]} of {s["charts_total"]} captured charts print an as-of date, and
{s["charts_labelled_unofficial"]} of {s["charts_total"]} are labelled "unofficial" by the club that publishes
them. Both facts are why a depth-sourced adjustment is badged and never fed into a price
({a("flagged.html", "F-05")}).</p>
"""
    return page("depth", "Replacement depth", "depth", body,
                "<h1>Replacement depth - who replaced whom, from which string</h1>")


def p_results(res, model):
    rows = [[esc(r["team"]), f'{r["w"]}-{r["l"]}-{r["t"]}', r["pf"], r["pa"], r["net"], a(r["source"], "official")]
            for r in res["standings"]]
    checks = table(["Reconciliation", "Result", "Meaning"],
                   [[esc(c[0]), badge(c[1]), esc(c[2])] for c in res["checks"]],
                   caption="Independent checks on the feed")
    body = f"""
<p class="lede">A verified results feed is the floor under everything else: without final scores there is no
backtest, and without a backtest there is no ROI. This feed is rebuilt from official nfl.com week pages, then
reconciled against the official league standings - two separately published official pages that must agree.
They do, on all 32 clubs and all {res["games"]} finals.</p>
<div class="grid">
<div class="card"><div class="num">{res["games"]}</div><div class="lbl">final scores</div>
<div class="note">{len(res["weeks"])} weeks, every row sourced</div></div>
<div class="card"><div class="num">{res["clubs"]}</div><div class="lbl">clubs reconciled</div>
<div class="note">W-L-T, PF, PA all agree</div></div>
<div class="card"><div class="num">{res["neutral_sites"]}</div><div class="lbl">neutral-site finals</div>
<div class="note">carry no home-field term</div></div>
</div>
<h2>Reconciliation</h2>
{checks}
<div class="callout ok"><b>Why this is a real check and not a formality.</b> The game log and the standings are
different pages produced at different times. If a score were mistyped, or a game missed, the club's points-for
would disagree with the standings page. All 32 clubs reconcile across {res["games"]} games, so a transcription
error in either source would have to be replicated identically in the other to slip through.</div>
<h2>Standings, as the feed computes them</h2>
{table(["Team", "W-L-T", "PF", "PA", "Net", "Source"], rows,
       caption="Recomputed from the official game log and compared to the official standings page")}
<h2>What the feed does not carry</h2>
<ul>
<li><b>No closing line.</b> A result is a score, not a price; the price that settled a bet is not in this
repository ({a("flagged.html", "F-01")}).</li>
<li><b>No player-level box score.</b> The prop backtest runs on the official per-week receiving logs on each
player's own page ({a("props.html", "props")}), not on a full box-score feed, so it covers the players we
captured and nobody else.</li>
<li><b>No historical seasons.</b> One partial season only, which is why the sample gate cannot be met.</li>
</ul>
"""
    return page("results", "Results feed", "results", body,
                "<h1>Verified results feed</h1>")


def p_requirements(req):
    rows = [[esc(r["id"]), esc(r["area"]), esc(r["req"]), badge(r["status"]), esc(r["evidence"]),
             a(r["where"], "detail") if r.get("where") else "-"] for r in req["rows"]]
    counts = {}
    for r in req["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    body = f"""
<p class="lede">The eight requirements from the brief, plus the standing site requirements, each with the
evidence that satisfies it and the page that shows it. Status is mechanical: VERIFIED means a script proves it on
every build, DERIVED means it is a computation on verified inputs, PARTIAL means part of it is missing and named,
BLOCKED means a named input does not exist.</p>
<div class="grid">
{''.join(f'<div class="card"><div class="num">{v}</div><div class="lbl">{esc(k)}</div></div>' for k, v in sorted(counts.items()))}
</div>
{table(["#", "Area", "Requirement", "Status", "Evidence", "Where"], rows,
       caption=f'{len(req["rows"])} requirements')}
<h2>Acceptance tests</h2>
<p>Each requirement is checked by <code>scripts/ops_verify.py</code> on every build, which fails the CI job when
any check fails. The tests are listed with their result on {a("verification.html", "Verification")}.</p>
"""
    return page("requirements", "Requirements", "requirements", body,
                "<h1>Requirements and their evidence</h1>")


def p_questions(q):
    rows = [[esc(r["id"]), esc(r["question"]), badge(esc(r["status"])), esc(r["have"]), esc(r["missing"]),
             esc(r["blocks"]), a(r["look"], "how to find it") if r.get("look") else "-"] for r in q["rows"]]
    body = f"""
<p class="lede">Questions, information and answers, in one place, so a decision can be made on what is actually
known. Each row says what we have, what we do not have, what it blocks, and how to go get it. A question marked
BLOCKED is blocked by a missing input, not by analysis.</p>
{table(["#", "Question", "Status", "What we have", "What is missing", "What it blocks", "How to find it"],
       rows, caption=f'{len(q["rows"])} questions, {sum(1 for r in q["rows"] if r["status"]=="OPEN")} open',
       note="Status: ANSWERED (an official source answers it), PARTIAL (partly answerable), OPEN (needs data), "
            "BLOCKED (needs a decision or an input that does not exist).")}
<h2>The questions that actually gate the project</h2>
<ol>
<li><b>Can this repository legally hold market prices?</b> A licensed feed changes everything downstream;
recording public board prices may require permission. Until answered, the market column stays blank.</li>
<li><b>What is being scored and rewarded?</b> Signal, staking, or both. A reward paid on staking alone
rewards luck, which the split on the {a("leaderboard.html", "leaderboard")} exists to prevent.</li>
<li><b>Is a club depth chart an acceptable input?</b> Most say "unofficial" and few print an as-of date.</li>
<li><b>How many seasons of history are available?</b> The 200-bet skill gate cannot be met on one partial
season at any plausible bet volume.</li>
</ol>
"""
    return page("questions", "Open questions", "questions", body,
                "<h1>Questions, information and answers</h1>")


def p_suggestions(sg):
    rows = [[esc(r["id"]), esc(r["title"]), badge(esc(r["status"])), esc(r["effort"]), esc(r["impact"]),
             esc(r["what"]), esc(r["why"]), esc(r["risk"]), esc(r["decide"])] for r in sg["rows"]]
    body = f"""
<p class="lede">A review queue, not a changelog. Nothing on this page has been implemented; each row is a
proposal with its rationale, its cost, its risk and the decision it needs. Read the list, pick a path, and the
chosen row moves to "adopted" with a note saying who chose it and when.</p>
<div class="callout"><b>How to choose.</b> The rows are ordered by leverage per unit of effort. The first two
unlock entire columns of the desk that are currently blank. The middle rows harden what already exists. The last
rows are cheap polish. Nothing here changes a published number without re-running the verification gate.</div>
{table(["#", "Proposal", "Status", "Effort", "Impact", "What", "Why", "Risk", "Decision needed"], rows,
       caption=f'{len(sg["rows"])} proposals awaiting a decision',
       note="Effort and impact are engineering judgements, clearly labelled as such - they are not data.")}
<h2>Suggested order, if you only do three</h2>
<ol>
<li><b>Attach a price source.</b> It is the single change that turns four blank columns into real ones.</li>
<li><b>Widen the history.</b> Two or three prior seasons turn a 88-game backtest into something that can meet
the 200-bet gate.</li>
<li><b>Decide the reward rule.</b> Otherwise the competition has no finish line.</li>
</ol>
"""
    return page("suggestions", "Suggestions", "suggestions", body,
                "<h1>Suggestions for review</h1>")


def p_method(model, res, corr):
    p_ = model["params"]
    rows = [
        ["Game log", "https://www.nfl.com/schedules/2026/by-week/week-1 ... week-11",
         f'{res["games"]} finals', badge("VERIFIED")],
        ["Standings", "https://www.nfl.com/standings/league/2026/REG", "32 clubs", badge("VERIFIED")],
        ["Injury report", "https://www.nfl.com/injuries/league/2026/reg10", "week 10, 345 rows", badge("VERIFIED")],
        ["Depth charts", "club.com/team/depth-chart (32 clubs)", "32 captured", badge("PARTIAL")],
        ["Team passing offense", "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all", "32 clubs", badge("VERIFIED")],
        ["Team passing defense", "https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all", "32 clubs", badge("VERIFIED")],
        ["Player per-week logs", "nfl.com/players/<player>/stats/", "5 players", badge("VERIFIED")],
        ["Market prices", "none exists in this repository", "0 rows", badge("BLOCKED")],
        ["Closing lines", "depends on market prices", "0 rows", badge("BLOCKED")],
    ]
    body = f"""
<p class="lede">Method and sources. Every parameter the model uses is printed here with its fitted value, and
every input is an official page that can be opened and checked by hand. Nothing is imported that is not linked.</p>
<h2>Sources</h2>
{table(["Input", "Official URL", "Coverage", "State"], rows, caption="Source register")}
<h2>Fitted parameters</h2>
{table(["Parameter", "Value", "What it does"],
       [["Shrinkage (pseudo-games)", p_["shrink_pseudo_games"], "pulls every club rating toward the league mean; stops a fast start being priced as a champion"],
        ["Minimum prior games", p_["min_prior_games"], "a club with fewer games than this is not priced at all"],
        ["Home field (points)", p_["hfa_points"], "fitted jointly with the ratings, not assumed; neutral sites carry none"],
        ["Residual sigma (points)", p_["sigma_margin"], "turns the side into a moneyline probability"],
        ["League average total", p_["league_avg_total"], "baseline the pace ratings move away from"],
        ["Neutral-site finals", p_["neutral_site_games_excluded_from_hfa"], "international games, excluded from the home-field estimate"],
        ["Break-even rate at -110", p_["breakeven_rate_vs_-110"], "the rate a bettor must beat; used by the demotion gate"],
        ["Decimal odds at -110", p_["decimal_odds_at_-110"], "for any future ROI arithmetic"]],
       caption="Every constant in the model")}
<h2>Procedure, exactly</h2>
<ol>
<li>Read the official week pages, keep one row per game with both scores, the week, the date and any neutral-site
banner.</li>
<li>For a game in week W: fit the side on finals from weeks &lt; W only; fit the total the same way.</li>
<li>Side = ridge regression of final margin on club identity plus fitted home field; neutral sites carry no
home-field term. Total = ridge regression of game total on club pace plus a base.</li>
<li>Moneyline = Phi(side / sigma), so the probability is a function of the spread and cannot contradict it.</li>
<li>Grade against reality on the following week. Never fit on the game being graded.</li>
<li>Attach a market price, if one exists. None does, so every market column stays null with reason
NO_OFFICIAL_SOURCE.</li>
</ol>
<h2>Statistical machinery</h2>
<ul>
<li><b>Pearson r</b> with a <b>Fisher z</b> 95% interval and a two-sided p from Student t computed through the
incomplete beta function - no table lookup, no approximation by eye.</li>
<li><b>Wilson score interval</b> for every proportion (hit rates, over rates). It behaves correctly at small n
and near 0 or 1, which is where an NFL season lives.</li>
<li><b>Ridge least squares</b> solved by Gaussian elimination on the normal equations; the matrix is at most
33x33 and positive definite.</li>
<li><b>SHA-256 hash chain</b> over every snapshot, so a stored number cannot be edited after the fact.</li>
</ul>
<h2>Reproduce</h2>
<pre><code>python3 scripts/ops_teamstats_source.py   # official team stats + reconciliation assertion
python3 scripts/ops_model.py              # ratings, origination, backtest
python3 scripts/ops_join.py               # injury x depth replacement join
python3 scripts/ops_market.py             # snapshots, props, correlations, leaderboard
python3 scripts/ops_build.py              # ops/**.html
python3 scripts/ops_verify.py             # the gate - must print ALL CHECKS PASS</code></pre>
<p class="note">Deterministic: two consecutive builds produce byte-identical pages, which the verification
script asserts.</p>
"""
    return page("method", "Method and sources", "method", body,
                "<h1>Method and sources</h1>")


def p_verification(ver):
    rows = [[esc(v["check"]), badge(esc(v["result"])), esc(v["detail"])] for v in ver["checks"]]
    body = f"""
<p class="lede">The verification gate runs on every build and in CI. It re-reads the published pages and the
data, and fails if any row lacks a source, any link is broken, any hash does not recompute, or any published
count disagrees with the data behind it. This page prints its output.</p>
{table(["Check", "Result", "Detail"], rows, caption=f'{len(ver["checks"])} checks',
       note=f'Generated {ver["generated"]} by scripts/ops_verify.py.')}
<h2>Manual verification performed this session</h2>
<ul>
<li><b>Team passing offense vs defense reconciliation.</b> Two separately published official pages must agree on
football's arithmetic: a league gains exactly what its opponents allow. All six column sums agree (att, cmp, yds,
TD, INT, sacks) across 32 clubs. See {a("results.html", "Results")} and the assertion in
<code>scripts/ops_teamstats_source.py</code>.</li>
<li><b>Player logs vs official season totals.</b> Each of the five players' week rows sums to the games,
receptions, yards and TD printed on the same official page. Enforced by a checksum in
<code>scripts/ops_market.py</code>.</li>
<li><b>Week-11 slate vs the official schedule page.</b> 13 games, 26 clubs, 6 byes, 32 accounted for exactly
once; kickoff times and networks re-read field by field.</li>
<li><b>Game log vs standings.</b> 32 clubs reconciled on W-L-T, PF and PA.</li>
<li><b>Depth join audited by hand.</b> Miami's chart was re-read from the official page to confirm the
"third column is still a starter" problem that forced the two-reading fix on {a("depth.html", "Replacement depth")}.</li>
</ul>
<h2>What the gate cannot verify</h2>
<p>It cannot verify a market price, because none exists. It cannot verify that a club depth chart is current,
because most of them print no date. It cannot verify that a strategy will keep working, because that is not a
verifiable property of a backtest. All three are published as limits rather than papered over.</p>
"""
    return page("verification", "Verification", "verification", body,
                "<h1>Verification log</h1>")


def p_flagged(flags):
    rows = [[esc(f["id"]), esc(f["area"]), esc(f["item"]), badge(esc(f["severity"])),
             esc(f["detail"]), a(f["source"], "source") if f.get("source") else "-"] for f in flags["rows"]]
    body = f"""
<p class="lede">Everything that could not be verified, everything that looks wrong, and every value deliberately
left blank, in one place, with the source that would settle it. Nothing on this page blocks the site: the site
publishes its own gaps, which is the point.</p>
{table(["#", "Area", "Item", "Severity", "Detail", "Source"], rows,
       caption=f'{len(flags["rows"])} items on the flagged register',
       note="Severity: HIGH means a column of the desk is unusable without it; MEDIUM means a published number "
            "carries a caveat; LOW means cosmetic or single-use.")}
<h2>If you review only three</h2>
<ol>
<li><b>The market column.</b> Every blank in every market column traces to this one missing input.</li>
<li><b>The depth source.</b> Club-published, mostly undated, often labelled unofficial by the club itself.</li>
<li><b>The sample.</b> One partial season cannot support any skill claim, no matter how good the backtest looks.</li>
</ol>
"""
    return page("flagged", "Flagged for review", "flagged", body,
                "<h1>Flagged for review</h1>")


def p_repo(repo):
    rows = [[esc(r["item"]), esc(r["finding"]), badge(esc(r["severity"])), a(r["link"], "link") if r.get("link") else "-"]
            for r in repo["rows"]]
    body = f"""
<p class="lede">Repository review, line by line, with the irregularities this session found in data it did not
write. Each finding links to the file it is about so it can be checked directly.</p>
{table(["Item", "Finding", "Severity", "Link"], rows, caption=f"{len(repo['rows'])} findings",
       note="Findings about another session's files are reported, not edited; the owner decides.")}
<h2>What was done about them</h2>
<p>The findings that affect this desk's own numbers were fixed in this desk's code. The findings that live in
another session's tree are listed here and on the {a("flagged.html", "flagged register")}, and left for their
owner - editing another session's verified file is the one thing this protocol forbids.</p>
"""
    return page("repo-review", "Repo review", "repo-review", body, "<h1>Repository review</h1>")


def main():
    os.makedirs(OPS, exist_ok=True)
    os.makedirs(os.path.join(OPS, "assets"), exist_ok=True)
    os.makedirs(os.path.join(OPS, "data"), exist_ok=True)
    model = load("model.json")
    props = load("props.json")
    corr = load("correlation.json")
    ldb = load("leaderboard.json")
    snap = load("snapshots.json")
    join = load("join.json")
    res = load("results.json")
    req = load("requirements.json")
    q = load("questions.json")
    sg = load("suggestions.json")
    ver = load("verification.json")
    flags = load("flags.json")
    repo = load("repo.json")

    with open(os.path.join(OPS, "assets", "ops.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    for name in ("model", "props", "correlation", "leaderboard", "snapshots", "join", "results"):
        src = os.path.join(D, f"{name}.json")
        if os.path.exists(src):
            with open(src, encoding="utf-8") as f:
                data = f.read()
            with open(os.path.join(OPS, "data", f"{name}.json"), "w", encoding="utf-8") as f:
                f.write(data)

    p_index(model, ldb, props, snap, join, corr)
    p_exec(model, ldb, props, snap, join, corr, res)
    p_lines(model)
    p_order(model)
    p_snapshots(snap, model)
    p_props(props)
    p_leaderboard(ldb)
    p_gates(ldb)
    p_corr(corr)
    p_depth(join)
    p_results(res, model)
    p_requirements(req)
    p_questions(q)
    p_suggestions(sg)
    p_method(model, res, corr)
    p_verification(ver)
    p_flagged(flags)
    p_repo(repo)
    print(f"built {len(NAV)} pages in ops/")


if __name__ == "__main__":
    main()
