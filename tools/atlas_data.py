#!/usr/bin/env python3
"""Verified inputs for the atlas/ decision desk (session arena/dbb50f8c-x3).

Every value in this file was transcribed from an official NFL page that this
session actually read on 2026-11-17. Nothing is inferred, modelled or filled in.
Where an official page does not publish a value, the value is absent here and
the page renders it as UNVERIFIED / BLOCKED.

Sources are recorded once, in SOURCES, and referenced by key from every table.
"""
from __future__ import annotations

AS_OF = "2026-11-17"
SEASON = 2026
WEEK_COMPLETE = 10
WEEK_NEXT = 11

# --------------------------------------------------------------------------
# Source register - only pages this session fetched and read are listed.
# --------------------------------------------------------------------------
SOURCES = {
    "standings": {
        "label": "nfl.com - 2026 league standings",
        "url": "https://www.nfl.com/standings/league/2026/REG",
        "read": "2026-11-17",
        "kind": "official",
        "note": "32 rows; W/L/T, PCT, PF, PA, NET, home, road, div, conf, non-conf, streak, last-5.",
    },
    "wk10": {
        "label": "nfl.com - 2026 Week 10 schedule (final scores)",
        "url": "https://www.nfl.com/schedules/2026/by-week/week-10",
        "read": "2026-11-17",
        "kind": "official",
        "note": "14 finals; 4 clubs on bye (CHI, DEN, PHI, TB).",
    },
    "wk9capture": {
        "label": "data/hub/standings_2026_thru_wk9.csv - through-Week-9 standings captured 2026-11-14",
        "url": "../data/hub/standings_2026_thru_wk9.csv",
        "read": "2026-11-17",
        "kind": "repo capture of an official page",
        "note": "32 rows captured by an earlier session from nfl.com/standings/league/2026/REG "
                "on 2026-11-14. Used here only as a dated prior capture to diff against the "
                "live page - not as a statement about the present.",
    },
    "wk11": {
        "label": "nfl.com - 2026 Week 11 schedule",
        "url": "https://www.nfl.com/schedules/2026/by-week/week-11",
        "read": "2026-11-17",
        "kind": "official",
        "note": "13 fixtures and 6 clubs on bye (ATL, CLE, GB, LAR, NE, SEA).",
    },
    "injuries": {
        "label": "nfl.com - official injury report, Week 10 2026",
        "url": "https://www.nfl.com/injuries/league/2026/reg10",
        "read": "2026-11-17",
        "kind": "official",
        "note": "28 club sections (bye clubs absent). reg11 still redirects here: Week 11 "
               "designations do not exist yet.",
    },
    "news1117": {
        "label": "nfl.com - news roundup, Tuesday Nov. 17",
        "url": "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-tuesday-nov-17",
        "read": "2026-11-17",
        "kind": "official",
        "note": "Club-by-club signings, IR placements, cuts and practice designations.",
    },
    "odds404": {
        "label": "nfl.com/odds returns HTTP 404",
        "url": "https://www.nfl.com/odds/",
        "read": "2026-11-17",
        "kind": "official",
        "note": "Page title: '404 - Flag on the Play.' The league publishes no odds, so every "
                "market-price cell on this site is blank and flagged.",
    },
}

# Game-centre pages read for venue, location and official season team stats.
# key -> (slug, location, stadium, schedule-page venue string, note)
GAME_CENTRE = "https://www.nfl.com/games/%s-2026-reg-11"

