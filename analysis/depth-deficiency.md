# Depth-deficiency rule R-1

Requirement: *know any deficiencies in defenses such as 2nd/3rd/4th string backups
having to replace starters due to lineups — same for offenses.*

## Rule

A team–position group is **flagged** when either:

1. **Count test:** 2+ players from the group are unavailable per the verified injury
   board (game-day Out/Doubtful rows + the line-moving IR subset), or
2. **Chart test:** a captured depth chart shows an availability-tagged (IR/O) player
   inside the top two strings of the group.

## String-level claims policy

"2nd/3rd/4th string replacing starter" is stated **only** when a depth chart or a
cited report verifies the string. As of 2026-11-14 that means PIT and BAL only
(RotoWire-via-ESPN charts — trusted, not official; flag F-05). For every other team
the replacement string is left blank and the source cell shows an UNVERIFIED badge.

Worked examples (all chart-verified):

- **BAL QB:** Lamar Jackson (IR) is listed 4th behind Jacoboby Brissett (starter),
  Joe Fagnano (2nd), Kedon Slovis (3rd); Tyler Huntley and Skylar Thompson are also
  on IR but not on the chart → the room is running on its backup and two depth QBs.
- **PIT WR:** Roman Wilson (3rd, IR) and Michael Pittman Jr. (2nd, IR) behind
  Ben Skowronek → a 3rd-string-level WR group.
- **PIT NT:** starter Keeanu Benton's only listed backup (Sebastian Joseph-Day) is
  on IR → no listed backup.
- **SEA QB:** Sam Darnold out; Drew Lock starts per cited ESPN report.

## Outputs

- `x3lab/data/deficiencies.json` — 24 flagged groups for Week 10.
- `x3lab/depth.html` — rendered tables.

## Next step

Automate official depth-chart + gamebook pulls for all 32 teams (SUG-06) so every
string claim can be chart-verified, then re-run R-1 weekly with snap counts (Q-08).
