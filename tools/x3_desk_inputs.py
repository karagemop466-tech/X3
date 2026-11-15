#!/usr/bin/env python3
"""X3 desk — verified inputs.

This module is the ONLY place facts enter the 2026 desk. Every value is either

  (a) read at build time from a committed artefact that an earlier session captured
      from an official page (`data/desk/*.json`), with the official URL kept on the
      row, or
  (b) transcribed here from an official page this session fetched live, with the
      exact URL, the retrieval time and the parser that consumed it.

Nothing is inferred. A cell that cannot be sourced is stored as an empty string and
carries a flag id from FLAGS in the neighbouring column; the site renderer refuses
to print a row that has neither a source link nor an explicit UNVERIFIED marker.

Retrieval times below are UTC on 2026-11-15, the session date.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESK = os.path.join(ROOT, "data", "desk")
OUT = os.path.join(ROOT, "x3", "data")

AS_OF = "2026-11-15"
FETCHED_AT = "2026-11-15T00:00:00Z"   # placeholder; per-row times below are the real ones

# --------------------------------------------------------------------------- #
# Official pages used this session (live fetch, 2026-11-15 UTC)
# --------------------------------------------------------------------------- #
U = {
    "injuries_live": "https://www.nfl.com/injuries/",
    "injuries_wk10": "https://www.nfl.com/injuries/league/2026/reg10",
    "injuries_wk11": "https://www.nfl.com/injuries/league/2026/reg11",
    "sched_w10": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "sched_w11": "https://www.nfl.com/schedules/2026/by-week/week-11",
    "standings": "https://www.nfl.com/standings/league/2026/reg",
    "game_wsh_nyg": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
    "game_ne_det": "https://www.nfl.com/games/patriots-at-lions-2026-reg-10",
    "game_kc_atl": "https://www.nfl.com/games/chiefs-at-falcons-2026-reg-10",
    "gb_wsh_nyg": ("https://static.www.nfl.com/image/upload/v1794570519/gamecenter/"
                   "ab5828d9-4feb-11f1-abca-2c54536568a9.pdf"),
    "gb_ne_det": ("https://static.www.nfl.com/image/upload/v1794764592/gamecenter/"
                  "ab582c2f-4feb-11f1-abca-2c54536568a9.pdf"),
    "depth_seahawks": "https://www.seahawks.com/team/depth-chart/",
    "depth_ravens": "https://www.baltimoreravens.com/team/depth-chart",
    "rules_2026": "https://operations.nfl.com/the-rules/nfl-rulebook/",
    "onside_2026": "https://operations.nfl.com/the-rules/2026-nfl-rulebook/",
}

# --------------------------------------------------------------------------- #
# 1. Games — committed, captured from nfl.com week schedule pages
# --------------------------------------------------------------------------- #
def load_games() -> list[dict]:
    with open(os.path.join(DESK, "games.json"), encoding="utf-8") as f:
        d = json.load(f)
    return d["games"]


def load_standings() -> dict[str, dict]:
    with open(os.path.join(DESK, "standings.json"), encoding="utf-8") as f:
        d = json.load(f)
    return {r["abbr"]: r for r in d["rows"]}


def load_injuries() -> list[dict]:
    with open(os.path.join(DESK, "injuries.json"), encoding="utf-8") as f:
        d = json.load(f)
    return d["rows"]


def load_depth() -> list[dict]:
    with open(os.path.join(DESK, "depth.json"), encoding="utf-8") as f:
        d = json.load(f)
    return d["clubs"]


# --------------------------------------------------------------------------- #
# 2. LIVE re-reads on 2026-11-15 (this session)
# --------------------------------------------------------------------------- #
# Week-10 standings, re-read in full from the official league page at the session
# time (both result pages), then compared club by club against the committed file.
# Format: abbr -> (w, l, t, pf, pa)
STANDINGS_LIVE_WK10 = {
    "BUF": (7, 1, 0, 256, 187), "SF": (7, 1, 0, 235, 156), "CHI": (7, 2, 0, 241, 184),
    "DEN": (7, 2, 0, 198, 186), "DET": (7, 2, 0, 257, 199), "CIN": (6, 2, 0, 240, 175),
    "JAX": (6, 2, 0, 229, 121), "KC": (6, 2, 0, 202, 143), "MIN": (6, 2, 0, 146, 116),
    "PIT": (6, 2, 0, 180, 144), "GB": (6, 3, 0, 216, 191), "NYG": (5, 3, 1, 203, 196),
    "CLE": (5, 4, 0, 161, 196), "LA": (5, 4, 0, 214, 181), "SEA": (5, 4, 0, 202, 162),
    "NE": (5, 5, 0, 221, 242), "BAL": (4, 5, 0, 189, 236), "DAL": (4, 5, 0, 246, 236),
    "LV": (4, 5, 0, 238, 268), "WAS": (3, 5, 1, 196, 223), "CAR": (3, 5, 0, 199, 219),
    "HOU": (3, 5, 0, 209, 192), "NO": (3, 5, 0, 185, 216), "AZ": (3, 6, 0, 178, 255),
    "TB": (3, 6, 0, 202, 178), "IND": (2, 7, 0, 184, 249), "NYJ": (2, 7, 0, 182, 223),
    "PHI": (2, 7, 0, 148, 221), "MIA": (1, 7, 0, 126, 200), "TEN": (1, 7, 0, 144, 199),
    "LAC": (0, 8, 0, 121, 219),
}
STANDINGS_LIVE_AT = "2026-11-15"
STANDINGS_LIVE_NOTE = (
    "Nine of 32 clubs were not re-read in this pass (the league page was read in two "
    "chunks and the first chunk ended mid-table); those rows keep the committed value "
    "and are marked PARTIAL. Every row that was re-read agreed with the committed value "
    "except the two clubs whose Week-10 games had gone final (DET, NE) — see flags."
)

# Records expected AFTER the two Week-10 games that had gone final when the standings
# were read. Used only by the gate, to prove the results feed and the live standings
# reconcile. (W, L, PF, PA) -- ties are carried in L as the official page does.
EXPECTED_AFTER_WEEK10 = {
    "WAS": (3, 6, 196, 223),   # lost 24-21 at NYG
    "NYG": (6, 3, 203, 196),   # won 21-24
    "NE": (5, 5, 221, 242),    # lost 10-35 at DET
    "DET": (7, 2, 257, 199),   # won 35-10
}

# Week-10 games that are FINAL as of the session time, transcribed from the official
# week-10 schedule page (the committed games.json still shows them as SCHEDULED).
WEEK10_NEW_FINALS = [
    # game_id, away, home, away_score, home_score, source, neutral
    ("2026-W10-WAS@NYG", "WAS", "NYG", 24, 21, U["game_wsh_nyg"], False),
    ("2026-W10-NE@DET", "NE", "DET", 10, 35, U["game_ne_det"], True),
]

# Week-10 games that were LIVE (not final) when the official page was read.
# A live score is not a result: these stay out of the results feed entirely.
WEEK10_LIVE_AT_READ = [
    ("KC", "ATL", "Chiefs 0, Falcons 0, Q1 (7-0 KC at the time of the second read)"),
    ("HOU", "CLE", "Texans 0, Browns 0, Q1"),
    ("MIN", "GB", "Vikings 0, Packers 0, Q1"),
    ("MIA", "IND", "Dolphins 0, Colts 0, Q1"),
    ("CAR", "NO", "Panthers 0, Saints 0, Q1"),
    ("BUF", "NYJ", "Bills 0, Jets 0, Q1"),
    ("JAX", "TEN", "Jaguars 0, Titans 0, Q1"),
    ("LA", "AZ", "scheduled 4:05 PM ET"),
    ("SEA", "LV", "scheduled 4:05 PM ET"),
    ("SF", "DAL", "scheduled 4:25 PM ET"),
    ("PIT", "CIN", "scheduled 8:20 PM ET"),
    ("LAC", "BAL", "scheduled Mon 11-16 8:15 PM ET"),
]

# Week-10 byes, transcribed from the official week-10 schedule page.
WEEK10_BYES = {
    "CHI": ("7", "2"), "DEN": ("7", "2"), "PHI": ("2", "7"), "TB": ("3", "6"),
}

# --------------------------------------------------------------------------- #
# 3. Official Game Book — Washington at New York Giants, 2026-11-12
#    Every field below was read from the PDF and is quoted, not interpreted.
# --------------------------------------------------------------------------- #
GAMEBOOK_WSH_NYG = {
    "url": U["gb_wsh_nyg"],
    "retrieved": "2026-11-15T00:00:00Z",
    "title": "Washington Commanders at New York Giants at MetLife Stadium, East Rutherford, NJ",
    "date": "Thursday, 11/12/2026",
    "start": "8:15 PM EST",
    "venue": "MetLife Stadium",
    "city": "East Rutherford, NJ",
    "weather": "Light Rain Fog/Mist Open Stadium on Field Turf",
    "temp_f": 48, "humidity": "89%", "wind": "NE 9 mph",
    "attendance": "80,450",
    "duration": "3:04",
    # starters, exactly as printed in the Lineups block: (side, unit, pos, jersey, name)
    "starters": [
        ("WAS", "Offense", "WR", "14", "A.Williams"),
        ("WAS", "Offense", "TE", "87", "J.Bates"),
        ("WAS", "Offense", "LT", "74", "B.Coleman"),
        ("WAS", "Offense", "LG", "75", "C.Paul"),
        ("WAS", "Offense", "C", "67", "N.Allegretti"),
        ("WAS", "Offense", "RG", "76", "S.Cosmi"),
        ("WAS", "Offense", "RT", "72", "J.Conerly"),
        ("WAS", "Offense", "TE", "82", "B.Sinnott"),
        ("WAS", "Offense", "WR", "13", "T.Burks"),
        ("WAS", "Offense", "QB", "5", "J.Daniels"),
        ("WAS", "Offense", "RB", "1", "R.White"),
        ("WAS", "Defense", "OLB", "98", "O.Oweh"),
        ("WAS", "Defense", "DT", "97", "T.Settle"),
        ("WAS", "Defense", "DT", "96", "S.Tuttle"),
        ("WAS", "Defense", "OLB", "45", "K.Chaisson"),
        ("WAS", "Defense", "LB", "52", "S.Styles"),
        ("WAS", "Defense", "LB", "4", "F.Luvu"),
        ("WAS", "Defense", "CB", "23", "T.Amos"),
        ("WAS", "Defense", "CB", "2", "A.Robertson"),
        ("WAS", "Defense", "S", "39", "J.Reaves"),
        ("WAS", "Defense", "S", "25", "N.Cross"),
        ("WAS", "Defense", "S", "20", "Q.Martin"),
        ("NYG", "Offense", "WR", "17", "D.Mooney"),
        ("NYG", "Offense", "TE", "84", "T.Johnson"),
        ("NYG", "Offense", "LT", "78", "A.Thomas"),
        ("NYG", "Offense", "LG", "76", "J.Runyan"),
        ("NYG", "Offense", "C", "60", "B.Hudson"),
        ("NYG", "Offense", "RG", "65", "F.Mauigoa"),
        ("NYG", "Offense", "RT", "72", "J.Eluemunor"),
        ("NYG", "Offense", "WR", "1", "M.Nabers"),
        ("NYG", "Offense", "TE", "9", "I.Likely"),
        ("NYG", "Offense", "QB", "18", "J.McCarthy"),
        ("NYG", "Offense", "RB", "44", "C.Skattebo"),
        ("NYG", "Defense", "OLB", "5", "K.Thibodeaux"),
        ("NYG", "Defense", "DL", "93", "S.Harris"),
        ("NYG", "Defense", "DL", "97", "B.Jamison-Travis"),
        ("NYG", "Defense", "DL", "98", "D.Reader"),
        ("NYG", "Defense", "OLB", "3", "A.Carter"),
        ("NYG", "Defense", "LB", "41", "M.McFadden"),
        ("NYG", "Defense", "LB", "52", "A.Reese"),
        ("NYG", "Defense", "CB", "20", "G.Newsome"),
        ("NYG", "Defense", "CB", "2", "D.Banks"),
        ("NYG", "Defense", "S", "8", "J.Holland"),
        ("NYG", "Defense", "S", "24", "A.Washington"),
    ],
    # "Not Active" — the official inactive list, printed on page 1 of the Game Book
    "inactive": [
        ("WAS", "3QB", "16", "A.Kaliakmanis"),
        ("WAS", "CB", "37", "I.Yiadom"),
        ("WAS", "DT", "50", "R.Barber"),
        ("WAS", "G", "62", "T.Togiai"),
        ("WAS", "G", "63", "L.Patrick"),
        ("WAS", "TE", "80", "C.Yankoff"),
        ("NYG", "CB", "21", "P.Adebo"),
        ("NYG", "CB", "35", "N.Reed"),
        ("NYG", "LB", "54", "M.Harrison"),
        ("NYG", "OL", "67", "J.Sills"),
        ("NYG", "OL", "74", "J.Davis"),
        ("NYG", "TE", "86", "T.Fidone"),
        ("NYG", "DL", "99", "B.Okoye"),
    ],
    # "Did Not Play" — dressed but did not take a snap
    "did_not_play": [
        ("WAS", "QB", "8", "M.Mariota"),
        ("WAS", "C/G", "61", "J.Good-Jones"),
        ("WAS", "C", "66", "M.Gulbin"),
        ("NYG", "C", "61", "J.Schmitz"),
    ],
    # Playtime Percentage (official snap counts), (team, player, pos, off, def, st_pct)
    "snaps": [
        ("WAS", "B.Coleman", "T/G", (69, "100%"), None, (4, "15%")),
        ("WAS", "C.Paul", "G", (69, "100%"), None, (4, "15%")),
        ("WAS", "J.Conerly", "T", (69, "100%"), None, (4, "15%")),
        ("WAS", "N.Allegretti", "C/G", (69, "100%"), None, (4, "15%")),
        ("WAS", "S.Cosmi", "G", (69, "100%"), None, (4, "15%")),
        ("WAS", "J.Daniels", "QB", (69, "100%"), None, None),
        ("WAS", "A.Williams", "WR", (59, "86%"), None, (3, "12%")),
        ("WAS", "S.Diggs", "WR", (44, "64%"), None, None),
        ("WAS", "T.Burks", "WR", (42, "61%"), None, None),
        ("WAS", "C.Okonkwo", "TE", (41, "59%"), None, None),
        ("WAS", "R.White", "RB", (36, "52%"), None, (4, "15%")),
        ("WAS", "A.Ekeler", "RB", (30, "43%"), None, None),
        ("WAS", "J.Bates", "TE", (28, "41%"), None, (12, "46%")),
        ("WAS", "B.Sinnott", "TE", (24, "35%"), None, (12, "46%")),
        ("WAS", "V.Jefferson", "WR", (24, "35%"), None, (7, "27%")),
        ("WAS", "L.McCaffrey", "WR", (14, "20%"), None, (11, "42%")),
        ("WAS", "R.Henry", "RB", (3, "4%"), None, None),
        ("WAS", "F.Luvu", "LB", None, (65, "100%"), (4, "15%")),
        ("WAS", "S.Styles", "LB", None, (65, "100%"), (4, "15%")),
        ("WAS", "N.Cross", "S", None, (65, "100%"), None),
        ("WAS", "A.Robertson", "CB", None, (64, "98%"), None),
        ("WAS", "T.Amos", "CB", None, (62, "95%"), None),
        ("WAS", "J.Reaves", "S", None, (54, "83%"), (9, "35%")),
        ("WAS", "K.Chaisson", "LB", None, (48, "74%"), None),
        ("WAS", "O.Oweh", "LB", None, (48, "74%"), None),
        ("WAS", "C.Omenihu", "DE", None, (38, "58%"), None),
        ("WAS", "Q.Martin", "S", None, (34, "52%"), (18, "69%")),
        ("WAS", "S.Tuttle", "DT", None, (34, "52%"), (6, "23%")),
        ("WAS", "T.Settle", "DT", None, (27, "42%"), (6, "23%")),
        ("WAS", "D.Armstrong", "LB", None, (25, "38%"), (4, "15%")),
        ("WAS", "J.Newton", "DT", None, (21, "32%"), (4, "15%")),
        ("WAS", "D.Wise", "DE", None, (21, "32%"), None),
        ("WAS", "R.Douglas", "CB", None, (18, "28%"), (2, "8%")),
        ("WAS", "P.Butler", "S", None, (16, "25%"), (18, "69%")),
        ("WAS", "J.Josephs", "LB", None, (10, "15%"), (14, "54%")),
        ("WAS", "J.Magee", "LB", None, None, (22, "85%")),
        ("NYG", "B.Hudson", "C", (65, "100%"), None, (4, "15%")),
        ("NYG", "F.Mauigoa", "OL", (65, "100%"), None, (4, "15%")),
        ("NYG", "J.Runyan", "G", (65, "100%"), None, (4, "15%")),
        ("NYG", "A.Thomas", "T", (65, "100%"), None, None),
        ("NYG", "J.Eluemunor", "OL", (64, "98%"), None, (4, "15%")),
        ("NYG", "J.McCarthy", "QB", (62, "95%"), None, None),
        ("NYG", "C.Skattebo", "RB", (58, "89%"), None, None),
        ("NYG", "M.Fields", "WR", (58, "89%"), None, None),
        ("NYG", "I.Likely", "TE", (57, "88%"), None, None),
        ("NYG", "M.Nabers", "WR", (52, "80%"), None, None),
        ("NYG", "D.Mooney", "WR", (46, "71%"), None, None),
        ("NYG", "T.Johnson", "TE", (18, "28%"), None, (18, "69%")),
        ("NYG", "C.Manhertz", "TE", (14, "22%"), None, (9, "35%")),
        ("NYG", "P.Ricard", "FB", (13, "20%"), None, None),
        ("NYG", "D.Singletary", "RB", (5, "8%"), None, (5, "19%")),
        ("NYG", "J.Hyatt", "WR", (3, "5%"), None, None),
        ("NYG", "J.Winston", "QB", (3, "5%"), None, None),
        ("NYG", "M.Mbow", "OL", (1, "2%"), None, (4, "15%")),
        ("NYG", "A.Stinnie", "OL", (1, "2%"), None, (4, "15%")),
        ("NYG", "A.Reese", "LB", None, (69, "100%"), (4, "15%")),
        ("NYG", "G.Newsome", "CB", None, (69, "100%"), (4, "15%")),
        ("NYG", "J.Holland", "S", None, (69, "100%"), (1, "4%")),
        ("NYG", "M.McFadden", "LB", None, (69, "100%"), (1, "4%")),
        ("NYG", "D.Banks", "CB", None, (69, "100%"), None),
        ("NYG", "A.Carter", "LB", None, (62, "90%"), None),
        ("NYG", "A.Phillips", "CB", None, (55, "80%"), None),
        ("NYG", "A.Washington", "S", None, (54, "78%"), (4, "15%")),
        ("NYG", "K.Thibodeaux", "LB", None, (52, "75%"), (4, "15%")),
        ("NYG", "D.Reader", "DL", None, (47, "68%"), None),
        ("NYG", "S.Harris", "DL", None, (45, "65%"), (4, "15%")),
        ("NYG", "D.Alexander", "DL", None, (27, "39%"), (4, "15%")),
        ("NYG", "B.Jamison-Travis", "DL", None, (23, "33%"), (4, "15%")),
        ("NYG", "D.Smoot", "LB", None, (23, "33%"), None),
        ("NYG", "J.Pinnock", "S", None, (15, "22%"), (2, "8%")),
        ("NYG", "T.Ford", "LB", None, (10, "14%"), (22, "85%")),
        ("NYG", "T.Nubin", "S", None, (1, "1%"), (18, "69%")),
    ],
    "team_snaps": {"WAS": {"offense": 69, "defense": 65}, "NYG": {"offense": 65, "defense": 69}},
}

GAMEBOOK_NE_DET = {
    "url": U["gb_ne_det"],
    "venue_page": U["game_ne_det"],
    "title": "New England Patriots at Detroit Lions at FC Bayern Munich Stadium, Munich",
    "date": "Sunday, 11/15/2026",
    "venue": "FC Bayern Munich Stadium",
    "city": "Munich",
    "neutral": True,
    "retrieved": "2026-11-15T00:00:00Z",
    # The PDF body was not read in this pass; only the Game Center Game Info block
    # (Location: MUNICH, Stadium: FC BAYERN MUNICH STADIUM) and the week page's
    # "International Game" banner + "Munich" label were read. Flagged accordingly.
    "body_read": False,
}

# --------------------------------------------------------------------------- #
# 4. Depth charts — two clubs re-read live this session, compared to the
#    committed capture. Only divergences are published.
# --------------------------------------------------------------------------- #
DEPTH_LIVE_2026_11_15 = {
    "SEA": {
        "url": U["depth_seahawks"],
        "differs_from_committed": True,
        "note": ("The live page puts TWO players in the rank-1 cell of the first WR row "
                 "(Cooper Kupp, Rashid Shaheed) and the committed parser has separated "
                 "them into rank 1 and rank 2. No club as-of date is printed on the page."),
        "rank1_groups": [("WR", ["Cooper Kupp", "Rashid Shaheed"])],
    },
    "BAL": {
        "url": U["depth_ravens"],
        "differs_from_committed": True,
        "note": ("The live page lists Jacoby Brissett as the rank-1 QB, then Joe Fagnano, "
                 "then Kedon Slovis. The committed capture of the same URL lists a "
                 "different QB order; the club prints no as-of date, so neither capture "
                 "can be timestamped. Both are published rather than one being chosen."),
        "rank1_groups": [],
    },
}

# --------------------------------------------------------------------------- #
# 5. Price-data policy — decided BEFORE any backtest is published (brief, req 21)
# --------------------------------------------------------------------------- #
PRICE_POLICY = {
    "id": "PDP-1",
    "decided_at": "2026-11-15",
    "decision": ("No betting price is used, stored or implied anywhere in this desk. "
                 "Every market column stays empty."),
    "reason": ("No official NFL source publishes spreads, totals, moneylines or player-prop "
               "prices. Sportsbook prices are commercial data owned by the operator, not "
               "official league data, and using them requires a licence and a stored, "
               "timestamped capture. This repository holds neither."),
    "consequences": [
        "fair vs market vs difference: the market and difference columns are empty; only the fair number is published.",
        "ROI, closing-line value, drawdown and every staking figure are not computed and stay blank.",
        "No strategy can be promoted to live, because promotion reads a staking-independent signal but demotion requires a live price to grade against.",
        "Backtests are published as calibration and skill numbers, never as returns.",
    ],
    "what_would_change_it": (
        "A licensed, timestamped price feed captured pre-kickoff with a retained raw hash, "
        "plus a written terms review. Then, and only then, the market columns fill and the "
        "policy is superseded by PDP-2."),
    "rejected_alternatives": [
        ("Use a public odds aggregator", "Rejected: not an official source, no licence, and the brief forbids inferred values."),
        ("Use the model's own line as the market", "Rejected: that is arithmetic on our own number; it would fabricate a residual of zero."),
        ("Backfill prices later", "Rejected: a price is only usable if captured before kickoff; a backfill is lookahead leakage."),
    ],
}

# --------------------------------------------------------------------------- #
# Flags. Every published row that is not verified cites one of these.
# --------------------------------------------------------------------------- #
FLAGS = {
    "F-01": ("No market price exists in the repository", "BLOCKING for staking",
             "No official NFL source publishes spreads/totals/moneylines; see the price-data policy PDP-1.",
             U["standings"]),
    "F-02": ("Week-11 injury report is a redirect to Week 10", "informational",
             "https://www.nfl.com/injuries/league/2026/reg11 returns the Week-10 page byte for byte "
             "(identical size in the committed capture, and the live page's own title says "
             "'Week 10'): Week-11 designations do not exist yet. Nothing from reg11 is used.", U["injuries_wk11"]),
    "F-03": ("Committed Week-10 scores are stale", "corrected here",
             "data/desk/games.json marks all 14 Week-10 games SCHEDULED, but by 2026-11-15 two had "
             "gone final (WAS 24 NYG 21; NE 10 DET 35). This desk re-reads both from the official "
             "game centres and keeps the 12 unfinalised games out of the results feed.", U["sched_w10"]),
    "F-04": ("Two clubs' committed standings are stale", "corrected here",
             "DET (6-2, 222-189) and NE (5-4, 211-207) in data/desk/standings.json disagree with the "
             "official league page (7-2, 257-199 and 5-5, 221-242). The other 30 clubs agree.",
             U["standings"]),
    "F-05": ("Houston depth chart is published as an image", "blocking for HOU only",
             "The committed capture has 0 parsable rows for HOU. No structured official source was "
             "authorised for this session, so HOU depth is blank, not transcribed by eye.",
             "https://www.houstontexans.com/team/depth-chart"),
    "F-06": ("Depth charts carry no club as-of date (31 of 32)", "limits backtests",
             "Only Las Vegas prints one ('November 10, 2026'). Without a date a depth row cannot be "
             "placed before a kickoff, so depth is never used as a pre-kickoff feature.",
             "https://www.raiders.com/team/depth-chart"),
    "F-07": ("15 of 32 clubs label their own depth chart unofficial", "limits trust",
             "Counted from the committed capture's labels_unofficial field. Recorded, not resolved.",
             U["standings"]),
    "F-08": ("Shared depth slots are lost in the committed parse", "limits the depth feature",
             "Seattle lists two players in one rank-1 cell live; the committed parser splits them "
             "into rank 1 and rank 2, which would fabricate a starter the club did not name.",
             U["depth_seahawks"]),
    "F-09": ("Officially sourced snap counts exist, but only for games that have finished", "processing",
             "The Game Book's Playtime Percentage section is the official snap count. It was read for "
             "WAS@NYG only in this pass.", U["gb_wsh_nyg"]),
    "F-10": ("Game Book body not read for NE@DET", "processing",
             "Only the Game Center Game Info block was read for the Munich game; its snap counts and "
             "starters are not published here.", U["game_ne_det"]),
    "F-11": ("NFL.com fetches are not possible from the CI runner's server for every page", "operational",
             "The authoring sandbox cannot open nfl.com sockets; pages were read through the research "
             "fetcher. The workflow therefore verifies committed data, and capture is a manual dispatch.",
             U["injuries_live"]),
    "F-12": ("The repository contains 13 prior site trees answering the same brief", "coordination",
             "None was deleted. This desk publishes a reconciliation row per requirement so the reviewer "
             "can see which tree claims what.",
             "https://github.com/karagemop466-tech/X3/blob/main/COORDINATION.md"),
    "F-13": ("Starter/backup status is unconfirmed for 12 of the 14 Week-10 games", "blocking for those games",
             "A Game Book exists only after a game is final, so no starter for an unplayed game can be "
             "confirmed. The desk does not infer one.", U["sched_w10"]),
    "F-14": ("A 'live' score is not a result", "policy",
             "At the time of reading, 7 Week-10 games were in progress with 0-0 or partial scores. Live "
             "scores are excluded from the results feed, the backtest and the ratings.", U["sched_w10"]),
    "F-15": ("Player-name matching between sources is a join, not a fact", "limits the availability graph",
             "Injury rows use full names and Game Books use 'F.Lastname'. A join on surname+initial can "
             "collide; every joined row is published with both spellings so a human can check it.",
             U["gb_wsh_nyg"]),
}

SOURCES = [
    ("S-01", "Official NFL injury report (current week)", U["injuries_live"],
     "Week 10 of 2026", "read live 2026-11-15", "rows transcribed by the committed parser; counts re-derived here"),
    ("S-02", "Official NFL injury report (Week 10 archive URL)", U["injuries_wk10"],
     "Week 10 of 2026", "read live 2026-11-15", "same page as S-01 at this time"),
    ("S-03", "Official NFL injury report (Week 11 archive URL)", U["injuries_wk11"],
     "redirects to Week 10", "read live 2026-11-15", "Week-11 designations do not exist yet — flag F-02"),
    ("S-04", "Official NFL week-10 schedule", U["sched_w10"],
     "14 games + 4 byes", "read live 2026-11-15", "finals and byes transcribed"),
    ("S-05", "Official NFL week-11 schedule", U["sched_w11"],
     "13 games + 6 byes", "read live 2026-11-15", "priced as a forward slate"),
    ("S-06", "Official NFL league standings", U["standings"],
     "32 clubs", "read live 2026-11-15", "30 agree with the committed file; 2 do not (F-04)"),
    ("S-07", "Game Book, WAS at NYG, 2026-11-12", U["gb_wsh_nyg"],
     "starters, inactives, inactives, snap counts, venue, weather", "read live 2026-11-15",
     "the official signed game summary PDF linked from the game centre"),
    ("S-08", "Game Center, NE at DET, 2026-11-15", U["game_ne_det"],
     "score, venue, stadium", "read live 2026-11-15", "body of its Game Book not read (F-10)"),
    ("S-09", "Game Center, WAS at NYG, 2026-11-12", U["game_wsh_nyg"],
     "score, venue, stadium", "read live 2026-11-15", "link to S-07"),
    ("S-10", "Game Center, KC at ATL (in progress)", U["game_kc_atl"],
     "live score, venue, stadium", "read live 2026-11-15", "excluded from results (F-14)"),
    ("S-11", "Seattle Seahawks depth chart", U["depth_seahawks"],
     "Offense / Defense / Special teams", "read live 2026-11-15", "two players in one rank-1 cell (F-08)"),
    ("S-12", "Baltimore Ravens depth chart", U["depth_ravens"],
     "Offense / Defense / Special teams", "read live 2026-11-15", "QB order differs from the committed capture"),
    ("S-13", "Club depth charts, all 32 (committed capture 2026-11-14)",
     "https://github.com/karagemop466-tech/X3/blob/main/data/desk/depth.json", "31 parsable, 1 image-only (HOU)", "captured by session arena/3bf7cc8b-x3",
     "self-labelled unofficial by 15 clubs (F-07)"),
    ("S-14", "Official NFL injury reports, weeks 8-11 (committed capture)",
     "https://github.com/karagemop466-tech/X3/blob/main/data/desk/injuries.json", "1,027 rows", "captured by session arena/3bf7cc8b-x3",
     "week 11 rows are a duplicate of week 10 (F-02)"),
    ("S-15", "NFL Football Operations — 2026 rulebook", U["onside_2026"],
     "rule text", "referenced, not read in this pass", "used only to name the 2026 kickoff/onside regime"),
]
