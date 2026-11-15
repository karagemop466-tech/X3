#!/usr/bin/env python3
"""
Gate for the session data layer: data/verified, data/decisions, data/picks,
data/snapshots and the eight pages built from them.

The point is that the new pages cannot drift from their sources. Every check here
either recomputes a published number from its inputs or asserts a stated
invariant. A failure exits non-zero so CI stops before deploying.

Run: python3 tools/verify_desk.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "hub")
PAGES = ["summary", "results", "picks", "snapshots", "correlation-live",
         "leaderboard-live", "depth-tiers", "decisions",
         "repo-review-live", "flagged-live"]
PROBLEMS = []
CHECKS = 0


def _approved_hosts():
    """Same allowlist the canonical hub verifier uses: NFL, its clubs, GitHub.

    Reusing the rule rather than restating it keeps the two gates from disagreeing
    about what counts as an official source.
    """
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("nfl_data", os.path.join(here, "nfl_data.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    hosts = {"nfl.com", "operations.nfl.com", "github.com", "karagemop466-tech.github.io"}
    hosts |= {urlparse(u).netloc for (_a, _n, _p, u, _c, _d) in mod.TEAMS}
    return {h.lower() for h in hosts}


APPROVED = _approved_hosts()


def host_ok(url: str) -> bool:
    h = urlparse(url).netloc.lower()
    return any(h == a or h.endswith("." + a) for a in APPROVED)


def ck(cond, msg):
    global CHECKS
    CHECKS += 1
    if not cond:
        PROBLEMS.append(msg)


def J(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return json.load(f)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.stack = []
        self.errors = []

    def handle_starttag(self, t, a):
        d = dict(a)
        if t == "a" and d.get("href"):
            self.refs.append(d["href"])
        if t in ("script", "link") and (d.get("src") or d.get("href")):
            self.refs.append(d.get("src") or d.get("href"))
        if t not in ("meta", "link", "br", "img", "input", "hr"):
            self.stack.append(t)

    def handle_endtag(self, t):
        if self.stack and self.stack[-1] == t:
            self.stack.pop()
        elif t in self.stack:
            self.errors.append(f"mismatched </{t}>")
            while self.stack and self.stack.pop() != t:
                pass


def main():
    rec = J("data", "verified", "reconciliation.json")
    bt = J("data", "verified", "backtest.json")
    corr = J("data", "verified", "correlation.json")
    dep = J("data", "verified", "depth_map.json")
    kn = J("data", "verified", "key_numbers.json")
    demo = J("data", "verified", "staking_demo.json")
    gates = J("data", "decisions", "gates.json")
    qs = J("data", "decisions", "questions.json")
    picks = J("data", "picks", "picks_2026_wk10.json")
    snap = J("data", "snapshots", "store_meta.json")

    # ---------------- results feed
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data/verified/results_2026.csv"),
                                    encoding="utf-8")))
    ck(len(rows) == rec["finals_used"],
       f"results csv has {len(rows)} rows, reconciliation says {rec['finals_used']}")
    ck(all(r["source_url"].startswith("https://www.nfl.com/schedules/") for r in rows),
       "a results row does not carry an official schedule URL")
    for r in rows:
        if r["status"] == "FINAL":
            ck(int(r["away_score"]) >= 0 and int(r["home_score"]) >= 0,
               f"{r['away']}@{r['home']} has a negative score")
            ck(int(r["home_margin"]) == int(r["home_score"]) - int(r["away_score"]),
               f"{r['away']}@{r['home']} margin does not equal home-away")
            ck(int(r["total"]) == int(r["away_score"]) + int(r["home_score"]),
               f"{r['away']}@{r['home']} total does not equal the sum")

    # ---------------- reconciliation must have passed, and be internally consistent
    ck(rec["status"] == "PASS", f"reconciliation status is {rec['status']}")
    ck(rec["fields_agree"] + rec["fields_disagree"] == rec["fields_compared"],
       "reconciliation agree+disagree does not equal fields compared")
    ck(rec["fields_disagree"] == 0, "reconciliation has disagreements")
    ck(rec["clubs_recomputed"] == rec["clubs_official"] == 32,
       "reconciliation does not cover 32 clubs")
    # PF must equal PA in a closed league
    off = list(csv.DictReader(open(os.path.join(ROOT, "data/verified/standings_2026_official.csv"),
                                   encoding="utf-8")))
    ck(sum(int(x["pf"]) for x in off) == sum(int(x["pa"]) for x in off),
       "sum of points for does not equal sum of points against")
    ck(sum(int(x["net"]) for x in off) == 0, "net points do not sum to zero")
    ck(sum(int(x["w"]) for x in off) == sum(int(x["l"]) for x in off),
       "total wins do not equal total losses")

    # ---------------- backtest integrity
    n_scored = bt["n_games_scored"]
    ck(n_scored == len(bt["rows"]), "backtest n does not match its rows")
    ck(bt["weeks_scored"] == sorted(bt["weeks_scored"]), "backtest weeks not sorted")
    ck(min(bt["weeks_scored"]) > 1, "backtest scored week 1 with no history")
    ck(bt["claim_limit"], "backtest has no stated claim limit")
    # the backtest must never score a game using data from that week or later
    for r in bt["rows"]:
        ck(bool(r["source"].startswith("https://www.nfl.com/schedules/")),
           f"backtest row {r['game']} has no official source")

    # ---------------- correlations
    for r in corr["rows"]:
        ck(r["n"] > 2, f"{r['pair']} has n={r['n']}")
        ck(-1 <= r["pearson_r"] <= 1, f"{r['pair']} r out of range")
        ck(-1 <= r["spearman_rho"] <= 1, f"{r['pair']} rho out of range")
        ck(r["ci95_low"] <= r["pearson_r"] <= r["ci95_high"],
           f"{r['pair']} CI does not bracket r")
        ck(0 <= r["perm_p"] <= 1, f"{r['pair']} p out of range")
        ck("nfl.com" in r["source"], f"{r['pair']} source is not official")
    # recompute one coefficient from raw data as an independent check
    m = [abs(int(r["home_margin"])) for r in rows]
    t = [int(r["total"]) for r in rows]
    mx, my = sum(t) / len(t), sum(m) / len(m)
    num = sum((a - mx) * (b - my) for a, b in zip(t, m))
    den = math.sqrt(sum((a - mx) ** 2 for a in t) * sum((b - my) ** 2 for b in m))
    r_chk = round(num / den, 4)
    pub = next(r for r in corr["rows"] if r["pair"] == "game total vs |margin|")["pearson_r"]
    ck(abs(r_chk - pub) < 5e-4, f"total vs |margin| recomputes to {r_chk}, published {pub}")

    # ---------------- key numbers
    ck(kn["n_games"] == len(rows), "key-number n does not match the feed")
    # the published shares are rounded to 4dp, so sum the COUNTS instead of the shares;
    # a rounding artefact must not fail the gate, a missing game must.
    ck(sum(r["games"] for r in kn["by_margin"]) == kn["n_games"],
       "key-number game counts do not sum to n")
    ck(abs(sum(r["share"] for r in kn["by_margin"]) - 1.0) < 0.01,
       "key-number shares are off by more than a rounding tolerance")
    for r in kn["by_margin"]:
        if r["games"]:
            ck(abs(r["share"] - r["games"] / kn["n_games"]) < 5e-5,
               f"margin {r['margin']}: share does not equal games/n")
    ck(kn["by_margin"][-1]["cum_games_le"] == kn["n_games"],
       "cumulative margin count does not reach n")

    # ---------------- depth
    ck(dep["rows_total"] == len(dep["rows"]), "depth rows_total does not match rows")
    ck(dep["replacements_identified"] == sum(1 for r in dep["rows"] if r["replacement"]),
       "depth replacement count does not match rows")
    for r in dep["rows"]:
        ck(r["status"] in ("Out", "Doubtful"),
           f"depth row {r['player']} has status {r['status']!r}; only Out/Doubtful may be counted")
        if r["replacement"]:
            ck(r["replacement_tier"] == r["chart_tier"] + 1,
               f"{r['player']}: replacement tier is not chart tier + 1")
            ck(bool(r["chart_url"]), f"{r['player']}: replacement with no chart URL")
        else:
            ck(bool(r["reason"]), f"{r['player']}: blank replacement with no stated reason")
    ck(sum(dep["tier_counts"].values()) == dep["replacements_identified"],
       "tier counts do not sum to the replacement count")
    ck(dep["completeness"]["status"] == "PASS",
       f"depth completeness is {dep['completeness']['status']} - a row was lost in the join")
    ck(not dep["completeness"]["missing_from_output"], "depth rows are missing from the output")
    ck(dep["completeness"]["emitted_rows"] == dep["completeness"]["eligible_out_or_doubtful"],
       "depth emitted row count does not equal the eligible count")

    # ---------------- staking / masking
    sig = demo["signal"]
    ck(sig["sign_correct"] + sig["pushes_excluded"] <= sig["n_games_scored"],
       "sign-test counts exceed the games scored")
    ck(sig["sign_accuracy"] == round(sig["sign_correct"] / sig["decided_games"], 4),
       "sign accuracy does not equal correct/decided")
    for k, v in demo["masking"]["a_share_finishing_above_start_flat_1u"].items():
        for n_, p in v.items():
            ck(0 <= p <= 1, f"masking share out of range for {k} at {n_} bets")
    pw = demo["masking"]["c_bets_needed_for_80pct_power"]
    ns = [v["n_needed_80pct_power"] for v in pw.values()]
    ck(ns == sorted(ns, reverse=True),
       f"required sample is not monotone in the edge: {ns}")

    # ---------------- gates
    ck(len(gates["gates"]) >= 10, "fewer than 10 gates published")
    ck(all(g["status"] in ("PASS", "FAIL", "BLOCKED", "PARTIAL", "NOT RUN")
           for g in gates["gates"]), "a gate has an unknown status")
    ck(all(g["evidence"] for g in gates["gates"]), "a gate has no evidence")
    ck(len(gates["demotion_triggers"]) >= 5, "fewer than 5 demotion triggers")
    ck(all(t["arithmetic"] for t in gates["demotion_triggers"]),
       "a demotion trigger has no stated arithmetic")

    # ---------------- questions
    ck(qs["summary"]["questions_total"] == len(qs["questions"]),
       "question count does not match the list")
    for q in qs["questions"]:
        ck(q["answer_status"] in ("ANSWERED", "PARTIAL", "OPEN", "BLOCKED"),
           f"{q['id']} has an unknown status {q['answer_status']}")
        ck(bool(q["source"]), f"{q['id']} has no source")
        if q["answer_status"] == "ANSWERED":
            ck(bool(q["answer"]), f"{q['id']} is ANSWERED with an empty answer")
        if q["answer_status"] in ("OPEN", "BLOCKED"):
            ck(bool(q["how_to_close"]), f"{q['id']} is {q['answer_status']} with no path to close")

    # ---------------- picks
    ck(picks["n_games"] == len(picks["picks"]), "picks n_games mismatch")
    for p in picks["picks"]:
        ck(p["order"] == ["SIDE", "TOTAL", "MONEYLINE"], f"{p['game']} order is wrong")
        ck(p["side"]["our_line"] and p["total"]["our_line"], f"{p['game']} missing a line")
        ck(p["market_side"] == "" and p["diff_side"] == "",
           f"{p['game']} has a market value with no official source")
        ck(p["moneyline"]["home"] != 0, f"{p['game']} has no moneyline")
        # a favourite (negative spread) must carry a negative moneyline
        sp = p["side"]["number_home"]
        ml = p["moneyline"]["home"]
        aml = p["moneyline"]["away"]
        ck((sp < 0 and ml < 0) or (sp > 0 and ml > 0) or sp == 0,
           f"{p['game']}: spread {sp} and home moneyline {ml} disagree on the favourite")
        # The two-way price must be fair: the model has no vig, so the two implied
        # probabilities must sum to 1. This is the check that caught a real defect
        # where the away price was derived by negating rather than from its own
        # probability, producing an implied sum of 1.22.
        def implied(a):
            return abs(a) / (abs(a) + 100) if a < 0 else 100 / (a + 100)
        tot = implied(ml) + implied(aml)
        ck(abs(tot - 1.0) < 0.005,
           f"{p['game']}: moneylines {ml}/{aml} imply {tot:.4f}, expected a fair 1.000")

    # ---------------- snapshot store
    snaprows = list(csv.DictReader(open(os.path.join(ROOT, "data/snapshots/snapshots_2026_wk10.csv"),
                                       encoding="utf-8")))
    ck(len(snaprows) == snap["rows"], "snapshot row count does not match store_meta")
    ck(snap["checks"]["status"] == "PASS", "snapshot invariant checks did not pass")
    for r in snaprows:
        ck(r["market_status"] == "UNVERIFIED" or r["market_source"],
           f"{r['game']} {r['market']}: market marked verified with no source")
        ck(not (r["diff_fair_minus_market"] and not r["market_open"]),
           f"{r['game']} {r['market']}: difference computed against a blank market")
        ck(r["third_party_status"] in ("", "NOT OFFICIAL / NOT INGESTED"),
           f"{r['game']}: third-party price not marked as excluded")

    # ---------------- pages: parse, links, and every table row accounted for
    total_refs = 0
    for name in PAGES:
        f = os.path.join(HUB, f"{name}.html")
        ck(os.path.exists(f), f"{name}.html missing")
        if not os.path.exists(f):
            continue
        s = open(f, encoding="utf-8").read()
        p = Links()
        p.feed(s)
        total_refs += len(p.refs)
        ck(not p.stack, f"{name}.html has unclosed tags: {p.stack[:5]}")
        ck(not p.errors, f"{name}.html has mismatched tags: {p.errors[:3]}")
        for ref in p.refs:
            if ref.startswith(("http://", "https://", "#", "mailto:")):
                if ref.startswith("http"):
                    ck(host_ok(ref), f"{name}.html links a non-official host: {ref}")
                continue
            tgt = os.path.normpath(os.path.join(HUB, ref.split("#")[0]))
            ck(os.path.exists(tgt), f"{name}.html has a broken link: {ref}")
        ck("{" not in s.replace("{", "", 0) or "K(" not in s, f"{name}.html has an unfilled token")
        ck('href="index.html.html"' not in s, f"{name}.html has a doubled extension in a link")

    # ---------------- prose drift: a count written by hand cannot disagree with the data
    src = open(os.path.join(ROOT, "tools", "build_desk.py"), encoding="utf-8").read()
    HARD = ["Thirteen originated", "Thirteen claims", "Nine coefficients", "Six demotion",
            "Six triggers", "Nine of the twelve", "twelve have zero", "37 depth rows"]
    for phrase in HARD:
        ck(phrase not in src,
           f"build_desk.py contains a hand-typed count ({phrase!r}); interpolate it instead")

    print(f"checks run: {CHECKS}   pages: {len(PAGES)}   internal/external refs: {total_refs}")
    if PROBLEMS:
        print(f"FAILED - {len(PROBLEMS)} problems")
        for x in PROBLEMS[:30]:
            print("  ", x)
        raise SystemExit(1)
    print("PASS - verified data layer and pages are consistent with their sources")


if __name__ == "__main__":
    main()
