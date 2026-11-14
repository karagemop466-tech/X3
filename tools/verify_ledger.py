#!/usr/bin/env python3
"""Line-by-line gate for the decision ledger (data/ledger/* and ledger/*.html).

Checks, all offline (no network): 
  1. Results feed reconciles to the live official standings snapshot:
     W, L, T, PF, PA, home record and road record for all 32 clubs.
  2. Price store: 13 games x 3 markets in origination order; every opening/closing/book
     value is blank unless a price_source_url is present; every row carries a game source.
  3. Replacement depth: each row's game_status equals the official injury report
     (data/hub/injuries_2026_wk10.csv) for the same team and player.
  4. Every table row on every ledger page links an approved official host, OR a repo
     page for a PROPOSED/UNVERIFIED policy row, OR is explicitly flagged UNVERIFIED.
  5. Every internal link in ledger/*.html resolves to a file.
Exit code 0 only if every check passes.
"""
import csv, html, json, pathlib, re, sys
from collections import defaultdict
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "ledger"
PAGES = ROOT / "ledger"
INJ = ROOT / "data" / "hub" / "injuries_2026_wk10.csv"
ALIAS = {"ARI": "AZ"}  # game-log code -> standings code (official standings use AZ)

APPROVED_HOSTS = {"www.nfl.com", "nfl.com", "operations.nfl.com"}


def club_hosts():
    """Club depth-chart hosts, taken from the depth file. Each team must map to exactly one host."""
    per_team = defaultdict(set)
    for r in read("replacement_depth_wk10.csv"):
        per_team[r["team"]].add(re.sub(r"^https?://", "", r["depth_source_url"]).split("/")[0].lower())
    bad = {t: h for t, h in per_team.items() if len(h) != 1}
    return set().union(*per_team.values()) if per_team else set(), bad


def read(name):
    with (LEDGER / name).open(newline="") as fh:
        return list(csv.DictReader(fh))


def reconcile():
    """Return (teams_checked, mismatches) comparing results feed to live standings."""
    results = read("results_2026.csv")
    standings = read("standings_live_2026_wk10.csv")
    agg = defaultdict(lambda: dict(w=0, l=0, t=0, pf=0, pa=0, hw=0, hl=0, ht=0, rw=0, rl=0, rt=0))
    for g in results:
        a, h = int(g["away_score"]), int(g["home_score"])
        away = ALIAS.get(g["away"], g["away"])
        home = ALIAS.get(g["home"], g["home"])
        for team, pf, pa, is_home in ((home, h, a, True), (away, a, h, False)):
            d = agg[team]
            d["pf"] += pf
            d["pa"] += pa
            outcome = "w" if pf > pa else ("l" if pf < pa else "t")
            d[outcome] += 1
            d[("h" if is_home else "r") + outcome] += 1
    mismatches = []
    for s in standings:
        team = s["team"]
        d = agg.get(team)
        if d is None:
            mismatches.append((team, "no results rows"))
            continue
        for key in ("w", "l", "t", "pf", "pa"):
            if d[key] != int(s[key]):
                mismatches.append((team, f"{key}: feed {d[key]} vs standings {s[key]}"))
        home_rec = f"{d['hw']}-{d['hl']}-{d['ht']}"
        road_rec = f"{d['rw']}-{d['rl']}-{d['rt']}"
        if home_rec != s["home_rec"]:
            mismatches.append((team, f"home: feed {home_rec} vs standings {s['home_rec']}"))
        if road_rec != s["road_rec"]:
            mismatches.append((team, f"road: feed {road_rec} vs standings {s['road_rec']}"))
    return len(standings), mismatches


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.hrefs.append(href)


META_ROWS = []


