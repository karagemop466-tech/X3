#!/usr/bin/env python3
"""Row-level verification gate for the ledger module (session arena/a60a2bf7-x3).

Checks, all offline:
  1. Every <tbody> row of every table in ledger/*.html either
       (a) links an approved official host (nfl.com, operations.nfl.com, or a club
           domain that appears in data/ledger/replacement_depth.csv), or
       (b) contains an explicit flag word: UNVERIFIED, DESIGN, DERIVED, IRREGULAR,
           NOT ORIGINATED, COMPUTED.
     Tables carrying class "k-meta" are navigation/summary tables and are exempt; the
     exemption is visible in the markup.
  2. Every CSV row in data/ledger/ that has a source_url / injury_source / url column
     points at an approved host, or the row is flagged in its verification column.
  3. Every relative link and asset in ledger/*.html resolves to a file.
  4. results_feed.csv equals the FINAL rows of data/desk/games.json (count, scores, no
     duplicate ids, margin and total arithmetic).
  5. Rebuilding is byte-identical (determinism).

Exit code 0 = pass, 1 = fail.
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "ledger"
DATA = ROOT / "data" / "ledger"
FLAG_WORDS = ("UNVERIFIED", "DESIGN", "DERIVED", "IRREGULAR", "NOT ORIGINATED", "COMPUTED")
BASE_HOSTS = {"www.nfl.com", "nfl.com", "operations.nfl.com"}


def club_hosts():
    hosts = set()
    p = DATA / "replacement_depth.csv"
    if p.exists():
        with p.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                u = r.get("depth_source", "")
                if u.startswith("https://"):
                    hosts.add(urlparse(u).netloc)
    return hosts


APPROVED = BASE_HOSTS | club_hosts()


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []  # list of dict(cls, rows=[(text, hrefs)])
        self.hrefs_all = []
        self.in_tbody = False
        self.cur_table = None
        self.cur_row = None
        self.cur_text = []
        self.cur_hrefs = []
        self.cur_cells = 0
        self.head_cells = None
        self.in_thead = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.cur_table = {"cls": a.get("class", ""), "rows": [], "head": None, "mismatch": []}
            self.tables.append(self.cur_table)
        elif tag == "thead":
            self.in_thead = True
            self.head_cells = 0
        elif tag == "th" and self.in_thead:
            self.head_cells += 1
        elif tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.cur_row = True
            self.cur_text = []
            self.cur_hrefs = []
            self.cur_cells = 0
        elif tag == "td" and self.cur_row:
            self.cur_cells += 1
        elif tag == "a" and "href" in a:
            self.hrefs_all.append(a["href"])
            if self.cur_row:
                self.cur_hrefs.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "thead":
            self.in_thead = False
            self.cur_table["head"] = self.head_cells
        elif tag == "tbody":
            self.in_tbody = False
        elif tag == "tr" and self.cur_row:
            if self.cur_table["head"] is not None and self.cur_cells != self.cur_table["head"]:
                self.cur_table["mismatch"].append(self.cur_cells)
            self.cur_table["rows"].append((" ".join(self.cur_text), self.cur_hrefs))
            self.cur_row = None

    def handle_data(self, data):
        if self.cur_row:
            self.cur_text.append(data)


def host_ok(url):
    p = urlparse(url)
    return p.scheme == "https" and p.netloc in APPROVED


def check_pages(fails, notes):
    pages = sorted(LEDGER.glob("*.html"))
    if not pages:
        fails.append("no ledger pages found")
        return
    total_rows = exempt = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        tp = TableParser()
        tp.feed(text)
        for t in tp.tables:
            if t["mismatch"]:
                fails.append(f"{page.name}: table column count mismatch (header {t['head']}, row cells {sorted(set(t['mismatch']))})")
            if "k-meta" in t["cls"]:
                exempt += len(t["rows"])
                continue
            for body, hrefs in t["rows"]:
                total_rows += 1
                ok_link = any(host_ok(h) for h in hrefs)
                ok_flag = any(w in body.upper() for w in FLAG_WORDS)
                if not (ok_link or ok_flag):
                    fails.append(f"{page.name}: row without official link or flag: {body[:90]!r}")
        # internal links and assets
        for href in tp.hrefs_all:
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            if href.split("#")[0] and not target.exists():
                fails.append(f"{page.name}: broken relative link {href}")
        for m in re.finditer(r'(?:src|href)="([^"#?]+\.(?:css|js))"', text):
            if not (page.parent / m.group(1)).exists():
                fails.append(f"{page.name}: missing asset {m.group(1)}")
    notes.append(f"pages: {len(pages)}; table rows checked: {total_rows}; k-meta rows exempt: {exempt}")


def check_csvs(fails, notes):
    for path in sorted(DATA.glob("*.csv")):
        with path.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        url_cols = [c for c in ("source_url", "injury_source", "url") if rows and c in rows[0]]
        for i, r in enumerate(rows, 1):
            if not url_cols:
                continue
            urls = [r[c] for c in url_cols if r.get(c)]
            flagged = any(w in (r.get("verification", "") + r.get("result", "")).upper() for w in FLAG_WORDS)
            if not urls and not flagged:
                fails.append(f"{path.name} row {i}: no source URL and not flagged")
            for u in urls:
                if not host_ok(u):
                    fails.append(f"{path.name} row {i}: non-approved source host {u}")
        notes.append(f"{path.name}: {len(rows)} rows")


def check_results(fails, notes):
    games = json.loads((ROOT / "data" / "desk" / "games.json").read_text())["games"]
    finals = [g for g in games if g["status"] == "FINAL"]
    with (DATA / "results_feed.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != len(finals):
        fails.append(f"results_feed rows {len(rows)} != FINAL games {len(finals)}")
    ids = [r["game_id"] for r in rows]
    if len(set(ids)) != len(ids):
        fails.append("results_feed has duplicate game_id")
    src = {(g["away"], g["home"], g["week"]): g for g in finals}
    for r in rows:
        g = src.get((r["away"], r["home"], int(r["week"])))
        if g is None:
            fails.append(f"results row {r['game_id']} not in games.json FINAL set")
            continue
        if int(r["away_score"]) != g["away_score"] or int(r["home_score"]) != g["home_score"]:
            fails.append(f"score mismatch {r['game_id']}")
        if int(r["home_margin"]) != int(r["home_score"]) - int(r["away_score"]):
            fails.append(f"margin arithmetic {r['game_id']}")
        if int(r["total_points"]) != int(r["home_score"]) + int(r["away_score"]):
            fails.append(f"total arithmetic {r['game_id']}")
    notes.append(f"results_feed: {len(rows)} FINAL games reconciled to data/desk/games.json")


def check_determinism(fails, notes):
    def digest():
        h = hashlib.sha256()
        for p in sorted(list(LEDGER.glob("*")) + list(DATA.glob("*.csv"))):
            h.update(p.name.encode())
            h.update(p.read_bytes())
        return h.hexdigest()

    before = digest()
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_ledger.py")], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        fails.append("build_ledger.py failed: " + r.stderr.strip()[-200:])
        return
    after = digest()
    if before != after:
        fails.append("build is not deterministic / committed output differs from a rebuild")
    notes.append("determinism: rebuild byte-identical" if before == after else "determinism: DIFF")


def main():
    fails, notes = [], []
    check_pages(fails, notes)
    check_csvs(fails, notes)
    check_results(fails, notes)
    check_determinism(fails, notes)
    for n in notes:
        print("OK  ", n)
    for f in fails:
        print("FAIL", f)
    print("LEDGER VERIFY", "PASSED" if not fails else f"FAILED ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
