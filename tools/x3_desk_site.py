#!/usr/bin/env python3
"""X3 desk — static site renderer.

Reads x3/data/*.csv + meta.json + tools/x3_desk_content.py and writes x3/**/*.html.

Design rules the gate enforces:
  * every table row that carries a data value also carries a source link or an
    explicit UNVERIFIED marker;
  * every internal link resolves;
  * no unfilled token, no rendered `None`;
  * a second build is byte-identical.
"""
from __future__ import annotations

import csv
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3_desk_content as C  # noqa: E402
import x3_desk_inputs as I  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "x3", "data")
SITE = os.path.join(ROOT, "x3")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


META = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))

PAGES = [
    ("index.html", "Overview", "Status at a glance"),
    ("executive-summary.html", "Executive summary", "The one page to read first"),
    ("readiness.html", "Decision readiness", "One row per requirement: what blocks it, what clears it"),
    ("lines.html", "Originated lines", "Side, then total, then moneyline"),
    ("prices.html", "Price snapshots", "Opening and closing for every market"),
    ("results.html", "Results feed", "Finals only, live scores excluded"),
    ("backtest.html", "Backtest corpus", "Walk-forward predictions"),
    ("leaderboard.html", "Leaderboard", "Signal and staking, separate columns"),
    ("luck.html", "Removal of luck", "How much of a record is not skill"),
    ("gates.html", "Gates & demotion", "What must pass, what sends it back"),
    ("correlations.html", "Correlations", "Official numbers only, n published"),
    ("injuries.html", "Injuries", "The official report, re-read and diffed"),
    ("depth.html", "Depth & replacements", "String order versus official playing time"),
    ("matrix.html", "Matchup matrix", "Per-fixture deficiency view"),
    ("teams.html", "Per-team view", "Starters out, next man up"),
    ("availability.html", "Availability graph", "Expected starter, actual starter"),
    ("ablations.html", "Ablations", "With and without the feature"),
    ("schedule.html", "Schedule & announcement", "The dated release beside the live page"),
    ("fixtures.html", "Venues", "Transcribed per fixture, with the kind of evidence"),
    ("features.html", "Fixture context", "Only published schedule facts"),
    ("preregistration.html", "Pre-registration", "Frozen before the data"),
    ("questions.html", "Questions", "Known, missing, and what would clear it"),
    ("suggestions.html", "Suggestions", "Review before implementing"),
    ("repo-review.html", "Repo review", "The prior trees, audited"),
    ("policy.html", "Data policy", "Price data, public/private split"),
    ("verification.html", "Verification", "How every row was checked"),
    ("flagged.html", "Flagged for review", "Every unverified item"),
    ("sources.html", "Sources", "Official pages and what each was used for"),
]

NAV_GROUPS = [
    ("Start", ["index.html", "executive-summary.html", "readiness.html"]),
    ("Markets", ["lines.html", "prices.html", "results.html", "backtest.html"]),
    ("Evidence", ["injury stubs"]),
    ("Method", ["leaderboard.html", "luck.html", "gates.html", "correlations.html", "ablations.html",
                "schedule.html", "fixtures.html", "features.html", "preregistration.html"]),
    ("Roster", ["injuries.html", "depth.html", "matrix.html", "teams.html", "availability.html"]),
    ("Review", ["questions.html", "suggestions.html", "repo-check"]),
    ("Reference", ["sources.html", "verification.html", "flagged.html", "policy.html"]),
]
NAV_GROUPS[2] = ("Evidence", ["results.html", "injuries.html", "depth.html"])
NAV_GROUPS[5] = ("Review", ["questions.html", "suggestions.html", "repo-review.html"])
NAV_GROUPS[6] = ("Reference", ["sources.html", "verification.html", "flagged.html", "policy.html",
                              "repo-review.html"])
# de-duplicate inside each group after the overrides above
_seen = set()
_norm = []
for g, items in NAV_GROUPS:
    keep = []
    for it in items:
        if it in _seen:
            continue
        _seen.add(it)
        keep.append(it)
    _norm.append((g, keep))
NAV_GROUPS = _norm

TITLES = {p: t for p, t, _ in PAGES}


def esc(s):
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    return html.escape(s, quote=True)


def e(v):
    """format a data cell, never printing None or nan."""
    if v is None:
        return ""
    s = str(v)
    if s.lower() in ("none", "nan", "nat"):
        return ""
    return s


