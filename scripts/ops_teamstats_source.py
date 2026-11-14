#!/usr/bin/env python3
"""Official 2026 team passing offense/defense, transcribed from nfl.com on 2026-11-14.

Two pages, same column order, independent capture:
  offense gained : https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all
  defense allowed: https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all
A league must gain exactly what its opponents allow, so the script asserts the five column
sums agree across the two pages before writing data/ops/reference/teamstats.json. That makes
a transcription error in either table impossible to publish silently.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLS = ["att", "cmp", "cmp_pct", "yds_att", "yds", "td", "int", "rate", "first", "first_pct", "twenty", "forty", "lng", "sck"]

OFFENSE = """SF 236 163 69.1 8.4 1980 17 5 109.8 97 41.1 27 4 82T 8
CHI 312 211 67.6 7.4 2310 10 9 88 108 34.6 35 4 58T 20
CIN 296 219 74 8.1 2386 23 6 114.8 119 40.2 27 5 47T 15
BUF 236 156 66.1 8.6 2027 12 6 99.3 93 39.4 32 8 57 17
DEN 287 174 60.6 6 1730 11 4 84.7 85 29.6 21 4 52T 11
CLE 283 185 65.4 7.4 2105 9 3 93.7 93 32.9 28 5 64T 38
TB 240 146 60.8 5.9 1423 6 9 70.2 67 27.9 16 5 64 27
AZ 359 232 64.6 5.8 2080 13 7 84 110 30.6 19 0 38 23
LAC 243 146 60.1 6.6 1615 7 11 70.6 71 29.2 18 6 58 31
KC 263 177 67.3 7.8 2037 14 4 101.8 94 35.7 22 7 73T 11
IND 304 184 60.5 5.7 1730 6 10 69.1 86 28.3 18 3 55T 25
WAS 299 187 62.5 6.8 2025 15 3 95 95 31.8 29 5 53 21
DAL 336 218 64.9 7.1 2381 16 5 95.4 119 35.4 28 6 53 14
MIA 209 122 58.4 6.9 1442 6 6 77.1 64 30.6 18 5 77T 24
PHI 303 179 59.1 5.7 1740 10 6 78 81 26.7 14 3 64 30
ATL 256 156 60.9 6.9 1766 11 12 76.4 74 28.9 23 4 76 16
NYG 304 188 61.8 7.2 2193 13 7 88.3 101 33.2 30 6 66T 28
JAX 227 147 64.8 8.6 1940 18 4 110.8 91 40.1 27 4 52 13
NYJ 271 183 67.5 7.7 2078 12 3 100.4 89 32.8 24 9 60 28
DET 274 186 67.9 7.8 2145 15 2 106.5 104 38 23 5 57 19
GB 341 215 63 7.7 2618 19 6 97.9 110 32.3 40 12 81T 17
CAR 313 189 60.4 7.2 2244 16 6 91.3 111 35.5 28 4 55 26
NE 281 183 65.1 8.4 2349 18 11 96.2 102 36.3 33 6 63 20
LV 324 209 64.5 7.4 2401 20 8 97 121 37.4 31 5 45 11
LA 349 232 66.5 6.8 2387 16 9 90.5 122 35 24 6 64 13
BAL 247 165 66.8 7.5 1842 10 5 93.9 90 36.4 20 6 54 23
NO 308 204 66.2 6.4 1986 14 6 91.2 99 32.1 21 5 52 20
SEA 288 182 63.2 7.2 2089 15 9 89.3 109 37.8 24 4 82 19
PIT 290 175 60.3 6.4 1871 13 6 85.6 82 28.3 24 6 80T 23
HOU 285 182 63.9 7.9 2258 16 2 104.1 98 34.4 32 7 63T 16
TEN 248 155 62.5 6 1483 6 5 78.8 73 29.4 16 1 41 13
MIN 225 137 60.9 6.4 1437 8 5 82 68 30.2 19 2 51T 23"""

DEFENSE = """AZ 258 166 64.3 8 2076 19 3 108.9 92 35.7 25 6 82T 19
LA 293 179 61.1 6.4 1882 11 7 82.3 93 31.7 21 6 57 16
GB 325 203 62.5 6.4 2087 13 13 77.6 101 31.1 22 4 68 26
DAL 296 194 65.5 7.2 2133 16 4 99.1 106 35.8 28 4 64 17
LV 279 183 65.6 8 2238 20 7 103.6 112 40.1 27 6 55 19
CAR 278 176 63.3 6.4 1774 12 5 88.3 92 33.1 14 4 57 12
CHI 260 161 61.9 8.2 2120 13 7 93.1 88 33.8 26 12 58T 26
NO 261 171 65.5 7.8 2045 13 4 99.6 91 34.9 28 6 64T 23
IND 264 162 61.4 8.1 2145 16 2 104.1 89 33.7 30 11 80T 19
NYG 286 179 62.6 6.2 1763 17 8 88.1 89 31.1 20 2 64 17
PHI 300 180 60 7.2 2150 13 3 92.2 102 34 31 4 53 16
WAS 332 217 65.4 7 2341 17 6 95.5 110 33.1 29 4 66T 18
CIN 273 174 63.7 7.3 1989 9 5 88.9 93 34.1 26 2 48T 23
PIT 280 183 65.4 6.9 1936 7 7 83.3 88 31.4 27 4 63 26
SEA 277 178 64.3 5.5 1519 9 8 77.3 73 26.4 14 1 44 21
DEN 344 207 60.2 6.5 2249 14 8 83.4 106 30.8 26 6 73T 26
HOU 276 178 64.5 7.4 2056 12 4 95.3 91 33 31 7 58T 29
CLE 297 177 59.6 6.7 1982 12 6 84.6 88 29.6 26 5 58 26
NE 286 193 67.5 7.9 2256 14 5 100.2 99 34.6 32 7 58 25
DET 313 203 64.9 7.2 2265 18 6 97.5 114 36.4 34 6 51 27
NYJ 270 174 64.4 7.1 1909 16 1 103.5 98 36.3 23 4 63T 22
KC 276 170 61.6 6.4 1764 7 6 79.4 88 31.9 20 5 57 14
ATL 318 210 66 6.8 2171 14 3 96.3 108 34 26 5 55 20
TEN 272 193 71 8 2182 11 8 95.9 105 38.6 30 2 52 20
BAL 287 187 65.2 7.6 2177 12 4 96.1 102 35.5 26 7 52 17
LAC 233 153 65.7 7.9 1845 13 7 95.9 85 36.5 23 5 63T 13
TB 307 190 61.9 6.6 2040 12 16 72.7 86 28 21 6 76 17
BUF 300 183 61 6.7 2022 15 6 89.3 107 35.7 28 1 44T 17
SF 280 188 67.1 6.4 1783 11 6 88.7 86 30.7 18 2 77T 15
JAX 261 172 65.9 7.3 1907 8 11 80.1 89 34.1 21 5 62T 16
MIN 234 135 57.7 6.4 1495 5 9 67.9 68 29.1 16 5 81T 29
MIA 221 168 76 8.1 1797 16 5 114 87 39.4 22 8 60 12"""


def parse(block):
    out = []
    for line in block.strip().split("\n"):
        p = line.split()
        assert len(p) == 15, p
        row = {"team": p[0]}
        for c, v in zip(COLS, p[1:]):
            row[c] = v if c in ("cmp_pct", "yds_att", "rate", "first_pct", "lng") else int(v)
        out.append(row)
    return out


def main():
    off, dfn = parse(OFFENSE), parse(DEFENSE)
    assert len(off) == 32 and len(dfn) == 32
    for col in ("att", "cmp", "yds", "td", "int", "sck"):
        a = sum(r[col] for r in off)
        b = sum(r[col] for r in dfn)
        assert a == b, f"league {col} does not reconcile across the two official pages: {a} != {b}"
    out = {
        "as_of": "2026-11-14",
        "season": 2026,
        "url_off": "https://www.nfl.com/stats/team-stats/offense/passing/2026/reg/all",
        "url": "https://www.nfl.com/stats/team-stats/defense/passing/2026/reg/all",
        "columns": COLS,
        "offense_passing": off,
        "defense_passing": dfn,
        "reconciliation": {c: {"offense": sum(r[c] for r in off), "defense": sum(r[c] for r in dfn)}
                           for c in ("att", "cmp", "yds", "td", "int", "sck")},
        "note": ("Both pages are official and independently published; a league must gain exactly what its "
                 "opponents allow, so the six column sums reconciling is the transcription check."),
    }
    p = os.path.join(ROOT, "data", "ops", "reference", "teamstats.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("teamstats written:", len(off), "offense,", len(dfn), "defense; six column sums reconcile")


if __name__ == "__main__":
    main()
