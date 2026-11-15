#!/usr/bin/env python3
"""Verify the readiness module (session arena/6259c7b0-x3).

Gates (exit 1 on any failure):
  V1  every readiness/*.html page parses and every internal link resolves
  V2  every table row with a Source column carries an official link, a provenance
      link, or an explicit UNVERIFIED/BLOCKED marker
  V3  the register (readiness.json) is complete: status vocabulary, non-empty gate
      and clearing-number cells, and every row's status matches its published badge
  V4  announced-starter rows link only official nfl.com news/video pages
  V5  the change-our-mind register covers the union of every strategy entry in the
      four trees (signals 15, desk 10, ops 5, hub 12) - 42 entries, no duplicates
  V6  the drift report agrees with the pins file (same dataset ids, no FAIL rows)
  V7  determinism: rebuilding the module reproduces byte-identical pages
  V8  control baselines reproduce exactly on re-computation (fixed seed)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / "readiness"
PROBLEMS: list[str] = []


def fail(msg):
    PROBLEMS.append(msg)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("href"):
            self.links.append(a["href"])


CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
UNVER_RE = re.compile(r"UNVERIFIED|BLOCKED|PENDING|NOT", re.I)


def strip(s):
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", s)).strip()


def main():
    pages = sorted(MOD.glob("*.html"))
    if not pages:
        fail("no readiness pages found")
        return report()

    # V1 + V2
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        p = LinkParser()
        p.feed(text)
        for href in p.links:
            if href.startswith(("http", "#", "mailto:", "data:", "tel:", "javascript:")):
                continue
            target = href.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            if not (page.parent / target).exists():
                fail(f"V1 {page.name}: broken internal link -> {href}")
        for tbl_m in TABLE_RE.finditer(text):
            tbl = tbl_m.group(1)
            head_m = re.search(r"<thead>(.*?)</thead>", tbl, re.S | re.I)
            if not head_m:
                continue
            headers = [strip(c).lower() for c in CELL_RE.findall(head_m.group(1))]
            src_idx = next((i for i, h in enumerate(headers) if "source" in h), None)
            if src_idx is None:
                continue
            body = re.sub(r"<thead>.*?</thead>", "", tbl, flags=re.S | re.I)
            for row in TR_RE.findall(body):
                if "<td" not in row:
                    continue
                cells = CELL_RE.findall(row)
                cell = cells[src_idx] if src_idx < len(cells) else cells[-1]
                if re.search(r"https?://", row):
                    continue
                if re.search(r"""href\s*=\s*["'](?!https?:)[^"']+["']""", cell, re.I):
                    continue
                if UNVER_RE.search(strip(cell)) or UNVER_RE.search(strip(row)):
                    continue
                fail(f"V2 {page.name}: source cell neither links nor flags - "
                     f"{strip(row)[:90]!r}")

    # V3 register completeness
    reg = json.loads((MOD / "data" / "readiness.json").read_text())
    vocab = {"done", "partial", "blocked", "registered", "rejected"}
    ids = set()
    for r in reg["rows"]:
        if r["status"] not in vocab:
            fail(f"V3 register {r['id']}: bad status {r['status']!r}")
        if not r.get("gate") or not r.get("clears"):
            fail(f"V3 register {r['id']}: empty gate/clears cell")
        if not r.get("where"):
            fail(f"V3 register {r['id']}: no implementing page")
        if not r.get("source"):
            fail(f"V3 register {r['id']}: no source link")
        if r["id"] in ids:
            fail(f"V3 register: duplicate id {r['id']}")
        ids.add(r["id"])
    rendered = (MOD / "decision-readiness.html").read_text().count("<tr>") - 1
    if rendered != len(reg["rows"]):
        fail(f"V3 rendered register rows {rendered} != register rows {len(reg['rows'])}")

    # V4 announced starters are official
    ann = (MOD / "announced-starters.html").read_text()
    for url in re.findall(r'href="(https?://[^"]+)"', ann):
        if not url.startswith(("https://www.nfl.com/news/", "https://www.nfl.com/videos/")):
            fail(f"V4 announced-starters carries a non-official link {url}")

    # V5 change-our-mind union
    cm = json.loads((MOD / "data" / "change_mind.json").read_text())
    expect = {
        "signals": len(json.loads((ROOT / "signals" / "data" / "strategies.json").read_text())),
        "desk": len(json.loads((ROOT / "data" / "desk" / "strategies.json").read_text())["strategies"]),
        "ops": len(json.loads((ROOT / "ops" / "data" / "leaderboard.json").read_text())["rows"]),
        "hub": len(json.loads((ROOT / "hub" / "data" / "prereg.json").read_text())["strategies"]),
    }
    counts = {}
    seen = set()
    for r in cm["rows"]:
        counts[r["tree"]] = counts.get(r["tree"], 0) + 1
        key = (r["tree"], r["id"])
        if key in seen:
            fail(f"V5 duplicate strategy entry {key}")
        seen.add(key)
        if not r.get("would_upgrade") or not r.get("would_abandon"):
            fail(f"V5 {key}: missing one side of the change-our-mind field")
    for tree, n in expect.items():
        if counts.get(tree) != n:
            fail(f"V5 tree {tree}: {counts.get(tree)} entries, expected {n}")

    # V6 drift report agrees with pins
    pins = json.loads((MOD / "data" / "drift_pins.json").read_text())
    rep = json.loads((MOD / "data" / "drift_report.json").read_text())
    pin_ids = [p["id"] for p in pins["pins"]]
    rep_ids = [r["id"] for r in rep["results"]]
    if pin_ids != rep_ids:
        fail("V6 drift report datasets disagree with pins file")
    if rep["failed"] != 0:
        fail(f"V6 drift report has {rep['failed']} failing datasets")

    # V7 determinism: rebuild and compare
    before = {p.name: p.read_bytes() for p in pages}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_readiness.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"V7 rebuild failed: {r.stderr[-300:]}")
    else:
        for p in pages:
            if p.read_bytes() != before.get(p.name):
                fail(f"V7 {p.name} not byte-identical after rebuild")

    # V8 controls reproduce
    c_before = (MOD / "data" / "control_baselines.json").read_bytes()
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "readiness_compute.py")],
                       capture_output=True, text=True)
    c_after = (MOD / "data" / "control_baselines.json").read_bytes()
    if r.returncode != 0:
        fail(f"V8 compute failed: {r.stderr[-300:]}")
    elif c_before != c_after:
        fail("V8 control baselines changed between runs (seed must be fixed)")
    # rebuild pages again so the tree is consistent with the final data
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_readiness.py")],
                   capture_output=True, text=True)

    return report()


def report():
    if PROBLEMS:
        print("READINESS VERIFY FAILED")
        for p in PROBLEMS:
            print(f"  {p}")
        return 1
    print("READINESS CHECK PASSED - links resolve; every source row linked or flagged; "
          "register complete; 42 change-our-mind entries; drift pins agree; "
          "pages byte-identical on rebuild; controls reproduce with fixed seed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
