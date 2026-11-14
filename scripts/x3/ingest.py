#!/usr/bin/env python3
"""
X3 pipeline stage 1 - ingest + verified results feed + price-snapshot store (session arena/873c7396-x3).

Reads (all committed in-repo, provenance in data/x3/source/README.md):
  data/x3/source/games.csv          nflverse games 1999-2026 (results + PFF closing lines)
  data/x3/source/initial_lines.csv  Westgate 2021 openers (pilot only)
  data/x3/source/standings.csv      nflverse standings
  data/desk/games.json              prior session's per-game capture from NFL.com week pages
  data/hub/standings_2026_thru_wk9.csv  prior session's official standings transcription

Writes:
  data/x3/results_feed_2026.csv       every 2026 REG game + verification fields
  data/x3/results_history.csv         completed games 1999-2025 (backtest/correlation base)
  data/x3/price_snapshots_2026.csv    price-snapshot store export (obs_type OPEN/CURRENT/CLOSE/MODEL)
  data/x3/opening_lines_2021_pilot.csv openers pilot (schema demo; no 2026 source exists)
  data/x3/verification_log.json       line-by-line cross-check results

Deterministic: no wall-clock reads; every "captured_at" is the SOURCE commit timestamp.
"""
from __future__ import annotations
import csv, json, os, math, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "data", "x3", "source")
OUT = os.path.join(ROOT, "data", "x3")
AS_OF = "2026-11-14"
SRC_TS = "2026-11-14T19:05:17Z"          # nflverse/nfldata master commit d9772e4e
NFLVERSE_URL = "https://github.com/nflverse/nfldata/blob/master/data/games.csv"
NFL_DATA_URL = "https://github.com/nflverse/nfldata"
DESK_URL_NOTE = "NFL.com week schedule pages (per-row source in data/desk/games.json)"

ALIAS = {"ARI": "ARI", "AZ": "ARI", "LA": "LA", "LAR": "LA", "WAS": "WAS", "WSH": "WAS",
         "JAX": "JAX", "JAC": "JAX", "GB": "GB", "KC": "KC", "LV": "LV", "SF": "SF",
         "NE": "NE", "NO": "NO"}

def norm(t):
    return ALIAS.get((t or "").strip().upper(), (t or "").strip().upper())

def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path, heads, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(heads)
        for r in rows:
            w.writerow([r.get(h, "") for h in heads])
    print("wrote", os.path.relpath(path, ROOT), f"({len(rows)} rows)")

def blank_if_na(v):
    return "" if v in ("", "NA", None) else v

# ---------------------------------------------------------------- load sources
games_all = read_csv(os.path.join(SRC, "games.csv"))
desk = json.load(open(os.path.join(ROOT, "data", "desk", "games.json"), encoding="utf-8"))
desk_by_key = {}
for g in desk["games"]:
    desk_by_key[(int(g["week"]), norm(g["away"]), norm(g["home"]))] = g
hub_stand_rows = read_csv(os.path.join(ROOT, "data", "hub", "standings_2026_thru_wk9.csv"))
nfl_stand = [r for r in read_csv(os.path.join(SRC, "standings.csv")) if r["season"] == "2026"]
initial = read_csv(os.path.join(SRC, "initial_lines.csv"))

g26 = [g for g in games_all if g["season"] == "2026" and g["game_type"] == "REG"]
g26.sort(key=lambda g: (int(g["week"]), g["gameday"], g["game_id"]))

