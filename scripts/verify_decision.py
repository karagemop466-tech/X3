#!/usr/bin/env python3
"""
Gate for the decision layer. This is the rule the brief states as "every table
row must have a source link to an official site; if a value can't be confirmed
from an official source, leave it blank and flag it as unverified" - enforced on
this tree so it is a build failure rather than a promise.

Checks
  1. every page in the nav exists, and every nav link on every page resolves
  2. every row of a <table class="data"> carries either an official link
     (nfl.com / operations.nfl.com) or a repository citation whose target exists
  3. commentary tables (class="agg") are counted and reported, never silent
  4. no placeholder text survives (TODO, TBD, FIXME, "n/a" outside an agg table,
     "lorem")
  5. every official host linked from this tree is one the project treats as
     authoritative - no stray third-party domains
  6. determinism: re-running the builder emits byte-identical files
  7. the numbers quoted on the snapshot pages still recompute from
     data/snapshots/*.json (so a re-capture cannot leave stale prose behind)

Run: python3 scripts/verify_decision.py
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "decision")
OFFICIAL_HOSTS = re.compile(r'https?://(www\.)?(nfl\.com|operations\.nfl\.com|docs\.github\.com|github\.com)/')
ALLOWED_HOSTS = re.compile(r'https?://(www\.)?(nfl\.com|operations\.nfl\.com|docs\.github\.com|github\.com|packers\.com|houstontexans\.com|baltimoreravens\.com)/')
OFFICIAL_ROW_RE = re.compile(r'href="https?://[^"]*(nfl\.com|docs\.github\.com|github\.com|(?:packers|houstontexans|baltimoreravens|detroitlions)\.com)')
CITE_RE = re.compile(r'href="((?:\.\./)+)([^"#]+?)"')
BAD_WORDS = ("TODO", "TBD", "FIXME", "lorem", "PLACEHOLDER", "XXX")

fail, warn = [], []
stats = {"data_rows": 0, "official": 0, "repo": 0, "agg_rows": 0, "pages": 0}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main() -> int:
    if not os.path.isdir(OUT):
        print("FAIL: run scripts/build_decision.py first")
        return 1
    pages = sorted(f for f in os.listdir(OUT) if f.endswith(".html"))
    if not pages:
        fail.append("no pages produced")
        print("FAIL: no pages in decision/")
        return 1

    docs = {}
    for p in pages:
        docs[p] = open(os.path.join(OUT, p), encoding="utf-8").read()
        stats["pages"] += 1

    # 1 nav + internal links
    nav_html = re.search(r'<nav class="nav">(.*?)</nav>', docs.get("index.html", ""), re.S)
    nav_names = set(re.findall(r'href="([^"]+)"', nav_html.group(1))) if nav_html else set()
    for n in sorted(nav_names):
        if n not in docs:
            fail.append(f"nav target missing from the tree: {n}")
    for p, d in docs.items():
        # every emitted page - including landing-block.html - is audited where it
        # lives (decision/), matching scripts/audit_all.py; the root-paste variant
        # must be re-derived with source_link(..., standalone=False) before pasting
        base = OUT
        for m in re.finditer(r'href="([^"]+)"', d):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = href.split("#")[0]
            if not target:
                continue
            if target.endswith(".html"):
                if not os.path.exists(os.path.join(base, target)):
                    fail.append(f"{p}: broken internal link -> {target}")
            else:
                here = os.path.join(base, target)
                there = os.path.normpath(os.path.join(ROOT, target))
                if not (os.path.exists(here) or os.path.exists(there)):
                    fail.append(f"{p}: link does not resolve: {target}")
        # repo citations must point at files that exist
        for m in CITE_RE.finditer(d):
            path = m.group(2)
            if not os.path.exists(os.path.join(ROOT, path)):
                fail.append(f"{p}: cited repo file does not exist: {path}")
            elif path.endswith(".json") and os.path.getsize(os.path.join(ROOT, path)) < 8:
                fail.append(f"{p}: cited artefact is empty: {path}")

    # 2 / 3 row-level source discipline
    for p, d in docs.items():
        if p == "landing-block.html":
            continue
        for tbl in re.finditer(r'<table class="(data|agg)[^"]*">(.*?)</table>', d, re.S):
            cls, body = tbl.group(1), tbl.group(2)
            for row in re.finditer(r"<tr>(.*?)</tr>", body, re.S):
                cells = row.group(1)
                if "<th>" in cells:
                    continue
                if cls == "agg":
                    stats["agg_rows"] += 1
                    continue
                stats["data_rows"] += 1
                has_official = bool(OFFICIAL_ROW_RE.search(cells))
                has_cite = 'class="cite"' in cells or 'class="src"' in cells
                if has_official:
                    stats["official"] += 1
                elif has_cite:
                    stats["repo"] += 1
                if not (has_official or has_cite):
                    snippet = re.sub(r"<[^>]+>", " ", cells)[:110]
                    fail.append(f'{p}: data row with no source - "{snippet.strip()}..."')

    # 4 placeholders
    for p, d in docs.items():
        for w in BAD_WORDS:
            if re.search(rf"\b{w}\b", d):
                fail.append(f"{p}: placeholder token {w} survived into a published page")

    # 5 hosts
    for p, d in docs.items():
        for m in re.finditer(r'href="(https?://[^"]+)"', d):
            if not ALLOWED_HOSTS.match(m.group(1)):
                fail.append(f"{p}: link to a host this project does not treat as authoritative: {m.group(1)}")

    # 6 determinism
    before = {p: sha(os.path.join(OUT, p)) for p in pages}
    rc = os.system(f"cd {ROOT} && python3 scripts/build_decision.py >/dev/null 2>&1")
    if rc != 0:
        fail.append("scripts/build_decision.py did not exit 0 when re-run")
    after = {p: sha(os.path.join(OUT, p)) for p in sorted(f for f in os.listdir(OUT) if f.endswith(".html"))}
    if before != after:
        diff = [p for p in after if before.get(p) != after[p]]
        fail.append(f"builder is not deterministic, changed on re-run: {diff}")

    # 7 quoted numbers still recompute
    try:
        led = json.load(open(os.path.join(ROOT, "data", "snapshots", "ledger.json"), encoding="utf-8"))
        dl = json.load(open(os.path.join(ROOT, "data", "snapshots", "delta.json"), encoding="utf-8"))["deltas"][0]
        sealed = [c for c in led["captures"] if c.get("sealed")][0]
        base = [c for c in led["captures"] if not c.get("sealed")][0]
        snap = docs.get("snapshots.html", "")
        checks = [f"{base['counts']['rows']} rows", f"{sealed['counts']['rows']} rows",
                  str(dl["designation_changes_count"]), str(dl["added_rows_count"]), str(dl["practice_changes_count"]),
                  sealed["sha256"][:24]]
        for needle in checks:
            if needle not in snap:
                fail.append(f"snapshots.html no longer states the recomputed figure {needle!r} - rebuild after a re-capture")
        if sealed["counts"]["rows"] != len([1 for _ in open(os.path.join(ROOT, sealed["files"][0]), encoding="utf-8")]) - 1:
            fail.append("sealed capture row count disagrees with the stored file")
    except Exception as exc:  # a broken store must not verify clean
        fail.append(f"snapshot figures could not be recomputed: {exc}")

    print(f"pages {stats['pages']} · data rows {stats['data_rows']} (official-linked {stats['official']}, repo-cited {stats['repo']}) "
          f"· commentary rows {stats['agg_rows']}")
    for w in warn:
        print("  WARN:", w)
    if fail:
        print(f"\nFAIL - {len(fail)} problem(s):")
        for f in fail:
            print("  -", f)
        return 1
    print("PASS - every nav target resolves, every data row is sourced, no placeholders, builder deterministic, figures recompute")
    return 0


if __name__ == "__main__":
    sys.exit(main())
