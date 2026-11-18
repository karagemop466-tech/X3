#!/usr/bin/env python3
"""Build the designation-reliability module (Q43/Q44/Q45).

Reads the raw captures under reliability/raw/ (official nfl.com report chunks and
Game Book evidence files), joins every designated player in the disclosed sample to
that game's official Game Book outcomes, and writes:

  reliability/manifest.csv     sha256 of every captured file + source URL + fetch time
  reliability/games.csv        the 12 sampled games with their official sources
  reliability/designations.csv every Out/Doubtful/Questionable row of the sampled teams
  reliability/join.csv         per-player outcome (played / inactive / unresolved)
  reliability/rates.csv        play rate and inactive rate per designation, Wilson 95% CI
  reliability/flagged.csv      irregularities and unresolved rows (published, never guessed)
  reliability/*.html           landing + subpages (deterministic; no live timestamps)

Matching rules (also printed on the methods page):
  * name key = first initial of the report first name + normalized surname; suffixes
    (Jr/II/III) stripped only when another surname token exists;
  * position family must agree between report and Game Book (so Ty Johnson RB never
    matches Taron Johnson CB);
  * played = a Game Book playtime row exists for the key with at least one snap, when
    the row count for the key is >= the report row count for the key; fewer rows than
    report rows is ambiguous -> UNRESOLVED; a row count of 0 means did not play, except
    when the evidence file declares a missing playtime band (then UNRESOLVED);
  * inactive = the key appears in the game's parsed Not Active set, only for games
    whose Game Book render carries an explicit Not Active section (rule A); games
    whose render drops the DNP/NA labels are excluded from the inactive rate (rule B);
  * inactive=yes forces played=0; a player found in both Not Active and playtime is a
    CONFLICT and is excluded from both rates;
  * every unresolved row carries a reason; nothing is inferred.
"""
from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL = ROOT / "reliability"
RAW = REL / "raw"
DATA = REL / "data"

Z = 1.959963984540054  # 97.5th percentile of the standard normal

# ---------------------------------------------------------------------------
# Disclosed sampling design: Week 10 of 2023/2024/2025, first four games as
# listed on the official report page (convenience sample, NOT random).
# ---------------------------------------------------------------------------
GAMES = [
    # season, slug, away, home, na_rule, playtime_band_missing, centre_url, pdf_url, evidence, fetched_at
    (2023, "panthers-at-bears", "Panthers", "Bears", "A", False,
     "https://www.nfl.com/games/panthers-at-bears-2023-reg-10",
     "https://static.www.nfl.com/image/upload/v1704923034/gamecenter/cbac56ac-f053-11ed-b4a7-bab79e4492fa.pdf",
     "reliability/raw/games/2023/panthers-at-bears.md", "2026-11-17T23:05Z"),
    (2023, "colts-at-patriots", "Colts", "Patriots", "B", False,
     "https://www.nfl.com/games/colts-at-patriots-2023-reg-10",
     "https://static.www.nfl.com/image/upload/v1699894876/gamecenter/cbac6844-f053-11ed-b4a7-bab79e4492fa.pdf",
     "reliability/raw/games/2023/colts-at-patriots.md", "2026-11-17T23:05Z"),
    (2023, "49ers-at-jaguars", "49ers", "Jaguars", "A", False,
     "https://www.nfl.com/games/49ers-at-jaguars-2023-reg-10",
     "https://static.www.nfl.com/image/upload/v1704923037/gamecenter/cbac8368-f053-11ed-b4a7-bab79e4492fa.pdf",
     "reliability/raw/games/2023/49ers-at-jaguars.md", "2026-11-17T23:06Z"),
    (2023, "titans-at-buccaneers", "Titans", "Buccaneers", "A", False,
     "https://www.nfl.com/games/titans-at-buccaneers-2023-reg-10",
     "https://static.www.nfl.com/image/upload/v1704923039/gamecenter/cbac9b0b-f053-11ed-b4a7-bab79e4492fa.pdf",
     "reliability/raw/games/2023/titans-at-buccaneers.md", "2026-11-17T23:05Z"),
    (2024, "bengals-at-ravens", "Bengals", "Ravens", "A", False,
     "https://www.nfl.com/games/bengals-at-ravens-2024-reg-10",
     "https://static.www.nfl.com/image/upload/v1731065430/gamecenter/ae9d1561-1312-11ef-afd1-646009f18b2e.pdf",
     "reliability/raw/games/2024/bengals-at-ravens.md", "2026-11-17T23:07Z"),
    (2024, "giants-at-panthers", "Giants", "Panthers", "A", True,
     "https://www.nfl.com/games/giants-at-panthers-2024-reg-10",
     "https://static.www.nfl.com/image/upload/v1731324632/gamecenter/ae9d1ae1-1312-11ef-afd1-646009f18b2e.pdf",
     "reliability/raw/games/2024/giants-at-panthers.md", "2026-11-17T23:07Z"),
    (2024, "bills-at-colts", "Bills", "Colts", "A", False,
     "https://www.nfl.com/games/bills-at-colts-2024-reg-10",
     "https://static.www.nfl.com/image/upload/v1731324634/gamecenter/ae9d22f8-1312-11ef-afd1-646009f18b2e.pdf",
     "reliability/raw/games/2024/bills-at-colts.md", "2026-11-17T23:07Z"),
    (2024, "broncos-at-chiefs", "Broncos", "Chiefs", "B", False,
     "https://www.nfl.com/games/broncos-at-chiefs-2024-reg-10",
     "https://static.www.nfl.com/image/upload/v1731324633/gamecenter/ae9d2ac6-1312-11ef-afd1-646009f18b2e.pdf",
     "reliability/raw/games/2024/broncos-at-chiefs.md", "2026-11-17T23:07Z"),
    (2025, "raiders-at-broncos", "Raiders", "Broncos", "A", False,
     "https://www.nfl.com/games/raiders-at-broncos-2025-reg-10",
     "https://static.www.nfl.com/image/upload/v1762513482/gamecenter/f7b51f32-311e-11f0-b670-ae1250fadad1.pdf",
     "reliability/raw/games/2025/raiders-at-broncos.md", "2026-11-17T23:01Z"),
    (2025, "falcons-at-colts", "Falcons", "Colts", "B", False,
     "https://www.nfl.com/games/falcons-at-colts-2025-reg-10",
     "https://static.www.nfl.com/image/upload/v1762772747/gamecenter/f7b52372-311e-11f0-b670-ae1250fadad1.pdf",
     "reliability/raw/games/2025/falcons-at-colts.md", "2026-11-17T23:08Z"),
    (2025, "saints-at-panthers", "Saints", "Panthers", "A", False,
     "https://www.nfl.com/games/saints-at-panthers-2025-reg-10",
     "https://static.www.nfl.com/image/upload/v1762772747/gamecenter/f7b52798-311e-11f0-b670-ae1250fadad1.pdf",
     "reliability/raw/games/2025/saints-at-panthers.md", "2026-11-17T23:08Z"),
    (2025, "bills-at-dolphins", "Bills", "Dolphins", "A", False,
     "https://www.nfl.com/games/bills-at-dolphins-2025-reg-10",
     "https://static.www.nfl.com/image/upload/v1762772748/gamecenter/f7d4b0eb-311e-11f0-b670-ae1250fadad1.pdf",
     "reliability/raw/games/2025/bills-at-dolphins.md", "2026-11-17T23:08Z"),
]

