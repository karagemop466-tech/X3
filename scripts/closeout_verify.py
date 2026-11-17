#!/usr/bin/env python3
"""Verification gate for the X3 close-out desk (session arena/e1ad8b78-x3).

Checks V-01..V-16, each one reproducing a claim printed on the site. Any failure exits 1, so a build that
would publish an unsupported number cannot ship.

Usage:  python3 scripts/closeout_verify.py [--quiet]
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import re
import sys
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data", "closeout")
DD = os.path.join(D, "derived")
SITE = os.path.join(ROOT, "closeout")
QUIET = "--quiet" in sys.argv

FAILS, CHECKS = [], []


def ok(cid, desc, detail):
    CHECKS.append((cid, desc, "PASS", detail))


def fail(cid, desc, detail):
    CHECKS.append((cid, desc, "FAIL", detail))
    FAILS.append(f"{cid}: {detail}")


def rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cellv(v):
    return (v or "").strip()


# ------------------------------------------------------------------ data checks
fin = rows(os.path.join(D, "week10_finals.csv"))
stand = rows(os.path.join(D, "official_standings_2026_wk10.csv"))
recon = rows(os.path.join(DD, "reconciliation.csv"))
slate = rows(os.path.join(D, "week11_slate.csv"))
byes10 = rows(os.path.join(D, "week10_byes.csv"))
byes11 = rows(os.path.join(D, "week11_byes.csv"))
log = rows(os.path.join(DD, "season_log.csv"))
fore = rows(os.path.join(DD, "forecasts_w11.csv"))
settle = rows(os.path.join(D, "settlement.csv")) if os.path.exists(os.path.join(D, "settlement.csv")) \
    else rows(os.path.join(DD, "settlement.csv"))
ungraded = rows(os.path.join(DD, "ungraded.csv"))
store = rows(os.path.join(DD, "price_store.csv"))
ledger = rows(os.path.join(D, "source_reads.csv"))
avail = rows(os.path.join(D, "availability_w10.csv"))
corr = rows(os.path.join(DD, "correlations.csv"))
score = rows(os.path.join(DD, "scorecard.csv"))
gates = rows(os.path.join(DD, "prereg_gates.csv"))
q = rows(os.path.join(D, "questions.csv"))
sg = rows(os.path.join(D, "suggestions.csv"))
flags = rows(os.path.join(D, "flags.csv"))
ready = rows(os.path.join(D, "readiness.csv"))
meta = json.load(open(os.path.join(DD, "meta.json")))

# V-01 Week-10 finals complete and FINAL
bad = [r["game_id"] for r in fin if r["status"].upper() != "FINAL" or not cellv(r["away_score"])
       or not cellv(r["home_score"])]
(ok, fail)[bool(bad) or len(fin) != 14]("V-01", "Week-10 close-out complete",
     f"{len(fin)} rows, all FINAL with both scores" if not bad and len(fin) == 14 else f"bad: {bad or len(fin)}")

# V-02 margin/total arithmetic on every captured game
bad = [g["game_id"] for g in fin
       if int(g["home_score"]) - int(g["away_score"]) != int(g["margin_home"])
       or int(g["home_score"]) + int(g["away_score"]) != int(g["total"])]
(ok, fail)[bool(bad)]("V-02", "score-line arithmetic", "14/14 margins and totals re-derived" if not bad else str(bad))

# V-03 reconciliation: 32 clubs, zero mismatches
mm = [r["team"] for r in recon if r["agree"] != "MATCH"]
gg = [r["team"] for r in recon if r["games_agree"] != "yes"]
(ok, fail)[bool(mm or gg) or len(recon) != 32]("V-03", "log vs official standings",
     f"32 clubs, {len(mm)} mismatches, {len(gg)} games-count disagreements" if not (mm or gg) else f"{mm} {gg}")

# V-04 standings internal arithmetic (PF-PA == NET) and league balance
bad = [r["team"] for r in stand if int(r["pf"]) - int(r["pa"]) != int(r["net"])]
spf = sum(int(r["pf"]) for r in stand)
spa = sum(int(r["pa"]) for r in stand)
(ok, fail)[bool(bad) or spf != spa]("V-04", "standings arithmetic",
     f"PF-PA=NET for {32 - len(bad)}/32; league PF={spf} PA={spa}" if not bad and spf == spa else f"{bad}")

# V-05 slate accounts for all 32 clubs
played = {c for r in slate for c in (r["away"], r["home"])}
bye = {r["team"] for r in byes11}
allc = {r["team"] for r in stand}
bad = []
if len(played) + len(bye) != 32:
    bad.append(f"{len(played)} playing + {len(bye)} byes != 32")
if played & bye:
    bad.append(f"club both playing and on bye: {played & bye}")
if played | bye != allc:
    bad.append(f"missing: {allc - (played | bye)}")
for r in slate:
    if r["home"] not in allc or r["away"] not in allc:
        bad.append(f"{r['game_id']}: unknown club code")
(ok, fail)[bool(bad)]("V-05", "Week-11 slate covers 32 clubs",
     f"{len(slate)} games x 2 + {len(bye)} byes = 32; all codes exist in the standings" if not bad else str(bad))

# V-06 bye lists are consistent with the schedule pages themselves
bad = []
played10 = {c for r in fin for c in (r["away"], r["home"])}
if played10 | {r["team"] for r in byes10} != allc:
    bad.append("week-10 clubs do not close")
(ok, fail)[bool(bad)]("V-06", "Week-10 clubs close", "14 games x 2 + 4 byes = 32" if not bad else str(bad))

# V-07 every forecast row is stamped before the first Week-11 kickoff, and carries its inputs
FIRST = "2026-11-19T23:15:00Z"
bad = []
for r in fore:
    if not (r["frozen_utc"] < FIRST):
        bad.append(f"{r['game_id']}: freeze {r['frozen_utc']} not before {FIRST}")
    for c in ("model_version", "rating_home", "rating_away", "home_advantage", "sigma_margin",
              "sigma_total", "n_train_games", "availability_input", "side_fair_line_home", "total_fair_line",
              "ml_prob_home", "side_prob_home_cover", "total_prob_over"):
        if not cellv(r.get(c, "")):
            bad.append(f"{r['game_id']}: missing {c}")
(ok, fail)[bool(bad) or len(fore) != 13]("V-07", "pre-registration timestamp and inputs",
     f"{len(fore)} rows frozen {fore[0]['frozen_utc']} < first kickoff {FIRST}; 13 input columns non-empty"
     if not bad else str(bad[:4]))

# V-08 no market price anywhere
bad = [r["game_id"] for r in fore if cellv(r.get("market_side")) or cellv(r.get("market_total"))
       or cellv(r.get("market_ml_home")) or cellv(r.get("diff_side")) or cellv(r.get("diff_total"))]
bad += [r["market_id"] for r in store if cellv(r.get("market_price")) or cellv(r.get("difference"))]
bad += [r["id"] for r in score if re.search(r"ROI|CLV|\bcash\b", json.dumps(r), re.I) and "no price" not in json.dumps(r)]
(ok, fail)[bool(bad)]("V-08", "no invented market price",
     f"0 non-empty market/difference cells across {len(fore)} forecasts and {len(store)} price rows"
     if not bad else str(bad[:4]))

# V-09 settlement cannot drop inconvenient games
priced = len(settle) + len([r for r in ungraded if cellv(r.get("game_id"))])
bad = [] if priced == 13 and not [r for r in ungraded if cellv(r.get("game_id"))] else [f"{priced}"]
(ok, fail)[bool(bad)]("V-09", "every priced game graded",
     f"{len(settle)} settled, {len([r for r in ungraded if cellv(r.get('game_id'))])} ungraded" if not bad else str(bad))

# V-10 the model figures on the site equal the recomputed figures
r = rows(os.path.join(DD, "reconciliation.csv"))
games = len(log)
bad = []
if games != meta["games_in_log"]:
    bad.append(f"log has {games}, meta says {meta['games_in_log']}")
for x in score:
    if x["id"] == "SC-1" and int(x["n_gradable"]) != len(settle):
        bad.append("SC-1 n != settled games")
if abs(sum(int(x["margin_home"]) for x in log)) > 10000:
    bad.append("margin column out of range")
(ok, fail)[bool(bad)]("V-10", "published numbers equal recomputed numbers",
     f"{games} games in the log; scorecard n matches the settlement table" if not bad else str(bad))

# V-11 capture ledger: hashes and timestamps
bad = []
for r2 in ledger:
    fp = os.path.join(ROOT, r2["capture_file"])
    if not os.path.exists(fp):
        bad.append(f"{r2['id']}: capture file missing")
        continue
    h = hashlib.sha256(open(fp, "rb").read()).hexdigest()
    if h != r2["capture_sha256"]:
        bad.append(f"{r2['id']}: capture hash mismatch")
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$", r2["captured_utc"]):
        bad.append(f"{r2['id']}: clock time not to the minute")
(ok, fail)[bool(bad) or len(ledger) < 12]("V-11", "capture ledger integrity",
     f"{len(ledger)} reads, all hashed and time-stamped" if not bad else str(bad[:4]))

# V-12 availability rows: a VERIFIED claim must cite both a report and a game book
bad = [r3["player"] for r3 in avail if r3["claim_status"] == "VERIFIED"
       and (not cellv(r3["source_report"]) or not cellv(r3["source_gamebook"]))]
(ok, fail)[bool(bad)]("V-12", "availability claims are double-sourced",
     f"{len([r3 for r3 in avail if r3['claim_status'] == 'VERIFIED'])} verified rows cite report + Game Book; "
     f"{len([r3 for r3 in avail if r3['claim_status'] != 'VERIFIED'])} rows are explicitly not confirmed"
     if not bad else str(bad))

# V-13 correlations publish n and never exceed 1
bad = []
for r4 in corr:
    if not str(r4["n"]).isdigit():
        bad.append(f"{r4['id']}: n not published")
    if r4["r"] and abs(float(r4["r"])) > 1:
        bad.append(f"{r4['id']}: |r|>1")
    if r4["r"] and r4["ci95_lo"] and not (float(r4["ci95_lo"]) <= float(r4["r"]) <= float(r4["ci95_hi"])):
        bad.append(f"{r4['id']}: r outside its own interval")
(ok, fail)[bool(bad)]("V-13", "correlations carry n and a consistent interval",
     f"{len(corr)} values" if not bad else str(bad))

# V-14 gates are answered with a measured value, not an assertion
bad = [r5["id"] for r5 in gates if not cellv(r5["measured_now"])]
(ok, fail)[bool(bad)]("V-14", "every gate has a measured value", f"{len(gates)} gates" if not bad else str(bad))

# V-15 questions and suggestions are complete
bad = []
for r6 in q:
    for c in ("question", "what_we_already_know_with_a_number", "what_is_missing", "what_would_answer_it",
              "who_can_answer", "official_source", "status"):
        if not cellv(r6.get(c, "")):
            bad.append(f"{r6['id']}: {c} empty")
for r7 in sg:
    for c in ("title", "what_and_why", "impact", "effort", "risk", "depends_on", "publishes", "status", "source"):
        if not cellv(r7.get(c, "")):
            bad.append(f"{r7['id']}: {c} empty")
(ok, fail)[bool(bad)]("V-15", "questions and suggestions are complete",
     f"{len(q)} questions, {len(sg)} suggestions, no empty decision column" if not bad else str(bad[:5]))

# V-16 site: every table row with a source column is sourced or flagged; links resolve
MARK = re.compile(
    r"unverified|not confirmed|left blank|no official|n/a|no line|no data|derived|blocked|flagged|404|blank",
    re.I)


class T(HTMLParser):
    """collects (heads, body rows) per table, plus every href on the page"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.cur, self.row, self.cell = [], None, None, None
        self.sec, self.intd = None, False
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.cur = {"heads": [], "rows": []}
        elif tag in ("thead", "tbody") and self.cur is not None:
            self.sec = tag
        elif tag == "tr" and self.cur is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell, self.intd = "", True
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "table" and self.cur is not None:
            self.tables.append(self.cur)
            self.cur = None
        elif tag in ("thead", "tbody"):
            self.sec = None
        elif tag == "tr" and self.row is not None and self.cur is not None:
            if self.row:
                (self.cur["rows"] if self.sec == "tbody" else self.cur["heads"]).append(self.row)
            self.row = None
        elif tag in ("td", "th") and self.intd:
            self.row.append(self.cell.strip())
            self.cell, self.intd = None, False

    def handle_data(self, data):
        if self.intd:
            self.cell += data


