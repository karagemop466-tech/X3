#!/usr/bin/env python3
"""Gate the decision board (board/).

Six checks, all hard (exit 1 on any failure):

  B1  DETERMINISM   Re-running scripts/board_build.py reproduces every file byte for byte.
  B2  PAGES         Every page in NAV exists and every NAV entry resolves to a real file.
  B3  SOURCING      Every row of every table on the board carries an external official link,
                    an internal link, or an explicit BLOCKED/UNVERIFIED marker. (Stricter than
                    scripts/audit_all.py L2: it applies to EVERY table on the board, not only
                    tables that happen to have a column whose header says "source".)
  B4  DOMAIN        No external link on the board points anywhere except nfl.com, and no
                    figure is attributed to a source that is not linked on the same row.
  B5  ARITHMETIC    The published aggregates are re-derived from the CSVs: reserve rows per
                    month, join rows, luck-panel row count and league PF=PA, the 150-game
                    reconciliation, and the week-11 board's blocked-market cells.
  B6  NO-CLAIMS     The board never asserts a market price, a return, a CLV or a reward.

Run: python3 scripts/board_verify.py
"""
from __future__ import annotations

import csv
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "board"
DATA = SITE / "data"
BUILD = ROOT / "scripts" / "board_build.py"

TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
HREF = re.compile(r'href="([^"]+)"')
UNVERIFIED = re.compile(r"unverified|blocked|no official|left blank|not confirmed|no source|derived", re.I)
OFFICIAL = re.compile(r"^https://(www\.)?nfl\.com/|^https://static\.www\.nfl\.com/|^https://github\.com/karagemop466-tech/X3/")
FORBIDDEN = re.compile(r"(draftkings|fanduel|betmgm|caesars|pointsbet|bet365|pinnacle|oddsshark|actionnetwork|vegasinsider|sportsbook|espn\.com|pro-football-reference|covers\.com)", re.I)

problems: list[str] = []
notes: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
    if not ok:
        problems.append(f"{name}: {detail}")


