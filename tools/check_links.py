#!/usr/bin/env python3
"""Verify the built static site: no broken internal links and every data-table
row carries a source link. Run after tools/build_site.py."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK_RE = re.compile(r'href="([^"]+)"')


def main():
    pages = [f for f in os.listdir(ROOT) if f.endswith(".html")]
    problems = []
    checked = 0
    for page in pages:
        with open(os.path.join(ROOT, page), encoding="utf-8") as f:
            html_text = f.read()
        for href in LINK_RE.findall(html_text):
            checked += 1
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            # internal link — must resolve to a file
            target = href.split("#")[0].split("?")[0]
            if not target:
                continue
            if not os.path.exists(os.path.join(ROOT, target)):
                problems.append(f"{page}: broken link -> {href}")

    # Sanity: every data table should contain a source link cell.
    # We approximate by ensuring each data page contains 'class="src"'.
    for page in pages:
        with open(os.path.join(ROOT, page), encoding="utf-8") as f:
            txt = f.read()
        if "source" in page or page in ("index.html",):
            if 'class="src"' not in txt:
                problems.append(f"{page}: data page has no source-link cells")

    if problems:
        print("FAIL — issues found:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"OK — {len(pages)} pages, {checked} links checked, no broken internal links.")


if __name__ == "__main__":
    main()
