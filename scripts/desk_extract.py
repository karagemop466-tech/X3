#!/usr/bin/env python3
"""Extract structured, source-linked data from captured official NFL pages.

Input : capture/  directory of raw HTML captured by .github/workflows/desk-capture.yml
Output: data/desk/*.json  (one file per dataset, every row keeping its official URL)

Rules enforced here:
  * a value is only written when it was read from the captured page
  * every row stores the exact official URL it came from
  * anything the parser cannot read is reported in data/desk/extract_report.json,
    never guessed
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

CAPTURE_URLS = {
    "standings-2026.html": "https://www.nfl.com/standings/league/2026/reg",
    "team-stats.html": "https://www.nfl.com/stats/team-stats/",
}
for _w in range(1, 12):
    CAPTURE_URLS[f"schedule-w{_w}.html"] = f"https://www.nfl.com/schedules/2026/by-week/week-{_w}"
for _w in range(8, 12):
    CAPTURE_URLS[f"injuries-w{_w}.html"] = f"https://www.nfl.com/injuries/league/2026/reg{_w}"

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
WS_RE = re.compile(r"[ \t\r\f\v]+")
NL_RE = re.compile(r"\n{3,}")


def text_of(raw: str) -> str:
    """HTML -> readable text, keeping table cell boundaries as tabs and rows as newlines."""
    s = SCRIPT_RE.sub(" ", raw)
    s = re.sub(r"</t[dh]>", "\t", s, flags=re.I)
    s = re.sub(r"</tr>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s)
    s = WS_RE.sub(" ", s)
    s = "\n".join(line.strip() for line in s.splitlines())
    return NL_RE.sub("\n", s)


def find_table_blocks(text: str) -> list[list[list[str]]]:
    """Group consecutive tab-separated lines into tables of rows of cells."""
    tables, cur = [], []
    for line in text.splitlines():
        if "\t" in line and line.count("\t") >= 2:
            cur.append([c.strip() for c in line.split("\t") if c.strip() != ""] or [""])
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    return tables


def main(src: str, dst: str) -> int:
    cap = Path(src)
    out = Path(dst)
    out.mkdir(parents=True, exist_ok=True)
    report = {"captured": {}, "notes": []}
    texts = {}
    for f in sorted(cap.glob("*.html")):
        raw = f.read_text(errors="replace")
        texts[f.name] = text_of(raw)
        report["captured"][f.name] = {
            "url": CAPTURE_URLS.get(f.name, ""),
            "bytes": len(raw),
            "text_chars": len(texts[f.name]),
        }
    # Structural diagnostics only; dataset parsers are added once the shape is known.
    for name, text in texts.items():
        report["notes"].append(
            {"file": name, "tables": len(find_table_blocks(text)),
             "lines": len(text.splitlines())}
        )
    (out / "extract_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["notes"], indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
