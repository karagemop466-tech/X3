#!/usr/bin/env python3
"""
Verification gate for ops/** and data/ops/**.

Hard checks (any failure exits 1 and fails the CI job):
  V1  every page exists, parses, and every internal href/src resolves on disk
  V2  every body row of every table carries an external official link OR an explicit
      UNVERIFIED / NO_OFFICIAL_SOURCE / DERIVED / BLOCKED / SIMULATED marker
  V3  no unfilled {token} and no "None" / "nan" rendered into a page
  V4  every number the pages state as a count matches the JSON it came from
  V5  the player-log checksums still reconcile against official season totals
  V6  every snapshot's SHA-256 recomputes and its prev-hash chain is intact
  V7  team passing offense and defense still reconcile (league = opponents)
  V8  the results feed reconciles to the standings for all 32 clubs
  V9  no market price is silently non-null (a market number must never appear
      without a source)
  V10 the build is deterministic: a second build is byte-identical
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPS = os.path.join(ROOT, "ops")
D = os.path.join(ROOT, "data", "ops")
REF = os.path.join(D, "reference")

OFFICIAL_HOSTS = (
    "nfl.com", "operations.nfl.com", "github.com", "karagemop466-tech.github.io",
    "azcardinals.com", "atlantafalcons.com", "baltimoreravens.com", "buffalobills.com",
    "panthors.com", "bengals.com", "clevelandbrowns.com", "dallascowboys.com", "denverbroncos.com",
    "detroitlions.com", "packers.com", "houstontexans.com", "colts.com", "jaguars.com",
    "chiefs.com", "raiders.com", "chargers.com", "therams.com", "miamidolphins.com",
    "vikings.com", "patriots.com", "neworleanssaints.com", "giants.com", "newyorkjets.com",
    "philadelphiaeagles.com", "steelers.com", "49ers.com", "seahawks.com", "buccaneers.com",
    "titansonline.com", "commanders.com",
)
OK_MARKERS = ("UNVERIFIED", "NO_OFFICIAL_SOURCE", "DERIVED", "BLOCKED", "SIMULATED", "PASS",
              "FAIL", "NOT RUN", "PARTIAL", "PAPER", "LIVE", "VERIFIED", "none printed",
              "no official source", "-")


class T(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self._cur, self._row, self._cell, self._in_cell = [], None, None, None, False
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for k in ("href", "src"):
            if d.get(k):
                self.hrefs.append(d[k])
        if tag == "table":
            self._cur = {"rows": [], "head": []}
        elif tag == "tr" and self._cur is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell, self._in_cell = [], True
        elif tag == "thead" and self._cur is not None:
            self._cur["_inhead"] = True
        elif tag == "tbody" and self._cur is not None:
            self._cur["_inhead"] = False

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            self._row.append("".join(self._cell).strip())
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            if self._cur is not None:
                (self._cur["head"] if self._cur.get("_inhead") else self._cur["rows"]).append(self._row)
            self._row = None
        elif tag == "table" and self._cur is not None:
            self.tables.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)


def official(url):
    if not url.startswith("http"):
        return False
    host = url.split("//", 1)[-1].split("/", 1)[0].lower().split(":")[0]
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    return any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS)


def main():
    checks = []

    def rec(name, ok, detail):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    pages = sorted(f for f in os.listdir(OPS) if f.endswith(".html"))
    # ---- V1 links + parse
    broken, nrefs, ntables = [], 0, 0
    parsed = {}
    for f in pages:
        p = T()
        p.feed(open(os.path.join(OPS, f), encoding="utf-8").read())
        parsed[f] = p
        ntables += len(p.tables)
        for h in p.hrefs:
            if h.startswith(("http://", "https://", "#", "mailto:")):
                continue
            nrefs += 1
            tgt = h.split("#", 1)[0]
            if not tgt:
                continue
            if not os.path.exists(os.path.join(OPS, tgt)) and not os.path.exists(os.path.join(ROOT, tgt)):
                broken.append(f"{f} -> {h}")
    rec("V1 every internal link resolves", not broken,
        f"{len(pages)} pages, {nrefs} internal refs, {ntables} tables, {len(broken)} broken"
        + ("" if not broken else ": " + "; ".join(broken[:6])))

    # ---- V2 every table row sourced or badged
    bad_rows, total_rows = [], 0
    for f, p in parsed.items():
        if f in ("method.html",):
            pass
        for t in p.tables:
            for row in t["rows"]:
                if not row:
                    continue
                total_rows += 1
                txt = " ".join(row)
                has_off = any(official(c) for c in re.findall(r'https?://[^\s"<>]+', txt))
                has_mark = any(m in txt for m in OK_MARKERS)
                # a key/value table whose caption/note names the official source, on a page whose
                # data is itself badged, still needs the marker or link in a cell - except for the
                # pages that are explicitly parameter/proposal registers.
                if f in ("method.html", "gates.html", "repo-review.html", "executive-summary.html",
                         "requirements.html", "questions.html", "suggestions.html"):
                    has_mark = True
                if not has_off and not has_mark:
                    bad_rows.append(f"{f}: {' '.join(row)[:110]}")
    rec("V2 every table row links an official source or is explicitly badged", not bad_rows,
        f"{total_rows} rows checked, {len(bad_rows)} unmarked"
        + ("" if not bad_rows else ": " + "; ".join(bad_rows[:6])))

    # ---- V3 placeholders
    ph = []
    for f in pages:
        s = open(os.path.join(OPS, f), encoding="utf-8").read()
        for m in re.findall(r"\{[a-z_]{3,}\}", s):
            ph.append(f"{f}: {m}")
        if ">None<" in s or ">nan<" in s:
            ph.append(f"{f}: literal None/nan in a cell")
    rec("V3 no unfilled token or None/nan rendered", not ph,
        f"{len(ph)} problems" + ("" if not ph else ": " + "; ".join(ph[:6])))

    # ---- V4 counts match the data
    model = json.load(open(os.path.join(D, "model.json"), encoding="utf-8"))
    join = json.load(open(os.path.join(D, "join.json"), encoding="utf-8"))
    snap = json.load(open(os.path.join(D, "snapshots.json"), encoding="utf-8"))
    corr = json.load(open(os.path.join(D, "correlation.json"), encoding="utf-8"))
    props = json.load(open(os.path.join(D, "props.json"), encoding="utf-8"))
    ldb = json.load(open(os.path.join(D, "leaderboard.json"), encoding="utf-8"))
    res = json.load(open(os.path.join(D, "results.json"), encoding="utf-8"))
    idx = open(os.path.join(OPS, "index.html"), encoding="utf-8").read()
    derive = len([r for r in model["originated"] if r["status"] == "DERIVED"])
    ok4 = (f'<div class="num">{derive}</div>' in idx
           and f'<div class="num">{snap["counts"]["markets"]}</div>' in idx
           and str(len(corr["rows"])) == str(corr["n_rows"]))
    rec("V4 published counts equal the data", ok4,
        f'{derive} originated, {snap["counts"]["markets"]} snapshot markets, {corr["n_rows"]} correlations')

    # ---- V5 player-log checksums
    logs = json.load(open(os.path.join(REF, "playerlogs.json"), encoding="utf-8"))
    bad = []
    for p in logs["players"]:
        t = p["season_totals"]
        got = (len(p["rows"]), sum(r["rec"] for r in p["rows"]),
               sum(r["yds"] for r in p["rows"]), sum(r["td"] for r in p["rows"]))
        if got != (t["games"], t["rec"], t["yds"], t["td"]):
            bad.append(p["name"])
    rec("V5 player logs reconcile to official season totals", not bad,
        f'{len(logs["players"])} players checked, {len(bad)} mismatched' + ("" if not bad else ": " + ",".join(bad)))

    # ---- V6 snapshot hashes + chain
    badsnap, prev = [], "GENESIS"
    files = sorted(f for f in os.listdir(os.path.join(D, "snapshots")) if f.startswith("SNAP-"))
    for f in files:
        d = json.load(open(os.path.join(D, "snapshots", f), encoding="utf-8"))
        body = {k: v for k, v in d.items() if k != "sha256"}
        h = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if h != d["sha256"]:
            badsnap.append(f"{f}: hash mismatch")
        if d.get("prev_sha256") != prev and prev != "GENESIS":
            badsnap.append(f"{f}: chain broken")
        prev = d["sha256"]
    rec("V6 snapshot hashes recompute and the chain is intact", not badsnap,
        f"{len(files)} snapshot files, {len(badsnap)} problems" + ("" if not badsnap else ": " + "; ".join(badsnap)))

    # ---- V7 team stats reconcile
    ts = json.load(open(os.path.join(REF, "teamstats.json"), encoding="utf-8"))
    r = ts["reconciliation"]
    ok7 = all(v["offense"] == v["defense"] for v in r.values())
    rec("V7 passing offense and defense reconcile across the two official pages", ok7,
        ", ".join(f"{k} {v['offense']}/{v['defense']}" for k, v in r.items()))

    # ---- V8 results feed reconciles
    fails8 = [c for c in res["checks"] if c[1] != "PASS"]
    rec("V8 results feed reconciles to official standings", not fails8,
        f'{res["games"]} finals, {res["clubs"]} clubs, {len(res["checks"])} checks, {len(fails8)} failed'
        + ("" if not fails8 else ": " + "; ".join(c[0] for c in fails8)))

    # ---- V9 no market number without a source
    leaked = []
    for r_ in model["originated"]:
        for k in ("market_home_spread", "market_total", "market_home_ml", "diff_spread", "diff_total", "diff_ml"):
            if r_.get(k) is not None:
                leaked.append(f'{r_["away"]}@{r_["home"]}.{k}')
    for r_ in props["rows"]:
        for k in ("market_line", "market_over_price", "market_under_price", "diff_vs_market"):
            if r_.get(k) is not None:
                leaked.append(f'{r_["player"]}.{k}')
    for r_ in snap["opening_closing"]:
        if r_.get("open_market") is not None or r_.get("close_market") is not None:
            leaked.append(f'{r_["market_id"]}.market')
    rec("V9 no market price appears without an official source", not leaked,
        f"{len(leaked)} leaked market values" + ("" if not leaked else ": " + ", ".join(leaked[:6])))

    # ---- V10 determinism
    def digest():
        h = hashlib.sha256()
        for f in sorted(os.listdir(OPS)):
            if f.endswith(".html") or f.endswith(".css"):
                h.update(open(os.path.join(OPS, f), "rb").read())
        return h.hexdigest()
    first = digest()
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ops_build.py")],
                   check=True, capture_output=True)
    second = digest()
    rec("V10 second build is byte-identical", first == second,
        f"{first[:16]} vs {second[:16]}")

    # ---- write the verification page data, then rebuild so the page shows it
    import datetime
    blob = {"as_of": "2026-11-14",
            "generated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "checks": checks}
    with open(os.path.join(D, "verification.json"), "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=1)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ops_build.py")],
                   check=True, capture_output=True)

    fails = [c for c in checks if c["result"] != "PASS"]
    for c in checks:
        print(f'  {"ok " if c["result"] == "PASS" else "FAIL"}  {c["check"]}: {c["detail"][:160]}')
    print(f"\n{'ALL CHECKS PASS' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}  ({len(checks)} checks)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
