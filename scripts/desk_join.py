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


# Position codes differ between clubs (LG/RG/G, SLB/OLB/LB, RCB/CB, N/NCB/NB, LDT/DT). Each
# injury-report code maps only to codes that describe the SAME role on a depth chart. Kicking-game
# roles (KR/PR/LS/H) are never treated as aliases for offensive or defensive positions.
POS_ALIASES = {
    "QB": {"QB"}, "RB": {"RB", "FB"}, "FB": {"FB", "RB"},
    "WR": {"WR", "SLOT", "X", "Y", "Z"}, "TE": {"TE", "H"},
    "C": {"C"}, "LG": {"LG", "G"}, "RG": {"RG", "G"}, "G": {"G", "LG", "RG"},
    "LT": {"LT", "T"}, "RT": {"RT", "T"}, "T": {"T", "LT", "RT"},
    "OL": {"OL", "LT", "RT", "LG", "RG", "C"},
    "DE": {"DE", "EDGE", "LE", "RE", "DL"}, "EDGE": {"EDGE", "DE", "LE", "RE", "DL"},
    "DT": {"DT", "NT", "LDT", "RDT", "DL"}, "NT": {"NT", "DT", "DL"},
    "DL": {"DL", "DT", "NT", "DE", "EDGE", "LDT", "RDT"},
    "LB": {"LB", "ILB", "OLB", "MLB", "SLB", "WLB", "MIKE", "WILL", "SAM"},
    "ILB": {"ILB", "LB", "MLB", "MIKE"}, "OLB": {"OLB", "LB", "SLB", "WLB", "EDGE"},
    "CB": {"CB", "RCB", "LCB", "NCB", "NB", "N", "DB", "SLOT"},
    "S": {"S", "SS", "FS", "DB"},
    "DB": {"DB", "CB", "RCB", "LCB", "NCB", "NB", "S", "SS", "FS"},
    "S": {"S", "SS", "FS", "DB"}, "SS": {"SS", "S", "FS"}, "FS": {"FS", "S", "SS"},
    "K": {"K"}, "P": {"P"}, "LS": {"LS"}, "KR": {"KR"}, "PR": {"PR"}, "H": {"H"},
}

ROLE_GROUP = {
    "offense": {"QB", "RB", "FB", "WR", "TE", "SLOT", "X", "Y", "Z", "H"},
    "oline": {"C", "LG", "RG", "G", "LT", "RT", "T", "OL"},
    "dline": {"DE", "EDGE", "DT", "NT", "DL", "LE", "RE", "LDT", "RDT"},
    "linebacker": {"LB", "ILB", "OLB", "MLB", "SLB", "WLB", "MIKE", "WILL", "SAM"},
    "secondary": {"CB", "DB", "RCB", "LCB", "NCB", "NB", "N", "S", "SS", "FS"},
    "kicking": {"K", "P", "LS", "KR", "PR", "H"},
}


def role_of(code: str) -> str:
    for group, codes in ROLE_GROUP.items():
        if code.upper() in codes:
            return group
    return ""


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
            aliases = POS_ALIASES.get(pos, {pos})

            my_role = role_of(pos)
            same_pos = [h for h in hits
                        if h["pos"].upper() in aliases and role_of(h["pos"].upper()) == my_role]
            pick = (same_pos or hits)[0]
            entry.update({
                "unit": pick["unit"], "slot": pick["pos"],
                "depth_string": pick["depth"],
                "replacement": pick["behind"][0] if pick["behind"] else "",
                "replacement_depth": pick["depth"] + 1 if pick["behind"] else "",
                "chart_size": pick["slot_size"],
                "join": "matched" if same_pos else "matched-name-only",
                "ambiguous": len(hits) > 1,
            })
            entry["has_backup"] = bool(pick["behind"])
            if not pick["behind"] and entry["join"] == "matched":
                entry["join"] = "matched-no-backup"
        if not entry["join"].startswith("matched") or entry["join"] == "matched-name-only":
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
        "matched": sum(1 for e in rows if e["join"] in ("matched", "matched-no-backup")),
        "matched_name_only": sum(1 for e in rows if e["join"] == "matched-name-only"),
        "unmatched": len(misses),
        "by_depth_string": by_depth,
        "by_group": {g: sum(1 for e in rows if e["group"] == g) for g in ("offense", "defense", "special", "unknown")},
        "weeks": sorted({e["week"] for e in rows}),
        "starter_outs": sum(1 for e in rows if e["depth_string"] == 1),
        "backup_promotions": sum(1 for e in rows if isinstance(e["depth_string"], int) and e["depth_string"] >= 2),
    }
    partial_charts = []
    for c in dep["clubs"]:
        n_slots = sum(len(u["slots"]) for u in c["units"])
        if c["units"] and n_slots < 15:
            partial_charts.append({"abbr": c["abbr"], "slots": n_slots, "url": c["url"]})
    (base / "deficiencies.json").write_text(json.dumps({
        "method": ("Official injury report (game status Out/Doubtful) joined to the same club's "
                   "own depth chart by normalised player name. depth_string 1 = first team. "
                   "'replacement' is the player listed one string lower at the same slot. "
                   "Club depth charts are club-published and most are labelled unofficial."),
        "summary": summary, "rows": rows, "unmatched": misses,
        "partial_charts": partial_charts,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
