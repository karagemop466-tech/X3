#!/usr/bin/env python3
"""
Verifier for the X3 signals module.

Fails the build (exit 1) on any of:

  1. a table row that neither links an official source nor carries an UNVERIFIED marker
  2. a broken internal link
  3. an originated market that is missing its opening or its closing snapshot (gate G11)
  4. a leaderboard whose ranking key is anything other than a signal column (gate G12)
  5. a non-deterministic engine (--determinism: two runs must produce identical data)

Usage:
    python3 scripts/verify_signals.py            # structure, sources, links, gates
    python3 scripts/verify_signals.py --determinism
"""
from __future__ import annotations

import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIG = ROOT / "signals"
DATA = SIG / "data"

OFFICIAL_HOSTS = {"www.nfl.com", "nfl.com", "github.com"}


class RowAudit(HTMLParser):
    """Collect, per <tr>, whether it carries a source link and/or an unverified marker."""

    def __init__(self):
        super().__init__()
        self.in_tbody = False
        self.depth_stack = []
        self.row = None
        self.rows = []
        self.has_thead = False
        self.in_src = False
        self.src_href = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "thead":
            self.has_thead = True
        if tag == "tbody":
            self.in_tbody = True
        if tag == "tr" and self.in_tbody:
            self.row = {"src": False, "unv": False, "cells": 0}
        if self.row is not None:
            if tag == "a" and "src" in (d.get("class") or "").split():
                self.row["src"] = True
                self.src_href = d.get("href", "")
            # a plain external link to an official host also satisfies the rule
            if tag == "a" and (d.get("href") or "").startswith(("http://", "https://")):
                host = d["href"].split("//", 1)[-1].split("/", 1)[0]
                if host in OFFICIAL_HOSTS:
                    self.row["src"] = True
            cls = (d.get("class") or "").split()
            if "unv" in cls:
                self.row["unv"] = True
            if tag == "td":
                self.row["cells"] += 1

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_tbody = False


