#!/usr/bin/env python3
"""Second-pass structure inspection: dump raw HTML slices around known markers.

Outputs to data/desk/samples/:
  row-standings.txt  first standings data row
  row-injuries.txt   first injury player row
  row-depth-ARI.txt  the offense block of the Arizona depth chart
  flight-w9.txt      decoded Next.js payload windows around completed-game score data
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PUSH_RE = re.compile(r"self\.__next_f\.push\(\[1,(\".*?\")\]\)", re.S)


def decode_flight(raw: str) -> str:
    parts = []
    for chunk in PUSH_RE.findall(raw):
        try:
            parts.append(json.loads(chunk))
        except Exception:
            pass
    return "".join(parts)


def slice_around(s: str, marker: str, width: int = 4500) -> str:
    i = s.find(marker)
    return s[max(0, i - 400): i - 400 + width] if i >= 0 else f"[marker {marker!r} not found]"


def main(src: str, dst: str) -> int:
    cap, out = Path(src), Path(dst) / "samples"
    out.mkdir(parents=True, exist_ok=True)
    info = {}

    st = (cap / "standings-2026.html").read_text(errors="replace")
    (out / "row-standings.txt").write_text(slice_around(st, "Buffalo Bills", 6000))
    info["standings_marker"] = "Buffalo Bills" in st

    inj = (cap / "injuries-w10.html").read_text(errors="replace")
    i = inj.find("John Bates")
    (out / "row-injuries.txt").write_text(inj[max(0, i - 3000): i + 3000] if i >= 0 else "not found")
    info["injuries_marker"] = i >= 0

    depth = (cap / "depth-ARI.html").read_text(errors="replace")
    (out / "row-depth-ARI.txt").write_text(slice_around(depth, "Reggie Virgil", 6000))
    info["depth_marker"] = "Reggie Virgil" in depth

    sch = (cap / "schedule-w9.html").read_text(errors="replace")
    flight = decode_flight(sch)
    (out / "flight-w9-meta.json").write_text(json.dumps({
        "flight_chars": len(flight),
        "pushes": len(PUSH_RE.findall(sch)),
        "has_scores_key": '"scores"' in flight,
        "has_gameId": flight.count('"gameId"'),
        "has_homeScore": flight.count("homeScore"),
        "has_awayScore": flight.count("awayScore"),
        "has_score_colon": flight.count('"score":'),
    }, indent=1))
    windows = []
    for m in list(re.finditer(r'\\?"gameId\\?"', flight))[:6]:
        windows.append(flight[max(0, m.start() - 200): m.start() + 2600])
    (out / "flight-w9.txt").write_text("\n\n----WINDOW----\n\n".join(windows))
    info["flight_windows"] = len(windows)
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
