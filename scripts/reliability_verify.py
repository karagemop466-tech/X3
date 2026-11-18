#!/usr/bin/env python3
"""Gate for the designation-reliability module.

Checks, in order:
  1. determinism — the build regenerates byte-identical CSVs and pages;
  2. completeness — every Out/Doubtful/Questionable row of the sampled teams in the
     raw report captures appears in designations.csv, and join.csv covers it;
  3. evidence — every played=1 row's matched Game Book name really appears in that
     game's stored Playtime section; every inactive=yes surname really appears in
     the stored Not Active set; unresolved/excluded rows carry a reason;
  4. arithmetic — rates.csv recomputes exactly from join.csv (independent Wilson);
  5. manifest — sha256 of every captured file matches reliability/manifest.csv;
  6. pages — nav links resolve, row counts match, every join/rate row carries an
     official source link, no placeholders.
Exit 0 = PASS.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL = ROOT / "reliability"
DATA = REL / "data"
Z = 1.959963984540054

sys.path.insert(0, str(ROOT / "scripts"))
import reliability_build as rb  # noqa: E402

problems: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def wilson(x: int, n: int) -> tuple[float, float]:
    p = x / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def check_determinism() -> None:
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(REL.rglob("*")) if p.is_file() and p.suffix in {".html", ".csv"}}
    r = subprocess.run([sys.executable, str(ROOT / "scripts/reliability_build.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        fail(f"build failed: {r.stderr.strip()[:300]}")
        return
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(REL.rglob("*")) if p.is_file() and p.suffix in {".html", ".csv"}}
    changed = [str(p.relative_to(ROOT)) for p in before if before.get(p) != after.get(p)]
    added = [str(p.relative_to(ROOT)) for p in after if p not in before]
    if changed or added:
        fail(f"build not deterministic: changed={changed} added={added}")


def check_completeness(designations: list[dict], join_rows: list[dict]) -> None:
    parsed = rb.parse_reports()
    key = lambda r: (str(r["season"]), r["game_slug"], r["team"], r["report_name"],
                     r["designation"], r["position"])
    a, b = sorted(map(key, parsed)), sorted(map(key, designations))
    if a != b:
        miss = [k for k in a if k not in set(b)]
        extra = [k for k in b if k not in set(a)]
        fail(f"designations.csv != raw reports: missing={miss[:5]} extra={extra[:5]}")
    if sorted(map(key, join_rows)) != b:
        fail("join.csv does not cover exactly the designated rows")
    if len({(r["season"], r["game_slug"], r["team"], r["report_name"]) for r in join_rows}) != len(join_rows):
        fail("join.csv has duplicate player rows")


def check_evidence(join_rows: list[dict]) -> None:
    cache: dict[str, str] = {}
    na_cache: dict[str, set[tuple[str, str]]] = {}
    for r in join_rows:
        ev = r["evidence_file"]
        if ev not in cache:
            text = (ROOT / ev).read_text(encoding="utf-8")
            cache[ev] = text
            na_cache[ev] = rb.parse_na_set(text)[0]
        text = cache[ev]
        if r["played"] == "1":
            idx = text.rfind("Playtime Percentage")
            region = text[idx:] if idx >= 0 else ""
            names = [n.strip() for n in r["gb_name_matched"].split(";") if n.strip()]
            if not names:
                fail(f"played=1 without matched name: {r['report_name']} {r['game_slug']}")
            for nm in names:
                # the matched name must literally appear in the stored playtime section
                if nm not in region:
                    fail(f"played row not corroborated by playtime section: "
                         f"{r['report_name']} ({r['game_slug']}) name={nm}")
        if r["inactive"] == "yes":
            _, sur = rb.name_key(r["report_name"])
            if not any(s == sur for _, s in na_cache[ev]):
                fail(f"inactive=yes not corroborated by Not Active set: "
                     f"{r['report_name']} ({r['game_slug']})")
            # the surname must appear as a printed dotted token in the NA region
            na_region = _na_region(text)
            tokens = re.findall(r"\b([A-Z]{1,3}\.[A-Za-z][A-Za-z.\-']*)\b", na_region)
            if not any(rb.gb_key(t)[1] == sur for t in tokens):
                fail(f"inactive surname not present as printed token: "
                     f"{r['report_name']} ({r['game_slug']})")
        if r["played"] in {"unresolved", "excluded-conflict"} and not r["played_evidence"]:
            fail(f"unresolved played without reason: {r['report_name']}")
        if r["inactive"] in {"unresolved", "excluded-rule-b"} and not r["inactive_evidence"]:
            fail(f"unresolved inactive without reason: {r['report_name']}")


def _na_region(text: str) -> str:
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if "NOT ACTIVE sets as parsed" in ln or "NA presence set" in ln:
            start = i
            break
    if start is None:
        return ""
    out = []
    for ln in lines[start:]:
        if out and (ln.startswith("## ") or "DID NOT PLAY" in ln
                    or "PARSING NOTE" in ln or "cross-check" in ln):
            break
        out.append(ln)
    return "\n".join(out)


def _surname_token(sur: str) -> str:
    """Best-effort printed surname for token search (first capitalised chunk)."""
    # stored surnames are lowercased alnum; find a dotted token in NA region ending with it
    return sur  # matched below with a looser search


def check_rates(join_rows: list[dict], rates: list[dict]) -> None:
    for r in rates:
        des, metric = r["designation"], r["metric"]
        col, keep = ("played", {"0", "1"}) if metric == "play_rate" else ("inactive", {"yes", "no"})
        sel = [x for x in join_rows if x["designation"] == des and x[col] in keep]
        x = sum(1 for v in sel if (v[col] == "1" if col == "played" else v[col] == "yes"))
        n = len(sel)
        if int(r["n"]) != n or int(r["events"]) != x:
            fail(f"rates mismatch {des}/{metric}: csv {r['events']}/{r['n']} vs {x}/{n}")
            continue
        if n:
            lo, hi = wilson(x, n)
            if round(lo, 4) != float(r["ci95_low"]) or round(hi, 4) != float(r["ci95_high"]):
                fail(f"wilson mismatch {des}/{metric}: {r['ci95_low']}..{r['ci95_high']} "
                     f"vs {lo:.4f}..{hi:.4f}")
            if round(x / n, 4) != float(r["rate"]):
                fail(f"rate mismatch {des}/{metric}: {r['rate']} vs {x / n:.4f}")


def check_manifest() -> None:
    rows = read_csv(REL / "manifest.csv")
    if not rows:
        fail("manifest.csv empty")
    for m in rows:
        p = ROOT / m["path"]
        if not p.exists():
            fail(f"manifest file missing: {m['path']}")
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != m["sha256"]:
            fail(f"sha256 mismatch: {m['path']}")
        if not m["source_url"].startswith("https://www.nfl.com") and \
           not m["source_url"].startswith("https://static.www.nfl.com"):
            fail(f"non-official source in manifest: {m['source_url']}")
    # every raw capture must be in the manifest
    on_disk = {p.relative_to(ROOT).as_posix() for p in (REL / "raw").rglob("*.md")}
    listed = {m["path"] for m in rows}
    if on_disk != listed:
        fail(f"manifest coverage: missing={sorted(on_disk - listed)} extra={sorted(listed - on_disk)}")


def check_pages(designations: list[dict], join_rows: list[dict], rates: list[dict]) -> None:
    pages = sorted(REL.glob("*.html"))
    names = {p.name for p in pages}
    for p in pages:
        html = p.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"#]+\.html)"', html):
            if href.startswith("http"):
                continue
            if href not in names:
                fail(f"{p.name}: broken nav link {href}")
        for bad in ("TODO", "TBD", "PLACEHOLDER", "XXX", "lorem"):
            if bad.lower() in html.lower():
                fail(f"{p.name}: placeholder text {bad!r}")
    join_html = (REL / "join.html").read_text(encoding="utf-8")
    rows_shown = join_html.count('<td class="num">20')  # season cells
    if rows_shown != len(join_rows):
        fail(f"join.html shows {rows_shown} rows, csv has {len(join_rows)}")
    if join_html.count('href="https://static.www.nfl.com') < len(join_rows):
        fail("join.html: not every row carries a Game Book source link")
    if join_html.count('href="https://www.nfl.com/injuries/') < len(join_rows):
        fail("join.html: not every row carries a report source link")
    rel_html = (REL / "reliability.html").read_text(encoding="utf-8")
    for r in rates:
        if r["n"]:
            pct = f'{100 * float(r["rate"]):.1f}%'
            if pct not in rel_html:
                fail(f"reliability.html missing rate {r['designation']}/{r['metric']}={pct}")
    idx = (REL / "index.html").read_text(encoding="utf-8")
    if "Flagged for Review" not in idx or "Flagged for Review" not in (REL / "flagged.html").read_text(encoding="utf-8"):
        fail("flagged page not linked/present")
    fl = (REL / "flagged.html").read_text(encoding="utf-8")
    if fl.count('class="flag"') < 15:
        fail("flagged.html has fewer than 15 flagged rows")
    # designations count surfaced on archive page
    ar = (REL / "archive.html").read_text(encoding="utf-8")
    for s in (2023, 2024, 2025):
        n = sum(1 for d in designations if int(d["season"]) == s)
        if f"<td class=\"num\">{n}</td>" not in ar:
            fail(f"archive.html missing designated count for {s} ({n})")


def main() -> int:
    check_determinism()
    designations = read_csv(DATA / "designations.csv")
    join_rows = read_csv(DATA / "join.csv")
    rates = read_csv(DATA / "rates.csv")
    if not designations or not join_rows or not rates:
        fail("empty data files")
    else:
        check_completeness(designations, join_rows)
        check_evidence(join_rows)
        check_rates(join_rows, rates)
    check_manifest()
    check_pages(designations, join_rows, rates)
    if problems:
        print(f"FAIL — {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print(f"PASS — {len(designations)} designated rows, {len(join_rows)} join rows, "
          f"{len(rates)} rate rows, manifest sealed, pages consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
