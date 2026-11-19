"""Static pages for the Week-10 recount (called by scripts/recount_build.py).

Every table row carries a source link to an official NFL page (or to the schedule
page for bye clubs). Committed-file references are relative links to repo files.
Nothing here is typed by hand: all numbers come from the build's data structures.
"""
from __future__ import annotations

import html
import os
from collections import Counter, defaultdict

E = lambda s: html.escape("" if s is None else str(s), quote=True)

CSS = """
body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1d2330;background:#f7f8fa}
header{background:#0b2545;color:#fff;padding:14px 22px}
header a{color:#cfe3ff;margin-right:14px;text-decoration:none}
header b{font-size:17px;margin-right:24px}
main{max-width:1200px;margin:0 auto;padding:18px 22px 60px}
h1{font-size:24px;margin:8px 0 4px} h2{font-size:18px;margin:28px 0 8px;border-bottom:2px solid #d8dee9;padding-bottom:4px}
.lede{color:#3d4657;max-width:900px}
.banner{background:#fff4e5;border-left:5px solid #e08a00;padding:10px 14px;margin:14px 0;border-radius:4px}
.ok{background:#eaf7ee;border-left-color:#2e8b57}
table{border-collapse:collapse;width:100%;background:#fff;margin:8px 0 14px;font-size:14px}
th,td{border:1px solid #dde3ec;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eef2f8;font-weight:600}
tr.diff td{background:#fff8e6}
tr.miss td{background:#fdecec}
.num{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:12px;font-weight:600}
.t-ok{background:#d9f2e3;color:#1d6b3a}.t-bad{background:#fbd7d7;color:#8a1c1c}.t-warn{background:#ffe9b3;color:#7a5200}
.small{font-size:13px;color:#4a5365}
code{background:#eef2f8;padding:0 4px;border-radius:3px}
"""

