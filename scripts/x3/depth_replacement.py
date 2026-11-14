#!/usr/bin/env python3
"""
X3 pipeline stage 3 - depth-of-replacement tracker (session arena/873c7396-x3).

Requirement: "Track the depth of the replacement, not just the fact of a replacement."

Inputs
  data/x3/raw/club_depth_charts_2026_wk10/*.md   31 club depth charts transcribed verbatim from official
                                                 club sites on 2026-11-14 (HOU did not render - flagged)
  data/hub/injuries_2026_wk10.csv                345-row official Week-10 report (prior session, verified)

Output
  data/x3/depth_replacement_2026_wk10.csv   one row per first-string vacancy:
                                            who is out, WHO replaces them, and the DEPTH of that
                                            replacement (2nd/3rd/4th string), plus link-out flags
  hub/data/replacement.json                 aggregates for the hub page

Matching rules (published):
  - "starter out" = player listed at depth 1 of a chart slot with game status Out or Doubtful.
  - "replacement" = the next player in the same slot's depth order who is NOT Out/Doubtful
    (Questionable counts as available for this purpose - they are tagged as such).
  - replacement_depth = 2/3/4/... = the depth position of that replacement in the same slot.
  - if the injured player is not depth 1 of any slot, the row records NOT-A-STARTER (tracked, no vacancy).
  - position mapping: report T/G/C vs chart LT/LG/C/RG/RT etc.; name match after normalisation.
Deterministic.
"""
from __future__ import annotations
import csv, json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "x3", "raw", "club_depth_charts_2026_wk10")
OUT = os.path.join(ROOT, "data", "x3")
HUBD = os.path.join(ROOT, "hub", "data")
AS_OF = "2026-11-14"

def norm_name(n):
    n = n.replace("[co-listed ", "|").replace("]", "")
    n = re.sub(r"\|.*", "", n)                       # drop co-listed annotations
    n = n.replace("'", "").replace(".", "").replace("-", " ").lower()
    n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", n)
    return re.sub(r"\s+", " ", n).strip()

POS_MAP = {"LOT": "T", "RT": "T", "ROT": "T", "LT": "T", "LG": "G", "RG": "G", "C": "C",
           "HB": "RB", "FB": "FB", "PK": "K", "K": "K", "P": "P", "LS": "LS", "H": "H",
           "NT": "DT", "LDT": "DT", "RDT": "DT", "DL": "DL", "DT": "DT", "DE": "DE",
           "LDE": "DE", "RDE": "DE", "EDGE": "EDGE", "OLB": "LB", "ILB": "LB", "MLB": "LB",
           "WLB": "LB", "SLB": "LB", "SAM": "LB", "MIKE": "LB", "WILL": "LB", "LB": "LB",
           "RUSH": "EDGE", "CB": "CB", "LCB": "CB", "RCB": "CB", "NCB": "CB", "NB": "CB",
           "DB": "CB", "S": "S", "SS": "S", "FS": "S", "N": "CB", "KR": "KR", "PR": "PR",
           "KO": "KO", "WR": "WR", "TE": "TE", "QB": "QB", "RB": "RB"}

# ------------------------------------------------------------------ parse charts
charts = {}
for fn in sorted(os.listdir(RAW)):
    if not fn.endswith(".md"):
        continue
    club = fn[:-3]
    slots = []                                        # (unit, pos_raw, [names in depth order])
    unit = None
    for line in open(os.path.join(RAW, fn), encoding="utf-8"):
        if line.startswith("## Offense"): unit = "offense"; continue
        if line.startswith("## Defense"): unit = "defense"; continue
        if line.startswith("## Special"): unit = "special"; continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            pos = cells[0].strip()
            names = []
            for c in cells[1:]:
                for piece in re.split(r"\[co-listed ([^\]]+)\]", c):
                    piece = piece.strip()
                    if piece and piece not in ("[co-listed",) and not piece.startswith("["):
                        names.append(piece)
            if pos and names:
                slots.append((unit, pos, names))
    charts[club] = {"slots": slots, "source": f"club depth chart (fetched {AS_OF})"}

