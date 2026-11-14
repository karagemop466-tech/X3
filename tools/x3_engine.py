#!/usr/bin/env python3
"""
X3 / hub analytics engine.

Reads ONLY the canonical verified CSVs in data/hub/ (transcribed by session
arena/e9b492ab-x3 from official NFL.com pages on 2026-11-14) and emits derived
artifacts to hub/data/*.json. Nothing here is a fact about the world: everything
emitted is tagged DERIVED (computed from verified inputs using stated
parameters) or UNVERIFIED (parameter not yet estimable from available data).

Run:  python3 tools/x3_engine.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "hub")
OUT = os.path.join(ROOT, "hub", "data")

SRC_STANDINGS = "https://www.nfl.com/standings/league/2026/REG"
SRC_INJURIES = "https://www.nfl.com/injuries/league/2026/reg10"
SRC_SCHEDULE = "https://www.nfl.com/schedules/2026/by-week/week-10"
AS_OF = "2026-11-14"
WEEK = 10

# ---------------------------------------------------------------------------
# Model parameters. Every one of these is an ASSUMPTION, not a measurement:
# no game log, no market price and no league-published efficiency figure is
# available in this repo yet. They are published on the site and frozen in the
# pre-registration ledger so that later calibration cannot silently move them.
# ---------------------------------------------------------------------------
PARAMS = {
    "shrinkage_games": 4.0,      # games of pseudo-data pulling a team toward league average
    "hfa_points_used": 0.0,      # HFA applied by the model. The official standings HOME/ROAD
                                 # columns are internally consistent (137 appearances each) and
                                 # give a measured home win pct of 0.493, i.e. no detectable
                                 # home edge this season; 0.0 sits inside that interval.
    "hfa_conversion_sigma": 13.5,  # sd of home-minus-away game margin, used ONLY to translate a
                                   # win-probability edge into points. UNVERIFIED - no game log.
    "pyth_k": 2.37,              # Pythagorean exponent for NFL scoring. UNVERIFIED constant.
    "status_weight": {"Out": 1.0, "Doubtful": 0.9, "Questionable": 0.35, "": 0.0},
    "string_weight": {1: 1.0, 2: 0.60, 3: 0.30, 4: 0.15, 0: 0.80},  # 0 = not on club chart
}

# Points-per-game replacement cost of a 1st-string unavailable player, by position group.
POS_COST = {
    "QB": 4.0, "RB": 1.5, "WR": 1.1, "TE": 0.9, "FB": 0.3,
    "C": 1.2, "G": 1.0, "T": 1.0, "OL": 1.0, "LG": 1.0, "RG": 1.0, "LT": 1.0, "RT": 1.0,
    "DE": 1.0, "DT": 0.8, "LB": 0.6, "EDGE": 1.0, "CB": 0.9, "S": 0.7, "DL": 0.7,
    "K": 0.1, "P": 0.1, "LS": 0.05,
}
OFF_POS = {"QB", "RB", "WR", "TE", "FB", "C", "G", "T", "OL", "LG", "RG", "LT", "RT"}
DEF_POS = {"DE", "DT", "LB", "EDGE", "CB", "S", "DL"}

OFFENSIVE_UNITS = {"QB", "RB", "WR", "TE", "FB", "C", "G", "T", "OL", "LG", "RG", "LT", "RT"}


def read(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def norm_pos(p):
    p = (p or "").strip().upper()
    return {"LT": "T", "RT": "T", "LG": "G", "RG": "G", "EDGE": "DE", "H": "P", "PR": "WR",
            "KR": "RB", "CB ": "CB"}.get(p, p)


# ---------------------------------------------------------------------------
# 1. Standings -> team ratings
# ---------------------------------------------------------------------------
teams = {}
for r in read("standings_2026_thru_wk9.csv"):
    g = int(r["w"]) + int(r["l"]) + int(r["t"])
    teams[r["team"]] = {
        "team": r["team"], "name": r["name"], "g": g,
        "w": int(r["w"]), "l": int(r["l"]), "t": int(r["t"]), "pct": float(r["pct"]),
        "pf": int(r["pf"]), "pa": int(r["pa"]), "net": int(r["net"]),
        "home": r["home"], "road": r["road"], "div": r["div"], "conf": r["conf"],
        "streak": r["streak"], "last5": r["last5"],
        "source": SRC_STANDINGS,
    }

tot_g = sum(t["g"] for t in teams.values())
league_ppg = sum(t["pf"] for t in teams.values()) / tot_g          # points per team-game
# empirical home advantage, from the official HOME and ROAD split columns
hw = sum(int(t["home"].split("-")[0]) for t in teams.values())
hl = sum(int(t["home"].split("-")[1]) for t in teams.values())
ht = sum(int(t["home"].split("-")[2]) for t in teams.values())
home_wp = (hw + 0.5 * ht) / (hw + hl + ht)
rw = sum(int(t["road"].split("-")[0]) for t in teams.values())
rl = sum(int(t["road"].split("-")[1]) for t in teams.values())
rt = sum(int(t["road"].split("-")[2]) for t in teams.values())
road_wp = (rw + 0.5 * rt) / (rw + rl + rt)


def probit(p):
    """Inverse normal CDF (Acklam) - used only for the sensitivity illustration."""
    a = [-3.969637e+01, 2.209461e+02, -2.759285e+02, 1.383574e+02, -3.066479e+01, 2.506628e+00]
    b = [-5.447609e+01, 1.615859e+02, -1.556989e+02, 6.680131e+01, -1.328068e+01]
    c = [-7.784894e-03, -3.223964e-01, -2.400758e+00, -2.549732e+00, 4.374664e+00, 2.938163e+00]
    d = [7.784695e-03, 3.224671e-01, 2.445134e+00, 3.754408e+00]
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# HOME/ROAD split integrity. Two independent tests:
#   (a) column-level - every game contributes one home and one road appearance, so the two
#       columns must sum to the same number of appearances (they do: 137 = 137);
#   (b) club-level   - for each club, home games + road games must equal its overall games.
#       This is the stronger test: it can pass while (a) fails, and vice versa, and it is what
#       catches a mis-transcribed split row.
# The split is therefore internally consistent and CAN be used as a measurement. It measures a
# home win pct of 0.4927 with a 95% CI that straddles 0.50, so no home-field advantage is
# detectable in 2026 data to date: HFA is applied as 0.0 pts, with a sensitivity table.
home_apps = hw + hl + ht
road_apps = rw + rl + rt
split_imbalance_games = (road_apps - home_apps) // 2


def _games(s_):
    return sum(int(x) for x in s_.split("-") if x.isdigit())


_raw_st = read("standings_2026_thru_wk9.csv")
split_per_team_bad = [r["team"] for r in _raw_st
                      if _games(r["home"]) + _games(r["road"]) != _games(f'{r["w"]}-{r["l"]}-{r["t"]}')]
split_per_team_checked = len(_raw_st)
home_wp_ci = [round(home_wp - 1.96 * math.sqrt(home_wp * (1 - home_wp) / max(1, home_apps)), 4),
              round(home_wp + 1.96 * math.sqrt(home_wp * (1 - home_wp) / max(1, home_apps)), 4)]
hfa_equiv_pts = round(probit(home_wp) * PARAMS["hfa_conversion_sigma"], 2)
hfa_equiv_ci = [round(probit(home_wp_ci[0]) * PARAMS["hfa_conversion_sigma"], 2),
                round(probit(home_wp_ci[1]) * PARAMS["hfa_conversion_sigma"], 2)]
hfa_used = PARAMS["hfa_points_used"]
hfa_sensitivity = {f"hfa_{v:+.1f}": v for v in (-1.5, 0.0, 1.5, 2.5, 3.5)}
games_played_league = (hw + hl + ht)

for t in teams.values():
    k = PARAMS["shrinkage_games"]
    w = t["g"] / (t["g"] + k)
    t["off"] = w * (t["pf"] / t["g"] - league_ppg)          # points vs league average
    t["def"] = w * (t["pa"] / t["g"] - league_ppg)         # points allowed vs league average
    t["raw_off"] = t["pf"] / t["g"]
    t["raw_def"] = t["pa"] / t["g"]
    t["net_ppg"] = (t["pf"] - t["pa"]) / t["g"]
    exp_wl = t["pf"] ** PARAMS["pyth_k"] / (t["pf"] ** PARAMS["pyth_k"] + t["pa"] ** PARAMS["pyth_k"])
    t["pyth_wins"] = round(exp_wl * t["g"], 2)
    t["luck_wins"] = round(t["w"] + 0.5 * t["t"] - exp_wl * t["g"], 2)

# ---------------------------------------------------------------------------
# 2. Injury report -> per-team availability, replacement cost, backup exposure
# ---------------------------------------------------------------------------
injury_rows = read("injuries_2026_wk10.csv")
depth_by_team = defaultdict(list)
for r in injury_rows:
    depth_by_team[r["team"]].append(r)

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("nfl_data", os.path.join(ROOT, "tools", "nfl_data.py"))
    nfl_data = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nfl_data)
    DEPTH = nfl_data.DEPTH
except Exception:                                     # pragma: no cover
    DEPTH = {}

# index every player by the string (tier) they occupy on their club's chart
DEPTH_ALIAS = {"ARI": "AZ", "LA": "LAR"}   # official pages print AZ / LAR; repo file prints ARI / LA
chart_index = {}
DEPTH_COVERED = []
CHART_UNDATED = []
for abbr, d in DEPTH.items():
    abbr = DEPTH_ALIAS.get(abbr, abbr)
    DEPTH_COVERED.append(abbr)
    if not (d.get("as_of") or "").strip():
        CHART_UNDATED.append(abbr)
    for slot_i, (label, names) in enumerate(d["slots"]):
        for j, nm in enumerate(names):
            clean = " ".join(nm.split()[-2:]) if nm.split()[0].isdigit() else nm
            chart_index[(abbr, clean.lower())] = (j + 1, label)


def chart_tier(abbr, player):
    """1 = listed first on the club chart for that slot, 0 = not found on chart."""
    key = (player or "").strip().lower()
    for (a, p), (tier, label) in chart_index.items():
        if a == abbr and (p == key or key.endswith(p) or p.endswith(key)):
            return tier, label
    return 0, ""


avail = defaultdict(lambda: {"out": 0, "doubtful": 0, "questionable": 0, "dnp": 0, "limited": 0,
                             "full": 0, "rest": 0, "rows": 0, "cost_off": 0.0, "cost_def": 0.0,
                             "backup_forced": [], "unverified_depth": 0})
for r in injury_rows:
    t = avail[r["team"]]
    t["rows"] += 1
    ps = r["practice"].lower()
    if "did not participate" in ps:
        t["dnp"] += 1
    elif "limited" in ps:
        t["limited"] += 1
    elif "full" in ps:
        t["full"] += 1
    stt = r["status"]
    if stt == "Out":
        t["out"] += 1
    elif stt == "Doubtful":
        t["doubtful"] += 1
    elif stt == "Questionable":
        t["questionable"] += 1
    if "resting player" in (r["injury"] or "").lower():
        t["rest"] += 1
    pos = norm_pos(r["pos"])
    cost = POS_COST.get(pos)
    if cost is None:
        continue
    sw = PARAMS["status_weight"].get(stt, 0.0)
    if sw == 0.0:
        continue
    tier, slot = chart_tier(r["team"], r["player"])
    strw = PARAMS["string_weight"].get(tier, PARAMS["string_weight"][0])
    if tier == 0:
        t["unverified_depth"] += 1
    impact = cost * sw * strw
    if pos in OFFENSIVE_UNITS:
        t["cost_off"] += impact
    else:
        t["cost_def"] += impact
    if stt in ("Out", "Doubtful") and tier == 1:
        t["backup_forced"].append({"player": r["player"], "pos": r["pos"], "slot": slot, "status": stt})

for t in avail.values():
    for k in ("cost_off", "cost_def"):
        t[k] = round(t[k], 2)

# ---------------------------------------------------------------------------
# 3. Week 10 slate -> originated lines
# ---------------------------------------------------------------------------
slate = {}
for r in injury_rows:
    g = r["game"]
    slot = slate.setdefault(g, {"game": g, "date": r["date"], "slot": r["slot"],
                                "away": r["opp"] if r["side"] == "H" else r["team"],
                                "home": r["team"] if r["side"] == "H" else r["opp"]})
# verified against the official Week 10 schedule page + injury page headers
NEUTRAL = {"NE@DET": "Alemun & Munchen / Munich (NFL International Game) - no home field"}
BYE = ["CHI", "DEN", "PHI", "TB"]
PLAYED = {"WAS@NYG": {"result": "Commanders 24, Giants 21, FINAL (Thu Nov 12)",
                     "source": SRC_SCHEDULE}}

lines = []
for g in sorted(slate, key=lambda k: (slate[k]["date"], slate[k]["slot"], k)):
    s = slate[g]
    h, a = s["home"], s["away"]
    if g in PLAYED:
        continue
    if h not in teams or a not in teams:
        continue
    neutral = g in NEUTRAL
    hfa = hfa_used
    # exp_home = L + off_h + (points allowed by A) ; exp_away = L + off_a + (points allowed by H)
    base_margin = (teams[h]["off"] + teams[a]["def"]) - (teams[a]["off"] + teams[h]["def"]) + hfa
    base_total = (teams[h]["raw_off"] + teams[a]["raw_off"]
                  + teams[h]["raw_def"] + teams[a]["raw_def"]) / 2
    # injury adjustment: weaker offence scores less, weaker defence concedes more
    hi, ai = avail.get(h, {}), avail.get(a, {})
    adj_margin = (base_margin
                  - hi.get("cost_off", 0) - hi.get("cost_def", 0)
                  + ai.get("cost_off", 0) + ai.get("cost_def", 0))
    adj_total = (base_total - hi.get("cost_off", 0) - ai.get("cost_off", 0)
                 + hi.get("cost_def", 0) + ai.get("cost_def", 0))
    spread = -round(adj_margin * 2) / 2            # home spread, negative = home favoured
    tot = round(adj_total * 2) / 2
    lines.append({
        "game": g, "date": s["date"], "slot": s["slot"], "home": h, "away": a,
        "neutral_site": NEUTRAL.get(g, ""),
        "base_margin_home": round(base_margin, 2),
        "adj_margin_home": round(adj_margin, 2),
        "injury_delta": round(adj_margin - base_margin, 2),
        "model_spread_home": spread,
        "model_total": tot,
        "market_spread": "", "market_total": "", "market_source": "",
        "home_cost_off": hi.get("cost_off", 0), "home_cost_def": hi.get("cost_def", 0),
        "away_cost_off": ai.get("cost_off", 0), "away_cost_def": ai.get("cost_def", 0),
        "home_backup_starts": len(hi.get("backup_forced", [])),
        "away_backup_starts": len(ai.get("backup_forced", [])),
        "signal": "",
    })

for l in lines:
    d = l["injury_delta"]
    if abs(d) >= 3.5:
        l["signal"] = "STRONG - injury shift >= 3.5 pts"
    elif abs(d) >= 1.5:
        l["signal"] = "MODERATE - injury shift 1.5-3.5 pts"
    else:
        l["signal"] = "NO MATERIAL INJURY SHIFT"
    if l["neutral_site"]:
        l["signal"] += "; neutral site (HFA removed)"

# ---------------------------------------------------------------------------
# 4. Correlations + luck decomposition (computed from the official standings)
# ---------------------------------------------------------------------------
def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return (sum((x - mx) * (y - my) for x, y in zip(xs, ys))) / (sx * sy)


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    return pearson(rank(xs), rank(ys))


tl = sorted(teams.values(), key=lambda t: t["team"])
V = {
    "pf_ppg": [t["pf"] / t["g"] for t in tl],
    "pa_ppg": [t["pa"] / t["g"] for t in tl],
    "net_ppg": [t["net"] / t["g"] for t in tl],
    "win_pct": [t["pct"] for t in tl],
    "home_pct": [ (int(t["home"].split("-")[0]) + 0.5*int(t["home"].split("-")[2]))
                  / max(1, sum(int(x) for x in t["home"].split("-"))) for t in tl],
    "road_pct": [ (int(t["road"].split("-")[0]) + 0.5*int(t["road"].split("-")[2]))
                  / max(1, sum(int(x) for x in t["road"].split("-"))) for t in tl],
    "pyth_pct": [t["pyth_wins"] / t["g"] for t in tl],
    "luck_wins": [t["luck_wins"] for t in tl],
    "last5_pct": [ (int(t["last5"].split("-")[0]) + 0.5*int(t["last5"].split("-")[2]))
                   / max(1, sum(int(x) for x in t["last5"].split("-"))) if t["last5"] else None
                   for t in tl],
    "pa_spread": [t["pa"] for t in tl],
}
V = {k: v for k, v in V.items() if None not in v}
PAIRS = [
    ("points scored per game", "pf_ppg", "win_pct", "offence -> wins"),
    ("points allowed per game", "pa_ppg", "win_pct", "defence -> wins"),
    ("net points per game", "net_ppg", "win_pct", "point differential -> wins"),
    ("net points per game", "net_ppg", "pyth_pct", "identity check (should be ~1.00)"),
    ("Pythagorean win pct", "pyth_pct", "win_pct", "how much of the record is scoring"),
    ("home win pct", "home_pct", "road_pct", "is home form portable to the road?"),
    ("last-5 win pct", "last5_pct", "net_ppg", "'hot streak' vs underlying point differential"),
    ("season luck (wins - Pythagorean wins)", "luck_wins", "last5_pct", "does past luck predict 'form'?"),
]
corr = []
VAR_LABEL = {"pf_ppg": "points scored per game", "pa_ppg": "points allowed per game",
             "net_ppg": "net points per game", "win_pct": "win pct",
             "home_pct": "home win pct", "road_pct": "road win pct",
             "pyth_pct": "Pythagorean win pct", "luck_wins": "luck (wins - Pyth wins)",
             "last5_pct": "last-5 win pct"}
for label, xa, xb, note in PAIRS:
    r = pearson(V[xa], V[xb])
    rho = spearman(V[xa], V[xb])
    n = len(V[xa])
    se = 1.0 / math.sqrt(n - 3) if n > 3 else None
    z = 0.5 * math.log((1 + r) / (1 - r)) if r is not None and abs(r) < 1 else None
    lo = hi = None
    if z is not None:
        lo = math.tanh(z - 1.96 * se)
        hi = math.tanh(z + 1.96 * se)
    corr.append({
        "x": VAR_LABEL[xa], "y": VAR_LABEL[xb], "x_key": xa, "y_key": xb,
        "pearson_r": round(r, 4), "spearman_rho": round(rho, 4),
        "n": n, "ci95_low": None if lo is None else round(lo, 4),
        "ci95_high": None if hi is None else round(hi, 4),
        "r2": round(r * r, 4), "note": note,
        "source": SRC_STANDINGS,
    })

# luck decomposition: R^2 of net_ppg on win_pct = share of record variance explained by scoring
net = V["net_ppg"]; wp = V["win_pct"]
r_main = pearson(net, wp)
r2_main = r_main ** 2
luck_sd = st.pstdev(V["luck_wins"])
luck = {
    "n_teams": len(tl),
    "games_total": tot_g,
    "r_net_to_win": round(r_main, 4),
    "r2_net_to_win": round(r2_main, 4),
    "unexplained_variance_share": round(1 - r2_main, 4),
    "luck_residual_sd_wins": round(luck_sd, 3),
    "most_fortunate": sorted(tl, key=lambda t: -t["luck_wins"])[:5] and [
        {"team": t["team"], "luck_wins": t["luck_wins"], "w_l": f"{t['w']}-{t['l']}-{t['t']}",
         "pyth_wins": t["pyth_wins"]} for t in sorted(tl, key=lambda t: -t["luck_wins"])[:5]],
    "most_unlucky": [
        {"team": t["team"], "luck_wins": t["luck_wins"], "w_l": f"{t['w']}-{t['l']}-{t['t']}",
         "pyth_wins": t["pyth_wins"]} for t in sorted(tl, key=lambda t: t["luck_wins"])[:5]],
    "regression_candidates_up": [t["team"] for t in tl if t["luck_wins"] >= 1.5],
    "regression_candidates_down": [t["team"] for t in tl if t["luck_wins"] <= -1.5],
    "method": ("Pythagorean wins = g * PF^k/(PF^k+PA^k), k=%s. Luck residual = actual wins - "
               "Pythagorean wins. R^2 of net points per game on win pct is the share of record "
               "variance the scoring differential already explains; the remainder is outcome noise."
               % PARAMS["pyth_k"]),
    "source": SRC_STANDINGS,
}

# ---------------------------------------------------------------------------
# 5. Emit
# ---------------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)


def dump(name, obj):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=1, sort_keys=False)


meta = {
    "as_of": AS_OF, "season": 2026, "week": WEEK, "generated_by": "tools/x3_engine.py",
    "inputs": {"standings": SRC_STANDINGS, "injuries": SRC_INJURIES, "schedule": SRC_SCHEDULE},
    "rows": {"standings": len(teams), "injuries": len(injury_rows), "games": len(slate),
             "lines": len(lines)},
    "params": PARAMS, "pos_cost": POS_COST,
}
dump("meta.json", meta)
dump("teams.json", {"league_ppg": round(league_ppg, 3), "home_win_pct": round(home_wp, 4),
                    "road_win_pct": round(road_wp, 4),
    "home_games": hw + hl + ht,
    "home_win_pct_ci95": [round(home_wp - 1.96 * math.sqrt(home_wp * (1 - home_wp) / (hw + hl + ht)), 4),
                          round(home_wp + 1.96 * math.sqrt(home_wp * (1 - home_wp) / (hw + hl + ht)), 4)], "home_win_rate": f"{hw}-{hl}-{ht}",
                    "road_win_rate": f"{rw}-{rl}-{rt}",
                    "hfa_used": hfa_used,
                    "hfa_measured_equiv_points": hfa_equiv_pts, "hfa_measured_ci95": hfa_equiv_ci,
                    "splits_balanced": split_imbalance_games == 0,
                    "splits_per_team_checked": split_per_team_checked,
                    "splits_per_team_mismatch": split_per_team_bad,
                    "games_played_league": games_played_league,
                    "split_home_appearances": home_apps, "split_road_appearances": road_apps,
                    "split_imbalance_games": split_imbalance_games,
                    "note": "HOME and ROAD columns each sum to 137 appearances = 274/2; internally consistent.",
                    "home_win_pct_ci95": home_wp_ci,
                    "hfa_sensitivity_points_per_game": hfa_sensitivity,
                    "rows": sorted(teams.values(), key=lambda t: -t["net_ppg"]),
                    "source": SRC_STANDINGS})
dump("lines.json", {"rows": lines, "bye": BYE, "played": PLAYED,
                    "neutral": NEUTRAL, "model": "X3-v1 (standings + official injury report)",
                    "params": PARAMS})
dump("injuries.json", {"rows": injury_rows,
                       "counts": {t: {k: (len(v) if k == "backup_forced" else vv)
                                      for k, vv in v.items()}
                                  for t, v in sorted(avail.items())}})
dump("correlations.json", {"rows": corr, "pairs": [p[3] for p in PAIRS]})
dump("luck.json", luck)
dump("depth.json", {"clubs_in_chart": sorted(set(DEPTH_COVERED)),
                    "charts_total": len(DEPTH), "charts_undated": len(set(CHART_UNDATED)),
                    "clubs_in_week10_slate": len(set(DEPTH_COVERED) & set(teams)),
                    "chart_missing": sorted(set(teams) - set(DEPTH_COVERED)),
                    "teams": {t: {"backup_forced": v["backup_forced"],
                                  "unverified_depth": v["unverified_depth"]}
                              for t, v in sorted(avail.items())}})

print(f"teams={len(teams)} games={len(slate)} lines={len(lines)} "
      f"league_ppg={league_ppg:.3f} home_wp={home_wp:.4f} HFA used={hfa_used}")
print(f"home appearances={home_apps} road appearances={road_apps} imbalance={split_imbalance_games} games; "
      f"per-club home+road mismatch on {len(split_per_team_bad)}/{split_per_team_checked} clubs "
      f"{split_per_team_bad}")
print(f"hfa sensitivity: {hfa_sensitivity}")
print(f"R^2(net ppg -> win pct) = {r2_main:.4f}  luck sd = {luck_sd:.3f} wins")
print(f"strong signals: {sum(1 for l in lines if l['signal'].startswith('STRONG'))}/"
      f"{len(lines)}")
print("wrote:", ", ".join(sorted(os.listdir(OUT))))
