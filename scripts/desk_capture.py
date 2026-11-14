#!/usr/bin/env python3
"""Capture official NFL pages from a GitHub runner and write diagnostics.

Run by .github/workflows/desk-capture.yml (runners have full internet; the authoring
sandbox cannot reach nfl.com). Downloads go to `capture/` (git-ignored); the
diagnostics go to `data/desk/capture_diag.json` and are committed so the authoring
session can see exactly what happened.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
WEEKS = list(range(1, 12))
INJ_WEEKS = [8, 9, 10, 11]


def get(url: str, dest: Path, tries: int = 3) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = ""
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
                dest.write_bytes(body)
                return {"url": url, "status": r.status, "bytes": len(body), "attempts": attempt}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 * attempt)
    return {"url": url, "status": None, "bytes": 0, "error": last, "attempts": tries}


def club_sites() -> dict[str, str]:
    src = Path("tools/nfl_data.py").read_text()
    out = {}
    for abbr, club in re.findall(
            r'\("([A-Z]{2,3})",\s*"[^"]+",\s*"https://www\.nfl\.com/teams/[^"]+",\s*"(https://[^"]+)"',
            src):
        out[abbr] = club.rstrip("/") + "/team/depth-chart"
    return out


def main(capdir: str) -> int:
    cap = Path(capdir)
    diag: dict[str, object] = {"pages": [], "links": {}, "notes": []}

    targets = [(f"https://www.nfl.com/schedules/2026/by-week/week-{w}", f"schedule-w{w}.html")
               for w in WEEKS]
    targets.append(("https://www.nfl.com/standings/league/2026/reg", "standings-2026.html"))
    targets.append(("https://www.nfl.com/stats/team-stats/", "team-stats.html"))
    targets += [(f"https://www.nfl.com/injuries/league/2026/reg{w}", f"injuries-w{w}.html")
                for w in INJ_WEEKS]
    clubs = club_sites()
    diag["clubs_found"] = len(clubs)
    targets += [(url, f"depth-{abbr}.html") for abbr, url in sorted(clubs.items())]

    for url, name in targets:
        diag["pages"].append({"file": name, **get(url, cap / name)})

    # Locate per-game links inside the captured schedule pages (escaped JSON or plain HTML).
    slugs: set[str] = set()
    for w in WEEKS:
        f = cap / f"schedule-w{w}.html"
        if not f.exists():
            continue
        raw = f.read_text(errors="replace")
        found = set(re.findall(r"games/([a-z0-9]+-at-[a-z0-9-]+-2026-reg-\d+)", raw))
        found |= set(re.findall(r"games/([a-z0-9-]+-\d{4}-reg-\d+)", raw))
        diag["links"][f"week-{w}"] = {
            "occurrences_of_games_slash": raw.count("games/"),
            "slugs": len(found),
            "sample": sorted(found)[:3],
        }
        slugs |= found
    diag["distinct_game_slugs"] = len(slugs)

    game_dir = cap / "games"
    game_dir.mkdir(exist_ok=True)
    for slug in sorted(slugs):
        dest = game_dir / f"{slug}.html"
        if dest.exists() and dest.stat().st_size > 10000:
            continue
        diag["pages"].append({"file": f"games/{slug}.html",
                              **get(f"https://www.nfl.com/games/{slug}", dest)})

    (Path("data/desk")).mkdir(parents=True, exist_ok=True)
    Path("data/desk/capture_diag.json").write_text(json.dumps(diag, indent=1) + "\n")
    ok = sum(1 for p in diag["pages"] if p.get("status") == 200)
    print(f"captured {ok}/{len(diag['pages'])} pages; distinct game slugs: {len(slugs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "capture"))
