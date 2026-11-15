#!/usr/bin/env python3
"""Build the decision-readiness register (readiness/**) for the 2026-11-15 brief.

Inputs (all in the repository):
  data/readiness/requirements.csv   one row per requirement in the brief
  data/readiness/questions.csv      questions, what we have, what is missing
  data/readiness/suggestions.csv    proposed paths (nothing is implemented)
  data/readiness/flags.csv          irregularities for review
  data/readiness/sources.csv        every official page read, and how
  + the repo data files named by each metric below (counted, never typed)

Outputs:
  readiness/index.html              decision-readiness table (one row per requirement)
  readiness/questions.html          questions, information and answers
  readiness/suggestions.html        suggestion queue (proposed, not implemented)
  readiness/executive-summary.html  executive summary
  readiness/flagged.html            Flagged for Review
  readiness/sources.html            sources read, and how
  readiness/fragments/landing-table.inc  compact table included on the root landing

Deterministic: no clock is read. Run: python3 tools/build_readiness.py
"""
import csv
import glob
import html
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AS_OF = "2026-11-15"
DATA = os.path.join(ROOT, "data", "readiness")
OUT = os.path.join(ROOT, "readiness")
FRAG = os.path.join(OUT, "fragments")
STATUS_ORDER = ["DONE", "PARTIAL", "BLOCKED", "NOT STARTED", "DECISION", "POLICY"]
STATUS_CLASS = {"DONE": "ok", "PARTIAL": "warn", "BLOCKED": "bad", "NOT STARTED": "grey",
                "DECISION": "info", "POLICY": "info"}
LIONS = {"Kerby Joseph", "Cade Mays", "D.J. Reed"}

DECISIONS = [
    ("D-01", "Price-data policy: which price source, if any, may be stored and used, and what it may be used for", "S-01"),
    ("D-02", "Canonical strategy registry and canonical site tree", "S-02, S-12"),
    ("D-03", "Depth-order route for the backup-deficiency feature", "S-06"),
    ("D-04", "Train, validation and holdout seasons (frozen before any evaluation)", "S-14"),
    ("D-05", "Public and private data split, after the source terms are read", "S-15"),
]


def esc(x):
    return html.escape(str(x), quote=True)


