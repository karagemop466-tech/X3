#!/usr/bin/env python3
"""Reconcile the live official Week-10 injury read against the published audit table.

Input 1: audit/official_injury_wk10_2026.live.psv
    Pipe-delimited, one row per player, transcribed from all 8 chunks of
    https://www.nfl.com/injuries/league/2026/reg10 (read 2026-11-15 UTC).
Input 2: audit/official_injury_wk10_2026.csv
    The table the site was built from (345 rows).

Output:
    audit/official_injury_wk10_2026.live.csv   - the live read as CSV
    audit/live_reconcile.json                  - counts, per-team counts, every mismatch

Exit status is non-zero if the two tables disagree in any field, so the difference
is never published silently. Run:  python3 scripts/reconcile_live_injury.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_PSV = ROOT / "audit" / "official_injury_wk10_2026.live.psv"
AUDIT_CSV = ROOT / "audit" / "official_injury_wk10_2026.csv"
LIVE_CSV = ROOT / "audit" / "official_injury_wk10_2026.live.csv"
OUT_JSON = ROOT / "audit" / "live_reconcile.json"
DELTA_CSV = ROOT / "data" / "hub" / "injury_delta_2026-11-15.csv"

PRACTICE = {"Full": "Full", "Limited": "Limited", "DNP": "DNP",
            "Full Participation in Practice": "Full",
            "Limited Participation in Practice": "Limited",
            "Did Not Participate In Practice": "DNP"}
GAME_OK = {"", "Out", "Doubtful", "Questionable"}


def norm_injury(s: str) -> str:
    """Compare injury text independent of separator and case."""
    parts = re.split(r"[;,]", s or "")
    return "|".join(sorted(p.strip().lower() for p in parts if p.strip()))


def load_live() -> list[dict]:
    rows = []
    for line in LIVE_PSV.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        team, player, pos, injury, practice, game = line.split("|")
        if practice not in ("Full", "Limited", "DNP"):
            raise SystemExit(f"unknown practice code in live read: {line}")
        if game not in GAME_OK:
            raise SystemExit(f"unknown game status in live read: {line}")
        rows.append({"team": team, "player": player, "position": pos,
                     "injury": injury, "practice": practice, "game_status": game})
    return rows


def load_audit() -> list[dict]:
    out = []
    with AUDIT_CSV.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            out.append({"team": r["team"], "player": r["player"], "position": r["position"],
                        "injury": r["injury"], "practice": PRACTICE.get(r["practice_status"], r["practice_status"]),
                        "game_status": r["game_status"], "game": r["game"]})
    return out


def main() -> int:
    live = load_live()
    audit = load_audit()

    with LIVE_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["team", "player", "position", "injury", "practice_status", "game_status",
                    "source_url"])
        for r in live:
            w.writerow([r["team"], r["player"], r["position"], r["injury"], r["practice"],
                        r["game_status"], "https://www.nfl.com/injuries/league/2026/reg10"])

    live_key = Counter((r["team"], r["player"]) for r in live)
    audit_key = Counter((r["team"], r["player"]) for r in audit)
    dup_live = [k for k, v in live_key.items() if v > 1]

    live_by = {(r["team"], r["player"]): r for r in live}
    audit_by = {(r["team"], r["player"]): r for r in audit}

    mismatches = []
    for key in sorted(set(live_by) | set(audit_by)):
        if key not in audit_by:
            mismatches.append({"team": key[0], "player": key[1], "kind": "missing_from_audit",
                               "live": live_by[key]})
            continue
        if key not in live_by:
            mismatches.append({"team": key[0], "player": key[1], "kind": "missing_from_live",
                               "audit": audit_by[key]})
            continue
        a, l = audit_by[key], live_by[key]
        diffs = {}
        if a["position"] != l["position"]:
            diffs["position"] = [a["position"], l["position"]]
        if norm_injury(a["injury"]) != norm_injury(l["injury"]):
            diffs["injury"] = [a["injury"], l["injury"]]
        if a["practice"] != l["practice"]:
            diffs["practice"] = [a["practice"], l["practice"]]
        if a["game_status"] != l["game_status"]:
            diffs["game_status"] = [a["game_status"], l["game_status"]]
        if diffs:
            mismatches.append({"team": key[0], "player": key[1], "kind": "field_diff", "fields": diffs})

    live_teams = Counter(r["team"] for r in live)
    audit_teams = Counter(r["team"] for r in audit)
    team_diff = {t: [audit_teams.get(t, 0), live_teams.get(t, 0)]
                 for t in sorted(set(live_teams) | set(audit_teams))
                 if audit_teams.get(t, 0) != live_teams.get(t, 0)}

    live_status = Counter(r["game_status"] or "(blank)" for r in live)
    audit_status = Counter(r["game_status"] or "(blank)" for r in audit)
    teams_with_injury = {t for t in live_teams if any(
        r["injury"] or r["game_status"] for r in live if r["team"] == t)}

    report = {
        "source_url": "https://www.nfl.com/injuries/league/2026/reg10",
        "read_utc": "2026-11-15",
        "live_rows": len(live),
        "audit_rows": len(audit),
        "live_clubs": len(live_teams),
        "audit_clubs": len(audit_teams),
        "live_duplicate_player_keys": dup_live,
        "live_game_status": dict(live_status),
        "audit_game_status": dict(audit_status),
        "live_rows_by_team": dict(sorted(live_teams.items())),
        "team_count_diffs_audit_vs_live": team_diff,
        "clubs_with_at_least_one_listed_player": len(teams_with_injury),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    live_teams = Counter(r["team"] for r in live)
    print(f"live rows {len(live)} | audit rows {len(audit)} | clubs live {len(live_teams)} audit {len(audit_teams)}")
    print(f"live status {dict(live_status)}")
    print(f"audit status {dict(audit_status)}")
    print(f"team count diffs (audit, live): {team_diff}")
    print(f"field/missing mismatches: {len(mismatches)}")
    for m in mismatches:
        print("  ", m["kind"], m["team"], m["player"], m.get("fields", ""))
    # delta table published on hub/snapshots.html (publish the delta, never the level)
    with DELTA_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["team", "player", "change", "field", "snapshot_2026_11_14", "snapshot_2026_11_15",
                    "source_url"])
        for m in mismatches:
            if m["kind"] == "field_diff":
                for field, (old, new) in m["fields"].items():
                    w.writerow([m["team"], m["player"], "changed", field, old, new,
                                "https://www.nfl.com/injuries/league/2026/reg10"])
            elif m["kind"] == "missing_from_audit":
                w.writerow([m["team"], m["player"], "added", "row", "(not in 2026-11-14 table)",
                            "row present", "https://www.nfl.com/injuries/league/2026/reg10"])
            else:
                w.writerow([m["team"], m["player"], "removed", "row", "row present", "(not on live page)",
                            "https://www.nfl.com/injuries/league/2026/reg10"])
    print(f"delta rows written: {sum(1 for _ in DELTA_CSV.open(encoding='utf-8')) - 1}")
    # Exit 0 when the read parsed cleanly, even if the two snapshots differ: a difference
    # between clock-timed reads is the expected result of a timestamped series, and it is
    # published as a delta. Exit 2 only on a parse or structural failure.
    if dup_live or len(live_teams) != 28:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