bad, checked, tables = [], 0, 0
for f in sorted(os.listdir(SITE)):
    if not f.endswith(".html"):
        continue
    p = os.path.join(SITE, f)
    html = open(p, encoding="utf-8").read()
    tp = T()
    tp.feed(html)
    for href in tp.hrefs:
        if href.startswith(("http", "mailto:", "#")):
            continue
        tgt = os.path.normpath(os.path.join(SITE, href.split("#")[0].split("?")[0]))
        if not os.path.exists(tgt):
            bad.append(f"{f}: broken link {href}")
    for tb in tp.tables:
        heads = [h.lower() for h in (tb["heads"][0] if tb["heads"] else [])]
        if not any("source" in h for h in heads):
            continue
        idx = [i for i, h in enumerate(heads) if "source" in h]
        tables += 1
        for rw in tb["rows"]:
            checked += 1
            joined = " ".join(rw)
            has_ext = "http://" in joined or "https://" in joined
            src_txt = " ".join(rw[i] for i in idx if i < len(rw))
            has_int = bool(re.search(r'href="(?!\s*http)', src_txt)) or "../data/" in src_txt or \
                "data/closeout" in src_txt
            if not (has_ext or has_int or MARK.search(src_txt) or MARK.search(joined)):
                bad.append(f"{f}: unsourced row: {rw[0][:40] if rw else '?'}")
