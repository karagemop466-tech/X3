#!/usr/bin/env python3
"""
Week-11 2026 NFL injury report - structured transcription of the scheduled
availability capture, plus the Week-10 -> Week-11 delta.

Inputs (read-only):
  readiness/data/history/2026-11-19/league-injury-report.html
      The official report as captured by .github/workflows/availability-snapshots.yml
      at 2026-11-19T02:16:10Z (URL https://www.nfl.com/injuries/, HTTP 200,
      373,969 bytes). The exact bytes are pinned below; if the capture is
      re-taken, this pin must be updated deliberately, never silently.
  data/desk/injuries.json
      The repository's canonical store of the Week-8/9/10 report rows (as
      captured by the desk pipeline). Used ONLY as the delta baseline.

Outputs:
  data/week11/reg11_2026-11-19.csv        one row per published player row
  data/week11/reg11_2026-11-19_delta.csv  week-10 -> week-11 transitions

Cross-check (recorded in data/week11/reg11_2026-11-19.md): a live read of the
canonical deep link https://www.nfl.com/injuries/league/2026/reg11 (2026-11-19,
~07:35Z, fetch tool, all chunks) contains the same 26 club sections in the same
order, the same 253 rows, and the same 16 designations (9 Out, 7 Questionable,
0 Doubtful). Zero row-level mismatches on position/injuries/practice/game.

Method notes:
  * Tables are parsed from the raw HTML with a stdlib parser; nothing is
    transcribed by eye. player_url is the /players/... href on the page.
  * Club full names are mapped to codes (49ers -> SF, ...). Club codes are
    normalised for the delta join only (ARI->AZ, LA->LAR); the CSV keeps the
    page's own full name and the code applied is stated per row.
  * Bengals and Commanders sections render the page's explicit
    "No Injuries Reported" empty state (no table). They are recorded in the
    summary with 0 rows - absence of a table is NOT absence from the page.
  * Delta keys on (club_code, player). A trade shows up as one drop + one add;
    the delta never moves a player between clubs silently.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
from collections import Counter

ROOT = __file__.rsplit("/", 2)[0]
CAPTURE_REL = "readiness/data/history/2026-11-19/league-injury-report.html"
CAPTURE_SHA256 = "d00b606b59242871a56455d762e338ad9a3192596a5da1a557e9666247b3448e"
CAPTURE_URL = "https://www.nfl.com/injuries/"
CANONICAL_URL = "https://www.nfl.com/injuries/league/2026/reg11"
CAPTURED_AT = "2026-11-19T02:16:10+00:00"
CAPTURE_ID = "SNAP-2026-11-19T0216Z-WEEK11-LEAGUE-INJURY-REPORT"
DESK = "data/desk/injuries.json"
OUT_CSV = "data/week11/reg11_2026-11-19.csv"
OUT_DELTA = "data/week11/reg11_2026-11-19_delta.csv"

CLUB_CODE = {
    "Colts": "IND", "Texans": "HOU", "Steelers": "PIT", "Eagles": "PHI",
    "Cardinals": "AZ", "Chiefs": "KC", "Ravens": "BAL", "Panthers": "CAR",
    "Buccaneers": "TB", "Lions": "DET", "Dolphins": "MIA", "Bills": "BUF",
    "Titans": "TEN", "Cowboys": "DAL", "Saints": "NO", "Bears": "CHI",
    "Jets": "NYJ", "Chargers": "LAC", "Jaguars": "JAX", "Giants": "NYG",
    "Raiders": "LV", "Broncos": "DEN", "Vikings": "MIN", "49ers": "SF",
    "Bengals": "CIN", "Commanders": "WAS",
}
ALIAS = {"ARI": "AZ", "LA": "LAR"}


def norm_team(t: str) -> str:
    return ALIAS.get(t, t)


def parse(s: str):
    """Return (sections, errors). sections: list of dicts with club + rows."""
    errors = []
    # club sections in document order, each ending at the next subtitle or the NEWS carousel
    sub_pat = re.compile(r'<div class="d3-o-section-sub-title"><span>([^<]+)</span></div>')
    marks = [m.start() for m in sub_pat.finditer(s)]
    names = [html.unescape(m.group(1)).strip() for m in sub_pat.finditer(s)]
    carousel = s.find('<section class="d3-l-grid--outer d3-l-section-row"><div class="d3-l-grid--i" data-require="modules/carousel"')
    region_end = carousel if carousel != -1 else len(s)
    sections = []
    for i, (pos, club) in enumerate(zip(marks, names)):
        end = marks[i + 1] if i + 1 < len(marks) else region_end
        seg = s[pos:end]
        tm = re.search(r"<table[^>]*>(.*?)</table>", seg, re.S)
        if tm is None:
            if "No Injuries Reported" not in seg:
                errors.append(f"{club}: no table and no explicit empty state - page structure drifted")
            sections.append({"club": club, "code": CLUB_CODE[club], "empty": True, "rows": []})
            continue
        tbody = re.search(r"<tbody>(.*?)</tbody>", tm.group(1), re.S)
        if tbody is None:
            errors.append(f"{club}: table without tbody")
            continue
        rows = []
        for tr in re.finditer(r"<tr>(.*?)</tr>", tbody.group(1), re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", tr.group(1), re.S)
            if len(cells) != 5:
                errors.append(f"{club}: row with {len(cells)} cells (expected 5)")
                continue
            link = re.search(r'href="(/players/[^"]+)"', cells[0])
            clean = []
            for c in cells:
                t = re.sub(r"<[^>]+>", "", c)
                t = html.unescape(t).strip()
                t = re.sub(r"\s+", " ", t)
                clean.append(t)
            rows.append({"player": clean[0], "pos": clean[1], "injury": clean[2],
                         "practice": clean[3], "status": clean[4],
                         "player_url": "https://www.nfl.com" + link.group(1) if link else ""})
        sections.append({"club": club, "code": CLUB_CODE[club], "empty": False, "rows": rows})
    return sections, errors


def main() -> int:
    raw = open(f"{ROOT}/{CAPTURE_REL}", "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CAPTURE_SHA256:
        print(f"FAIL: capture sha256 {digest} != pinned {CAPTURE_SHA256}")
        return 1
    s = raw.decode("utf-8", errors="replace")
    sections, errors = parse(s)

    # --- invariants: the page's structure, stated exactly --------------------
    if len(sections) != 26:
        errors.append(f"expected 26 club sections, parsed {len(sections)}")
    empties = [x["club"] for x in sections if x["empty"]]
    if empties != ["Bengals", "Commanders"]:
        errors.append(f"explicit empty states are Bengals/Commanders in this capture; parsed {empties}")
    all_rows = [(sec, r) for sec in sections for r in sec["rows"]]
    if len(all_rows) != 253:
        errors.append(f"expected 253 player rows, parsed {len(all_rows)}")
    desig = Counter(r["status"] for sec, r in all_rows if r["status"])
    if desig != Counter({"Out": 9, "Questionable": 7}):
        errors.append(f"game-status designations drifted: {dict(desig)}")

    # --- write the transcription ---------------------------------------------
    with open(f"{ROOT}/{OUT_CSV}", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["club_code", "club", "player", "position", "injury", "practice_status",
                    "game_status", "player_url", "source_url", "canonical_url",
                    "capture_id", "captured_at_utc", "capture_sha256"])
        for sec in sections:
            for r in sec["rows"]:
                w.writerow([sec["code"], sec["club"], r["player"], r["pos"], r["injury"],
                            r["practice"], r["status"], r["player_url"], CAPTURE_URL,
                            CANONICAL_URL, CAPTURE_ID, CAPTURED_AT, CAPTURE_SHA256])

    # --- delta vs the desk store's week-10 rows ------------------------------
    desk = json.load(open(f"{ROOT}/{DESK}", encoding="utf-8"))
    wk10 = {}
    for r in desk["rows"]:
        if r["week"] == 10:
            wk10[(norm_team(r["team"]), r["player"])] = r
    wk11 = {}
    for sec in sections:
        for r in sec["rows"]:
            wk11[(norm_team(sec["code"]), r["player"])] = r

    delta = []
    for key in sorted(set(wk10) | set(wk11)):
        code, player = key
        a, b = wk10.get(key), wk11.get(key)
        if a and not b:
            kind = "dropped"
            delta.append([code, player, kind, a.get("practice", ""), "", a.get("status", ""), "",
                          a.get("pos", ""), b["pos"] if b else ""])
        elif b and not a:
            kind = "added"
            delta.append([code, player, kind, "", b["practice"], "", b["status"], "", b["pos"]])
        else:
            moves = []
            if a["practice"] != b["practice"]:
                moves.append(f"practice {a['practice']} -> {b['practice']}")
            if a["status"] != b["status"]:
                moves.append(f"game-status {a['status'] or '(none)'} -> {b['status'] or '(none)'}")
            if (a.get("injury") or "") != (b["injury"] or ""):
                moves.append(f"injury {a.get('injury') or '(none)'} -> {b['injury'] or '(none)'}")
            if moves:
                delta.append([code, player, "moved", a["practice"], b["practice"],
                              a["status"], b["status"], a.get("pos", ""), b["pos"],
                              "; ".join(moves)])
    with open(f"{ROOT}/{OUT_DELTA}", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["club_code", "player", "change", "practice_wk10", "practice_wk11",
                    "status_wk10", "status_wk11", "pos_wk10", "pos_wk11", "detail"])
        for row in delta:
            w.writerow(row + [""] * (10 - len(row)))

    adds = sum(1 for d in delta if d[2] == "added")
    drops = sum(1 for d in delta if d[2] == "dropped")
    moves = sum(1 for d in delta if d[2] == "moved")
    by_team = Counter(d[0] for d in delta if d[2] == "dropped")
    bye_drops = sum(v for t, v in by_team.items() if t in ("ATL", "CLE", "GB", "LAR", "NE", "SEA"))
    status_set = sum(1 for d in delta if d[2] == "moved" and not d[5] and d[6])
    status_unset = sum(1 for d in delta if d[2] == "moved" and d[5] and not d[6])
    status_chg = sum(1 for d in delta if d[2] == "moved" and d[5] and d[6] and d[5] != d[6])
    practice_moves = sum(1 for d in delta if d[2] == "moved" and d[3] != d[4])
    print(f"capture sha256 OK ({CAPTURE_SHA256[:12]}...)")
    print(f"club sections: {len(sections)} (24 with tables, 2 explicit 'No Injuries Reported': "
          f"{', '.join(empties)})")
    print(f"player rows: {len(all_rows)}; game-status designations: "
          f"{dict(desig)}; blank: {len(all_rows) - sum(desig.values())}")
    print(f"delta vs week-10 desk store: +{adds} added, -{drops} dropped, {moves} moved (rows with any change)")
    print(f"  drops in week-11 bye clubs (ATL/CLE/GB/LAR/NE/SEA): {bye_drops}; elsewhere: {drops - bye_drops}")
    print(f"  practice-status changes: {practice_moves}")
    print(f"  game-status set (''->designated): {status_set}; unset (designated->'' for the new cycle): {status_unset}; changed (both designated): {status_chg}")
    print("  note: game-status cells fall due with a new report cycle - the Sunday/Monday designations")
    print("  are not issued yet at this capture, so designated->'' is an artifact of the cycle, not an")
    print("  availability event. Treat only status set / changed pairs as real transitions.")
    if errors:
        for e in errors:
            print("FAIL", e)
        return 1
    print("PASS - invariants hold (26 sections / 253 rows / designations 9 Out + 7 Questionable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
