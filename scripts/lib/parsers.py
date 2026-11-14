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


def _schedule_competitor_blocks(card) -> list:
    """Find the per-team blocks inside a game card."""
    for selector in (
        "div.d3-o-gamecard__competitor",
        "li.d3-o-gamecard__competitor",
        "div.nfl-c-matchup-strip__team",
    ):
        blocks = card.select(selector)
        if len(blocks) >= 2:
            return blocks
    return []


def _schedule_competitor(block, is_home: bool) -> dict:
    """Extract one team's name, abbreviation, score and record from a block."""
    name = ""
    abbr = ""
    score = ""
    record = ""

    for selector in (
        "div.d3-o-gamecard__team-name",
        "span.d3-o-gamecard__team-name",
        "div.nfl-c-matchup-strip__team-fullname",
        "a.nfl-c-matchup-strip__team-fullname",
        "div.d3-o-gamecard__competitor-title",
        "span.d3-o-gamecard__team-abbreviation",
        "span.nfl-c-matchup-strip__team-abbreviation",
    ):
        node = block.select_one(selector)
        if node is None:
            continue
        text = _txt(node)
        if not text:
            continue
        if "abbreviation" in selector:
            abbr = text
        elif "fullname" in selector:
            name = name or text
        elif not name:
            name = text
    if not name:
        link = block.find("a")
        if link is not None:
            name = _txt(link)
    if not abbr and name:
        abbr = name.split()[-1] if name.split() else ""
    if not abbr:
        node = block.select_one("[class*=abbreviation]")
        if node is not None:
            abbr = _txt(node)

    for selector in (
        "div.d3-o-gamecard__score",
        "span.d3-o-gamecard__score",
        "div.nfl-c-matchup-strip__team-score",
        "span.nfl-c-matchup-strip__team-score",
    ):
        node = block.select_one(selector)
        if node is not None:
            score = _txt(node)
            break

    for selector in (
        "div.d3-o-gamecard__competitor-metadata",
        "span.d3-o-gamecard__competitor-metadata",
        "div.nfl-c-matchup-strip__record",
    ):
        node = block.select_one(selector)
        if node is not None:
            record = _txt(node).strip("()")
            break

    return {
        "name": name,
        "abbr": abbr,
        "score": score,
        "record": record,
        "is_home": is_home,
    }