# --------------------------------------------------------------------------
# Standings through Week 10 (complete). Transcribed field for field from
# https://www.nfl.com/standings/league/2026/REG on 2026-11-17.
#   team, name, w, l, t, pct, pf, pa, net, home, road, div, div_pct,
#   conf, conf_pct, nonconf, streak, last5
# --------------------------------------------------------------------------
STANDINGS = [
    ("BUF", "Buffalo Bills", 8, 1, 0, ".889", 287, 199, 88, "3-1-0", "5-0-0", "1-1-0", ".500", "5-1-0", ".833", "3-0-0", "5W", "5-0-0"),
    ("SF", "San Francisco 49ers", 8, 1, 0, ".889", 281, 196, 85, "5-0-0", "3-1-0", "3-0-0", "1.000", "5-1-0", ".833", "3-0-0", "2W", "4-1-0"),
    ("CHI", "Chicago Bears", 7, 2, 0, ".778", 241, 184, 57, "4-1-0", "3-1-0", "0-2-0", ".000", "5-2-0", ".714", "2-0-0", "4W", "4-1-0"),
    ("CIN", "Cincinnati Bengals", 7, 2, 0, ".778", 278, 193, 85, "3-1-0", "4-1-0", "2-1-0", ".667", "5-2-0", ".714", "2-0-0", "5W", "5-0-0"),
    ("DEN", "Denver Broncos", 7, 2, 0, ".778", 198, 186, 12, "4-0-0", "3-2-0", "2-1-0", ".667", "3-1-0", ".750", "4-1-0", "5W", "5-0-0"),
    ("DET", "Detroit Lions", 7, 2, 0, ".778", 257, 199, 58, "5-0-0", "2-2-0", "2-0-0", "1.000", "4-1-0", ".800", "3-1-0", "5W", "5-0-0"),
    ("JAX", "Jacksonville Jaguars", 7, 2, 0, ".778", 269, 144, 125, "4-1-0", "3-1-0", "2-1-0", ".667", "6-2-0", ".750", "1-0-0", "3W", "4-1-0"),
    ("KC", "Kansas City Chiefs", 7, 2, 0, ".778", 237, 156, 81, "4-0-0", "3-2-0", "3-1-0", ".750", "6-1-0", ".857", "1-1-0", "2W", "3-2-0"),
    ("MIN", "Minnesota Vikings", 7, 2, 0, ".778", 176, 126, 50, "3-1-0", "4-1-0", "3-1-0", ".750", "5-1-0", ".833", "2-1-0", "1W", "3-2-0"),
    ("PIT", "Pittsburgh Steelers", 6, 3, 0, ".667", 198, 182, 16, "4-0-0", "2-3-0", "2-2-0", ".500", "3-3-0", ".500", "3-0-0", "1L", "4-1-0"),
    ("NYG", "New York Giants", 5, 3, 1, ".611", 203, 196, 7, "3-2-0", "2-1-1", "2-1-1", ".625", "3-3-1", ".500", "2-0-0", "1L", "2-2-1"),
    ("CLE", "Cleveland Browns", 6, 4, 0, ".600", 188, 220, -32, "4-0-0", "2-4-0", "2-1-0", ".667", "4-3-0", ".571", "2-1-0", "1W", "3-2-0"),
    ("GB", "Green Bay Packers", 6, 4, 0, ".600", 226, 221, 5, "3-2-0", "3-2-0", "1-3-0", ".250", "4-4-0", ".500", "2-0-0", "1L", "3-2-0"),
    ("LAR", "Los Angeles Rams", 6, 4, 0, ".600", 248, 187, 61, "2-3-0", "4-1-0", "1-2-0", ".333", "4-2-0", ".667", "2-2-0", "4W", "4-1-0"),
    ("SEA", "Seattle Seahawks", 6, 4, 0, ".600", 223, 175, 48, "4-2-0", "2-2-0", "2-1-0", ".667", "2-3-0", ".400", "4-1-0", "2W", "3-2-0"),
    ("NE", "New England Patriots", 5, 5, 0, ".500", 221, 242, -21, "3-1-0", "2-4-0", "3-0-0", "1.000", "5-1-0", ".833", "0-4-0", "2L", "2-3-0"),
    ("CAR", "Carolina Panthers", 4, 5, 0, ".444", 219, 236, -17, "1-3-0", "3-2-0", "2-1-0", ".667", "4-3-0", ".571", "0-2-0", "1W", "2-3-0"),
    ("BAL", "Baltimore Ravens", 4, 6, 0, ".400", 209, 259, -50, "1-4-0", "3-2-0", "0-2-0", ".000", "2-5-0", ".286", "2-1-0", "5L", "0-5-0"),
    ("DAL", "Dallas Cowboys", 4, 6, 0, ".400", 286, 282, 4, "1-4-0", "3-2-0", "2-1-0", ".667", "2-5-0", ".286", "2-1-0", "1L", "2-3-0"),
    ("LV", "Las Vegas Raiders", 4, 6, 0, ".400", 251, 289, -38, "1-4-0", "3-2-0", "1-1-0", ".500", "3-3-0", ".500", "1-3-0", "2L", "1-4-0"),
    ("WAS", "Washington Commanders", 3, 5, 1, ".389", 196, 223, -27, "2-2-1", "1-3-0", "2-2-1", ".500", "3-4-1", ".438", "0-1-0", "1W", "2-2-1"),
    ("HOU", "Houston Texans", 3, 6, 0, ".333", 233, 219, 14, "0-4-0", "3-2-0", "2-1-0", ".667", "3-4-0", ".429", "0-2-0", "1L", "3-2-0"),
    ("NO", "New Orleans Saints", 3, 6, 0, ".333", 202, 236, -34, "1-5-0", "2-1-0", "0-2-0", ".000", "1-4-0", ".200", "2-2-0", "1L", "2-3-0"),
    ("TB", "Tampa Bay Buccaneers", 3, 6, 0, ".333", 202, 178, 24, "1-4-0", "2-2-0", "2-0-0", "1.000", "3-3-0", ".500", "0-3-0", "1L", "3-2-0"),
    ("AZ", "Arizona Cardinals", 3, 7, 0, ".300", 184, 289, -105, "0-4-0", "3-3-0", "1-4-0", ".200", "2-6-0", ".250", "1-1-0", "2L", "2-3-0"),
    ("ATL", "Atlanta Falcons", 3, 7, 0, ".300", 201, 258, -57, "1-5-0", "2-2-0", "1-2-0", ".333", "3-3-0", ".500", "0-4-0", "3L", "1-4-0"),
    ("IND", "Indianapolis Colts", 3, 7, 0, ".300", 208, 271, -63, "2-3-0", "1-4-0", "1-2-0", ".333", "2-5-0", ".286", "1-2-0", "1W", "1-4-0"),
    ("PHI", "Philadelphia Eagles", 2, 7, 0, ".222", 148, 221, -73, "1-4-0", "1-3-0", "1-3-0", ".250", "1-6-0", ".143", "1-1-0", "7L", "0-5-0"),
    ("NYJ", "New York Jets", 2, 8, 0, ".200", 194, 254, -60, "1-4-0", "1-4-0", "0-3-0", ".000", "2-5-0", ".286", "0-3-0", "5L", "0-5-0"),
    ("LAC", "Los Angeles Chargers", 1, 8, 0, ".111", 144, 239, -95, "0-4-0", "1-4-0", "0-3-0", ".000", "1-5-0", ".167", "0-3-0", "1W", "1-4-0"),
    ("MIA", "Miami Dolphins", 1, 8, 0, ".111", 148, 224, -76, "0-4-0", "1-4-0", "1-1-0", ".500", "1-5-0", ".167", "0-3-0", "3L", "1-4-0"),
    ("TEN", "Tennessee Titans", 1, 8, 0, ".111", 167, 239, -72, "0-5-0", "1-3-0", "1-2-0", ".333", "1-6-0", ".143", "0-2-0", "3L", "1-4-0"),
]