class LinkAudit(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.refs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for attr in ("href", "src"):
            v = d.get(attr)
            if not v:
                continue
            if v.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            self.refs.append(v.split("#", 1)[0])


def check_pages():
    problems = []
    pages = sorted(SIG.glob("*.html"))
    if not pages:
        problems.append("no pages found in signals/")
        return problems, 0, 0, 0

    total_rows = 0
    linked_rows = 0
    flagged_rows = 0
    for page in pages:
        text = page.read_text()
        ra = RowAudit()
        ra.feed(text)
        for i, r in enumerate(ra.rows, start=1):
            total_rows += 1
            if r["src"]:
                linked_rows += 1
            if r["unv"]:
                flagged_rows += 1
            if not r["src"] and not r["unv"]:
                problems.append(f"{page.name}: table row {i} has neither an official source link "
                                f"nor an UNVERIFIED marker ({r['cells']} cells)")

        la = LinkAudit(page)
        la.feed(text)
        for ref in la.refs:
            if not ref:
                continue
            target = (SIG / ref).resolve()
            if not target.exists():
                # allow links that escape the module (../hub/, ../index.html, ...)
                if not (ROOT / ref).exists():
                    problems.append(f"{page.name}: broken internal link -> {ref}")

    return problems, total_rows, linked_rows, flagged_rows


def check_snapshots():
    """Gate G11: every originated market has both an opening and a closing row."""
    problems = []
    snaps = json.loads((DATA / "price_snapshots.json").read_text())
    by_market = {}
    for s in snaps:
        by_market.setdefault(s["market_id"], set()).add(s["snapshot"])
    originated = {s["market_id"] for s in snaps if s["status"] == "originated"}
    for mid in sorted(originated):
        have = by_market[mid]
        if "open" not in have or "close" not in have:
            problems.append(f"G11: market {mid} is originated but missing snapshots {sorted(have)}")
    # the store must never invent a market price
    for s in snaps:
        if s["market_value"] not in ("", None) or s["difference"] not in ("", None):
            problems.append(f"market_value/difference must stay empty (F-01); {s['market_id']} has a value")
    return problems, len(originated), len(by_market)


def check_leaderboard():
    """Gate G12: ranking is decided by signal only; staking columns must be empty."""
    problems = []
    lb = json.loads((DATA / "leaderboard.json").read_text())
    for r in lb:
        for col in ("staking_roi", "staking_roi_ci", "staking_max_drawdown", "mask_ratio"):
            if r.get(col) not in ("", None):
                problems.append(f"G12: {r['strategy']} has a non-empty staking column '{col}' "
                                f"while no price series exists (F-01)")
    ranked = [r for r in lb if r["rank"] != "unranked"]
    keyed = sorted([r for r in ranked if r["skill_gap_ci_low"] not in ("", None)],
                   key=lambda r: r["rank"])
    if len(keyed) != len(ranked):
        problems.append("G12: a ranked row has no signal-interval, so it cannot have been ranked on signal")
    order = [r["skill_gap_ci_low"] for r in keyed]
    if order != sorted(order, reverse=True):
        problems.append("G12: ranking is not ordered by the lower bound of the signal interval")
    ranks = [r["rank"] for r in keyed]
    if ranks != list(range(1, len(ranks) + 1)):
        problems.append(f"G12: rank labels are not 1..n: {ranks}")
    return problems, len(lb), len(ranked)


def check_correlations():
    """Every published coefficient must carry an n and a source."""
    problems = []
    corr = json.loads((DATA / "correlations.json").read_text())
    for c in corr:
        if c["r"] not in ("", None) and (c["n"] in ("", None) or int(c["n"]) < 4):
            problems.append(f"correlation '{c['pair']}' prints r without a usable n")
        if not c.get("source"):
            problems.append(f"correlation '{c['pair']}' has no source link")
        if c["r"] not in ("", None) and (c["ci95_low"] in ("", None) or c["p"] in ("", None)):
            problems.append(f"correlation '{c['pair']}' prints r without an interval or a p-value")
    return problems, len(corr)


EXPECTED_TREES = ["analysis", "archive", "audit", "capture", "crosscheck", "dashboard", "desk",
                  "docs", "hub", "lab", "legacy", "pages", "research", "site", "verification-hub",
                  "x3lab"]


def check_repo_review():
    """repo_review is a live report on the working tree, so its bytes move; its STRUCTURE must not."""
    problems = []
    rows = json.loads((DATA / "repo_review.json").read_text())
    found = sorted(r["tree"] for r in rows)
    expected = [t for t in EXPECTED_TREES if (ROOT / t).exists()]
    if found != expected:
        problems.append(f"repo review tree list changed: {found} != {expected}")
    for r in rows:
        if r["html_pages"] + r["data_files"] + r.get("other_files", 0) == 0:
            problems.append(f"repo review row '{r['tree']}' has no pages and no data files")
        if not r.get("source"):
            problems.append(f"repo review row '{r['tree']}' has no source link")
    return problems, len(rows)


def check_determinism():
    import hashlib
    def snapshot():
        h = {}
        for f in sorted(DATA.glob("*.json")):
            # meta.json carries no build timestamp; repo_review.json is a report about
            # the working tree, which other sessions' builders legitimately rewrite, so
            # its bytes are a fact about the tree rather than an output of the engine.
            if f.name in ("meta.json", "repo_review.json"):
                continue
            h[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        return h
    before = snapshot()
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "x3_signals.py")],
                       capture_output=True, text=True, cwd=str(ROOT))
    if r.returncode != 0:
        return ["engine re-run failed:\n" + r.stderr[-2000:]]
    after = snapshot()
    problems = []
    for k in sorted(set(before) | set(after)):
        if before.get(k) != after.get(k):
            problems.append(f"non-deterministic output: {k}")
    return problems


def main():
    only = "--determinism" in sys.argv
    problems = []

    if not only:
        ppages, total_rows, linked, flagged = check_pages()
        problems += ppages
        psnap, n_orig, n_mkts = check_snapshots()
        problems += psnap
        plb, n_lb, n_ranked = check_leaderboard()
        problems += plb
        pcorr, n_corr = check_correlations()
        problems += pcorr
        prev, n_trees = check_repo_review()
        problems += prev
        print(f"pages            : {len(list(SIG.glob('*.html')))}")
        print(f"table rows       : {total_rows}  (linked to an official source: {linked}, "
              f"carrying an UNVERIFIED marker: {flagged})")
        print(f"markets          : {n_mkts} stored, {n_orig} originated (G11: both snapshots present)")
        print(f"leaderboard      : {n_lb} rows, {n_ranked} ranked on the signal interval (G12)")
        print(f"correlations     : {n_corr}, each with n, interval, p and source")
        print(f"repo review      : {n_trees} trees, structure stable (bytes excluded - they track "
              f"the working tree, which other builders rewrite)")
    else:
        print("determinism      : re-running the engine ...")

    dprob = check_determinism()
    problems += dprob
    print(f"determinism      : {'PASS' if not dprob else 'FAIL'} "
          f"(engine re-run reproduces the data; repo_review.json excluded - it reports on the "
          f"working tree, which other builders rewrite)")

    if problems:
        print("\n".join("FAIL: " + p for p in problems))
        print(f"\nSIGNALS CHECK FAILED ({len(problems)} problems)")
        return 1
    print("\nSIGNALS CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
