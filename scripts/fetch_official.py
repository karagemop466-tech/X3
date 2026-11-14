#!/usr/bin/env python3
"""Fetch every official source registered in :mod:`lib.official` and write a
provenance manifest.

Usage:
    python scripts/fetch_official.py                # everything
    python scripts/fetch_official.py --category injuries standings
    python scripts/fetch_official.py --key-prefix schedule_2026
    python scripts/fetch_official.py --out data/raw

The raw HTML is cached (and git-ignored); the manifest is committed so every
published number can be traced back to a byte-exact official payload.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.official import club_sources, fetch_all, league_sources, write_manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/raw", help="raw payload cache directory")
    ap.add_argument("--manifest", default="data/datasets/fetch_manifest.json")
    ap.add_argument("--category", nargs="*", help="restrict to these categories")
    ap.add_argument("--key-prefix", nargs="*", help="restrict to keys with these prefixes")
    ap.add_argument("--groups", nargs="*", default=["league", "club"], choices=["league", "club"])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--dry-run", action="store_true", help="list sources and exit")
    args = ap.parse_args()

    sources: list = []
    if "league" in args.groups:
        sources += league_sources()
    if "club" in args.groups:
        sources += club_sources()
    if args.category:
        sources = [s for s in sources if s.category in args.category]
    if args.key_prefix:
        sources = [s for s in sources if any(s.key.startswith(p) for p in args.key_prefix)]

    if args.dry_run:
        for s in sources:
            print(f"{s.key}\t{s.category}\t{s.url}")
        print(f"# {len(sources)} sources")
        return 0

    os.makedirs(args.out, exist_ok=True)
    print(f"Fetching {len(sources)} official sources -> {args.out}", flush=True)
    records = fetch_all(sources, args.out, workers=args.workers, timeout=args.timeout)
    summary = write_manifest(records, args.manifest)
    print(json.dumps(summary["by_category"], indent=2)[:2000])
    print(
        f"done: {summary['succeeded']}/{summary['total']} succeeded, "
        f"{summary['failed']} failed -> {args.manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
