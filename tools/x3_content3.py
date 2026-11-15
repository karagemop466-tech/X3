#!/usr/bin/env python3
"""X3 hub extension - session arena/c0176769-x3.

Adds to the canonical hub, through the same hooks used by tools/x3_content2.py:

  readiness        decision-readiness register: one row per requirement of the brief
  snapshots        clock-timed official injury reads and the delta between them
  change-our-mind  two-sided decision rule (keep / demote) for every registered strategy
  landing block    the same readiness table, shown on the root landing page
  NEW_FLAGS        F-60 .. F-67 appended to the flagged-for-review register

Inputs are plain CSVs in data/hub/ (readiness.csv, injury_snapshots.csv,
injury_delta_2026-11-15.csv, change_our_mind.csv). Every number on these pages is
counted from those files at build time; nothing is typed in by hand.
"""
from __future__ import annotations

import csv
import os
from collections import Counter

import x3_content2 as X2  # helpers (esc, badge, link, table) are registered by build_hub

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "hub")
OFFICIAL_INJ = "https://www.nfl.com/injuries/league/2026/reg10"
REPO = "https://github.com/karagemop466-tech/X3/blob/main/"


def _csv(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _h():
    return X2.H["esc"], X2.H["badge"], X2.H["link"], X2.H["table"]


# status word in the register -> badge word already defined by the hub
STATUS_BADGE = {"DONE": "PASS", "PARTIAL": "PARTIAL", "BLOCKED": "BLOCKED",
                "NOT STARTED": "NOT RUN", "REJECTED": "REJECTED"}
STATUS_MEANING = {
    "DONE": "Implemented in the repository and visible on a page",
    "PARTIAL": "Part of the requirement exists; the gap is named in the row",
    "BLOCKED": "Cannot be done until the gate in the row is cleared",
    "NOT STARTED": "Not started; the number that would clear it is stated",
    "REJECTED": "Rejected by policy; recorded so it is not proposed again",
}

NAV_EXTRA = [
    ("readiness", "Decision readiness", "One row per brief requirement: status, gate, number that clears it"),
    ("snapshots", "Injury snapshots", "Clock-timed official reads and the delta between them"),
    ("change-our-mind", "Change our mind", "Two-sided decision rule for every registered strategy"),
]

NEW_FLAGS = [
    ("F-60", "HIGH", "Injury data",
     "Brief figures not reproduced. The brief quotes a published Week-10 table of 254 rows with 4 no-injury "
     "sections against 279 rows and 2 sections live, and says Seattle (15) and Cincinnati (4) show as injury-free. "
     "The official page read on 2026-11-15 has 347 rows across 28 clubs and no club without a listed player; "
     "Seattle lists 15 and Cincinnati lists 9 on both the 2026-11-14 table and the live read. "
     "No read in this repository produces 254 or 279 rows.",
     OFFICIAL_INJ, "Owner: confirm which page the brief quoted (an earlier week or a cached copy?)"),
    ("F-61", "HIGH", "Market data",
     "Market prices are not official. The 548 CLOSE rows in data/x3/price_snapshots_2026.csv come from PFF "
     "through nflverse and are labelled MARKET-3P in the file. The site rule is official sources only, so every "
     "market-based figure stays third-party until the price-data policy is decided. The file holds 0 OPEN rows.",
     REPO + "data/x3/price_snapshots_2026.csv", "Owner: decide the price-data policy (Q-01)"),
    ("F-62", "MEDIUM", "Results",
     "Game count disagrees with the brief. The brief refers to a 136-game log; the verified results feed holds "
     "137 FINAL games (272 games in total). No single source reconciles 136 with 137.",
     REPO + "data/x3/results_feed_2026.csv", "Owner: reconcile the count before the backtest corpus is fixed"),
    ("F-63", "MEDIUM", "Injury data",
     "The canonical Week-10 table is the 2026-11-14 read (345 rows). The 2026-11-15 read (347 rows) differs in "
     "34 delta rows: 32 field changes across 16 players (13 LAC, 2 BAL, 1 IND) and 2 Ravens rows added "
     "(Campbell, Stanley). The source does not state why a designation changed; the delta does not infer it.",
     REPO + "data/hub/injury_delta_2026-11-15.csv", "Owner: decide whether to re-base the hub on the 2026-11-15 read"),
    ("F-64", "HIGH", "Reserve list",
     "Reserve and injured-reserve lists are not captured, so a player absent from the report cannot be read as "
     "available. Official NFL headlines seen on the 2026-11-15 injury page name IR moves, including the Dolphins "
     "placing QB Malik Willis on injured reserve. Those articles were not read in full and nothing is inferred from them.",
     "https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start",
     "Owner: add an official reserve-list source"),
    ("F-65", "MEDIUM", "Capture",
     "Scheduled capture added. snapshots/manifest.csv is written every 6 hours from main; the first scheduled run "
     "is not yet confirmed. Raw HTML is kept as a workflow artifact (90-day retention), not in the Pages tree, because "
     "the terms of use for raw NFL pages have not been reviewed.",
     REPO + ".github/workflows/injury-snapshot.yml", "Owner: review the terms of use; confirm the first run"),
    ("F-66", "MEDIUM", "Depth",
     "The Texans depth chart is published as an image and remains unparsed. The Packers jersey-prefix handling was "
     "not re-verified in this session. Both stay open until an authorised structured source or a re-run confirms them.",
     REPO + "hub/depth.html", "Owner: choose an authorised structured source for the Texans chart"),
    ("F-67", "LOW", "Process",
     "The site has many parallel trees (desk, ops, origin, signals, council, ledger, x3lab, dashboard, "
     "verification-hub, archive) and COORDINATION.md runs to 2,600+ lines. This session added pages to the hub "
     "only; the other trees are unchanged and not consolidated.",
     REPO + "COORDINATION.md", "Owner: decide whether to consolidate the trees"),
    ("F-68", "MEDIUM", "Process",
     "Duplicate flag IDs. F-24, F-25, F-26 and F-27 are each defined twice in the flag register: once in "
     "tools/x3_content.py (FLAGS2) and once in tools/x3_content2.py (NEW_FLAGS). Both copies were on main "
     "before this session. The hub verifier accepts the ID but a reader cannot tell which entry is meant. "
     "Fix: renumber one copy in the owning session; this session did not edit either shared file.",
     REPO + "tools/x3_content2.py", "Owner: the session that owns tools/x3_content.py renumbers one copy"),
]


def p_readiness():
    esc, badge, link, table = _h()
    rows = _csv("readiness.csv")
    counts = Counter(r["status"] for r in rows)
    summary = table(["Status", "Requirements", "What it means", "Source"],
                    [[badge(STATUS_BADGE[s]), str(counts.get(s, 0)), esc(STATUS_MEANING[s]),
                      link(REPO + "data/hub/readiness.csv", "register (CSV)")]
                     for s in ["DONE", "PARTIAL", "BLOCKED", "NOT STARTED", "REJECTED"]], tid="rdy-sum")
    body_rows = []
    for r in rows:
        body_rows.append([f"<b>{esc(r['id'])}</b>", esc(r["area"]), esc(r["requirement"]),
                          badge(STATUS_BADGE.get(r["status"], r["status"])), esc(r["blocking_gate"]),
                          esc(r["number_that_clears_it"]),
                          f"{link(r['evidence_url'], 'source')}<br><span class=\"note\">{esc(r['evidence_note'])}</span>"])
    main = table(["ID", "Area", "Requirement", "Status", "Gate that blocks it", "Number that clears it", "Source"],
                 body_rows, tid="readiness")
    intro = ("One row per requirement in the project brief, as it stands in the repository today. A blocked row "
             "names the gate that stops it and the number that would clear it. Every row links to the page, "
             "file or official source that supports its status.")
    body = f"{summary}\n{main}"
    return "readiness", "Decision readiness", intro, body


def p_snapshots():
    esc, badge, link, table = _h()
    snaps = _csv("injury_snapshots.csv")
    delta = _csv("injury_delta_2026-11-15.csv")
    live = [s for s in snaps if s["snapshot_id"].endswith("LIVE")][0]
    base = [s for s in snaps if not s["snapshot_id"].endswith("LIVE")][0]
    n_changed = sum(1 for r in delta if r["change"] == "changed")
    n_added = sum(1 for r in delta if r["change"] == "added")
    n_removed = sum(1 for r in delta if r["change"] == "removed")
    ledger = table(["Snapshot", "Read (UTC)", "Source", "Method", "Rows", "Clubs", "Out", "Doubtful",
                    "Questionable", "Blank", "Table SHA-256 (first 16)"],
                   [[esc(s["snapshot_id"]), esc(s["read_utc"]), link(s["source_url"], "nfl.com injury report"),
                     esc(s["method"]), esc(s["rows"]), esc(s["clubs"]), esc(s["out"]), esc(s["doubtful"]),
                     esc(s["questionable"]), esc(s["blank_status"]), f"<code>{esc(s['sha256_of_table'][:16])}</code>"]
                    for s in (base, live)], tid="snap-ledger")
    src_delta = link(REPO + "data/hub/injury_delta_2026-11-15.csv", "delta (CSV)")
    headline = table(["Measure", "Value", "Source"], [
        ["Rows in the 2026-11-14 table", esc(base["rows"]), link(OFFICIAL_INJ, "nfl.com")],
        ["Rows in the 2026-11-15 read", esc(live["rows"]), link(OFFICIAL_INJ, "nfl.com")],
        ["Changed rows (field-level)", str(n_changed), src_delta],
        ["Rows added / removed", f"{n_added} added / {n_removed} removed", src_delta],
        ["Teams with any change", esc(str(len({r['team'] for r in delta}))), src_delta],
    ], tid="snap-head")
    delta_rows = [[esc(r["team"]), esc(r["player"]), esc(r["change"]), esc(r["field"]),
                   esc(r["snapshot_2026_11_14"]), esc(r["snapshot_2026_11_15"]),
                   link(r["source_url"], "nfl.com")] for r in delta]
    delta_tbl = table(["Team", "Player", "Change", "Field", "2026-11-14 table", "2026-11-15 read", "Source"],
                      delta_rows, tid="snap-delta")
    brief = table(["Claim in the brief", "What the official page shows", "Status here", "Source"], [
        ["Published table of 254 rows", "347 rows on the 2026-11-15 read; 345 in the 2026-11-14 table",
         "NOT REPRODUCED (flag F-60)", link(OFFICIAL_INJ, "nfl.com")],
        ["Live page has 279 rows and 2 no-injury sections", "All 28 clubs list at least one player",
         "NOT REPRODUCED (flag F-60)", link(OFFICIAL_INJ, "nfl.com")],
        ["Seattle shown injury-free while listing 15", "Seattle lists 15 players on both reads",
         "Count confirmed; display not re-checked", link(OFFICIAL_INJ, "nfl.com")],
        ["Cincinnati listing 4 players", "Cincinnati lists 9 players on both reads",
         "NOT REPRODUCED (flag F-60)", link(OFFICIAL_INJ, "nfl.com")],
        ["Lions Joseph, Mays and Reed have blank game status", "All three are Out on both reads",
         "CONFIRMED on both reads", link(OFFICIAL_INJ, "nfl.com")],
        ["Ravens: 8 rows listed", "10 rows on the live read (Campbell and Stanley added)",
         "Corrected in the delta (flag F-63)", link(OFFICIAL_INJ, "nfl.com")],
    ], tid="snap-brief")
    intro = ("Every injury-report read is kept with its clock time and source, and the difference between reads is "
             "published, never the level alone. Two reads exist so far; the scheduled workflow adds one every "
             "6 hours. The live read was transcribed row by row from all eight pages of the official report.")
    body = f"<h2>Reads</h2>\n{ledger}\n<h2>Headline delta</h2>\n{headline}\n<h2>Brief claims checked against the official page</h2>\n{brief}\n<h2>Row-level delta, 2026-11-14 to 2026-11-15</h2>\n{delta_tbl}"
    return "snapshots", "Injury snapshots and delta", intro, body


def p_change():
    esc, badge, link, table = _h()
    rows = _csv("change_our_mind.csv")
    body_rows = [[f"<b>{esc(r['strategy_id'])}</b>", esc(r["strategy"]), esc(r["keep_or_promote_if"]),
                  esc(r["demote_to_paper_if"]), esc(r["gate_refs"]), link(r["evidence_url"], "gate page")]
                 for r in rows]
    main = table(["ID", "Strategy", "Keep or promote if", "Demote to paper if", "Gate references", "Source"],
                 body_rows, tid="change")
    intro = ("Every registered strategy carries two sides: what would make us keep or promote it, and what would send "
             "it back to paper. These are pre-registered decision rules, not results. None of them has been met or failed "
             "because no strategy has settled bets.")
    return "change-our-mind", "What would change our mind", intro, main


PAGES = [p_readiness, p_snapshots, p_change]


def landing_block():
    """Readiness table for the root landing page (same rows as hub/readiness.html)."""
    esc, badge, link, table = _h()
    rows = _csv("readiness.csv")
    counts = Counter(r["status"] for r in rows)
    chips = " &middot; ".join(
        f"{badge(STATUS_BADGE[s])} {counts.get(s, 0)}" for s in ["DONE", "PARTIAL", "BLOCKED", "NOT STARTED", "REJECTED"])
    body_rows = [[f"<b>{esc(r['id'])}</b>", esc(r["requirement"]), badge(STATUS_BADGE.get(r["status"], r["status"])),
                  esc(r["blocking_gate"]), esc(r["number_that_clears_it"]), link(r["evidence_url"], "source")]
                 for r in rows]
    tbl = table(["ID", "Requirement", "Status", "Gate that blocks it", "Number that clears it", "Source"],
                body_rows, tid="landing-readiness")
    return (f'<section class="callout" id="decision-readiness" style="margin-top:22px">'
            f'<h2>Decision readiness - one row per requirement</h2>'
            f'<p>{len(rows)} requirements from the brief. {chips}. The full register is at '
            f'<a href="hub/readiness.html"><b>hub/readiness.html</b></a>; the injury delta at '
            f'<a href="hub/snapshots.html"><b>hub/snapshots.html</b></a>.</p>{tbl}</section>')
