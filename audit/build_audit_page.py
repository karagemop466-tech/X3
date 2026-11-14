"""Render audit/index.html from the audit CSV/JSON outputs (stdlib only).

Every table row carries a link to the official NFL.com page it was checked against.
Run after audit/build_and_diff.py.
"""
import csv, json, html
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
S = json.loads((AUDIT / "summary.json").read_text())
OFF = list(csv.DictReader(open(AUDIT / "official_injury_wk10_2026.csv", newline="")))
DIFF = {(r["team"], r["player"]): r for r in csv.DictReader(open(AUDIT / "diff_report.csv", newline=""))}
SCHED = list(csv.DictReader(open(AUDIT / "schedule_check_wk10.csv", newline="")))
esc = lambda s: html.escape(str(s or ""))

FLAGS = [
    ("F-A01", "Game label orientation and format",
     "24 rows (NE, DET): repo label 'NE vs DET (Munich)'",
     "Schedule: 'Patriots at Lions', tagged International Game: Munich. Orientation NE @ DET.",
     "Change label to 'NE @ DET (Munich)' after owner review. Not changed by this audit.",
     [("Schedule page", S["schedule_source"]), ("Game page", "https://www.nfl.com/games/patriots-at-lions-2026-reg-10")]),
    ("F-A02", "TV list for the Monday game",
     "27 rows (LAC, BAL): repo 'ESPN, ABC, ESPN2'",
     "Injury page: 'ESPN, ABC, ESPN2, ESPN DEPORTES'. Schedule page lists 'ESPN' only.",
     "Confirm the broadcast list before changing. The two official pages differ.",
     [("Injury page", S["injury_source"]), ("Schedule page", S["schedule_source"]), ("Game page", "https://www.nfl.com/games/chargers-at-ravens-2026-reg-10")]),
    ("F-A03", "Per-row source link is the generic index",
     "All 345 rows: https://www.nfl.com/injuries/",
     "Week-specific page: https://www.nfl.com/injuries/league/2026/reg10",
     "Point the source column at the week page so each row traces to the exact report.",
     [("Week 10 injury page", S["injury_source"])]),
    ("F-A04", "Thursday game already final on the schedule",
     "WAS @ NYG rows (20 rows) show pre-game designations",
     "Schedule page shows 'Commanders 24, Giants 21, FINAL' for Thu Nov 12.",
     "Treat the Thursday rows as a pre-game snapshot, not current status.",
     [("Schedule page", S["schedule_source"]), ("Game page", "https://www.nfl.com/games/commanders-at-giants-2026-reg-10")]),
    ("F-A05", "Practice-status labels are abbreviated in the repo",
     "Repo: Full / Limited / DNP",
     "Official: Full Participation in Practice / Limited Participation in Practice / Did Not Participate In Practice",
     "Mapping is one-to-one and checked row by row. Not an error; the official wording is shown here.",
     [("Week 10 injury page", S["injury_source"])]),
    ("F-A06", "Snapshot time not shown on the page extract",
     "Fetched 2026-11-14",
     "The page extract carries no update timestamp.",
     "Re-check the live page before any decision that depends on a designation.",
     [("Week 10 injury page", S["injury_source"])]),
]

def link(label, url):
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'

rows_html = []
for o in OFF:
    d = DIFF.get((o["team"], o["player"]), {})
    res = d.get("result", "")
    fields = d.get("fields", "")
    badge = ('<span class="ok">MATCH</span>' if res == "MATCH"
             else f'<span class="warn">DIFF: {esc(fields)}</span>')
    rows_html.append(
        "<tr>"
        f"<td>{esc(o['game'])}</td><td>{esc(o['kickoff_et'])}</td><td>{esc(o['tv'])}</td>"
        f"<td>{esc(o['team'])}</td><td>{esc(o['team_record'])}</td>"
        f"<td>{esc(o['player'])}</td><td>{esc(o['position'])}</td><td>{esc(o['injury'])}</td>"
        f"<td>{esc(o['practice_status'])}</td><td>{esc(o['game_status'])}</td>"
        f"<td>{badge}</td>"
        f"<td>{link('NFL.com', o['source_url'])}</td>"
        "</tr>")

