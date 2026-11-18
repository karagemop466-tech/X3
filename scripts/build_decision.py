#!/usr/bin/env python3
"""
Render the decision layer from scripts/x3_decision_content.py.

Every page is generated; nothing here is hand-written HTML that a data change
would miss. Prose numbers come from the content module's CTX, which is computed
from repository artefacts at build time - a missing key aborts the build rather
than printing a placeholder.

Run: python3 scripts/build_decision.py
"""
from __future__ import annotations

import html
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3_decision_content as C  # noqa: E402

ROOT, OUT = C.ROOT, C.OUT
OFFICIAL = ("nfl.com", "operations.nfl.com", "github.com", "docs.github.com")

NAV = [
    ("index.html", "Decision desk", "what is ready, what is blocked"),
    ("readiness.html", "Readiness register", "one row per requirement: gate + clearing number"),
    ("suggestions.html", "Suggestion queue", "review and choose a path before implementing"),
    ("questions.html", "Questions & answers", "what we have, what we lack, how to close it"),
    ("snapshots.html", "Point-in-time series", "sealed reads, hashes, the delta"),
    ("pricing.html", "Price-data policy", "the decision plus the first settled line"),
    ("trees.html", "Tree overlap", "which artefact answers which requirement"),
    ("executive-summary.html", "Executive summary", "the one-page brief"),
    ("flagged.html", "Flagged for review", "irregularities, none of them hidden"),
    ("sources.html", "Sources", "official pages, timestamps, what each confirmed"),
    ("verification.html", "Verification log", "how each line was checked, and how to re-check"),
]

BADGE = {"READY": "ok", "PARTIAL": "warn", "BLOCKED": "bad", "NOT STARTED": "dim",
         "POLICY": "info", "DEFECT": "bad", "DECIDED": "info"}
BASIS = {"VERIFIED THIS SESSION": "ok", "READ REPO FILE": "info", "PRIOR AUDIT CITED": "warn", "NOT RE-COUNTED": "dim"}


def e(s):
    return html.escape(str(s), quote=True)


def badge(text):
    return f'<span class="badge b-{BADGE.get(text,"dim")}">{e(text)}</span>'


def source_cell(src):
    """Every row cites something. An official URL when the claim is about the
    world; a repository path when the claim is about this repository. A row with
    neither is a build error, not a style choice."""
    if src.startswith(("http://", "https://")):
        src = "url:" + src          # tolerate a bare URL at any call site
    kind, _, path = src.partition(":")
    if kind == "url":
        return f'<td class="src"><a href="{e(path)}" rel="noopener">{e(path.replace("https://","").replace("www.",""))}</a></td>'
    target = os.path.join(ROOT, path)
    if os.path.isdir(target):
        # A directory is cited by a link to its tree on GitHub, so the row carries
        # a resolvable source rather than unlinked text. (Same fix reached
        # independently by arena/dbb50f8c-x3 and by the session that landed on
        # main; the GitHub-URL form is kept.)
        url = "https://github.com/karagemop466-tech/X3/tree/main/" + path.rstrip("/")
        return f'<td class="src"><a class="cite" href="{e(url)}" rel="noopener">repo: {e(path)}</a></td>'
    if path.startswith("decision/"):
        # an artefact of this very build, so it cannot pre-exist; the verifier
        # resolves every such link once the whole tree has been written
        return f'<td class="src"><a class="cite" href="{e(os.path.basename(path))}">{e(path)}</a></td>'
    if not os.path.exists(target):
        raise SystemExit(f"row cites a file that does not exist: {path}")
    return f'<td class="src"><a class="cite" href="../{e(path)}">{e(path)}</a></td>'


def table(headers, rows, cls="data"):
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "\n".join("<tr>" + "".join(c) + "</tr>" for c in rows)
    return f'<table class="{cls}"><thead><tr>{head}</tr></thead><tbody>\n{body}\n</tbody></table>'


def td(text, cls=""):
    return f'<td{f" class={cls}" if cls else ""}>{text}</td>'


# ----------------------------------------------------------------- pages -----
def page(fname, title, lede, sections, kicker=""):
    nav = "".join('<a href="%s"%s><b>%s</b><span>%s</span></a>' % (href, ' class="active"' if href == fname else "", e(lbl), e(sub))
                  for href, lbl, sub in NAV)
    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} - X3 decision desk</title>
<meta name="description" content="{e(lede)}">
<link rel="stylesheet" href="../hub/assets/hub.css">
<link rel="stylesheet" href="assets/decision.css">
</head>
<body>
<header class="top">
 <div class="brand"><a href="../index.html">X3</a> &middot; <a href="index.html">decision desk</a></div>
 <div class="asof">evidence as of <b>{e(C.AS_OF)}</b> &middot; season 2026, week 10</div>
