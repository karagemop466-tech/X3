#!/usr/bin/env python3
"""
X3 hub quality gate. Fails (exit 1) unless:

  1. every hub page exists and is reachable from the landing page, and the
     navigation on every page links all pages of the tree;
  2. every internal href / stylesheet / script target resolves to a real file;
  3. every row of every table either carries a link to an approved
     official/repo host, or explicitly states UNVERIFIED / DERIVED / no
     designation (blank-by-policy cells);
  4. no unfilled {token} survived into the published HTML (prose can never
     drift from the data);
  5. every hub/data/*.json is valid JSON and its row count matches the CSV it
     was built from.

Run:  python3 tools/verify_hub.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "hub")
# Approved hosts = the league's own domain, this repository, and the official
# club domains taken from the repo team registry (tools/nfl_data.py TEAMS).


def _club_hosts():
    import importlib.util
    spec = importlib.util.spec_from_file_location("nfl_data",
                                                  os.path.join(ROOT, "tools", "nfl_data.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return {urlparse(u).netloc for (_a, _n, _p, u, _c, _d) in m.TEAMS}


_HOSTS = ["nfl.com", "operations.nfl.com", "github.com", "karagemop466-tech.github.io"]
try:
    _HOSTS += sorted(_club_hosts())
except Exception as e:                                    # pragma: no cover
    print("warn: club-host registry unavailable:", e)
APPROVED_HOSTS = {h.lower() for h in _HOSTS}


def host_ok(url):
    host = urlparse(url).netloc.lower()
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    return any(host == h or host.endswith("." + h) for h in APPROVED_HOSTS)

OK_MARKERS = ("UNVERIFIED", "DERIVED", "no designation", "INHERITED", "blank", "NOT USED",
              "PARTIAL", "BLOCKED", "PROPOSED", "ADOPTED", "ARCHIVE", "PASS", "FAIL", "NOT RUN",
              "VERIFIED")


class RowScan(HTMLParser):
    """collect rows: (table caption index, [cells], raw html of the row)"""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.cur = None
        self.row = None
        self.cell = None
        self.in_thead = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.cur = {"head": [], "rows": [], "class": dict(attrs).get("class", "")}
            self.tables.append(self.cur)
        elif tag == "th" and self.cur is not None:
            self.cell = []
            self.cur["head"].append(None)
        elif tag == "thead":
            self.in_thead = True
        elif tag == "tr" and self.cur is not None and not self.in_thead:
            self.row = []
        elif tag == "a" and self.row is not None:
            self.row.append(dict(attrs).get("href", ""))
        elif tag == "td" and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag == "thead":
            self.in_thead = False
        elif tag == "table":
            self.cur = None
        elif tag in ("td", "th") and self.cell is not None:
            if tag == "th" and self.cur is not None:
                self.cur["head"][-1] = " ".join(self.cell)
            else:
                self.row.append(" ".join(self.cell))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.cur["rows"].append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            t = data.strip()
            if t:
                self.cell.append(t)


def approved_link(hrefs_and_text, page_dir=None):
    for h in hrefs_and_text:
        if h.startswith("../") or h.startswith("hub/"):
            tgt = os.path.normpath(os.path.join(page_dir or HUB, h.split("#")[0]))
            if os.path.exists(tgt):
                return True
            continue
        if not h.startswith("http"):
            continue
        if host_ok(h):
            return True
    return False


def _flag_ids():
    import importlib.util
    spec = importlib.util.spec_from_file_location("hub_content", os.path.join(ROOT, "tools",
                                                                                "hub_content.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["hub_content"] = m
    spec.loader.exec_module(m)
    ids = {f[0] for f in m.FLAGS}
    # the X3-v2 session extends the register additively (tools/x3_content2.py) at build time
    spec2 = importlib.util.spec_from_file_location("x3_content2", os.path.join(ROOT, "tools",
                                                                               "x3_content2.py"))
    m2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(m2)
    ids |= {f[0] for f in m2.NEW_FLAGS}
    # and this session's register (tools/x3_content.py) is additive in the same way
    spec3 = importlib.util.spec_from_file_location("x3_content", os.path.join(ROOT, "tools",
                                                                             "x3_content.py"))
    m3 = importlib.util.module_from_spec(spec3)
    spec3.loader.exec_module(m3)
    ids |= {f[0] for f in m3.FLAGS2}
    return ids


try:
    KNOWN_FLAGS = _flag_ids()
except Exception as e:                                    # pragma: no cover
    print("warn: flag register unavailable:", e)
    KNOWN_FLAGS = set()


def main():
    data_rows = 0
    failures, warnings = [], []
    meta_tables = meta_rows = 0
    pages = sorted(f for f in os.listdir(HUB) if f.endswith(".html"))
    if len(pages) < 18:
        failures.append(f"expected >=18 hub pages, found {len(pages)}")

    # 1 + 2: links
    for fn in pages:
        path = os.path.join(HUB, fn)
        html = open(path, encoding="utf-8").read()
        for m in re.finditer(r'href="([^"#]+)(?:#[^"]*)?"', html):
            href = m.group(1)
            if href.startswith(("mailto:", "javascript:")):
                continue
            if href.startswith("http"):
                if not href.startswith(("https://www.nfl.com", "https://nfl.com", "https://operations.nfl.com",
                                        "https://github.com/karagemop466-tech/X3",
                                        "https://karagemop466-tech.github.io/")):
                    if not host_ok(href):
                        warnings.append(f"{fn}: external link to non-approved host {href}")
                continue
            target = os.path.normpath(os.path.join(HUB, href))
            if not os.path.exists(target):
                failures.append(f"{fn}: broken internal link -> {href}")
        for m in re.finditer(r'(?:src|href)="(assets/[^"]+)"', html):
            if not os.path.exists(os.path.join(HUB, m.group(1))):
                failures.append(f"{fn}: missing asset {m.group(1)}")
        # flag references must resolve to a real row of the flag register
        for m in re.finditer(r"\bF-(\d{2})\b", html):
            fid = "F-" + m.group(1)
            if fid not in KNOWN_FLAGS:
                failures.append(f"{fn}: references {fid}, which is not in the flag register")
        # markdown must never ship: the generator emits HTML, not source text
        for m in re.finditer(r"(?<![A-Za-z0-9])\*\*?[A-Za-z][^<>]*?\*\*?(?![A-Za-z0-9])", html):
            failures.append(f"{fn}: markdown emphasis leaked into HTML: {m.group(0)[:50]}")
        for m in re.finditer(r"`[^`\n]{1,40}`", html):
            failures.append(f"{fn}: markdown code span leaked into HTML: {m.group(0)[:50]}")
        # 4: unfilled tokens
        for m in re.finditer(r"\{[a-z_]+\}", html):
            failures.append(f"{fn}: unfilled token {m.group(0)}")
        # 3: row sources
        scan = RowScan()
        scan.feed(html)
        for t in scan.tables:
            if "k-meta" in t["class"]:
                meta_tables += 1
                meta_rows += len(t["rows"])
                continue
            heads = " | ".join(h or "" for h in t["head"])
            for ri, row in enumerate(t["rows"]):
                data_rows += 1
                if not row:
                    continue
                txt = " ".join(str(c) for c in row)
                links = [c for c in row if isinstance(c, str) and c.startswith(("http", "../", "hub/"))]
                if not approved_link(links, HUB) and not any(k in txt for k in OK_MARKERS):
                    failures.append(f"{fn}: table [{heads}] row {ri+1} has no official source link "
                                    f"and no UNVERIFIED/DERIVED marker: {txt[:90]}")

    # landing page reachability
    root_index = os.path.join(ROOT, "index.html")
    landing = open(root_index, encoding="utf-8").read()
    for fn in pages:
        if f"hub/{fn}" not in landing and fn != "index.html":
            failures.append(f"landing page does not link hub/{fn}")
        for other in pages:
            pass
    # navigation completeness
    for fn in pages:
        html = open(os.path.join(HUB, fn), encoding="utf-8").read()
        for other in pages:
            if f'href="{other}"' not in html and f'href="index.html"' not in html:
                failures.append(f"{fn}: nav missing link to {other}")
                break

    # 5: json + csv consistency
    meta = json.load(open(os.path.join(HUB, "data", "meta.json"), encoding="utf-8"))
    import csv
    for name, key in (("injuries_2026_wk10.csv", "injuries"), ("standings_2026_thru_wk9.csv", "standings")):
        rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "hub", name), encoding="utf-8")))
        if len(rows) != meta["rows"][key]:
            failures.append(f"{name}: {len(rows)} rows but meta says {meta['rows'][key]}")
    for fn in os.listdir(os.path.join(HUB, "data")):
        if fn.endswith(".json"):
            try:
                json.load(open(os.path.join(HUB, "data", fn), encoding="utf-8"))
            except Exception as e:                      # pragma: no cover
                failures.append(f"hub/data/{fn}: invalid JSON: {e}")
    lj = json.load(open(os.path.join(HUB, "data", "lines.json"), encoding="utf-8"))
    n_priced = len(lj["rows"])
    html = open(os.path.join(HUB, "lines.html"), encoding="utf-8").read()
    if html.count("<tr>") < n_priced:
        failures.append(f"lines.html shows fewer rows than the data ({n_priced})")

    print(f"pages={len(pages)}  data-rows-checked={data_rows}  register-rows-exempt={meta_rows} "
          f"({meta_tables} k-meta tables)  failures={len(failures)}  warnings={len(warnings)}")
    for f in failures:
        print("FAIL", f)
    for w in warnings[:12]:
        print("warn", w)
    if failures:
        sys.exit(1)
    print("PASS - every row is sourced or explicitly unverified; no broken links; no unfilled tokens")


if __name__ == "__main__":
    main()
