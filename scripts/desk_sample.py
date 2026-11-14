#!/usr/bin/env python3
"""Write small structure samples so parsers can be written against the real payload.

Output: data/desk/samples/<page>.sample.txt
  * server-rendered pages (standings, injuries, depth charts): the tab-separated table lines
  * client-rendered pages (schedules): windows of the Next.js flight payload around score keys
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from desk_extract import text_of

FLIGHT_KEY = re.compile(r'\\?"(homeTeam|homeScore|scores|week\\?":[0-9]+)')


def main(src: str, dst: str) -> int:
    cap, out = Path(src), Path(dst) / "samples"
    out.mkdir(parents=True, exist_ok=True)
    index = {}
    for f in sorted(cap.glob("*.html")):
        raw = f.read_text(errors="replace")
        if f.name.startswith("schedule-"):
            payload = "\n".join(re.findall(r"self\.__next_f\.push\(\[1,(\".*?\")\]\)", raw, re.S))
            body = payload.encode().decode("unicode_escape", errors="replace")
            samples = []
            for m in list(FLIGHT_KEY.finditer(body))[:8]:
                samples.append(body[max(0, m.start() - 300): m.start() + 900])
            text = "\n\n----WINDOW----\n\n".join(samples)
        else:
            txt = text_of(raw)
            rows = [ln for ln in txt.splitlines() if ln.count("\t") >= 3]
            text = "\n".join(rows[:400])
        (out / (f.stem + ".sample.txt")).write_text(text)
        index[f.name] = {"sample_bytes": len(text)}
    (out / "index.json").write_text(json.dumps(index, indent=1) + "\n")
    print(json.dumps({k: v["sample_bytes"] for k, v in index.items()}, indent=0)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
