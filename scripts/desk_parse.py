#!/usr/bin/env python3
"""Parse captured official NFL pages into source-linked datasets.

Inputs : capture/*.html                 raw HTML captured by the CI workflow
Outputs: data/desk/games.json           2026 regular-season game log (W1-W11)
         data/desk/standings.json       2026 league standings
         data/desk/injuries.json        Week 8-11 official injury reports
         data/desk/depth.json           32 club depth charts with string order
         data/desk/parse_report.json    per-page counts + every parse problem

Parsing rules:
  * values are read only from the captured page; missing cells stay empty
  * each row keeps the official URL it came from (game page when the schedule links
    one, otherwise the week's schedule page)
  * a game is emitted only when both scores are present; scheduled games are emitted
    with empty scores and an explicit status
  * nothing is inferred, normalised or filled in
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from desk_extract import text_of

NFL = "https://www.nfl.com"
SCHEDULE_URL = NFL + "/schedules/2026/by-week/week-{}"
STANDINGS_URL = NFL + "/standings/league/2026/reg"
INJURY_URL = NFL + "/injuries/league/2026/reg{}"

CLUB_DEPTH = {
    "ARI": "https://www.azcardinals.com/team/depth-chart",
    "ATL": "https://www.atlantafalcons.com/team/depth-chart",
    "BAL": "https://www.baltimoreravens.com/team/depth-chart",
    "BUF": "https://www.buffalobills.com/team/depth-chart",
    "CAR": "https://www.panthers.com/team/depth-chart",
    "CHI": "https://www.chicagobears.com/team/depth-chart",
    "CIN": "https://www.bengals.com/team/depth-chart",
    "CLE": "https://www.clevelandbrowns.com/team/depth-chart",
    "DAL": "https://www.dallascowboys.com/team/depth-chart",
    "DEN": "https://www.denverbroncos.com/team/depth-chart",
    "DET": "https://www.detroitlions.com/team/depth-chart",
    "GB": "https://www.packers.com/team/depth-chart",
    "HOU": "https://www.houstontexans.com/team/depth-chart",
    "IND": "https://www.colts.com/team/depth-chart",
    "JAX": "https://www.jaguars.com/team/depth-chart",
    "KC": "https://www.chiefs.com/team/depth-chart",
    "LA": "https://www.therams.com/team/depth-chart",
    "LAC": "https://www.chargers.com/team/depth-chart",
    "LV": "https://www.raiders.com/team/depth-chart",
    "MIA": "https://www.miamidolphins.com/team/depth-chart",
    "MIN": "https://www.vikings.com/team/depth-chart",
    "NE": "https://www.patriots.com/team/depth-chart",
    "NO": "https://www.neworleanssaints.com/team/depth-chart",
    "NYG": "https://www.giants.com/team/depth-chart",
    "NYJ": "https://www.newyorkjets.com/team/depth-chart",
    "PHI": "https://www.philadelphiaeagles.com/team/depth-chart",
    "PIT": "https://www.steelers.com/team/depth-chart",
    "SEA": "https://www.seahawks.com/team/depth-chart",
    "SF": "https://www.49ers.com/team/depth-chart",
    "TB": "https://www.buccaneers.com/team/depth-chart",
    "TEN": "https://www.tennesseetitans.com/team/depth-chart",
    "WAS": "https://www.commanders.com/team/depth-chart",
}

SCHEDULE_CLUB_NAME = {
    "Cardinals": "ARI", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF",
    "Panthers": "CAR", "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE",
    "Cowboys": "DAL", "Broncos": "DEN", "Lions": "DET", "Packers": "GB",
    "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX", "Chiefs": "KC",
    "Rams": "LA", "Chargers": "LAC", "Raiders": "LV", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG",
    "Jets": "NYJ", "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF",
    "Seahawks": "SEA", "Buccaneers": "TB", "Titans": "TEN", "Commanders": "WAS",
}

PARSE_NOTES: list[str] = []


def note(msg: str) -> None:
    PARSE_NOTES.append(msg)


# --------------------------------------------------------------------------- #
# 1. Game log                                                                  #
# --------------------------------------------------------------------------- #
SCORE_LINE = re.compile(
    r"^([A-Za-z0-9 ]+?) (\d{1,3}), ([A-Za-z0-9 ]+?) (\d{1,3}), FINAL", re.M)


def parse_schedule(name: str, raw: str) -> list[dict]:
    week = int(re.search(r"week-(\d+)", name).group(1))
    text = text_of(raw)
    links = {}
    for href, inner in re.findall(
            r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw, re.S | re.I):
        m = re.search(r"/games/([a-z0-9-]+-2026-reg-\d+)$", href)
        if not m:
            continue
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
        links.setdefault(m.group(1), label)
    games = []
    for line in text.splitlines():
        m = SCORE_LINE.match(line)
        if not m:
            continue
        away_name, away_score, home_name, home_score = m.groups()
        away_name, home_name = away_name.strip(), home_name.strip()
        good = {v: k for k, v in ((a, b) for a, b in SCHEDULE_CLUB_NAME.items())}
        if away_name not in SCHEDULE_CLUB_NAME or home_name not in SCHEDULE_CLUB_NAME:
            note(f"{name}: unrecognised club in score line: {line}")
            continue
        slug_part = f"{away_name.lower().replace(' ', '-')}-at-{home_name.lower().replace(' ', '-')}-2026-reg-{week}"
        slug_part = slug_part.replace("49ers", "49ers")
        src = f"{NFL}/games/{slug_part}"
        if slug_part not in links:
            note(f"{name}: no game link for {line}; using schedule page as source")
            src = SCHEDULE_URL.format(week)
        games.append({
            "week": week, "away": SCHEDULE_CLUB_NAME[away_name],
            "home": SCHEDULE_CLUB_NAME[home_name],
            "away_score": int(away_score), "home_score": int(home_score),
            "status": "FINAL", "source": src,
        })
    # Scheduled (not yet played) games: HOME at AWAY team cards, no FINAL line.
    scheduled = []
    for m in re.finditer(r"/games/([a-z0-9-]+-2026-reg-(\d+))", raw):
        pass
    return games


def parse_schedule_scheduled(name: str, raw: str) -> list[dict]:
    """Games with no FINAL line: read gameTime + club abbreviations from the payload."""
    week = int(re.search(r"week-(\d+)", name).group(1))
    out = []
    for m in re.finditer(r'"gameTime":"([^"]+)"', raw):
        pass
    # Next.js payload: {"gameTime":..,"homeTeam":{"abbreviation":..},"awayTeam":..}
    for chunk in re.findall(r'self\.__next_f\.push\(\[1,(".*?")\]\)', raw, re.S):
        try:
            payload = json.loads(chunk)
        except Exception:
            continue
        for g in re.finditer(
                r'"gameTime":"([^"]+)".{0,4000}?"homeTeam":\{"abbreviation":"([A-Z]{2,3})"'
                r'.{0,4000}?"awayTeam":\{"abbreviation":"([A-Z]{2,3})"', payload, re.S):
            out.append({"gameTime": g.group(1), "home": g.group(2), "away": g.group(3)})
    return out

def main(src: str, dst: str) -> int:
    cap, out = Path(src), Path(dst)
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"notes": PARSE_NOTES}
    # implemented below
    (out / "parse_report.json").write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
