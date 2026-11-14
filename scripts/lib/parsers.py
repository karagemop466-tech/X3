"""Parsers that turn raw official HTML into flat, source-linked records.

Every parser returns a list of dicts. Each dict MUST carry ``source_url`` so
the published tables can link every row back to the official page it came from.
Values that the official page does not publish are left as empty strings —
never inferred.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

SPACE_RE = re.compile(r"\s+")


def _txt(node) -> str:
    if node is None:
        return ""
    return SPACE_RE.sub(" ", node.get_text(" ", strip=True)).strip()


def _int(value: str):
    """Parse an integer cell; return None when the cell is blank/non-numeric."""
    value = (value or "").strip()
    if not value:
        return None
    m = re.search(r"-?\d[\d,]*", value.replace("−", "-"))
    if not m:
        return None
    try:
        return int(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _float(value: str):
    value = (value or "").strip()
    if not value:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", value.replace("−", "-"))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Injury report — https://www.nfl.com/injuries/
# ---------------------------------------------------------------------------

PRACTICE_STATUSES = (
    "Did Not Participate In Practice",
    "Limited Participation in Practice",
    "Full Participation in Practice",
)


def parse_injuries(html: str, source_url: str) -> dict:
    """Parse the official NFL.com weekly injury report."""
    soup = BeautifulSoup(html, "lxml")
    title = _txt(soup.find("h1")) or ""
    week_match = re.search(r"WEEK\s+(\d+)", title, re.I)
    week = int(week_match.group(1)) if week_match else None

    rows: list[dict] = []
    games: list[dict] = []
    for wrap in soup.select("div.nfl-o-injury-report__wrap"):
        # The page groups every game of the week inside one wrapper, with a
        # day heading ("THURSDAY, NOVEMBER 12TH") preceding each day's games.
        # Walk the wrapper in document order so each unit inherits the day
        # heading that actually precedes it.
        units = wrap.select("section.nfl-o-injury-report__unit")
        ordered: list[tuple[int, str, object]] = []
        for child in wrap.descendants:
            if not getattr(child, "name", None):
                continue
            if child.name in ("h2", "h3"):
                ordered.append((0, "heading", child))
            elif getattr(child, "attrs", {}).get("class") and any(
                c == "nfl-o-injury-report__unit" for c in child.get("class", [])
            ):
                ordered.append((1, "unit", child))
        current_date = ""
        for _, kind, node in ordered:
            if kind == "heading":
                current_date = _txt(node)
                continue
            unit = node
            game_date = current_date
            strip = unit.select_one("div.nfl-c-matchup-strip")
            teams = unit.select("div.nfl-c-matchup-strip__team")
            info: dict = {"game_date": game_date}
            if strip:
                dt = strip.select_one("span.nfl-c-matchup-strip__date-time")
                tz = strip.select_one("span.nfl-c-matchup-strip__date-timezone")
                net = strip.select_one("p.nfl-c-matchup-strip__networks")
                info["game_time"] = _txt(dt)
                info["game_timezone"] = _txt(tz)
                info["network"] = _txt(net)
            team_meta = []
            for t in teams:
                abbr = t.select_one("span.nfl-c-matchup-strip__team-abbreviation")
                name = t.select_one("a.nfl-c-matchup-strip__team-fullname")
                rec = t.select_one("div.nfl-c-matchup-strip__record")
                team_meta.append(
                    {
                        "abbr": _txt(abbr),
                        "name": _txt(name),
                        "record": _txt(rec).strip("()"),
                        "slug": (name.get("href") if name else "") or "",
                    }
                )
            if len(team_meta) >= 2:
                info["away_team"] = team_meta[0]["abbr"]
                info["away_team_name"] = team_meta[0]["name"]
                info["away_record"] = team_meta[0]["record"]
                info["home_team"] = team_meta[1]["abbr"]
                info["home_team_name"] = team_meta[1]["name"]
                info["home_record"] = team_meta[1]["record"]
            sub = unit.select_one("div.d3-o-section-sub-title span")
            table = unit.find("table")
            if table is None:
                continue
            # The sub-title names the team whose table follows.
            current_team = _txt(sub)
            if len(team_meta) >= 2:
                if current_team.lower() == team_meta[0]["name"].lower():
                    current_team = team_meta[0]["abbr"]
                elif current_team.lower() == team_meta[1]["name"].lower():
                    current_team = team_meta[1]["abbr"]
            headers = [_txt(th) for th in table.select("thead th")]
            idx = {h.lower(): i for i, h in enumerate(headers)}
            for tr in table.select("tbody tr"):
                cells = tr.find_all("td")
                if len(cells) < 3:
                    continue
                values = [_txt(c) for c in cells]

                def get(col: str) -> str:
                    i = idx.get(col.lower())
                    if i is None or i >= len(values):
                        return ""
                    return values[i]

                player_link = cells[0].find("a")
                rows.append(
                    {
                        "week": week,
                        "game_date": info.get("game_date", ""),
                        "game_time": info.get("game_time", ""),
                        "game_timezone": info.get("game_timezone", ""),
                        "network": info.get("network", ""),
                        "away_team": info.get("away_team", ""),
                        "away_team_name": info.get("away_team_name", ""),
                        "away_record": info.get("away_record", ""),
                        "home_team": info.get("home_team", ""),
                        "home_team_name": info.get("home_team_name", ""),
                        "home_record": info.get("home_record", ""),
                        "team": current_team,
                        "player": get("player"),
                        "player_url": (
                            "https://www.nfl.com" + player_link.get("href")
                            if player_link and player_link.get("href", "").startswith("/")
                            else ""
                        ),
                        "position": get("position"),
                        "injuries": get("injuries"),
                        "practice_status": get("practice status"),
                        "game_status": get("game status"),
                        "source_url": source_url,
                    }
                )
            games.append(
                {
                    "week": week,
                    "game_date": info.get("game_date", ""),
                    "game_time": info.get("game_time", ""),
                    "game_timezone": info.get("game_timezone", ""),
                    "network": info.get("network", ""),
                    "away_team": info.get("away_team", ""),
                    "away_team_name": info.get("away_team_name", ""),
                    "away_record": info.get("away_record", ""),
                    "home_team": info.get("home_team", ""),
                    "home_team_name": info.get("home_team_name", ""),
                    "home_record": info.get("home_record", ""),
                    "source_url": source_url,
                }
            )
    return {
        "week": week,
        "title": title,
        "rows": rows,
        "games": games,
        "source_url": source_url,
    }


# ---------------------------------------------------------------------------
# Standings — https://www.nfl.com/standings/league/<year>/REG
# ---------------------------------------------------------------------------

STANDING_COLUMNS = [
    "team",
    "wins",
    "losses",
    "ties",
    "win_pct",
    "points_for",
    "points_against",
    "net_points",
    "home",
    "road",
    "division",
    "division_pct",
    "conference",
    "conference_pct",
    "non_conference",
    "streak",
    "last_5",
]


def parse_standings(html: str, source_url: str, season: int | None = None) -> list[dict]:
    """Parse an NFL.com standings table (league, division or conference view)."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []
    headers = [_txt(th) for th in table.select("thead th")]
    # The team cell carries the logo; the visible header row starts with an
    # empty column when the table is league/conference scoped.
    rows: list[dict] = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 8:
            continue
        team_cell = cells[0]
        link = team_cell.find("a")
        full = team_cell.select_one(".d3-o-club-fullname")
        short = team_cell.select_one(".d3-o-club-shortname")
        team_name = _txt(full) if full else ""
        if not team_name and link:
            label = link.get("aria-label", "")
            team_name = re.sub(r"^Go to\s+", "", label).replace(" info page.", "").strip()
        if not team_name:
            team_name = _txt(link)
        nickname = _txt(short) if short else ""
        slug = ""
        if link and link.get("href"):
            slug = link["href"].strip("/").split("/")[-1]
        values = [_txt(c) for c in cells[1:]]
        rec = {
            "season": season,
            "team": team_name,
            "team_nickname": nickname,
            "team_slug": slug,
            "source_url": source_url,
        }
        for col, value in zip(STANDING_COLUMNS[1:], values):
            rec[col] = value
        rows.append(rec)
    return rows


