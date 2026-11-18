#!/usr/bin/env python3
"""Freshness audit (session arena/40cd3b17-x3, M2).

Re-reads published on 2026-11-18 from the official pages are diffed against the
committed canonical numbers:

  standings  : data/week11/standings_read_2026-11-18.csv  vs  data/atlas/standings_2026_thru_wk10.csv
               and data/closeout/official_standings_2026_wk10.csv
  wk10 finals: data/week11/week10_finals_read_2026-11-18.csv vs data/closeout/week10_finals.csv
  wk11 slate : data/week11/week11_slate_read_2026-11-18.csv vs data/closeout/week11_slate.csv (+ byes)
  reg11 probe: data/week11/reg11_probes.csv (the Wednesday capture series, B50)

Every row of the emitted freshness_audit.csv carries the dataset, the compared key,
the committed value, the value read today, and the official source URL. League
arithmetic checks (sum PF = sum PA; PF-PA = NET per club) run on today's read.

Nothing here writes a canonical dataset: week11/ is a drift check, not a feed.
"""
from __future__ import annotations

import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W11 = os.path.join(ROOT, "data", "week11")

STANDINGS_URL = "https://www.nfl.com/standings/league/2026/REG"
WK10_URL = "https://www.nfl.com/schedules/2026/by-week/week-10"
WK11_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
REG11_URL = "https://www.nfl.com/injuries/league/2026/reg11"

# The Rams page code is LA; the committed atlas register uses LAR (alias F-09).
ALIAS = {"LA": "LAR"}
# Known official-source venue naming variants (existing flag F-03): the schedule
# page hotel-link block says "GEHA Field at Arrowhead Stadium" while the game
# centre says "Arrowhead Stadium". Same venue, different published strings.
VENUE_VARIANTS = [
    ("GEHA Field at Arrowhead Stadium", "Arrowhead Stadium"),
]


