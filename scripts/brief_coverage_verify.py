#!/usr/bin/env python3
"""Verify analysis/brief-coverage-2026-11-19.csv against the repository.

Each row must:
  * have a unique id and a status of Present, Partial or Blocked;
  * name an evidence_path that exists in the repository;
  * if evidence_check is set, contain that exact substring in the evidence file;
  * if source_url is set, contain that exact URL in the evidence file, and the URL
    must be on an official host (nfl.com, operations.nfl.com, media.nfl.com,
    static.www.nfl.com, api.weather.gov);
  * a Present row must carry evidence_check or source_url;
  * every non-Present row must state a gap.
Exit status is non-zero on any failure, so a missing file fails loudly.
"""
import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "analysis" / "brief-coverage-2026-11-19.csv"
STATUSES = {"Present", "Partial", "Blocked"}
OFFICIAL_HOSTS = {"www.nfl.com", "operations.nfl.com", "media.nfl.com",
                  "static.www.nfl.com", "api.weather.gov"}


def main() -> int:
    failures = []
    with REGISTER.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < 30:
        failures.append(f"register has {len(rows)} rows; expected at least 30")
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        failures.append("duplicate ids")

    counts = {s: 0 for s in STATUSES}
    for r in rows:
        rid = r["id"]
        status = r["status"]
        if status not in STATUSES:
            failures.append(f"{rid}: bad status {status!r}")
            continue
        counts[status] += 1
        path = ROOT / r["evidence_path"]
        if not path.is_file():
            failures.append(f"{rid}: evidence file missing: {r['evidence_path']}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        check = r["evidence_check"].strip()
        if check and check not in text:
            failures.append(f"{rid}: substring {check!r} not found in {r['evidence_path']}")
        url = r["source_url"].strip()
        if url:
            host = urlparse(url).netloc
            if host not in OFFICIAL_HOSTS:
                failures.append(f"{rid}: non-official source host {host!r}")
            if url not in text:
                failures.append(f"{rid}: source URL {url} not found in {r['evidence_path']}")
        if status == "Present" and not (check or url):
            failures.append(f"{rid}: Present row has neither evidence_check nor source_url")
        if status != "Present" and not r["gap"].strip():
            failures.append(f"{rid}: {status} row must state a gap")

    print(f"brief_coverage_verify: {len(rows)} rows "
          f"(Present {counts['Present']}, Partial {counts['Partial']}, Blocked {counts['Blocked']})")
    for f in failures:
        print("FAIL", f)
    print("PASS" if not failures else f"FAILED ({len(failures)})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
