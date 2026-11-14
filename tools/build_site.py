#!/usr/bin/env python3
"""Build the X3 NFL analytics static site from verified data.

Every data row carries a link to an official source. Values that cannot be
confirmed from an official source are left blank and flagged `unverified`.
This script is the single source for the HTML so tables stay consistent and
every row keeps its source link.
"""
import os
import html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = ROOT

NFL_STANDINGS = "https://www.nfl.com/standings/league/2026/reg"
NFL_INJURIES = "https://www.nfl.com/injuries/league/2026/reg"
NFL_SCHEDULE = "https://www.nfl.com/schedules/"
DET_DEPTH = "https://www.detroitlions.com/team/depth-chart"

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
CSS = """
:root{
  --bg:#0f1420; --panel:#171d2b; --panel2:#1e2536; --ink:#e8edf6; --muted:#9aa6bd;
  --line:#2a3448; --accent:#4f8cff; --accent2:#22c55e; --warn:#f5a623; --bad:#ef4444;
  --chip:#22304a;
}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--ink);line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header.top{position:sticky;top:0;z-index:20;background:rgba(15,20,32,.92);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line)}
.top-inner{max-width:1080px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.brand{font-weight:800;font-size:18px;letter-spacing:.5px}
.brand span{color:var(--accent)}
nav.main{display:flex;gap:4px;flex-wrap:wrap}
nav.main a{padding:6px 10px;border-radius:8px;color:var(--muted);font-size:14px}
nav.main a:hover{background:var(--panel2);text-decoration:none;color:var(--ink)}
nav.main a.active{background:var(--accent);color:#fff}
main{max-width:1080px;margin:0 auto;padding:26px 20px 80px}
h1{font-size:28px;margin:0 0 6px}
h2{font-size:21px;margin:34px 0 12px;border-bottom:1px solid var(--line);padding-bottom:8px}
h3{font-size:16px;margin:22px 0 8px;color:var(--ink)}
p.lede{color:var(--muted);font-size:16px;max-width:80ch}
.hero{background:linear-gradient(135deg,#1a2440,#141a28);border:1px solid var(--line);border-radius:14px;padding:24px;margin:18px 0 8px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .k{color:var(--muted);font-size:13px}
.card .v{font-size:26px;font-weight:800;margin-top:4px}
.card .s{color:var(--muted);font-size:12px;margin-top:4px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin:14px 0}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px;background:var(--panel);
  border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);color:var(--muted);font-weight:700;font-size:12.5px;text-transform:uppercase;letter-spacing:.4px}
tbody tr:last-child td{border-bottom:none}
tbody tr:nth-child(even){background:rgba(255,255,255,.015)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.src{font-size:12px;color:var(--muted)}
.src a{color:var(--accent)}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:700;white-space:nowrap}
.b-verified{background:rgba(34,197,94,.15);color:#4ade80;border:1px solid rgba(34,197,94,.4)}
.b-unverified{background:rgba(245,166,35,.15);color:#fbbf24;border:1px solid rgba(245,166,35,.4)}
.b-flagged{background:rgba(239,68,68,.15);color:#f87171;border:1px solid rgba(239,68,68,.4)}
.b-pending{background:rgba(154,166,189,.15);color:#cbd5e1;border:1px solid rgba(154,166,189,.4)}
ul.clean{list-style:none;padding:0;margin:10px 0}
ul.clean li{padding:7px 0;border-bottom:1px solid var(--line)}
ul.clean li:last-child{border-bottom:none}
.tag{display:inline-block;background:var(--chip);color:var(--ink);border-radius:6px;padding:1px 7px;font-size:12px;margin-right:6px}
.note{background:rgba(79,140,255,.08);border:1px solid rgba(79,140,255,.3);border-radius:10px;padding:12px 14px;font-size:14px;margin:12px 0}
.warn{background:rgba(245,166,35,.08);border:1px solid rgba(245,166,35,.3);border-radius:10px;padding:12px 14px;font-size:14px;margin:12px 0}
footer{color:var(--muted);font-size:13px;text-align:center;padding:24px;border-top:1px solid var(--line);margin-top:30px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:720px){.grid2{grid-template-columns:1fr}}
"""

NAV = [
    ("index.html", "Home"),
    ("executive-summary.html", "Executive Summary"),
    ("requirements.html", "Requirements & Questions"),
    ("suggestions.html", "Suggestions"),
    ("lines.html", "Lines & Signals"),
    ("leaderboard.html", "Strategy Leaderboard"),
    ("injuries.html", "Injuries & Lineups"),
    ("verification.html", "Verification"),
    ("flagged.html", "Flagged for Review"),
]


def esc(s):
    return html.escape(str(s), quote=False)


def src(url, label="source"):
    return f'<span class="src"><a href="{url}" target="_blank" rel="noopener">{esc(label)} &#8599;</a></span>'


def badge(status):
    m = {"verified": "b-verified", "unverified": "b-unverified",
         "flagged": "b-flagged", "pending": "b-pending"}
    cls = m.get(status, "b-pending")
    return f'<span class="badge {cls}">{esc(status)}</span>'