# --------------------------------------------------------------------------
# Week 10 finals. Transcribed from nfl.com/schedules/2026/by-week/week-10.
#   date, away, home, away_pts, home_pts, slot
# --------------------------------------------------------------------------
WEEK10_RESULTS = [
    ("2026-11-12", "WAS", "NYG", 24, 21, "Thursday"),
    ("2026-11-15", "NE", "DET", 10, 35, "Munich game"),
    ("2026-11-15", "KC", "ATL", 35, 13, "Sunday 1:00pm"),
    ("2026-11-15", "HOU", "CLE", 24, 27, "Sunday 1:00pm"),
    ("2026-11-15", "MIN", "GB", 30, 10, "Sunday 1:00pm"),
    ("2026-11-15", "MIA", "IND", 22, 24, "Sunday 1:00pm"),
    ("2026-11-15", "CAR", "NO", 20, 17, "Sunday 1:00pm"),
    ("2026-11-15", "BUF", "NYJ", 31, 12, "Sunday 1:00pm"),
    ("2026-11-15", "JAX", "TEN", 40, 23, "Sunday 1:00pm"),
    ("2026-11-15", "LAR", "AZ", 34, 6, "Sunday 4:05pm"),
    ("2026-11-15", "SEA", "LV", 21, 13, "Sunday 4:05pm"),
    ("2026-11-15", "SF", "DAL", 46, 40, "Sunday 4:25pm"),
    ("2026-11-15", "PIT", "CIN", 18, 38, "Sunday night"),
    ("2026-11-16", "LAC", "BAL", 23, 20, "Monday night"),
]
WEEK10_BYES = ["CHI", "DEN", "PHI", "TB"]

# --------------------------------------------------------------------------
# Week 11 fixtures. date/time/network from nfl.com/schedules/2026/by-week/week-11;
# location and stadium transcribed from each club's official game centre; the
# schedule page's own hotel link carries a second venue string, kept and compared.
#   date, time_et, network, away, home, slug, location, stadium, sched_venue
# --------------------------------------------------------------------------
WEEK11_FIXTURES = [
    ("2026-11-19", "8:15 PM", "PRIME", "IND", "HOU", "colts-at-texans",
     "HOUSTON, TX", "RELIANT STADIUM", "NRG Stadium"),
    ("2026-11-22", "1:00 PM", "CBS", "MIA", "BUF", "dolphins-at-bills",
     "ORCHARD PARK, NY", "HIGHMARK STADIUM", "Highmark Stadium"),
    ("2026-11-22", "1:00 PM", "FOX", "BAL", "CAR", "ravens-at-panthers",
     "CHARLOTTE, NC", "BANK OF AMERICA STADIUM", "Bank of America Stadium"),
    ("2026-11-22", "1:00 PM", "FOX", "NO", "CHI", "saints-at-bears",
     "CHICAGO, IL", "SOLDIER FIELD", "Soldier Field"),
    ("2026-11-22", "1:00 PM", "FOX", "TEN", "DAL", "titans-at-cowboys",
     "ARLINGTON, TX", "AT&T STADIUM", "AT&T Stadium"),
    ("2026-11-22", "1:00 PM", "FOX", "TB", "DET", "buccaneers-at-lions",
     "DETROIT, MI", "FORD FIELD", "Ford Field"),
    ("2026-11-22", "1:00 PM", "CBS", "AZ", "KC", "cardinals-at-chiefs",
     "KANSAS CITY, MO", "ARROWHEAD STADIUM", "GEHA Field at Arrowhead Stadium"),
    ("2026-11-22", "1:00 PM", "CBS", "PIT", "PHI", "steelers-at-eagles",
     "PHILADELPHIA, PA", "LINCOLN FINANCIAL FIELD", "Lincoln Financial Field"),
    ("2026-11-22", "4:05 PM", "FOX", "NYJ", "LAC", "jets-at-chargers",
     "INGLEWOOD, CA", "SOFI STADIUM", "SoFi Stadium"),
    ("2026-11-22", "4:25 PM", "CBS", "JAX", "NYG", "jaguars-at-giants",
     "EAST RUTHERFORD, NJ", "METLIFE STADIUM", "MetLife Stadium"),
    ("2026-11-22", "4:25 PM", "CBS", "LV", "DEN", "raiders-at-broncos",
     "DENVER, CO", "EMPOWER FIELD AT MILE HIGH", "Empower Field at Mile High"),
    ("2026-11-22", "8:20 PM", "NBC", "MIN", "SF", "vikings-at-49ers",
     "MEXICO CITY", "ESTADIO BANORTE", "(no hotel link published)"),
    ("2026-11-23", "8:15 PM", "ESPN", "CIN", "WAS", "bengals-at-commanders",
     "LANDOVER, MD", "NORTHWEST STADIUM", "FedEx Field"),
]
WEEK11_BYES = ["ATL", "CLE", "GB", "LAR", "NE", "SEA"]

