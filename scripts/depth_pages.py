#!/usr/bin/env python3
"""HTML for depth/ (session arena/784043ed-x3). Called only from scripts/depth_build.py.

Every table body row carries a source link (the official club page, or the nfl.com page it cites).
Nothing on the page is inferred; statuses are copied from cross_checks built by depth_build.py.
"""
from __future__ import annotations

import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = """
:root{--ink:#14202b;--mut:#5b6876;--line:#dfe4ea;--bg:#f7f8fa;--card:#fff;--acc:#1d4f7a;--warn:#8a5a00;--ok:#1f6b3a;--bad:#9b2226}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#10273b;color:#fff;padding:14px 22px}header a{color:#cfe3f5}
header h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:#b9cadb;font-size:13px}
main{max-width:1200px;margin:0 auto;padding:18px}
h2{font-size:17px;margin:26px 0 8px}
p.lede{color:var(--mut);margin:4px 0 12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:10px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--mut);font-size:12px}
.tw{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f0f3f7;position:sticky;top:0}
td.raw{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:#35424f}
.tag{display:inline-block;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:600;background:#eef2f6;color:#33465c}
.tag.ok{background:#e4f3ea;color:var(--ok)}.tag.warn{background:#fff3d6;color:var(--warn)}.tag.bad{background:#fbe3e4;color:var(--bad)}
nav.sub{margin:8px 0 2px}nav.sub a{margin-right:12px;color:var(--acc)}
.note{background:#fff;border-left:4px solid var(--acc);padding:8px 12px;margin:10px 0;border-radius:4px;color:#2b3a48}
"""

STATUS_TAG = {
    "CONFIRMED": "ok", "CONFIRMED_IN_REPO_NOT_RE_READ": "ok", "REPRODUCED_HANDLED": "ok",
    "NOT_REPRODUCED": "warn", "NOT_REPRODUCED_ON_2026_11_19": "warn",
    "UNVERIFIED_NO_STRUCTURED_SOURCE": "bad", "FLAG_FOR_REVIEW": "warn", "DISCREPANCY_UNRECONCILED": "bad",
    "NOT_CONFIRMED": "bad",
}


def e(x):
    return html.escape(str(x if x is not None else ""))


def link(url, text=None):
    if not url:
        return ""
    return f'<a href="{e(url)}" rel="noopener">{e(text or url)}</a>'


def src_links(text):
    urls = re.findall(r"https?://[^\s;)]+", text or "")
    return " · ".join(link(u, u.replace("https://", "")) for u in urls)


def page(title, body, active):
    nav = [("index.html", "Summary"), ("register.html", "Register"), ("flagged.html", "Flagged for review")]
    navh = "".join('<a href="%s"%s>%s</a>' % (h, ' style="font-weight:700"' if h == active else "", t) for h, t in nav)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · Depth-chart register</title><style>{CSS}</style></head>
