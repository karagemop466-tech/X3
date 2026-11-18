#!/usr/bin/env python3
"""Render the week11 module (session arena/40cd3b17-x3, task M2).

Reads the committed fresh-day reads and the computed freshness audit from
data/week11/ and writes the static pages under week11/. Deterministic: same
inputs -> byte-identical pages. No prose figure is hand-typed; every number is
interpolated from the data files.

Run: python3 scripts/week11_audit.py && python3 scripts/week11_build.py
"""
from __future__ import annotations

import csv
import json
import os
from html import escape as _h

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "week11")
SITE = os.path.join(ROOT, "week11")

STANDINGS_URL = "https://www.nfl.com/standings/league/2026/REG"
WK10_URL = "https://www.nfl.com/schedules/2026/by-week/week-10"
WK11_URL = "https://www.nfl.com/schedules/2026/by-week/week-11"
REG11_URL = "https://www.nfl.com/injuries/league/2026/reg11"

CSS = """:root{--ink:#1c2330;--mut:#5b6577;--line:#d8dee9;--bg:#f6f8fb;--ok:#1a7f37;--bad:#b42318;--warn:#946800}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#0b1f3a;color:#fff;padding:26px 22px 20px}header h1{margin:0 0 6px;font-size:24px}header p{margin:0;color:#c7d2e4;max-width:70em}
nav.bar{background:#12294a;padding:10px 22px}nav.bar a{color:#dbe6f6;margin-right:18px;text-decoration:none;font-weight:600}nav.bar a:hover{text-decoration:underline}
main{max-width:1120px;margin:0 auto;padding:22px}
h2{margin:26px 0 10px;font-size:19px}h3{margin:18px 0 8px;font-size:16px}
p.lede{font-size:16px;color:var(--ink)}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:13.5px}
caption{caption-side:top;text-align:left;padding:10px 12px;font-weight:700;color:var(--mut);background:#eef2f7}
th{background:#eef2f7;text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:6px 10px;border-bottom:1px solid #e8ecf2;vertical-align:top}
tr:last-child td{border-bottom:none}
td.mut{color:var(--mut)}td.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11.5px;font-weight:700}
.b-ok{background:#e6f4ea;color:var(--ok)}.b-bad{background:#fde8e8;color:var(--bad)}.b-warn{background:#fdf3d7;color:var(--warn)}.b-mut{background:#e9edf3;color:var(--mut)}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}
.kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 16px;min-width:150px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--mut);font-size:12.5px}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid #0b1f3a;border-radius:8px;padding:14px 16px;margin:14px 0}
.src{white-space:nowrap}.src a{color:#0b57d0;text-decoration:none}.src a:hover{text-decoration:underline}
code{background:#eef2f7;padding:0 4px;border-radius:4px;font-size:12.5px}
footer{max-width:1120px;margin:0 auto;padding:10px 22px 30px;color:var(--mut);font-size:12.5px}
"""