# --------------------------------------------------------------------------
# Official season team stats, transcribed from each Week 11 game centre
# ("Regular season at a glance"). Only the 26 clubs playing in Week 11 appear.
#   team, ppg, ypg, top, def_sacks, def_ints, to_diff
# --------------------------------------------------------------------------
TEAM_STATS = [
    ("IND", 20.8, 287.6, "31:07", 22, 2, -12),
    ("HOU", 25.9, 349.1, "29:33", 33, 5, 4),
    ("MIN", 19.6, 271.8, "30:22", 37, 10, 8),
    ("SF", 31.2, 399.8, "30:13", 16, 7, 3),
    ("MIA", 16.4, 283.4, "28:50", 13, 7, -2),
    ("BUF", 31.9, 386.7, "31:23", 21, 7, 0),
    ("BAL", 20.9, 328.3, "30:38", 19, 4, -4),
    ("CAR", 24.3, 353.6, "29:32", 15, 6, 1),
    ("NO", 22.4, 314.2, "29:52", 26, 4, -8),
    ("CHI", 26.8, 383.2, "34:31", 26, 7, -4),
    ("TEN", 18.6, 278.6, "25:12", 21, 9, -1),
    ("DAL", 28.6, 368.3, "29:24", 22, 4, -3),
    ("TB", 22.4, 305.3, "32:38", 17, 16, 7),
    ("DET", 28.6, 392.4, "31:14", 32, 7, 2),
    ("AZ", 18.4, 298.5, "30:31", 21, 4, -1),
    ("KC", 26.3, 392.2, "29:21", 17, 7, 6),
    ("PIT", 22.0, 316.2, "30:40", 27, 7, 5),
    ("PHI", 16.4, 260.2, "28:03", 16, 3, -4),
    ("NYJ", 19.4, 316.5, "30:13", 23, 2, 3),
    ("LAC", 16.0, 291.1, "30:09", 15, 8, -5),
    ("JAX", 29.9, 358.9, "31:46", 17, 12, 9),
    ("NYG", 22.6, 340.4, "33:15", 17, 8, -2),
    ("LV", 25.1, 314.2, "28:32", 22, 7, 3),
    ("DEN", 22.0, 277.3, "28:51", 26, 8, 5),
    ("CIN", 30.9, 383.7, "30:47", 26, 5, 2),
    ("WAS", 21.8, 327.0, "30:09", 18, 6, 7),
]

# --------------------------------------------------------------------------
# Week 10 injury report. Row counts per club read live on 2026-11-17, set
# against the capture committed by an earlier session (data/hub, 2026-11-14).
#   team, live_rows, committed_rows, live_designated, committed_designated
# --------------------------------------------------------------------------
INJURY_TEAM_COUNTS = [
    ("WAS", 9, 9, 2, 2), ("NYG", 11, 11, 1, 1), ("NE", 15, 15, 12, 12),
    ("DET", 9, 9, 5, 5), ("KC", 13, 13, 6, 6), ("ATL", 11, 11, 5, 5),
    ("MIN", 13, 13, 8, 8), ("GB", 17, 17, 12, 12), ("JAX", 11, 11, 4, 4),
    ("TEN", 12, 12, 6, 6), ("BUF", 14, 14, 5, 5), ("NYJ", 9, 9, 8, 8),
    ("MIA", 11, 11, 4, 4), ("IND", 14, 14, 7, 7), ("CAR", 12, 12, 7, 7),
    ("NO", 12, 12, 6, 6), ("HOU", 16, 16, 11, 11), ("CLE", 12, 12, 3, 3),
    ("LAR", 14, 14, 7, 7), ("AZ", 15, 15, 9, 9), ("SEA", 15, 15, 4, 4),
    ("LV", 5, 5, 2, 2), ("SF", 12, 12, 8, 8), ("DAL", 19, 19, 11, 11),
    ("PIT", 8, 8, 1, 1), ("CIN", 9, 9, 4, 4), ("LAC", 19, 19, 10, 10),
    ("BAL", 10, 8, 2, 0),
]
# Designation totals computed from the committed capture (exact, programmatic).
COMMITTED_TOTALS = {"rows": 345, "out": 66, "doubtful": 10, "questionable": 84, "blank": 185}
LIVE_TOTALS = {"rows": 347, "designated": 170}

# --------------------------------------------------------------------------
# Availability / roster events. Each row is a dated item on an official page
# that this session read. Nothing here is inferred from a depth chart.
#   date, club, kind, player, detail, source_key
# --------------------------------------------------------------------------
ROSTER_EVENTS = [
    ("2026-11-17", "AZ", "Reserve", "Jordan Burch", "LB (knee) placed on injured reserve", "news1117"),
    ("2026-11-17", "AZ", "Reserve", "Andrew Wingard", "S (wrist/knee) placed on IR", "news1117"),
    ("2026-11-17", "BUF", "Reserve", "Ar'maj Reed-Adams", "G placed on injured reserve", "news1117"),
    ("2026-11-17", "DET", "Reserve", "Aidan Hutchinson", "DE - test confirmed a torn ACL suffered in the Week 10 win over New England; surgery pending", "news1117"),
    ("2026-11-17", "DET", "Return", "Kerby Joseph", "S (knee) expected to make his season debut in Week 11 - has not played since Week 6 of 2025", "news1117"),
    ("2026-11-17", "HOU", "Reserve", "Azeez Al-Shaair", "LB (groin) placed on injured reserve", "news1117"),
    ("2026-11-17", "HOU", "Practice", "Woody Marks", "RB (concussion) did not practise", "news1117"),
    ("2026-11-17", "HOU", "Practice", "Marvin Harrison Jr.", "WR (hamstring) did not practise", "news1117"),
    ("2026-11-17", "HOU", "Practice", "Danielle Hunter", "DE (hamstring) did not practise", "news1117"),
    ("2026-11-17", "HOU", "Practice", "David Montgomery", "RB (groin) full participation", "news1117"),
    ("2026-11-17", "HOU", "Added to report", "Kamari Lassiter", "CB (wrist) added as limited", "news1117"),
    ("2026-11-17", "IND", "Reserve", "Jaylon Carlies", "LB placed on injured reserve", "news1117"),
    ("2026-11-17", "IND", "Practice", "Sauce Gardner", "CB (calf) did not practise", "news1117"),
    ("2026-11-17", "IND", "Practice", "Bernhard Raimann", "OT (concussion) did not practise", "news1117"),
    ("2026-11-17", "CHI", "Return", "Luther Burden III", "WR is out of the concussion protocol", "news1117"),
    ("2026-11-17", "CHI", "Practice", "Kyler Gordon", "CB (shoulder) - status for Week 11 undecided", "news1117"),
    ("2026-11-17", "CLE", "Schedule", "-", "Week 12 vs Las Vegas flexed to Sunday Night Football, 8:20pm ET, Nov 29", "news1117"),
    ("2026-11-17", "JAX", "Schedule", "-", "Week 12 at Tennessee flexed to 1:00pm ET on FOX, Nov 29", "news1117"),
    ("2026-11-16", "MIN", "Reserve", "Jordan Addison", "WR needs thumb surgery, could go to IR", "injuries"),
    ("2026-11-16", "NE", "Reserve", "Drake Maye", "QB - NFL Network reports he could miss the rest of 2026 (ankle, Week 10)", "injuries"),
    ("2026-11-16", "TB", "Injury", "Baker Mayfield", "QB dealing with a lower leg injury ahead of Week 11", "injuries"),
    ("2026-11-15", "NYJ", "Injury", "Geno Smith", "QB suffered an ankle injury in the Week 10 loss to Buffalo", "injuries"),
    ("2026-11-14", "NE", "Reserve", "TreVeyon Henderson", "RB (illness) placed on injured reserve", "injuries"),
    ("2026-11-13", "BAL", "Reserve", "Lamar Jackson", "QB - Ravens confirm he is expected to miss 6-10 weeks", "injuries"),
    ("2026-11-11", "MIA", "Reserve", "Malik Willis", "QB (groin) placed on injured reserve; Kyle McCord in line for his first start", "injuries"),
    ("2026-11-10", "BUF", "Trade", "Amani Hooker", "S acquired by Buffalo", "injuries"),
    ("2026-11-10", "DEN", "Trade", "Daiyan Henley", "LB acquired from the Chargers", "injuries"),
    ("2026-11-10", "LAR", "Reserve", "Puka Nacua", "WR likely to be placed on IR (turf toe, sprained MCL and PCL)", "injuries"),
    ("2026-11-10", "GB", "Reserve", "Josh Jacobs", "RB to undergo surgery on a finger; timeline to return TBD", "injuries"),
]

