#!/usr/bin/env python3
"""
X3 / replacement-depth engine.

Requirement: "track the depth of the replacement, not just the fact of a replacement."

The old model recorded a boolean: a first-stringer is Out, so a backup starts. That throws
away the only thing that matters for a price - WHO replaces him. Two absences at the same
position are not the same event if one is covered by a second-string All-Pro and the other
by a fourth-string practice-squad call-up.

Method (no imputation anywhere):

  1. Read the official availability report for Week 10 (data/hub/injuries_2026_wk10.csv,
     345 rows, source nfl.com/injuries/league/2026/reg10).
  2. Read each club's own published depth chart (tools/nfl_data.py DEPTH, 31 of 32 clubs;
     Houston publishes an image only, so Houston rows are UNVERIFIED by construction).
  3. Locate the unavailable player's tier on his club's chart for that slot.
     tier 1 = first string, 2 = second, 3 = third, 4 = fourth, 0 = not on the chart.
  4. Walk down the chart from his tier to the first man who is NOT himself unavailable in
     the same report. That man is the replacement, and HIS tier is the published depth of
     the replacement. If everyone below is also unavailable, the row says so.
  5. A starter with no chart entry gets no replacement: the row is published with a blank
     and badged UNVERIFIED, never guessed.

Dating caveat, published with the table: only 5 of 32 club charts print an as-of date, so
the chart is a snapshot of unknown age. That is a real limit of the source, not of the
method, and it is flagged per club.

Run: python3 tools/depth_engine.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "x3")
SRC_INJ = "https://www.nfl.com/injuries/league/2026/reg10"
AS_OF = "2026-11-14"

ALIAS = {"ARI": "AZ", "LA": "LAR"}
OFF = {"QB", "RB", "FB", "WR", "TE", "C", "G", "T", "OL", "LT", "RT", "LG", "RG"}
DEF = {"DE", "DT", "NT", "LB", "ILB", "OLB", "MLB", "EDGE", "CB", "S", "FS", "SS", "DB", "DL"}

UNAVAILABLE = {"Out", "Doubtful"}


def norm_pos(p):
    p = (p or "").strip().upper()
    return {"LT": "T", "RT": "T", "LG": "G", "RG": "G", "NT": "DT", "ILB": "LB", "OLB": "LB",
            "MLB": "LB", "FS": "S", "SS": "S", "DB": "S", "EDGE": "DE", "OL": "T"}.get(p, p)


def unit_of(pos):
    p = norm_pos(pos)
    if p in {norm_pos(x) for x in OFF}:
        return "offence"
    if p in {norm_pos(x) for x in DEF}:
        return "defence"
    return "special teams"


def load_prior():
    spec = importlib.util.spec_from_file_location("nfl_data", os.path.join(ROOT, "tools", "nfl_data.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    prior = load_prior()
    charts = {}
    for abbr, d in prior.DEPTH.items():
        a = ALIAS.get(abbr, abbr)
        slots = []
        for label, names in d["slots"]:
            slots.append((label, [n for n in names if n and n.strip()]))
        charts[a] = {"url": d.get("url", ""), "as_of": (d.get("as_of") or "").strip(),
                     "slots": slots}

    inj = list(csv.DictReader(open(os.path.join(ROOT, "data", "hub",
                                                "injuries_2026_wk10.csv"), encoding="utf-8")))
    # everyone on the report with a designation that costs availability
    unavailable_by_team = {}
    for r in inj:
        if r["status"] in UNAVAILABLE:
            unavailable_by_team.setdefault(r["team"], set()).add(r["player"].strip().lower())

    def slot_pos(label):
        """position code out of a chart slot label: 'RT', 'ILB', 'TE (2)', 'RB' -> position."""
        return norm_pos(label.split("(")[0].strip().split()[0] if label.strip() else "")

    def find_tier(team, player, pos):
        """return (tier, slot_label, slot_index) on the club chart, or ('MISMATCH', label, si).

        A name match is only ACCEPTED when the chart slot's position group equals the
        position on the official report. Two different players can share a name, and a
        name match in the wrong position group would invent a replacement.
        """
        ch = charts.get(team)
        if not ch:
            return None
        key = player.strip().lower()
        want = norm_pos(pos)
        mismatch = None
        for si, (label, names) in enumerate(ch["slots"]):
            for j, nm in enumerate(names):
                if nm.strip().lower() == key:
                    if slot_pos(label) == want:
                        return (j + 1, label, si)
                    mismatch = (label, j + 1, si)
        if mismatch:
            return ("MISMATCH", mismatch[0], mismatch[2])
        return None

    rows, club_summary = [], {}
    for r in inj:
        if r["status"] not in UNAVAILABLE:
            continue
        team = r["team"]
        pos = r["pos"]
        tier_info = find_tier(team, r["player"], r["pos"])
        base = {
            "club": team, "player": r["player"].strip(), "pos": r["pos"], "unit": unit_of(pos),
            "status": r["status"], "practice": r["practice"],
            "source_report": SRC_INJ,
            "chart_url": charts.get(team, {}).get("url", ""),
            "chart_as_of": charts.get(team, {}).get("as_of", ""),
        }
        if team not in charts:
            rows.append({**base, "tier": "", "slot": "", "replacement": "",
                         "replacement_tier": "", "depth_of_replacement": "",
                         "chain": "", "state": "UNVERIFIED",
                         "why": "the club publishes no machine-readable chart (image only), so the "
                                "man who replaces him cannot be named from an official source"})
            continue
        if tier_info and tier_info[0] == "MISMATCH":
            rows.append({**base, "tier": "", "slot": tier_info[1], "replacement": "",
                         "replacement_tier": "", "depth_of_replacement": "",
                         "chain": "", "state": "UNVERIFIED",
                         "why": f"the only chart match for this name sits in a different position "
                                f"group ({tier_info[1]}); a cross-role name match is refused rather "
                                f"than used to name a replacement"})
            continue
        if tier_info is None:
            rows.append({**base, "tier": "", "slot": "", "replacement": "",
                         "replacement_tier": "", "depth_of_replacement": "",
                         "chain": "", "state": "UNVERIFIED",
                         "why": "player is not listed on his club's chart (new signing, injured "
                                "reserve, or a chart that has not been updated)"})
            continue

        tier, slot, si = tier_info
        chain = charts[team]["slots"][si][1]
        out_set = unavailable_by_team.get(team, set())
        replacement, rep_tier = "", ""
        for j in range(tier, len(chain)):
            nm = chain[j]
            if nm.strip().lower() in out_set:
                continue
            replacement, rep_tier = nm, j + 1
            break
        state = "VERIFIED" if replacement else "UNVERIFIED"
        why = "" if replacement else ("every man listed below him on the chart is also out or "
                                      "doubtful in the same report, so the replacement is not on "
                                      "the chart")
        label = {2: "2nd string", 3: "3rd string", 4: "4th string"}.get(rep_tier, "")
        if replacement and not label:
            label = f"{rep_tier}th string" if isinstance(rep_tier, int) else ""
        rows.append({**base, "tier": tier, "slot": slot, "replacement": replacement,
                     "replacement_tier": rep_tier, "depth_of_replacement": label,
                     "chain": " > ".join(chain), "state": state, "why": why})

    # ---- per-club aggregation: the deepest hole on each unit --------------------
    for row in rows:
        c = club_summary.setdefault(row["club"], {
            "club": row["club"], "chart_url": row["chart_url"], "chart_as_of": row["chart_as_of"],
            "absences": 0, "starters_out": 0, "offence": 0, "defence": 0, "st": 0,
            "replacement_tiers": [], "unverified": 0, "deepest": ""})
        c["absences"] += 1
        if row["tier"] == 1:
            c["starters_out"] += 1
            c["offence" if row["unit"] == "offence" else
              ("defence" if row["unit"] == "defence" else "st")] += 1
        if isinstance(row["replacement_tier"], int):
            c["replacement_tiers"].append(row["replacement_tier"])
        if row["state"] != "VERIFIED":
            c["unverified"] += 1
    for c in club_summary.values():
        if c["replacement_tiers"]:
            deep = max(c["replacement_tiers"])
            c["deepest"] = {2: "2nd string", 3: "3rd string", 4: "4th string"}.get(deep, f"{deep}th string")
            c["mean_replacement_tier"] = round(sum(c["replacement_tiers"]) / len(c["replacement_tiers"]), 2)
        else:
            c["deepest"] = ""
            c["mean_replacement_tier"] = ""
        c.pop("replacement_tiers", None)

    named = [r for r in rows if r["state"] == "VERIFIED"]
    tiers = [r["replacement_tier"] for r in named]
    deep3 = [r for r in named if isinstance(r["replacement_tier"], int) and r["replacement_tier"] >= 3]

    out = {
        "as_of": AS_OF, "generated_by": "tools/depth_engine.py",
        "counts": {
            "absences_out_or_doubtful": len(rows),
            "replacement_named": len(named),
            "replacement_unverified": len(rows) - len(named),
            "replaced_by_2nd_string": sum(1 for t in tiers if t == 2),
            "replaced_by_3rd_string_or_deeper": sum(1 for t in tiers if isinstance(t, int) and t >= 3),
            "clubs_with_a_chart": len(charts),
            "clubs_total": 32,
            "charts_with_as_of_date": sum(1 for c in charts.values() if c["as_of"]),
        },
        "definition": ("depth of the replacement = the chart tier of the first man listed below "
                       "the unavailable player who is not himself Out or Doubtful in the same "
                       "official report"),
        "sources": {"report": SRC_INJ,
                    "charts": "each club's own /team/depth-chart page (URL per row); all "
                              "self-labelled unofficial by the clubs",
                    "chart_registry": "tools/nfl_data.py DEPTH"},
        "limits": [
            "Club charts are unofficial by the clubs' own label and only 5 of 32 print an as-of "
            "date, so a chart may predate a trade or a promotion.",
            "Houston publishes an image only; its rows are UNVERIFIED, not guessed.",
            "A chart is a depth ORDER, not a snap count. The next man up may in practice play "
            "fewer snaps than the man behind him.",
            "This is Week 10 only; no history exists, so no replacement-depth effect can be "
            "fitted yet (see the correlation page, blank rows).",
        ],
        "clubs": [club_summary[k] for k in sorted(club_summary)],
        "rows": sorted(rows, key=lambda r: (r["club"], str(r["tier"]), r["player"])),
        "deepest_holes": sorted([r for r in rows if r["state"] == "VERIFIED"],
                                key=lambda r: (-(r["replacement_tier"] or 0), r["club"]))[:14],
    }
    with open(os.path.join(OUT, "depth_replacement.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    cols = ["club", "player", "pos", "unit", "status", "tier", "slot", "replacement",
            "replacement_tier", "depth_of_replacement", "chain", "state", "why",
            "chart_as_of", "chart_url", "source_report"]
    with open(os.path.join(OUT, "depth_replacement.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"absences (Out/Doubtful): {len(rows)}")
    print(f"replacement named: {len(named)}  ({sum(1 for t in tiers if t == 2)} by a 2nd string, "
          f"{sum(1 for t in tiers if isinstance(t, int) and t >= 3)} by a 3rd string or deeper)")
    print(f"unverified (no chart / not listed / chain exhausted): {len(rows) - len(named)}")
    print(f"charts with an as-of date: {out['counts']['charts_with_as_of_date']}/32")
    for r in out["deepest_holes"][:6]:
        print(f"  {r['club']:>4} {r['pos']:<3} {r['player']:<24} out -> {r['replacement']:<24} "
              f"({r['depth_of_replacement']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
