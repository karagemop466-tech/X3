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

from lib.diagnostics import describe_html, failure_report, write_report
from lib.official import CLUBS, resolve_payload
from lib.parsers import (
    normalise_depth_groups,
    parse_depth_chart,
    parse_injuries,
    parse_player_stats,
    parse_schedule,
    parse_standings,
    resolve_depth_string,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INJURY_PAGE = "https://www.nfl.com/injuries/"
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
    """Locate the cached payload for a fetch record."""
    return resolve_payload(record, RAW)


def write_json(name: str, payload) -> str:
    path = os.path.join(OUT, name)
    os.makedirs(OUT, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


OFFENCE_POSITIONS = {"QB", "RB", "FB", "WR", "TE", "OL", "C", "G", "T", "RB/FB"}


def _unit_for_position(position: str) -> str:
    """Classify a position as offence or defence.

    A position the platform does not recognise is reported as "unknown"
    rather than being assigned to a unit by inference.
    """
    pos = (position or "").strip().upper()
    if pos in OFFENCE_POSITIONS:
        return "offence"
    if pos in {"DL", "DE", "DT", "NT", "LB", "OLB", "ILB", "CB", "S", "SS", "FS"}:
        return "defence"
    if pos in {"K", "P", "LS", "RS"}:
        return "special teams"
    return "unknown"


def main() -> int:
    """Entry point: runs the build and always leaves a diagnostic report."""
    try:
        return _build()
    except Exception as exc:  # noqa: BLE001 - reported, then re-raised
        failure_report("build_datasets", exc)
        raise


def _build() -> int:
    manifest = load_manifest()
    records = manifest["records"]
    datasets: list[dict] = []
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    structure: dict = {}

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
    injuries: dict | None = None
    for rec in records:
        if rec["key"] != "injuries_current":
            continue
        path = raw_path(rec)
        if not path:
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            parsed = parse_injuries(fh.read(), rec["url"])
        injuries = parsed
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

    # ------------------------------------------------------- injury archive
    for season in (2023, 2024, 2025, 2026):
        weeks: list[dict] = []
        used: list[dict] = []
        for rec in records:
            if not rec["key"].startswith(f"injuries_{season}_w"):
                continue
            path = raw_path(rec)
            if not path:
                continue
            week = int(rec["key"].rsplit("_w", 1)[-1])
            with open(path, encoding="utf-8", errors="replace") as fh:
                parsed = parse_injuries(fh.read(), rec["url"])
            if not parsed["rows"]:
                continue
            weeks.append({"week": week, "source_url": rec["url"], "rows": parsed["rows"], "games": parsed["games"]})
            used.append(rec)
        if weeks:
            weeks.sort(key=lambda w: w["week"])
            write_json(
                f"injuries_history_{season}.json",
                {"season": season, "weeks": weeks, "source_url": f"https://www.nfl.com/injuries/league/{season}/reg<week>"},
            )
            datasets.append(
                {
                    "dataset": f"injuries_history_{season}.json",
                    "source_key": f"injuries_{season}_w01..w18",
                    "source_url": f"https://www.nfl.com/injuries/league/{season}/reg<week>",
                    "official_org": "National Football League",
                    "sha256": [u["sha256"] for u in used][:8],
                    "fetched_at": [u["fetched_at"] for u in used][:8],
                    "rows": sum(len(w["rows"]) for w in weeks),
                }
            )

    # ----------------------------------------------------------- depth charts
    depth: dict[str, dict] = {}
    rejected: list[dict] = []
    for rec in records:
        if rec["category"] != "depth_chart":
            continue
        path = raw_path(rec)
        if not path:
            continue
        club = rec["official_org"]
        if club in depth:
            # One official chart per club: the first URL that really contains a
            # depth chart wins, so a club's application shell cannot be counted.
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
        parsed = parse_depth_chart(html, rec["url"], club)
        if not parsed["units"]:
            rejected.append({"club": club, "url": rec["url"], "reason": parsed.get("reason", "")})
            continue
        depth[club] = {
            "club": club,
            "sources": [{"url": rec["url"], "sha256": rec["sha256"], "fetched_at": rec["fetched_at"]}],
            "units": parsed["units"],
            "groups": normalise_depth_groups(parsed["units"]),
        }
    if depth or rejected:
        write_json(
            "depth_charts.json",
            {
                "clubs": list(depth.values()),
                "rejected_candidates": rejected,
                "coverage": {
                    "clubs_resolved": len(depth),
                    "clubs_total": 32,
                    "clubs_unresolved": 32 - len(depth),
                },
            },
        )
        datasets.append(
            {
                "dataset": "depth_charts.json",
                "source_key": "club_depth_*",
                "source_url": "https://www.nfl.com/teams/",
                "official_org": "Official NFL club sites",
                "sha256": [s["sha256"] for c in depth.values() for s in c["sources"]][:8],
                "fetched_at": [s["fetched_at"] for c in depth.values() for s in c["sources"]][:8],
                "rows": sum(len(c["units"]) for c in depth.values()),
            }
        )

    # ------------------------------------------------- depth-string resolution
    # Resolve, for every player the official report lists as unavailable, the
    # depth string of the replacement that is now expected to start. The
    # string comes only from an official club depth chart. Where the club
    # publishes no chart that could be parsed, the cell is left empty.
    resolved: list[dict] = []
    unresolved: list[dict] = []
    if injuries and depth:
        # Map the official NFL team abbreviation used on the injury report to
        # the club whose official depth chart was retrieved.
        club_by_abbr: dict[str, dict] = {}
        for slug, _domain, name, abbr in CLUBS:
            for club_entry in depth.values():
                if club_entry["club"] == name:
                    club_by_abbr[abbr] = club_entry
                    break
        for row in injuries.get("rows", []):
            if row.get("game_status") not in ("Out", "Doubtful", "Questionable"):
                continue
            team = row.get("team", "")
            club_entry = club_by_abbr.get(team.upper())
            depth_string = ""
            if club_entry:
                depth_string = resolve_depth_string(
                    club_entry.get("groups", []), row.get("player", ""), row.get("position", "")
                )
            record = {
                "week": injuries.get("week"),
                "game_date": row.get("game_date", ""),
                "away_team": row.get("away_team", ""),
                "home_team": row.get("home_team", ""),
                "team": team,
                "player": row.get("player", ""),
                "player_url": row.get("player_url", ""),
                "position": row.get("position", ""),
                "game_status": row.get("game_status", ""),
                "practice_status": row.get("practice_status", ""),
                "depth_string": depth_string,
                "unit": _unit_for_position(row.get("position", "")),
                "depth_source_url": (
                    club_entry["sources"][0]["url"] if club_entry and club_entry.get("sources") else ""
                ),
                "source_url": row.get("source_url", ""),
            }
            if depth_string:
                resolved.append(record)
            else:
                unresolved.append(record)
    if resolved or unresolved:
        write_json(
            "depth_resolution.json",
            {
                "resolved": resolved,
                "unresolved": unresolved,
                "coverage": {
                    "absences_total": len(resolved) + len(unresolved),
                    "absences_resolved": len(resolved),
                    "absences_unresolved": len(unresolved),
                },
                "policy": "A depth string is published only when an official club depth chart resolves it. "
                "Otherwise the cell is blank and the absence is listed on the Flagged for Review page.",
            },
        )
        datasets.append(
            {
                "dataset": "depth_resolution.json",
                "source_key": "injuries_current + club_depth_*",
                "source_url": INJURY_PAGE,
                "official_org": "National Football League and official NFL club sites",
                "sha256": None,
                "fetched_at": None,
                "rows": len(resolved) + len(unresolved),
            }
        )

    # --------------------------------------------------------------- manifest
    summary = {
        "generated_at": built_at,
        "datasets": sorted(datasets, key=lambda d: d["dataset"]),
    }
    write_json("manifest.json", summary)

    # ------------------------------------------------------------ diagnostics
    # A structural summary of the official payloads, so a parser can be written
    # or repaired from the repository alone.
    # The samples that matter most for parser repair come first, so the
    # report is not crowded out by the club depth charts.
    priority = [
        "schedule_2026_w01", "schedule_2026_w05", "schedule_2026_w10",
        "injuries_current", "injuries_2026_w05",
        "standings_league_2026", "standings_division_2026",
        "stats_player_passing_2026", "stats_player_receiving_2026",
        "club_depth_atlanta-falcons_team_depth-chart",
    ]
    by_key = {r["key"]: r for r in records}
    for key in priority:
        rec = by_key.get(key)
        if not rec:
            continue
        path = raw_path(rec)
        if not path:
            continue
        structure[key] = describe_html(path)
    for rec in records:
        if len(structure) > 24:
            break
        path = raw_path(rec)
        if not path or rec["key"] in structure:
            continue
        if rec["category"] in ("schedule", "injuries", "injuries_history", "standings", "player_stats"):
            structure[rec["key"]] = describe_html(path)
    write_report("structure_report.json", {"sources": structure})

    # A readable sample of the official schedule markup, committed so that a
    # parser for it can be written or repaired without a network fetch.
    for key, payload in structure.items():
        sample = payload.get("game_card_sample")
        if not sample:
            continue
        name = "schedule_sample.html" if key.startswith("schedule_") else f"sample_{key}.html"
        with open(os.path.join(OUT, "logs", name), "w", encoding="utf-8") as fh:
            fh.write("\n<!-- ---- next game card ---- -->\n".join(sample))

    write_report("build_report.json", {"built_at": built_at, "datasets": len(datasets), "ok": True})

    print(f"built {len(datasets)} datasets -> {OUT}")
    for d in summary["datasets"]:
        print(f"  {d['dataset']:<44} rows={d['rows']:<6} src={d['source_url'][:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
