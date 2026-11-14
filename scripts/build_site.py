#!/usr/bin/env python3
"""Build the static GitHub Pages site in docs/ from the CSV data in data/.

Standard library only. Run from the repository root:  python3 scripts/build_site.py
Every table row carries a source link taken from data/ (official URLs where available).
Blank values that could not be confirmed are shown blank and marked 'unverified'.
"""
import csv
import html
import os
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DOCS = os.path.join(ROOT, "docs")
AS_OF = "2026-11-14"


def read(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


SOURCES = {r["source_id"]: r for r in read("sources.csv")}


def e(s):
    return html.escape(s or "", quote=True)


def link(url, text=None):
    if not url:
        return '<span class="flag">no official source</span>'
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{e(text or url)}</a>'


def src_link(source_id):
    s = SOURCES.get(source_id)
    if not s:
        return '<span class="flag">no official source</span>'
    return link(s["url"], s["name"])


def table(headers, rows, table_id, search=True):
    out = []
    if search:
        out.append(f'<input class="search" type="search" placeholder="Filter rows..." '
                   f'data-target="{table_id}" aria-label="Filter rows">')
    out.append(f'<div class="tablewrap"><table id="{table_id}"><thead><tr>')
    out += [f"<th>{e(h)}</th>" for h in headers]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for c in r:
            out.append(f"<td>{c}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


NAV = OrderedDict([
    ("Overview", [("index.html", "Dashboard"), ("executive-summary.html", "Executive summary")]),
    ("Data", [("injuries.html", "Injuries (Week 10)"), ("schedule.html", "2026 key dates"),
              ("sources.html", "Official sources")]),
    ("Analysis", [("strategies.html", "Strategy leaderboard"), ("correlations.html", "Correlations")]),
    ("Decisions", [("questions.html", "Questions"), ("suggestions.html", "Suggestions (for review)"),
                   ("requirements.html", "Requirements")]),
    ("Review", [("flagged.html", "Flagged for Review")]),
])


def page(filename, title, body, active):
    nav_html = []
    for group, items in NAV.items():
        links = " ".join(
            f'<a href="{href}"{" class=active" if href == active else ""}>{e(label)}</a>'
            for href, label in items)
        nav_html.append(f'<div class="navgroup"><span class="navlabel">{e(group)}</span>{links}</div>')
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | X3 NFL Research</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="top"><a class="brand" href="index.html">X3 NFL Research</a>
<span class="asof">Data as of {AS_OF} &middot; Research only, not betting advice</span></header>
<nav class="nav">{''.join(nav_html)}</nav>
<main>
<h1>{e(title)}</h1>
{body}
</main>
<footer>Every table row links to an official source where one exists. Blank cells are unverified and flagged.
Wagering from Japan with private bookmakers is criminal for the bettor under Penal Code Art. 185
(<a href="{e(SOURCES['JP-PENAL-185']['url'])}" target="_blank" rel="noopener">official text</a>).
Built from data/ by scripts/build_site.py.</footer>
<script src="assets/site.js"></script>
</body>
</html>
"""
    with open(os.path.join(DOCS, filename), "w", encoding="utf-8") as f:
        f.write(doc)


def badge(status):
    s = (status or "").lower()
    cls = "ok" if s.startswith(("done", "pass", "verified")) else (
        "flag" if s.startswith(("flag", "unverified", "blocked", "high")) else "todo")
    return f'<span class="badge {cls}">{e(status)}</span>'


# ---------- data ----------
injuries = read("injury_report_2026_wk10.csv")
schedule = read("schedule_2026_key_dates.csv")
strategies = read("strategies.csv")
gates = read("gates.csv")
correlations = read("correlations.csv")
questions = read("questions.csv")
suggestions = read("suggestions.csv")
requirements = read("requirements.csv")
flags = read("flags.csv")
sources = read("sources.csv")

status_counts = Counter(r["game_status"] for r in injuries if r["game_status"])
pos_out = Counter(r["position"] for r in injuries if r["game_status"] == "Out")
team_out = Counter(r["team"] for r in injuries if r["game_status"] == "Out")
teams = sorted({r["team"] for r in injuries})
verified_dates = sum(1 for r in schedule if r["verification"] == "Verified")
unverified_dates = sum(1 for r in schedule if r["verification"] != "Verified")
high_flags = sum(1 for r in flags if r["severity"] == "High")
open_q = sum(1 for r in questions if r["status"] == "Open")
pending_s = sum(1 for r in suggestions if r["decision"].startswith("Pending"))
validated = sum(1 for r in strategies if r["gate_status"].startswith("Pass"))
nonfull_rows = len(injuries)

# ---------- Injuries ----------
inj_rows = []
for r in injuries:
    inj_rows.append([
        e(r["team"]), e(r["slot"]), e(r["player"]), e(r["position"]), e(r["injury"]),
        e(r["practice_status"]), e(r["game_status"]),
        f'<span class="flag">{e(r["note"])}</span>' if r["note"] else "",
        src_link(r["source_id"]),
    ])
team_rows = [[e(t), str(team_out.get(t, 0)),
              str(sum(1 for r in injuries if r["team"] == t and r["game_status"] == "Doubtful")),
              str(sum(1 for r in injuries if r["team"] == t and r["game_status"] == "Questionable")),
              str(sum(1 for r in injuries if r["team"] == t)), src_link("NFL-INJ-W10")] for t in teams]
pos_rows = [[e(p), str(n), src_link("NFL-INJ-W10")] for p, n in pos_out.most_common()]

inj_body = f"""
<p class="lede">Official NFL.com Week 10 injury report (Sunday Nov 15 2026 games, plus Thu Nov 12 and Mon Nov 16).
Each row is one player who has an injury entry, a game-status designation, or a practice status other than Full Participation.
Players listed with Full Participation and no designation are omitted; they are on the source page.</p>
<div class="cards">
<div class="card"><b>{nonfull_rows}</b><span>rows captured</span></div>
<div class="card"><b>{status_counts.get('Out', 0)}</b><span>Out</span></div>
<div class="card"><b>{status_counts.get('Doubtful', 0)}</b><span>Doubtful</span></div>
<div class="card"><b>{status_counts.get('Questionable', 0)}</b><span>Questionable</span></div>
<div class="card"><b>{len(teams)}</b><span>teams on the report</span></div>
</div>
<div class="notice"><b>Depth-chart analysis is not built yet.</b> Starter-to-backup mapping (2nd/3rd string
replacements on offense and defense) needs official depth charts, which were not retrieved in this session.
See Questions Q05 and Suggestion S02. Until then the table shows the injury status only.</div>
<h2>Designations by team</h2>
{table(['Team', 'Out', 'Doubtful', 'Questionable', 'Rows', 'Source'], team_rows, 'tbl-team', search=False)}
<h2>Out designations by position</h2>
{table(['Position', 'Out count', 'Source'], pos_rows, 'tbl-pos', search=False)}
<h2>All captured rows</h2>
{table(['Team', 'Game slot', 'Player', 'Pos', 'Injury', 'Practice', 'Game status', 'Note', 'Source'],
       inj_rows, 'tbl-inj')}
"""
page("injuries.html", "Injuries - Week 10 2026 (official report)", inj_body, "injuries.html")

# ---------- Schedule ----------
sched_rows = []
for r in schedule:
    url = r["source_url"]
    src = link(url, SOURCES.get(r["source_id"], {}).get("name", "Official source")) if url else \
        '<span class="flag">no official source</span>'
    vcell = badge(r["verification"])
    sched_rows.append([e(r["item"]), e(r["date_or_window"]), e(r["detail"]), vcell, src])
sched_body = f"""
<p class="lede">Key dates for the 2026 season, taken from the NFL's 2026 schedule announcement. Items that could not
be confirmed from an official source are blank and flagged.</p>
<div class="cards">
<div class="card"><b>{verified_dates}</b><span>verified dates</span></div>
<div class="card"><b>{unverified_dates}</b><span>unverified / flagged</span></div>
</div>
{table(['Item', 'Date / window', 'Detail', 'Verification', 'Source'], sched_rows, 'tbl-sched')}
"""
page("schedule.html", "2026 season key dates", sched_body, "schedule.html")

# ---------- Strategies ----------
STRAT_SOURCE = {
    "S01": "INJ", "S02": "INJ", "S03": "INJ", "S04": "NGS", "S05": "INJ", "S06": "NGS",
    "S07": "SCHED", "S08": "TEAMS",
}
SRC_FOR = {
    "INJ": ("NFL-INJ-W10", SOURCES["NFL-INJ-W10"]["url"]),
    "NGS": ("NFL-NGS", SOURCES["NFL-NGS"]["url"]),
    "SCHED": ("NFL-SCHED-PR", SOURCES["NFL-SCHED-PR"]["url"]),
    "TEAMS": (None, "https://www.nfl.com/teams/"),
}
strat_rows = []
for r in strategies:
    key = STRAT_SOURCE[r["strategy_id"]]
    sid, url = SRC_FOR[key]
    label = SOURCES[sid]["name"] if sid else "NFL.com team pages (not yet retrieved)"
    strat_rows.append([
        e(r["strategy_id"]), e(r["name"]), e(r["bet_type"]), e(r["hypothesis"]),
        e(r["official_input_available"]),
        badge(r["status"]),
        e(r["sample_size"]),
        '<span class="flag">unverified</span>' if not r["roi"] else e(r["roi"]),
        '<span class="flag">unverified</span>' if not r["clv"] else e(r["clv"]),
        e(r["leaderboard_rank"]) or '<span class="flag">not ranked</span>',
        link(url, label),
    ])
gate_rows = [[e(g["gate_id"]), e(g["gate"]), e(g["definition"]), badge(g["status"]), e(g["note"]),
              link(SOURCES["JP-PENAL-185"]["url"], "Penal Code (Art. 185)") if g["gate_id"] == "G9"
              else '<span class="flag">proposed; no external source</span>'] for g in gates]
strat_body = f"""
<p class="lede">Leaderboard for candidate NFL strategies. A strategy ranks only after it passes every validation gate.
<b>No strategy has passed any gate yet</b>, because no historical odds, results or depth-chart data have been retrieved
from a verified source. ROI, CLV and sample sizes are therefore blank and flagged, not estimated.</p>
<div class="cards">
<div class="card"><b>{len(strategies)}</b><span>candidate strategies</span></div>
<div class="card"><b>{validated}</b><span>passed all gates</span></div>
<div class="card"><b>0</b><span>graded bets</span></div>
</div>
<div class="notice"><b>Rewards are not set up.</b> Reward mechanics are a user decision (Questions Q08; Suggestions S06-S07).</div>
<h2>Leaderboard</h2>
{table(['ID', 'Strategy', 'Bet type', 'Hypothesis', 'Official inputs', 'Gate status', 'Sample',
        'ROI', 'CLV', 'Rank', 'Source'], strat_rows, 'tbl-strat')}
<h2>Validation gates</h2>
<p>Gate thresholds marked "proposed" are design choices, not sourced facts, and need user approval (Questions Q07).</p>
{table(['Gate', 'Name', 'Definition', 'Status', 'Note', 'Source'], gate_rows, 'tbl-gates', search=False)}
"""
page("strategies.html", "Strategy leaderboard and validation gates", strat_body, "strategies.html")

# ---------- Correlations ----------
CORR_SRC = {"C01": "NFL-INJ-W10", "C02": "NFL-INJ-W10", "C03": "NFL-NGS", "C04": "NFL-INJ-W10",
            "C05": "NFL-NGS", "C06": None}
corr_rows = []
for r in correlations:
    sid = CORR_SRC.get(r["corr_id"])
    src = src_link(sid) if sid else '<span class="flag">depth charts not retrieved</span>'
    corr_rows.append([e(r["corr_id"]), e(r["signal_a"]), e(r["signal_b"]),
                      '<span class="flag">unverified</span>' if not r["correlation_value"]
                      else e(r["correlation_value"]),
                      e(r["method"]), e(r["sample"]), badge(r["verification"]), e(r["note"]), src])
corr_body = f"""
<p class="lede">Correlation values between signals and between parlay or combo legs. Each value must come from measured
data (gate G8 for parlays). <b>None has been computed.</b> Values stay blank because there is no verified historical dataset yet.</p>
<div class="notice">Correlation between parlay legs is required before any parlay or same-game combo can be assessed.</div>
{table(['ID', 'Signal A', 'Signal B', 'Correlation', 'Method', 'Sample', 'Status', 'Note', 'Source'],
       corr_rows, 'tbl-corr')}
"""
page("correlations.html", "Correlations (not yet computed)", corr_body, "correlations.html")

# ---------- Questions ----------
q_rows = []
for r in questions:
    where = r["where_to_verify"]
    if where.startswith("http"):
        where_html = link(where)
    else:
        where_html = e(where) + ' <span class="flag">no external source (user decision)</span>'
    q_rows.append([e(r["id"]), e(r["category"]), e(r["question"]), e(r["why_it_matters"]),
                   e(r["what_we_have"]), e(r["what_we_lack"]), where_html,
                   e(r["decision_owner"]), badge(r["status"])])
q_body = f"""
<p class="lede">Questions and missing information that must be answered before a decision can reasonably be made.
{open_q} questions are open. Each row lists what we have, what is missing, and where to check it.</p>
{table(['ID', 'Category', 'Question', 'Why it matters', 'What we have', 'What we lack',
        'Where to verify', 'Decision owner', 'Status'], q_rows, 'tbl-q')}
"""
page("questions.html", "Questions and information gaps", q_body, "questions.html")

# ---------- Suggestions ----------
s_rows = []
for r in suggestions:
    url = r["source_link"]
    if url.startswith("http"):
        src = link(url)
    else:
        src = '<span class="flag">not applicable (user decision)</span>'
    s_rows.append([e(r["id"]), e(r["area"]), e(r["suggestion"]), e(r["options"]), e(r["pros"]),
                   e(r["cons"]), src, badge(r["decision"]), badge(r["status"])])
s_body = f"""
<p class="lede">Suggestions for improving the site and the research process. <b>Nothing on this page has been
implemented.</b> Review the options and mark your choice; each item is implemented only after a decision.
{pending_s} suggestions are awaiting your decision.</p>
<div class="notice">How to decide: pick an option letter for each item (for example "S01: B") and the chosen path will be implemented in the next session.</div>
{table(['ID', 'Area', 'Suggestion', 'Options', 'Pros', 'Cons', 'Source', 'Decision', 'Status'],
       s_rows, 'tbl-s')}
"""
page("suggestions.html", "Suggestions (awaiting review)", s_body, "suggestions.html")

# ---------- Requirements ----------
RQ_LINK = {"docs/requirements.html": "requirements.html", "docs/suggestions.html": "suggestions.html",
           "docs/questions.html": "questions.html", "docs/strategies.html": "strategies.html",
           "docs/correlations.html": "correlations.html", "docs/injuries.html": "injuries.html",
           "docs/executive-summary.html": "executive-summary.html", "docs/flagged.html": "flagged.html",
           "docs/index.html": "index.html", "docs/sources.html": "sources.html",
           "COORDINATION.md": "https://github.com/karagemop466-tech/X3/blob/arena/0c38f465-x3/COORDINATION.md"}
rq_rows = []
for r in requirements:
    ev = r["evidence_link"]
    href = RQ_LINK.get(ev, ev)
    if href.startswith("http"):
        ev_html = link(href, ev)
    else:
        ev_html = f'<a href="{e(href)}">{e(href)}</a>'
    rq_rows.append([e(r["id"]), e(r["requirement"]), badge(r["status"]), e(r["delivered"]),
                    ev_html + ' <span class="flag">internal page</span>' if not ev.startswith("http") else ev_html])
rq_body = f"""
<p class="lede">Tracker for each item in the project brief. Status is shown as delivered, partial, or blocked.
Requirements are internal, so their evidence links point to the site pages and repo files; they are not official sources.</p>
{table(['ID', 'Requirement', 'Status', 'What was delivered', 'Evidence'], rq_rows, 'tbl-rq')}
"""
page("requirements.html", "Requirements tracker", rq_body, "requirements.html")

# ---------- Sources ----------
src_rows = []
for r in sources:
    src_rows.append([e(r["source_id"]), e(r["name"]), e(r["publisher"]), link(r["url"]), e(r["type"]),
                     e(r["used_for"]), e(r["fetch_status"]), e(r["checked_on"]), e(r["notes"])])
src_body = f"""
<p class="lede">Source registry. Official sources are the only basis for table values. Third-party pages are listed only
to document conflicts and are never used as a source for a value.</p>
{table(['ID', 'Name', 'Publisher', 'Link', 'Type', 'Used for', 'Fetch status', 'Checked', 'Notes'],
       src_rows, 'tbl-src')}
"""
page("sources.html", "Official sources registry", src_body, "sources.html")

# ---------- Flagged ----------
f_rows = []
for r in flags:
    sev = r["severity"]
    f_rows.append([e(r["id"]), f'<span class="badge {"flag" if sev == "High" else "todo"}">{e(sev)}</span>',
                   e(r["area"]), e(r["issue"]), e(r["evidence"]), link(r["source_link"]),
                   e(r["action_for_user"])])
f_body = f"""
<p class="lede"><b>Flagged for Review.</b> These are irregularities, conflicts and unverified items found while building
the site. They do not block publication. Each row has a link so you can check it. Tell us which to change.</p>
<div class="cards">
<div class="card"><b>{len(flags)}</b><span>flags</span></div>
<div class="card"><b>{high_flags}</b><span>high severity</span></div>
</div>
{table(['ID', 'Severity', 'Area', 'Issue', 'Evidence', 'Source link', 'Action for you'],
       f_rows, 'tbl-flags')}
"""
page("flagged.html", "Flagged for Review", f_body, "flagged.html")

# ---------- Executive summary ----------
top_out = ", ".join(f"{p} ({n})" for p, n in pos_out.most_common(4))
exec_body = f"""
<p class="lede">Snapshot as of {AS_OF} (Week 10 of the 2026 NFL season). This summary states only what is verified.</p>
<h2>1. What this project is</h2>
<p>A research workspace to collect NFL information, track injuries, and test candidate strategies for NFL lines
(single bets, parlays and player-prop combos). Strategies are ranked on a leaderboard only after passing validation gates.</p>
<h2>2. What is verified now</h2>
<ul>
<li>Week 10 official injury report captured: <b>{nonfull_rows} rows</b> across {len(teams)} teams
(<a href="{e(SOURCES['NFL-INJ-W10']['url'])}" target="_blank" rel="noopener">NFL.com source</a>).</li>
<li>Out designations on the report: <b>{status_counts.get('Out', 0)}</b>; Doubtful: <b>{status_counts.get('Doubtful', 0)}</b>;
Questionable: <b>{status_counts.get('Questionable', 0)}</b>.</li>
<li>Most Out designations by position: {e(top_out)}.</li>
<li>2026 season key dates from the NFL schedule announcement: {verified_dates} verified items
(<a href="{e(SOURCES['NFL-SCHED-PR']['url'])}" target="_blank" rel="noopener">NFL Media</a>).</li>
</ul>
<h2>3. What is not known yet</h2>
<ul>
<li><b>No strategy is validated.</b> There is no verified historical odds, results or depth-chart data, so ROI, CLV, sample size and correlations are blank.</li>
<li><b>Backup analysis is not built.</b> Starter-to-backup replacement status needs official depth charts (Questions Q05).</li>
<li><b>Injury history is limited.</b> Only one official snapshot (Week 10) has been captured (Questions Q04).</li>
</ul>
<h2>4. Key risks</h2>
<ul>
<li><b>Legal:</b> Wagering with private bookmakers from Japan is a criminal offence for the bettor under Penal Code Article 185
(<a href="{e(SOURCES['JP-PENAL-185']['url'])}" target="_blank" rel="noopener">official source</a>). Legal review is needed before any wagering (Suggestion S08).</li>
<li><b>Source conflicts:</b> The NFL.com page titled 2026 important dates lists 2025-season dates; Thanksgiving matchups conflict across sources (see Flagged for Review).</li>
<li><b>Data quality:</b> Name and position labels differ between the report and the news article; some injured players show blank injury fields.</li>
</ul>
<h2>5. Decisions needed from you</h2>
<ul>
<li>Scope: research only, or research plus paper-trading (Suggestion S08; Questions Q01-Q02).</li>
<li>Data sources: which odds provider, and approval to collect depth charts and injury history (Questions Q03-Q06; Suggestions S01-S02).</li>
<li>Validation thresholds and reward design (Questions Q07-Q08; Suggestions S03-S07).</li>
</ul>
<p>Open questions: <b>{open_q}</b> &middot; Suggestions awaiting decision: <b>{pending_s}</b> &middot;
Flags: <b>{len(flags)}</b> ({high_flags} high).</p>
<p><a href="suggestions.html">Review suggestions</a> &middot; <a href="questions.html">Review questions</a> &middot;
<a href="flagged.html">Flagged for Review</a></p>
"""
page("executive-summary.html", "Executive summary", exec_body, "executive-summary.html")

# ---------- Dashboard ----------
dash_body = f"""
<p class="lede">A simple dashboard for NFL data, injury tracking and strategy research. Pick a category below.
<b>This is research, not betting advice.</b></p>
<div class="cards">
<div class="card"><b>{nonfull_rows}</b><span>injury rows (Week 10, official)</span></div>
<div class="card"><b>{len(teams)}</b><span>teams on the Week 10 report</span></div>
<div class="card"><b>{verified_dates}</b><span>verified 2026 key dates</span></div>
<div class="card"><b>{validated}</b><span>validated strategies</span></div>
<div class="card"><b>{open_q}</b><span>open questions</span></div>
<div class="card"><b>{pending_s}</b><span>suggestions awaiting decision</span></div>
</div>
<div class="grid">
<a class="tile" href="executive-summary.html"><b>Executive summary</b><span>Verified facts, gaps, risks and decisions needed</span></a>
<a class="tile" href="injuries.html"><b>Injuries</b><span>Official Week 10 report by team and position</span></a>
<a class="tile" href="schedule.html"><b>2026 key dates</b><span>Season dates from the NFL announcement</span></a>
<a class="tile" href="strategies.html"><b>Strategy leaderboard</b><span>Candidate strategies and validation gates</span></a>
<a class="tile" href="correlations.html"><b>Correlations</b><span>Not yet computed; blank until data is verified</span></a>
<a class="tile" href="questions.html"><b>Questions</b><span>What must be answered before deciding</span></a>
<a class="tile" href="suggestions.html"><b>Suggestions</b><span>Options to review; nothing implemented yet</span></a>
<a class="tile" href="requirements.html"><b>Requirements</b><span>Tracker for every item in the brief</span></a>
<a class="tile" href="sources.html"><b>Official sources</b><span>Registry of links and fetch status</span></a>
<a class="tile flagtile" href="flagged.html"><b>Flagged for Review</b><span>{len(flags)} irregularities and unverified items with links</span></a>
</div>
<div class="notice"><b>Legal note:</b> Under Japanese Penal Code Article 185, betting on sports with a private bookmaker is
gambling, and a bettor can be fined. This site does not recommend any wager.
(<a href="{e(SOURCES['JP-PENAL-185']['url'])}" target="_blank" rel="noopener">Official text</a>)</div>
"""
page("index.html", "Dashboard", dash_body, "index.html")

print("built", len(os.listdir(DOCS)), "files")
