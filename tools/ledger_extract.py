#!/usr/bin/env python3
"""Deterministic seeding of the decision-ledger input CSVs.

Writes (no value is inferred; every blank stays blank):
  data/ledger/results_2026.csv          FINAL games from data/desk/games.json
                                        (official nfl.com week-schedule capture, row-level URL)
  data/ledger/price_snapshots.csv       one row per originated market for each unplayed Week-10
                                        game in hub/data/lines.json, in origination order
                                        side (spread) -> total -> moneyline. Opening/closing
                                        columns are blank: no official price source exists.
  data/ledger/replacement_depth_wk10.csv  Week-10 Out/Doubtful rows with the replacement's
                                        string number, copied from the archived overlay and
                                        re-checked by tools/verify_ledger.py.

tools/verify_ledger.py re-checks every file written here.
"""
import csv, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAMES = ROOT / "data" / "desk" / "games.json"
LINES = ROOT / "hub" / "data" / "lines.json"
OVERLAY = ROOT / "archive" / "hub-621bf404" / "data" / "depth_overlay_wk10_2026.csv"
OUT = ROOT / "data" / "ledger"

WEEK10_PAGE = "https://www.nfl.com/schedules/2026/by-week/week-10"
INJ_PAGE = "https://www.nfl.com/injuries/league/2026/reg10"
PRICE_STATUS = "UNVERIFIED: no official price source; left blank by policy"

RESULT_FIELDS = ["season", "week", "date_iso", "away", "home", "away_score", "home_score",
                 "status", "neutral_site", "source_url"]
PRICE_FIELDS = ["game_id", "season", "week", "date_iso", "kickoff_et", "away", "home",
                "origination_order", "market", "opening_value", "closing_value", "book",
                "price_source_url", "game_source_url", "status"]
DEPTH_FIELDS = ["team", "game_status", "player", "position", "injury", "unit", "slot",
                "starter_string", "replacement", "replacement_string", "join",
                "chart_labelled_unofficial", "injury_source_url", "depth_source_url"]


def write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def results():
    rows = []
    for g in json.loads(GAMES.read_text())["games"]:
        if g["status"] != "FINAL":
            continue
        if g["away_score"] is None or g["home_score"] is None:
            raise SystemExit(f"FINAL game without both scores: {g}")
        rows.append({
            "season": 2026, "week": g["week"], "date_iso": g["date_iso"],
            "away": g["away"], "home": g["home"],
            "away_score": g["away_score"], "home_score": g["home_score"],
            "status": g["status"], "neutral_site": "yes" if g["neutral_site"] else "no",
            "source_url": g["source"],
        })
    rows.sort(key=lambda r: (r["week"], r["date_iso"], r["away"]))
    write(OUT / "results_2026.csv", RESULT_FIELDS, rows)
    return len(rows)


# The model (hub/data/lines.json) uses the standings codes LAR and AZ; the official game
# capture uses LA and ARI. This is the only alias; it is applied, never guessed.
MODEL_TO_CAPTURE = {"LAR": "LA", "AZ": "ARI"}


def prices():
    games = {f"{g['away']}@{g['home']}": g for g in json.loads(GAMES.read_text())["games"]
             if g["week"] == 10 and g["status"] == "SCHEDULED"}
    rows = []
    for r in json.loads(LINES.read_text())["rows"]:
        key = "@".join(MODEL_TO_CAPTURE.get(t, t) for t in r["game"].split("@"))
        g = games.get(key)
        if g is None:
            raise SystemExit(f"model game {r['game']} not in official week-10 capture")
        for order, market in ((1, "spread"), (2, "total"), (3, "moneyline")):
            rows.append({
                "game_id": f"2026-W10-{g['away']}-{g['home']}", "season": 2026, "week": 10,
                "date_iso": g["date_iso"] or r["date"], "kickoff_et": g["kickoff_et"] or r["slot"],
                "away": g["away"], "home": g["home"], "origination_order": order,
                "market": market, "opening_value": "", "closing_value": "", "book": "",
                "price_source_url": "", "game_source_url": WEEK10_PAGE, "status": PRICE_STATUS,
            })
    write(OUT / "price_snapshots.csv", PRICE_FIELDS, rows)
    return len(rows)


def depth():
    rows = []
    for r in csv.DictReader(OVERLAY.open(newline="")):
        depth_url = r["depth_source"]
        rows.append({
            "team": r["team"], "game_status": r["game_status"], "player": r["player"],
            "position": r["position"], "injury": r["injury"], "unit": r["unit"],
            "slot": r["slot"], "starter_string": r["starter_string"],
            "replacement": r["replacement"], "replacement_string": r["replacement_string"],
            "join": r["join"], "chart_labelled_unofficial": r["chart_labelled_unofficial"],
            "injury_source_url": INJ_PAGE, "depth_source_url": depth_url,
        })
    write(OUT / "replacement_depth_wk10.csv", DEPTH_FIELDS, rows)
    return len(rows)


if __name__ == "__main__":
    print("results rows:", results())
    print("price rows:", prices())
    print("depth rows:", depth())
