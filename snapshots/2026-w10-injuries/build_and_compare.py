#!/usr/bin/env python3
"""Validate the Week 10 official-injury transcription, hash it, and compare it
field by field with the published hub table (hub/injuries.html).

Inputs : snapshots/2026-w10-injuries/official_transcription.psv   (hand transcription of the live page)
         hub/injuries.html                                          (published table)
Outputs: snapshots/2026-w10-injuries/official_rows.csv
         snapshots/2026-w10-injuries/compare_hub.csv
         snapshots/2026-w10-injuries/summary.json
Run from the repository root:  python3 snapshots/2026-w10-injuries/build_and_compare.py
"""
import csv
import hashlib
import html
import json
import re
from collections import Counter, OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PSV = HERE / "official_transcription.psv"
HUB = ROOT / "hub" / "injuries.html"
SOURCE_URL = "https://www.nfl.com/injuries/"
SOURCE_TITLE = "Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season | NFL.com"

# Kickoff labels exactly as printed on the official page (ET). Game order follows the page.
KICKOFF = OrderedDict([
    ("WAS @ NYG", "Thu 2026-11-12 8:15 PM ET, Prime Video"),
    ("NE @ DET", "Sun 2026-11-15 9:30 AM ET, FOX / FOX Deportes (Munich)"),
    ("KC @ ATL", "Sun 2026-11-15 1:00 PM ET, CBS"),
    ("MIN @ GB", "Sun 2026-11-15 1:00 PM ET, FOX"),
    ("JAX @ TEN", "Sun 2026-11-15 1:00 PM ET, FOX"),
    ("BUF @ NYJ", "Sun 2026-11-15 1:00 PM ET, CBS"),
    ("MIA @ IND", "Sun 2026-11-15 1:00 PM ET, CBS"),
    ("CAR @ NO", "Sun 2026-11-15 1:00 PM ET, FOX"),
    ("HOU @ CLE", "Sun 2026-11-15 1:00 PM ET, FOX"),
    ("LAR @ AZ", "Sun 2026-11-15 4:05 PM ET, CBS"),
    ("SEA @ LV", "Sun 2026-11-15 4:05 PM ET, CBS"),
    ("SF @ DAL", "Sun 2026-11-15 4:25 PM ET, FOX / FOX Deportes"),
    ("PIT @ CIN", "Sun 2026-11-15 8:20 PM ET, NBC / UNIVERSO"),
    ("LAC @ BAL", "Mon 2026-11-16 8:15 PM ET, ESPN / ABC / ESPN2 / ESPN Deportes"),
])
HUB_GAME = {k: k.replace(" @ ", "@") for k in KICKOFF}


def load_official():
    raw = PSV.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    header = lines[0].split("|")
    assert header == ["game", "team", "record", "player", "position", "injury", "practice", "game_status"], header
    rows, problems = [], []
    for i, line in enumerate(lines[1:], start=2):
        f = line.split("|")
        if len(f) != 8:
            problems.append(f"line {i}: expected 8 fields, got {len(f)}")
            continue
        rec = dict(zip(header, f))
        if rec["game"] not in KICKOFF:
            problems.append(f"line {i}: unknown game {rec['game']}")
        if rec["practice"] == "":
            problems.append(f"line {i}: blank practice status for {rec['player']}")
        rows.append(rec)
    return raw, rows, problems


def load_hub():
    t = HUB.read_text(encoding="utf-8")
    out = []
    for r in re.findall(r"<tr>(.*?)</tr>", t, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(cells) == 11 and re.match(r"\d{4}-\d{2}-\d{2}", cells[1]):
            out.append({
                "game": cells[2], "team": cells[3], "player": cells[5], "position": cells[6],
                "injury": cells[7], "practice": cells[8], "game_status": "" if cells[9] == "no designation" else cells[9],
            })
    return out


def key(team, player):
    return (team, player)


def main():
    raw, off, problems = load_official()
    hub = load_hub()
    sha_raw = hashlib.sha256(raw).hexdigest()

    # ---- official side summary
    per_game = Counter(r["game"] for r in off)
    per_team = Counter(r["team"] for r in off)
    status = Counter(r["game_status"] or "(blank)" for r in off)
    practice = Counter(r["practice"] for r in off)
    dup_keys = [k for k, v in Counter(key(r["team"], r["player"]) for r in off).items() if v > 1]

    # ---- write normalized official CSV (one row per player, source column on every row)
    with open(HERE / "official_rows.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["game", "kickoff_et_tv", "team", "team_record", "player", "position",
                    "injury", "practice_status", "game_status", "source_url"])
        for r in off:
            w.writerow([r["game"], KICKOFF.get(r["game"], ""), r["team"], r["record"], r["player"],
                        r["position"], r["injury"], r["practice"], r["game_status"], SOURCE_URL])

    # ---- compare with hub
    off_idx = {key(r["team"], r["player"]): r for r in off}
    hub_idx = {}
    hub_dups = []
    for h in hub:
        k = key(h["team"], h["player"])
        if k in hub_idx:
            hub_dups.append(k)
        hub_idx[k] = h
    rows = []
    fields = ["injury", "practice", "game_status", "position", "game"]
    off_game_key = {}
    for r in off:
        off_game_key[key(r["team"], r["player"])] = r["game"]
    counts = Counter()
    for k in list(off_idx) + [k for k in hub_idx if k not in off_idx]:
        o = off_idx.get(k)
        h = hub_idx.get(k)
        if o and not h:
            status_s = "OFFICIAL_ONLY"
        elif h and not o:
            status_s = "HUB_ONLY"
        else:
            diffs = []
            for f in fields:
                ov = {"injury": o["injury"] if o else "", "practice": o["practice"] if o else "",
                      "game_status": o["game_status"] if o else "", "position": o["position"] if o else "",
                      "game": (o["game"].replace(" ", "")) if o else ""}[f]
                hv = {"injury": h["injury"] if h else "", "practice": h["practice"] if h else "",
                      "game_status": h["game_status"] if h else "", "position": h["position"] if h else "",
                      "game": (h["game"]) if h else ""}[f]
                if f == "game":
                    # hub writes "NE@DET"; compare with official label without spaces
                    if ov != hv:
                        diffs.append(f"{f}: hub={hv!r} official={ov!r}")
                elif ov != hv:
                    diffs.append(f"{f}: hub={hv!r} official={ov!r}")
            status_s = "MATCH" if not diffs else "DIFF"
        counts[status_s] += 1
        team, player = k
        rows.append([status_s, team, player,
                     (o or {}).get("game", ""), (h or {}).get("game", ""),
                     "; ".join(diffs) if (o and h and status_s == "DIFF") else ""])
    # Recompute diffs string for DIFF rows (kept simple above)
    with open(HERE / "compare_hub.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["result", "team", "player", "official_game", "hub_game", "field_differences"])
        w.writerows(rows)

    summary = OrderedDict([
        ("official_source", SOURCE_URL),
        ("official_title", SOURCE_TITLE),
        ("transcription_file", PSV.name),
        ("transcription_sha256", sha_raw),
        ("transcription_bytes", len(raw)),
        ("official_rows", len(off)),
        ("official_games", len(per_game)),
        ("official_clubs", len(per_team)),
        ("official_rows_per_team", dict(sorted(per_team.items()))),
        ("official_status_counts", dict(status)),
        ("official_practice_counts", dict(practice)),
        ("official_duplicate_team_player", dup_keys),
        ("validation_problems", problems),
        ("hub_rows_parsed", len(hub)),
        ("hub_duplicate_team_player", hub_dups),
        ("compare_counts", dict(counts)),
    ])
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
