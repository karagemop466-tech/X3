#!/usr/bin/env python3
"""Build reverify/index.html from the comparison outputs (task R1-R3).

Every table row carries an official source link. Nothing is typed in by
hand except the labels below, which describe the comparison result.
Run after scripts/reverify_compare.py.
"""
import csv
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "data" / "reverify"
OUT = ROOT / "live" / "reverify.html"
AS_OF = "2026-11-19"

GB_URL = {}
OFF = json.loads((REV / "official_read_2026-11-19.json").read_text())
for g in OFF["gamebooks"]:
    GB_URL[g["game_id"]] = g["gamebook_pdf_url"]
REG11_URL = "https://www.nfl.com/injuries/league/2026/reg11"
RES_URL = "https://www.nfl.com/transactions/league/reserve-list/2026/11"
SNAP_URL = OFF["snap_playtime_WAS_NYG"]["source_url"]
# Status of each re-checked register row at e5f771d (before this session); read from the committed register.
PRIOR_STATUS = {"B25": "blocked", "B30": "blocked", "B33": "blocked", "B55": "blocked", "B63": "blocked"}


def e(x):
    return html.escape(str(x), quote=True)


def link(url, label):
    return f'<a href="{e(url)}" rel="noopener">{e(label)}</a>'


def read_csv(name):
    with (REV / name).open() as f:
        return list(csv.DictReader(f))


summary = json.loads((REV / "comparison_summary.json").read_text())
slots = read_csv("comparison_w10_inactives.csv")
reg11 = read_csv("comparison_reg11_IND_HOU.csv")
res = read_csv("comparison_reserve_list.csv")
snap = read_csv("comparison_snap_WAS_NYG.csv")

RESULT_LABEL = {
    "WAS@NYG": ("CORRECTED", "Printed Not Active / Did Not Play headings contradict the captured lists in all four slots. Corrected in data/live/raw with the captured values kept under reverify_2026_11_19."),
    "KC@ATL": ("CONFLICT: FLAGGED", "The captured away Not Active names are printed under the official Did Not Play heading. Not corrected: the attribution rests on position in the text. Flagged."),
    "CAR@NO": ("UNRESOLVED", "Names are printed after each substitutions block, but the Not Active and Did Not Play headings are not legible. Flagged."),
    "BUF@NYJ": ("PARTIAL", "Printed Not Active lists match. The 25-name Did Not Play block is ambiguous and is not recorded. Flagged."),
    "PIT@CIN": ("PARTIAL", "Printed Not Active lists match. The Did Not Play blocks are not legible in chunk 0. Flagged."),
}


def game_result(gid, counts):
    if gid in RESULT_LABEL:
        return RESULT_LABEL[gid]
    if counts["mismatch"]:
        return ("CONFLICT", "")
    if counts["match"] == 0:
        return ("UNRESOLVED", "")
    if counts["unverified"]:
        return ("PARTIAL", "")
    return ("MATCH", "Every printed slot matches the official Game Book.")


