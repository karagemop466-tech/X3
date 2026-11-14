#!/usr/bin/env python3
"""Check local HTML links and static assets without network access."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import sys

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = [ROOT / "index.html", *sorted((ROOT / "lab").glob("*.html"))]
EXPECTED_PAGES = [
    "executive-summary", "strategies", "validation", "lineups", "correlations",
    "leaderboard", "questions", "suggestions", "flagged", "sources",
]


class AuditParser(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.local_links: list[str] = []
        self.has_lang = False
        self.has_title = False

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "html" and attr.get("lang"):
            self.has_lang = True
        if tag == "title":
            self.has_title = True
        for key in ("href", "src"):
            value = attr.get(key)
            if not value:
                continue
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith(("#", "data:")):
                continue
            self.local_links.append(parsed.path or "")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


errors = []
for html_file in HTML_FILES:
    parser = AuditParser(html_file)
    parser.feed(html_file.read_text(encoding="utf-8"))
    if not parser.has_lang:
        errors.append(f"{html_file.relative_to(ROOT)}: missing html lang attribute")
    for raw in parser.local_links:
        if not raw:
            continue
        target = (html_file.parent / raw).resolve()
        if raw.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            errors.append(f"{html_file.relative_to(ROOT)}: missing local target {raw}")

for slug in ["index", *EXPECTED_PAGES]:
    page = ROOT / "lab" / f"{slug}.html"
    if not page.exists():
        errors.append(f"missing expected page: lab/{slug}.html")

if errors:
    print("Static-site link audit FAILED:")
    for error in errors:
        print(f" - {error}")
    sys.exit(1)

print(f"Static-site link audit passed: {len(HTML_FILES)} HTML pages; all local href/src targets exist.")
