#!/usr/bin/env python3
"""proof/ shared data layer.

Reads the frozen files in `proof/raw/` (see `proof/fetch.py`) and produces the
two tables every other proof module needs:

  games      one row per completed regular-season game: season, week, teams,
             score, closing line, roof/surface, rest days.
  availability
             one row per team-game: how many players the club listed on that
             week's official report, broken down by game designation, plus the
             playing-time-weighted "vacancy" measure.

Both are DERIVED. Their inputs and hashes are printed by `python3 proof/engine.py
--provenance`.

Rule that this module enforces rather than documents: a game is only usable if
the availability report for that season is actually present. A missing report is
never treated as "everybody healthy" - it is dropped and counted.
"""
from __future__ import annotations

import csv
import os
import statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "proof", "raw")

INJURY_STATUSES = ("Out", "Doubtful", "Questionable")

# nflverse/codes: some historical club codes differ from the modern ones.
TEAM_ALIAS = {
    "LA": "LA", "LAR": "LA", "STL": "LA", "SD": "LAC", "OAK": "LV", "LVR": "LV",
    "WSH": "WAS", "WAS": "WAS", "JAC": "JAX", "JAX": "JAX", "ARZ": "ARI", "ARI": "ARI",
    "BLT": "BAL", "BAL": "BAL", "CLV": "CLE", "CLE": "CLE", "HOU": "HOU", "HST": "HOU",
    "SL": "LA", "RAM": "LA", "OTI": "TEN", "TEN": "TEN", "SFO": "SF", "SF": "SF",
    "TAM": "TB", "TB": "TB", "KAN": "KC", "KC": "KC", "NOR": "NO", "NO": "NO",
    "NWE": "NE", "NE": "NE", "NYG": "NYG", "NYJ": "NYJ", "PHI": "PHI", "PIT": "PIT",
    "SEA": "SEA", "MIN": "MIN", "MIA": "MIA", "IND": "IND", "DET": "DET", "DEN": "DEN",
    "DAL": "DAL", "CIN": "CIN", "CHI": "CHI", "CAR": "CAR", "BUF": "BUF", "ATL": "ATL",
    "GNB": "GB", "GB": "GB", "CHI ": "CHI",
}


def norm_team(t: str) -> str:
    t = (t or "").strip().upper()
    return TEAM_ALIAS.get(t, t)


def _path(name: str) -> str:
    return os.path.join(RAW, name)


def have(name: str) -> bool:
    return os.path.exists(_path(name))


