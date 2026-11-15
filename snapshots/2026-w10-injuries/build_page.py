#!/usr/bin/env python3
"""Render snapshots/2026-w10-injuries/index.html from the outputs of build_and_compare.py.
Every table row carries a link to the official NFL source. Nothing is inferred: blank
official cells stay blank. Run after build_and_compare.py:
    python3 snapshots/2026-w10-injuries/build_page.py
"""
import csv
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = "https://www.nfl.com/injuries/"
SRC_SCHED = "https://www.nfl.com/schedules/2026/by-week/week-10"
HUB = "../../hub/injuries.html"
SRC_LINK = '<a href="https://www.nfl.com/injuries/" target="_blank" rel="noopener">nfl.com/injuries</a>'

summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
official = list(csv.DictReader(open(HERE / "official_rows.csv", encoding="utf-8")))
compare = list(csv.DictReader(open(HERE / "compare_hub.csv", encoding="utf-8")))


def esc(x):
    return html.escape(x or "", quote=True)


def cell(x):
    return "<td>" + (esc(x) if x else '<span class="blank">blank</span>') + "</td>"


def src_cell():
    return f'<td><a href="{SRC}" target="_blank" rel="noopener">nfl.com/injuries</a></td>'


# ---------- flagged differences
diff_rows = [r for r in compare if r["result"] != "MATCH"]
n_diff = sum(1 for r in diff_rows if r["result"] == "DIFF")
n_off_only = sum(1 for r in diff_rows if r["result"] == "OFFICIAL_ONLY")
n_hub_only = sum(1 for r in diff_rows if r["result"] == "HUB_ONLY")

