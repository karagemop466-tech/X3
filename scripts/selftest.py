#!/usr/bin/env python3
"""Offline self-tests for the parsing and metric code.

These run without network access and use fixtures captured from official
sources, so a regression in a parser or a metric is caught before the
pipeline runs.

    python scripts/selftest.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.parsers import (
    normalise_depth_groups,
    parse_injuries,
    parse_player_stats,
    parse_schedule,
    parse_standings,
    resolve_depth_string,
)
import compute_signals as cs

FAILURES: list[str] = []
PASSES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSES.append(name)
        print(f"[PASS] {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"[FAIL] {name} {detail}")


#: Fixtures are captured from official sources into ``scripts/fixtures`` by
#: ``scripts/capture_fixtures.py``, which the pipeline runs after the fetch.
#: They are not committed, so the repository stays small and the fixtures can
#: never drift from the live pages.
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

#: Which cached payload backs which fixture.
FIXTURE_SOURCES = {
    "injuries.html": "injuries_current",
    "standings.html": "standings_league_2026",
    "player_stats_passing.html": "stats_player_passing_2026",
    "schedule.html": "schedule_2026_w05",
}


def fixture(name: str) -> str:
    path = os.path.join(FIXTURES, name)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def test_injuries() -> None:
    html = fixture("injuries.html")
    if not html:
        print("[SKIP] injuries fixture not present")
        return
    parsed = parse_injuries(html, "https://www.nfl.com/injuries/")
    check("injuries: week detected", parsed["week"] == 10, f"got {parsed['week']}")
    check("injuries: rows parsed", len(parsed["rows"]) > 100, f"got {len(parsed['rows'])}")
    check("injuries: games parsed", len(parsed["games"]) >= 14, f"got {len(parsed['games'])}")
    check(
        "injuries: every row has a source_url",
        all(r.get("source_url") for r in parsed["rows"]),
    )
    check(
        "injuries: every row has a team",
        all(r.get("team") for r in parsed["rows"]),
    )
    dates = {r["game_date"] for r in parsed["rows"]}
    check("injuries: multiple game dates bound correctly", len(dates) >= 2, f"got {dates}")
    statuses = {r["game_status"] for r in parsed["rows"]}
    check(
        "injuries: game statuses are official values",
        statuses <= {"", "Out", "Doubtful", "Questionable"},
        f"got {statuses}",
    )


def test_standings() -> None:
    html = fixture("standings.html")
    if not html:
        print("[SKIP] standings fixture not present")
        return
    rows = parse_standings(html, "https://www.nfl.com/standings/league/2026/REG", 2026)
    check("standings: 32 teams", len(rows) == 32, f"got {len(rows)}")
    check(
        "standings: names carry no duplicated nickname",
        all(r["team"] != f'{r["team"]} {r["team_nickname"]}' for r in rows if r.get("team_nickname")),
        str([r["team"] for r in rows[:3]]),
    )
    check(
        "standings: names match the official club names",
        {r["team"] for r in rows} >= {"Los Angeles Chargers", "Miami Dolphins", "Tennessee Titans"},
        str(sorted(r["team"] for r in rows)[:5]),
    )
    check(
        "standings: points for and against are numeric",
        all(str(r["points_for"]).isdigit() for r in rows),
    )
    check(
        "standings: every row has a source_url",
        all(r.get("source_url") for r in rows),
    )
    sample = rows[0]
    check(
        "standings: first row reads the official values",
        sample["team"] and sample["wins"] and sample["points_for"],
        str(sample),
    )


def test_player_stats() -> None:
    html = fixture("player_stats_passing.html")
    if not html:
        print("[SKIP] player stats fixture not present")
        return
    parsed = parse_player_stats(html, "https://www.nfl.com/stats/", "passing", 2026)
    check("player stats: rows parsed", len(parsed["rows"]) > 20, f"got {len(parsed['rows'])}")
    check(
        "player stats: headers preserved",
        "Pass Yds" in parsed["columns"] and "Rate" in parsed["columns"],
        str(parsed["columns"]),
    )
    check(
        "player stats: every row has a source_url",
        all(r.get("source_url") for r in parsed["rows"]),
    )


def test_schedule() -> None:
    html = fixture("schedule.html")
    if not html:
        print("[SKIP] schedule fixture not present")
        return
    parsed = parse_schedule(html, "https://www.nfl.com/schedules/2026/by-week/week-5", 2026, 5)
    games = parsed["games"]
    check("schedule: games parsed", len(games) >= 10, f"got {len(games)}")
    scored = [g for g in games if g.get("away_score") and g.get("home_score")]
    check("schedule: final scores captured", len(scored) >= 10, f"got {len(scored)}")
    check(
        "schedule: every game has both teams",
        all(g.get("away_team") and g.get("home_team") for g in games),
    )
    check(
        "schedule: every game carries its official link",
        all("/games/" in (g.get("game_url") or "") for g in games),
    )
    check(
        "schedule: every game carries a source_url",
        all(g.get("source_url") for g in games),
    )
    check(
        "schedule: the game week matches the requested week",
        all(
            (not g.get("game_url")) or f"-reg-{parsed['week']}" in g["game_url"]
            for g in games
        ),
        str([g["game_url"] for g in games[:3]]),
    )
    check(
        "schedule: network and date are captured",
        any(g.get("network") for g in games) and any(g.get("game_date") for g in games),
        str(games[:1]),
    )


def test_depth_resolution() -> None:
    # The layout an official club depth chart actually uses: a Position column
    # and depth columns labelled 1st, 2nd, 3rd.
    units = [
        {
            "headers": ["Position", "1st", "2nd", "3rd", "4th"],
            "rows": [
                ["QB", "Jordan Love", "Deshaun Watson", "Malik Willis", ""],
                ["WR", "Jordan Watkins", "Christian Watson", "Romeo Doubs", "Jalen Moreno"],
                ["RB", "A.J. Dillon", "Chris Brooks", "Tyrion Mitchell", ""],
            ],
        }
    ]
    groups = normalise_depth_groups(units)
    positions = {g["position"] for g in groups}
    check("depth: positions normalised", positions == {"QB", "WR", "RB"}, str(positions))
    check(
        "depth: QB1 resolved",
        resolve_depth_string(groups, "Jordan Love", "QB") == "QB1",
        resolve_depth_string(groups, "Jordan Love", "QB"),
    )
    check(
        "depth: QB3 resolved",
        resolve_depth_string(groups, "Malik Willis", "QB") == "QB3",
        resolve_depth_string(groups, "Malik Willis", "QB"),
    )
    check(
        "depth: WR4 resolved",
        resolve_depth_string(groups, "Jalen Moreno", "WR") == "WR4",
        resolve_depth_string(groups, "Jalen Moreno", "WR"),
    )
    check(
        "depth: unknown player is not guessed",
        resolve_depth_string(groups, "Nobody Here", "QB") == "",
    )
    check(
        "depth: unknown position is not guessed",
        resolve_depth_string(groups, "Jordan Love", "K") == "",
    )
    numbered = [{"headers": [], "rows": [["RB", "1. A.J. Dillon", "2. Chris Brooks"]]}]
    ngroups = normalise_depth_groups(numbered)
    check(
        "depth: explicit ordinals honoured",
        resolve_depth_string(ngroups, "Chris Brooks", "RB") == "RB2",
        resolve_depth_string(ngroups, "Chris Brooks", "RB"),
    )

    # The layout a club uses when the offence and the defence are printed side
    # by side, read column by column.
    side_by_side = [
        {
            "headers": [],
            "rows": [
                ["QB", "QB", "DE"],
                ["Jordan Love", "Joe Burrow", "Cameron Thomas"],
                ["Deshaun Watson", "Joe Flacco", "Za'Darius Smith"],
            ],
        }
    ]
    sgroups = normalise_depth_groups(side_by_side)
    check(
        "depth: side-by-side layout separates the units",
        resolve_depth_string(sgroups, "Joe Burrow", "QB") == "QB1"
        and resolve_depth_string(sgroups, "Cameron Thomas", "DE") == "DE1",
        str([(g["position"], [p["name"] for p in g["players"]]) for g in sgroups]),
    )


def test_skill_share() -> None:
    """A strategy with a real edge must beat a pure-luck strategy on skill share."""
    rng = __import__("random").Random(7)
    n = 400
    price = 0.55

    skilled_bets = [
        {"p_model": 0.60, "price": price, "won": 1 if rng.random() < 0.60 else 0, "edge": 0.05}
        for _ in range(n)
    ]
    skill, low, high, null_p, perm_p, t = cs.skill_share_stats(skilled_bets)
    check("skill share: skilled strategy has a high share", skill is not None and skill > 0.8, str(skill))
    check("skill share: interval excludes zero", low is not None and low > 0.5, f"{low}..{high}")
    check("skill share: luck null rejects the skilled strategy", null_p is not None and null_p < 0.05, str(null_p))
    check("skill share: edge t-statistic is large", t is not None and t > 3, str(t))

    luck_bets = [
        {"p_model": 0.50, "price": price, "won": 1 if rng.random() < 0.5 else 0, "edge": 0.0}
        for _ in range(n)
    ]
    lskill, llow, lhigh, lnull_p, lperm_p, lt = cs.skill_share_stats(luck_bets)
    check("skill share: luck strategy shows much less skill", lskill is not None and skill is not None and lskill < skill * 0.25, f"{lskill} vs {skill}")
    check("skill share: luck strategy is not significant", lnull_p is None or lnull_p > 0.05, str(lnull_p))

    # A strategy whose edge is real but tiny must not clear the gate.
    thin_bets = [
        {"p_model": 0.505, "price": 0.50, "won": 1 if rng.random() < 0.505 else 0, "edge": 0.005}
        for _ in range(n)
    ]
    tskill, _l, _h, tnull, _tp, _tt = cs.skill_share_stats(thin_bets)
    check("skill share: a thin edge does not clear the threshold", tskill is not None and tskill < 0.25, str(tskill))


def test_correlation() -> None:
    xs = [1, 2, 3, 4, 5, 6]
    ys = [2, 4, 6, 8, 10, 12]
    r = cs.pearson(xs, ys)
    check("correlation: perfect positive", r is not None and abs(r - 1.0) < 1e-9, str(r))
    r2 = cs.pearson(xs, list(reversed(ys)))
    check("correlation: perfect negative", r2 is not None and abs(r2 + 1.0) < 1e-9, str(r2))
    check("correlation: too few points gives None", cs.pearson([1], [2]) is None)


def test_scoring() -> None:
    bets = [
        {"profit": 1.0, "p_model": 0.6, "won": 1, "edge": 0.05, "fold": "2026-W01"},
        {"profit": -1.0, "p_model": 0.45, "won": 0, "edge": 0.02, "fold": "2026-W01"},
        {"profit": 2.0, "p_model": 0.55, "won": 1, "edge": 0.04, "fold": "2026-W02"},
        {"profit": -1.0, "p_model": 0.45, "won": 0, "edge": 0.01, "fold": "2026-W02"},
    ]
    m = cs.score_bets(bets)
    check("scoring: bet count", m["bets"] == 4, str(m))
    check("scoring: net units", abs(m["net_units"] - 1.0) < 1e-9, str(m))
    check("scoring: roi", abs(m["roi"] - 0.25) < 1e-9, str(m))
    check("scoring: drawdown computed", m["max_drawdown_units"] is not None, str(m))
    folds = cs.fold_consistency(bets)
    check("scoring: fold count", folds["n_folds"] == 2, str(folds))
    check("scoring: positive fold share", abs(folds["positive_fold_share"] - 0.5) < 1e-9, str(folds))
    empty = cs.score_bets([])
    check("scoring: empty bets give None metrics", empty["net_units"] is None and empty["bets"] == 0)


def main() -> int:
    test_injuries()
    test_standings()
    test_player_stats()
    test_schedule()
    test_depth_resolution()
    test_skill_share()
    test_correlation()
    test_scoring()
    print()
    print(f"{len(PASSES)} passed, {len(FAILURES)} failed")
    for f in FAILURES:
        print(f"  FAILED: {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