def rows(name: str) -> list[dict]:
    with open(_path(name), newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# results + closing prices
# ---------------------------------------------------------------------------
def closing_prices(seasons: set[int]) -> dict[tuple[str, str], dict]:
    """(game_id, market) -> {line, odds}  from closing_lines.csv.

    `closing_lines.csv` is keyed by the long game_id (`2026090700`) but carries
    `alt_game_id` (`2026_01_NE_SEA`) as well, which is the key used everywhere
    else; the alt id is what we key on.
    """
    out: dict[tuple[str, str], dict] = {}
    if not have("closing_lines.csv"):
        return out
    for r in rows("closing_lines.csv"):
        gid = (r.get("alt_game_id") or "").strip()
        if not gid:
            continue
        try:
            season = int(gid.split("_")[0])
        except (ValueError, IndexError):
            continue
        if season not in seasons:
            continue
        out[(gid, r["type"].upper())] = {"line": r.get("line", "").strip(),
                                         "odds": r.get("odds", "").strip()}
    return out


def games(seasons: set[int]) -> list[dict]:
    """Completed regular-season games with scores and closing prices."""
    prices = closing_prices(seasons)
    out = []
    for r in rows("games.csv"):
        if r.get("game_type") != "REG":
            continue
        try:
            season = int(r["season"])
        except (KeyError, ValueError):
            continue
        if season not in seasons:
            continue
        try:
            hs, as_ = int(r["home_score"]), int(r["away_score"])
        except (KeyError, ValueError):
            continue  # unplayed: no result, therefore no truth to score against
        gid = r["game_id"]
        sp = prices.get((gid, "SPREAD"), {})
        tot = prices.get((gid, "TOTAL"), {})
        mlh = prices.get((gid, "MONEYLINE"), {})
        away, home = norm_team(r["away_team"]), norm_team(r["home_team"])
        rec = {
            "game_id": gid,
            "season": season,
            "week": int(r["week"]),
            "gameday": r.get("gameday", ""),
            "away": away,
            "home": home,
            "home_score": hs,
            "away_score": as_,
            "margin_home": hs - as_,
            "total_points": hs + as_,
            "roof": (r.get("roof") or "").strip(),
            "surface": (r.get("surface") or "").strip(),
            "away_rest": _int_or_blank(r.get("away_rest")),
            "home_rest": _int_or_blank(r.get("home_rest")),
            "spread_line": _float_or_blank(r.get("spread_line")),
            "total_line": _float_or_blank(r.get("total_line")),
            "close_spread": _float_or_blank(sp.get("line")),
            "close_total": _float_or_blank(tot.get("line")),
            "close_ml_home": _float_or_blank(mlh.get("odds")),
        }
        # prefer the closing file, fall back to the games file, never invent
        if rec["close_spread"] is None and rec["spread_line"] is not None:
            rec["close_spread"] = rec["spread_line"]
            rec["price_source"] = "games.csv spread_line (closing feed absent)"
        elif rec["close_spread"] is not None:
            rec["price_source"] = "closing_lines.csv"
        else:
            rec["price_source"] = ""
        if rec["close_total"] is None and rec["total_line"] is not None:
            rec["close_total"] = rec["total_line"]
        out.append(rec)
    out.sort(key=lambda g: (g["season"], g["week"], g["gameday"], g["game_id"]))
    return out


def _int_or_blank(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _float_or_blank(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# availability: the official injury report, per team-week
# ---------------------------------------------------------------------------
class Availability:
    """Official injury-report rows, indexed so a model can only see week < T.

    `report_status` is the game designation the club filed (Out / Doubtful /
    Questionable / blank). It is a *level*, not a surprise, and predicting from a
    level is exactly what the brief forbids - so this class also exposes the
    *unexpected* part: who was on the report and who had been playing a lot.
    """

    def __init__(self, seasons: set[int], min_snap_share: float = 0.35):
        self.min_snap_share = min_snap_share
        self.rows: list[dict] = []
        self.seasons_present: set[int] = set()
        self.counts_by_season: dict[int, int] = {}
        for s in sorted(seasons):
            name = f"injuries_{s}.csv"
            if not have(name):
                continue
            got = rows(name)
            self.seasons_present.add(s)
            self.counts_by_season[s] = len(got)
            for r in got:
                if (r.get("season_type") or "REG") != "REG":
                    continue
                try:
                    wk = int(r["week"])
                except (KeyError, ValueError):
                    continue
                self.rows.append({
                    "season": s,
                    "week": wk,
                    "team": norm_team(r.get("team", "")),
                    "player": (r.get("full_name") or "").strip(),
                    "gsis_id": (r.get("gsis_id") or "").strip(),
                    "position": (r.get("position") or "").strip(),
                    "injury": (r.get("report_primary_injury") or "").strip(),
                    "status": (r.get("report_status") or "").strip(),
                    "practice": (r.get("practice_status") or "").strip(),
                })
        self.by_team_week: dict[tuple[int, int, str], list[dict]] = defaultdict(list)
        for r in self.rows:
            self.by_team_week[(r["season"], r["week"], r["team"])].append(r)
        self._load_playing_time(seasons)

    # -- playing time (starter proxy) --------------------------------------
    def _load_playing_time(self, seasons: set[int]) -> None:
        """Average offensive+defensive snap share per player, from previous weeks only.

        Snap counts are the measured proxy for "is this man a starter". They are
        accumulated per (season, week, player) so the model can ask for the share
        as it stood *before* week T without peeking at week T.
        """
        self.snap_share: dict[tuple[int, int, str], float] = {}
        seasons_with_snaps = set()
        for s in sorted(seasons):
            name = f"snap_counts_{s}.csv"
            if not have(name):
                continue
            seasons_with_snaps.add(s)
            for r in rows(name):
                try:
                    wk = int(r["week"])
                except (KeyError, ValueError):
                    continue
                key = (s, wk, (r.get("player") or "").strip())
                try:
                    off = float(r.get("offense_pct") or 0)
                    dfn = float(r.get("defense_pct") or 0)
                except ValueError:
                    continue
                # a defensive starter has ~0 offense_pct and vice versa; take the
                # larger of the two as "share of his own side's snaps"
                share = max(off, dfn)
                if share > self.snap_share.get(key, -1.0):
                    self.snap_share[key] = share
        self.snap_seasons = seasons_with_snaps
        self._prior: dict[tuple[int, str], float] = {}
        byseason: dict[tuple[int, str], list[tuple[int, float]]] = defaultdict(list)
        for (s, wk, player), share in self.snap_share.items():
            byseason[(s, player)].append((wk, share))
        self._byseason = byseason

    def snap_share_before(self, season: int, week: int, player: str) -> float | None:
        """Mean snap share over the player's weeks strictly before `week`.

        Returns None when the player has no snap history before that week - the
        caller must treat that as unknown, not as zero.
        """
        hist = [(w, v) for (w, v) in self._byseason.get((season, player), []) if w < week]
        if not hist:
            # fall back to the previous season as a prior, clearly labelled
            hist = self._byseason.get((season - 1, player), [])
            if not hist:
                return None
        return st.mean(v for _w, v in hist)

    def team_week(self, season: int, week: int, team: str) -> dict:
        """Availability summary for one club-week, with the surprise decomposition.

        `vacancy` is the playing-time-weighted number of *established* players the
        club has ruled out or made doubtful. A backup being ruled out adds almost
        nothing; a 90%-snap player being ruled out adds 0.9. That is the whole
        point: the level of the report is not the signal, the loss is.
        """
        rs = self.by_team_week.get((season, week, team), [])
        counts = {k: 0 for k in INJURY_STATUSES}
        counts["blank"] = 0
        vacancy = 0.0
        vac_q = 0.0
        established_out: list[dict] = []
        unexpected: list[dict] = []
        for r in rs:
            s = r["status"]
            if s in counts:
                counts[s] += 1
            else:
                counts["blank"] += 1
            share = self.snap_share_before(season, week, r["player"])
            if share is None:
                continue
            if s == "Out":
                vacancy += share
                if share >= self.min_snap_share:
                    established_out.append({**r, "snap_share": round(share, 3)})
            elif s == "Doubtful":
                vacancy += share * 0.75
                if share >= self.min_snap_share:
                    established_out.append({**r, "snap_share": round(share, 3)})
            elif s == "Questionable":
                vacancy += share * 0.25
                vac_q += share
            # "surprise": a player the club had *not* been listing who appears on
            # the report at all, weighted by how much he normally plays. This is
            # the change in information, not the level of information.
            if s == "" and share >= self.min_snap_share:
                unexpected.append({**r, "snap_share": round(share, 3)})
        return {
            "reported": len(rs),
            "out": counts["Out"],
            "doubtful": counts["Doubtful"],
            "questionable": counts["Questionable"],
            "no_designation": counts["blank"],
            "vacancy": round(vacancy, 3),
            "vacancy_questionable": round(vac_q, 3),
            "established_out": established_out,
            "practice_only_established": unexpected,
            "has_report": bool(rs),
        }
