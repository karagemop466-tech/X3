#!/usr/bin/env python3
"""Probe captured pages: report where the machine-readable payload lives.

NFL.com renders schedules, standings and injuries client-side from a JSON payload
embedded in the page. This probe reports the script blocks that could hold it so the
parsers can be written against the real structure instead of guessed HTML.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_BLOCK = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)


def main(src: str, dst: str) -> int:
    cap, out = Path(src), Path(dst)
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for f in sorted(cap.glob("*.html")):
        raw = f.read_text(errors="replace")
        blocks = []
        for attrs, body in SCRIPT_BLOCK.findall(raw):
            m = re.search(r'type="([^"]+)"', attrs)
            blocks.append({"type": m.group(1) if m else "text/javascript",
                           "attrs": attrs.strip()[:160],
                           "len": len(body),
                           "head": body.strip()[:200]})
        blocks.sort(key=lambda b: -b["len"])
        report[f.name] = {
            "html_bytes": len(raw),
            "script_blocks": len(blocks),
            "jsonish": [b for b in blocks if "json" in b["type"].lower()][:3],
            "largest": blocks[:3],
            "has_next_data": "__NEXT_DATA__" in raw,
            "has_ld_json": "application/ld+json" in raw,
        }
    (out / "probe.json").write_text(json.dumps(report, indent=1) + "\n")
    k = "schedule-w1.html"
    print(json.dumps(report.get(k, {}), indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
