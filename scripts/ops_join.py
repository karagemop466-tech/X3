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
        # Build the club's printed depth ladder for this player's ROLE GROUP: every slot whose
        # position code is in the same role group (so G, LG and RG form one interior-line ladder,
        # and CB and DB form one secondary ladder), in the order the club prints them. A slot in a
        # different role group is never traversed - a kick returner is not a running back.
        grp = group(pos) if pos else None
        ladder, slot_tiers_of_hit, hit_slot = [], None, None
        for u in c["units"]:
            for slot in u.get("slots", []):
                if grp and group(slot.get("pos", "")) != grp:
                    continue
                for names in (slot.get("tiers") or []):
                    for nm in names:
                        ladder.append({"name": nm, "slot_pos": slot.get("pos", ""), "tiers": slot.get("tiers") or []})
        hit = next((i for i, x in enumerate(ladder) if norm(x["name"]) == norm(player)), None)
        if hit is None:
            # name exists on the chart, but only at a position in another role group -> refused
            anywhere = any(norm(nm) == norm(player)
                           for u in c["units"] for sl in u.get("slots", [])
                           for nm in [n for t in (sl.get("tiers") or []) for n in t])
            if anywhere:
                partial.append({**base, "reason": "name appears only at a position in a different role group - refused"})
            else:
                unmatched.append({**base, "reason": "player not listed on his own club's depth chart"})
            continue
        h = ladder[hit]
        tiers = h["tiers"]
        slot_tiers_of_hit = tiers
        # inside the hit slot, find the tier index of the player
        tier = next((ti for ti, names in enumerate(tiers) if any(norm(n) == norm(player) for n in names)), 0)
        # --- the two honest scalars, no synthesis ---
        # column_rank : which column at this exact position code is he printed in (1-based).
        #               3 = the club printed two earlier WR columns before his.
        # tier        : his depth inside his own column. 1 = the starter of that column.
        cols = []
        for x in ladder[:hit + 1]:
            if x["slot_pos"] not in cols:
                cols.append(x["slot_pos"])
        column_rank = len(cols)
        tier_number = tier + 1
        duplicate = sum(1 for x in ladder if norm(x["name"]) == norm(player)) > 1

        # --- replacement, only ever at the SAME position code ---
        # 1. next man in his own column (the club's own answer)
        # 2. first name in the next column at the same position code
        # Anything further down a different position code is NOT a replacement at this position,
        # so it is recorded as "no backup at this position" instead of being invented.
        rep, rep_kind, rep_col, rep_tier = "", "", None, None
        if tier + 1 < len(tiers) and tiers[tier + 1]:
            rep, rep_kind, rep_col, rep_tier = tiers[tier + 1][0], "next man in his own column", column_rank, tier_number + 1
        else:
            same = [x for x in ladder[hit + 1:] if x["slot_pos"] == h["slot_pos"]]
            if same:
                rep, rep_kind, rep_col, rep_tier = same[0]["name"], "first man in the next column at this position", column_rank + 1, 1
        row = {**base, "unit": "", "slot_pos": h["slot_pos"],
               "depth_string": column_rank, "chart_size": len([x for x in ladder if x["slot_pos"] == h["slot_pos"]]),
               "pos_tier": tier_number, "pos_column": column_rank,
               "replacement": rep, "replacement_depth": rep_col,
               "replacement_tier": rep_tier,
               "replacement_kind": rep_kind,
               "replacement_by_slot": rep if rep_kind.startswith("next man") else "",
               "duplicate_listing": duplicate,
               "reading": (f'column {column_rank} at {h["slot_pos"]}, tier {tier_number} inside it')}
        if not rep:
            no_backup.append({**row, "reason": "the club lists nobody else at this position code below him"})
        else:
            out.append(row)

    by_depth = {}
    for r in out:
        by_depth[str(r["depth_string"])] = by_depth.get(str(r["depth_string"]), 0) + 1
    by_rep = {}
    for r in out:
        by_rep[str(r["replacement_depth"])] = by_rep.get(str(r["replacement_depth"]), 0) + 1
    by_tier = {}
    for r in out:
        by_tier[str(r["pos_tier"])] = by_tier.get(str(r["pos_tier"]), 0) + 1
    by_starters = sum(1 for r in out if r["pos_column"] == 1 and r["pos_tier"] == 1)
    by_kind = {}
    for r in out:
        by_kind[r["replacement_kind"]] = by_kind.get(r["replacement_kind"], 0) + 1
    dupes = [f'{r["team"]} {r["player"]}' for r in out + no_backup if r.get("duplicate_listing")]
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
        "by_pos_tier": by_tier,
        "by_replacement_kind": by_kind,
        "starters_affected_column1_tier1": by_starters,
        "duplicate_chart_listings": dupes,
        "by_replacement_depth": by_rep,
        "by_group": by_group,
        "charts_with_as_of_date": sum(1 for a in chart_as_of if chart_as_of[a]),
        "charts_labelled_unofficial": sum(1 for a in chart_unofficial if chart_unofficial[a]),
        "charts_total": len(chart),
    }
    joined_exact = [r for r in out if r["pos_column"] == 1 and r["pos_tier"] == 1]
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
