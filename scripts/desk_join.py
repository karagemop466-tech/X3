#!/usr/bin/env python3
"""Join the verified injury report to the club depth charts.

Output: data/desk/deficiencies.json

For every player on an official injury report with a game status of Out or Doubtful,
find that player on his own club's depth chart and record
  * the unit and position slot
  * his depth string (1 = first/starter, 2 = second, ...)
  * who is listed behind him
  * a *derived* replacement string: the next listed player at that slot
Where the join fails, the row says so and is flagged; nothing is inferred.

Depth charts are published by each club and most are labelled "unofficial" by the
publisher; that limitation is carried on every row and on the site.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

SUFFIX = {"jr", "sr", "ii", "iii", "iv", "v"}


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower().replace(".", " ").replace("'", "").replace("-", " ")
    parts = [p for p in re.split(r"\s+", s) if p and p not in SUFFIX]
    return " ".join(parts)


def index_depth(clubs: list[dict]) -> tuple[dict, dict]:
    """(club, normalized name) -> {unit, pos, depth, behind[], slot_size}. Positions may repeat."""
    idx: dict[tuple[str, str], list[dict]] = {}
    for c in clubs:
        for u in c["units"]:
            for slot in u["slots"]:
                for depth, tier in enumerate(slot["tiers"], start=1):
                    for name in tier:
                        idx.setdefault((c["abbr"], norm(name)), []).append({
                            "unit": u["unit"], "pos": slot["pos"], "depth": depth,
                            "behind": [n for t in slot["tiers"][depth:] for n in t],
                            "slot_size": len(slot["tiers"]),
                            "player": name,
                        })
    return idx, {c["abbr"]: c for c in clubs}


UNIT_GROUP = {
    "QB": "offense", "RB": "offense", "FB": "offense", "WR": "offense", "TE": "offense",
    "LT": "offense", "LG": "offense", "C": "offense", "RG": "offense", "RT": "offense",
    "G": "offense", "T": "offense", "OL": "offense",
    "DL": "defense", "DT": "defense", "DE": "defense", "NT": "defense", "EDGE": "defense",
    "OLB": "defense", "ILB": "defense", "LB": "defense", "CB": "defense", "S": "defense",
    "SS": "defense", "FS": "defense", "DB": "defense",
    "K": "special", "P": "special", "LS": "special", "KR": "special", "PR": "special",
    "H": "special",
}


def main(dst: str) -> int:
    base = Path(dst)
    inj = json.loads((base / "injuries.json").read_text())
    dep = json.loads((base / "depth.json").read_text())
    idx, clubs = index_depth(dep["clubs"])
    rows, misses = [], []
    for r in inj["rows"]:
        if r["status"] not in ("Out", "Doubtful"):
            continue
        key = (r["team"], norm(r["player"]))
        hits = idx.get(key, [])
        entry = {
            "week": r["week"], "team": r["team"], "player": r["player"], "pos": r["pos"],
            "injury": r["injury"], "status": r["status"], "practice": r["practice"],
            "player_url": r["player_url"], "injury_source": r["source"],
            "unit": "", "slot": "", "depth_string": "", "replacement": "",
            "replacement_depth": "", "chart_size": "", "group": UNIT_GROUP.get(r["pos"], "unknown"),
            "depth_source": clubs.get(r["team"], {}).get("url", ""),
            "chart_as_of": clubs.get(r["team"], {}).get("as_of_text", ""),
            "chart_unofficial": clubs.get(r["team"], {}).get("labels_unofficial", None),
            "join": "",
        }
        if not clubs.get(r["team"]) or not clubs[r["team"]]["units"]:
            entry["join"] = "club depth chart not machine-readable in capture"
        elif not hits:
            entry["join"] = "player not listed on his own club's depth chart"
        else:
            pos = (r["pos"] or "").upper()
            aliases = {pos}
            if pos in ("G", "LG", "RG", "C", "T", "LT", "RT", "OL"):
                aliases |= {"G", "LG", "RG", "C", "T", "LT", "RT", "OL"}
            if pos in ("CB", "NCB", "DB", "NB"):
                aliases |= {"CB", "NCB", "DB", "NB"}
            if pos in ("S", "SS", "FS"):
                aliases |= {"S", "SS", "FS"}
            if pos in ("LB", "ILB", "OLB", "MLB"):
                aliases |= {"LB", "ILB", "OLB", "MLB"}
            if pos in ("DE", "DT", "NT", "DL", "EDGE"):
                aliases |= {"DE", "DT", "NT", "DL", "EDGE"}
            same_pos = [h for h in hits if h["pos"].upper() in aliases]
            pick = (same_pos or hits)[0]
            entry.update({
                "unit": pick["unit"], "slot": pick["pos"],
                "depth_string": pick["depth"],
                "replacement": pick["behind"][0] if pick["behind"] else "",
                "replacement_depth": pick["depth"] + 1 if pick["behind"] else "",
                "chart_size": pick["slot_size"],
                "join": "matched" if same_pos else "matched on name only (position differs)",
                "ambiguous": len(hits) > 1,
            })
            if not pick["behind"]:
                entry["join"] += "; no backup listed at this slot"
        if entry["join"] != "matched":
            misses.append(entry)
        rows.append(entry)

    by_depth = {1: 0, 2: 0, 3: 0, 4: 0, "unknown": 0}
    for e in rows:
        d = e["depth_string"]
        if d in (1, 2, 3, 4):
            by_depth[d] += 1
        else:
            by_depth["unknown"] += 1
    summary = {
        "rows": len(rows),
        "matched": sum(1 for e in rows if e["join"].startswith("matched")),
        "unmatched": len(misses),
        "by_depth_string": by_depth,
        "by_group": {g: sum(1 for e in rows if e["group"] == g) for g in ("offense", "defense", "special", "unknown")},
        "weeks": sorted({e["week"] for e in rows}),
        "starter_outs": sum(1 for e in rows if e["depth_string"] == 1),
        "backup_promotions": sum(1 for e in rows if isinstance(e["depth_string"], int) and e["depth_string"] >= 2),
    }
    (base / "deficiencies.json").write_text(json.dumps({
        "method": ("Official injury report (game status Out/Doubtful) joined to the same club's "
                   "own depth chart by normalised player name. depth_string 1 = first team. "
                   "'replacement' is the player listed one string lower at the same slot. "
                   "Club depth charts are club-published and most are labelled unofficial."),
        "summary": summary, "rows": rows, "unmatched": misses,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
