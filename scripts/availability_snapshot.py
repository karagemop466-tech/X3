#!/usr/bin/env python3
"""Scheduled immutable availability snapshots (RD-06, session arena/6259c7b0-x3).

Runs on a GitHub-hosted runner (the authoring sandbox cannot reach nfl.com; the
runner can - the same pattern the desk-capture workflow established).

Each run captures the CURRENT official league injury report page (which is always
the live week's report) and the league schedule landing page, stores the RAW HTML
under readiness/data/history/<UTC-date>/, appends a SHA-256 + size + HTTP status row
to the append-only manifest, and prints loud SCHEMA CHANGE alerts when the extracted
table-row count moves more than 20% against the previous capture.

Freshness: if the newest capture in the manifest is older than 4 days, the script
exits 1 with a FRESHNESS ALERT (this is the alerting half of the requirement).

Network failure is recorded (http status 000) and does not exit nonzero unless
STRICT=1, so a blocked runner cannot silently wipe the manifest - but it IS printed
loudly. Parser pins (scripts/drift_alarm.py) fail the build when stored datasets
lose required fields.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "readiness" / "data" / "history"
MANIFEST = HIST / "manifest.csv"
TARGETS = [
    ("league-injury-report", "https://www.nfl.com/injuries/"),
    ("league-schedule", "https://www.nfl.com/schedules/"),
]
MAX_AGE_DAYS = 4.0
SCHEMA_DELTA = 0.20
UA = "Mozilla/5.0 (X3 research snapshot; contact: repo owner)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.getcode(), resp.read()


def row_count(html_text):
    """A crude, parser-independent size signal for schema-change detection."""
    return len(re.findall(r"<tr[^>]*>", html_text))


def prev_counts():
    """Last stored row-count per slug, from the newest history dirs."""
    out = {}
    if not HIST.exists():
        return out
    for day in sorted((d for d in HIST.iterdir() if d.is_dir()), reverse=True):
        meta = day / "meta.json"
        if meta.exists():
            try:
                for slug, rc in json.loads(meta.read_text())["row_counts"].items():
                    out.setdefault(slug, rc)
            except (json.JSONDecodeError, KeyError):
                pass
        if out:
            break
    return out


def manifest_append(row):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    new_file = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        if new_file:
            f.write("captured_at_utc,slug,url,http_status,bytes,sha256,row_count\n")
        f.write(",".join(str(x) for x in row) + "\n")


def main():
    now = datetime.now(timezone.utc)
    day_dir = HIST / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    prev = prev_counts()
    meta = {"captured_at_utc": now.isoformat(timespec="seconds"), "row_counts": {},
            "alerts": []}
    had_error = False

    for slug, url in TARGETS:
        try:
            status, body = fetch(url)
        except Exception as exc:                      # noqa: BLE001 - record, don't crash
            had_error = True
            print(f"!! CAPTURE FAILED for {url}: {exc} (recorded with status 000)")
            manifest_append([now.isoformat(timespec="seconds"), slug, url, "000", 0, "", 0])
            meta["alerts"].append(f"fetch failed: {url}: {exc}")
            continue
        text = body.decode("utf-8", errors="replace")
        rc = row_count(text)
        sha = hashlib.sha256(body).hexdigest()
        (day_dir / f"{slug}.html").write_text(text, encoding="utf-8")
        manifest_append([now.isoformat(timespec="seconds"), slug, url, status,
                         len(body), sha, rc])
        meta["row_counts"][slug] = rc
        print(f"captured {slug}: http {status}, {len(body)} bytes, sha256 {sha[:12]}..., "
              f"{rc} table rows")
        if slug in prev and prev[slug]:
            delta = abs(rc - prev[slug]) / prev[slug]
            if delta > SCHEMA_DELTA:
                msg = (f"SCHEMA CHANGE ALERT: {slug} row count moved "
                       f"{prev[slug]} -> {rc} ({delta:.0%})")
                print(f"!! {msg}")
                meta["alerts"].append(msg)

    (day_dir / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    # freshness alert
    if MANIFEST.exists():
        import csv
        with open(MANIFEST, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["http_status"] == "200"]
        if rows:
            newest = max(r["captured_at_utc"] for r in rows)
            age = (now - datetime.fromisoformat(newest)).total_seconds() / 86400.0
            if age > MAX_AGE_DAYS:
                print(f"!! FRESHNESS ALERT: newest successful capture is {age:.1f} days old "
                      f"(> {MAX_AGE_DAYS}). Availability snapshots are stale - check the "
                      f"capture workflow.")
                return 1
            print(f"freshness ok: newest successful capture {age:.1f} days old")

    if had_error and os.environ.get("STRICT") == "1":
        print("STRICT=1 and a capture failed - exiting 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
