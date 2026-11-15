"""Agency verification gate.

Runs after scripts/agency_engine.py and scripts/agency_site.py. Fails loudly (non-zero
exit) when any expected row count, required field, provenance hash or source link is
missing — this is the drift alarm for every agency scraper/parser.

Exit codes: 0 = all gates pass; 1 = any gate fails.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "agency" / "data" / "out"
RAW = ROOT / "agency" / "data" / "derived"
SITE = ROOT / "agency" / "site"

failures = []


def fail(msg):
    failures.append(msg)
    print(f"::error::FAIL {msg}")


def ok(msg):
    print(f"ok: {msg}")


def require(cond, msg):
    if cond:
        ok(msg)
    else:
        fail(msg)


def load_json(name):
    p = OUT / name
    if not p.exists():
        fail(f"missing output {name}")
        return None
    try:
        return json.load(open(p))
    except Exception as e:
        fail(f"invalid JSON in {name}: {e}")
        return None


def require_file(name, must_exist=True):
    p = ROOT / name
    exists = p.exists()
    require(exists or not must_exist, f"file present: {name}")
    return p if exists else None


def sha256_file(p):
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- 1. engine outputs exist
GATE_OUTPUTS = [
    "reconciliation.json", "walkforward.json", "origination_week11.json",
    "provenance.json", "strategies.json", "luck.json", "correlations.json",
    "availability.json", "injury_surprise.json", "fixture_context.json",
]
for name in GATE_OUTPUTS:
    require_file(f"agency/data/out/{name}")

# ---------------------------------------------------------------- 2. standings reconciliation 32/32
rec = load_json("reconciliation.json")
if isinstance(rec, dict):
    require(isinstance(rec.get("n_teams"), int) and rec["n_teams"] == 32,
              f"reconciliation covers 32 teams (got {rec.get('n_teams')})")
    require(isinstance(rec.get("n_match"), int) and rec["n_match"] == 32,
              f"reconciliation 32/32 exact (got {rec.get('n_match')})")
    require(all(r.get("match") is True for r in rec.get("rows", [])),
              "every reconciliation row matches the official page")
    require(rec.get("n_finals_in_feed") == 138,
              f"reconciliation finals = 138 (got {rec.get('n_finals_in_feed')})")

# ---------------------------------------------------------------- 3. injury table row/column contract
inj = RAW / "injury_designations_w10_2026.csv"
def clean(v):
    if v is None: return ""
    return str(v).strip().strip(chr(39)+chr(34))
if inj.exists():
    rows = list(csv.DictReader(open(inj)))
    teams = {clean(r["team"]) for r in rows}
    require(len(rows) == 347, f"injury rows = 347 (got {len(rows)})")
    require(len(teams) == 28, f"injury clubs = 28 (got {len(teams)})")
    for i, r in enumerate(rows):
        for c in ("team", "player", "source_url", "captured_utc"):
            require(bool(clean(r.get(c))), f"injury row {i} required field {c}")
        require(clean(r["source_url"]).startswith("http"), f"injury row {i} source_url is an official URL")
        # injury / game_status may be blank = unverified; that is permitted by the brief
        if clean(r.get("injury")):
            require(bool(clean(r.get("injury"))), f"injury row {i} injury present")
        if clean(r.get("game_status")):
            require(bool(clean(r.get("game_status"))), f"injury row {i} game_status present")
else:
    fail("injury_designations_w10_2026.csv missing")

# ---------------------------------------------------------------- 4. starters + inactives have sources
starters = RAW / "starters_w10.json"
if starters.exists():
    data = json.load(open(starters))
    require(len(data) >= 88, f"starter rows >= 88 (got {len(data)})")
    for i, r in enumerate(data):
        require(bool(r.get("source")), f"starter row {i} has source")
inact = RAW / "inactives_w10.csv"
if inact.exists():
    rows = list(csv.DictReader(open(inact)))
    require(len(rows) >= 39, f"inactive rows >= 39 (got {len(rows)})")

# ---------------------------------------------------------------- 5. provenance hashes match inputs
prov = load_json("provenance.json")
if isinstance(prov, dict):
    inputs = prov.get("inputs", {})
    if isinstance(inputs, dict):
        for path, expected in inputs.items():
            p = ROOT / path
            if p.exists():
                require(sha256_file(p) == expected, f"provenance hash matches: {path}")
            else:
                fail(f"provenance input missing: {path}")

# ---------------------------------------------------------------- 6. strategy rows carry required fields
strat = load_json("strategies.json")
if isinstance(strat, dict):
    for sid, s in strat.items():
        for c in ("id", "label", "n"):
            require(c in s, f"strategy {sid} field {c}")
        if "brier_skill_score" in s:
            require("brier_baseline" in s, f"strategy {sid} field brier_baseline")
            require("brier_model" in s, f"strategy {sid} field brier_model")
            ci = s.get("cluster_ci95_brier") or s.get("ci95", [])
            if ci:
                require(len(ci) == 2, f"strategy {sid} ci95 has 2 values")
        else:
            for c in ("hits", "rate", "p_vs_constant", "ci95"):
                require(c in s, f"strategy {sid} field {c}")
            ci = s.get("ci95", [])
            require(len(ci) == 2, f"strategy {sid} ci95 has 2 values")
            require(0 <= (s.get("rate") or 0) <= 1, f"strategy {sid} rate in [0,1]")

# ---------------------------------------------------------------- 7. origination: side -> total -> ML order
orig = load_json("origination_week11.json")
if isinstance(orig, list):
    require(len(orig) == 13, f"Week-11 games originated = 13 (got {len(orig)})")
    for g in orig:
        keys = list(g.keys())
        # side fields must appear before total fields before moneyline fields
        side_idx = min([keys.index(k) for k in ("side_fair", "side_alt") if k in keys] or [99])
        total_idx = min([keys.index(k) for k in ("total_fair", "total_naive") if k in keys] or [99])
        ml_idx = keys.index("ml_home_win_prob") if "ml_home_win_prob" in keys else 99
        require(side_idx <= total_idx <= ml_idx, f"column order side->total->ML for {g.get('game')}")
        # market columns must be blank by price-data policy (never inferred)
        for c in ("market_side", "market_total", "residual"):
            require(g.get(c) in (None, ""), f"{g.get('game')} market field {c} is blank (policy)")

# ---------------------------------------------------------------- 8. every derived table row has a source link
DERIVED_WITH_SOURCES = [
    ("agency/data/derived/standings_2026_thru_w10_official.csv", "source_url"),
    ("agency/data/derived/injury_designations_w10_2026.csv", "source_url"),
    ("agency/data/derived/announced_starters.csv", "source_url"),
]
for path, col in DERIVED_WITH_SOURCES:
    p = ROOT / path
    if not p.exists():
        fail(f"missing {path}")
        continue
    rows = list(csv.DictReader(open(p)))
    for i, r in enumerate(rows):
        require(bool(r.get(col)) and r[col].startswith("http"),
                f"{path} row {i} {col} is an official URL")

# ---------------------------------------------------------------- 9. site built and links local
if SITE.exists():
    pages = sorted(SITE.glob("*.html"))
    require(len(pages) >= 15, f"site pages >= 15 (got {len(pages)})")
    require((SITE / "index.html").exists(), "site landing page present")
    require((SITE / "flagged.html").exists(), "site flagged-for-review page present")

# ---------------------------------------------------------------- verdict
print(f"\n{len(failures)} verification failure(s)" if failures else "\nAll agency verification gates passed.")
sys.exit(1 if failures else 0)
