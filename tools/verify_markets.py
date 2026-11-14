#!/usr/bin/env python3
"""
X3 / market-layer gate (session arena/f0880a0b-x3).

Fails (exit 1) unless every claim the new pages make is still true of the files behind
them. Each check is a property, not a snapshot, so re-running the engines and rebuilding
cannot silently break one:

  M1  determinism      rebuilding the derived files reproduces them byte for byte
  M2  results feed     the feed reconciles to the official standings with 0 mismatches,
                       and the box-score sample agrees 16/16
  M3  price store      every market we originate has an opening number; a close is either
                       a number or the literal PENDING; no market_* column is ever
                       populated without a source URL
  M4  origination      the order is side -> total -> moneyline, and a moneyline row never
                       carries a handicap
  M5  fair/market/diff three distinct keys per market row; a blank market line implies a
                       blank difference (a difference cannot be computed against nothing)
  M6  leaderboard      signal and staking are separate keys; no strategy is ranked without
                       both; a staking score never exists without a price source
  M7  replacements     every absence row names a replacement + tier, or is UNVERIFIED with
                       a non-empty reason; no row has a tier but no name
  M8  correlation      every computed row has a source URL and n > 0; every blank row has
                       a data_required string
  M9  demotion         the gate has four clauses, each evaluated, and the published verdict
                       matches the clause results
  M10 rows published   every new page exists and every data row carries an official URL or
                       an explicit marker (delegated to verify_hub, reported here)

Run: python3 tools/verify_markets.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "x3")
HUB = os.path.join(ROOT, "hub")
fails: list[str] = []


def J(n):
    with open(os.path.join(D, n), encoding="utf-8") as f:
        return json.load(f)


def check(cond, msg):
    if not cond:
        fails.append(msg)


def main() -> int:
    res = J("results.json")
    mk = J("markets.json")
    dp = J("depth_replacement.json")
    co = J("correlations.json")
    st = J("strategies.json")

    # M1 determinism: re-run the engines and require a byte-identical tree
    before = {n: open(os.path.join(D, n), "rb").read() for n in sorted(os.listdir(D))
              if n.endswith((".json", ".csv"))}
    for script in ("results_feed.py", "markets_engine.py", "correlation_engine.py",
                   "depth_engine.py", "strategies_engine.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", script)],
                           capture_output=True, text=True, cwd=ROOT)
        check(r.returncode == 0, f"M1 {script} exited {r.returncode}: {r.stderr[-300:]}")
    for n, b in before.items():
        path = os.path.join(D, n)
        now = open(path, "rb").read() if os.path.exists(path) else b"<missing>"
        check(now == b, f"M1 {n} is not deterministic: a rebuild changed it")

    # M2 results feed
    rc = res["checks"]["R2_standings_reconciliation"]
    check(rc["mismatches"] == 0, f"M2 standings mismatches = {rc['mismatches']}")
    check(rc["clubs_compared"] == 32, f"M2 clubs compared = {rc['clubs_compared']}, expected 32")
    bs = res["checks"]["R3_box_score_sample"]
    check(bs["agreed"] == bs["checked"] == 16,
          f"M2 box-score sample {bs['agreed']}/{bs['checked']}, expected 16/16")
    check(res["counts"]["finals"] > 0, "M2 no final games in the feed")
    for r in res["rows"]:
        if r["status"] == "FINAL":
            check(r["away_score"] != "" and r["home_score"] != "",
                  f"M2 {r['game_id']} is FINAL without both scores")
            check(r["margin_home"] == r["home_score"] - r["away_score"],
                  f"M2 {r['game_id']} margin is not home minus away")
        check(r["source"].startswith("https://www.nfl.com/"),
              f"M2 {r['game_id']} has no official source URL")

    # M3 price store
    store_rows = []
    for r in mk["live"]:
        store_rows.append(r)
    seen = set()
    for g in [mk["live"][0]] if mk["live"] else []:
        pass
    import csv as _csv
    prow = list(_csv.DictReader(open(os.path.join(D, "price_store.csv"), encoding="utf-8")))
    check(len(prow) > 0, "M3 price store is empty")
    for r in prow:
        seen.add(r["market_id"])
        check(r["open_line"] != "" or r["open_price_decimal"] != "",
              f"M3 {r['market_id']} has neither an opening line nor an opening price")
        check(r["close_status"] in ("RECORDED", "PENDING"),
              f"M3 {r['market_id']} close_status = {r['close_status']!r}")
        if r["close_status"] == "RECORDED":
            check(r["close_line"] != "" or r["close_price_decimal"] != "",
                  f"M3 {r['market_id']} is RECORDED with an empty close")
        if r["close_status"] == "PENDING":
            check(r["close_line"] == "" and r["close_price_decimal"] == "",
                  f"M3 {r['market_id']} is PENDING but carries a close number")
        check(r["source"].startswith("https://www.nfl.com/"),
              f"M3 {r['market_id']} has no official source URL")
        if r["market_close"] or r["market_open"]:
            check(r["market_source"].startswith("https"),
                  f"M3 {r['market_id']} carries a market number with no market source")
    check(len(seen) == len(prow), "M3 duplicate market_id in the store")

    # M4 origination order
    check(mk["origination_order"] == ["side", "total", "moneyline"],
          f"M4 origination order = {mk['origination_order']}")
    for s in store_rows:
        pass
    for r in prow:
        if r["market"] == "moneyline":
            check(r["open_line"] == "" and r["close_line"] == "",
                  f"M4 {r['market_id']} is a moneyline with a handicap")
    for r in mk["live"]:
        check(r["origination_order"] == "1 side, 2 total, 3 moneyline",
              f"M4 {r['game_id']} does not state the order")

    # M5 fair / market / difference
    for r in mk["market_rows"]:
        for k in ("fair_line", "market_line", "difference"):
            check(k in r, f"M5 market row {r['game_id']} missing {k}")
        if r["market_line"] in ("", None):
            check(r["difference"] in ("", None),
                  f"M5 {r['game_id']} has a difference against a blank market line")
            check("UNVERIFIED" in r["market_status"],
                  f"M5 {r['game_id']} blanks the market without a status")
        check(bool(r["source_fair"]), f"M5 {r['game_id']} has no fair-line source")

    # M6 leaderboard: signal and staking are separate
    for s in st["strategies"]:
        for k in ("signal_score", "signal_status", "staking_score", "staking_status"):
            check(k in s, f"M6 {s['id']} missing {k}")
        if s["staking_status"] == "SCORED":
            check(any(x.get("market_source") for x in prow),
                  f"M6 {s['id']} has a staking score but no market price exists")
        if s["rank"] is not None:
            check(s["signal_status"] == "ESTABLISHED" and s["staking_status"] == "SCORED",
                  f"M6 {s['id']} is ranked without both scores")
    check(st["counts"]["staking_scored"] == 0 or any(x.get("market_source") for x in prow),
          "M6 staking scores exist with no price source")

    # M7 replacements
    for r in dp["rows"]:
        if r["state"] == "VERIFIED":
            check(bool(r["replacement"]), f"M7 {r['club']} {r['player']} VERIFIED with no replacement")
            check(isinstance(r["replacement_tier"], int),
                  f"M7 {r['club']} {r['player']} VERIFIED with no tier")
        else:
            check(bool(r["why"]), f"M7 {r['club']} {r['player']} UNVERIFIED with no reason")
            check(not r["replacement"], f"M7 {r['club']} {r['player']} UNVERIFIED but names a man")
        if r["replacement_tier"] != "":
            check(bool(r["replacement"]), f"M7 {r['club']} {r['player']} has a tier but no name")
    tot = dp["counts"]["replacement_named"] + dp["counts"]["replacement_unverified"]
    check(tot == dp["counts"]["absences_out_or_doubtful"],
          f"M7 named + unverified ({tot}) != absences ({dp['counts']['absences_out_or_doubtful']})")

    # M8 correlations
    for r in co["rows"]:
        check(bool(r["source"]) and r["source"].startswith("https://www.nfl.com/"),
              f"M8 computed row {r['x']} vs {r['y']} has no official source")
        check(isinstance(r["n"], int) and r["n"] > 0,
              f"M8 computed row {r['x']} vs {r['y']} has no n")
        check(r["value"] is not None, f"M8 computed row {r['x']} vs {r['y']} has no value")
    for r in co["blank_rows"]:
        check(r["value"] is None, f"M8 blank row {r['x']} vs {r['y']} carries a value")
        check(bool(r["data_required"]), f"M8 blank row {r['x']} vs {r['y']} names no missing input")

    # M9 demotion gate
    dg = st["demotion_gate"]
    check(len(dg["clauses"]) == 4, f"M9 demotion gate has {len(dg['clauses'])} clauses, expected 4")
    for c in dg["clauses"]:
        found = [k for k in dg["results"] if k.startswith(c["id"] + "_")]
        check(bool(found), f"M9 clause {c['id']} is not evaluated")
    firing = [k for k, v in dg["results"].items() if v["fires"]]
    check(sorted(firing) == sorted(dg["firing"]),
          f"M9 published firing list {dg['firing']} != evaluated {firing}")
    if firing:
        check("PAPER" in dg["verdict"], "M9 clauses fire but the verdict is not PAPER")

    # M10 pages + row-source rule via the hub gate
    for p in ("markets.html", "price-store.html", "results.html", "replacements.html",
              "leaderboard.html", "correlation.html", "gates.html", "suggestions.html",
              "questions.html", "requirements.html", "flagged.html", "executive-summary.html"):
        check(os.path.exists(os.path.join(HUB, p)), f"M10 missing page {p}")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "verify_hub.py")],
                       capture_output=True, text=True, cwd=ROOT)
    check(r.returncode == 0, f"M10 hub gate failed: {r.stdout[-400:]}")

    print(f"markets gate: results={res['counts']['finals']} finals, "
          f"store={len(prow)} rows, replacements={dp['counts']['replacement_named']} named, "
          f"correlations={co['counts']['computed']} computed, "
          f"strategies={st['counts']['strategies']}, demotion firing={len(firing)}")
    if fails:
        for f in fails:
            print("FAIL", f)
        return 1
    print("PASS - every market-layer property holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
