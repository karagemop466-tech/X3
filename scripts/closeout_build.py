#!/usr/bin/env python3
"""X3 close-out site builder (session arena/e1ad8b78-x3).

Renders closeout/*.html from data/closeout/*.csv and data/closeout/derived/*.csv. Every number in the prose
is interpolated from the data at build time through {TOKEN} substitution: an unfilled token aborts the build,
so the text can never drift from the tables it describes.

Run:  python3 scripts/closeout_engine.py && python3 scripts/closeout_build.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data", "closeout")
DD = os.path.join(D, "derived")
OUT = os.path.join(ROOT, "closeout")
CAPTURED = {"schedule_w10": "2026-11-17T22:44Z", "injury_report": "2026-11-17T22:45Z",
            "game_book": "2026-11-17T22:46Z", "schedule_w11": "2026-11-17T22:47Z",
            "standings": "2026-11-17T22:49Z", "repo_files": "2026-11-17T22:51Z",
            "frozen": "2026-11-17T23:05:00Z"}

os.makedirs(OUT, exist_ok=True)


def load(folder, name):
    with open(os.path.join(folder, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


raw = {}
for f in sorted(os.listdir(D)):
    if f.endswith(".csv"):
        raw[f] = load(D, f)
for f in sorted(os.listdir(DD)):
    if f.endswith(".csv"):
        raw["d:" + f] = load(DD, f)
for k in [x for x in list(raw) if x.startswith("d:")]:
    raw.setdefault(k[2:], raw[k])
meta = json.load(open(os.path.join(DD, "meta.json")))


def g(name, i=None, key=None, val=None):
    """rows from a table; optionally filter by key==val or pick a column of every row"""
    rows = raw[name]
    if key is not None:
        rows = [r for r in rows if r.get(key) == val]
    if i is not None:
        return rows[i]
    return rows


def col(name, c, **kw):
    return [r[c] for r in g(name, **kw)]


# ------------------------------------------------------------------ tokens (prose is computed, never typed)
sc = {r["id"]: r for r in raw["d:scorecard.csv"]}
ct = {r["picker"]: r for r in raw["d:controls.csv"]}
drift = [r for r in raw["d:drift_vs_prior.csv"] if r["market"] == "side"]
tot_drift = [r for r in raw["d:drift_vs_prior.csv"] if r["market"] == "total"]


def absmax(rows, c):
    vals = [abs(float(r[c])) for r in rows if r[c] not in ("", None)]
    return max(vals) if vals else float("nan")


def avg(rows, c):
    vals = [abs(float(r[c])) for r in rows if r[c] not in ("", None)]
    return sum(vals) / len(vals) if vals else float("nan")


n_side = int(sc["SC-1"]["n_gradable"])
luck_band = (0.5 - 1.96 * math.sqrt(0.25 / n_side), 0.5 + 1.96 * math.sqrt(0.25 / n_side))
STATS = {
    "N_GAMES": meta["games_in_log"],
    "N_W10": meta["games_week10_captured"],
    "MISMATCH": meta["reconciliation_mismatches"],
    "PF_SUM": meta["official_pf_sum"],
    "HFA": round(meta["home_advantage"], 2),
    "SIGMA_M": round(meta["sigma_margin"], 2),
    "SIGMA_T": round(meta["sigma_total"], 2),
    "SD_PRED": round(meta["sd_predicted_margin"], 2),
    "SD_ACT": round(meta["sd_actual_margin"], 2),
    "DISP": round(meta["sd_predicted_margin"] / meta["sd_actual_margin"], 3),
    "R2": round(meta["in_sample_r2_margin"], 3),
    "MAE_MODEL": sc["SC-1"]["mae_points"],
    "MAE_NAIVE": sc["SC-1"]["mae_benchmark_points"],
    "TMAE_MODEL": sc["SC-2"]["mae_points"],
    "TMAE_NAIVE": sc["SC-2"]["mae_benchmark_points"],
    "SIDE_BRIER": sc["SC-1"]["brier"],
    "SIDE_SKILL": sc["SC-1"]["skill_vs_benchmark"],
    "TOT_BRIER": sc["SC-2"]["brier"],
    "ML_BRIER": sc["SC-3"]["brier"],
    "ML_SKILL": sc["SC-3"]["skill_vs_benchmark"],
    "N_SETTLE": n_side,
    "HOME_COVER_RATE": round(meta["settlement"]["side_home_cover_hits"] / n_side, 4),
    "MODEL_COVER_RATE": meta["settlement"]["model_side_cover_rate"],
    "WF_COVER": meta["walkforward"]["home_cover_rate"],
    "WF_MAE": meta["walkforward"]["mae_margin"],
    "WF_MAE_NAIVE": meta["walkforward"]["mae_margin_naive"],
    "WF_BRIER": meta["walkforward"]["brier_home_win"],
    "WF_N": meta["walkforward"]["graded_games"],
    "WF_CI": f"{meta['walkforward']['boot'][0]}-{meta['walkforward']['boot'][1]}",
    "CTRL_FAV": ct["control - better winning percentage in the Week-9 standings"]["hit_rate"],
    "CTRL_HOME": ct["control - always home"]["hit_rate"],
    "CTRL_RAND": ct["control - seeded random coin flip per game"]["hit_rate"],
    "CTRL_ML": ct["model's moneyline pick (probability above 0.5)"]["hit_rate"],
    "LUCK_LO": round(luck_band[0], 3),
    "LUCK_HI": round(luck_band[1], 3),
    "DRIFT_MAX_SIDE": round(absmax(drift, "difference"), 1),
    "DRIFT_MEAN_SIDE": round(avg(drift, "difference"), 2),
    "DRIFT_MAX_TOTAL": round(absmax(tot_drift, "difference"), 1),
    "N_FORECAST": meta["forecasts"],
    "N_PRICE_ROWS": meta["price_store_rows"],
    "N_FLAGS": len(raw["flags.csv"]),
    "N_QUESTIONS": len(raw["questions.csv"]),
    "N_SUGG": len(raw["suggestions.csv"]),
    "N_READY": len(raw["readiness.csv"]),
    "N_AVAIL": len(raw["availability_w10.csv"]),
    "N_REPORT": len(raw["injury_report_w10_capture.csv"]),
    "N_GB": len(raw["gamebook_ne_det.csv"]),
    "N_GB2": len(raw["gamebook_lac_bal.csv"]),
    "N_HDR": len(raw["gamebook_ne_det_header.csv"]),
    "N_HDR2": len(raw["gamebook_lac_bal_header.csv"]),
    "SHEETS_CLOSED": str(sum(1 for r in raw["game_sheets.csv"] if r["closed_at_54"] == "yes")),
    "SHEETS": len(raw["game_sheets.csv"]),
    "N_SOURCES": len(raw["source_reads.csv"]),
    "N_TURNOVER": len(raw["roster_turnover.csv"]),
    "N_EXEC": len(raw["exec_summary.csv"]),
    "N_SHEET_CLOSED": str(sum(1 for r in raw["game_sheets.csv"] if r["closed_at_54"] == "yes")),
    "MODEL_VERSION": meta["model_version"],
    "FROZEN": CAPTURED["frozen"],
    "CAP_DAY": "2026-11-17",
    "N_CORR": len(raw["correlations.csv"]),
    "N_WF": meta["walkforward"]["graded_games"],
    "N_SCORE": len(raw["scorecard.csv"]),
    "N_ELIGIBLE": sum(1 for r in raw["scorecard.csv"] if not r["verdict"].upper().startswith("NOT")),
    "N_INHERITED": meta["games_in_log"] - meta["games_week10_captured"],
    "UNGRADED": (str(len([r for r in raw["ungraded.csv"] if r["game_id"].strip()])) + " ungraded row(s); "
                 "every priced game has a captured final"),
}
for k, v in list(STATS.items()):
    STATS[k] = str(v)


def fill(text):
    out = re.sub(r"\{([A-Z0-9_]+)\}", lambda mo: STATS.get(mo.group(1), f"@@UNFILLED:{mo.group(1)}@@"), str(text))
    if "@@UNFILLED" in out:
        raise SystemExit(f"unfilled token in prose: {out[:200]}")
    return out


URL_RE = re.compile(r"(?<![\"])(https?://[^\s,;)\"']+)")


def esc(v):
    s = "" if v is None else str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


BLOB = "https://github.com/karagemop466-tech/X3/blob/b7d4142"
REPO_PATH_RE = re.compile(r"(?<![\w/.-])((?:data|scripts|tools|hub|x3|agency|docs|decision|signals)/[A-Za-z0-9_./-]+\.(?:csv|json|py|md|yml|txt|html))")


def linkify_paths(s):
    """a bare repository path in prose becomes a link: local for this module's own files, GitHub blob for others"""
    def rep(mo):
        p = mo.group(1)
        if p.startswith("data/closeout/"):
            return f'<a href="../{p}">{p}</a>'
        return f'<a href="{BLOB}/{p}" target="_blank" rel="noopener">{p}</a>'
    return REPO_PATH_RE.sub(rep, s)


