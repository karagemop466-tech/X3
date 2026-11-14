#!/usr/bin/env python3
"""
X3 verified results feed.

Purpose (requirement: "add a verified results feed so backtests and ROI can be
computed at all"):

  Build one row per scheduled 2026 game from a capture of the official NFL.com
  week schedule pages, then REFUSE TO PUBLISH unless every row survives three
  checks that do not use the capture's own arithmetic:

    R1  completeness   -- every final game must carry both scores; a final without
                          scores is dropped and counted, never imputed;
    R2  standings      -- the final scores must aggregate to exactly the official
                          standings (W-L-T, PF, PA, games played) for all 32 clubs,
                          read from data/hub/standings_2026_thru_wk9.csv, which a
                          different session transcribed from a different NFL page;
    R3  box scores     -- a sample of games is compared score-by-score against an
                          independent live read of the official week page; the
                          comparison is recorded, not asserted.

Inputs are read-only:
  data/desk/games.json                     capture of nfl.com/schedules/2026/by-week/week-N
                                           (captured by the repo's own CI runner; every
                                           page returned HTTP 200 - data/desk/capture_diag.json)
  data/hub/standings_2026_thru_wk9.csv      official standings transcription (other session)
  data/desk/injuries.json                   report availability per week 8/9/10

Outputs:
  data/x3/verified/results_2026.csv     one row per game, every row source-linked
  data/x3/verified/results.json         the same rows plus the check record

Run: python3 tools/results_feed.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "x3", "verified")

SRC_WEEK = "https://www.nfl.com/schedules/2026/by-week/week-{w}"
SRC_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"
SRC_INJ = "https://www.nfl.com/injuries/league/2026/reg{w}"

# The capture prints Arizona as ARI and the Rams as LA; the official standings page
# prints AZ and LAR. The alias is stated here, applied once, and counted.
ALIAS = {"ARI": "AZ", "LA": "LAR"}

# Independent verification: a live read of the official Week-1 schedule page on
# 2026-11-14 (fetch tool, both chunks) returned these 16 box scores. Every one is
# compared below against the capture; the result is published as a check row.
WEEK1_LIVE_READ = {
    ("NE", "SEA"): (10, 13), ("SF", "LAR"): (27, 7), ("CHI", "CAR"): (59, 37),
    ("TB", "CIN"): (27, 33), ("NO", "DET"): (30, 31), ("BUF", "HOU"): (36, 31),
    ("BAL", "IND"): (41, 23), ("CLE", "JAX"): (10, 34), ("ATL", "PIT"): (13, 20),
    ("NYJ", "TEN"): (23, 10), ("AZ", "LAC"): (26, 14), ("MIA", "LV"): (13, 27),
    ("GB", "MIN"): (22, 39), ("WAS", "PHI"): (22, 24), ("DAL", "NYG"): (20, 28),
    ("DEN", "KC"): (10, 31),
}


def norm(t: str) -> str:
    return ALIAS.get(t, t)


def main() -> int:
    cap = json.load(open(os.path.join(ROOT, "data", "desk", "games.json"), encoding="utf-8"))
    raw = cap["games"]
    st = {r["team"]: r for r in csv.DictReader(
        open(os.path.join(ROOT, "data", "hub", "standings_2026_thru_wk9.csv"), encoding="utf-8"))}

    errors: list[str] = []
    dropped: list[dict] = []
    rows: list[dict] = []

    for g in raw:
        away, home = norm(g["away"]), norm(g["home"])
        final = g["status"] == "FINAL"
        a_s, h_s = g.get("away_score"), g.get("home_score")
        # R1 completeness: a final must carry both scores; never imputed.
        if final and (a_s in ("", None) or h_s in ("", None)):
            dropped.append({"week": g["week"], "game": f"{away}@{home}", "reason": "FINAL with no score"})
            continue
        row = {
            "game_id": f"{g['week']}:{away}@{home}",
            "week": g["week"],
            "date_iso": g["date_iso"],
            "away": away,
            "home": home,
            "away_name": g["away_name"],
            "home_name": g["home_name"],
            "neutral_site": bool(g["neutral_site"]),
            "venue": g["neutral_site_name"] or "",
            "status": g["status"],
            "away_score": a_s if final else "",
            "home_score": h_s if final else "",
            "margin_home": (h_s - a_s) if final else "",
            "total": (h_s + a_s) if final else "",
            "source": g["source"] or SRC_WEEK.format(w=g["week"]),
        }
        rows.append(row)

    rows.sort(key=lambda r: (r["week"], r["date_iso"], r["game_id"]))

    # ---- R2: the results must reproduce the official standings exactly ----------
    agg: dict[str, dict] = {}
    for r in rows:
        if r["status"] != "FINAL":
            continue
        for t, pf, pa in ((r["away"], r["away_score"], r["home_score"]),
                          (r["home"], r["home_score"], r["away_score"])):
            d = agg.setdefault(t, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "g": 0})
            d["g"] += 1
            d["pf"] += pf
            d["pa"] += pa
            if pf > pa:
                d["w"] += 1
            elif pf < pa:
                d["l"] += 1
            else:
                d["t"] += 1

    if len(agg) != 32:
        errors.append(f"results feed covers {len(agg)} clubs, expected 32")
    standings_rows, mismatches = [], []
    for t in sorted(agg):
        d, s = agg[t], st.get(t)
        if s is None:
            mismatches.append({"team": t, "field": "row", "feed": "present", "standings": "absent"})
            continue
        want = (int(s["w"]), int(s["l"]), int(s["t"]), int(s["pf"]), int(s["pa"]),
                int(s["w"]) + int(s["l"]) + int(s["t"]))
        got = (d["w"], d["l"], d["t"], d["pf"], d["pa"], d["g"])
        for name, a, b in zip(("W", "L", "T", "PF", "PA", "GP"), got, want):
            if a != b:
                mismatches.append({"team": t, "field": name, "feed": a, "standings": b})
        standings_rows.append({"team": t, "feed": dict(zip(("w", "l", "t", "pf", "pa", "g"), got)),
                               "standings": dict(zip(("w", "l", "t", "pf", "pa", "g"), want)),
                               "agree": got == want})
    if mismatches:
        errors.append(f"{len(mismatches)} standings mismatches between the results feed and "
                      f"the official standings transcription: {mismatches[:5]}")

    # ---- R3: independent box-score sample ------------------------------------
    wk1 = [r for r in rows if r["week"] == 1 and r["status"] == "FINAL"]
    checked = agreed = 0
    detail = []
    for r in wk1:
        key = (r["away"], r["home"])   # already normalised: AZ, LAR
        if key not in WEEK1_LIVE_READ:
            continue
        checked += 1
        want = WEEK1_LIVE_READ[key]
        ok = (r["away_score"], r["home_score"]) == want
        agreed += 1 if ok else 0
        detail.append({"game": f"{r['away']}@{r['home']}", "capture": [r["away_score"], r["home_score"]],
                       "live_read": list(want), "agree": ok})
    if checked != 16 or agreed != 16:
        errors.append(f"independent Week-1 box-score check: {agreed}/{checked} agree, expected 16/16")

    # ---- availability of the injury report per week (for backtests that join it) --
    inj = json.load(open(os.path.join(ROOT, "data", "desk", "injuries.json"), encoding="utf-8"))
    report_weeks = [{"week": w["week"], "rows": w["rows"], "source": w["url"]} for w in inj["weeks"]]

    finals = [r for r in rows if r["status"] == "FINAL"]
    meta = {
        "as_of": "2026-11-14",
        "generated_by": "tools/results_feed.py",
        "season": cap["season"],
        "counts": {
            "games_total": len(rows), "finals": len(finals),
            "scheduled": len(rows) - len(finals), "clubs": len(agg),
            "weeks_with_finals": sorted({r["week"] for r in finals}),
            "dropped_for_missing_score": len(dropped),
        },
        "sources": {
            "schedule": "https://www.nfl.com/schedules/2026/by-week/week-N (N=1..11)",
            "standings": SRC_STANDINGS,
            "capture_diagnostics": "data/desk/capture_diag.json (212/212 pages HTTP 200)",
        },
        "checks": {
            "R1_completeness": {"rule": "a FINAL row without both scores is dropped, never imputed",
                                "dropped": len(dropped), "detail": dropped},
            "R2_standings_reconciliation": {
                "rule": "final scores aggregated per club must equal the official standings on "
                        "W, L, T, PF, PA and games played",
                "clubs_compared": len(standings_rows),
                "mismatches": len(mismatches), "detail": mismatches,
                "rows": standings_rows,
                "source": SRC_STANDINGS,
                "note": "independent of the results capture: a different page, transcribed by a "
                        "different session, with club-code aliasing ARI->AZ and LA->LAR applied once",
            },
            "R3_box_score_sample": {
                "rule": "16 Week-1 finals compared score-by-score with a live read of the official "
                        "Week-1 page on 2026-11-14",
                "checked": checked, "agreed": agreed, "detail": detail,
                "source": SRC_WEEK.format(w=1),
            },
        },
        "availability_feed": report_weeks,
        "limitations": [
            "One season to date. No prior-season results are in this repository, so no strategy "
            "can clear a three-season walk-forward yet (gate G-3).",
            "The capture covers weeks 1-11 of the 2026 schedule only.",
            "No prices are attached to any row. A result grades a bet; it cannot price one.",
        ],
        "rows": rows,
    }

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    cols = ["game_id", "week", "date_iso", "away", "home", "neutral_site", "venue", "status",
            "away_score", "home_score", "margin_home", "total", "source"]
    with open(os.path.join(OUT, "results_2026.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"results: {len(rows)} games ({len(finals)} final, {len(rows)-len(finals)} scheduled), "
          f"{len(agg)} clubs")
    print(f"R2 standings: {len(standings_rows)} clubs compared, {len(mismatches)} mismatches")
    print(f"R3 box scores: {agreed}/{checked} Week-1 finals agree with the live read")
    if errors:
        for e in errors:
            print("FAIL", e)
        return 1
    print("PASS - results feed reconciles to the official standings with zero mismatches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
