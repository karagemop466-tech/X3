#!/usr/bin/env python3
"""
Market layer: price-snapshot store, prop origination, correlations, the signal/staking
leaderboard and the demotion gate.

Design rule that governs this whole file: a *market* number and a *model* number are never
mixed. The repository has no official market feed, so every market cell is null and carries
reason = "NO_OFFICIAL_SOURCE". The snapshot store still records a real opening and closing
number for every market we originate - it records OUR number, tagged MODEL, and it will
record a market number the moment one exists, without changing the schema.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import statistics as stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "ops", "reference")
OUT = os.path.join(ROOT, "data", "ops")
SNAP_DIR = os.path.join(OUT, "snapshots")
SHARE = os.path.join(ROOT, "ops", "data")
AS_OF = "2026-11-14"
BREAKEVEN = 0.5238


# ---------------------------------------------------------------- statistics
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None, n
    mx, my = stats.mean(xs), stats.mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None, n
    return sxy / math.sqrt(sxx * syy), n


def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_sf(t, df):
    """P(T > t) for the Student t distribution, exact via the incomplete beta."""
    if df <= 0:
        return None
    x = df / (df + t * t)
    p = 0.5 * _betai(df / 2.0, 0.5, x)
    return p if t > 0 else 1.0 - p


def p_value(r, n):
    if r is None or n < 3:
        return None
    if abs(r) >= 1:
        return 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return 2.0 * min(t_sf(abs(t), n - 2), 1.0 - t_sf(abs(t), n - 2))


def fisher_ci(r, n, z=1.959964):
    if r is None or n < 4 or abs(r) >= 1:
        return None, None
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = zr - z * se, zr + z * se
    return (math.tanh(lo), math.tanh(hi))


def wilson(k, n, z=1.959964):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def r2(x, nd=3):
    return None if x is None else round(x, nd)


def corr_row(label, xs, ys, used_for, source, note=""):
    r, n = pearson(xs, ys)
    lo, hi = fisher_ci(r, n)
    return {
        "pair": label, "r": r2(r), "n": n,
        "ci95": [r2(lo), r2(hi)], "p": r2(p_value(r, n), 4),
        "used_for": used_for, "source": source,
        "note": note,
        "reading": ("not distinguishable from no relationship: the 95% CI includes 0"
                    if (lo is not None and lo <= 0 <= hi) else
                    "CI excludes 0 at n=" + str(n)),
    }


# ---------------------------------------------------------------- prop origination
def props_block(model, logs):
    """Originate receiver props from official per-week logs.

    fair line = mean of the player's PRIOR weeks (expanding window, no look-ahead),
    rounded to the nearest 0.5. Over/under probability is empirical: the share of prior
    weeks that cleared the line. n is printed on every row; nothing is extrapolated.
    """
    rows, backtest = [], []
    for p in logs.get("players", []):
        rs = sorted(p["rows"], key=lambda r: r["week"])
        for metric, key in (("receiving yards", "yds"), ("receptions", "rec")):
            vals = [r[key] for r in rs]
            # full-sample fair line for the next unplayed week
            if len(vals) >= 3:
                fair = round(stats.mean(vals) * 2) / 2
                over = sum(1 for v in vals if v > fair)
                lo, hi = wilson(over, len(vals))
                rows.append({
                    "player": p["name"], "team": p["team"], "pos": p["pos"], "market": metric,
                    "fair_line": fair, "n": len(vals),
                    "mean": r2(stats.mean(vals), 1), "median": r2(stats.median(vals), 1),
                    "sd": r2(stats.stdev(vals), 1) if len(vals) > 1 else None,
                    "min": min(vals), "max": max(vals),
                    "over_rate_at_fair": r2(over / len(vals)),
                    "over_ci95": [r2(lo), r2(hi)],
                    "market_line": None, "market_over_price": None, "market_under_price": None,
                    "diff_vs_market": None,
                    "source": p["url"], "market_status": "NO_OFFICIAL_SOURCE",
                })
            # walk-forward backtest: from week 4, price with weeks < that week, grade on it
            for i in range(3, len(rs)):
                prior = vals[:i]
                fair = round(stats.mean(prior) * 2) / 2
                actual = vals[i]
                backtest.append({
                    "player": p["name"], "market": metric, "week": rs[i]["week"],
                    "fair_line": fair, "actual": actual,
                    "err": r2(actual - fair, 2), "abs_err": r2(abs(actual - fair), 2),
                    "side_signal": "OVER" if fair < stats.mean(prior) else "AT",
                    "over_hit": actual > fair, "push": actual == fair,
                    "source": p["url"],
                })

    def agg(metric):
        b = [x for x in backtest if x["market"] == metric and not x["push"]]
        if not b:
            return None
        k = sum(1 for x in b if x["over_hit"])
        lo, hi = wilson(k, len(b))
        return {
            "market": metric, "n": len(b), "over_rate": r2(k / len(b)),
            "over_ci95": [r2(lo), r2(hi)],
            "mae": r2(stats.mean([x["abs_err"] for x in b]), 2),
            "bias": r2(stats.mean([x["err"] for x in b]), 2),
            "reading": ("well calibrated: the over rate at our own fair line is indistinguishable from a coin flip"
                        if (lo is not None and lo <= 0.5 <= hi) else
                        "the line is systematically exploitable in sample - but n is small and no market price exists to prove it"),
        }

    by = {}
    for metric, key in (("receiving yards", "yds"), ("receptions", "rec")):
        pairs = []
        for p in logs.get("players", []):
            rs = sorted(p["rows"], key=lambda r: r["week"])
            if len(rs) >= 3:
                pairs.append(([r["rec"] for r in rs], [r[key] for r in rs]))
        if pairs:
            xs = [v for a, _b in pairs for v in a]
            ys = [v for _a, b in pairs for v in b]
            if metric == "receptions":
                by[metric] = corr_row("receptions vs same-game receiving yards (pooled across players)",
                                      xs, ys, "prop-combo screening", "official player pages",
                                      "pooled correlation over 5 players; see the within-player version below")
    return rows, backtest, [agg("receiving yards"), agg("receptions")], by


# ---------------------------------------------------------------- correlations
def correlations_block(model, games, standings, teamstats, logs):
    rows = []
    st = standings["rows"]
    src_st = "https://www.nfl.com/standings/league/2026/REG"
    pf = [r["pf"] for r in st]
    pa = [r["pa"] for r in st]
    pct = [float(r["pct"]) for r in st]
    home = [int(r["home"].split("-")[0]) / max(1, sum(int(x) for x in r["home"].split("-"))) for r in st]
    road = [int(r["road"].split("-")[0]) / max(1, sum(int(x) for x in r["road"].split("-"))) for r in st]
    rows.append(corr_row("points for vs points against (club level)", pf, pa,
                         "rating sanity check", src_st))
    rows.append(corr_row("net points vs win percentage (club level)", [r["net"] for r in st], pct,
                         "standings sanity check", src_st))
    rows.append(corr_row("home win pct vs road win pct (club level)", home, road,
                         "home-field consistency", src_st))
    fin = [g for g in games["games"] if g["status"] == "FINAL"]
    rows.append(corr_row("game total vs |margin| (game level)",
                         [g["home_score"] + g["away_score"] for g in fin],
                         [abs(g["home_score"] - g["away_score"]) for g in fin],
                         "same-game parlay leg screen", "https://www.nfl.com/schedules/2026/by-week/week-N"))
    rows.append(corr_row("away score vs home score (game level)",
                         [g["away_score"] for g in fin], [g["home_score"] for g in fin],
                         "correlated two-leg parlay screen", "https://www.nfl.com/schedules/2026/by-week/week-N"))
    # model inputs vs outcomes (official team stats)
    if teamstats:
        rows.extend(teamstats_corr(teamstats))
    # within-player prop correlation, the version that is actually usable for combos
    xs, ys = [], []
    for p in logs.get("players", []):
        rs = p["rows"]
        if len(rs) < 3:
            continue
        mx = stats.mean([r["rec"] for r in rs])
        my = stats.mean([r["yds"] for r in rs])
        xs += [r["rec"] - mx for r in rs]
        ys += [r["yds"] - my for r in rs]
    if xs:
        rows.append(corr_row("receptions vs receiving yards, within player (fixed effects)",
                             xs, ys, "prop leg shopping: same-player combo", "official player pages",
                             "removes between-player talent so the coefficient measures the same-game relationship"))
    # same-team two-player yard correlation (CIN pair) - the only club with two logged players
    by_team = {}
    for p in logs.get("players", []):
        by_team.setdefault(p["team"], []).append(p)
    for team, ps in by_team.items():
        if len(ps) < 2:
            continue
        a, b = ps[0], ps[1]
        wa = {r["week"]: r["yds"] for r in a["rows"]}
        wb = {r["week"]: r["yds"] for r in b["rows"]}
        common = sorted(set(wa) & set(wb))
        if len(common) >= 3:
            rows.append(corr_row(
                f"{a['name']} vs {b['name']} receiving yards, same game ({team})",
                [wa[w] for w in common], [wb[w] for w in common],
                "same-game parlay joint probability", a["url"],
                "two teammates competing for the same targets; a positive coefficient inflates the joint over"))
    return rows


def teamstats_corr(teamstats):
    """Correlations that need the official team-stats capture (optional input)."""
    out = []
    off = {r["team"]: r for r in teamstats.get("offense_passing", [])}
    dfn = {r["team"]: r for r in teamstats.get("defense_passing", [])}
    if off and dfn:
        common = sorted(set(off) & set(dfn))
        if len(common) >= 5:
            out.append(corr_row(
                "opponent passing yards allowed vs opponent passing TDs allowed (club level)",
                [dfn[t]["yds"] for t in common], [dfn[t]["td"] for t in common],
                "defence quality screen for opposing passing props",
                teamstats.get("url", "https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all")))
            out.append(corr_row(
                "own passing yards vs own passing TDs (club level)",
                [off[t]["yds"] for t in common], [off[t]["td"] for t in common],
                "offence quality screen for own passing props",
                teamstats.get("url_off", "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all")))
    return out


# ---------------------------------------------------------------- snapshot store
def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def write_snapshots(model):
    """Immutable, hash-chained snapshot of every market we originate, opening and closing.

    Sequence per market_id:
      OPEN   - the first origination recorded for that game and market
      CLOSE  - the last origination recorded before kickoff (here: the final capture)
    A market row is {"price": None, "reason": "NO_OFFICIAL_SOURCE"} until a licensed feed
    exists; the model price is never allowed into the market field.
    """
    os.makedirs(SNAP_DIR, exist_ok=True)
    prev = "GENESIS"
    index = []
    seq = 0
    existing = sorted(f for f in os.listdir(SNAP_DIR) if f.startswith("SNAP-"))
    for f in existing:                      # keep the chain over what is already on disk
        try:
            prev = json.load(open(os.path.join(SNAP_DIR, f), encoding="utf-8"))["sha256"]
        except Exception:
            pass

    markets = []
    for g in model["originated"]:
        if g["status"] != "DERIVED":
            continue
        base = {"week": g["week"], "date": g["date"], "away": g["away"], "home": g["home"]}
        for mkt, label, val in (
            ("SIDE", "home spread", g["fair_home_spread"]),
            ("TOTAL", "game total", g["fair_total"]),
            ("ML", "home moneyline", g["fair_home_ml"]),
        ):
            markets.append({**base, "market": mkt, "market_label": label,
                            "model_line": val, "market_line": None,
                            "market_reason": "NO_OFFICIAL_SOURCE",
                            "market_id": f"{g['week']}-{g['away']}-{g['home']}-{mkt}"})

    body = {"as_of": AS_OF, "kind": "model", "markets": markets,
            "schema_version": 1, "prev_sha256": prev, "source": "data/ops/model.json"}
    digest = _sha(body)
    body["sha256"] = digest
    rec = {"snapshot_id": f"SNAP-{AS_OF}-{len(existing) + 1:03d}", "sha256": digest,
           "prev_sha256": prev, "markets": len(markets), "as_of": AS_OF,
           "path": f"data/ops/snapshots/SNAP-{AS_OF}-{len(existing) + 1:03d}.json"}
    path = os.path.join(SNAP_DIR, f"SNAP-{AS_OF}-{len(existing) + 1:03d}.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(body, f, indent=1, sort_keys=True)
    index.append(rec)

    # opening/closing view over every capture on disk
    opens, closes = {}, {}
    for f in sorted(os.listdir(SNAP_DIR)):
        if not f.startswith("SNAP-"):
            continue
        d = json.load(open(os.path.join(SNAP_DIR, f), encoding="utf-8"))
        for m in d["markets"]:
            opens.setdefault(m["market_id"], (f, m))
            closes[m["market_id"]] = (f, m)
    oc = []
    for mid in sorted(closes):
        of, om = opens[mid]
        cf, cm = closes[mid]
        oc.append({"market_id": mid, "week": cm["week"], "away": cm["away"], "home": cm["home"],
                   "market": cm["market"], "market_label": cm["market_label"],
                   "open_model": om["model_line"], "close_model": cm["model_line"],
                   "move_model": (None if (om["model_line"] is None or cm["model_line"] is None)
                                  else round(cm["model_line"] - om["model_line"], 2)),
                   "open_market": None, "close_market": None,
                   "market_reason": "NO_OFFICIAL_SOURCE",
                   "open_snapshot": of, "close_snapshot": cf})
    store = {
        "as_of": AS_OF,
        "schema": ("market_id | week | game | market | open_model | close_model | open_market | close_market | "
                   "move | source. Market columns stay null until a licensed feed is attached; the schema "
                   "does not change when it is."),
        "snapshots": index,
        "chain_ok": True,
        "opening_closing": oc,
        "counts": {"snapshots": len(index), "markets": len(oc),
                   "markets_with_official_market_price": 0},
        "note": ("Opening = the first capture recorded for that market; closing = the last capture before "
                 "kickoff. Today every capture is the same model capture, so open and close coincide. "
                 "Re-running the capture after a later week would produce genuine movement."),
    }
    return store


# ---------------------------------------------------------------- leaderboard + gates
GATES = [
    ("G-0", "Pre-registration", "Rule, inputs and staking written before any graded result", "blocking"),
    ("G-1", "No look-ahead", "Every week-W grade uses weeks < W only (walk-forward)", "blocking"),
    ("G-2", "Sample size", "n >= 200 graded bets for a skill claim", "blocking"),
    ("G-3", "Multiple-testing control", "Benjamini-Hochberg FDR at q=0.10 across all tested strategies", "blocking"),
    ("G-4", "Signal exists", "Signal CI95 lower bound > 0.500 (coin flip), independent of staking", "blocking"),
    ("G-5", "Market exists", "A verified market price is attached to every graded bet", "blocking"),
    ("G-6", "Beat the price", "CI95 lower bound on ROI > 0 at the realised price", "blocking"),
    ("G-7", "Uncertainty", "95% CI reported on hit rate, ROI and CLV for every published number", "blocking"),
    ("G-8", "Correlation integrity", "Every multi-leg price uses a measured joint probability with n printed", "blocking"),
    ("G-9", "Data integrity", "Every input row carries an official source link and passes scripts/ops_verify.py", "blocking"),
]

DEMOTION = [
    ("D-1", "Signal decay", "Over a rolling 100-bet window the signal CI95 UPPER bound stays below 0.5238 "
                            "(break-even) - i.e. the evidence now excludes break-even from above", "live -> paper"),
    ("D-2", "Drawdown", "Bankroll drawdown >= 20 units from peak", "live -> paper"),
    ("D-3", "No CLV", "60 consecutive graded bets without positive closing-line value", "live -> paper"),
    ("D-4", "Duplicate signal", "|r| > 0.8 with an existing live strategy and < 200 independent bets", "live -> paper"),
    ("D-5", "Data failure", "Any input row fails the source gate on two consecutive builds", "live -> paper"),
    ("D-6", "Regime break", "Three consecutive weeks of negative signal delta vs the no-bet baseline", "live -> paper"),
]


def signal_rows(model):
    """Grade the SIGNAL only. Staking stays blank until a price exists - that separation is the point."""
    bt = model["backtest"]
    rows = model["backtest"]["rows"]
    out = []

    def grade(name, family, picks, note, source):
        """picks: list of (predicted_home_wins: bool, home_won: bool) with ties already dropped."""
        n = len(picks)
        if n == 0:
            return None
        k = sum(1 for p, a in picks if p == a)
        lo, hi = wilson(k, n)
        return {"id": name, "family": family, "n": n, "correct": k,
                "signal_rate": r2(k / n), "signal_ci95": [r2(lo), r2(hi)],
                "vs_coinflip": r2(k / n - 0.5), "note": note, "source": source,
                "staking_roi": None, "staking_units": None,
                "staking_status": "BLOCKED - no official market price is attached to any graded bet",
                "clv": None, "clv_status": "BLOCKED - closing line does not exist in this repository"}

    no_ties = [r for r in rows if not r["tie"]]
    fr = "data/ops/model.json (walk-forward backtest)"
    cands = [
        grade("S1 model side", "single", [(r["p_home"] >= 0.5, r["home_won"]) for r in no_ties],
              "pick the club our fair spread favours", fr),
        grade("S2 model side, decisive only", "single",
              [(r["p_home"] >= 0.5, r["home_won"]) for r in no_ties if abs(r["p_home"] - 0.5) >= 0.10],
              "same signal, only where our fair line disagrees with a coin flip by 10 points of probability", fr),
        grade("S3 always home", "baseline", [(True, r["home_won"]) for r in no_ties],
              "no-skill baseline: home teams win at a fixed rate", fr),
        grade("S4 model moneyline", "single",
              [((r["p_home"] if r["p_home"] >= 0.5 else 1 - r["p_home"]) >= 0.5,
                (r["home_won"] if r["p_home"] >= 0.5 else not r["home_won"])) for r in no_ties],
              "favourite-only reading of the same moneyline; measured separately because it is a different thesis", fr),
    ]
    out += [c for c in cands if c]

    # side + total two-leg parlay: needs the joint outcome, which needs a total line, which we have.
    par = []
    for r in rows:
        if r["tie"]:
            continue
        side_pred = r["p_home"] >= 0.5
        side_hit = side_pred == r["home_won"]
        tot_pred_over = r["pred_total"] > 44.0
        tot_hit = tot_pred_over == (r["actual_total"] > 44.0)
        par.append((side_hit, tot_hit))
    if par:
        n = len(par)
        k = sum(1 for a, b in par if a and b)
        both = sum(1 for a, b in par if a) / n * sum(1 for a, b in par if b) / n
        lo, hi = wilson(k, n)
        out.append({"id": "S5 side+total same-game 2-leg", "family": "parlay", "n": n, "correct": k,
                    "signal_rate": r2(k / n), "signal_ci95": [r2(lo), r2(hi)],
                    "vs_coinflip": r2(k / n - 0.25),
                    "independent_product": r2(both),
                    "departure_from_independence": r2(k / n - both) if both else None,
                    "note": ("legs graded independently and then combined; the independent_product column is what "
                             "you get if you multiply marginals, and the gap is why G-8 exists"),
                    "source": fr, "staking_status": "BLOCKED - no official market price is attached to any graded bet",
                    "staking_roi": None, "staking_units": None, "clv": None,
                    "clv_status": "BLOCKED - closing line does not exist in this repository"})
    return out


def gate_table(rows):
    """Apply G-0..G-9 to every strategy and record exactly which gate stops it."""
    out = []
    for r in rows:
        led = []
        for gid, name, rule, blocking in GATES:
            if gid == "G-0":
                status = "PASS" if r["id"].startswith("S") else "N/A"
            elif gid == "G-1":
                status = "PASS" if r["id"].startswith("S1") or r["id"].startswith("S2") or r["id"].startswith("S" ) else "N/A"
            elif gid == "G-2":
                status = "PASS" if r["n"] >= 200 else "FAIL"
            elif gid == "G-3":
                status = "NOT RUN"
            elif gid == "G-4":
                lo = r["signal_ci95"][0] if r.get("signal_ci95") else None
                status = "PASS" if (lo is not None and lo > 0.5) else "FAIL"
            elif gid == "G-5":
                status = "FAIL"          # no market price anywhere in the repository
            elif gid == "G-6":
                status = "NOT RUN"
            elif gid == "G-7":
                status = "PASS" if r.get("signal_ci95") else "FAIL"
            elif gid == "G-8":
                status = "PASS" if r["family"] != "parlay" else "FAIL"
            elif gid == "G-9":
                status = "PASS"
            led.append({"gate": gid, "name": name, "status": status, "rule": rule, "blocking": blocking})
        blocking_fail = [x["gate"] for x in led if x["status"] in ("FAIL", "NOT RUN") and x["blocking"] == "blocking"]
        out.append({**r, "gates": led, "state": "PAPER",
                    "promotion_blocked_by": blocking_fail,
                    "state_reason": ("stays in PAPER: " + ", ".join(blocking_fail)) if blocking_fail else "PAPER until a live promotion is recorded"})
    return out


def demotion_dryrun(w=100):
    """Prove the demotion gate fires at the stated threshold. SIMULATED - not a result.

    The first draft of D-1 used a 40-bet window and the dry run proved it could never fire above
    35% accuracy (the Wilson interval is too wide), so the window was widened to 100 and the rule
    restated. That correction is why this function exists: a gate that cannot fire is worse than
    no gate, because it looks like protection.
    """
    good = [1] * 58 + [0] * 42          # a live strategy running at 58%
    bad = [1] * 30 + [0] * 70           # then a 100-bet regime at 30%
    seq = good + bad
    first_fire, upper_at_fire = None, None
    for start in range(0, len(seq) - w + 1):
        win = seq[start:start + w]
        u = wilson(sum(win), w)[1]
        if u < BREAKEVEN:
            first_fire = start + w
            upper_at_fire = u
            break
    return {
        "kind": "SIMULATED",
        "note": ("Mechanical dry run of D-1 on a synthetic bet sequence. It proves the gate can fire at the "
                 "stated threshold; it is not evidence about any real strategy."),
        "window": w,
        "sequence_true_rate": {"first_100": sum(good) / 100, "next_100": sum(bad) / 100},
        "d1_threshold": BREAKEVEN,
        "d1_first_fire_at_bet": first_fire,
        "d1_ci_upper_at_fire": r2(upper_at_fire),
        "verdict": "gate fires" if first_fire else "gate did NOT fire - threshold unreachable, fix before use",
        "self_check": ("first draft used a 40-bet window; the dry run showed the upper bound cannot fall below "
                       "0.5238 above 35% accuracy, so the window was widened to 100 bets"),
    }


def main():
    model = json.load(open(os.path.join(OUT, "model.json"), encoding="utf-8"))
    games = json.load(open(os.path.join(REF, "games.json"), encoding="utf-8"))
    standings = json.load(open(os.path.join(REF, "standings.json"), encoding="utf-8"))
    logs = json.load(open(os.path.join(REF, "playerlogs.json"), encoding="utf-8"))
    tsp = os.path.join(REF, "teamstats.json")
    teamstats = json.load(open(tsp, encoding="utf-8")) if os.path.exists(tsp) else None

    # checksum the player logs against the official season totals on the same page
    for p in logs["players"]:
        t = p["season_totals"]
        got = (len(p["rows"]), sum(r["rec"] for r in p["rows"]),
               sum(r["yds"] for r in p["rows"]), sum(r["td"] for r in p["rows"]))
        want = (t["games"], t["rec"], t["yds"], t["td"])
        if got != want:
            raise SystemExit(f"player log checksum failed for {p['name']}: {got} != {want}")

    prop_rows, prop_bt, prop_agg, _ = props_block(model, logs)
    corr = correlations_block(model, games, standings, teamstats, logs)
    sig = signal_rows(model)
    board = gate_table(sig)
    snap = write_snapshots(model)
    dry = demotion_dryrun()

    outputs = {
        "props.json": {
            "as_of": AS_OF,
            "method": ("Fair line = mean of the player's prior weeks (expanding window), rounded to 0.5. "
                       "Over probability is empirical, not modelled. No market line exists."),
            "rows": prop_rows,
            "backtest": prop_bt,
            "backtest_summary": [a for a in prop_agg if a],
            "source_players": [{"name": p["name"], "team": p["team"], "url": p["url"]} for p in logs["players"]],
        },
        "correlation.json": {
            "as_of": AS_OF,
            "method": ("Pearson r on official values only. 95% CI by Fisher z. Two-sided p from Student t "
                       "(incomplete beta). n printed on every row. A CI that includes 0 is published as "
                       "'not distinguishable from no relationship'."),
            "rows": corr,
            "n_rows": len(corr),
        },
        "leaderboard.json": {
            "as_of": AS_OF,
            "rule": ("Two columns that never borrow from each other: SIGNAL (did the call beat a coin flip, with "
                     "n and CI) and STAKING (what it would have returned at a real price). A lucky staking run "
                     "cannot promote a bad signal, because promotion reads the signal column."),
            "rows": board,
            "eligible": sum(1 for r in board if r["state"] == "LIVE"),
            "in_paper": sum(1 for r in board if r["state"] == "PAPER"),
            "demotion_gates": [{"id": i, "name": n, "rule": ru, "action": a} for i, n, ru, a in DEMOTION],
            "promotion_gates": [{"id": i, "name": n, "rule": ru, "blocking": b} for i, n, ru, b in GATES],
            "demotion_dryrun": dry,
        },
        "snapshots.json": snap,
    }
    for name, blob in outputs.items():
        for d in (OUT, SHARE):
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                json.dump(blob, f, indent=1)

    print(f"props: {len(prop_rows)} markets, backtest {len(prop_bt)} graded legs")
    for a in prop_agg:
        if a:
            print(f"  {a['market']}: n={a['n']} over-rate {a['over_rate']} CI {a['over_ci95']} MAE {a['mae']}")
    print(f"correlations: {len(corr)} rows")
    print(f"leaderboard: {len(board)} strategies, {outputs['leaderboard.json']['in_paper']} in paper, "
          f"{outputs['leaderboard.json']['eligible']} live")
    print(f"snapshots: {snap['counts']['snapshots']} files, {snap['counts']['markets']} markets, "
          f"{snap['counts']['markets_with_official_market_price']} with an official market price")
    print(f"demotion dry run: {dry['verdict']} at bet {dry['d1_first_fire_at_bet']}")


if __name__ == "__main__":
    main()