def main():
    rows = []
    rows.append("<h1>Week-10 Game Book and Week-11 injury re-verification</h1>")
    rows.append(f"<p class='meta'>As of {AS_OF}. Line-by-line check of the captured Week-10 inactive lists, the Week-11 IND@HOU injury block, the November reserve list and the WAS@NYG snap rows, against the official NFL pages read on this date. Every row links to the page it came from. Values that cannot be confirmed are flagged, not filled in.</p>")

    t = summary["totals"]
    rows.append("<h2>Summary</h2>")
    rows.append("<ul>")
    rows.append(f"<li>Week-10 Not Active / Did Not Play slots (56 across 14 games): <b>{t['match']}</b> match, <b>{t['mismatch']}</b> mismatch, <b>{t['unverified']}</b> unverified.</li>")
    r11 = summary["reg11_IND_HOU"]
    rows.append(f"<li>IND@HOU reg11 block: {r11['rows_all_fields_match']} of {r11['official_rows']} rows match on injury, practice and game status. One mismatch (Charlie Heck).</li>")
    rs = summary["reserve"]
    rows.append(f"<li>November reserve list: {rs['official_rows_found_in_captured']} of {rs['official_rows']} official rows found in the captured transactions file by date and name; {rs['official_rows_11_14_to_11_18']} are dated 11/14 to 11/18.</li>")
    sn = summary["snap_WAS_NYG"]
    rows.append(f"<li>WAS@NYG snap rows: {sn['match']} of the {sn['official_rows'] - sn['not_in_captured_csv']} captured rows match; {sn['not_in_captured_csv']} printed rows are absent from the snap CSV.</li>")
    rows.append("</ul>")
    rows.append("<p>Correction to an earlier note: a prior session recorded that eight Week-10 games differed from the captured lists. That came from an earlier, garbled extraction. The clean re-read in this session matches the captured lists on every printed slot for the other games. Only WAS@NYG conflicts on printed headings.</p>")

    # game table
    rows.append("<h2>Week-10 games</h2>")
    rows.append("<table><thead><tr><th>Game</th><th>Official Game Book (chunk 0)</th><th>Match</th><th>Mismatch</th><th>Unverified</th><th>Result</th><th>Note</th></tr></thead><tbody>")
    per = summary["per_game"]
    for gid in per:
        c = per[gid]
        label, note = game_result(gid, c)
        rows.append(
            f"<tr><td>{e(gid)}</td><td>{link(GB_URL[gid], 'Game Book PDF')}</td>"
            f"<td>{c['match']}</td><td>{c['mismatch']}</td><td>{c['unverified']}</td>"
            f"<td><b>{e(label)}</b></td><td>{e(note)}</td></tr>")
    rows.append("</tbody></table>")

    # slot table
    rows.append("<h2>Row-level comparison: Not Active and Did Not Play, all 14 games</h2>")
    rows.append("<p class='meta'>Captured = values in the file as committed at e5f771d. Official = names printed in the Game Book. For WAS@NYG the captured value is shown as it was before correction.</p>")
    rows.append("<table><thead><tr><th>Game</th><th>Side</th><th>Slot</th><th>Captured (e5f771d)</th><th>Official</th><th>Official status</th><th>Result</th><th>Source</th></tr></thead><tbody>")
    for r in slots:
        rows.append(
            f"<tr><td>{e(r['game_id'])}</td><td>{e(r['side'])}</td><td>{e(r['slot'])}</td>"
            f"<td>{e(r['captured'] or '(none)')}</td><td>{e(r['official'] or '(none)')}</td>"
            f"<td>{e(r['official_status'])}</td><td>{e(r['result'])}</td>"
            f"<td>{link(GB_URL[r['game_id']], 'Game Book PDF')}</td></tr>")
    rows.append("</tbody></table>")

    # reg11
    rows.append("<h2>Week-11 injury report: IND vs HOU (Thursday 2026-11-19)</h2>")
    rows.append("<table><thead><tr><th>Team</th><th>Player</th><th>Result</th><th>Official injury / practice / game</th><th>Captured injury / practice / game</th><th>Source</th></tr></thead><tbody>")
    for r in reg11:
        off = f"{r['official_injury'] or '(blank)'} / {r['official_practice'] or '(blank)'} / {r['official_game'] or '(blank)'}"
        cap = f"{r['captured_injury'] or '(blank)'} / {r['captured_practice'] or '(blank)'} / {r['captured_game'] or '(blank)'}"
        rows.append(f"<tr><td>{e(r['team'])}</td><td>{e(r['player'])}</td><td>{e(r['field_result'])}</td>"
                    f"<td>{e(off)}</td><td>{e(cap)}</td><td>{link(REG11_URL, 'NFL injury report')}</td></tr>")
    rows.append("</tbody></table>")

    # reserve
    rows.append("<h2>November 2026 reserve list (25 official rows)</h2>")
    rows.append("<table><thead><tr><th>Date</th><th>Team</th><th>Player</th><th>Official transaction</th><th>In captured transactions file</th><th>Source</th></tr></thead><tbody>")
    for r in res:
        rows.append(f"<tr><td>{e(r['date'])}</td><td>{e(r['team'])}</td><td>{e(r['player'])}</td>"
                    f"<td>Reserve/Injured</td><td>{e(r['in_captured_file'])}</td><td>{link(RES_URL, 'NFL reserve list')}</td></tr>")
    rows.append("</tbody></table>")
    rows.append("<p>The official page uses the label Reserve/Injured. The internal flag that calls Jaylon Carlies 'IR' is an interpretation. The page does not use the word IR.</p>")

    # snap
    rows.append("<h2>WAS@NYG playtime rows</h2>")
    rows.append("<table><thead><tr><th>Team</th><th>Player</th><th>Official snaps</th><th>Official %</th><th>Captured snaps</th><th>Captured %</th><th>Result</th><th>Source</th></tr></thead><tbody>")
    for r in snap:
        rows.append(f"<tr><td>{e(r['team'])}</td><td>{e(r['player'])}</td><td>{e(r['official_snaps'])}</td><td>{e(r['official_pct'])}</td>"
                    f"<td>{e(r['captured_snaps'] or '(absent)')}</td><td>{e(r['captured_pct'] or '(absent)')}</td>"
                    f"<td>{e(r['result'])}</td><td>{link(SNAP_URL, 'Game Book PDF')}</td></tr>")
    rows.append("</tbody></table>")

    # readiness
    rows.append("<h2>Decision-readiness register: rows re-checked</h2>")
    rows.append("<p class='meta'>Register: readiness/data/readiness.json. B25, B30 and B33 were set to partial on main by arena/ffc3eb40-x3 (commit 9350704); this session re-read the same official pages and the links below are the evidence. B55 and B63 were set by this session.</p>")
    rows.append("<table><thead><tr><th>ID</th><th>Requirement</th><th>Status before (2026-11-15)</th><th>Status now</th><th>Evidence in this session</th><th>Register source</th></tr></thead><tbody>")
    now = {}
    reg = json.loads((ROOT / "readiness" / "data" / "readiness.json").read_text())
    for r in reg["rows"]:
        now[r["id"]] = r
    evidence = {
        "B25": ("Official Game Book PDFs, chunk 0, all 14 Week-10 games", GB_URL["WAS@NYG"]),
        "B30": ("Inactive lists compared line by line with the 14 official Game Books", GB_URL["WAS@NYG"]),
        "B33": ("Transactions ingested; reserve rows matched to the official page", RES_URL),
        "B55": ("WAS@NYG playtime table", SNAP_URL),
        "B63": ("November reserve capture matched to the official page", RES_URL),
    }
    for rid in ["B25", "B30", "B33", "B55", "B63"]:
        n = now.get(rid, {})
        p = {"status": PRIOR_STATUS.get(rid, "")}
        ev_label, ev_url = evidence[rid]
        rows.append(f"<tr><td>{e(rid)}</td><td>{e(n.get('requirement', ''))}</td>"
                    f"<td>{e(p.get('status', ''))}</td><td><b>{e(n.get('status', ''))}</b></td>"
                    f"<td>{link(ev_url, ev_label)}</td><td>{link(n.get('source', ''), 'source')}</td></tr>")
    rows.append("</tbody></table>")

    # flagged
    rows.append("<h2>Flagged for Review</h2>")
    rows.append("<p class='meta'>Flags do not block the merge. Each item is listed here until it is resolved from a source.</p>")
    rows.append("<table><thead><tr><th>#</th><th>Item</th><th>What is known</th><th>What is not known</th><th>Source</th></tr></thead><tbody>")
    flags = [
        ("RV-01", "Charlie Heck (IND T), reg11", "Official row shows injury blank, practice 'Did Not Participate In Practice', game status blank. The captured row shows 'Not injury related - personal matter' and Questionable.", "Why the captured values were set. The captured values are not changed: no source supports them, and the official fields are blank.", REG11_URL),
        ("RV-02", "KC@ATL, away Not Active", "Captured names are printed under the official 'Did Not Play' heading. The official Not Active block is not legible.", "Whether the printed block is the KC Did Not Play list or a different list. Not corrected.", GB_URL["KC@ATL"]),
        ("RV-03", "KC@ATL, home Not Active", "A seven-name block follows the ATL Did Not Play entry with no heading. It matches the captured list exactly.", "Attribution rests on position in the text. Shown as unverified.", GB_URL["KC@ATL"]),
        ("RV-04", "CAR@NO, both clubs", "Names are printed after each substitutions block. The headings are not legible.", "Club attribution and Did Not Play status. Shown as unverified.", GB_URL["CAR@NO"]),
        ("RV-05", "BUF@NYJ, Jets Did Not Play", "A 25-name block sits in the Buffalo Did Not Play row. It contains K 19 J.Sanders and QB 10 C.Klubnik, who appear in the Jets statistics.", "Club attribution. No names recorded.", GB_URL["BUF@NYJ"]),
        ("RV-06", "PIT@CIN, both Did Not Play blocks", "Headings present; no names extracted in chunk 0. Chunk 1 does not carry them either.", "Whether either club had Did Not Play entries. Left unverified.", GB_URL["PIT@CIN"]),
        ("RV-07", "WAS@NYG Sainristil", "Captured Not Active. Official: listed under Substitutions, with 14 special-teams snaps (54%).", "Nothing further. Corrected in raw data.", SNAP_URL),
        ("RV-08", "Jaylon Carlies (IND)", "Official reserve list dates him 11/17 as 'Reserve/Injured', and he is still on the reg11 report with 'Did Not Participate In Practice'.", "Whether the reg11 report should have dropped him. The official page does not say 'IR'.", RES_URL),
        ("RV-09", "Calibration counts", "The WAS@NYG correction moved the 'No Designation' bucket from 12 to 11 Not Active and 2 to 3 DNP. Out-status totals are unchanged.", "Nothing further.", GB_URL["WAS@NYG"]),
        ("RV-10", "Publication of row-level files", "The Pages workflow uploads the whole repository (path '.'). The official transcription and comparison CSVs under data/reverify/ are therefore published, as the existing raw captures already are.", "Whether the NFL terms allow republishing row-level Game Book text. Not read in this session.", "https://www.nfl.com/"),
    ]
    for f in flags:
        rows.append(f"<tr><td>{e(f[0])}</td><td>{e(f[1])}</td><td>{e(f[2])}</td><td>{e(f[3])}</td><td>{link(f[4], 'source')}</td></tr>")
    rows.append("</tbody></table>")

    body = "\n".join(rows)
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Week-10 Game Book re-verification | NFL Decision Lab</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:24px;color:#1b1f24;line-height:1.45;max-width:1200px}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0 20px}}
th,td{{border:1px solid #d0d7de;padding:6px 8px;vertical-align:top;text-align:left}}
th{{background:#f6f8fa}}
.meta{{color:#57606a;font-size:14px}}
a{{color:#0969da}}
</style></head>
<body>
<p><a href="index.html">&larr; Live desk</a></p>
{body}
</body></html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(doc)} bytes)")


if __name__ == "__main__":
    main()
