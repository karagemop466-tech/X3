"""Line-by-line comparison: stored capture CSV vs live official page (reg11, Thu IND@HOU).

Live values were transcribed from the fetch of https://www.nfl.com/injuries/league/2026/reg11
(chunk 0, fetched 2026-11-19T22:02:09Z). Blank page cells are recorded as ''.
Stored values come from data/live/week11_injuries.csv (built from the 2026-11-19T02:16:10Z capture).
"""
import csv, hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
URL = "https://www.nfl.com/injuries/league/2026/reg11"
LIVE_FETCH_UTC = "2026-11-19T22:02:09Z"
STORED_CAPTURE_UTC = "2026-11-19T02:16:10Z"
RAW = ROOT / "readiness/data/history/2026-11-19/league-injury-report.bin"

# (team, player) -> (injuries, practice status, game status) as rendered on the live page
LIVE = {
 ("IND","Jaylon Carlies"): ("", "Did Not Participate In Practice", ""),
 ("IND","Sauce Gardner"): ("Calf", "Did Not Participate In Practice", "Questionable"),
 ("IND","Anthony Gould"): ("Toe", "Full Participation in Practice", "Questionable"),
 ("IND","Charlie Heck"): ("", "Did Not Participate In Practice", ""),
 ("IND","Will Mallory"): ("Hamstring", "Did Not Participate In Practice", "Out"),
 ("IND","Bernhard Raimann"): ("Concussion", "Did Not Participate In Practice", "Out"),
 ("IND","Luke Rhodes"): ("Hamstring", "Limited Participation in Practice", "Questionable"),
 ("IND","Jerry Tillery"): ("Calf", "Did Not Participate In Practice", "Out"),
 ("IND","Jalen Travis"): ("Knee", "Did Not Participate In Practice", "Out"),
 ("IND","Dalton Tucker"): ("", "Full Participation in Practice", ""),
 ("IND","Charvarius Ward"): ("Knee", "Did Not Participate In Practice", "Out"),
 ("HOU","Azeez Al-Shaair"): ("", "Did Not Participate In Practice", ""),
 ("HOU","Reed Blankenship"): ("", "Full Participation in Practice", ""),
 ("HOU","Tank Dell"): ("", "Full Participation in Practice", ""),
 ("HOU","Blake Fisher"): ("", "Full Participation in Practice", ""),
 ("HOU","Marvin Harrison Jr."): ("Hamstring", "Did Not Participate In Practice", "Out"),
 ("HOU","Jacob Hummel"): ("Groin", "Full Participation in Practice", "Questionable"),
 ("HOU","Danielle Hunter"): ("Hamstring", "Did Not Participate In Practice", "Out"),
 ("HOU","Brevin Jordan"): ("Foot, Illness", "Did Not Participate In Practice", "Out"),
 ("HOU","Kamari Lassiter"): ("", "Full Participation in Practice", ""),
 ("HOU","Woody Marks"): ("Concussion", "Did Not Participate In Practice", "Out"),
 ("HOU","David Montgomery"): ("", "Full Participation in Practice", ""),
 ("HOU","Febechi Nwaiwu"): ("", "Full Participation in Practice", ""),
 ("HOU","Keylan Rutledge"): ("", "Full Participation in Practice", ""),
 ("HOU","Jaylin Smith"): ("Hamstring", "Full Participation in Practice", "Questionable"),
 ("HOU","Wyatt Teller"): ("Back", "Full Participation in Practice", "Questionable"),
}

rows, stored_keys = [], set()
with open(ROOT / "data/live/week11_injuries.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["game_id"] != "IND@HOU":
            continue
        key = (r["team"], r["player"])
        stored_keys.add(key)
        s = (r["injury"], r["practice_status"], r["game_status"])
        live = LIVE.get(key)
        if live is None:
            result = "NOT ON LIVE BLOCK"
        else:
            diffs = [n for n, a, b in zip(("injury", "practice", "game"), s, live) if a != b]
            result = "MATCH" if not diffs else "DELTA: " + ",".join(diffs)
        rows.append({
            "team": r["team"], "player": r["player"],
            "stored_injury": s[0], "stored_practice": s[1], "stored_game_status": s[2],
            "live_injury": live[0] if live else "", "live_practice": live[1] if live else "",
            "live_game_status": live[2] if live else "",
            "result": result, "stored_capture_utc": STORED_CAPTURE_UTC,
            "live_fetch_utc": LIVE_FETCH_UTC, "source_url": URL,
        })

missing_from_stored = sorted(set(LIVE) - stored_keys)
out = ROOT / "data/fresh_check/ind_hou_thu_2026_11_19_compare.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

summary = {
    "game": "IND@HOU (Thu 2026-11-19, Week 11)",
    "source_url": URL,
    "stored_capture_utc": STORED_CAPTURE_UTC,
    "stored_capture_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
    "live_fetch_utc": LIVE_FETCH_UTC,
    "rows_compared": len(rows),
    "match": sum(r["result"] == "MATCH" for r in rows),
    "delta": [f"{r['team']} {r['player']}: {r['result']}" for r in rows if r["result"] != "MATCH"],
    "live_names_missing_from_stored": [f"{t} {n}" for t, n in missing_from_stored],
    "note": ("Only the live page's rendered table was compared (markdown rendering). "
             "The stored capture's Heck injury text is confirmed in the raw bytes; the live rendered cell is blank."),
}
(ROOT / "data/fresh_check/ind_hou_thu_2026_11_19_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