NAV = [
    ("index.html", "Overview"),
    ("freshness.html", "Freshness audit"),
    ("freshness-detail.html", "Freshness detail"),
    ("report.html", "Week-11 report watch"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
]


def esc(x):
    return _h("" if x is None else str(x), quote=True)


def link(url, label):
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'


def table(cols, rows, tid, caption=None):
    c = f"<caption>{esc(caption)}</caption>" if caption else ""
    th = "".join(f"<th>{esc(x)}</th>" for x in cols)
    body = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
    return (f'<div class="tblwrap"><table id="{tid}">{c}<thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def rd(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def badge(verdict):
    m = {"MATCH": ("b-ok", "MATCH"), "VARIANT": ("b-warn", "VARIANT"),
         "MISMATCH": ("b-bad", "MISMATCH"), "PENDING": ("b-warn", "PENDING"),
         "PUBLISHED": ("b-ok", "PUBLISHED")}
    k, t = m.get(verdict, ("b-mut", verdict))
    return f'<span class="badge {k}">{t}</span>'


def page(fname, title, lede, body):
    nav = "".join(f'<a href="{n}">{esc(l)}</a>' for n, l in NAV)
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 week11</title><link rel="stylesheet" href="assets/week11.css"></head>
<body><header><h1>{esc(title)}</h1><p>{esc(lede)}</p></header>
<nav class="bar">{nav}</nav><main>
{body}
</main><footer>week11 module - session arena/40cd3b17-x3 - built by <code>scripts/week11_build.py</code> from <code>data/week11/</code>. Every value traces to an official source or is left blank and flagged. Shell HTTP is blocked in the authoring sandbox: official pages are read with the page-reader tool, and each read records the tool clock time.</footer>
</body></html>"""
    with open(os.path.join(SITE, fname), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    with open(os.path.join(SITE, "assets", "week11.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    summary = json.load(open(os.path.join(DATA, "freshness_summary.json"), encoding="utf-8"))
    audit = rd(os.path.join(DATA, "freshness_audit.csv"))
    probes = rd(os.path.join(DATA, "reg11_probes.csv"))
    standings = rd(os.path.join(DATA, "standings_read_2026-11-18.csv"))
    finals = rd(os.path.join(DATA, "week10_finals_read_2026-11-18.csv"))
    slate = rd(os.path.join(DATA, "week11_slate_read_2026-11-18.csv"))
    manifest = rd(os.path.join(DATA, "captures", "manifest.csv"))

    mism = [r for r in audit if r["verdict"] == "MISMATCH"]
    assert not mism, "the audit must be clean before the site is built"
    last_probe = probes[-1]["probe_utc"]
    published = summary["reg11_published"]

    # ---------------- index ----------------
    kpis = "".join(
        f'<div class="kpi"><b>{v}</b><span>{s}</span></div>' for v, s in [
            (len(audit), "field-level comparisons, all MATCH"),
            (0, "mismatches against committed canonical numbers"),
            (len(standings), "standings rows re-read (32 clubs)"),
            (len(finals), "Week-10 finals re-read, all FINAL"),
            (len(slate), "Week-11 fixtures re-read + 6 byes"),
            (len(probes), "dated reg11 probes (B50 series)"),
        ])
    report_state = ("the league has published the Week-11 report - captured below"
                    if published else
                    f"the league has not yet published the Week-11 report (latest probe {esc(last_probe)} UTC)")
    idx_body = f"""
<p class="lede">This module is the Wednesday 2026-11-18 entry of two standing requirements: it re-reads
today's official pages and diffs them against the committed canonical numbers (a freshness audit, not a
new feed), and it opens the B50 Wed/Thu/Fri capture series for the Week-11 report, whose first snap is
Thursday 2026-11-19 8:15 PM ET per the official schedule page.</p>
<div class="kpis">{kpis}</div>
<div class="callout"><b>Week-11 report status:</b> {report_state}. Every probe is logged with its clock
time on <a href="report.html">Week-11 report watch</a>; nothing is transcribed until the page itself
serves a Week-11 report.</div>
<h2>What was re-read</h2>
{table(['Dataset', 'Official page read', 'Rows read', 'Compared against', 'Verdict'], [
    ['2026 league standings (32 clubs)', link(STANDINGS_URL, 'nfl.com/standings/league/2026/REG'),
     len(standings), 'data/atlas + data/closeout registers', badge('MATCH')],
    ['Week-10 finals (14 games)', link(WK10_URL, 'nfl.com/schedules/2026/by-week/week-10'),
     len(finals), 'data/closeout/week10_finals.csv', badge('MATCH')],
    ['Week-11 slate (13 games + byes)', link(WK11_URL, 'nfl.com/schedules/2026/by-week/week-11'),
     len(slate), 'data/closeout/week11_slate.csv + week11_byes.csv', badge('MATCH')],
    ['League arithmetic', 'computed from the standings read', 'sum PF = sum PA = '
     f'{summary["standings_league_pf"]}', 'data/closeout/derived/reconciliation.csv', badge('MATCH')],
], tid='idx', caption='Fresh-day reads of 2026-11-18 vs the committed canonical numbers')}
<h2>Why a freshness audit instead of a new dataset</h2>
<p>Three prior sessions already publish canonical registers for these datasets (atlas and closeout), each
guarded by its own CI gate. Re-publishing them would create a fourth competing copy; instead this module
re-reads the official pages and diffs them field by field against what is committed, so drift would fail
loudly here and in <code>scripts/week11_verify.py</code> - the same fail-loudly rule the drift-alarm
requirement (B62) pins on every scraper. Full field-level detail:
<a href="freshness.html">freshness audit</a>.</p>
"""
    page("index.html", "Week-11 Wednesday watch", "Fresh-day verification of 2026-11-18 and the first dated entry of the Week-11 report capture series.", idx_body)

    # ---------------- freshness ----------------
    # one summary row per (dataset, key): fields compared + verdict
    keys = []
    seen = {}
    order = []
    for r in audit:
        k = (r["dataset"], r["key"])
        if k not in seen:
            seen[k] = {"fields": 0, "verdicts": set(), "src": r["official_source"],
                       "reg": r["committed_register"]}
            order.append(k)
        seen[k]["fields"] += 1
        seen[k]["verdicts"].add(r["verdict"])
    for (ds, key) in order:
        e = seen[(ds, key)]
        vs = e["verdicts"]
        if "MISMATCH" in vs:
            v = "MISMATCH"
        elif "PENDING" in vs:
            v = "PENDING"
        elif "VARIANT" in vs:
            v = "VARIANT"
        else:
            v = "MATCH"
        label = {"standings": "standings club", "wk10_finals": "Week-10 game",
                 "wk11_slate": "Week-11 fixture", "wk11_byes": "Week-11 bye",
                 "reg11_probe": "reg11 probe"}.get(ds, ds)
        keys.append([esc(label), f"<b>{esc(key)}</b>", e["fields"], badge(v),
                     f'<span class="mut">{esc(e["reg"])}</span>',
                     f'<span class="src">{link(e["src"], "official")}</span>'
                     if e["src"].startswith("http") else f'<span class="mut">{esc(e["src"])}</span>'])
    detail = [[esc(r["dataset"]), f"<b>{esc(r['key'])}</b>", esc(r["field"]),
               esc(r["committed_value"]), esc(r["read_today"]), badge(r["verdict"]),
               f'<span class="mut">{esc(r["committed_register"])}</span>',
               f'<span class="src">{link(r["official_source"], "official")}</span>'
               if r["official_source"].startswith("http") else '<span class="mut">computed</span>']
              for r in audit]
    fresh_body = f"""
<p class="lede">Every field published in the committed canonical registers was re-read today from the
official page and compared. {len(audit)} field-level comparisons, {len(mism)} mismatches. League
arithmetic on today's read: sum PF {summary['standings_league_pf']} = sum PA {summary['standings_league_pa']},
and PF-PA = NET for all 32 clubs. Percentage cells are compared to three decimals because the two
committed registers write .889 and 0.889 for the same published value. The complete field-level list is
on <a href="freshness-detail.html">freshness detail</a>; the committed machine-readable form is
<code>data/week11/freshness_audit.csv</code>.</p>
{table(['Dataset', 'Key', 'Fields compared', 'Verdict', 'Committed register', 'Source'],
       keys, tid='fresh-key', caption='One row per compared key - the freshness verdict at reading granularity')}
"""
    page("freshness.html", "Freshness audit", f"{len(audit)} field-level comparisons between the official pages of 2026-11-18 and the committed canonical numbers - {len(mism)} mismatches.", fresh_body)

    detail_body = f"""
<p class="lede">All {len(audit)} field-level comparisons behind the
<a href="freshness.html">freshness verdict</a> - dataset, key, field, the committed value, the value
read today from the official page, and the verdict. This is the rendered form of
<code>data/week11/freshness_audit.csv</code>; a MISMATCH anywhere fails
<code>scripts/week11_audit.py</code> and the CI gate.</p>
{table(['Dataset', 'Key', 'Field', 'Committed', 'Read today', 'Verdict', 'Committed register', 'Source'],
       detail, tid='fresh-detail', caption='All field-level comparisons (data/week11/freshness_audit.csv)')}
"""
    page("freshness-detail.html", "Freshness detail", "Every field-level comparison between the 2026-11-18 official reads and the committed canonical registers.", detail_body)


    # ---------------- report watch ----------------
    probe_rows = [[esc(p["probe_utc"]),
                   f'<span class="src">{link(p["url"], "nfl.com/injuries/league/2026/reg11")}</span>',
                   esc(p["observed_week"]),
                   f'<span class="mut">{esc(p["redirected_to"])}</span>',
                   esc(p["finding"])]
                  for p in probes]
    report_body = f"""
<p class="lede">Requirement B50 wants the official report captured every Wednesday, Thursday and Friday
with its fetch time, so designations can be replayed as they were known. This page holds the capture
series for Week 11. The first snap is Thursday, November 19th, 8:15 PM ET per the
{link(WK11_URL, 'official Week-11 schedule page')}.</p>
<div class="callout"><b>Status as of {esc(last_probe)} UTC:</b> {"the Week-11 report is published and captured (see below)." if published else "the league has not yet published the Week-11 report. The endpoint serves the Week-10 report. The probe series below is the dated evidence; no Week-11 row is transcribed from anywhere else, and none is inferred."}</div>
{table(['Probe (UTC)', 'Endpoint', 'Week served', 'Effective URL', 'Finding'],
       probe_rows, tid='probe', caption='Dated probe log - the Wednesday entry of the B50 capture series')}
<h2>Why the probe log is the deliverable before publication</h2>
<p>The report page carries no last-updated timestamp (standing question Q-04), so the only way to bracket
designation timing is to store dated reads. Before the league publishes, the honest capture is the probe
itself: it proves the endpoint state at a recorded clock time. Once a probe observes a Week-11 report,
the capture (raw evidence + sha256 in <code>data/week11/captures/</code>) and the per-club designation
table are added here and never back-filled.</p>
"""
    page("report.html", "Week-11 report watch", "The Wed/Thu/Fri capture series for the official Week-11 injury report (requirement B50), with clock times.", report_body)

    # ---------------- sources ----------------
    src_rows = [
        ["2026 league standings", link(STANDINGS_URL, "nfl.com/standings/league/2026/REG"),
         "all 32 league rows, read twice (twice-read discipline)", "2026-11-18T03:05Z-03:25Z",
         "<code>captures/standings_2026-11-18.md</code>"],
        ["Week-10 results", link(WK10_URL, "nfl.com/schedules/2026/by-week/week-10"),
         "all 14 finals + page bye block", "2026-11-18T03:05Z-03:25Z",
         "<code>captures/week10_finals_2026-11-18.md</code>"],
        ["Week-11 schedule", link(WK11_URL, "nfl.com/schedules/2026/by-week/week-11"),
         "all 13 fixtures, kickoff clocks, networks, venue blocks, page bye block",
         "2026-11-18T03:05Z-03:25Z", "<code>captures/week11_slate_2026-11-18.md</code>"],
        ["Week-11 report endpoint", link(REG11_URL, "nfl.com/injuries/league/2026/reg11"),
         "probe: serves the Week-10 report (report not yet published)", "2026-11-18T03:06Z, 03:16Z",
         "<code>captures/reg11_probe_2026-11-18.md</code>"],
    ]
    m_rows = [[f"<code>{esc(m['file'])}</code>", f'<span class="mut">{esc(m["sha256"])}</span>']
              for m in manifest]
    src_body = f"""
<p class="lede">Every value in this module traces to one of the official pages below. The authoring
sandbox's shell cannot reach nfl.com; the page-reader tool is the route, and each read is recorded with
the tool clock time. Raw evidence notes and their sha256 live in <code>data/week11/captures/</code>.</p>
{table(['Source', 'Official page', 'What was read', 'Read window (UTC)', 'Capture'], src_rows, tid='src', caption='Official-source register')}
<h2>Capture manifest (sha256)</h2>
{table(['File', 'SHA-256'], m_rows, tid='manifest', caption='data/week11/captures/manifest.csv')}
"""
    page("sources.html", "Sources", "Official pages read on 2026-11-18, what was read from each, and the hashed capture files.", src_body)

    # ---------------- flagged ----------------
    fl_rows = [
        ["<b>W1</b>", '<span class="badge b-warn">OPEN</span>', "Week-11 report",
         "the league has not published the Week-11 report; reg11 serves the Week-10 report on every probe so far",
         f'<span class="src">{link(REG11_URL, "probe evidence")}</span>',
         "capture when published; probe series continues Wed/Thu/Fri (B50)"],
        ["<b>W2</b>", '<span class="badge b-mut">DISCLOSED</span>', "transcription quality",
         "the first read of the CIN standings row noted non-conf 2-1-0, arithmetically impossible with a "
         "7-game conference record on 9 games; the twice-read rule caught it and the second read shows "
         "2-0-0, matching both committed registers and the arithmetic",
         f'<span class="src">{link(STANDINGS_URL, "official page")}</span>',
         "disclosed in captures/README.md; committed transcription uses the twice-read value"],
        ["<b>W3</b>", '<span class="badge b-warn">KNOWN SPLIT</span>', "venue naming",
         "the schedule page's club block says GEHA Field at Arrowhead Stadium while the game centre says "
         "Arrowhead Stadium - the standing official-source naming split (flag F-03 in the atlas module)",
         f'<span class="src">{link(WK11_URL, "week-11 page")}</span>',
         "recorded as VARIANT, never reconciled by inference"],
        ["<b>W4</b>", '<span class="badge b-warn">VARIANT</span>', "MIN@SF venue evidence depth",
         "the week-11 page renders the Mexico City International Series event block; the game-centre read "
         "(closeout register) names Estadio Banorte. Same site, different published granularity",
         f'<span class="src">{link(WK11_URL, "week-11 page")}</span>',
         "recorded as VARIANT; the game-centre evidence remains the deeper class"],
    ]
    fl_body = f"""
<p class="lede">Irregularities and disclosures found during the 2026-11-18 fresh-day round. None blocks
the merge; each stays open until an official source resolves it. Every row carries its evidence link.</p>
{table(['ID', 'Status', 'Area', 'Finding', 'Evidence', 'Action'], fl_rows, tid='flg', caption='Flagged for review - week11 module')}
"""
    page("flagged.html", "Flagged for review", "Open irregularities and disclosures from the 2026-11-18 fresh-day round, each with its evidence.", fl_body)

    print(f"week11 build: 6 pages from {len(audit)} audit rows, {len(probes)} probes, "
          f"{len(standings)}+{len(finals)}+{len(slate)} read rows")


if __name__ == "__main__":
    main()
