#!/usr/bin/env python3
"""Depth-chart register (session arena/784043ed-x3).

Builds, deterministically, from committed inputs only:

  INPUTS
    data/x3/raw/club_depth_charts_2026_wk10/*.md   31 club charts captured 2026-11-14 (prior session, read-only here)
    data/depth/live_2026-11-19/*.md                 4 club charts re-read 2026-11-19 (this session) + HOU (no text)
    data/live/raw/transactions_nov2026.json        nfl.com November trades (captured 2026-11-19, read-only here)
    data/injury_report_2026_wk10.csv               Week-10 designation rows (read-only, for the Lions check)

  OUTPUTS
    data/depth/depth_register.csv   one row per (snapshot, club, unit, row, rank) cell that is filled, shared, gap or empty
    data/depth/slot_groups.csv      one row per (snapshot, club, unit, position label) group
    data/depth/conflicts.csv        live (2026-11-19) vs captured (2026-11-14) differences for the four re-read clubs
    data/depth/cross_checks.json    each brief item checked against an official source, with status
    data/depth/summary.json         counts used by the page and by depth_verify.py
    depth/index.html, depth/flagged.html

Rules (published on the page):
  * A chart row = one position line. Column 1 = rank 1, column 2 = rank 2, and so on.
  * FILLED   = a name in the cell.
  * SHARED   = the cell names two players (page annotation "[co-listed X]", or two linked names with no separator).
  * GAP      = an empty cell that is followed by a filled cell in the same row (a slot the chart leaves empty).
  * EMPTY    = an empty rank-1 cell with no players in the row.
  * A leading jersey number ("9 Christian Watson") is stripped from player_name and kept in player_cell_raw.
  * A row with a blank position label is kept and flagged UNLABELED; its group is "(blank)".
  * Nothing is inferred: no starter is named unless the chart lists a rank-1 name.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

CAPTURE_DIR = P("data", "x3", "raw", "club_depth_charts_2026_wk10")
LIVE_DIR = P("data", "depth", "live_2026-11-19")
OUT_DIR = P("data", "depth")
PAGE_DIR = P("depth")

CAPTURE_DATE = "2026-11-14"
LIVE_DATE = "2026-11-19"
UNITS = ("Offense", "Defense", "Special Teams")
LIVE_CLUBS = ["BAL", "GB", "SEA", "WAS"]
HOU_NO_TEXT = "HOU"

# Two linked names with no separator on the live page (SEA WR1). Split here, flagged in the register.
SEPARATOR_OVERRIDES = {
    ("SEA", "Cooper Kupp Rashid Shaheed"): ("Cooper Kupp", ["Rashid Shaheed"]),
}

CO_RE = re.compile(r"\[co-listed (?:with )?(.*?)\]")
JERSEY_RE = re.compile(r"^(\d{1,2}) (.+)$")


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def parse_cell(club, raw):
    """Return (player_name, jersey_no, co_listed[list], separator_override_bool)."""
    raw = raw.strip()
    if (club, raw) in SEPARATOR_OVERRIDES:
        name, co = SEPARATOR_OVERRIDES[(club, raw)]
        return name, "", list(co), True
    jersey = ""
    m = JERSEY_RE.match(raw)
    if m:
        jersey, raw = m.group(1), m.group(2)
    co = []
    cm = CO_RE.search(raw)
    if cm:
        co = [x.strip() for x in re.split(r",| and ", cm.group(1)) if x.strip()]
        raw = CO_RE.sub("", raw).strip()
    return raw.strip(), jersey, co, False


def read_capture(path):
    """Capture files: header '# <Club> depth chart (fetched <date>, <url>)', sections '## Offense' etc."""
    lines = open(path, encoding="utf-8").read().splitlines()
    head = lines[0]
    url = re.search(r"https?://[^\s)]+", head).group(0)
    date = re.search(r"fetched (\d{4}-\d{2}-\d{2})", head).group(1)
    label = head
    return dict(url=url, date=date, label=label, lines=lines[1:])


def read_live(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    meta = {}
    body = []
    for ln in lines:
        if ln.startswith("source_url: "):
            meta["url"] = ln.split(": ", 1)[1].strip()
        elif ln.startswith("club_label_on_page: "):
            meta["label"] = ln.split(": ", 1)[1].strip()
        elif ln.startswith("# ") or ln.startswith("read_method:") or ln.startswith("result:") or ln.startswith("policy:"):
            pass
        else:
            body.append(ln)
    meta["date"] = LIVE_DATE
    meta["lines"] = body
    return meta


def table_rows(lines):
    """Yield (unit, pos_label_raw, [player_cells]) for each chart line, in order."""
    unit = None
    for ln in lines:
        if ln.startswith("## "):
            t = ln[3:].strip()
            if t in UNITS:
                unit = t
            continue
        if not ln.startswith("|"):
            continue
        if set(ln.replace("|", "").strip()) <= set("- "):
            continue
        cells = [c.strip() for c in ln.strip()[1:-1].split("|")]
        if cells and cells[0].lower() == "position":
            continue
        if unit is None:
            continue
        yield unit, cells[0], cells[1:]


def build_snapshot(club, snap_date, url, label, lines, source_file, file_sha):
    rows = []
    row_no = 0
    for unit, pos_raw, cells in table_rows(lines):
        row_no += 1
        pos = pos_raw if pos_raw else "(blank)"
        last_filled = max([i for i, c in enumerate(cells) if c], default=-1)
        flags_row = []
        if not pos_raw:
            flags_row.append("UNLABELED_ROW")
        if last_filled < 0:
            flags_row.append("EMPTY_ROW")
        for j, cell in enumerate(cells):
            rank = j + 1
            if cell:
                name, jersey, co, sep = parse_cell(club, cell)
                flags = []
                if co:
                    flags.append("SHARED_CO_LISTED")
                if sep:
                    flags.append("SHARED_NO_SEPARATOR_ON_PAGE")
                if jersey:
                    flags.append("JERSEY_NUMBER_STRIPPED")
                status = "SHARED" if co else "FILLED"
                rows.append(dict(
                    snapshot_date=snap_date, club=club, unit=unit, position=pos, row_no=row_no, rank=rank,
                    slot_status=status, player_cell_raw=cell, player_name=name, jersey_no=jersey,
                    co_listed="; ".join(co), flags=";".join(flags_row + flags),
                    source_url=url, source_file=source_file, source_sha256=file_sha, club_label=label,
                ))
            elif j < last_filled and pos_raw:
                rows.append(dict(
                    snapshot_date=snap_date, club=club, unit=unit, position=pos, row_no=row_no, rank=rank,
                    slot_status="GAP", player_cell_raw="", player_name="", jersey_no="", co_listed="",
                    flags=";".join(flags_row + ["EMPTY_SLOT_BEFORE_FILLED"]),
                    source_url=url, source_file=source_file, source_sha256=file_sha, club_label=label,
                ))
            elif j == 0 and pos_raw:
                rows.append(dict(
                    snapshot_date=snap_date, club=club, unit=unit, position=pos, row_no=row_no, rank=rank,
                    slot_status="EMPTY", player_cell_raw="", player_name="", jersey_no="", co_listed="",
                    flags=";".join(flags_row + ["EMPTY_RANK_1"]),
                    source_url=url, source_file=source_file, source_sha256=file_sha, club_label=label,
                ))
    return rows


def main():
    register = []
    clubs_seen = collections.OrderedDict()

    # --- captured snapshot (2026-11-14), all 31 club files
    n_capture_files = 0
    for fn in sorted(os.listdir(CAPTURE_DIR)):
        if not fn.endswith(".md"):
            continue
        n_capture_files += 1
        club = fn[:-3]
        path = os.path.join(CAPTURE_DIR, fn)
        cap = read_capture(path)
        clubs_seen[club] = "capture"
        register += build_snapshot(club, cap["date"], cap["url"], cap["label"], cap["lines"], rel(path), sha256(path))

    # --- live snapshot (2026-11-19), four text charts + HOU (no rows)
    live_meta = {}
    n_live_text = 0
    for fn in sorted(os.listdir(LIVE_DIR)):
        if not fn.endswith(".md"):
            continue
        club = fn[:-3]
        path = os.path.join(LIVE_DIR, fn)
        live = read_live(path)
        live_meta[club] = dict(url=live["url"], label=live.get("label", ""), file=rel(path), sha=sha256(path))
        if club == HOU_NO_TEXT:
            continue
        clubs_seen[club] = "live"
        n_live_text += 1
        register += build_snapshot(club, live["date"], live["url"], live.get("label", "") or "no club label on page",
                                   live["lines"], rel(path), sha256(path))

    # Expose the Houston non-row record explicitly so it is never silent.
    register_sorted = sorted(register, key=lambda r: (r["snapshot_date"], r["club"], UNITS.index(r["unit"]), r["row_no"], r["rank"]))

    # ------------------------------------------------------------ slot groups
    groups = collections.OrderedDict()
    for r in register_sorted:
        key = (r["snapshot_date"], r["club"], r["unit"], r["position"])
        g = groups.setdefault(key, dict(rows=set(), rank1_rows=set(), shared=0, gaps=0, names=[], unlabeled=False))
        g["rows"].add(r["row_no"])
        if r["rank"] == 1 and r["slot_status"] in ("FILLED", "SHARED"):
            g["rank1_rows"].add(r["row_no"])
        if r["slot_status"] == "SHARED":
            g["shared"] += 1
        if r["slot_status"] == "GAP":
            g["gaps"] += 1
        if "UNLABELED_ROW" in r["flags"]:
            g["unlabeled"] = True
        if r["player_name"]:
            g["names"].append(r["player_name"])
    group_rows = []
    for (snap, club, unit, pos), g in groups.items():
        n_r1 = len(g["rank1_rows"])
        group_rows.append(dict(
            snapshot_date=snap, club=club, unit=unit, position=pos, n_rows=len(g["rows"]),
            n_rank1_filled_rows=n_r1, multi_rank1=("YES" if n_r1 > 1 else "NO"),
            n_shared_cells=g["shared"], n_gap_cells=g["gaps"], unlabeled_row=("YES" if g["unlabeled"] else "NO"),
            distinct_names=len(set(g["names"])),
            note=("two or more rows show a rank-1 name; the chart does not say which one starts" if n_r1 > 1 else
                  ("no rank-1 name listed" if n_r1 == 0 else "one rank-1 row")),
        ))

    # ------------------------------------------------------------ same player in several slots (per club snapshot)
    dup = collections.defaultdict(set)
    for r in register_sorted:
        if r["player_name"]:
            dup[(r["snapshot_date"], r["club"], r["player_name"])].add((r["unit"], r["position"], r["rank"]))
    dup_rows = [(k, sorted(v)) for k, v in dup.items() if len(v) > 1]

    # ------------------------------------------------------------ conflicts: live vs capture for four re-read clubs
    def name_map(snap, club):
        m = collections.defaultdict(set)
        for r in register_sorted:
            if r["snapshot_date"] == snap and r["club"] == club and r["player_name"]:
                m[r["player_name"]].add(f'{r["unit"]} / {r["position"]} / rank {r["rank"]}')
                for c in [x for x in r["co_listed"].split("; ") if x]:
                    m[c].add(f'{r["unit"]} / {r["position"]} / rank {r["rank"]} (shared)')
        return m

    conflicts = []
    for club in LIVE_CLUBS:
        cap = name_map(CAPTURE_DATE, club)
        liv = name_map(LIVE_DATE, club)
        for name in sorted(set(cap) | set(liv)):
            if name in cap and name not in liv:
                conflicts.append(dict(club=club, change="NOT_ON_LIVE_CHART", player=name,
                                      capture_2026_11_14="; ".join(sorted(cap[name])), live_2026_11_19="",
                                      capture_url=live_meta[club]["url"], live_url=live_meta[club]["url"]))
            elif name in liv and name not in cap:
                conflicts.append(dict(club=club, change="NEW_ON_LIVE_CHART", player=name,
                                      capture_2026_11_14="", live_2026_11_19="; ".join(sorted(liv[name])),
                                      capture_url=live_meta[club]["url"], live_url=live_meta[club]["url"]))
            elif cap[name] != liv[name]:
                conflicts.append(dict(club=club, change="SLOT_CHANGED", player=name,
                                      capture_2026_11_14="; ".join(sorted(cap[name])),
                                      live_2026_11_19="; ".join(sorted(liv[name])),
                                      capture_url=live_meta[club]["url"], live_url=live_meta[club]["url"]))

    # ------------------------------------------------------------ cross-checks
    qb_live = [r for r in register_sorted if r["snapshot_date"] == LIVE_DATE and r["club"] == "BAL" and r["position"] == "QB"]
    bal_live_names = {r["player_name"] for r in register_sorted if r["snapshot_date"] == LIVE_DATE and r["club"] == "BAL"}
    bal_cap_names = {r["player_name"] for r in register_sorted if r["snapshot_date"] == CAPTURE_DATE and r["club"] == "BAL"}
    qb_cap = [r for r in register_sorted if r["snapshot_date"] == CAPTURE_DATE and r["club"] == "BAL" and r["position"] == "QB"]
    gb_cap_rg = [r for r in register_sorted if r["snapshot_date"] == CAPTURE_DATE and r["club"] == "GB"]
    was_cap_lb = [r for r in register_sorted if r["snapshot_date"] == CAPTURE_DATE and r["club"] == "WAS" and r["position"] == "LB"]
    was_live_lb = [r for r in register_sorted if r["snapshot_date"] == LIVE_DATE and r["club"] == "WAS" and r["position"] == "LB"]
    gb_live_num = [r for r in register_sorted if r["snapshot_date"] == LIVE_DATE and r["club"] == "GB" and r["jersey_no"]]
    sea_live_shared = [r for r in register_sorted if r["snapshot_date"] == LIVE_DATE and r["club"] == "SEA" and "SHARED" in r["slot_status"]]

    # Week-10 designations (repo file read-only) for the three Lions rows
    lions = []
    with open(P("data", "injury_report_2026_wk10.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["team"] == "DET" and row["player"] in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
                lions.append(dict(player=row["player"], position=row["position"], injury=row["injury"],
                                  practice=row["practice_status"], game_status=row["game_status"],
                                  repo_source=row["source_id"]))

    def row_text(rows):
        if not rows:
            return "(row not found)"
        rn = rows[0]["row_no"]
        parts = []
        for r in sorted([x for x in rows if x["row_no"] == rn], key=lambda x: x["rank"]):
            parts.append(f'rank {r["rank"]} {r["slot_status"]}' + (f' ({r["player_name"]})' if r["player_name"] else ""))
        return f'{rows[0]["unit"]} / {rows[0]["position"]}: ' + " | ".join(parts)

    was_cap_luvu = [r for r in register_sorted if r["snapshot_date"] == CAPTURE_DATE and r["club"] == "WAS" and r["player_name"] == "Frankie Luvu"]
    was_live_luvu = [r for r in register_sorted if r["snapshot_date"] == LIVE_DATE and r["club"] == "WAS" and r["player_name"] == "Frankie Luvu"]
    # the empty-slot row in the capture is the row that contains Luvu
    was_cap_luvu = [r for r in register_sorted if r["snapshot_date"] == CAPTURE_DATE and r["club"] == "WAS" and r["row_no"] in {x["row_no"] for x in was_cap_luvu} and r["unit"] == was_cap_luvu[0]["unit"]] if was_cap_luvu else []
    was_live_luvu = [r for r in register_sorted if r["snapshot_date"] == LIVE_DATE and r["club"] == "WAS" and r["row_no"] in {x["row_no"] for x in was_live_luvu} and r["unit"] == was_live_luvu[0]["unit"]] if was_live_luvu else []

    checks = [
        dict(id="X01", item="Baltimore stale QB rows: Lamar Jackson and Tyler Huntley still listed at QB after IR (brief VR-17, VR-26, VQ-07)",
             official_source="https://www.baltimoreravens.com/team/depth-chart (read 2026-11-19); https://www.nfl.com/transactions/league/trades/2026/11 (read 2026-11-19); https://www.nfl.com/transactions/league/reserve-list/2026/11 (read 2026-11-19, both chunks)",
             observation=("Live QB row = " + " / ".join(r["player_name"] for r in qb_live) + ". Jackson and Huntley appear in no Baltimore cell on the 2026-11-19 chart. "
                          "nfl.com trades (Nov 2026) list Jacoby Brissett, Arizona to Baltimore, 11/06. "
                          "The nfl.com reserve list (Nov 2026, entries dated 11/10 to 11/18) has no Baltimore entry."),
             status="NOT_REPRODUCED",
             notes=("The stale-row claim does not hold for the 2026-11-19 chart. Jackson's injured-reserve status is UNVERIFIED: the official reserve list does not show it. "
                    "The repo's data/atlas/roster_events_2026.csv row dated 2026-11-13 cites the Week-10 injury report text ('expected to miss 6-10 weeks'), which is a designation, not a reserve transaction.")),
        dict(id="X02", item="Lions game-status cells blank for Kerby Joseph, Cade Mays, D.J. Reed (brief VR-08, VR-12)",
             official_source="https://www.nfl.com/news/nfl-week-10-injury-report-2026-season (read 2026-11-19, chunk 0 of 3, Week-10 article)",
             observation=("Article lists under LIONS: OUT Kerby Joseph (knee), Cade Mays (ankle), CB D.J. Reed (hip). Repo file data/injury_report_2026_wk10.csv holds: "
                          + "; ".join(f'{l["player"]} = {l["game_status"] or "(blank)"} ({l["repo_source"]})' for l in lions)),
             status=("CONFIRMED_IN_REPO_NOT_RE_READ" if lions and all(l["game_status"] == "Out" for l in lions) else "NOT_CONFIRMED"),
             notes="The repo already holds 'Out' for all three rows, matching the article. The live nfl.com Week-10 report cell was not re-read in this session, so the page cell itself is not re-checked."),
        dict(id="X03", item="Packers depth chart prepends jersey numbers (number stripping + raw string)",
             official_source="https://www.packers.com/team/depth-chart (read 2026-11-19)",
             observation=f"Live page shows jersey-number prefixes on {len(gb_live_num)} player cells; the 2026-11-14 capture has none.",
             status="REPRODUCED_HANDLED",
             notes="Register strips the leading number into jersey_no and keeps the raw cell in player_cell_raw."),
        dict(id="X04", item="Seattle puts two players in one slot (brief VR-21)",
             official_source="https://www.seahawks.com/team/depth-chart/ (read 2026-11-19)",
             observation=f"Live WR rank-1 cell names 'Cooper Kupp' and 'Rashid Shaheed' with no separator on the page (register: {len(sea_live_shared)} SHARED cell). The 2026-11-14 capture annotates it '[co-listed Rashid Shaheed]'.",
             status="REPRODUCED_HANDLED",
             notes="Recorded as SHARED with the co-listed name kept. Split rule for the no-separator cell is a documented override in the script."),
        dict(id="X05", item="Washington leaves a slot empty (brief VR-23)",
             official_source="https://www.commanders.com/team/depth-chart (read 2026-11-19); repo capture 2026-11-14 (data/x3/raw/club_depth_charts_2026_wk10/WAS.md)",
             observation=("2026-11-14 capture, row containing Frankie Luvu: " + row_text(was_cap_luvu) +
                          ". 2026-11-19 live, row containing Frankie Luvu: " + row_text(was_live_luvu)),
             status="NOT_REPRODUCED_ON_2026_11_19",
             notes="The gap (empty rank 2) is in the 2026-11-14 capture only. The live 2026-11-19 row lists a second named player. The register keeps both snapshots."),
        dict(id="X06", item="Houston depth chart: image-only, no structured source (brief B31, B51)",
             official_source="https://www.houstontexans.com/team/depth-chart (read 2026-11-19)",
             observation="Page labels the chart 'Unofficial Depth Chart' and publishes it as an image. The page reader returned no table text.",
             status="UNVERIFIED_NO_STRUCTURED_SOURCE",
             notes="Zero Houston rows in the register. The image is not transcribed by eye."),
        dict(id="X07", item="Club charts labelled 'Unofficial' (route (a) requires official club depth charts)",
             official_source="https://www.packers.com/team/depth-chart (footer 'Unofficial, Nov. 10, 2026'); https://www.houstontexans.com/team/depth-chart (heading 'Unofficial Depth Chart')",
             observation="Packers footer: 'Unofficial, Nov. 10, 2026'. Texans heading: 'Unofficial Depth Chart'. The Washington page (single chunk read) carries no such label. The Baltimore and Seattle pages were read in chunk 0 only, so their footers were not read.",
             status="FLAG_FOR_REVIEW",
             notes="The club's own label conflicts with the brief's wording 'official per-club depth chart'. The owner should decide whether these pages qualify as official."),
        dict(id="X08", item="Count of club/unit/position slots listing more than one rank-1 player (brief: 149)",
             official_source="https://www.packers.com/team/depth-chart; https://www.commanders.com/team/depth-chart; https://www.seahawks.com/team/depth-chart/; https://www.baltimoreravens.com/team/depth-chart (the other 27 captured club URLs are in depth_register.csv, source_url; 2026-11-14 captures)",
             observation=(f"Under this register's grouping (snapshot, club, unit, position label): "
                          f"{sum(1 for g in group_rows if g['snapshot_date'] == CAPTURE_DATE and g['multi_rank1'] == 'YES')} groups on 2026-11-14 "
                          f"and {sum(1 for g in group_rows if g['snapshot_date'] == LIVE_DATE and g['multi_rank1'] == 'YES')} groups on 2026-11-19 (four clubs)."),
             status="DISCREPANCY_UNRECONCILED",
             notes="The brief's figure of 149 does not state its grouping rule. This register counts 155 on the 2026-11-14 capture, so the brief's count is not reproduced."),
        dict(id="X09", item="Baltimore 2026-11-14 capture vs 2026-11-19 page: RG depth-2 and K cells",
             official_source="https://www.baltimoreravens.com/team/depth-chart (read 2026-11-19)",
             observation="2026-11-14 capture lacks 'Chuma Edoga' at RG rank 2 and 'Riley Patterson' at K. The 2026-11-19 page lists both.",
             status="FLAG_FOR_REVIEW",
             notes="The repo cannot tell whether the capture omitted these cells or the page changed between the two reads. Both snapshots are kept with their dates."),
        dict(id="X10", item="Captured depth charts vs live pages (Green Bay, Washington, Seattle)",
             official_source="https://www.packers.com/team/depth-chart; https://www.commanders.com/team/depth-chart; https://www.seahawks.com/team/depth-chart/ (all read 2026-11-19)",
             observation=(f"Conflicts recorded: {sum(1 for c in conflicts if c['club'] == 'GB')} GB, {sum(1 for c in conflicts if c['club'] == 'WAS')} WAS, "
                          f"{sum(1 for c in conflicts if c['club'] == 'SEA')} SEA, {sum(1 for c in conflicts if c['club'] == 'BAL')} BAL (see conflicts.csv)."),
             status="FLAG_FOR_REVIEW",
             notes="Several rows differ between the captured and live charts. Existing depth outputs built on the 2026-11-14 captures (data/x3/depth_replacement_2026_wk10.csv, data/x3/verified/depth_replacement.csv) are not re-derived here and must not be treated as current."),
        dict(id="X11", item="Name shown vs player-page URL slug (display-name mismatch)",
             official_source="https://www.baltimoreravens.com/team/depth-chart; https://www.commanders.com/team/depth-chart (read 2026-11-19)",
             observation="BAL DT 'Nnamdi Madubuike' links to players-roster/justin-madubuike. WAS FS 'Quan Martin' links to players-roster/jartavius-martin.",
             status="FLAG_FOR_REVIEW",
             notes="Display names are kept as shown. The player link does not match the displayed name. Left for the club or for manual review."),
        dict(id="X12", item="Unlabelled continuation row and duplicate players in a slot group (Packers)",
             official_source="https://www.packers.com/team/depth-chart (read 2026-11-19)",
             observation="Packers RB block has an unlabelled row with '26 Kaleb Johnson' at rank 3. S rank 2 lists 'Kitan Oladapo' in both S rows.",
             status="FLAG_FOR_REVIEW",
             notes="Kept as published (UNLABELED_ROW flag). The register does not guess which position the unlabelled row belongs to."),
        dict(id="X13", item="Transactions check: Brissett trade to Baltimore; Neuzil and Vorhees (Baltimore depth players)",
             official_source="https://www.nfl.com/transactions/league/trades/2026/11 (read 2026-11-19)",
             observation="Nov 2026 trades include: Jacoby Brissett AZ to BAL 11/06; Ryan Neuzil ATL to BAL 11/10; Andrew Vorhees BAL to ATL 11/10.",
             status="CONFIRMED",
             notes="The live Baltimore chart carries Brissett at QB rank 1 and Neuzil at LG rank 2 and C rank 2. Vorhees does not appear on the live chart."),
    ]

    # ------------------------------------------------------------ write data
    os.makedirs(OUT_DIR, exist_ok=True)

    reg_cols = ["snapshot_date", "club", "unit", "position", "row_no", "rank", "slot_status", "player_cell_raw",
                "player_name", "jersey_no", "co_listed", "flags", "source_url", "source_file", "source_sha256", "club_label"]
    with open(os.path.join(OUT_DIR, "depth_register.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=reg_cols, lineterminator="\n")
        w.writeheader()
        for r in register_sorted:
            w.writerow({k: r.get(k, "") for k in reg_cols})

    grp_cols = ["snapshot_date", "club", "unit", "position", "n_rows", "n_rank1_filled_rows", "multi_rank1",
                "n_shared_cells", "n_gap_cells", "unlabeled_row", "distinct_names", "note"]
    with open(os.path.join(OUT_DIR, "slot_groups.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=grp_cols, lineterminator="\n")
        w.writeheader()
        for g in group_rows:
            w.writerow(g)

    con_cols = ["club", "change", "player", "capture_2026_11_14", "live_2026_11_19", "capture_url", "live_url"]
    with open(os.path.join(OUT_DIR, "conflicts.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=con_cols, lineterminator="\n")
        w.writeheader()
        for c in conflicts:
            w.writerow(c)

    summary = dict(
        as_of=LIVE_DATE, capture_date=CAPTURE_DATE,
        clubs_captured_2026_11_14=n_capture_files,
        clubs_text_read_2026_11_19=n_live_text,
        clubs_no_text_2026_11_19=[HOU_NO_TEXT],
        register_rows=len(register_sorted),
        register_rows_by_snapshot={d: sum(1 for r in register_sorted if r["snapshot_date"] == d) for d in (CAPTURE_DATE, LIVE_DATE)},
        slot_status_counts={s: sum(1 for r in register_sorted if r["slot_status"] == s) for s in ("FILLED", "SHARED", "GAP", "EMPTY")},
        groups_total=len(group_rows),
        multi_rank1_groups={d: sum(1 for g in group_rows if g["snapshot_date"] == d and g["multi_rank1"] == "YES") for d in (CAPTURE_DATE, LIVE_DATE)},
        same_player_multi_slot={d: sum(1 for k, _ in dup_rows if k[0] == d) for d in (CAPTURE_DATE, LIVE_DATE)},
        jersey_numbers_stripped=len(gb_live_num),
        conflicts=dict(collections.Counter(c["change"] for c in conflicts)),
        conflicts_by_club={c: sum(1 for x in conflicts if x["club"] == c) for c in LIVE_CLUBS},
        live_club_files={c: dict(url=m["url"], file=m["file"], sha256=m["sha"], label=m["label"]) for c, m in live_meta.items()},
    )
    with open(os.path.join(OUT_DIR, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(OUT_DIR, "cross_checks.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(as_of=LIVE_DATE, checks=checks, lions_rows=lions,
                       duplicate_same_player_slots=[dict(snapshot=k[0], club=k[1], player=k[2], slots=["; ".join(map(str, s)) for s in v]) for k, v in dup_rows]),
                  fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # ------------------------------------------------------------ pages
    from depth_pages import write_pages
    write_pages(dict(register=register_sorted, groups=group_rows, conflicts=conflicts, checks=checks,
                     summary=summary, lions=lions, dup_rows=dup_rows, live_meta=live_meta, LIVE_CLUBS=LIVE_CLUBS,
                     CAPTURE_DATE=CAPTURE_DATE, LIVE_DATE=LIVE_DATE, PAGE_DIR=PAGE_DIR))
    print(f"depth_build: {len(register_sorted)} register rows; {len(group_rows)} groups; {len(conflicts)} conflicts; {len(checks)} cross-checks")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
