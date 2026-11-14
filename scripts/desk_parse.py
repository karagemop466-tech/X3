#!/usr/bin/env python3
"""Parse captured official NFL pages into source-linked datasets.

Inputs : capture/            raw HTML captured by scripts/desk_capture.py
Outputs: data/desk/games.json      2026 regular-season schedule + results (W1-W11)
         data/desk/standings.json  2026 league standings
         data/desk/injuries.json   official injury reports, weeks 8-11
         data/desk/depth.json      32 club depth charts with string order
         data/desk/parse_report.json  per-page counts and every parse problem

Parsing rules
  * a value is written only when it was read from the captured page
  * missing cells stay empty (never guessed, never carried over)
  * every row keeps the official URL it came from
  * a row that cannot be parsed is reported, not silently dropped
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from desk_extract import text_of
from desk_parse_meta import (CLUB_DEPTH, FULL_NAME, INJURY_URL, NFL, NICKNAME,
                             SCHEDULE_URL, STANDINGS_URL)

PROBLEMS: list[dict] = []


def problem(page: str, msg: str, detail: str = "") -> None:
    PROBLEMS.append({"page": page, "problem": msg, "detail": detail[:400]})


# --------------------------------------------------------------------------- #
# 1. Schedule page: completed games and scheduled games                        #
# --------------------------------------------------------------------------- #
FINAL_RE = re.compile(
    r"^([A-Za-z0-9.&' ]+?) (\d{1,3}), ([A-Za-z0-9.&' ]+?) (\d{1,3}), FINAL, "
    r"([A-Za-z]+), ([A-Za-z]+ \d{1,2})(?:st|nd|rd|th)(?:.*)$")
SCHED_RE = re.compile(
    r"^([A-Za-z0-9.&' ]+?) at ([A-Za-z0-9.&' ]+), ([A-Za-z]+), "
    r"([A-Za-z]+ \d{1,2})(?:st|nd|rd|th), (\d{1,2}:\d{2} [AP]M), ([A-Za-z0-9 ,]+?)(?:\s+Tickets.*)?$")
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


def iso_date(month_name: str, day_text: str, season: int = 2026) -> str:
    """Date from the page text; a January date belongs to the following year."""
    month = MONTHS.get(month_name)
    if not month:
        return ""
    day = int(re.sub(r"\D", "", day_text))
    year = season + 1 if month <= 2 else season
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_schedule(page: str, raw: str) -> list[dict]:
    wm = re.search(r"-w(\d+)$", page)
    if not wm:
        problem(page, "page name does not contain a week number")
        return []
    week = int(wm.group(1))
    src = SCHEDULE_URL.format(week)
    rows: list[dict] = []
    for line in text_of(raw).splitlines():
        m = FINAL_RE.match(line)
        if m is not None:
            away, ascore, home, hscore, _day, date_text = m.groups()
            rows.append({
                "week": week, "away": NICKNAME.get(away, ""), "home": NICKNAME.get(home, ""),
                "away_name": away, "home_name": home,
                "away_score": int(ascore), "home_score": int(hscore),
                "status": "FINAL", "date_text": date_text,
                "date_iso": iso_date(date_text.split()[0], date_text),
                "kickoff_et": "", "network": "", "neutral_site": False, "neutral_site_name": "", "source": src,
            })
            if not rows[-1]["away"] or not rows[-1]["home"]:
                problem(page, "club not mapped to an abbreviation", line)
            continue
        m = SCHED_RE.match(line)
        if m:
            away, home, _day, date_text, kickoff, network = m.groups()
            rows.append({
                "week": week, "away": NICKNAME.get(away, ""), "home": NICKNAME.get(home, ""),
                "away_name": away, "home_name": home,
                "away_score": None, "home_score": None, "status": "SCHEDULED",
                "date_text": date_text, "date_iso": iso_date(date_text.split()[0], date_text),
                "kickoff_et": kickoff, "network": network.strip(), "neutral_site": False, "neutral_site_name": "",
                "source": src,
            })
            if not rows[-1]["away"] or not rows[-1]["home"]:
                problem(page, "club not mapped to an abbreviation", line)
    # Neutral-site (international) games: the page prints an "International Game" banner and a
    # host city immediately before that game's line. A city name alone is ambiguous, so a match
    # requires the banner; the city is recorded as published, not interpreted.
    lines = text_of(raw).splitlines()
    HOST_CITIES = {"MUNICH", "MADRID", "LONDON", "SAO PAULO", "MELBOURNE", "DUBLIN", "PARIS",
                   "FRANKFURT", "MEXICO CITY", "TORONTO", "RIO DE JANEIRO", "BERLIN", "TOKYO", "EAST MELBOURNE"}
    for idx, line in enumerate(lines):
        m2 = FINAL_RE.match(line) or SCHED_RE.match(line)
        if not m2:
            continue
        back = lines[max(0, idx - 4):idx]
        if not any("International Game" in b for b in back):
            continue
        city = next((b.strip() for b in reversed(back) if b.strip().upper() in HOST_CITIES), "")
        home_name = m2.group(3) if m2.re is FINAL_RE else m2.group(2)
        for r in rows:
            if r["away_name"] == m2.group(1) and r["home_name"] == home_name:
                r["neutral_site"] = True
                r["neutral_site_name"] = city
    seen, unique = set(), []
    for r in rows:
        key = (r["away"], r["home"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    if not unique:
        problem(page, "no games parsed")
    return unique


# --------------------------------------------------------------------------- #
# 2. Standings                                                                 #
# --------------------------------------------------------------------------- #
RECORD_RE = re.compile(r"(\d+) - (\d+) - (\d+)")
NUM_RE = re.compile(r"^-?\d+\.\d{3}$")


def parse_standings(page: str, raw: str) -> list[dict]:
    lines = text_of(raw).splitlines()
    rows, i = [], 0
    names = {v: k for k, v in FULL_NAME.items()}
    while i < len(lines) - 2:
        name = lines[i].strip()
        if name in names and lines[i + 1].strip() == name.split()[-1]:
            data = lines[i + 2].strip()
            parts = data.split()
            if len(parts) >= 7 and parts[0].isdigit():
                recs = RECORD_RE.findall(data)
                pcts = [p for p in parts if NUM_RE.match(p)]
                rows.append({
                    "abbr": names[name], "name": name,
                    "w": int(parts[0]), "l": int(parts[1]), "t": int(parts[2]),
                    "pct": parts[3], "pf": int(parts[4]), "pa": int(parts[5]),
                    "net": int(parts[6]),
                    "home": "-".join(recs[0]) if len(recs) > 0 else "",
                    "road": "-".join(recs[1]) if len(recs) > 1 else "",
                    "div": "-".join(recs[2]) if len(recs) > 2 else "",
                    "div_pct": pcts[1] if len(pcts) > 1 else "",
                    "conf": "-".join(recs[3]) if len(recs) > 3 else "",
                    "conf_pct": pcts[2] if len(pcts) > 2 else "",
                    "nonconf": "-".join(recs[4]) if len(recs) > 4 else "",
                    "strk": parts[-2] if re.fullmatch(r"\d+[WL]", parts[-2]) else "",
                    "last5": "-".join(recs[-1]) if recs else "",
                    "source": STANDINGS_URL,
                })
            i += 3
            continue
        i += 1
    if len(rows) != 32:
        problem(page, f"expected 32 standings rows, parsed {len(rows)}")
    return rows


# --------------------------------------------------------------------------- #
# 3. Injury reports                                                            #
# --------------------------------------------------------------------------- #
TABLE_RE = re.compile(r"(<table\b.*?</table>)", re.S)
TITLE_RE = re.compile(r'<div class="nfl-t-stats__title">.*?</div></div>', re.S)
CELL_RE = re.compile(r"<tr><td\b[^>]*>(.*?)</td><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>", re.S)
LINK_RE = re.compile(r'<a href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', re.S)
PRACTICE = {"Full Participation in Practice", "Limited Participation in Practice",
            "Did Not Participate In Practice", "Not Listed"}
GAME_STATUS = {"Out", "Doubtful", "Questionable", ""}


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def parse_injuries(page: str, raw: str, week: int) -> tuple[list[dict], dict]:
    src = INJURY_URL.format(week)
    rows: list[dict] = []
    current = ""
    for m in re.finditer(r'<div class="nfl-t-stats__title">(.*?)</div></div>|<table\b.*?</table>', raw, re.S):
        chunk = m.group(0)
        if chunk.startswith("<div"):
            label = clean(chunk).split()[-1] if clean(chunk) else ""
            if label in NICKNAME:
                current = NICKNAME[label]
            else:
                problem(page, "team header not recognised", clean(chunk)[:80])
            continue
        if not current:
            problem(page, "player table with no team header")
            continue
        if "<th>Player</th>" not in chunk:
            continue
        for cm in CELL_RE.finditer(chunk):
            cells = [clean(c) for c in cm.groups()]
            name_cell = cm.group(1)
            link = LINK_RE.search(name_cell)
            player = cells[0]
            href = link.group(1) if link else ""
            injury, practice, status = cells[2], cells[3], cells[4]
            player_url = (NFL + href) if href.startswith("/players/") else ""
            rows.append({
                "team": current, "week": week, "player": player,
                "player_url": player_url, "pos": cells[1], "injury": injury,
                "practice": practice, "status": status, "source": src,
            })
            if injury and injury not in ("",) and len(injury) > 60:
                problem(page, "suspicious injury cell", injury)
            if practice and practice not in PRACTICE:
                problem(page, "unrecognised practice value", practice)
            if status and status not in GAME_STATUS:
                problem(page, "unrecognised game status", status)
    if not rows:
        problem(page, "no injury rows parsed")
    stats = {
        "week": week, "rows": len(rows),
        "teams": len({r["team"] for r in rows}),
        "out": sum(r["status"] == "Out" for r in rows),
        "doubtful": sum(r["status"] == "Doubtful" for r in rows),
        "questionable": sum(r["status"] == "Questionable" for r in rows),
        "no_status": sum(r["status"] == "" for r in rows),
        "url": src,
    }
    return rows, stats


# --------------------------------------------------------------------------- #
# 4. Club depth charts                                                         #
# --------------------------------------------------------------------------- #
CAPTION_RE = re.compile(r"<caption[^>]*>(.*?)</caption>", re.S)
TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
DROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
UNOFFICIAL_RE = re.compile(r"unofficial", re.I)
ASOF_RE = re.compile(r"(?:as of|updated)\s*[:\-]?\s*([A-Z][a-z]+ \d{1,2},? \d{4}|[A-Z][a-z]+ \d{1,2})", re.I)


def parse_depth(page: str, raw: str, abbr: str) -> dict:
    text = text_of(raw)
    out = {"abbr": abbr, "url": CLUB_DEPTH.get(abbr, ""), "units": [],
           "labels_unofficial": bool(UNOFFICIAL_RE.search(text[:6000])),
           "as_of_text": "", "rows": 0}
    m = ASOF_RE.search(text)
    if m:
        out["as_of_text"] = m.group(1)
    for tm in re.finditer(r"<table\b.*?</table>", raw, re.S):
        table = tm.group(0)
        cm = CAPTION_RE.search(table)
        caption = clean(cm.group(1)) if cm else ""
        ths = [clean(t) for t in TH_RE.findall(table)[:6]]
        if not any(t.lower().startswith(("first", "1st", "starter")) for t in ths):
            if "Position" not in ths:
                continue
        unit = caption or ("Offense" if not out["units"] else "Unknown")
        slots = []
        for rm in DROW_RE.finditer(table):
            cells = TD_RE.findall(rm.group(1))
            if len(cells) < 2:
                continue
            pos = clean(cells[0])
            if not pos or len(pos) > 12:
                continue
            tiers = []
            for cell in cells[1:]:
                names = [clean(a) for a in re.findall(r"<a\b[^>]*>(.*?)</a>", cell, re.S)]
                if not names:
                    txt = clean(cell)
                    # some clubs prefix the jersey number inside the cell: "44 Zaire Franklin"
                    txt = re.sub(r"^#?\d{1,2}\s+", "", txt)
                    names = [txt] if txt else []
                tiers.append(names)
            while tiers and not tiers[-1]:
                tiers.pop()
            if not any(tiers):
                continue
            slots.append({"pos": pos, "tiers": tiers})
        if slots:
            out["units"].append({"unit": unit, "headers": ths, "slots": slots})
            out["rows"] += sum(len(s["tiers"]) for s in slots)
    if not out["units"]:
        problem(page, "no depth-chart tables parsed", f"{abbr} {out['url']}")
    return out


# --------------------------------------------------------------------------- #
def main(src: str, dst: str) -> int:
    cap, out = Path(src), Path(dst)
    out.mkdir(parents=True, exist_ok=True)
    games, standings, injuries, depth = [], [], [], []
    inj_stats = []

    for w in range(1, 12):
        f = cap / f"schedule-w{w}.html"
        if not f.exists():
            problem(f"schedule-w{w}", "page not captured")
            continue
        games += parse_schedule(f"schedule-w{w}", f.read_text(errors="replace"))
    f = cap / "standings-2026.html"
    if f.exists():
        standings = parse_standings("standings-2026", f.read_text(errors="replace"))
    for w in (8, 9, 10, 11):
        f = cap / f"injuries-w{w}.html"
        if not f.exists():
            problem(f"injuries-w{w}", "page not captured")
            continue
        rows, st = parse_injuries(f"injuries-w{w}", f.read_text(errors="replace"), w)
        injuries += rows
        inj_stats.append(st)
    for abbr, url in sorted(CLUB_DEPTH.items()):
        f = cap / f"depth-{abbr}.html"
        if not f.exists():
            problem(f"depth-{abbr}", "page not captured", url)
            continue
        depth.append(parse_depth(f"depth-{abbr}", f.read_text(errors="replace"), abbr))

    # Guard against NFL.com serving the current week's report for a future week.
    sig = {}
    for w in inj_stats:
        rows_w = [r for r in injuries if r["week"] == w["week"]]
        sig[w["week"]] = tuple(sorted((r["team"], r["player"], r["status"]) for r in rows_w))
    dup_weeks = []
    weeks_sorted = sorted(sig)
    for i, w in enumerate(weeks_sorted[:-1]):
        for later in weeks_sorted[i + 1:]:
            if sig[w] == sig[later] and sig[w]:
                dup_weeks.append(later)
    if dup_weeks:
        keep = min(dup_weeks)
        drop = set(dup_weeks) - {keep}
        injuries = [r for r in injuries if r["week"] not in drop]
        inj_stats = [w for w in inj_stats if w["week"] not in drop]
        for w in dup_weeks:
            problem(f"injuries-w{w}", "identical to an earlier week's report; dropped as a "
                                     "duplicate served for a future week")

    final = [g for g in games if g["status"] == "FINAL"]
    (out / "games.json").write_text(json.dumps({
        "season": 2026, "source_note": "Parsed from official NFL.com week schedule pages",
        "games": games,
        "counts": {"total": len(games), "final": len(final),
                   "scheduled": len(games) - len(final)},
    }, indent=1) + "\n")
    (out / "standings.json").write_text(json.dumps({
        "season": 2026, "url": STANDINGS_URL, "rows": standings}, indent=1) + "\n")
    (out / "injuries.json").write_text(json.dumps({
        "season": 2026, "weeks": inj_stats, "rows": injuries}, indent=1) + "\n")
    (out / "depth.json").write_text(json.dumps({
        "captured": "2026-11-14",
        "note": "Club depth charts are published by each club; most are labelled unofficial by the club.",
        "clubs": depth}, indent=1) + "\n")
    (out / "parse_report.json").write_text(json.dumps({
        "problems": PROBLEMS,
        "problem_count": len(PROBLEMS),
        "game_counts": {"total": len(games), "final": len(final)},
        "standings_rows": len(standings),
        "injury_weeks": inj_stats,
        "depth_clubs": len(depth),
        "depth_rows": {d["abbr"]: d["rows"] for d in depth},
    }, indent=1) + "\n")
    print(json.dumps({"problems": len(PROBLEMS), "games": len(games),
                      "final": len(final), "standings": len(standings),
                      "injuries": len(injuries), "depth_clubs": len(depth)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
