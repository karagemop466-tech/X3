#!/usr/bin/env python3
"""Gate for the depth-chart register (session arena/784043ed-x3). Exit 1 on any failure.

Independent re-checks (they do not reuse the parser in depth_build.py):
  * every source file's SHA-256 matches the value recorded in depth_register.csv and summary.json
  * the live (2026-11-19) cell count is recounted from the raw markdown with a plain split
  * the jersey-number count is recounted from the raw markdown
  * every register row carries an https source URL and a 64-hex SHA-256
  * every rendered table body row carries a source link
  * every internal link on depth/*.html resolves, and the landing page links to depth/index.html
  * the Houston chart contributes zero rows (image only)
"""
import csv
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


reg = list(csv.DictReader(open(P("data", "depth", "depth_register.csv"), encoding="utf-8")))
summary = json.load(open(P("data", "depth", "summary.json"), encoding="utf-8"))
checks = json.load(open(P("data", "depth", "cross_checks.json"), encoding="utf-8"))["checks"]

# 1. registry shape
check(len(reg) == summary["register_rows"], "register row count != summary")
check(all(r["source_url"].startswith("https://") for r in reg), "a register row lacks an https source URL")
check(all(re.fullmatch(r"[0-9a-f]{64}", r["source_sha256"]) for r in reg), "a register row lacks a 64-hex SHA-256")
check(all(r["slot_status"] in ("FILLED", "SHARED", "GAP", "EMPTY") for r in reg), "unknown slot_status")

# 2. clubs by snapshot
cap_clubs = {r["club"] for r in reg if r["snapshot_date"] == "2026-11-14"}
live_clubs = {r["club"] for r in reg if r["snapshot_date"] == "2026-11-19"}
check(len(cap_clubs) == 31, f"captured clubs {len(cap_clubs)} != 31")
check(live_clubs == {"BAL", "GB", "SEA", "WAS"}, f"live clubs {sorted(live_clubs)} != BAL,GB,SEA,WAS")
check("HOU" not in live_clubs, "Houston rows present although the chart is image-only")

# 3. source hashes (capture files and live files)
cap_dir = P("data", "x3", "raw", "club_depth_charts_2026_wk10")
for fn in os.listdir(cap_dir):
    if fn.endswith(".md"):
        club = fn[:-3]
        rows = [r for r in reg if r["snapshot_date"] == "2026-11-14" and r["club"] == club]
        check(bool(rows), f"no register rows for captured club {club}")
        if rows:
            check(rows[0]["source_sha256"] == sha(os.path.join(cap_dir, fn)), f"hash mismatch for capture {club}")
for club, meta in summary["live_club_files"].items():
    path = P(meta["file"])
    check(os.path.exists(path), f"missing live file {meta['file']}")
    check(sha(path) == meta["sha256"], f"live file hash changed for {club}")

# 4. independent recount of live cells and jersey numbers
live_cells = 0
jersey_cells = 0
for club in ("BAL", "GB", "SEA", "WAS"):
    text = open(P("data", "depth", "live_2026-11-19", club + ".md"), encoding="utf-8").read().splitlines()
    n = 0
    for ln in text:
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip()[1:-1].split("|")]
        if cells and cells[0].lower() == "position":
            continue
        players = cells[1:]
        for c in players:
            if c:
                n += 1
                if re.match(r"^\d{1,2} ", c):
                    jersey_cells += 1
    live_cells += n
    reg_club = [r for r in reg if r["snapshot_date"] == "2026-11-19" and r["club"] == club and r["slot_status"] in ("FILLED", "SHARED")]
    check(len(reg_club) == n, f"live filled-cell count {club}: register {len(reg_club)} vs raw {n}")
check(jersey_cells == summary["jersey_numbers_stripped"], f"jersey count raw {jersey_cells} vs summary {summary['jersey_numbers_stripped']}")
check(all(r["jersey_no"] for r in reg if r["flags"] and "JERSEY_NUMBER_STRIPPED" in r["flags"]), "jersey flag without jersey number")
check(not any(re.match(r"^\d{1,2} ", r["player_name"]) for r in reg), "a jersey number leaked into player_name")

# 5. pinned expectations (documented in the page; a change must be explained in COORDINATION.md)
check(summary["multi_rank1_groups"]["2026-11-14"] == 155, "pinned multi-rank-1 count (2026-11-14) changed")
check(summary["multi_rank1_groups"]["2026-11-19"] == 18, "pinned multi-rank-1 count (2026-11-19) changed")
check(summary["conflicts_by_club"]["BAL"] == 6 and summary["conflicts_by_club"]["GB"] == 2
      and summary["conflicts_by_club"]["SEA"] == 2 and summary["conflicts_by_club"]["WAS"] == 27,
      "pinned conflict counts changed")

# 6. cross-checks
allowed = {"CONFIRMED", "CONFIRMED_IN_REPO_NOT_RE_READ", "REPRODUCED_HANDLED", "NOT_REPRODUCED",
           "NOT_REPRODUCED_ON_2026_11_19", "UNVERIFIED_NO_STRUCTURED_SOURCE", "FLAG_FOR_REVIEW",
           "DISCREPANCY_UNRECONCILED", "NOT_CONFIRMED"}
for c in checks:
    check(c["status"] in allowed, f"cross-check {c['id']} has unknown status {c['status']}")
    check("https://" in c["official_source"], f"cross-check {c['id']} lacks an official https source")

# 7. rendered pages
class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.rows = 0
        self.row_links = 0
        self.in_tbody_tr = 0
        self.tr_has_link = False
        self.bad_rows = 0
        self.depth_tr = 0
        self.in_tr = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag == "tr":
            self.in_tr = True
            self.tr_has_link = False
            self.tr_cells = 0
            self.tr_is_header = False
        if tag == "td" and self.in_tr:
            self.tr_cells = getattr(self, "tr_cells", 0) + 1
        if tag == "th" and self.in_tr:
            self.tr_is_header = True
        if tag == "a" and self.in_tr:
            self.tr_has_link = True

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_tr:
            self.in_tr = False
            if not getattr(self, "tr_is_header", False) and getattr(self, "tr_cells", 0) > 0:
                self.rows += 1
                if self.tr_has_link:
                    self.row_links += 1
                else:
                    self.bad_rows += 1


pages = ["index.html", "register.html", "flagged.html"]
for name in pages:
    path = P("depth", name)
    check(os.path.exists(path), f"missing page depth/{name}")
    if not os.path.exists(path):
        continue
    text = open(path, encoding="utf-8").read()
    check(not re.search(r">\s*(None|nan)\s*<", text), f"{name} renders None/nan")
    s = Scan()
    s.feed(text)
    if name == "register.html":
        check(s.rows == len(reg), f"register.html rows {s.rows} != {len(reg)}")
    check(s.bad_rows == 0, f"{name}: {s.bad_rows} table rows without a source link")
    for h in s.hrefs:
        if h.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = h.split("#", 1)[0]
        if not target:
            continue
        full = os.path.normpath(os.path.join(os.path.dirname(path), target))
        check(os.path.exists(full), f"{name}: broken internal link {h}")

landing = open(P("index.html"), encoding="utf-8").read()
check('href="depth/index.html"' in landing, "landing page does not link depth/index.html")

if FAILS:
    print("depth_verify: FAIL")
    for f in FAILS:
        print(" -", f)
    sys.exit(1)
print(f"depth_verify: PASS — {len(reg)} register rows; {len(cap_clubs)} captured clubs; live cells {live_cells}; "
      f"jersey {jersey_cells}; {len(checks)} cross-checks; 3 pages; 0 failures")