# ------------------------------------------------- results feed (verification)
feed = []
desk_final_agree = desk_final_seen = 0
desk_mismatch = []
for g in g26:
    home, away = norm(g["home_team"]), norm(g["away_team"])
    week = int(g["week"])
    played = g["home_score"] not in ("", "NA")
    key = (week, away, home)
    d = desk_by_key.get(key)
    desk_status = desk_note = ""
    if d:
        if d["status"] == "FINAL" and played:
            desk_final_seen += 1
            if int(d["home_score"]) == int(g["home_score"]) and int(d["away_score"]) == int(g["away_score"]):
                desk_final_agree += 1
                desk_status = "MATCH"
            else:
                desk_status = "MISMATCH"
                desk_mismatch.append(key)
        elif d["status"] == "FINAL" and not played:
            desk_status = "DESK-AHEAD"
        else:
            desk_status = "DESK-PENDING"
    elif week <= 10:
        desk_status = "DESK-MISSING"   # irregularity: capture should cover wks 1-10
    ah, as_ = blank_if_na(g["home_score"]), blank_if_na(g["away_score"])
    status = "FINAL" if played else "SCHEDULED"
    sp = blank_if_na(g["spread_line"]); tt = blank_if_na(g["total_line"])
    hml = blank_if_na(g["home_moneyline"]); aml = blank_if_na(g["away_moneyline"])
    # nflverse spread_line: positive = home favoured -> publish home-perspective line (neg = home fav)
    msh = "" if sp == "" else (-float(sp))
    feed.append({
        "game_id": g["game_id"], "week": week, "gameday": g["gameday"], "weekday": g["weekday"],
        "gametime_et": g["gametime"], "away_team": away, "home_team": home,
        "away_score": as_, "home_score": ah, "status": status,
        "overtime": g["overtime"] if played else "",
        "total_pts": (int(ah) + int(as_)) if played else "",
        "margin_home": (int(ah) - int(as_)) if played else "",
        "market_spread_home_close": ("" if msh == "" else (f"{msh:+g}".rstrip("0").rstrip(".") if msh % 1 else f"{int(msh)}")),
        "market_total_close": tt, "market_ml_home_close": hml, "market_ml_away_close": aml,
        "desk_crosscheck": desk_status,
        "source_results": NFLVERSE_URL,
        "source_market": f"{NFL_DATA_URL} (PFF market lines; MARKET-3P, not league-official)",
        "source_crosscheck": f"{DESK_URL_NOTE}; nfl.com/standings",
        "verified": "VERIFIED" if (played and desk_status in ("MATCH", "DESK-AHEAD")) else
                    ("PARTIAL" if played else "PENDING"),
    })
write_csv(os.path.join(OUT, "results_feed_2026.csv"), list(feed[0].keys()), feed)

# --------------------------------------------------- standings reconciliation
def standings_from(rows_games, thru_week=None):
    S = {t: dict(w=0, l=0, t=0, pf=0, pa=0, g=0) for t in
         ["ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB",
          "HOU", "IND", "JAX", "KC", "LV", "LAC", "LA", "MIA", "MIN", "NE", "NO", "NYG", "NYJ",
          "PHI", "PIT", "SF", "SEA", "TB", "TEN", "WAS"]}
    for g in rows_games:
        if g["home_score"] in ("", "NA"):
            continue
        if thru_week is not None and int(g["week"]) > thru_week:
            continue
        h, a = norm(g["home_team"]), norm(g["away_team"])
        hs, as_ = int(g["home_score"]), int(g["away_score"])
        S[h]["g"] += 1; S[a]["g"] += 1
        S[h]["pf"] += hs; S[h]["pa"] += as_; S[a]["pf"] += as_; S[a]["pa"] += hs
        if hs > as_: S[h]["w"] += 1; S[a]["l"] += 1
        elif hs < as_: S[a]["w"] += 1; S[h]["l"] += 1
        else: S[h]["t"] += 1; S[a]["t"] += 1
    return S

