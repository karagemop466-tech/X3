#!/usr/bin/env python3
"""Hard gate for the X3 decision council (council/).

Fails (exit 1) on any of:
  1. a table row that carries neither an official source link nor an explicit badge;
  2. a broken internal link, asset reference or nav target;
  3. a rendered page that is not well-formed enough to parse;
  4. a build that is not deterministic (two runs, different bytes);
  5. an unfilled {{token}} left in the HTML;
  6. a data row in council.json whose source field is empty and is not marked unverified.

It is offline and fast: it reads only files in the repository.
Run after scripts/council_build.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNCIL = os.path.join(ROOT, "council")
DATA = os.path.join(ROOT, "data", "council", "council.json")

DATA_KEY = "data/council/council.json"

NAV = ["index.html", "executive-summary.html", "requirements.html", "questions.html",
       "suggestions.html", "verification.html", "repo-review.html", "flagged.html",
       "sources.html"]

BADGE_RE = re.compile(r'class="bad[^"]*"[^>]*>([^<]+)<')
LINK_RE = re.compile(r'href="([^"]+)"')
TOKEN_RE = re.compile(r"\{\{\w+\}\}")
ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
TD_RE = re.compile(r"<td>(.*?)</td>", re.S)
SRC_RE = re.compile(r'href="(https?://[^"]+)"')

# Rows that legitimately carry no external link, because the row is a rule or a
# design statement rather than a measurement. They must still carry a badge.
EXEMPT_CELL = re.compile(r'class="bad')

failures = []
checks = 0


def fail(msg):
    failures.append(msg)


def ok(msg):
    global checks
    checks += 1
    print("  ok   %s" % msg)


def page_files():
    out = []
    for fn in sorted(os.listdir(COUNCIL)):
        if fn.endswith(".html"):
            out.append(fn)
    return out


MISLABEL_RE = re.compile(r'<a href="https?://[^"]+"[^>]*>[^<]*(?:UNVERIFIED|no official source)')


def check_mislabels(fn, txt):
    """A row that links a source must never render the UNVERIFIED text. A link and a
    badge are opposites: printing both on one row tells the reader the row is
    unsourced when it is not."""
    for mo in MISLABEL_RE.finditer(txt):
        fail("%s: a row links a source but is labelled UNVERIFIED: %s"
             % (fn, mo.group(0)[:110]))


def check_rows(fn, txt):
    """Every <tr> must contain either an external link or an explicit badge."""
    n = 0
    for mo in ROW_RE.finditer(txt):
        row = mo.group(1)
        if "<td>" not in row:      # header rows carry no data
            continue
        n += 1
        if SRC_RE.search(row):
            continue
        if EXEMPT_CELL.search(row):
            continue
        fail("%s: a table row carries neither a source link nor an UNVERIFIED badge: %s"
             % (fn, row[:110].replace("\n", " ")))
    return n


def check_links(fn, txt):
    for mo in LINK_RE.finditer(txt):
        href = mo.group(1)
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = href.split("#")[0].split("?")[0]
        if not target:
            continue
        path = os.path.normpath(os.path.join(COUNCIL, target))
        if not os.path.exists(path):
            fail("%s: broken internal link -> %s" % (fn, href))


def main():
    print("council verify")

    if not os.path.isdir(COUNCIL):
        print("FAIL: council/ does not exist - run scripts/council_build.py first")
        return 1

    files = page_files()
    if not files:
        print("FAIL: council/ has no html pages")
        return 1

    # 1. nav completeness ---------------------------------------------------
    index = open(os.path.join(COUNCIL, "index.html"), encoding="utf-8").read()
    missing = [p for p in NAV if 'href="%s"' % p not in index]
    if missing:
        fail("index.html nav is missing: %s" % ", ".join(missing))
    else:
        ok("nav lists all %d pages" % len(NAV))

    # 2. every page: no token, rows sourced, links resolve -------------------
    total_rows = 0
    for fn in files:
        txt = open(os.path.join(COUNCIL, fn), encoding="utf-8").read()

        tok = TOKEN_RE.search(txt)
        if tok:
            fail("%s: unfilled prose token %s" % (fn, tok.group(0)))

        if "<html" not in txt or "</html>" not in txt:
            fail("%s: page is not a complete document" % fn)

        total_rows += check_rows(fn, txt)
        check_links(fn, txt)
        check_mislabels(fn, txt)

    if total_rows < 40:
        fail("only %d table rows found across the tree - expected the full registers" % total_rows)
    else:
        ok("%d table rows checked across %d pages; every row is linked or badged, and no "
           "linked row is labelled UNVERIFIED" % (total_rows, len(files)))

    # 3. css present and referenced ----------------------------------------
    css = os.path.join(COUNCIL, "assets", "council.css")
    if not os.path.exists(css):
        fail("assets/council.css is missing")
    else:
        for fn in files:
            if 'href="assets/council.css"' not in open(
                    os.path.join(COUNCIL, fn), encoding="utf-8").read():
                fail("%s: does not reference assets/council.css" % fn)
        ok("stylesheet present and referenced by all %d pages" % len(files))

    # 4. determinism --------------------------------------------------------
    before = {}
    for fn in files + ["assets/council.css"]:
        p = os.path.join(COUNCIL, fn)
        before[fn] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    if os.path.exists(DATA):
        before[DATA_KEY] = hashlib.sha256(open(DATA, "rb").read()).hexdigest()

    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "council_build.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        fail("rebuild failed: %s" % (r.stderr.strip() or r.stdout.strip()))
    else:
        drift = []
        for fn, h in before.items():
            p = DATA if fn == DATA_KEY else os.path.join(COUNCIL, fn)
            now = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if now != h:
                drift.append(fn)
        if drift:
            fail("build is not deterministic; changed on rebuild: %s" % ", ".join(drift))
        else:
            ok("build is deterministic (%d files byte-identical on rerun)" % len(before))

    # 5. data payload -------------------------------------------------------
    if not os.path.exists(DATA):
        fail("data/council/council.json is missing")
    else:
        d = json.load(open(DATA))
        for key in ("requirements", "questions", "suggestions", "flags", "sources",
                    "verification", "verified", "correlations", "trees"):
            if not d.get(key):
                fail("council.json: register %r is empty" % key)
        for c in d.get("correlations", []):
            if not c.get("n"):
                fail("council.json: correlation %r has no n" % c.get("pair"))
            if not c.get("source"):
                fail("council.json: correlation %r has no source" % c.get("pair"))
        for v in d.get("verified", []):
            if not v.get("source") and v.get("value"):
                fail("council.json: verified fact %r has a value but no source" % v["id"])
        ok("data payload: %d correlations with n and source, %d verified facts"
           % (len(d.get("correlations", [])), len(d.get("verified", []))))

    # 6. external links point at the right hosts ----------------------------
    hosts = set()
    for fn in files:
        for mo in SRC_RE.finditer(open(os.path.join(COUNCIL, fn), encoding="utf-8").read()):
            hosts.add(re.sub(r"^https?://(www\.)?", "", mo.group(1)).split("/")[0])
    allowed = {"nfl.com", "operations.nfl.com", "github.com", "azcardinals.com"}
    unexpected = sorted(h for h in hosts if h not in allowed)
    if unexpected:
        fail("links to hosts outside the approved set: %s" % ", ".join(unexpected))
    else:
        ok("all external links point at approved hosts: %s" % ", ".join(sorted(hosts)))

    print()
    if failures:
        print("COUNCIL VERIFY FAILED - %d problem(s):" % len(failures))
        for f in failures:
            print("  FAIL  %s" % f)
        return 1
    print("COUNCIL VERIFY PASSED (%d checks, %d table rows)" % (checks, total_rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