# ---------------------------------------------------------------------------
# Player statistics — https://www.nfl.com/stats/player-stats/category/...
# ---------------------------------------------------------------------------


def parse_player_stats(html: str, source_url: str, category: str, season: int | None) -> dict:
    """Parse an NFL.com player-statistics table, preserving the official headers."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return {"category": category, "season": season, "columns": [], "rows": [], "source_url": source_url}
    headers = [_txt(th) for th in table.select("thead th")]
    rows: list[dict] = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        link = cells[0].find("a")
        player = _txt(link) if link else _txt(cells[0])
        player_url = ""
        if link and (link.get("href") or "").startswith("/"):
            player_url = "https://www.nfl.com" + link["href"]
        values = [_txt(c) for c in cells[1:]]
        rec: dict = {
            "season": season,
            "category": category,
            "player": player,
            "player_url": player_url,
            "source_url": source_url,
        }
        for h, v in zip(headers[1:], values):
            rec[h] = v
        rows.append(rec)
    return {
        "category": category,
        "season": season,
        "columns": headers[1:],
        "rows": rows,
        "source_url": source_url,
    }


# ---------------------------------------------------------------------------
# Schedule / scores — https://www.nfl.com/schedules/<year>/REG<week>/
# ---------------------------------------------------------------------------


def parse_schedule(html: str, source_url: str, season: int | None, week: int | None) -> dict:
    """Parse an NFL.com weekly schedule page into game records with scores."""
    soup = BeautifulSoup(html, "lxml")
    games: list[dict] = []
    for card in soup.select("div.nfl-c-matchup-strip, div.d3-o-gamecard"):
        strip = card
        teams = strip.select("div.nfl-c-matchup-strip__team")
        if len(teams) < 2:
            continue
        def team_info(t):
            abbr = t.select_one("span.nfl-c-matchup-strip__team-abbreviation")
            name = t.select_one("a.nfl-c-matchup-strip__team-fullname")
            rec = t.select_one("div.nfl-c-matchup-strip__record")
            return {
                "abbr": _txt(abbr),
                "name": _txt(name),
                "record": _txt(rec).strip("()"),
            }
        a, b = team_info(teams[0]), team_info(teams[1])
        dt = strip.select_one("span.nfl-c-matchup-strip__date-time")
        tz = strip.select_one("span.nfl-c-matchup-strip__date-timezone")
        net = strip.select_one("p.nfl-c-matchup-strip__networks")
        scores = [s.get_text(" ", strip=True) for s in strip.select("div.nfl-c-matchup-strip__team-score, .d3-o-gamecard__score")]
        status = strip.select_one(".d3-o-gamecard__status, .nfl-c-matchup-strip__status")
        link = strip.find("a", href=re.compile(r"/games/"))
        games.append(
            {
                "season": season,
                "week": week,
                "game_date": _txt(dt),
                "game_timezone": _txt(tz),
                "network": _txt(net),
                "away_team": a["abbr"],
                "away_team_name": a["name"],
                "away_record": a["record"],
                "home_team": b["abbr"],
                "home_team_name": b["name"],
                "home_record": b["record"],
                "away_score": scores[0] if len(scores) > 0 else "",
                "home_score": scores[1] if len(scores) > 1 else "",
                "status": _txt(status),
                "game_url": ("https://www.nfl.com" + link["href"]) if link else "",
                "source_url": source_url,
            }
        )
    return {"season": season, "week": week, "games": games, "source_url": source_url}


# ---------------------------------------------------------------------------
# Club depth charts — official NFL club sites
# ---------------------------------------------------------------------------


def parse_depth_chart(html: str, source_url: str, club: str) -> dict:
    """Best-effort parse of an official club depth chart.

    Club sites differ in markup, and several return the same application shell
    for every path, so the result is only accepted when the page really
    contains a table that looks like a depth chart. Anything else yields no
    units, which the dataset builder then reports as an unresolved gap.
    """
    soup = BeautifulSoup(html, "lxml")
    page_text = _txt(soup).lower()
    if "depth" not in page_text:
        return {"club": club, "units": [], "source_url": source_url, "accepted": False,
                "reason": "the page does not identify itself as a depth chart"}
    units: list[dict] = []
    for table in soup.find_all("table"):
        headers = [_txt(th) for th in table.select("thead th")]
        body = table.select("tbody tr")
        if len(body) < 5:
            continue
        cols = len(body[0].find_all(["td", "th"]))
        if cols < 2:
            continue
        rows = []
        for tr in body:
            cells = [_txt(c) for c in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(cells)
        if len(rows) < 5:
            continue
        units.append({"headers": headers, "rows": rows, "n_rows": len(rows)})
    if not units:
        return {"club": club, "units": [], "source_url": source_url, "accepted": False,
                "reason": "no table with at least five rows was found"}
    return {"club": club, "units": units, "source_url": source_url, "accepted": True, "reason": ""}