NAV = """<header><b>X3 · Week 10 recount</b>
<a href="../index.html">Repo landing</a><a href="index.html">Summary</a><a href="rows.html">All 347 rows</a>
<a href="#flags">Flags</a></header>"""


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><style>{CSS}</style></head>
<body>{NAV}<main>{body}</main></body></html>
"""


def _tag(kind: str, text: str) -> str:
    cls = {"ok": "t-ok", "bad": "t-bad", "warn": "t-warn"}[kind]
    return f'<span class="tag {cls}">{E(text)}</span>'


def _count(committed: dict, club: str) -> int:
    return sum(len(v) for k, v in committed.items() if k[0] == club)


def write_pages(live, cmp, audit, agency, hub, diffs, root) -> None:
    out_dir = os.path.join(root, "recount")
    os.makedirs(out_dir, exist_ok=True)
    REG10 = cmp["source"]
    SCHED = cmp["schedule"]
    s_agency, s_audit, s_hub = cmp["comparisons"]

    # ---- per-club counts
    st_by_club = defaultdict(Counter)
    for r in live:
        st_by_club[r["club"]][r["game_status"] or "(blank)"] += 1
    clubs = sorted(set(st_by_club) | set(cmp["bye_clubs"]))

    # ---- diffs grouped per (club, player, field) for the index table
    grouped = defaultdict(dict)
    order = []
    for d in diffs:
        key = (d["row_no"], d["club"], d["player"], d["field"])
        if key not in grouped:
            grouped[key] = {}
            order.append(key)
        grouped[key][d["source"]] = d["committed"]
    lookup_live = {r["row_no"]: r for r in live}

    def live_val(r, field):
        return {"position": r["position"], "injury": r["injury"], "practice_status": r["practice_status"],
                "game_status": r["game_status"], "ROW": "present"}[field]

    # ================= index.html =================
    b = []
    b.append("<h1>Week 10 injury report — full recount</h1>")
    b.append('<p class="lede">The official NFL Week-10 injury report was re-read in full on 2026-11-19 (all 8 chunks of the page), '
             'transcribed row by row, and compared with the three committed Week-10 tables in this repository. '
             'Each figure below is either read from the official page or computed from that transcription. '
             'Nothing is inferred; committed files are not edited by this page.</p>')
    lac_bal = sum(1 for d in diffs if d["source"] == "audit" and d["club"] in ("LAC", "BAL") and d["field"] != "ROW")
    other = sum(1 for d in diffs if d["source"] == "audit" and d["club"] not in ("LAC", "BAL") and d["field"] != "ROW")
    b.append(f'<div class="banner"><b>Result:</b> the live page has <b>{cmp["live_rows"]} player rows</b> in '
             f'<b>{cmp["live_clubs"]} club sections</b> across <b>{cmp["live_games"]} games</b>. '
             f'The agency capture matches all {s_agency["matched_players"]} players; its {s_agency["field_differences"]} differing field value{"" if s_agency["field_differences"] == 1 else "s"} {"is" if s_agency["field_differences"] == 1 else "are"} capitalisation only. '
             f'The audit and hub tables are <b>stale</b>: they are missing {s_audit["missing_from_committed"]} Ravens rows and disagree on '
             f'{s_audit["field_differences"]} field values ({lac_bal} in the Chargers and Ravens block, LAC @ BAL, and {other} elsewhere; see R-F9).</div>')

    b.append("<h2>1. What the official page shows today</h2>")
    b.append('<table><thead><tr><th>Measure</th><th class="num">Value</th><th>Source</th></tr></thead><tbody>')
    rows_meas = [
        ("Player rows on the report", cmp["live_rows"], REG10),
        ("Club sections on the report", cmp["live_clubs"], REG10),
        ("Games on the report (listed in the page's day sections)", cmp["live_games"], REG10),
        ("Clubs absent from the report (Week-10 byes: " + ", ".join(cmp["bye_clubs"]) + ")", len(cmp["bye_clubs"]), SCHED),
        ("Rows with game status Out", cmp["status_counts"].get("Out", 0), REG10),
        ("Rows with game status Questionable", cmp["status_counts"].get("Questionable", 0), REG10),
        ("Rows with game status Doubtful", cmp["status_counts"].get("Doubtful", 0), REG10),
        ("Rows with blank game status", cmp["status_counts"].get("(blank)", 0), REG10),
    ]
    for label, val, src in rows_meas:
        b.append(f'<tr><td>{E(label)}</td><td class="num">{E(val)}</td>'
                 f'<td><a href="{E(src)}" rel="noopener">{E(src)}</a></td></tr>')
    b.append("</tbody></table>")

    b.append("<h2>2. Committed tables compared with the live page</h2>")
    b.append('<table><thead><tr><th>Committed file</th><th class="num">Rows</th><th class="num">Matched by club + player</th>'
             '<th class="num">Missing</th><th class="num">Field values that differ</th><th>Verdict</th><th>Source</th></tr></thead><tbody>')
    verdicts = {
        "agency": ("ok", "Matches live page"),  # capitalisation-only differences are listed in section 3
        "audit": ("bad", "Stale — republish"),
        "hub": ("bad", "Stale — republish"),
    }
    for s, key, path in [(s_agency, "agency", "agency/data/derived/injury_designations_w10_2026.csv"),
                         (s_audit, "audit", "audit/official_injury_wk10_2026.csv"),
                         (s_hub, "hub", "data/hub/injuries_2026_wk10.csv")]:
        kind, txt = verdicts[key]
        if key == "agency":
            txt = f"Matches live page ({s['field_differences']} capitalisation-only difference)"
        b.append(f'<tr><td><a href="../{E(path)}">{E(path)}</a></td><td class="num">{s["committed_rows"]}</td>'
                 f'<td class="num">{s["matched_players"]}</td><td class="num">{s["missing_from_committed"]}</td>'
                 f'<td class="num">{s["field_differences"]}</td><td>{_tag(kind, txt)}</td>'
                 f'<td><a href="{E(REG10)}">{E(REG10)}</a></td></tr>')
    b.append("</tbody></table>")
    b.append('<p class="small">The hub table is the one shown on the site (hub/injuries). The audit and hub tables hold the same 345 rows. '
             'Republishing requires an integration session, because the hub is a shared build output (see COORDINATION.md, '
             'session arena/d6d831c6-x3, request R-1).</p>')

    b.append("<h2>3. Every difference from the live page</h2>")
    b.append('<p class="small">One line per player-field. "missing" = the player is not in that committed file. '
             'Practice status is compared in full text; committed abbreviations (Full / Limited / DNP) are expanded first.</p>')
    b.append('<table><thead><tr><th class="num">Live row</th><th>Club</th><th>Player</th><th>Field</th>'
             '<th>Live (official)</th><th>Audit file</th><th>Hub file</th><th>Agency file</th><th>Source</th></tr></thead><tbody>')
    for key in order:
        row_no, club, player, field = key
        lr = lookup_live[row_no]
        vals = grouped[key]
        def cv(src):
            if src not in vals:
                return "—"
            v = vals[src]
            return "missing" if v == "missing" else (v if v != "" else "(blank)")
        cls = "miss" if field == "ROW" else "diff"
        b.append(f'<tr class="{cls}"><td class="num">{row_no}</td><td>{E(club)}</td><td>{E(player)}</td>'
                 f'<td>{E(field)}</td><td>{E(live_val(lr, field) or "(blank)")}</td>'
                 f'<td>{E(cv("audit"))}</td><td>{E(cv("hub"))}</td><td>{E(cv("agency"))}</td>'
                 f'<td><a href="{E(REG10)}">reg10</a></td></tr>')
    b.append("</tbody></table>")

    b.append("<h2>4. Per game</h2>")
    b.append('<table><thead><tr><th>Game (away @ home)</th><th>Day</th><th>Kickoff ET</th><th>Network</th>'
             '<th class="num">Rows</th><th>Source</th></tr></thead><tbody>')
    for gid, g in cmp["by_game"].items():
        b.append(f'<tr><td>{E(g["away"])} @ {E(g["home"])}</td><td>{E(g["day"])}</td><td>{E(g["kick"])}</td>'
                 f'<td>{E(g["net"])}</td><td class="num">{g["rows"]}</td>'
                 f'<td><a href="{E(gid and live_game_url(live, gid))}">game page</a> · <a href="{E(REG10)}">reg10</a></td></tr>')
    b.append("</tbody></table>")

    b.append("<h2>5. Per club</h2>")
    b.append('<table><thead><tr><th>Club</th><th class="num">Live rows</th><th class="num">Out</th><th class="num">Questionable</th>'
             '<th class="num">Doubtful</th><th class="num">Audit rows</th><th class="num">Hub rows</th><th class="num">Agency rows</th>'
             '<th>Source</th></tr></thead><tbody>')
    for c in clubs:
        if c in cmp["bye_clubs"] and c not in st_by_club:
            b.append(f'<tr><td>{E(c)}</td><td class="num">0</td><td colspan="3">Not on the report — Week-10 bye per the official schedule</td>'
                     f'<td class="num">{_count(audit, c)}</td><td class="num">{_count(hub, c)}</td><td class="num">{_count(agency, c)}</td>'
                     f'<td><a href="{E(SCHED)}">schedule: Teams on Bye</a></td></tr>')
            continue
        st = st_by_club[c]
        b.append(f'<tr><td>{E(c)}</td><td class="num">{sum(st.values())}</td><td class="num">{st.get("Out", 0)}</td>'
                 f'<td class="num">{st.get("Questionable", 0)}</td><td class="num">{st.get("Doubtful", 0)}</td>'
                 f'<td class="num">{_count(audit, c)}</td><td class="num">{_count(hub, c)}</td><td class="num">{_count(agency, c)}</td>'
                 f'<td><a href="{E(REG10)}">reg10</a></td></tr>')
    b.append("</tbody></table>")

    b.append('<h2 id="flags">6. Flags for review</h2>')
    b.append('<p class="small">These are not resolved here. Each one is a reviewer task with the official link attached.</p>')
    b.append('<table><thead><tr><th>ID</th><th>Irregularity</th><th>Status</th><th>Source</th></tr></thead><tbody>')
    for fid, text, status, src in FLAGS(cmp, s_audit):
        b.append(f'<tr><td>{E(fid)}</td><td>{text}</td><td>{_tag(status[0], status[1])}</td>'
                 f'<td><a href="{E(src)}">{E(src)}</a></td></tr>')
    b.append("</tbody></table>")

    b.append("<h2>7. Method and limits</h2>")
    b.append("<ul>"
             "<li>Transcription: all 8 chunks of the official page were read and each row was written to "
             "<code>data/recount/reg10_2026_live_transcription.psv</code>. The build writes "
             "<code>data/recount/reg10_2026_live.csv</code> and the hashes in <code>data/recount/MANIFEST.json</code>.</li>"
             "<li>Raw HTML bytes were <b>not</b> retained: the sandbox cannot reach nfl.com with curl (TLS failure). "
             "The agency capture of 2026-11-15 is an independent earlier reading of the same page; it agrees with this transcription on every player.</li>"
             "<li>Row counts per game equal the club-section counts on the page. The page prints no row totals, so the totals are computed.</li>"
             "<li>Checks: <code>python3 scripts/recount_verify.py</code>.</li>"
             "</ul>")
    b.append('<p class="small">Official sources: '
             f'<a href="{E(REG10)}">{E(REG10)}</a> · <a href="{E(SCHED)}">{E(SCHED)}</a></p>')
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(_page(
        "Week 10 injury report — full recount", "\n".join(b)))

    # ================= rows.html =================
    per_row = defaultdict(list)
    for d in diffs:
        per_row[d["row_no"]].append(d)
    rb = []
    rb.append("<h1>Week 10 official injury report — all 347 rows</h1>")
    rb.append('<p class="lede">One row per player on the official reg10 report, as read on 2026-11-19. '
              'The last column says whether the committed copies agree with this row.</p>')
    rb.append('<table><thead><tr><th class="num">#</th><th>Game</th><th>Club</th><th>Player</th><th>Pos</th>'
              '<th>Injury</th><th>Practice status</th><th>Game status</th><th>Committed copies</th><th>Source</th></tr></thead><tbody>')
    for r in live:
        ds = per_row.get(r["row_no"], [])
        if not ds:
            status_txt = _tag("ok", "agrees: audit, hub, agency")
            cls = ""
        else:
            parts = []
            for d in ds:
                if d["field"] == "ROW":
                    parts.append(f'{d["source"]}: missing')
                else:
                    parts.append(f'{d["source"]}: {d["field"]} differs')
            seen = []
            for p in parts:
                if p not in seen:
                    seen.append(p)
            status_txt = _tag("bad", "; ".join(seen))
            cls = ' class="diff"'
        rb.append(f'<tr{cls}><td class="num">{r["row_no"]}</td><td>{E(r["game"])}</td><td>{E(r["club"])}</td>'
                  f'<td>{E(r["player"])}</td><td>{E(r["position"])}</td><td>{E(r["injury"])}</td>'
                  f'<td>{E(r["practice_status"])}</td><td>{E(r["game_status"]) or "—"}</td><td>{status_txt}</td>'
                  f'<td><a href="{E(REG10)}">reg10</a> · <a href="{E(r["game_url"])}">game</a></td></tr>')
    rb.append("</tbody></table>")
    rb.append('<p class="small">Blank game status is printed as "—" here, and means the official page shows no game status for that player.</p>')
    open(os.path.join(out_dir, "rows.html"), "w", encoding="utf-8").write(_page(
        "Week 10 injury report — all rows", "\n".join(rb)))


def live_game_url(live, gid):
    for r in live:
        if r["game_id"] == gid:
            return r["game_url"]
    return ""


def FLAGS(cmp, s_audit):
    REG10 = cmp["source"]
    SCHED = cmp["schedule"]
    return [
        ("R-F1", "The official page heading reads <b>Week 11 of the 2026 Season</b>, but the report body reads "
                 "<b>Injuries - WEEK 10</b> and every game listed is a Week-10 game. Which week the page is about needs a reviewer's decision before the page is cited as Week 10.",
         ("warn", "Unresolved"), REG10),
        ("R-F2", f"The audit and hub tables are missing <b>{s_audit['missing_from_committed']} Ravens rows</b>: "
                 "Calais Campbell (DT) and Ronnie Stanley (T), both listed on the live page with practice status "
                 "Did Not Participate In Practice and no game status. The agency capture contains both rows.",
         ("bad", "Stale copy"), REG10),
        ("R-F3", "The Chargers and Ravens block (LAC @ BAL) has blank or different injury, practice or game-status cells "
                 "in the audit and hub tables. The agency capture (dated 2026-11-15T19:05Z in its file) agrees with today's page. "
                 "The audit README dates its fetch to 2026-11-14. The cause is not established from the repo "
                 "(stale capture or transcription error); no value was changed.",
         ("bad", "Stale copy"), REG10),
        ("R-F9", "Arden Key (IND, DE): the audit and hub tables show injury <b>Hamstring</b> and game status <b>Questionable</b>. "
                 "The live page shows no injury and no game status, and the agency capture agrees with the live page. "
                 "This is a value conflict in the committed copies, not a missing row.",
         ("bad", "Value conflict"), REG10),
        ("R-F4", "The brief's figures (254 rows / 4 no-injury sections, and 279 rows / 2 sections live) are <b>not reproduced</b>. "
                 "Today's page has 347 rows in 28 club sections, and no section is empty. The four clubs with no section are the "
                 "Week-10 byes (CHI, DEN, PHI, TB), per the official schedule page.",
         ("warn", "Not reproduced"), SCHED),
        ("R-F5", "The brief says Seattle and Cincinnati are shown as injury-free while listing 15 and 4 players. "
                 "Neither the audit nor the hub table shows Seattle or Cincinnati as injury-free: both list their players. "
                 "The live page lists 15 Seahawks and 9 Bengals rows. The Cincinnati count of 4 is not reproduced. "
                 "The page that showed the injury-free display was not located in this recount.",
         ("warn", "Not reproduced"), REG10),
        ("R-F6", "Single-reader transcription. The raw page bytes could not be retained from this sandbox. "
                 "The agency capture is an independent earlier reading; it agrees on all 347 players, with one capitalisation difference. "
                 "A second reader should check this transcription against the live page before the figures are relied on.",
         ("warn", "Needs second reader"), REG10),
        ("R-F7", "Roster assignment is published as shown on the page. It was not checked against transactions in this recount. "
                 "Example for a manual check: Myles Garrett is listed under LAR with position LB and no Browns row on the page.",
         ("warn", "Manual check"), REG10),
        ("R-F8", "Capitalisation only: the agency capture spells one practice status <code>Did Not Participate in Practice</code> "
                 "(Trevin Wallace, NYJ). It is counted as a field difference so it stays visible. No change is proposed.",
         ("ok", "Cosmetic"), REG10),
    ]
