#!/usr/bin/env python3
"""Generate docs/pages/injuries.html and docs/pages/standings.html from verified CSVs.

Every generated data row carries its official source link. Values that cannot be
verified are rendered as blank cells with an UNVERIFIED badge — never inferred.
"""
import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
PAGES = ROOT / "docs" / "pages"

NAV = [
    ("../index.html", "Dashboard"),
    ("executive-summary.html", "Executive Summary"),
    ("requirements.html", "Requirements"),
    ("strategies.html", "Line Origination"),
    ("validation.html", "Validation"),
    ("correlation.html", "Correlation"),
    ("leaderboard.html", "Leaderboard"),
    ("injuries.html", "Injuries"),
    ("standings.html", "Standings"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged"),
    ("sources.html", "Sources"),
    ("repo-audit.html", "Repo Audit"),
]


def shell(title, body, active):
    nav = " ".join(
        f'<a href="{href}"{" class=active" if label == active else ""}>{label}</a>'
        for href, label in NAV
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — X3 NFL Research</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header><h1>{html.escape(title)}</h1>
<p class="meta">X3 NFL Research &amp; Line-Origination Project · data captured 2026-11-14 ·
every row links to an official source · blank = UNVERIFIED (never inferred)</p>
<nav>{nav}</nav>
</header>
<main>
{body}
</main>
<footer><p>Built by session arena-4856379c · verification policy: every table row carries an
official source link or is blank and flagged UNVERIFIED · see <a href="sources.html">Sources</a>
and <a href="flagged.html">Flagged for Review</a>.</p></footer>
</body>
</html>
"""


UNIT_MAP = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "T": "OL", "G": "OL", "C": "OL",
    "DT": "DL", "DE": "DL", "EDGE": "DL",
    "LB": "LB", "CB": "DB", "S": "DB",
    "K": "ST", "P": "ST", "LS": "ST",
}


def build_injuries():
    rows = list(csv.DictReader(open(DATA / "injury-2026-week10.csv")))
    # ---- team summary -------------------------------------------------
    teams = {}
    for r in rows:
        t = teams.setdefault(r["team"], {
            "record": r["team_record"], "Out": 0, "Doubtful": 0,
            "Questionable": 0, "no_status": 0, "units": {}, "rest_out": 0,
            "players_out": [],
        })
        gs = r["game_status"]
        rest = "resting player" in r["injury"]
        if gs in ("Out", "Doubtful", "Questionable"):
            if rest and gs == "Out":
                t["rest_out"] += 1
            else:
                t[gs] += 1
                unit = UNIT_MAP.get(r["position"], "OTHER")
                t["units"][unit] = t["units"].get(unit, 0) + 1
                if gs in ("Out", "Doubtful"):
                    t["players_out"].append(f'{r["player"]} ({r["position"]})')
        elif gs == "":
            t["no_status"] += 1

    out = []
    out.append("""<h2>Team deficiency summary — 2026 Week 10</h2>
<p>Counts include only official game-status designations (Out / Doubtful / Questionable) from the
official injury report. Rows whose injury reason is &quot;Not injury related - resting player&quot;
are counted separately (rest, not injury). <b>Depth rank (1st/2nd/3rd/4th string) is
<span class="flag">UNVERIFIED</span></b> — official depth-chart pages returned 404 on 2026-11-14
(Flagged F-04), so starter-vs-backup columns are intentionally blank and never inferred.</p>""")
    out.append("""<table><thead><tr><th>Team</th><th>Record</th><th>Out</th><th>Doubtful</th>
<th>Questionable</th><th>Out/Doubtful players (verified names)</th><th>Unit counts (Out+Doubtful+Q)</th>
<th>Rest-outs</th><th>Depth rank of replacements</th><th>Source</th></tr></thead><tbody>""")
    for team in sorted(teams):
        t = teams[team]
        units = ", ".join(f"{u}×{n}" for u, n in sorted(t["units"].items())) or "—"
        players = "; ".join(t["players_out"]) or "—"
        out.append(
            f'<tr><td><b>{team}</b></td><td>{t["record"]}</td><td>{t["Out"]}</td>'
            f'<td>{t["Doubtful"]}</td><td>{t["Questionable"]}</td>'
            f'<td>{html.escape(players)}</td><td>{units}</td><td>{t["rest_out"]}</td>'
            f'<td class="flag">UNVERIFIED</td>'
            f'<td><a href="https://www.nfl.com/injuries/">nfl.com/injuries</a></td></tr>'
        )
    out.append("</tbody></table>")

    # ---- critical alerts ---------------------------------------------
    out.append("""<h2>Critical deficiency alerts (verified)</h2>
<table><thead><tr><th>Alert</th><th>Verified detail</th><th>Depth rank of replacement</th>
<th>Source</th></tr></thead><tbody>
<tr><td><b>BAL — QB room</b></td><td>Lamar Jackson (QB) placed on injured reserve (right thumb);
backup Tyler Huntley (QB) out for season (turf toe) → 3rd/4th-string QBs expected vs LAC</td>
<td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/news/ravens-lamar-jackson-right-thumb-out-6-9-weeks-expects-to-return-this-season">nfl.com news (Jackson)</a> ·
<a href="https://www.nfl.com/news/ravens-qb-tyler-huntley-out-for-season-turf-toe-injury">nfl.com news (Huntley)</a></td></tr>
<tr><td><b>MIN — QB1 out</b></td><td>Kyler Murray (QB, hamstring) Out; Carson Wentz (QB) full
participation, no designation</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/injuries/">nfl.com/injuries</a></td></tr>
<tr><td><b>SEA — QB1 out</b></td><td>Sam Darnold (QB, ribs/quad) Out; Drew Lock to start (no injury
designation)</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again">nfl.com news</a></td></tr>
<tr><td><b>MIA — QB on IR + starting C out</b></td><td>Malik Willis (QB, groin) placed on IR; Kyle
McCord in line for first start; Aaron Brewer (C) Out (concussion)</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start">nfl.com news (Willis IR)</a> ·
<a href="https://www.nfl.com/injuries/">nfl.com/injuries</a></td></tr>
<tr><td><b>ARI — QB change</b></td><td>Carson Beck to start vs LAR</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11">nfl.com news roundup (Nov 11)</a></td></tr>
<tr><td><b>DET — secondary + center</b></td><td>Kerby Joseph (S) Out, D.J. Reed (CB) Out, Cade Mays
(C) Out</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/injuries/">nfl.com/injuries</a></td></tr>
<tr><td><b>GB — RB1 / pass rush / center</b></td><td>Josh Jacobs (RB) Out (finger surgery); Micah
Parsons (LB) Out; Sean Rhyan (C) Out; Zaire Franklin (LB) Doubtful</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/news/packers-rb-josh-jacobs-to-undergo-surgery-on-finger-this-week">nfl.com news (Jacobs)</a> ·
<a href="https://www.nfl.com/injuries/">nfl.com/injuries</a></td></tr>
<tr><td><b>HOU — pass rush + WR1</b></td><td>Danielle Hunter (DE) Out; Azeez Al-Shaair (LB) Out;
Marvin Harrison Jr. (WR) Out</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/injuries/">nfl.com/injuries</a></td></tr>
<tr><td><b>LAR — WR1 likely IR</b></td><td>Puka Nacua likely placed on IR (turf toe, sprained MCL/PCL);
Steve Avila (G) Out; Terrance Ferguson (TE) Out</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/news/rams-wr-puka-nacua-likely-to-be-placed-on-injured-reserve-with-turf-toe-sprained-mcl-and-pcl">nfl.com news (Nacua)</a></td></tr>
<tr><td><b>NE — RB / CB / C</b></td><td>TreVeyon Henderson (RB) Out; Carlton Davis III (CB) Out;
Ben Brown (C) Out</td><td class="flag">UNVERIFIED</td>
<td><a href="https://www.nfl.com/injuries/">nfl.com/injuries</a></td></tr>
</tbody></table>""")

    # ---- full per-game tables ----------------------------------------
    out.append("""<h2>Full official report — every captured row</h2>
<p>All 345 rows transcribed from the official Week-10 2026 injury report
(<a href="https://www.nfl.com/injuries/">nfl.com/injuries</a>, captured 2026-11-14). Practice status:
Full = full participation, Limited = limited participation, DNP = did not participate.</p>""")
    games = []
    for r in rows:
        if r["game"] not in [g for g, _ in games]:
            games.append((r["game"], r["kickoff_et"]))
    for game, kickoff in games:
        out.append(f'<h3>{html.escape(game)} — {html.escape(kickoff)} ET</h3>')
        out.append("""<table><thead><tr><th>Team</th><th>Player</th><th>Pos</th><th>Injury</th>
<th>Practice</th><th>Game status</th><th>Source</th></tr></thead><tbody>""")
        for r in rows:
            if r["game"] != game:
                continue
            gs = r["game_status"] or '—'
            cls = ""
            if r["game_status"] == "Out":
                cls = ' class="st-out"'
            elif r["game_status"] == "Doubtful":
                cls = ' class="st-doubt"'
            elif r["game_status"] == "Questionable":
                cls = ' class="st-quest"'
            out.append(
                f'<tr><td>{r["team"]}</td><td>{html.escape(r["player"])}</td>'
                f'<td>{r["position"]}</td><td>{html.escape(r["injury"]) or "&nbsp;"}</td>'
                f'<td>{r["practice_status"]}</td><td{cls}>{gs}</td>'
                f'<td><a href="{r["source_url"]}">nfl.com/injuries</a></td></tr>'
            )
        out.append("</tbody></table>")

    out.append("""<h2>Tracker methodology &amp; data gaps</h2>
<ul>
<li><b>Depth ranks (2nd/3rd/4th string replacements):</b>
<span class="flag">UNVERIFIED — blank by policy</span>. nfl.com/depthcharts and
/teams/*/depth-chart/ return 404 (tested 2026-11-14). Discovery paths: official club sites'
depth-chart pages, official personnel notices, snap-count evidence (nfl.com/stats). Flagged F-04.</li>
<li><b>IR players do not appear in weekly game-status reports</b> (designations cover active-roster
players) — IR tracking must come from nfl.com/news transaction headlines (verified examples linked
above) and official personnel notices.</li>
<li><b>Rest designations:</b> &quot;Not injury related - resting player&quot; rows are excluded from
injury severity but tracked (see rest-outs column) — e.g., 2 Jaguars listed Out for rest.</li>
<li><b>Blank game status ≠ healthy.</b> Rows with no game status (185 this week) are players on the
report without a designation; several are DNP without status (e.g., Aaron Donald, Puka Nacua) and
need follow-up (Flagged F-09).</li>
<li>Historical reports are available per-week back to 1965 on the same official page (year selector
verified) — backfill path for historical analysis (Questions page Q-10).</li>
</ul>""")

    (PAGES / "injuries.html").write_text(
        shell("Injury &amp; Depth Tracker — 2026 Week 10", "\n".join(out), "Injuries")
    )
    print("injuries.html rows:", len(rows))


def build_standings():
    rows = list(csv.DictReader(open(DATA / "standings-2026-week10.csv")))
    out = ["""<h2>2026 NFL standings — snapshot 2026-11-14</h2>
<p>Transcribed from the official standings page
<a href="https://www.nfl.com/standings/">nfl.com/standings</a> (2026 regular season, detailed view).
Team records were cross-checked against the official injury page's team headers — all 28 non-bye
teams match. Two source columns (a record the source does not label in its legend, and a
&quot;last 5&quot;-style column) are preserved in the CSV but hidden here pending label
verification — Flagged F-11.</p>"""]
    for conf in ("AFC", "NFC"):
        out.append(f"<h2>{conf}</h2>")
        for div in ("East", "North", "South", "West"):
            out.append(f"<h3>{conf} {div}</h3>")
            out.append("""<table><thead><tr><th>Team</th><th>W</th><th>L</th><th>T</th><th>PCT</th>
<th>PF</th><th>PA</th><th>NET</th><th>Home</th><th>Road</th><th>Div</th><th>Conf</th><th>Streak</th>
<th>Source</th></tr></thead><tbody>""")
            for r in rows:
                if r["conference"] != conf or r["division"] != div:
                    continue
                net = f'+{r["net"]}' if int(r["net"]) > 0 else r["net"]
                out.append(
                    f'<tr><td><b>{r["team"]}</b></td><td>{r["w"]}</td><td>{r["l"]}</td>'
                    f'<td>{r["t"]}</td><td>{r["pct"]}</td><td>{r["pf"]}</td><td>{r["pa"]}</td>'
                    f'<td>{net}</td><td>{r["home"]}</td><td>{r["road"]}</td><td>{r["div"]}</td>'
                    f'<td>{r["conf"]}</td><td>{r["strk"]}</td>'
                    f'<td><a href="{r["source_url"]}">nfl.com/standings</a></td></tr>'
                )
            out.append("</tbody></table>")
    out.append("""<p class="meta">W = wins, L = losses, T = ties, PCT = winning percentage (ties count
as half-win in the source's own PCT column), PF/PA = points for/against, NET = point differential.</p>""")
    (PAGES / "standings.html").write_text(
        shell("2026 Standings Snapshot", "\n".join(out), "Standings")
    )
    print("standings.html rows:", len(rows))


if __name__ == "__main__":
    build_injuries()
    build_standings()