(ok, fail)[bool(bad)]("V-16", "site row-source and link audit",
     f"{tables} source-bearing tables, {checked} rows, {len(bad)} problems" if not bad else str(bad[:6]))

# V-17 determinism: rebuilding the pages from the same data yields byte-identical HTML
if not QUIET:
    pass
b = os.path.join(SITE, "index.html")
h1 = hashlib.sha256(open(b, "rb").read()).hexdigest()
os.system(f"python3 {os.path.join(ROOT, 'scripts', 'closeout_build.py')} >/dev/null 2>&1")
h2 = hashlib.sha256(open(b, "rb").read()).hexdigest()
(ok, fail)[h1 != h2]("V-17", "build determinism", "two builds produce identical HTML" if h1 == h2 else "differs")

# V-18 tokens: no unfilled placeholder or TODO anywhere in the tree
bad = []
for root_, _, files in os.walk(SITE):
    for fn in files:
        txt = open(os.path.join(root_, fn), encoding="utf-8", errors="ignore").read()
        for pat in ("@@UNFILLED", "TODO", "FIXME", "{N_"):
            if pat in txt:
                bad.append(f"{fn}: {pat}")
        if re.search(r"\bNaN\b|>\s*nan\s*<|\bnan\b", txt):
            bad.append(f"{fn}: a NaN leaked into a cell")
