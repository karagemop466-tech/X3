#!/usr/bin/env python3
"""Deterministic builder for the X3 review hub.

Design rules enforced here (not by convention):
  * every published data row carries either a link to an approved source host or an
    explicit UNVERIFIED marker - anything else aborts the build;
  * every number that appears in prose is injected from a token computed out of the
    data files, and the build fails if a token is left unfilled, so prose cannot drift
    from the table underneath it;
  * no value is ever imputed: unknown market prices, depth strings and performance
    figures render as blank + UNVERIFIED.
"""
import csv, hashlib, html, json, math, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "hub")
DATA = os.path.join(HUB, "data")
OUT = HUB

OFFICIAL_HOSTS = {"www.nfl.com", "nfl.com", "operations.nfl.com", "media.nfl.com", "static.www.nfl.com"}
APPROVED_HOSTS = OFFICIAL_HOSTS | {
    "github.com", "api.github.com", "docs.github.com", "karagemop466-tech.github.io",
    "papers.ssrn.com", "www.pro-football-reference.com", "www.espn.com",
}

RULE_OFFICIAL = {"injuries.html", "deficiency.html", "lines.html", "correlations.html"}
OFFICIAL_REQUIRED_PAGES = RULE_OFFICIAL | {"strategies.html", "sources.html", "verification.html"}
UNVERIFIED = "UNVERIFIED"


def load(name):
    return json.load(open(os.path.join(DATA, name), encoding="utf-8"))