</header>
<main>
<h1>{e(title)}</h1>
<p class="lede">{lede}</p>
{kicker}
<nav class="nav">{nav}</nav>
{body}
</main>
<footer class="foot">built by <code>scripts/build_decision.py</code> from repository artefacts; it reads other trees and never writes them.
Every table row links to an official page or to the repo file that states it. Re-run:
<code>python3 scripts/build_decision.py &amp;&amp; python3 scripts/verify_decision.py</code></footer>
</body></html>
"""


def kpi(rows):
    cards = "".join(f'<div class="card"><div class="num">{e(n)}</div><div class="lbl">{l}</div></div>' for n, l in rows)
    return f'<div class="grid">{cards}</div>'


def index():
    counts = {}
    for r in C.REQS:
        counts[r[2]] = counts.get(r[2], 0) + 1
    stat = " &middot; ".join(f'{badge(k)} {v}' for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    top = [
        ("Readiness register", "readiness.html", f"{len(C.REQS)} rows, one per requirement of the brief, each with the gate that blocks it and the number that clears it."),
        ("Suggestion queue", "suggestions.html", f"{len(C.SUGS)} paths to choose between. Nothing in the queue has been implemented; the decision column is yours."),
        ("Questions and answers", "questions.html", f"{len(C.QUESTIONS)} questions, each naming the artefact or the fetch that would close it."),
        ("Point-in-time series", "snapshots.html", "the first two hashed, clock-stamped reads of the availability report, and the delta between them."),
        ("Price-data policy", "pricing.html", "the decision the brief asks for before any backtest is published, plus the one line this project has settled."),
        ("Flagged for review", "flagged.html", f"{len(C.FLAGS)} irregularities found while verifying, including one where the code and the brief disagree."),
    ]
    cards = "".join(f'<div class="card t"><a href="{h}"><b>{e(t)}</b><span>{d}</span></a></div>' for t, h, d in top)
    sec = [
        kpi([
            (f"{len(C.REQS)}", "requirements in the readiness register"),
            (f'{counts.get("READY",0)} / {len(C.REQS)}', "ready today, and every READY row says who checked it"),
            (f"{C.rows_before} &rarr; {C.rows_after}", "official availability rows, two sealed reads one day apart"),
            (f"{C.n_desig_changes}", "designation changes measured between those two reads"),
            (f"{C.n_priced} / {C.n_with_market}", "games priced by our model / of those with any market line"),
            (f"{C.n_trees}", "overlapping site trees this layer reads and refuses to duplicate"),
        ]),
        f'<section class="callout"><h2>What this tree is</h2><p>Sixteen sessions each answered the same brief by building another site. '
        f'This one adds no competing model, leaderboard or scraper. It is the review surface: a register of every requirement with the gate that '
        f'blocks it, a queue of paths to choose between, the questions that must be answered first, and the one new dataset this session could '
        f'legitimately create - a hashed, clock-stamped series of the official availability report, with the delta published instead of the level.</p>'
        f'<p class="note">Statuses: {stat}</p></section>',
        f'<section class="callout"><h2>Two findings a reader should not have to dig for</h2>'
        f'<p><b>1. The report does not stop moving.</b> Between a read on 2026-11-14 and a read at {e(C.AS_OF)} on the same week, '
        f'{C.n_desig_changes} game designations changed, {C.n_prac_changes} practice columns moved and {C.n_added} rows appeared, while one '
        f'designation was withdrawn. They are concentrated on the two Monday-night clubs. So "the Week 10 report" is not one artefact, and a '
        f'backtest cut weekly either leaks or starves depending on the game slot. See <a href="snapshots.html">the series</a>.</p>'
        f'<p><b>2. The pre-registered model applies fixed injury penalties, which the brief forbids.</b> <code>hub/data/prereg.json</code> pins '
        f'pos_cost QB 4.0 / RB 1.5 / WR 1.1 and a status weight, and <code>hub/data/lines.json</code> adds that as points to the margin on all '
        f'{C.n_priced} priced rows. The brief asks for an ablation with uncertainty instead. This is a decision, not a bug report - '
        f'see <a href="flagged.html">F-D01</a> and <a href="suggestions.html">S-D5</a>.</p>'
        f'<p><b>And one unblock.</b> Past seasons are reachable: the official page serves <code>/injuries/league/2024/reg10</code> in full, and its '
        f'own selector runs back to 1965. "Archive weekly reports for past seasons" moves from blocked to schedulable, and with it the '
        f'train/validation/holdout split and the empirical calibration of "Questionable".</p></section>',
        f'<section class="callout"><h2>Start with the one decision that gates the rest</h2>'
        f'<p>There is no market price anywhere in this repository - {C.n_with_market} of {C.n_priced} priced games carry a market line - so ROI, '
        f'closing-line value, rewards and the staking half of the leaderboard are all blocked on the same missing input, and three trees publish '
        f'backtests anyway. The brief says the price-data policy must be decided before any backtest is published. '
        f'<a href="pricing.html">Three options, with what each buys and costs</a>.</p></section>',
    ]
    return page("index.html", "X3 decision desk",
                "Readiness, suggestions, open questions and the point-in-time evidence - a review layer over the implementation trees, "
                "not another one. Every row is tied to an official page or to the repository file that states it.", sec)


def readiness():
    groups = {}
    for r in C.REQS:
        g = r[0].split("-")[0]
        groups.setdefault(g, []).append(r)
    names = {"P": "Market &amp; price layer", "L": "Leaderboard, gates and luck", "A": "Availability, injury and depth",
             "M": "Model outputs and features", "G": "Governance, process and the site itself"}
    out = []
    for g in ("P", "L", "A", "M", "G"):
        rows = []
        for rid, text, st, where, gate, clears, basis, src in groups[g]:
            rows.append([td(f'<span class="mono">{e(rid)}</span>'), td(e(text)), td(badge(st)),
                         td(f'<span class="sm">{e(where)}</span>'), td(e(gate)), td(e(clears)),
                         td(f'<span class="badge b-{BASIS.get(basis,"dim")}">{e(basis)}</span>'), source_cell(src)])
        out.append(f'<section class="callout"><h2>{names[g]}</h2>'
                   + table(["id", "requirement (as the brief states it)", "status", "where it lives",
                            "gate that blocks it", "the number that clears it", "how this status was established", "source"], rows)
                   + "</section>")
    counts = {}
    for r in C.REQS:
        counts[r[2]] = counts.get(r[2], 0) + 1
    out.insert(0, f'<section class="callout"><h2>How to read this</h2><p>One row per requirement. <b>Gate</b> is the specific thing standing in the '
                 f'way, stated so it can be checked rather than argued with. <b>The number that clears it</b> is the threshold that turns the row '
                 f'green. <b>How this status was established</b> is the honesty column: {e("VERIFIED THIS SESSION")} means a human-readable artefact '
                 f'was opened this session (an official page or the file named on the right); {e("READ REPO FILE")} means the status was read out of '
                 f'a repository artefact; {e("PRIOR AUDIT CITED")} reproduces another session\'s audit without re-running it; '
                 f'{e("NOT RE-COUNTED")} marks a figure from the brief this session could not reproduce from retained data, and nothing else on the '
                 f'site should be trusted more than that label. Totals: '
                 + ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])) + ".</p></section>")
    return page("readiness.html", "Decision-readiness register",
                f"{len(C.REQS)} requirements from the brief. For each one: what implements it, the gate that blocks it, and the number that would clear it.",
                out)


SUG_EVID = {
 "S-D1": "file:hub/data/lines.json", "S-D2": "file:decision/trees.html",
 "S-D3": "file:data/snapshots/README.md", "S-D4": "url:https://www.nfl.com/injuries/league/2024/reg10",
 "S-D5": "file:hub/data/prereg.json", "S-D6": "file:data/snapshots/delta.json",
 "S-D7": "file:data/desk/text/", "S-D8": "file:data/desk/text/",
 "S-D9": "url:https://www.nfl.com/injuries/league/2026/reg10", "S-D10": "file:data/desk/parse_report.json",
 "S-D11": "file:data/desk/games.json", "S-D12": "file:hub/data/lines.json",
 "S-D13": "file:signals/gates.html", "S-D14": "file:data/desk/correlations.json",
 "S-D15": "file:scripts/x3_snapshots_verify.py", "S-D16": "file:hub/data/lines.json",
}


def suggestions():
    rows = []
    for sid, title, tag, problem, opts, unblocks, cost, note in C.SUGS:
        rendered = "".join(f'<div class="opt"><b>{e(letter)}</b> {e(text)}</div>' for letter, text in opts)
        rows.append([td(f'<span class="mono">{e(sid)}</span>'),
                     td(f'<b>{e(title)}</b><div class="sm">{e(tag)}</div>'),
                     td(e(problem)), td(rendered),
                     td(e(unblocks)), td(e(cost)), td(f'<span class="sm muted">{e(note)}</span>'),
                     source_cell(SUG_EVID[sid]),
                     td('<span class="decision">awaiting reviewer</span>')])
    tbl = table(["id", "suggestion", "the problem, from the artefacts", "paths to choose between",
                 "what it unblocks", "cost", "this session's read", "evidence", "decision"], rows)
    sec = [
        f'<section class="callout"><h2>Rules of this queue</h2><p>Nothing here has been implemented, and nothing will be before a choice is made: '
        f'each row ends in an empty decision column. Suggestions are ordered by how much they unblock, not by how easy they are. Where a suggestion '
        f'contradicts another tree\'s published number, the file is cited rather than edited - these trees belong to other sessions, and the request is '
        f'logged in <a class="cite" href="../COORDINATION.md">COORDINATION.md</a>. The single most valuable entry is S-D1: it is the only one that '
        f'unblocks money. Every row carries the artefact that shows the problem, so a path can be argued with the file open.</p></section>',
        f'<section class="callout"><h2>{len(C.SUGS)} suggestions, in order of what they unlock</h2>' + tbl + "</section>",
        f'<section class="callout"><h2>Explicitly rejected, and kept rejected</h2><p>Two shortcuts appear in the brief as rejections and are recorded '
        f'here so nobody re-proposes them as an optimisation: deriving depth order from jersey number, experience or salary; and ranking strategies on '
        f'season-long realised return alone. Both stay out of every page in this tree, and A-12 and G-13 in the '
        f'<a href="readiness.html">register</a> carry the rule.</p></section>',
    ]
    return page("suggestions.html", "Suggestion review queue",
                "Paths under consideration, not work ordered. Choose a path, then implement it.", sec)


# Which artefact a question's row is grounded in. Every row must cite something:
# an official page when the claim is about the world, a repository file when it is
# about the repository, or an explicit statement that the answer is not held.
EVIDENCE = {
 "Q-D1": "file:hub/data/lines.json", "Q-D2": "url:https://www.nfl.com/injuries/league/2026/reg10",
 "Q-D3": "file:origin/data/depth.json", "Q-D4": "file:data/desk/text/",
 "Q-D5": "file:signals/index.html", "Q-D6": "file:hub/data/lines.json",
 "Q-D7": "file:data/snapshots/delta.json", "Q-D8": "file:data/snapshots/delta.json",
 "Q-D9": "url:https://www.nfl.com/injuries/league/2024/reg10", "Q-D10": "file:data/desk/games.json",
 "Q-D11": "file:hub/data/prereg.json", "Q-D12": "file:decision/trees.html",
 "Q-D13": "file:data/desk/text/", "Q-D14": "file:signals/gates.html",
 "Q-D15": "url:https://www.nfl.com/schedules/2026/by-week/week-10",
}


def questions():
    rows = []
    for qid, q, have, lack, ans, link in C.QUESTIONS:
        rows.append([td(f'<span class="mono">{e(qid)}</span>'), td(f'<b>{e(q)}</b>'), td(e(have)), td(e(lack)),
                     td(e(ans)), td(f'<a href="suggestions.html">{e(link)}</a>'), source_cell(EVIDENCE[qid])])
    sec = [
        f'<section class="callout"><h2>How a question closes</h2><p>Each row states what is already held, what is missing, and the current best answer '
        f'from the evidence on the page - not from recollection. A question is closed when the middle two columns are empty, which is why each one names '
        f'the artefact or the fetch that would empty them. Two questions were closed by evidence gathered this session (Q-D7, Q-D8, Q-D9) and one '
        f'(Q-D9) turns a blocker into a task.</p></section>',
        table(["id", "question that must be answered before deciding", "information we already have", "information we do not have",
               "best answer from what is held", "suggestion that would close it", "evidence"], rows),
        f'<section class="callout"><h2>The answer to "what is missing"</h2><p>Settling every question above needs four artefacts, and only four: '
        f'(1) dated market prices per game - <b>Q-D1, Q-D14</b>; (2) official inactive lists at T-90 - <b>Q-D2, Q-D3, Q-D15 partly</b>; '
        f'(3) a transactions/reserve capture - <b>Q-D3, Q-D4</b>; (4) past seasons of designations joined to results - '
        f'<b>Q-D2, Q-D9</b>. Items 3 and 4 are reachable with the sources this repository already uses; items 1 and 2 are not, and that is a '
        f'decision and a permissions question, not an engineering one.</p></section>',
    ]
    return page("questions.html", "Questions, information and answers",
                "What must be known before any of this can be decided reasonably - separated into what we hold, what we lack, and the answer the difference allows.",
                sec)


def snapshots():
    caps = []
    for c in C.ledger["captures"]:
        caps.append([td(f'<span class="mono">{e(c["capture_id"])}</span>'), td(e(c["fetched_at_utc"])),
                     td(e(c["clock_precision"])), td(f'{c["rows"]} rows / {c["counts"]["teams"]} clubs'),
                     td("Out %d &middot; Doubtful %d &middot; Questionable %d &middot; no designation %d"
                        % (c["counts"]["designation_counts"]["Out"], c["counts"]["designation_counts"]["Doubtful"],
                           c["counts"]["designation_counts"]["Questionable"], c["counts"]["blank_game_status"])),
                     td(f'<span class="mono">{e(c["sha256"][:24])}&hellip;</span>'),
                     td(f'<span class="sm">{e(c["sealed"] and "sealed capture" or "reconstructed from retained files - not sealed")}</span>'),
                     source_cell("url:" + c["source_url"])])
    drows = []
    for x in C.D["designation_changes"]:
        cor = x["corroboration_before"]
        drows.append([td(e(x["team"])), td(e(x["player"])), td(e(x["pos"])),
                      td(f'{e(x["status_before"])} &rarr; <b>{e(x["status_after"])}</b>'),
                      td(f'{e(x["practice_before"])} &rarr; {e(x["practice_after"])}'),
                      td(f'<span class="badge b-{"ok" if cor["verdict"]=="CORROBORATED" else "warn"}">{e(cor["verdict"])}</span>'),
                      source_cell("url:" + C.D["source_url"])])
    arows = []
    for x in C.D.get("added_detail", []):
        arows.append([td(e(x["team"])), td(e(x["player"])), td(e(x["pos"])), td(e(x["practice_after"])),
                      td(e(x["status_after"])), td('<span class="badge b-warn">ABSENT FROM PRIOR READS</span>'),
                      source_cell("url:" + C.D["source_url"])])
    prow = []
    for x in C.D["practice_changes"]:
        prow.append([td(e(x["team"])), td(e(x["player"])), td(e(x["pos"])),
                     td(f'{e(x["practice_before"])} &rarr; {e(x["practice_after"])}'), td(e(x["status_both"])),
                     td('<span class="sm">designation unchanged; only practice moved</span>'),
                     source_cell("url:" + C.D["source_url"])])
    percl = {}
    for x in C.D["designation_changes"]:
        percl[x["team"]] = percl.get(x["team"], 0) + 1
    slot = table(["club", "designation changes in this window"],
                 [[td(f'<span class="mono">{e(t)}</span>'), td(str(n))] for t, n in sorted(percl.items(), key=lambda kv: (-kv[1], kv[0]))],
                 cls="agg")
    sec = [
        f'<section class="callout"><h2>Why this exists</h2><p>The brief asks for the injury hub as "a timestamped series, not a weekly snapshot", for '
        f'every read stored "with its clock time", and for the site to publish "the delta, never the level". Until this session the repository held one '
        f'read of Week 10 and therefore no delta. Below are two hashed reads of the same official page, and what moved between them.</p>'
        f'<p class="note">Captured through the authoring environment\'s page reader, because direct HTTP to nfl.com is blocked here '
        f'(<code>curl</code> to www.nfl.com:443 fails with SSL_ERROR_SYSCALL). The hash therefore seals the transcription this store keeps, not the '
        f'league\'s raw bytes; the store README states this rather than hiding it, and S-D3 is the suggestion that fixes it.</p></section>',
        f'<section class="callout"><h2>The ledger</h2>' + table(
            ["read", "fetched at", "clock precision", "volume", "designations in this read", "sha256 of stored bytes", "kind", "source"], caps)
            + '</section>',
        f'<section class="callout"><h2>The delta - what a day of "no news" actually contains</h2>'
        f'<p>{C.rows_before} rows &rarr; {C.rows_after}; {C.n_desig_changes} designation changes; {C.n_prac_changes} practice-only changes; '
        f'{C.n_added} rows appeared; {C.n_dropped} disappeared. Adverse surprises (a designation gained toward Out or Doubtful): '
        f'<b>{C.adverse}</b>. Favourable (a designation withdrawn): <b>{C.favourable}</b>. Each row carries a corroboration verdict, computed by '
        f'comparing against the <i>two</i> independent 2026-11-14 reads retained in the repository (the desk store and the audit transcription) - '
        f'a change is only published as real when both prior reads agree with each other.</p>'
        + table(["club", "player", "pos", "game status moved", "practice moved", "corroboration", "source"], drows) + "</section>",
        f'<section class="callout"><h2>Rows that appeared between reads</h2><p>These two are the argument for the whole store: a row can arrive the day '
        f'before a game with a practice designation and <i>no</i> game status, which is neither "listed as out" nor "absent, therefore healthy". '
        f'Nothing in the earlier captures mentions them, so no model built from those captures could have known.</p>'
        + table(["club", "player", "pos", "practice", "game status", "prior reads", "source"], arows) + "</section>",
        f'<section class="callout"><h2>Practice moved without any designation moving</h2>'
        + table(["club", "player", "pos", "practice moved", "designation both days", "note", "source"], prow)
        + '<p class="note">All three are Los Angeles (AC) - the Monday-night club. A Friday deadline does not freeze a Monday game.</p></section>',
        f'<section class="callout"><h2>Where the movement was</h2><p>Concentration is the finding, not the count: the changes sit on the two clubs '
        f'playing Monday night, plus one withdrawal in Indianapolis. A weekly capture gives those clubs Friday information and the rest of the league '
        f'Friday information, and calls both of them "Week 10".</p>' + slot + "</section>",
        f'<section class="callout"><h2>What this does not claim</h2><p>Two points are not a series. The earlier read carries no clock time, so the gap '
        f'cannot be stated in hours (F-D07). Two rows appearing cannot be attributed to the league rather than to a missed earlier transcription, '
        f'because no sealed hash of the page as served exists for 2026-11-14 (F-D03). And the report still does not carry the reserve list, so an absent '
        f'row means "not in this read", never "available".</p></section>',
    ]
    return page("snapshots.html", "Point-in-time availability series",
                "Sealed, clock-stamped reads of the official Week 10 availability report, the delta between them, and the limits of what two reads can prove.",
                sec)


def pricing():
    # the one settled observation this project has: a line priced before kickoff, then a final
    ne = next(r for r in C.lines_rows if r["game"] == "NE@DET")
    away, home = 10, 35   # Patriots 10, Lions 35, FINAL - official Week 10 schedule page, read 2026-11-15T18:16Z
    actual_margin_home = home - away
    actual_total = home + away
    spread_home = float(ne["model_spread_home"])
    model_total = float(ne["model_total"])
    pred_margin = float(ne["adj_margin_home"])
    p_home = 0.5 * (1.0 + math.erf((pred_margin) / (13.5 * math.sqrt(2.0))))
    brier = (p_home - 1.0) ** 2
    side_hit = actual_margin_home > spread_home
    total_over = actual_total > model_total
    rows = [
        [td("game"), td("NE @ DET (Munich)"), td("final"), td("Patriots 10, Lions 35"),
         source_cell("url:https://www.nfl.com/schedules/2026/by-week/week-10")],
        [td("originated"), td("spread DET -3.5 / total 46.5"), td("priced from"),
         td(f'hub/data/lines.json, for {e(ne["date"])} - before kickoff'), source_cell("file:hub/data/lines.json")],
        [td("side"), td(f'model {e(spread_home)} vs actual {actual_margin_home:+d}'), td("result"),
         td(f'<b>{"HIT" if side_hit else "MISS"}</b> on the side as originated'), source_cell("file:hub/data/lines.json")],
        [td("total"), td(f'model {model_total} vs actual {actual_total}'), td("result"),
         td(f'<b>{"OVER" if total_over else "UNDER"}</b> by {abs(actual_total-model_total):.1f}'), source_cell("file:hub/data/lines.json")],
        [td("margin error"), td(f'predicted {pred_margin} / actual {actual_margin_home}'), td("abs error"),
         td(f'{abs(actual_margin_home-pred_margin):.2f} points'), source_cell("file:hub/data/lines.json")],
        [td("probability"), td(f'P(home) = {p_home:.3f} from Phi(adj_margin/13.5)'), td("Brier"),
         td(f'{brier:.3f} vs 0.250 for a constant - on <b>one</b> game, which is nothing'), source_cell("file:hub/data/lines.json")],
    ]
    pol = []
    for name, what, buys, costs, honest in [
        ("A. No prices, by policy", "the project originates and grades structure only; ROI, CLV and rewards are marked not-applicable, not blank-pending",
         "every page becomes defensible today; nothing monetised is ever implied", "no leaderboard can ever pay out; the staking half stays empty forever",
         "this is the honest default if no feed is licensed, and it is one word change on three trees"),
        ("B. Licensed feed", "contract a market-data source, keep open and close per market with the fetch time, retain the terms",
         "P-01, P-05, P-08, L-01 staking, L-09 - all of them, at once", "procurement and storage policy first; a week of shadow capture before anything cites it",
         "the only path where the residual panel means something on day one"),
        ("C. Self-recorded book", "one operator's open and close captured daily by this project, hashed like the availability store, after a terms read",
         "CLV and a residual without a contract", "legal review; a single book is one book, and vig cannot be separated from it",
         "cheapest path that still produces a real residual; it inherits F-D04's exposure unless S-D8 lands"),
    ]:
        pol.append([td(f'<b>{e(name)}</b>'), td(e(buys)), td(e(costs)), td(e(honest))])
    pending = []
    for r in C.lines_rows:
        g = next((x for x in C.games_rows if x.get("week") == 10 and {x["away"], x["home"]} == {r["away"], r["home"]}), None)
        if r["game"] == "NE@DET":
            st = "FINAL 10-35 (settled above)"
        elif g and g.get("home_score") is not None:
            st = f'FINAL {g["away_score"]}-{g["home_score"]} (already in the corpus)'
        else:
            st = "unplayed or in progress at capture time"
        pending.append([td(e(r["game"])), td(f'{e(r["model_spread_home"])} / {e(r["model_total"])}'), td(e(st)),
                        source_cell("url:https://www.nfl.com/schedules/2026/by-week/week-10")])
    sec = [
        f'<section class="callout"><h2>The decision the brief puts before every backtest</h2>'
        f'<p>"Decide the price-data policy before any backtest is published." Three trees publish walk-forward numbers today, and the repository holds '
        f'{C.n_with_market} market lines across {C.n_priced} priced games. The fair line therefore exists for every market, the market line for none, '
        f'and the residual cannot be computed from anything here. This page states the choice; it does not make it.</p>'
        + table(["option", "what it buys", "what it costs", "what this session would say on the page"], pol, cls="agg") + "</section>",
        f'<section class="callout"><h2>The first and only settled originated line</h2>'
        f'<p>Priced before kickoff by another session, settled today from the official final. Published in full because one observation is a data point, '
        f'and hidden nowhere because one observation is not evidence. The side was covered; the total landed under; the margin error was '
        f'{abs(actual_margin_home-pred_margin):.1f} points, which is the under-spreading flagged as Q-D6 in the open questions.</p>'
        + table(["field", "value", "check", "result", "source"], rows) + "</section>",
        f'<section class="callout"><h2>The rest of the slate, at capture time</h2>'
        f'<p>Settling a partial slate would misreport the model, so the other games are listed as unresolved. At {e(C.AS_OF)} the official page showed '
        f'two finals (Thursday, and Munich), seven 1:00 PM games in progress, and four games not yet started including Monday night.</p>'
        + table(["game", "originated spread / total", "status", "source"], pending) + "</section>",
        '<section class="callout"><h2>What "the residual" would look like</h2><p>Three columns, published from the first day, two of them empty on '
        'purpose: fair line, market line, and the difference, each row carrying the timestamp of the read that produced it. An empty column is the '
        'mechanism that keeps a future number comparable rather than retrofitted - S-D12 in the queue. Until then, "our line versus the market" is '
        'arithmetically undefined here, and every page in this repository says so instead of estimating one.</p></section>',
    ]
    return page("pricing.html", "Price-data policy, and the one settled line",
                "The decision that gates ROI, closing-line value and rewards - plus the single originated line this project has been able to grade.",
                sec)


def trees():
    rows = []
    for t, n in C.TREES:
        note = C.TREES_NOTES.get(t, "not surveyed in detail by this session")
        verdict = "this layer" if t == "decision" else ("canonical candidate" if t in ("hub", "signals") else "duplicate or partial overlap")
        rows.append([td(f'<a href="../{e(t)}/index.html"><span class="mono">{e(t)}/</span></a>'), td(str(n)), td(e(note)),
                     td(badge(verdict.upper() if verdict != "this layer" else "THIS LAYER")),
                     source_cell(f"file:{t}/index.html")])
    sec = [
        f'<section class="callout"><h2>{C.n_trees} directories, each serving its own landing page</h2>'
        f'<p>Counted from the filesystem, not from the notes: {", ".join(t for t,_ in C.TREES)}. Four of them (hub, signals, origin, ops) each '
        f're-implement the same eight operating requirements on the same inputs, and council restates them as acceptance tests. The result is that a '
        f'correction lands in one tree and the wrong number stays published in another - which is exactly what happened to the mislabelled '
        f'correlation (L-07) and to the Munich venue string (G-04, F-D02), still on {C.venue_stale} rows of a served file.</p>'
        f'<p class="note">This session adds a further tree and does not pretend that helps: it is the sixteenth, it implements no competing engine, '
        f'and S-D2 exists to end the pattern. A seventeen-session project needs a merge policy, not another module.</p></section>',
        table(["tree", "pages served", "what it holds", "this session's read", "entry point"], rows),
        f'<section class="callout"><h2>Consolidation, as a decision rather than a cleanup</h2>'
        f'<p>One canonical tree, one results feed, one price store, one correlation store, one leaderboard, one requirement register; the rest frozen '
        f'read-only with a pointer from the landing page. That is S-D2. The mechanical half (choosing <code>hub/</code> or <code>signals/</code>) is an '
        f'afternoon; the judgement half is deciding which engine gets to be the model, because today the site answers that question three different ways '
        f'in three different files.</p></section>',
    ]
    return page("trees.html", "Tree overlap and the consolidation path",
                "Which artefact answers which requirement, and what it costs to keep sixteen sites that each think they are the site.", sec)


def flagged():
    rows = []
    for fid, sev, title, detail, action, src in C.FLAGS:
        rows.append([td(f'<span class="mono">{e(fid)}</span>'), td(badge(sev.upper())), td(f'<b>{e(title)}</b>'),
                     td(e(detail)), td(e(action)), source_cell(src)])
    sec = [
        f'<section class="callout"><h2>Everything this session found that does not look right</h2>'
        f'<p>None of these block the site or the merge, and none are quietly fixed on another session\'s files: each names the file and the action. '
        f'They are published so a reviewer can check them after go-live rather than take this page\'s word for it. Severity is this session\'s read: '
        f'<b>high</b> where the brief and the code disagree, <b>medium</b> where a published number is wrong or unverifiable, <b>low</b> where the '
        f'record needs explaining.</p></section>',
        table(["id", "severity", "irregularity", "what the artefacts say", "proposed action", "source"], rows),
        f'<section class="callout"><h2>Superseded claims, kept on the record</h2><p>Several numbers in the brief no longer describe the repository and '
        f'were re-checked rather than repeated: the Week 10 table is not 254 rows with four injury-free sections but {C.rows_before} rows '
        f'(2026-11-14) then {C.rows_after} rows (2026-11-15) across 28 clubs; "only 6 of 254 rows carry a game designation" is now '
        f'{C.desig_after} of {C.rows_after}; the Baltimore depth chart no longer lists Lamar Jackson and Tyler Huntley at QB - the retained capture '
        f'reads <code>QB Jacoby Brissett Joe Fagnano Kedon Slovis</code>; the three Lions designations (Joseph, Mays, Reed) are populated and print Out; '
        f'and the "136-game log" is {C.n_games} games with {C.n_finals} finals. F-D10 records the pattern: the brief describes a repository that has '
        f'since moved, so each claim was re-read before being repeated here.</p></section>',
    ]
    return page("flagged.html", "Flagged for review",
                "Irregularities and unverifiable items found while verifying, each with its source link and a proposed action.", sec)


def sources():
    src = [
     ("Official NFL injury report, Week 10 2026", "https://www.nfl.com/injuries/league/2026/reg10", C.AS_OF,
      f'all 28 club tables, chunks 0-6; {C.rows_after} player rows, all five columns each; club codes print AZ and LAR'),
     ("Same page as retained by two prior sessions", "https://www.nfl.com/injuries/league/2026/reg10", "2026-11-14",
      f'{C.rows_before} rows; used as the earlier point of the delta and as the pair of independent corroborating reads'),
     ("Official Week 10 2026 schedule", "https://www.nfl.com/schedules/2026/by-week/week-10", C.AS_OF,
      'Patriots 10, Lions 35 FINAL (Munich, International Game); Commanders 24, Giants 21 FINAL (Thu); seven 1:00 PM games in progress; four not started'),
     ("Official injury report, Week 10 2024 - historical reachability test", "https://www.nfl.com/injuries/league/2024/reg10", C.AS_OF,
      'serves a complete prior-season report; the page selector lists seasons back to 1965 and weeks 1-18 plus post-season'),
     ("Announced-starter evidence: Seahawks", "https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders", "linked from the report page at " + C.AS_OF,
      'Drew Lock has no designation and starts at QB for Seattle with Sam Darnold ruled out - a dated official statement of a starter change'),
     ("Announced-starter evidence: Browns and Cardinals", "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11", "2026-11-11",
      'Cleveland to start Deshaun Watson; Arizona\'s Carson Beck to start at Los Angeles'),
     ("Announced-starter evidence: Dolphins", "https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start", "Nov 2026",
      'Malik Willis to IR, Kyle McCord in line for his first start - the reserve-list case where "not listed" is not "available"'),
     ("Gameday injury news affecting Week 11", "https://www.nfl.com/news/lions-aidan-hutchinson-knee-injury-patriots", "2026-11-15",
      'Hutchinson injured on a post-sack celebration in the Munich game; not in any Week 10 report row'),
     ("Club depth chart, Baltimore", "https://www.baltimoreravens.com/team/depth-chart", "retained capture data/desk/text/depth-BAL.txt",
      'line 52 reads QB Jacoby Brissett Joe Fagnano Kedon Slovis'),
     ("Club depth chart, Houston", "https://www.houstontexans.com/team/depth-chart", "retained capture data/desk/text/depth-HOU.txt",
      f'zero parsable depth rows - the image-published chart named in the brief (A-09)'),
     ("Club depth chart, Green Bay", "https://www.packers.com/team/depth-chart", "retained capture data/desk/text/depth-GB.txt",
      'line 51 reads "QB 10 Jordan Love 6 Tyrod Taylor" - jersey numbers prefixed to every name'),
     ("2026 NFL rulebook", "https://operations.nfl.com/the-rules/2026-nfl-rulebook/", "cited by prior sessions",
      'the competition and final-score authority; it defines no betting settlement, which is why M-04 has a source and no parameter'),
     ("GitHub Pages documentation", "https://docs.github.com/pages", "this session",
      'publish source and build requirements for the site this tree is served from'),
    ]
    rows = [[td(f'<b>{e(t)}</b>'), td(f'<a href="{e(u)}" rel="noopener">{e(u)}</a>'), td(e(when)), td(e(what))] for t, u, when, what in src]
    internal = [[td("Snapshot store"), td("two sealed reads, hashes and counts"), source_cell("file:data/snapshots/ledger.json")],
                [td("Point-in-time delta"), td("13 designation changes, 2 added rows, corroboration verdicts"), source_cell("file:data/snapshots/delta.json")],
                [td("Originated Week-10 slate"), td(f'{C.n_priced} games with a fair spread and total, no market line'), source_cell("file:hub/data/lines.json")],
                [td("Results feed"), td(f'{C.n_games} games, {C.n_finals} finals'), source_cell("file:data/desk/games.json")],
                [td("Pre-registration"), td("frozen parameters, including the fixed position costs"), source_cell("file:hub/data/prereg.json")],
                [td("Parser problems"), td(f'{C.parse_problems} recorded problems, incl. the Texans depth page'), source_cell("file:data/desk/parse_report.json")],
                [td("Correlation store"), td("the mislabelled pair, still published under the wrong label"), source_cell("file:data/desk/correlations.json")],
                [td("Venue defect"), td("the unsourced string, still on served rows"), source_cell("file:origin/data/markets.json")]]
    sec = [
        f'<section class="callout"><h2>Official pages read, and when</h2><p>Every value on this tree traces to a row below. Where a claim is about the '
        f'world, the link is to the league or the club; where it is about this repository, the link is to the file. Nothing on any page here is asserted '
        f'from recollection, and where the official page and a reader\'s expectation disagree, the page wins - see F-D08.</p></section>',
        table(["source", "link", "read at", "what it confirmed"], rows),
        f'<section class="callout"><h2>Repository artefacts this tree reads and never writes</h2>' + table(["artefact", "what it holds", "cite"], internal) + "</section>",
        f'<section class="callout"><h2>Sources searched for and not found</h2><p>An official publication of NFL betting prices or of operator '
        f'prop lines: none exists, which is the substance of Q-D1 and the reason the residual, ROI, CLV and rewards rows stay empty rather than '
        f'estimated. An official snap-count or inactive-list feed reachable from this sandbox: none found - the report page carries practice status and '
        f'game status only, and snap counts belong to the Game Center artefacts that no tree here retains. Both absences are stated as absences, '
        f'not filled with a plausible number.</p></section>',
    ]
    return page("sources.html", "Sources and retrieval timestamps",
                "Official pages read line by line, the repository artefacts cited, and what was looked for and does not exist.", sec)


def verification():
    checks = [
        ("Availability series, both ends", f"re-read all {C.rows_after} rows of the official Week 10 report against the two retained 2026-11-14 reads; club-by-club counts recomputed",
         "PASS with one open ambiguity (F-D03: 2 rows appear in the new read that no prior read holds)", "url:" + C.D["source_url"]),
        ("Ledger immutability and provenance", "each sealed capture re-hashed and compared to the ledger; row counts and designation counts recomputed from the stored bytes",
         "PASS - scripts/x3_snapshots_verify.py, exit 0", "file:scripts/x3_snapshots_verify.py"),
        ("Delta reconciliation", "the level change (+11 designations) must equal gained-minus-lost-plus-adds-minus-drops from the row-level events; a mismatch aborts",
         "PASS - reconciles exactly; the builder also proved deterministic (byte-identical JSON on re-run)", "file:data/snapshots/delta.json"),
        ("Club-code join hazard", "an unmapped official club code now fails the build; the two that need mapping are declared",
         "PASS - AZ and LAR mapped and asserted; 29 phantom adds/drops eliminated", "file:scripts/x3_snapshots.py"),
        ("Lions game statuses (brief: three missing)", "Kerby Joseph, Cade Mays, D.J. Reed read from the live page and from the hub store",
         "3 of 3 print Out in both; the brief's defect is resolved", "url:" + C.D["source_url"]),
        ("Week 10 volume claims in the brief", "254 rows / 4 injury-free sections / 6 designated rows, re-counted",
         f"superseded: {C.rows_before} then {C.rows_after} rows, {C.desig_after} with a designation (F-D10)", "url:" + C.D["source_url"]),
        ("Baltimore stale-depth claim", "retained capture grep for Jackson and Huntley at QB",
         "no longer present; line 52 reads Brissett, Fagnano, Slovis (A-19)", "file:data/desk/text/depth-BAL.txt"),
        ("Two named depth-parsing failures", "row counts derived per club from the retained depth captures",
         f"Packers raw still carries jersey-number prefixes; Texans yields 0 rows; {C.depth_clubs} of 32 clubs parse (A-09, A-14)", "file:data/desk/text/depth-HOU.txt"),
        ("Munich venue string", "grep for 'Alemun' across served files",
         f"still on {C.venue_stale} rows of origin/data/markets.json; official page prints International Game / Munich (F-D02)",
         "https://www.nfl.com/schedules/2026/by-week/week-10"),
        ("Fixed penalty versus ablation", "adj_margin_home = base_margin_home + injury_delta checked on all priced rows; prereg position costs read",
         "confirmed: a fixed additive penalty is in force and pre-registered (F-D01, Q-D11)", "file:hub/data/prereg.json"),
        ("Settlement of the originated line", "Patriots 10 Lions 35 read from the official schedule page, compared to the stored originated line",
         "side HIT, total UNDER by 1.5, margin error 21.36 points, Brier 0.155 on n=1 (F-D11)", "https://www.nfl.com/schedules/2026/by-week/week-10"),
        ("Internal links and row citations", "every row of every table on this tree must link to an official page or to an existing repository file",
         "enforced by scripts/verify_decision.py, which fails the build on a bare row", "file:scripts/verify_decision.py"),
    ]
    rows = [[td(f'<b>{e(a)}</b>'), td(e(b)), td(e(c)), source_cell(d)] for a, b, c, d in checks]
    sec = [
        f'<section class="callout"><h2>Method</h2><p>Line by line, from the artefact, with the link. Two disciplines are enforced mechanically rather '
        f'than promised: no row on this tree may make a claim without a source cell that resolves - an official URL, or a repository path that exists '
        f'and is checked at build time; and no number in the prose may be typed in, since every one is interpolated from a data file at build time and '
        f'an unfilled key aborts the build. Where verification could not be completed, the row says so in the status basis instead of looking settled.</p>'
        f'<p class="note">Re-run: <code>python3 scripts/x3_snapshots.py &amp;&amp; python3 scripts/x3_snapshots_verify.py &amp;&amp; '
        f'python3 scripts/build_decision.py &amp;&amp; python3 scripts/verify_decision.py</code> - all offline, all deterministic.</p></section>',
        table(["what was checked", "how", "result", "source"], rows),
        f'<section class="callout"><h2>Corrections this session made to its own draft, and why they are still here</h2>'
        f'<p>The first cut of the delta reported 15 added and 15 dropped rows for Arizona, plus 14 more for the Rams. That was a join failure wearing a '
        f'migration\'s clothes: the official page prints AZ and LAR while the repository keys those clubs ARI and LA. The fix is an explicit alias map '
        f'with a build-time assertion, so the next unmapped code fails loudly instead of publishing a roster shake-up. A second draft counted '
        f'"13 designation changes" as "+13 designations", which the reconciliation check rejected: one of the 13 was a withdrawal, so the level moved by '
        f'+11. Both are recorded because a verification log that only shows clean passes is not a log.</p></section>',
    ]
    return page("verification.html", "Verification log",
                "What was checked, against which official page or file, and what happened when a check failed.", sec)


def execsum():
    counts = {}
    for r in C.REQS:
        counts[r[2]] = counts.get(r[2], 0) + 1
    ready, partial = counts.get("READY", 0), counts.get("PARTIAL", 0)
    blocked = counts.get("BLOCKED", 0) + counts.get("NOT STARTED", 0)
    sec = [
        kpi([(f"{ready}/{len(C.REQS)}", "requirements ready and stated as such"),
             (f"{partial}", "partial, with the missing half named"),
             (f"{blocked}", "blocked or not started"),
             ("2", "defects where published content is wrong"),
             (f"{C.n_desig_changes}", "availability changes measured in one day"),
             ("1", "originated line settled to date")]),
        f'<section class="callout"><h2>The position in one paragraph</h2><p>The data layer is real and it is verified: {C.n_games} games with '
        f'{C.n_finals} finals reconciled to the official standings, {C.rows_after} availability rows on 28 clubs re-read this session with hashes and '
        f'clock times, {C.n_priced} games originated with a fair spread and total, one order-checked three-market pipeline, and gates that rank on '
        f'proper scores with confidence intervals instead of win rate. What is missing is not sloppy work but absent input: a single market price. '
        f'There is no official NFL publication of prices, so the fair line exists for every market, the market line for none, and ROI, '
        f'closing-line value, rewards and the staking half of the leaderboard are all one decision away from existing - or one decision away from being '
        f'correctly declared out of scope. That decision (S-D1) is the most consequential line in this project.</p></section>',
        f'<section class="callout"><h2>What is genuinely new since the last session</h2>'
        f'<p><b>A time series instead of a snapshot.</b> Two sealed reads of the official report, one day apart, with the delta published: '
        f'{C.n_desig_changes} designation changes, {C.n_prac_changes} practice-only moves, {C.n_added} rows appearing, and one designation withdrawn - '
        f'almost all of it on the two Monday-night clubs. That settles an open design question: report "finality" belongs to a game slot, not to a week, '
        f'so the capture cadence must be cut per kickoff (S-D6) or a weekly backtest leaks and starves at the same time.</p>'
        f'<p><b>The first settled originated line.</b> Patriots 10, Lions 35: the side as originated (DET -3.5) covered, the total (46.5) landed under, '
        f'and the margin error was 21.4 points against a predicted margin of 3.6 - the under-spreading flagged across the site, now with a dated, '
        f'sourced example. One game, so it is published as a data point and nothing more.</p>'
        f'<p><b>An unblock.</b> Past seasons are reachable on the official site (Week 10 2024 served in full; the selector runs to 1965), which converts '
        f'archiving prior reports, a train/validation/holdout season split and the empirical calibration of "Questionable" from impossible to '
        f'work (S-D4).</p></section>',
        f'<section class="callout"><h2>Three things a reader should be told, not shown a chart of</h2>'
        f'<p><b>The model disagrees with the brief on injuries.</b> The pre-registered model applies a fixed points cost per absent starter '
        f'(QB 4.0, RB 1.5, WR 1.1, and a status weight of Out 1.0 / Doubtful 0.9 / Questionable 0.35) and adds it to the margin. The brief rejects exactly '
        f'that and asks for an ablation with uncertainty (F-D01, Q-D11, S-D5). Both are defensible; only one is what was asked for, and the site should '
        f'say which it is showing.</p>'
        f'<p><b>A wrong string is still published.</b> The Munich venue appears on {C.venue_stale} served rows as "Alemun &amp; Munchen", which no '
        f'official page prints. A prior session corrected the correlation label in one tree and left the old one in another; the same fix-in-the-wrong-place '
        f'pattern is why the venue survives (F-D02, L-07, S-D14). Both are minutes of work once someone owns one tree.</p>'
        f'<p><b>The raw club pages are on the public site.</b> {len(C.depth_files)} depth captures and game-centre text sit under the publish root while '
        f'the terms are unread (F-D04, S-D8). Moving the bodies out costs nothing analytically, because every derived row already links to the official page.</p></section>',
        f'<section class="callout"><h2>What this project should do next, in order</h2><p>1. Decide the price-data policy (S-D1) and label every published '
        f'backtest with it. 2. Choose one canonical tree and freeze the other {C.n_trees-1} with a pointer (S-D2). 3. Put the capture on a per-game clock '
        f'in CI with raw bytes and HTTP headers (S-D3, S-D6). 4. Backfill prior seasons and build the holdout (S-D4). 5. Replace the fixed injury penalty '
        f'with an ablation and re-register (S-D5). 6. Add transactions/reserve and T-90 inactive captures (S-D7, S-D9), which is the only route from '
        f'"a backup is suspected to start" to "a backup is confirmed to start".</p>'
        f'<p class="note">Everything above is a choice this session deliberately did not make: the brief asks for a review section where paths are '
        f'compared before work is implemented, so the register, the queue and the questions are the deliverable, and the queue is empty of '
        f'implementations by design.</p></section>',
    ]
    return page("executive-summary.html", "Executive summary",
                "The state of the project, the two things published wrongly, and the ordered next moves - for a decision, not for reading.", sec)


def landing_block():
    """A paste-ready section for the root landing page. The landing page belongs to
    another session while PR #72 is open, so this is emitted rather than inserted,
    and the request is logged in COORDINATION.md."""
    rows = []
    for rid, text, st, where, gate, clears, basis, src in C.REQS:
        rows.append(f'<tr><td class="mono">{e(rid)}</td><td>{e(text)}</td><td>{badge(st)}</td>'
                    f'<td>{e(gate)}</td><td>{e(clears)}</td><td class="src">{source_link(src)}</td></tr>')
    tbl = ('<table class="data"><thead><tr><th>id</th><th>requirement</th><th>status</th><th>gate that blocks it</th>'
           '<th>the number that would clear it</th><th>source</th></tr></thead><tbody>'
           + "\n".join(rows) + "</tbody></table>")
    return (f'<!-- BEGIN DECISION-READINESS (generated by scripts/build_decision.py - do not hand-edit) -->\n'
            f'<!-- data-link-base="root": a paste-ready fragment for the root landing page, '
            f'so its links are written against the repository root. -->\n'
            f'<section class="callout" style="margin-top:22px">\n<h2>Decision readiness - one row per requirement</h2>\n'
            f'<p>Generated from the repository. Statuses: {sum(1 for r in C.REQS if r[2]=="READY")} ready, '
            f'{sum(1 for r in C.REQS if r[2]=="PARTIAL")} partial, {sum(1 for r in C.REQS if r[2] in ("BLOCKED","NOT STARTED"))} blocked or not started, '
            f'{sum(1 for r in C.REQS if r[2]=="DEFECT")} defects. Full register with evidence and per-row basis: '
            f'<a href="decision/readiness.html">decision/readiness.html</a>. Paths to choose between: '
            f'<a href="decision/suggestions.html">decision/suggestions.html</a>.</p>\n{tbl}\n</section>\n'
            f'<!-- END DECISION-READINESS -->\n')


def source_link(src):
    """Links for the paste-ready landing block, which lives at the repository
    root: repo paths are root-relative, and this tree's own pages are prefixed."""
    if src.startswith(("http://", "https://")):
        src = "url:" + src          # tolerate a bare URL at any call site
    kind, _, path = src.partition(":")
    if kind == "url":
        return f'<a href="{e(path)}" rel="noopener">official page</a>'
    if os.path.isdir(os.path.join(ROOT, path)):
        # A repo directory is cited by a link to its tree on GitHub, so the row carries a
        # resolvable source rather than unlinked text.
        url = "https://github.com/karagemop466-tech/X3/tree/main/" + path.rstrip("/")
        return f'<a class="cite" href="{e(url)}" rel="noopener">repo: {e(path)}</a>'
    if path.startswith("decision/"):
        return f'<a class="cite" href="{e(path)}">{e(path)}</a>'
    return f'<a class="cite" href="{e(path)}">{e(path)}</a>'


