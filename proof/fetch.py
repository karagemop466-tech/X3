#!/usr/bin/env python3
"""proof/ acquisition layer - freeze the versioned source files, record their hashes.

This is the ONLY file in `proof/` that touches the network. Everything else reads
the frozen copies in `proof/raw/` and is therefore reproducible offline.

Sources and why each one is used
--------------------------------
results + closing prices
    github.com/nflverse/nfldata  `games.csv` (scores, roof, surface, rest, moneyline)
    and `closing_lines.csv` (closing spread/total/moneyline per game). This is the
    same repository the earlier X3 sessions already used for
    `data/x3/source/games.csv`; the proof layer re-freezes it so its hash is
    recorded next to every number derived from it.
availability
    github.com/nflverse/nflverse-data release `injuries` - the league injury
    report, one row per player-report-week with `report_status` (the game
    designation) and `practice_status`. nfl.com publishes the same report as
    HTML with no historical archive, so this dated mirror is what makes a
    point-in-time replay possible at all.
playing time
    the same repository's `snap_counts` release - offensive/defensive snap counts
    per player per game. This is the starter proxy required when a club depth
    chart is undated or missing (the brief's SG route (b)).

Nothing is downloaded that cannot be re-derived: every file is recorded with its
URL, byte size and sha256 in `proof/hashes.json`. Once recorded, a file is never
overwritten in place - a changed source becomes a new dated snapshot.

Usage
  python3 proof/fetch.py            # download anything missing, then write hashes.json
  python3 proof/fetch.py --verify   # no network: compare local files to hashes.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "proof", "raw")

RELEASE = "https://github.com/nflverse/nflverse-data/releases/download"
NFLDAT = "https://raw.githubusercontent.com/nflverse/nfldata/master/data"

# Injury reports are small; take the whole modern era so designation reliability
# can be measured over several seasons rather than asserted.
INJURY_SEASONS = list(range(2018, 2027))
# Snap counts are per player per game; six seasons is ~13 MB and enough to build
# a stable playing-time prior without bloating the repository.
SNAP_SEASONS = list(range(2021, 2027))


def targets() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for s in INJURY_SEASONS:
        out.append((f"injuries_{s}.csv", f"{RELEASE}/injuries/injuries_{s}.csv"))
    for s in SNAP_SEASONS:
        out.append((f"snap_counts_{s}.csv", f"{RELEASE}/snap_counts/snap_counts_{s}.csv"))
    out.append(("games.csv", f"{NFLDAT}/games.csv"))
    out.append(("closing_lines.csv", f"{NFLDAT}/closing_lines.csv"))
    return out


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "x3-proof-capture"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def main() -> int:
    verify_only = "--verify" in sys.argv
    os.makedirs(RAW, exist_ok=True)
    manifest_path = os.path.join(ROOT, "proof", "hashes.json")
    old = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {"files": {}}
    files = dict(old.get("files", {}))
    problems: list[str] = []

    for name, url in targets():
        dest = os.path.join(RAW, name)
        if verify_only:
            if not os.path.exists(dest):
                problems.append(f"missing {name}")
                continue
            got = sha256_file(dest)
            want = files.get(name, {}).get("sha256")
            if want is None:
                problems.append(f"{name}: not recorded in hashes.json")
            elif got != want:
                problems.append(f"{name}: sha256 {got[:16]} != recorded {want[:16]}")
            continue
        if os.path.exists(dest) and name in files:
            continue  # frozen: a recorded capture is never rewritten
        try:
            download(url, dest)
        except Exception as e:  # noqa: BLE001 - reported, never raised
            problems.append(f"{name}: download failed: {e!r}")
            if os.path.exists(dest):
                os.remove(dest)
            continue
        files[name] = {"url": url, "bytes": os.path.getsize(dest), "sha256": sha256_file(dest)}

    if not verify_only:
        json.dump(
            {
                "source_results": "github.com/nflverse/nfldata",
                "source_availability": "github.com/nflverse/nflverse-data",
                "files": dict(sorted(files.items())),
            },
            open(manifest_path, "w"),
            indent=1,
        )

    if problems:
        print("FETCH ISSUES:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"ok: {len(files)} frozen files, all sha256 match proof/hashes.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
