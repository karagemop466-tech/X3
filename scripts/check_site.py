#!/usr/bin/env python3
"""Check docs/: internal links resolve, and each table body row has a source link or an explicit flag."""
import os, re, sys
from html.parser import HTMLParser

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT_DIR, "docs")
errors, ext_links, rows_total, rows_missing = [], set(), 0, 0

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.in_tbody = False; self.row = None; self.rows = []
        self.cur_has = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"): self.links.append(a["href"])
        if tag == "tbody": self.in_tbody = True
        if tag == "tr" and self.in_tbody: self.row = True; self.cur_has = False
        if tag == "a" and self.row and a.get("href"): self.cur_has = True
        if tag == "span" and self.row and "flag" in (a.get("class") or ""): self.cur_has = True
    def handle_endtag(self, tag):
        if tag == "tbody": self.in_tbody = False
        if tag == "tr" and self.row:
            self.rows.append(self.cur_has); self.row = None

for name in sorted(os.listdir(DOCS)):
    if not name.endswith(".html"): continue
    p = P(); p.feed(open(os.path.join(DOCS, name), encoding="utf-8").read())
    for href in p.links:
        if href.startswith("http"): ext_links.add(href); continue
        if href.startswith("#") or href.startswith("mailto:"): continue
        target = href.split("#")[0]
        ok = os.path.exists(os.path.normpath(os.path.join(DOCS, target)))
        if not ok:
            errors.append(f"{name}: broken internal link -> {href}")
    rows_total += len(p.rows); rows_missing += sum(1 for ok in p.rows if not ok)
    print(f"{name:26s} table rows={len(p.rows):4d} rows-without-link-or-flag={sum(1 for ok in p.rows if not ok)}")

print(f"external links referenced: {len(ext_links)}; table rows: {rows_total}; rows without link/flag: {rows_missing}")
for e in errors: print("ERROR", e)
sys.exit(1 if errors else 0)
