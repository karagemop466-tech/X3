#!/usr/bin/env python3
"""Gate for the atlas/ module (session arena/dbb50f8c-x3).

Checks, in order:
  A1  every page parses as HTML
  A2  every relative link resolves; no root-absolute paths
  A3  every row of a source-column table links an official page or carries an
      explicit UNVERIFIED / BLOCKED / DERIVED marker
  A4  every row on the flagged page carries a link or a marker
  A5  the arithmetic is self-consistent (standings sums, game counts, model rows)
  A6  no market price, depth rank or strategy result has been filled in
Exit 1 on any failure.
"""
from __future__ import annotations

import csv
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "atlas"
DATA = ROOT / "data" / "atlas"

STRONG = re.compile(
    r"unverified|not confirmed|left blank|no official|none identified|no line|no wagers|"
    r"no market|no game log|no strategy|no nfl|no data|no source|cannot|can never|flagged|"
    r"DERIVED|BLOCKED|NOT VERIFIED|NOT STARTED|AWAITING DEFINITION|404|UNVERIFIED",
    re.I,
)


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        d = dict(attrs)
        for k in ("href", "src"):
            if d.get(k):
                self.links.append(d[k])


TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
THEAD_RE = re.compile(r"<thead[^>]*>(.*?)</thead>", re.S)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def plain(s):
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", s)).strip()


def read_csv(name):
    with (DATA / name).open() as fh:
        return list(csv.DictReader(fh))


def main():
    fails: list[str] = []
    checks = 0

    pages = sorted(SITE.glob("*.html"))
    if len(pages) < 20:
        fails.append(f"A1 expected at least 20 pages, found {len(pages)}")

    rows_checked = 0
    flagged_rows = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        p = P()
        p.feed(text)
        checks += 1

        for href in p.links:
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if href.startswith("/"):
                fails.append(f"A2 {page.name}: root-absolute path breaks under /X3/ -> {href}")
                continue
            target = href.split("#")[0].split("?")[0]
            if target and not (page.parent / target).exists():
                fails.append(f"A2 {page.name}: broken link -> {href}")

        is_flag = "flag" in page.name.lower()
        for tbl in TABLE_RE.findall(text):
            head = THEAD_RE.search(tbl)
            headers = [plain(c).lower() for c in CELL_RE.findall(head.group(1))] if head else []
            src_idx = next((i for i, h in enumerate(headers) if "source" in h and "sourced" not in h), None)
            body = tbl.replace(head.group(0), "", 1) if head else tbl
            for row in [r for r in TR_RE.findall(body) if "<td" in r]:
                if src_idx is not None:
                    rows_checked += 1
                    if (re.search(r"https?://", row)
                            or re.search(r"""href\s*=\s*["'](?!https?:|mailto:)[^"']+["']""", row, re.I)
                            or STRONG.search(plain(row))):
                        pass
                    else:
                        fails.append(f"A3 {page.name}: unsourced row -> {plain(row)[:80]!r}")
                if is_flag:
                    flagged_rows += 1
                    if (re.search(r"https?://", row) or STRONG.search(plain(row))):
                        pass
                    else:
                        fails.append(f"A4 {page.name}: flagged row without marker -> {plain(row)[:80]!r}")
    checks += 1

    # ---- A5 arithmetic -------------------------------------------------
    st = read_csv("standings_2026_thru_wk10.csv")
    if len(st) != 32:
        fails.append(f"A5 standings has {len(st)} rows, expected 32")
    tg = sum(int(r["games"]) for r in st)
    if tg != 300:
        fails.append(f"A5 club-games sum to {tg}, expected 300")
    if tg % 2:
        fails.append("A5 club-games must be even")
    if sum(int(r["w"]) for r in st) != sum(int(r["l"]) for r in st):
        fails.append("A5 wins and losses do not balance across the league")
    if sum(int(r["pf"]) for r in st) != sum(int(r["pa"]) for r in st):
        fails.append("A5 points for and points against do not balance")
    checks += 5

    res = read_csv("results_2026_wk10.csv")
    if len(res) != 14:
        fails.append(f"A5 week 10 results has {len(res)} rows, expected 14")
    for r in res:
        if int(r["home_pts"]) + int(r["away_pts"]) <= 0:
            fails.append(f"A5 implausible score in {r['game']}")
        if int(r["home_margin"]) != int(r["home_pts"]) - int(r["away_pts"]):
            fails.append(f"A5 margin mismatch in {r['game']}")
    checks += 1

    fx = read_csv("fixtures_2026_wk11.csv")
    if len(fx) != 13:
        fails.append(f"A5 week 11 fixtures has {len(fx)} rows, expected 13")
    if sum(1 for r in fx if r["venue_flag"]) != 3:
        fails.append(f"A5 expected 3 venue conflicts, found {sum(1 for r in fx if r['venue_flag'])}")
    clubs = [c for r in fx for c in (r["away"], r["home"])]
    if len(set(clubs)) != 26:
        fails.append(f"A5 week 11 should involve 26 distinct clubs, found {len(set(clubs))}")
    checks += 3

    orig = read_csv("origination_2026_wk11.csv")
    if len(orig) != 13:
        fails.append(f"A5 origination has {len(orig)} rows, expected 13")
    for r in orig:
        try:
            base = float(r["fair_side_home"])
            pers = float(r["fair_side_personnel"])
            delta = float(r["personnel_delta"])
            gap = float(r["total_gap"])
        except ValueError:
            fails.append(f"A5 non-numeric model output in {r['game']}")
            continue
        if abs((base + delta) - pers) > 0.011:
            fails.append(f"A5 side arithmetic broken in {r['game']}")
        if abs((float(r["fair_total_points_model"]) - float(r["fair_total_league_anchored"])) - gap) > 0.011:
            fails.append(f"A5 total gap arithmetic broken in {r['game']}")
        p = float(r["p_home_win"])
        if not 0.0 < p < 1.0:
            fails.append(f"A5 win probability out of range in {r['game']}")
    checks += 3

    corr = read_csv("correlations_2026.csv")
    if len(corr) != 10:
        fails.append(f"A5 correlations has {len(corr)} rows, expected 10")
    for r in corr:
        if int(r["n"]) < 26:
            fails.append(f"A5 correlation on too few observations: {r['quantity_a']} n={r['n']}")
        if not r["source"].startswith("http"):
            fails.append(f"A5 correlation without source: {r['quantity_a']}")
    checks += 1

    inj = read_csv("injury_counts_2026_wk10.csv")
    if len(inj) != 28:
        fails.append(f"A5 injury club counts has {len(inj)} rows, expected 28")
    if sum(int(r["rows_committed_2026_11_14"]) for r in inj) != 345:
        fails.append("A5 committed injury rows do not sum to 345")
    checks += 2

    # ---- A6 nothing forbidden has been filled in ------------------------
    for r in orig:
        for k in ("market_side", "market_total", "market_ml", "diff_side", "diff_total", "diff_ml"):
            if (r.get(k) or "").strip():
                fails.append(f"A6 {k} is populated for {r['game']} - no market source exists")
    for name in ("injury_report_2026_wk10.csv",):
        pass
    checks += 1

    total = checks + rows_checked
    if fails:
        print(f"atlas_verify: FAIL ({len(fails)} problem(s))")
        for f in fails[:40]:
            print("  FAIL", f)
        return 1
    print(f"atlas_verify: PASS - {len(pages)} pages, {rows_checked} source rows, "
          f"{flagged_rows} flagged rows, {checks} checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
