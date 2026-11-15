# Point-in-time snapshot store — official availability reads

Sealed, append-only reads of the official NFL availability report, so a
backtest can be replayed **as the information was known** and a pre-kickoff
delta can be published instead of a level.

This directory answers five requirements of the brief at once:

| Brief requirement | How this store satisfies it |
|---|---|
| "Store every injury-hub read with its clock time and publish the delta, never the level" | one record per read with `fetched_at_utc`; `delta.json` is the published product |
| "Automate immutable multi-day availability snapshots … with retained hashes" | `sealed: true` + `sha256` of the stored bytes; the verifier fails if a sealed file's hash moves |
| "Point-in-Time Snapshot Ledger for Injuries, Depth Charts & Inactives" | `ledger.json` |
| "Treat the injury report as a timestamped series, not a weekly snapshot" | reads are per-page-load, not per-week; two reads of week 10 now exist, one day apart |
| "Add a drift alarm to every scraper" | `scripts/x3_snapshots_verify.py` — counts must recompute, aliases must be declared, duplicate-served pages must be caught, builder must be deterministic |

## Layout

```
data/snapshots/
  ledger.json                     index of every read, with hash + clock time
  delta.json                      one record per consecutive pair of reads
  wk10/capture-<date>T<hhmm>Z-nfl-com-injuries-reg<week>.csv     one sealed read
```

## Rules

1. **A capture never changes.** The filename encodes the fetch clock time; the
   ledger stores the sha256 of the bytes. To correct a capture, add a new one —
   never edit an old one. A corrected old one is a leak.
2. **The filename is the metadata.** `capture-YYYY-MM-DDTHHMMZ-nfl-com-injuries-regW.csv`.
   The builder refuses any other name, because a capture whose clock time is
   guessable is not a point-in-time observation.
3. **Two reads of one page are one read.** If two capture files hash equal, the
   store treats that as a failure, not a duplicate data point. The official site
   has been observed to serve a stale report when asked for a future week
   (`data/desk/parse_report.json`: *"injuries-w11 … identical to an earlier
   week's report; dropped as a duplicate served for a future week"*).
4. **One documented alias, asserted.** The official page prints `AZ` and `LAR`;
   the repository keys those clubs `ARI` and `LA`. The alias map lives in
   `scripts/x3_snapshots.py`; the verifier fails on any new unmapped club code,
   because an unmapped code looks like 29 added rows plus 29 dropped rows and is
   really a join failure.
5. **Absence is not availability.** A player missing from a read means "not in
   this read". The weekly report does not carry the reserve/IR list, so a healthy
   player and a long-term absentee are indistinguishable in it. Flagged, not resolved.

## Columns of a capture

`team,player,pos,injury,practice,status`

* `team` — the club code **as printed on the page** (canonicalised by rule 4).
* `practice` — `FP` / `LP` / `DNP`, mapping one-to-one to the official strings
  ("Full / Limited Participation in Practice", "Did Not Participate In Practice").
* `status` — `Out` / `Doubtful` / `Questionable` / empty. Empty is a value: it
  means "listed on the report, no game designation".

## What a read is, honestly

Captures are made through the authoring environment's page reader (the rendered
text of the official page), because this sandbox blocks direct HTTP to nfl.com
(`curl https://www.nfl.com/...` → `SSL_ERROR_SYSCALL`). The reader returns the
page's rendered content, not raw HTML bytes, so:

* the hash seals **the transcription this store keeps**, not the league's HTML;
* a read is one render of one page at one clock time; the render order of the
  club tables is the page's own game order;
* the `retrieved_via` field on each ledger record states this, so nobody mistakes
  a capture for a byte-level archive of the league's page.

A byte-level archive (raw HTML + HTTP date header) needs a runner with network
egress to nfl.com — the workflow in `.github/workflows/origin-capture.yml` is the
place to add it. That is suggestion **S-D3** in the review queue.

## Rebuild and gate

```bash
python3 scripts/x3_snapshots.py         # re-derive ledger.json + delta.json
python3 scripts/x3_snapshots_verify.py  # gate: exits non-zero on any of the above
```

Both are offline and deterministic; the verifier re-runs the builder and fails
if the bytes move.