counts = summary["compare_counts"]
css = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1d2330;background:#f7f8fa;line-height:1.45}
header{background:#14213d;color:#fff;padding:14px 22px}
header a{color:#fff;text-decoration:none;font-weight:600}
main{max-width:1200px;margin:0 auto;padding:18px 22px 60px}
h1{font-size:1.5rem;margin:.3rem 0 .4rem} h2{font-size:1.15rem;margin:1.6rem 0 .5rem;border-bottom:1px solid #d7dce5;padding-bottom:4px}
.lede{color:#3c4656;max-width:900px}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.card{background:#fff;border:1px solid #d7dce5;border-radius:8px;padding:10px 14px;min-width:150px}
.card b{display:block;font-size:1.35rem}
.card span{font-size:.82rem;color:#5a6474}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.86rem;margin:8px 0 14px}
th,td{border:1px solid #e1e5ec;padding:5px 7px;text-align:left;vertical-align:top}
th{background:#eef1f6;position:sticky;top:0}
.blank{color:#9aa3b2;font-style:italic}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:.78rem;font-weight:600}
.DIFF{background:#fde8c8;color:#7a4300}.OFFICIAL_ONLY{background:#dbeafe;color:#1e3a8a}.HUB_ONLY{background:#f3e8ff;color:#5b21b6}.MATCH{background:#dcfce7;color:#166534}
.flag{background:#fff7ed;border-left:4px solid #f59e0b;padding:10px 14px;margin:10px 0;border-radius:4px}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.8rem;word-break:break-all}
.wrap{overflow-x:auto}
"""

parts = []
parts.append(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Week 10 2026 official injury report - re-capture and comparison - X3</title>
<style>{css}</style></head>
<body>
<header><a href="../../index.html">X3 NFL decision desk</a> &nbsp;|&nbsp; <a href="../../hub/injuries.html">Injury tracker (hub)</a></header>
<main>
<h1>Week 10, 2026 - official injury report re-capture</h1>
<p class="lede">Every row below was read from the live official NFL injury report
(<a href="{SRC}" target="_blank" rel="noopener">{SRC}</a>) in this session and transcribed to
<code>official_transcription.psv</code>. The transcription is checked by a script
(<code>build_and_compare.py</code>) and compared field by field with the published hub table.
Blank cells mean the official page shows no value; they are not filled in.</p>

<div class="cards">
  <div class="card"><b>{summary['official_rows']}</b><span>official rows captured</span></div>
  <div class="card"><b>{summary['official_games']}</b><span>games on the report</span></div>
  <div class="card"><b>{summary['official_clubs']}</b><span>clubs with rows (4 bye clubs have none)</span></div>
  <div class="card"><b>{counts.get('MATCH',0)}</b><span>rows matching the hub</span></div>
  <div class="card"><b>{n_diff}</b><span>rows that differ from the hub</span></div>
  <div class="card"><b>{n_off_only}</b><span>official rows missing from the hub</span></div>
</div>

<h2>Capture record</h2>
<table><thead><tr><th>Item</th><th>Value</th><th>Source</th></tr></thead><tbody>
<tr><th>Official source</th><td><a href="{SRC}" target="_blank" rel="noopener">{SRC}</a> (title: {esc(summary['official_title'])})</td><td>{SRC_LINK}</td></tr>
<tr><th>Schedule cross-reference</th><td><a href="{SRC_SCHED}" target="_blank" rel="noopener">{SRC_SCHED}</a></td><td><a href="{SRC_SCHED}" target="_blank" rel="noopener">nfl.com/schedules</a></td></tr>
<tr><th>Capture method</th><td>Fetched through the sandbox page-fetch tool (the sandbox shell cannot reach nfl.com directly). The tool returned 8 text chunks; all were read in full. The fetch tool did not return an HTTP clock time, so no per-fetch timestamp is claimed here.</td><td>{SRC_LINK}</td></tr>
<tr><th>Transcription written</th><td>2026-11-15, sandbox clock (last modified 18:31 UTC)</td><td>{SRC_LINK}</td></tr>
<tr><th>Transcription file</th><td><a href="official_transcription.psv">official_transcription.psv</a> ({summary['transcription_bytes']} bytes)</td><td>{SRC_LINK}</td></tr>
<tr><th>SHA-256 of transcription</th><td class="mono">{summary['transcription_sha256']}</td><td>{SRC_LINK}</td></tr>
<tr><th>Raw HTML / raw fetch bytes</th><td>Not retained. Only the transcription is hashed. Raw hashes of the fetched text are not available in this session.</td><td>{SRC_LINK}</td></tr>
<tr><th>Independent cross-check</th><td>agency/data/derived/injury_designations_w10_2026.csv (merged to main via PR #82, captured 2026-11-15 19:05 UTC per that file): 347 of 347 player keys match; all fields match except one capitalisation difference in one practice label ("in" vs "In"). Source text: "Did Not Participate In Practice".</td><td>{SRC_LINK}</td></tr>
<tr><th>Validation</th><td>{len(summary['validation_problems'])} parse problems; {len(summary['official_duplicate_team_player'])} duplicate team/player keys; 8 fields per row checked.</td><td>{SRC_LINK}</td></tr>
</tbody></table>

<h2>Flagged for review</h2>
<div class="flag"><b>1. Lions game-status cells (brief VR-08):</b> Kerby Joseph, Cade Mays and D.J. Reed are <b>Out</b> on the official page, and <b>Out</b> in the hub, the root injuries page, the dashboard data file and the 2026-11-14 audit file. The blank cell described in the brief is not present in any of these copies. Nothing was changed.</div>
<div class="flag"><b>2. Row count (brief VR-04/05):</b> the brief cites 279 live rows and 2 no-injury sections. The live page read here has {summary['official_rows']} rows across {summary['official_clubs']} clubs and no empty club sections. The published hub has 345 rows. The brief's figures were not reproduced.</div>
<div class="flag"><b>3. Chargers and Ravens statuses changed after the 2026-11-14 captures:</b> {n_diff - 1} rows in the LAC and BAL blocks have a designation or practice status on the live page that the hub and audit files show as blank or different. Two Ravens players (Calais Campbell, Ronnie Stanley) appear on the live page and not in the hub. This page does not say which version was correct at any earlier moment; it records the delta only.</div>
<div class="flag"><b>4. Arden Key (IND):</b> the hub shows Hamstring / Questionable. The live page shows no designation for him. The hub and 2026-11-14 audit file agree with each other, not with the live page.</div>
<div class="flag"><b>5. Not captured here:</b> reserve lists (injured reserve), inactive lists, snap counts and depth charts. Several news items on the official page say players were placed on injured reserve (for example Malik Willis, TreVeyon Henderson and Lamar Jackson). Those moves are not on this report and this page does not infer them.</div>

<h2>Differences from the published hub table</h2>
<p class="lede">{counts.get('MATCH',0)} rows match the hub on every field. The table below lists every row that does not match, plus official rows missing from the hub. Field values use the official text. "hub" is the value in <a href="{HUB}">hub/injuries.html</a>. "game" compares the game label only; the hub writes the label as <code>LAR@AZ</code>.</p>
<div class="wrap"><table>
<thead><tr><th>Result</th><th>Team</th><th>Player</th><th>Official game</th><th>Hub game</th><th>Field differences</th><th>Source</th></tr></thead><tbody>
""")
for r in diff_rows:
    parts.append(
        f"<tr><td><span class='tag {esc(r['result'])}'>{esc(r['result'])}</span></td>"
        f"<td>{esc(r['team'])}</td><td>{esc(r['player'])}</td><td>{esc(r['official_game'])}</td>"
        f"<td>{esc(r['hub_game'])}</td><td>{esc(r['field_differences'])}</td>"
        f"<td><a href='{SRC}' target='_blank' rel='noopener'>nfl.com/injuries</a> &middot; <a href='{HUB}'>hub</a></td></tr>\n"
    )
parts.append("</tbody></table></div>\n")

parts.append("""<h2>Full official table (Week 10, as captured)</h2>
<p class="lede">One row per player on the official report. Every row links to the official source. Use the browser's find box to search a team or player.</p>
<div class="wrap"><table>
<thead><tr><th>Game</th><th>Kickoff / TV (as printed)</th><th>Team</th><th>Record</th><th>Player</th><th>Pos</th><th>Injury</th><th>Practice status</th><th>Game status</th><th>Source</th></tr></thead><tbody>
""")
kickoff = {}
for r in official:
    kickoff.setdefault(r["game"], r["kickoff_et_tv"])
for r in official:
    parts.append(
        "<tr>"
        + cell(r["game"]) + cell(r["kickoff_et_tv"]) + cell(r["team"]) + cell(r["team_record"])
        + cell(r["player"]) + cell(r["position"]) + cell(r["injury"]) + cell(r["practice_status"])
        + cell(r["game_status"]) + src_cell() + "</tr>\n"
    )
parts.append("</tbody></table></div>\n")
parts.append(f"""<h2>Counts by official game status</h2>
<table><thead><tr><th>Game status</th><th>Rows</th><th>Source</th></tr></thead><tbody>
{''.join(f"<tr><td>{esc(k)}</td><td>{v}</td><td>{SRC_LINK}</td></tr>" for k, v in summary['official_status_counts'].items())}
</tbody></table>
<h2>Counts by practice status</h2>
<table><thead><tr><th>Practice status</th><th>Rows</th><th>Source</th></tr></thead><tbody>
{''.join(f"<tr><td>{esc(k)}</td><td>{v}</td><td>{SRC_LINK}</td></tr>" for k, v in summary['official_practice_counts'].items())}
</tbody></table>

<h2>Requests to other sessions (logged, not edited here)</h2>
<ul>
<li><b>hub/injuries.html</b> (owner: hub session): update the LAC @ BAL block and the IND Arden Key row to the official values listed above, add Calais Campbell and Ronnie Stanley, and state the capture date. Replace the "345 rows" text with the captured count.</li>
<li><b>flagged.html / index.html</b> (owner: integration session): link this page as the Week 10 re-capture entry in the Flagged for Review list.</li>
</ul>
<p class="lede">Method notes: this page is generated by <code>build_page.py</code> from <code>build_and_compare.py</code> outputs. Re-running both scripts after any change to the transcription keeps the counts and hash in step.</p>
</main></body></html>
""")

(HERE / "index.html").write_text("".join(parts), encoding="utf-8")
print("wrote", HERE / "index.html", "rows:", len(official), "diff rows:", len(diff_rows))