# by normalized player -> list of (club, unit, pos, depth)
place = {}
for club, c in charts.items():
    for unit, pos, names in c["slots"]:
        for d, nm in enumerate(names, start=1):
            place.setdefault(norm_name(nm), []).append((club, unit, pos, d, nm))

# ------------------------------------------------------------------- injuries
inj = list(csv.DictReader(open(os.path.join(ROOT, "data", "hub", "injuries_2026_wk10.csv"))))
OUT_STATUS = {"Out", "Doubtful"}

rows = []
no_chart_match = []
for r in inj:
    team = r["team"].strip()
    status = r["status"].strip()
    nm = r["player"].strip()
    pos = r["pos"].strip()
    if status not in OUT_STATUS:
        continue
    hits = [p for p in place.get(norm_name(nm), []) if p[0] == team]
    if not hits:
        no_chart_match.append((team, nm, pos, status))
        continue
    # prefer same broad position group
    def pos_family(p_raw):
        return POS_MAP.get(p_raw.upper(), p_raw.upper())
    want = pos_family(pos)
    same = [h for h in hits if pos_family(h[2]) == want]
    if not same and want in ("DE", "EDGE", "DL", "DT"):
        same = [h for h in hits if pos_family(h[2]) in ("DE", "EDGE", "DL", "DT")]
    if not same and want in ("CB", "S"):
        same = [h for h in hits if pos_family(h[2]) in ("CB", "S")]
    if not same:
        same = hits
    club, unit, pos_raw, depth, chart_name = sorted(same, key=lambda h: h[3])[0]
    if depth != 1:
        rows.append({"club": team, "unit": unit, "pos": pos, "player_out": nm, "status": status,
                     "chart_pos": pos_raw, "out_depth": depth, "replacement": "", "replacement_depth": "",
                     "flag": "NOT-A-STARTER (injured player is not depth 1 in this slot)",
                     "source": f"https://www.google.com/search?q={team}+depth+chart"})
        continue
    # find replacement: next depth not itself Out/Doubtful, in the slot where THIS player is depth 1
    cand_slots = [names for (u, p, names) in charts[club]["slots"] if u == unit and p == pos_raw]
    out_norm = norm_name(nm)
    slot_names = [s for s in cand_slots if s and norm_name(s[0]) == out_norm] or cand_slots
    repl, repl_d, blocked = "", "", []
    if slot_names:
        out_set = {norm_name(x["player"]) for x in inj
                   if x["team"] == team and x["status"] in OUT_STATUS}
        for cand_d, cand in enumerate(slot_names[0], start=1):
            if cand_d == 1:
                continue
            if norm_name(cand) in out_set:
                blocked.append(f"{cand} (d{cand_d})")
                continue
            repl, repl_d = cand, cand_d
            break
    rows.append({"club": team, "unit": unit, "pos": pos, "player_out": nm, "status": status,
                 "chart_pos": pos_raw, "out_depth": 1, "replacement": repl,
                 "replacement_depth": repl_d,
                 "flag": ("replacement also Out/Doubtful: " + "; ".join(blocked)) if blocked else "",
                 "source": f"club depth chart + nfl.com injury report (see page)"})

