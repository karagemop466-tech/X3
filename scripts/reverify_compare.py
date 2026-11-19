#!/usr/bin/env python3
"""Re-verification comparison (task R1-R2).

Compares the frozen captured Week-10 Not Active / Did Not Play lists
(data/reverify/captured_before_w10_inactives.json, copied from e5f771d)
against the official Game Book text transcribed on 2026-11-19
(data/reverify/official_read_2026-11-19.json), and also checks the
reserve-list events, the reg11 IND@HOU block and the WAS@NYG snap rows.

Rules:
- Nothing is inferred. A captured name is 'match' only if the same
  normalised name appears in the SAME official slot with status 'printed'.
- If the official slot is not 'printed' (not_legible, ambiguous,
  located_unlabelled, printed_empty with captured names) the row is
  'unverified', never 'match'.
- Outputs are written under data/reverify/ only.
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "data" / "reverify"
CAPTURED = REV / "captured_before_w10_inactives.json"
OFFICIAL = REV / "official_read_2026-11-19.json"
RAW_TX = ROOT / "data" / "live" / "raw" / "transactions_nov2026.json"
SNAP_CSV = ROOT / "data" / "live" / "week10_snap_depth.csv"
REG11_CSV = ROOT / "data" / "live" / "week11_injuries.csv"


def norm(name: str) -> str:
    s = re.sub(r"\s+", " ", name.strip())
    s = s.replace("OL B ", "OLB ")  # extraction spacing only; recorded in method
    return s


def slots_for(game):
    return [
        ("away", "not_active", game["away_not_active"]),
        ("away", "dnp", game["away_dnp"]),
        ("home", "not_active", game["home_not_active"]),
        ("home", "dnp", game["home_dnp"]),
    ]


def main() -> int:
    cap = json.loads(CAPTURED.read_text())["games"]
    off = json.loads(OFFICIAL.read_text())["gamebooks"]
    off_by_id = {g["game_id"]: g for g in off}
    cap_by_id = {g["game_id"]: g for g in cap}
    assert set(off_by_id) == set(cap_by_id), "game id sets differ"

    cap_key = {("away", "not_active"): "away_not_active", ("away", "dnp"): "away_dnp",
               ("home", "not_active"): "home_not_active", ("home", "dnp"): "home_dnp"}

    rows = []
    per_game = {}
    for gid in cap_by_id:
        c = cap_by_id[gid]
        o = off_by_id[gid]
        counts = {"match": 0, "mismatch": 0, "unverified": 0}
        for side, slot, ostruct in slots_for(o):
            cap_names = [norm(x) for x in c[cap_key[(side, slot)]]]
            off_status = ostruct["status"]
            off_names = [norm(x) for x in ostruct["entries"]]
            # cross-slot presence
            other = []
            for s2, sl2, o2 in slots_for(o):
                if (s2, sl2) != (side, slot):
                    other += [norm(x) for x in o2["entries"]]
            if not cap_names and not off_names and off_status in ("printed", "printed_empty"):
                result = "match_empty"
            elif off_status != "printed":
                result = "unverified"
            else:
                if sorted(cap_names) == sorted(off_names):
                    result = "match"
                else:
                    result = "mismatch"
            for n in cap_names:
                if result == "mismatch" and n in other:
                    note = "captured name appears in the other slot of the official book"
                    break
            else:
                note = ""
            if result == "match_empty":
                counts["match"] += 1
            elif result in counts:
                counts[result] += 1
            rows.append({
                "game_id": gid, "side": side, "slot": slot,
                "captured": "; ".join(cap_names), "official": "; ".join(off_names),
                "official_status": off_status, "result": result,
                "only_in_captured": "; ".join(sorted(set(cap_names) - set(off_names))),
                "only_in_official": "; ".join(sorted(set(off_names) - set(cap_names))),
                "note": note,
            })
        per_game[gid] = counts

    with (REV / "comparison_w10_inactives.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # reserve list: captured events vs official rows
    tx = json.loads(RAW_TX.read_text())["events"]
    cap_res = [e for e in tx if "reserve" in e.get("category", "") or "Reserve" in e.get("transaction", "")]
    off_res = json.loads(OFFICIAL.read_text())["reserve_list_nov_2026"]["rows"]
    cap_keys = {(e["date"], norm(e["player"])) for e in cap_res}
    off_keys = {(r["date"], norm(r["player"])) for r in off_res}
    in_window = {k for k in cap_keys if "2026-11-14" <= k[0] <= "2026-11-18"}
    res_rows = []
    for r in off_res:
        k = (r["date"], norm(r["player"]))
        res_rows.append({"date": r["date"], "team": r["team"], "player": r["player"],
                         "in_captured_file": "yes" if k in cap_keys else "no"})
    with (REV / "comparison_reserve_list.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res_rows[0].keys()))
        w.writeheader()
        w.writerows(res_rows)
    reserve_summary = {
        "official_rows": len(off_res),
        "official_rows_11_14_to_11_18": sum(1 for r in off_res if "2026-11-14" <= r["date"] <= "2026-11-18"),
        "captured_reserve_events": len(cap_res),
        "captured_events_11_14_to_11_18": len(in_window),
        "official_rows_found_in_captured": sum(1 for r in res_rows if r["in_captured_file"] == "yes"),
        "captured_only_not_on_official_page": sorted(
            f"{d} {p}" for d, p in (cap_keys - off_keys)),
    }

    # reg11 IND/HOU vs week11_injuries.csv (field-level: injury, practice, game)
    off_reg = json.loads(OFFICIAL.read_text())["reg11_IND_HOU"]["rows"]
    cap_reg = {}
    with REG11_CSV.open() as f:
        for r in csv.DictReader(f):
            cap_reg.setdefault((r["team"], r["player"].strip()), r)
    reg_rows = []
    fields_ok = 0
    for r in off_reg:
        hit = cap_reg.get((r["team"], r["player"].strip()))
        if hit is None:
            reg_rows.append({"team": r["team"], "player": r["player"], "in_captured_csv": "no",
                             "field_result": "unverified", "diff": "not in captured CSV"})
            continue
        diffs = []
        for off_key, cap_key, label in (("injury", "injury", "injury"),
                                        ("practice", "practice_status", "practice"),
                                        ("game", "game_status", "game")):
            o = r[off_key].strip()
            c = (hit.get(cap_key) or "").strip()
            if o != c:
                diffs.append(f"{label}: official='{o}' captured='{c}'")
        if not diffs:
            fields_ok += 1
        reg_rows.append({"team": r["team"], "player": r["player"], "in_captured_csv": "yes",
                         "field_result": "match" if not diffs else "mismatch",
                         "diff": " | ".join(diffs),
                         "official_injury": r["injury"], "official_practice": r["practice"],
                         "official_game": r["game"],
                         "captured_injury": hit.get("injury", ""),
                         "captured_practice": hit.get("practice_status", ""),
                         "captured_game": hit.get("game_status", ""),
                         "captured_cross_check_flag": hit.get("cross_check_flag", ""),
                         "source_url": "https://www.nfl.com/injuries/league/2026/reg11"})
    keys = ["team", "player", "in_captured_csv", "field_result", "diff", "official_injury",
            "official_practice", "official_game", "captured_injury", "captured_practice",
            "captured_game", "captured_cross_check_flag", "source_url"]
    with (REV / "comparison_reg11_IND_HOU.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(reg_rows)

    # snap rows WAS@NYG: captured week10_snap_depth.csv vs official playtime rows
    off_snap = json.loads(OFFICIAL.read_text())["snap_playtime_WAS_NYG"]["rows"]
    cap_snap = {}
    with SNAP_CSV.open() as f:
        for r in csv.DictReader(f):
            if r["game_id"] == "WAS@NYG":
                cap_snap[(r["team"], r["player"])] = r
    snap_rows = []
    snap_match = 0
    for o in off_snap:
        c = cap_snap.get((o["team"], o["player"]))
        if c is None:
            snap_rows.append({"team": o["team"], "player": o["player"], "official_snaps": o["snaps"],
                              "official_pct": o["pct"], "captured_snaps": "", "captured_pct": "",
                              "result": "not in captured snap CSV"})
            continue
        ok = str(o["snaps"]) == c["snaps"] and str(o["pct"]) == c["snap_pct"]
        snap_match += ok
        snap_rows.append({"team": o["team"], "player": o["player"], "official_snaps": o["snaps"],
                          "official_pct": o["pct"], "captured_snaps": c["snaps"],
                          "captured_pct": c["snap_pct"], "result": "match" if ok else "mismatch"})
    with (REV / "comparison_snap_WAS_NYG.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(snap_rows[0].keys()))
        w.writeheader()
        w.writerows(snap_rows)
    snap_out = snap_rows

    summary = {
        "method": "scripts/reverify_compare.py; see module docstring for rules",
        "per_game": per_game,
        "totals": {k: sum(v[k] for v in per_game.values()) for k in ("match", "mismatch", "unverified")},
        "reserve": reserve_summary,
        "reg11_IND_HOU": {
            "official_rows": len(reg_rows),
            "in_captured_csv": sum(1 for r in reg_rows if r["in_captured_csv"] == "yes"),
            "rows_all_fields_match": fields_ok,
            "rows_with_field_mismatch": sum(1 for r in reg_rows if r.get("field_result") == "mismatch"),
        },
        "snap_WAS_NYG": {
            "official_rows": len(snap_out),
            "match": snap_match,
            "not_in_captured_csv": sum(1 for r in snap_out if r["result"].startswith("not in")),
        },
    }
    (REV / "comparison_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
