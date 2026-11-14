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

    # Structural fingerprints: which element chains carry the game links, and
    # which class names dominate. This is what a parser for an unfamiliar
    # component needs, and it is far smaller than the raw payload.
    from collections import Counter

    classes = Counter()
    for el in soup.find_all(True):
        for c in el.get("class") or []:
            classes[c] += 1
    out["top_classes"] = [c for c, _ in classes.most_common(30)]

    # A compact, representative sample of the game cards, so a parser can be
    # written or repaired from the repository alone. The full page is
    # megabytes long; two cards are enough to see the structure.
    # One card per distinct game URL. The page shows the same games several
    # times (a score strip, a mobile strip and the week's own list), so the
    # first card for each URL is kept, which reaches the week's own list.
    cards: list[str] = []
    seen_hrefs: set[str] = set()
    for a in soup.find_all("a", href=True):
        if "/games/" not in a["href"]:
            continue
        if a["href"] in seen_hrefs:
            continue
        node = a
        for _ in range(8):
            node = node.parent
            if node is None:
                break
            if node.name in ("li", "article", "section", "div"):
                seen_hrefs.add(a["href"])
                cards.append(str(node))
                break
        if len(cards) >= 40:
            break
    if cards:
        out["game_card_sample"] = cards

    # The weekly list of games is rendered on the client, so the data it uses
    # is embedded in the page as a JSON payload. Locate that payload so a
    # parser can be written against it.
    payloads: list[dict] = []
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is not None:
        payloads.append(
            {
                "kind": "__NEXT_DATA__",
                "bytes": len(next_data.string or ""),
                "sample": (next_data.string or "")[:1500],
            }
        )
    pushes = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        if "self.__next_f.push" in text:
            pushes.append(text)
    if pushes:
        combined = "".join(pushes)
        payloads.append(
            {
                "kind": "next_f_push",
                "scripts": len(pushes),
                "bytes": len(combined),
                "sample": combined[:2500],
            }
        )
    if payloads:
        out["data_payloads"] = payloads

    # Any element carrying game data in an attribute.
    for element in soup.find_all(True):
        for attr, value in (element.attrs or {}).items():
            if attr.startswith("data-") and isinstance(value, str) and len(value) > 200:
                out.setdefault("data_attributes", []).append(
                    {"tag": element.name, "attr": attr, "bytes": len(value), "sample": value[:400]}
                )
                break
        if len(out.get("data_attributes", [])) >= 3:
            break

    chains = []
    for a in soup.find_all("a", href=True):
        if "/games/" not in a["href"]:
            continue
        chain = []
        node = a
        for _ in range(6):
            node = node.parent
            if node is None or getattr(node, "name", None) in (None, "[document]"):
                break
            chain.append(f"{node.name}.{'.'.join(node.get('class') or []) or '-'}")
        chains.append({"href": a["href"], "chain": chain})
        if len(chains) >= 3:
            break
    out["game_link_chains"] = chains
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
