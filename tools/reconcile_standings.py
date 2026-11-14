#!/usr/bin/env python3
"""Independent reconciliation of the 2026 results feed to the OFFICIAL league standings.

Inputs:
  data/ledger/results_feed.csv                 (results feed, FINAL games; read-only here)
  data/reconcile/standings_live_2026_wk10.csv  (32 club rows transcribed from
                                                https://www.nfl.com/standings/league/2026/REG,
                                                fetched live 2026-11-14, both chunks read)
Output:
  data/reconcile/standings_check_wk10.csv      one row per club: feed value, official value,
                                                match flag, and the official source URL

For each club the script rebuilds W, L, T, points for, points against, home record and
road record from the feed and compares them with the official standings row. Any mismatch
makes the script exit 1. Nothing is inferred: a club missing from either side is an error.

Club codes: the official standings use AZ; the results feed uses ARI (the only alias).
"""
import csv, pathlib, sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEED = ROOT / "data" / "ledger" / "results_feed.csv"
STAND = ROOT / "data" / "reconcile" / "standings_live_2026_wk10.csv"
OUT = ROOT / "data" / "reconcile" / "standings_check_wk10.csv"
ALIAS = {"ARI": "AZ"}


def main():
    feed = list(csv.DictReader(FEED.open(newline="")))
    finals = [g for g in feed if g["away_score"] and g["home_score"]]
    if len(finals) != len(feed):
        print(f"WARNING: {len(feed) - len(finals)} feed rows have no score and are excluded")
    agg = defaultdict(lambda: dict(w=0, l=0, t=0, pf=0, pa=0, hw=0, hl=0, ht=0, rw=0, rl=0, rt=0))
    for g in finals:
        a, h = int(g["away_score"]), int(g["home_score"])
        away, home = ALIAS.get(g["away"], g["away"]), ALIAS.get(g["home"], g["home"])
        for team, pf, pa, is_home in ((home, h, a, True), (away, a, h, False)):
            d = agg[team]
            d["pf"] += pf
            d["pa"] += pa
            res = "w" if pf > pa else ("l" if pf < pa else "t")
            d[res] += 1
            d[("h" if is_home else "r") + res] += 1
    standings = list(csv.DictReader(STAND.open(newline="")))
    out, bad = [], 0
    for s in standings:
        team = s["team"]
        d = agg.get(team, {})
        feed_vals = {
            "w": d.get("w"), "l": d.get("l"), "t": d.get("t"), "pf": d.get("pf"), "pa": d.get("pa"),
            "home_rec": f"{d.get('hw')}-{d.get('hl')}-{d.get('ht')}" if d else None,
            "road_rec": f"{d.get('rw')}-{d.get('rl')}-{d.get('rt')}" if d else None,
        }
        off_vals = {"w": int(s["w"]), "l": int(s["l"]), "t": int(s["t"]), "pf": int(s["pf"]),
                    "pa": int(s["pa"]), "home_rec": s["home_rec"], "road_rec": s["road_rec"]}
        mism = [k for k in off_vals if str(feed_vals[k]) != str(off_vals[k])]
        bad += bool(mism) or not d
        out.append({
            "team": team,
            "feed_w_l_t": f"{feed_vals['w']}-{feed_vals['l']}-{feed_vals['t']}",
            "official_w_l_t": f"{off_vals['w']}-{off_vals['l']}-{off_vals['t']}",
            "feed_pf_pa": f"{feed_vals['pf']}-{feed_vals['pa']}",
            "official_pf_pa": f"{off_vals['pf']}-{off_vals['pa']}",
            "feed_home_road": f"{feed_vals['home_rec']} / {feed_vals['road_rec']}",
            "official_home_road": f"{off_vals['home_rec']} / {off_vals['road_rec']}",
            "match": "MATCH" if not mism and d else "MISMATCH: " + ", ".join(mism or ["no feed rows"]),
            "source_url": s["source_url"],
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(f"finals in feed: {len(finals)}; clubs compared: {len(standings)}; mismatched clubs: {bad}")
    if len(standings) != 32:
        print("expected 32 clubs")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