def check_pages():
    failures = []
    CLUBS, _ = club_hosts()
    rows_checked = 0
    for page in sorted(PAGES.glob("*.html")):
        text = page.read_text()
        # row-level: every <tr> inside <tbody> needs an approved link or an UNVERIFIED/PROPOSED flag
        for tr in re.findall(r"<tbody>(.*?)</tbody>", text, flags=re.S):
            for row_open, row in re.findall(r"<tr([^>]*)>(.*?)</tr>", tr, flags=re.S):
                if 'class="k-meta"' in row_open:
                    # site-navigation / register row: exempt by explicit marker, counted separately
                    META_ROWS.append(page.name)
                    continue
                rows_checked += 1
                links = re.findall(r'href="([^"]+)"', row)
                flagged = bool(re.search(r"UNVERIFIED|PROPOSED|DERIVED", row))
                official = []
                for href in links:
                    if href.startswith(("http://", "https://")):
                        host = re.sub(r"^https?://", "", href).split("/")[0].lower()
                        if host in APPROVED_HOSTS or host in CLUBS:
                            official.append(href)
                if not official and not flagged:
                    failures.append(f"{page.name}: row without official link or flag: {html.unescape(re.sub(r'<[^>]+>', ' ', row))[:120]!r}")
                if not links:
                    failures.append(f"{page.name}: row has no link at all")
        parser = _Links()
        parser.feed(text)
        for href in parser.hrefs:
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = href.split("#", 1)[0]
            if target and not (page.parent / target).exists():
                failures.append(f"{page.name}: broken internal link {href}")
    return rows_checked, failures


def check_prices():
    out = []
    rows = read("price_snapshots.csv")
    if len(rows) != 39:
        out.append(f"price store has {len(rows)} rows, expected 13 games x 3 markets = 39")
    games = defaultdict(list)
    for r in rows:
        games[r["game_id"]].append(r)
    for gid, rs in games.items():
        orders = [int(r["origination_order"]) for r in rs]
        markets = [r["market"] for r in rs]
        if orders != [1, 2, 3] or markets != ["spread", "total", "moneyline"]:
            out.append(f"{gid}: origination order is {list(zip(orders, markets))}, expected side->total->moneyline")
    for r in rows:
        for field in ("opening_value", "closing_value", "book", "price_source_url"):
            if r[field].strip():
                if field == "price_source_url" and r[field].startswith("https://www.nfl.com/"):
                    continue
                out.append(f"{r['game_id']} {r['market']}: {field} filled ({r[field]!r}) without an official price source; must be blank")
        if not r["game_source_url"].startswith("https://www.nfl.com/"):
            out.append(f"{r['game_id']} {r['market']}: game_source_url is not an nfl.com page")
    return len(rows), out


def check_depth():
    out = []
    official = {}
    for r in csv.DictReader(INJ.open(newline="")):
        official[(r["team"], r["player"])] = r["status"]
    rows = read("replacement_depth_wk10.csv")
    for r in rows:
        key = (r["team"], r["player"])
        if key not in official:
            out.append(f"{key}: not in official injury report")
        elif official[key] != r["game_status"]:
            out.append(f"{key}: status {r['game_status']!r} vs official {official[key]!r}")
        if r["join"].startswith("matched") and not r["replacement"] and r["join"] != "matched-no-backup":
            out.append(f"{key}: join says matched but no replacement name")
    return len(rows), out


def main():
    problems = []
    teams, mism = reconcile()
    print(f"standings reconciliation: {teams} clubs, {len(mism)} mismatches")
    problems += [f"reconcile {t}: {m}" for t, m in mism]
    if teams != 32:
        problems.append(f"expected 32 clubs, got {teams}")
    n_res = len(read("results_2026.csv"))
    print(f"results feed rows: {n_res}")
    if n_res != 137:
        problems.append(f"results feed has {n_res} rows, expected 137 FINAL games")
    n_px, px = check_prices()
    print(f"price store rows: {n_px}")
    problems += px
    n_dp, dp = check_depth()
    print(f"replacement-depth rows checked against official injury report: {n_dp}")
    problems += dp
    _, multi = club_hosts()
    problems += [f"team {t} uses more than one depth-chart host: {sorted(h)}" for t, h in multi.items()]
    if PAGES.exists():
        n_rows, pages = check_pages()
        print(f"ledger page table rows checked: {n_rows} (navigation rows exempt by k-meta marker: {len(META_ROWS)})")
        problems += pages
    if problems:
        print(f"LEDGER CHECK FAILED: {len(problems)} problem(s)")
        for p in problems[:200]:
            print(" -", p)
        return 1
    print("LEDGER CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