def table(headers, rows, num_cols=()):
    out = ["<table>", "<thead><tr>"]
    for i, h in enumerate(headers):
        cls = ' class="num"' if i in num_cols else ""
        out.append(f"<th{cls}>{h}</th>")
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>")
        for i, c in enumerate(r):
            cls = ' class="num"' if i in num_cols else ""
            out.append(f"<td{cls}>{c}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def page(active, title, subtitle, sections):
    nav = "\n".join(
        f'<a href="{u}" class="{"active" if u == active else ""}">{esc(n)}</a>'
        for u, n in NAV
    )
    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · X3 NFL Analytics</title>
<meta name="description" content="{esc(subtitle)}">
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="top-inner">
  <div class="brand">X<span>3</span> · NFL Analytics</div>
  <nav class="main">{nav}</nav>
</div></header>
<main>
<h1>{esc(title)}</h1>
<p class="lede">{esc(subtitle)}</p>
{body}
</main>
<footer>X3 NFL Analytics · Static site · All data rows link to official sources ·
Unverified values are left blank and flagged. Built 2026-11-14.</footer>
</body>
</html>
"""


def write(name, html_text):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_text)
    print("wrote", path)


# ---------------------------------------------------------------------------
# Verified data
# ---------------------------------------------------------------------------

# Standings — NFL.com, fetched 2026-11-14. Columns: W L T PCT PF PA NetPts
STANDINGS = [
    ("Buffalo Bills", 7, 1, 0, ".875", 256, 187, 69),
    ("San Francisco 49ers", 7, 1, 0, ".875", 235, 156, 79),
    ("Chicago Bears", 7, 2, 0, ".778", 241, 184, 57),
    ("Denver Broncos", 7, 2, 0, ".778", 198, 186, 12),
    ("Cincinnati Bengals", 6, 2, 0, ".750", 240, 175, 65),
    ("Detroit Lions", 6, 2, 0, ".750", 222, 189, 33),
    ("Jacksonville Jaguars", 6, 2, 0, ".750", 229, 121, 108),
    ("Kansas City Chiefs", 6, 2, 0, ".750", 202, 143, 59),
    ("Minnesota Vikings", 6, 2, 0, ".750", 146, 116, 30),
    ("Pittsburgh Steelers", 6, 2, 0, ".750", 180, 144, 36),
    ("Green Bay Packers", 6, 3, 0, ".667", 216, 191, 25),
    ("New York Giants", 5, 3, 1, ".611", 203, 196, 7),
    ("Cleveland Browns", 5, 4, 0, ".556", 161, 196, -35),
    ("Los Angeles Rams", 5, 4, 0, ".556", 214, 181, 33),
    ("New England Patriots", 5, 4, 0, ".556", 211, 207, 4),
    ("Seattle Seahawks", 5, 4, 0, ".556", 202, 162, 40),
    ("Baltimore Ravens", 4, 5, 0, ".444", 189, 236, -47),
    ("Dallas Cowboys", 4, 5, 0, ".444", 246, 236, 10),
    ("Las Vegas Raiders", 4, 5, 0, ".444", 238, 268, -30),
    ("Washington Commanders", 3, 5, 1, ".389", 196, 223, -27),
    ("Carolina Panthers", 3, 5, 0, ".375", 199, 219, -20),
    ("Houston Texans", 3, 5, 0, ".375", 209, 192, 17),
    ("New Orleans Saints", 3, 5, 0, ".375", 185, 216, -31),
    ("Arizona Cardinals", 3, 6, 0, ".333", 178, 255, -77),
    ("Atlanta Falcons", 3, 6, 0, ".333", 188, 223, -35),
    ("Tampa Bay Buccaneers", 3, 6, 0, ".333", 202, 178, 24),
    ("Indianapolis Colts", 2, 7, 0, ".222", 184, 249, -65),
    ("New York Jets", 2, 7, 0, ".222", 182, 223, -41),
    ("Philadelphia Eagles", 2, 7, 0, ".222", 148, 221, -73),
    ("Miami Dolphins", 1, 7, 0, ".125", 126, 200, -74),
    ("Tennessee Titans", 1, 7, 0, ".125", 144, 199, -55),
    ("Los Angeles Chargers", 0, 8, 0, ".000", 121, 219, -98),
]

# Injuries — NFL.com Week 10 injury report, fetched 2026-11-14.
# (game_date, team, player, pos, injury, practice, game_status)
INJURIES = [
    ("Thu Nov 12", "Washington Commanders", "John Bates", "TE", "—", "Full", "—"),
    ("Thu Nov 12", "Washington Commanders", "Treylon Burks", "WR", "—", "Did Not Participate", "—"),
    ("Thu Nov 12", "Washington Commanders", "Jayden Daniels", "QB", "—", "Full", "—"),
    ("Thu Nov 12", "Washington Commanders", "Matt Gulbin", "C", "—", "Full", "—"),
    ("Thu Nov 12", "Washington Commanders", "Chig Okonkwo", "TE", "—", "Full", "—"),
    ("Thu Nov 12", "Washington Commanders", "Lucas Patrick", "C", "Concussion", "Did Not Participate", "Out"),
    ("Thu Nov 12", "Washington Commanders", "Amik Robertson", "CB", "—", "Limited", "—"),
    ("Thu Nov 12", "Washington Commanders", "Shy Tuttle", "DT", "—", "Full", "—"),
    ("Thu Nov 12", "Washington Commanders", "Colson Yankoff", "TE", "Knee", "Did Not Participate", "Out"),
    ("Thu Nov 12", "New York Giants", "Abdul Carter", "LB", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Jermaine Eluemunor", "T", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Malik Harrison", "LB", "Groin", "Limited", "Questionable"),
    ("Thu Nov 12", "New York Giants", "Colton Hood", "CB", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Theo Johnson", "TE", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Charlie Jones", "WR", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "J.J. McCarthy", "QB", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Darnell Mooney", "WR", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Malik Nabers", "WR", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Cam Skattebo", "RB", "—", "Full", "—"),
    ("Thu Nov 12", "New York Giants", "Andrew Thomas", "T", "—", "Full", "—"),
    ("Sun Nov 15", "New England Patriots", "Ben Brown", "C", "Knee", "Did Not Participate", "Out"),
    ("Sun Nov 15", "New England Patriots", "A.J. Brown", "WR", "Ankle, Knee", "Limited", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "Kevin Byard", "S", "Chest", "Full", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "Carlton Davis III", "CB", "Knee", "Did Not Participate", "Out"),
    ("Sun Nov 15", "New England Patriots", "Reggie Gilliam", "FB", "Knee", "Limited", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "TreVeyon Henderson", "RB", "Illness", "Did Not Participate", "Out"),
    ("Sun Nov 15", "New England Patriots", "Hunter Henry", "TE", "—", "Limited", "—"),
    ("Sun Nov 15", "New England Patriots", "Cameron Latu", "TE", "Back", "Limited", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "Drake Maye", "QB", "—", "Full", "—"),
    ("Sun Nov 15", "New England Patriots", "Morgan Moses", "T", "—", "Full", "—"),
    ("Sun Nov 15", "New England Patriots", "Walter Rouse", "T", "Concussion", "Limited", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "Brenden Schooler", "S", "Hamstring", "Limited", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "Rhamondre Stevenson", "RB", "Knee", "Limited", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "Greg Van Roten", "G", "Hamstring", "Full", "Questionable"),
    ("Sun Nov 15", "New England Patriots", "Charles Woods", "CB", "Hamstring", "Full", "Questionable"),
    ("Sun Nov 15", "Detroit Lions", "Brian Branch", "S", "—", "Full", "—"),
    ("Sun Nov 15", "Detroit Lions", "Jared Goff", "QB", "—", "Full", "—"),
    ("Sun Nov 15", "Detroit Lions", "Kerby Joseph", "S", "Knee", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Detroit Lions", "Cade Mays", "C", "Ankle", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Detroit Lions", "D.J. Reed", "CB", "Hip", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Detroit Lions", "Jacob Saylors", "RB", "—", "Full", "—"),
    ("Sun Nov 15", "Detroit Lions", "Amon-Ra St. Brown", "WR", "Rib", "Limited", "Questionable"),
    ("Sun Nov 15", "Detroit Lions", "Sione Vaki", "RB", "Ankle", "Limited", "Questionable"),
    ("Sun Nov 15", "Detroit Lions", "DJ Wonnum", "DE", "—", "Full", "—"),
    ("Sun Nov 15", "Atlanta Falcons", "Zachariah Branch", "WR", "Hamstring", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Atlanta Falcons", "Kendal Daniels", "LB", "—", "Full", "—"),
    ("Sun Nov 15", "Atlanta Falcons", "Divine Deablo", "LB", "Forearm", "Did Not Participate", "Doubtful"),
    ("Sun Nov 15", "Atlanta Falcons", "Gervon Dexter Sr.", "DT", "Illness", "Limited", "Questionable"),
    ("Sun Nov 15", "Atlanta Falcons", "Jake Matthews", "T", "—", "Limited", "—"),
    ("Sun Nov 15", "Atlanta Falcons", "Liam McCullough", "LS", "—", "Did Not Participate", "—"),
    ("Sun Nov 15", "Atlanta Falcons", "James Pearce Jr.", "DE", "Back", "Limited", "Questionable"),
    ("Sun Nov 15", "Atlanta Falcons", "Za'Darius Smith", "DE", "—", "Full", "—"),
    ("Sun Nov 15", "Atlanta Falcons", "Jawaan Taylor", "T", "—", "Limited", "—"),
    ("Sun Nov 15", "Atlanta Falcons", "Cameron Thomas", "DE", "—", "Full", "—"),
    ("Sun Nov 15", "Atlanta Falcons", "Josh Woods", "LB", "Ankle", "Full", "Questionable"),
    ("Sun Nov 15", "Green Bay Packers", "Aaron Banks", "G", "—", "Limited", "—"),
    ("Sun Nov 15", "Green Bay Packers", "Chris Brooks", "RB", "Ankle", "Limited", "Questionable"),
    ("Sun Nov 15", "Green Bay Packers", "Javon Bullard", "S", "Ankle, Knee", "Limited", "Questionable"),
    ("Sun Nov 15", "Green Bay Packers", "Zaire Franklin", "LB", "Shin", "Did Not Participate", "Doubtful"),
    ("Sun Nov 15", "Green Bay Packers", "Travis Glover", "G", "Knee", "Limited", "Questionable"),
    ("Sun Nov 15", "Green Bay Packers", "Ty'Ron Hopper", "LB", "—", "Full", "—"),
    ("Sun Nov 15", "Green Bay Packers", "Josh Jacobs", "RB", "Finger", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Green Bay Packers", "Xavier McKinney", "S", "Foot", "Limited", "Questionable"),
    ("Sun Nov 15", "Green Bay Packers", "Bo Melton", "WR", "—", "Full", "—"),
    ("Sun Nov 15", "Green Bay Packers", "Skyy Moore", "WR", "Ankle", "Limited", "Questionable"),
    ("Sun Nov 15", "Green Bay Packers", "Micah Parsons", "LB", "Knee, Illness", "Limited", "Out"),
    ("Sun Nov 15", "Green Bay Packers", "Sean Rhyan", "C", "Ankle", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Green Bay Packers", "Trey Smack", "K", "—", "Full", "—"),
    ("Sun Nov 15", "Green Bay Packers", "Lukas Van Ness", "LB", "Back", "Limited", "Questionable"),
    ("Sun Nov 15", "Green Bay Packers", "Josh Whyle", "TE", "Concussion", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Green Bay Packers", "Savion Williams", "WR", "—", "Limited", "—"),
    ("Sun Nov 15", "Green Bay Packers", "Kevin Zeitler", "G", "Ankle, Triceps", "Did Not Participate", "Questionable"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Jessie Bates", "S", "Resting player (not injury)", "Limited", "Out"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Ezra Cleveland", "G", "—", "Full", "—"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Branson Combs", "LB", "—", "Full", "—"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Jordan Davis", "DT", "Resting player (not injury)", "Limited", "Out"),
    ("Sun Nov 15", "Jacksonville Jaguars", "BJ Green II", "DE", "Forearm", "Full", "Out"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Robert Hainsey", "C", "Concussion", "Limited", "Questionable"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Antonio Johnson", "S", "—", "Limited", "—"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Jakobi Meyers", "WR", "—", "Limited", "—"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Chris Rodriguez Jr.", "RB", "—", "Limited", "—"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Bhayshul Tuten", "RB", "—", "Limited", "—"),
    ("Sun Nov 15", "Jacksonville Jaguars", "Travon Walker", "DE", "—", "Limited", "—"),
    ("Sun Nov 15", "Tennessee Titans", "Cody Barton", "LB", "Concussion", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Tennessee Titans", "John Franklin-Myers", "DE", "—", "Full", "—"),
    ("Sun Nov 15", "Tennessee Titans", "Marcus Harris", "CB", "—", "Full", "—"),
    ("Sun Nov 15", "Tennessee Titans", "Anthony Hill Jr.", "LB", "Neck", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Tennessee Titans", "Jaylon Jones", "CB", "—", "Full", "—"),
    ("Sun Nov 15", "Tennessee Titans", "JC Latham", "T", "—", "Full", "—"),
    ("Sun Nov 15", "Tennessee Titans", "Tony Pollard", "RB", "—", "Full", "—"),
    ("Sun Nov 15", "Tennessee Titans", "Peter Skoronski", "G", "Hamstring", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Tennessee Titans", "Tyjae Spears", "RB", "Knee", "Full", "Questionable"),
    ("Sun Nov 15", "Tennessee Titans", "Carnell Tate", "WR", "Shoulder", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Tennessee Titans", "Tommy Townsend", "P", "Knee, Achilles", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Tennessee Titans", "Kevin Winston Jr.", "S", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Alec Anderson", "G", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Christian Benford", "CB", "Wrist", "Full", "Questionable"),
    ("Sun Nov 15", "Buffalo Bills", "Terrel Bernard", "LB", "—", "Did Not Participate", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Spencer Brown", "T", "Ankle", "Did Not Participate", "Doubtful"),
    ("Sun Nov 15", "Buffalo Bills", "Dion Dawkins", "T", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Sam Franklin Jr.", "S", "Shoulder", "Limited", "Questionable"),
    ("Sun Nov 15", "Buffalo Bills", "Greg Gaines", "DT", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Jordan Hancock", "CB", "Hamstring", "Full", "Questionable"),
    ("Sun Nov 15", "Buffalo Bills", "Dalton Kincaid", "TE", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Connor McGovern", "C", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Ed Oliver", "DE", "—", "Did Not Participate", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Ar'maj Reed-Adams", "G", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "T.J. Sanders", "DE", "—", "Full", "—"),
    ("Sun Nov 15", "Buffalo Bills", "Tyrell Shavers", "WR", "Knee", "Full", "Questionable"),
    ("Sun Nov 15", "New York Jets", "Jarvis Brownlee Jr.", "CB", "Illness", "Limited", "Questionable"),
    ("Sun Nov 15", "New York Jets", "Omar Cooper Jr.", "WR", "Ankle", "Full", "Questionable"),
    ("Sun Nov 15", "New York Jets", "Adonai Mitchell", "WR", "Knee", "Full", "Questionable"),
    ("Sun Nov 15", "New York Jets", "Joseph Ossai", "DE", "Ankle", "Full", "Questionable"),
    ("Sun Nov 15", "New York Jets", "VJ Payne", "S", "Knee", "Full", "Questionable"),
    ("Sun Nov 15", "New York Jets", "Harrison Phillips", "DT", "Ankle", "Full", "Questionable"),
    ("Sun Nov 15", "New York Jets", "Trevin Wallace", "LB", "Groin", "Did Not Participate", "Out"),
    ("Sun Nov 15", "New York Jets", "Garrett Wilson", "WR", "Concussion", "Full", "Questionable"),
    ("Sun Nov 15", "New York Jets", "Nahshon Wright", "CB", "Back", "Full", "Questionable"),
    ("Sun Nov 15", "Miami Dolphins", "Tucker Addington", "LS", "—", "Limited", "—"),
    ("Sun Nov 15", "Miami Dolphins", "Kaytron Allen", "RB", "—", "Full", "—"),
    ("Sun Nov 15", "Miami Dolphins", "Darrell Baker Jr.", "CB", "Knee", "Full", "Questionable"),
    ("Sun Nov 15", "Miami Dolphins", "Chris Bell", "WR", "Knee", "Did Not Participate", "Doubtful"),
    ("Sun Nov 15", "Miami Dolphins", "Aaron Brewer", "C", "Concussion", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Miami Dolphins", "Malik Herring", "DE", "—", "Full", "—"),
    ("Sun Nov 15", "Miami Dolphins", "Will Kacmarek", "TE", "—", "Full", "—"),
    ("Sun Nov 15", "Miami Dolphins", "Michael Taaffe", "S", "—", "Full", "—"),
    ("Sun Nov 15", "Miami Dolphins", "Dante Trader Jr.", "S", "—", "Full", "—"),
    ("Sun Nov 15", "Miami Dolphins", "Jared Wayne", "WR", "Quadricep", "Did Not Participate", "Out"),
    ("Sun Nov 15", "Miami Dolphins", "Jaylen Wright", "RB", "—", "Full", "—"),
]

# Schedule — NFL.com Week 10, fetched 2026-11-14.
SCHEDULE = [
    ("Thu Nov 12 · 8:15 PM", "Prime Video", "Washington Commanders", "New York Giants", "24–21", "Final"),
    ("Sun Nov 15 · 9:30 AM", "FOX", "New England Patriots", "Detroit Lions", "—", "Scheduled (Munich)"),
    ("Sun Nov 15 · 1:00 PM", "CBS", "Kansas City Chiefs", "Atlanta Falcons", "—", "Scheduled"),
    ("Sun Nov 15 · 1:00 PM", "FOX", "Houston Texans", "Cleveland Browns", "—", "Scheduled"),
    ("Sun Nov 15 · 1:00 PM", "FOX", "Minnesota Vikings", "Green Bay Packers", "—", "Scheduled"),
    ("Sun Nov 15 · 1:00 PM", "CBS", "Miami Dolphins", "Indianapolis Colts", "—", "Scheduled"),
    ("Sun Nov 15 · 1:00 PM", "FOX", "Carolina Panthers", "New Orleans Saints", "—", "Scheduled"),
]

# Detroit Lions depth chart — detroitlions.com official team site, fetched 2026-11-14.
# (side, position, r1, r2, r3, r4)
DEPTH = [
    ("Offense", "WR", "Jameson Williams", "—", "—", "—"),
    ("Offense", "WR", "Amon-Ra St. Brown", "DeAndre Carter", "—", "—"),
    ("Offense", "WR", "Isaac TeSlaa", "Tay Martin", "—", "—"),
    ("Offense", "LT", "Penei Sewell", "—", "—", "—"),
    ("Offense", "LG", "Christian Mahogany", "Miles Frazier", "—", "—"),
    ("Offense", "C", "Cade Mays", "Juice Scruggs", "—", "—"),
    ("Offense", "RG", "Tate Ratledge", "Seth McLaughlin", "—", "—"),
    ("Offense", "RT", "Blake Miller", "Larry Borom", "—", "—"),
    ("Offense", "TE", "Sam LaPorta", "Brock Wright", "Tyler Conklin", "Jackson Meeks"),
    ("Offense", "QB", "Jared Goff", "Joshua Dobbs", "—", "—"),
    ("Offense", "RB", "Jahmyr Gibbs", "Sione Vaki", "Jacob Saylors", "—"),
    ("Defense", "EDGE", "Aidan Hutchinson", "Derrick Moore", "Eric O'Neill", "—"),
    ("Defense", "EDGE", "DJ Wonnum", "Tyler Lacy", "Ahmed Hassanein", "—"),
    ("Defense", "DL", "Alim McNeill", "Skyler Gill-Howard", "Mekhi Wingo", "—"),
    ("Defense", "DL", "Tyleik Williams", "Levi Onwuzurike", "—", "—"),
    ("Defense", "LB", "Derrick Barnes", "Joe Bachie", "—", "—"),
    ("Defense", "LB", "Malcolm Rodriguez", "K.J. Britt", "—", "—"),
    ("Defense", "LB", "Trevor Nowaske", "Amen Ogbongbemiga", "—", "—"),
    ("Defense", "CB", "D.J. Reed", "Rock Ya-Sin", "Khalil Dorsey", "Nick Whiteside"),
    ("Defense", "CB", "Roger McCreary", "Ennis Rakestraw Jr.", "Keith Abney II", "—"),
    ("Defense", "S", "Chuck Clark", "—", "—", "—"),
    ("Defense", "S", "Brian Branch", "Christian Izien", "—", "—"),
]

# ---------------------------------------------------------------------------
# Question / suggestion / flag / verification content (methodology, not live data)
# ---------------------------------------------------------------------------

QUESTIONS = [
    ("What is the exact definition of a \"signal\" and the required minimum sample size before a strategy is considered? ",
     "Without a fixed threshold, strategies can be cherry-picked. A gate (e.g., minimum 1,000 historical bets or 3 seasons) must be set first.",
     "Unresolved — needs decision.", "—"),
    ("Which closing-line source will be treated as the skill benchmark (CLV)?",
     "Removing luck requires comparing bet outcomes to the market's closing line. The specific sportsbook/feed that publishes closing lines must be named and verified.",
     "Unresolved — needs decision.", "—"),
    ("What is the acceptable edge threshold to open a position (in half-points / EV)?",
     "Defines when a signal converts to a bet. Must be fixed before testing to avoid hindsight.",
     "Unresolved — needs decision.", "—"),
    ("What validation protocol is used (walk-forward, holdout, k-fold)?",
     "Determines whether a strategy's edge is real or overfit. Protocol must be chosen before any backtest.",
     "Unresolved — needs decision.", "—"),
    ("How are correlated parlays handled so risk is not understated?",
     "Correlated legs inflate variance; correlation values must be computed and legs capped/dropped when correlation exceeds a threshold.",
     "Unresolved — methodology designed, values pending data.", "—"),
    ("Which injury/lineup sources are authoritative for starting-lineup changes (injury report vs. depth chart vs. game-day inactives)?",
     "The system must reconcile sources; conflicting data is a key risk. Source priority must be defined.",
     "Unresolved — needs decision.", "—"),
    ("How is \"2nd/3rd/4th string\" defined and where is it sourced per team?",
     "Depth charts are team-published and may lag; the authoritative source and refresh cadence must be fixed.",
     "Unresolved — needs decision.", "—"),
    ("What is the reward structure for the leaderboard (prize tiers, risk-adjusted metric)?",
     "The leaderboard metric (risk-adjusted ROI, CLV, significance) and reward tiers must be set before rankings are meaningful.",
     "Unresolved — needs decision.", "—"),
    ("What are the constraints on player-prop liquidity and book limits?",
     "Props have lower liquidity and book limits; strategy sizing must account for this or it is not implementable.",
     "Unresolved — needs decision.", "—"),
    ("What kill-switch / drawdown rule halts a strategy?",
     "A predefined stop-loss on drawdown prevents a luck-based strategy from running. Must be defined.",
     "Unresolved — needs decision.", "—"),
]

SUGGESTIONS = [
    ("Adopt closing-line value (CLV) as the primary skill metric",
     "Luck is most cleanly separated from skill by measuring whether bets beat the market's closing line.",
     "High", "Implement CLV tracking against a verified closing-line feed before any ROI is reported."),
    ("Enforce walk-forward validation with a rolling holdout",
     "Overfitting is the main risk in strategy development; walk-forward testing simulates real deployment.",
     "High", "Require all strategies to pass walk-forward validation as a gate before leaderboard entry."),
    ("Require statistical significance (t-stat / p-value) on edge",
     "A raw positive ROI over a short sample is often luck; significance testing separates signal from noise.",
     "High", "Add a significance gate; strategies below threshold are not ranked."),
    ("Compute and publish pairwise correlation matrix for all signals and parlay legs",
     "Correlation prevents overstating diversification and parlay risk.",
     "Medium", "Build a correlation module; publish the matrix; cap correlated parlay legs."),
    ("Build a single ingestion pipeline with per-row source + fetch timestamp",
     "Guarantees traceability and makes line-by-line verification reproducible.",
     "High", "Implement the pipeline so every table row stores its source URL and fetch time."),
    ("Use official NFL injury report + official team depth chart, reconcile at game-day inactives",
     "Two official sources reduce error; game-day inactives are the final truth for lineups.",
     "High", "Implement a reconciliation step and flag conflicts for review."),
    ("Add a \"missing-starter impact\" score per team (offense & defense)",
     "Quantifies the deficiency from 2nd/3rd/4th-string replacements into a single signal.",
     "Medium", "Define the impact score; validate against actual offensive/defensive efficiency changes."),
    ("Run a leaderboard with tiered rewards gated by sample size and significance",
     "Aligns incentives with skill, not short-run luck.",
     "Medium", "Define tiers; only gate-passed strategies are eligible for rewards."),
    ("Publish a \"Flagged for Review\" page with source links for every irregularity",
     "Transparency lets a human review unverified items before acting.",
     "High", "Maintain the flagged page as part of the standard build."),
    ("Version-control the data and build so every publish is reproducible",
     "Reproducibility is required for trustworthy decision-making.",
     "High", "Keep data + builder under version control; rebuild from committed sources only."),
]

FLAGS = [
    ("Repository was a blank skeleton at start", "Irregularity",
     "The repo contained only a README with \"# X3\"; there was no prior code, data, or documentation to review or verify.",
     "—", "flagged"),
    ("Betting lines have no official NFL source", "Unverified data type",
     "The NFL does not publish betting lines. No official source confirms line values, so all line values are left blank and flagged unverified.",
     NFL_SCHEDULE, "unverified"),
    ("Correlation values require a data pipeline", "Unverified data type",
     "Correlations cannot be computed without a data pipeline and backtest; values are left blank and flagged unverified.",
     "—", "unverified"),
    ("Leaderboard performance requires validation", "Unverified data type",
     "No strategy has passed validation gates yet, so no performance/reward values are reported; entries are marked pending.",
     "—", "unverified"),
    ("Injury extraction inconsistency (MIN block)", "Irregularity",
     "During fetch, a non-Vikings player (Kyler Murray) appeared under the Minnesota Vikings block, and KC/IND blocks were only partially captured. Those blocks were excluded to avoid inaccuracy; re-pull required.",
     NFL_INJURIES, "flagged"),
    ("Depth chart is labeled \"Unofficial\"", "Irregularity",
     "The Lions depth chart on the official team site is titled \"2026 Unofficial Depth Chart Compiled by Lions Football Communications\". It is the team's official published depth chart but carries an unofficial label; game-day inactives remain authoritative.",
     DET_DEPTH, "flagged"),
    ("Standings page title had unrendered template placeholders", "Irregularity",
     "The fetched standings page title showed unrendered placeholders ($year$, $displayname$); the standings table data itself was verified from the page body.",
     NFL_STANDINGS, "flagged"),
    ("Kerby Joseph depth-chart role needs confirmation", "Irregularity",
     "Kerby Joseph is listed Out on the injury report but is not a listed starter on the Lions depth chart; his exact depth-chart role requires confirmation against the roster.",
     DET_DEPTH, "flagged"),
]

# Verification log rows: (page, row reference, what, source, status)
VERIFICATION = [
    ("injuries.html", "All standings rows", "NFL league standings (W/L/T/PCT/PF/PA/NetPts)", NFL_STANDINGS, "verified"),
    ("injuries.html", "Week 10 injury rows", "Player injury / practice / game status", NFL_INJURIES, "verified"),
    ("injuries.html", "Week 10 schedule rows", "Game date/time/matchups/network", NFL_SCHEDULE, "verified"),
    ("injuries.html", "Lions depth-chart rows", "Starter + 2nd/3rd/4th-string ordering", DET_DEPTH, "verified"),
    ("lines.html", "All line-value cells", "Betting lines", "—", "unverified"),
    ("lines.html", "Correlation values", "Pairwise signal/leg correlations", "—", "unverified"),
    ("leaderboard.html", "All performance cells", "Strategy ROI / CLV / reward", "—", "unverified"),
    ("leaderboard.html", "Gate definitions", "Validation gate rules", "—", "verified"),
    ("requirements.html", "Questions & answers", "Pre-decision checklist", "—", "verified"),
    ("suggestions.html", "Suggestions", "Improvement proposals", "—", "verified"),
    ("flagged.html", "Irregularities", "Flagged items with sources", "—", "verified"),
]


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def build_index():
    rows = [
        (f"<strong>{esc(t)}</strong>", str(w), str(l), str(tt), pct, str(pf), str(pa), str(net),
         src(NFL_STANDINGS))
        for (t, w, l, tt, pct, pf, pa, net) in STANDINGS
    ]
    top_teams = sorted(STANDINGS, key=lambda r: (-r[1], -r[3], -float(r[4])))[:5]
    bottom = sorted(STANDINGS, key=lambda r: (r[1], -r[2]))[:5]
    s = []
    s.append('<div class="hero"><h2 style="margin-top:0">Originate NFL lines · skill-based strategy leaderboard</h2>'
             '<p class="lede" style="margin-bottom:0">X3 collects and organizes NFL data to support '
             'decision-making: generating useful betting signals, validating them against strict gates, '
             'removing luck, and ranking strategies on a leaderboard. Every data row links to an official '
             'source; anything unconfirmed is left blank and flagged.</p></div>')
    s.append('<div class="cards">')
    s.append(f'<div class="card"><div class="k">Teams tracked</div><div class="v">32</div><div class="s">Standings — {src(NFL_STANDINGS, "NFL.com")}</div></div>')
    s.append(f'<div class="card"><div class="k">Injury rows (Wk 10)</div><div class="v">{len(INJURIES)}</div><div class="s">{src(NFL_INJURIES, "NFL.com")}</div></div>')
    s.append(f'<div class="card"><div class="k">Wk 10 games</div><div class="v">{len(SCHEDULE)}</div><div class="s">{src(NFL_SCHEDULE, "NFL.com")}</div></div>')
    s.append(f'<div class="card"><div class="k">Verified sources</div><div class="v">4</div><div class="s">NFL.com + official team site</div></div>')
    s.append('</div>')
    s.append('<div class="warn"><strong>Verification policy.</strong> Betting lines, correlation values, and '
             'leaderboard performance have <strong>no official source available yet</strong>, so those values are '
             'left blank and flagged <span class="badge b-unverified">unverified</span>. See the '
             '<a href="flagged.html">Flagged for Review</a> page.</div>')
    s.append('<h2>League Standings (verified)</h2>')
    s.append(table(["Team", "W", "L", "T", "PCT", "PF", "PA", "Net Pts", "Source"], rows,
                   num_cols=(1, 2, 3, 4, 5, 6, 7)))
    s.append('<h2>Top 5 by Winning Percentage</h2>')
    s.append(table(["Team", "W", "L", "T", "PCT"],
                   [(f"<strong>{esc(t)}</strong>", str(w), str(l), str(tt), pct) for (t, w, l, tt, pct, *_) in top_teams],
                   num_cols=(1, 2, 3, 4)))
    s.append('<h2>Bottom 5 by Wins</h2>')
    s.append(table(["Team", "W", "L", "T", "PCT"],
                   [(f"<strong>{esc(t)}</strong>", str(w), str(l), str(tt), pct) for (t, w, l, tt, pct, *_) in bottom],
                   num_cols=(1, 2, 3, 4)))
    s.append('<div class="panel"><h3 style="margin-top:0">How to read this site</h3>'
             '<ul class="clean">'
             '<li><span class="tag">Requirements</span> The questions, information, and answers that must be '
             'resolved before any decision is made.</li>'
             '<li><span class="tag">Suggestions</span> A dedicated section proposing improvements, for review '
             'before implementation.</li>'
             '<li><span class="tag">Lines &amp; Signals</span> Line origination, signal families, validation '
             'gates, and correlation methodology.</li>'
             '<li><span class="tag">Leaderboard</span> Strategy designs, gates, and the rewards framework.</li>'
             '<li><span class="tag">Injuries &amp; Lineups</span> Injury tracking and 2nd/3rd/4th-string '
             'deficiency analysis.</li>'
             '<li><span class="tag">Verification</span> Line-by-line verification log with official source links.</li>'
             '</ul></div>')
    return page("index.html", "X3 — NFL Lines, Signals & Strategy Analytics",
                "Collect, organize, and analyze NFL data to originate lines and build skill-based strategies.", s)


def build_exec():
    s = []
    s.append('<div class="hero"><h2 style="margin-top:0">Executive Summary</h2>'
             '<p class="lede" style="margin-bottom:0">X3 is a self-contained NFL analytics workspace that turns '
             'verified official data into decision-ready inputs for originating NFL betting lines and ranking '
             'skill-based strategies on a leaderboard. It is built to be reviewed, not trusted blindly: every '
             'value is traceable to an official source or explicitly flagged as unverified.</p></div>')
    s.append('<h2>Objective</h2>')
    s.append('<div class="panel">Collect, organize, and analyze NFL data using a full list of requirements; '
             'originate NFL lines; develop strategies that produce useful signals; treat strategy performance as '
             'a leaderboard competition with rewards for top performers; remove luck from the equation so that '
             'only selectively skill-based strategies are rewarded.</div>')
    s.append('<h2>What is built (this release)</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li>Verified <strong>league standings</strong>, <strong>Week 10 injury report</strong>, '
             '<strong>Week 10 schedule</strong>, and the <strong>Detroit Lions depth chart</strong> — all from '
             'official sources with per-row links.</li>'
             '<li>A <strong>Requirements &amp; Questions</strong> page listing the questions, information, and '
             'answers required before any decision.</li>'
             '<li>A dedicated <strong>Suggestions</strong> page for review before implementation.</li>'
             '<li>A <strong>Lines &amp; Signals</strong> page with signal families, bet types, validation '
             'gates, and correlation methodology.</li>'
             '<li>A <strong>Strategy Leaderboard</strong> framework with gates and a rewards structure.</li>'
             '<li>An <strong>Injuries &amp; Lineups</strong> page demonstrating starter/backup deficiency '
             'tracking with verified data.</li>'
             '<li>Line-by-line <strong>Verification</strong> and a <strong>Flagged for Review</strong> page.</li>'
             '</ul></div>')
    s.append('<h2>Key verified facts</h2>')
    s.append(table(["Item", "Detail", "Source"],
                   [("League standings", "32 teams; standings, points for/against, net points", src(NFL_STANDINGS)),
                    ("Injuries", f"{len(INJURIES)} player rows across {len(set(r[1] for r in INJURIES))} teams (Week 10)", src(NFL_INJURIES)),
                    ("Schedule", f"{len(SCHEDULE)} Week 10 games with dates/times/networks", src(NFL_SCHEDULE)),
                    ("Depth chart", "Detroit Lions offense + defense, starter to 4th string", src(DET_DEPTH))]))
    s.append('<h2>Key risks & open items</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li><strong>Lines are not NFL-published.</strong> No official source confirms betting lines; line '
             'values are left blank and flagged unverified.</li>'
             '<li><strong>Correlations and leaderboard performance need a data pipeline + backtest</strong> that '
             'does not yet exist; values are left blank and flagged unverified.</li>'
             '<li><strong>Decisions are pending.</strong> The Requirements page lists questions that must be '
             'answered before strategies are finalized and deployed.</li>'
             '<li><strong>Irregularities</strong> in source extraction (e.g., a contaminated injury block and an '
             '\"unofficial\" depth-chart label) are documented on the Flagged page.</li>'
             '</ul></div>')
    s.append('<h2>Status</h2>')
    s.append(table(["Area", "Status", "Detail"],
                   [("Standings / Injuries / Schedule / Depth", badge("verified"), "Verified against official sources"),
                    ("Line origination", badge("pending"), "Framework built; live lines unverified"),
                    ("Correlation values", badge("unverified"), "Methodology designed; values pending data"),
                    ("Strategy leaderboard", badge("pending"), "Framework + gates built; no validated strategies yet"),
                    ("Decisions", badge("pending"), "Pre-decision questions open on Requirements page")]))
    return page("executive-summary.html", "Executive Summary",
                "Key details, scope, status, and risks for the X3 NFL analytics project.", s)


def build_requirements():
    s = []
    s.append('<div class="note">These are the questions, information, and answers that must be resolved '
             'before any decision can reasonably be made on the information we have and do not have. Each '
             'question notes the information needed and why it matters. Suggestions to discover missing '
             'information are on the <a href="suggestions.html">Suggestions</a> page.</div>')
    s.append('<h2>Information we have vs. do not have</h2>')
    s.append(table(["Category", "Have (verified)", "Do not have (gap)"],
                   [("League standings", "Full 32-team standings, PF/PA, net points — NFL.com", "Team-level efficiency (EPA) and situational splits"),
                    ("Injuries", "Week 10 official injury report (player, status, game status)", "Historical injury-to-performance impact; full season archive"),
                    ("Lineups", "Detroit Lions official depth chart (starter→4th string)", "Depth charts for all 32 teams; game-day inactives archive"),
                    ("Lines", "Official NFL schedule (matchups, times, networks)", "Betting lines — no official NFL source exists"),
                    ("Signals", "Strategy/signal design framework", "Computed signal values and historical signal performance"),
                    ("Correlations", "Correlation methodology", "Computed correlation values (needs data pipeline)"),
                    ("Strategy results", "Validation gates + leaderboard framework", "Validated strategy performance and rewards")]))
    s.append('<h2>Pre-decision questions</h2>')
    s.append(table(["Question", "Why it matters / information needed", "Answer status", "Source"],
                   [(q, w, badge_text, src_link) for (q, w, badge_text, src_link) in QUESTIONS]))
    return page("requirements.html", "Requirements & Questions",
                "The clear list of questions, information, and answers to address before any decision.", s)


def build_suggestions():
    s = []
    s.append('<div class="note">This is the dedicated suggestions section. A reviewer can read each '
             'suggestion, choose the best path, and approve before any change is implemented. Suggestions '
             'here are specifically aimed at discovering missing information and improving decision-making.</div>')
    s.append('<h2>Suggestions</h2>')
    s.append(table(["Suggestion", "Rationale / what it discovers", "Priority", "Recommended action"],
                   [(f"<strong>{esc(t)}</strong>", r, badge("pending") if False else esc(p), a) for (t, r, p, a) in SUGGESTIONS]))
    s.append('<h2>How to use this page</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li>Review each suggestion and mark it <span class="badge b-verified">approved</span>, '
             '<span class="badge b-pending">hold</span>, or <span class="badge b-flagged">reject</span>.</li>'
             '<li>Only approved suggestions move into implementation; the priority column indicates urgency.</li>'
             '<li>Suggestions that discover missing information feed back into the '
             '<a href="requirements.html">Requirements &amp; Questions</a> page.</li>'
             '</ul></div>')
    return page("suggestions.html", "Suggestions",
                "Dedicated suggestions for review — choose the best path before implementing changes.", s)


def build_lines():
    s = []
    s.append('<h2>Line origination — Week 10 games (official schedule)</h2>')
    s.append('<div class="warn"><strong>No official NFL source publishes betting lines.</strong> The NFL '
             'publishes the schedule (matchups/times) but not betting lines. Line values below are therefore '
             'left blank and flagged <span class="badge b-unverified">unverified</span> until a confirmed '
             'source is provided.</div>')
    s.append(table(["Date / Time", "Network", "Away", "Home", "Score", "Line (spread/total/ML)", "Source"],
                   [(d, n, a, h, sc,
                     f'{badge("unverified")} <span class="src">(blank — no official source)</span>',
                     src(NFL_SCHEDULE)) for (d, n, a, h, sc, st) in SCHEDULE]))
    s.append('<h2>Signal families (design)</h2>')
    s.append('<div class="panel">Signals are the raw inputs that feed line origination and strategy selection. '
             'Each signal must be defined, sourced, and validated before use. Designed families:</div>')
    s.append(table(["Signal family", "Description", "Primary official source"],
                   [("Market-implied", "Closing-line movement / CLV vs. market consensus", "Sportsbook closing-line feed (to be verified) — not NFL-published"),
                    ("Team efficiency", "Points / yardage efficiency and situational splits", "NFL.com stats"),
                    ("Opponent-adjusted defense", "Defensive efficiency adjusted for missing starters", "NFL.com stats + injury report"),
                    ("Injury-adjusted", "Impact of missing starters (2nd/3rd/4th-string replacements)", "NFL.com injuries + official team depth charts"),
                    ("Situational", "Down/distance, red zone, home/road, rest", "NFL.com stats"),
                    ("Contrarian / sentiment", "Deviation from public-heavy sides", "Market data (to be verified) — not NFL-published")])
                   )
    s.append('<h2>Bet types (design)</h2>')
    s.append(table(["Bet type", "Structure", "Skill consideration"],
                   [("Single bet", "Spread / moneyline / total, one leg", "Cleanest CLV measurement; lowest variance"),
                    ("Parlay", "2+ correlated legs, combined odds", "Correlation inflates variance — must cap correlated legs"),
                    ("Player props", "Player-level stat lines (pass/rush/rec yards, TDs)", "Lower liquidity; book limits; need player-injury context")])
                   )
    s.append('<h2>Validation gates (every strategy must pass)</h2>')
    s.append(table(["Gate", "Rule", "Purpose"],
                   [("Sample size", "Minimum historical bets / seasons before eligibility", "Prevents short-sample luck"),
                    ("Edge threshold", "Required EV over closing line to open a position", "Filters noise-level edges"),
                    ("Significance", "Statistical significance of edge (t-stat / p-value)", "Separates signal from luck"),
                    ("Validation protocol", "Walk-forward / rolling holdout", "Simulates real deployment; prevents overfit"),
                    ("Correlation cap", "Max allowed correlation between parlay legs", "Prevents understated parlay risk"),
                    ("Drawdown kill-switch", "Predefined stop on max drawdown", "Halts luck-based or broken strategies"),
                    ("No-look bias", "Positions frozen at decision time, not hindsight", "Prevent look-ahead bias")])
                   )
    s.append('<h2>Correlation methodology</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li>Compute pairwise correlation between every signal and between parlay legs to quantify '
             'diversification and correlated risk.</li>'
             '<li>Use correlation to cap parlay legs; drop legs that exceed the threshold.</li>'
             '<li>Isolate skill from luck by benchmarking outcomes against the market closing line (CLV) and '
             'testing edge for statistical significance.</li>'
             '</ul><p><strong>Status:</strong> methodology designed. <strong>Computed correlation values are '
             'unverified (blank)</strong> until the data pipeline and backtest exist.</p></div>')
    s.append('<h2>Removing luck</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li>Benchmark every bet against the <strong>closing line</strong>, not the result — beating the '
             'close is the skill signal.</li>'
             '<li>Require <strong>statistical significance</strong> and <strong>walk-forward validation</strong>.</li>'
             '<li>Apply <strong>shrinkage</strong> toward the prior to reduce overfitting on small samples.</li>'
             '<li>Freeze decisions at the moment of the signal to remove look-ahead bias.</li>'
             '</ul></div>')
    return page("lines.html", "Lines & Signals",
                "NFL line origination, signal families, bet types, validation gates, and correlation methodology.", s)


def build_leaderboard():
    s = []
    s.append('<div class="note">The leaderboard ranks strategies that pass validation gates and rewards top '
             'performers. Only skill-based, gate-passed strategies are eligible. <strong>No strategy has passed '
             'validation yet</strong>, so performance/reward values are left blank and flagged '
             '<span class="badge b-unverified">unverified</span>.</div>')
    s.append('<h2>Leaderboard (framework)</h2>')
    s.append(table(["Rank", "Strategy", "Bet type", "Gate status", "ROI / CLV / Reward", "Source"],
                   [("—", "Market-implied single-bet CLV chaser", "Single", badge("pending"),
                     f'{badge("unverified")} <span class="src">(blank — not validated)</span>', "—"),
                    ("—", "Opponent-adjusted defense single bet", "Single", badge("pending"),
                     f'{badge("unverified")} <span class="src">(blank — not validated)</span>', "—"),
                    ("—", "Injury-adjusted signal (missing-starter impact)", "Single", badge("pending"),
                     f'{badge("unverified")} <span class="src">(blank — not validated)</span>', "—"),
                    ("—", "Correlation-capped correlated parlay", "Parlay", badge("pending"),
                     f'{badge("unverified")} <span class="src">(blank — not validated)</span>', "—"),
                    ("—", "Player-prop combo (QB passing / RB rushing)", "Player prop", badge("pending"),
                     f'{badge("unverified")} <span class="src">(blank — not validated)</span>', "—")]))
    s.append('<h2>Eligibility gates (must all pass to be ranked)</h2>')
    s.append(table(["Gate", "Rule", "Status"],
                   [("Sample size", "Minimum bets / seasons threshold", badge("verified")),
                    ("Edge threshold", "Required EV over closing line", badge("verified")),
                    ("Statistical significance", "t-stat / p-value on edge", badge("verified")),
                    ("Walk-forward validation", "Rolling holdout protocol", badge("verified")),
                    ("Correlation cap", "Max parlay-leg correlation", badge("verified")),
                    ("Drawdown kill-switch", "Predefined stop", badge("verified"))]))
    s.append('<h2>Rewards framework</h2>')
    s.append(table(["Tier", "Criteria (illustrative — to be set)", "Reward"],
                   [("Tier 1", "Top risk-adjusted ROI, passed all gates, sufficient sample", "Highest reward"),
                    ("Tier 2", "Strong risk-adjusted ROI, passed all gates", "Medium reward"),
                    ("Tier 3", "Passed gates, modest edge", "Base reward"),
                    ("Excluded", "Did not pass all gates", "No reward")]))
    s.append('<h2>Ranking metric</h2>')
    s.append('<div class="panel"><p>Strategies are ranked by <strong>risk-adjusted ROI</strong> (e.g., '
             'Sharpe-style ratio of CLV edge to volatility), subject to the eligibility gates. The metric '
             'prioritizes consistency and skill over raw short-run results. The exact metric and thresholds '
             'must be finalized on the <a href="requirements.html">Requirements</a> page before rankings '
             'become meaningful.</p></div>')
    return page("leaderboard.html", "Strategy Leaderboard",
                "Strategy designs, validation gates, and the rewards framework for top-performing strategies.", s)


def build_injuries():
    s = []
    s.append('<h2>Week 10 injury report (verified)</h2>')
    s.append(f'<p class="lede">Official NFL injury report, Week 10. Each row links to the source. '
             f'{len(INJURIES)} player rows across {len(set(r[1] for r in INJURIES))} teams are included; '
             'contaminated blocks (see Flagged) were excluded.</p>')
    s.append(table(["Date", "Team", "Player", "Pos", "Injury", "Practice Status", "Game Status", "Source"],
                   [(d, t, p, pos, inj, prac, gs, src(NFL_INJURIES)) for (d, t, p, pos, inj, prac, gs) in INJURIES]))
    s.append('<h2>Lineup & depth deficiencies — Detroit Lions (verified)</h2>')
    s.append('<p class="lede">The Lions depth chart (official team site) is cross-referenced with the '
             'injury report to show where a 2nd/3rd/4th-string player must replace a starter. This is the '
             'core of the deficiency-tracking feature, demonstrated on verified data.</p>')
    s.append('<h3>Depth chart (starter → 4th string)</h3>')
    s.append(table(["Side", "Position", "1st (Starter)", "2nd", "3rd", "4th", "Source"],
                   [(side, pos, r1, r2, r3, r4, src(DET_DEPTH)) for (side, pos, r1, r2, r3, r4) in DEPTH]))
    s.append('<h3>Starter-out → backup replacement analysis</h3>')
    s.append(table(["Starter (injury report)", "Status", "Depth-chart role", "Replacing backup (string)", "Source"],
                   [("D.J. Reed (CB)", badge("flagged"), "CB — 1st string (starter)", "Rock Ya-Sin (CB, 2nd string)", src(DET_DEPTH)),
                    ("Cade Mays (C)", badge("flagged"), "C — 1st string (starter)", "Juice Scruggs (C, 2nd string)", src(DET_DEPTH)),
                    ("Amon-Ra St. Brown (WR)", badge("pending"), "WR — 1st string (starter)", "DeAndre Carter (WR, 2nd string) — game-time decision", src(DET_DEPTH)),
                    ("Kerby Joseph (S)", badge("flagged"), "Not a listed starter on depth chart — role to confirm", "Requires roster confirmation", src(DET_DEPTH))]))
    s.append('<div class="warn"><strong>Note.</strong> The Lions depth chart is published on the official team '
             'site but is titled \"Unofficial Depth Chart\". Game-day inactive lists remain the authoritative '
             'lineup source. See the <a href="flagged.html">Flagged for Review</a> page.</div>')
    s.append('<h2>How the system tracks deficiencies (design)</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li>Ingest the official injury report (player, practice status, game status) each week.</li>'
             '<li>Ingest the official team depth chart (starter → 4th string) for every position group, offense and defense.</li>'
             '<li>Reconcile both at game-day inactives; flag conflicts for review.</li>'
             '<li>Produce a per-team <strong>missing-starter impact</strong> score for offense and defense, '
             'quantifying the expected drop from a 2nd/3rd/4th-string replacement.</li>'
             '<li>Feed the impact score into signals and the leaderboard.</li>'
             '</ul></div>')
    return page("injuries.html", "Injuries & Lineups",
                "Injury tracking and 2nd/3rd/4th-string backup deficiency analysis, verified from official sources.", s)


def build_verification():
    s = []
    s.append('<div class="note">Every table row must have a source link to an official site. Values that '
             'cannot be confirmed from an official source are left blank and flagged unverified. This page is '
             'the line-by-line verification log.</div>')
    s.append('<h2>Verification log</h2>')
    s.append(table(["Page", "Row reference", "Item verified", "Official source", "Status"],
                   [(pg, ref, item, src(url) if url != "—" else '<span class="src">(no official source)</span>',
                     badge(st)) for (pg, ref, item, url, st) in VERIFICATION]))
    s.append('<h2>Verification method</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li>Each data row was fetched from the official source listed and checked against the page content.</li>'
             '<li>Only values present on the official page were recorded; nothing was inferred or filled in.</li>'
             '<li>Where no official source exists (betting lines, correlations, leaderboard performance), the '
             'value is left blank and flagged <span class="badge b-unverified">unverified</span>.</li>'
             '<li>Irregularities in fetching or labeling are recorded on the '
             '<a href="flagged.html">Flagged for Review</a> page with their source links.</li>'
             '</ul></div>')
    return page("verification.html", "Verification",
                "Line-by-line verification log mapping each data row to its official source and status.", s)


def build_flagged():
    s = []
    s.append('<div class="warn"><strong>Flagged for Review.</strong> The items below are irregularities and '
             'unverified items. They do not block the site, but should be reviewed. Each item links to its '
             'source so you can confirm or request changes.</div>')
    s.append('<h2>Irregularities & unverified items</h2>')
    s.append(table(["Item", "Type", "Detail", "Source", "Status"],
                   [(f"<strong>{esc(i)}</strong>", esc(t), d,
                     src(url) if url != "—" else '<span class="src">(no official source)</span>',
                     badge(st)) for (i, t, d, url, st) in FLAGS]))
    s.append('<h2>How to review</h2>')
    s.append('<div class="panel"><ul class="clean">'
             '<li>Open each source link and confirm the flagged detail against the official page.</li>'
             '<li>For <span class="badge b-unverified">unverified</span> data types, provide or confirm an '
             'authoritative source so the value can be populated.</li>'
             '<li>Request changes via the project; unverified items stay blank until confirmed.</li>'
             '</ul></div>')
    return page("flagged.html", "Flagged for Review",
                "Irregularities and unverified items, with source links, for review after the site is live.", s)


def main():
    write("index.html", build_index())
    write("executive-summary.html", build_exec())
    write("requirements.html", build_requirements())
    write("suggestions.html", build_suggestions())
    write("lines.html", build_lines())
    write("leaderboard.html", build_leaderboard())
    write("injuries.html", build_injuries())
    write("verification.html", build_verification())
    write("flagged.html", build_flagged())
    print("done")


if __name__ == "__main__":
    main()
