#!/usr/bin/env python3
"""Capture the live official pages as dated, hashed snapshots.

Every capture is one JSON file per (page, UTC date) in `proof/snapshots/`. A
capture that already exists is never overwritten: if the page changed during
the day, the new capture is suffixed `-2`, `-3`, ... so the sequence of what the
page said, and when, is preserved and can be replayed.

Each record stores: url, fetched_at (UTC, second resolution), http status,
sha256 of the bytes, byte count, and the extracted text. The extracted text is
what a later diff reads; the hash is what proves the text came from that page at
that time.

Usage:  python3 proof/capture_live.py
        python3 proof/capture_live.py --index   # no network: print the index
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "proof", "snapshots")

# The pages that decide what was knowable before a kickoff.
PAGES = [
    ("injury-report", "https://www.nfl.com/injuries/league/2026/reg{suffix}"),
    ("standings", "https://www.nfl.com/standings/league/2026/REG"),
    ("schedule-week", "https://www.nfl.com/schedules/2026/by-week/week-{suffix}"),
]


def week_candidates() -> list[int]:
    """The injury report and the schedule are week-addressed; capture 1..18."""
    return list(range(1, 19))


def fetch(url: str, timeout: int = 60) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; x3-proof)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except Exception as e:  # noqa: BLE001
        return 0, repr(e).encode()


TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"[ \t\r\f\v]+")


def text_of(body: bytes) -> str:
    try:
        s = body.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = TAG.sub(" ", s)
    s = WS.sub(" ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def main() -> int:
    if "--index" in sys.argv:
        n = 0
        for name in sorted(os.listdir(OUT)) if os.path.isdir(OUT) else []:
            if name.endswith(".json"):
                d = json.load(open(os.path.join(OUT, name)))
                print(f"{name:44s} {d['url'][:70]:70s} {d.get('bytes', 0):>9,d}  {d.get('sha256','')[:12]}")
                n += 1
        print(f"{n} snapshots")
        return 0

    os.makedirs(OUT, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    made, empty = 0, 0
    targets: list[tuple[str, str]] = [("standings", PAGES[1][1])]
    for wk in week_candidates():
        targets.append((f"injury-report-week{wk:02d}", PAGES[0][1].format(suffix=wk)))
        targets.append((f"schedule-week{wk:02d}", PAGES[2][1].format(suffix=wk)))

    for label, url in targets:
        base = f"{today}_{label}"
        status, body = fetch(url)
        if status == 0 or len(body) < 5000:
            empty += 1
            continue
        rec = {
            "label": label,
            "url": url,
            "fetched_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "http_status": status,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "text": text_of(body)[:400_000],
        }
        # never overwrite an existing capture: suffix instead
        n = 1
        while True:
            name = base + ("" if n == 1 else f"-{n}") + ".json"
            path = os.path.join(OUT, name)
            if not os.path.exists(path):
                break
            n += 1
        json.dump(rec, open(path, "w"), indent=0)
        made += 1
    print(f"captured {made} pages, {empty} unreachable; {today}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
