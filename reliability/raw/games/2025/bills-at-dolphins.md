# Game evidence capture — BUF at MIA, 2025 REG 10
# Session arena/73e6752d-x3, fetched 2026-11-17T23:08Z via page-fetch tool
# Sources (official nfl.com):
#   centre: https://www.nfl.com/games/bills-at-dolphins-2025-reg-10
#   game book: https://static.www.nfl.com/image/upload/v1762772748/gamecenter/f7d4b0eb-311e-11f0-b670-ae1250fadad1.pdf (7 chunks; chunk 0 + chunk 6 captured)

## Centre facts (verbatim key lines)
Buffalo Bills at Miami Dolphins 2025 REG 10 - Game Center
Final: Buffalo 13, Miami 30
Date shown: 2025 WEEK 10, Nov 9
Location: OPA LOCKA, FL — Stadium: HARD ROCK STADIUM

## Game Book chunk 0 — header + roster sections (verbatim; render mislabels — see note)
## National Football League Game Summary
NFL Copyright © 2025 by The National Football League. All rights reserved. This summary and play-by-play is for the express purpose of assisting media in their
coverage of the game; any other use of this material is prohibited without the written permission of the National Football League.
| Date: Sunday, 11/9/2025 |  | Buffalo Bills at Miami Dolphins at Hard Rock Stadium, Miami Gardens, FL |  |  |  | Start Time: 1:03 PM EST |  |
| Game Weather: Partly Cloudy Open Stadium on Natural Grass |  | Temp: 84° F (28.9° C) Humidity: 68%, Wind: SE 6 mph |  |  |  |  |  |
| Lineups |  |  |  |  |  |  |  |  |
| Buffalo Bills |  | Miami Dolphins |  |  |  |  |  |  |
[full lineups table present in source chunk 0; not reproduced — the join uses the lists below and Playtime Percentage]
| Substitutions |  |  |  |  | Substitutions |  |  |  |  |
| WR 1 C.Samuel, QB 11 M.Trubisky, K 15 M.Prater, WR 18 E.Moore, P 19 M.Wishnowsky, RB 22 R.Davis, CB 23 D.Jackson, RB 26 Ty.Johnson, DB 28 S.Franklin, DB 37 J.Hancock, FB 41 R.Gilliam, LB 42 D.Williams, LB 44 J.Andreessen, CB 46 J.Ingram, DT 52 J.Phillips, LB 54 B.Spector, DE 56 J.Solomon, C/G 62 S.Van Pran-Granger, LS 69 R.Ferguson, T 70 A.Anderson, DT 72 P.Mathis, T 74 R.Van Demark, TE 86 D.Kincaid, TE 88 D.Knox, DE 94 L.Jackson, DT 99 L.Ogunjobi |  |  |  |  | [MIA substitutions cell not rendered in the labelled row] |  |  |  |  |
| Did Not Play |  |  |  |  | Did Not Play |  |  |  |  |
| LB 3 K.Britt, RB 5 J.Wright, WR 6 M.Washington, LB 8 M.Judon, S 9 I.Melifonwu, P 16 J.Bailey, WR 19 C.Wilson, DB 22 E.Campbell, CB 27 E.Bonner, RB 31 O.Gordon, CB 33 J.Marshall, S 43 J.Colbert, CB 46 I.Johnson, K 47 R.Patterson, LS 49 J.Cardona, LB 53 C.Goode, LB 56 Q.Bell, T 70 K.Lamm, OL 71 K.Smith, WR 84 T.Washington, TE 85 G.Dulcich, TE 87 H.Rucci, DT 90 K.Grant, DT 91 M.Butler, DT 93 Z.Biggers |  |  |  |  |  |  |  |  |  |
| QB 0 Z.Wilson |  |  |  |  |  |  |  |  |
| Not Active |  |  |  |  | Not Active |  |  |  |  |
| WR 5 J.Palmer, CB 7 Ta.Johnson, CB 29 B.Codrington, OLB 45 S.Thompson, CB 47 C.Benford, DE 57 A.Epenesa, T 77 C.Lundt |  |  |  |  |  |  |  |  |

# NOT ACTIVE sets as parsed
BUF: J.Palmer, Ta.Johnson, B.Codrington, S.Thompson, C.Benford, A.Epenesa, C.Lundt (7)
MIA: (labelled MIA Not Active cell is EMPTY in the render; MIA's Not Active list appears AFTER
the Scoring Plays as an unlabelled paragraph:) 3QB 14 Q.Ewers, S 21 A.Davis, CB 26 R.Douglas,
LB 44 C.Robinson, LB 50 A.Carter, WR 82 D.Eskridge, TE 89 J.Hill (7)

# PARSING NOTE (irregularity, published on Flagged page):
# The 25-name list filed under the first "Did Not Play" cell contains only Dolphins players
# (verified: K.Britt, J.Wright, M.Washington, M.Judon, I.Melifonwu, O.Gordon, G.Dulcich and
# others all appear in the Dolphins playtime table with snaps, and in the Miami box score).
# Player-by-player evidence shows that list is the Dolphins' SUBSTITUTIONS block printed under
# the wrong label (the MIA substitutions cell is empty in the same row). It is parsed as
# substitutions — NOT as Did Not Play and NOT as Not Active — and flagged.
# "LB 44 C.Robinson" in the MIA Not Active paragraph: matched to report row "Chop Robinson"
# (LB) by initial+surname+position family only — the report page publishes no jersey numbers,
# so this match is flagged for human review and EXCLUDED from the inactive_rate as ambiguous.

## Playtime Percentage — designated-player rows (verbatim) + section facts
Section header present in chunk 6: "**Playtime Percentage** / Percent of playtime per player on offense, defense and special teams (Unofficial) / Buffalo Bills Miami Dolphins"; full table captured (46 data rows per side).
Rows (verbatim):
| T.Johnson | RB | 27 40% |  | 7 | 32% |   <- Ty Johnson (RB); NOT Taron Johnson (CB, Q) — different player, position families differ
| D.Kincaid | TE | 18 26% |  |  |  |
| O.Gordon | RB | 3 6% |  |  |  |
| I.Melifonwu | S |  | 36 53% |  |  |
| D.Jones | DT |  | 25 47% |  |  |
| B.Spector | LB |  |  | 14 | 64% |
(C.Benford, A.Epenesa, S.Thompson, J.Palmer (BUF) and A.Davis, R.Douglas, D.Eskridge, J.Hill (MIA) were Not Active — no playtime rows. Taron Johnson (BUF, CB, Q) has NO playtime row — the "T.Johnson RB" row is Ty Johnson and does not match by position family.)