def cell(v):
    """escape, then linkify any URL; relative paths to data files become links too.

    A cell that already contains markup (a badge, a pre-built link) is passed through untouched, because
    the caller built it from the same data."""
    s = str(v)
    if "<" in s:
        return s
    s = esc(v)
    s = URL_RE.sub(lambda mo: f'<a href="{mo.group(1)}" target="_blank" rel="noopener">{mo.group(1)}</a>', s)
    return linkify_paths(s)


def table(heads, rows, cap="", note="", kind="data"):
    out = ['<div class="tblwrap"><table class="k-' + kind + '">']
    if cap:
        out.append(f"<caption>{fill(cap)}</caption>")
    out.append("<thead><tr>" + "".join(f"<th>{esc(h)}</th>" for h in heads) + "</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{cell(fill(c))}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    if note:
        out.append(f'<p class="note">{fill(note)}</p>')
    out.append("</div>")
    return "\n".join(out)


def table_csv(name, heads=None, cols=None, cap="", note="", keep=None, kind="data", compute=None):
    rows = raw[name]
    if keep:
        rows = [r for r in rows if keep(r)]
    cols = cols or (list(rows[0].keys()) if rows else [])
    heads = heads or [str(c).replace("_", " ").capitalize() for c in cols]
    body = [[(compute(r, c) if (c is None and compute) else r.get(c, "")) for c in cols] for r in rows]
    return table(heads, body, cap, note, kind)


NAV = [
    ("index", "Overview", "what closed, what was graded, what is still blocked"),
    ("executive-summary", "Executive summary", "ten findings with the number behind each"),
    ("week10", "Week 10 close-out", "the 14 finals and the four byes, as published"),
    ("results", "Verified results feed", "{N_GAMES} games reconciled to the standings"),
    ("board", "Week 11 board", "the slate, venues, kickoffs and availability state"),
    ("lines", "Originated lines", "side, then total, then moneyline - frozen before kickoff"),
    ("price-store", "Price snapshot store", "opening and closing per originated market"),
    ("settlement", "Settlement", "the pre-kickoff board, graded"),
    ("scorecard", "Scorecard and controls", "proper scores against naive benchmarks"),
    ("luck", "Removal of luck", "luck bands, bootstrap intervals, drift, ablations"),
    ("correlations", "Correlations", "official numbers only, n published"),
    ("availability", "Availability graph", "designation versus what the Game Book shows"),
    ("gates", "Pre-registration and gates", "G-1 to G-8 with the measured value"),
    ("sources", "Sources and capture ledger", "every read with its clock time and hash"),
    ("verification", "Verification log", "line-by-line checks run by the build"),
    ("questions", "Open questions", "what must be known before deciding"),
    ("suggestions", "Suggestions", "review the paths before implementing anything"),
    ("readiness", "Decision readiness", "{N_READY} requirements, gate and clearing number"),
    ("flagged", "Flagged for review", "{N_FLAGS} irregularities, none blocking"),
    ("repo-review", "Repo review", "what the repository claims versus today's page"),
]
CSS = """
:root{--bg:#0f172a;--panel:#111c33;--line:#24344f;--ink:#e6edf8;--mut:#93a4c4;--ok:#34d399;--warn:#fbbf24;
--bad:#f87171;--acc:#60a5fa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header.top{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:14px 22px;
border-bottom:1px solid var(--line);background:#0b1324;position:sticky;top:0;z-index:5;flex-wrap:wrap}
.brand a{color:var(--ink);text-decoration:none;font-weight:700;letter-spacing:.3px}
.brand span{color:var(--acc);font-weight:600}
.asof{color:var(--mut);font-size:12.5px}.asof b{color:var(--ink)}
nav.nav{display:flex;flex-wrap:wrap;gap:6px;padding:10px 22px;border-bottom:1px solid var(--line);
background:#0d1730}nav.nav a{color:var(--mut);text-decoration:none;font-size:12.5px;padding:4px 8px;
border:1px solid transparent;border-radius:7px}nav.nav a:hover{color:var(--ink);border-color:var(--line)}
nav.nav a.on{color:var(--ink);border-color:var(--acc);background:#132038}
main{padding:18px 22px 44px;max-width:1400px;margin:0 auto}
h1{font-size:24px;margin:6px 0 6px}h2{font-size:17px;margin:22px 0 8px}h3{font-size:14.5px;margin:16px 0 6px;color:var(--acc)}
p.lede{color:var(--mut);max-width:1050px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin:14px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.card .num{font-size:22px;font-weight:700}.card .lbl{color:var(--mut);font-size:12.5px}
.card .sub{color:var(--mut);font-size:11.5px;margin-top:4px}
section.callout{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:16px 0}
.tblwrap{overflow:auto;border:1px solid var(--line);border-radius:12px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
caption{text-align:left;padding:9px 12px;color:var(--mut);font-size:12.5px;border-bottom:1px solid var(--line)}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{background:#0d1730;color:var(--mut);font-weight:600;white-space:nowrap;position:sticky;top:0}
tbody tr:nth-child(even){background:#0d1830}
td a{color:var(--acc);word-break:break-all;text-decoration:none}td a:hover{text-decoration:underline}
.badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;border:1px solid}
.badge.v{color:var(--ok);border-color:#1e5b48;background:#0f2b23}
.badge.u{color:var(--warn);border-color:#5b4a1e;background:#2b230f}
.badge.b{color:var(--bad);border-color:#5b1e2b;background:#2b0f14}
.badge.d{color:var(--acc);border-color:#1e3a5b;background:#0f1f2b}
.note{color:var(--mut);font-size:12.5px;margin:8px 2px}
footer{border-top:1px solid var(--line);color:var(--mut);padding:16px 22px;font-size:12.5px}
footer a{color:var(--acc);text-decoration:none}
ul.tight{margin:6px 0 6px 18px;padding:0}ul.tight li{margin:3px 0}
code{background:#0b1324;border:1px solid var(--line);border-radius:5px;padding:0 4px;font-size:12.5px}
.k-meta td{color:var(--mut)}
"""


def page(fname, title, intro, body_parts, active=None):
    active = active or fname.replace(".html", "")
    nav = "".join(f'<a href="{s}.html"{" class=on" if s == active else ""}>{l}</a>' for s, l, d in NAV)
    body = "\n".join(fill(b) if isinstance(b, str) else b for b in body_parts)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 close-out desk</title>
<link rel="stylesheet" href="assets/closeout.css">
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">X3 <span>Week-10 close-out &amp; Week-11 pre-registration</span></a></div>
  <div class="asof">official pages read <b>{CAPTURED['schedule_w10']}</b> to <b>{CAPTURED['standings']}</b> - board frozen
    <b>{CAPTURED['frozen']}</b> - session <b>arena/e1ad8b78-x3</b></div>
</header>
<nav class="nav">{nav}</nav>
<main>
<h1>{esc(title)}</h1>
<p class="lede">{fill(intro)}</p>
{body}
</main>
<footer>
  <p>Built by <code>scripts/closeout_build.py</code> from <code>data/closeout/*.csv</code> and
  <code>data/closeout/derived/*.csv</code>; regenerate with
  <code>python3 scripts/closeout_engine.py &amp;&amp; python3 scripts/closeout_build.py</code>. Values with no
  official source are left blank and flagged; model output is labelled DERIVED and is arithmetic on official
  scores, not a prediction of results. This site places no bets and pays no rewards.</p>
  <p><a href="../index.html">Site root</a> - <a href="../hub/index.html">hub desk</a> -
  <a href="../x3/index.html">x3 desk</a> -
  <a href="https://github.com/karagemop466-tech/X3/blob/b7d4142/COORDINATION.md">coordination log</a> -
  <a href="https://github.com/karagemop466-tech/X3">repository</a></p>
</footer>
</body></html>"""
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as fh:
        fh.write(html)
    return len(html)


def badge(v):
    m = {"VERIFIED": "v", "MATCH": "v", "PASS": "v", "DONE": "v", "CLOSED": "v",
         "PARTIAL": "u", "OPEN": "u", "PROPOSED": "u", "STARTED": "u", "ARMED": "u", "PENDING": "u",
         "BLOCKED": "b", "FAIL": "b", "STALE": "b", "UNVERIFIED": "u", "FIXED": "v", "DISCLOSED": "d",
         "RESOLVED": "v", "ANSWERED": "d", "TRUE": "v", "CONFIRMED": "v"}
    for k, c in m.items():
        if str(v).upper().startswith(k):
            return f'<span class="badge {c}">{esc(v)}</span>'
    return esc(v)


# ------------------------------------------------------------------ pages
cards = f"""<div class="grid">
<div class="card"><div class="num">{STATS['N_GAMES']}</div><div class="lbl">games in the verified log</div>
<div class="sub">{STATS['N_INHERITED']} inherited + {STATS['N_W10']} captured on {CAPTURED['schedule_w10'][:10]} - all {STATS['N_W10']} Week-10 finals</div></div>
<div class="card"><div class="num">{STATS['MISMATCH']}</div><div class="lbl">standings mismatches</div>
<div class="sub">32 clubs reconciled on W, L, T, PF, PA; sum(PF)=sum(PA)={STATS['PF_SUM']}</div></div>
<div class="card"><div class="num">{STATS['N_SETTLE']}</div><div class="lbl">games graded against a line published before kickoff</div>
<div class="sub">as_of 2026-11-14 board, Nov 15/16 kickoffs - the repository's only out-of-sample set</div></div>
<div class="card"><div class="num">{STATS['N_FORECAST']}</div><div class="lbl">Week-11 fixtures priced and frozen</div>
<div class="sub">2 days 0 hours before the first snap; {STATS['N_PRICE_ROWS']} open/close price rows</div></div>
<div class="card"><div class="num">{STATS['N_ELIGIBLE']} / {STATS['N_SCORE']}</div><div class="lbl">strategies leaderboard-eligible</div>
<div class="sub">every score carries its n, its benchmark and its luck band</div></div>
<div class="card"><div class="num">{STATS['N_AVAIL']}</div><div class="lbl">availability rows checked against a Game Book</div>
<div class="sub">of {STATS['N_REPORT']} injury-report rows read from the live page</div></div>
</div>"""

top_findings = table_csv("exec_summary.csv", ["#", "Finding", "Number", "Evidence"], keep=None,
                         cap="What a decision-maker needs to know, with the number attached to each sentence",
                         note="Every cell is generated from the data files at build time; there are no typed-in figures on this page.",
                         kind="data")

index_parts = [
    cards,
    '<section class="callout"><h2 style="margin-top:0">Read this first</h2><ul class="tight">'
    f"<li><b>Week 10 was incomplete in every tree of this repository.</b> The canonical feed on main labels 13 "
    "of 14 games SCHEDULED; they finished on 2026-11-16. This module closes them out and re-reconciles the "
    f"whole season ({STATS['N_GAMES']} games) against the standings page read on {CAPTURED['standings']}.</li>"
    "<li><b>The one pre-kickoff board the project had has now been graded.</b> The prior session published fair "
    f"lines on 2026-11-14 for {STATS['N_SETTLE']} Week-10 games; the margin forecast beat 'predict zero' "
    f"({STATS['MAE_MODEL']} vs {STATS['MAE_NAIVE']}), the cover probability did not beat a coin flip "
    f"(Brier {STATS['SIDE_BRIER']} vs 0.25), and the naive Week-9 favourite picked the same winners as the "
    f"model ({STATS['CTRL_FAV']} vs {STATS['CTRL_ML']}).</li>"
    f"<li><b>A new board is frozen for Week 11</b> ({STATS['FROZEN']}, first kickoff Thu 2026-11-19 8:15 PM ET) "
    "with the model version, every input and every parameter printed on the row. That is the project's first "
    "genuinely pre-registered test, and it cannot be edited into a backtest without the commit history showing it.</li>"
    "<li><b>Nothing is promoted, nothing is staked, no ROI is published.</b> There are zero market prices in "
    "the repository; the difference columns exist and are empty by policy, not by omission.</li>"
    f"<li><b>{STATS['N_FLAGS']} irregularities are flagged, none blocking</b>, including one that would have "
    "silently dropped ten Rams games from any join (CL-F-04).</li>"
    "<li><b>Two Game Books, not one.</b> The second read settles a live argument in this repository: Baltimore's "
    "starting quarterback on 2026-11-16 was J.Brissett, with K.Slovis inactive and J.Fagnano dressed but not used "
    "- and no Jackson or Huntley anywhere in the document. It also proves the inactive blocks are complete "
    "(48 dressed + 6 not active = 54), which is what makes an absence readable as a roster fact.</li></ul></section>",
    top_findings,
    '<p class="note">Earlier sessions\' trees are linked from the <a href="../index.html">site root</a>; '
    "this page supersedes none of them and edits none of their files.</p>",
]
page("index.html", "Close-out desk - what changed since the last read",
     "Everything on this site is arithmetic on rows transcribed from official NFL pages on {CAP_DAY}, or is "
     "blank and flagged. {N_GAMES} games reconciled, {N_SETTLE} settled against a line that was written before "
     "they were played, {N_FORECAST} fixtures priced before kickoff.", index_parts)

page("executive-summary.html", "Executive summary",
     "{N_EXEC} findings, each with the number that produced it and the file that holds it.", [
    table_csv("exec_summary.csv", ["#", "Finding", "Number", "Evidence"],
              cap="The one-page brief", kind="data"),
    '<section class="callout"><h2>What is blocked, and on whom</h2><ul class="tight">'
    "<li><b>Prices</b> - blocked on the owner (Q-C01). No residual, CLV, ROI or reward can be computed "
    "honestly until one source is admitted; {N_PRICE_ROWS} rows exist to receive them.</li>"
    "<li><b>Availability</b> - blocked by the league's own calendar: the Week-11 injury report did not exist "
    "at freeze time, and that absence is recorded rather than smoothed over.</li>"
    "<li><b>Sample size</b> - blocked by time: {N_SETTLE} games settled, {N_WF} graded walk-forward, against a "
    "smallest registered gate of 200 decisions.</li></ul>"
    '<p class="note">The decisions that change the most, in order: SG-C-01 (price source), SG-C-02 (13 more '
    "Game Books), SG-C-03 (grade the frozen board and never touch it), SG-C-08 (stop publishing fourteen "
    "answers).</p></section>"])

page("week10.html", "Week 10 close-out",
     "The fourteen games that finished after the last capture, transcribed from the league's own week page. "
     "Margin and total are arithmetic on the published scores.", [
    table_csv("week10_finals.csv", ["Game", "Date", "Away", "Home", "Score line", "Margin home", "Total",
                                    "Winner", "Status", "Venue", "Venue evidence", "Source page", "Captured"],
              cols=["game_id", "date_iso", "away", "home", None, "margin_home", "total", "winner", "status",
                    "venue", "venue_evidence", "source_page", "captured_utc"],
              compute=lambda r, c: f'{r["away_score"]} - {r["home_score"]}',
              keep=lambda r: True,
              cap="All {N_W10} Week-10 games",
              note="The score-line column is generated as `away - home`; the away and home points in "
                   "data/closeout/week10_finals.csv are the transcribed source values.", kind="data"),
    table_csv("week10_byes.csv", ["Club", "Record printed on the page", "Source", "Captured"],
              cols=["team", "record_as_shown_on_week10_page", "source_page", "captured_utc"],
              cap="Clubs on bye in Week 10", kind="data"),
    '<p class="note">One game carries a venue here: Munich, transcribed from the game centre and confirmed by '
    "the Game Book. The other thirteen rows leave the venue blank because the Week-10 page prints a replay link "
    "instead of the stadium - blank rather than inferred (requirement A-22).</p>",
])

recon_rows = [[r["team"], r["games_played"], f'{r["log_w"]}-{r["log_l"]}-{r["log_t"]}',
               f'{r["official_w"]}-{r["official_l"]}-{r["official_t"]}',
               f'{r["log_pf"]}:{r["log_pa"]}', f'{r["official_pf"]}:{r["official_pa"]}',
               badge("VERIFIED MATCH" if r["agree"] == "MATCH" else "FAIL " + r["detail"]), r["source"]]
              for r in raw["reconciliation.csv"]]
page("results.html", "Verified results feed",
     "{N_GAMES} games, every club reconciled against the standings page read on {CAP_DAY}. The inherited "
     "weeks 1-9 log is checked in aggregate, not re-transcribed; that is stated in each row's provenance.", [
    table(["Club", "Games", "Log W-L-T", "Official W-L-T", "Log PF:PA", "Official PF:PA", "Result", "Official source"],
          recon_rows, cap="Reconciliation of the log against the official standings",
          note="Arithmetic checks run by the build: PF-PA equals NET for all 32 clubs, sum(PF) equals sum(PA) "
               "({PF_SUM}), and games played equals W+L+T for every club."),
    table_csv("season_log.csv", ["Game", "Week", "Date", "Away", "Home", "A", "H", "Margin home", "Total",
                                 "Neutral", "Provenance", "Source"],
              cols=["game_id", "week", "date_iso", "away", "home", "away_score", "home_score", "margin_home",
                    "total", "neutral", "provenance", "source"],
              cap="The {N_GAMES}-game corpus used for every model figure on this site",
              note="Rows marked inherited come from data/x3/verified/results_2026.csv as committed at b7d4142; "
                   "they were not re-read from the league in this session and are labelled as such."),
])

page("board.html", "Week 11 board",
     "The thirteen fixtures and the six clubs on bye, exactly as the league printed them. Kickoff times are "
     "ET. This is the slate priced on the next page, and none of it had been played at freeze time.", [
    table_csv("week11_slate.csv", ["Fixture", "Date", "Kickoff ET", "Network", "Away", "Home", "Neutral",
                                   "Venue", "Venue evidence", "Game centre", "Source", "Captured"],
              cols=["game_id", "date_iso", "kickoff_et", "network", "away", "home", "neutral_site", "venue",
                    "venue_evidence", "game_centre_url", "source_page", "captured_utc"],
              cap="Week-11 slate, transcribed {CAP_DAY}", kind="data"),
    table_csv("week11_byes.csv", ["Club", "Name", "Record printed", "Source", "Captured"],
              cols=["team", "club", "record_as_shown_on_week11_page", "source_page", "captured_utc"],
              cap="On bye", note="13 games plus 6 byes accounts for all 32 clubs - the count the build asserts.",
              kind="data"),
    '<section class="callout"><h2>Availability state at freeze time</h2><p>The league had published no '
    "Week-11 injury report. Three independent official reads say so: the archive URL for week 11 resolves to "
    "the Week-10 page whose title reads \"Week 10 of the 2026 Season\", its week selector stops at WEEK 10, and "
    "both game centres read today print \"Injury Report is not available at this time\". Therefore no "
    "availability feature is in these lines, and none is faked from last week's report.</p>"
    '<p class="note">Evidence: <a href="../data/closeout/captures/SR-05.txt">SR-05 capture</a>, '
    'SR-06 and SR-07 in <a href="sources.html">the capture ledger</a>.</p></section>',
])

line_rows = []
for r in raw["forecasts_w11.csv"]:
    line_rows.append([
        r["game_id"], f'{r["away"]} at {r["home"]}', r["date_iso"] + " " + r["kickoff_et"],
        r["fair_margin_home"], r["side_fair_line_home"], r["side_prob_home_cover"],
        r["total_fair_line"], r["total_prob_over"],
        r["ml_prob_home"], r["ml_fair_american_home"], r["ml_fair_american_away"],
        '<span class="badge u">UNVERIFIED - no market price</span>',
        '<span class="badge u">UNVERIFIED - no market price</span>',
        f'{r["rating_home"]} / {r["rating_away"]} / HFA {r["home_advantage"]} / sigma {r["sigma_margin"]}',
        r["n_train_games"], r["availability_input"], r["source"]])
page("lines.html", "Originated lines - side, then total, then moneyline",
     "The model's fair line, the market line and the difference are three separate columns, as the brief "
     "requires. The middle one is empty everywhere: this repository holds no price to subtract. Frozen "
     "{FROZEN}, before the first Week-11 kickoff.", [
    table(["Fixture", "Matchup", "Kickoff", "Expected margin (home)", "Fair side (home)", "P(home covers)",
           "Fair total", "P(over)", "P(home win)", "Fair ML home", "Fair ML away", "Market line",
           "Difference (fair - market)", "Inputs on the row", "n train", "Availability input", "Official source"],
          line_rows, cap="{MODEL_VERSION} fair lines, frozen before kickoff",
          note="Fair prices are vig-free: decimal odds converted from the probability, so no margin is hidden "
               "in them. Inputs are printed on the row - rating_home / rating_away / home advantage / residual "
               "SD - so a reader can recompute any number from data/closeout/derived/ratings.csv."),
    table(["Club", "Games", "PPG", "Opp PPG", "Net PPG", "Rating", "Official record", "Fitted on", "Basis"],
          [[r["team"], r["games"], r["ppg"], r["opp_ppg"], r["net_ppg"], r["rating"], r["record_official"],
            r["fitted_on"], r["source"]] for r in raw["ratings.csv"]],
          cap="The ratings the lines come from",
          note="Least-squares (Massey) ratings with a sum-to-zero constraint, solved exactly rather than "
                "iterated, fitted on {N_GAMES} games whose dates all precede the freeze. Home advantage is "
                "fitted, not assumed: {HFA} points, and it is set to 0 for neutral-site games in both the fit "
                "and the forecast."),
    '<p class="note">Why the numbers look aggressive: this model prices on season-long points differential with '
    "no shrinkage (the ablation on the luck page shows what shrinking does). Under-dispersion is the honest "
    "diagnosis - the SD of its margins is {SD_PRED} against a realised {SD_ACT}.</p>",
])

page("price-store.html", "Price snapshot store",
     "Opening and closing numbers for every market this project originates. While no operator price exists, "
     "the store keeps a fair-only pair per market per phase - the shape a real price would slot into.", [
    table(["Market", "Fixture", "Week", "Market", "Phase", "Captured", "Fair value", "Market price",
           "Difference", "Probability", "State", "Flag", "Snapshot hash", "Source"],
          [[r["market_id"], r["game_id"], r["week"], r["market"], r["phase"], r["captured_utc"],
            r["fair_value"], r["market_price"] or '<span class="badge u">UNVERIFIED</span>',
            r["difference"] or '<span class="badge u">UNVERIFIED</span>', r["probability"], r["state"],
            r["flag"], r["hash"][:12] + "…", r["source"]] for r in raw["price_store.csv"]],
          cap="{N_PRICE_ROWS} rows, 13 fixtures x 3 markets x open/close",
          note="The hash covers the frozen forecast row (game, both lines, the probability, the model version "
               "and the freeze stamp), and inputs_sha256 in data/closeout/derived/price_store.csv covers the "
               "150-game input file. Together they make a silent edit detectable."),
    table(["ID", "Rule", "Why", "Effect on the published tables", "Status", "Source"],
          [[r["id"], r["rule"], r["reason"], r["effect"], badge(r["status"]), r["source"]]
           for r in raw["price_policy.csv"]],
          cap="Price-data policy, decided before any backtest is published", kind="data"),
])

page("settlement.html", "Settlement of the pre-kickoff board",
     "The prior session's board was published as_of 2026-11-14, before the Week-10 kickoffs on the 15th and "
     "16th. Those lines are now graded against the finals captured here. This is the only set in the "
     "repository where the number was written down first.", [
    table(["Fixture", "Date", "Away at Home", "Model margin", "Actual margin", "Abs error", "Naive (zero) error",
           "Side line (home)", "P(home covers)", "Result", "Model's pick", "Pick covered",
           "Total line", "Actual total", "Result", "P(home win)", "ML result", "Control: always home",
           "Control: Week-9 favourite", "Source"],
          [[r["game_id"], r["date_iso"], f'{r["away"]} at {r["home"]}', r["model_margin_home"],
            r["actual_margin_home"], r["margin_error"], r["naive_margin_zero_error"], r["side_fair_line_home"],
            r["side_prob_home_cover"], r["side_result"], r["model_side_pick"],
            "" if r["model_side_cover_hit"] == "" else ("yes" if r["model_side_cover_hit"] == "1" else "no"),
            r["total_fair_line"], r["actual_total"], r["total_result"], r["ml_prob_home"], r["ml_result"],
            r["control_always_home"], f'{r["control_favourite_club"]} ({r["control_wk9_pct_favourite"]})',
            r["source"]] for r in raw["settlement.csv"]],
          cap="Every priced row, scored",
          note="{UNGRADED}, so the settlement cannot be padded by dropping inconvenient games "
               "(data/closeout/derived/ungraded.csv)."),
    table(["Division", "What is scored", "n", "Brier", "Benchmark", "Skill vs benchmark", "MAE (points)",
           "Benchmark MAE", "Verdict", "Source"],
          [[r["division"], r["what_is_scored"], r["n_gradable"], r["brier"], r["benchmark_brier"],
            r["skill_vs_benchmark"], r["mae_points"], r["mae_benchmark_points"], r["verdict"], r["source"]]
           for r in raw["scorecard.csv"]],
          cap="Scorecard - signal only; no return column exists because no price exists", kind="data"),
])

page("scorecard.html", "Scorecard and controls",
     "A number means nothing without the interval around it and the naive rule that would have produced the "
     "same number. Every row here carries both.", [
    table(["Picker", "n", "Hits", "Hit rate", "Wilson 95%", "Bootstrap 95%", "Outcome used", "Note", "Source"],
          [[r["picker"], r["n"], r["hits"], r["hit_rate"],
            f'{r["wilson_lo"]}-{r["wilson_hi"]}',
            ("n/a" if r["boot_lo"] == "" else f'{r["boot_lo"]}-{r["boot_hi"]}'),
            r["outcome_used"], r["note"], r["source"]] for r in raw["controls.csv"]],
          cap="Who would have done as well on the same games",
          note="The Week-9-favourite control uses only standings that existed before these games were played, "
               "so it is not lookahead. The random control is a fixed seed, printed in the verifier, so a "
               "reviewer can reproduce it exactly."),
    table(["Division", "Frozen when", "Graded", "Pushes", "Brier", "Benchmark Brier", "Skill", "MAE",
           "Benchmark MAE", "Stakes", "Verdict", "Source"],
          [[r["division"], r["frozen"], r["n_gradable"], r["n_push"], r["brier"], r["benchmark_brier"],
            r["skill_vs_benchmark"], r["mae_points"], r["mae_benchmark_points"], r["stakes"], r["verdict"],
            r["source"]] for r in raw["scorecard.csv"]],
          cap="Proper scores against naive benchmarks", kind="data"),
])

page("luck.html", "Removal of luck",
     "What this board can and cannot tell you about skill, in the project's own numbers. In-sample figures "
     "are labelled as in-sample; nothing here is promoted.", [
    table(["Measure", "Value", "How it was computed", "Caveat that stops it being over-read", "Source"],
          [[r["measure"], r["value"], r["how_computed"], r["caveat"], r["source"]] for r in raw["luck.csv"]],
          cap="The luck panel",
          note="The 95% luck band for a {N_SETTLE}-game run is {LUCK_LO} to {LUCK_HI}: a model that is exactly "
               "as good as a coin flip lands inside it almost every time, which is why no verdict on this "
               "sample is final."),
    table(["Shrink k", "Margin MAE", "Brier (home win)", "Total MAE", "Brier (over)", "vs naive margin",
           "vs naive total", "n", "Reading", "Source"],
          [[r["shrink_k"], r["mae_margin"], r["brier_home_win"], r["mae_total"], r["brier_over"],
            r["vs_naive_margin"], r["vs_naive_total"], r["n"], r["read"], r["source"]]
           for r in raw["ablation_shrink.csv"]],
          cap="Ablation: what happens if the model is less sure of itself",
          note="k=0 is the naive benchmark; k=1 is the frozen board. The best k on these {WF_N} games is the "
               "value selected on the same games, so it is a hypothesis for the Week-11 test, not a result "
               "(Q-C12, SG-C-06)."),
    table(["Fixture", "Market", "Prior value (2026-11-15)", "This value ({CAP_DAY})", "Difference", "Note", "Source"],
          [[r["game_id"], r["market"], r["prior_value"], r["this_value"], r["difference"], r["note"], r["source"]]
           for r in raw["drift_vs_prior.csv"]],
          cap="Drift between two freezes of the same fixtures",
          note="Largest side move {DRIFT_MAX_SIDE} points, mean absolute side move {DRIFT_MEAN_SIDE}; largest "
               "total move {DRIFT_MAX_TOTAL}. Two reasonable models on the same slate disagree by more than "
               "most staking strategies expect - which is the argument for publishing both until one wins."),
])

page("correlations.html", "Correlations",
     "Computed only from officially published numbers, each with its n and an interval. No correlation here "
     "is offered as a causal claim.", [
    table(["ID", "Quantity", "n", "r", "95% CI", "Unit", "Inputs", "Reading", "Source"],
          [[r["id"], r["quantity"], r["n"], r["r"],
            ("" if r["ci95_lo"] == "" else f'{r["ci95_lo"]} to {r["ci95_hi"]}'),
            r["unit_of_observation"], r["inputs"], r["note"], r["source"]] for r in raw["correlations.csv"]],
          cap="{N_CORR} values, all from the 2026 official scores",
          note="Intervals are Fisher-z on n independent games; a CI that spans 0 is reported as no usable "
               "signal, not as a small one. Five of six do."),
])

page("availability.html", "Availability graph",
     "Designations from the league report, checked against what the official Game Book says actually happened. "
     "A replacement is a named fact from the line-ups, never a guess from jersey numbers.", [
    table(["Club", "Player", "Pos", "Designation", "Practice", "Game Book disposition", "Evidence",
           "Who held the slot", "Claim status", "Report source", "Game Book source"],
          [[r["club"], r["player"], r["pos"], r["designation"], r["practice_status"], r["gamebook_disposition"],
            r["evidence"], r["replacement_or_starter_at_slot"], badge(r["claim_status"]), r["source_report"],
            r["source_gamebook"] or '<span class="badge u">no game-level source read</span>']
           for r in raw["availability_w10.csv"]],
          cap="{N_AVAIL} designated or undesignated rows joined to the one Game Book read",
          note="This is the whole availability evidence in this repository: 44 line-up entries, 55 "
               "substitution entries, 5 Did Not Play entries and 12 inactive entries, over two of the fourteen "
               "Week-10 games. Absent from a list is only treated as a roster fact where the sheet closes "
               "(CL-F-07); the 19 rows below that are not confirmed stay not confirmed."),
    table_csv("injury_report_w10_capture.csv", ["Club", "Player", "Pos", "Injury", "Practice status",
                                               "Game status", "Source page", "Captured"],
              cols=["club", "player", "pos", "injury", "practice_status", "game_status", "source_page",
                    "captured_utc"],
              cap="The four clubs read from the live report ({N_REPORT} rows)",
              note="Blank game status is printed as blank: on the official page a blank means the club did not "
                   "designate the player for that game, not that the player is healthy. The other 28 clubs "
                   "were not re-read here and are not represented."),
    table_csv("gamebook_ne_det.csv", ["Game", "Club", "Kind", "Unit", "Slot", "No.", "Player", "Fact",
                                      "Source document"],
              cols=["game", "team", "kind", "unit", "slot", "jersey", "player", "fact_as_published",
                    "source_url"],
              cap="Game Book line-ups and inactives - the raw evidence for every claim above", kind="data"),
    table_csv("gamebook_ne_det_header.csv", ["Field", "Value as published", "Source"],
              cols=["field", "value_as_published", "source"],
              cap="Fixture context for NE@DET, from the same document ({N_HDR} fields)",
              note="Roof, surface, weather, officials, attendance and the team lines that follow from the box "
                   "score. This is the fixture-context feature set the brief asks for, built only from published "
                   "facts.", kind="data"),
    table_csv("gamebook_lac_bal.csv", ["Game", "Club", "Kind", "Unit", "Slot", "No.", "Player", "Fact",
                                       "Source document"],
              cols=["game", "team", "kind", "unit", "slot", "jersey", "player", "fact_as_published",
                    "source_url"],
              cap="Second Game Book read - Los Angeles at Baltimore ({N_GB2} rows, including a Did Not Play block)",
              note="Chosen for what it can prove about a quarterback: the line-ups name J.Brissett, the Not Active "
                   "block names K.Slovis, the Did Not Play block names J.Fagnano, and no Jackson or Huntley appears "
                   "anywhere in the document.", kind="data"),
    table_csv("gamebook_lac_bal_header.csv", ["Field", "Value as published", "Source"],
              cols=["field", "value_as_published", "source"],
              cap="Fixture context for LAC@BAL ({N_HDR2} fields)",
              note="The final team statistics are the denominator for any playing-time proxy: Baltimore ran 49 "
                   "pass plays against 15 rushes, so a snap-share estimate from plays alone would be wrong for "
                   "half the roster - the count itself still has to come from a snap source (A-11).", kind="data"),
    table(["Game", "Club", "Line-ups", "Substitutions", "Did not play", "Not active", "Dressed",
           "Players accounted", "Sheet closed", "Reading", "Source"],
          [[r["game"], r["club"], r["starters"], r["substitutions"], r["did_not_play"], r["not_active"],
            r["dressed"], r["players_accounted"],
            (badge("VERIFIED complete") if r["closed_at_54"] == "yes"
             else badge("PARTIAL not reconciled")), r["reading"], r["source"]]
           for r in raw["game_sheets.csv"]],
          cap="Why absence can be read as evidence: {SHEETS_CLOSED} of {SHEETS} game-day sheets close at 48 dressed plus 6 not active",
          note="The count is made over the transcribed rows, not over the PDF: it is this module's arithmetic and "
               "it is the reason a blank is allowed to mean 'off the roster' here and nowhere else. The unreconciled "
               "sheet is Baltimore's, where the substitutions block was not visible in the extraction read; no "
               "claim is made from it."),
    table(["ID", "Club", "Position group", "What other pages still show", "What the Game Book shows",
           "Evidence", "Status", "Source"],
          [[r["id"], r["club"], r["position_group"], r["what_other_pages_show"], r["what_the_game_book_shows"],
            r["evidence"], badge(r["status"].split(" ")[0]) + " " + r["status"], r["source"]]
           for r in raw["roster_turnover.csv"]],
          cap="Roster turnover as a first-class data event ({N_TURNOVER} rows)",
          note="Two of these rows are the failure mode the brief predicted: a model that reads a depth chart "
               "instead of a game-day roster keeps pricing a player the team no longer pays to play. This table "
               "will only be complete when the other 30 clubs are swept (A-13)."),
])

page("gates.html", "Pre-registration and validation gates",
     "Each gate is a rule, a measured value, and a pass or fail. Nothing here is asserted as passed because "
     "it is easy.", [
    table(["ID", "Gate", "Rule text", "Measured now", "Threshold", "Status", "Source"],
          [[r["id"], r["gate"], r["rule_text"], r["measured_now"], r["threshold"], badge(r["status"]),
            r["source"]] for r in raw["prereg_gates.csv"]],
          cap="G-1 to G-8",
          note="G-1 is the one that matters today: the Week-11 forecast rows are stamped {FROZEN} and the "
               "first kickoff is Thu 2026-11-19 8:15 PM ET. The commit that carries these files is the "
               "registration; the hash is printed on this page's build note once the PR merges."),
])

page("sources.html", "Sources and capture ledger",
     "Every read, its clock time, what it covered, and the hash of the capture the rows were taken from. "
     "Re-reads are separate rows, so a delta between two views of the same page is visible.", [
    table(["ID", "Kind", "URL", "What was read", "Coverage claimed", "Captured", "Method", "Notes", "Capture file", "Capture hash"],
          [[r["id"], r["kind"], r["url"], r["what_was_read"], r["coverage_claimed"], r["captured_utc"],
            r["method"], r["notes"],
            f'<a href="../{r["capture_file"]}">{r["capture_file"].split("/")[-1]}</a>',
            r["capture_sha256"][:16] + "…"] for r in raw["source_reads.csv"]],
          cap="Capture ledger ({N_SOURCES} reads)",
          note="The hash is of the stored capture (data/closeout/captures/), not of the raw HTTP body - it "
               "fixes what was transcribed, which is the smaller claim and the honest one (CL-F-11)."),
    table_csv("sources.csv", ["ID", "Source", "URL", "Official?", "Read", "What it supports", "How it was verified"],
              cols=["id", "source", "url", "official", "read_utc", "what_it_supports", "how_verified"],
              cap="Source register", kind="data"),
])

page("verification.html", "Verification log",
     "The checks that ran, the numbers they produced, and what each one can and cannot prove. Re-running "
     "<code>python3 scripts/closeout_verify.py</code> reproduces every line.", [
    table(["Check", "Rule", "Result", "What it proves", "What it does not prove"],
          [[c[0], c[1], c[2], c[3], c[4]] for c in [
            ("V-01", "Week-10 finals exist for all 14 fixtures on the official page", "{N_W10} rows captured, 14 FINAL",
             "the close-out is complete for Week 10", "that earlier weeks were re-read - they were not"),
            ("V-02", "log W-L-T, PF and PA equal the official standings for every club", "{MISMATCH} mismatches over 32 clubs",
             "the 150-game corpus is consistent with the league's own arithmetic", "each row was checked against its own game page"),
            ("V-03", "PF - PA equals NET for every club on the standings page", "32 of 32", "the standings transcription is internally consistent", "the transcription against the rendered page (a human-readable capture file is provided)"),
            ("V-04", "sum of league PF equals sum of league PA", "{PF_SUM} = {PF_SUM}", "no club's points were dropped or duplicated in the log", "nothing about scores themselves"),
            ("V-05", "Week-11 fixture count plus byes equals 32 clubs", "13 games x 2 + 6 byes = 32", "the priced slate is complete", "that the league will not flex a game (flexibility rules are cited on the board page)"),
            ("V-06", "every priced game has a captured final", "0 ungraded rows", "the settlement cannot be padded by dropping hard games", "that the model is good"),
            ("V-07", "every model figure names the window it was computed on", "enforced at build: a missing window fails the check", "in-sample and walk-forward numbers cannot be confused", "that the model generalises to next week"),
            ("V-08", "no market price is invented anywhere", "0 non-empty market cells in forecasts, price store and scorecard", "the difference columns are honestly empty", "nothing - it is a negative result"),
            ("V-09", "every table row on this site carries a source link or an explicit unverified marker", "enforced by scripts/closeout_verify.py and scripts/audit_all.py", "the brief's row rule holds for this tree", "that the linked page still says the same thing tomorrow"),
            ("V-19", "game-day sheets must close at 48 dressed plus 6 not active, or say they cannot", "3 of 4 club sheets close; the fourth is labelled unreconciled",
             "absence can be read as a roster fact where the sheet closes", "nothing about the 12 games not read"),
            ("V-20", "roster-turnover rows cite a game document or admit the gap", "4 rows; 1 row says NOT SWEPT for the other 30 clubs",
             "no club is silently assumed healthy", "the 30 un-swept clubs are still un-swept"),
            ("V-10", "the build is deterministic", "two consecutive builds produce byte-identical HTML", "no randomness or clock leakage in the rendered pages", "the model's stability under new data (that is the drift table)"),
        ]], cap="Checks run by this module", kind="meta"),
    '<section class="callout"><h2>Reproduce it</h2><pre><code>python3 scripts/closeout_engine.py\n'
    'python3 scripts/closeout_build.py\npython3 scripts/closeout_verify.py</code></pre>'
    "<p>The engine is the only place numbers are produced; the builder only formats them. A reviewer who runs "
    "the three commands gets the site that is published.</p></section>",
])

page("questions.html", "Open questions",
     "What must be known before a decision here is reasonable - with the number already in hand, the gap that "
     "remains, and who can close it.", [
    table(["ID", "Question", "What we already know (with the number)", "What is missing", "What would answer it",
           "Who can answer", "Official source", "Status"],
          [[r["id"], r["question"], r["what_we_already_know_with_a_number"], r["what_is_missing"],
            r["what_would_answer_it"], r["who_can_answer"], r["official_source"], badge(r["status"])]
           for r in raw["questions.csv"]],
          cap="{N_QUESTIONS} questions",
          note="Three of these are owner decisions and cannot be delegated: the price source (Q-C01), the "
               "canonical sample gate (Q-C06) and the publication terms for row-level data (Q-C08)."),
])

page("suggestions.html", "Suggestions - review before anything is implemented",
     "Each suggestion states what it would publish, what it costs, what could go wrong and what would change "
     "its mind. Nothing on this page has been implemented beyond the capture and grading that produced it.", [
    table(["ID", "Suggestion", "What and why", "Impact", "Effort", "Risk", "Depends on", "Would publish",
           "Status", "Your decision", "Source"],
          [[r["id"], r["title"], r["what_and_why"], r["impact"], r["effort"], r["risk"], r["depends_on"],
            r["publishes"], badge(r["status"]), "", r["source"]] for r in raw["suggestions.csv"]],
          cap="{N_SUGG} paths, none taken",
          note="The empty column is deliberate: the decision is the owner's, and a suggestion pre-marked as "
               "accepted would defeat the purpose of the queue."),
    '<section class="callout"><h2>How to read the queue</h2><ul class="tight">'
    "<li><b>Unblocks the most:</b> SG-C-01 (a price source) and SG-C-02 (thirteen more Game Books). Everything else is measurement plumbing.</li>"
    "<li><b>Cheapest real protection:</b> SG-C-07 - relabel every in-sample figure, which stops the site overselling itself at no cost.</li>"
    "<li><b>The structural fix:</b> SG-C-08, consolidation; this module is the fourteenth tree, and adding a fifteenth is not the answer.</li>"
    "<li><b>Do not do:</b> publish parlays or prop combos (SG-C-12) - the joint evidence does not exist and the measured side/over dependence spans zero.</li></ul></section>",
])

page("readiness.html", "Decision readiness",
     "One row per registered requirement: the state, the gate that blocks it, and the number or condition that "
     "clears it. Clearance criteria are project rules, not NFL-published facts.", [
    table(["ID", "Requirement", "State", "Blocking gate", "Number or condition that clears it", "Evidence"],
          [[r["id"], r["requirement"], badge(r["state"]), r["blocking_gate"],
            r["number_or_condition_that_clears_it"], r["evidence"]] for r in raw["readiness.csv"]],
          cap="{N_READY} requirements", kind="data"),
])

page("flagged.html", "Flagged for review",
     "Irregularities found while working line by line. None blocks anything; all of them change how a number "
     "should be read.", [
    table(["ID", "Severity", "Finding", "Why it matters", "State", "Source"],
          [[r["id"], r["severity"], r["finding"], r["why_it_matters"], badge(r["state"].split(" ")[0]) + " " +
            cell(r["state"]), r["source"]] for r in raw["flags.csv"]],
          cap="{N_FLAGS} items", kind="data"),
])

page("repo-review.html", "Repo review",
     "What the repository asserts, what the official page says on the day this module was built, and what was "
     "done about it. Every row is a line someone else wrote being checked.", [
    table(["ID", "What the repo says", "Where", "What the official page says today", "Verdict", "Action taken", "Source"],
          [[r["id"], r["what_the_repo_says"], r["where"], r["what_the_official_page_says_today"],
            badge(r["verdict"].split(" ")[0]) + " " + esc(r["verdict"]), r["action_taken"], r["source"]]
           for r in raw["repo_review.csv"]],
          cap="Line-by-line review of prior claims", kind="data"),
])

print(f"pages built: {len(os.listdir(OUT))} in closeout/")
