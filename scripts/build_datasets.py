#!/usr/bin/env python3
"""Turn the raw official-source cache into verified, source-linked datasets.

Input : data/raw/*.html            (populated by scripts/fetch_official.py)
        data/datasets/fetch_manifest.json (provenance for every payload)
Output: data/datasets/*.json        (committed; every row keeps its source_url)
        data/datasets/manifest.json (dataset -> source -> sha256 provenance)

Nothing is inferred. If a source failed to download, its dataset is simply
absent and the site reports it as missing rather than guessing.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.parsers import (
    parse_depth_chart,
    parse_injuries,
    parse_player_stats,
    parse_schedule,
    parse_standings,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "datasets")


def load_manifest() -> dict:
    path = os.path.join(OUT, "fetch_manifest.json")
    if not os.path.exists(path):
        raise SystemExit(
            "fetch_manifest.json missing — run scripts/fetch_official.py first."
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def raw_path(record: dict) -> str | None:
    if not record.get("ok") or not record.get("content_path"):
        return None
    return os.path.join(ROOT, record["content_path"])


def write_json(name: str, payload) -> str:
    path = os.path.join(OUT, name)
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def main() -> int:
    manifest = load_manifest()
    records = manifest["records"]
    datasets: list[dict] = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def note(name: str, rec: dict, rows: int, extra: dict | None = None) -> None:
        entry = {
            "dataset": name,
            "source_key": rec["key"],
            "source_url": rec["url"],
            "official_org": rec["official_org"],
            "sha256": rec["sha256"],
            "fetched_at": rec["fetched_at"],
            "rows": rows,
        }
        if extra:
            entry.update(extra)
        datasets.append(entry)

    # ---------------------------------------------------------------- injuries
    for rec in records:
        if rec["key"] != "injuries_current":
            continue
        path = raw_path(rec)
        if not path:
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            parsed = parse_injuries(fh.read(), rec["url"])
        write_json("injuries.json", parsed)
        note("injuries.json", rec, len(parsed["rows"]), {"week": parsed["week"]})

    # --------------------------------------------------------------- standings
    for rec in records:
        if not rec["key"].startswith("standings_league_"):
            continue
        path = raw_path(rec)
        if not path:
            continue
        season = int(rec["key"].rsplit("_", 1)[-1])
        with open(path, encoding="utf-8", errors="replace") as fh:
            rows = parse_standings(fh.read(), rec["url"], season)
        write_json(f"standings_{season}.json", {"season": season, "rows": rows, "source_url": rec["url"]})
        note(f"standings_{season}.json", rec, len(rows))

    # ---------------------------------------------------------------- schedule
    for season in (2023, 2024, 2025, 2026):
        games: list[dict] = []
        used: list[dict] = []
        for rec in records:
            if not rec["key"].startswith(f"schedule_{season}_w"):
                continue
            path = raw_path(rec)
            if not path:
                continue
            week = int(rec["key"].rsplit("_w", 1)[-1])
            with open(path, encoding="utf-8", errors="replace") as fh:
                parsed = parse_schedule(fh.read(), rec["url"], season, week)
            if not parsed["games"]:
                continue
            games.extend(parsed["games"])
            used.append(rec)
        if games:
            payload = {"season": season, "games": games, "source_urls": sorted({g["source_url"] for g in games})}
            write_json(f"schedule_{season}.json", payload)
            datasets.append(
                {
                    "dataset": f"schedule_{season}.json",
                    "source_key": f"schedule_{season}_w01..w18",
                    "source_url": f"https://www.nfl.com/schedules/{season}/",
                    "official_org": "National Football League",
                    "sha256": [u["sha256"] for u in used][:8],
                    "fetched_at": [u["fetched_at"] for u in used][:8],
                    "rows": len(games),
                }
            )

    # ----------------------------------------------------------- player stats
    for rec in records:
        if not rec["key"].startswith("stats_player_"):
            continue
        path = raw_path(rec)
        if not path:
            continue
        parts = rec["key"].split("_")  # stats_player_<category...>_<season>
        season = int(parts[-1])
        category = "_".join(parts[2:-1])
        with open(path, encoding="utf-8", errors="replace") as fh:
            parsed = parse_player_stats(fh.read(), rec["url"], category, season)
        if not parsed["rows"]:
            continue
        name = f"player_stats_{category.replace('-', '_')}_{season}.json"
        write_json(name, parsed)
        note(name, rec, len(parsed["rows"]))

    # ----------------------------------------------------------- depth charts
    depth: dict[str, dict] = {}
    for rec in records:
        if rec["category"] != "depth_chart":
            continue
        path = raw_path(rec)
        if not path:
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        parsed = parse_depth_chart(html, rec["url"], rec["official_org"])
        if not parsed["units"]:
            continue
        club = rec["official_org"]
        depth.setdefault(club, {"club": club, "sources": [], "units": []})
        depth[club]["sources"].append({"url": rec["url"], "sha256": rec["sha256"], "fetched_at": rec["fetched_at"]})
        depth[club]["units"].extend(parsed["units"])
    if depth:
        write_json("depth_charts.json", {"clubs": list(depth.values())})
        datasets.append(
            {
                "dataset": "depth_charts.json",
                "source_key": "club_depth_*",
                "source_url": "https://www.<club>.com/ (official club sites)",
                "official_org": "Official NFL club sites",
                "sha256": [s["sha256"] for c in depth.values() for s in c["sources"]][:8],
                "fetched_at": [s["fetched_at"] for c in depth.values() for s in c["sources"]][:8],
                "rows": sum(len(c["units"]) for c in depth.values()),
            }
        )

    # --------------------------------------------------------------- manifest
    summary = {
        "generated_at": built_at,
        "datasets": sorted(datasets, key=lambda d: d["dataset"]),
    }
    write_json("manifest.json", summary)
    print(f"built {len(datasets)} datasets -> {OUT}")
    for d in summary["datasets"]:
        print(f"  {d['dataset']:<44} rows={d['rows']:<6} src={d['source_url'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
