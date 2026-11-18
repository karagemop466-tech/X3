#!/usr/bin/env python3
"""Gate for the week11 module (session arena/40cd3b17-x3, M2).

Checks, in order:
  V1  the freshness audit is clean (0 MISMATCH rows in data/week11/freshness_audit.csv)
  V2  the audit summary agrees with the CSV (row counts, league totals)
  V3  the site rebuilds deterministically (byte-identical pages)
  V4  every capture file matches its sha256 in the manifest
  V5  the probe log is chronologically ordered and each probe names the endpoint
  V6  every emitted page exists and carries the module footer (built, not stale)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "week11")
SITE = os.path.join(ROOT, "week11")
PAGES = ["index.html", "freshness.html", "freshness-detail.html", "report.html",
         "sources.html", "flagged.html"]

fail = []


def check(cond, msg):
    if not cond:
        fail.append(msg)


def rd(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    audit = rd(os.path.join(DATA, "freshness_audit.csv"))
    summary = json.load(open(os.path.join(DATA, "freshness_summary.json"), encoding="utf-8"))
    probes = rd(os.path.join(DATA, "reg11_probes.csv"))

    # V1: audit clean
    mism = [r for r in audit if r["verdict"] == "MISMATCH"]
    check(not mism, f"V1 freshness audit has {len(mism)} MISMATCH rows")

    # V2: summary agrees with the CSV
    check(summary["audit_rows"] == len(audit),
          f"V2 summary.audit_rows {summary['audit_rows']} != csv rows {len(audit)}")
    check(summary["mismatches"] == [],
          f"V2 summary lists mismatches: {summary['mismatches']}")
    check(summary["standings_rows"] == 32, "V2 standings read must cover 32 clubs")
    check(summary["standings_league_pf"] == summary["standings_league_pa"],
          "V2 league sum PF must equal sum PA on today's read")

    # V3: deterministic rebuild
    before = {p: open(os.path.join(SITE, p), "rb").read() for p in PAGES}
    r1 = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "week11_build.py")],
                        capture_output=True, text=True)
    check(r1.returncode == 0, f"V3 rebuild failed: {r1.stderr[-200:]}")
    for p in PAGES:
        after = open(os.path.join(SITE, p), "rb").read()
        check(after == before[p], f"V3 {p} is not the current output of week11_build.py")

    # V4: capture hashes
    manifest = rd(os.path.join(DATA, "captures", "manifest.csv"))
    for m in manifest:
        path = os.path.join(DATA, "captures", m["file"])
        check(os.path.exists(path), f"V4 manifest lists missing file {m['file']}")
        if os.path.exists(path):
            h = hashlib.sha256(open(path, "rb").read()).hexdigest()
            check(h == m["sha256"], f"V4 sha256 mismatch for {m['file']}")

    # V5: probe log hygiene
    times = [p["probe_utc"] for p in probes]
    check(times == sorted(times), "V5 probe log must be chronologically ordered")
    check(all(p["url"].startswith("https://www.nfl.com/") for p in probes),
          "V5 every probe must name the official endpoint")

    # V6: pages present + fresh
    for p in PAGES:
        path = os.path.join(SITE, p)
        check(os.path.exists(path), f"V6 missing page {p}")
        if os.path.exists(path):
            body = open(path, encoding="utf-8").read()
            check("week11 module" in body, f"V6 {p} was not written by week11_build.py")

    print(f"week11_verify: {len(audit)} audit rows, {len(probes)} probes, "
          f"{len(manifest)} hashed captures")
    if fail:
        for f in fail:
            print("FAIL", f)
        raise SystemExit(1)
    print("PASS - audit clean, build deterministic, captures sealed, pages current")


if __name__ == "__main__":
    main()
