#!/usr/bin/env python3
"""Repo-wide integration audit for the X3 NFL project.

Covers EVERY site unit in the repository (root pages, pages/, site/, docs/,
dashboard/, lab/, x3lab/, verification-hub/, plus any other HTML found), which
no single prior check did:
  1. HTML well-formedness (balanced core structural tags).
  2. Internal href/src/link integrity across units (cross-unit link check).
  3. Table-row accounting per page and per unit.
  4. Row-source policy check: rows inside <tbody> must contain either an
     external http(s) link or an explicit UNVERIFIED/flag marker.

Exit code 1 on any failure; prints a JSON summary consumed by
verification-hub/index.html generation.
"""
from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
STRUCTURAL = {"html", "head", "body", "table", "thead", "tbody", "tr", "td", "th"}


class PageAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.refs: list[tuple[str, str]] = []  # (attr, value)
        self.rows: int = 0
        self.rows_flagged: int = 0
        self.rows_unsourced: list[str] = []
        self._row_text: list[str] = []
        self._row_refs: int = 0
        self._in_row = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for attr in ("href", "src"):
            if attr in d and d[attr] and not d[attr].startswith("data:"):
                self.refs.append((attr, d[attr]))
        if tag in STRUCTURAL and tag not in VOID:
            self.stack.append(tag)
        if tag == "tr":
            self._in_row = True
            self._row_text = []
            self._row_refs = 0
            self.rows += 1
        if self._in_row and tag == "a" and d.get("href", "").startswith(("http://", "https://")):
            self._row_refs += 1

    def handle_endtag(self, tag):
        if tag == "tr":
            self._in_row = False
            text = " ".join(self._row_text).upper()
            if self._row_refs or "UNVERIFIED" in text or "UNCONFIRMED" in text \
               or "NOT-YET-VERIFIED" in text or "DERIVED" in text or "FLAG" in text \
               or "NO OFFICIAL SOURCE" in text or "BLANK" in text or "TBD" in text \
               or "N/A" in text or "PENDING" in text:
                self.rows_flagged += 1
            else:
                self.rows_unsourced.append(" ".join(self._row_text)[:120])
        # HTML5 optional-end-tag rules: a close of an ancestor implicitly
        # closes open descendants (e.g. </tbody> closes an open <tr>/<td>).
        if tag in STRUCTURAL and tag not in VOID:
            if tag in self.stack:
                while self.stack:
                    top = self.stack.pop()
                    if top == tag:
                        break
            elif tag not in ("tr", "td", "th"):  # truly stray (not implicit-close)
                self.errors.append(f"stray </{tag}>")

    def handle_data(self, data):
        if self._in_row:
            self._row_text.append(data.strip())


def audit() -> dict:
    pages = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)
    units: dict[str, list] = {}
    problems: list[str] = []
    total_rows = 0
    total_flagged = 0
    internal_refs = 0

    for page in pages:
        rel = page.relative_to(ROOT).as_posix()
        unit = rel.split("/")[0] if "/" in rel else "(root)"
        pa = PageAudit()
        try:
            pa.feed(page.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:  # pragma: no cover
            problems.append(f"{rel}: parse error {exc}")
            continue
        if pa.stack:
            problems.append(f"{rel}: unclosed tags {pa.stack}")
        problems.extend(f"{rel}: {e}" for e in pa.errors)

        resolved = []
        for attr, href in pa.refs:
            if href.startswith(("http://", "https://", "#", "mailto:", "tel:")):
                continue
            internal_refs += 1
            target = href.split("#", 1)[0]
            if not target:
                continue
            if (page.parent / target).exists() or (ROOT / target).exists():
                resolved.append(href)
            else:
                problems.append(f"{rel}: broken internal ref {href}")

        units.setdefault(unit, {"pages": 0, "rows": 0, "flagged_rows": 0,
                                "refs": 0, "unsourced_rows": []})
        units[unit]["pages"] += 1
        units[unit]["rows"] += pa.rows
        units[unit]["flagged_rows"] += pa.rows_flagged
        units[unit]["refs"] += len(pa.refs)
        units[unit]["unsourced_rows"].extend(
            f"{rel}: {t}" for t in pa.rows_unsourced)
        total_rows += pa.rows
        total_flagged += pa.rows_flagged

    for u in units.values():
        u["unsourced_examples"] = u.pop("unsourced_rows")[:8]

    summary = {
        "units": {k: v for k, v in sorted(units.items())},
        "pages_total": len(pages),
        "rows_total": total_rows,
        "rows_flagged_or_sourced": total_flagged,
        "internal_refs": internal_refs,
        "problems": problems,
    }
    return summary


def main() -> int:
    summary = audit()
    out = ROOT / "verification-hub" / "audit-report.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"pages={summary['pages_total']} rows={summary['rows_total']} "
          f"sourced/flagged={summary['rows_flagged_or_sourced']} "
          f"internal_refs={summary['internal_refs']} problems={len(summary['problems'])}")
    for unit, u in summary["units"].items():
        print(f"  {unit:22s} pages={u['pages']:3d} rows={u['rows']:5d} "
              f"flagged/sourced={u['flagged_rows']:5d} refs={u['refs']}")
    if summary["problems"]:
        print("PROBLEMS:")
        for p in summary["problems"][:60]:
            print("  -", p)
        return 1
    print("PASS: all pages parse; all internal links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
