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


_GAME_SLUG_RE = re.compile(r"/games/([a-z0-9\-]+)-([a-z0-9]+)-at-([a-z0-9]+)-(\d{4})-reg-(\d+)")
_SCORE_RE = re.compile(r"^\d{1,3}$")
_RECORD_RE = re.compile(r"^\d{1,2}-\d{1,2}(-\d{1,2})?$")
_TIME_RE = re.compile(r"\d{1,2}:\d{2}\s*(AM|PM)", re.I)
_DATE_RE = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}", re.I
)


def _title_from_slug(word: str) -> str:
    return " ".join(part.capitalize() for part in word.split("-") if part)


def _game_cards(soup) -> list:
    """Return the game cards on an NFL.com schedule page.

    The current NFL.com schedule is rendered with utility classes that carry
    no semantics, so the cards are located structurally: every element that
    directly contains a link to a game page is a card.
    """
    cards: list = []
    seen: set[int] = set()
    for link in soup.find_all("a", href=re.compile(r"/games/")):
        node = link.parent
        if node is None or id(node) in seen:
            continue
        seen.add(id(node))
        cards.append(node)
    return cards


def _score_rows(card) -> list[dict]:
    """Extract each team's identity and score from a game card.

    A card holds one row per team. Each row carries the official club logo
    (which gives the abbreviation), a screen-reader label with the full club
    name, and the score in a ``blurrable-score`` container.
    """
    rows: list[dict] = []
    for score_node in card.select('[data-testid="blurrable-score"]'):
        row = score_node.parent
        abbr = ""
        name = ""
        img = row.find("img", src=re.compile(r"/clubs/logos/"))
        if img is not None:
            abbr = (img.get("src") or "").rsplit("/", 1)[-1].split(".")[0].upper()
        label = row.find("span", class_=re.compile(r"sr-only"))
        if label is not None:
            name = _txt(label)
        score = _txt(score_node)
        rows.append({"abbr": abbr, "name": name, "score": score})
    if rows:
        return rows

    # Fallback for a card without the score container: read the club logos.
    for img in card.find_all("img", src=re.compile(r"/clubs/logos/")):
        abbr = (img.get("src") or "").rsplit("/", 1)[-1].split(".")[0].upper()
        label = img.find_next("span", class_=re.compile(r"sr-only"))
        rows.append({"abbr": abbr, "name": _txt(label) if label else "", "score": ""})
    return rows


def _leaf_texts(node) -> list[str]:
    """Text of the deepest elements that carry content, in document order."""
    out: list[str] = []
    for element in node.find_all(True):
        if element.find(True):
            continue
        text = _txt(element)
        if text:
            out.append(text)
    return out


def parse_schedule(html: str, source_url: str, season: int | None, week: int | None) -> dict:
    """Parse an NFL.com weekly schedule page into game records with scores.

    The current NFL.com schedule markup is built from utility classes, so the
    parser works structurally: it locates each game by its link, reads the
    teams from the official club logos and their screen-reader labels, the
    scores from the official score container, the records from the win-loss
    cells, and the network from the broadcaster logo.

    Only the games belonging to the requested week are returned. The page also
    carries a by-week strip for other weeks, and mixing those in would file
    one week of games under another.
    """
    soup = BeautifulSoup(html, "lxml")
    games: list[dict] = []
    seen: set[str] = set()

    for card in _game_cards(soup):
        link = card.find("a", href=re.compile(r"/games/"))
        if link is None:
            continue
        slug_match = _GAME_SLUG_RE.search(link.get("href", ""))
        if slug_match:
            away_slug, _at, home_slug, slug_season, slug_week = slug_match.groups()
            game_week = int(slug_week)
            if week is not None and game_week != int(week):
                continue
            slug_year = int(slug_season)
            away_fallback = _title_from_slug(away_slug)
            home_fallback = _title_from_slug(home_slug)
        else:
            game_week = week
            slug_year = season
            away_fallback = ""
            home_fallback = ""

        rows = _score_rows(card)
        if len(rows) < 2:
            continue
        away, home = rows[0], rows[1]
        away_abbr = away["abbr"] or ""
        home_abbr = home["abbr"] or ""
        if not away_abbr or not home_abbr:
            continue

        texts = _leaf_texts(card)
        records = [t for t in texts if _RECORD_RE.match(t)]
        time_text = ""
        date_text = ""
        for text in texts:
            if not time_text and _TIME_RE.search(text):
                time_text = text
            if not date_text and _DATE_RE.search(text):
                date_text = text
            if time_text and date_text:
                break

        network = ""
        for img in card.find_all("img", src=re.compile(r"broadcaster")):
            alt = (img.get("alt") or "").strip()
            network = alt.replace(" network logo", "").strip().upper()
            if network:
                break

        key = f"{away_abbr}@{home_abbr}#{game_week}"
        if key in seen:
            continue
        seen.add(key)

        games.append(
            {
                "season": slug_year if slug_year else season,
                "week": game_week,
                "game_date": date_text or time_text,
                "game_time": time_text,
                "game_timezone": "",
                "network": network,
                "away_team": away_abbr,
                "away_team_name": away["name"] or away_fallback,
                "away_record": records[0] if len(records) > 0 else "",
                "away_score": away["score"],
                "home_team": home_abbr,
                "home_team_name": home["name"] or home_fallback,
                "home_record": records[1] if len(records) > 1 else "",
                "home_score": home["score"],
                "status": "",
                "game_url": "https://www.nfl.com" + link.get("href", ""),
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
