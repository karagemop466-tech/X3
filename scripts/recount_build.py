#!/usr/bin/env python3
"""
Week-10 official injury report: full recount build (session arena/d6d831c6-x3).

Input  : data/recount/reg10_2026_live_transcription.psv
         Row-by-row transcription of all 8 chunks of
         https://www.nfl.com/injuries/league/2026/reg10 (read 2026-11-19).
         Pipe-delimited: game_id|club|player|position|injury|practice|game_status|chunk
Reads  : committed Week-10 tables, for comparison only (never edited here):
         audit/official_injury_wk10_2026.csv
         agency/data/derived/injury_designations_w10_2026.csv
         data/hub/injuries_2026_wk10.csv
Writes : data/recount/reg10_2026_live.csv         (row-level, one row per official row)
         data/recount/comparison.json              (summary numbers used by the page)
         data/recount/diffs.csv                    (every committed-vs-live difference)
         data/recount/MANIFEST.json                (sha256 of every input/output)
         recount/index.html, recount/rows.html     (static pages)

Run:   python3 scripts/recount_build.py && python3 scripts/recount_verify.py
Nothing is inferred: a value that is not in the transcription is written blank.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

PSV = P("data", "recount", "reg10_2026_live_transcription.psv")
OUT_CSV = P("data", "recount", "reg10_2026_live.csv")
OUT_CMP = P("data", "recount", "comparison.json")
OUT_DIFF = P("data", "recount", "diffs.csv")
OUT_MAN = P("data", "recount", "MANIFEST.json")
AUDIT = P("audit", "official_injury_wk10_2026.csv")
AGENCY = P("agency", "data", "derived", "injury_designations_w10_2026.csv")
HUB = P("data", "hub", "injuries_2026_wk10.csv")

REG10 = "https://www.nfl.com/injuries/league/2026/reg10"
SCHED = "https://www.nfl.com/schedules/2026/by-week/week-10"
RETRIEVED = "2026-11-19"

# Game metadata as printed on the official reg10 page (kickoff ET, networks) and
# the official schedule page's game URLs (away-at-home orientation from the URL slug).
GAMES = {
    "G01": dict(away="WAS", home="NYG", day="Thu 2026-11-12", kick="20:15", net="Prime Video",
                url="https://www.nfl.com/games/commanders-at-giants-2026-reg-10"),
    "G02": dict(away="NE", home="DET", day="Sun 2026-11-15", kick="09:30", net="FOX, FOX DEPORTES (Munich)",
                url="https://www.nfl.com/games/patriots-at-lions-2026-reg-10"),
    "G03": dict(away="KC", home="ATL", day="Sun 2026-11-15", kick="13:00", net="CBS",
                url="https://www.nfl.com/games/chiefs-at-falcons-2026-reg-10"),
    "G04": dict(away="MIN", home="GB", day="Sun 2026-11-15", kick="13:00", net="FOX",
                url="https://www.nfl.com/games/vikings-at-packers-2026-reg-10"),
    "G05": dict(away="JAX", home="TEN", day="Sun 2026-11-15", kick="13:00", net="FOX",
                url="https://www.nfl.com/games/jaguars-at-titans-2026-reg-10"),
    "G06": dict(away="BUF", home="NYJ", day="Sun 2026-11-15", kick="13:00", net="CBS",
                url="https://www.nfl.com/games/bills-at-jets-2026-reg-10"),
    "G07": dict(away="MIA", home="IND", day="Sun 2026-11-15", kick="13:00", net="CBS",
                url="https://www.nfl.com/games/dolphins-at-colts-2026-reg-10"),
    "G08": dict(away="CAR", home="NO", day="Sun 2026-11-15", kick="13:00", net="FOX",
                url="https://www.nfl.com/games/panthers-at-saints-2026-reg-10"),
    "G09": dict(away="HOU", home="CLE", day="Sun 2026-11-15", kick="13:00", net="FOX",
                url="https://www.nfl.com/games/texans-at-browns-2026-reg-10"),
    "G10": dict(away="LAR", home="AZ", day="Sun 2026-11-15", kick="16:05", net="CBS",
                url="https://www.nfl.com/games/rams-at-cardinals-2026-reg-10"),
    "G11": dict(away="SEA", home="LV", day="Sun 2026-11-15", kick="16:05", net="CBS",
                url="https://www.nfl.com/games/seahawks-at-raiders-2026-reg-10"),
    "G12": dict(away="SF", home="DAL", day="Sun 2026-11-15", kick="16:25", net="FOX, FOX DEPORTES",
                url="https://www.nfl.com/games/49ers-at-cowboys-2026-reg-10"),
    "G13": dict(away="PIT", home="CIN", day="Sun 2026-11-15", kick="20:20", net="NBC, UNIVERSO",
                url="https://www.nfl.com/games/steelers-at-bengals-2026-reg-10"),
    "G14": dict(away="LAC", home="BAL", day="Mon 2026-11-16", kick="20:15", net="ESPN, ABC, ESPN2, ESPN DEPORTES",
                url="https://www.nfl.com/games/chargers-at-ravens-2026-reg-10"),
}
BYE_CLUBS = ["CHI", "DEN", "PHI", "TB"]  # "Teams on Bye" on the official schedule page

PRACTICE_FULL = {
    "Full": "Full Participation in Practice",
    "Limited": "Limited Participation in Practice",
    "DNP": "Did Not Participate In Practice",
}
PRACTICE_ALLOWED = set(PRACTICE_FULL.values())
GAME_ALLOWED = {"", "Questionable", "Doubtful", "Out"}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def norm_practice(s: str) -> str:
    """Expand only the audit/hub abbreviations (Full / Limited / DNP). Everything else is compared exactly,
    so a capitalisation difference in a committed file is reported, not hidden."""
    s = (s or "").strip()
    return PRACTICE_FULL.get(s, s)


def load_live() -> list[dict]:
    rows = []
    with open(PSV, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|")
            assert len(parts) == 8, f"psv line {n}: expected 8 fields, got {len(parts)}"
            gid, club, player, pos, inj, practice, gstatus, chunk = parts
            g = GAMES[gid]
            rows.append(dict(
                row_no=len(rows) + 1, game_id=gid, game=f"{g['away']} @ {g['home']}",
                day=g["day"], kickoff_et=g["kick"], network=g["net"], club=club, player=player,
                position=pos, injury=inj, practice_status=practice, game_status=gstatus,
                page_chunk=int(chunk), source_url=REG10, game_url=g["url"],
            ))
    return rows


def load_committed(path: str, club_k: str, player_k: str, pos_k: str, inj_k: str,
                   pr_k: str, gs_k: str) -> dict:
    """returns {(club, normname): {pos, inj, pr, gs, player}} ; duplicates are kept as a list"""
    out: dict = defaultdict(list)
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r[club_k].strip(), norm_name(r[player_k]))
            out[key].append(dict(player=r[player_k], pos=r.get(pos_k, "") or "",
                                 inj=r.get(inj_k, "") or "", pr=norm_practice(r.get(pr_k, "") or ""),
                                 gs=(r.get(gs_k, "") or "").strip()))
    return out


def compare(live: list[dict], committed: dict, label: str, path_rel: str) -> tuple[dict, list[dict]]:
    diffs: list[dict] = []
    matched = 0
    field_diffs = 0
    missing = []
    seen = set()
    for r in live:
        key = (r["club"], norm_name(r["player"]))
        recs = committed.get(key)
        if not recs:
            missing.append(r)
            diffs.append(dict(source=label, row_no=r["row_no"], club=r["club"], player=r["player"],
                              field="ROW", live="present", committed="missing", file=path_rel))
            continue
        matched += 1
        seen.add(key)
        c = recs[0]
        for field, lv, cv in [("position", r["position"], c["pos"]), ("injury", r["injury"], c["inj"]),
                              ("practice_status", r["practice_status"], c["pr"]), ("game_status", r["game_status"], c["gs"])]:
            if field == "practice_status" and lv == cv:
                continue
            if (lv or "").strip() != (cv or "").strip():
                field_diffs += 1
                diffs.append(dict(source=label, row_no=r["row_no"], club=r["club"], player=r["player"],
                                  field=field, live=lv, committed=cv, file=path_rel))
    extra = [k for k in committed if k not in seen and k not in {(x["club"], norm_name(x["player"])) for x in live}]
    summary = dict(label=label, file=path_rel, committed_rows=sum(len(v) for v in committed.values()),
                   live_rows=len(live), matched_players=matched, missing_from_committed=len(missing),
                   committed_not_on_live=len(extra), field_differences=field_diffs,
                   missing_players=[f"{x['club']} {x['player']}" for x in missing])
    return summary, diffs


def main() -> None:
    live = load_live()
    os.makedirs(P("data", "recount"), exist_ok=True)

    # 1. row-level CSV (the authoritative transcription, in CSV form)
    fields = ["row_no", "game_id", "game", "day", "kickoff_et", "network", "club", "player", "position",
              "injury", "practice_status", "game_status", "page_chunk", "source_url", "game_url"]
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in live:
            w.writerow({k: r[k] for k in fields})

    # 2. comparisons with committed tables
    audit = load_committed(AUDIT, "team", "player", "position", "injury", "practice_status", "game_status")
    agency = load_committed(AGENCY, "team", "player", "position", "injury", "practice_status", "game_status")
    hub = load_committed(HUB, "team", "player", "pos", "injury", "practice", "status")
    s_audit, d_audit = compare(live, audit, "audit", "audit/official_injury_wk10_2026.csv")
    s_agency, d_agency = compare(live, agency, "agency", "agency/data/derived/injury_designations_w10_2026.csv")
    s_hub, d_hub = compare(live, hub, "hub", "data/hub/injuries_2026_wk10.csv")
    diffs = d_audit + d_hub + d_agency
    with open(OUT_DIFF, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "row_no", "club", "player", "field", "live", "committed", "file"])
        w.writeheader()
        for d in diffs:
            w.writerow(d)

    # 3. summary numbers
    by_game = Counter(r["game_id"] for r in live)
    by_club = Counter(r["club"] for r in live)
    status = Counter(r["game_status"] or "(blank)" for r in live)
    practice = Counter(r["practice_status"] for r in live)
    clubs_expected = sorted(set(by_club) | set(BYE_CLUBS))
    cmp = dict(
        retrieved=RETRIEVED, source=REG10, schedule=SCHED,
        live_rows=len(live), live_games=len(by_game), live_clubs=len(by_club),
        bye_clubs=BYE_CLUBS, clubs_in_32=len(clubs_expected),
        by_game={k: dict(rows=v, **{kk: GAMES[k][kk] for kk in ("away", "home", "day", "kick", "net")}) for k, v in sorted(by_game.items())},
        by_club={k: v for k, v in sorted(by_club.items())},
        status_counts=dict(status), practice_counts=dict(practice),
        comparisons=[s_agency, s_audit, s_hub],
        diff_total=len(diffs),
    )
    with open(OUT_CMP, "w", encoding="utf-8") as f:
        json.dump(cmp, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # 4. static pages
    from recount_pages import write_pages  # local module, same folder
    write_pages(live, cmp, audit, agency, hub, diffs, ROOT)

    # 5. manifest of hashes (inputs and outputs)
    man = dict(
        session="arena/d6d831c6-x3", retrieved=RETRIEVED,
        method=("Transcribed from fetch_page text of all 8 chunks of the official page; the raw HTML bytes "
                "could not be retained because the sandbox cannot reach nfl.com with curl (TLS failure). "
                "A second reader should check the transcription against the live page before reuse."),
        inputs={os.path.relpath(p, ROOT): sha256(p) for p in [PSV, AUDIT, AGENCY, HUB]},
        outputs={os.path.relpath(p, ROOT): sha256(p) for p in [OUT_CSV, OUT_CMP, OUT_DIFF]},
    )
    with open(OUT_MAN, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
        f.write("\n")
    print(f"live rows {len(live)} | games {len(by_game)} | clubs {len(by_club)} | diffs {len(diffs)}")
    for s in (s_agency, s_audit, s_hub):
        print(f"  {s['label']}: rows {s['committed_rows']} matched {s['matched_players']} "
              f"missing {s['missing_from_committed']} field-diffs {s['field_differences']}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
