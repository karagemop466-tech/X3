"""Diagnostics for the dataset build.

The build runs inside GitHub Actions, whose log and artifact endpoints are not
reachable from every environment. To keep the build debuggable, each script
writes a machine-readable report into ``data/datasets/`` and the workflow
commits it even when a step fails.

The report contains:

* the failing step and its traceback, when something raised;
* a structural summary of the official payloads that were parsed, so a
  parser can be written or repaired without eyeballing raw HTML.
"""

from __future__ import annotations

import json
import os
import traceback
from datetime import datetime, timezone

from bs4 import BeautifulSoup

REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "datasets")


def describe_html(path: str, max_tables: int = 3, max_cells: int = 12) -> dict:
    """Summarise the structure of an HTML payload without dumping it."""
    out: dict = {"file": os.path.basename(path), "tables": []}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
    except OSError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    out["bytes"] = len(html)
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    title = soup.find("title")
    out["title"] = title.get_text(" ", strip=True) if title else ""
    h1 = soup.find("h1")
    out["h1"] = h1.get_text(" ", strip=True) if h1 else ""
    for table in soup.find_all("table")[:max_tables]:
        headers = [th.get_text(" ", strip=True) for th in table.select("thead th")]
        rows = table.select("tbody tr")[:2]
        body = []
        for tr in rows:
            body.append([td.get_text(" ", strip=True)[:60] for td in tr.find_all(["td", "th"])][:max_cells])
        out["tables"].append({"headers": headers, "rows": body, "n_rows": len(table.select("tbody tr"))})
    # A short text excerpt helps identify unfamiliar markup.
    text = soup.get_text(" ", strip=True)
    out["text_sample"] = text[:600]
    return out


def write_report(name: str, payload: dict) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, name)
    payload = dict(payload)
    payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def failure_report(step: str, exc: BaseException, extra: dict | None = None) -> str:
    payload = {
        "step": step,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": traceback.format_exc().splitlines()[-25:],
    }
    if extra:
        payload.update(extra)
    return write_report("build_errors.json", payload)