REPORT_URL = {2023: "https://www.nfl.com/injuries/league/2023/reg10",
              2024: "https://www.nfl.com/injuries/league/2024/reg10",
              2025: "https://www.nfl.com/injuries/league/2025/reg10"}
REPORT_FETCHED = {2023: "2026-11-17T23:02Z", 2024: "2026-11-17T23:03Z",
                  2025: "2026-11-17T23:02Z"}

# Designations whose Not Active match is ambiguous in the source (documented on
# the Flagged page) and therefore excluded from the inactive rate.
AMBIGUOUS_NA = {("bills-at-dolphins", "C.Robinson")}

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
FAMILY = {
    "QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "FB": "FB",
    "T": "OL", "G": "OL", "C": "OL", "OT": "OL", "OG": "OL", "OL": "OL", "OLB1": "OL",
    "DT": "DL", "NT": "DL", "DE": "DL", "DL": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB", "WLB": "LB", "SLB": "LB",
    "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB", "NB": "DB",
    "K": "ST", "P": "ST", "LS": "ST",
}
DESIGNATIONS = {"Out", "Doubtful", "Questionable"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def _segments_initial(first: str) -> set[str]:
    """Candidate single-letter initials for a report first name.

    'P.J.' -> {p, j}; 'DJ' -> {d}; 'Vonn' -> {v}; 'B.J.' -> {b, j}.
    """
    out: set[str] = set()
    if not first:
        return out
    out.add(first[0].lower())
    for seg in first.split("."):
        a = re.sub(r"[^A-Za-z]", "", seg)
        if a:
            out.add(a[0].lower())
    return out


def name_key(name: str) -> tuple[frozenset[str], str]:
    """(candidate initials, normalized surname) from a report name."""
    toks = [t for t in re.split(r"\s+", name.strip()) if t]
    if not toks:
        return (frozenset(), "")
    first = toks[0]
    sur_toks = toks[1:]
    while (sur_toks and sur_toks[-1].lower().strip(".") in SUFFIXES
           and len(sur_toks) > 1):
        sur_toks = sur_toks[:-1]
    surname = norm(sur_toks[-1]) if sur_toks else norm(first)
    return (frozenset(_segments_initial(first)), surname)


def gb_key(gb_name: str) -> tuple[str, str]:
    """(initial as printed, normalized surname) from a Game Book name.

    'B.Hill' -> ('b','hill'); 'D.J.Johnson' -> ('d','johnson');
    'Ta.Johnson' -> ('ta','johnson')  (two-letter initials stay two-letter, so a
    report first name 'Taron' can never match them);
    'E St. Brown' -> ('e','brown'); 'V Bell' -> ('v','bell').
    """
    gb_name = gb_name.strip()
    if "." in gb_name:
        head, _, tail = gb_name.rpartition(".")
        first_seg = head.split(".")[0]
        m = re.match(r"[A-Za-z]+", first_seg)
        initial = m.group(0).lower() if m else ""  # full first run: 'Ta' stays 'ta'
        return (initial, norm(tail))
    toks = [t for t in re.split(r"\s+", gb_name) if t]
    if not toks:
        return ("", "")
    m = re.match(r"[A-Za-z]", toks[0])
    return (m.group(0).lower() if m else "", name_key(gb_name)[1])


def fam(pos: str) -> str:
    return FAMILY.get(pos.strip().upper(), pos.strip().upper())


def wilson(x: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = x / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * ((p * (1 - p) / n + Z * Z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


# ---------------------------------------------------------------------------
# Report parsing
# ---------------------------------------------------------------------------
ROW_RE = re.compile(
    r"^\|\s*\[([^\]]+)\]\(https://www\.nfl\.com/players/[^)]+\)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$"
)


# All 32 club short names as they print on the report page: a bare line that is a
# club name switches attribution; a NON-sampled club clears it so its rows can never
# be credited to the previously sampled club.
ALL_CLUBS = {
    "Cardinals", "Falcons", "Ravens", "Bills", "Panthers", "Bears", "Browns",
    "Cowboys", "Broncos", "Lions", "Packers", "Texans", "Colts", "Jaguars",
    "Chiefs", "Chargers", "Rams", "Dolphins", "Vikings", "Patriots", "Saints",
    "Giants", "Jets", "Eagles", "Steelers", "49ers", "Seahawks", "Buccaneers",
    "Titans", "Commanders", "Bengals", "Raiders",
}


def load_chunk(path: Path) -> str:
    """Capture file with this session's header comments removed, for clean chunk gluing."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [ln for ln in lines
            if not ln.startswith("# Capture:") and not ln.startswith("# Fetched:")
            and not ln.startswith("# Scope:")]
    return "".join(kept)


def parse_reports() -> list[dict]:
    team_to_game: dict[tuple[int, str], tuple[str, str]] = {}
    for season, slug, away, home, *_rest in GAMES:
        team_to_game[(season, away)] = (slug, away)
        team_to_game[(season, home)] = (slug, home)
    team_names = {t for (_s, t) in team_to_game}
    rows: list[dict] = []
    for season in (2023, 2024, 2025):
        text0 = load_chunk(RAW / f"injuries/{season}/reg10_chunk0.md")
        text1 = load_chunk(RAW / f"injuries/{season}/reg10_chunk1.md")
        # contiguous tool chunks: a row split across the boundary rejoins here
        text = text0.rstrip("\n") + text1.lstrip("\n")
        current_team = None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped in ALL_CLUBS:
                current_team = stripped if (season, stripped) in team_to_game else None
                continue
            m = ROW_RE.match(stripped)
            if not m or current_team is None:
                continue
            pname, pos, _inj, _practice, status = m.groups()
            status = status.strip()
            if status not in DESIGNATIONS:
                continue
            slug, team = team_to_game[(season, current_team)]
            rows.append({
                "season": season, "week": 10, "game_slug": slug, "team": team,
                "report_name": pname.strip(), "position": pos.strip(),
                "designation": status,
                "report_source": f"reliability/raw/injuries/{season}/reg10_chunk0.md + chunk1",
                "report_url": REPORT_URL[season],
            })
    rows.sort(key=lambda r: (r["season"], r["game_slug"], r["team"], r["report_name"]))
    return rows


# ---------------------------------------------------------------------------
# Evidence parsing
# ---------------------------------------------------------------------------
def parse_na_set(text: str) -> tuple[set[tuple[str, str]], list[str]]:
    """Extract (initial-as-printed, surname) keys from the parsed Not Active block."""
    keys: set[tuple[str, str]] = set()
    notes: list[str] = []
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if "NOT ACTIVE sets as parsed" in ln or "NA presence set" in ln:
            start = i
            break
    if start is None:
        return keys, notes
    region: list[str] = []
    for ln in lines[start:]:
        if region and (ln.startswith("## ") or "DID NOT PLAY" in ln
                       or "PARSING NOTE" in ln or "cross-check" in ln):
            break
        region.append(ln)
    blob = "\n".join(region)
    # drop bracketed render-gap annotations before scanning names
    blob_clean = re.sub(r"\[[^\]]*\]", " ", blob)
    for m in re.finditer(r"\b([A-Z]{1,3}\.?[A-Za-z][A-Za-z.\-']*)\b", blob_clean):
        tok = m.group(1)
        if "." not in tok:
            continue
        if tok.lower().startswith(("http", "www")):
            continue
        initial, surname = gb_key(tok)
        if initial and surname:
            keys.add((initial, surname))
    if "[name missing" in blob or "[first name missing" in blob:
        notes.append("Not Active render drops at least one player name")
    return keys, notes


def _expand_cells(cells: list[str]) -> list[str]:
    """Split glued cells like '26% E Cleveland' that the PDF render jams together."""
    out: list[str] = []
    for c in cells:
        m = re.match(r"^(\d+\s*%)\s+([A-Z][A-Za-z.'\- ]+)$", c)
        if m:
            out.append(m.group(1))
            out.append(m.group(2))
        else:
            out.append(c)
    return out


def parse_playtime(text: str) -> list[tuple[str, str, bool]]:
    """Return (gb_name, position, has_snaps) for rows in the Playtime Percentage section."""
    idx = text.rfind("Playtime Percentage")
    if idx < 0:
        return []
    region = text[idx:]
    out: list[tuple[str, str, bool]] = []
    pos_tokens = set(FAMILY)
    for line in region.splitlines():
        if not line.startswith("|"):
            continue
        cells = _expand_cells([c.strip() for c in line.strip().strip("|").split("|")])
        if all(set(c) <= set("-: ") for c in cells if c):
            continue
        i = 0
        while i < len(cells) - 1:
            nm, ps = cells[i], cells[i + 1]
            if (nm and ps and ps.upper() in pos_tokens
                    and re.match(r"^[A-Z][A-Za-z.'\- ]*$", nm)
                    and not nm.isdigit()):
                snaps = False
                for c in cells[i + 2:i + 8]:
                    mm = re.match(r"^(\d+)\s+\d*%?$", c) or re.match(r"^(\d+)%$", c)
                    if mm and int(mm.group(1)) > 0:
                        snaps = True
                        break
                out.append((nm, ps, snaps))
                i += 2
                continue
            i += 1
    return out


# ---------------------------------------------------------------------------
# Join + rates
# ---------------------------------------------------------------------------
def build_join(designations: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    ev_cache: dict[str, dict] = {}
    for season, slug, _a, _h, na_rule, band_missing, centre, pdf, ev_path, fetched in GAMES:
        text = (ROOT / ev_path).read_text(encoding="utf-8")
        na_keys, na_notes = parse_na_set(text)
        play = parse_playtime(text)
        ev_cache[slug] = {
            "text": text, "na": na_keys, "na_notes": na_notes, "play": play,
            "na_rule": na_rule, "band_missing": band_missing,
            "centre": centre, "pdf": pdf, "path": ev_path, "fetched": fetched,
        }

    by_game: dict[str, list[dict]] = defaultdict(list)
    for d in designations:
        by_game[d["game_slug"]].append(d)

    join_rows: list[dict] = []
    flagged: list[dict] = []
    for season, slug, _a, _h, na_rule, band_missing, centre, pdf, ev_path, _f in GAMES:
        ev = ev_cache[slug]
        game_designated = by_game[slug]
        # playtime candidate index
        play_idx: dict[tuple, list[tuple[str, str, bool]]] = defaultdict(list)
        for nm, ps, snaps in ev["play"]:
            if snaps:
                play_idx[(gb_key(nm), fam(ps))].append((nm, ps, snaps))
        report_key_counts = Counter()
        for d in game_designated:
            report_key_counts[(name_key(d["report_name"]), fam(d["position"]))] += 1

        # report duplicate counts by (surname, family) within the game
        sur_fam_counts = Counter(
            (name_key(d["report_name"])[1], fam(d["position"])) for d in game_designated)
        # game-book same-surname+family row counts (initials ignored) and per-key rows
        gb_sur_fam: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        for nm, ps, snaps in ev["play"]:
            if snaps:
                ini, sur = gb_key(nm)
                gb_sur_fam[(sur, fam(ps))].append((nm, f"{ini}"))

        for d in game_designated:
            cands_ini, sur = name_key(d["report_name"])
            rfam = fam(d["position"])
            flags: list[str] = []
            same = gb_sur_fam.get((sur, rfam), [])
            cands = [nm for nm, ini in same if ini in cands_ini]
            needed = sur_fam_counts[(sur, rfam)]
            # Not Active presence: match any printed initial in the set for this surname
            in_na = na_rule == "A" and any(
                nini == ini and nsur == sur for (nini, nsur) in ev["na"]
                for ini in cands_ini) or (
                na_rule == "A" and any(nsur == sur and nini in cands_ini
                                       for (nini, nsur) in ev["na"]))
            last = d["report_name"].split()[-1]
            ambiguous_na = any(
                (slug, f"{ini.upper()}.{last}") in AMBIGUOUS_NA for ini in cands_ini)
            if ambiguous_na:
                flags.append("ambiguous Not Active match flagged for human review")
            gb_names = "; ".join(cands)
            # --- played ------------------------------------------------------
            if in_na and not ambiguous_na:
                played, played_note = "0", "inactive per Not Active section"
            elif cands and len(cands) < needed:
                played, played_note = "unresolved", (
                    f"{len(cands)} playtime row(s) for {needed} report rows with this surname+position")
                flags.append("duplicate key: fewer playtime rows than report rows")
            elif cands:
                played, played_note = "1", f"playtime row: {gb_names}"
                if needed > 1:
                    flags.append(f"duplicate key resolved by row count: {needed} report rows, {len(cands)} playtime rows")
            elif same and not band_missing:
                # surname+position exist in the section but no initial matches:
                # render garble or a different player — absence is not evidence
                played, played_note = "unresolved", (
                    "playtime rows share this surname+position but none matches "
                    "the report initial (render garble or different player)")
                flags.append("near-miss playtime rows; UNRESOLVED")
            elif band_missing:
                played, played_note = "unresolved", "playtime band missing in captured chunks; absence is not evidence"
            else:
                played, played_note = "0", "no playtime row in captured section"
            # --- inactive ----------------------------------------------------
            if na_rule == "B":
                inactive, inactive_note = "excluded-rule-b", "Game Book render drops the Not Active labels; game excluded from inactive rate"
            elif ambiguous_na:
                inactive, inactive_note = "unresolved", "Not Active entry cannot be tied to this report row with confidence"
            elif in_na:
                inactive, inactive_note = "yes", "in parsed Not Active set"
            elif played == "1":
                inactive, inactive_note = "no", "has playtime row"
            else:
                inactive, inactive_note = "unresolved", "not in Not Active set and no playtime row"
            # --- conflict ----------------------------------------------------
            if inactive == "yes" and played == "1":
                flags.append("CONFLICT: listed Not Active yet has playtime row")
                played, inactive = "excluded-conflict", "excluded-conflict"
            if played == "1" and d["designation"] == "Out":
                flags.append("OUT->PLAYED discrepancy")
            if inactive == "yes" and d["designation"] == "Questionable":
                flags.append("Questionable player inactive")
            join_rows.append({
                "season": season, "game_slug": slug, "team": d["team"],
                "report_name": d["report_name"], "gb_name_matched": gb_names,
                "position": d["position"], "designation": d["designation"],
                "played": played, "played_evidence": played_note,
                "inactive": inactive, "inactive_evidence": inactive_note,
                "na_rule": na_rule, "flags": "; ".join(flags),
                "evidence_file": ev_path,
            })
            if flags:
                for fl in flags:
                    flagged.append({
                        "id": "", "kind": "row", "title": f"{season} {slug}: {d['report_name']} ({d['team']}, {d['designation']})",
                        "detail": fl, "source": ev["pdf"],
                    })
    join_rows.sort(key=lambda r: (r["season"], r["game_slug"], r["team"], r["report_name"]))
    return join_rows, flagged, [ev_cache[g[1]] for g in GAMES]


def compute_rates(join_rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for designation in ("Out", "Doubtful", "Questionable"):
        for metric, col, keep in (
            ("play_rate", "played", {"0", "1"}),
            ("inactive_rate", "inactive", {"yes", "no"}),
        ):
            sel = [r for r in join_rows if r["designation"] == designation and r[col] in keep]
            x = sum(1 for r in sel if (r[col] == "1" if col == "played" else r[col] == "yes"))
            n = len(sel)
            lo, hi = wilson(x, n)
            by_season = Counter(r["season"] for r in sel)
            unresolved = sum(1 for r in join_rows
                             if r["designation"] == designation
                             and r[col] not in keep
                             and not (col == "inactive" and r[col] == "excluded-rule-b"))
            excluded_rb = sum(1 for r in join_rows
                              if r["designation"] == designation and r[col] == "excluded-rule-b")
            out.append({
                "designation": designation, "metric": metric,
                "n": n, "events": x,
                "rate": f"{x / n:.4f}" if n else "",
                "ci95_low": f"{lo:.4f}" if n else "",
                "ci95_high": f"{hi:.4f}" if n else "",
                "unresolved_excluded": unresolved,
                "excluded_rule_b": excluded_rb,
                "per_season_n": "; ".join(f"{s}:{by_season[s]}" for s in sorted(by_season)),
            })
    return out


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


NAV = [("index.html", "Overview"), ("archive.html", "Archive"), ("reliability.html", "Reliability"),
       ("join.html", "Player join"), ("flagged.html", "Flagged for Review"),
       ("sources.html", "Sources"), ("methods.html", "Methods")]


def page(title: str, active: str, body: str) -> str:
    links = " · ".join(
        f'<a href="{h}"{" class=on" if h == active else ""}>{esc(t)}</a>' for h, t in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — X3 designation reliability</title>
<style>
 body{{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#15202b;background:#f6f8fa}}
 header{{background:#0d2137;color:#fff;padding:14px 22px}}
 header h1{{margin:0;font-size:19px;font-weight:650}}
 header .sub{{opacity:.75;font-size:12.5px;margin-top:3px}}
 nav{{background:#132f4c;padding:7px 22px;font-size:13.5px}}
 nav a{{color:#cfe3f7;text-decoration:none;margin-right:14px}}
 nav a.on{{color:#fff;font-weight:700;text-decoration:underline}}
 main{{max-width:1080px;margin:16px auto;padding:0 18px}}
 h2{{font-size:17px;margin:26px 0 8px}} h3{{font-size:14.5px;margin:20px 0 6px}}
 table{{border-collapse:collapse;width:100%;background:#fff;font-size:13.5px}}
 th,td{{border:1px solid #d7dee6;padding:5px 8px;text-align:left;vertical-align:top}}
 th{{background:#e8eef4;position:sticky;top:0}}
 td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
 .ok{{color:#0a6b33;font-weight:600}} .bad{{color:#a4262c;font-weight:600}}
 .mut{{color:#5b6b7c}} .flag{{background:#fff6e5}}
 a{{color:#0b57a4}} code{{background:#eef2f6;padding:0 4px;border-radius:3px;font-size:12.5px}}
 .card{{background:#fff;border:1px solid #d7dee6;border-radius:8px;padding:12px 16px;margin:10px 0}}
 .kpi{{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}}
 .kpi div{{background:#fff;border:1px solid #d7dee6;border-radius:8px;padding:10px 16px;min-width:150px}}
 .kpi b{{display:block;font-size:22px}}
 .kpi span{{font-size:12px;color:#5b6b7c}}
 footer{{max-width:1080px;margin:26px auto 40px;padding:0 18px;font-size:12.5px;color:#5b6b7c}}
</style></head><body>
<header><h1>Past-season injury archive &amp; designation reliability</h1>
<div class="sub">Official NFL sources only · Week 10, seasons 2023–2025 · session arena/73e6752d-x3 · captures 2026-11-17</div></header>
<nav>{links}</nav>
<main>
{body}
</main>
<footer>Every table row on this module links to its official source or is explicitly flagged.
Rates are descriptive measurements of the sample described on the Methods page — not a model input, not advice.</footer>
</body></html>
"""


def write_pages(designations, join_rows, rates, games_rows, flagged, manifest_rows):
    n_games = len(GAMES)
    n_des = len(designations)
    n_out = sum(1 for d in designations if d["designation"] == "Out")
    n_q = sum(1 for d in designations if d["designation"] == "Questionable")
    n_d = sum(1 for d in designations if d["designation"] == "Doubtful")
    n_unres = sum(1 for r in join_rows if r["played"] == "unresolved")
    n_outplayed = sum(1 for r in join_rows if "OUT->PLAYED" in r["flags"])
    rates_by = {(r["designation"], r["metric"]): r for r in rates}

    def rate_cell(des, metric):
        r = rates_by[(des, metric)]
        if not r["n"]:
            return '<td class="num">n/a</td><td class="num">0</td>'
        return (f'<td class="num">{100 * float(r["rate"]):.1f}%</td>'
                f'<td class="num">{100 * float(r["ci95_low"]):.1f}–{100 * float(r["ci95_high"]):.1f}%</td>')

    # --- index -------------------------------------------------------------
    kpis = f"""<div class="kpi">
 <div><b>{n_games}</b><span>games joined (3 seasons × first 4 games)</span></div>
 <div><b>{n_des}</b><span>designated players (Out {n_out} · Q {n_q} · D {n_d})</span></div>
 <div><b>{n_outplayed}</b><span>Out→played discrepancies (measured, flagged)</span></div>
 <div><b>{n_unres}</b><span>rows left UNRESOLVED (never guessed)</span></div>
</div>"""
    rate_table = """<table><thead><tr><th>Designation</th><th class="num">Played n</th><th class="num">Play rate</th><th class="num">Wilson 95% CI</th><th class="num">Inactive n</th><th class="num">Inactive rate</th><th class="num">Wilson 95% CI</th></tr></thead><tbody>"""
    for des in ("Out", "Questionable", "Doubtful"):
        pr, ir = rates_by[(des, "play_rate")], rates_by[(des, "inactive_rate")]
        rate_table += (f"<tr><td><b>{des}</b></td>"
                       f'<td class="num">{pr["n"]}</td>' + rate_cell(des, "play_rate") +
                       f'<td class="num">{ir["n"]}</td>' + rate_cell(des, "inactive_rate") + "</tr>")
    rate_table += "</tbody></table>"
    body = f"""
<h2>What this module is</h2>
<div class="card"><p>Two brief items had no coverage anywhere in the repository: <b>Q43</b> — archive weekly
injury reports for past seasons, and <b>Q44/Q45</b> — score injury-designation reliability by joining
designations to the official inactive lists and measuring the play rate per designation with confidence
intervals. This module does both, from official nfl.com sources only:</p>
<ul>
<li><b><a href="archive.html">Archive</a></b> — dated captures of the official Week-10 injury reports for
2023, 2024 and 2025 with sha256 seals (<code>reliability/manifest.csv</code>).</li>
<li><b><a href="reliability.html">Reliability</a></b> — play rate and inactive rate per designation with
Wilson 95% intervals and n per row.</li>
<li><b><a href="join.html">Player join</a></b> — every designated player in the sample, the Game Book
evidence for the outcome, and the unresolved rows.</li>
<li><b><a href="flagged.html">Flagged for Review</a></b> — render irregularities, ambiguous matches and
the Out→played discrepancies. Nothing here blocks publication; nothing here is reconciled by guesswork.</li>
</ul></div>
{kpis}
<h2>Headline rates (sample descriptive, Wilson 95% CI)</h2>
{rate_table}
<p class="mut">Read the intervals, not just the point estimates — n per row is small by design (this is a
pilot join, not a season-long study). Denominators exclude UNRESOLVED rows; the excluded counts are on
the <a href="reliability.html">Reliability</a> page.</p>
<h2>What it means for the desk</h2>
<div class="card"><ul>
<li><b>Out</b> is close to a reliable "will not play" statement in this sample, but not perfect: {n_outplayed}
Out-listed players have official playtime rows. Those rows are published as discrepancies, not reconciled —
the report page exposes no last-updated timestamp, so designation-vs-kickoff timing is unknown (Q-04).</li>
<li><b>Questionable</b> is a wide band: the sample play rate is high but the interval spans a range that
cannot be collapsed to a single multiplier yet. Q45's calibration needs more weeks before any model use.</li>
<li><b>Doubtful</b> behaves like a mild Out in this sample, with n too small to treat as more than a pilot
number.</li>
</ul></div>
<h2>Scope decisions (disclosed before capture)</h2>
<div class="card"><ul>
<li>Week 10 of each season 2023–2025; the <b>first four games as listed on the official report page</b>
(Thursday + early-Sunday window) — a convenience sample, not random. Three of the twelve games are
international-series games (Frankfurt 2023, Munich 2024, Berlin 2025) because those kick off early.</li>
<li>2026 Week 10 is <b>not</b> joined here: its report re-capture is claimed by another session (PR #79),
and its Monday game was not final at capture time.</li>
<li>The archive stores report chunks 0–1 of each week (the sampled games' rows are complete within them),
not the full 7–9 chunks — full-week archive is the next increment.</li>
</ul></div>
"""
    (REL / "index.html").write_text(page("Overview", "index.html", body), encoding="utf-8")

    # --- archive -----------------------------------------------------------
    rows = ""
    for m in manifest_rows:
        rows += (f'<tr><td><code>{esc(m["path"])}</code></td><td>{esc(m["kind"])}</td>'
                 f'<td><a href="{esc(m["source_url"])}">official source</a></td>'
                 f'<td>{esc(m["fetched_at"])}</td><td><code>{esc(m["sha256"][:16])}…</code></td></tr>')
    body = f"""
<h2>Q43 — past-season injury report archive</h2>
<div class="card">Every capture below was taken on 2026-11-17 through the session's page-fetch tool and
sealed with sha256 in <code>reliability/manifest.csv</code>. Report chunks are stored verbatim; game
evidence files store the official centre facts, the Not Active / Did Not Play sections verbatim and the
playtime rows needed for the join, each with its source URL.</div>
<table><thead><tr><th>File</th><th>Kind</th><th>Source</th><th>Fetched (UTC)</th><th>sha256</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2>Report pages archived</h2>
<table><thead><tr><th>Season</th><th>Week</th><th>Official page</th><th>Chunks stored</th><th>Designated rows found</th></tr></thead><tbody>
""" + "".join(
        f'<tr><td>{s}</td><td>10</td><td><a href="{REPORT_URL[s]}">nfl.com injury report</a></td>'
        f'<td>0–1 (of {tc})</td><td class="num">{sum(1 for d in designations if d["season"] == s)}</td></tr>'
        for s, tc in ((2023, 7), (2024, 9), (2025, 8))) + """</tbody></table>
<p class="mut">Uncovered increment (flagged, not blocking): full-week chunks for each season, and 2026
Week 10 once its re-capture lands.</p>
"""
    (REL / "archive.html").write_text(page("Archive", "archive.html", body), encoding="utf-8")

    # --- reliability -------------------------------------------------------
    rt = """<table><thead><tr><th>Designation</th><th>Metric</th><th class="num">Events / n</th><th class="num">Rate</th><th class="num">Wilson 95% CI</th><th class="num">Unresolved excluded</th><th class="num">Rule-B excluded</th><th>Per-season n</th></tr></thead><tbody>"""
    for r in rates:
        rate = f'{100 * float(r["rate"]):.1f}%' if r["n"] else "n/a"
        ci = f'{100 * float(r["ci95_low"]):.1f}–{100 * float(r["ci95_high"]):.1f}%' if r["n"] else "n/a"
        rt += (f'<tr><td>{esc(r["designation"])}</td><td>{esc(r["metric"])}</td>'
               f'<td class="num">{r["events"]} / {r["n"]}</td><td class="num">{rate}</td>'
               f'<td class="num">{ci}</td><td class="num">{r["unresolved_excluded"]}</td>'
               f'<td class="num">{r["excluded_rule_b"]}</td><td>{esc(r["per_season_n"])}</td></tr>')
    rt += "</tbody></table>"
    games_t = "<table><thead><tr><th>Season</th><th>Game</th><th>Venue (official)</th><th>Not Active rule</th><th>Game Book</th></tr></thead><tbody>"
    for g in games_rows:
        games_t += (f'<tr><td class="num">{g["season"]}</td><td>{esc(g["game_slug"])}</td>'
                    f'<td>{esc(g["venue"])}</td><td>{"A — labelled section" if g["na_rule"] == "A" else "<span class=bad>B — labels dropped, inactive rate excluded</span>"}</td>'
                    f'<td><a href="{esc(g["pdf_url"])}">Game Book</a></td></tr>')
    games_t += "</tbody></table>"
    body = f"""
<h2>Q44/Q45 — play rate and inactive rate per designation</h2>
<div class="card"><p><b>Play rate</b> = share of designated players with an official playtime row
(&gt;0 snaps) in that game's Game Book. <b>Inactive rate</b> = share found in the game's Not Active
section, computed only for games whose Game Book render carries an explicit Not Active section
(rule A); games whose render drops those labels are excluded from this metric (rule B) rather than
guessing. Intervals are Wilson score 95%.</p></div>
{rt}
<h3>How to read this</h3>
<div class="card"><ul>
<li>Denominators count only resolved rows; unresolved rows and rule-B exclusions are shown as columns,
never folded into the rate.</li>
<li>UNRESOLVED happens when a name cannot be matched with confidence (position families, duplicate keys,
missing render bands) — those rows sit on the <a href="join.html">Player join</a> page with reasons.</li>
<li>This is a descriptive pilot: three seasons, twelve games, convenience sample. It is pre-registered as
measurement only — no model consumes it in this pass.</li>
</ul></div>
<h2>The twelve sampled games</h2>
{games_t}
"""
    (REL / "reliability.html").write_text(page("Reliability", "reliability.html", body), encoding="utf-8")

    # --- join --------------------------------------------------------------
    jt = """<table><thead><tr><th>Season</th><th>Game</th><th>Team</th><th>Report player</th><th>Pos</th><th>Designation</th><th>Played</th><th>Play evidence</th><th>Inactive</th><th>Inactive evidence</th><th>Flags</th></tr></thead><tbody>"""
    for r in join_rows:
        pc = "ok" if r["played"] == "1" else ("bad" if r["played"] == "0" else "mut")
        ic = {"yes": "bad", "no": "ok"}.get(r["played"] and r["inactive"], "mut")
        ic = "bad" if r["inactive"] == "yes" else ("ok" if r["inactive"] == "no" else "mut")
        row_cls = ' class="flag"' if r["flags"] else ""
        jt += (f'<tr{row_cls}><td class="num">{r["season"]}</td><td>{esc(r["game_slug"])}</td>'
               f'<td>{esc(r["team"])}</td><td>{esc(r["report_name"])}</td><td>{esc(r["position"])}</td>'
               f'<td>{esc(r["designation"])}</td><td class="{pc}">{esc(r["played"])}</td>'
               f'<td>{esc(r["played_evidence"])}</td><td class="{ic}">{esc(r["inactive"])}</td>'
               f'<td>{esc(r["inactive_evidence"])}</td><td>{esc(r["flags"])}</td></tr>')
    jt += "</tbody></table>"
    body = f"""
<h2>Player join — every designated row in the sample</h2>
<div class="card">{len(join_rows)} rows. Report side parsed verbatim from
<code>reliability/raw/injuries/&lt;season&gt;/reg10_chunk*.md</code> (official report page); outcome side
from each game's evidence file (official Game Book). Shaded rows carry flags. "unresolved" means the
captured evidence does not settle the question — it is excluded from rates, never guessed.</div>
{jt}
"""
    (REL / "join.html").write_text(page("Player join", "join.html", body), encoding="utf-8")

    # --- flagged -----------------------------------------------------------
    # curated structural flags first
    curated = [
        {"kind": "scope", "title": "Convenience sample, not random",
         "detail": "First four games as listed on each official report page (Thursday + early-Sunday window); 3 of 12 games are international series. Rates are sample-descriptive only.",
         "source": REPORT_URL[2025]},
        {"kind": "scope", "title": "Archive covers report chunks 0–1, not the full week",
         "detail": "The sampled games' designated rows are complete inside chunks 0–1; full-week chunks (7–9 per report) are the next increment for Q43.",
         "source": REPORT_URL[2023]},
        {"kind": "scope", "title": "2026 Week 10 excluded from the join",
         "detail": "Its report re-capture is claimed by another session (PR #79) and its Monday game was not final at capture time. Joining it is the next increment.",
         "source": "https://www.nfl.com/injuries/league/2026/reg10"},
        {"kind": "timing", "title": "Report page exposes no last-updated timestamp (existing Q-04)",
         "detail": "Designation-vs-kickoff timing is unknown, so Out→played rows may be timing artifacts rather than errors. Published as measured, not reconciled.",
         "source": "https://www.nfl.com/injuries/"},
        {"kind": "source", "title": "Playtime Percentage section is labelled (Unofficial) in some Game Books",
         "detail": "2023 and several 2024/2025 books print 'Percent of playtime per player ... (Unofficial)' under the Playtime Percentage heading. The Game Book itself is the official publication; the league's label is quoted in the evidence files.",
         "source": "https://static.www.nfl.com/image/upload/v1731324634/gamecenter/ae9d22f8-1312-11ef-afd1-646009f18b2e.pdf"},
        {"kind": "capture", "title": "Shell curl to nfl.com is blocked in this environment",
         "detail": "All captures went through the session's page-fetch tool; files are transcriptions of tool output and sealed with sha256 in the manifest. One Game Book chunk-0 fetch failed and succeeded on retry (SF@JAX).",
         "source": "https://www.nfl.com/games/49ers-at-jaguars-2023-reg-10"},
        {"kind": "render", "title": "Three Game Books drop the Did Not Play / Not Active labels",
         "detail": "IND@NE (2023), DEN@KC (2024) and ATL@IND (2025) render the roster lists without their labels; these games are excluded from the inactive rate (rule B) and only contribute to the play rate.",
         "source": "https://static.www.nfl.com/image/upload/v1699894876/gamecenter/cbac6844-f053-11ed-b4a7-bab79e4492fa.pdf"},
        {"kind": "render", "title": "BUF@MIA render files the Dolphins substitutions under a 'Did Not Play' label",
         "detail": "Player-by-player evidence (playtime table + box score) shows all 25 names in that list played. Parsed as substitutions; the label mismatch is preserved in the evidence file.",
         "source": "https://static.www.nfl.com/image/upload/v1762772748/gamecenter/f7d4b0eb-311e-11f0-b670-ae1250fadad1.pdf"},
        {"kind": "render", "title": "Dropped player names inside Not Active lists",
         "detail": "SF@JAX ('DL 90' name missing), IND@NE ('TE 85' name missing), DEN@KC ('G 76' name missing), ATL@IND ('OL 65' / 'T 67' names missing). Players whose match depends on a dropped name are UNRESOLVED.",
         "source": "https://static.www.nfl.com/image/upload/v1704923037/gamecenter/cbac8368-f053-11ed-b4a7-bab79e4492fa.pdf"},
        {"kind": "render", "title": "NYG@CAR playtime band missing at the tool chunk boundary",
         "detail": "Rows between the chunk-7 cut and the chunk-8 start are not in the captured text; A.Thielen (Out) cannot be resolved from absence and is left UNRESOLVED.",
         "source": "https://static.www.nfl.com/image/upload/v1731324632/gamecenter/ae9d1ae1-1312-11ef-afd1-646009f18b2e.pdf"},
        {"kind": "render", "title": "Garbled playtime rows for J. Blackwell (CAR@CHI, 2023)",
         "detail": "The section prints 'D Blackwell CB' and 'J Blackwell RB' with identical snap counts; no row satisfies initial+surname+position for report row Josh Blackwell (CB), so that row is UNRESOLVED.",
         "source": "https://static.www.nfl.com/image/upload/v1704923034/gamecenter/cbac56ac-f053-11ed-b4a7-bab79e4492fa.pdf"},
        {"kind": "match", "title": "Ambiguous Not Active entry: 'LB 44 C.Robinson' (BUF@MIA, 2025)",
         "detail": "Matched to report row Chop Robinson (LB) by initial+surname+position only; the report page publishes no jersey numbers. Excluded from the inactive rate, shown on the join page for human review.",
         "source": "https://static.www.nfl.com/image/upload/v1762772748/gamecenter/f7d4b0eb-311e-11f0-b670-ae1250fadad1.pdf"},
        {"kind": "match", "title": "Duplicate key: two J. Jones (CB) rows in IND@NE (2023)",
         "detail": "Report rows Jack Jones and Jonathan Jones share initial+surname+position with two New England playtime rows; both counted played by the row-count rule and flagged on the join page.",
         "source": "https://static.www.nfl.com/image/upload/v1699894876/gamecenter/cbac6844-f053-11ed-b4a7-bab79e4492fa.pdf"},
    ]
    ft = """<table><thead><tr><th>#</th><th>Kind</th><th>Item</th><th>Detail</th><th>Source</th></tr></thead><tbody>"""
    i = 0
    for c in curated:
        i += 1
        ft += (f'<tr class="flag"><td class="num">F{i:02d}</td><td>{esc(c["kind"])}</td>'
               f'<td><b>{esc(c["title"])}</b></td><td>{esc(c["detail"])}</td>'
               f'<td><a href="{esc(c["source"])}">official</a></td></tr>')
    row_flags = [f for f in flagged if f["kind"] == "row"]
    # collapse duplicate titles
    seen: set[str] = set()
    for f in row_flags:
        if f["title"] in seen:
            continue
        seen.add(f["title"])
        i += 1
        ft += (f'<tr class="flag"><td class="num">F{i:02d}</td><td>row</td>'
               f'<td><b>{esc(f["title"])}</b></td><td>{esc(f["detail"])}</td>'
               f'<td><a href="{esc(f["source"])}">Game Book</a></td></tr>')
    ft += "</tbody></table>"
    body = f"""
<h2>Flagged for Review</h2>
<div class="card">Flagged items do not block publication or the merge (per brief). Nothing on this page
was reconciled by inference: where evidence stops, the join says <code>unresolved</code>.</div>
{ft}
"""
    (REL / "flagged.html").write_text(page("Flagged for Review", "flagged.html", body), encoding="utf-8")

    # --- sources -----------------------------------------------------------
    st = """<table><thead><tr><th>#</th><th>Source</th><th>Used for</th></tr></thead><tbody>"""
    srcs = []
    for season in (2023, 2024, 2025):
        srcs.append((REPORT_URL[season], f"Week-10 designations, {season} (report chunks 0–1 archived)"))
    for _s, slug, _a, _h, _nr, _bm, centre, pdf, _ev, _f in GAMES:
        srcs.append((centre, f"{slug} — final score, venue, Game Book link"))
        srcs.append((pdf, f"{slug} — Not Active / Did Not Play / Playtime Percentage"))
    for u, use in srcs:
        st += f'<tr><td class="num">{srcs.index((u, use)) + 1}</td><td><a href="{esc(u)}">{esc(u)}</a></td><td>{esc(use)}</td></tr>'
    st += "</tbody></table>"
    body = f"""
<h2>Official sources used by this module</h2>
<div class="card">Only nfl.com and static.www.nfl.com (the league's own Game Book host) are used.
No third-party stat site, no news article, no inferred value appears in any table on this module.</div>
{st}
<h2>Standing sources referenced by the wider project</h2>
<div class="card"><ul>
<li><a href="https://www.nfl.com/schedules/league/2026/REG">nfl.com schedules</a> — fixture context.</li>
<li><a href="https://operations.nfl.com/">operations.nfl.com</a> — official rulebook (not used by this module).</li>
</ul></div>
"""
    (REL / "sources.html").write_text(page("Sources", "sources.html", body), encoding="utf-8")

    # --- methods -----------------------------------------------------------
    body = f"""
<h2>Methods (pre-registered before capture)</h2>
<div class="card"><ol>
<li><b>Sample.</b> Week 10 of 2023, 2024, 2025. The first four games as listed on each official report
page. Convenience sample — disclosed on every page. 2026 Week 10 excluded (other session's claim + game
not final at capture time).</li>
<li><b>Archive (Q43).</b> Report chunks 0–1 stored verbatim with source URL and fetch time; sha256 of
every stored file in <code>reliability/manifest.csv</code>.</li>
<li><b>Designations.</b> Rows whose Game Status is Out, Doubtful or Questionable. Blank-status rows are
not part of this join (a no-designation baseline needs full playtime capture — next increment).</li>
<li><b>Outcome — played.</b> A row in the game's official Playtime Percentage section with ≥1 snap,
matched by first-initial + surname + position family, game-scoped. Duplicate keys resolve by row count;
fewer playtime rows than report rows is UNRESOLVED. Missing render bands make absence UNRESOLVED.</li>
<li><b>Outcome — inactive.</b> Presence in the game's parsed Not Active set, only when the Game Book
render carries an explicit Not Active section (rule A). Games whose render drops the labels (rule B:
IND@NE 2023, DEN@KC 2024, ATL@IND 2025) are excluded from the inactive rate entirely.</li>
<li><b>Conflicts.</b> Listed Not Active yet has a playtime row → CONFLICT, excluded from both rates,
published on the join and flagged pages.</li>
<li><b>Rates.</b> Wilson score 95% intervals. Denominators exclude unresolved/excluded rows; the excluded
counts are columns on the Reliability page. Per-season n published on every row.</li>
<li><b>Reproducibility.</b> <code>python3 scripts/reliability_build.py</code> regenerates every CSV and
page deterministically; <code>python3 scripts/reliability_verify.py</code> re-parses the raw captures,
re-checks completeness, evidence tokens and rate arithmetic.</li>
</ol></div>
<h2>What this module deliberately does not do</h2>
<div class="card"><ul>
<li>No inference: unresolved stays unresolved; no value is filled from expectation.</li>
<li>No model input: these are descriptive measurements; no strategy consumes them in this pass.</li>
<li>No non-official source: every table row links to nfl.com or static.www.nfl.com.</li>
<li>No shared-file edits: landing navigation registration for <code>reliability/</code> is logged as an
integration request in COORDINATION.md, not done here.</li>
</ul></div>
"""
    (REL / "methods.html").write_text(page("Methods", "methods.html", body), encoding="utf-8")


# ---------------------------------------------------------------------------
def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    designations = parse_reports()
    join_rows, flagged, _evs = build_join(designations)
    rates = compute_rates(join_rows)

    games_rows = []
    for season, slug, away, home, na_rule, band, centre, pdf, ev_path, fetched in GAMES:
        text = (ROOT / ev_path).read_text(encoding="utf-8")
        m = re.search(r"Location:?\s*([A-Z][A-Z ,]+)|at ([A-Z][^\n|]+(?:Stadium|Arena|Field)[^\n|]*)", text)
        venue = ""
        mv = re.search(r"^(?:Location:\s*)?(.+?(?:Stadium|Arena|Field|Dome).*)$", text, re.M)
        if mv:
            venue = mv.group(1).strip()
        else:
            mv = re.search(r"at ([A-Za-z .]+(?:Stadium|Arena|Field))", text)
            venue = mv.group(1).strip() if mv else "see Game Book"
        games_rows.append({
            "season": season, "week": 10, "game_slug": slug, "away": away, "home": home,
            "venue": venue, "na_rule": na_rule, "playtime_band_missing": "yes" if band else "no",
            "centre_url": centre, "pdf_url": pdf, "evidence_file": ev_path, "fetched_at": fetched,
        })

    # manifest
    manifest_rows = []
    for p in sorted(RAW.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        if "/injuries/" in rel:
            season = int(rel.split("/")[3])
            url = REPORT_URL[season]
            fetched = REPORT_FETCHED[season]
            kind = "report-chunk"
        else:
            slug = p.stem
            g = next(g for g in GAMES if g[1] == slug)
            url = g[7]
            fetched = g[9]
            kind = "game-evidence"
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        manifest_rows.append({
            "path": rel, "kind": kind, "source_url": url, "fetched_at": fetched,
            "sha256": digest, "bytes": p.stat().st_size,
        })

    def write_csv(path, rows, cols):
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})

    write_csv(DATA / "designations.csv", designations,
              ["season", "week", "game_slug", "team", "report_name", "position",
               "designation", "report_source", "report_url"])
    write_csv(DATA / "join.csv", join_rows,
              ["season", "game_slug", "team", "report_name", "gb_name_matched", "position",
               "designation", "played", "played_evidence", "inactive", "inactive_evidence",
               "na_rule", "flags", "evidence_file"])
    write_csv(DATA / "rates.csv", rates,
              ["designation", "metric", "n", "events", "rate", "ci95_low", "ci95_high",
               "unresolved_excluded", "excluded_rule_b", "per_season_n"])
    write_csv(DATA / "games.csv", games_rows,
              ["season", "week", "game_slug", "away", "home", "venue", "na_rule",
               "playtime_band_missing", "centre_url", "pdf_url", "evidence_file", "fetched_at"])
    # flag ids
    for i, f in enumerate(flagged, 1):
        f["id"] = f"R{i:03d}"
    write_csv(DATA / "row_flags.csv", flagged, ["id", "kind", "title", "detail", "source"])
    write_csv(REL / "manifest.csv", manifest_rows,
              ["path", "kind", "source_url", "fetched_at", "sha256", "bytes"])

    write_pages(designations, join_rows, rates, games_rows, flagged, manifest_rows)
    print(f"designations={len(designations)} join={len(join_rows)} rates={len(rates)} "
          f"manifest={len(manifest_rows)} flagged_rows={len(flagged)}")


if __name__ == "__main__":
    main()
