#!/usr/bin/env python3
"""Capture parser fixtures from the freshly fetched official payloads.

The fixtures are used by ``scripts/selftest.py`` so that a parser regression
is caught before the site is published. They are regenerated on every pipeline
run and are never committed, which keeps the repository small and guarantees
that the fixtures always match the live official pages.
"""

from __future__ import annotations

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
DATA = os.path.join(ROOT, "data", "datasets")
FIXTURES = os.path.join(ROOT, "scripts", "fixtures")

sys.path.insert(0, os.path.join(ROOT, "scripts"))

from lib.official import resolve_payload
from selftest import FIXTURE_SOURCES


def main() -> int:
    manifest_path = os.path.join(DATA, "fetch_manifest.json")
    if not os.path.exists(manifest_path):
        print("no fetch manifest; skipping fixture capture")
        return 0
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    by_key = {r["key"]: r for r in manifest.get("records", [])}

    os.makedirs(FIXTURES, exist_ok=True)
    captured = 0
    for fixture_name, key in FIXTURE_SOURCES.items():
        record = by_key.get(key)
        if not record or not record.get("ok") or not record.get("content_path"):
            print(f"  skip {fixture_name}: {key} not available")
            continue
        source = resolve_payload(record, RAW)
        if not source:
            print(f"  skip {fixture_name}: payload not found for {key}")
            continue
        shutil.copyfile(source, os.path.join(FIXTURES, fixture_name))
        captured += 1
        print(f"  captured {fixture_name} from {record['url']}")
    print(f"captured {captured}/{len(FIXTURE_SOURCES)} fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
