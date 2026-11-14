#!/usr/bin/env python3
"""Origin module verifier (session arena/f2df8317-x3).

Re-derives every published number from the frozen inputs and checks the module
pages. Exit 1 on any failure. Checks:

  1. results feed: every row has an official nfl.com source; statuses valid;
     cross-check vs the independent desk transcription has zero conflicts
  2. origination order: seq(sides) < seq(totals) < seq(moneylines)
  3. moneylines reproducible: p = Phi(adj_margin/sigma) and fair ML recompute
     exactly from each market's own side row
  4. snapshot store: every market has an open row with model_line equal to its
     fair line; every market has a close row (pending until cycle close);
     market_line/diff blank exactly when no price source exists
  5. leaderboard: rank computed from signal metrics only; every ranked row has
     n > 0; props row BLOCKED; staking cells blank while no prices exist
  6. depth: every row has sources; blank replacement implies a stated reason;
     per-club index equals the sum of its rows; ordinals within 1..4
  7. correlations: every sourced row has n >= 4 and both axes officially
     sourced; derived-axis rows quarantined; CI present for n >= 4
  8. gates: demotion gate D-1 exists with all triggers registered
  9. HTML: relative links resolve; no root-absolute URLs; tbody rows carry an
     external link or an explicit badge (repo row-source rule); pages parse
 10. build determinism: a second build produces byte-identical pages

Usage: python3 scripts/origin_verify.py [--rebuild-check]
"""
from __future__ import annotations

import json
import math
import re
import sys
import tempfile
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = ROOT / "origin"
DATA = ORIGIN / "data"

FAILURES: list[str] = []
CHECKS = 0


def check(cond: bool, msg: str) -> None:
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append(msg)


def jload(p: Path):
    return json.loads(p.read_text())


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []
        self.rows: list[str] = []
        self._row: list[str] = []
        self._in_row = False
        self._in_tbody = False
        self.row_refs: list[int] = []
        self._refs = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])
            if self._in_row:
                self._refs += 1
        if tag == "tbody":
            self._in_tbody = True
        if tag == "tr":
            self._in_row = True
            self._row = []
            self._refs = 0

    def handle_endtag(self, tag):
        if tag == "tr":
            self._in_row = False
            if self._in_tbody:  # thead rows are headers, not claims
                self.rows.append(" ".join(self._row))
                self.row_refs.append(self._refs)
        if tag == "tbody":
            self._in_tbody = False

    def handle_data(self, data):
        if self._in_row:
            self._row.append(data)


BADGE_RE = re.compile(
    r"UNVERIFIED|DERIVED|PENDING|BLOCKED|RECORDED|PASS|REGISTERED|DEMOTED|no chart|n/a",
    re.I)


