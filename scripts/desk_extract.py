#!/usr/bin/env python3
"""Turn captured official NFL pages into reviewable text + link maps.

Input : capture/                     raw HTML captured by the CI workflow
Output: data/desk/text/<page>.txt     rendered page text (tabs keep table cells)
        data/desk/text/<page>.links   "anchor text \t href" for nfl.com game/player links
        data/desk/extract_report.json structure diagnostics per page

Why text and not HTML: the authoring sandbox cannot reach the artifact download host,
so the CI job commits this reduced form. Nothing is inferred here; these files are a
faithful reduction of the captured page, and every downstream parser cites the page URL.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

CAPTURE_URLS = {
    "standings-2026.html": "https://www.nfl.com/standings/league/2026/reg",
    "team-stats.html": "https://www.nfl.com/stats/team-stats/",
}
for _w in range(1, 12):
    CAPTURE_URLS[f"schedule-w{_w}.html"] = f"https://www.nfl.com/schedules/2026/by-week/week-{_w}"
for _w in range(8, 12):
    CAPTURE_URLS[f"injuries-w{_w}.html"] = f"https://www.nfl.com/injuries/league/2026/reg{_w}"

SCRIPT_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.S | re.I)
ANCHOR_RE = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
WS_RE = re.compile(r"[ \t\r\f\v]+")
TAG_RE = re.compile(r"<[^>]+>")


def links_of(raw: str) -> str:
    out = []
    for href, inner in ANCHOR_RE.findall(SCRIPT_RE.sub(" ", raw)):
        txt = WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", inner))).strip()
        if re.search(r"nfl\.com/(games|players)/", href) or "/team/depth-chart" in href:
            out.append(f"{txt}\t{href}")
    return "\n".join(out) + ("\n" if out else "")


def text_of(raw: str) -> str:
    s = SCRIPT_RE.sub(" ", raw)
    s = re.sub(r"</t[dh]>", "\t", s, flags=re.I)
    s = re.sub(r"</tr>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h[1-6]|table|section|article)>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", s, flags=re.S | re.I)
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s).replace("\u00a0", " ")
    lines = []
    for line in s.splitlines():
        line = WS_RE.sub(" ", line).strip()
        line = re.sub(r"\t+", "\t", line).strip("\t")
        if line:
            lines.append(line)
    return "\n".join(lines) + "\n"


def main(src: str, dst: str) -> int:
    cap, out = Path(src), Path(dst)
    textdir = out / "text"
    textdir.mkdir(parents=True, exist_ok=True)
    report = {"pages": {}, "notes": []}
    for f in sorted(cap.rglob("*.html")):
        rel = f.relative_to(cap)
        raw = f.read_text(errors="replace")
        txt = text_of(raw)
        stem = "__".join(rel.with_suffix("").parts)
        (textdir / (stem + ".txt")).write_text(txt)
        (textdir / (stem + ".links")).write_text(links_of(raw))
        lines = txt.splitlines()
        report["pages"][stem] = {
            "url": CAPTURE_URLS.get(f.name, "") or ("https://www.nfl.com/games/" + f.stem.replace("-2026-reg-", "-2026-reg-")),
            "html_bytes": len(raw),
            "text_bytes": len(txt),
            "lines": len(lines),
            "tabbed_cell_lines": sum(1 for ln in lines if ln.count("\t") >= 2),
        }
    (out / "extract_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["pages"], indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