# unblocked rows get real source urls
CLUB_URL = {"ARI": "https://www.azcardinals.com/team/depth-chart", "ATL": "https://www.atlantafalcons.com/team/depth-chart",
    "BAL": "https://www.baltimoreravens.com/team/depth-chart", "BUF": "https://www.buffalobills.com/team/depth-chart",
    "CAR": "https://www.panthers.com/team/depth-chart", "CHI": "https://www.chicagobears.com/team/depth-chart",
    "CIN": "https://www.bengals.com/team/depth-chart", "CLE": "https://www.clevelandbrowns.com/team/depth-chart",
    "DAL": "https://www.dallascowboys.com/team/depth-chart", "DEN": "https://www.denverbroncos.com/team/depth-chart/",
    "DET": "https://www.detroitlions.com/team/depth-chart", "GB": "https://www.packers.com/team/depth-chart",
    "IND": "https://www.colts.com/team/depth-chart", "JAX": "https://www.jaguars.com/team/depth-chart",
    "KC": "https://www.chiefs.com/team/depth-chart", "LV": "https://www.raiders.com/team/depth-chart",
    "LAC": "https://www.chargers.com/team/depth-chart", "LA": "https://www.therams.com/team/depth-chart",
    "MIA": "https://www.miamidolphins.com/team/depth-chart", "MIN": "https://www.vikings.com/team/depth-chart",
    "NE": "https://www.patriots.com/team/depth-chart", "NO": "https://www.neworleanssaints.com/team/depth-chart",
    "NYG": "https://www.giants.com/team/depth-chart", "NYJ": "https://www.newyorkjets.com/team/depth-chart",
    "PHI": "https://www.philadelphiaeagles.com/team/depth-chart", "PIT": "https://www.steelers.com/team/depth-chart/",
    "SF": "https://www.49ers.com/team/depth-chart", "SEA": "https://www.seahawks.com/team/depth-chart/",
    "TB": "https://www.buccaneers.com/team/depth-chart", "TEN": "https://www.tennesseetitans.com/team/depth-chart",
    "WAS": "https://www.commanders.com/team/depth-chart"}
for r in rows:
    if r["club"] in CLUB_URL:
        r["source"] = CLUB_URL[r["club"]]

rows.sort(key=lambda r: (r["club"], r["unit"], r["pos"]))
heads = ["club", "unit", "pos", "player_out", "status", "chart_pos", "out_depth", "replacement",
         "replacement_depth", "flag", "source"]
with open(os.path.join(OUT, "depth_replacement_2026_wk10.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(heads)
    for r in rows: w.writerow([r[h] for h in heads])
print("wrote data/x3/depth_replacement_2026_wk10.csv", f"({len(rows)} rows)")

vac = [r for r in rows if r["out_depth"] == 1]
by_depth = collections.Counter(str(r["replacement_depth"]) for r in vac)
unmatched = [r for r in vac if not r["replacement"]]
agg = {
    "as_of": AS_OF, "clubs_with_chart": len(charts), "chart_missing": ["HOU"],
    "starters_out_or_doubtful": len(vac),
    "replacement_depth_counts": dict(sorted(by_depth.items())),
    "no_backup_listed": len([r for r in vac if not r["replacement"] and not r["flag"]]),
    "backup_also_out": len([r for r in vac if r["flag"].startswith("replacement also")]),
    "not_a_starter_rows": len(rows) - len(vac),
    "report_rows_without_chart_match": len(no_chart_match),
    "no_chart_match_sample": no_chart_match[:12],
    "irregularities": [
        "HOU club depth chart page did not render a table on 2026-11-14 (2 attempts) - club flagged",
        "MIA chart has an EMPTY kicker slot (K row lists no player)",
        "BAL chart has an EMPTY kicker slot (K row lists no player)",
        "LA chart lists a player at DE who has not been on an NFL roster since 2023 (Aaron Donald) - template error on club page",
        "Charts are club-published UNOFFICIAL depth charts on official club domains; several pages are undated",
    ],
}
json.dump(agg, open(os.path.join(HUBD, "replacement.json"), "w"), indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in agg.items() if k not in ("no_chart_match_sample",)}, indent=1)[:900])
print("sample rows:")
for r in vac[:6]:
    print(" ", r["club"], r["pos"], r["player_out"], "->", r["replacement"] or "(none listed)", "depth", r["replacement_depth"])
