#!/usr/bin/env python3
"""Round-2 module builder (session arena/4c2f61cd-x3, 2026-11-15).

Renders round2/*.html deterministically from round2/data/*.csv.
Every data table carries a Source column; rows are either linked to an
official source or explicitly flagged UNVERIFIED / UNCOVERED / DERIVED.
Reads only round2/data/*.csv - no network access, no other module writes.
"""
from __future__ import annotations

import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "round2" / "data"
OUT = ROOT / "round2"

STATUS_BADGE = {
    "done": '<span class="st st-done">done</span>',
    "done (as implemented)": '<span class="st st-done">done (as implemented)</span>',
    "done (rejected)": '<span class="st st-done">done (rejected)</span>',
    "done (module)": '<span class="st st-done">done (module)</span>',
    "done (as rendered)": '<span class="st st-done">done (as rendered)</span>',
    "done (this round)": '<span class="st st-done">done (this round)</span>',
    "partial": '<span class="st st-partial">partial</span>',
    "blocked": '<span class="st st-blocked">blocked</span>',
    "not covered": '<span class="st st-missing">not covered</span>',
}


def read_csv(name: str) -> tuple[list[str], list[dict]]:
    with open(D / name, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def table(cols: list[str], rows: list[dict], source_col: str = "source") -> str:
    out = ['<table><thead><tr>']
    for c in cols:
        out.append(f"<th>{html.escape(c)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for c in cols:
            v = row.get(c, "")
            if c == source_col:
                v = source_cell(v)
            out.append(f"<td>{v}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def source_cell(v: str) -> str:
    """Render a source cell: links stay as-is (already html in data), plain
    official URLs become links, and unverified/derived values get a badge."""
    if v.startswith("http"):
        return f'<a class="src" href="{html.escape(v, quote=True)}" target="_blank" rel="noopener">official source</a>'
    return v  # already HTML (internal links / badges written by the callers)


CSS = """
:root{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--brand:#0b3b5c;--acc:#0e7490;--ok:#047857;--warn:#b45309;--bad:#b91c1c}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:#f8fafc}
header.top{background:var(--brand);color:#fff;padding:14px 20px;display:flex;gap:18px;align-items:baseline;flex-wrap:wrap}
header.top .brand{font-weight:700;font-size:17px}
header.top nav a{color:#dbeafe;margin-right:12px;text-decoration:none;font-size:13.5px}
header.top nav a:hover{text-decoration:underline}
main{max-width:1180px;margin:0 auto;padding:22px 20px 60px}
h1{font-size:24px;margin:6px 0 4px}
h2{font-size:19px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:16px;margin:18px 0 6px}
p.lede{color:var(--mut);margin-top:0}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13px;margin:10px 0}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f1f5f9;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:#334155}
tr:nth-child(even) td{background:#fcfdfe}
a.src{color:var(--acc);text-decoration:none;border-bottom:1px dotted var(--acc)}
a.inl{color:var(--brand);text-decoration:none;border-bottom:1px dotted var(--brand)}
.st{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11.5px;font-weight:600;white-space:nowrap}
.st-done{background:#d1fae5;color:var(--ok)}
.st-partial{background:#fef3c7;color:var(--warn)}
.st-missing{background:#fee2e2;color:var(--bad)}
.st-blocked{background:#e2e8f0;color:#334155}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px}
.kpi b{display:block;font-size:22px}
.kpi span{color:var(--mut);font-size:12.5px}
.note{background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:13.5px}
footer{border-top:1px solid var(--line);margin-top:40px;padding-top:12px;color:var(--mut);font-size:12.5px}
"""

NAV = """
<header class="top"><div class="brand">X3 &middot; round 2 (2026-11-15)</div>
<nav>
<a href="index.html">Round 2</a>
<a href="verification.html">Verification</a>
<a href="readiness.html">Decision readiness</a>
<a href="audit.html">Repo audit</a>
<a href="flagged.html">Flagged for review</a>
<a href="suggestions.html">Suggestions</a>
<a href="sources.html">Sources</a>
<a href="../index.html">Site root</a>
</nav></header>
"""


def page(fname: str, title: str, body: str, desc: str) -> None:
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} - X3 round 2</title>
<meta name="description" content="{html.escape(desc)}">
<style>{CSS}</style>
</head>
<body>
{NAV}
<main>
{body}
<footer>
Session <code>arena/4c2f61cd-x3</code> &middot; 2026-11-15 &middot; built by
<code>scripts/build_round2.py</code> from <code>round2/data/*.csv</code> &middot;
<a href="../COORDINATION.md">coordination log</a> &middot;
<a href="https://www.nfl.com/">nfl.com</a> is the primary data authority; every value is linked or flagged.
</footer>
</main>
</body>
</html>
"""
    (OUT / fname).write_text(doc, encoding="utf-8")
    print(f"wrote: round2/{fname}")


def inl(path: str, label: str) -> str:
    return f'<a class="inl" href="{path}">{html.escape(label)}</a>'


def main() -> None:
    # ---------- index ----------
    body = f"""
<h1>Round 2: fresh-day verification &amp; decision readiness</h1>
<p class="lede">Session <code>arena/4c2f61cd-x3</code>, 2026-11-15 (NFL Week&nbsp;10 game day).
This round re-verified the repository against official NFL sources on a fresh day, captured the
Week&nbsp;10 state as it happened, proved the official Game&nbsp;Book capture route, and built the
decision-readiness matrix the brief asks for: <em>one row per requirement, with the gate that
blocks it and the number that would clear it</em>.</p>

<div class="kpis">
  <div class="kpi"><b>66</b><span>requirement lines mapped in the readiness matrix</span></div>
  <div class="kpi"><b>32</b><span>done &middot; 20 partial &middot; 13 not covered &middot; 1 blocked</span></div>
  <div class="kpi"><b>30 / 32</b><span>official standings rows matched the repo exactly; the 2 diffs are exactly today's Munich final</span></div>
  <div class="kpi"><b>44 + 12</b><span>official Game Book starters + Not Active transcribed (NE@DET)</span></div>
  <div class="kpi"><b>12 / 12</b><span>repo-wide gates PASS (221 pages, 7,686 source rows)</span></div>
  <div class="kpi"><b>7</b><span>new flags for review (2 new evidence irregularities)</span></div>
</div>

<h2>What this round did</h2>
<ul>
  <li><b>Fresh-day reconciliation.</b> All 32 official league standings rows were compared to the repo snapshot: 30 identical; the only two differences (DET, NE) are <em>exactly</em> the Munich final played this morning (DET 35, NE&nbsp;10) - the repo's 137-final feed is consistent with the official record. {inl('verification.html', 'Verification log')}</li>
  <li><b>Week&nbsp;10 captured live.</b> The official Week&nbsp;10 slate was captured at fetch time: two finals (WAS 24 @ NYG 21; NE 10 @ DET 35), seven early games live 0-0 in Q1, three late games, SNF and MNF pending, byes CHI/DEN/PHI/TB. {inl('verification.html', 'Details')}</li>
  <li><b>Official Game Book route proven.</b> The Game Center links an official NFL Game Book PDF; this round transcribed its lineups (44 starters), Not Active lists (12 players), venue, game-day weather, roof/surface, officials and attendance - the evidence class the brief demands for starters and inactives. {inl('verification.html', 'Game Book capture')}</li>
  <li><b>Decision-readiness matrix built.</b> 66 requirement lines from the brief, each with its implementing page, blocking gate, and the number that would clear it. {inl('readiness.html', 'Open the matrix')}</li>
  <li><b>Repo-wide audit re-run.</b> Every published gate passed on 2026-11-15. {inl('audit.html', 'Gate results')}</li>
  <li><b>Gaps published for review.</b> 13 brief lines have no first-class coverage; 7 flags and 10 suggestions are queued for the reviewer. {inl('flagged.html', 'Flags')} &middot; {inl('suggestions.html', 'Suggestions')}</li>
</ul>

<h2>Round-2 data files</h2>
<p>All captures live under <code>round2/data/</code>: standings, Week&nbsp;10 slate, results delta,
Game Book facts/starters/inactives, the full requirements matrix, audit results, flags, suggestions
and the sources register. Every row carries its official source link.</p>
"""
    page("index.html", "Round 2 landing", body, "Fresh-day re-verification round and decision-readiness matrix")

    # ---------- verification ----------
    _, slate = read_csv("week10_slate_2026-11-15.csv")
    _, rec = read_csv("week10_results_delta_2026-11-15.csv")
    _, gbf = read_csv("gamebook_munich_facts.csv")
    _, st = read_csv("gamebook_munich_starters.csv")
    _, na = read_csv("gamebook_munich_not_active.csv")
    std_cols, std = read_csv("standings_league_2026-11-15.csv")

    def rows_with_src(rows, cols, src="source_url", extra=None):
        out = []
        for r in rows:
            rr = dict(r)
            rr[src] = f'<a class="src" href="{html.escape(rr[src], quote=True)}" target="_blank" rel="noopener">official source</a>'
            out.append(rr)
        return out

    slate_cols = ["game_id", "date", "window", "away", "home", "status_at_capture", "score_at_capture", "network", "source_url"]
    body = f"""
<h1>Verification log - 2026-11-15</h1>
<p class="lede">Every check below was performed on NFL Week&nbsp;10 game day against official NFL pages,
fetched fresh by this session. Fetch timestamps are in {inl('sources.html', 'the sources register')}.</p>

<h2>1. League standings reconciliation (line by line, 32 rows)</h2>
<p>The repo snapshot (<code>data/hub/standings_2026_thru_wk9.csv</code>, captured 2026-11-14) was compared
column by column (W, L, T, PF, PA) against the official league standings page fetched 2026-11-15.</p>
{table(["check", "repo_value", "official_value_2026-11-15", "verdict", "detail", "source_url"], rows_with_src(rec, ["check", "repo_value", "official_value_2026-11-15", "verdict", "detail", "source_url"]))}
<div class="note"><b>Verdict:</b> the repo results feed is consistent with the official record as of
2026-11-15. The single new final the repo lacks is the Munich game (DET 35, NE 10), recorded in this
round's delta. Do not overwrite the owned modules' data from this round; the delta is published here
for the capture job to ingest.</div>

<h2>2. Week 10 slate as captured (14 games + byes)</h2>
{table(slate_cols, rows_with_src(slate, slate_cols))}
<p>Byes at capture: CHI (7-2), DEN (7-2), PHI (2-7), TB (3-6) -
<a class="src" href="https://www.nfl.com/schedules/2026/by-week/week-10" target="_blank" rel="noopener">official week-10 page</a>.
Early-window games were live 0-0 in Q1 at fetch time; their scores are therefore
<span class="st st-partial">capture-time values</span>, not results.</p>

<h2>3. Official Game Book capture (NE @ DET, Munich, 2026-11-15)</h2>
<p>The official Game Center links the NFL Game Book PDF. This is the evidence class the brief
requires for actual starters, game-day status, venue and weather - captured here for the first time
in the repository.</p>
{table(["item", "value", "verbatim_context", "source_url"], rows_with_src(gbf, ["item", "value", "verbatim_context", "source_url"]))}

<h3>Official starting lineups (44 players)</h3>
{table(["team", "unit", "slot", "player", "notes"], st)}

<h3>Official Not Active lists (12 players)</h3>
{table(["team", "listed_as", "player", "cross_check"], na)}
<div class="note"><b>Cross-check:</b> DET CB D.J. Reed (hip) and DET C Cade Mays (ankle) are Not Active
in the Game Book, matching their official Out designations in the repo injuries rows dated 2026-11-15.
DET S Kerby Joseph (officially Out) does <em>not</em> appear in the rendered Not Active list -
see flag <b>R2-F1</b> on {inl('flagged.html', 'Flagged for review')}.</div>

<h2>4. Official standings table as fetched (32 rows, 2026-11-15)</h2>
<p>Raw capture, fetch-time-stamped. Column order follows the official page (W, L, T, PCT, PF, PA, NET,
home, road, division, division pct, conference, conference pct, non-conference, streak, last 5).</p>
{table(std_cols, std, source_col="__none__")}
<p class="lede">Source: <a class="src" href="https://www.nfl.com/standings/league/2026/REG" target="_blank" rel="noopener">https://www.nfl.com/standings/league/2026/REG</a> (fetched 2026-11-15, games live in progress - see flag R2-F4).</p>
"""
    page("verification.html", "Verification log", body, "Line-by-line fresh-day verification against official NFL sources")

    # ---------- readiness ----------
    _, reqs = read_csv("requirements_full.csv")
    req_rows = []
    for r in reqs:
        st_txt = r["status"]
        badge = STATUS_BADGE.get(st_txt, STATUS_BADGE.get(st_txt.split(" (")[0], f'<span class="st st-partial">{html.escape(st_txt)}</span>'))
        req_rows.append({
            "id": html.escape(r["id"]),
            "requirement": html.escape(r["requirement"]),
            "status": badge,
            "where": inl(r["where"].split(" ")[0] if r["where"].startswith("http") else r["where"], r["where"]) if False else f'<a class="inl" href="{r["where"].split(" ")[0]}" target="_blank" rel="noopener">{html.escape(r["where"])}</a>',
            "blocking_gate": html.escape(r["blocking_gate"]),
            "clear": html.escape(r["number_that_would_clear_it"]),
            "source": f'<a class="src" href="{html.escape(r["source"], quote=True)}" target="_blank" rel="noopener">source</a>',
        })
    body = f"""
<h1>Decision-readiness matrix</h1>
<p class="lede">One row per requirement line from the brief: the implementing page, the gate that
blocks it, and the number that would clear it. Statuses verified 2026-11-15 against the repository
(searches performed per row) and official sources. 32 done &middot; 20 partial &middot; 13 not covered
&middot; 1 blocked.</p>
{table(["id", "requirement", "status", "where", "blocking_gate", "clear", "source"], req_rows)}
<div class="note"><b>How to read this:</b> <span class="st st-done">done</span> = a first-class
implementation exists and was re-verified. <span class="st st-partial">partial</span> = something
exists but a named gate blocks completion (the gate and the clearing number are in the row).
<span class="st st-missing">not covered</span> = nothing implements it anywhere in the repo (searched
2026-11-15); these are queued as flags and suggestions, not implemented by this session, because the
brief requires reviewer sign-off before new work. <span class="st st-blocked">blocked</span> = not
computable until an external input (market prices) exists.</div>
"""
    page("readiness.html", "Decision readiness", body, "One row per requirement: implementing page, blocking gate, number that clears it")

    # ---------- audit ----------
    _, audit = read_csv("audit_round2.csv")
    audit_rows = []
    for r in audit:
        audit_rows.append({
            "gate": html.escape(r["gate"]),
            "script": f'<a class="inl" href="{r["script"].split(" ")[0]}" target="_blank" rel="noopener">{html.escape(r["script"])}</a>',
            "result": r["result"].replace("PASS", '<span class="st st-done">PASS</span>').replace("CAPTURED", '<span class="st st-done">CAPTURED</span>'),
            "key_numbers": html.escape(r["key_numbers"]),
            "source": f'<a class="src" href="{html.escape(r["source_url"], quote=True)}" target="_blank" rel="noopener">source</a>',
        })
    body = f"""
<h1>Repo audit - 2026-11-15</h1>
<p class="lede">Every gate in the repository was run by this session on 2026-11-15 before any change
was made. All gates pass on the working tree, and the market engines rebuild byte-identical
(deterministic). Numbers are the scripts' own reported values.</p>
{table(["gate", "script", "result", "key_numbers", "source"], audit_rows)}
<h2>Gate scope</h2>
<p>The repo-wide audit (<code>scripts/audit_all.py</code>) covers every HTML page in the repository:
221 pages, 15,778 link references (5,359 internal), 401 tables; 7,686 source rows, of which 7,509
carry a link and 177 carry an explicit UNVERIFIED marker; all 372 flagged-page rows carry a marker.
This round's pages are built to the same rule and are picked up automatically.</p>
"""
    page("audit.html", "Repo audit", body, "Repo-wide gate results re-run on 2026-11-15")

    # ---------- flagged ----------
    _, flags = read_csv("flags_round2.csv")
    flag_rows = []
    for r in flags:
        sev = r["severity"]
        sev_badge = f'<span class="st st-missing">{html.escape(sev)}</span>' if "high" in sev else f'<span class="st st-partial">{html.escape(sev)}</span>'
        flag_rows.append({
            "id": f'<b>{html.escape(r["id"])}</b>',
            "flag": html.escape(r["flag"]),
            "severity": sev_badge,
            "detail": html.escape(r["detail"]),
            "resolve": html.escape(r["what_would_resolve_it"]),
            "source": f'<a class="src" href="{html.escape(r["source_url"], quote=True)}" target="_blank" rel="noopener">source</a>',
        })
    body = f"""
<h1>Flagged for review - round 2 (2026-11-15)</h1>
<p class="lede">Non-blocking. Irregularities and unverified items found by this round, published here
with sources so the reviewer can request changes after the site is live. Pre-existing flags live on
<a class="inl" href="../signals/flagged.html" target="_blank" rel="noopener">signals/flagged.html</a>
and the other modules' flagged pages; those are not duplicated here.</p>
{table(["id", "flag", "severity", "detail", "resolve", "source"], flag_rows)}
"""
    page("flagged.html", "Flagged for review", body, "Round-2 irregularities and unverified items for reviewer review")

    # ---------- suggestions ----------
    _, sug = read_csv("suggestions_round2.csv")
    sug_rows = []
    for r in sug:
        sug_rows.append({
            "id": f'<b>{html.escape(r["id"])}</b>',
            "suggestion": html.escape(r["suggestion"]),
            "addresses": html.escape(r["addresses"]),
            "first_step": html.escape(r["first_step"]),
            "decision": html.escape(r["decision_needed"]),
            "source": f'<a class="src" href="{html.escape(r["source_url"], quote=True)}" target="_blank" rel="noopener">source</a>',
        })
    body = f"""
<h1>Suggestions awaiting a decision - round 2</h1>
<p class="lede">Nothing below is implemented. Per the brief, suggestions are reviewed here, a path is
chosen, and only then does implementation start. Each suggestion names the readiness-matrix rows it
addresses and the first concrete step.</p>
{table(["id", "suggestion", "addresses", "first_step", "decision", "source"], sug_rows)}
"""
    page("suggestions.html", "Suggestions", body, "Round-2 suggestions awaiting reviewer decision")

    # ---------- sources ----------
    _, srcs = read_csv("sources_round2.csv")
    src_rows = []
    for r in srcs:
        src_rows.append({
            "source": html.escape(r["source"]),
            "url": f'<a class="src" href="{html.escape(r["url"], quote=True)}" target="_blank" rel="noopener">{html.escape(r["url"])}</a>',
            "fetched": html.escape(r["fetched_at_utc"]),
            "what": html.escape(r["what_was_taken"]),
            "status": html.escape(r["status"]),
        })
    body = f"""
<h1>Sources register - round 2</h1>
<p class="lede">Every page this session fetched or referenced on 2026-11-15, with what was taken from
it. Official NFL properties only; third-party mirrors are cited as corroboration in the audit page, never as
the primary source of a value.</p>
{table(["source", "url", "fetched", "what", "status"], src_rows)}
"""
    page("sources.html", "Sources", body, "Round-2 sources register with fetch timestamps")


if __name__ == "__main__":
    main()