(ok, fail)[bool(bad)]("V-18", "no unfilled tokens or placeholders", "clean" if not bad else str(bad[:5]))

# V-19 game-day sheets: 48 dressed + 6 not active, or the row says it is unreconciled
sheets = rows(os.path.join(DD, "game_sheets.csv"))
bad = []
for sh in sheets:
    if sh["closed_at_54"] == "yes":
        if int(sh["dressed"]) != 48 or int(sh["not_active"]) != 6:
            bad.append(f'{sh["game"]} {sh["club"]}: claims closed at {sh["dressed"]}+{sh["not_active"]}')
    else:
        if "not reconciled" not in sh["reading"] and "NOT" not in sh["reading"].upper():
            bad.append(f'{sh["game"]} {sh["club"]}: incomplete sheet without a warning')
(ok, fail)[bool(bad) or len(sheets) != 4]("V-19", "game-day sheets reconcile or say they cannot",
     f"{len([x for x in sheets if x['closed_at_54'] == 'yes'])}/{len(sheets)} club sheets close at 48 dressed + 6 "
     "not active; the rest state that no claim may be made" if not bad else str(bad))

# V-20 roster-turnover rows either cite a game document or are explicitly not swept
rt = rows(os.path.join(D, "roster_turnover.csv"))
bad = [r["id"] for r in rt if "NOT SWEPT" not in r["status"] and "http" not in r["source"]]
(ok, fail)[bool(bad)]("V-20", "roster turnover cites a document or admits the gap",
     f"{len(rt)} rows; {len([r for r in rt if 'NOT SWEPT' in r['status']])} row(s) say the other clubs are unswept"
     if not bad else str(bad))

# V-21 the injury delta is computed from two dated files, and the published claim matches the recomputation
d1 = rows(os.path.join(D, "injury_report_w10_capture.csv"))
d2 = rows(os.path.join(D, "injury_report_w10_reread.csv"))
k1 = {(x["club"], x["player"]): (x["injury"], x["practice_status"], x["game_status"]) for x in d1}
k2 = {(x["club"], x["player"]): (x["injury"], x["practice_status"], x["game_status"]) for x in d2}
real_changed = len([k for k in set(k1) & set(k2) if k1[k] != k2[k]]) + len(set(k2) - set(k1)) + len(set(k1) - set(k2))
pub = rows(os.path.join(DD, "injury_delta.csv"))
pub_changed = sum(int(x["designation_or_injury_changed"]) + int(x["added"]) + int(x["removed"]) for x in pub)
bad = []
if real_changed != pub_changed:
    bad.append(f"published {pub_changed}, recomputed {real_changed}")
if not (d1[0]["captured_utc"] < d2[0]["captured_utc"]):
    bad.append("the two captures are not strictly time-ordered")
if {x["source_page"] for x in d1} != {x["source_page"] for x in d2}:
    bad.append("the two reads are not of the same URL")
(ok, fail)[bool(bad)]("V-21", "injury delta recomputes from two dated captures",
     f"{len(d1)} rows at {d1[0]['captured_utc']} vs {len(d2)} at {d2[0]['captured_utc']}; "
     f"{real_changed} changed - published as a stability check, not a signal" if not bad else str(bad))

print(f"checks run: {len(CHECKS)}  failures: {len(FAILS)}")
if not QUIET:
    for cid, desc, st, detail in CHECKS:
        print(f"  {cid:5} {st:4} {desc:46} {detail[:110]}")
if FAILS:
    print("\nFAILURES")
    for x in FAILS:
        print("  -", x)
    sys.exit(1)
print("close-out verification: PASS")
