#!/usr/bin/env python3
"""Origin capture: fetch official NFL.com week schedule pages and build the
verified results feed for the origination module (`origin/`).

This runs on a GitHub Actions runner (full internet). The authoring sandbox
cannot reach nfl.com. Output:
  origin/data/results.json       the results feed (one row per game, per-row
                                 official source URL, captured_at timestamp)
  origin/data/capture_diag.json  fetch diagnostics (status/bytes per page)
Raw HTML goes to capture/origin/ (git-ignored) for manual review.

Modes:
  python3 scripts/origin_capture.py results        # fetch + parse results feed
  python3 scripts/origin_capture.py close          # cycle-close snapshot pass:
                                                   # re-stamp closing model lines
                                                   # from the frozen inputs and
                                                   # record the capture time in
                                                   # origin/data/close_marker.json
  python3 scripts/origin_capture.py results --local capture/origin
                                                   # re-parse already-captured HTML

No fact is typed by hand. If a page cannot be fetched, its week is recorded as
a capture failure in the diagnostics and the parser reports the gap; nothing is
inferred or filled in.

Parser patterns mirror scripts/desk_parse.py (two independent sessions have
already used them on the same pages; agreement between the two transcriptions
is checked by scripts/origin_verify.py).
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "origin" / "data"
CAPTURE = ROOT / "capture" / "origin"

NFL = "https://www.nfl.com"
SCHEDULE_URL = NFL + "/schedules/2026/by-week/week-{}"
SEASON = 2026
WEEKS = list(range(1, 12))  # weeks 1..11 (11 = next cycle, scheduled only)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

# Nicknames as printed by NFL.com schedule pages -> club abbreviations.
# Mapping reference: https://www.nfl.com/teams/ (same table as scripts/desk_parse_meta.py).
NICKNAME = {
    "Cardinals": "ARI", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF",
    "Panthers": "CAR", "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE",
    "Cowboys": "DAL", "Broncos": "DEN", "Lions": "DET", "Packers": "GB",
    "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX", "Chiefs": "KC",
    "Rams": "LA", "Chargers": "LAC", "Raiders": "LV", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG",
    "Jets": "NYJ", "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF",
    "Seahawks": "SEA", "Buccaneers": "TB", "Titans": "TEN", "Commanders": "WAS",
}

FINAL_RE = re.compile(
    r"^([A-Za-z0-9.&' ]+?) (\d{1,3}), ([A-Za-z0-9.&' ]+?) (\d{1,3}), FINAL, "
    r"([A-Za-z]+), ([A-Za-z]+ \d{1,2})(?:st|nd|rd|th)(?:.*)$")
SCHED_RE = re.compile(
    r"^([A-Za-z0-9.&' ]+?) at ([A-Za-z0-9.&' ]+), ([A-Za-z]+), "
    r"([A-Za-z]+ \d{1,2})(?:st|nd|rd|th), (\d{1,2}:\d{2} [AP]M), ([A-Za-z0-9 ,]+?)(?:\s+Tickets.*)?$")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
WS_RE = re.compile(r"\s+")
HOST_CITIES = {"MUNICH", "MADRID", "LONDON", "SAO PAULO", "MELBOURNE", "DUBLIN",
               "PARIS", "FRANKFURT", "MEXICO CITY", "TORONTO", "RIO DE JANEIRO",
               "BERLIN", "TOKYO", "EAST MELBOURNE"}
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}

PROBLEMS: list[dict] = []


def problem(page: str, msg: str, detail: str = "") -> None:
    PROBLEMS.append({"page": page, "problem": msg, "detail": detail[:300]})


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_date(month_name: str, day_text: str, season: int = SEASON) -> str:
    month = MONTHS.get(month_name, 0)
    if not month:
        return ""
    day = int(re.sub(r"\D", "", day_text) or 0)
    year = season + 1 if month <= 2 else season
    return f"{year:04d}-{month:02d}-{day:02d}"


def text_of(raw: str) -> str:
    """Visible text of the page, one non-empty line per block. Byte-for-byte the
    same approach as scripts/desk_extract.py text_of (proven on these pages by
    two prior sessions) — including tab-preservation for table cells."""
    s = SCRIPT_RE.sub(" ", raw)
    s = re.sub(r"</t[dh]>", "\t", s, flags=re.I)
    s = re.sub(r"</tr>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h[1-6]|table|section|article)>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", s, flags=re.S | re.I)
    s = TAG_RE.sub(" ", s)
    s = html.unescape(s).replace("\u00a0", " ")
    lines = []
    for line in s.splitlines():
        line = WS_RE.sub(" ", line).strip()
        line = re.sub(r"\t+", "\t", line).strip("\t")
        if line:
            lines.append(line)
    return "\n".join(lines) + "\n"


def get(url: str, dest: Path, tries: int = 3) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = ""
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
                dest.write_bytes(body)
                return {"url": url, "status": r.status, "bytes": len(body), "attempts": attempt}
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 * attempt)
    return {"url": url, "status": None, "bytes": 0, "error": last, "attempts": tries}


def parse_schedule(page_name: str, raw: str) -> list[dict]:
    wm = re.search(r"-w(\d+)$", page_name)
    if not wm:
        problem(page_name, "page name does not contain a week number")
        return []
    week = int(wm.group(1))
    src = SCHEDULE_URL.format(week)
    rows: list[dict] = []
    lines = text_of(raw).splitlines()
    for line in lines:
        m = FINAL_RE.match(line)
        if m is not None:
            away, ascore, home, hscore, _day, date_text = m.groups()
            rows.append({
                "week": week, "away": NICKNAME.get(away, ""), "home": NICKNAME.get(home, ""),
                "away_name": away, "home_name": home,
                "away_score": int(ascore), "home_score": int(hscore),
                "status": "FINAL", "date_text": date_text,
                "date_iso": iso_date(date_text.split()[0], date_text),
                "kickoff_et": "", "network": "",
                "neutral_site": False, "neutral_site_name": "", "source": src,
                "captured_at": None,  # stamped by the caller
            })
            if not rows[-1]["away"] or not rows[-1]["home"]:
                problem(page_name, "club not mapped to an abbreviation", line)
            continue
        m = SCHED_RE.match(line)
        if m:
            away, home, _day, date_text, kickoff, network = m.groups()
            rows.append({
                "week": week, "away": NICKNAME.get(away, ""), "home": NICKNAME.get(home, ""),
                "away_name": away, "home_name": home,
                "away_score": None, "home_score": None, "status": "SCHEDULED",
                "date_text": date_text, "date_iso": iso_date(date_text.split()[0], date_text),
                "kickoff_et": kickoff, "network": network.strip(),
                "neutral_site": False, "neutral_site_name": "", "source": src,
                "captured_at": None,
            })
            if not rows[-1]["away"] or not rows[-1]["home"]:
                problem(page_name, "club not mapped to an abbreviation", line)
    # Neutral-site (international) games: require the "International Game" banner
    # immediately before the game line (same rule as scripts/desk_parse.py).
    for idx, line in enumerate(lines):
        m2 = FINAL_RE.match(line) or SCHED_RE.match(line)
        if not m2:
            continue
        back = lines[max(0, idx - 4):idx]
        if not any("International Game" in b for b in back):
            continue
        city = next((b.strip() for b in reversed(back) if b.strip().upper() in HOST_CITIES), "")
        home_name = m2.group(3) if m2.re is FINAL_RE else m2.group(2)
        for r in rows:
            if r["away_name"] == m2.group(1) and r["home_name"] == home_name:
                r["neutral_site"] = True
                r["neutral_site_name"] = city
    seen, unique = set(), []
    for r in rows:
        key = (r["away"], r["home"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    finals = [r for r in unique if r["status"] == "FINAL"]
    if not unique:
        problem(page_name, "no games parsed")
    elif week < 10 and len(finals) < 12:
        problem(page_name, f"only {len(finals)} finals parsed from week {week}")
    return unique


def cross_check(rows: list[dict]) -> dict:
    """Independent cross-check against the desk transcription
    (data/desk/games.json, session arena/3bf7cc8b-x3, parsed by a different
    program from the same official pages). Agreement is evidence; disagreement
    is a flag, never auto-resolved."""
    desk_path = ROOT / "data" / "desk" / "games.json"
    if not desk_path.exists():
        return {"available": False, "reason": "data/desk/games.json not present"}
    desk = json.loads(desk_path.read_text())["games"]
    desk_idx = {(g["week"], g["away"], g["home"]): g for g in desk}
    mine_idx = {(g["week"], g["away"], g["home"]): g for g in rows}
    matched, agree, conflicts = 0, 0, []
    for key, g in mine_idx.items():
        d = desk_idx.get(key)
        if d is None:
            continue
        matched += 1
        same = (g["status"] == d["status"]
                and g["away_score"] == d["away_score"]
                and g["home_score"] == d["home_score"])
        if same:
            agree += 1
        else:
            conflicts.append({
                "key": list(key), "origin": [g["status"], g["away_score"], g["home_score"]],
                "desk": [d["status"], d["away_score"], d["home_score"]]})
    return {"available": True, "desk_rows": len(desk), "origin_rows": len(rows),
            "matched": matched, "agree": agree, "conflicts": conflicts}


def selftest() -> list[str]:
    """Offline proof that this parser agrees with the proven desk transcription.
    Runs the parser over the desk-extracted official page text
    (data/desk/text/schedule-w*.txt, committed by session arena/3bf7cc8b-x3) and
    compares the finals against data/desk/games.json. Any mismatch is a parser
    bug in THIS script, not in the data."""
    fails: list[str] = []
    desk = json.loads((ROOT / "data" / "desk" / "games.json").read_text())["games"]
    desk_idx = {(g["week"], g["away"], g["home"]): g for g in desk}
    textdir = ROOT / "data" / "desk" / "text"
    mine = {}
    for w in range(1, 12):
        f = textdir / f"schedule-w{w}.txt"
        if not f.exists():
            fails.append(f"desk text missing: {f.name}")
            continue
        for g in parse_schedule(f"schedule-w{w}", f.read_text(errors="replace")):
            key = (g["week"], g["away"], g["home"])
            mine[key] = g
    agree = disagree = missing = 0
    for key, g in mine.items():
        d = desk_idx.get(key)
        if d is None:
            missing += 1
            continue
        if (g["status"] == d["status"] and g["away_score"] == d["away_score"]
                and g["home_score"] == d["home_score"]):
            agree += 1
        else:
            disagree += 1
            fails.append(f"mismatch {key}: origin={g['status']}/{g['away_score']}/{g['home_score']} "
                         f"desk={d['status']}/{d['away_score']}/{d['home_score']}")
    desk_only = [k for k in desk_idx if k not in mine]
    summary = f"selftest vs desk transcription: agree={agree} disagree={disagree} " \
              f"unique-to-origin={missing} unique-to-desk={len(desk_only)}"
    print(summary)
    if disagree:
        fails.insert(0, summary)
    elif missing > 2 or len(desk_only) > 6:
        # small asymmetries are expected (descheduled/renamed rows), wholesale
        # divergence is not
        fails.append(f"{summary} — divergence too large for two parsers of the same pages")
    return fails


def cmd_results() -> int:
    global PROBLEMS
    diag: dict = {"pages": [], "captured_at": now_iso(), "notes": [], "problems": [],
                  "fatal": None, "selftest": None}
    PROBLEMS = diag["problems"]
    DATA.mkdir(parents=True, exist_ok=True)
    diag_path = DATA / "capture_diag.json"

    def flush() -> None:
        diag_path.write_text(json.dumps(diag, indent=1) + "\n")

    try:
        fails = selftest()
        diag["selftest"] = {"passed": not fails, "detail": fails[:20]}
        flush()
        if fails:
            print("PARSER SELF-TEST FAILED:", file=sys.stderr)
            for f in fails[:20]:
                print("  ", f, file=sys.stderr)
            return 1
        all_rows: list[dict] = []
        if "--local" in sys.argv:
            idx = sys.argv.index("--local")
            capdir = Path(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else CAPTURE
            files = sorted(capdir.glob("week-*.html"))
            if not files:
                print(f"no captured pages in {capdir}", file=sys.stderr)
                return 1
            for f in files:
                all_rows.extend(parse_schedule(f.name, f.read_text(errors="replace")))
            diag["notes"].append(f"parsed locally from {capdir}")
        else:
            for week in WEEKS:
                url = SCHEDULE_URL.format(week)
                dest = CAPTURE / f"schedule-w{week}.html"
                d = get(url, dest)
                diag["pages"].append(d)
                flush()
                if d["status"] != 200:
                    PROBLEMS.append({"page": f"week-{week}",
                                     "problem": f"fetch failed ({d.get('error', d['status'])})"})
                    continue
                all_rows.extend(parse_schedule(dest.stem,
                                               dest.read_text(errors="replace")))
                time.sleep(1)
        ts = now_iso()
        for r_ in all_rows:
            r_["captured_at"] = ts
        finals = [r_ for r_ in all_rows if r_["status"] == "FINAL"]
        cc = cross_check(all_rows)
        diag["problems"] = PROBLEMS
        feed = {
            "season": SEASON,
            "generated_at": ts,
            "source_pages": [SCHEDULE_URL.format(w) for w in WEEKS],
            "source_note": "Official NFL.com 2026 week schedule pages; one row per game; "
                           "scores transcribed from the page's own final-score lines; "
                           "nothing typed by hand or inferred.",
            "counts": {
                "total": len(all_rows),
                "final": len(finals),
                "scheduled": len(all_rows) - len(finals),
            },
            "cross_check_vs_desk_transcription": cc,
            "problems": PROBLEMS,
            "games": sorted(all_rows, key=lambda g: (g["week"], g["date_iso"], g["away"])),
        }
        (DATA / "results.json").write_text(json.dumps(feed, indent=1) + "\n")
        ok_fetch = sum(1 for p in diag["pages"] if p.get("status") == 200)
        print(f"origin_capture results: {ok_fetch}/{len(diag['pages'])} pages fetched, "
              f"{len(all_rows)} games ({len(finals)} finals) parsed, "
              f"{len(PROBLEMS)} problems")
        if cc.get("available"):
            print(f"cross-check vs desk transcription: {cc['agree']}/{cc['matched']} matched "
                  f"rows agree; {len(cc['conflicts'])} conflicts")
            for c in cc["conflicts"][:10]:
                print("  CONFLICT:", c)
        for p in PROBLEMS[:10]:
            print("  PROBLEM:", p)
        # A results feed with zero finals parsed while official pages were fetched
        # is a broken capture, not an empty season: fail loudly.
        if ok_fetch and not finals:
            print("FATAL: pages fetched but no finals parsed - parser is broken", file=sys.stderr)
            diag["fatal"] = "pages fetched but no finals parsed"
            flush()
            return 1
        return 0
    except Exception as e:  # noqa: BLE001 — always leave diagnostics behind
        import traceback
        diag["fatal"] = f"{type(e).__name__}: {e}"
        diag["traceback"] = traceback.format_exc()[-4000:]
        flush()
        print("FATAL:", diag["fatal"], file=sys.stderr)
        print(diag.get("traceback", ""), file=sys.stderr)
        return 1


def cmd_close() -> int:
    """Cycle-close pass: stamp the close phase. The closing MODEL line is read
    from the frozen module inputs by the builder at build time; this marker
    records WHEN the close capture ran. Closing MARKET numbers stay blank until
    the owner connects a price source (open decision Q-01)."""
    DATA.mkdir(parents=True, exist_ok=True)
    marker = {"phase": "close", "captured_at": now_iso(),
              "note": "Cycle-close capture marker. Closing model lines are read from "
                      "the frozen inputs by scripts/origin_build.py at the next build; "
                      "closing market prices remain blank pending the price-source decision."}
    (DATA / "close_marker.json").write_text(json.dumps(marker, indent=1) + "\n")
    print("origin_capture close:", marker["captured_at"])
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "results"
    sys.exit(cmd_results() if mode == "results" else cmd_close())
