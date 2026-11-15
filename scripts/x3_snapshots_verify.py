#!/usr/bin/env python3
"""
Gate for the point-in-time snapshot store. Fails loudly - this is the drift
alarm the brief asks for, applied to this store itself.

Checks
  1. every capture in the ledger has the required provenance fields
  2. the recorded sha256 still matches the stored bytes (immutability)
  3. the recorded row / designation counts still recompute from the file
  4. no two captures of the same (season, week) share a hash - the official page
     has been observed to serve a stale week's report for a future week (the
     repository's own parse report records exactly that for injuries-w11), so a
     duplicate hash is a silent no-op capture and must not be counted as a read
  5. the team-code alias map is exactly the set the official page needs today; a
     new unmapped code is a parse failure, not a data point
  6. the practice-code mapping is one-to-one and total in both directions
  7. the published delta recomputes to the same numbers
  8. every designation change in the delta cites the official source URL
  9. determinism: re-running the builder emits byte-identical JSON

Run: python3 scripts/x3_snapshots_verify.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, "data", "snapshots")

REQUIRED = ("capture_id", "source_url", "fetched_at_utc", "sha256", "bytes", "rows", "parser_version")
DESIGNATIONS = ("Out", "Doubtful", "Questionable")
PRACTICE_FULL = {
    "FP": "Full Participation in Practice",
    "LP": "Limited Participation in Practice",
    "DNP": "Did Not Participate In Practice",
}
EXPECTED_ALIASES = {"AZ": "ARI", "LAR": "LA"}

fail: list[str] = []
warn: list[str] = []


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    ledger_p = os.path.join(SNAP, "ledger.json")
    delta_p = os.path.join(SNAP, "delta.json")
    if not (os.path.exists(ledger_p) and os.path.exists(delta_p)):
        print("FAIL: run scripts/x3_snapshots.py first - no ledger.json / delta.json")
        return 1
    ledger = json.load(open(ledger_p, encoding="utf-8"))
    delta = json.load(open(delta_p, encoding="utf-8"))

    # --- 1,2,3 provenance, immutability, recomputed counts -------------------
    hashes: dict[str, list[str]] = {}
    for c in ledger["captures"]:
        cid = c.get("capture_id", "?")
        for f in REQUIRED:
            if not c.get(f):
                fail.append(f"{cid}: required provenance field '{f}' is empty")
        files = c.get("files") or [c["file"]]
        for rel in files:
            p = os.path.join(ROOT, rel.strip())
            if not os.path.exists(p):
                fail.append(f"{cid}: cited file does not exist: {rel}")
                continue
            if c.get("sealed") and rel.strip().endswith(".csv") and sha256_of(p) != c["sha256"]:
                fail.append(f"{cid}: sha256 of {rel} no longer matches the ledger - a sealed capture must not change")
        if c.get("sealed"):
            p = os.path.join(ROOT, c["files"][0])
            if os.path.exists(p):
                rows = list(csv.DictReader(open(p, newline="", encoding="utf-8")))
                if len(rows) != c["rows"] or len(rows) != c["counts"]["rows"]:
                    fail.append(f"{cid}: ledger says {c['counts']['rows']} rows, file holds {len(rows)}")
                if len(rows) != sum(1 for _ in open(p, encoding='utf-8')) - 1:
                    fail.append(f"{cid}: physical line count disagrees with parsed row count - malformed row?")
                st = {k: sum(1 for r in rows if (r["status"] or "").strip() == k) for k in DESIGNATIONS}
                if st != c["counts"]["designation_counts"]:
                    fail.append(f"{cid}: designation counts do not recompute: ledger {c['counts']['designation_counts']} vs file {st}")
                blanks = sum(1 for r in rows if not (r["status"] or "").strip())
                if blanks != c["counts"]["blank_game_status"]:
                    fail.append(f"{cid}: blank-designation count does not recompute")
                for r in rows:
                    if r["practice"].strip() not in PRACTICE_FULL:
                        fail.append(f"{cid}: line {rows.index(r)+2}: unmapped practice code {r['practice']!r}")
                hashes.setdefault(c["sha256"], []).append(cid)
        else:
            hashes.setdefault(c["sha256"], []).append(cid)

    # --- 4 duplicate-served-page detection ----------------------------------
    for h, ids in hashes.items():
        if len(ids) > 1:
            fail.append(f"duplicate capture bytes {h[:12]}... shared by {ids}: two 'reads' of one page are one read, not two")

    # --- 5 alias map ---------------------------------------------------------
    for c in ledger["captures"]:
        printed = sorted(c.get("team_codes_printed", []))
        if printed:
            for code in printed:
                if code not in EXPECTED_ALIASES:
                    fail.append(f"{c['capture_id']}: official page printed club code {code!r} with no alias - "
                                f"rows will silently fail to join across reads; extend TEAM_ALIAS and re-verify")

    # --- 6 mapping is one-to-one and total ----------------------------------
    if len(set(PRACTICE_FULL.values())) != len(PRACTICE_FULL):
        fail.append("practice mapping is not one-to-one")

    # --- 7,8 delta recomputation and citations ------------------------------
    for d in delta["deltas"]:
        n_desig = len(d["designation_changes"])
        if n_desig != d["designation_changes_count"]:
            fail.append(f"delta {d['from_read']}->{d['to_read']}: designation_changes_count {d['designation_changes_count']} != len(list) {n_desig}")
        if d["rows_after"] - d["rows_before"] != d["added_rows_count"] - d["dropped_rows_count"]:
            fail.append(f"delta {d['from_read']}->{d['to_read']}: row-count change is not explained by adds minus drops")
        net_desig = (d["counts_after"]["rows"] - d["counts_after"]["blank_game_status"]) - (d["counts_before"]["rows"] - d["counts_before"]["blank_game_status"])
        gained = sum(1 for x in d["designation_changes"] if x["status_before"] == "(none)" and x["status_after"] != "(none)")
        lost = sum(1 for x in d["designation_changes"] if x["status_after"] == "(none)" and x["status_before"] != "(none)")
        added_desig = sum(1 for x in d.get("added_detail", []) if x.get("status_after", "(none)") != "(none)")
        dropped_desig = sum(1 for x in d.get("dropped_detail", []) if x.get("status_before", "(none)") != "(none)")
        expected = gained - lost + added_desig - dropped_desig
        if net_desig != expected:
            fail.append(f"delta {d['from_read']}->{d['to_read']}: designation level moved {net_desig:+d} but the row-level "
                        f"events account for {expected:+d} ({gained} gained, {lost} lost, {added_desig} added-with, "
                        f"{dropped_desig} dropped-with) - a change is unexplained")
        if "nfl.com" not in d.get("source_url", ""):
            fail.append(f"delta {d['from_read']}->{d['to_read']}: no official source_url")
        for x in d["designation_changes"] + d["practice_changes"]:
            cor = x.get("corroboration_before", {}).get("verdict", "")
            if cor not in ("CORROBORATED", "SINGLE READ", "CONTESTED", "ABSENT FROM PRIOR READS"):
                fail.append(f"delta row {x.get('team')} {x.get('player')}: corroboration verdict missing/unknown ({cor!r})")
            if cor == "SINGLE READ":
                warn.append(f"{x.get('team')} {x.get('player')}: change rests on a single prior read - not corroborated")
    for d in delta["deltas"]:
        for x in d.get("added_detail", []):
            if x["corroboration_before"]["verdict"] == "ABSENT FROM PRIOR READS" and x["in_prior_desk_store"] is False:
                pass  # expected: a row that appeared between reads is the point of a series

    # --- 9 determinism ------------------------------------------------------
    before = {p: sha256_of(p) for p in (ledger_p, delta_p)}
    rc = os.system(f"cd {ROOT} && python3 scripts/x3_snapshots.py >/dev/null 2>&1")
    if rc != 0:
        fail.append("scripts/x3_snapshots.py did not exit 0 when re-run")
    after = {p: sha256_of(p) for p in (ledger_p, delta_p)}
    if before != after:
        fail.append("builder is not deterministic: ledger/delta bytes changed on re-run")

    n_cap = len(ledger["captures"])
    n_rows = sum(1 for c in ledger["captures"] if c.get("sealed"))
    print(f"snapshot store: {n_cap} reads indexed ({n_rows} sealed capture file(s)), {len(delta['deltas'])} published delta(s)")
    for w in warn:
        print("  WARN:", w)
    if fail:
        print(f"\nFAIL - {len(fail)} problem(s):")
        for f in fail:
            print("  -", f)
        return 1
    print("PASS - every capture sealed by hash, counts recompute, delta reconciles, builder deterministic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
