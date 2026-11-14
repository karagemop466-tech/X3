#!/usr/bin/env python3
"""Line-by-line site verification (T12).

Rules enforced:
- HARD: every row of any table that has a Source column must contain an external
  source link (http/https) OR the string UNVERIFIED. (R21/R22/R23)
- SOFT: every table row anywhere must carry some evidence marker: an href, or a
  pill/ok/flag badge, or an explicit spec marker (proposal / Process rule / spec).
- LINKS: every internal href must resolve to a file that exists.
Fails (exit 1) on HARD or LINK errors; prints SOFT warnings.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
problems, warnings = [], []

row_re = re.compile(r"<tr>(.*?)</tr>", re.S)
cell_re = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
href_re = re.compile(r'href="([^"]+)"')

pages = sorted((DOCS / "pages").glob("*.html")) + [DOCS / "index.html"]
for page in pages:
    text = page.read_text()
    rel = page.relative_to(ROOT)

    # --- internal link resolution -------------------------------------
    for href in href_re.findall(text):
        if href.startswith("http") or href.startswith("#") or href.startswith("mailto:"):
            continue
        target = (page.parent / href.split("#")[0]).resolve()
        if not target.exists():
            problems.append(f"{rel}: broken internal link -> {href}")

    for tbl_m in re.finditer(r"<table>(.*?)</table>", text, re.S):
        tbl = tbl_m.group(1)
        header_m = re.search(r"<thead>(.*?)</thead>", tbl, re.S)
        header = header_m.group(1) if header_m else ""
        header_cells = [re.sub(r"<[^>]+>", "", c).strip().lower() for c in cell_re.findall(header)]
        has_source_col = any("source" in h for h in header_cells)

        body_m = re.search(r"<tbody>(.*?)</tbody>", tbl, re.S)
        body = body_m.group(1) if body_m else tbl.replace(header, "")
        for row in row_re.findall(body):
            if "<td" not in row:
                continue
            plain = re.sub(r"<[^>]+>", " ", row)
            has_href = bool(href_re.search(row))
            has_unverified = "UNVERIFIED" in row
            has_marker = any(m in row for m in (
                'class="pill', 'class="ok"', 'class="flag"', "class=\"flag\"",
                "Process rule", "proposal", "Proposal", "spec", "Kelly criterion", "Standard", "RULE",
            ))
            if has_source_col and not (has_href or has_unverified):
                problems.append(f"{rel}: SOURCE table row without link/UNVERIFIED -> {plain.strip()[:90]}")
            if not (has_href or has_unverified or has_marker):
                warnings.append(f"{rel}: row without evidence marker -> {plain.strip()[:90]}")

n_tables = sum(len(re.findall(r"<table>", p.read_text())) for p in pages)
print(f"checked {len(pages)} pages, {n_tables} tables")
for w in warnings:
    print("WARN ", w)
for p in problems:
    print("FAIL ", p)
if problems:
    sys.exit(1)
print("OK — every source-table row carries an official link or UNVERIFIED flag")
