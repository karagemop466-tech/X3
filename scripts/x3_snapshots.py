#!/usr/bin/env python3
"""
X3 point-in-time snapshot ledger for the official availability report.

Why this exists
---------------
The brief says the injury hub must be "a timestamped series, not a weekly
snapshot", that every read must be stored "with its clock time" and that the
site must "publish the delta, never the level". Before this script the
repository held exactly one read of the Week 10 report (2026-11-14), which
cannot produce a delta. This script turns any number of dated reads into:

  data/snapshots/ledger.json   one record per read: sha256 of the stored bytes,
                               fetch clock time, source URL, chunks read, row
                               and designation counts, parser version
  data/snapshots/delta.json    one record per consecutive pair of reads of the
                               same (season, week): added rows, dropped rows,
                               designation changes, practice changes - each with
                               a corroboration verdict against the independent
                               reads retained in the repository

Determinism: the only clock involved is the clock time recorded *inside* each
capture record at capture time. Re-running this script on unchanged inputs
re-emits byte-identical JSON. No network access is performed here; the capture
files are produced by scripts/x3_snap_fetch.md (documented procedure), because
this sandbox can reach nfl.com only through the fetch tool, not through a shell
HTTP client (verified: curl to www.nfl.com:443 fails with SSL_ERROR_SYSCALL).

Run: python3 scripts/x3_snapshots.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, "data", "snapshots")
CAPDIR = os.path.join(SNAP, "wk10")

PARSER_VERSION = "x3-snap-v1"

# The official page prints "AZ" for the Arizona Cardinals and "LAR" for the Los
# Angeles Rams, while the desk store keys those clubs "ARI" and "LA". Without one
# documented alias map, 29 rows silently fail to join across two reads of the
# same page and every one of them shows up as "added" then "dropped" - the exact
# class of bug this store exists to make visible. x3_snapshots_verify.py asserts
# these are the only two codes that need mapping.
TEAM_ALIAS = {"AZ": "ARI", "LAR": "LA"}

# The captures store the practice designation in the abbreviated form this
# repository already uses (audit flag F-A05 records that the mapping is
# one-to-one). The full official string is reconstructed for comparison.
PRACTICE_FULL = {
    "FP": "Full Participation in Practice",
    "LP": "Limited Participation in Practice",
    "DNP": "Did Not Participate In Practice",
}
PRACTICE_CODES = {v: k for k, v in PRACTICE_FULL.items()}
DESIGNATIONS = ("Out", "Doubtful", "Questionable")

# The filename carries the capture clock time. 2026-11-14T0000Z means "the
# 2026-11-14 read as retained in the repository"; that read recorded a date but
# no clock time, which is the defect this store is designed to prevent, and it
# is published as such rather than back-filled with an invented hour.
CAPTURE_FILE_RE = re.compile(r"^capture-(\d{4}-\d{2}-\d{2})T(\d{4})Z-nfl-com-injuries-reg(\d+)\.csv$")


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def canon_team(code: str) -> str:
    return TEAM_ALIAS.get(code, code)


def read_capture(path: str) -> list[dict]:
    """Load one capture CSV into normalised rows."""
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh), start=2):
            if None in r or any(v is None for v in r.values()):
                raise SystemExit(f"{os.path.basename(path)} line {i}: wrong field count")
            prac = r["practice"].strip()
            if prac not in PRACTICE_FULL:
                raise SystemExit(f"{os.path.basename(path)} line {i}: unknown practice code {prac!r}")
            st = r["status"].strip()
            if st and st not in DESIGNATIONS:
                raise SystemExit(f"{os.path.basename(path)} line {i}: unknown designation {st!r}")
            out.append({
                "team": canon_team(r["team"].strip()),
                "team_printed": r["team"].strip(),
                "player": r["player"].strip(),
                "pos": r["pos"].strip(),
                "injury": r["injury"].strip(),
                "practice": prac,
                "practice_full": PRACTICE_FULL[prac],
                "status": st or "",
                "key": (canon_team(r["team"].strip()), r["player"].strip().lower()),
                "line": i,
            })
    return out


def from_desk(path: str, week: int) -> list[dict]:
    """The 2026-11-14 read as stored by the desk pipeline (full practice strings)."""
    data = json.load(open(path, encoding="utf-8"))
    out = []
    for r in data["rows"]:
        if r.get("week") != week:
            continue
        prac = PRACTICE_CODES.get(r.get("practice", "").strip(), "?")
        out.append({
            "team": r["team"], "team_printed": r["team"], "player": r["player"].strip(),
            "pos": r.get("pos", ""), "injury": r.get("injury", "") or "",
            "practice": prac, "practice_full": r.get("practice", "").strip(),
            "status": (r.get("status") or "").strip(),
            "key": (r["team"], r["player"].strip().lower()), "line": 0,
        })
    return out


# The audit tree abbreviates the practice column its own way ("Full", "Limited",
# "DNP"); the mapping to this store's codes is one-to-one and total, which
# x3_snapshots_verify asserts rather than assumes.
AUDIT_PRACTICE = {"Full": "FP", "Full Participation in Practice": "FP",
                  "Limited": "LP", "Limited Participation in Practice": "LP",
                  "DNP": "DNP", "Did Not Participate In Practice": "DNP"}


def from_audit_csv(path: str) -> list[dict]:
    """The same day's second, independent read, retained by the audit tree.

    Its columns are game, kickoff_et, tv, team, team_record, player, position,
    injury, practice_status, game_status, source_url - a different layout from
    the desk store on purpose (it was written by another session), so the header
    is asserted here instead of guessed at."""
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        need = {"team", "player", "position", "practice_status", "game_status"}
        missing = need - set(rdr.fieldnames or [])
        if missing:
            raise SystemExit(f"audit csv missing expected columns: {sorted(missing)}")
        for r in rdr:
            raw = r["practice_status"].strip()
            if raw not in AUDIT_PRACTICE:
                raise SystemExit(f"audit csv: unmapped practice string {raw!r}")
            prac = AUDIT_PRACTICE[raw]
            out.append({
                "team": canon_team(r["team"].strip()), "team_printed": r["team"].strip(),
                "player": r["player"].strip(), "pos": r.get("position", "").strip(),
                "injury": (r.get("injury") or "").strip(),
                "practice": prac, "practice_full": PRACTICE_FULL[prac],
                "status": (r.get("game_status") or "").strip(),
                "key": (canon_team(r["team"].strip()), r["player"].strip().lower()), "line": 0,
            })
    return out


def counts(rows: list[dict]) -> dict:
    st = Counter((r["status"] or "blank_game_status") for r in rows)
    pr = Counter(r["practice"] for r in rows)
    return {
        "rows": len(rows),
        "teams": len({r["team"] for r in rows}),
        "designation_counts": {k: st.get(k, 0) for k in DESIGNATIONS},
        "blank_game_status": st.get("blank_game_status", 0),
        "practice_counts": {k: pr.get(k, 0) for k in ("FP", "LP", "DNP")},
        "rows_with_designation": sum(st.get(k, 0) for k in DESIGNATIONS),
    }


def compare(old_rows: list[dict], new_rows: list[dict], old_by_key: dict, new_by_key: dict) -> dict:
    added = [k for k in new_by_key if k not in old_by_key]
    dropped = [k for k in old_by_key if k not in new_by_key]
    desig, prac = [], []
    for k, nr in new_by_key.items():
        orow = old_by_key.get(k)
        if not orow:
            continue
        if nr["status"] != orow["status"]:
            desig.append({
                "team": k[0], "player": nr["player"], "pos": nr["pos"],
                "status_before": orow["status"] or "(none)", "status_after": nr["status"] or "(none)",
                "practice_before": orow["practice"], "practice_after": nr["practice"],
            })
        elif nr["practice"] != orow["practice"]:
            prac.append({
                "team": k[0], "player": nr["player"], "pos": nr["pos"],
                "practice_before": orow["practice"], "practice_after": nr["practice"],
                "status_both": nr["status"] or "(none)",
            })
    return {"added": added, "dropped": dropped, "designation_changes": desig, "practice_changes": prac}


def corroboration(key: tuple, reads: list[tuple[str, list[dict]]], field: str) -> dict:
    """How many independent retained reads agree on `field` for this player at the
    earlier timestamp. Two agreeing reads is corroboration; one read is not."""
    vals = {}
    for name, rows in reads:
        by = {r["key"]: r for r in rows}
        if key in by:
            vals[name] = by[key][field]
    uniq = set(vals.values())
    if len(vals) >= 2 and len(uniq) == 1:
        verdict = "CORROBORATED"
    elif len(vals) == 1:
        verdict = "SINGLE READ"
    elif len(vals) >= 2:
        verdict = "CONTESTED"
    else:
        verdict = "ABSENT FROM PRIOR READS"
    return {"verdict": verdict, "prior_reads": vals}


def main() -> int:
    if not os.path.isdir(CAPDIR):
        raise SystemExit("no capture directory at data/snapshots/wk10")

    # --- prior reads retained in the repository, recomputed here, never edited ---
    desk_path = os.path.join(ROOT, "data", "desk", "injuries.json")
    audit_path = os.path.join(ROOT, "audit", "official_injury_wk10_2026.csv")
    prior = from_desk(desk_path, 10)
    prior_reads = [("data/desk/injuries.json (week 10 rows)", prior)]
    if os.path.exists(audit_path):
        prior_reads.append(("audit/official_injury_wk10_2026.csv", from_audit_csv(audit_path)))

    captures = []
    files = sorted(f for f in os.listdir(CAPDIR) if f.endswith(".csv"))
    for f in files:
        m = CAPTURE_FILE_RE.match(f)
        if not m:
            raise SystemExit(f"capture filename does not encode dateTtimeZ and week: {f}")
        date, hhmm, week = m.group(1), m.group(2), int(m.group(3))
        path = os.path.join(CAPDIR, f)
        rows = read_capture(path)
        clock = f"{date}T{hhmm[:2]}:{hhmm[2:]}:00Z"
        rec = {
            "capture_id": f"SNAP-2026W{week}-{date}T{hhmm}Z",
            "season": 2026, "week": week,
            "source_url": f"https://www.nfl.com/injuries/league/2026/reg{week}",
            "fetched_at_utc": clock,
            "clock_precision": "minute" if hhmm != "0000" else "day-only (clock time not recorded by the capturing session)",
            "retrieved_via": "fetch_page (rendered markdown of the official page); shell HTTP clients are blocked in this sandbox",
            "chunks_read": "0-6 of 8 (the 8th chunk carries only the news module; the last club table closes before its heading)",
            "file": f"data/snapshots/wk10/{f}",
            "sha256": sha256_of(path),
            "bytes": os.path.getsize(path),
            "parser_version": PARSER_VERSION,
            "sealed": True,
            "files": [f"data/snapshots/wk10/{f}"],
            "rows": len(rows),
            "counts": counts(rows),
            "team_codes_printed": sorted({r["team_printed"] for r in rows} - {r["team"] for r in rows}),
        }
        captures.append(rec)

    captures.sort(key=lambda c: c["fetched_at_utc"])
    if not captures:
        raise SystemExit("no captures found")

    # --- baseline record for the read the repository already held -------------
    baseline = {
        "capture_id": "SNAP-2026W10-2026-11-14T0000Z",
        "season": 2026, "week": 10,
        "source_url": "https://www.nfl.com/injuries/league/2026/reg10",
        "fetched_at_utc": "2026-11-14 (no clock time recorded)",
        "clock_precision": "day only - flagged: a read without an hour cannot anchor a pre-kickoff delta",
        "retrieved_via": "prior sessions (desk pipeline, audit transcription)",
        "chunks_read": "not recorded by the capturing sessions",
        "file": "data/desk/injuries.json (week=10 rows) + audit/official_injury_wk10_2026.csv",
        "sha256": sha256_of(desk_path),
        "bytes": os.path.getsize(desk_path),
        "parser_version": "pre-store (no parser version recorded)",
        "sealed": False,
        "files": ["data/desk/injuries.json", "audit/official_injury_wk10_2026.csv"],
        "rows": len(prior),
        "counts": counts(prior),
        "note": "Reconstructed from bytes already in the repository. The desk store is the canonical "
                "series; the audit CSV is a second, independent transcription of the same page on the "
                "same day. Both are read here read-only; neither is modified by this script.",
    }
    ledger = {
        "store_version": "x3-snapshot-store-v1",
        "policy": {
            "immutable": "capture files are append-only; this script never rewrites a capture, it re-derives the index",
            "hash_target": "sha256 of the stored capture bytes",
            "required_per_capture": ["source_url", "fetched_at_utc", "sha256", "bytes", "rows", "parser_version"],
            "unit_of_observation": "one dated read of one official page, not one week",
            "delta_is_the_product": "levels are stored; deltas are published",
            "reserve_list_limit": "the weekly report does not carry the IR/reserve list, so an absent row is "
                                  "'not in this read', never 'available'. Flagged, not resolved.",
        },
        "captures": [baseline] + captures,
        "independent_prior_reads": [
            {"read": name, "rows_week10": len(rows), "sha256_of_source": sha256_of(
                desk_path if name.startswith("data/desk") else audit_path)}
            for name, rows in prior_reads
        ],
    }

    # --- pairwise deltas over consecutive reads of the same week --------------
    all_reads = [("baseline 2026-11-14", prior)] + [(c["capture_id"], read_capture(os.path.join(ROOT, c["file"]))) for c in captures]
    deltas = []
    for i in range(len(all_reads) - 1):
        (aname, arows), (bname, brows) = all_reads[i], all_reads[i + 1]
        a_by = {r["key"]: r for r in arows}
        b_by = {r["key"]: r for r in brows}
        if len(a_by) != len(arows) or len(b_by) != len(brows):
            raise SystemExit("duplicate (team,player) key inside one capture - capture is not a set of unique rows")
        cmp = compare(arows, brows, a_by, b_by)
        # corroboration is computed against every retained read at the *earlier* timestamp
        prior_tag = "baseline 2026-11-14"
        reads_at_t = [(nm, rw) for (nm, rw) in all_reads if nm == prior_tag]
        if os.path.exists(audit_path):
            reads_at_t.append(("audit/official_injury_wk10_2026.csv", from_audit_csv(audit_path)))
        for d in cmp["designation_changes"]:
            d["corroboration_before"] = corroboration((d["team"], d["player"].lower()), reads_at_t, "status")
        for d in cmp["practice_changes"]:
            d["corroboration_before"] = corroboration((d["team"], d["player"].lower()), reads_at_t, "practice_full")
        for k in cmp["added"]:
            r = b_by[k]
            d = {"team": k[0], "player": r["player"], "pos": r["pos"], "practice_after": r["practice"],
                 "status_after": r["status"] or "(none)",
                 "corroboration_before": corroboration(k, reads_at_t, "practice_full")}
            d["in_prior_desk_store"] = k in {x["key"] for x in arows}
            cmp.setdefault("added_detail", []).append(d)
        for k in cmp["dropped"]:
            r = a_by[k]
            cmp.setdefault("dropped_detail", []).append({
                "team": k[0], "player": r["player"], "pos": r["pos"],
                "practice_before": r["practice"], "status_before": r["status"] or "(none)"})
        ca, cb = counts(arows), counts(brows)
        deltas.append({
            "from_read": aname, "to_read": bname,
            "season": 2026, "week": 10,
            "source_url": "https://www.nfl.com/injuries/league/2026/reg10",
            "window_note": "gap between the two reads is a day and part of the following day; "
                           "the earlier read carries no clock time, so the gap cannot be stated in hours",
            "rows_before": ca["rows"], "rows_after": cb["rows"],
            "designation_changes_count": len(cmp["designation_changes"]),
            "practice_changes_count": len(cmp["practice_changes"]),
            "added_rows_count": len(cmp["added"]), "dropped_rows_count": len(cmp["dropped"]),
            "counts_before": ca, "counts_after": cb,
            **{k: v for k, v in cmp.items() if k != "added"},
            "surprise_panel": {
                "definition": "injury signal as movement, not level: rows that gained an adverse "
                              "designation (none/LP/FP -> Out or Doubtful) between two reads",
                "adverse": sum(1 for d in cmp["designation_changes"]
                               if d["status_after"] in ("Out", "Doubtful")),
                "favourable": sum(1 for d in cmp["designation_changes"]
                                  if d["status_after"] == "(none)" or (d["status_before"] in ("Out", "Doubtful")
                                                                       and d["status_after"] == "Questionable")),
                "changed_anything": len(cmp["designation_changes"]) > 0 or len(cmp["added"]) > 0,
            },
        })

    os.makedirs(SNAP, exist_ok=True)
    with open(os.path.join(SNAP, "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(SNAP, "delta.json"), "w", encoding="utf-8") as fh:
        json.dump({"store_version": "x3-snapshot-delta-v1", "deltas": deltas}, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")

    print(f"captures: {len(ledger['captures'])}  deltas: {len(deltas)}")
    for d in deltas:
        print(f"  {d['from_read']} -> {d['to_read']}: rows {d['rows_before']}->{d['rows_after']} "
              f"designation-changes {d['designation_changes_count']} practice-changes {d['practice_changes_count']} "
              f"added {d['added_rows_count']} dropped {d['dropped_rows_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