<body><header><h1>Depth-chart register: dated, per row, with sources</h1>
<p>Source: official club depth-chart pages (links on every row). Read dates shown. <a href="../index.html">← X3 landing</a></p>
<nav class="sub">{navh}</nav></header>
<main>{body}</main></body></html>
"""


def write_pages(d):
    reg = d["register"]
    groups = d["groups"]
    conflicts = d["conflicts"]
    checks = d["checks"]
    s = d["summary"]
    lions = d["lions"]
    dup_rows = d["dup_rows"]
    live_meta = d["live_meta"]
    LIVE = d["LIVE_DATE"]
    CAP = d["CAPTURE_DATE"]
    out_dir = d["PAGE_DIR"]
    os.makedirs(out_dir, exist_ok=True)

    cap_clubs = s["clubs_captured_2026_11_14"]
    live_clubs = s["clubs_text_read_2026_11_19"]
    mr = s["multi_rank1_groups"]

    kpis = [
        (cap_clubs, f"club charts captured {CAP} (repo, not re-read)"),
        (live_clubs, f"club charts text re-read {LIVE} (BAL, GB, SEA, WAS)"),
        (s["clubs_no_text_2026_11_19"][0], "Houston: image only, zero rows"),
        (s["register_rows_by_snapshot"][CAP], f"register rows, {CAP} snapshot"),
        (s["register_rows_by_snapshot"][LIVE], f"register rows, {LIVE} snapshot"),
        (mr[CAP], f"groups with more than one rank-1 row ({CAP})"),
        (s["slot_status_counts"]["SHARED"], "shared cells (two players in one slot)"),
        (s["slot_status_counts"]["GAP"], "gap cells (empty slot before a filled one)"),
        (s["jersey_numbers_stripped"], f"jersey numbers stripped, {LIVE} (raw kept)"),
    ]
    kpi_html = "".join(f'<div class="kpi"><b>{e(v)}</b><span>{e(t)}</span></div>' for v, t in kpis)

    def tag(st):
        return f'<span class="tag {STATUS_TAG.get(st, "")}">{e(st)}</span>'

    # Cross-check table
    cc_rows = []
    for c in checks:
        cc_rows.append(
            f"<tr><td>{e(c['id'])}</td><td>{e(c['item'])}</td><td>{e(c['observation'])}</td>"
            f"<td>{tag(c['status'])}</td><td>{e(c['notes'])}</td><td>{src_links(c['official_source'])}</td></tr>"
        )
    cc_html = ('<div class="tw"><table><tr><th>ID</th><th>Brief item</th><th>What the record shows</th><th>Status</th>'
               '<th>Notes</th><th>Source</th></tr>' + "".join(cc_rows) + "</table></div>")

    # Lions
    lions_rows = "".join(
        f"<tr><td>{e(l['player'])}</td><td>{e(l['position'])}</td><td>{e(l['injury'])}</td><td>{e(l['practice'])}</td>"
        f"<td>{e(l['game_status'])}</td><td>{link('https://www.nfl.com/news/nfl-week-10-injury-report-2026-season', 'nfl.com Week-10 article')}</td></tr>"
        for l in lions)
    lions_html = ('<div class="tw"><table><tr><th>Player</th><th>Pos</th><th>Injury</th><th>Practice</th><th>Game status (repo)</th>'
                  '<th>Source</th></tr>' + lions_rows + "</table></div>")

    # Conflicts
    con_rows = "".join(
        f"<tr><td>{e(c['club'])}</td><td>{tag('NOT_REPRODUCED' if c['change']=='NOT_ON_LIVE_CHART' else 'FLAG_FOR_REVIEW')} {e(c['change'])}</td>"
        f"<td>{e(c['player'])}</td><td class='raw'>{e(c['capture_2026_11_14'])}</td><td class='raw'>{e(c['live_2026_11_19'])}</td>"
        f"<td>{link(c['live_url'], 'club page')}</td></tr>"
        for c in conflicts)
    con_html = ('<div class="tw"><table><tr><th>Club</th><th>Change</th><th>Player</th><th>2026-11-14 capture</th>'
                '<th>2026-11-19 live</th><th>Source</th></tr>' + con_rows + "</table></div>")

    # Groups (live snapshot only, multi-rank-1 + all groups of the four re-read clubs)
    grp_rows = "".join(
        f"<tr><td>{e(g['snapshot_date'])}</td><td>{e(g['club'])}</td><td>{e(g['unit'])}</td><td>{e(g['position'])}</td>"
        f"<td>{e(g['n_rows'])}</td><td>{e(g['n_rank1_filled_rows'])}</td><td>{e(g['multi_rank1'])}</td>"
        f"<td>{e(g['n_shared_cells'])}</td><td>{e(g['n_gap_cells'])}</td><td>{e(g['note'])}</td>"
        f"<td>{link(live_meta[g['club']]['url'] if g['snapshot_date']==LIVE and g['club'] in live_meta else '', 'club page')}</td></tr>"
        for g in groups if g["snapshot_date"] == LIVE)
    grp_html = ('<div class="tw"><table><tr><th>Snapshot</th><th>Club</th><th>Unit</th><th>Position</th><th>Rows</th>'
                '<th>Rank-1 rows filled</th><th>More than one rank-1</th><th>Shared</th><th>Gaps</th><th>Note</th><th>Source</th></tr>'
                + grp_rows + "</table></div>")

    # Register (all rows)
    reg_rows = []
    for r in reg:
        reg_rows.append(
            f"<tr><td>{e(r['snapshot_date'])}</td><td>{e(r['club'])}</td><td>{e(r['unit'])}</td><td>{e(r['position'])}</td>"
            f"<td>{e(r['row_no'])}</td><td>{e(r['rank'])}</td><td>{e(r['slot_status'])}</td>"
            f"<td>{e(r['player_name'])}</td><td class='raw'>{e(r['player_cell_raw'])}</td><td>{e(r['co_listed'])}</td>"
            f"<td>{e(r['flags'])}</td><td>{link(r['source_url'], 'club page')}</td></tr>")
    reg_html = ('<div class="tw"><table><tr><th>Read date</th><th>Club</th><th>Unit</th><th>Position label</th><th>Row</th><th>Rank</th>'
                '<th>Slot status</th><th>Player (name)</th><th>Cell as published</th><th>Co-listed</th><th>Flags</th><th>Source</th></tr>'
                + "".join(reg_rows) + "</table></div>")

    summary_body = f"""