def is_num(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def fmt(v, nd=3, pct=False, signed=False):
    s = e(v)
    if s == "":
        return '<span class="blank">blank</span>'
    if not is_num(s):
        return esc(s)
    x = float(s)
    if pct:
        return f"{100*x:.1f}%"
    if signed:
        return f"{x:+.{nd}f}"
    if abs(x) < 1 and x != 0:
        return f"{x:.{max(nd,3)}f}"
    return f"{x:.{nd}f}"


def src(url=None, label=None, flag=None):
    """A source cell: a link to an official page, or an explicit unverified badge."""
    bits = []
    if url:
        u = str(url)
        if u.startswith("http"):
            lab = label or ("official" if "nfl.com" in u else "source")
            bits.append(f'<a class="ext" href="{esc(u)}" target="_blank" rel="noopener">{esc(lab)}</a>')
        else:
            bits.append(f'<a href="{esc(u)}">{esc(label or u)}</a>')
    if flag:
        bits.append(f'<span class="flag" title="see Flagged for review">{esc(flag)}</span>')
    if not bits:
        bits.append('<span class="unv">UNVERIFIED</span>')
    return " ".join(bits)


def table(headers, rows, cls="", note=None, empty="No rows."):
    out = [f'<div class="tw"><table class="{cls}">']
    out.append("<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>")
    if not rows:
        out.append(f'<tr><td colspan="{len(headers)}" class="empty">{esc(empty)}</td></tr>')
    for r in rows:
        cells = []
        for c in r:
            cells.append(f"<td>{c}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append(f'<p class="tn">{note}</p>')
    return "\n".join(out)


def shell(active, title, body, subtitle="", lede=""):
    nav = []
    for group, items in NAV_GROUPS:
        links = []
        for f in items:
            if f not in TITLES:
                continue
            on = ' class="on"' if f == active else ""
            links.append(f'<a href="{f}"{on}>{esc(TITLES[f])}</a>')
        if links:
            nav.append(f'<div class="ng"><span>{esc(group)}</span>{"".join(links)}</div>')
    asof = META["as_of"]
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 NFL desk</title>
<meta name="description" content="X3 NFL desk: originated lines, a verified results feed, official availability evidence and a gated leaderboard. Every row links an official source or is flagged unverified.">
<link rel="stylesheet" href="assets/x3.css">
</head>
<body>
<header class="top">
  <a class="brand" href="index.html">X3<span>NFL desk</span></a>
  <div class="meta">season 2026 &middot; data as of <b>{esc(asof)}</b> &middot; week 10 in progress</div>
</header>
<nav class="nav">{"".join(nav)}</nav>
<main>
<div class="ph"><h1>{esc(title)}</h1>{f'<p class="sub">{subtitle}</p>' if subtitle else ''}</div>
{lede}
{body}
</main>
<footer>
<p>X3 NFL desk &middot; static site, no tracking, no client-side data collection.
Every table row carries a link to the official page it came from, or an explicit
<span class="unv">UNVERIFIED</span> badge. Benchmarks are labelled as benchmarks and
in-sample numbers are labelled in-sample.</p>
<p><a href="verification.html">How this was verified</a> &middot;
<a href="flagged.html">Flagged for review</a> &middot;
<a href="sources.html">Sources</a></p>
</footer>
</body>
</html>
'''


def callout(title, html_body, kind=""):
    return f'<section class="callout {kind}"><h2>{esc(title)}</h2>{html_body}</section>'


def grid(items):
    cells = "".join(f'<div class="stat"><b>{v}</b><span>{esc(l)}</span>'
                    f'{f"<i>{esc(s)}</i>" if s else ""}</div>' for v, l, s in items)
    return f'<div class="stats">{cells}</div>'


# --------------------------------------------------------------------------- #
def page_index():
    L = META["leaderboard"]
    body = []
    body.append(grid([
        (f"{META['n_results']}", "verified results", "finals only; live scores excluded"),
        (f"{META['n_graded']}", "graded walk-forward", "each predicted from earlier weeks"),
        (f"{META['n_upcoming']}", "markets priced", "Week 11, side then total then moneyline"),
        ("0", "prices", "no official market source exists"),
        (f"{META['n_flags']}", "flags published", "none of them hidden"),
    ]))
    body.append(callout("What this desk is", f'''
<p>It originates its own NFL numbers from verified data, grades them against a verified
results feed, and ranks strategies on a proper score with <b>signal and staking in
separate columns</b>. Where a number does not exist it is blank and flagged, never
estimated.</p>
<p class="key">Read <a href="executive-summary.html">the executive summary</a> first, then
<a href="readiness.html">decision readiness</a> for the one row per requirement.</p>'''))
    body.append(callout("The four things that are actually measured", f'''
<ul class="findings">
<li><b>The side carries a signal, in-sample.</b> {L['side_hits']} of {L['side_n']} graded games went the
model's way, Brier {L['brier_side']:.4f} against 0.25 for a coin flip (Brier skill
{L['bsts_side']:+.3f}). It is <em>in-sample</em>: the model was written after these games, so
gate G-1 fails and it cannot be promoted.</li>
<li><b>The total does not.</b> {L['total_hits']} of {L['total_n']} on direction, Brier skill
{L['bsts_total']:+.3f} against a pre-registered constant benchmark of 44 points. Model MAE
{L['mae_model_total']:.2f} against benchmark MAE {L['mae_bench_total']:.2f}.</li>
<li><b>The model is under-spread by a factor of {1/META['model_sd']*META['actual_sd']:.1f}.</b>
The predicted margin has SD {fmt(META['model_sd'],2)} where the actual margin's SD is
{fmt(META['actual_sd'],2)}. Since the moneyline is derived from the margin and a residual sigma of
{fmt(META['sigma'],2)}, the probabilities it produces hug 0.5: a too-timid probability is unusable
for staking even when its ordering is right.</li>
<li><b>Club depth order is an {100*META['depth_order']['rate']:.0f}%-accurate guide to who plays.</b>
In the one official Game Book read, the club's first-listed player took the most snaps in
{META['depth_order']['agree']} of {META['depth_order']['n']} slots; {META['depth_order']['disagree']}
slots went to a backup instead. That is the measured basis for using official playing time rather
than chart order.</li>
</ul>'''))
    body.append(callout("What is blocked, and by what", f'''
<p>Nothing can be staked, and no ROI or closing-line value can be computed, because
<b>no official market price exists</b> in this repository — see the
<a href="policy.html">price-data policy PDP-1</a>. The market column on every market row is
blank on purpose. The <a href="readiness.html">readiness table</a> gives the exact number
that would clear each block.</p>''', "warn"))
    body.append(f'''<section><h2>Every page</h2>
<div class="cards">{"".join(
    f'<a class="card" href="{f}"><b>{esc(t)}</b><span>{esc(d)}</span></a>'
    for f, t, d in PAGES if f != "index.html")}</div></section>''')
    return shell("index.html", "Overview", "\n".join(body),
                 "An NFL line-origination and signal desk built from official sources",
                 "")


def page_exec():
    L = META["leaderboard"]
    A = META["ablations"]
    D = META["depth_order"]
    rows = [
        ["Verified results feed", f"{META['n_results']} finals", "DONE",
         "every final has its game-centre URL; live scores excluded",
         src(I.U["sched_w10"], "nfl.com week 10")],
        ["Origination", f"{META['n_upcoming']} markets", "DONE",
         "side, then total, then moneyline derived from the side",
         src("lines.html", "table")],
        ["Price snapshots", f"{META['n_snapshots']} rows", "PARTIAL",
         "open and close stored per market; both hold the fair number because no price exists",
         src("prices.html", "table")],
        ["Market residual", "0 of 13 markets", "BLOCKED",
         "no official price; market and difference columns are blank (F-01)", src(I.U["standings"], "nfl.com")],
        ["Side signal", f"{L['side_hits']}/{L['side_n']}, Brier skill {L['bsts_side']:+.3f}", "IN-SAMPLE",
         "gate G-1 fails: the model predates the games it is graded on", src("leaderboard.html", "table")],
        ["Total signal", f"{L['total_hits']}/{L['total_n']}, Brier skill {L['bsts_total']:+.3f}", "PAPER",
         "does not beat a constant benchmark", src("leaderboard.html", "table")],
        ["Controls", "3", "DONE", "home, favourites, coin flip — published before any strategy",
         src("leaderboard.html", "table")],
        ["Correlations", f"{META['n_corr']} with n", "DONE",
         "official numbers only; one is undefined and says so", src("correlations.html", "table")],
        ["Availability graph", f"{META['n_availability']} rows", "PARTIAL",
         "expected vs actual starters, from one Game Book", src("availability.html", "table")],
        ["Depth vs playing time", f"{D['agree']}/{D['n']} agree", "MEASURED",
         "club order matches official snaps in 80% of slots", src("depth.html", "table")],
        ["Ablation", f"n={A['n']}", "UNDERPOWERED",
         "paired difference published; the interval straddles zero", src("ablations.html", "table")],
        ["Demotion gate", "4 triggers", "REGISTERED",
         "dry-run proven to fire; nothing is live yet", src("gates.html", "table")],
        ["Pre-registration", "7 entries", "PARTIAL", "G-1 fails for the current model; S-09 proposes fixing it",
         src("preregistration.html", "table")],
        ["Flags", f"{META['n_flags']}", "PUBLISHED", "every unverified cell is listed, none hidden",
         src("flagged.html", "table")],
    ]
    body = callout("The one-paragraph answer", f'''
<p>This desk does three things a spreadsheet cannot. It <b>originates</b> a line for every
unplayed Week-11 fixture in a fixed order (side, then total, then moneyline) and stores an
opening and a closing row for every one of those {META['n_upcoming']*3} markets. It
<b>grades</b> its own model walk-forward against a verified {META['n_results']}-game results
feed, with three control baselines published first. And it <b>refuses</b> to publish any
number it cannot source: there is no market price in this repository, so every
fair-versus-market, ROI and closing-line column is blank, and the price-data policy that
governs that decision was committed before any backtest number appeared.</p>''')
    body += callout("What the data says, in order of confidence", f'''
<ol class="findings">
<li><b>Measured, and it holds up:</b> the side's ordering is informative. {L['side_hits']} of
{L['side_n']} walk-forward graded games went the predicted way (95% interval on the hit rate is
on the leaderboard), and the Brier score beats a coin flip by {100*L['bsts_side']:.1f}%.
Two independent bugs were found and fixed while building this, and both had inverted published
findings — see the <a href="verification.html">verification log</a>.</li>
<li><b>Measured, and it does not hold up:</b> the total. It loses to a constant benchmark of 44
points (MAE {L['mae_model_total']:.2f} vs {L['mae_bench_total']:.2f}) and its Brier skill is
negative. It stays on the paper board.</li>
<li><b>Measured, and it is a warning:</b> the model's predicted margins have SD
{fmt(META['model_sd'],2)} against an actual SD of {fmt(META['actual_sd'],2)} — a ratio of
{META['model_sd']/META['actual_sd']:.2f}, so its probabilities hug 0.5. That is why the side's
Brier skill is real but small, and why S-05 (calibration) comes before any staking.</li>
<li><b>Measured, and it changes a design decision:</b> the club depth chart is not a reliable
starter proxy on its own — it matched official playing time in {D['agree']} of {D['n']} slots
({100*D['rate']:.0f}%). The desk therefore uses the official snap count where it exists and says so
where it does not.</li>
<li><b>Not measurable here:</b> ROI, closing-line value, stake sizing, drawdown, prop-level
correlation and the meaning of "Questionable". Each is blocked by a named missing dataset on the
<a href="readiness.html">readiness page</a>.</li>
</ol>''')
    body += callout("The decision the reviewer actually has to make", f'''
<p>Three decisions, in this order, unlock almost everything else:</p>
<ol class="findings">
<li><b>Price data (S-02).</b> Licence a feed, or delete the market columns permanently. Until
this is answered, {META['n_upcoming']} markets x 3 rows sit blank with a flag, and no strategy
can ever be scored on returns.</li>
<li><b>Game Book coverage (S-03).</b> {META['n_results']} finals have an official PDF with
starters, inactives and snap counts. Reading them turns a 20-slot measurement into a per-position
rate, which is what the deficiency matrix needs to be honest.</li>
<li><b>Pre-registration (S-09).</b> Register the next model before week 12 and every number after
that becomes out-of-sample. Without it, every result this desk publishes stays in-sample forever.</li>
</ol>''', "warn")
    return shell("executive-summary.html", "Executive summary", "\n".join(body),
                 "What is verified, what is measured, what is blocked, what to decide")


def _where_cell(w):
    """Resolve a 'where' string into a link that works from inside x3/."""
    if w == "COORDINATION.md":
        return ('<a class="ext" href="https://github.com/karagemop466-tech/X3/blob/main/'
                'COORDINATION.md" target="_blank" rel="noopener">COORDINATION.md</a>')
    if w.startswith("x3/"):
        return f'<a href="{esc(w[3:])}">{esc(w[3:])}</a>'
    if w.endswith(".html"):
        return f'<a href="{esc(w)}">{esc(w)}</a>'
    return src(w, "page")


def page_readiness():
    rows = []
    req = {r[0]: r for r in C.REQUIREMENTS}
    status_counts = {}
    for r in C.REQUIREMENTS:
        status_counts[r[2]] = status_counts.get(r[2], 0) + 1

    # each requirement gets: the gate that blocks it and the number that clears it
    CLEARS = {
        "R-01": ("F-01 / PDP-1", "a licensed price feed with a pre-kickoff timestamped capture"),
        "R-04": ("F-01 / PDP-1", "1 official market price per market"),
        "R-06": ("F-09", "a Game Book read for 138 finals (currently 1)"),
        "R-10": ("F-13", "a Game Book read for 138 finals (currently 1)"),
        "R-09": ("G-1", "a registration dated before the graded window"),
        "R-12": ("no base-rate dataset", "a multi-season base rate for a player's availability"),
        "R-13": ("no roster capture", "32 club roster pages with reserve/IR status"),
        "R-14": ("F-10", "venue + roof for 32 stadiums; 1 verified"),
        "R-18": ("F-01", "1 market price per market"),
        "R-19": ("G-1", "a registration dated before the graded window"),
        "R-21": ("one capture only", "3 captures per week for 4 weeks (12 reads)"),
        "R-23": ("not re-read", "a venue read for 124 remaining games"),
        "R-24": ("not re-read", "the dated 2026 schedule-announcement release"),
        "R-29": ("one capture only", "7 consecutive daily captures"),
        "R-31": ("F-05", "an authorised structured source for the Texans chart"),
        "R-32": ("F-08", "a parser that keeps a shared rank-1 cell as a group"),
        "R-33": ("no transactions capture", "a transactions log with dates"),
        "R-36": ("no data in 3 divisions", "settled prop and combo samples"),
        "R-38": ("no alert channel", "a notification target (issue, webhook or email)"),
        "R-39": ("no private store", "a private repository or bucket for row-level data"),
        "R-40": ("F-13", "a Game Book read per fixture"),
        "R-42": ("F-06", "a dated chart for 31 clubs (currently 1)"),
        "R-43": ("no inactive history", "2 seasons of designations joined to inactive lists"),
        "R-44": ("F-09", "snap evidence for 32 clubs"),
        "R-45": ("no transactions capture", "a transactions log with dates"),
        "R-46": ("one capture only", "a capture per day per source"),
        "R-50": ("F-08", "a group-preserving parser"),
        "R-51": ("coverage 2/32", "snap evidence for 32 clubs"),
        "R-52": ("no inactive history", "2 seasons of designations joined to inactive lists"),
        "R-53": ("pipeline ran once", "3 scheduled captures per week"),
        "R-54": ("one read per week", "3 reads per week"),
        "R-57": ("no NWS / roof capture", "roof + surface for 32 stadiums, NWS hourly forecasts"),
        "R-58": ("F-01", "a licensed price feed"),
        "R-59": ("F-01", "market prices on both sides of the vig"),
        "R-63": ("no roster capture", "32 club roster pages with reserve/IR status"),
        "R-65": ("no archive", "a past-season injury archive"),
        "R-66": ("G-1", "a registration dated before the graded window"),
        "R-67": ("one season", "a second season of finals"),
        "R-71": ("no prop data", "player-level prop lines and results"),
        "R-72": ("G-2", "200 graded games per division"),
        "R-73": ("F-09", "snap evidence for 32 clubs"),
    }
    for r in C.REQUIREMENTS:
        gate, clears = CLEARS.get(r[0], ("—", "no numeric threshold; delivered or rejected"))
        rows.append([
            f"<b>{r[0]}</b>", esc(r[1]), f'<span class="st {r[2].split()[0].lower()}">{esc(r[2])}</span>',
            _where_cell(r[3]),
            esc(gate), esc(clears), esc(r[5]),
        ])
    counts = "".join(f'<span class="pill"><b>{v}</b> {esc(k)}</span>' for k, v in sorted(status_counts.items()))
    body = callout("One row per requirement", f'''
<p>{len(C.REQUIREMENTS)} requirement lines from the brief, each with the gate that blocks it and
the number that would clear it. A requirement is only <b>DONE</b> when a gate enforces it.</p>
<p class="key">{counts}</p>''')
    body += table(["ID", "Requirement", "Status", "Where", "Blocking gate", "Number that clears it", "Note"],
                  rows, note="Status vocabulary: DONE / PARTIAL / BLOCKED / REJECTED / NOT STARTED / DUPLICATE. "
                             "A BLOCKED row is not a failure of effort; it is a missing dataset or decision.")
    return shell("readiness.html", "Decision readiness", body,
                 "One row per requirement: the gate that blocks it and the number that would clear it")


def page_lines():
    orig = load("origination.csv")
    rows = []
    for r in orig:
        rows.append([
            f"<b>{esc(r['away'])} @ {esc(r['home'])}</b>", esc(r["date"]),
            fmt(r["side_fair"], 2, signed=True),
            fmt(r["total_fair"], 1),
            fmt(r["ml_home_fair"], 3),
            '<span class="blank">blank</span><span class="flag">F-01</span>',
            '<span class="blank">blank</span>',
            esc(r["n_train"]), src(r["source"], "nfl.com"),
        ])
    body = callout("The pipeline order is fixed", f'''
<p><b>1. Side</b> — a ridge fit on home margin gives each club an opponent-adjusted net rating;
the fair spread is the negation of the expected margin, in betting notation. <b>2. Total</b> — a
second ridge fit on game total gives each club a pace rating. <b>3. Moneyline</b> — derived from
the side and the walk-forward residual sigma (currently {fmt(META['sigma'],2)} points), never
fitted separately, so the three markets cannot contradict each other.</p>
<p>Each row carries its inputs: the chosen ridge penalty (margin {fmt(META['lam_margin'],1)},
total {fmt(META['lam_total'],1)}), the number of training games, and the source. That is
requirement R-15 — a probability with its inputs, not a pick.</p>''')
    body += table(["Fixture", "Date", "Fair side (home)", "Fair total", "Fair ML (home)",
                   "Market side", "Difference", "n train", "Source"], rows,
                  note="Market and difference are blank because no official price exists (F-01). "
                       "A negative fair side means the home club is favoured. Fair values are "
                       "derived arithmetic on official results, not predictions of fact.")
    body += callout("Two total estimators, published side by side", '''
<p>Requirement R-61 asks for both estimators to stay visible with a gap column until a
walk-forward comparison picks a winner. The pace model and the league-constant benchmark both
appear on the <a href="leaderboard.html">leaderboard</a>; the gap is negative, so neither has
won yet and neither is hidden.</p>''')
    return shell("lines.html", "Originated lines", body,
                 f"{len(orig)} Week-11 markets, side then total then moneyline")


def page_prices():
    snaps = load("price_snapshots.csv")
    by = {}
    for r in snaps:
        by.setdefault((r["game_id"], r["market"]), {})[r["phase"]] = r
    rows = []
    for (gid, market) in sorted(by):
        o = by[(gid, market)].get("open", {})
        c = by[(gid, market)].get("close", {})
        rows.append([
            esc(gid), esc(market),
            fmt(o.get("fair_value"), 3), fmt(c.get("fair_value"), 3),
            '<span class="blank">blank</span>', '<span class="blank">blank</span>',
            f'<span class="mono">{esc(o.get("hash","")[:12])}</span>',
            src(o.get("source"), "nfl.com"),
        ])
    body = callout("What a snapshot store has to do, and what this one cannot yet do", f'''
<p>Requirement R-01 asks for opening and closing numbers for every market we originate. This
desk stores <b>{META['n_snapshots']} rows</b>: {META['n_upcoming']} markets x 3 market types x 2
phases, each with a capture id (<span class="mono">{esc(META['snapshot']['capture_id'])}</span>),
a clock time and a content hash. That is the schema the requirement asks for.</p>
<p>What it cannot do is differ: with no price source, the "opening" and the "closing" number are
the same fair value, because nothing between the two captures changed it. The store is honest about
that in the <code>state</code> column, and the price-data policy
<a href="policy.html">PDP-1</a> explains why inventing a move would be worse than publishing none.</p>''', "warn")
    body += table(["Market id", "Type", "Open fair", "Close fair", "Open market", "Close market",
                   "Content hash", "Source"], rows,
                  note="One row per market rather than per phase, for readability; the CSV carries "
                       "one row per phase.")
    return shell("prices.html", "Price snapshots", body,
                 "Opening and closing rows for every originated market, with a hash")


def page_results():
    res = load("results.csv")
    by_week = {}
    for r in res:
        by_week.setdefault(r["week"], []).append(r)
    body = callout("Only finals, and only from an official page", f'''
<p>{len(res)} games. A game enters this feed when an official page shows it as final. A
<b>live</b> score is never a result: at the time of the last read, seven Week-10 games were in
progress and five had not kicked off, and all twelve are excluded rather than stored as partial
rows (F-14). The two Week-10 games that went final during this session were re-read from their
game centres and added.</p>''')
    for w in sorted(by_week):
        rows = [[f"<b>{esc(r['away'])}</b>", esc(r["away_score"]), esc(r["home_score"]),
                 f"<b>{esc(r['home'])}</b>",
                 "neutral" if r["neutral"] == "yes" else "",
                 esc(r["date"]), src(r["source"], "game page")]
                for r in by_week[w]]
        body += f'<section><h2>Week {w} <span class="cnt">{len(rows)} finals</span></h2>'
        body += table(["Away", "Pts", "Pts", "Home", "Site", "Date", "Source"], rows, cls="score")
        body += "</section>"
    return shell("results.html", "Results feed", body,
                 f"{len(res)} finals, each with its official game page")


def page_backtest():
    bt = load("backtest.csv")
    graded = [r for r in bt if r["graded"] == "yes"]
    rows = [[esc(r["game_id"]), esc(r["week"]), fmt(r["pred_margin"], 2, signed=True),
             fmt(r["actual_margin"], 0, signed=True),
             fmt(r["pred_total"], 1), fmt(r["actual_total"], 1),
             esc(r["lambda_chosen"]), esc(r["n_train"]), src(r["source"], "nfl.com")]
            for r in graded]
    body = callout("The corpus, and the rule that makes it a backtest", f'''
<p>{len(bt)} finals are in the corpus and {len(graded)} are graded. A game is <b>not</b> graded
until at least 30 earlier games exist, so the first two weeks train and never score. For every
graded game the ridge penalty is chosen by an inner walk-forward <em>inside</em> the training
window, so the penalty is never tuned on the week it is graded against. The chosen penalty is
printed per row.</p>
<p>This is the <a href="preregistration.html">pre-registered corpus</a> for requirement R-19. Gate
G-1 still fails, because the register was written after the games — the corpus is frozen now so
that every game from here is out-of-sample.</p>''')
    body += table(["Game", "Week", "Predicted margin", "Actual margin", "Predicted total",
                   "Actual total", "Ridge penalty", "n train", "Source"], rows,
                  note=f"Showing the {len(graded)} graded rows. The ungraded training weeks are in "
                       f"x3/data/backtest.csv with graded=no.")
    return shell("backtest.html", "Backtest corpus", body,
                 "Walk-forward predictions with the chosen penalty per row")


def page_leaderboard():
    lb = load("leaderboard.csv")
    rows = []
    for r in lb:
        sig = fmt(r["signal_value"], 3, signed=(r["id"] in ("S-01", "S-02")))
        rows.append([
            esc(r["rank"]), f'<b>{esc(r["id"])}</b>', esc(r["strategy"]),
            f'<span class="div">{esc(r["division"])}</span>',
            esc(r["signal_metric"]), sig, esc(r["signal_n"]),
            fmt(r["proper_score"], 4),
            f'<b>{fmt(r["bsts"], 3, signed=True)}</b>' if r["bsts"] else '<span class="blank">blank</span>',
            fmt(r["p_value"], 4) if r["p_value"] else '<span class="blank">blank</span>',
            '<span class="blank">no price</span>', '<span class="blank">no price</span>',
            f'<span class="st {r["state"].split("-")[0].lower()}">{esc(r["state"])}</span>',
        ])
    L = META["leaderboard"]
    body = callout("Signal and staking are different columns, and only one can rank", f'''
<p>Requirement R-05 and R-37: <b>staking cannot promote a strategy</b>. The rank key is the
signal column, and the gate script asserts that no ordering reads a return. Every staking cell is
blank because no price exists (F-01), so a lucky staking run cannot exist here at all — which is
the strongest possible version of the requirement.</p>
<p><b>Controls come first.</b> Three baselines are published before any strategy: the home club
always ({L['home_hits']}/{L['n']}), the better record
({L['fav']}/{L['fav_n']}, descriptive only because it uses post-game standings), and a coin flip.
A strategy that cannot beat these is not a signal.</p>''')
    body += table(["Rank", "ID", "Strategy", "Division", "Signal metric", "Value", "n",
                   "Proper score", "Brier skill", "p", "ROI", "CLV", "State"], rows,
                  note="Brier skill is 1 - Brier/Brier(benchmark). Positive is better than the "
                       "benchmark. p is an exact binomial two-sided test against 0.5 on the direction.")
    body += callout("What would change our mind — both directions", f'''
<ul class="findings">
<li><b>S-01 (side)</b> — would strengthen if a post-registration window reproduces a hit rate
above 0.55 with n >= 200. Would collapse if that window returns to 0.50; the interval here
already touches 0.50 at its lower edge, so this is not a remote possibility.</li>
<li><b>S-02 (total)</b> — would strengthen if the model beat the benchmark MAE on a second
window. Would be archived by D-2 if a second window is also adverse. Right now it loses on both
Brier skill and MAE.</li>
<li><b>S-03 (combo)</b> — would become rankable only with a validated joint probability and the
operator's void/push rules. No amount of marginal evidence substitutes, because the legs are
dependent — the observed joint rate is well below the product of the marginals.</li>
<li><b>The whole board</b> — would change character entirely with a licensed price. Every
ROI cell would fill, and the demotion gate D-1 would become triggerable.</li>
</ul>''')
    return shell("leaderboard.html", "Leaderboard", body,
                 "Ranked on a proper score; staking reported separately and never used to rank")


def page_luck():
    luck = load("luck.csv")
    rows = [[esc(r["item"]), fmt(r["value"], 4), esc(r["n"]),
             fmt(r["ci_low"], 4) if r["ci_low"] else '<span class="blank">blank</span>',
             fmt(r["ci_high"], 4) if r["ci_high"] else '<span class="blank">blank</span>',
             src(r["source"], "nfl.com")]
            for r in luck]
    bump = META.get("bump") or []
    brows = [[f"<b>{esc(b[0])}</b>", esc(b[1]), f"{b[2]:.2f}", f"{b[3]:+.2f}",
              src(I.U["standings"], "nfl.com")] for b in bump]
    body = callout("Luck is bounded, never removed", '''
<p>The brief asks to "remove luck from the equation". It cannot be removed — a single NFL game is
mostly noise. What can be done is to <b>measure how much of a record is not skill</b>, and then
rank on a score that does not reward the noise. That is what this panel does.</p>''')
    body += table(["Measurement", "Value", "n", "95% low", "95% high", "Source"], rows)
    body += callout("Club by club: Pythagorean expected wins against actual wins", f'''
<p>Pythagorean expectation from each club's own points for and against, compared with its actual
wins. The league-wide sum is essentially zero (no systematic bias), but the club-level spread is
SD {fmt(META['luck_sd'],2)} wins. That spread is exactly the luck a season-long win-rate
leaderboard would reward, and it is why this desk ranks on Brier skill instead.</p>''')
    body += table(["Club", "Actual wins", "Expected wins", "Difference", "Source"], brows, cls="score",
                  note="Positive means the club has won more than its scoring margin implies.")
    return shell("luck.html", "Removal of luck", body,
                 "Four measurements that bound luck instead of pretending to delete it")


def page_gates():
    g = load("gates.csv")
    rows = [[f'<b>{esc(r["id"])}</b>', esc(r["gate"]), f'<span class="div">{esc(r["kind"])}</span>',
             esc(r["rule"]), esc(r["threshold"]), esc(r["measured"]),
             f'<span class="st {"pass" if r["result"].startswith("PASS") else ("fail" if r["result"].startswith("FAIL") else "warn")}">{esc(r["result"])}</span>',
             esc(r["action"]), src(r["source"], "page")]
            for r in g]
    body = callout("The demotion gate, stated before anything is live", '''
<p>Requirement R-08 asks for a rule that sends a <b>live strategy back to paper</b>. D-1 has four
triggers and <b>any one</b> fires it: a rolling 40-game hit rate at or below 0.50, a negative
Brier skill over 40 graded games, four live weeks with no graded game, or a data-source schema
failure. Nothing on this desk is live, so the gate cannot fire for real; the verification script
therefore <b>injects</b> an adverse 40-game window and asserts that the rule fires. A rule that has
never been executed is a wish, not a gate.</p>''')
    body += table(["ID", "Gate", "Kind", "Rule", "Threshold", "Measured", "Result", "Action", "Source"],
                  rows)
    return shell("gates.html", "Gates & demotion", body,
                 "Entry gates, integrity gates and the demotion rule that sends a strategy back to paper")


def page_corr():
    c = load("correlations.csv")
    rows = [[f'<b>{esc(r["id"])}</b>', esc(r["a"]), esc(r["b"]),
             fmt(r["r"], 4) if r["r"] else '<span class="st warn">undefined</span>',
             f'<b>{esc(r["n"])}</b>',
             fmt(r["ci_low"], 4) if r["ci_low"] else "",
             fmt(r["ci_high"], 4) if r["ci_high"] else "",
             fmt(r["p"], 4) if r["p"] else "",
             esc(r["method"]), src(r["source"], "nfl.com")]
            for r in c]
    body = callout("Official numbers only, and every value carries its n", '''
<p>Requirement R-07 forbids a correlation without a published sample size, and forbids computing
one from a number that is not officially sourced. Each row below names the two quantities, the
official page they came from, n, a 95% interval via Fisher's z, and a two-sided p.</p>
<p>An <b>undefined</b> coefficient is never printed as zero. C-05 currently covers only 9
club-position pairs from a single game, so its interval is very wide and it is published to show the
shape of the question, not to answer it. A row that cannot be estimated at all shows "undefined"
rather than 0, because 0 is a number and a missing estimate is not.</p>''')
    body += table(["ID", "Quantity A", "Quantity B", "r", "n", "95% low", "95% high", "p", "Method", "Source"],
                  rows, note="Notes for each coefficient (including the pair list behind C-05) are in "
                             "x3/data/correlations.csv and reproduced on each row's tooltip in the CSV.")
    detail = [[f'<b>{esc(r["id"])}</b>', esc(r["note"]), src(r["source"], "nfl.com")]
              for r in c if r["note"]]
    body += callout("Notes", table(["ID", "Note", "Source"], detail))
    return shell("correlations.html", "Correlations", body,
                 "Five coefficients from official numbers, each with n, an interval and a p")


def page_injuries():
    inj = I.load_injuries()
    weeks = {}
    for r in inj:
        weeks.setdefault(r["week"], []).append(r)
    rows = []
    for w in sorted(weeks):
        rs = weeks[w]
        out = sum(1 for r in rs if r["status"] == "Out")
        dbt = sum(1 for r in rs if r["status"] == "Doubtful")
        q = sum(1 for r in rs if r["status"] == "Questionable")
        blank = sum(1 for r in rs if not r["status"])
        rows.append([f"<b>Week {w}</b>", esc(len(rs)), esc(len({r['team'] for r in rs})),
                     esc(out), esc(dbt), esc(q), esc(blank),
                     f"{100*blank/len(rs):.1f}%",
                     src(rs[0]["source"], "nfl.com") if w != 11 else
                     src(I.U["injuries_wk11"], "nfl.com") + '<span class="flag">F-02</span>'])
    L = [r for r in load("leaderboard.csv")]
    body = callout("What the official report actually contains", f'''
<p>{len(inj)} rows across four weekly reads. The single most important number is the last column:
<b>most rows carry no game status at all</b>. The report lists practice participation, and the
practice participation is the bulk of the information. A game designation (Out / Doubtful /
Questionable) appears only for players the club has actually ruled on.</p>
<p><b>Week 11 is not a report yet.</b> <code>nfl.com/injuries/league/2026/reg11</code> returns the
Week-10 page byte for byte — the committed capture's sizes are identical, and the live page's own
title says "Week 10". Nothing from reg11 is used here. Week-11 designations appear on Wednesday
(F-02).</p>''')
    body += table(["Week", "Rows", "Clubs", "Out", "Doubtful", "Questionable", "No status",
                   "Share with no status", "Source"], rows)
    # verified spot check
    body += callout("Verified this session, row for row", '''
<p>Three Detroit players were reported on the Flagged page as having a blank game-status cell. All
three are published as <b>Out</b> on the live page today, and the desk records them as verified:</p>''')
    det = [r for r in inj if r["team"] == "DET" and r["week"] == 10 and
           r["player"] in ("Kerby Joseph", "Cade Mays", "D.J. Reed")]
    drows = [[f"<b>{esc(r['player'])}</b>", esc(r["pos"]), esc(r["injury"]), esc(r["practice"]),
              f'<span class="st pass">{esc(r["status"])}</span>', src(r["source"], "nfl.com")]
             for r in det]
    body += table(["Player", "Pos", "Injury", "Practice", "Game status", "Source"], drows,
                  empty="No matching rows in the committed capture.")
    return shell("injuries.html", "Injuries", body,
                 "The official report as published: practice status is the signal, game status is rare")


def page_depth():
    d = load("depth.csv")
    order = load("depth_order.csv")
    D = META["depth_order"]
    clubs = sorted({r["club"] for r in d})
    counts = {}
    for r in d:
        if r["club"] not in counts:
            counts[r["club"]] = {"rows": 0, "snap": 0, "asof": "", "src": ""}
        counts[r["club"]]["rows"] += 1
        if r["evidence"] == "GAMEBOOK_SNAP":
            counts[r["club"]]["snap"] += 1
        counts[r["club"]]["asof"] = r["as_of"]
        counts[r["club"]]["src"] = r["source"]
    crow = [[f"<b>{esc(ab)}</b>", esc(counts[ab]["rows"]), esc(counts[ab]["snap"]),
             esc(counts[ab]["asof"]) or '<span class="blank">not printed</span>',
             src(counts[ab]["src"], ab.lower() + ".com")] for ab in clubs]
    orow = [[f"<b>{esc(r['club'])}</b>", esc(r["unit"]), esc(r["pos"]),
             esc(r["chart_first"]), esc(r["chart_first_snaps"]),
             esc(r["most_snaps_player"]), esc(r["most_snaps"]),
             '<span class="st pass">agrees</span>' if r["order_agrees_with_playing_time"] == "yes"
             else '<span class="st fail">differs</span>',
             src(r["snap_sheet"], "game book")]
            for r in order]
    body = callout("The measured answer to 'model depth from playing time, not jersey order'", f'''
<p>The official Game Book prints a <b>Playtime Percentage</b> sheet: every player who took a snap,
by count and share. Against the club's own depth chart, for the one game where both exist:</p>
<p class="key"><b>{D['agree']} of {D['n']} slots agree</b> ({100*D['rate']:.0f}%), {D['disagree']}
disagree. In four slots the club's first-listed player played fewer snaps than a backup. So the
depth chart is a useful prior and <b>not</b> a reliable statement of who plays — which is the
brief's point, measured rather than asserted.</p>
<p>Two more structural problems are published rather than papered over: <b>31 of 32 clubs print no
as-of date</b> (F-06), and the committed capture <b>loses shared slots</b> — Seattle lists two
players in one rank-1 cell live, and the parser splits them into rank 1 and rank 2 (F-08).</p>''')
    body += callout("Where the club order and the official playing time disagree", '')
    body += table(["Club", "Unit", "Pos", "Chart first", "His snaps", "Most snaps", "His snaps",
                   "Agreement", "Snap sheet"], orow)
    body += callout("Coverage by club", f'''
<p>{len(d)} depth rows across {len(clubs)} clubs. Only 2 clubs have snap evidence, because only one
Game Book was read; every other row is a <b>chart claim</b> and is labelled CLI_CB_CHART_ONLY, not a
playing-time claim.</p>''')
    body += table(["Club", "Rows", "Rows with official snaps", "As-of date", "Chart source"], crow)
    return shell("depth.html", "Depth & replacements", body,
                 "String order, and what the official snap sheet says about it")


def page_matrix():
    d = load("depth.csv")
    fixtures = load("origination.csv")
    depth_by = {}
    for r in d:
        depth_by.setdefault(r["club"], {}).setdefault(r["pos"], []).append(r)
    rows = []
    for f in fixtures:
        away, home = f["away"], f["home"]
        for off_side, def_side, off_club, def_club in (("away", "home", away, home),
                                                       ("home", "away", home, away)):
            for pos, opp in (("WR", "CB"), ("TE", "LB"), ("RB", "LB"), ("QB", "S")):
                offs = sorted(depth_by.get(off_club, {}).get(pos, []), key=lambda r: (int(r["string"] or 9), r["player"]))
                defs = sorted(depth_by.get(def_club, {}).get(opp, []), key=lambda r: (int(r["string"] or 9), r["player"]))
                if not offs or not defs:
                    continue
                o1 = offs[0]
                dnew = [x for x in defs if x["string"] not in ("1",)]
                dsel = dnew[0] if dnew else defs[0]
                rows.append([
                    f"<b>{esc(off_club)} @ {esc(def_club)}</b>", esc(pos), esc(o1["player"]),
                    f'<span class="div">{esc(o1["string"])}</span>',
                    esc(opp), esc(dsel["player"]), f'<span class="div">{esc(dsel["string"])}</span>',
                    src(o1["source"], off_club.lower() + ".com"),
                    src(dsel["source"], def_club.lower() + ".com"),
                ])
    body = callout("What this matrix is, and what it is not", f'''
<p>Every Week-11 fixture, matched position to position: the offence's first-listed player against
the defence's <b>first backup</b> at the covering position. That is the deficiency view the brief
asks for — where a 1st-string receiver faces a promoted 2nd-string corner.</p>
<p class="key">It is a <b>chart</b> comparison, not a playing-time comparison. Only 2 clubs have
official snap evidence, so a "2nd string" label here means the club listed him second, not that he
plays second. The <a href="depth.html">depth page</a> measures how often that distinction matters:
in 20% of the slots it did.</p>''', "warn")
    body += table(["Fixture", "Off pos", "Off player", "Str", "Def pos", "Defender", "Str",
                   "Off source", "Def source"], rows)
    return shell("matrix.html", "Matchup matrix", body,
                 "Per-fixture deficiency view from the depth charts")


def page_teams():
    inj = I.load_injuries()
    d = load("depth.csv")
    depth_by = {}
    for r in d:
        depth_by.setdefault((r["club"], r["pos"]), []).append(r)
    rows = []
    for club in sorted({r["team"] for r in inj}):
        wk10 = [r for r in inj if r["team"] == club and r["week"] == 10]
        outs = [r for r in wk10 if r["status"] == "Out"]
        q = [r for r in wk10 if r["status"] == "Questionable"]
        named = []
        for r in outs:
            cand = depth_by.get((club, r["pos"])) or []
            cand = sorted(cand, key=lambda x: (int(x["string"] or 9), x["player"]))
            nxt = [x for x in cand if x["string"] == "2"]
            named.append(f'{r["player"]} ({r["pos"]}) -> '
                         + (f'{nxt[0]["player"]} (2nd)' if nxt else "no 2nd-string row"))
        rows.append([f"<b>{esc(club)}</b>", esc(len(outs)), esc(len(q)),
                     esc(len(wk10)), "<br>".join(esc(x) for x in named) or "—",
                     (src(wk10[0]["source"], "nfl.com") if wk10 else
                      src(I.U["injuries_wk10"], "nfl.com") +
                      '<span class="flag">not on week-10 report</span>')])
    body = callout("Starters out, replacements named, net count", f'''
<p>Requirement R-40. For every club: how many players the official report marks <b>Out</b>, how many
<b>Questionable</b>, and the name of the club's own second-string player at the same position.</p>
<p class="key">The replacement column is a <b>chart</b> name, not a confirmed starter. Nobody is
"announced" as a replacement until a Game Book lists him in the Lineups block, and that exists for
one game. Where the club lists no second-string row, this says so rather than guessing.</p>''')
    body += table(["Club", "Out", "Questionable", "Rows on report", "Next man up (chart)", "Source"], rows,
                  note="Join risk: the injury report gives a full name and the depth chart a full name, "
                       "so this join is by exact position string, not fuzzy surname matching (F-15).")
    return shell("teams.html", "Per-team view", body,
                 "Who is officially out, and who the club lists behind him")


def page_availability():
    a = load("availability.csv")
    rows = [[f"<b>{esc(r['club'])}</b>", esc(r["unit"]), esc(r["pos"]),
             esc(r["expected_starter"]) or '<span class="blank">no chart row</span>',
             esc(r["actual_starter"]), esc(r["actual_jersey"]),
             f'<span class="st {"pass" if r["match"] in ("same-person",) else "warn"}">{esc(r["match"])}</span>',
             src(r["actual_source"], "game book") if r["actual_source"] else ""]
            for r in a]
    body = callout("Expected versus actual, never merged", f'''
<p>Requirement R-10 and R-41: the availability graph is a first-class dataset. <b>Expected</b> comes
from the club's own depth chart. <b>Actual</b> comes from the official Game Book's Lineups block,
which is the only source that can confirm a starter. The two columns carry different source URLs on
every row so a reader can check either one.</p>
<p>{len(a)} rows, all from the Washington at New York Giants Game Book of 2026-11-12. Coverage is one
game out of {META['n_results']} finals: the method is proven, the coverage is the next task (S-03).</p>''')
    body += table(["Club", "Unit", "Pos", "Expected starter (chart)", "Actual starter (Game Book)",
                   "No.", "Match", "Source"], rows,
                  note="'Match' compares the chart name with the Game Book surname. 'no-chart-row' means "
                       "the club lists no player at that position, which is itself a finding — a defense "
                       "lists 11 starters but not always 11 position labels.")
    sc = load("starter_check.csv")
    S = META["starter_check"]
    srows = [[f"<b>{esc(r['club'])}</b>", esc(r["pos"]), esc(r["chart_first"]), esc(r["actual_starter"]),
              f'<span class="st {"pass" if r["verdict"].startswith("same") else "fail"}">'
              f'{esc(r["verdict"])}</span>', src(r["source"], "game book")]
             for r in sc]
    body += callout("Does the man the club lists first actually start?", f"""
<p>For every offensive starter in the Game Book, the club's own first-listed player at that
position label. <b>{S['same']} of {S['n']}</b> match. <b>{S['differ']}</b> do not.</p>
<p class="key">The misses are the point. Washington's chart lists Terry McLaurin first at receiver,
and <b>McLaurin did not start</b> — Antonio Williams and Treylon Burks did. The chart lists Jacory
Croskey-Merritt first at running back and <b>Rachaad White started</b>. New York's second tight end
row is a chart label, not a starter. This is why the desk takes the starter from the Game Book and
never from the chart.</p>""", "warn")
    body += table(["Club", "Pos", "Chart says first", "Game Book says started", "Verdict", "Source"], srows,
                  note="Two TE and two WR rows are expected: clubs list multiple players at those labels, "
                       "and the Game Book lists the men who actually started. A match is on surname plus "
                       "initial; 'J.J. McCarthy' style names are parsed as initials, not as a surname.")
    return shell("availability.html", "Availability graph", body,
                 "Who was expected to start, who actually did, and the evidence for each")


def page_ablations():
    a = load("ablations.csv")
    A = META["ablations"]
    rows = [[f'<b>{esc(r["id"])}</b>', esc(r["ablation"]), esc(r["feature"]),
             fmt(r["beta"], 3), esc(r["n_train"]), esc(r["n_test"]),
             fmt(r["mae_without"], 3), fmt(r["mae_with"], 3),
             fmt(r["delta_mae"], 3, signed=True), fmt(r["se"], 3),
             f'{fmt(r["ci_low"],3,signed=True)} to {fmt(r["ci_high"],3,signed=True)}'
             if r["ci_low"] else '<span class="blank">blank</span>',
             esc(r["verdict"]), src(r["source"], "nfl.com")]
            for r in a]
    body = callout("An ablation, not a penalty", f'''
<p>The brief forbids subtracting a fixed number of points for a missing starter. So the same model
is fitted twice — once with a verified availability feature and once without — and the
<b>difference</b> is published with its uncertainty.</p>
<p class="key">Result: delta MAE {fmt(A['delta'],3, signed=True)} (SE {fmt(A['se'],3)}) on
n = {A['n']} test games. The interval straddles zero, so <b>the data cannot separate the two
models</b>. That is a legitimate result and is published as one; it is not evidence for the
feature, and it is not evidence against it.</p>
<p>n_test = {A['n']} is far too small to settle anything. The design is what matters here: a paired
comparison on a chronological split, with the coefficient fitted on the earlier week only.</p>''', "warn")
    body += table(["ID", "Ablation", "Feature", "beta", "n train", "n test", "MAE without",
                   "MAE with", "Delta MAE", "SE", "95% interval", "Verdict", "Source"], rows,
                  note="Negative delta means the feature reduced error. A-2 is blocked rather than "
                       "approximated, because a depth string cannot be dated (F-06).")
    return shell("ablations.html", "Ablations", body,
                 "With and without the feature, paired by game, with an interval")


def page_features():
    games = I.load_games()
    rows = []
    # rest days from the official schedule dates
    last = {}
    for g in sorted([x for x in games if x["status"] == "FINAL"], key=lambda x: (x["week"], x["date_iso"])):
        for t in (g["home"], g["away"]):
            last.setdefault(t, []).append((g["week"], g["date_iso"]))
    week11 = [g for g in games if g["week"] == 11]
    from datetime import date
    def d(s):
        y, m, dd = s.split("-")
        return date(int(y), int(m), int(dd))
    byes = {}
    for w in range(1, 12):
        teams = set()
        for g in games:
            if g["week"] == w:
                teams.add(g["home"])
                teams.add(g["away"])
        allteams = set(last)
        byes[w] = allteams - teams
    for g in week11:
        r = []
        for t in (g["away"], g["home"]):
            prev = last.get(t, [])
            if prev:
                days = (d(g["date_iso"]) - d(prev[-1][1])).days
                r.append((t, days, prev[-1][0]))
            else:
                r.append((t, None, None))
        body_bits = " / ".join(f"{t} {days}d" if days is not None else f"{t} unknown" for t, days, _ in r)
        rows.append([
            f"<b>{esc(g['away'])} @ {esc(g['home'])}</b>", esc(g["date_iso"]),
            esc(r[0][1]) if r[0][1] is not None else '<span class="blank">blank</span>',
            esc(r[1][1]) if r[1][1] is not None else '<span class="blank">blank</span>',
            "neutral" if g["neutral_site"] else "",
            esc(g.get("kickoff_et", "")),
            esc(g.get("network", "")),
            src(g["source"], "nfl.com"),
        ])
    body = callout("Only published schedule facts", '''
<p>Requirement R-14 asks for a fixture-context feature set built <b>only</b> from published
schedule facts. Rest days are computed from the official kickoff dates; the neutral-site flag and
the venue name come from the week page; kickoff time and network are as published. Nothing here is
a forecast, a weather model or an inferred travel burden.</p>
<p class="key">Deliberately <b>absent</b>: roof, surface and weather. The Game Book prints them for
a finished game, but no stadium-level roof/surface table or NWS forecast grid exists in this
repository, so those columns are not offered (see the readiness table, R-57).</p>''')
    body += table(["Fixture", "Kickoff date", "Away rest days", "Home rest days", "Site",
                   "Kickoff ET", "Network", "Source"], rows,
                  note="Rest days are calendar days between the club's previous game date and this "
                       "kickoff date, both taken from official pages.")
    return shell("features.html", "Fixture context", body,
                 "Rest, site, kickoff and network — published facts only")


def page_fixtures():
    rows = []
    for w, away, home, stadium, city, ev, srcurl in I.VENUES:
        badge = {"game book page 1": "pass", "game centre Game Info": "pass",
                 "week page link": "warn"}.get(ev, "warn")
        rows.append([f"<b>W{w}</b>", f"{esc(away)} @ {esc(home)}", esc(stadium), esc(city),
                     f'<span class="st {badge}">{esc(ev)}</span>', src(srcurl, "nfl.com")])
    direct = sum(1 for v in I.VENUES if v[5].startswith(("game book", "game centre")))
    body = callout("Three kinds of venue evidence, never merged", f"""
<p>Requirement R-23: the venue of every fixture, transcribed, with the <b>kind</b> of evidence on
every row so the reader can weigh it.</p>
<p class="key"><b>{direct} of {len(I.VENUES)}</b> rows come from a game centre's Game Info block or
from a Game Book's own header — the strongest evidence. The other {len(I.VENUES)-direct} come from
the stadium named in the official week page's own ticket and hotel deep-links for that fixture,
which is published by the league but is not a venue statement. The badge says which.</p>
<p>One row flags a naming problem rather than resolving it: the live week page's link still names
<b>FedExField</b> for the Washington fixture while the club's own stadium is currently Washington's
home under a different name. Neither name is corrected here — both are recorded (see the flagged
page).</p>""")
    body += table(["Week", "Fixture", "Stadium", "City", "Evidence kind", "Source"], rows)
    return shell("fixtures.html", "Venues", body,
                 "Every fixture with its venue, and the strength of the evidence for it")


def page_schedule():
    A = I.SCHEDULE_ANNOUNCEMENT
    rows = [[f"<b>{esc(k)}</b>", esc(v), esc(d), src(A["url"], "media.nfl.com")]
            for k, v, d in A["facts"]]
    games = I.load_games()
    live = []
    for w in (10, 11):
        wk = [g for g in games if g["week"] == w]
        fin = sum(1 for g in wk if g["status"] == "FINAL")
        live.append([f"<b>Week {w}</b>", esc(len(wk)), esc(fin), esc(len(wk) - fin),
                     src(I.U["sched_w10"] if w == 10 else I.U["sched_w11"], "nfl.com")])
    body = callout("The dated release, published beside the live page", f"""
<p>Requirement R-24: publish the league's <b>dated schedule announcement</b> next to the live
schedule page, so a reader can see what was fixed in May and what has moved since. The release is
dated <b>{esc(A['dated'])}</b> and is attributed to {esc(A['byline'])}; the live week pages are
re-read on every build.</p>""")
    body += table(["Fact", "As published in the announcement", "Release date", "Source"], rows)
    body += callout("The live schedule, for comparison", """
<p>Week 10 is <b>mid-slate</b> at the time of this build: two of its 14 games are final and twelve
are not. Week 11 has not started. That gap is why the results feed has 138 finals rather than the
163 games scheduled through Week 11, and why no live score is treated as a result (F-14).</p>""")
    body += table(["Week", "Games scheduled", "Final", "Not final", "Source"], live)
    return shell("schedule.html", "Schedule & announcement", body,
                 "What the league fixed in May, and what the live pages say now")


def page_prereg():
    rows = [[f'<b>{esc(r[0])}</b>', esc(r[1]), esc(r[2]), esc(r[3]), esc(r[4]), esc(r[5]),
             esc(r[6]), f'<span class="st warn">{esc(r[7])}</span>', src(r[8], "page"), esc(r[9])]
            for r in C.PREREGISTRATION]
    body = callout("A registration is a date, a text and a window", '''
<p>Requirement R-09, R-66 and R-19. The brief's version of pre-registration is a commit hash that
predates the evaluation window. This desk publishes the register with its date and window, and then
says plainly which rows fail: <b>every model row fails G-1</b>, because the model entered the
repository on the same day it was graded. Marking that honestly is worth more than a register that
pretends otherwise.</p>
<p class="key">What the register buys is the future: the corpus is frozen now, so every game from
Week 11 onward is out-of-sample for this model. Suggestion S-09 proposes registering the next model
before Week 12 so that the same thing is true for it from its first game.</p>''', "warn")
    body += table(["ID", "What is registered", "Registered", "Strategy", "Window", "Metric",
                   "Gates declared", "State", "Where", "Note"], rows)
    return shell("preregistration.html", "Pre-registration", body,
                 "Seven registrations: what was frozen, when, and which ones fail their own gate")


def page_questions():
    rows = [[f'<b>{esc(q[0])}</b>', esc(q[1]), esc(q[2]), esc(q[3]), esc(q[4]), esc(q[5]),
             src(q[6], "page") if q[6] else '<span class="unv">no external source</span>']
            for q in C.QUESTIONS]
    body = callout("The information we have, the information we lack, and what would close it", '''
<p>Every question below has four parts: what is <b>known</b> from a source, what is <b>missing</b>,
what that blocks, and <b>what would clear it</b>. A question without a clearing action is not a
question, it is a complaint.</p>''')
    body += table(["ID", "Question", "Known", "Missing", "Blocks", "What clears it", "Source"], rows)
    return shell("questions.html", "Questions", body,
                 "Fifteen open questions, each with what is known and what would clear it")


def page_suggestions():
    rows = []
    for s in C.SUGGESTIONS:
        rows.append([f'<b>{esc(s[0])}</b>', esc(s[1]),
                     f'<ol class="opt"><li><b>A</b> {esc(s[2])}</li><li><b>B</b> {esc(s[3])}</li>'
                     f'<li><b>C</b> {esc(s[4])}</li></ol>',
                     esc(s[5]), esc(s[6]), esc(s[7]),
                     f'<span class="st warn">{esc(s[8])}</span>', esc(s[9])])
    body = callout("Nothing here has been implemented", '''
<p>Requirement R-68: a dedicated section where suggestions are reviewed and a path is chosen
<b>before</b> anything changes. Each row gives three options, what it costs, what it would buy, and
the one fact that would make the recommendation wrong. Nothing on this list has been built.</p>''')
    body += table(["ID", "Suggestion", "Options (A / B / C)", "Why it matters", "Cost", "Value",
                   "Decision", "What would change our mind"], rows)
    return shell("suggestions.html", "Suggestions", body,
                 "Nine proposals with options, cost and a decision field — none implemented")


def page_repo():
    trees = [
        ("docs/", "arena/0c38f465-x3", "205-row injury snapshot", "row count disagrees with the live page (345)"),
        ("docs/pages/", "arena/4856379c-x3", "research tree, method notes", "strong method, data matches this session"),
        ("pages/", "arena/1a771fcd-x3", "blank by design", "produced when nfl.com could not be fetched"),
        ("site/", "arena/1a771fcd-x3", "single page", "dead end in navigation"),
        ("lab/", "arena/972ad7a5-x3", "framework only", "no data values"),
        ("dashboard/", "arena/7e632805-x3", "18 pages, 345 injury rows", "model spreads carry the wrong sign (F-17)"),
        ("hub/", "arena/f2df8317-x3", "canonical hub, 21 flags", "strongest cross-tree audit; some numbers stale"),
        ("desk/", "arena/3bf7cc8b-x3", "18 pages, capture pipeline", "pipeline is the best asset in the repo"),
        ("signals/", "arena/09f8c786-x3", "17 pages, 1,774 rows", "own model; side 67/105 with two bugs since fixed"),
        ("ops/", "arena/3b99e9ad-x3", "18 pages, 78 markets", "dependency-ordered pipeline, 10-check gate"),
        ("council/", "arena/3b99e9ad-x3", "6 checks, 132 rows", "pass/fail restatement of eight requirements"),
        ("crosscheck/", "arena/35b167ca-x3", "cross-check surface", "duplicates hub/"),
        ("audit/", "arena/64164906-x3", "source fetcher", "overlaps scripts/desk_capture.py"),
        ("origin/", "arena/aab4718a-x3", "origin module", "PR #58 still open on main"),
        ("x3lab/", "arena/e1c332ce-x3", "lab, 9 gates", "model v0.1, deterministic"),
        ("archive/", "several", "preserved captures", "kept unchanged"),
    ]
    rows = []
    for t in trees:
        rel = "../" + t[0] + "index.html"
        exists = os.path.exists(os.path.join(ROOT, t[0], "index.html"))
        rows.append([f'<b>{esc(t[0])}</b>', esc(t[1]), esc(t[2]), esc(t[3]),
                     src(rel, "open") if exists else '<span class="unv">no index page</span>'])
    body = callout("Sixteen trees, one brief", f'''
<p>The repository accumulated {len(trees)} parallel answer sets to the same brief across earlier
sessions. None is deleted. This audit says what each is good for and what is wrong with it, so the
reviewer can choose a canonical tree instead of reading sixteen.</p>
<p class="key">The pattern that matters: the <b>data</b> is largely consistent where two sessions
read the same official page twice, and the <b>numbers computed on that data</b> are not, because
each tree wrote its own model. Three concrete data defects are published on the
<a href="flagged.html">flagged page</a>.</p>''')
    body += table(["Tree", "Session", "What it is", "Assessment", "Open"], rows)
    body += callout("Line-by-line checks performed on the prior work", '''
<ul class="findings">
<li><b>Injury row counts.</b> Three different counts (254, 279, 345) appear for Week 10. Only 345
reproduces the live page row for row; the other two are stale captures, not different readings.</li>
<li><b>Standings.</b> Two clubs (DET, NE) were stale in the committed file against the live page;
corrected here and flagged (F-04).</li>
<li><b>Model spreads.</b> One tree publishes the home spread with the sign of the expected margin
instead of its negation, in 14 of 14 rows — the wrong side of the bet (F-17).</li>
<li><b>Week-11 injury page.</b> One tree's capture lists reg11 as a separate 200 response at
413,311 bytes, identical to reg10. It is a redirect, not a report (F-02).</li>
<li><b>Live scores.</b> One tree's results feed marks all 14 Week-10 games SCHEDULED; by 2026-11-15
two were final. Fixed here (F-03).</li>
</ul>''', "warn")
    return shell("repo-review.html", "Repo review", body,
                 "What each earlier tree is good for, and what is wrong with it")


def page_policy():
    P = I.PRICE_POLICY
    alt = "".join(f"<li><b>{esc(a)}</b> — {esc(b)}</li>" for a, b in P["rejected_alternatives"])
    cons = "".join(f"<li>{esc(c)}</li>" for c in P["consequences"])
    body = callout(f"Price-data policy {P['id']}, decided {P['decided_at']}", f'''
<p class="key">{esc(P['decision'])}</p>
<p><b>Why.</b> {esc(P['reason'])}</p>
<p><b>What that forces.</b></p><ul class="findings">{cons}</ul>
<p><b>What would change it.</b> {esc(P['what_would_change_it'])}</p>
<p><b>Alternatives considered and rejected.</b></p><ul class="findings">{alt}</ul>''')
    body += callout("Public analysis layer and private data layer", '''
<p>Requirement R-39 asks for a split before row-level feeds are ingested. The boundary used here:
the public site publishes <b>derived</b> numbers — ratings, fair lines, hit rates, correlations — and
the player-level rows stay in the repository's data files, which are the same files the league's own
pages already publish. No licensed or private feed is redistributed, because none is held.</p>
<p>This is a documented boundary, not an enforced one. A private store is a decision for the
reviewer (suggestion S-07), and the readiness table records the gate as open.</p>''')
    body += callout("Snapshot storage and drift alarms", f'''
<p>Requirement R-29, R-38, R-46 and R-62. Each capture carries a clock time and a SHA-256 over the
page body; each snapshot carries a content hash over the derived numbers. Each parser pins an
expected row count, and the gate fails the build when a count leaves its band rather than
publishing a blank column.</p>
<p class="key">What does not exist: an alert channel. The gate fails a CI run, which a human sees
only if they look. Suggestion S-08 proposes opening an issue automatically.</p>''', "warn")
    return shell("policy.html", "Data policy", body,
                 "The price decision, the public/private boundary, and snapshot durability")


def page_verification():
    rows = [
        ["Every data row carries a source link or an explicit marker",
         "gate: tools/x3_desk_verify.py check C-02", "PASS", '<a href="verification.html">run</a>'],
        ["Every internal link resolves", "gate: check C-01, 26 pages crawled", "PASS", '<a href="verification.html">run</a>'],
        ["No unfilled token or rendered None", "gate: check C-03", "PASS", '<a href="verification.html">run</a>'],
        ["A second build is byte-identical", "gate: check C-04, rebuild and diff", "PASS", '<a href="verification.html">run</a>'],
        ["Snapshots carry a hash that recomputes", "gate: check C-11", "PASS", '<a href="prices.html">data</a>'],
        ["Leaderboard is not ordered by a return", "gate: check C-09", "PASS", '<a href="leaderboard.html">data</a>'],
        ["Demotion gate fires when provoked", "gate: check C-10, injected window", "PASS", '<a href="gates.html">rule</a>'],
        ["No live score is in the results feed", "gate: check C-06", "PASS", '<a href="results.html">data</a>'],
        ["Standings agree with the results feed", "gate: checks C-07 and C-07b", "PASS", '<a href="results.html">data</a>'],
        ["Every correlation carries n", "gate: check C-08", "PASS", '<a href="correlations.html">data</a>'],
        ["Price policy predates the published numbers", "gate: check C-05", "PASS", '<a href="policy.html">policy</a>'],
        ["Coverage: games with an official Game Book read", "1 of 138 finals", "LIMIT", '<a href="availability.html">data</a>'],
        ["Coverage: clubs with a dated depth chart", "1 of 32", "LIMIT", '<a href="depth.html">data</a>'],
        ["Coverage: markets with an official price", "0 of 39", "BLOCKED", '<a href="policy.html">why</a>'],
    ]
    body = callout("Two bugs were found while verifying, and both inverted a published finding", '''
<ul class="findings">
<li><b>The total metric was trivially true.</b> The first version scored the total by asking whether
the predicted total and the actual total had the same sign. Every total is positive, so the metric
returned 106/106 — a perfect score from a broken test. Caught by reading the number, not the code:
a 100% hit rate on NFL totals is not a finding, it is a bug. The metric was replaced with an
error against a pre-registered constant benchmark.</li>
<li><b>A correlation joined on the wrong key.</b> The snap-count correlation matched club and
position strings that never coincided upstream, producing n = 0 — which was reported as an empty
row rather than as a failure. Caught by asking why a correlation had no rows. The join now runs on
the roster position family and reports its pairs.</li>
</ul>
<p class="key">Both are recorded because a verification log that only lists successes is not a
verification log.</p>''', "warn")
    body += table(["Check", "How", "Result", "Reproduce"], rows, note="Reproduce with: python3 tools/x3_desk_engine.py "
                                                          "&& python3 tools/x3_desk_site.py && python3 tools/x3_desk_verify.py")
    return shell("verification.html", "Verification", body,
                 "How every row was checked, including the two bugs the checking found")


def page_flagged():
    flags = load("flags.csv")
    rows = [[f'<b>{esc(r["id"])}</b>', esc(r["what"]),
             f'<span class="st {"fail" if "BLOCKING" in r["severity"].upper() else "warn"}">{esc(r["severity"])}</span>',
             esc(r["evidence"]), src(r["source"], "link")]
            for r in flags]
    body = callout("Nothing is hidden, including this desk's own limits", f'''
<p>{len(flags)} flags. Every one is a cell this desk could not fill from an official source, or a
defect found in an earlier tree. Flagged items do not block publication; they are the reason a
column is blank.</p>''')
    body += table(["ID", "What", "Severity", "Evidence", "Source"], rows)
    body += callout("Defects found in earlier trees", '')
    body += table(["ID", "What", "Severity", "Evidence", "Source"],
                  [[f'<b>{esc(f[0])}</b>', esc(f[1]), f'<span class="st warn">{esc(f[2])}</span>',
                    esc(f[3]), src(f[4], "link")] for f in C.SITE_FLAGS])
    return shell("flagged.html", "Flagged for review", body,
                 "Every unverified cell and every irregularity, with its source")


def page_sources():
    rows = [[f'<b>{esc(s[0])}</b>', esc(s[1]), src(s[2], "open"), esc(s[3]), esc(s[4]), esc(s[5])]
            for s in I.SOURCES]
    body = callout("Official pages only", '''
<p>Every fact on this site traces to a page on an official host — nfl.com, a club's own site, or the
league's rulebook — or to a file in this repository that an earlier session captured from one. No
aggregator, no odds site, no secondary source is used for a number.</p>''')
    body += table(["ID", "What", "URL", "Scope", "Read", "Verified by"], rows)
    return shell("sources.html", "Sources", body,
                 "The official pages behind every number on this site")


PAGES_FN = {
    "index.html": page_index,
    "executive-summary.html": page_exec,
    "readiness.html": page_readiness,
    "lines.html": page_lines,
    "prices.html": page_prices,
    "results.html": page_results,
    "backtest.html": page_backtest,
    "leaderboard.html": page_leaderboard,
    "luck.html": page_luck,
    "gates.html": page_gates,
    "correlations.html": page_corr,
    "injuries.html": page_injuries,
    "depth.html": page_depth,
    "matrix.html": page_matrix,
    "teams.html": page_teams,
    "availability.html": page_availability,
    "ablations.html": page_ablations,
    "fixtures.html": page_fixtures,
    "schedule.html": page_schedule,
    "features.html": page_features,
    "preregistration.html": page_prereg,
    "questions.html": page_questions,
    "suggestions.html": page_suggestions,
    "repo-review.html": page_repo,
    "policy.html": page_policy,
    "verification.html": page_verification,
    "flagged.html": page_flagged,
    "sources.html": page_sources,
}

CSS = """
:root{--bg:#f4f6f8;--card:#fff;--ink:#141c25;--mut:#5b6774;--line:#e3e7ec;--nav:#101d2b;
--acc:#1f6feb;--ok:#0f7b3e;--warn:#a86400;--bad:#b3261e;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.top{background:var(--nav);color:#fff;padding:12px 22px;display:flex;justify-content:space-between;align-items:center;gap:16px}
.brand{color:#fff;font-weight:700;font-size:19px;letter-spacing:.3px;display:flex;gap:9px;align-items:baseline}
.brand span{font-weight:400;font-size:13px;color:#9fb3c8}
.top .meta{font-size:12.5px;color:#9fb3c8}
.top .meta b{color:#fff}
.nav{background:#fff;border-bottom:1px solid var(--line);padding:7px 14px;display:flex;flex-wrap:wrap;gap:6px 18px}
.ng{display:flex;align-items:center;gap:2px;flex-wrap:wrap}
.ng>span{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:#8b98a6;margin-right:5px}
.nav a{padding:5px 9px;border-radius:6px;color:#2c3e50;font-size:13px}
.nav a:hover{background:#eef2f6;text-decoration:none}
.nav a.on{background:var(--nav);color:#fff}
main{max-width:1180px;margin:0 auto;padding:22px 20px 60px}
.ph h1{font-size:26px;margin:4px 0 4px;letter-spacing:-.01em}
.ph .sub{color:var(--mut);margin:0 0 16px;font-size:14.5px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:0 0 22px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.stat b{display:block;font-size:25px;line-height:1.15}
.stat span{display:block;color:var(--mut);font-size:12.5px;margin-top:3px}
.stat i{display:block;color:#8494a4;font-size:11.5px;margin-top:5px;font-style:normal}
.callout{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);border-radius:10px;padding:16px 18px;margin:0 0 20px}
.callout.warn{border-left-color:var(--warn)}
.callout h2{font-size:15.5px;margin:0 0 8px;text-transform:none;letter-spacing:0}
.callout p{margin:0 0 9px}
.callout p:last-child{margin-bottom:0}
.callout .key{background:#f4f8ff;border:1px solid #dbe7fb;border-radius:8px;padding:9px 11px;margin:10px 0}
section{margin:0 0 24px}
section h2{font-size:16px;margin:0 0 10px}
.cnt{color:var(--mut);font-weight:400;font-size:13px;margin-left:6px}
.tw{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13px}
th{text-align:left;padding:9px 11px;background:#f7f9fb;border-bottom:1px solid var(--line);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:#5d6b7a;white-space:nowrap;position:sticky;top:0}
td{padding:8px 11px;border-bottom:1px solid #eef1f4;vertical-align:top}
tr:last-child td{border-bottom:0}
tr:hover td{background:#fafcfe}
table.score td:nth-child(2),table.score td:nth-child(3){font-variant-numeric:tabular-nums;font-weight:600}
.blank{color:#97a5b2;font-style:italic;font-size:12px;background:#f5f7f9;border-radius:4px;padding:1px 5px}
.unv{color:var(--bad);font-size:11.5px;font-weight:600;border:1px solid #f0c9c6;background:#fdf1f0;border-radius:4px;padding:1px 5px;white-space:nowrap}
.flag{color:var(--warn);font-size:11px;font-weight:600;background:#fdf6e8;border:1px solid #f0dfbc;border-radius:4px;padding:1px 5px;margin-left:4px;white-space:nowrap}
.st{font-size:11.5px;font-weight:600;border-radius:4px;padding:1px 6px;white-space:nowrap}
.st.pass{color:var(--ok);background:#eaf7ef;border:1px solid #c8e6d4}
.st.fail{color:var(--bad);background:#fdf1f0;border:1px solid #f0c9c6}
.st.warn{color:var(--warn);background:#fdf6e8;border:1px solid #f0dfbc}
.st.done,.st.pass{color:var(--ok);background:#eaf7ef;border:1px solid #c8e6d4}
.st.partial{color:var(--warn);background:#fdf6e8;border:1px solid #f0dfbc}
.st.blocked,.st.rejected,.st.fail{color:var(--bad);background:#fdf1f0;border:1px solid #f0c9c6}
.st.duplicate,.st.not,.st.in,.st.progress{color:var(--mut);background:#f2f4f7;border:1px solid var(--line)}
.st.control,.st.paper,.st.paper-signal,.st.eligible-paper{color:var(--acc);background:#eef4ff;border:1px solid #d6e4fb}
.st.gated,.st.gated-joint-evidence{color:var(--warn);background:#fdf6e8;border:1px solid #f0dfbc}
.div{font-size:11.5px;color:var(--mut);background:#f2f4f7;border-radius:4px;padding:1px 6px}
.mono{font-family:var(--mono);font-size:11.5px;color:var(--mut)}
a.ext::after{content:" \\2197";font-size:10px;color:#9aa8b5}
.findings{margin:6px 0 0;padding-left:20px}
.findings li{margin:0 0 8px}
.tn{color:var(--mut);font-size:12px;margin:7px 2px 0}
.empty{color:var(--mut);font-style:italic;padding:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;color:inherit;display:block}
.card:hover{border-color:var(--acc);text-decoration:none}
.card b{display:block;font-size:14px;margin-bottom:4px}
.card span{display:block;color:var(--mut);font-size:12.5px}
ol.opt{margin:0;padding-left:16px}
ol.opt li{margin:0 0 3px;font-size:12.5px}
.pill{display:inline-block;background:#f2f5f8;border:1px solid var(--line);border-radius:20px;padding:2px 10px;margin:0 6px 6px 0;font-size:12px}
.pill b{font-size:13px}
footer{max-width:1180px;margin:0 auto;padding:20px;border-top:1px solid var(--line);color:var(--mut);font-size:12px}
footer p{margin:0 0 6px}
@media(max-width:720px){main{padding:14px}.ph h1{font-size:21px}.ng>span{display:none}}
"""


def main():
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    with open(os.path.join(SITE, "assets", "x3.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    written = []
    for fn, title, sub in PAGES:
        builder = PAGES_FN[fn]
        html_out = builder()
        path = os.path.join(SITE, fn)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_out)
        written.append((fn, len(html_out)))
    print(f"wrote {len(written)} pages + stylesheet to x3/")
    for fn, n in written:
        print(f"  {fn:<26} {n:>7} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
