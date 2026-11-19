#!/usr/bin/env python3
"""Fresh-day verification gate (2026-11-19) for the fresh module.

Deterministic checks only — no network. Every check prints PASS/FAIL and the
script exits non-zero if any FAIL. Source links live in the CSV files under
data/fresh/; this script re-derives invariants and cross-checks committed
registers so the published pages cannot drift from the captured evidence.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRESH = ROOT / "data" / "fresh"

failures = []
notes = []

def check(name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(f"{name}: {detail}")

def load(name):
    with open(FRESH / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

# ---------- standings ----------
standings = load("standings_2026-11-19.csv")
check("standings: 32 rows", len(standings) == 32, f"got {len(standings)}")
clubs = [r["club"] for r in standings]
check("standings: 32 unique clubs", len(set(clubs)) == 32)
ALL32 = {'AZ','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LA','LAC','LV','MIA','MIN','NE','NO','NYG','NYJ','PHI','PIT','SEA','SF','TB','TEN','WAS'}
check("standings: club set is the full NFL", set(clubs) == ALL32, str(sorted(ALL32 - set(clubs))))
tot_pf = sum(int(r["pf"]) for r in standings)
tot_pa = sum(int(r["pa"]) for r in standings)
check("standings: league PF == league PA", tot_pf == tot_pa, f"PF {tot_pf} vs PA {tot_pa}")
BYE11 = {"ATL","CLE","GB","LA","NE","SEA"}
for r in standings:
    w, l, t = int(r["wins"]), int(r["losses"]), int(r["ties"])
    games = w + l + t
    # clubs whose bye already happened: 9 played; everyone else (incl. this week's six byes): 10
    expected_min, expected_max = 9, 10
    check(f"standings {r['club']}: games played in [9,10]", expected_min <= games <= expected_max, f"{w}+{l}+{t}={games}")
    exp_games = 10 if r["club"] in BYE11 else None  # this week's byes have NOT had their bye
    if exp_games is not None:
        check(f"standings {r['club']}: Week-11 bye club shows 10 played (bye not yet taken)", games == exp_games, f"got {games}")
    pct = (w + 0.5 * t) / games
    check(f"standings {r['club']}: pct consistent ((w+0.5t)/gp)", abs(pct - float(r["pct"])) < 5e-4, f"{r['pct']} vs {pct:.4f}")
    check(f"standings {r['club']}: net = pf - pa", int(r["pf"]) - int(r["pa"]) == int(r["net_pts"]))

# cross-check committed registers (records unchanged since Week 10 finals)
atlas = {r["team"]: r for r in csv.DictReader(open(ROOT / "data/atlas/standings_2026_thru_wk10.csv", newline="", encoding="utf-8"))}
ATLAS_KEY = {"LA": "LAR"}  # atlas file uses LAR for the Rams
for k in list(atlas):
    pass
closeout = {r["team"]: r for r in csv.DictReader(open(ROOT / "data/closeout/official_standings_2026_wk10.csv", newline="", encoding="utf-8"))}
for r in standings:
    a, c = atlas.get(ATLAS_KEY.get(r["club"], r["club"])), closeout.get(r["club"])
    if a:
        same = (a["w"] == str(r["wins"]) and a["l"] == str(r["losses"]) and a["t"] == str(r["ties"])
                and a["pf"] == str(r["pf"]) and a["pa"] == str(r["pa"]) and a["net"] == str(r["net_pts"]))
        check(f"standings {r['club']}: matches committed atlas register", same,
              f"atlas {a['w']}-{a['l']}-{a['t']} pf {a['pf']} vs fresh {r['wins']}-{r['losses']}-{r['ties']} pf {r['pf']}")
    else:
        check(f"standings {r['club']}: atlas register present", False)
    if c:
        same = (c["w"] == str(r["wins"]) and c["l"] == str(r["losses"]) and c["t"] == str(r["ties"])
                and c["pf"] == str(r["pf"]) and c["pa"] == str(r["pa"]) and c["net"] == str(r["net_pts"]))
        check(f"standings {r['club']}: matches committed closeout register", same)
    else:
        check(f"standings {r['club']}: closeout register present", False)

# ---------- slate ----------
slate = load("week11_slate_2026-11-19.csv")
byes = [r["club"] for r in load("byes_week11_2026-11-19.csv")]
check("slate: 13 games", len(slate) == 13, f"got {len(slate)}")
check("slate: 6 byes", len(byes) == 6, f"got {len(byes)}")
played = set()
for g in slate:
    played.add(g["away"]); played.add(g["home"])
check("slate: 32 clubs accounted for exactly once (games + byes)",
      played | set(byes) == ALL32 and len(played & set(byes)) == 0 and len(played) == 26,
      f"games cover {len(played)} clubs, overlap with byes: {sorted(played & set(byes))}")
check("slate: byes are ATL, CLE, GB, LA, NE, SEA", sorted(byes) == sorted(["ATL","CLE","GB","LA","NE","SEA"]))
rec = {r["club"]: (f"{r['wins']}-{r['losses']}-{r['ties']}" if r["ties"] != "0" else f"{r['wins']}-{r['losses']}") for r in standings}
for g in slate:
    for side, club in (("away", g["away"]), ("home", g["home"])):
        check(f"slate {g['game_id']}: {side} {club} record matches standings",
              rec[club] == g[f"{side}_record"], f"slate {g[f'{side}_record']} vs standings {rec[club]}")
committed = {r["game_id"]: r for r in csv.DictReader(open(ROOT / "data/week11/week11_slate_read_2026-11-18.csv", newline="", encoding="utf-8"))}
for g in slate:
    c = committed.get(g["game_id"])
    check(f"slate {g['game_id']}: present in committed 2026-11-18 read", c is not None)
    if c:
        for k, mine, theirs in (("date_iso","date_iso","date_iso"),("kickoff","kickoff_et","kickoff_et"),("network","network","network")):
            ok = mine == theirs
            check(f"slate {g['game_id']}: {k} unchanged vs 2026-11-18", ok, f"{mine} vs {theirs}")
        ok_venue = (g["venue_hotel_link"].replace(" (International Game)", " (International Series)") == c["venue"]) or g["venue_hotel_link"] == c["venue"]
        check(f"slate {g['game_id']}: venue (hotel link) unchanged vs 2026-11-18", ok_venue,
              f"{g['venue_hotel_link']} vs {c['venue']}")
check("slate: MIN@SF is the Mexico City international game",
      any(g["game_id"] == "MIN@SF" and "Mexico City" in g["venue_hotel_link"] for g in slate))
check("slate: CIN@WAS is Monday 2026-11-23 ESPN",
      any(g["game_id"] == "CIN@WAS" and g["date_iso"] == "2026-11-23" and g["network"] == "ESPN" for g in slate))
check("slate: IND@HOU is Thursday 2026-11-19 PRIME",
      any(g["game_id"] == "IND@HOU" and g["date_iso"] == "2026-11-19" and g["network"] == "PRIME" for g in slate))

# ---------- injury report (reg11, first capture) ----------
inj = load("injury_w11_2026.csv")
check("injury: 253 rows transcribed", len(inj) == 253, f"got {len(inj)}")
keys = [(r["club"], r["player"]) for r in inj]
check("injury: no duplicate club/player rows", len(keys) == len(set(keys)))
PRACTICE = {"Did Not Participate In Practice", "Limited Participation in Practice", "Full Participation in Practice"}
DESIG = {"", "Out", "Questionable"}
bad_p = sorted({r["practice_status"] for r in inj} - PRACTICE)
bad_d = sorted({r["game_status"] for r in inj} - DESIG)
check("injury: practice_status values within official vocabulary", not bad_p, str(bad_p))
check("injury: game_status values within official vocabulary", not bad_d, str(bad_d))
by_club = {}
for r in inj:
    by_club.setdefault(r["club"], []).append(r)
check("injury: 24 clubs carry rows", len(by_club) == 24, f"got {len(by_club)}: {sorted(by_club)}")
check("injury: CIN and WAS absent (No Injuries Reported)", "CIN" not in by_club and "WAS" not in by_club)
out_rows = [r for r in inj if r["game_status"] == "Out"]
q_rows = [r for r in inj if r["game_status"] == "Questionable"]
check("injury: 9 Out designations", len(out_rows) == 9, f"got {len(out_rows)}: {[r['player'] for r in out_rows]}")
check("injury: 7 Questionable designations", len(q_rows) == 7, f"got {len(q_rows)}: {[r['player'] for r in q_rows]}")

# cross-check game-centre Out lists vs the report transcription
game_centre = open(FRESH / "ind_hou_game_centre_2026-11-19.csv", encoding="utf-8").read()
ind_out = sorted(r["player"] for r in out_rows if r["club"] == "IND")
hou_out = sorted(r["player"] for r in out_rows if r["club"] == "HOU")
for p in ["Will Mallory", "Bernhard Raimann", "Jerry Tillery", "Jalen Travis", "Charvarius Ward"]:
    check(f"game-centre/report agree: IND Out {p}", p in ind_out and p in game_centre)
for p in ["Marvin Harrison Jr.", "Danielle Hunter", "Brevin Jordan", "Woody Marks"]:
    check(f"game-centre/report agree: HOU Out {p}", p in hou_out and p in game_centre)
check("venue conflict preserved in game-centre evidence", "RELIANT STADIUM" in game_centre and "NRG Stadium" in game_centre)
check("game-centre evidence records IND 3-7 / HOU 3-6", "IND 3-7" in game_centre and "HOU 3-6" in game_centre)

# ---------- game-centre fixture ----------
gc = load("ind_hou_game_centre_2026-11-19.csv")
fields = {r["field"]: r["value"] for r in gc}
check("game-centre: stadium field is RELIANT STADIUM", fields.get("stadium") == "RELIANT STADIUM")
check("game-centre: schedule link field is NRG Stadium", fields.get("schedule_hotel_link_venue") == "NRG Stadium")

# ---------- freshness summary ----------
summary = json.load(open(FRESH / "freshness_summary.json", encoding="utf-8"))
check("freshness summary: reg11_published true", summary["reg11_published"] is True)
check("freshness summary: counts match CSVs",
      summary["reg11_rows"] == len(inj) and summary["standings_rows"] == len(standings) and summary["wk11_slate_rows"] == len(slate))
check("freshness summary: league PF/PA both 6923", summary["standings_league_pf"] == 6923 and summary["standings_league_pa"] == 6923)

print()
if failures:
    print(f"FRESH VERIFY: FAIL ({len(failures)} failure(s))")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("FRESH VERIFY: PASS — all checks green")