def main() -> int:
    # ---------------- 1. results feed ----------------
    feed_path = DATA / "results.json"
    check(feed_path.exists(), "results feed missing — run scripts/origin_capture.py first")
    if feed_path.exists():
        feed = jload(feed_path)
        games = feed["games"]
        check(len(games) > 0, "results feed is empty")
        check(feed["counts"]["final"] == sum(1 for g in games if g["status"] == "FINAL"),
              "counts.final disagrees with the rows")
        bad_src = [g for g in games if not str(g.get("source", "")).startswith("https://www.nfl.com/")]
        check(not bad_src, f"{len(bad_src)} feed rows lack an official source URL")
        bad_status = [g for g in games if g["status"] not in ("FINAL", "SCHEDULED")]
        check(not bad_status, "feed rows with unknown status")
        finals = [g for g in games if g["status"] == "FINAL"]
        bad_scores = [g for g in finals if not isinstance(g["away_score"], int)
                      or not isinstance(g["home_score"], int)]
        check(not bad_scores, "final rows without integer scores")
        sched = [g for g in games if g["status"] == "SCHEDULED"]
        blank_sched = [g for g in sched if g["away_score"] is not None or g["home_score"] is not None]
        check(not blank_sched, "scheduled rows carry scores — never inferred")
        cc = feed.get("cross_check_vs_desk_transcription", {})
        if cc.get("available"):
            check(len(cc.get("conflicts", [])) == 0,
                  f"results-feed cross-check has {len(cc['conflicts'])} conflicts with the "
                  "desk transcription — resolve before trusting the feed")
            check(cc.get("agree", 0) == cc.get("matched", 1),
                  "cross-check agreement is not total")

    # ---------------- 2-6. markets, snapshots, leaderboard, depth, gates ----------------
    markets = jload(DATA / "markets.json")["rows"] if (DATA / "markets.json").exists() else []
    if not markets:
        check(False, "markets.json missing/empty")
        # keep the verifier going for the remaining checks
    types_seq = {}
    for m in markets:
        types_seq.setdefault(m["market_type"], []).append(m["seq"])
    if types_seq.get("side") and types_seq.get("total") and types_seq.get("moneyline"):
        check(max(types_seq["side"]) < min(types_seq["total"]),
              "origination order violated: totals before sides")
        check(max(types_seq["total"]) < min(types_seq["moneyline"]),
              "origination order violated: moneylines before totals")
    check(len(markets) == 39, f"expected 39 originated markets (13 games x 3), got {len(markets)}")

    prereg = jload(ROOT / "hub" / "data" / "prereg.json")
    sigma = float(prereg["params"]["hfa_conversion_sigma"])
    lines = {r_["game"]: r_ for r_ in jload(ROOT / "hub" / "data" / "lines.json")["rows"]}
    for m in markets:
        if m["market_type"] == "moneyline":
            src = lines[m["game"]]
            p = norm_cdf(src["adj_margin_home"] / sigma)
            check(abs(m["p_home_win"] - round(p, 4)) < 1e-9,
                  f"moneyline {m['market_id']} p does not reproduce from its side")
            pf = 100.0 * p / (1 - p)
            pa = 100.0 * (1 - p) / p
            rnd = lambda v: int(math.floor(v + 0.5))
            if p >= 0.5:
                hml, aml = -rnd(pf), +rnd(pa)
            else:
                hml, aml = +rnd(pf), -rnd(pa)
            check(m["fair_line"] == hml and m["away_fair_ml"] == aml,
                  f"moneyline {m['market_id']} fair odds do not reproduce "
                  f"(published {m['fair_line']}/{m['away_fair_ml']}, recomputed {hml}/{aml})")
        check(m["market_line"] == "" and m["market_source"] == "" and m["diff"] == "",
              f"market {m['market_id']} has market/diff values without a price source — "
              "values must stay blank until a source exists")

    snaps = jload(DATA / "snapshots.json")
    snaps = snaps if isinstance(snaps, list) else snaps.get("rows", [])
    by_market: dict[str, set[str]] = {}
    for s in snaps:
        by_market.setdefault(s["market_id"], set()).add(s["phase"])
    for m in markets:
        phases = by_market.get(m["market_id"], set())
        check("open" in phases, f"market {m['market_id']} has no open snapshot")
        check("close" in phases, f"market {m['market_id']} has no close snapshot row")
    idx = {m["market_id"]: m for m in markets}
    for s in snaps:
        if s["phase"] == "open":
            m = idx[s["market_id"]]
            if m["market_type"] == "moneyline":
                expect = f"home {m['fair_line']:+d}"
            elif m["market_type"] == "side":
                expect = f"{round(m['fair_line'] * 2) / 2.0:+.1f}".replace("+0.0", "PK").replace("-0.0", "PK")
            else:
                expect = f"{float(m['fair_line']):.1f}"
            check(s["model_line"] == expect,
                  f"open snapshot {s['market_id']} model_line {s['model_line']!r} != market fair line {expect!r}")
        else:
            check(s["model_line"] == "" or s["status"] != "PENDING",
                  f"close snapshot {s['market_id']} claims a number while pending")
        check(s["market_line"] == "" or s["market_source"] != "",
              f"snapshot {s['market_id']}/{s['phase']} carries a market price without a source")

    lb = jload(DATA / "leaderboard.json")
    floor = lb.get("min_signal_n", 100)
    ranked = [x for x in lb["rows"] if x["signal_rank"]]
    check(len(ranked) >= 1, "leaderboard has no ranked strategy")
    for x in lb["rows"]:
        if x["signal_rank"]:
            check(x["signal_n"] >= floor, f"{x['strategy_id']} ranked below the n-floor")
            check(x["signal_value"] is not None, f"{x['strategy_id']} ranked without a value")
        elif x["signal_value"] is not None:
            check(x["signal_n"] < floor,
                  f"{x['strategy_id']} has a value and n>={floor} but no rank")
        if x["strategy_id"] == "LB-5":
            check("BLOCKED" in x["staking"]["status"] or x["signal_value"] is None,
                  "prop strategy must stay BLOCKED without an official source")
        check(x["staking"]["roi_per_100"] == "" if x["staking"]["settled_bets"] == 0 else True,
              f"{x['strategy_id']} has staking ROI without settled bets")
    ranks = sorted(x["signal_rank"] for x in ranked)
    check(ranks == list(range(1, len(ranked) + 1)), "signal ranks are not a dense sequence")
    # rank order must follow the signal metric, ignoring staking entirely
    vals = [(x["signal_value"], x["strategy_id"]) for x in ranked]
    by_rank = sorted(ranked, key=lambda x: x["signal_rank"])
    rest = [x for x in ranked if x["strategy_id"] != "LB-3"]
    brier = [x for x in ranked if x["strategy_id"] == "LB-3"]
    ordered = sorted(rest, key=lambda x: -x["signal_value"]) + sorted(brier, key=lambda x: x["signal_value"])
    check([x["strategy_id"] for x in by_rank] == [x["strategy_id"] for x in ordered],
          "signal rank does not follow the signal metric")

    depth = jload(DATA / "depth.json")
    for x in depth["rows"]:
        check(x["injury_source"].startswith("https://www.nfl.com/"),
              f"depth row {x['club']}/{x['player']} lacks the official report source")
        if not x["replacement"]:
            check(bool(x["reason_if_blank"]),
                  f"depth row {x['club']}/{x['player']} blank replacement without a reason")
        else:
            check(2 <= (x["replacement_ordinal"] or 0) <= 4,
                  f"depth row {x['club']}/{x['player']} ordinal out of range")
            check(x["replacement_ordinal"] > (x["starter_ordinal"] or 0),
                  f"depth row {x['club']}/{x['player']} replacement is not deeper than the starter")
        check(float(x["deficiency_pts"]) > 0, f"depth row {x['club']}/{x['player']} non-positive cost")
    for c in depth["clubs"]:
        s = sum(x["deficiency_pts"] for x in depth["rows"] if x["club"] == c["club"])
        check(abs(s - c["deficiency_index"]) < 0.011,
              f"club {c['club']} deficiency index {c['deficiency_index']} != row sum {s:.2f}")

    corr = jload(DATA / "correlations.json")
    for x in corr["rows"]:
        check(isinstance(x["n"], int) and x["n"] >= 4, f"{x['id']} n missing or too small")
        check(x["inputs_official"] is True, f"{x['id']} not marked officially sourced")
        check(len(x["sources"]) >= 1 and all(s.startswith("http") for s in x["sources"]),
              f"{x['id']} missing source links")
        if x["n"] >= 4:
            check(x["ci95_low"] is not None and x["ci95_high"] is not None,
                  f"{x['id']} missing CI")
    for x in corr["model_diagnostics"]:
        check("DERIVED" in x["sources"][-1] or "DERIVED" in x["note"],
              f"{x['id']} quarantined row must be labelled DERIVED")
    check(any("absolute home margin" in x["y"] for x in corr["rows"]),
          "the corrected |margin| correlation (C-02) is missing")

    gates = jload(DATA / "gates.json")
    d = gates["demotion"]
    check(d["id"] == "D-1" and len(d["triggers"]) >= 4, "demotion gate D-1 incomplete")
    check(all(t.get("threshold_registered_now") for t in d["triggers"]),
          "a D-1 trigger without a registered threshold")
    check(d["re_promotion"]["id"] == "D-2", "re-promotion gate D-2 missing")

    # ---------------- 9. HTML ----------------
    pages = sorted(ORIGIN.glob("*.html"))
    check(len(pages) >= 14, f"expected >= 14 pages, found {len(pages)}")
    all_files = {str(p.relative_to(ORIGIN)) for p in ORIGIN.rglob("*") if p.is_file()}
    for page_path in pages:
        html_text = page_path.read_text()
        parser = Links()
        parser.feed(html_text)
        check(parser.rows, f"{page_path.name} has no table rows")
        for href in parser.hrefs:
            if href.startswith(("http://", "https://", "#", "mailto:")):
                if href.startswith("http://"):
                    FAILURES.append(f"{page_path.name}: insecure http link {href}")
                continue
            check(not href.startswith("/"),
                  f"{page_path.name}: root-absolute link {href} (breaks under /X3/)")
            target = href.split("#", 1)[0]
            if not target:
                continue
            resolved = (page_path.parent / target).resolve()
            ok = resolved.exists() or target in all_files
            check(ok, f"{page_path.name}: broken internal link {href}")
        for row_text, refs in zip(parser.rows, parser.row_refs):
            if not row_text.strip():
                continue
            has_badge = bool(BADGE_RE.search(row_text)) or "no official source" in row_text
            check(refs > 0 or has_badge,
                  f"{page_path.name}: unsourced row {row_text[:100]!r}")
        check("TODO" not in html_text and "PLACEHOLDER" not in html_text.upper()
              or page_path.name == "README.md", f"{page_path.name}: placeholder text")

    # ---------------- 10. determinism ----------------
    if "--rebuild-check" in sys.argv:
        before = {p.name: p.read_bytes() for p in pages}
        subprocess.run([sys.executable, str(ROOT / "scripts" / "origin_build.py")],
                       check=True, capture_output=True)
        for p in pages:
            check(before.get(p.name) == p.read_bytes(), f"{p.name} is not deterministically built")

    print(f"origin_verify: {CHECKS} checks, {len(FAILURES)} failures")
    for f in FAILURES[:30]:
        print("  FAIL:", f)
    if FAILURES:
        return 1
    print("ORIGIN MODULE: ALL GATES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
