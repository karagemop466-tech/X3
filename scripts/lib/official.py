"""Official-source registry and fetcher for the X3 NFL decision-support platform.

Design rules enforced here:

* Every datum this project publishes must be traceable to an **official** URL
  (NFL.com, NFL Operations, or an official NFL club site). Nothing is inferred.
* Every fetch records provenance: source URL, HTTP status, byte count,
  SHA-256 of the raw payload, and the UTC fetch timestamp.
* The fetcher never fabricates. If a URL fails, the manifest records the
  failure and downstream dataset builders treat the dataset as missing rather
  than inventing values.
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import hashlib
import json
import os
import re
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Iterable

import requests

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 X3-NFL-research/1.0"
)

# --------------------------------------------------------------------------
# Source registry
# --------------------------------------------------------------------------

NFL_COM = "https://www.nfl.com"
OPS_NFL = "https://operations.nfl.com"


@dataclasses.dataclass(frozen=True)
class Source:
    """A single official document to fetch."""

    key: str
    url: str
    category: str
    description: str
    kind: str = "html"  # html | json | pdf
    official_org: str = "National Football League"
    optional: bool = False  # optional sources never fail the run


#: Official NFL club websites (club-operated, league-sanctioned domains).
CLUBS: list[tuple[str, str, str]] = [
    # slug (nfl.com/teams/<slug>), club domain, club full name
    ("buffalo-bills", "buffalobills.com", "Buffalo Bills"),
    ("san-francisco-49ers", "49ers.com", "San Francisco 49ers"),
    ("chicago-bears", "chicagobears.com", "Chicago Bears"),
    ("denver-broncos", "denverbroncos.com", "Denver Broncos"),
    ("cincinnati-bengals", "bengals.com", "Cincinnati Bengals"),
    ("detroit-lions", "detroitlions.com", "Detroit Lions"),
    ("jacksonville-jaguars", "jaguars.com", "Jacksonville Jaguars"),
    ("kansas-city-chiefs", "chiefs.com", "Kansas City Chiefs"),
    ("minnesota-vikings", "vikings.com", "Minnesota Vikings"),
    ("pittsburgh-steelers", "steelers.com", "Pittsburgh Steelers"),
    ("green-bay-packers", "packers.com", "Green Bay Packers"),
    ("new-york-giants", "giants.com", "New York Giants"),
    ("cleveland-browns", "browns.com", "Cleveland Browns"),
    ("los-angeles-rams", "therams.com", "Los Angeles Rams"),
    ("new-england-patriots", "patriots.com", "New England Patriots"),
    ("seattle-seahawks", "seahawks.com", "Seattle Seahawks"),
    ("baltimore-ravens", "baltimoreravens.com", "Baltimore Ravens"),
    ("dallas-cowboys", "dallascowboys.com", "Dallas Cowboys"),
    ("las-vegas-raiders", "raiders.com", "Las Vegas Raiders"),
    ("washington-commanders", "commandersons.com", "Washington Commanders"),
    ("carolina-panthers", "panthers.com", "Carolina Panthers"),
    ("houston-texans", "texans.com", "Houston Texans"),
    ("new-orleans-saints", "neworleanssaints.com", "New Orleans Saints"),
    ("arizona-cardinals", "cardinals.com", "Arizona Cardinals"),
    ("atlanta-falcons", "atlantafalcons.com", "Atlanta Falcons"),
    ("miami-dolphins", "miamidolphins.com", "Miami Dolphins"),
    ("new-york-jets", "newyorkjets.com", "New York Jets"),
    ("indianapolis-colts", "colts.com", "Indianapolis Colts"),
    ("tennessee-titans", "titans.com", "Tennessee Titans"),
    ("philadelphia-eagles", "philaeagles.com", "Philadelphia Eagles"),
    ("los-angeles-chargers", "chargers.com", "Los Angeles Chargers"),
    ("tampa-bay-buccaneers", "buccaneers.com", "Tampa Bay Buccaneers"),
]

#: Club depth-chart URL candidates, probed in order until one resolves.
DEPTH_CHART_CANDIDATES = (
    "/team/depth-chart",
    "/team/depth-chart/offense",
    "/team/depth-chart/defense",
    "/team/depth-charts",
    "/depth-chart",
    "/team/roster/depth-chart",
)

#: Player-stat categories published by the NFL (verified URL pattern:
#: /stats/player-stats/category/<category>/<year>/<seasonType>/all/<metric>/desc)
STAT_CATEGORIES: list[tuple[str, str]] = [
    ("passing", "passingyards"),
    ("rushing", "rushingyards"),
    ("receiving", "receivingreceptions"),
    ("fumbles", "defensiveforcedfumble"),
    ("tackles", "defensivecombinetackles"),
    ("interceptions", "defensiveinterceptions"),
    ("field-goals", "kickingfgmade"),
    ("kickoffs", "kickofftotal"),
    ("kickoff-returns", "kickreturnsaverageyards"),
    ("punting", "puntingaverageyards"),
    ("punt-returns", "puntreturnsaverageyards"),
]

#: Seasons pulled for backtesting / correlation work.
SEASONS = (2023, 2024, 2025, 2026)
CURRENT_SEASON = 2026
WEEKS = tuple(range(1, 19))


def league_sources(seasons: Iterable[int] = SEASONS) -> list[Source]:
    """Official NFL.com league-wide sources."""
    out: list[Source] = [
        Source(
            key="injuries_current",
            url=f"{NFL_COM}/injuries/",
            category="injuries",
            description="Official latest NFL injury report (all games, all teams).",
        ),
        Source(
            key="nfl_teams_index",
            url=f"{NFL_COM}/teams/",
            category="reference",
            description="NFL.com official team index (32 clubs).",
        ),
        Source(
            key="nfl_rules_index",
            url=f"{OPS_NFL}/rules/",
            category="policy",
            description="NFL Operations — official rulebook index.",
            optional=True,
        ),
        Source(
            key="nfl_communications",
            url=f"{NFL_COM}/news/nfl-communications",
            category="policy",
            description="NFL Communications — official league statements and policy.",
            optional=True,
        ),
    ]
    for season in seasons:
        out += [
            Source(
                key=f"standings_league_{season}",
                url=f"{NFL_COM}/standings/league/{season}/REG",
                category="standings",
                description=f"{season} NFL league standings (official NFL.com).",
            ),
            Source(
                key=f"standings_division_{season}",
                url=f"{NFL_COM}/standings/division/{season}/REG",
                category="standings",
                description=f"{season} NFL division standings (official NFL.com).",
            ),
        ]
        for week in WEEKS:
            out.append(
                Source(
                    key=f"schedule_{season}_w{week:02d}",
                    url=f"{NFL_COM}/schedules/{season}/REG{week}/",
                    category="schedule",
                    description=f"{season} regular-season schedule, week {week}.",
                    optional=True,
                )
            )
        for category, metric in STAT_CATEGORIES:
            out.append(
                Source(
                    key=f"stats_player_{category}_{season}",
                    url=(
                        f"{NFL_COM}/stats/player-stats/category/{category}/{season}"
                        f"/reg/all/{metric}/desc"
                    ),
                    category="player_stats",
                    description=f"{season} player {category} statistics (official NFL.com).",
                    optional=True,
                )
            )
    return out


def club_sources() -> list[Source]:
    """Official NFL club team pages and depth-chart candidates."""
    out: list[Source] = []
    for slug, domain, name in CLUBS:
        out.append(
            Source(
                key=f"club_team_{slug}",
                url=f"{NFL_COM}/teams/{slug}/",
                category="club",
                description=f"{name} official NFL.com team page.",
                official_org=name,
            )
        )
        for candidate in DEPTH_CHART_CANDIDATES:
            out.append(
                Source(
                    key=f"club_depth_{slug}_{candidate.strip('/').replace('/', '_')}",
                    url=f"https://www.{domain}{candidate}",
                    category="depth_chart",
                    description=f"{name} official depth chart ({candidate}).",
                    official_org=name,
                    optional=True,
                )
            )
    return out


def all_sources() -> list[Source]:
    return league_sources() + club_sources()


# --------------------------------------------------------------------------
# Fetcher
# --------------------------------------------------------------------------

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return SLUG_RE.sub("_", text.lower()).strip("_")[:120]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch_one(
    source: Source,
    outdir: str,
    session: requests.Session | None = None,
    retries: int | None = None,
    timeout: int | None = None,
) -> dict:
    """Fetch one official source and persist the raw payload.

    Optional sources are given a shorter budget so that one slow club site
    cannot stall the whole pipeline.
    """
    if retries is None:
        retries = 2 if source.optional else 3
    if timeout is None:
        timeout = 25 if source.optional else 45
    own = session is None
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    url = source.url
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record: dict = {
        "key": source.key,
        "url": url,
        "category": source.category,
        "description": source.description,
        "kind": source.kind,
        "official_org": source.official_org,
        "optional": source.optional,
        "fetched_at": fetched_at,
        "ok": False,
        "status": None,
        "bytes": 0,
        "sha256": None,
        "final_url": None,
        "content_path": None,
        "error": None,
    }
    try:
        last_err = None
        for attempt in range(retries):
            try:
                resp = sess.get(url, timeout=timeout, allow_redirects=True)
                record["status"] = resp.status_code
                record["final_url"] = resp.url
                if resp.status_code == 200 and resp.content:
                    payload = resp.content
                    suffix = ".pdf" if source.kind == "pdf" else ".html"
                    fname = f"{slugify(source.key)}{suffix}"
                    fpath = os.path.join(outdir, fname)
                    with open(fpath, "wb") as fh:
                        fh.write(payload)
                    record.update(
                        ok=True,
                        bytes=len(payload),
                        sha256=_sha256(payload),
                        content_path=os.path.relpath(fpath, os.path.dirname(outdir) or "."),
                    )
                    return record
                last_err = f"HTTP {resp.status_code}"
            except Exception as exc:  # noqa: BLE001 - recorded, never raised
                last_err = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
        record["error"] = last_err
    finally:
        if own:
            sess.close()
    return record


def fetch_all(
    sources: list[Source],
    outdir: str,
    workers: int = 8,
    timeout: int = 45,
) -> list[dict]:
    """Fetch every source concurrently, politely and with retries."""
    os.makedirs(outdir, exist_ok=True)
    records: list[dict] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

    def task(src: Source) -> dict:
        return fetch_one(src, outdir, session=session, timeout=timeout)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for rec in pool.map(task, sources):
            records.append(rec)
    session.close()
    records.sort(key=lambda r: r["key"])
    return records


def write_manifest(records: list[dict], path: str) -> dict:
    """Persist the provenance manifest and return a summary."""
    ok = [r for r in records if r["ok"]]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(records),
        "succeeded": len(ok),
        "failed": len(records) - len(ok),
        "by_category": {},
    }
    for rec in records:
        cat = summary["by_category"].setdefault(
            rec["category"], {"ok": 0, "failed": 0, "urls": []}
        )
        if rec["ok"]:
            cat["ok"] += 1
        else:
            cat["failed"] += 1
        cat["urls"].append(
            {
                "key": rec["key"],
                "url": rec["url"],
                "ok": rec["ok"],
                "status": rec["status"],
                "sha256": rec["sha256"],
                "bytes": rec["bytes"],
                "fetched_at": rec["fetched_at"],
                "error": rec["error"],
            }
        )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "records": records}, fh, indent=2)
    return summary