sched_html = []
for s in SCHED:
    sched_html.append(
        "<tr>"
        f"<td>{esc(s['game'])}</td><td>{esc(s['schedule_day'])}</td><td>{esc(s['schedule_time_et'])} ET</td>"
        f"<td>{esc(s['schedule_network'])}</td><td>{esc(s['schedule_note'])}</td>"
        f"<td>{esc(s['injury_report_kickoff_et'])}</td><td>{esc(s['injury_report_tv'])}</td>"
        f"<td>{link('Game page', s['game_page'])} · {link('Schedule', s['source_url'])}</td>"
        "</tr>")

flag_html = []
for fid, title, repo, official, action, links in FLAGS:
    flag_html.append(
        "<tr>"
        f"<td><strong>{fid}</strong></td><td>{esc(title)}</td><td>{esc(repo)}</td>"
        f"<td>{esc(official)}</td><td>{esc(action)}</td>"
        f"<td>{' · '.join(link(l, u) for l, u in links)}</td>"
        "</tr>")

sc = S["official_status_counts"]
rr = S["row_results"]
fm = S["field_mismatch_counts"]

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Week 10 2026 Injury Report: Official-Source Audit | X3</title>
<style>
  :root {{ --ink:#1b2430; --muted:#5b6675; --line:#dfe4ea; --bg:#f6f8fa; --ok:#15734a; --warn:#9a5b00; --accent:#1f5fbf; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; color:var(--ink); background:#fff; }}
  header {{ background:var(--bg); border-bottom:1px solid var(--line); padding:20px 24px; }}
  header h1 {{ margin:0 0 4px; font-size:22px; }}
  header p {{ margin:0; color:var(--muted); }}
  nav a {{ color:var(--accent); text-decoration:none; margin-right:14px; }}
  main {{ max-width:1200px; margin:0 auto; padding:20px 24px 60px; }}
  h2 {{ font-size:18px; margin:32px 0 10px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
  .card {{ border:1px solid var(--line); border-radius:10px; padding:12px 14px; background:#fff; }}
  .card b {{ display:block; font-size:24px; }}
  .card span {{ color:var(--muted); font-size:13px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
  th, td {{ text-align:left; padding:7px 8px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:var(--bg); position:sticky; top:0; }}
  .wrap {{ overflow:auto; max-height:640px; border:1px solid var(--line); border-radius:8px; }}
  .ok {{ color:var(--ok); font-weight:600; }}
  .warn {{ color:var(--warn); font-weight:600; }}
  a {{ color:var(--accent); }}
  input[type=search] {{ width:100%; max-width:360px; padding:8px 10px; border:1px solid var(--line); border-radius:8px; margin:6px 0 10px; font:inherit; }}
  .note {{ color:var(--muted); font-size:13px; }}
</style>
</head>
<body>
<header>
  <nav><a href="../">&larr; X3 home</a> <a href="#flags">Flagged for review</a> <a href="#schedule">Schedule check</a> <a href="#rows">All 345 rows</a></nav>
  <h1>Week 10, 2026 injury report: official-source audit</h1>
  <p>Independent line-by-line check of the repo's Week 10 dataset against NFL.com. Fetched {esc(S['fetched'])}.</p>
</header>
<main>

<section>
  <h2>Result at a glance</h2>
  <div class="cards">
    <div class="card"><b>{S['official_rows']}</b><span>official rows transcribed (NFL.com)</span></div>
    <div class="card"><b>{rr.get('MATCH',0)}</b><span>rows match on every compared field</span></div>
    <div class="card"><b>{rr.get('DIFF',0)}</b><span>rows differ (game label {fm.get('game',0)}, TV {fm.get('tv',0)})</span></div>
    <div class="card"><b>{fm.get('injury',0)+fm.get('practice_status',0)+fm.get('game_status',0)+fm.get('position',0)+fm.get('team_record',0)}</b><span>mismatches in status, injury, practice, position, record</span></div>
    <div class="card"><b>{sc['Out']} / {sc['Doubtful']} / {sc['Questionable']}</b><span>Out / Doubtful / Questionable designations</span></div>
    <div class="card"><b>{sc['blank_game_status']}</b><span>rows with no game-status designation (left blank, not inferred)</span></div>
  </div>
  <p class="note">Compared fields: team, team record, player, position, injury, practice status, game status, game label (orientation), kickoff, TV. Method and files are listed at the bottom of this page.</p>
</section>

<section id="flags">
  <h2>Flagged for review (irregularities)</h2>
  <p class="note">Flags are published for owner review. None blocks use of the status values, which match the official page row for row.</p>
  <div class="wrap"><table>
    <thead><tr><th>ID</th><th>Issue</th><th>Repo value</th><th>Official value</th><th>Proposed action</th><th>Sources</th></tr></thead>
    <tbody>{''.join(flag_html)}</tbody>
  </table></div>
</section>

<section id="schedule">
  <h2>Schedule check (orientation, kickoff, network)</h2>
  <p class="note">Official schedule: {link('NFL.com Week 10 schedule', S['schedule_source'])}. Bye teams: {esc(', '.join(S['schedule_byes']))}.</p>
  <div class="wrap"><table>
    <thead><tr><th>Game (away @ home)</th><th>Day</th><th>Time</th><th>Network (schedule)</th><th>Note</th><th>Injury page kickoff</th><th>Injury page TV</th><th>Sources</th></tr></thead>
    <tbody>{''.join(sched_html)}</tbody>
  </table></div>
</section>

<section id="rows">
  <h2>All 345 official rows, with comparison to the repo</h2>
  <input type="search" id="filter" placeholder="Filter by team, player, or status…" aria-label="Filter rows">
  <div class="wrap"><table id="rowtable">
    <thead><tr><th>Game</th><th>Kickoff (ET)</th><th>TV</th><th>Team</th><th>Record</th><th>Player</th><th>Pos</th><th>Injury</th><th>Practice (official)</th><th>Game status</th><th>Repo check</th><th>Source</th></tr></thead>
    <tbody>{''.join(rows_html)}</tbody>
  </table></div>
  <p class="note">Practice labels are the official wording shortened as Full / Limited / DNP in the repo. Blank cells are blank on the official page.</p>
</section>

<section id="method">
  <h2>Method and files</h2>
  <ul>
    <li>Official rows: 8 chunks of {link('nfl.com/injuries/league/2026/reg10', S['injury_source'])}, transcribed into <code>audit/official_injury_wk10_2026.raw.txt</code> and converted by <code>audit/build_and_diff.py</code>.</li>
    <li>Schedule and orientation: 3 chunks of {link('nfl.com/schedules/2026/by-week/week-10', S['schedule_source'])}.</li>
    <li>Repo dataset compared: <code>docs/data/injury-2026-week10.csv</code> (345 rows, read-only in this audit).</li>
    <li>Outputs: <code>audit/diff_report.csv</code> (one line per row), <code>audit/summary.json</code>, <code>audit/schedule_check_wk10.csv</code>.</li>
    <li>Limit: the sandbox cannot reach NFL.com directly, so the official text was read through the fetch tool. Raw HTML was not diffed byte for byte.</li>
  </ul>
</section>

</main>
<script>
  const f = document.getElementById('filter');
  const rows = Array.from(document.querySelectorAll('#rowtable tbody tr'));
  f.addEventListener('input', () => {{
    const q = f.value.trim().toLowerCase();
    rows.forEach(r => r.style.display = !q || r.textContent.toLowerCase().includes(q) ? '' : 'none');
  }});
</script>
</body>
</html>
"""
(AUDIT / "index.html").write_text(page)
print("wrote", AUDIT / "index.html", len(page), "bytes;", len(OFF), "rows;", len(FLAGS), "flags")
