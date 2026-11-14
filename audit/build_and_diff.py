"""Independent audit of the 2026 Week 10 injury dataset in this repo.

Inputs (official NFL.com, fetched 2026-11-14):
  audit/official_injury_wk10_2026.raw.txt  hand transcription of
      https://www.nfl.com/injuries/league/2026/reg10  (8 chunks)
  SCHEDULE below                           transcription of
      https://www.nfl.com/schedules/2026/by-week/week-10  (3 chunks)
Repo dataset compared: docs/data/injury-2026-week10.csv

Standard library only. Writes audit/official_injury_wk10_2026.csv,
audit/schedule_check_wk10.csv, audit/diff_report.csv, audit/summary.json.
"""
import csv, json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "audit"
RAW = AUDIT / "official_injury_wk10_2026.raw.txt"
EXISTING = ROOT / "docs" / "data" / "injury-2026-week10.csv"
INJURY_URL = "https://www.nfl.com/injuries/league/2026/reg10"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/by-week/week-10"
FETCHED = "2026-11-14"

PRACTICE_SHORT = {
    "Full Participation in Practice": "Full",
    "Limited Participation in Practice": "Limited",
    "Did Not Participate In Practice": "DNP",
    "": "",
}

# Official schedule (away, home, day, time ET, network as printed, note, game page slug).
# Away/home follow the schedule headline "<away> at <home>".
SCHEDULE = [
    ("WAS", "NYG", "Thu Nov 12", "8:15 PM", "Thursday Night Football", "", "commanders-at-giants-2026-reg-10"),
    ("NE", "DET", "Sun Nov 15", "9:30 AM", "FOX", "International Game: Munich", "patriots-at-lions-2026-reg-10"),
    ("KC", "ATL", "Sun Nov 15", "1:00 PM", "CBS", "", "chiefs-at-falcons-2026-reg-10"),
    ("MIN", "GB", "Sun Nov 15", "1:00 PM", "FOX", "", "vikings-at-packers-2026-reg-10"),
    ("JAX", "TEN", "Sun Nov 15", "1:00 PM", "FOX", "", "jaguars-at-titans-2026-reg-10"),
    ("BUF", "NYJ", "Sun Nov 15", "1:00 PM", "CBS", "", "bills-at-jets-2026-reg-10"),
    ("MIA", "IND", "Sun Nov 15", "1:00 PM", "CBS", "", "dolphins-at-colts-2026-reg-10"),
    ("CAR", "NO", "Sun Nov 15", "1:00 PM", "FOX", "", "panthers-at-saints-2026-reg-10"),
    ("HOU", "CLE", "Sun Nov 15", "1:00 PM", "FOX", "", "texans-at-browns-2026-reg-10"),
    ("LAR", "AZ", "Sun Nov 15", "4:05 PM", "CBS", "", "rams-at-cardinals-2026-reg-10"),
    ("SEA", "LV", "Sun Nov 15", "4:05 PM", "CBS", "", "seahawks-at-raiders-2026-reg-10"),
    ("SF", "DAL", "Sun Nov 15", "4:25 PM", "FOX", "", "49ers-at-cowboys-2026-reg-10"),
    ("PIT", "CIN", "Sun Nov 15", "8:20 PM", "NBC", "", "steelers-at-bengals-2026-reg-10"),
    ("LAC", "BAL", "Mon Nov 16", "8:15 PM", "ESPN", "", "chargers-at-ravens-2026-reg-10"),
]
SCHEDULE_BYES = ["CHI", "DEN", "PHI", "TB"]
SCHED_BY_TEAM = {}
for away, home, *_ in SCHEDULE:
    SCHED_BY_TEAM[away] = (away, home)
    SCHED_BY_TEAM[home] = (away, home)

# ---------- 1. parse the hand transcription ----------
games_on_report, records, rows = {}, {}, []
for line in RAW.read_text().splitlines():
    if not line or line.startswith("#"):
        continue
    if line.startswith("@GAME|"):
        _, a, b, kick, tv = line.split("|")
        for t in (a, b):
            games_on_report[t] = {"listed": (a, b), "kickoff": kick, "tv": tv}
    elif line.startswith("@REC|"):
        _, t, rec = line.split("|")
        records[t] = rec
    else:
        team, player, pos, injury, practice, game_status = line.split("|")
        rows.append(dict(team=team, player=player, position=pos, injury=injury,
                         practice=practice, game_status=game_status))