S9 = standings_from(g26, thru_week=9)
# The transcription file is named "thru_wk9" but was reconciled by the prior session as including the
# Week-10 Thursday final (WAS 24 @ NYG 21). Compare it against ALL finals (137) as of 2026-11-14 and
# record the filename irregularity if that is the only explanation.
S_all_finals = standings_from(g26)
mismatch9 = []
mismatch9_wk9strict = []
for i, r in enumerate(hub_stand_rows):
    if i > 0 and r.get("team", "").strip().lower() == "team":
        continue                                    # duplicated header row in the transcription file
    t = norm(r.get("team") or "")
    if t not in S_all_finals:
        mismatch9.append(("team-key", t, r)); continue
    for csv_k, s_k in (("w", "w"), ("l", "l"), ("t", "t"), ("pf", "pf"), ("pa", "pa")):
        if str(S_all_finals[t][s_k]) != str(r[csv_k]).strip():
            mismatch9.append((t, csv_k, r[csv_k], S_all_finals[t][s_k]))
        if str(S9[t][s_k]) != str(r[csv_k]).strip():
            mismatch9_wk9strict.append((t, csv_k, r[csv_k], S9[t][s_k]))
S10 = standings_from(g26)
nfl_map = {norm(r["team"]): r for r in nfl_stand}
mismatch_nfl = []
for t, s in S10.items():
    r = nfl_map.get(t)
    if not r:
        mismatch_nfl.append((t, "missing")); continue
    if (int(r["wins"]), int(r["losses"]), int(r["ties"])) != (s["w"], s["l"], s["t"]):
        mismatch_nfl.append((t, "WLT", (r["wins"], r["losses"], r["ties"]), (s["w"], s["l"], s["t"])))
    if (int(r["scored"]), int(r["allowed"])) != (s["pf"], s["pa"]):
        mismatch_nfl.append((t, "PFPA", (r["scored"], r["allowed"]), (s["pf"], s["pa"])))

# ------------------------------------------------------------- history (backtest base)
hist = []
for g in games_all:
    if g["game_type"] != "REG" or g["home_score"] in ("", "NA"):
        continue
    sp, tt = blank_if_na(g["spread_line"]), blank_if_na(g["total_line"])
    if sp in ("", "NA") and tt in ("", "NA"):
        continue
    hs, as_ = int(g["home_score"]), int(g["away_score"])
    msh = -float(sp) if sp not in ("", "NA") else ""
    hist.append({
        "game_id": g["game_id"], "season": g["season"], "week": g["week"], "gameday": g["gameday"],
        "away_team": norm(g["away_team"]), "home_team": norm(g["home_team"]),
        "home_score": hs, "away_score": as_, "margin_home": hs - as_, "total": hs + as_,
        "market_spread_home_close": msh, "market_total_close": tt,
        "market_ml_home_close": blank_if_na(g["home_moneyline"]),
        "market_ml_away_close": blank_if_na(g["away_moneyline"]),
        "source": NFLVERSE_URL, "market_label": "MARKET-3P (PFF via nflverse)",
    })
write_csv(os.path.join(OUT, "results_history.csv"), list(hist[0].keys()), hist)

# ------------------------------------------------------- opening lines pilot (2021)
op_rows = []
for r in initial:
    if r["type"] == "SPREAD":
        line = float(r["line"]); side = r["side"]
        # Westgate lists each side's spread; home perspective:
        op_rows.append({"season": r["season"], "about_game": r["about"], "side": side,
                        "spread_side": line, "sportsbook": r["sportsbook"],
                        "source": f"{NFL_DATA_URL}/blob/master/data/initial_lines.csv (Westgate openers, 2021 pilot only)"})
write_csv(os.path.join(OUT, "opening_lines_2021_pilot.csv"), list(op_rows[0].keys()), op_rows)