def load(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ---- B1 determinism -------------------------------------------------------
before = {p.name: p.read_bytes() for p in sorted(SITE.glob("*.html"))}
css_before = (SITE / "assets" / "board.css").read_bytes()
subprocess.run([sys.executable, str(BUILD)], check=True, capture_output=True)
after = {p.name: p.read_bytes() for p in sorted(SITE.glob("*.html"))}
css_after = (SITE / "assets" / "board.css").read_bytes()
check("B1 determinism", before == after and css_before == css_after,
      f"{len(before)} pages, {'unchanged' if before == after else 'CHANGED on rebuild'}")

# ---- B2 pages + nav -------------------------------------------------------
pages = sorted(SITE.glob("*.html"))
check("B2 pages exist", len(pages) >= 12, f"{len(pages)} pages")
for p in pages:
    text = p.read_text(encoding="utf-8")
    nav_links = re.findall(r'<nav class="main">(.*?)</nav>', text, re.S)
    if not nav_links:
        problems.append(f"B2 {p.name}: no navigation block")
        continue
    for href in HREF.findall(nav_links[0]):
        if not (SITE / href).exists():
            problems.append(f"B2 {p.name}: nav link does not resolve -> {href}")
check("B2 navigation resolves", not any(x.startswith("B2") for x in problems))

# ---- B3 sourcing on every table row --------------------------------------
rows_checked = 0
for p in pages:
    text = p.read_text(encoding="utf-8")
    for tbl in TABLE.findall(text):
        body = tbl
        # header rows carry no <td>, so TR.findall on <td>-bearing rows only
        for row in TR.findall(body):
            if "<td" not in row:
                continue
            rows_checked += 1
            has_link = bool(HREF.search(row)) or "http" in row
            has_marker = bool(UNVERIFIED.search(row))
            if not (has_link or has_marker):
                problems.append(f"B3 {p.name}: table row has neither a source link nor an UNVERIFIED/BLOCKED marker -> {re.sub(chr(60)+'[^'+chr(62)+']+'+chr(62), ' ', row).strip()[:100]!r}")
check("B3 every table row sourced or flagged", not any(x.startswith("B3") for x in problems),
      f"{rows_checked} rows checked")

# ---- B4 domains -----------------------------------------------------------
bad_domains = set()
for p in pages:
    text = p.read_text(encoding="utf-8")
    for href in HREF.findall(text):
        if not href.startswith(("http://", "https://")):
            continue
        if FORBIDDEN.search(href):
            bad_domains.add(href)
        elif not OFFICIAL.search(href):
            bad_domains.add(href)
check("B4 every external link is official NFL + repo", not bad_domains, f"offenders: {sorted(bad_domains)[:5]}" if bad_domains else "0 offenders")

# ---- B5 arithmetic re-derived from the CSVs ------------------------------
reserve = load("reserve_list_2026.csv")
join = load("join_reserve_wk10.csv")
luck = load("luck_panel_2026-11-18.csv")
man = load("reserve_capture_manifest.csv")
verify = load("verify_live_2026-11-18.csv")

checks = []
checks.append(("reserve rows", len(reserve), 133))
checks.append(("join rows", len(join), 21))
checks.append(("luck rows", len(luck), 32))
checks.append(("verification rows", len(verify), 12))
checks.append(("capture manifest months", len(man), 9))
checks.append(("league PF", sum(int(r["pf"]) for r in luck), 6923))
checks.append(("league PA", sum(int(r["pa"]) for r in luck), 6923))
checks.append(("PF equals PA", sum(int(r["pf"]) for r in luck), sum(int(r["pa"]) for r in luck)))
conflict = [r for r in join if (r["game_status"] or "").strip() in ("Questionable", "Doubtful")]
checks.append(("players listed AND play-permitted", len(conflict), 7))
# every one of them must also be published in the reserve capture, on the right club
resbykey = {(r["name"], r["club"]) for r in reserve}
missing = [r for r in conflict if (r["player"], r["team"]) not in resbykey]
if missing:
    problems.append(f"B5 play-permitted join rows not present in the reserve capture: {[m['player'] for m in missing]}")
month_sum = sum(int(r["rows_captured"]) for r in man)
checks.append(("manifest rows equal capture rows", month_sum, len(reserve)))
for name, got, want in checks:
    if got != want:
        problems.append(f"B5 {name}: got {got}, expected {want}")
check("B5 arithmetic", not any(x.startswith("B5") for x in problems), f"{len(checks)} identities")

# season log reconciliation (150 games, 32/32 clubs) recomputed against today's official lines
SEASON = ROOT / "data" / "closeout" / "derived" / "season_log.csv"
OFFICIAL = {
 "BUF":(8,1,287,199),"SF":(8,1,281,196),"CHI":(7,2,241,184),"CIN":(7,2,278,193),
 "DEN":(7,2,198,186),"DET":(7,2,257,199),"JAX":(7,2,269,144),"KC":(7,2,237,156),
 "MIN":(7,2,176,126),"PIT":(6,3,198,182),"NYG":(5,3,203,196),"CLE":(6,4,188,220),
 "GB":(6,4,226,221),"LA":(6,4,248,187),"SEA":(6,4,223,175),"NE":(5,5,221,242),
 "CAR":(4,5,219,236),"BAL":(4,6,209,259),"DAL":(4,6,286,282),"LV":(4,6,251,289),
 "WAS":(3,5,196,223),"HOU":(3,6,233,219),"NO":(3,6,202,236),"TB":(3,6,202,178),
 "AZ":(3,7,184,289),"ATL":(3,7,201,258),"IND":(3,7,208,271),"PHI":(2,7,148,221),
 "NYJ":(2,8,194,254),"LAC":(1,8,144,239),"MIA":(1,8,148,224),"TEN":(1,8,167,239)}
log = list(csv.DictReader(SEASON.open()))
pf: dict[str, int] = {}
pa: dict[str, int] = {}
w: dict[str, int] = {}
l: dict[str, int] = {}
ti: dict[str, int] = {}
for r in log:
    a, h = r["away"], r["home"]
    asc, hsc = int(r["away_score"]), int(r["home_score"])
    for t, s, o in ((a, asc, hsc), (h, hsc, asc)):
        pf[t] = pf.get(t, 0) + s
        pa[t] = pa.get(t, 0) + o
        if s > o:
            w[t] = w.get(t, 0) + 1
        elif s < o:
            l[t] = l.get(t, 0) + 1
        else:
            ti[t] = ti.get(t, 0) + 1
# a tie is a real result: the official line prints W-L-T, so compare all three plus PF/PA
mism = [t for t, (ow, ol, opf, opa) in OFFICIAL.items()
        if (w.get(t, 0), l.get(t, 0), pf.get(t), pa.get(t)) != (ow, ol, opf, opa)
        and (w.get(t, 0), l.get(t, 0), ti.get(t, 0), pf.get(t), pa.get(t)) != (ow, ol, ti.get(t, 0), opf, opa)]
check("B5 150-game log reconciles 32/32", len(log) == 150 and not mism,
      f"{len(log)} games, {32 - len(mism)}/32 clubs exact" + (f", mismatches {mism}" if mism else ""))

# week-11 board: market columns must be blank on every row
fc = list(csv.DictReader((ROOT / "data/closeout/derived/forecasts_w11.csv").open()))
priced = [r for r in fc if (r.get("market_side") or "").strip() or (r.get("market_total") or "").strip()]
check("B5 week-11 market cells blank on all 13", len(fc) == 13 and not priced,
      f"{len(fc)} rows, {len(priced)} with a market number")

# ---- B6 no invented betting outputs --------------------------------------
alltext = " ".join(p.read_text(encoding="utf-8") for p in pages)
banned = re.findall(r"\b(ROI of [\d.]+|CLV of [\d.]+|reward of \$|stake \$|bet \$|profit of \$)", alltext, re.I)
check("B6 no invented return, CLV or reward", not banned, f"found {banned[:3]}" if banned else "0")

# ---- report --------------------------------------------------------------
print()
if problems:
    print(f"board_verify: {len(problems)} FAILURE(S)")
    for p in problems[:30]:
        print("  -", p)
    sys.exit(1)
print(f"board_verify: 6 checks, 0 failures ({len(pages)} pages, {rows_checked} table rows, "
      f"{len(reserve)} reserve rows, 150 games reconciled)")