def parse_schedule(html: str, source_url: str, season: int | None, week: int | None) -> dict:
    """Parse an NFL.com weekly schedule page into game records with scores.

    NFL.com renders a schedule week as a list of game cards. Two markups are
    supported: the ``d3-o-gamecard`` card and the ``nfl-c-matchup-strip``
    strip. Both carry the teams, the final score, the network and the kickoff
    time.
    """
    soup = BeautifulSoup(html, "lxml")
    games: list[dict] = []
    cards = soup.select(
        "div.d3-o-gamecard, li.d3-o-gamecard, section.d3-o-gamecard, div.nfl-c-matchup-strip"
    )
    seen: set[str] = set()
    for card in cards:
        blocks = _schedule_competitor_blocks(card)
        if len(blocks) < 2:
            continue
        competitors = []
        for block in blocks[:2]:
            classes = " ".join(block.get("class") or [])
            is_home = "--home" in classes
            competitors.append(_schedule_competitor(block, is_home))
        # The first competitor is the away team on every NFL.com layout.
        away, home = competitors[0], competitors[1]
        if "--away" in " ".join(blocks[0].get("class") or []) or "--home" in " ".join(blocks[1].get("class") or []):
            if "--home" in " ".join(blocks[0].get("class") or []):
                away, home = competitors[1], competitors[0]

        date_time = ""
        for selector in (
            "div.d3-o-gamecard__date-time",
            "span.d3-o-gamecard__date-time",
            "span.nfl-c-matchup-strip__date-time",
            "div.d3-o-gamecard__header",
        ):
            node = card.select_one(selector)
            if node is not None:
                date_time = _txt(node)
                break
        network = ""
        for selector in (
            "div.d3-o-gamecard__network",
            "span.d3-o-gamecard__network",
            "p.nfl-c-matchup-strip__networks",
            "div.nfl-c-matchup-strip__networks",
        ):
            node = card.select_one(selector)
            if node is not None:
                network = _txt(node)
                break
        status = ""
        for selector in (
            "div.d3-o-gamecard__status",
            "span.d3-o-gamecard__status",
            "div.d3-o-gamecard__header-status",
        ):
            node = card.select_one(selector)
            if node is not None:
                status = _txt(node)
                break

        link = card.find("a", href=re.compile(r"/games/"))
        game_url = ("https://www.nfl.com" + link["href"]) if link else ""
        key = (away["abbr"], home["abbr"], date_time)
        if key in seen:
            continue
        seen.add(key)
        games.append(
            {
                "season": season,
                "week": week,
                "game_date": date_time,
                "game_time": date_time,
                "game_timezone": "",
                "network": network,
                "away_team": away["abbr"],
                "away_team_name": away["name"],
                "away_record": away["record"],
                "away_score": away["score"],
                "home_team": home["abbr"],
                "home_team_name": home["name"],
                "home_record": home["record"],
                "home_score": home["score"],
                "status": status,
                "game_url": game_url,
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


# ---------------------------------------------------------------------------
# Depth-chart normalisation and depth-string resolution
# ---------------------------------------------------------------------------

#: Position groups as clubs label them, mapped to a canonical position.
POSITION_GROUPS: dict[str, str] = {
    "quarterback": "QB", "quarterbacks": "QB", "qb": "QB",
    "running back": "RB", "running backs": "RB", "rb": "RB", "halfback": "RB",
    "wide receiver": "WR", "wide receivers": "WR", "wr": "WR",
    "tight end": "TE", "tight ends": "TE", "te": "TE",
    "offensive line": "OL", "offensive lineman": "OL", "offensive linemen": "OL", "ol": "OL",
    "center": "C", "c": "C", "guard": "G", "guards": "G", "g": "G",
    "tackle": "T", "tackles": "T", "t": "T",
    "lt": "T", "rt": "T", "left tackle": "T", "right tackle": "T",
    "lg": "G", "rg": "G", "left guard": "G", "right guard": "G",
    "defensive line": "DL", "defensive lineman": "DL", "defensive linemen": "DL", "dl": "DL",
    "defensive end": "DE", "defensive ends": "DE", "de": "DE",
    "defensive tackle": "DT", "defensive tackles": "DT", "dt": "DT",
    "nose tackle": "NT", "nt": "NT",
    "linebacker": "LB", "linebackers": "LB", "lb": "LB",
    "outside linebacker": "OLB", "olb": "OLB",
    "inside linebacker": "ILB", "ilb": "ILB",
    "cornerback": "CB", "cornerbacks": "CB", "cb": "CB",
    "safety": "S", "safeties": "S", "s": "S",
    "strong safety": "SS", "ss": "SS",
    "free safety": "FS", "fs": "FS",
    "kicker": "K", "k": "K",
    "punter": "P", "p": "P",
    "long snapper": "LS", "ls": "LS",
    "returner": "RS", "return specialist": "RS",
    "pr": "PR", "kr": "KR", "nb": "NB", "rb/fb": "FB", "de/edge": "DE",
    "offense": "OFF", "offense": "OFF", "defense": "DEF",
    "fullback": "FB", "fb": "FB",
    "running back/fullback": "RB/FB", "fb/rb": "FB",
}

_ORDINAL_RE = re.compile(r"^\s*(\d{1,2})\s*[\.\)]?\s+(.+)$")


def _is_position_label(text: str) -> bool:
    key = text.strip().lower()
    return key in POSITION_GROUPS


_ORDINAL_WORDS = {
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6, "7th": 7,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
}


def _depth_ordinals(headers: list[str]) -> dict[int, int] | None:
    """Map column index to depth ordinal when the table headers declare one.

    Official club depth charts label their columns ``1st``, ``2nd``, ``3rd``
    and so on. When the header row says that, the depth order is read from the
    header rather than inferred from the order of the rows.
    """
    if not headers:
        return None
    if headers[0].strip().lower() not in ("position", "pos"):
        return None
    ordinals: dict[int, int] = {}
    for index, header in enumerate(headers[1:], start=1):
        key = header.strip().lower()
        if key in _ORDINAL_WORDS:
            ordinals[index] = _ORDINAL_WORDS[key]
    if not ordinals:
        return None
    return ordinals


def normalise_depth_groups(units: list[dict]) -> list[dict]:
    """Turn parsed depth-chart tables into ordered position groups.

    Two layouts are supported:

    * The club's own layout, where the table header declares the depth
      columns (``Position | 1st | 2nd | 3rd``). The depth of each player is
      then read from the header, which is the club's published ordering.
    * A plain two-column layout, where the position label is in the first
      column and the players follow in depth order. Here the order of the
      cells is the depth.

    Either way a group is a position label plus its players in depth order,
    and the order is what makes a depth string meaningful.
    """
    groups: list[dict] = []
    for unit in units:
        rows = unit.get("rows", [])
        if not rows:
            continue
        ordinals = _depth_ordinals(unit.get("headers", []))
        if ordinals:
            for row in rows:
                if not row:
                    continue
                label = row[0].strip()
                if not label:
                    continue
                position = POSITION_GROUPS.get(label.lower(), label.upper())
                group = {"position": position, "label": label, "players": []}
                for index, cell in enumerate(row[1:], start=1):
                    text = cell.strip()
                    if not text:
                        continue
                    match = _ORDINAL_RE.match(text)
                    name = match.group(2).strip() if match else text
                    ordinal = ordinals.get(index)
                    if ordinal is None:
                        ordinal = len(group["players"]) + 1
                    group["players"].append({"name": name, "ordinal": ordinal})
                groups.append(group)
            continue

        # Fall back to reading the table row by row, which suits clubs that
        # print the position label in the first cell and the players beside it.
        labelled = [r for r in rows if r and _is_position_label(r[0].strip())]
        if labelled and len(labelled) * 2 >= len(rows):
            for row in rows:
                if not row:
                    continue
                label = row[0].strip()
                if not label or not _is_position_label(label):
                    continue
                group = {
                    "position": POSITION_GROUPS.get(label.lower(), label.upper()),
                    "label": label,
                    "players": [],
                }
                for cell in row[1:]:
                    text = cell.strip()
                    if not text:
                        continue
                    match = _ORDINAL_RE.match(text)
                    group["players"].append(
                        {
                            "name": match.group(2).strip() if match else text,
                            "ordinal": int(match.group(1)) if match else None,
                        }
                    )
                groups.append(group)
            continue

        # Fall back to reading the table column by column, which suits clubs
        # that print the offence and the defence side by side.
        width = max(len(r) for r in rows)
        for column in range(width):
            current: dict | None = None
            for row in rows:
                if column >= len(row):
                    continue
                text = row[column].strip()
                if not text:
                    continue
                if _is_position_label(text):
                    label = text.lower()
                    current = {
                        "position": POSITION_GROUPS.get(label, label.upper()),
                        "label": text,
                        "players": [],
                    }
                    groups.append(current)
                    continue
                if current is None:
                    continue
                match = _ORDINAL_RE.match(text)
                current["players"].append(
                    {
                        "name": match.group(2).strip() if match else text,
                        "ordinal": int(match.group(1)) if match else None,
                    }
                )
    # Fill in ordinals where the club did not number them.
    for group in groups:
        for index, player in enumerate(group["players"], start=1):
            if player["ordinal"] is None:
                player["ordinal"] = index
    return groups


def resolve_depth_string(groups: list[dict], player_name: str, position: str = "") -> str:
    """Return the depth string of a player, for example ``WR3``.

    Returns an empty string when the player cannot be located in an official
    depth chart. It is never guessed.
    """
    target = re.sub(r"[^a-z ]", "", (player_name or "").lower()).strip()
    if not target:
        return ""
    last = target.split()[-1] if target.split() else ""
    for group in groups:
        if position and group["position"] != position.upper():
            continue
        for player in group["players"]:
            name = re.sub(r"[^a-z ]", "", player["name"].lower()).strip()
            if not name:
                continue
            if name == target or (last and last == name.split()[-1] and name.split()[-1] == last):
                ordinal = player.get("ordinal")
                if ordinal:
                    return f"{group['position']}{ordinal}"
    return ""