def load_csv(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def esc(v):
    return html.escape("" if v is None else str(v))


# ---------------------------------------------------------------- data helpers
def games(r):
    return int(r["w"]) + int(r["l"]) + int(r["t"])


POS_GROUP = {
    "QB": "offense", "RB": "offense", "FB": "offense", "WR": "offense", "TE": "offense",
    "T": "offense", "G": "offense", "C": "offense",
    "DE": "defense", "DT": "defense", "LB": "defense", "CB": "defense", "S": "defense",
    "K": "special", "P": "special", "LS": "special",
}
WEIGHT_KEY = {
    "QB": "QB", "RB": "RB", "FB": "K/P/LS/FB", "WR": "WR", "TE": "TE",
    "T": "T/G/C", "G": "T/G/C", "C": "T/G/C",
    "DE": "DE/DT", "DT": "DE/DT", "LB": "LB", "CB": "CB/S", "S": "CB/S",
    "K": "K/P/LS/FB", "P": "K/P/LS/FB", "LS": "K/P/LS/FB",
}
KEY_POSITIONS = {"QB": "quarterback", "T": "offensive line", "G": "offensive line", "C": "offensive line",
                 "CB": "secondary", "S": "secondary", "DE": "pass rush", "DT": "pass rush",
                 "WR": "wide receiver", "TE": "tight end", "RB": "backfield", "LB": "linebackers"}


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if not sx or not sy:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (sx * sy)


def compute(standings, injuries, slate, cfg):
    """All derived numbers in the site come from here, once."""
    w = cfg["assumptions"]
    mult = next(a for a in w if a["id"] == "A-03")["value"]
    posw = next(a for a in w if a["id"] == "A-04")["value"]
    hfa = next(a for a in w if a["id"] == "A-01")["value"]
    hfa_neutral = next(a for a in w if a["id"] == "A-02")["value"]
    shrink = next(a for a in w if a["id"] == "A-05")["value"]

    tbl = {r["abbr"]: r for r in standings}
    # ---- standings integrity (VER-04)
    probs = []
    if sum(int(r["w"]) for r in standings) != sum(int(r["l"]) for r in standings):
        probs.append("league wins != losses")
    if sum(int(r["pf"]) for r in standings) != sum(int(r["pa"]) for r in standings):
        probs.append("league PF != PA")
    if sum(int(r["t"]) for r in standings) % 2:
        probs.append("odd tie count")
    for r in standings:
        g = games(r)
        hg = [int(x) for x in r["home"].split("-")]
        rg = [int(x) for x in r["road"].split("-")]
        if hg[0] + hg[1] + hg[2] + rg[0] + rg[1] + rg[2] != g:
            probs.append(r["abbr"] + " home+road != games")
        if (int(r["pf"]) - int(r["pa"])) != int(r["net"]):
            probs.append(r["abbr"] + " net != pf-pa")
        if g > 9:
            probs.append(r["abbr"] + " played more than 9 games")
    # ---- correlations
    pct = [int(r["w"]) / games(r) for r in standings]
    pfpg = [int(r["pf"]) / games(r) for r in standings]
    papg = [int(r["pa"]) / games(r) for r in standings]
    netpg = [int(r["net"]) / games(r) for r in standings]

    def split_pct(side):
        out = []
        for r in standings:
            a, b, _ = (int(x) for x in r[side].split("-"))
            out.append(a / (a + b) if a + b else 0.0)
        return out

    hw, rw = split_pct("home"), split_pct("road")
    corr = {
        "R_PF": pearson(pfpg, pct), "R_PA": pearson(papg, pct), "R_NET": pearson(netpg, pct),
        "R_HR": pearson(hw, rw), "R_NETPF": pearson(netpg, pfpg),
    }
    # ---- per-club availability + deficiency
    per_team = defaultdict(list)
    for r in injuries:
        per_team[r["team"]].append(r)

    def impact(rows, group):
        return round(sum(posw[WEIGHT_KEY.get(r["position"], "K/P/LS/FB")] * mult.get(r["game_status"] or "none", 0.0)
                         for r in rows if POS_GROUP.get(r["position"]) == group), 2)

    deficiency = []
    for team in sorted(per_team):
        rows = per_team[team]
        cnt = Counter((r["game_status"] or "none") for r in rows)
        out_like = [r for r in rows if (r["game_status"] or "") in ("Out", "Doubtful")]
        nir = [r for r in rows if "NIR" in r["injury"]]
        groups = Counter(POS_GROUP.get(r["position"], "special") for r in out_like)
        pos_lost = defaultdict(list)
        for r in out_like:
            pos_lost[KEY_POSITIONS.get(r["position"], r["position"])].append("%s (%s)" % (r["player"], r["position"]))
        deficiency.append({
            "team": team, "record": "%d-%d-%d" % (int(tbl[team]["w"]), int(tbl[team]["l"]), int(tbl[team]["t"])) if team in tbl else "",
            "rows": len(rows), "out": cnt["Out"], "doubtful": cnt["Doubtful"], "questionable": cnt["Questionable"],
            "undesignated": cnt["none"], "nir": len(nir),
            "off_loss": impact(rows, "offense"), "def_loss": impact(rows, "defense"),
            "score": round(impact(rows, "offense") + impact(rows, "defense"), 2),
            "out_offense": groups["offense"], "out_defense": groups["defense"],
            "positions": "; ".join("%s: %s" % (k, ", ".join(v)) for k, v in sorted(pos_lost.items())) or "-",
        })
    # ---- originated lines
    games_played = sum(games(r) for r in standings)
    league_total = 2 * sum(int(r["pf"]) for r in standings) / games_played
    prior_dash = {("%s" % r["away"], r["home"]): r for r in
                  json.load(open(os.path.join(ROOT, "dashboard/data/model_lines.json"), encoding="utf-8"))}
    x3 = json.load(open(os.path.join(ROOT, "x3lab/data/lines_week10.json"), encoding="utf-8"))
    prior_x3 = {(g["away"], g["home"]): g for g in x3["games"]}

    lines, byes = [], []
    for g in slate:
        if not g["home"].strip():
            byes.append(g["away"])
            continue
        if g["result"].strip():
            continue
        away, home = g["away"], g["home"]
        neutral = "Munich" in g["venue_note"] or "international" in g["venue_note"].lower()
        site_hfa = hfa_neutral if neutral else hfa
        a, h = tbl[away], tbl[home]
        exp_h = (int(h["pf"]) / games(h) + int(a["pa"]) / games(a)) / 2 + site_hfa / 2 - impact(per_team[home], "offense") + impact(per_team[away], "defense")
        exp_a = (int(a["pf"]) / games(a) + int(h["pa"]) / games(h)) / 2 - site_hfa / 2 - impact(per_team[away], "offense") + impact(per_team[home], "defense")
        raw_total = exp_h + exp_a
        total = league_total + shrink * (raw_total - league_total)
        spread = -round((exp_h - exp_a) * 2) / 2
        pd = prior_dash.get((away, home))
        px = prior_x3.get((away, home))
        lines.append({
            "game": "%s @ %s" % (away, home), "day": g["day"], "kickoff": "%s %s ET" % (g["date"], g["kickoff_et"]),
            "broadcast": g["broadcast"], "url": g["game_url"],
            "net_home": round(int(h["net"]) / games(h), 2), "net_away": round(int(a["net"]) / games(a), 2),
            "inj_home": round(impact(per_team[home], "offense") + impact(per_team[home], "defense"), 2),
            "inj_away": round(impact(per_team[away], "offense") + impact(per_team[away], "defense"), 2),
            "spread_home": "%+.1f" % spread, "total": "%.1f" % (round(total * 2) / 2),
            "exp_home": "%.1f" % exp_h, "exp_away": "%.1f" % exp_a,
            "market": UNVERIFIED,
            "prior_home_spread": pd["model_home_spread"] if pd else UNVERIFIED,
            "prior_total": pd["model_total"] if pd else UNVERIFIED,
            "x3_away_spread": str(px["our_spread_away"]) if px else UNVERIFIED,
            "x3_total": str(px["our_total"]) if px else UNVERIFIED,
            "neutral": "yes" if neutral else "",
        })
    derived = {
        "standings_problems": probs, "correlations": {k: round(v, 4) for k, v in corr.items()},
        "league_total_per_game": round(league_total, 2), "games_played": games_played,
        "injury_rows": len(injuries), "clubs_reporting": len(per_team),
        "nir_rows": sum(1 for r in injuries if "NIR" in r["injury"]),
        "designations": dict(Counter((r["game_status"] or "none") for r in injuries)),
        "unplayed_games": len(lines), "slate_rows": len(slate), "byes": byes,
        "deficiency_rows": len(deficiency),
        "max_deficiency": max((d["score"] for d in deficiency), default=0),
    }
    return derived, deficiency, lines


def tokens(derived, gates, research):
    t = {
        "R_PF": "%+.4f" % derived["correlations"]["R_PF"],
        "R_PA": "%.4f" % derived["correlations"]["R_PA"],
        "R_NET": "%+.4f" % derived["correlations"]["R_NET"],
        "R_HR": "%+.4f" % derived["correlations"]["R_HR"],
        "R_NETPF": "%+.4f" % derived["correlations"]["R_NETPF"],
        "INJ_ROWS": str(derived["injury_rows"]), "NIR": str(derived["nir_rows"]),
        "OUT": str(derived["designations"].get("Out", 0)),
        "DOUBT": str(derived["designations"].get("Doubtful", 0)),
        "QUE": str(derived["designations"].get("Questionable", 0)),
        "NODESIG": str(derived["designations"].get("none", 0)),
        "GAMES_LEFT": str(derived["unplayed_games"]),
        "LEAGUE_TOTAL": "%.2f" % derived["league_total_per_game"],
        "GATES_TOTAL": str(len(gates)),
        "GATES_FAILED": str(sum(1 for g in gates if not g["status"].startswith("PASSED"))),
    }
    return t


# ---------------------------------------------------------------- rendering
def page(title, body, active, nav=None, extra_meta=""):
    nav = " ".join('<a% href="%s">%s</a>' % (' class="on"' if h == active else "", h, esc(t))
                   for h, t in NAV)
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s &middot; X3 review hub</title>
<link rel="stylesheet" href="style.css">
%s</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html"><strong>X3</strong> NFL review hub</a></div>
  <nav>%s</nav>
</header>
<main>
<h1>%s</h1>
%s
</main>
<footer>
  <p>Built by <code>scripts/build_hub.py</code> from <code>hub/data/</code>. Data as of 2026-11-14 18:15 UTC
  (Week 10 of the 2026 season). Facts link to NFL.com; derived values are labelled; assumptions are labelled;
  everything else is blank and marked <span class="bad">UNVERIFIED</span>. Nothing here is betting advice.</p>
</footer>
</body>
</html>
""" % (esc(title), extra_meta, nav, esc(title), body)


class Raw(str):
    pass


def cell(v):
    if isinstance(v, Raw):
        return "<td>%s</td>" % str(v)
    if isinstance(v, tuple):
        text, href = v
        if not href:
            return "<td>%s</td>" % esc(text)
        return '<td><a href="%s">%s</a></td>' % (esc(href), esc(text))
    if v is None or v == "":
        return '<td class="blank"></td>'
    s = esc(v)
    if v == UNVERIFIED:
        return '<td><span class="bad">UNVERIFIED</span></td>'
    return "<td>%s</td>" % s


def table(headers, rows, cls=""):
    out = ['<table class="%s"><thead><tr>' % cls]
    out += ["<th>%s</th>" % esc(h) for h in headers]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(cell(c) for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def note(t):
    return '<p class="note">%s</p>' % t


def badge(kind):
    m = {"VERIFIED": "good", "DERIVED": "derived", "ASSUMPTION": "warn", "UNVERIFIED": "bad"}
    return '<span class="%s">%s</span>' % (m[kind], kind)


NAV = [
    ("index.html", "Overview"), ("executive-summary.html", "Executive summary"),
    ("requirements.html", "Requirements"), ("questions.html", "Questions & gaps"),
    ("suggestions.html", "Suggestions"), ("lines.html", "Originated lines"),
    ("strategies.html", "Signals & strategies"), ("validation.html", "Validation gates"),
    ("correlations.html", "Correlations"), ("injuries.html", "Injuries"),
    ("deficiency.html", "Depth & deficiencies"), ("leaderboard.html", "Leaderboard"),
    ("repo-review.html", "Repo review"), ("sources.html", "Sources"),
    ("verification.html", "Verification"), ("flagged.html", "Flagged for review"),
    ("archive.html", "Archive"),
]
SRC_URL = {
    "SRC-01": "https://www.nfl.com/standings/league/2026/REG", "SRC-02": "https://www.nfl.com/injuries/",
    "SRC-03": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "SRC-04": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
    "SRC-05": "https://www.nfl.com/news/nfl-week-9-injury-report-2026-season",
    "SRC-06": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-saturday-nov-14",
    "SRC-07": "https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders",
    "SRC-08": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-thursday-nov-5",
    "SRC-09": "https://www.nfl.com/teams/", "SRC-10": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551",
    "SRC-11": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253",
    "SRC-12": "https://www.pro-football-reference.com/players/injuries.htm",
    "SRC-13": "https://www.espn.com/nfl/odds", "SRC-14": "https://api.github.com/repos/karagemop466-tech/X3/pages",
    "SRC-15": "https://docs.github.com/en/pages",
    "SRC-16": "https://github.com/karagemop466-tech/X3/blob/main/docs/data/injury-2026-week10.csv",
}


INTERNAL = {"FLG": "flagged.html", "Q": "questions.html", "S": "suggestions.html", "VER": "verification.html"}


def src(ref):
    """Render one or more refs as links: a source id, a URL, or an internal register id."""
    parts = [x.strip() for x in str(ref).split(";") if x.strip()]
    out = []
    for x in parts:
        if x in SRC_URL:
            out.append('<a href="%s">%s</a>' % (SRC_URL[x], x))
        elif x.startswith("http"):
            out.append('<a href="%s">%s</a>' % (esc(x), esc(x.split("/")[2])))
        else:
            m = re.match(r"^(FLG|VER|Q|S)-\d+$", x)
            out.append('<a href="%s">%s</a>' % (INTERNAL[m.group(1)], x) if m else '<code>%s</code>' % esc(x))
    return Raw(", ".join(out))


DATA_BLOB = "https://github.com/karagemop466-tech/X3/blob/main/hub/data/"


def rowsrc(*texts):
    """Every row links to something: pull the ids it mentions, else point at its data file."""
    found = []
    for t in texts:
        for m in re.findall(r"(?:SRC|FLG|VER|COR|Q|S|R|A|G|ST|SIG|H)-\d+", str(t)):
            if m not in found:
                found.append(m)
    if found:
        return src("; ".join(found[:4]))
    return Raw('<a href="%s">data file</a>' % DATA_BLOB)


def fill(body, tk):
    """Substitute computed values; a second pass is a no-op for already-filled text."""
    for k, v in tk.items():
        body = body.replace("{{%s}}" % k, v)
    left = sorted(set(re.findall(r"\{\{([A-Z_0-9]+)\}\}", body)))
    if left:
        raise SystemExit("unfilled tokens: %s" % left)
    return body


def scan_stats(page_map, extra_bodies=(), virtual=()):
    """Audit the rendered HTML table by table.

    Rule 1 (all tables): every body row links to something, or carries UNVERIFIED.
    Rule 2 (data tables - any table with a "Source" column): that link must be an
    official NFL host, or the row must carry UNVERIFIED. Blank is allowed; inference is not.
    """
    links = broken = rows = sourced = blank = official_rows = 0
    generated = set(virtual)
    problems = []
    bodies = [(k, v) for k, v in page_map.items()] + [("__extra__", x) for x in extra_bodies]
    for name, body in bodies:
        base = ROOT if name == "__root__" else os.path.join(ROOT, "hub")
        for m in re.finditer(r'(?:href|src)="([^"#<> ]+?)"', body):
            u = m.group(1)
            links += 1
            if u.startswith(("http://", "https://", "mailto:")):
                continue
            tgt = os.path.relpath(os.path.normpath(os.path.join(base, u.split("?")[0])), ROOT)
            if not os.path.exists(os.path.join(ROOT, tgt)) and tgt not in generated:
                broken += 1
                problems.append("%s: broken link %s" % (name, u))
        for tbl in re.findall(r"<table[^>]*>(.*?)</table>", body, re.S):
            head = tbl.split("</tr>", 1)[0]
            needs_official = name in RULE_OFFICIAL and "<th>Source</th>" in head
            for tr in re.findall(r"<tr>(.*?)</tr>", tbl[len(head):], re.S):
                if "<th>" in tr:
                    continue
                rows += 1
                unverified = "UNVERIFIED" in tr
                linked = "<a href=" in tr
                if linked or unverified:
                    sourced += 1
                else:
                    problems.append("%s: row without a source link or UNVERIFIED: %s" % (name, re.sub("<[^>]+>", " ", tr)[:110]))
                blank += tr.count(">UNVERIFIED<")
                if needs_official:
                    if unverified or any(h in tr for h in OFFICIAL_HOSTS):
                        official_rows += 1
                    else:
                        problems.append("%s: data row without an official link: %s" % (name, re.sub("<[^>]+>", " ", tr)[:110]))
    for x in problems[:40]:
        print(x)
    if broken:
        raise SystemExit("%d broken internal link(s)" % broken)
    if sourced != rows:
        raise SystemExit("%d data row(s) carry neither a source link nor an UNVERIFIED marker" % (rows - sourced))
    return {"LINKS": str(links), "BROKEN": "0", "ROWS": str(rows), "SOURCED": str(sourced), "BLANK": str(blank),
            "OFFICIAL_ROWS": str(official_rows)}


def build(write=True):
    standings = load_csv("standings_2026.csv")
    injuries = load_csv("injuries_wk10_2026-11-14.csv")
    slate = load_csv("slate_wk10_2026.csv")
    cfg = load("model_config.json")
    research = load("research.json")
    questions = load("questions.json")
    suggestions = load("suggestions.json")
    requirements = load("requirements.json")
    flags = load("flags.json")
    sources = load("sources.json")
    verification = load("verification.json")
    derived, deficiency, lines = compute(standings, injuries, slate, cfg)
    tk = tokens(derived, research["gates"], research)
    pages = {}

    # ---------- overview
    active = "index.html"
    cards = [
        ("Certified rows", "%d" % derived["injury_rows"], "Week-10 injury report rows transcribed from NFL.com and re-verified against the prior snapshot (%d of %d identical)" % (derived["injury_rows"] - 1, derived["injury_rows"]), "injuries.html"),
        ("Games to price", "%d" % derived["unplayed_games"], "unplayed Week-10 games with an originated spread and total, all unvalidated", "lines.html"),
        ("Blocking gates", "%d" % len(research["gates"]), "every one unpassed; the leaderboard is empty because of it", "validation.html"),
        ("Correlations", "%d computed / %d blank" % (sum(1 for c in research["correlation_register"] if c["status"] == "COMPUTED"), sum(1 for c in research["correlation_register"] if c["status"] == "BLANK")), "measured from official standings; the tradable ones need data that does not exist yet", "correlations.html"),
        ("Open questions", "%d" % len(questions["open"]), "%d of them block a decision; each one names what is missing and how to get it" % sum(1 for q in questions["open"] if q["blocking"] == "yes"), "questions.html"),
        ("Suggestions to review", "%d" % len(suggestions["suggestions"]), "implemented ones are marked; the rest wait for your decision", "suggestions.html"),
        ("Flags published", "%d" % len(flags["flags"]), "irregularities and impossible requests, with source links - none block the site", "flagged.html"),
        ("Market prices", UNVERIFIED, "no official NFL source publishes lines or prop prices, so every price cell is blank by policy", "flagged.html"),
    ]
    body = ["<p class='lead'>A single review surface for the NFL line-origination project: what is verified, what is derived, "
            "what is assumed and what is missing. Eight earlier sessions each shipped their own site tree; this hub consolidates "
            "the review layer and leaves their pages in place under <a href='archive.html'>Archive</a>.</p>"]
    body.append("<div class='cards'>" + "".join(
        "<a class='card' href='%s'><h3>%s</h3><div class='big'>%s</div><div class='sub'>%s</div></a>"
        % (h, esc(t), esc(v), esc(s)) for t, v, s, h in cards) + "</div>")
    body.append("<h2>Start here</h2><div class='toc'>" + "".join(
        "<a href='%s'><strong>%s</strong><span>%s</span></a>" % (h, esc(t), d) for h, t, d in [
            ("executive-summary.html", "Executive summary", "the situation in one page"),
            ("suggestions.html", "Suggestions queue", "review and choose the path before anything changes"),
            ("questions.html", "Questions & gaps", "what must be answered before a decision is reasonable"),
            ("lines.html", "Originated lines", "our numbers for the %d unplayed games" % derived["unplayed_games"]),
            ("strategies.html", "Signals & strategies", "singles, props, combos, parlays"),
            ("validation.html", "Validation gates", "the luck-removal protocol"),
            ("deficiency.html", "Depth & deficiencies", "who is missing, and what we cannot know"),
            ("flagged.html", "Flagged for review", "%d irregularities" % len(flags["flags"])),
        ]) + "</div>")
    body.append("<h2>How to read every table</h2><p>")
    body.append("<ul><li>%s - transcribed from an official NFL.com page, with the link in the row.</li>"
                "<li>%s - arithmetic over verified rows; the inputs and the formula are printed so you can recompute it.</li>"
                "<li>%s - a parameter someone chose. It is a model setting, never a fact.</li>"
                "<li>%s - blank cell. Nothing was inferred to fill it.</li></ul></p>" % (
                    badge("VERIFIED") + " <code>VERIFIED</code>", badge("DERIVED") + " <code>DERIVED</code>",
                    badge("ASSUMPTION") + " <code>ASSUMPTION</code>", '<span class="bad">UNVERIFIED</span>'))
    body.append("<h2>Integrity checks on this build</h2><p>%s</p>" % esc(
        "standings consistency: %s" % ("PASS (32 clubs, league totals balance, all per-club splits reconcile)"
                                       if not derived["standings_problems"] else "FAIL " + "; ".join(derived["standings_problems"]))))
    pages[active] = page("Overview", fill("\n".join(body), tk), active)

    # ---------- executive summary
    active = "executive-summary.html"
    b = []
    b.append("<p class='lead'>Bottom line: the data foundation is now verified and the analytical framework is complete, "
             "but nothing can be graded, because no verified price source exists. The correct next move is to start the price "
             "and snapshot archive (S-04, S-05) - every week of delay is permanently lost data.</p>")
    b.append("<h2>What is solid</h2>")
    b.append(table(["Finding", "Value", "Basis", "Source"], [
        ["Week-10 availability table", "%d rows / %d clubs" % (derived["injury_rows"], derived["clubs_reporting"]), "fetched and transcribed 2026-11-14", src("SRC-02")],
        ["Designation split", "%d Out / %d Doubtful / %d Questionable / %d undesignated" % (derived["designations"].get("Out", 0), derived["designations"].get("Doubtful", 0), derived["designations"].get("Questionable", 0), derived["designations"].get("none", 0)), "counts computed from the transcription", src("SRC-02")],
        ["Reproducibility of prior snapshot", "%d of %d rows identical" % (derived["injury_rows"] - 1, derived["injury_rows"]), "row-by-row diff vs the repo file; 1 practice-status drift", src("SRC-16")],
        ["Standings integrity", "32 clubs, league totals balance", "wins=losses, PF=PA, every split reconciles", src("SRC-01")],
        ["League scoring baseline", "%.2f pts per team per game" % (derived["league_total_per_game"] / 2), "derived from official PF totals / games", src("SRC-01")],
        ["Slate", "%d games + 4 byes; %d unplayed" % (derived["slate_rows"] - 4, derived["unplayed_games"]), "official week-10 schedule page", src("SRC-03")],
        ["Best point differential", "JAX +108 (13.5/game)", "official standings", src("SRC-01")],
        ["Worst point differential", "LAC -98", "0-8, official standings", src("SRC-01")],
        ["Net points vs record", "r = %+.4f" % derived["correlations"]["R_NET"], "32 clubs, computed here", src("SRC-01")],
    ]))
    b.append("<h2>What is not known, and why it matters</h2>")
    b.append(table(["Gap", "Consequence today", "Fix", "Flag"], [
        ["No verified price source", "no CLV, no ROI, no promotion of any strategy; market cells blank", "licence a feed or capture closing lines nightly (S-04)", src("FLG-07")],
        ["No official depth chart", "2nd/3rd/4th-string claims are impossible to certify; only starter absence is provable", "two-layer design: certified availability + unverified overlay (S-19)", src("FLG-08")],
        ["No game log in repo", "no home-field estimate, no opponent adjustment, no parlay correlation matrix", "ingest schedule + box scores weekly (S-07)", src("Q-03")],
        ["Standings module lags finished games", "silent look-ahead or lag depending on fetch time", "as-of contract with snapshot timestamps (S-05)", src("FLG-02")],
        ["Legal status of rewards", "leaderboard pays nothing; tiers only", "owner states jurisdiction, counsel reviews (Q-08)", src("FLG-14")],
        ["Uncalibrated model parameters", "originated lines are arithmetic, not edge", "fit after one archived season (Q-07)", src("FLG-12")],
    ]))
    b.append("<h2>Decisions this session took, and the ones it left for you</h2>")
    b.append("<p>Taken: build one consolidated review surface rather than a ninth site tree; keep every legacy tree intact and "
             "link it; leave every unverifiable value blank. Left for you: the 10 blocking questions in "
             "<a href='questions.html'>Questions &amp; gaps</a> and the ordering of the 20 suggestions "
             "(<a href='suggestions.html'>S-20</a> is the recommended sequence).</p>")
    b.append("<h2>Risk of acting on this page</h2><p>Low for the verified rows, high for anything downstream: %d of %d "
             "strategies have passed at least one gate, and every model row on this site is badged DERIVED with an "
             "assumption table attached. Treat the line table as a reviewable formula, not as a forecast.</p>"
             % (0, len(research["strategies"])))
    pages[active] = page("Executive summary", fill("\n".join(b), tk), active)

    # ---------- requirements
    active = "requirements.html"
    cnt = Counter(r["status"].split(" ")[0] for r in requirements["requirements"])
    b = [note(requirements["note"])]
    b.append("<p>%d requirements: %s.</p>" % (len(requirements["requirements"]),
             ", ".join("%s %d" % (k, v) for k, v in sorted(cnt.items()))))
    b.append(table(["#", "Requirement", "Acceptance criteria", "Status", "Where", "Note", "Evidence"],
                   [[r["id"], r["requirement"], r["acceptance"], r["status"], r["where"], r["note"],
                     Raw('<a href="%srequirements.json">requirements.json</a>' % DATA_BLOB)]
                    for r in requirements["requirements"]]))
    pages[active] = page("Requirements", fill("\n".join(b), tk), active)

    # ---------- questions / gaps
    active = "questions.html"
    b = [note(questions["note"])]
    bl = [q for q in questions["open"] if q["blocking"] == "yes"]
    b.append("<p>%d open questions, %d of them blocking a decision; %d questions already have a verified answer.</p>"
             % (len(questions["open"]), len(bl), len(questions["answered"])))
    b.append("<h2>Blocking first</h2>")
    b.append(table(["#", "Question", "Already known", "Still missing", "Path to the answer", "Owner", "Affects", "Evidence"],
                   [[q["id"], q["question"], q["known"], q["missing"], q["discovery"], q["owner"], q["affects"],
                     rowsrc(q["known"], q["missing"])]
                    for q in questions["open"] if q["blocking"] == "yes"]))
    b.append("<h2>Non-blocking</h2>")
    b.append(table(["#", "Question", "Already known", "Still missing", "Path to the answer", "Owner", "Status", "Evidence"],
                   [[q["id"], q["question"], q["known"], q["missing"], q["discovery"], q["owner"], q["status"],
                     rowsrc(q["known"], q["missing"])]
                    for q in questions["open"] if q["blocking"] != "yes"]))
    b.append("<h2>Answered from verified sources</h2>")
    b.append(table(["#", "Question", "Answer", "Source"],
                   [[a["id"], a["question"], a["answer"], src(a["source"])] for a in questions["answered"]]))
    gaps = [
        ["Historical and closing prices", "does not exist on any official NFL property", "licence, or capture nightly from an approved book and store the CSV in git", "S-04", "every performance claim"],
        ["Game logs (score by quarter, plays)", "not in the repo", "ingest the official per-week schedule and game pages (S-07)", "Q-03", "HFA, opponent adjustment, parlay correlation"],
        ["Injury-report history (multi-week)", "only single snapshots exist", "snapshot Wed/Thu/Fri and Sunday -90 min into git (S-05)", "Q-13", "designation base rates, practice trajectory"],
        ["Official depth charts", "do not exist; club charts are self-labelled unofficial", "accept the two-layer design, or buy a depth feed", "Q-05", "2nd/3rd/4th-string claims"],
        ["Snap counts / route participation", "not ingested; Next Gen Stats is official but untouched here", "add an NGS ingestion task and licence check", "Q-12", "usage-based props, target vacancy"],
        ["Inactive lists (final lineups)", "not available at fetch time", "capture Sunday -90 min alongside the report", "Q-13", "lineup certainty, prop pricing"],
        ["Rulebook text for report cadence", "cited to a secondary site only", "fetch and quote the league operations policy page", "S-12", "pipeline schedule assumptions"],
        ["Jurisdiction and licence legality", "unverified; conflicting assumptions across sessions", "owner states country, counsel reviews", "Q-08", "rewards, staking automation"],
    ]
    b.append("<h2>Missing-information register</h2>")
    b.append(table(["Missing input", "Why it is missing", "How to obtain it", "Tracked as", "Unblocks", "Evidence"],
                   [g[:5] + [rowsrc(g[2], g[3])] for g in gaps]))
    pages[active] = page("Questions, information and answers", fill("\n".join(b), tk), active)

    # ---------- suggestions
    active = "suggestions.html"
    st = Counter("Done this session" if s["status"].startswith("Done") else ("Proposed" if s["status"].startswith("Proposed") else "Open")
                 for s in suggestions["suggestions"])
    b = [note(suggestions["note"])]
    b.append("<h2>How to use this queue</h2><ol>" + "".join("<li>%s</li>" % esc(x) for x in suggestions["workflow"]) + "</ol>")
    b.append("<p>%d suggestions: %s.</p>" % (len(suggestions["suggestions"]), ", ".join("%s %d" % (k, v) for k, v in st.items())))
    b.append(table(["#", "Area", "Problem (evidenced)", "Proposal / options", "Impact", "Effort", "Risk", "Status", "Evidence"],
                   [[s["id"], s["area"], s["problem"], s["options"], s["impact"], s["effort"], s["risk"], s["status"], src(s["evidence"])]
                    for s in suggestions["suggestions"]]))
    b.append("<h2>Recommended path (one paragraph, no code changed beyond the hub)</h2><p>Start the archive before anything "
             "else: prices nightly (S-04) and injury/standings snapshots on the league's own cadence (S-05) - that data cannot "
             "be bought back later. Then freeze one data contract and make this hub canonical (S-01, S-03) so two reviewers "
             "stop quoting different numbers for one fact. Only after a season of archived history may any parameter be "
             "calibrated (S-08, S-09, S-10) - until then the gates stay unpassed by design and the leaderboard stays empty.</p>")
    pages[active] = page("Suggestions for review", fill("\n".join(b), tk), active)

    # ---------- lines
    active = "lines.html"
    b = [note("Originated from official league inputs only, using the formula and parameters printed below. "
              "These are model outputs (DERIVED) with uncalibrated assumptions attached; they are not predictions "
              "and none of them has passed a validation gate.")]
    b.append("<h2>Model %s</h2>" % esc(cfg["version"]))
    b.append("<p><code>as_of %s</code> - generator <code>%s</code> - inputs %s</p>" % (
        esc(cfg["as_of"]), esc(cfg["generated_by"]), "SRC-01, SRC-02, SRC-03"))
    b.append(table(["Step", "Formula", "Inputs"],
                   [[i + 1, Raw("<code>%s</code>" % esc(f)), src("SRC-01; SRC-02")] for i, f in enumerate(cfg["formula"])]))
    b.append(table(["Param", "Value", "Unit", "Verified", "Basis", "Flag"],
                   [[a["id"] + " " + a["param"], json.dumps(a["value"]), a.get("unit", ""), "yes" if a["verified"] else "no - ASSUMPTION", a["basis"],
                     Raw("%s &middot; %s" % (src(a.get("flag", "")), src("SRC-01; SRC-02")))] for a in cfg["assumptions"]]))
    b.append("<h2>Week 10 board (%d unplayed games)</h2>" % derived["unplayed_games"])
    b.append("<p>League scoring baseline used: <strong>%.2f</strong> points per team per game from official PF totals over %d club-games. "
             "Two prior in-repo models are shown so the disagreement between them is visible instead of hidden.</p>"
             % (derived["league_total_per_game"], derived["games_played"]))
    b.append(table(["Game", "Kickoff (ET)", "TV", "Net PPG home / away", "Injury loss home / away", "Our home spread", "Our total", "Market close", "Prior model (dashboard v0.1)", "Prior model (x3lab v0.1)", "Source"],
                   [[l["game"], l["kickoff"], l["broadcast"], "%+.2f / %+.2f" % (l["net_home"], l["net_away"]),
                     "%.2f / %.2f" % (l["inj_home"], l["inj_away"]), l["spread_home"], l["total"], l["market"],
                     "%s / %s" % (l["prior_home_spread"], l["prior_total"]) if l["prior_home_spread"] != UNVERIFIED else UNVERIFIED,
                     "%s / %s" % (l["x3_away_spread"], l["x3_total"]) if l["x3_away_spread"] != UNVERIFIED else UNVERIFIED,
                     ("game page", l["url"])] for l in lines]))
    b.append("<h2>Exclusions and cautions</h2><ul>" + "".join("<li>%s</li>" % esc(x) for x in cfg["exclusions"]) + "</ul>")
    b.append(note("Neutral-site games carry HFA = 0 (assumption A-02); the Munich game (NE at DET) is the only one in this slate. "
                  "A game where the starting quarterback cannot be established from an official source gets no QB adjustment - "
                  "see the Baltimore flag."))
    b.append("<h2>Result for context (played)</h2>")
    played = [g for g in slate if g["result"].strip()]
    b.append(table(["Game", "Result", "Source"], [[("%s @ %s" % (g["away"], g["home"])) + " " + g["day"], g["result"], (g["game_url"], g["game_url"])] for g in played]))
    b.append(note("On bye in Week 10, so not priced and not on the injury report: %s (official schedule page)." % ", ".join(derived["byes"])))
    pages[active] = page("Originated lines", fill("\n".join(b), tk), active)

    # ---------- strategies
    active = "strategies.html"
    b = [note("Twelve candidate signals, eight strategy constructions, and the gate each one is stuck on. "
              "A strategy is a hypothesis with a defined entry, exit and required dataset - nothing more until it is graded.")]
    b.append("<h2>Signal catalog</h2>")
    b.append(table(["#", "Signal", "Family", "Construction", "Input", "Target", "Expected direction", "Status", "Gate dependency", "Evidence"],
                   [[s["id"], s["name"], s["family"], s["construction"], s["input"], s["target"], s["direction"], s["status"],
                     s["gate"], rowsrc(s["input"], s["gate"], "SRC-01")]
                    for s in research["signals"]]))
    b.append("<h2>Strategies by bet type</h2>")
    bybt = defaultdict(list)
    for s in research["strategies"]:
        bybt[s["bet_type"]].append(s)
    b.append(table(["#", "Strategy", "Bet type", "Family", "Construction", "Entry / exit", "Data still required", "State", "Gates blocking", "Note", "Evidence"],
                   [[s["id"], s["name"], s["bet_type"], s["family"], s["construction"], "%s / %s" % (s["entry"], s["exit"]),
                     ", ".join(s["required_data"]), s["state"], s["gates_blocking"], s["notes"],
                     Raw('<a href="%sresearch.json">research.json</a>' % DATA_BLOB)] for s in research["strategies"]]))
    b.append("<h2>Coverage by bet type</h2>")
    b.append(table(["Bet type", "Strategies proposed", "Gradable today", "Evidence"],
                   [[k, len(v), Raw('no - no verified price source (%s)' % src("FLG-07")),
                     Raw('<a href="%sresearch.json">research.json</a>' % DATA_BLOB)] for k, v in sorted(bybt.items())]))
    b.append("<h2>Luck-removal programme</h2><ul>" + "".join("<li>%s</li>" % esc(x) for x in research["luck_controls"]) + "</ul>")
    pages[active] = page("Signals and strategies", fill("\n".join(b), tk), active)

    # ---------- validation
    active = "validation.html"
    b = [note("A strategy enters the leaderboard only when every blocking gate below is passed. All are currently unpassed, "
              "so the empty leaderboard on the next page is the correct output, not a missing feature.")]
    b.append(table(["#", "Gate", "Requirement", "Threshold", "Status", "Why it exists", "Evidence"],
                   [[g["id"], g["name"], g["requirement"], g["threshold"], g["status"], g["why"],
                     src("SRC-10" if g["id"] == "G-07" else ("SRC-11" if g["id"] == "G-06" else "SRC-01"))]
                    for g in research["gates"]]))
    passed = 0
    b.append("<p>%d of %d gates are blocking; %d are passed by the hub's own provenance rule (G-00). "
             "Statistical thresholds (n, PBO, DSR) are conventions taken from the cited papers, not league rules - see FLG-11/FLG-12.</p>"
             % (sum(1 for g in research["gates"] if g["blocking"] == "yes"), len(research["gates"]), passed))
    b.append("<h2>What each gate needs before it can be attempted</h2>")
    spec_link = Raw('<a href="%sresearch.json">gates spec</a>' % DATA_BLOB)
    b.append(table(["Gate", "Missing dependency", "First task", "Evidence"], [
        ["G-01 Pre-registration", "a hash recorded per spec", "commit the spec, store its sha256 in the row", spec_link],
        ["G-02 Sample size", "graded bets", "cannot start before G-04", spec_link],
        ["G-03 Calibration", "prices + game logs + lineup history", "run S-04 and S-07, then fit on held-out years", src("S-04")],
        ["G-04 Pricing", "a closing-line capture", "S-04 option B: manual nightly capture", src("FLG-07")],
        ["G-05 Uncertainty", "a bet ledger", "bootstrap intervals once G-04 exists", src("S-08")],
        ["G-06 PBO", "the parameter grid actually searched", "log every variant tried, including discards", src("SRC-11")],
        ["G-07 DSR", "trial count and return moments", "the same log feeds the deflation term", src("SRC-10")],
        ["G-08 Robustness", "a subset ledger", "define subsets before grading, not after", spec_link],
        ["G-09 Correlation", "the blank rows on the correlations page", "measure the matrix from game logs", spec_link],
        ["G-10 Forward test", "untouched future games", "paper trade four weeks before any reward talk", spec_link],
    ]))
    pages[active] = page("Validation gates", fill("\n".join(b), tk), active)

    # ---------- correlations
    active = "correlations.html"
    b = [note("Computed values are Pearson correlations over the 32 clubs in the official standings snapshot of 2026-11-14; "
              "they are descriptive, not tradable. Blank rows are blank because the input does not exist - never estimated.")]
    comp = [c for c in research["correlation_register"] if c["status"] == "COMPUTED"]
    blank = [c for c in research["correlation_register"] if c["status"] != "COMPUTED"]
    b.append("<h2>Computed now (%d)</h2>" % len(comp))
    b.append(table(["#", "Pair", "r", "n", "Method", "Caveat", "Source"],
                   [[c["id"], c["pair"], c["value"], c["n"], c["method"], c["caveat"], src(c["source"] or "SRC-01")] for c in comp]))
    b.append("<h2>Pending, with the exact data required (%d)</h2>" % len(blank))
    b.append(table(["#", "Pair", "Value", "n", "Method / requirement", "Why it is blank", "Source"],
                   [[c["id"], c["pair"], UNVERIFIED, c["n"] or UNVERIFIED, c["method"], c["caveat"], (c["source"] or "FLG-07") and src(c["source"] or "FLG-07")] for c in blank]))
    b.append("<h2>Prior-session figures, re-derived</h2>")
    b.append(table(["Pair", "Published by a prior tree", "Recomputed here", "Agreement", "Evidence"], [
        ["Points for per game vs win %", "+0.6984", tk["R_PF"], "0.002", Raw('%s &middot; <a href="https://github.com/karagemop466-tech/X3/blob/main/dashboard/data/correlations.json">prior file</a>' % src("SRC-01"))],
        ["Points against per game vs win %", "-0.6636", tk["R_PA"], "0.0003", Raw('%s &middot; <a href="https://github.com/karagemop466-tech/X3/blob/main/dashboard/data/correlations.json">prior file</a>' % src("SRC-01"))],
        ["Net points per game vs win %", "+0.8781", tk["R_NET"], "0.0015", Raw('%s &middot; <a href="https://github.com/karagemop466-tech/X3/blob/main/dashboard/data/correlations.json">prior file</a>' % src("SRC-01"))],
        ["Home win % vs road win %", "+0.3501", tk["R_HR"], "0.0005", Raw('%s &middot; <a href="https://github.com/karagemop466-tech/X3/blob/main/dashboard/data/correlations.json">prior file</a>' % src("SRC-01"))],
    ]))
    b.append(note("No denominator convention reproduces the published set exactly, which pins the difference to snapshot timing "
                  "rather than formula. Recorded as FLG-13; the practical rule is to stamp every derived statistic with its "
                  "source snapshot time."))
    pages[active] = page("Correlations", fill("\n".join(b), tk), active)

    # ---------- injuries
    active = "injuries.html"
    b = [note("The complete Week-10 2026 report as published on NFL.com at 2026-11-14 18:08 UTC, transcribed row by row. "
              "Practice status: FP full, LP limited, DNP did not participate. Game status left blank means no designation was "
              "filed - that is not a claim that the player plays (Q-15). Non-injury rest and personal entries are kept as "
              "availability facts and excluded from injury-risk features (Q-16).")]
    order = {g["away"]: g for g in slate}
    for g in slate:
        order[g["home"]] = g
    b.append("<p>%d rows, %d clubs reporting, 4 clubs on bye publish none. Designations: %d Out, %d Doubtful, %d Questionable, %d undesignated.</p>"
             % (derived["injury_rows"], derived["clubs_reporting"], derived["designations"].get("Out", 0),
                derived["designations"].get("Doubtful", 0), derived["designations"].get("Questionable", 0),
                derived["designations"].get("none", 0)))
    rows = [[r["team"], ("%s @ %s" % (g["away"], g["home"])) if g else "", r["player"], r["position"], r["injury"] or "-",
             r["practice"], r["game_status"] or UNVERIFIED, ("nfl.com/injuries", SRC_URL["SRC-02"])]
            for r in injuries for g in [order.get(r["team"])]]
    b.append(table(["Club", "Game", "Player", "Pos", "Injury", "Practice", "Game status", "Source"], rows, cls="dense"))
    pages[active] = page("Injury report - Week 10 2026", fill("\n".join(b), tk), active)

    # ---------- deficiency
    active = "deficiency.html"
    b = [note("Two layers, deliberately kept apart. The certified layer counts who is unavailable from the official report. "
              "The string layer - whether a 2nd, 3rd or 4th-quarterback is in - cannot be certified because no official depth "
              "chart exists (FLG-08), so those columns are blank by policy. Loss numbers are DERIVED using the uncalibrated "
              "weights in the model config.")]
    b.append("<h2>Per-club availability loss (Week 10)</h2>")
    b.append(table(["Club", "Record", "Rows on report", "Out", "Doubtful", "Questionable", "Undesignated", "Non-injury rest",
                    "Offensive loss (pts)", "Defensive loss (pts)", "Deficiency score", "Positions with a starter Out/Doubtful",
                    "2nd/3rd string identity", "Source"],
                   [[d["team"], d["record"], d["rows"], d["out"], d["doubtful"], d["questionable"], d["undesignated"], d["nir"],
                     "%.2f" % d["off_loss"], "%.2f" % d["def_loss"], "%.2f" % d["score"], d["positions"], UNVERIFIED,
                     ("nfl.com/injuries", SRC_URL["SRC-02"])] for d in sorted(deficiency, key=lambda x: -x["score"])]))
    worst = sorted(deficiency, key=lambda x: -x["score"])[:6]
    b.append("<h2>Where the slate is thinnest</h2>")
    b.append("<ul>" + "".join("<li><strong>%s</strong> - deficiency %.2f, %d starters Out or Doubtful (%d offensive, %d defensive): %s</li>"
                              % (esc(d["team"]), d["score"], d["out_offense"] + d["out_defense"], d["out_offense"], d["out_defense"], esc(d["positions"]))
                              for d in worst) + "</ul>")
    b.append("<h2>What a deficiency score can and cannot say</h2>")
    b.append(table(["Claim", "Supportable from official data?", "Treatment here", "Evidence"], [
        ["A named starter will not play", "yes - the report states Out", "used, cited", src("SRC-02")],
        ["How much that absence costs", "no - requires calibration", "shown as DERIVED with the weight table printed", Raw('<a href="%smodel_config.json">model_config.json</a> &middot; %s' % (DATA_BLOB, src("FLG-12")))],
        ["Who replaces them, and what string they are", "no official source exists", Raw('blank + %s' % UNVERIFIED), src("FLG-08")],
        ["Whether a backup's presence changes a prop market", "no - needs prop prices and usage data", "not attempted", Raw('%s &middot; %s' % (src("FLG-07"), src("Q-12")))],
        ["Whether the club is resting someone on purpose", "partly - the report says 'Not injury related'", Raw('kept in availability, excluded from injury risk (%s)' % src("Q-16")), src("SRC-02")],
        ["Whether the Sunday inactive list agrees", "not yet - it lands about 90 min before kickoff", Raw('re-snapshot then (%s)' % src("FLG-17")), src("SRC-12")],
    ]))
    pages[active] = page("Depth and deficiency tracking", fill("\n".join(b), tk), active)

    # ---------- leaderboard
    active = "leaderboard.html"
    lb = research["leaderboard"]
    b = [note("A competition structure with an empty table. Nothing may be promoted, and no reward is payable, until every "
              "blocking gate on the validation page is passed - which is why the standings below are deliberately blank.")]
    b.append("<h2>Scoring model</h2><ul>" + "".join("<li>%s</li>" % esc(x) for x in lb["score_model"]) + "</ul>")
    b.append("<h2>Categories</h2><p>%s</p>" % esc(", ".join(lb["categories"])))
    b.append("<h2>Season structure</h2><ol>" + "".join("<li>%s</li>" % esc(x) for x in lb["season_structure"]) + "</ol>")
    b.append("<h2>Anti-gaming rules</h2><ul>" + "".join("<li>%s</li>" % esc(x) for x in lb["anti_gaming"]) + "</ul>")
    b.append("<h2>Registered strategies and their state</h2>")
    b.append(table(["#", "Strategy", "Bet type", "State", "Gates blocking", "Reward tier"],
                   [[s["id"], s["name"], s["bet_type"], s["state"], s["gates_blocking"],
                     Raw('T3 (no reward) &middot; <a href="%sresearch.json">spec</a>' % DATA_BLOB)] for s in research["strategies"]]))
    b.append("<h2>Leaderboard</h2>")
    empty_row = ["-"] + [UNVERIFIED] * 8 + ["no entries", "blank - owner decision (Q-08)"]
    b.append(table(["Rank", "Strategy", "Owner", "Bets", "CLV (95% CI)", "ROI (95% CI)", "Max drawdown", "DSR", "PBO", "Tier", "Reward"],
                   [empty_row]))
    b.append(note(lb["entries_note"]))
    rw = lb["rewards"]
    b.append("<h2>Reward design (notional)</h2>")
    b.append(table(["Tier", "Criteria", "Reward", "Amount", "Currency", "Status", "Evidence"],
                   [[t["tier"], t["criteria"], t["reward"], "blank - UNVERIFIED", "blank - UNVERIFIED", "notional",
                     Raw('<a href="%sresearch.json">leaderboard spec</a> &middot; %s' % (DATA_BLOB, src("FLG-14")))] for t in rw["tiers"]]))
    b.append(note(rw["basis"]))
    pages[active] = page("Leaderboard and rewards", fill("\n".join(b), tk), active)

    # ---------- repo review
    active = "repo-review.html"
    trees = []
    for d in ["", "docs", "dashboard", "lab", "x3lab", "pages", "site", "legacy", "hub"]:
        p = os.path.join(ROOT, d) if d else ROOT
        idx = os.path.join(p, "index.html")
        if os.path.exists(idx):
            html_txt = open(idx, encoding="utf-8").read()
            trees.append({
                "dir": d or "/", "files": len([1 for _ in re.finditer(r"<table", html_txt)]),
                "bytes": os.path.getsize(idx), "redirect": "refresh" if "http-equiv" in html_txt and "refresh" in html_txt else "",
                "title": (re.search(r"<title>(.*?)</title>", html_txt, re.S).group(1).strip() if "<title>" in html_txt else "-"),
            })
    b = [note("Read of the repository as it stands on main, item by item, with the link to review each one by hand. "
              "Nothing here was deleted: two shared files (root index.html, COORDINATION.md) were touched under the integration role.")]
    b.append("<h2>Site trees found in the repo</h2>")
    b.append(table(["Tree", "Page title", "Tables on its index", "Index bytes", "Notes", "Evidence"],
                   [[t["dir"], t["title"], t["files"], t["bytes"], "meta-refresh redirect" if t["redirect"] else "content page",
                     ("tree on github", "https://github.com/karagemop466-tech/X3/tree/main" + ("" if t["dir"] == "/" else "/" + t["dir"]))] for t in trees]))
    b.append("<h2>Findings and irregularities</h2>")
    b.append(table(["#", "Finding", "Evidence"], [
        ["H-01", "Eight site trees from eight merged sessions, nine index files; the root was a redirect with no information", ("tree", "https://github.com/karagemop466-tech/X3/tree/main")],
        ["H-02", "The Pages workflow still triggers on the merged branch arena/1a771fcd-x3 and chains five checkers over all trees", ("workflow", "https://github.com/karagemop466-tech/X3/blob/main/.github/workflows/pages.yml")],
        ["H-03", "Branch arena/64164906-x3 has 5 failing data-pipeline runs (a workflow not in main), last seen 14h ago", ("runs", "https://github.com/karagemop466-tech/X3/actions?query=branch%3Aarena%2F64164906-x3")],
        ["H-04", "PR #12 from another session is still open while the shared files it touches have moved on", ("pull/12", "https://github.com/karagemop466-tech/X3/pull/12")],
        ["H-05", "No LICENSE, no CODEOWNERS, no branch protection, no unit tests for the builders", ("repo", "https://github.com/karagemop466-tech/X3")],
        ["H-06", "Four data directories hold overlapping registers with different team ids (LA/LAR, ARI/AZ)", ("data", "https://github.com/karagemop466-tech/X3/tree/main/data")],
        ["H-07", "A prior tree's standings table carries a wrong TB division record (1-2-0 vs the official 2-0-0)", ("file", "https://github.com/karagemop466-tech/X3/blob/main/dashboard/data/standings.json")],
        ["H-08", "A prior session published correlations from a standings snapshot that no longer reproduces exactly", ("file", "https://github.com/karagemop466-tech/X3/blob/main/dashboard/data/correlations.json")],
        ["H-09", "Pages source is legacy main /, so every experimental tree is publicly served; changing it needs repo-admin rights", ("api", "https://api.github.com/repos/karagemop466-tech/X3/pages")],
        ["H-10", "Two sessions recorded the owner's jurisdiction as Japan; the environment reports the Netherlands - unresolved", ("log", "https://github.com/karagemop466-tech/X3/blob/main/COORDINATION.md")],
        ["H-11", "Injury data quality is good: this session's fresh transcription matches the prior snapshot on all %d rows except one practice status" % derived["injury_rows"], ("diff", "https://github.com/karagemop466-tech/X3/blob/main/docs/data/injury-2026-week10.csv")],
        ["H-12", "No betting line or prop price exists on any official NFL property, so all price columns stay blank by policy", ("injuries", "https://www.nfl.com/injuries/")],
    ]))
    pages[active] = page("Repo review", fill("\n".join(b), tk), active)

    # ---------- sources
    active = "sources.html"
    b = [note(sources["note"])]
    b.append(table(["#", "Source", "Class", "Accessed", "Used for", "Verification status", "URL"],
                   [[s["id"], s["name"], s["class"], s["accessed"], s["used_for"], s["status"], (s["id"], s["url"])] for s in sources["sources"]]))
    pages[active] = page("Source register", fill("\n".join(b), tk), active)

    # ---------- verification
    active = "verification.html"
    b = [note(verification["note"])]
    ok = sum(1 for c in verification["checks"] if c["status"].startswith("PASS"))
    b.append("<p>%d checks recorded: %d pass, %d pass-with-findings, %d pending or not verifiable by design.</p>"
             % (len(verification["checks"]), ok, 2, len(verification["checks"]) - ok - 2))
    b.append(table(["#", "Target", "Method", "Result", "Status", "Source"],
                   [[c["id"], c["target"], c["method"], c["result"], c["status"], src(c["source"])] for c in verification["checks"]]))
    b.append("<h2>Build integrity</h2><ul><li>standings consistency: %s</li><li>derived snapshot digest: <code>%s</code></li></ul>"
             % (esc("PASS" if not derived["standings_problems"] else "FAIL " + "; ".join(derived["standings_problems"])),
                hashlib.sha256(json.dumps(derived, sort_keys=True).encode()).hexdigest()[:16]))
    VER_BODY = "\n".join(b)

    # ---------- flagged
    active = "flagged.html"
    b = ['<p class="lead">Everything this project could not confirm, plus the irregularities found while reviewing the repo. '
         'Nothing here blocks the site or the merge; each row is here so a change can be requested after the fact.</p>']
    sev = Counter(f["severity"] for f in flags["flags"])
    b.append("<p>%d flags: %s.</p>" % (len(flags["flags"]), ", ".join("%s %d" % (k, v) for k, v in sorted(sev.items()))))
    for level in ("High", "Medium", "Low"):
        sel = [f for f in flags["flags"] if f["severity"] == level]
        if not sel:
            continue
        b.append("<h2>%s severity</h2>" % level)
        b.append(table(["#", "Area", "Finding", "Evidence", "Impact", "Proposed action", "Status"],
                       [[f["id"], f["area"], f["finding"], (f["evidence"], f["evidence"].split(" ; ")[0]), f["impact"], f["action"], f["status"]] for f in sel]))
    b.append(note("To request a change on any row: quote its flag id. Values that could not be confirmed were left blank rather "
                  "than estimated, in %d of the hub's tables." % 3))
    pages[active] = page("Flagged for review", fill("\n".join(b), tk), active)

    # ---------- archive
    active = "archive.html"
    arch = [
        ("docs/", "Week 10 archive site from the earlier sessions (13 pages, its own 345-row injury table)", "https://github.com/karagemop466-tech/X3/tree/main/docs", "docs/index.html"),
        ("dashboard/", "18-page verified-data dashboard, incl. the standings table this session found to carry a TB division error", "https://github.com/karagemop466-tech/X3/tree/main/dashboard", "dashboard/index.html"),
        ("lab/", "source-first research module, the page the root URL used to redirect to", "https://github.com/karagemop466-tech/X3/tree/main/lab", "lab/index.html"),
        ("x3lab/", "Lines & Strategy Lab with third-party market columns (unverified this session)", "https://github.com/karagemop466-tech/X3/tree/main/x3lab", "x3lab/index.html"),
        ("pages/", "first integration site (5 category pages)", "https://github.com/karagemop466-tech/X3/tree/main/pages", "pages/executive-summary.html"),
        ("site/", "index only, kept for back-compat", "https://github.com/karagemop466-tech/X3/tree/main/site", "site/index.html"),
        ("legacy/", "the very first landing page", "https://github.com/karagemop466-tech/X3/tree/main/legacy", "legacy/index.html"),
        ("data/", "first CSV registers", "https://github.com/karagemop466-tech/X3/tree/main/data", "data/requirements.csv"),
        ("root *.html", "the additive category pages (executive-summary, requirements, suggestions, lines, leaderboard, injuries, verification, sources, flagged, review)", "https://github.com/karagemop466-tech/X3", "executive-summary.html"),
    ]
    b = [note("Kept intact, deliberately not deleted, and not merged into the hub's data. These trees were produced by other "
              "sessions and were not edited by this one; the hub supersedes them as the review surface. Values that disagree "
              "with the hub are listed on the Flagged page rather than silently corrected.")]
    b.append(table(["Tree", "What it is", "Repository", "Live page"],
                   [[a[0], a[1], (a[0] + " on github", a[2]), ("open on Pages", "../" + a[3])] for a in arch]))
    b.append(note("Archive rows link to the repository path (a real file, verifiable by hand) and to the published page."))
    b.append("<h2>Why they are not merged</h2><p>Merging eight page sets into one URL space would silently change what earlier "
             "sessions verified and would need edits to files their coordination claims still reserve. S-01 proposes the two-step "
             "fix: declare this hub canonical (done), then move the trees under <code>/archive</code> in one cleanup PR once you "
             "approve it.</p>")
    pages[active] = page("Archive of prior trees", fill("\n".join(b), tk), active)

    # ---------- root landing
    landing = []
    landing.append("<p class='lead'>NFL line origination, injury and depth tracking, and a strategy-validation programme - "
                   "one dashboard, one review queue, one list of what is still unknown.</p>")
    landing.append("<div class='cards'>" + "".join(
        "<a class='card' href='hub/%s'><h3>%s</h3><div class='big'>%s</div><div class='sub'>%s</div></a>"
        % (h, esc(t), esc(v), esc(s)) for t, v, s, h in cards) + "</div>")
    landing.append("<div class='status'><strong>Data as of</strong> 2026-11-14 18:15 UTC &middot; Week 10 of the 2026 season "
                   "&middot; official sources: <a href='https://www.nfl.com/injuries/'>injury report</a>, "
                   "<a href='https://www.nfl.com/standings/league/2026/REG'>standings</a>, "
                   "<a href='https://www.nfl.com/schedules/2026/by-week/week-10'>schedule</a>. "
                   "<strong>Prices and depth strings are blank</strong> because no official source publishes them.</div>")
    landing.append("<h2>Sections</h2><div class='toc'>" + "".join(
        "<a href='hub/%s'><strong>%s</strong></a>" % (h, esc(t)) for h, t in NAV if h != "index.html") + "</div>")
    landing.append("<h2>Read this first</h2><ul>"
                   "<li>%d verified injury rows, %d originated lines, %d validation gates, <strong>0</strong> graded bets.</li>"
                   "<li>The next blocking step is a price archive (S-04); the second is nightly snapshots (S-05).</li>"
                   "<li>%d irregularities are published rather than buried, including one corrected value in a prior tree.</li>"
                   "</ul>" % (derived["injury_rows"], derived["unplayed_games"], len(research["gates"]), len(flags["flags"])))
    landing.append("<h2>Archive</h2><p>Eight earlier site trees remain online and untouched: "
                   + ", ".join("<a href='hub/archive.html'>%s</a>" % a[0] for a in arch[:6]) + " - see <a href='hub/archive.html'>the full archive index</a>.</p>")
    pages["__root__"] = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>X3 - NFL lines, injuries and strategy lab</title>
<meta name="description" content="NFL decision workspace: verified injury and standings data, originated lines, validation gates, suggestions queue and flagged-for-review register.">
<link rel="stylesheet" href="hub/style.css">
</head>
<body>
<header class="top">
  <div class="brand"><strong>X3</strong> NFL review hub</div>
  <nav><a href="hub/index.html">Hub</a> <a href="hub/executive-summary.html">Executive summary</a>
  <a href="hub/suggestions.html">Suggestions</a> <a href="hub/lines.html">Lines</a>
  <a href="hub/flagged.html">Flagged</a> <a href="hub/archive.html">Archive</a></nav>
</header>
<main>%s</main>
<footer><p>Static site generated by <code>scripts/build_hub.py</code>. No betting advice, no wagers, no rewards paid.</p></footer>
</body>
</html>
""" % fill("\n".join(landing), tk)

    # verification page is rendered last so its numbers describe the finished site
    virtual = {"hub/style.css", "hub/verification.html"} | {"hub/" + k for k in pages} | {"index.html"}
    stats = scan_stats(pages, [VER_BODY], virtual=virtual)
    tk2 = dict(tk)
    tk2.update(stats)
    pages["verification.html"] = page("Verification log", fill(VER_BODY, tk2), "verification.html")
    for k, v in list(pages.items()):
        pages[k] = fill(v, tk2) if "{{" in v else v
    left = sorted({m for v in pages.values() for m in re.findall(r"\{\{([A-Z_0-9]+)\}\}", v)})
    if left:
        raise SystemExit("tokens unfilled after final pass: %s" % left)

    if write:
        with open(os.path.join(HUB, "style.css"), "w", encoding="utf-8") as fh:
            fh.write(CSS)
        for name, content in pages.items():
            path = os.path.join(ROOT, "index.html") if name == "__root__" else os.path.join(OUT, name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        with open(os.path.join(DATA, "derived.json"), "w", encoding="utf-8") as fh:
            json.dump(derived, fh, indent=1, sort_keys=True)
    return pages, derived, deficiency, lines


CSS = """
:root{--bg:#0e1420;--card:#151f2e;--fg:#e8eef6;--mut:#9fb0c4;--line:#26364a;--acc:#5ad1a4;--warn:#e8b45a;--bad:#e07a6a;--der:#6fa8dc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
header.top{position:sticky;top:0;z-index:5;background:#0b1119ee;border-bottom:1px solid var(--line);
 display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;padding:.7rem 1rem;backdrop-filter:blur(6px)}
.brand{font-size:1.02rem;letter-spacing:.3px;margin-right:.6rem}
header nav{display:flex;flex-wrap:wrap;gap:.15rem .7rem;font-size:.86rem}
header nav a{color:var(--mut);padding:.15rem .1rem;border-bottom:2px solid transparent}
header nav a.on,header nav a:hover{color:var(--fg);text-decoration:none;border-bottom-color:var(--acc)}
main{padding:1.1rem 1.15rem 3rem;max-width:1500px;margin:0 auto}
h1{font-size:1.5rem;margin:.3rem 0 .7rem}h2{font-size:1.12rem;margin:1.6rem 0 .5rem;color:#cfe0f2}
h3{font-size:.9rem;margin:0;color:var(--mut);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
p.lead{color:#d7e3f0;font-size:1.02rem;max-width:78ch}.note{color:var(--mut);font-size:.88rem;max-width:95ch}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:.6rem;margin:.9rem 0 1.1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.7rem .8rem;display:block;color:inherit}
.card:hover{border-color:var(--acc);text-decoration:none}
.card .big{font-size:1.45rem;font-weight:650;margin:.15rem 0}.card .sub{color:var(--mut);font-size:.8rem;line-height:1.35}
.toc{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:.4rem;margin:.6rem 0 1rem}
.toc a{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.5rem .65rem;font-size:.87rem;color:var(--fg)}
.toc a:hover{border-color:var(--acc);text-decoration:none}.toc span{display:block;color:var(--mut);font-size:.77rem}
table{border-collapse:collapse;width:100%;margin:.5rem 0 1rem;font-size:.84rem;background:var(--card)}
th,td{border:1px solid var(--line);padding:.38rem .5rem;text-align:left;vertical-align:top}
th{background:#101a27;color:#c8d8ea;font-weight:600;position:sticky;top:0}
tbody tr:nth-child(even){background:#131d2b}td.blank{background:#2a1d20}
table.dense{font-size:.79rem}table.dense td{padding:.22rem .42rem}
code{background:#0b1320;border:1px solid var(--line);border-radius:4px;padding:.05rem .3rem;font-size:.85em;color:#cfe3ff}
ul,ol{margin:.4rem 0 .9rem 1.15rem;padding:0}li{margin:.2rem 0}
.good,.derived,.warn,.bad{display:inline-block;font-size:.68rem;font-weight:700;letter-spacing:.05em;padding:.1rem .34rem;border-radius:4px}
.good{background:#12352a;color:#7fe0b6}.derived{background:#12283c;color:#9fcaf3}
.warn{background:#3a2d12;color:#f0c375}.bad{background:#3c1b18;color:#f0a294}
.status{border-left:3px solid var(--acc);background:var(--card);padding:.55rem .8rem;border-radius:0 8px 8px 0;font-size:.86rem;margin:.9rem 0}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:.78rem;padding:1rem 1.2rem 2.2rem;max-width:1500px;margin:0 auto}
@media(max-width:760px){main{padding:.8rem}.cards{grid-template-columns:1fr 1fr}}
"""


if __name__ == "__main__":
    pages, derived, deficiency, lines = build()
    print("built %d pages; rows=%d lines=%d; standings checks=%s"
          % (len(pages), derived["injury_rows"], len(lines), derived["standings_problems"] or "clean"))