assert len(rows) == 345, len(rows)
assert set(r["team"] for r in rows) <= set(records)
assert len(records) == 28 and set(records) == set(games_on_report)

# ---------- 2. official rows in repo column layout ----------
official = []
for r in rows:
    g = games_on_report[r["team"]]
    away, home = SCHED_BY_TEAM[r["team"]]
    official.append({
        "game": f"{away} @ {home}",
        "kickoff_et": g["kickoff"],
        "tv": g["tv"],
        "team": r["team"],
        "team_record": records[r["team"]],
        "player": r["player"],
        "position": r["position"],
        "injury": r["injury"],
        "practice_status": PRACTICE_SHORT[r["practice"]],
        "game_status": r["game_status"],
        "source_url": INJURY_URL,
    })

def write_csv(path, data):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader(); w.writerows(data)

write_csv(AUDIT / "official_injury_wk10_2026.csv", official)

# ---------- 3. schedule check (orientation, kickoff, network) ----------
sched_rows = []
for away, home, day, time, net, note, slug in SCHEDULE:
    key_kick = None
    on_report = games_on_report.get(away)
    if on_report is not None:
        key_kick = on_report["kickoff"]
        report_tv = on_report["tv"]
    else:
        report_tv = ""
    sched_rows.append({
        "game": f"{away} @ {home}",
        "schedule_day": day,
        "schedule_time_et": time,
        "schedule_network": net,
        "schedule_note": note,
        "injury_report_kickoff_et": key_kick or "",
        "injury_report_tv": report_tv,
        "game_page": f"https://www.nfl.com/games/{slug}",
        "source_url": SCHEDULE_URL,
    })
write_csv(AUDIT / "schedule_check_wk10.csv", sched_rows)

# ---------- 4. diff against the repo dataset ----------
with open(EXISTING, newline="") as f:
    existing = list(csv.DictReader(f))

ex = {}
dup_keys = 0
for r in existing:
    k = (r["team"].strip(), r["player"].strip())
    if k in ex:
        dup_keys += 1
    ex[k] = r
off = {(r["team"], r["player"]): r for r in official}

COMPARE = ["team_record", "position", "injury", "practice_status", "game_status",
           "game", "kickoff_et", "tv"]
report = []
field_counts = collections.Counter()
for k, o in off.items():
    e = ex.get(k)
    if e is None:
        report.append(dict(team=k[0], player=k[1], result="MISSING_IN_REPO", fields="", detail=""))
        field_counts["MISSING_IN_REPO"] += 1
        continue
    diffs, details = [], []
    for f in COMPARE:
        ev = (e.get(f) or "").strip()
        ov = o[f]
        if ev != ov:
            diffs.append(f)
            field_counts[f] += 1
            details.append(f"{f}: repo='{ev}' official='{ov}'")
    report.append(dict(team=k[0], player=k[1],
                       result="MATCH" if not diffs else "DIFF",
                       fields=";".join(diffs), detail=" | ".join(details)))

for k in ex:
    if k not in off:
        report.append(dict(team=k[0], player=k[1], result="EXTRA_IN_REPO", fields="", detail=""))
        field_counts["EXTRA_IN_REPO"] += 1

with open(AUDIT / "diff_report.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["team", "player", "result", "fields", "detail"])
    w.writeheader(); w.writerows(report)

counts = collections.Counter(r["result"] for r in report)
repo_sources = collections.Counter(r["source_url"] for r in existing)
summary = dict(
    fetched=FETCHED,
    injury_source=INJURY_URL,
    schedule_source=SCHEDULE_URL,
    official_rows=len(official),
    repo_rows=len(existing),
    repo_duplicate_keys=dup_keys,
    row_results=dict(counts),
    field_mismatch_counts=dict(field_counts),
    official_status_counts={
        "Out": sum(1 for o in official if o["game_status"] == "Out"),
        "Doubtful": sum(1 for o in official if o["game_status"] == "Doubtful"),
        "Questionable": sum(1 for o in official if o["game_status"] == "Questionable"),
        "blank_game_status": sum(1 for o in official if o["game_status"] == ""),
    },
    repo_source_url_values=dict(repo_sources),
    schedule_games=len(SCHEDULE),
    schedule_byes=SCHEDULE_BYES,
)
(AUDIT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