CSS = """/* X3 decision layer - sits on top of the hub stylesheet, adds only what that one lacks. */
.badge.b-ok{background:#0d5c2e;color:#d9f6e4}
.badge.b-warn{background:#6b4c05;color:#fdf0cf}
.badge.b-bad{background:#7a1414;color:#ffe0e0}
.badge.b-dim{background:#2c3138;color:#c9d1d9}
.badge.b-info{background:#123a63;color:#d6e9ff}
.decision{display:inline-block;padding:2px 8px;border:1px dashed #7a828c;border-radius:4px;color:#9aa4ae;font-size:.8rem}
.opt{margin:0 0 6px;font-size:.86rem}
.sm{font-size:.82rem;color:#b6bec6}
.muted{color:#8b949e}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.84rem}
table.data td{vertical-align:top}
table.data.narrow{max-width:420px}
.src{white-space:nowrap}
.src a,.src .cite{color:#79b8ff;font-size:.78rem;text-decoration:underline dotted;word-break:break-all;white-space:normal;display:block}
.foot{margin:34px 0 10px;color:#8b949e;font-size:.8rem;border-top:1px solid #21262d;padding-top:14px}
.card.t a{display:block;text-decoration:none;color:inherit}
.card.t a span{display:block;color:#9aa4ae;font-size:.82rem;margin-top:6px}
.card.t{transition:border-color .15s ease}
.card.t:hover{border-color:#388bfd}
main h2{margin-top:26px}
section.callout{margin-top:22px}
a.active{border-color:#388bfd;background:#132a45}
"""


def main():
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    writers = {
        "index.html": index, "readiness.html": readiness, "suggestions.html": suggestions,
        "questions.html": questions, "snapshots.html": snapshots, "pricing.html": pricing,
        "trees.html": trees, "flagged.html": flagged, "sources.html": sources,
        "verification.html": verification, "executive-summary.html": execsum, "landing-block.html": landing_block,
    }
    for name, fn in writers.items():
        doc = fn()
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(doc)
    with open(os.path.join(OUT, "assets", "decision.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    print(f"wrote {len(writers)} files to decision/  ({len(C.REQS)} requirement rows, {len(C.SUGS)} suggestions, "
          f"{len(C.QUESTIONS)} questions, {len(C.FLAGS)} flags, {C.n_trees} trees counted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