<h2>Summary</h2>
<p class="lede">Depth charts are kept per row, with the read date and the official club page. Charts are never read as "the starter" unless the page lists a rank-1 name. Read dates: {e(CAP)} (repo captures, not re-read this session) and {e(LIVE)} (text re-read this session).</p>
<div class="kpis">{kpi_html}</div>
<div class="note"><b>Read first.</b> The 2026-11-19 re-read differs from the 2026-11-14 captures for Baltimore, Green Bay, Seattle and Washington. Every difference is listed below. The existing depth outputs built on the 2026-11-14 captures must not be treated as current.</div>
<h2>Cross-checks against official sources (every row sourced or flagged)</h2>
{cc_html}
<h2>Live (2026-11-19) vs captured (2026-11-14): conflicts</h2>
<p class="lede">{len(conflicts)} conflicts across four clubs. Rows show the player and slot on each read.</p>
{con_html}
<h2>Slot groups on the 2026-11-19 live charts</h2>
<p class="lede">A group is one club, unit and position label. More than one rank-1 row means the chart does not name a single starter for that group.</p>
{grp_html}
<h2>Lions Week-10 game-status check (VR-08, VR-12)</h2>
{lions_html}
<p class="lede">Source article: nfl.com Week-10 injury report. The repo table already holds Out for all three.</p>
"""
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(page("Summary", summary_body, "index.html"))

    open(os.path.join(out_dir, "register.html"), "w", encoding="utf-8").write(page("Register", f"""
<h2>Full register ({len(reg)} rows)</h2>
<p class="lede">One row per cell that is filled, shared, a gap or empty, for every chart read. Machine-readable copy: <code>data/depth/depth_register.csv</code> (SHA-256 of each source file in the same file).</p>
{reg_html}
""", "register.html"))

    flag_rows = []
    for c in checks:
        if c["status"] in ("FLAG_FOR_REVIEW", "NOT_REPRODUCED", "NOT_REPRODUCED_ON_2026_11_19", "DISCREPANCY_UNRECONCILED", "UNVERIFIED_NO_STRUCTURED_SOURCE", "NOT_CONFIRMED", "CONFIRMED_IN_REPO_NOT_RE_READ"):
            flag_rows.append(
                f"<tr><td>{e(c['id'])}</td><td>{e(c['item'])}</td><td>{tag(c['status'])}</td><td>{e(c['notes'])}</td>"
                f"<td>{src_links(c['official_source'])}</td></tr>")
    url_by = {(r["snapshot_date"], r["club"]): r["source_url"] for r in reg}
    dup_html = "".join(
        f"<tr><td>{e(k[0])}</td><td>{e(k[1])}</td><td>{e(k[2])}</td><td class='raw'>{e('; '.join(f'{u} / {p} / rank {rk}' for u,p,rk in v))}</td>"
        f"<td>{link(url_by.get((k[0], k[1])), 'club page')}</td></tr>"
        for k, v in dup_rows)
    flagged_body = f"""
<h2>Flagged for review</h2>
<p class="lede">These items are not resolved by this module. Each one is published with its source link. None of them blocks the site.</p>
<div class="tw"><table><tr><th>ID</th><th>Item</th><th>Status</th><th>Notes</th><th>Source</th></tr>{''.join(flag_rows)}</table></div>
<h2>Same player in more than one slot (same club, same snapshot)</h2>
<p class="lede">Informational. A player listed at two slots is not an error by itself, but it means the chart does not say which slot the player fills.</p>
<div class="tw"><table><tr><th>Snapshot</th><th>Club</th><th>Player</th><th>Slots</th><th>Source</th></tr>{dup_html}</table></div>
<h2>Not done in this module (by design)</h2>
<ul>
<li>Houston (HOU): the chart is an image. It is not transcribed by eye. No structured source has been found.</li>
<li>The other 26 clubs were not re-read on 2026-11-19. Their rows are the 2026-11-14 captures, dated as such.</li>
<li>Whether a listed player is available on game day comes from the injury report and the Game Book, not from the chart.</li>
</ul>
"""
    open(os.path.join(out_dir, "flagged.html"), "w", encoding="utf-8").write(page("Flagged for review", flagged_body, "flagged.html"))
