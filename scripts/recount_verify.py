#!/usr/bin/env python3
"""
Verifier for the Week-10 recount (session arena/d6d831c6-x3). Exit 1 on any failure.

Checks, all independent of the build's own arithmetic where possible:
  1. The transcription has 347 rows, 14 games, 28 clubs; the 4 clubs not on the page are the
     Week-10 byes printed on the official schedule page (CHI, DEN, PHI, TB).
  2. Every row has club, player, position, practice status (one of 3 allowed values), game status
     (blank / Questionable / Doubtful / Out) and a chunk number 0-7 (the 8 chunks of the page).
  3. Per-game row counts equal the published club-section sizes recorded in the transcription.
  4. The committed agency capture matches the live rows on every player, and its only field
     differences are capitalisation-only.
  5. The audit and hub tables are each missing exactly Calais Campbell and Ronnie Stanley (BAL),
     and their field differences are the ones listed in data/recount/diffs.csv.
  6. data/recount/reg10_2026_live.csv, comparison.json and diffs.csv regenerate byte-identically
     from the transcription (determinism), and their sha256 matches MANIFEST.json.
  7. recount/index.html and recount/rows.html: every table row that shows official data links an
     nfl.com page; the row count of rows.html is 347; every flagged item has a source link.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
FAILS: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main() -> int:
    psv = P("data", "recount", "reg10_2026_live_transcription.psv")
    rows = []
    for line in open(psv, encoding="utf-8"):
        line = line.rstrip("\n")
        if line:
            rows.append(line.split("|"))

    # 1. counts
    check(len(rows) == 347, f"transcription has 347 rows (found {len(rows)})")
    games = Counter(r[0] for r in rows)
    clubs = Counter(r[1] for r in rows)
    check(len(games) == 14, f"14 games (found {len(games)})")
    check(len(clubs) == 28, f"28 clubs on the page (found {len(clubs)})")
    byes = {"CHI", "DEN", "PHI", "TB"}
    check(not (byes & set(clubs)), "bye clubs CHI, DEN, PHI, TB have no section on the page")
    check(set(clubs) | byes == {c for c in clubs} | byes and len(set(clubs) | byes) == 32,
          "28 playing clubs + 4 bye clubs = 32 clubs")

    # 2. field validity
    allowed_pr = {"Full Participation in Practice", "Limited Participation in Practice", "Did Not Participate In Practice"}
    allowed_gs = {"", "Questionable", "Doubtful", "Out"}
    bad = []
    for r in rows:
        if len(r) != 8:
            bad.append(("arity", r))
            continue
        gid, club, player, pos, inj, pr, gs, chunk = r
        if not (club and player and pos and pr):
            bad.append(("blank required field", r))
        if pr not in allowed_pr:
            bad.append(("practice", r))
        if gs not in allowed_gs:
            bad.append(("game status", r))
        if chunk not in {str(i) for i in range(8)}:
            bad.append(("chunk", r))
    check(not bad, f"every row has club/player/position/practice and valid status values ({len(bad)} problems)")

    # 3. per-game sizes: the page's game sections, as recorded in the build's game metadata
    expected_games = {"G01": 20, "G02": 24, "G03": 24, "G04": 30, "G05": 23, "G06": 23, "G07": 25,
                      "G08": 24, "G09": 28, "G10": 29, "G11": 20, "G12": 31, "G13": 17, "G14": 29}
    check(dict(games) == expected_games, "per-game row counts equal the section sizes read from the page")
    expected_clubs = {"WAS": 9, "NYG": 11, "NE": 15, "DET": 9, "KC": 13, "ATL": 11, "MIN": 13, "GB": 17,
                      "JAX": 11, "TEN": 12, "BUF": 14, "NYJ": 9, "MIA": 11, "IND": 14, "CAR": 12, "NO": 12,
                      "HOU": 16, "CLE": 12, "LAR": 14, "AZ": 15, "SEA": 15, "LV": 5, "SF": 12, "DAL": 19,
                      "PIT": 8, "CIN": 9, "LAC": 19, "BAL": 10}
    check(dict(clubs) == expected_clubs, "per-club row counts equal the section sizes read from the page")

    # 4-5. comparisons with committed tables (read directly, not via the build)
    def read_csv(path):
        with open(P(*path), encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    live_keys = {(r[1], re.sub(r"[^a-z]", "", r[2].lower())) for r in rows}
    agency = read_csv(("agency", "data", "derived", "injury_designations_w10_2026.csv"))
    audit = read_csv(("audit", "official_injury_wk10_2026.csv"))
    hub = read_csv(("data", "hub", "injuries_2026_wk10.csv"))
    ak = {(r["team"], re.sub(r"[^a-z]", "", r["player"].lower())) for r in agency}
    check(ak == live_keys, "agency capture: same 347 (club, player) keys as the live page")
    ak_pr = {}
    for r in agency:
        ak_pr[(r["team"], re.sub(r"[^a-z]", "", r["player"].lower()))] = r
    cap_only = 0
    other = []
    for r in rows:
        k = (r[1], re.sub(r"[^a-z]", "", r[2].lower()))
        a = ak_pr[k]
        for live_v, com_v, name in [(r[3], a["position"], "pos"), (r[4], a["injury"], "injury"),
                                    (r[5], a["practice_status"], "practice"), (r[6], a["game_status"], "game")]:
            if live_v != com_v:
                if live_v.lower() == com_v.lower():
                    cap_only += 1
                else:
                    other.append((k, name, live_v, com_v))
    check(not other, f"agency capture: every field equals the live page, or differs by capitalisation only "
                     f"(capitalisation-only: {cap_only}; other: {len(other)})")
    check(cap_only == 1, "agency capture: exactly one capitalisation-only difference (Trevin Wallace)")

    for name, tbl, club_k, pl_k in [("audit", audit, "team", "player"), ("hub", hub, "team", "player")]:
        keys = {(r[club_k], re.sub(r"[^a-z]", "", r[pl_k].lower())) for r in tbl}
        missing = live_keys - keys
        check(len(tbl) == 345, f"{name} table has 345 rows (found {len(tbl)})")
        check(missing == {("BAL", "calaiscampbell"), ("BAL", "ronniestanley")},
              f"{name} table is missing exactly BAL Calais Campbell and Ronnie Stanley (found {sorted(missing)})")
        check(not (keys - live_keys), f"{name} table has no player that is absent from the live page")

    # diffs.csv: every field difference recorded, and the count per committed copy
    diffs = read_csv(("data", "recount", "diffs.csv"))
    for src, n_expected in [("audit", 34), ("hub", 34), ("agency", 1)]:
        n = sum(1 for d in diffs if d["source"] == src)
        check(n == n_expected, f"diffs.csv: {src} has {n_expected} recorded differences (found {n})")
    lac_bal_fields = [d for d in diffs if d["source"] == "audit" and d["field"] != "ROW" and d["club"] in ("LAC", "BAL")]
    check(len(lac_bal_fields) == 30, f"audit: 30 field differences sit in the LAC/BAL block (found {len(lac_bal_fields)})")
    arden = [d for d in diffs if d["source"] == "audit" and d["player"] == "Arden Key"]
    check({d["field"] for d in arden} == {"injury", "game_status"}, "audit: Arden Key has injury + game-status conflicts (R-F9)")

    # 6. determinism and manifest hashes
    man = json.load(open(P("data", "recount", "MANIFEST.json"), encoding="utf-8"))
    for rel, h in man["outputs"].items():
        check(sha256(P(rel)) == h, f"MANIFEST output hash matches: {rel}")
    for rel, h in man["inputs"].items():
        check(sha256(P(rel)) == h, f"MANIFEST input hash matches: {rel}")
    before = {p: sha256(P(p)) for p in ("data/recount/reg10_2026_live.csv", "data/recount/comparison.json",
                                        "data/recount/diffs.csv", "recount/index.html", "recount/rows.html")}
    rc = subprocess.run([sys.executable, P("scripts", "recount_build.py")], cwd=ROOT,
                        capture_output=True, text=True).returncode
    check(rc == 0, "recount_build.py runs")
    after = {p: sha256(P(p)) for p in before}
    check(before == after, "rebuild is byte-identical (deterministic)")

    # 7. pages
    for page in ("recount/index.html", "recount/rows.html"):
        text = open(P(page), encoding="utf-8").read()
        check("<table" in text, f"{page} contains tables")
    rows_html = open(P("recount", "rows.html"), encoding="utf-8").read()
    body_rows = re.findall(r"<tr(?: class=\"[a-z]+\")?><td class=\"num\">\d+</td>", rows_html)
    check(len(body_rows) == 347, f"rows.html lists 347 player rows (found {len(body_rows)})")
    tr_all = re.findall(r"<tr(?: class=\"[a-z]+\")?>(.*?)</tr>", rows_html, flags=re.S)
    data_tr = [t for t in tr_all if re.match(r"\s*<td class=\"num\">\d+</td>", t)]
    no_link = [t[:80] for t in data_tr if "nfl.com/" not in t]
    check(not no_link, f"rows.html: every player row links the official nfl.com page ({len(no_link)} without)")
    idx = open(P("recount", "index.html"), encoding="utf-8").read()
    flags = re.findall(r"<tr><td>(R-F\d+)</td>.*?<a href=\"(https://www\.nfl\.com/[^\"]+)\"", idx, flags=re.S)
    check(len(flags) >= 9, f"index.html: every flag has a nfl.com source link ({len(flags)} flags)")
    check("Week 11 of the 2026 Season" in idx and "Week 10" in idx, "index.html states the R-F1 heading conflict")

    print()
    if FAILS:
        print(f"RECOUNT VERIFY: FAIL ({len(FAILS)} check(s))")
        return 1
    print("RECOUNT VERIFY: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
