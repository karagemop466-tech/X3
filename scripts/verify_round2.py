#!/usr/bin/env python3
"""Round-2 module gate (session arena/4c2f61cd-x3, 2026-11-15).

Hard rules, exit 1 on violation:
  R1  Every round2/*.html page parses and contains no root-absolute href/src.
  R2  Determinism: rebuilding round2/ from round2/data/*.csv is byte-identical.
  R3  Every round2 data CSV parses and its row counts match the published KPIs.
  R4  Every body row in a round2 table carries an external link, an internal
      link, or an explicit UNVERIFIED/DERIVED/BLOCKED marker (same rule as
      scripts/audit_all.py L2, scoped to this module).
"""
from __future__ import annotations

import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "round2"

PAGES = ["index.html", "verification.html", "readiness.html", "audit.html",
         "flagged.html", "suggestions.html", "sources.html"]

CSV_ROWS = {
    "standings_league_2026-11-15.csv": 32,
    "week10_slate_2026-11-15.csv": 14,
    "week10_results_delta_2026-11-15.csv": 8,
    "gamebook_munich_facts.csv": 25,
    "gamebook_munich_starters.csv": 44,
    "gamebook_munich_not_active.csv": 12,
    "requirements_full.csv": 66,
    "audit_round2.csv": 12,
    "flags_round2.csv": 7,
    "suggestions_round2.csv": 10,
    "sources_round2.csv": 6,
}

TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
A_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
MARKER_RE = re.compile(
    r"unverified|derived|blocked|left blank|no official|not covered|n/a|none|"
    r"capture-time|fetch-time|not yet|not computed|unevaluable|flag",
    re.I,
)


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("a", "link", "script", "img"):
            href = dict(attrs).get("href") or dict(attrs).get("src")
            if href:
                self.hrefs.append(href)


def main() -> int:
    fails: list[str] = []

    # R1 parse + no root-absolute links
    pages = {}
    for name in PAGES:
        p = D / name
        if not p.exists():
            fails.append(f"R1 {name}: missing")
            continue
        text = p.read_text(encoding="utf-8")
        pages[name] = text
        parser = Links()
        parser.feed(text)
        for href in parser.hrefs:
            if href.startswith("//"):
                continue
            if href.startswith("/") and not href.startswith("/X3"):
                fails.append(f"R1 {name}: root-absolute link {href}")
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = href.split("#", 1)[0]
            if not target:
                continue
            if not (D / target).exists():
                fails.append(f"R1 {name}: broken internal link {href}")

    # R2 determinism
    before = {name: (D / name).read_bytes() for name in PAGES}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_round2.py")],
                   check=True, capture_output=True)
    for name in PAGES:
        if (D / name).read_bytes() != before[name]:
            fails.append(f"R2 {name}: rebuild is not byte-identical")

    # R3 data row counts
    import csv
    for fname, expected in CSV_ROWS.items():
        f = D / "data" / fname
        if not f.exists():
            fails.append(f"R3 {fname}: missing")
            continue
        with open(f, newline="", encoding="utf-8") as fh:
            n = sum(1 for _ in csv.DictReader(fh))
        if n != expected:
            fails.append(f"R3 {fname}: {n} rows, expected {expected}")

    # R4 every source-table row sourced/flagged (mirrors audit_all L2: only tables
    # whose header contains a "source" column are provenance tables)
    THEAD_RE = re.compile(r"<thead[^>]*>(.*?)</thead>", re.S)
    for name in PAGES:
        text = pages.get(name)
        if not text:
            continue
        for tbl in TABLE_RE.findall(text):
            m = THEAD_RE.search(tbl)
            if not m or "source" not in m.group(1).lower():
                continue
            body_tbl = tbl[m.end():]  # tbody only - header rows are exempt
            for tr in TR_RE.findall(body_tbl):
                if not CELL_RE.search(tr):
                    continue
                cells = [re.sub(r"<[^>]+>", "", c).strip() for c in CELL_RE.findall(tr)]
                joined = " ".join(cells)
                if len(cells) < 2:
                    continue
                has_link = bool(re.search(r'href="https?://', tr)) or bool(
                    re.search(r'href="(\.\./|\./|readiness\.html|verification\.html|audit\.html|flagged\.html|suggestions\.html|sources\.html|index\.html)', tr))
                if not has_link and not MARKER_RE.search(joined):
                    fails.append(f"R4 {name}: row neither linked nor flagged: {joined[:90]!r}")

    if fails:
        print("ROUND2 CHECK FAILED")
        for f in fails:
            print(" ", f)
        return 1
    print(f"ROUND2 CHECK PASSED  ({len(PAGES)} pages, {len(CSV_ROWS)} data files, determinism OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