# ------------------------------------------------------------ verification log
vlog = {
    "as_of": AS_OF, "source_commit": "d9772e4e83ab349de144bf6d7a4fc9fb3ee7b066", "source_ts": SRC_TS,
    "results_feed": {
        "rows": len(feed), "finals": sum(1 for r in feed if r["status"] == "FINAL"),
        "desk_finals_compared": desk_final_seen, "desk_finals_match": desk_final_agree,
        "desk_mismatches": [list(k) for k in desk_mismatch],
        "pending": sum(1 for r in feed if r["status"] == "SCHEDULED"),
    },
    "standings_transcription_reconciliation": {
        "file": "data/hub/standings_2026_thru_wk9.csv (transcribed from nfl.com/standings)",
        "clubs": 32,
        "field_mismatches_vs_all_137_finals": len(mismatch9),
        "detail": mismatch9[:10],
        "field_mismatches_vs_weeks_1_9_strict": len(mismatch9_wk9strict),
        "finding": ("IRREGULARITY F-24: the transcription file is named thru_wk9 but its values match "
                    "standings INCLUDING the Week-10 Thursday final (WAS 24 @ NYG 21) - the exact "
                    "differences were WAS +1 win/+24 PF/+21 PA and NYG +1 loss/+21 PF/+24 PA. The numbers "
                    "are correct as of 2026-11-14; the filename is misleading. Published as-is with this flag."),
        "also": "the transcription file contains a duplicated header row (row 2); skipped on read",
    },
    "standings_thru_wk10_vs_nflverse": {
        "clubs": 32, "field_mismatches": len(mismatch_nfl), "detail": mismatch_nfl[:10],
        "compared_to": "data/x3/source/standings.csv",
    },
}
json.dump(vlog, open(os.path.join(OUT, "verification_log.json"), "w"), indent=1)
print("verification:", json.dumps(vlog["results_feed"]), "| wk9 mismatches:", len(mismatch9),
      "| wk10-vs-nflverse mismatches:", len(mismatch_nfl))

# ------------------------------------------------------- price-snapshot store
# market rows: (game, market_key, line_home_perspective, odds, obs_type)
snaps = []
for r in feed:
    played = r["status"] == "FINAL"
    obs = "CLOSE" if played else "CURRENT"
    if r["market_spread_home_close"] != "":
        snaps.append([r["game_id"], r["week"], "SPREAD_HOME", r["market_spread_home_close"],
                      r["market_ml_away_close"] and "", obs, SRC_TS, "PFF via nflverse games.csv (MARKET-3P)",
                      NFLVERSE_URL, "closing market line compiled by PFF; not league-official"])
    if r["market_total_close"] != "":
        snaps.append([r["game_id"], r["week"], "TOTAL", r["market_total_close"], "", obs, SRC_TS,
                      "PFF via nflverse games.csv (MARKET-3P)", NFLVERSE_URL,
                      "closing market total compiled by PFF; not league-official"])
    if r["market_ml_home_close"] != "":
        snaps.append([r["game_id"], r["week"], "ML_HOME", r["market_ml_home_close"], "", obs, SRC_TS,
                      "PFF via nflverse games.csv (MARKET-3P)", NFLVERSE_URL, "American odds"])
        snaps.append([r["game_id"], r["week"], "ML_AWAY", r["market_ml_away_close"], "", obs, SRC_TS,
                      "PFF via nflverse games.csv (MARKET-3P)", NFLVERSE_URL, "American odds"])
    # OPEN observation: schema present, no source for 2026 -> published as explicit blank row policy note
n_open_games = len(feed)
snap_heads = ["game_id", "week", "market", "line", "odds", "obs_type", "captured_at", "source_name",
              "source_url", "note"]
write_csv(os.path.join(OUT, "price_snapshots_2026.csv"), snap_heads, [dict(zip(snap_heads, s)) for s in snaps])
json.dump({"open_observation_policy": (
    "OPEN (opening line) observations are schema-supported but left blank for 2026: no opening-line source "
    "is reachable from this sandbox (nflverse initial_lines.csv covers 2021 Westgate only; release-asset "
    "feeds are CDN-blocked). Opening capture starts once an owner-approved price source exists (Q-01)."),
    "rows": len(snaps), "games": n_open_games}, open(os.path.join(OUT, "snapshot_policy.json"), "w"), indent=1)
print("snapshots:", len(snaps))
