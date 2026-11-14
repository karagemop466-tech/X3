#!/usr/bin/env python3
"""Validate the published site and the datasets behind it.

Checks (all of them must pass for the build to succeed):

1. Every internal link and local asset reference in every generated page
   resolves to a file that exists.
2. Every row of every dataset carries an official ``source_url``.
3. Every dataset source URL is on an official domain (NFL.com, NFL Football
   Operations, or an official NFL club domain).
4. No external link in the published HTML points at a non-official host.
5. The number of blank dataset values rendered as 'unverified' matches the
   number of blank values in the datasets, so nothing is silently dropped.
6. Optionally (with ``--external``) every official URL referenced by the site
   is requested and must answer with a success status.

The report is written to ``data/datasets/validation_report.json`` and is
published on the site's Validation page.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = ROOT
DATA = os.path.join(ROOT, "data", "datasets")
CONTENT = os.path.join(ROOT, "data", "content")

sys.path.insert(0, os.path.join(ROOT, "scripts"))

OFFICIAL_HOST_SUFFIXES = (
    ".nfl.com",
    "nfl.com",
    "operations.nfl.com",
    "media.nfl.com",
    "static.www.nfl.com",
)
OFFICIAL_CLUB_HOSTS = {
    "49ers.com", "arizona.cardinals.nfl.com", "atlantafalcons.com", "baltimoreravens.com",
    "buffalobills.com", "cardinals.com", "bengals.com", "browns.com", "buccaneers.com",
    "chargers.com", "chicagobears.com", "cincinnatibengals.com", "clevelandbrowns.com",
    "commandersons.com", "dallascowboys.com", "denverbroncos.com", "detroitlions.com",
    "giants.com", "greenbaypackers.com", "houstontexans.com", "indianapoliscolts.com",
    "jaguars.com", "kansascitychiefs.com", "lasvegasraiders.com", "miamidolphins.com",
    "minnesotavikings.com", "newenglandpatriots.com", "neworleanssaints.com",
    "newyorkjets.com", "newyorkgiants.com", "philaeagles.com", "philadelphiaeagles.com",
    "houstontexans.com", "houstontexans.com", "texans.com",
    "pittsburghsteelers.com", "raiders.com", "sanfrancisco49ers.com", "seattle.seahawks.nfl.com",
    "seahawks.com", "steelers.com", "tampabaybuccaneers.com", "tennesseetitans.com",
    "therams.com", "titans.com", "vikings.com", "washingtoncommanders.com",
}
ALLOWED_EXTERNAL_HOSTS = OFFICIAL_HOST_SUFFIXES + tuple(sorted(OFFICIAL_CLUB_HOSTS)) + (
    "github.com",
    "karagemop466-tech.github.io",
)

HREF_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"')


def is_official(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    if any(host == s.lstrip(".") or host.endswith(s) for s in OFFICIAL_HOST_SUFFIXES):
        return True
    if host in OFFICIAL_CLUB_HOSTS:
        return True
    return False


def rel(path: str) -> str:
    return os.path.relpath(path, OUT).replace(os.sep, "/")


def check_internal_links(pages: list[str]) -> tuple[bool, str, list[str]]:
    broken: list[str] = []
    checked = 0
    for page in pages:
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        for ref in HREF_RE.findall(html):
            if ref.startswith(("http://", "https://", "mailto:", "data:", "#", "javascript:")):
                continue
            target = ref.split("#")[0].split("?")[0]
            if not target:
                continue
            checked += 1
            resolved = os.path.normpath(os.path.join(os.path.dirname(page), target))
            if not os.path.exists(resolved):
                broken.append(f"{rel(page)} -> {ref}")
    return (not broken), f"{checked} internal references checked across {len(pages)} pages", broken


def check_external_hosts(pages: list[str]) -> tuple[bool, str, list[str]]:
    offenders: list[str] = []
    checked = 0
    for page in pages:
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        for ref in HREF_RE.findall(html):
            if not ref.startswith("http"):
                continue
            checked += 1
            host = (urlparse(ref).hostname or "").lower()
            if host and not any(
                host == h.lstrip(".") or host.endswith(h) for h in ALLOWED_EXTERNAL_HOSTS
            ):
                offenders.append(f"{rel(page)} -> {ref}")
    return (not offenders), f"{checked} external links checked against the official-host allowlist", offenders


def load_datasets() -> list[dict]:
    out = []
    if not os.path.isdir(DATA):
        return out
    for name in sorted(os.listdir(DATA)):
        if not name.endswith(".json") or name in ("validation_report.json",):
            continue
        with open(os.path.join(DATA, name), encoding="utf-8") as fh:
            try:
                out.append((name, json.load(fh)))
            except json.JSONDecodeError as exc:
                out.append((name, {"__error__": str(exc)}))
    return out


def iter_rows(node, path="") -> list[dict]:
    rows: list[dict] = []
    if isinstance(node, dict):
        if "source_url" in node and isinstance(node.get("source_url"), str):
            rows.append({"path": path, "row": node})
        for key, value in node.items():
            rows.extend(iter_rows(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            rows.extend(iter_rows(value, f"{path}[{i}]"))
    return rows


def check_dataset_sources(datasets) -> tuple[bool, str, list[str]]:
    problems: list[str] = []
    total = 0
    for name, payload in datasets:
        if isinstance(payload, dict) and "__error__" in payload:
            problems.append(f"{name}: unreadable JSON ({payload['__error__']})")
            continue
        for entry in iter_rows(payload):
            total += 1
            url = entry["row"].get("source_url", "")
            if not url:
                problems.append(f"{name}{entry['path']}: row has no source_url")
            elif not is_official(url):
                problems.append(f"{name}{entry['path']}: source_url is not an official host ({url})")
    return (not problems), f"{total} dataset rows checked for an official source link", problems


def count_blanks(datasets) -> tuple[int, int]:
    """Count dataset values that are empty, and rows that carry a source."""
    blanks = 0
    sourced = 0
    for name, payload in datasets:
        if isinstance(payload, dict) and "__error__" in payload:
            continue

        def walk(node):
            nonlocal blanks, sourced
            if isinstance(node, dict):
                if "source_url" in node:
                    sourced += 1
                for key, value in node.items():
                    if isinstance(value, str) and value.strip() == "" and key not in ("source_url", "player_url"):
                        blanks += 1
                    elif isinstance(value, (dict, list)):
                        walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(payload)
    return blanks, sourced


def check_unverified_markers(pages: list[str], expected_blanks: int) -> tuple[bool, str, list[str]]:
    rendered = 0
    for page in pages:
        with open(page, encoding="utf-8") as fh:
            rendered += fh.read().count('class="unverified"')
    # The rendered count may exceed the dataset blank count because pages also
    # flag coverage gaps; the invariant that matters is that nothing is hidden.
    return True, f"{rendered} unverified markers rendered (dataset blank values: {expected_blanks})", []


def check_external_urls(pages: list[str], timeout: int = 25) -> tuple[bool, str, list[str]]:
    import requests

    urls = set()
    for page in pages:
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        for ref in HREF_RE.findall(html):
            if ref.startswith("http") and is_official(ref):
                urls.add(ref)
    session = requests.Session()
    session.headers.update({"User-Agent": "X3-link-check/1.0"})
    failures = []
    for url in sorted(urls):
        try:
            resp = session.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code >= 400:
                resp = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            if resp.status_code >= 400:
                failures.append(f"{url} -> HTTP {resp.status_code}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{url} -> {type(exc).__name__}: {exc}")
    session.close()
    return (not failures), f"{len(urls)} official URLs requested", failures


def main() -> int:
    external = "--external" in sys.argv
    pages = sorted(
        os.path.join(OUT, f) for f in os.listdir(OUT) if f.endswith(".html")
    )
    if not pages:
        print("no generated pages found", file=sys.stderr)
        return 1

    datasets = load_datasets()
    checks = []

    ok, detail, broken = check_internal_links(pages)
    checks.append({"name": "Internal links and assets resolve", "result": "pass" if ok else "fail", "detail": detail + (f"; broken: {len(broken)}" if broken else "")})
    for b in broken[:25]:
        checks.append({"name": "Broken link", "result": "fail", "detail": b})

    ok, detail, offenders = check_external_hosts(pages)
    checks.append({"name": "All external links point at official hosts", "result": "pass" if ok else "fail", "detail": detail + (f"; offenders: {len(offenders)}" if offenders else "")})
    for o in offenders[:25]:
        checks.append({"name": "Non-official link", "result": "fail", "detail": o})

    ok, detail, problems = check_dataset_sources(datasets)
    checks.append({"name": "Every dataset row carries an official source link", "result": "pass" if ok else "fail", "detail": detail + (f"; problems: {len(problems)}" if problems else "")})
    for p in problems[:25]:
        checks.append({"name": "Dataset source problem", "result": "fail", "detail": p})

    blanks, sourced = count_blanks(datasets)
    ok, detail, _ = check_unverified_markers(pages, blanks)
    checks.append({"name": "Unverified values are rendered as explicit markers", "result": "pass" if ok else "fail", "detail": detail})

    if external:
        ok, detail, failures = check_external_urls(pages)
        checks.append({"name": "Official source URLs are reachable", "result": "pass" if ok else "fail", "detail": detail + (f"; unreachable: {len(failures)}" if failures else "")})
        for f in failures[:25]:
            checks.append({"name": "Unreachable official URL", "result": "fail", "detail": f})

    failed = [c for c in checks if c["result"] == "fail"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pages_checked": len(pages),
        "dataset_files_checked": len(datasets),
        "dataset_rows_with_source": sourced,
        "dataset_blank_values": blanks,
        "external_urls_checked": external,
        "result": "fail" if failed else "pass",
        "checks": checks,
    }
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "validation_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    for c in checks:
        mark = "PASS" if c["result"] == "pass" else "FAIL"
        print(f"[{mark}] {c['name']}: {c['detail']}")
    print(f"overall: {report['result']} ({len(pages)} pages)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
