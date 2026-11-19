#!/usr/bin/env python3
"""Verify data/live/ and live/ integrity, SHA-256 manifest, link resolution, and source-row rules.

Run: python3 scripts/live_verify.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "live"
LIVE = ROOT / "live"

EXPECTED_PAGES = {
    "index.html",
    "lines-weather.html",
    "week10-gamebooks.html",
    "injuries-transactions.html",
    "calibration-strategies.html",
    "questions-suggestions.html",
    "flagged.html",
}

OK_MARKERS = ("UNVERIFIED", "DERIVED", "FLAGGED", "BLOCKED", "PENDING", "N/A")


class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []
        self.in_tbody = False
        self.in_tr = False
        self.row_text: list[str] = []
        self.row_ext = False
        self.tbody_rows = 0
        self.unsourced_rows: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        for attr in ("href", "src"):
            v = d.get(attr)
            if v:
                self.refs.append(v)
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.in_tr = True
            self.row_text = []
            self.row_ext = False
            self.tbody_rows += 1
        elif tag == "a" and self.in_tr:
            href = d.get("href", "") or ""
            if href.startswith(("http://", "https://")):
                self.row_ext = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self.in_tbody = False
        elif tag == "tr" and self.in_tr:
            self.in_tr = False
            txt = " ".join(self.row_text).upper()
            if not self.row_ext and not any(m in txt for m in OK_MARKERS):
                self.unsourced_rows.append(" ".join(self.row_text)[:120])

    def handle_data(self, data: str) -> None:
        if self.in_tr:
            self.row_text.append(data.strip())


def main() -> int:
    errors: list[str] = []

    # 1. No raw .html inside data/live/
    html_in_data = list(DATA.rglob("*.html"))
    if html_in_data:
        errors.append(f"Raw .html found in data/live/: {html_in_data}")

    # 2. Manifest SHA-256 verification
    manifest_path = DATA / "manifest.json"
    if not manifest_path.exists():
        errors.append("Missing data/live/manifest.json")
        manifest = {}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel, expected_sha in manifest.get("files_sha256", {}).items():
            fp = ROOT / rel
            if not fp.exists():
                errors.append(f"Missing manifest file: {rel}")
            else:
                got = hashlib.sha256(fp.read_bytes()).hexdigest()
                if got != expected_sha:
                    errors.append(f"SHA-256 mismatch on {rel}")

    # 3. Market cells strictly blank
    lines_csv = DATA / "week11_lines_live.csv"
    with lines_csv.open("r", encoding="utf-8", newline="") as f:
        lines = list(csv.DictReader(f))
    if len(lines) != 13:
        errors.append(f"Expected 13 Week-11 lines, got {len(lines)}")
    for r in lines:
        for col in ("market_side", "diff_side", "market_total", "diff_total", "market_ml", "diff_ml"):
            if r.get(col, "") != "":
                errors.append(f"Non-blank market cell {r['game_id']}.{col}={r[col]!r}")

    # 4. HTML pages & CSS
    css = LIVE / "assets" / "live.css"
    if not css.exists():
        errors.append("Missing live/assets/live.css")
    for p in EXPECTED_PAGES:
        fp = LIVE / p
        if not fp.exists():
            errors.append(f"Missing live/{p}")
            continue
        parser = AuditParser()
        parser.feed(fp.read_text(encoding="utf-8"))
        for href in parser.refs:
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if href.startswith("/"):
                errors.append(f"live/{p}: root-absolute ref {href}")
                continue
            target = href.split("#", 1)[0]
            if target and not (fp.parent / target).exists():
                errors.append(f"live/{p}: broken relative ref {href}")
        if parser.unsourced_rows:
            errors.append(f"live/{p}: {len(parser.unsourced_rows)} unsourced rows (e.g. {parser.unsourced_rows[0]})")

    if errors:
        print("LIVE VERIFY FAILED:")
        for e in errors:
            print(" -", e)
        return 1

    print(
        f"PASS: live/ verified ({len(EXPECTED_PAGES)} pages, "
        f"{len(manifest.get('files_sha256', {}))} hashed data files, "
        f"{manifest.get('week10_gamebooks')} W10 Game Books, "
        f"{manifest.get('week11_injury_rows')} reg11 rows, 0 errors)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
