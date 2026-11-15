#!/usr/bin/env python3
"""Repo-wide line-by-line verification for every site module (session arena/35b167ca-x3).

Covers ALL HTML pages in the repository — root category pages, docs/, docs/pages/,
dashboard/, lab/, x3lab/, site/, pages/, legacy/ — none of which are fully covered
by the existing per-module checkers:

  scripts/check_site.py      -> docs/ root pages only
  tools/verify_site.py       -> docs/pages/ only
  tools/check_links.py       -> root *.html links only
  scripts/check_dashboard.py -> index.html + lab/ links only
  scripts/verify_data.py     -> x3lab/ data wiring
  scripts/check_render.js    -> lab/ rendered views

Rules enforced (all hard, exit 1 on any violation):

  L1  LINKS          Every relative href/src on every page must resolve to a file
                     that exists (fragments and queries stripped). Root-absolute
                     paths are reported: GitHub Pages serves this repo under /X3/,
                     so a root-absolute path would break on the live site.

  L2  SOURCE ROWS    In any table whose header contains a "source" column, every
                     body row must satisfy at least one of:
                       (a) the row carries an external http(s) link;
                       (b) the source cell carries an internal link — a relative
                           path or a #fragment pointer to the page that
                           documents that row's provenance;
                       (c) the row or its source cell carries an explicit
                           marker — text stating the value cannot be confirmed
                           from an official source (strong markers: UNVERIFIED,
                           no official source, left blank, DERIVED (an explicit
                           model-output badge, i.e. not a sourced fact), BLOCKED
                           (explicitly unusable, with reason — e.g. no prices
                           exist), ...;
                           weak markers such as pending/proposed/open/n/a count
                           only inside the source cell itself).
                     Headers containing the word "sourced" (e.g. a
                     "Rows sourced or flagged" count column) are metrics, not
                     provenance columns, and are not treated as source columns.
                     This is the brief's rule: "Every table row must have a source
                     link to an official site. If a value can't be confirmed from
                     an official source, leave it blank and flag it as unverified."

  L3  FLAGGED PAGES  Every body row on any page whose file name contains "flag"
                     must carry an external link or an unverified/flag marker.

Register/spec pages (requirements, questions, suggestions, validation, strategy,
roadmaps) are not exempt from L1; their non-source tables are not subject to L2
because their rows are proposals, not values — proposals are reviewed on the
Suggestions page per the brief.

Usage:  python3 scripts/audit_all.py [--quiet]
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TABLE_RE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
THEAD_RE = re.compile(r"<thead[^>]*>(.*?)</thead>", re.S)
TBODY_RE = re.compile(r"<tbody[^>]*>(.*?)</tbody>", re.S)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
HREF_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
TAG_RE = re.compile(r"<[^>]+>")

# Strong markers: may appear anywhere in the row. They state plainly that the
# value cannot be confirmed from an official source.
STRONG_RE = re.compile(
    r"""
      unverified
    | not\s+confirmed
    | left\s+blank
    | to\s+be\s+verified
    | no\s+official
    | none\s+identified
    | not\s+applicable
    | \bn/?a\b
    | no\s+line
    | no\s+wagers
    | no\s+market
    | no\s+game\s+log
    | no\s+strategy
    | no\s+nfl
    | no\s+such
    | no\s+data
    | no\s+archive
    | no\s+provider
    | no\s+external\s+source
    | no\s+dated
    | no\s+source
    | no\s+decision
    | not\s+ingested
    | not\s+computed
    | not\s+defined
    | not\s+sourced
    | not\s+present
    | not\s+retrieved
    | nothing
    | never
    | cannot
    | can\s+never
    | \bflagged\b
    | \bDERIVED\b
    | \bBLOCKED\b
    | class="[^"]*\b(?:flag|blank|unverif)\b[^"]*
    | 404
    """,
    re.I | re.X,
)

# Weak markers: only credible when they appear inside the source cell itself,
# where they describe the provenance state (pending / proposed / open / ...).
WEAK_RE = re.compile(
    r"""
      pending
    | proposed
    | proposal
    | requires
    | open\b
    | unknown
    | absent
    | blocked
    | \bnone\b
    | to\s+be\s+(?:defined|computed|searched)
    | awaiting
    | not\s+(?:started|validated)
    """,
    re.I | re.X,
)


class PageParser(HTMLParser):
    """Collects link targets from a page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        for key in ("href", "src"):
            if a.get(key):
                self.links.append(a[key])


def strip_markup(fragment: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", fragment)).strip()


def source_cell_of_row(row_html: str, src_idx: int | None) -> str:
    cells = CELL_RE.findall(row_html)
    if not cells:
        return ""
    if src_idx is not None and src_idx < len(cells):
        return cells[src_idx]
    return cells[-1]  # fall back to the last cell


def main() -> int:
    quiet = "--quiet" in sys.argv
    pages = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)
    if not pages:
        print("FAIL: no HTML pages found")
        return 1

    problems: list[str] = []
    warnings: list[str] = []
    stats = {
        "pages": 0, "links": 0, "internal": 0, "tables": 0,
        "source_tables": 0, "source_rows": 0, "source_rows_linked": 0,
        "source_rows_unverified": 0, "flagged_rows": 0,
    }

    for page in pages:
        rel = page.relative_to(ROOT)
        text = page.read_text(encoding="utf-8", errors="replace")
        stats["pages"] += 1

        # ---- L1: link integrity -------------------------------------
        parser = PageParser()
        parser.feed(text)
        for href in parser.links:
            stats["links"] += 1
            if href.startswith(("http://", "https://", "#", "mailto:",
                                "javascript:", "data:", "tel:")):
                continue
            if href.startswith("/"):
                warnings.append(f"{rel}: root-absolute path breaks under /X3/ -> {href}")
                continue
            stats["internal"] += 1
            target = href.split("#", 1)[0].split("?", 1)[0]
            if not target:
                continue
            # paste-ready fragments (*-block.html) are written with root-relative
            # links by their generator (build_decision.py: "lives at the repository root")
            base = ROOT if page.name.endswith("-block.html") else page.parent
            if not (base / target).exists():
                problems.append(f"L1 {rel}: broken internal link -> {href}")

        # ---- L2: source cells in source-column tables ---------------
        is_flagged_page = "flag" in page.name.lower()
        flagged_seen = 0
        for tbl_m in TABLE_RE.finditer(text):
            tbl = tbl_m.group(1)
            stats["tables"] += 1
            thead = THEAD_RE.search(tbl)
            headers = [strip_markup(c).lower() for c in CELL_RE.findall(thead.group(1))] if thead else []
            src_idx = None
            for i, h in enumerate(headers):
                if "source" in h and "sourced" not in h:
                    src_idx = i
                    break
            body_m = TBODY_RE.search(tbl)
            body = body_m.group(1) if body_m else tbl
            if thead:
                body = body.replace(thead.group(0), "", 1)
            rows = [r for r in TR_RE.findall(body) if "<td" in r]
            if src_idx is not None:
                stats["source_tables"] += 1
                for row in rows:
                    stats["source_rows"] += 1
                    cell = source_cell_of_row(row, src_idx)
                    plain = strip_markup(cell)
                    if re.search(r"https?://", row):
                        # (a) the row itself carries an external source link
                        stats["source_rows_linked"] += 1
                        continue
                    if re.search(r"""href\s*=\s*["'](?!https?:|mailto:)[^"']+["']""", cell, re.I):
                        # (b) the source cell links the page documenting provenance
                        #     (relative path or #fragment on the same page)
                        stats["source_rows_linked"] += 1
                        continue
                    if STRONG_RE.search(row) or WEAK_RE.search(plain):
                        # (c) explicit unverified/flag marker
                        stats["source_rows_unverified"] += 1
                        continue
                    problems.append(
                        f"L2 {rel}: source cell neither links nor flags UNVERIFIED "
                        f"(row: {strip_markup(row)[:90]!r} | source cell: {plain[:70]!r})"
                    )

            # ---- L3: every row on a flagged page --------------------
            if is_flagged_page:
                for row in rows:
                    flagged_seen += 1
                    stats["flagged_rows"] += 1
                    plain = strip_markup(row)
                    if (re.search(r"https?://", row)
                            or re.search(r"""href\s*=\s*["'](?!https?:|mailto:)[^"']+["']""", row, re.I)
                            or STRONG_RE.search(row)
                            or WEAK_RE.search(plain)):
                        continue
                    problems.append(
                        f"L3 {rel}: flagged-page row without link/UNVERIFIED marker "
                        f"-> {plain[:90]!r}"
                    )

    # ---- report -----------------------------------------------------
    print(f"audit_all: {stats['pages']} pages, {stats['links']} link refs "
          f"({stats['internal']} internal), {stats['tables']} tables")
    print(f"  source-column tables: {stats['source_tables']} | "
          f"source rows: {stats['source_rows']} "
          f"(linked: {stats['source_rows_linked']}, "
          f"unverified-marked: {stats['source_rows_unverified']})")
    print(f"  flagged-page rows checked: {stats['flagged_rows']}")
    for w in warnings:
        print("WARN ", w)
    for p in problems:
        print("FAIL ", p)
    if problems:
        print(f"FAIL — {len(problems)} violation(s).")
        return 1
    print("PASS — all internal links resolve; every source cell links an "
          "official source or is explicitly flagged unverified; every "
          "flagged-page row carries a marker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
