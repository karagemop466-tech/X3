#!/usr/bin/env python3
"""Capture one timestamped read of the official NFL injury report.

Runs on a GitHub-hosted runner (full internet; the authoring sandbox cannot reach nfl.com).
For every run it:

  1. fetches the official page and records the HTTP status, the byte count, the
     SHA-256 of the raw bytes and the UTC clock time of the request;
  2. saves the raw bytes to snapshots/raw/ (git-ignored; uploaded as a workflow
     artifact by the workflow, never committed and never published on Pages);
  3. parses the player tables and counts rows and designations;
  4. appends one row to snapshots/manifest.csv (committed; the immutable ledger);
  5. FAILS LOUDLY (exit 1) if the page does not carry the expected table schema or
     fewer player rows than the floor. A drift alarm must not publish a blank.

Usage:  python3 scripts/injury_snapshot.py [--url URL] [--out snapshots] [--local FILE]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_URL = "https://www.nfl.com/injuries/league/2026/reg10"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
EXPECTED_HEAD = ["player", "position", "injuries", "practice status", "game status"]
PLAYER_ROW_FLOOR = 150          # the 2026-11-15 read has 347 rows; below 150 is a parse failure
MANIFEST_HEAD = ["snapshot_utc", "source_url", "http_status", "bytes", "sha256", "season_week",
                 "tables_with_schema", "player_rows", "out", "doubtful", "questionable",
                 "blank_status", "other_status", "schema_ok", "result", "note"]


class _Tables(HTMLParser):
    """Collects every table as a list of rows; each cell is (text, links_to_player)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[tuple[str, bool]]]] = []
        self._stack: list[list[list[tuple[str, bool]]]] = []
        self._row: list[tuple[str, bool]] | None = None
        self._cell: list[str] | None = None
        self._cell_player = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
        elif tag == "tr" and self._stack:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell, self._cell_player = [], False
        elif tag == "a" and self._cell is not None:
            if "/players/" in (dict(attrs).get("href") or ""):
                self._cell_player = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append((" ".join("".join(self._cell).split()), self._cell_player))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._stack:
            self._stack[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def fetch(url: str, tries: int = 3) -> tuple[int, bytes, str]:
    last = ""
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.status, r.read(), ""
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001 - recorded in the manifest, then fail loudly
            last = f"{type(e).__name__}: {e}"
        time.sleep(3 * attempt)
    return 0, b"", last


def parse(html: str) -> dict:
    p = _Tables()
    p.feed(html)
    schema_tables = 0
    rows = []
    for table in p.tables:
        if not table:
            continue
        head = [c[0].strip().lower() for c in table[0]]
        if head != EXPECTED_HEAD:
            continue
        schema_tables += 1
        for r in table[1:]:
            if len(r) == 5 and r[0][1]:          # first cell links to a player page
                rows.append(r)
    counts = {"Out": 0, "Doubtful": 0, "Questionable": 0, "blank": 0, "other": 0}
    for r in rows:
        status = r[4][0]
        if status == "":
            counts["blank"] += 1
        elif status in counts:
            counts[status] += 1
        else:
            counts["other"] += 1
    return {"tables": schema_tables, "rows": len(rows), "out": counts["Out"],
            "doubtful": counts["Doubtful"], "questionable": counts["Questionable"],
            "blank": counts["blank"], "other": counts["other"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default="snapshots")
    ap.add_argument("--local", default="", help="parse a saved copy instead of fetching (tests)")
    a = ap.parse_args()
    out = Path(a.out)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest = out / "manifest.csv"
    if not manifest.exists():
        with manifest.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(MANIFEST_HEAD)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.local:
        status, body, err = 200, Path(a.local).read_bytes(), ""
    else:
        status, body, err = fetch(a.url)
    sha = hashlib.sha256(body).hexdigest() if body else ""
    if body:
        (raw_dir / f"injury-{stamp.replace(':', '')}-{sha[:12]}.html").write_bytes(body)

    result, note, parsed, week = "FAIL", "", {}, ""
    if not body:
        note = f"fetch failed: {err or 'empty body'}"
    else:
        html = body.decode("utf-8", errors="replace")
        m = re.search(r"Week (\d+) of the (\d{4}) Season", html)
        week = f"{m.group(2)}-wk{m.group(1)}" if m else ""
        parsed = parse(html)
        if parsed["tables"] == 0:
            note = "schema drift: no table with header Player|Position|Injuries|Practice Status|Game Status"
        elif parsed["rows"] < PLAYER_ROW_FLOOR:
            note = f"only {parsed['rows']} player rows (floor {PLAYER_ROW_FLOOR}); parse or page change"
        else:
            result, note = "OK", ""
    row = [stamp, a.url, status, len(body), sha, week,
           parsed.get("tables", 0), parsed.get("rows", 0),
           parsed.get("out", 0), parsed.get("doubtful", 0), parsed.get("questionable", 0),
           parsed.get("blank", 0), parsed.get("other", 0), "yes" if result == "OK" else "no", result, note]
    with manifest.open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(row)
    print(f"{stamp} status={status} bytes={len(body)} sha256={sha[:16]} week={week or '?'} "
          f"rows={parsed.get('rows', 0)} out={parsed.get('out', 0)} result={result} {note}")
    return 0 if result == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
