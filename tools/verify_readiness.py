#!/usr/bin/env python3
"""Row-level gate for readiness/** (arena/129e76b5-x3). Offline; exit 1 on any failure.

Checks:
  D1  every CSV has its required columns and no blank id
  D2  statuses and answer statuses come from the allowed vocabulary
  D3  every requirement, question, suggestion, flag and source row has an official link
      or an explicit UNVERIFIED reason (no silent blanks)
  D4  every evidence path exists in the repository; every metric key is computable
  D5  every ID cited in any text (R##, Q-##, S-##, F-##, D-##) exists
  D6  every official link uses an allowed host; third-party and secondary sources are labelled
  H1  every table in readiness/*.html: any column headed "Official source" links an
      https URL or says UNVERIFIED on every body row
  H2  every body row on a page whose name contains "flag" carries a link or an UNVERIFIED marker
  H3  every internal link and src in readiness/*.html and the landing fragment resolves
  H4  the landing table has one row per requirement, and the index table has the same count
  B1  rebuilding in memory reproduces the committed readiness/*.html and fragment byte for byte
  X1  root index.html links readiness/index.html and includes the landing fragment
"""
import csv
import importlib.util
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build_readiness", os.path.join(ROOT, "tools", "build_readiness.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

FAILS = []
STATS = {"requirements": 0, "questions": 0, "suggestions": 0, "flags": 0, "sources": 0, "html_pages": 0, "table_rows": 0}
ALLOWED_HOST_SUFFIX = ("nfl.com", "houstontexans.com")  # official NFL and club sites
THIRD_PARTY_OK = ("github.com", "espn.com", "snapcountff.com", "sticktothemodel.com", "statchasers.com")
REQ_COLS = ["id", "group", "requirement", "status", "blocking_gate", "clearing_number", "metric",
            "evidence_path", "official_url", "unverified_reason", "note"]
Q_COLS = ["id", "question", "what_we_have", "what_is_missing", "answer_status", "how_to_discover", "official_url", "unverified_reason"]
S_COLS = ["id", "suggestion", "addresses", "options", "recommendation", "owner_decision", "status", "official_url", "unverified_reason"]
F_COLS = ["id", "irregularity", "evidence_path", "evidence_detail", "official_url", "unverified_reason", "action", "severity"]
SRC_COLS = ["url", "supports", "read_on", "read_method", "status"]
ID_RE = re.compile(r"\b(R\d{2}|Q-\d{2}|S-\d{2}|F-\d{2}|D-\d{2})\b")


def fail(code, msg):
    FAILS.append(f"{code} {msg}")