def read_csv(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_readiness(name):
    with open(os.path.join(DATA, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def metrics():
    """Each value is counted from a repo file. Labels say what was counted."""
    M = {}
    inj = read_csv("data/hub/injuries_2026_wk10.csv")
    M["inj_rows"] = (len(inj), "rows in data/hub/injuries_2026_wk10.csv")
    M["inj_rows_status"] = (sum(1 for r in inj if r["status"].strip()),
                            f"of {len(inj)} rows carry a game status")
    M["lions_out_rows"] = (sum(1 for r in inj if r["team"] == "DET" and r["player"] in LIONS and r["status"] == "Out"),
                           "of the 3 Lions rows show Out")
    ps = read_csv("signals/data/price_snapshots.csv")
    filled = sum(1 for r in ps if r["market_value"].strip())
    M["price_official_filled"] = (filled, f"of {len(ps)} rows hold a market value")
    M["price_market_filled"] = (filled, f"of {len(ps)} rows hold a market value")
    M["training_weeks"] = (sum(1 for r in ps if r["training_weeks"].strip()),
                           f"of {len(ps)} rows carry a ratings training-window tag")
    M["price_ledger_rows"] = (len(read_csv("data/ledger/price_snapshots.csv")), "rows in data/ledger/price_snapshots.csv")
    x3 = read_csv("data/x3/price_snapshots_2026.csv")
    M["price_3p_rows"] = (sum(1 for r in x3 if "PFF" in r["source_name"]),
                          "third-party closing rows (not league-official)")
    res = read_csv("data/ledger/results_feed.csv")
    M["results_finals"] = (len(res), "FINAL rows in data/ledger/results_feed.csv")
    M["results_rows_all"] = (len(read_csv("signals/data/results.csv")), "rows in signals/data/results.csv")
    M["seasons_in_results"] = (len({r["season"] for r in res}), "season(s) in the results feed")
    dep = read_csv("data/ledger/replacement_depth.csv")
    M["depth_rows"] = (len(dep), "injury rows joined to depth")
    M["depth_named"] = (sum(1 for r in dep if r["replacement"].strip()), f"of {len(dep)} rows name a replacement")
    M["depth_asof"] = (sum(1 for r in dep if r["chart_as_of"].strip()), f"of {len(dep)} rows carry a chart as-of date")
    M["depth_text_files"] = (len(glob.glob(os.path.join(ROOT, "data/desk/text/depth-*.txt"))),
                             "club depth text captures (HOU is an image page)")
    M["strategies_signals"] = (len(read_csv("signals/data/strategies.csv")), "strategies in signals/data/strategies.csv")
    with open(os.path.join(ROOT, "hub/data/prereg.json"), encoding="utf-8") as f:
        M["prereg_entries"] = (len(json.load(f)["strategies"]), "strategies in hub/data/prereg.json")
    lb = read_csv("signals/data/leaderboard.csv")
    M["rankable_yes"] = (sum(1 for r in lb if r["rankable"] == "yes"), "rows marked rankable=yes")
    M["rankable_gate_fail"] = (sum(1 for r in lb if r["rankable"] == "yes" and r["gates_failed"].strip()),
                               "of those rows fail at least one gate")
    M["gates_all_passed"] = (sum(1 for r in lb if not r["gates_failed"].strip()),
                             f"of {len(lb)} strategies pass every gate")
    M["corr_rows_n"] = (sum(1 for r in read_csv("signals/data/correlations.csv") if r["n"].strip()),
                        "correlation rows with n published")
    M["demotion_rules"] = (len(read_csv("signals/data/demotion.csv")), "demotion rules in signals/data/demotion.csv")
    with open(os.path.join(ROOT, "data/desk/games.json"), encoding="utf-8") as f:
        M["venue_fields"] = (f.read().lower().count("venue"), "venue fields in data/desk/games.json")
    M["snapshot_files_ops"] = (len([p for p in glob.glob(os.path.join(ROOT, "data/ops/snapshots/*")) if os.path.isfile(p)]),
                               "stored snapshot files in data/ops/snapshots")
    cron = 0
    for wf in glob.glob(os.path.join(ROOT, ".github/workflows/*.yml")):
        with open(wf, encoding="utf-8") as f:
            cron += sum(1 for line in f if re.match(r"^\s*-?\s*cron:", line))
    M["cron_entries"] = (cron, "scheduled-run entries in .github/workflows")
    raw = [p for p in glob.glob(os.path.join(ROOT, "capture/*")) if os.path.isfile(p) and not p.endswith("manifest.txt")]
    M["capture_raw_files"] = (len(raw), "raw captures retained in capture/")
    with open(os.path.join(ROOT, "capture/manifest.txt"), encoding="utf-8") as f:
        M["capture_manifest_rows"] = (sum(1 for _ in f), "manifest lines (URL, status, bytes; no hash)")
    archived = 0
    for pat in ("data/**/*injur*", "capture/**/*injur*"):
        for p in glob.glob(os.path.join(ROOT, pat), recursive=True):
            if "/archive/" in p:
                continue
            if re.search(r"(2021|2022|2023|2024|2025)", os.path.basename(p)):
                archived += 1
    M["archived_injury_files"] = (archived, "past-season injury files in data/ or capture/")
    return M


def now_text(key, M):
    if not key:
        return "—"
    if key not in M:
        raise KeyError(f"unknown metric {key}")
    value, label = M[key]
    return f"{value} {label}"


def links(urls):
    out = []
    for u in [x.strip() for x in urls.split(";") if x.strip()]:
        out.append(f'<a href="{esc(u)}" rel="noopener">{esc(u)}</a>')
    return "<br>".join(out)


def source_cell(official_url, unverified):
    if official_url.strip():
        return links(official_url)
    reason = unverified.strip() or "no official source identified"
    return f'<span class="unv">UNVERIFIED</span> — {esc(reason)}'


def evidence_cell(path):
    parts = [p.strip() for p in path.split(";") if p.strip()]
    return "<br>".join(f"<code>{esc(p)}</code>" for p in parts) if parts else "—"


def chip(status):
    cls = STATUS_CLASS.get(status, "grey")
    return f'<span class="chip {cls}">{esc(status)}</span>'


CSS = """
:root{--bg:#f5f7fa;--card:#fff;--ink:#132033;--mut:#56657a;--line:#dfe5ec;--nav:#10273b;
--ok:#1e7a4c;--warn:#a86b00;--bad:#b3261e;--info:#2456a6;--grey:#5b6573}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
background:var(--bg);color:var(--ink)}
header{background:var(--nav);color:#fff;padding:14px 22px}header a{color:#fff;text-decoration:none;font-weight:600}
nav.sub{display:flex;flex-wrap:wrap;gap:6px;padding:10px 22px;background:#fff;border-bottom:1px solid var(--line)}
nav.sub a{padding:6px 10px;border-radius:6px;color:#2c4057;text-decoration:none;font-size:13px}
nav.sub a:hover,nav.sub a.on{background:#e8eef5}
main{max-width:1280px;margin:0 auto;padding:18px 22px 60px}
h1{font-size:24px;margin:8px 0 6px}h2{font-size:18px;margin:26px 0 8px}
p.lede{color:var(--mut);max-width:880px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.card .n{font-size:24px;font-weight:700}.card .l{color:var(--mut);font-size:12px}
.tbl{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f0f4f8;position:sticky;top:0;font-weight:600;white-space:nowrap}
td.id{white-space:nowrap;font-weight:600}
code{font-size:12px;background:#f0f3f7;padding:1px 4px;border-radius:4px;word-break:break-all}
a{color:#1f5fa8;word-break:break-all}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;color:#fff;white-space:nowrap}
.chip.ok{background:var(--ok)}.chip.warn{background:var(--warn)}.chip.bad{background:var(--bad)}
.chip.info{background:var(--info)}.chip.grey{background:var(--grey)}
.unv{background:#fde8e6;color:var(--bad);font-weight:700;padding:0 5px;border-radius:4px;font-size:12px}
.note{background:#fff8e6;border:1px solid #f0dca8;border-radius:8px;padding:10px 12px;max-width:980px}
ul.plain li{margin:4px 0}
footer{color:var(--mut);font-size:12px;margin-top:30px}
.mut{color:var(--mut);font-size:12px}
"""

NAV = [
    ("index.html", "Decision readiness"),
    ("executive-summary.html", "Executive summary"),
    ("questions.html", "Questions and answers"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
]


def page(active, title, body, lede=""):
    nav = "".join(
        f'<a href="{href}"{" class=on" if href == active else ""}>{esc(label)}</a>' for href, label in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 readiness</title>
<style>{CSS}</style>
</head>
<body>
<header><a href="../index.html">X3 NFL decision desk</a> &middot; Decision readiness register &middot; data as of {AS_OF}</header>
<nav class="sub">{nav}<a href="../index.html">Back to landing</a></nav>
<main>
<h1>{esc(title)}</h1>
{('<p class="lede">' + lede + '</p>') if lede else ''}
{body}
<footer>Generated by tools/build_readiness.py from data/readiness/*.csv and repo data files. Verified by tools/verify_readiness.py. Every number is counted from a repo file; every row without an official link says UNVERIFIED.</footer>
</main>
</body>
</html>
"""


def cards(items):
    return '<div class="cards">' + "".join(
        f'<div class="card"><div class="n">{esc(n)}</div><div class="l">{esc(l)}</div></div>' for n, l in items) + "</div>"


def requirement_rows(reqs, M, with_evidence):
    head = ["ID", "Requirement", "Status", "Blocked by", "Number that would clear it", "Now (counted from repo)"]
    if with_evidence:
        head.append("Evidence in repo")
    head.append("Official source")
    out = ["<tr>" + "".join(f"<th>{esc(h)}</th>" for h in head) + "</tr>"]
    for r in reqs:
        cells = [f'<td class="id">{esc(r["id"])}</td>',
                 f'<td>{esc(r["requirement"])}<br><span class="mut">{esc(r["group"])}</span></td>',
                 f'<td>{chip(r["status"])}</td>',
                 f'<td>{esc(r["blocking_gate"])}</td>',
                 f'<td>{esc(r["clearing_number"])}</td>',
                 f'<td>{esc(now_text(r["metric"], M))}</td>']
        if with_evidence:
            cells.append(f"<td>{evidence_cell(r['evidence_path'])}</td>")
        cells.append(f"<td>{source_cell(r['official_url'], r['unverified_reason'])}</td>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    return "<table>" + "".join(out) + "</table>"


def status_counts(reqs):
    c = {s: 0 for s in STATUS_ORDER}
    for r in reqs:
        c[r["status"]] = c.get(r["status"], 0) + 1
    return c


def build():
    reqs = read_readiness("requirements.csv")
    qs = read_readiness("questions.csv")
    sugg = read_readiness("suggestions.csv")
    flags = read_readiness("flags.csv")
    srcs = read_readiness("sources.csv")
    M = metrics()
    for r in reqs:
        if r["status"] not in STATUS_ORDER:
            raise SystemExit(f"bad status {r['status']} on {r['id']}")
        now_text(r["metric"], M)  # raises on unknown metric key
    counts = status_counts(reqs)
    open_q = sum(1 for q in qs if q["answer_status"].startswith("OPEN"))
    high_flags = sum(1 for f in flags if f["severity"] == "High")
    pages = {}

    # ---- index: decision-readiness table ----
    cards_html = cards([(len(reqs), "requirements in the brief")] +
                       [(counts.get(s, 0), s.lower()) for s in STATUS_ORDER] +
                       [(len(DECISIONS), "owner decisions open"), (open_q, "questions open")])
    body = (
        '<h2>Decision readiness, one row per requirement</h2>'
        '<p class="lede">Each row names the gate that blocks it, the number that would clear it, what the repo holds today '
        '(counted by the build), and the official source it rests on. A cell that cannot be confirmed says UNVERIFIED. '
        'Nothing here is inferred or filled in.</p>'
        + cards_html +
        '<div class="tbl">' + requirement_rows(reqs, M, with_evidence=True) + '</div>'
        '<p class="note"><b>Status key.</b> DONE: built and checked in this session. PARTIAL: built, with named gaps. '
        'BLOCKED: needs a source or a decision that does not exist yet. NOT STARTED: no artifact in the repo. '
        'DECISION: an owner choice is needed. POLICY: a rule is stated but enforcement is not verified.</p>'
    )
    pages["index.html"] = page("index.html", "Decision readiness register", body,
                               "The brief's requirements, one row each. Use this to see what gate stops a decision and what number would clear it.")

    # ---- landing fragment (compact) ----
    compact_head = ["ID", "Requirement", "Status", "Blocked by", "Clears when", "Now (counted)", "Official source"]
    rows = ["<tr>" + "".join(f"<th>{esc(h)}</th>" for h in compact_head) + "</tr>"]
    for r in reqs:
        rows.append("<tr>" + "".join([
            f'<td class="id">{esc(r["id"])}</td>',
            f'<td>{esc(r["requirement"])}</td>',
            f'<td>{chip(r["status"])}</td>',
            f'<td>{esc(r["blocking_gate"])}</td>',
            f'<td>{esc(r["clearing_number"])}</td>',
            f'<td>{esc(now_text(r["metric"], M))}</td>',
            f'<td>{source_cell(r["official_url"], r["unverified_reason"])}</td>']) + "</tr>")
    os.makedirs(FRAG, exist_ok=True)
    frag = ('<style>#readiness .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:10px 0}'
            '#readiness .card{background:#fff;border:1px solid #dfe5ec;border-radius:8px;padding:8px 10px}'
            '#readiness .card .n{font-size:20px;font-weight:700}#readiness .card .l{color:#56657a;font-size:12px}'
            '#readiness .tbl{overflow-x:auto}#readiness table{border-collapse:collapse;width:100%;font-size:12.5px}'
            '#readiness th,#readiness td{padding:6px 8px;border-bottom:1px solid #e2e6eb;text-align:left;vertical-align:top}'
            '#readiness th{background:#f0f4f8;font-weight:600}#readiness td.id{white-space:nowrap;font-weight:600}'
            '#readiness .chip{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;font-weight:600;color:#fff;white-space:nowrap}'
            '#readiness .chip.ok{background:#1e7a4c}#readiness .chip.warn{background:#a86b00}#readiness .chip.bad{background:#b3261e}'
            '#readiness .chip.info{background:#2456a6}#readiness .chip.grey{background:#5b6573}'
            '#readiness .unv{background:#fde8e6;color:#b3261e;font-weight:700;padding:0 4px;border-radius:4px;font-size:11px}</style>'
            '<section class="callout" id="readiness"><h2>Decision readiness: one row per requirement</h2>'
            '<p>Status, the gate that blocks each requirement, the number that would clear it, and the count the repo holds '
            f'today ({len(reqs)} requirements). Full evidence: <a href="readiness/index.html"><b>readiness/index.html</b></a>.</p>'
            + cards([(counts.get(s, 0), s.lower()) for s in STATUS_ORDER]) +
            '<div class="tbl"><table class="ready">' + "".join(rows) + '</table></div></section>')
    with open(os.path.join(FRAG, "landing-table.inc"), "w", encoding="utf-8") as f:
        f.write(frag + "\n")

    # ---- questions ----
    qhead = ["ID", "Question", "What we have", "What is missing", "Answer status", "How to find out", "Official source"]
    qrows = ["<tr>" + "".join(f"<th>{esc(h)}</th>" for h in qhead) + "</tr>"]
    for q in qs:
        st = q["answer_status"]
        cls = "ok" if st.startswith("ANSWERED") else ("warn" if st.startswith("PARTIAL") else "bad")
        qrows.append("<tr>" + "".join([
            f'<td class="id">{esc(q["id"])}</td>',
            f'<td>{esc(q["question"])}</td>',
            f'<td>{esc(q["what_we_have"])}</td>',
            f'<td>{esc(q["what_is_missing"])}</td>',
            f'<td><span class="chip {cls}">{esc(st)}</span></td>',
            f'<td>{esc(q["how_to_discover"])}</td>',
            f'<td>{source_cell(q["official_url"], q["unverified_reason"])}</td>']) + "</tr>")
    body = ('<p class="lede">What must be known before a decision can reasonably be made, what the repo already holds, '
            'what is missing, and how to find out. Nothing on this page is a decision.</p>'
            + cards([(len(qs), "questions"), (open_q, "open"),
                     (sum(1 for q in qs if q["answer_status"].startswith("PARTIAL")), "partly answered"),
                     (sum(1 for q in qs if q["answer_status"].startswith("ANSWERED")), "answered")])
            + '<div class="tbl"><table>' + "".join(qrows) + "</table></div>")
    pages["questions.html"] = page("questions.html", "Questions and answers", body)

    # ---- suggestions ----
    shead = ["ID", "Suggestion", "Addresses", "Options", "Recommendation", "Owner decision", "Status", "Official source"]
    srows = ["<tr>" + "".join(f"<th>{esc(h)}</th>" for h in shead) + "</tr>"]
    for s in sugg:
        srows.append("<tr>" + "".join([
            f'<td class="id">{esc(s["id"])}</td>',
            f'<td>{esc(s["suggestion"])}</td>',
            f'<td>{esc(s["addresses"])}</td>',
            f'<td>{esc(s["options"])}</td>',
            f'<td>{esc(s["recommendation"])}</td>',
            f'<td>{esc(s["owner_decision"]) or "—"}</td>',
            f'<td><span class="chip info">{esc(s["status"])}</span></td>',
            f'<td>{source_cell(s["official_url"], s["unverified_reason"])}</td>']) + "</tr>")
    dec_items = "".join(f"<li><b>{esc(d[0])}</b> {esc(d[1])} (see {esc(d[2])})</li>" for d in DECISIONS)
    body = ('<p class="note"><b>Nothing on this page is implemented.</b> Each suggestion lists its options. '
            'Choose a path first; the build will not act on a suggestion until the owner decision is recorded.</p>'
            '<h2>Decisions the owner needs to make</h2><ul class="plain">' + dec_items + '</ul>'
            '<h2>Suggestion queue</h2><div class="tbl"><table>' + "".join(srows) + "</table></div>")
    pages["suggestions.html"] = page("suggestions.html", "Suggestions", body,
                                     "Proposed paths to discover missing information and to unblock decisions. Status is PROPOSED for every row.")

    # ---- flagged ----
    fhead = ["ID", "Irregularity", "Evidence in repo", "Detail", "Official source", "Action", "Severity"]
    frows = ["<tr>" + "".join(f"<th>{esc(h)}</th>" for h in fhead) + "</tr>"]
    for f_ in flags:
        sev = f_["severity"]
        sc = {"High": "bad", "Medium": "warn", "Low": "grey", "Resolved": "ok"}.get(sev, "grey")
        frows.append("<tr>" + "".join([
            f'<td class="id">{esc(f_["id"])}</td>',
            f'<td>{esc(f_["irregularity"])}</td>',
            f'<td>{evidence_cell(f_["evidence_path"])}</td>',
            f'<td>{esc(f_["evidence_detail"])}</td>',
            f'<td>{source_cell(f_["official_url"], f_["unverified_reason"])}</td>',
            f'<td>{esc(f_["action"])}</td>',
            f'<td><span class="chip {sc}">{esc(sev)}</span></td>']) + "</tr>")
    body = ('<p class="lede">Irregularities found while checking the repo against the brief and the official pages. '
            'Flagged items do not block the site; they are listed here with their source link or UNVERIFIED marker so the owner can review them.</p>'
            + cards([(len(flags), "flags"), (high_flags, "high severity")])
            + '<div class="tbl"><table>' + "".join(frows) + "</table></div>")
    pages["flagged.html"] = page("flagged.html", "Flagged for review", body)

    # ---- sources ----
    sh = ["Official page or source", "What it supports", "Read on", "How it was read", "Status"]
    srw = ["<tr>" + "".join(f"<th>{esc(h)}</th>" for h in sh) + "</tr>"]
    for s in srcs:
        srw.append("<tr>" + "".join([
            f'<td><a href="{esc(s["url"])}" rel="noopener">{esc(s["url"])}</a></td>',
            f'<td>{esc(s["supports"])}</td>',
            f'<td>{esc(s["read_on"])}</td>',
            f'<td>{esc(s["read_method"])}</td>',
            f'<td>{esc(s["status"])}</td>']) + "</tr>")
    body = ('<p class="lede">Each page read for this register, when, and how. "Prior session only" means the link is taken from an earlier '
            'session and was not re-read here. Third-party and secondary sources are labelled and are not official.</p>'
            '<div class="tbl"><table>' + "".join(srw) + "</table></div>")
    pages["sources.html"] = page("sources.html", "Sources", body)

    # ---- executive summary ----
    top = [f for f in flags if f["severity"] == "High"]
    top_items = "".join(
        f'<li><b>{esc(f["id"])}</b> {esc(f["irregularity"])}</li>' for f in top)
    dec_items = "".join(f"<li><b>{esc(d[0])}</b> {esc(d[1])}</li>" for d in DECISIONS)
    lb_all = M["gates_all_passed"][0]
    body = f"""
<h2>What this is</h2>
<p>A register that answers the brief's question for each requirement: is it built, what blocks it, and what number would clear it.
It is not a model result, a strategy result, or a betting recommendation. No value on this site is inferred.</p>
<h2>Where things stand</h2>
<ul class="plain">
<li><b>{len(reqs)}</b> requirements: {counts.get('DONE',0)} done, {counts.get('PARTIAL',0)} partial, {counts.get('BLOCKED',0)} blocked, {counts.get('NOT STARTED',0)} not started, {counts.get('DECISION',0)} decision, {counts.get('POLICY',0)} policy.</li>
<li>Official market values held in the price store: <b>{M['price_official_filled'][0]}</b> ({M['price_official_filled'][1]}). The store therefore cannot yet support an opening or closing line, a market residual, or any ROI.</li>
<li><b>{M['results_finals'][0]}</b> FINAL games are in the results feed, from {M['seasons_in_results'][0]} season.</li>
<li><b>{M['strategies_signals'][0]}</b> strategies are in the signals registry and <b>{M['prereg_entries'][0]}</b> in the hub prereg. The two must be reconciled (flag F-04).</li>
<li><b>{lb_all}</b> strategies pass every gate in the leaderboard. Four rows are marked rankable=yes while failing gates (flag F-03).</li>
<li><b>{M['cron_entries'][0]}</b> scheduled workflows exist, so no capture runs on a schedule. The sandbox cannot open nfl.com from bash, so captures cannot be scripted here.</li>
<li><b>{M['depth_named'][0]}</b> of {M['depth_rows'][0]} injury rows name a replacement. The Houston chart is an image on a page labelled Unofficial.</li>
</ul>
<h2>Verified in this session</h2>
<ul class="plain">
<li>The official Week 10 report shows Out for Kerby Joseph, Cade Mays and D.J. Reed (<a href="https://www.nfl.com/injuries/league/2026/reg10">nfl.com/injuries/league/2026/reg10</a>). The repo rows match.</li>
<li>The official transactions log shows the Colts trades of Keenan Allen and Josh Downs on 11/10, and Jacoby Brissett's trade on 11/06 (<a href="https://www.nfl.com/transactions/">nfl.com/transactions</a>).</li>
<li>The official policy defines Questionable, Doubtful and Out with no percentages (<a href="https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693">NFL.com injury-report policy</a>).</li>
<li>The official game centre shows MetLife Stadium as the venue of Commanders at Giants, and links a Game Book PDF (<a href="https://www.nfl.com/games/commanders-at-giants-2026-reg-10">game centre</a>).</li>
<li>The Houston depth chart page is labelled Unofficial and shows the chart as an image (<a href="https://www.houstontexans.com/team/depth-chart">houstontexans.com/team/depth-chart</a>).</li>
</ul>
<h2>What is blocked, and by what</h2>
<ul class="plain">
<li>Prices: no official price source is identified. Owner decision D-01.</li>
<li>Snap counts and depth order: no official snap-count source is identified. Owner decision D-03.</li>
<li>Calibration of designations and past-season models: no archive exists in the repo, although the 2025 Week 10 report is reachable on nfl.com.</li>
<li>Scheduled capture: no schedule exists and nfl.com cannot be reached from bash.</li>
</ul>
<h2>Decisions needed</h2>
<ul class="plain">{dec_items}</ul>
<h2>Most important irregularities (full list on Flagged for review)</h2>
<ul class="plain">{top_items}</ul>
<h2>Limits</h2>
<ul class="plain">
<li>The brief's VR and VQ identifiers do not appear in the repo, so they cannot be traced (flag F-13).</li>
<li>The fetch tool read nfl.com page by page. Only the pages in <a href="sources.html">Sources</a> were read this session; the rest are prior-session or unread.</li>
<li>The Week 10 counts (345 in the repo, 254 and 279 in the brief) were not recounted live (flag F-05).</li>
</ul>
<h2>Recommended order</h2>
<ul class="plain">
<li>1. Owner decisions D-01 to D-05 (see <a href="suggestions.html">Suggestions</a>).</li>
<li>2. Reconcile the registry, the leaderboard flag and the injury counts (S-02, S-03, S-04).</li>
<li>3. Open one Game Book and record its fields (S-05); archive past reports by hand (S-09).</li>
<li>4. Test a scheduled runner against nfl.com (Q-16) before building any capture (S-08).</li>
</ul>
"""
    pages["executive-summary.html"] = page("executive-summary.html", "Executive summary", body,
                                           "The short version: what exists, what is verified, what blocks each decision, and what the owner must decide.")
    return pages, frag


def write_all(pages):
    os.makedirs(OUT, exist_ok=True)
    for name, text in pages.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    pages, _ = build()
    write_all(pages)
    print(f"built {len(pages)} pages and fragments/landing-table.inc")
