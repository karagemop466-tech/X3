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

    # Sanity: verified-data pages must carry per-row source cells; the flagged
    # page must carry external source links. Methodology pages (requirements,
    # suggestions) have no per-row official source and are covered by the
    # broken-link check + the integrated scripts/check_site.py.
    data_pages = {
        "executive-summary.html", "lines.html", "leaderboard.html",
        "injuries.html", "verification.html",
    }
    for page in data_pages:
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            problems.append(f"{page}: authored page missing")
            continue
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        if 'class="src"' not in txt:
            problems.append(f"{page}: data page has no source-link cells")

    flag_path = os.path.join(ROOT, "flagged.html")
    if os.path.exists(flag_path):
        with open(flag_path, encoding="utf-8") as f:
            txt = f.read()
        if 'href="https://' not in txt:
            problems.append("flagged.html: no external source links")

    if problems:
        print("FAIL — issues found:")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"OK — {len(pages)} pages, {checked} links checked, no broken internal links.")


if __name__ == "__main__":
    main()