def load(name):
    with open(os.path.join(B.DATA, name), encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def host_ok(url):
    host = urlparse(url).hostname or ""
    return host.endswith(ALLOWED_HOST_SUFFIX)


def check_csv_shape(name, cols, rows, id_col="id"):
    header, _ = load(name)
    if header != cols:
        fail("D1", f"{name} header is {header}, expected {cols}")
    for i, r in enumerate(rows, start=2):
        if not (r.get(id_col) or "").strip():
            fail("D1", f"{name} line {i} has no id")


def main():
    KNOWN_METRICS = set(B.metrics())
    # ---------- D1, D2, D3, D6 : data files ----------
    hr, reqs = load("requirements.csv")
    check_csv_shape("requirements.csv", REQ_COLS, reqs)
    STATS["requirements"] = len(reqs)
    ids = [r["id"] for r in reqs]
    if len(set(ids)) != len(ids):
        fail("D1", "duplicate requirement ids")
    for r in reqs:
        if r["status"] not in B.STATUS_ORDER:
            fail("D2", f"{r['id']} status {r['status']!r}")
        if not r["official_url"].strip() and "UNVERIFIED" not in r["unverified_reason"] and not r["unverified_reason"].strip():
            fail("D3", f"{r['id']} has neither an official link nor an unverified reason")
        for u in [x.strip() for x in r["official_url"].split(";") if x.strip()]:
            if not u.startswith("https://") or not host_ok(u):
                fail("D6", f"{r['id']} official link is not an allowed official host: {u}")
        for p in [x.strip() for x in r["evidence_path"].split(";") if x.strip()]:
            if not os.path.exists(os.path.join(ROOT, p)):
                fail("D4", f"{r['id']} evidence path missing: {p}")
        if r["metric"] and r["metric"] not in KNOWN_METRICS:
            fail("D4", f"{r['id']} metric key unknown: {r['metric']}")
        if r["status"] == "DONE" and not r["evidence_path"].strip():
            fail("D4", f"{r['id']} is DONE but has no evidence path")

    _, qs = load("questions.csv")
    check_csv_shape("questions.csv", Q_COLS, qs)
    STATS["questions"] = len(qs)
    for q in qs:
        if not q["answer_status"].split(" ")[0] in ("OPEN", "PARTIAL", "ANSWERED"):
            fail("D2", f"{q['id']} answer_status {q['answer_status']!r}")
        if not q["official_url"].strip() and not q["unverified_reason"].strip():
            fail("D3", f"{q['id']} has neither an official link nor an unverified reason")
        if q["official_url"].strip() and not host_ok(q["official_url"]):
            fail("D6", f"{q['id']} link not an allowed official host: {q['official_url']}")

    _, sugg = load("suggestions.csv")
    check_csv_shape("suggestions.csv", S_COLS, sugg)
    STATS["suggestions"] = len(sugg)
    for s in sugg:
        if s["status"] != "PROPOSED":
            fail("D2", f"{s['id']} must be PROPOSED (nothing is implemented), got {s['status']!r}")
        if not s["official_url"].strip() and not s["unverified_reason"].strip():
            fail("D3", f"{s['id']} has neither an official link nor an unverified reason")

    _, flags = load("flags.csv")
    check_csv_shape("flags.csv", F_COLS, flags)
    STATS["flags"] = len(flags)
    for f_ in flags:
        if f_["severity"] not in ("High", "Medium", "Low", "Resolved"):
            fail("D2", f"{f_['id']} severity {f_['severity']!r}")
        if not f_["official_url"].strip() and not f_["unverified_reason"].strip():
            fail("D3", f"{f_['id']} has neither an official link nor an unverified reason")
        if f_["official_url"].strip() and not host_ok(f_["official_url"]):
            labelled = "third" in f_["unverified_reason"].lower() or "not an official" in f_["unverified_reason"].lower()
            if not labelled:
                fail("D6", f"{f_['id']} link is not an allowed official host and is not labelled third-party: {f_['official_url']}")

    _, srcs = load("sources.csv")
    check_csv_shape("sources.csv", SRC_COLS, srcs, id_col="url")
    STATS["sources"] = len(srcs)
    for s in srcs:
        ok_status = s["status"].split(" ")[0] in ("VERIFIED", "PRIOR", "SECONDARY", "THIRD-PARTY")
        if not ok_status:
            fail("D2", f"source {s['url']} status {s['status']!r}")
        host = urlparse(s["url"]).hostname or ""
        if s["status"].startswith("VERIFIED") and not host_ok(s["url"]):
            fail("D6", f"source {s['url']} marked VERIFIED but host not official")
        if not s["url"].startswith("https://"):
            fail("D6", f"source url not https: {s['url']}")

    # ---------- D5 : every cited ID exists ----------
    known = set(ids) | {q["id"] for q in qs} | {s["id"] for s in sugg} | {f_["id"] for f_ in flags} | {d[0] for d in B.DECISIONS}
    all_text = []
    for rows_ in (reqs, qs, sugg, flags):
        for r in rows_:
            all_text.append(" ".join(str(v) for v in r.values()))
    for d in B.DECISIONS:
        all_text.append(d[1] + " " + d[2])
    for text in all_text:
        for cited in ID_RE.findall(text):
            if cited not in known:
                fail("D5", f"cited id {cited} does not exist")

    # ---------- D4 : metrics computable ----------
    M = B.metrics()
    for r in reqs:
        try:
            B.now_text(r["metric"], M)
        except Exception as e:  # noqa: BLE001
            fail("D4", f"{r['id']} metric error: {e}")

    # ---------- B1 : rebuild reproduces committed files ----------
    pages, frag = B.build()
    for name, text in pages.items():
        path = os.path.join(B.OUT, name)
        if not os.path.exists(path) or open(path, encoding="utf-8").read() != text:
            fail("B1", f"readiness/{name} is not the current build; run python3 tools/build_readiness.py")
    fpath = os.path.join(B.FRAG, "landing-table.inc")
    if not os.path.exists(fpath) or open(fpath, encoding="utf-8").read() != frag + "\n":
        fail("B1", "readiness/fragments/landing-table.inc is not the current build")

    # ---------- H1-H4 : rendered HTML ----------
    class Page(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.links = []
            self.tables = []  # list of {"headers": [...], "rows": [[cell_html,...],...]}
            self._table = None
            self._row = None
            self._cell = None
            self._cell_buf = None
            self._in_th = False

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "a" and a.get("href"):
                self.links.append(a["href"])
            if tag in ("link",) and a.get("href"):
                self.links.append(a["href"])
            if tag in ("script", "img") and a.get("src"):
                self.links.append(a["src"])
            if tag == "table":
                self._table = {"headers": [], "rows": []}
            elif tag == "tr" and self._table is not None:
                self._row = []
            elif tag in ("td", "th") and self._row is not None:
                self._cell = []
                self._in_th = tag == "th"
            if self._cell is not None:
                self._cell.append(self.get_starttag_text() or "")

        def handle_endtag(self, tag):
            if self._cell is not None and tag not in ("td", "th"):
                self._cell.append(f"</{tag}>")
            if tag in ("td", "th") and self._cell is not None:
                text = "".join(self._cell)
                self._row.append((self._in_th, text))
                self._cell = None
            elif tag == "tr" and self._row is not None and self._table is not None:
                is_head = bool(self._row) and all(h for h, _ in self._row)
                if is_head:
                    self._table["headers"] = [re.sub(r"<[^>]+>", "", c).strip() for _, c in self._row]
                elif self._row:
                    self._table["rows"].append([c for _, c in self._row])
                self._row = None
            elif tag == "table" and self._table is not None:
                self.tables.append(self._table)
                self._table = None

        def handle_data(self, data):
            if self._cell is not None:
                self._cell.append(data)

    def cell_has_source(cell_html):
        return bool(re.search(r'href="https://', cell_html)) or "UNVERIFIED" in cell_html

    pages_dir = B.OUT
    html_files = sorted(os.path.join(pages_dir, f) for f in os.listdir(pages_dir) if f.endswith(".html"))
    html_files.append(fpath)
    for path in html_files:
        STATS["html_pages"] += 1
        text = open(path, encoding="utf-8").read()
        p = Page()
        p.feed(text)
        base = os.path.dirname(path)
        rel = os.path.relpath(path, ROOT)
        for link in p.links:
            if link.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            anchor_base = ROOT if path == fpath else base  # the fragment is included from the root page
            if not os.path.exists(os.path.normpath(os.path.join(anchor_base, target))):
                fail("H3", f"{rel}: broken link {link}")
        for t in p.tables:
            if "Official source" in t["headers"]:
                idx = t["headers"].index("Official source")
                for row in t["rows"]:
                    STATS["table_rows"] += 1
                    if idx >= len(row) or not cell_has_source(row[idx]):
                        fail("H1", f"{rel}: a row has no official link and no UNVERIFIED marker")
            if "flag" in os.path.basename(path).lower():
                for row in t["rows"]:
                    joined = " ".join(row)
                    if not (re.search(r'href="https?://', joined) or "UNVERIFIED" in joined):
                        fail("H2", f"{rel}: flagged row has no link or unverified marker")
        if re.search(r"TODO|lorem|XXX", re.sub(r"<style>.*?</style>", "", text, flags=re.S), flags=re.I):
            fail("H3", f"{rel}: placeholder text found")

    index_html = open(os.path.join(B.OUT, "index.html"), encoding="utf-8").read()
    idx_rows = index_html.count("<tr>") - 1
    frag_rows = frag.count("<tr>") - 1
    if idx_rows != len(reqs) or frag_rows != len(reqs):
        fail("H4", f"table rows: index={idx_rows} landing={frag_rows} requirements={len(reqs)}")
    STATS["landing_rows"] = frag_rows

    # ---------- X1 : root landing wiring ----------
    root = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    if 'href="readiness/index.html"' not in root:
        fail("X1", "root index.html does not link readiness/index.html")
    if 'id="readiness"' not in root:
        fail("X1", "root index.html does not include the readiness table")

    # ---------- report ----------
    print("verify_readiness: " + ", ".join(f"{k}={v}" for k, v in STATS.items()))
    if FAILS:
        print(f"FAIL: {len(FAILS)} problem(s)")
        for f_ in FAILS[:200]:
            print("  " + f_)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
