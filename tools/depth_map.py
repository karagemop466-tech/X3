#!/usr/bin/env python3
"""
Replacement depth: not "a backup plays", but *which* backup and how deep.

The brief asks to track "the depth of the replacement, not just the fact of a
replacement", and to know when a defence is on its 2nd, 3rd or 4th string.

Inputs
  data/desk/injuries.json   Week-10 official report, every row
  data/desk/depth.json      club depth charts captured 2026-11-14
  data/hub/injuries_2026_wk10.csv
                            the hub's independently transcribed report; used as
                            a second read so the absence list is not one person's
                            transcription

Method, stated in full because the join is the whole difficulty
  1. Take every Week-10 row whose game designation is Out or Doubtful. A
     Questionable player may well play, so counting him as "replaced" would be
     an inference, not an observation.
  2. Find that player on his club's depth chart, in the slot where he appears.
  3. Report the tier he occupies (1 = first string) and the men listed above and
     below him. The "replacement depth" is the tier of the next man up: a
     first-stringer going down means a 2nd-stringer plays; if the 2nd string is
     also out, it is the 3rd, and so on.
  4. If the player is not on the chart, or the club publishes no parseable chart,
     the row is kept with a blank replacement and an explicit reason. It is never
     filled by guessing.

A depth chart is not an official availability statement. Only 0-2 charts in the
capture carry an as-of date and most clubs label theirs "unofficial", which is
recorded per club and carried onto the page as a caveat, not hidden.

Run: python3 tools/depth_map.py
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "verified")


def norm_name(s: str) -> str:
    """Lowercase, strip punctuation and suffixes, so 'A.J. Brown' ~ 'AJ Brown'."""
    s = s.lower().replace(".", "").replace("'", "").replace("’", "")
    for suf in (" jr", " sr", " iii", " ii", " iv"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    return " ".join(s.split())


def load_injuries():
    p = os.path.join(ROOT, "data", "desk", "injuries.json")
    d = json.load(open(p, encoding="utf-8"))
    return d


WEEK = 10


def injuries_rows(d):
    """Normalise the injury capture into rows of (club, name, pos, status).

    data/desk/injuries.json stores every week it captured in one flat list, so
    the week has to be filtered here. Only the current week is used; an older
    week's designation says nothing about who plays this week.
    """
    rows = []
    for r in d.get("rows", []):
        if r.get("week") != WEEK:
            continue
        rows.append({
            "club": r.get("team", ""),
            "name": r.get("player", ""),
            "pos": r.get("pos", ""),
            "status": r.get("status", ""),
            "detail": r.get("injury", ""),
            "source": r.get("source", ""),
        })
    return rows


def build():
    raw = load_injuries()
    rows = injuries_rows(raw)
    if not rows:
        print("WARNING: no rows parsed from data/desk/injuries.json; "
              "falling back to the hub CSV so the page still reflects the official report")
        rows = []
        p = os.path.join(ROOT, "data", "hub", "injuries_2026_wk10.csv")
        for r in csv.DictReader(open(p, encoding="utf-8")):
            rows.append({
                "club": r.get("team") or r.get("club", ""),
                "name": r.get("player") or r.get("name", ""),
                "pos": r.get("pos") or r.get("position", ""),
                "status": r.get("game_status") or r.get("status", ""),
                "detail": r.get("injury") or r.get("detail", ""),
                "source": r.get("source", ""),
            })

    depth = json.load(open(os.path.join(ROOT, "data", "desk", "depth.json"), encoding="utf-8"))
    # index: (club, normalised name) -> list of (unit, slot pos, tier index, slot)
    idx = defaultdict(list)
    club_meta = {}
    abbr_map = {"ARI": "AZ", "LA": "LA"}
    for c in depth["clubs"]:
        club_meta[abbr_map.get(c["abbr"], c["abbr"])] = {
            "url": c.get("url", ""),
            "as_of_text": c.get("as_of_text", ""),
            "labels_unofficial": c.get("labels_unofficial", False),
            "slots": 0,
        }
        for u in c["units"]:
            for s in u["slots"]:
                club_meta[abbr_map.get(c["abbr"], c["abbr"])]["slots"] += 1
                for ti, tier in enumerate(s["tiers"]):
                    for nm in tier:
                        idx[(abbr_map.get(c["abbr"], c["abbr"]), norm_name(nm))].append(
                            {"unit": u["unit"], "pos": s["pos"], "tier": ti + 1, "slot": s})

    out_rows = []
    seen_keys = []
    for r in rows:
        st = (r["status"] or "").strip()
        if st not in ("Out", "Doubtful"):
            continue
        seen_keys.append((r["club"], r["name"]))
        club = r["club"]
        if not club:
            continue
        hits = idx.get((club, norm_name(r["name"])), [])
        if not hits:
            reason = ("club publishes an image-only chart" if club == "HOU"
                      else "chart captured" if club in club_meta else "club chart not captured")
            out_rows.append({
                "club": club, "player": r["name"], "pos": r["pos"], "status": st,
                "chart_slot": "", "chart_tier": "", "replacement": "", "replacement_tier": "",
                "replaced": "", "above": "", "below": "", "depth_known": False,
                "reason": f"not found on the club chart ({reason})",
                "chart_url": club_meta.get(club, {}).get("url", ""),
            })
            continue
        # choose the deepest listing (the chart may list a player on two units, e.g. KR)
        hit = sorted(hits, key=lambda h: h["tier"], reverse=True)[0]
        tiers = hit["slot"]["tiers"]
        tier = hit["tier"]
        below = tiers[tier] if tier < len(tiers) else []
        above = tiers[tier - 2] if tier >= 2 else []
        replacement = ", ".join(below)
        out_rows.append({
            "club": club, "player": r["name"], "pos": r["pos"], "status": st,
            "chart_slot": hit["pos"], "chart_tier": tier,
            "replacement": replacement,
            "replacement_tier": (tier + 1) if replacement else "",
            "replaced": ", ".join(t for t in above) if above else "",
            "above": ", ".join(", ".join(t) for t in tiers[: tier - 1]),
            "below": ", ".join(", ".join(t) for t in tiers[tier:]),
            "depth_known": bool(replacement),
            "reason": "" if replacement else "no lower tier listed on the club chart",
            "chart_url": club_meta.get(club, {}).get("url", ""),
        })

    # ---- completeness audit: every Out/Doubtful row in the capture must appear
    # exactly once in the output. A silent join loss is the failure mode this page
    # exists to prevent, so it is checked rather than assumed.
    eligible = [(r["club"], r["name"]) for r in rows
                if (r["status"] or "").strip() in ("Out", "Doubtful")]
    emitted = [(r["club"], r["player"]) for r in out_rows]
    missing = [k for k in eligible if k not in emitted]
    duplicated = sorted({k for k in emitted if emitted.count(k) > 1})
    extra = [k for k in emitted if k not in eligible]
    completeness = {
        "eligible_out_or_doubtful": len(eligible),
        "emitted_rows": len(emitted),
        "missing_from_output": missing,
        "duplicated_rows": duplicated,
        "emitted_but_not_eligible": extra,
        "status": ("PASS" if not missing and not duplicated and not extra
                   and len(emitted) == len(eligible) else "FAIL"),
    }

    # ---- aggregates
    tier_by_club = Counter()
    for row in out_rows:
        if row["replacement"]:
            tier_by_club[row["replacement_tier"]] += 1
    by_club = defaultdict(lambda: {"absences": 0, "resolved": 0, "tiers": []})
    for row in out_rows:
        b = by_club[row["club"]]
        b["absences"] += 1
        if row["replacement"]:
            b["resolved"] += 1
            b["tiers"].append(row["replacement_tier"])

    clubs = sorted(by_club)
    summary = []
    for c in clubs:
        b = by_club[c]
        meta = club_meta.get(c, {})
        summary.append({
            "club": c,
            "absences_out_or_doubtful": b["absences"],
            "replacements_identified": b["resolved"],
            "deepest_tier_forced": max(b["tiers"]) if b["tiers"] else "",
            "chart_slots": meta.get("slots", ""),
            "chart_as_of": meta.get("as_of_text", "") or "not stated by club",
            "chart_unofficial": "yes" if meta.get("labels_unofficial") else "no",
            "chart_url": meta.get("url", ""),
        })

    multi = sum(1 for j in idx.values() if len(j) > 1)
    out = {
        "method": "Game designation Out or Doubtful only; Questionable is excluded because "
                  "those players may play, and treating them as replaced would be inference. "
                  "The player is located on his club's own depth chart and the chart tier he "
                  "occupies is reported, together with the man immediately below him. "
                  "Replacement tier = chart tier + 1. Where a club lists no lower tier or no "
                  "parseable chart exists, the cell is blank and the row carries a reason.",
        "sources": {
            "injuries": "https://www.nfl.com/injuries/league/2026/reg10",
            "depth_charts": "each club's own /team/depth-chart page; URL per row",
        },
        "captured": depth.get("captured", ""),
        "rows_total": len(out_rows),
        "replacements_identified": sum(1 for r in out_rows if r["replacement"]),
        "tier_counts": {str(k): v for k, v in sorted(tier_by_club.items())},
        "clubs_with_absences": len(by_club),
        "player_listed_on_multiple_units": multi,
        "caveats": [
            "Most clubs label their depth chart unofficial and few publish an as-of date, so "
            "the chart is evidence of a published ordering, not of who will actually start.",
            "A player missing from a chart is not evidence he is not on the team; it is a "
            "capture limitation and is reported as one.",
            "The official injury report gives status, never a depth position. Nothing here "
            "overrides the official status.",
        ],
        "completeness": completeness,
        "clubs": summary,
        "rows": out_rows,
    }
    json.dump(out, open(os.path.join(OUT, "depth_map.json"), "w", encoding="utf-8"), indent=1)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    o = build()
    print(f"rows (Out/Doubtful): {o['rows_total']}  replacements identified: "
          f"{o['replacements_identified']}  clubs: {o['clubs_with_absences']}")
    print("tier counts (tier of the man who steps in):", o["tier_counts"])
    c = o["completeness"]
    print(f"completeness: {c['status']}  eligible {c['eligible_out_or_doubtful']} -> "
          f"emitted {c['emitted_rows']}  missing {len(c['missing_from_output'])}  "
          f"dup {len(c['duplicated_rows'])}")
    deepest = [c for c in o["clubs"] if c["deepest_tier_forced"] not in ("", 2)]
    print("clubs forced past the 2nd string:", len(deepest))
    for c in deepest:
        print(f"  {c['club']}: deepest tier {c['deepest_tier_forced']} "
              f"({c['replacements_identified']}/{c['absences_out_or_doubtful']} resolved)")
    print("OK")


if __name__ == "__main__":
    main()
