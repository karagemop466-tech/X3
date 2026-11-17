#!/usr/bin/env python3
"""Drift alarm for every parser/dataset in the repository (RD-03, arena/6259c7b0-x3).

"Add a drift alarm to every scraper: pin each parser to expected row counts and
required fields; fail the build loudly when a field goes missing rather than
publishing a blank."

The pins are frozen in readiness/data/drift_pins.json. Each pin records the dataset
path, the exact or minimum row count, the required fields per row, value pins (e.g.
32 clubs) and the official source the capture came from. Any mismatch prints a loud
FAIL block naming the dataset, the field and the observed value, and exits 1 so CI
fails the build - a blank page can never be published silently.

Output: readiness/data/drift_report.json (also rendered on readiness/drift-alarms.html).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PINS = ROOT / "readiness" / "data" / "drift_pins.json"
REPORT = ROOT / "readiness" / "data" / "drift_report.json"


def load_dataset(rel, kind):
    p = ROOT / rel
    if not p.exists():
        return None, f"file missing: {rel}"
    if kind == "json":
        return json.loads(p.read_text()), None
    if kind == "csv":
        with open(p, newline="") as f:
            return list(csv.DictReader(f)), None
    if kind == "text":
        lines = [l for l in p.read_text().splitlines() if l.strip()]
        return lines, None
    return None, f"unknown kind {kind}"


def get_rows(data, rows_key):
    if rows_key:
        return data.get(rows_key, []) if isinstance(data, dict) else data
    return data


def check_pin(pin):
    """Return list of failure strings for one pin."""
    fails = []
    data, err = load_dataset(pin["path"], pin["kind"])
    if err:
        return [f"{pin['id']}: {err}"]
    if data is None:
        return [f"{pin['id']}: empty dataset"]
    rows = get_rows(data, pin.get("rows_key"))

    if "exact_rows" in pin and len(rows) != pin["exact_rows"]:
        fails.append(f"{pin['id']}: row count drifted - expected {pin['exact_rows']}, "
                     f"got {len(rows)} ({pin['path']}). If the source genuinely changed, "
                     f"review the capture and update the pin deliberately.")
    if "min_rows" in pin and len(rows) < pin["min_rows"]:
        fails.append(f"{pin['id']}: row count below minimum - expected >= {pin['min_rows']}, "
                     f"got {len(rows)} ({pin['path']})")

    if pin.get("value_pins"):
        for key, expected in pin["value_pins"].items():
            node = data
            found = True
            for part in key.split("."):
                if isinstance(node, dict) and part in node:
                    node = node[part]
                elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
                    node = node[int(part)]
                else:
                    found = False
                    break
            if not found or node != expected:
                fails.append(f"{pin['id']}: value pin {key} expected {expected!r}, "
                             f"got {str(node)[:120]!r} ({pin['path']})")

    req = pin.get("required_fields") or []
    if isinstance(rows, dict):        # dict-shaped dataset: no row-level field checks
        rows = []
    if req and pin["kind"] == "csv":
        if rows:
            missing_cols = [c for c in req if c not in rows[0]]
            if missing_cols:
                fails.append(f"{pin['id']}: required columns missing - {missing_cols} "
                             f"({pin['path']})")
        bad = []
        for i, row in enumerate(rows[:pin.get("field_check_rows", 10**9)]):
            for c in req:
                if c in row and (row[c] is None or str(row[c]).strip() == ""):
                    bad.append(f"row {i + 2} field {c} blank")
                    if len(bad) >= 5:
                        break
            if len(bad) >= 5:
                break
        if bad:
            fails.append(f"{pin['id']}: required fields blank - {bad} ({pin['path']})")
    elif req and rows:
        bad = []
        for i, row in enumerate(rows[:pin.get("field_check_rows", 10**9)]):
            if not isinstance(row, dict):
                bad.append(f"row {i} not an object")
                continue
            miss = [c for c in req if row.get(c) in (None, "")]
            if miss:
                bad.append(f"row {i} missing {miss}")
                if len(bad) >= 5:
                    break
            if len(bad) >= 5:
                break
        if bad:
            fails.append(f"{pin['id']}: required fields missing/blank - {bad} "
                         f"({pin['path']})")

    for cond in pin.get("conditional_required") or []:
        fields = cond["fields"]
        wv = cond.get("when") or {}
        wkey, wval = next(iter(wv.items())) if wv else (None, None)
        bad = []
        for i, row in enumerate(rows[:pin.get("field_check_rows", 10**9)]):
            if not isinstance(row, dict):
                continue
            if wkey is not None:
                have = row.get(wkey)
                if str(wval).startswith(">"):
                    try:
                        hit = float(have) > float(str(wval)[1:])
                    except (TypeError, ValueError):
                        hit = False
                elif wkey == "rank_is_number":
                    try:
                        float(have); hit = True
                    except (TypeError, ValueError):
                        hit = False
                else:
                    hit = str(have) == str(wval)
                if not hit:
                    continue
            miss = [c for c in fields if row.get(c) in (None, "")]
            if miss:
                ident = (row.get("market_id") or row.get("game_id")
                         or row.get("strategy") or row.get("pair") or f"row {i + 2}")
                bad.append(f"{ident} missing {miss}")
                if len(bad) >= 5:
                    break
        if bad:
            fails.append(f"{pin['id']}: conditional required fields blank when "
                         f"{wkey}={wval} - {bad} ({pin['path']})")

    if pin.get("allowed_status_vocab") and rows:
        vocab = set(pin["allowed_status_vocab"])
        field = pin.get("status_field", "status")
        bad = sorted({str(r.get(field)) for r in rows
                      if r.get(field) not in (None, "") and str(r.get(field)) not in vocab})
        if bad:
            fails.append(f"{pin['id']}: status vocabulary drift - unexpected values {bad} "
                         f"({pin['path']})")

    if pin.get("all_source_hosts"):
        hosts = tuple(pin["all_source_hosts"])
        field = pin.get("source_field", "source")
        bad = 0
        for r in rows:
            src = str(r.get(field, "")) if isinstance(r, dict) else str(r)
            if src and not src.startswith(hosts):
                bad += 1
        if bad:
            fails.append(f"{pin['id']}: {bad} rows carry a non-official source host "
                         f"(expected {hosts}) ({pin['path']})")
    return fails


def main():
    pins = json.loads(PINS.read_text())
    results = []
    all_fails = []
    for pin in pins["pins"]:
        fails = check_pin(pin)
        results.append({
            "id": pin["id"], "dataset": pin["path"], "kind": pin["kind"],
            "source": pin.get("official_source", ""),
            "status": "FAIL" if fails else "PASS",
            "alarms": fails,
            "pins": {k: v for k, v in pin.items()
                     if k in ("exact_rows", "min_rows", "required_fields", "value_pins",
                              "allowed_status_vocab")},
        })
        all_fails.extend(fails)

    report = {
        "as_of": pins.get("as_of", ""),
        "generated_by": "scripts/drift_alarm.py",
        "policy": ("Every parser output is pinned to expected row counts and required "
                   "fields. Any drift fails the build loudly instead of publishing a "
                   "blank. Pins change only by a reviewed, deliberate commit."),
        "datasets": len(results),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "failed": sum(1 for r in results if r["status"] == "FAIL"),
        "results": results,
        "source": pins.get("register_source", ""),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1) + "\n")

    if all_fails:
        print("!! DRIFT ALARM - the build must fail loudly (RD-03) !!")
        for f in all_fails:
            print(f"  DRIFT: {f}")
        print(f"{report['failed']} of {report['datasets']} pinned datasets drifted. "
              f"Report: readiness/data/drift_report.json")
        return 1
    print(f"DRIFT CHECK PASSED - {report['datasets']} pinned datasets, "
          f"{report['passed']} pass, 0 alarms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