# --------------------------------------------------------------------------
# Pre-registered Week 11 model. The constants below are declared before any
# Week 11 kickoff; they are not fitted to Week 11 outcomes, which do not exist.
# --------------------------------------------------------------------------
MODEL = {
    "id": "ATL-M1",
    "name": "Official-points rating model (base)",
    "declared": "2026-11-17",
    "kickoff_first": "2026-11-19T20:15:00-05:00",
    "hfa_points": 2.0,
    "sigma_points": 13.0,
    "personnel_points_per_out": -0.10,
    "pythagorean_exponent": 2.37,
    "order": ["side", "total", "moneyline"],
    "inputs": "Official PF and PA per club game through Week 10 (n=32, nfl.com/standings) and "
              "Out counts from the official Week 10 injury report.",
    "side_rule": "home_margin = HFA + ((home_PPG + away_PAPG) - (away_PPG + home_PAPG)) / 2",
    "total_rule": "total = (home_PPG + away_PPG + home_PAPG + away_PAPG) / 2",
    "moneyline_rule": "P(home win) = Phi(home_margin / sigma); American price from that "
                      "probability with no margin applied",
}

# --------------------------------------------------------------------------
# The brief's requirement register. Status is this session's finding against
# the repo and the official sources; 'blocking gate' and 'number that clears'
# are project targets, not NFL-published facts, and are labelled as such.
#   id, requirement (short), status, blocking gate, number that clears it
# --------------------------------------------------------------------------
REQUIREMENTS = [
    ("R-01", "Price-snapshot store: opening and closing numbers for every market we originate", "BLOCKED", "G-PRICE", "One price source class approved; then >=1 stored open and >=1 stored close per market row"),
    ("R-02", "Verified results feed so backtests and ROI can be computed", "PARTIAL", "G-RESULTS", ">=1 full season of finals reconciled to the official standings with 0 mismatches (150 of 170 games today)"),
    ("R-03", "Originate the side first, then the total, then the moneyline", "DONE", "G-PREREG", "Model committed before kickoff; chain published side -> total -> moneyline"),
    ("R-04", "Publish fair line, market line and the difference as separate columns", "BLOCKED", "G-PRICE", "Market column populated for >=1 market from an approved source (nfl.com/odds is a 404)"),
    ("R-05", "Separate signal from staking in the leaderboard", "DONE", "G-LEADER", "Two published columns per strategy; 0 strategies ranked on staking alone"),
    ("R-06", "Track the depth of the replacement, not just the fact", "PARTIAL", "G-DEPTH", "Depth rank published for every unavailable starter (0 of 0 today - Week 11 report not published)"),
    ("R-07", "Correlations only from officially sourced numbers, publish n", "DONE", "G-CORR", "Every coefficient carries its n and its source page"),
    ("R-08", "Demotion gate that sends a live strategy back to paper", "DONE", "G-DEMOTE", "Rule text committed; fires on any of four clauses"),
    ("R-09", "Pre-register every strategy; backtest numbers never on the leaderboard", "DONE", "G-PREREG", "Commit hash recorded before the evaluation window opens"),
    ("R-10", "Availability graph as a first-class dataset", "PARTIAL", "G-AVAIL", "Expected starter and actual starter captured per club per week (0 weeks today)"),
    ("R-11", "Model depth from playing time, never jersey order", "NOT STARTED", "G-DEPTH", "Snap-share source approved for all 32 clubs"),
    ("R-12", "Injury signal as a surprise, never a level", "DONE", "G-SURPRISE", "Two or more dated captures so a delta can be computed"),
    ("R-13", "32-club roster/IR sweep before any team-level model is trusted", "PARTIAL", "G-SWEEP", "32 of 32 clubs swept in one capture cycle (today: ad-hoc items only)"),
    ("R-14", "Fixture-context features from published schedule facts only", "DONE", "G-FIXTURE", "Every feature traced to a dated official page"),
    ("R-15", "Store every model output as a probability plus its inputs", "DONE", "G-MODEL", "Every output row lists its inputs and the rule that produced it"),
    ("R-16", "Publish the removal-of-luck panel on the dashboard", "DONE", "G-LUCK", "Residual SD and r-squared published with n"),
    ("R-17", "Two-sided what-would-change-our-mind field on every strategy", "DONE", "G-PREREG", "Both an upgrade and a downgrade trigger recorded before results"),
    ("R-18", "Price a line ourselves and publish the residual, on a schedule", "BLOCKED", "G-PRICE", "Market price exists for the same market at the same timestamp"),
    ("R-19", "Turn the season game log into the pre-registered backtest corpus", "PARTIAL", "G-RESULTS", "150 of 170 games; earlier rounds of the season not yet captured here"),
    ("R-20", "Price-data policy decided before any backtest is published", "DONE", "G-PRICE", "Policy text committed; no backtest published before it"),
    ("R-21", "Store every injury-hub read with its clock time; publish the delta", "PARTIAL", "G-AVAIL", ">=2 captures per week with a recorded fetch timestamp (1 today)"),
    ("R-22", "Decision-readiness table on the landing page", "DONE", "G-COORD", "One row per requirement with its blocker and its clearing number"),
    ("R-23", "Transcribe the venue of every fixture from the official game centre", "DONE", "G-FIXTURE", "13 of 13 Week 11 venues transcribed (this session)"),
    ("R-24", "Publish the league's dated schedule announcement beside the live schedule", "NOT STARTED", "G-FIXTURE", "Announcement page fetched, dated and stored"),
    ("R-25", "Official NFL Game Books for actual starters and game-day status", "NOT STARTED", "G-DEPTH", "Game Book captured per club per week; no inferred snap rank"),
    ("R-26", "Ingest game-level results to make ratings opponent-aware", "PARTIAL", "G-RESULTS", "Opponent-adjusted rating computed on a full season of finals"),
    ("R-27", "Injury and personnel ablations, not fixed penalties", "DONE", "G-ABLATE", "Same model run with and without the feature on chronological holdouts"),
    ("R-28", "Automate immutable multi-day availability snapshots", "NOT STARTED", "G-AVAIL", "Scheduled job with retained hashes and a successful logged run"),
    ("R-29", "Capture official inactive lists and snap counts", "NOT STARTED", "G-DEPTH", "Inactives and snap share captured for >=1 round"),
    ("R-30", "Fix the two depth-parsing failures before widening coverage", "NOT STARTED", "G-DEPTH", "Texans image and Packers jersey-number cases both resolved"),
    ("R-31", "Model depth slots as groups, not a single starter", "NOT STARTED", "G-DEPTH", "Shared and empty slots represented in the schema"),
    ("R-32", "Treat roster turnover as a first-class data event", "PARTIAL", "G-SWEEP", "Every availability row versioned against the last official roster event"),
    ("R-33", "Singles-only shadow baseline, pre-registered", "DONE", "G-PREREG", "Baseline frozen and forecasts recorded before kickoff"),
    ("R-34", "Parlays and prop combos behind a joint-evidence gate", "DONE", "G-JOINT", "Validated joint probability plus the operator's void/push rules"),
    ("R-35", "Proper-score leaderboard divisions", "DONE", "G-LEADER", "Singles, game parlays, SGPs and prop combos ranked separately"),
    ("R-36", "Rank with proper scores and uncertainty, not win rate", "DONE", "G-LEADER", "Brier skill with a cluster lower bound and a multiplicity adjustment"),
    ("R-37", "Stadium roof/surface and hourly wind/precipitation overlay", "NOT STARTED", "G-WEATHER", "NWS grid joined to the official 90-minute roof designation"),
    ("R-38", "Two-stage leaderboard: proper-score qualification then CLV/ROI escrow", "BLOCKED", "G-PRICE", "Prospective multi-week CLV sample with prices"),
    ("R-39", "Vig-free market consensus vs originated fair-line decomposition", "BLOCKED", "G-PRICE", "Consensus price retrievable per market"),
    ("R-40", "Weekly what-changed diff instead of a static snapshot", "PARTIAL", "G-DIFF", "Two consecutive weekly snapshots stored (1 today)"),
    ("R-41", "Publish every model total twice until one wins", "DONE", "G-MODEL", "Both estimators visible with the gap column (base and personnel variants)"),
    ("R-42", "Drift alarm on every scraper", "NOT STARTED", "G-DRIFT", "Expected row counts and required fields pinned; build fails loudly"),
    ("R-43", "Capture the reserve list so 'not listed' never means 'available'", "PARTIAL", "G-SWEEP", "IR and reserve status captured for all 32 clubs"),
    ("R-44", "Reject ranking strategies by season-long ROI", "DONE", "G-LEADER", "Leaderboard shows no ROI column at all"),
    ("R-45", "Archive weekly injury reports for past seasons", "NOT STARTED", "G-HISTORY", ">=2 prior seasons of weekly reports archived"),
    ("R-46", "Freeze a rule before it sees data (pre-registration)", "DONE", "G-PREREG", "Rule text, sample window and gates committed; the hash is the registration"),
    ("R-47", "Split data into train, validation and final holdout seasons", "NOT STARTED", "G-HISTORY", "Three labelled seasons with fixed boundaries"),
    ("R-48", "Kickoff and onside-kick regime priors for 2026", "NOT STARTED", "G-RULES", "Rule change verified against the official rulebook page"),
    ("R-49", "Add a control baseline (random picks, favourites only) to every leaderboard run", "DONE", "G-LEADER", "Two control rows published beside every eligible strategy"),
    ("R-50", "Per-team view: starters out, replacements named, net injury count", "PARTIAL", "G-DEPTH", "Replacement named for every out starter (0 named today)"),
    ("R-51", "Announced-starter evidence field, not an inferred replacement", "PARTIAL", "G-DEPTH", "Dated starter announcements captured per club"),
    ("R-52", "Official depth-chart register with date and source per row", "NOT STARTED", "G-DEPTH", "32 of 32 club charts with an as-of date"),
    ("R-53", "Calibrate what 'Questionable' means empirically", "NOT STARTED", "G-HISTORY", "Designations joined to inactives with a play rate per designation and CIs"),
    ("R-54", "Snapshot the injury report Wed/Thu/Fri and keep dated history", "NOT STARTED", "G-AVAIL", "Three dated captures in one week with a logged job"),
    ("R-55", "Treat the injury report as a timestamped series, not a snapshot", "PARTIAL", "G-AVAIL", "Fetch timestamp recorded on every capture"),
    ("R-56", "Use snap counts as the starter proxy when no depth chart exists", "NOT STARTED", "G-DEPTH", "Official snap-count source approved"),
    ("R-57", "Interactive offence vs defence matchup deficiency matrix", "BLOCKED", "G-DEPTH", "Depth rank and slot for both sides of every matchup"),
    ("R-58", "Flag stale depth rows against the official transactions log", "PARTIAL", "G-SWEEP", "Every depth row dated and diffed against the transactions page"),
    ("R-59", "Point-in-time snapshot ledger for injuries, depth charts and inactives", "NOT STARTED", "G-AVAIL", "Immutable store with hashes outside the static site"),
    ("R-60", "Populate every missing game-status designation from the official article", "PARTIAL", "G-AVAIL", "0 blank game-status cells that the official article fills"),
    ("R-61", "Re-capture and republish the weekly injury tables", "DONE", "G-AVAIL", "Live row count published and reconciled to the committed capture"),
    ("R-62", "Reject deriving depth order from jersey number, experience or salary", "DONE", "G-DEPTH", "No depth row derived from a roster attribute"),
    ("R-63", "Represent shared and empty depth slots faithfully", "NOT STARTED", "G-DEPTH", "Shared-slot and empty-slot cases both represented"),
    ("R-64", "Resolve the depth-order source before building deficiency features", "NOT STARTED", "G-DEPTH", "One route verified for all 32 clubs"),
    ("R-65", "Score injury-designation reliability before using it as a feature", "NOT STARTED", "G-HISTORY", "Play rate per designation with confidence intervals"),
    ("R-66", "Durable snapshot storage and freshness alerts", "NOT STARTED", "G-OPS", "Captures stored outside the static site with a freshness monitor"),
    ("R-67", "Split the site into a public analysis layer and a private data layer", "NOT STARTED", "G-LEGAL", "Terms of use read and a storage decision recorded"),
    ("R-68", "Suggestions section with review before implementation", "DONE", "G-COORD", "Every proposal listed as a proposal; none implemented unreviewed"),
]

