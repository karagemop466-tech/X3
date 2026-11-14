#!/usr/bin/env python3
"""
Replacement-depth tracker.

The requirement is not "was there a replacement" but "WHO replaced WHOM, from which string,
and does the chart even carry one". This script answers that from two official inputs:

  data/ops/reference/injuries_wk10.json   official NFL injury report (game status)
  data/ops/reference/depth.json           club-published depth charts

For every Out/Doubtful player in week 10 it records:
  depth_string      1 = listed first on his own club's chart at that position
  replacement       the next name down the SAME position group
  replacement_depth 2, 3, 4 ... i.e. how deep the club has to go
  gap               no name below him on the chart at all
Classification is deliberately strict. A name that appears at a different position group is
NOT a match (a kick returner is not a running back), and a match with no name below it is
NOT a replacement. Both are published in their own tables rather than folded into a count.
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "ops", "reference")
OUT = os.path.join(ROOT, "data", "ops")
SHARE = os.path.join(ROOT, "ops", "data")

GROUPS = {
    "offense": {"QB", "RB", "FB", "WR", "TE", "T", "LT", "RT", "G", "LG", "RG", "C", "OL"},
    "dline": {"DE", "DT", "NT", "DL", "EDGE", "IDL"},
    "lb": {"LB", "ILB", "OLB", "MLB"},
    "secondary": {"CB", "S", "FS", "SS", "DB", "NB"},
    "kicking": {"K", "P", "LS", "H", "KR", "PR"},
}


def group(pos):
    p = (pos or "").upper().strip()
    for g, s in GROUPS.items():
        if p in s:
            return g
    return "unknown"


def norm(name):
    s = (name or "").lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def second(v):
    """Second on the chart at this slot, else the deepest name listed (so the buyer at the
    book sees the same player we do)."""
    if not v:
        return None
    if len(v) > 1:
        return v[1], 2
    return None, None


def build():
    inj = json.load(open(os.path.join(REF, "injuries_wk10.json"), encoding="utf-8"))
    depth = json.load(open(os.path.join(REF, "depth.json"), encoding="utf-8"))
    wk = [w for w in inj["weeks"] if w["week"] == 10][0]
    rows_all = inj["rows"] if isinstance(inj.get("rows"), list) else []
    chart = {c["abbr"]: c for c in depth["clubs"]}
    chart_as_of = {a: c.get("as_of_text", "") for a, c in chart.items()}
    chart_unofficial = {a: bool(c.get("labels_unofficial")) for a, c in chart.items()}

    out, unmatched, no_backup, partial = [], [], [], []
    for r in rows_all:
        if r.get("week") != 10:
            continue                       # injury rows carry their own week field where present
        if r.get("status") not in ("Out", "Doubtful"):
            continue
        team, player, pos = r.get("team", ""), r.get("player", ""), r.get("pos", "")
        base = {
            "week": 10, "team": team, "player": player, "pos": pos,
            "status": r.get("status"), "injury": r.get("injury", ""),
            "practice": r.get("practice", ""),
            "player_url": r.get("player_url", ""),
            "injury_source": r.get("injury_source") or wk["url"],
            "chart_source": (chart.get(team) or {}).get("url", ""),
            "chart_as_of": chart_as_of.get(team, ""),
            "chart_unofficial": chart_unofficial.get(team, True),
        }
        c = chart.get(team)
        if not c or not c.get("units"):
            unmatched.append({**base, "reason": "club depth chart not machine-readable in capture"})
            continue
        # Walk the chart in its own printed order across every slot of the same position,
        # so a club that lists two CB columns is read the way the club prints it.
        found = None
        ordered = []
        for u in c["units"]:
            for slot in u.get("slots", []):
                if slot.get("pos") == pos:
                    for names in (slot.get("tiers") or []):
                        ordered.extend(names)
        if ordered:
            for i, nm in enumerate(ordered):
                if norm(nm) == norm(player):
                    found = ("chart-order", pos, i, [ordered[j:j + 1] for j in range(len(ordered))])
                    break
        if not found:
            for u in c["units"]:
                for slot in u.get("slots", []):
                    if slot.get("pos") != pos:
                        continue
                    tiers = slot.get("tiers") or []
                    for ti, names in enumerate(tiers):
                        for nm in names:
                            if norm(nm) == norm(player):
                                found = (u.get("unit", ""), slot.get("pos", ""), ti, tiers)
                                break
                        if found:
                            break
                    if found:
                        break
                if found:
                    break
        if not found:
            unmatched.append({**base, "reason": "player not listed on his own club's depth chart"})
            continue
        unit, slot_pos, tier, tiers = found
        if group(slot_pos) != group(pos) and pos:
            partial.append({**base, "unit": unit, "slot_pos": slot_pos, "depth_string": tier + 1,
                            "reason": f"name appears at {slot_pos} but the report lists {pos} - not treated as a match"})
            continue
        if found[2] is not None and found[0] == "chart-order":
            nxt = ordered[found[2] + 1] if found[2] + 1 < len(ordered) else None
            rep, rep_depth = (nxt, found[2] + 2) if nxt else (None, None)
        else:
            rep, rep_depth = second(tiers[tier])
        row = {**base, "unit": unit, "slot_pos": slot_pos, "depth_string": tier + 1,
               "chart_size": len(tiers), "replacement": rep or "", "replacement_depth": rep_depth}
        if not rep:
            no_backup.append({**row, "reason": "no name below him on his own club's chart"})
        else:
            out.append(row)

    by_depth = {}
    for r in out:
        by_depth[str(r["depth_string"])] = by_depth.get(str(r["depth_string"]), 0) + 1
    by_rep = {}
    for r in out:
        by_rep[str(r["replacement_depth"])] = by_rep.get(str(r["replacement_depth"]), 0) + 1
    by_group = {}
    for r in out:
        g = group(r["pos"])
        by_group[g] = by_group.get(g, 0) + 1

    # which clubs have to reach furthest down their own board
    club_rep = {}
    for r in out:
        club_rep.setdefault(r["team"], []).append(r["replacement_depth"])
    club_rows = [{"team": t, "n": len(v), "deepest_replacement": max(v),
                  "mean_replacement_depth": round(sum(v) / len(v), 2),
                  "chart_as_of": chart_as_of.get(t, ""), "chart_unofficial": chart_unofficial.get(t, True),
                  "chart_source": (chart.get(t) or {}).get("url", ""),
                  "source": (chart.get(t) or {}).get("url", "")}
                 for t, v in sorted(club_rep.items(), key=lambda kv: -max(kv[1]))]

    summary = {
        "week": 10,
        "out_doubtful": len([r for r in rows_all if r.get("week") == 10 and r.get("status") in ("Out", "Doubtful")]) if any(
            "week" in r for r in rows_all) else None,
        "matched_with_replacement": len(out),
        "matched_no_backup": len(no_backup),
        "matched_wrong_position": len(partial),
        "unmatched": len(unmatched),
        "by_depth_string": by_depth,
        "by_replacement_depth": by_rep,
        "by_group": by_group,
        "charts_with_as_of_date": sum(1 for a in chart_as_of if chart_as_of[a]),
        "charts_labelled_unofficial": sum(1 for a in chart_unofficial if chart_unofficial[a]),
        "charts_total": len(chart),
    }
    joined_exact = [r for r in out if r["depth_string"] == 1]
    summary["starter_absences_with_a_named_backup"] = len(joined_exact)
    summary["starter_absences_needing_2nd_or_deeper"] = sum(1 for r in out if r["replacement_depth"] and r["replacement_depth"] >= 2)

    return {
        "as_of": "2026-11-14",
        "method": ("Official Week-10 game status (Out/Doubtful) joined to the same club's own depth chart by "
                   "normalised player name, then checked at the position-group level. depth_string 1 = first man "
                   "on the chart at that slot; replacement = next man at the SAME slot; replacement_depth = 2,3,4 "
                   "tells you how thin the club is. Cross-group and no-backup matches are separated, not counted."),
        "injury_source": wk["url"],
        "rows": out,
        "no_backup": no_backup,
        "wrong_position": partial,
        "unmatched": unmatched,
        "club_summary": club_rows,
        "summary": summary,
    }


def main():
    blob = build()
    os.makedirs(SHARE, exist_ok=True)
    for d in (OUT, SHARE):
        with open(os.path.join(d, "join.json"), "w", encoding="utf-8") as f:
            json.dump(blob, f, indent=1)
    s = blob["summary"]
    print(f"depth join: {s['matched_with_replacement']} matched with a named backup, "
          f"{s['matched_no_backup']} no-backup, {s['matched_wrong_position']} wrong-position, "
          f"{s['unmatched']} unmatched")
    print(f"  by depth string {s['by_depth_string']}  by replacement depth {s['by_replacement_depth']}")
    print(f"  starter absences with a named backup: {s['starter_absences_with_a_named_backup']}; "
          f"needing 2nd or deeper: {s['starter_absences_needing_2nd_or_deeper']}")


if __name__ == "__main__":
    main()
