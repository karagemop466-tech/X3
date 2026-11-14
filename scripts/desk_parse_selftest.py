#!/usr/bin/env python3
"""Self-test the desk parsers against the captured pages.

Run before desk_parse.py in CI. Exits non-zero when a parser is broken, so a silent
empty dataset can never be committed again. Every assertion is about parser
behaviour on the real captured page, not about an expected fact.
"""
from __future__ import annotations

import sys
from pathlib import Path

import desk_parse as P
from desk_parse_meta import NICKNAME


def main(capdir: str) -> int:
    cap = Path(capdir)
    fails: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
        if not cond:
            fails.append(name)

    for w in (1, 9, 10, 11):
        f = cap / f"schedule-w{w}.html"
        check(f"schedule-w{w} captured", f.exists())
        if not f.exists():
            continue
        rows = P.parse_schedule(f"schedule-w{w}", f.read_text(errors="replace"))
        finals = [r for r in rows if r["status"] == "FINAL"]
        check(f"schedule-w{w} parsed rows", len(rows) >= 10, f"{len(rows)} games, {len(finals)} final")
        check(f"schedule-w{w} all clubs mapped",
              all(r["away"] and r["home"] for r in rows))
        check(f"schedule-w{w} dates parsed", all(r["date_iso"] for r in rows))

    for w in (9, 10):
        f = cap / f"injuries-w{w}.html"
        check(f"injuries-w{w} captured", f.exists())
        if not f.exists():
            continue
        rows, st = P.parse_injuries(f"injuries-w{w}", f.read_text(errors="replace"), w)
        check(f"injuries-w{w} rows", len(rows) > 200, f"{len(rows)} rows, {st['teams']} teams")
        check(f"injuries-w{w} team headers", st["teams"] >= 28, f"{st['teams']} teams")

    f = cap / "standings-2026.html"
    check("standings captured", f.exists())
    if f.exists():
        rows = P.parse_standings("standings", f.read_text(errors="replace"))
        check("standings 32 rows", len(rows) == 32, f"{len(rows)}")
        check("standings clubs unique", len({r["abbr"] for r in rows}) == len(rows))

    f = cap / "depth-ARI.html"
    check("depth-ARI captured", f.exists())
    if f.exists():
        d = P.parse_depth("depth-ARI", f.read_text(errors="replace"), "ARI")
        check("depth-ARI units", len(d["units"]) >= 2, f"{len(d['units'])} units")
        check("depth-ARI slots", sum(len(u["slots"]) for u in d["units"]) >= 20)

    print(f"\n{len(fails)} failing checks")
    for name in fails:
        print("  -", name)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