# --------------------------------------------------------------------------
# Standings reconciliation. Diffing the live standings against the earlier
# through-Week-9 capture shows which Week 10 games the league has folded in.
# 13 of the 14 were folded in; the Thursday game was not. This is an observed
# fact about two official pages, not an explanation of why.
#   club, wk9_record, live_record, wk9_pf, live_pf, wk9_pa, live_pa, included
# --------------------------------------------------------------------------
STANDINGS_RECON = [
    ("ATL", "3-6-0", "3-7-0", 188, 201, 223, 258, "yes"),
    ("AZ", "3-6-0", "3-7-0", 178, 184, 255, 289, "yes"),
    ("BAL", "4-5-0", "4-6-0", 189, 209, 236, 259, "yes"),
    ("BUF", "7-1-0", "8-1-0", 256, 287, 187, 199, "yes"),
    ("CAR", "3-5-0", "4-5-0", 199, 219, 219, 236, "yes"),
    ("CHI", "7-2-0", "7-2-0", 241, 241, 184, 184, "n/a - on bye in Week 10"),
    ("CIN", "6-2-0", "7-2-0", 240, 278, 175, 193, "yes"),
    ("CLE", "5-4-0", "6-4-0", 161, 188, 196, 220, "yes"),
    ("DAL", "4-5-0", "4-6-0", 246, 286, 236, 282, "yes"),
    ("DEN", "7-2-0", "7-2-0", 198, 198, 186, 186, "n/a - on bye in Week 10"),
    ("DET", "6-2-0", "7-2-0", 222, 257, 189, 199, "yes"),
    ("GB", "6-3-0", "6-4-0", 216, 226, 191, 221, "yes"),
    ("HOU", "3-5-0", "3-6-0", 209, 233, 192, 219, "yes"),
    ("IND", "2-7-0", "3-7-0", 184, 208, 249, 271, "yes"),
    ("JAX", "6-2-0", "7-2-0", 229, 269, 121, 144, "yes"),
    ("KC", "6-2-0", "7-2-0", 202, 237, 143, 156, "yes"),
    ("LAC", "0-8-0", "1-8-0", 121, 144, 219, 239, "yes"),
    ("LAR", "5-4-0", "6-4-0", 214, 248, 181, 187, "yes"),
    ("LV", "4-5-0", "4-6-0", 238, 251, 268, 289, "yes"),
    ("MIA", "1-7-0", "1-8-0", 126, 148, 200, 224, "yes"),
    ("MIN", "6-2-0", "7-2-0", 146, 176, 116, 126, "yes"),
    ("NE", "5-4-0", "5-5-0", 211, 221, 207, 242, "yes"),
    ("NO", "3-5-0", "3-6-0", 185, 202, 216, 236, "yes"),
    ("NYG", "5-3-1", "5-3-1", 203, 203, 196, 196, "NO - the Thu Nov 12 game is absent"),
    ("NYJ", "2-7-0", "2-8-0", 182, 194, 223, 254, "yes"),
    ("PHI", "2-7-0", "2-7-0", 148, 148, 221, 221, "n/a - on bye in Week 10"),
    ("PIT", "6-2-0", "6-3-0", 180, 198, 144, 182, "yes"),
    ("SEA", "5-4-0", "6-4-0", 202, 223, 162, 175, "yes"),
    ("SF", "7-1-0", "8-1-0", 235, 281, 156, 196, "yes"),
    ("TB", "3-6-0", "3-6-0", 202, 202, 178, 178, "n/a - on bye in Week 10"),
    ("TEN", "1-7-0", "1-8-0", 144, 167, 199, 239, "yes"),
    ("WAS", "3-5-1", "3-5-1", 196, 196, 223, 223, "NO - the Thu Nov 12 game is absent"),
]

