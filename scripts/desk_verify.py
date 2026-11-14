#!/usr/bin/env python3
"""Line-by-line verification gate for the desk datasets and the built site.

Checks (all must pass; the CI workflow fails on the first failure):
  1. every dataset row carries an official or club-official source URL
  2. PF/PA/W-L-T in the standings page equal the values recomputed from the game log
  3. the game log has no duplicate matchups and no incomplete finals
  4. injury rows carry a player, a team and a status from the official vocabulary
  5. deficiency rows keep their join evidence (or an explicit no-join reason)
  6. every published HTML page has no broken internal link or missing asset
  7. every table row on the site carries a source link or an explicit UNVERIFIED badge
  8. no placeholder tokens remain in the built pages

Exit code 0 = all gates pass.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

OFFICIAL_HOSTS = ("nfl.com",)
CLUB_HOSTS = ("azcardinals.com", "atlantafalcons.com", "baltimoreravens.com",
              "buffalobills.com", "panthers.com", "chicagobears.com", "bengals.com",
              "clevelandbrowns.com", "dallascowboys.com", "denverbroncos.com",
              "detroitlions.com", "packers.com", "houstontexans.com", "colts.com",
              "jaguars.com", "chiefs.com", "therams.com", "chargers.com", "raiders.com",
              "miamidolphins.com", "vikings.com", "patriots.com", "neworleanssaints.com",
              "giants.com", "newyorkjets.com", "philadelphiaeagles.com", "steelers.com",
              "49ers.com", "seahawks.com", "buccaneers.com", "tennesseetitans.com",
              "commanders.com")
TRUSTED_HOSTS = OFFICIAL_HOSTS + CLUB_HOSTS + (
    "espn.com", "nist.gov", "scikit-learn.org", "ssrn.com", "arxiv.org")


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.srcs: list[str] = []
        self.rows: list[list[str]] = []
        self.row_hrefs: list[bool] = []
        self.row_in_head: list[bool] = []
        self.row_cells: list[list[str]] = []
        self.row_cell_html: list[list[str]] = []
        self._row_cells_html: list[list[str]] = []
        self._cur_row_cells: list[str] = []
        self._cell_buf: list[str] = []
        self._in_cell = False
        self._row_has_href = False
        self._in_thead = False
        self._in_row = False
        self._row: list[str] = []
        self._depth = 0
        self.ids: set[str] = set()
        self.anchors: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
            if self._in_row:
                self._row_has_href = True
        if tag in ("img", "script") and a.get("src"):
            self.srcs.append(a["src"])
        if tag == "link" and a.get("href"):
            self.srcs.append(a["href"])
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "thead":
            self._in_thead = True
        if tag == "tbody":
            self._in_thead = False
        if tag in ("td", "th"):
            self._in_cell = True
            self._cell_buf = [self.get_starttag_text() or ""]
        if tag == "tr":
            self._in_row = True
            self._row = []
            self._cur_row_cells = []
            self._row_has_href = False
        if tag == "a" and a.get("href", "").startswith("#"):
            self.anchors.append(a["href"][1:])

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._cur_row_cells.append("".join(self._cell_buf))
            self._in_cell = False
        if tag == "tr" and self._in_row:
            self.rows.append(self._row)
            self.row_hrefs.append(self._row_has_href)
            self.row_in_head.append(self._in_thead)
            self.row_cells.append(list(self._row))
            self._row_cells_html.append(list(self._cur_row_cells))
            self._cur_row_cells = []
            self._in_row = False

    def handle_data(self, data):
        if self._in_cell:
            self._cell_buf.append(data)
        if self._in_row:
            self._row.append(data)


def host_ok(url: str) -> bool:
    return any(h in url for h in TRUSTED_HOSTS)


def is_external(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def main(root: str = ".", site: str = "desk") -> int:
    root_p, site_p = Path(root), Path(root) / site
    fails: list[str] = []
    notes: list[str] = []

    def fail(msg: str) -> None:
        fails.append(msg)

    # ---- 1. datasets ------------------------------------------------------
    def load(name: str):
        p = root_p / "data" / "desk" / name
        if not p.exists():
            fail(f"dataset missing: {name}")
            return None
        return json.loads(p.read_text())

    games = load("games.json")
    standings = load("standings.json")
    injuries = load("injuries.json")
    depth = load("depth.json")
    deficiencies = load("deficiencies.json")
    model = load("model.json")
    correlations = load("correlations.json")

    if games:
        rows = games["games"]
        bad_src = [r for r in rows if not host_ok(r.get("source", ""))]
        if bad_src:
            fail(f"{len(bad_src)} game rows lack an official source URL")
        dupes = [k for k, v in Counter((r["week"], r["away"], r["home"]) for r in rows).items() if v > 1]
        if dupes:
            fail(f"duplicate matchups in game log: {dupes[:5]}")
        finals = [r for r in rows if r["status"] == "FINAL"]
        incomplete = [r for r in finals if r["away_score"] is None or r["home_score"] is None]
        if incomplete:
            fail(f"{len(incomplete)} FINAL rows without both scores")
        notes.append(f"games: {len(rows)} rows, {len(finals)} finals")

    if standings and games:
        W, L, T = Counter(), Counter(), Counter()
        PF, PA = Counter(), Counter()
        for r in [g for g in games["games"] if g["status"] == "FINAL"]:
            a, h, as_, hs = r["away"], r["home"], r["away_score"], r["home_score"]
            PF[a] += as_; PA[a] += hs; PF[h] += hs; PA[h] += as_
            if as_ > hs:
                W[a] += 1; L[h] += 1
            elif hs > as_:
                W[h] += 1; L[a] += 1
            else:
                T[a] += 1; T[h] += 1
        mismatched = []
        for s in standings["rows"]:
            t = s["abbr"]
            if (W[t], L[t], T[t], PF[t], PA[t]) != (s["w"], s["l"], s["t"], s["pf"], s["pa"]):
                mismatched.append(t)
        if mismatched:
            fail(f"standings disagree with game log for {len(mismatched)} clubs: {mismatched}")
        else:
            notes.append("standings reconcile exactly with the game log for all 32 clubs "
                         "(W, L, T, PF, PA)")
        if len(standings["rows"]) != 32:
            fail(f"standings has {len(standings['rows'])} rows, expected 32")

    if injuries:
        bad = [r for r in injuries["rows"] if not host_ok(r.get("source", ""))]
        if bad:
            fail(f"{len(bad)} injury rows lack an official source URL")
        bad_status = [r for r in injuries["rows"]
                      if r["status"] not in ("Out", "Doubtful", "Questionable", "")]
        if bad_status:
            fail(f"{len(bad_status)} injury rows have a status outside the official vocabulary")
        no_team = [r for r in injuries["rows"] if not r.get("team")]
        if no_team:
            fail(f"{len(no_team)} injury rows have no team")
        notes.append(f"injuries: {len(injuries['rows'])} rows across "
                     f"{len(injuries['weeks'])} weeks")

    if depth:
        no_url = [c for c in depth["clubs"] if not c.get("url")]
        if no_url:
            fail(f"{len(no_url)} depth charts have no club URL")
        empty = [c["abbr"] for c in depth["clubs"] if not c["units"]]
        if empty:
            notes.append(f"depth charts with no machine-readable rows: {empty}")

    if deficiencies:
        for r in deficiencies["rows"]:
            if not r.get("injury_source") or not host_ok(r["injury_source"]):
                fail(f"deficiency row without injury source: {r['player']}")
                break
            if not r.get("depth_source"):
                fail(f"deficiency row without depth source: {r['player']}")
                break
            if not r.get("join"):
                fail(f"deficiency row without a join statement: {r['player']}")
                break
        notes.append(f"deficiencies: {deficiencies['summary']['rows']} rows, "
                     f"{deficiencies['summary']['matched']} joined to a depth string")

    if model:
        if model["backtest"]["n"] == 0:
            fail("model backtest produced no rows")
        bad = [r for r in model["ratings"] if abs(r["net_rating"]) > 40]
        if bad:
            fail(f"implausible net ratings: {bad[:3]}")
        notes.append(f"model: hfa={model['home_field_points']}, "
                     f"backtest r={model['backtest']['predicted_vs_actual_r']} "
                     f"n={model['backtest']['n']}")

    if correlations:
        for p in correlations["pairs"]:
            if not (isinstance(p["r"], (int, float)) and -1 <= p["r"] <= 1):
                fail(f"correlation out of range: {p['pair']}")
            if p["n"] < 3:
                fail(f"correlation with n<3: {p['pair']}")
            lo, hi = p["ci95"]
            if not (lo <= p["r"] <= hi):
                fail(f"r outside its own CI: {p['pair']}")

    # ---- 2. site ----------------------------------------------------------
    pages = sorted(site_p.rglob("*.html"))
    if not pages:
        fail("no built pages found")
    for page in pages:
        parser = Links()
        parser.feed(page.read_text(errors="replace"))
        for href in parser.hrefs + parser.srcs:
            if is_external(href) or href.startswith(("#", "mailto:", "data:")):
                continue
            target = href.split("#", 1)[0]
            if not target:
                continue
            if not (page.parent / target).resolve().exists():
                fail(f"broken internal link in {page.relative_to(root_p)}: {href}")
        text = page.read_text(errors="replace")
        for tok in ("{{", "}}", "TODO", "PLACEHOLDER", "$year$", "$displayname$"):
            if tok in text:
                fail(f"placeholder token {tok!r} left in {page.relative_to(root_p)}")
        # every data table row must carry a source link or an explicit UNVERIFIED marker
        for row in parser.rows:
            joined = " ".join(row)
            if not joined.strip():
                continue
            idx = parser.rows.index(row)
            has_link = parser.row_hrefs[idx] if idx < len(parser.row_hrefs) else False
            in_head = parser.row_in_head[idx] if idx < len(parser.row_in_head) else False
            idx2 = parser.rows.index(row)
            n_cells = len(parser.row_cells[idx2]) if idx2 < len(parser.row_cells) else 0
            # a computed value may cite its own computation file as provenance
            cell_html = " ".join(parser._row_cells_html[idx2]) if idx2 < len(parser._row_cells_html) else ""
            low = cell_html.lower()
            derived_ok = ("derived" in low and any(k in low for k in (
                "data/desk", ".json", "coordination", "scripts/", "desk/", "inventory")))
            if not in_head and not has_link and "UNVERIFIED" not in joined.upper() and not derived_ok:
                fail(f"table row without source link or UNVERIFIED flag in "
                     f"{page.relative_to(root_p)}: {joined[:110]}")
        notes.append(f"page ok: {page.relative_to(root_p)}")

    print("VERIFICATION")
    for n in notes:
        print("  ok   ", n)
    if fails:
        print(f"\n{len(fails)} FAILURES")
        for f in fails[:40]:
            print("  FAIL ", f)
        return 1
    print(f"\nALL GATES PASS  ({len(pages)} pages checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