def rd(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def norm_kick(v):
    """12-hour '1:00 PM' -> 24-hour '13:00' for comparison."""
    v = v.strip()
    if ":" in v and ("AM" in v or "PM" in v):
        hm, ampm = v.rsplit(" ", 1)
        h, m = hm.split(":")
        h = int(h) % 12 + (12 if ampm == "PM" else 0)
        return f"{h:02d}:{m}"
    return v


def norm_rec(v):
    return v.replace(" ", "").replace(".", "").strip()


def val_eq(a, b):
    """Tolerant cell comparison: identical strings, or equal to 3 decimals
    (covers the .889 vs 0.889 pct-format difference between registers)."""
    if a == b:
        return True
    try:
        return round(float(a), 3) == round(float(b), 3)
    except (TypeError, ValueError):
        return False



def main():
    audit = []   # dataset, key, field, committed, read_today, verdict, source
    problems = []

    # ---- 1. standings -----------------------------------------------------
    today = rd(os.path.join(W11, "standings_read_2026-11-18.csv"))
    atlas = {r["team"]: r for r in rd(os.path.join(ROOT, "data", "atlas", "standings_2026_thru_wk10.csv"))}
    closeout = {r["team"]: r for r in rd(os.path.join(ROOT, "data", "closeout", "official_standings_2026_wk10.csv"))}
    fields = ["w", "l", "t", "pct", "pf", "pa", "net", "home", "road", "div",
              "div_pct", "conf", "conf_pct", "nonconf", "streak"]
    sum_pf = sum_pa = 0
    for r in today:
        t = r["team"]
        sum_pf += int(r["pf"]); sum_pa += int(r["pa"])
        if int(r["pf"]) - int(r["pa"]) != int(r["net"]):
            problems.append(f"standings arithmetic: {t} PF-PA != NET")
        for peer_name, peer in (("atlas", atlas), ("closeout", closeout)):
            code = "LAR" if (t == "LA" and peer_name == "atlas") else t
            p = peer.get(code)
            if p is None:
                problems.append(f"standings: {t} missing from {peer_name} register")
                continue
            common = [f for f in fields if f in p]
            for f in common:
                a, b = r[f].strip(), p[f].strip()
                verdict = "MATCH" if val_eq(a, b) else "MISMATCH"
                if verdict == "MISMATCH":
                    problems.append(f"standings vs {peer_name}: {t}.{f}: committed {b} vs read {a}")
                audit.append(["standings", code, f, b, a, verdict,
                              "data/atlas/standings_2026_thru_wk10.csv" if peer_name == "atlas" else "data/closeout/official_standings_2026_wk10.csv",
                              STANDINGS_URL])
    if sum_pf != sum_pa:
        problems.append(f"league totals: sum PF {sum_pf} != sum PA {sum_pa}")

    # ---- 2. week-10 finals --------------------------------------------------
    finals = rd(os.path.join(W11, "week10_finals_read_2026-11-18.csv"))
    committed_f = {r["game_id"]: r for r in rd(os.path.join(ROOT, "data", "closeout", "week10_finals.csv"))}
    for r in finals:
        g = r["game_id"]
        p = committed_f.get(g)
        if p is None:
            problems.append(f"wk10 finals: {g} not in committed register")
            continue
        for f, rf in (("away_score", "away_score"), ("home_score", "home_score"),
                      ("winner", "winner"), ("status", "status")):
            a, b = r[rf].strip(), p[f].strip()
            verdict = "MATCH" if a == b else "MISMATCH"
            if verdict == "MISMATCH":
                problems.append(f"wk10 finals: {g}.{f}: committed {b} vs read {a}")
            audit.append(["wk10_finals", g, f, b, a, verdict,
                          "data/closeout/week10_finals.csv", WK10_URL])
    if len(finals) != 14:
        problems.append(f"wk10 finals: expected 14 games, read {len(finals)}")

    # ---- 3. week-11 slate ---------------------------------------------------
    slate = rd(os.path.join(W11, "week11_slate_read_2026-11-18.csv"))
    committed_s = {r["game_id"]: r for r in rd(os.path.join(ROOT, "data", "closeout", "week11_slate.csv"))}
    for r in slate:
        g = r["game_id"]
        p = committed_s.get(g)
        if p is None:
            problems.append(f"wk11 slate: {g} not in committed register")
            continue
        pairs = [("date_iso", "date_iso"), ("network", "network"),
                 ("kickoff", "kickoff_et"), ("venue", "venue")]
        for f, cf in pairs:
            a = norm_kick(r["kickoff_et"]) if f == "kickoff" else r["venue" if f == "venue" else f].strip()
            b = p[cf].strip()
            if f == "kickoff":
                a, b = norm_kick(r["kickoff_et"]), norm_kick(p[cf])
            if f == "venue" and a != b:
                if "Mexico City" in a and "Mexico City" in b:
                    audit.append(["wk11_slate", g, "venue", b, a, "VARIANT",
                                  "data/closeout/week11_slate.csv (game-centre stadium name vs week-page event label; same site)", WK11_URL])
                    continue
                if any({a, b} <= set(vv) for vv in VENUE_VARIANTS):
                    audit.append(["wk11_slate", g, "venue", b, a, "VARIANT",
                                  "data/closeout/week11_slate.csv (known official naming split, flag F-03)", WK11_URL])
                    continue
            verdict = "MATCH" if a == b else "MISMATCH"
            if verdict == "MISMATCH":
                problems.append(f"wk11 slate: {g}.{f}: committed {b} vs read {a}")
            audit.append(["wk11_slate", g, f, b, a, verdict,
                          "data/closeout/week11_slate.csv", WK11_URL])
    if len(slate) != 13:
        problems.append(f"wk11 slate: expected 13 games, read {len(slate)}")
    committed_byes = {r["team"] for r in rd(os.path.join(ROOT, "data", "closeout", "week11_byes.csv"))}
    read_byes = {"ATL", "CLE", "GB", "LA", "NE", "SEA"}  # as read 2026-11-18 from the week-11 page bye block
    for t in sorted(read_byes ^ committed_byes):
        audit.append(["wk11_byes", t, "on_bye", "yes" if t in committed_byes else "no",
                      "yes" if t in read_byes else "no", "MATCH", "data/closeout/week11_byes.csv", WK11_URL])
    if committed_byes != read_byes:
        problems.append(f"wk11 byes: committed {sorted(committed_byes)} vs read {sorted(read_byes)}")

    # ---- 4. reg11 probe series ----------------------------------------------
    probes = rd(os.path.join(W11, "reg11_probes.csv"))
    for p in probes:
        audit.append(["reg11_probe", p["probe_utc"], "page_rendered",
                      "Week 10 of the 2026 Season", p["observed_week"],
                      "PENDING" if p["observed_week"] != "11" else "PUBLISHED",
                      "", REG11_URL])

    with open(os.path.join(W11, "freshness_audit.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dataset", "key", "field", "committed_value", "read_today",
                    "verdict", "committed_register", "official_source"])
        w.writerows(audit)

    summary = {
        "as_of": "2026-11-18",
        "read_window_utc": "2026-11-18T03:05Z-03:25Z",
        "reg11_published": any(p["observed_week"] == "11" for p in probes),
        "standings_rows": len(today),
        "standings_league_pf": sum_pf,
        "standings_league_pa": sum_pa,
        "wk10_finals_rows": len(finals),
        "wk11_slate_rows": len(slate),
        "wk11_byes": sorted(read_byes),
        "audit_rows": len(audit),
        "mismatches": problems,
        "probes": len(probes),
    }
    with open(os.path.join(W11, "freshness_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"week11 audit: {len(audit)} compared rows, {len(problems)} problems")
    for p in problems:
        print("  !", p)
    if problems:
        raise SystemExit(1)
    print("PASS - today's official reads match every committed canonical number")


if __name__ == "__main__":
    main()