# --------------------------------------------------------------------------
# Validation gates. Thresholds are project targets, not NFL-published facts.
#   id, gate, rule, what it blocks, current reading
# --------------------------------------------------------------------------
GATES = [
    ("G-PRICE", "Market price exists", "No fair-vs-market, CLV, ROI or staking figure is published until an approved price source class is recorded.", "R-01, R-04, R-18, R-38, R-39", "FAIL - nfl.com/odds is a 404 (verified 2026-11-17); no price anywhere in the repo"),
    ("G-PREREG", "Pre-registration", "Rule text, sample window and gates committed before the evaluation window opens; the commit hash is the registration.", "R-03, R-09, R-17, R-33, R-46", "PASS for Week 11 - model ATL-M1 committed before the Nov 19 kickoff"),
    ("G-RESULTS", "Verified results", "A result is published only when it is transcribed from an official box score or standings page.", "R-02, R-19, R-26", "PARTIAL - 150 games implied by the standings; 14 Week 10 finals transcribed this session"),
    ("G-AVAIL", "Two dated captures", "A designation delta is published only when two captures of the same report exist with fetch times.", "R-10, R-12, R-21, R-28, R-54, R-55, R-60, R-61", "FAIL - one capture; Week 11 designations do not exist yet"),
    ("G-DEPTH", "Depth from playing time", "No depth rank is published unless it comes from a dated official depth chart or an official snap count.", "R-06, R-11, R-25, R-29, R-30, R-31, R-50, R-51, R-52, R-56, R-57, R-62, R-63, R-64", "FAIL - no depth rank published anywhere on this module"),
    ("G-CORR", "Correlation provenance", "Every coefficient names its source page and its n.", "R-07", "PASS - see the correlation page"),
    ("G-LEADER", "Proper-score ranking", "Rank on benchmark-relative Brier skill with a cluster lower bound; two control baselines always shown.", "R-05, R-35, R-36, R-38, R-44, R-49", "PASS as a design; no strategy is eligible yet"),
    ("G-DEMOTE", "Demotion rule", "A live strategy returns to paper on any of four clauses.", "R-08", "PASS - rule committed"),
    ("G-ABLATE", "Ablation not penalty", "Personnel effects are reported as a with/without comparison with uncertainty, never as a settled points penalty.", "R-27, R-41", "PASS - base and personnel variants published together"),
    ("G-SWEEP", "32-club sweep", "Availability and depth evidence is versioned against the last official roster event for all 32 clubs.", "R-13, R-32, R-43, R-58", "FAIL - ad-hoc items for 16 clubs today"),
    ("G-FIXTURE", "Published schedule facts", "Fixture features come only from dated official pages.", "R-14, R-23, R-24", "PASS for Week 11 venues and kickoff times"),
    ("G-MODEL", "Probability plus inputs", "Every output row lists the inputs and the rule that produced it.", "R-15, R-41", "PASS"),
    ("G-LUCK", "Luck panel", "Residual SD and r-squared published with n.", "R-16", "PASS - n=32"),
    ("G-JOINT", "Joint evidence for combos", "A combo is ranked only with a validated joint probability and the operator's void/push rules.", "R-34", "FAIL - no joint probability validated; no combos ranked"),
    ("G-DIFF", "Weekly diff", "A what-changed column requires two consecutive snapshots.", "R-40", "FAIL - one snapshot"),
    ("G-DRIFT", "Drift alarm", "Each parser pins expected row counts and required fields; a missing field fails the build.", "R-42", "FAIL - not implemented for this module"),
    ("G-HISTORY", "Prior seasons", "Anything that needs a multi-season sample waits for that archive.", "R-45, R-47, R-53, R-65", "FAIL - 2026 only"),
    ("G-OPS", "Durable storage", "Captures live outside the static site with a freshness monitor.", "R-66", "FAIL"),
    ("G-LEGAL", "Terms read", "Raw row-level data stays private until the source terms are read.", "R-67", "FAIL - terms not read this session"),
    ("G-RULES", "Rulebook verified", "Regime changes are verified against the official rulebook page.", "R-48", "FAIL - not fetched this session"),
    ("G-WEATHER", "Weather overlay", "Roof designation joined to an NWS grid.", "R-37", "FAIL - not fetched this session"),
    ("G-COORD", "Coordination board", "Every task has an owner, a status and a file scope.", "R-22, R-68", "PASS - COORDINATION.md"),
]
