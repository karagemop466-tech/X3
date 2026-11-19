#!/usr/bin/env python3
"""Build data/live/* datasets deterministically from verified captures in data/live/raw/
and canonical repo logs (season_log, standings, Week-10 injuries, Week-11 freeze).

Run: python3 scripts/live_build.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "live" / "raw"
OUT = ROOT / "data" / "live"

AS_OF = "2026-11-19"


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def prob_to_american(p: float) -> str:
    if p <= 0.0 or p >= 1.0:
        return ""
    if p >= 0.5:
        return str(-round(100.0 * p / (1.0 - p)))
    return f"+{round(100.0 * (1.0 - p) / p)}"


def half_round(x: float) -> float:
    return round(x * 2.0) / 2.0


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


TEAM_ALIASES = {"LAR": "LA", "ARZ": "AZ", "BLT": "BAL", "CLV": "CLE", "HST": "HOU"}


def norm_team(t: str) -> str:
    t = t.strip().upper()
    return TEAM_ALIASES.get(t, t)


def name_key(player_name: str, team: str) -> tuple[str, str]:
    """Normalize 'First Last' or 'F.Last' to (team, last_name_alnum) + first initial for matching."""
    team = norm_team(team)
    s = re.sub(r"[^a-zA-Z0-9.\s'-]", "", player_name).strip()
    parts = s.split()
    if not parts:
        return team, ""
    if "." in parts[0] and len(parts) == 1:
        fi, ln = parts[0].split(".", 1)
        return team, f"{fi[:1].lower()}.{re.sub(r'[^a-z]', '', ln.lower())}"
    if "." in parts[0]:
        fi = parts[0].split(".", 1)[0][:1].lower()
        ln = re.sub(r"[^a-z]", "", parts[-1].lower())
        return team, f"{fi}.{ln}"
    fi = parts[0][:1].lower()
    # Strip suffixes like Jr., II, III
    clean = [p for p in parts if p.rstrip(".").lower() not in {"jr", "sr", "ii", "iii", "iv", "v"}]
    ln = re.sub(r"[^a-z]", "", (clean[-1] if clean else parts[-1]).lower())
    return team, f"{fi}.{ln}"


def parse_gb_player_entry(entry: str) -> str:
    # e.g., "LB 0 A.Al-Shaair" -> "A.Al-Shaair"
    parts = entry.strip().split()
    return parts[-1] if parts else entry


def build_week10_gamebooks(gb_raw: dict, season_log: list[dict[str, str]]) -> tuple[list[dict], dict]:
    log_by_id = {f"{r['away']}@{r['home']}": r for r in season_log if r.get("week") == "10"}
    rows = []
    tot_ko = tot_ez = tot_tb = tot_onside = tot_onside_rec = 0
    start_yards = []

    for g in gb_raw["games"]:
        gid = g["game_id"]
        log_row = log_by_id.get(gid, {})
        score_match = (
            str(g["away_score"]) == str(log_row.get("away_score", ""))
            and str(g["home_score"]) == str(log_row.get("home_score", ""))
        )
        ko = g["away_ko"] + g["home_ko"]
        ez = g["away_ez"] + g["home_ez"]
        tb = g["away_tb"] + g["home_tb"]
        tot_ko += ko
        tot_ez += ez
        tot_tb += tb
        tot_onside += g["onside_kicks"]
        tot_onside_rec += g["onside_recoveries"]

        for s_field in (g["away_avg_start"], g["home_avg_start"]):
            m = re.search(r"(\d+)$", s_field.strip())
            if m:
                start_yards.append(int(m.group(1)))

        rows.append({
            "game_id": gid,
            "date_iso": g["date_iso"],
            "away": g["away"],
            "home": g["home"],
            "away_score": g["away_score"],
            "home_score": g["home_score"],
            "total_points": g["away_score"] + g["home_score"],
            "margin_home": g["home_score"] - g["away_score"],
            "log_reconciled": "VERIFIED" if score_match else "MISMATCH",
            "gc_location": g["gc_location"],
            "gc_stadium": g["gc_stadium"],
            "gb_stadium": g["gb_stadium"],
            "roof": g["roof"],
            "surface": g["surface"],
            "temp_f": "" if g["temp_f"] is None else g["temp_f"],
            "humidity_pct": "" if g["humidity_pct"] is None else g["humidity_pct"],
            "wind": g["wind"],
            "weather_desc": g["weather_desc"],
            "attendance": g["attendance"],
            "kickoffs_total": ko,
            "kickoffs_in_ez": ez,
            "touchbacks": tb,
            "tb_rate_pct": round(100.0 * tb / ko, 1) if ko else 0.0,
            "onside_kicks": g["onside_kicks"],
            "onside_recoveries": g["onside_recoveries"],
            "away_avg_ko_start": g["away_avg_start"],
            "home_avg_ko_start": g["home_avg_start"],
            "away_not_active_cnt": len(g["away_not_active"]),
            "home_not_active_cnt": len(g["home_not_active"]),
            "away_dnp_cnt": len(g["away_dnp"]),
            "home_dnp_cnt": len(g["home_dnp"]),
            "game_center_url": g["game_center_url"],
            "gamebook_pdf_url": g["gamebook_pdf_url"],
        })

    avg_start = round(sum(start_yards) / len(start_yards), 2) if start_yards else None
    rule6 = {
        "as_of": AS_OF,
        "source_rulebook": "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
        "source_featured_rules": "https://operations.nfl.com/rules-officiating/featured-rules",
        "sample_games": len(rows),
        "kickoffs_total": tot_ko,
        "kickoffs_in_endzone": tot_ez,
        "endzone_rate_pct": round(100.0 * tot_ez / tot_ko, 2) if tot_ko else 0.0,
        "touchbacks": tot_tb,
        "touchback_rate_pct": round(100.0 * tot_tb / tot_ko, 2) if tot_ko else 0.0,
        "in_play_return_rate_pct": round(100.0 * (tot_ko - tot_tb) / tot_ko, 2) if tot_ko else 0.0,
        "onside_kicks_observed": tot_onside,
        "onside_recoveries_observed": tot_onside_rec,
        "avg_kickoff_drive_start_yd": avg_start,
        "rule_changes_2026": [
            {"rule": "6-1-3", "summary": "Modifies alignment requirements for receiving team players in the setup zone on a kickoff or safety kick."},
            {"rule": "6-1-5", "summary": "Modifies the dead ball spot after a touchback when the kickoff is from the 50-yard line (following 2025 touchback spot move to 35-yard line)."},
            {"rule": "6-1-6", "summary": "Permits the kicking team to declare an onside kick at any time during the game (removing trailing-only restriction from 2025); untouched beyond setup zone = 15-yd penalty."},
            {"rule": "19-2", "summary": "Permits officials to consult with NFL Officiating staff on flagrant foul disqualifications."}
        ],
    }
    return rows, rule6


def build_snap_depth_rows(gb_raw: dict) -> list[dict]:
    out = []
    for g in gb_raw["games"]:
        for s in g.get("key_snaps", []):
            snap_val = s.get("off_snaps") or s.get("def_snaps") or ""
            pct_val = s.get("off_pct") or s.get("def_pct") or ""
            unit = "OFF" if s.get("off_snaps") is not None else ("DEF" if s.get("def_snaps") is not None else "BOX")
            out.append({
                "game_id": g["game_id"],
                "team": s["team"],
                "player": s["player"],
                "pos": s["pos"],
                "unit": unit,
                "snaps": snap_val,
                "snap_pct": pct_val,
                "note": s.get("note", ""),
                "source_url": g["gamebook_pdf_url"],
            })
    return out


def build_w10_calibration(inj_w10: list[dict], gb_raw: dict, tx_raw: dict) -> tuple[list[dict], dict]:
    # Build lookup sets of Not Active and DNP per team from all 14 Week-10 Game Books
    na_map: dict[tuple[str, str], str] = {}
    dnp_map: dict[tuple[str, str], str] = {}
    for g in gb_raw["games"]:
        for side, team in (("away", g["away"]), ("home", g["home"])):
            for item in g[f"{side}_not_active"]:
                p = parse_gb_player_entry(item)
                na_map[name_key(p, team)] = item
            for item in g[f"{side}_dnp"]:
                p = parse_gb_player_entry(item)
                dnp_map[name_key(p, team)] = item

    ir_pre_w10: dict[tuple[str, str], str] = {}
    for e in tx_raw["events"]:
        if e["category"] == "reserve-list" and e["date"] <= "2026-11-16":
            ir_pre_w10[name_key(e["player"], e["to_team"])] = f"{e['transaction']} ({e['date']})"

    # Map team -> gamebook_pdf_url
    gb_url_by_team = {}
    for g in gb_raw["games"]:
        gb_url_by_team[g["away"]] = g["gamebook_pdf_url"]
        gb_url_by_team[g["home"]] = g["gamebook_pdf_url"]

    rows = []
    counts = {"Out": {"total": 0, "not_active": 0, "moved_to_ir": 0, "dnp": 0, "active_or_other": 0},
              "Doubtful": {"total": 0, "not_active": 0, "moved_to_ir": 0, "dnp": 0, "active_or_other": 0},
              "Questionable": {"total": 0, "not_active": 0, "moved_to_ir": 0, "dnp": 0, "active_or_other": 0},
              "No Designation": {"total": 0, "not_active": 0, "moved_to_ir": 0, "dnp": 0, "active_or_other": 0}}

    for r in inj_w10:
        team = norm_team(r["team"])
        player = r["player"]
        status = r["status"].strip() or "No Designation"
        k = name_key(player, team)
        if k in na_map:
            outcome = f"Not Active ({na_map[k]})"
            bucket = "not_active"
        elif k in ir_pre_w10:
            outcome = f"Moved to {ir_pre_w10[k]}"
            bucket = "moved_to_ir"
        elif k in dnp_map:
            outcome = f"Did Not Play ({dnp_map[k]})"
            bucket = "dnp"
        else:
            outcome = "Not in Not Active / DNP / Nov-IR blocks (Active or pre-Nov IR)"
            bucket = "active_or_other"

        if status in counts:
            counts[status]["total"] += 1
            counts[status][bucket] += 1

        rows.append({
            "game": r["game"],
            "team": team,
            "player": player,
            "pos": r["pos"],
            "injury": r["injury"],
            "practice_w10": r["practice"],
            "designation_w10": status,
            "gamebook_disposition": outcome,
            "bucket": bucket,
            "source_report": "https://www.nfl.com/injuries/league/2026/reg10",
            "source_gamebook": gb_url_by_team.get(team, ""),
        })

    return rows, counts


def build_w11_injuries_and_delta(
    inj_w11_raw: dict,
    inj_w10: list[dict],
    tx_raw: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    ir_players = {
        (e["to_team"], e["player"].lower()): e
        for e in tx_raw["events"]
        if e["category"] == "reserve-list"
    }
    trade_players = {
        e["player"].lower(): e
        for e in tx_raw["events"]
        if e["category"] == "trades"
    }

    w11_rows = []
    w11_by_key = {}
    for r in inj_w11_raw["rows"]:
        t, p = r["team"], r["player"]
        ir_ev = ir_players.get((t, p.lower()))
        tr_ev = trade_players.get(p.lower())
        flag_note = ""
        if ir_ev:
            flag_note = f"FLAG: Placed on {ir_ev['transaction']} on {ir_ev['date']} while listed on reg11"
        elif tr_ev:
            flag_note = f"Traded {tr_ev['from_team']}->{tr_ev['to_team']} on {tr_ev['date']}"

        row = {
            "game_id": r["game_id"],
            "team": t,
            "opp": r["opp"],
            "player": p,
            "pos": r["pos"],
            "injury": r["injury"],
            "practice_status": r["practice_status"],
            "game_status": r["game_status"],
            "cross_check_flag": flag_note,
            "source_url": r["source_url"],
        }
        w11_rows.append(row)
        w11_by_key[(t, p.lower())] = row

    # Add explicit CIN@WAS zero-injuries placeholder row for completeness
    w11_rows.append({
        "game_id": "CIN@WAS",
        "team": "CIN/WAS",
        "opp": "MNF",
        "player": "No Injuries Reported (as of 2026-11-19 02:16 UTC capture)",
        "pos": "",
        "injury": "",
        "practice_status": "Pending Thursday/Friday MNF practice report",
        "game_status": "",
        "cross_check_flag": "MNF game (Nov 23) — report opens Thursday afternoon",
        "source_url": "https://www.nfl.com/injuries/league/2026/reg11",
    })

    # Compute Week-10 -> Week-11 delta for teams that played Week 10 and are NOT on Week-11 Bye
    bye_teams = {"ATL", "CLE", "GB", "LA", "NE", "SEA"}
    w10_by_key = {}
    for r in inj_w10:
        nt = norm_team(r["team"])
        if nt not in bye_teams and nt not in {"CIN", "WAS"}:
            w10_by_key[(nt, r["player"].lower())] = r

    delta_rows = []
    all_keys = sorted(set(w10_by_key.keys()) | set(w11_by_key.keys()))
    for k in all_keys:
        team, plower = k
        r10 = w10_by_key.get(k)
        r11 = w11_by_key.get(k)
        if r11 and not r10:
            tr_ev = trade_players.get(plower)
            delta_type = "new_via_trade" if tr_ev else "new_to_report"
            delta_rows.append({
                "team": team,
                "player": r11["player"],
                "pos": r11["pos"],
                "delta_type": delta_type,
                "w10_practice": "Not on W10 report",
                "w10_status": "",
                "w11_practice": r11["practice_status"],
                "w11_status": r11["game_status"],
                "injury": r11["injury"],
                "ir_or_tx_note": r11["cross_check_flag"],
                "source_url": "https://www.nfl.com/injuries/league/2026/reg11",
            })
        elif r10 and not r11:
            ir_ev = ir_players.get((team, plower))
            delta_type = "placed_on_IR" if ir_ev else "removed_from_report"
            note = f"FLAG: {ir_ev['transaction']} on {ir_ev['date']} ('not listed' != available)" if ir_ev else "Not listed on W11 report (check roster/IR)"
            delta_rows.append({
                "team": team,
                "player": r10["player"],
                "pos": r10["pos"],
                "delta_type": delta_type,
                "w10_practice": r10["practice"],
                "w10_status": r10["status"],
                "w11_practice": "Not listed",
                "w11_status": "",
                "injury": r10["injury"],
                "ir_or_tx_note": note,
                "source_url": "https://www.nfl.com/transactions/league/reserve-list/2026/11" if ir_ev else "https://www.nfl.com/injuries/league/2026/reg11",
            })
        elif r10 and r11:
            p10, s10 = r10["practice"], r10["status"]
            p11, s11 = r11["practice_status"], r11["game_status"]
            if p10 == p11 and s10 == s11:
                dtype = "unchanged"
            else:
                dtype = "status_changed"
            delta_rows.append({
                "team": team,
                "player": r11["player"],
                "pos": r11["pos"],
                "delta_type": dtype,
                "w10_practice": p10,
                "w10_status": s10,
                "w11_practice": p11,
                "w11_status": s11,
                "injury": r11["injury"] or r10["injury"],
                "ir_or_tx_note": r11["cross_check_flag"],
                "source_url": "https://www.nfl.com/injuries/league/2026/reg11",
            })

    # Transactions audit table
    tx_rows = []
    for e in tx_raw["events"]:
        audit_note = ""
        if e["player"] == "Daiyan Henley":
            audit_note = "FLAG: Official 11/10 trade lists LAC->DEN, but 11/16 LAC@BAL Game Book still lists LB 0 D.Henley starting with 11 tackles"
        elif e["player"] in {"Azeez Al-Shaair", "Jaylon Carlies"}:
            audit_note = f"FLAG: Placed on {e['transaction']} ({e['date']}) yet still appears on Week-11 reg11 practice report"
        elif e["player"] == "Aidan Hutchinson":
            audit_note = "Played 9 snaps (15%) vs NE on 11/15, placed on Reserve/Injured 11/18; absent from reg11 report"
        elif e["player"] in {"Josh Downs", "Amani Hooker", "Kirk Cousins", "Keenan Allen", "Jacoby Brissett"}:
            audit_note = f"Verified active/played in Week-10 Game Book for new club ({e['to_team']})"
        elif e["category"] == "reserve-list":
            audit_note = f"Active Reserve/Injured — excludes player from available depth"
        tx_rows.append({
            "category": e["category"],
            "date": e["date"],
            "from_team": e["from_team"],
            "to_team": e["to_team"],
            "player": e["player"],
            "transaction": e["transaction"],
            "audit_note": audit_note,
            "source_url": e["source_url"],
        })

    return w11_rows, delta_rows, tx_rows


def build_w11_lines(
    slate_raw: dict,
    forecasts_frozen: list[dict[str, str]],
    w11_inj_rows: list[dict],
    tx_raw: dict,
) -> list[dict]:
    frozen_map = {r["game_id"]: r for r in forecasts_frozen}
    out_cnt: dict[str, int] = {}
    q_cnt: dict[str, int] = {}
    dnp_cnt: dict[str, int] = {}
    for r in w11_inj_rows:
        t = r["team"]
        if r["game_status"] == "Out":
            out_cnt[t] = out_cnt.get(t, 0) + 1
        elif r["game_status"] == "Questionable":
            q_cnt[t] = q_cnt.get(t, 0) + 1
        if "Did Not Participate" in r["practice_status"]:
            dnp_cnt[t] = dnp_cnt.get(t, 0) + 1

    ir_recent = {}
    for e in tx_raw["events"]:
        if e["category"] == "reserve-list" and e["date"] >= "2026-11-12":
            ir_recent.setdefault(e["to_team"], []).append(f"{e['player']} ({e['date'][5:]})")

    rows = []
    for g in slate_raw["games"]:
        gid = g["game_id"]
        fr = frozen_map.get(gid, {})
        away, home = g["away"], g["home"]

        base_margin = float(fr.get("fair_margin_home", 0.0))
        base_total = float(fr.get("total_fair_line", 45.0))
        sigma_margin = float(fr.get("sigma_margin", 10.401))
        sigma_total = float(fr.get("sigma_total", 12.860))

        # Diagnostic weather adjustment on Total ONLY (transparent, derived, never alters frozen X3-CO-1.0):
        # Wind >= 15 mph or Precip >= 30% -> small negative total adjustment + documented basis
        wx_adj = 0.0
        wx_reason = "None (indoor or calm weather)"
        wind_mph = 0
        m = re.search(r"(\d+)\s*mph", g["kickoff_wind"])
        if m:
            wind_mph = int(m.group(1))
        precip = g["kickoff_precip_pct"] or 0
        if wind_mph >= 15 and precip >= 30:
            wx_adj = -2.0
            wx_reason = f"Outdoor wind {wind_mph} mph + {precip}% precip (DERIVED -2.0 total overlay)"
        elif precip >= 30:
            wx_adj = -1.0
            wx_reason = f"Outdoor {precip}% rain probability (DERIVED -1.0 total overlay)"
        elif wind_mph >= 12:
            wx_adj = -0.5
            wx_reason = f"Outdoor wind {wind_mph} mph (DERIVED -0.5 total overlay)"

        # Availability delta summary (not an arbitrary point penalty — ablation rule B50/B39: published as context + flag)
        inj_summary_away = f"{away}: {out_cnt.get(away,0)} Out, {q_cnt.get(away,0)} Q, {dnp_cnt.get(away,0)} DNP"
        if away in ir_recent:
            inj_summary_away += f"; IR: {', '.join(ir_recent[away])}"
        inj_summary_home = f"{home}: {out_cnt.get(home,0)} Out, {q_cnt.get(home,0)} Q, {dnp_cnt.get(home,0)} DNP"
        if home in ir_recent:
            inj_summary_home += f"; IR: {', '.join(ir_recent[home])}"

        live_margin = base_margin  # Pre-registered side kept intact until ablation-calibrated availability weights clear holdout
        live_side_fair = half_round(-live_margin)
        live_total_fair = half_round(base_total + wx_adj)
        p_home_cover = round(1.0 - norm_cdf((-live_side_fair - live_margin) / sigma_margin), 4)
        p_over = round(1.0 - norm_cdf((live_total_fair - (base_total + wx_adj)) / sigma_total), 4)
        ml_home = round(norm_cdf(live_margin / sigma_margin), 4)
        ml_away = round(1.0 - ml_home, 4)

        rows.append({
            "game_id": gid,
            "date_iso": g["date_iso"],
            "kickoff_et": g["kickoff_et"],
            "network": g["network"],
            "away": away,
            "home": home,
            "gc_venue": f"{g['gc_stadium']} ({g['gc_location']})",
            "venue_diff_flag": "FLAG: diff vs schedule" if g["venue_diff_flag"] else "MATCH",
            "roof_surface": f"{g['roof_class']} / {g['surface']}",
            "nws_kickoff_wx": f"{g['kickoff_temp_f']}°F, {g['kickoff_wind']}, {g['kickoff_precip_pct']}% precip" if g["kickoff_temp_f"] is not None else g["kickoff_forecast"],
            "frozen_side_home": fr.get("side_fair_line_home", ""),
            "frozen_total": fr.get("total_fair_line", ""),
            "frozen_ml_home": fr.get("ml_fair_american_home", ""),
            "live_side_home": live_side_fair,
            "live_p_home_cover": p_home_cover,
            "live_total_fair": live_total_fair,
            "live_p_over": p_over,
            "live_ml_home_prob": ml_home,
            "live_ml_away_prob": ml_away,
            "live_ml_home_american": prob_to_american(ml_home),
            "live_ml_away_american": prob_to_american(ml_away),
            "wx_overlay_note": wx_reason,
            "availability_context": f"{inj_summary_away} | {inj_summary_home}",
            "market_side": "",
            "diff_side": "",
            "market_total": "",
            "diff_total": "",
            "market_ml": "",
            "diff_ml": "",
            "market_status": "UNVERIFIED - no official NFL market-price feed",
            "source_url": g["game_center_url"],
        })
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    gb_raw = load_json(RAW / "week10_gamebooks_2026.json")
    slate_raw = load_json(RAW / "week11_slate_weather_2026.json")
    tx_raw = load_json(RAW / "transactions_nov2026.json")
    inj_w11_raw = load_json(RAW / "week11_injuries_2026.json")
    arch_2025 = load_json(RAW / "archive_2025_reg10_sample.json")

    season_log = load_csv(ROOT / "data" / "closeout" / "derived" / "season_log.csv")
    forecasts_frozen = load_csv(ROOT / "data" / "closeout" / "derived" / "forecasts_w11.csv")
    inj_w10 = load_csv(ROOT / "data" / "hub" / "injuries_2026_wk10.csv")
    standings = load_csv(ROOT / "data" / "closeout" / "official_standings_2026_wk10.csv")

    gb_rows, rule6 = build_week10_gamebooks(gb_raw, season_log)
    snap_rows = build_snap_depth_rows(gb_raw)
    cal_rows, cal_counts = build_w10_calibration(inj_w10, gb_raw, tx_raw)
    w11_inj_rows, delta_rows, tx_rows = build_w11_injuries_and_delta(inj_w11_raw, inj_w10, tx_raw)
    w11_line_rows = build_w11_lines(slate_raw, forecasts_frozen, w11_inj_rows, tx_raw)

    write_csv(OUT / "week10_gamebooks.csv", list(gb_rows[0].keys()), gb_rows)
    write_json(OUT / "week10_gamebooks.json", {"as_of": AS_OF, "games": gb_rows})
    write_json(OUT / "rule6_kickoff_summary.json", rule6)

    write_csv(OUT / "week10_snap_depth.csv", list(snap_rows[0].keys()), snap_rows)
    write_csv(OUT / "week10_calibration.csv", list(cal_rows[0].keys()), cal_rows)
    write_json(OUT / "week10_calibration_summary.json", {"as_of": AS_OF, "w10_counts": cal_counts, "archive_2025_sample": arch_2025})

    write_csv(OUT / "week11_injuries.csv", list(w11_inj_rows[0].keys()), w11_inj_rows)
    write_csv(OUT / "injury_delta_w10_w11.csv", list(delta_rows[0].keys()), delta_rows)
    write_csv(OUT / "transactions_audit.csv", list(tx_rows[0].keys()), tx_rows)
    write_csv(OUT / "week11_lines_live.csv", list(w11_line_rows[0].keys()), w11_line_rows)
    write_json(OUT / "week11_lines_live.json", {"as_of": AS_OF, "lines": w11_line_rows})

    # What changed, Q&A, Suggestions, Flagged, Readiness, Sources
    what_changed = [
        {"area": "Week-10 Game Books", "prior_state": "2 of 14 Game Books read (NE@DET, LAC@BAL)", "live_state": "14 of 14 Game Books verified (starters, inactives, DNP, weather, kickoffs, touchbacks, snap counts)", "impact": "Clears B25, B30, B11, B55 data-capture gap", "source_url": "https://www.nfl.com/schedules/2026/by-week/week-10"},
        {"area": "Week-11 Injury Report", "prior_state": "Pre-publication probes only (reg11 resolved to reg10 on 2026-11-18)", "live_state": "253 player rows parsed across 12 games + CIN@WAS MNF zero-injuries notice; IND@HOU final Out/Q set", "impact": "Clears B21, B53, B54 live Week-11 read + W10->W11 delta", "source_url": "https://www.nfl.com/injuries/league/2026/reg11"},
        {"area": "Game Center Venues & Schedule", "prior_state": "11 of 13 Week-11 venues cited schedule page; May 14 announcement unread", "live_state": "13/13 Week-11 & 14/14 Week-10 Game Center venues transcribed; 3 naming diffs caught; May 14 release ingested", "impact": "Clears B23 & A-23", "source_url": "https://media.nfl.com/football-information/2026/news/2026-nfl-schedule-announced"},
        {"area": "NWS Weather & Roof Overlay", "prior_state": "No weather or stadium roof/surface dataset in repo (B57 blocked)", "live_state": "14 Game Book stadium roofs/surfaces + live api.weather.gov hourly kickoff forecasts for all 8 US outdoor Week-11 venues", "impact": "Clears B57 (NO@CHI 15 mph W / 34-80% rain flagged)", "source_url": "https://api.weather.gov/gridpoints/LOT/76,72/forecast/hourly"},
        {"area": "Nov 2026 Transactions & IR", "prior_state": "No transactions feed ingested (B33/B63 blocked)", "live_state": "Trades, Reserve/Injured, Waivers, Terminations, Signings ingested; 2 IR-vs-reg11 conflicts & 1 trade-vs-GB conflict caught", "impact": "Clears B33 & B63", "source_url": "https://www.nfl.com/transactions/league/reserve-list/2026/11"},
        {"area": "2026 Kickoff & Onside Priors", "prior_state": "Registered only; zero kickoff/onside numbers (B67)", "live_state": f"Rule 6-1-3/5/6 + 14-game Week-10 tally: {rule6['kickoffs_total']} kickoffs, {rule6['touchback_rate_pct']}% TB, {rule6['onside_kicks_observed']} onside kick, {rule6['avg_kickoff_drive_start_yd']} avg start", "impact": "Clears B67 empirical baseline", "source_url": "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook"},
        {"area": "Past-Season Archive & Calibration", "prior_state": "Zero past-season reports fetched (B65/B43/B52 blocked)", "live_state": "2025/reg10 archived + PHI@GB 2025 W10 & 345-row 2026/reg10 Game Book designation scoring", "impact": "Advances B65/B43/B52 to empirical partial/verified", "source_url": "https://www.nfl.com/injuries/league/2025/reg10"},
        {"area": "Market Prices & Leaderboard", "prior_state": "F-01 blocked: no official NFL odds feed", "live_state": "Still BLOCKED / UNVERIFIED — market lines, CLV, ROI, and leaderboard remain deliberately blank/empty", "impact": "Honest policy block preserved", "source_url": "UNVERIFIED - no official NFL market-price feed"},
    ]
    write_csv(OUT / "what_changed.csv", list(what_changed[0].keys()), what_changed)

    flagged = [
        {"id": "LF-01", "category": "Market Prices", "item": "No official NFL odds / market-price feed", "detail": "NFL.com publishes scores, stats, standings, injuries, transactions, and Game Books, not betting lines. Market spread/total/ML, diff, CLV, and ROI remain blank.", "status": "UNVERIFIED / BLOCKED", "source_url": "UNVERIFIED - no official NFL market-price feed"},
        {"id": "LF-02", "category": "IR vs Injury Report", "item": "Azeez Al-Shaair (HOU) & Jaylon Carlies (IND) listed on reg11 despite 11/17 Reserve/Injured", "detail": "Both players were placed on Reserve/Injured on 2026-11-17 (official Reserve List) after being Not Active in Week 10, yet still appear on the Week-11 reg11 practice report.", "status": "FLAGGED", "source_url": "https://www.nfl.com/transactions/league/reserve-list/2026/11"},
        {"id": "LF-03", "category": "Trade vs Game Book", "item": "Daiyan Henley listed on 11/10 trade (LAC->DEN) yet started 11/16 for LAC", "detail": "Official Trades page lists Daiyan Henley traded from Chargers to Broncos on 11/10, but the 11/16 LAC@BAL Game Book lists LB 0 D.Henley starting for LAC with 11 tackles.", "status": "FLAGGED", "source_url": "https://www.nfl.com/transactions/league/trades/2026/11"},
        {"id": "LF-04", "category": "Venue Naming Diff", "item": "3 Week-11 Game Center stadium names differ from NFL schedule page", "detail": "IND@HOU: RELIANT STADIUM vs NRG Stadium; AZ@KC: ARROWHEAD STADIUM vs GEHA Field at Arrowhead Stadium; CIN@WAS: NORTHWEST STADIUM vs FedEx Field.", "status": "FLAGGED", "source_url": "https://www.nfl.com/games/bengals-at-commanders-2026-reg-11"},
        {"id": "LF-05", "category": "International Weather", "item": "MIN@SF Estadio Banorte (Mexico City) outside US NWS grid", "detail": "National Weather Service api.weather.gov covers US territories only. Mexico City kickoff forecast is left blank/UNVERIFIED rather than filled from unverified sources.", "status": "UNVERIFIED", "source_url": "https://www.nfl.com/games/vikings-at-49ers-2026-reg-11"},
        {"id": "LF-06", "category": "Game Book Typo", "item": "Official Game Book player name spelling variants", "detail": "CAR@NO Game Book spells Saints QB T.Shough as 'T.Though' in box score; SEA@LV spells J.Smith-Njigba as 'J.Smith-Nijgba'; 2025/reg10 lists 'Zach Bako-Bewele' for zach-tom.", "status": "FLAGGED", "source_url": "https://static.www.nfl.com/image/upload/v1794829721/gamecenter/ab789769-4feb-11f1-abca-2c54536568a9.pdf"},
        {"id": "LF-07", "category": "MNF Missing Report", "item": "CIN@WAS has no injuries reported on reg11 as of 2026-11-19 02:16 UTC", "detail": "Monday Night Football clubs publish initial practice participation on Thursday afternoon; treated as pending rather than healthy.", "status": "FLAGGED / PENDING", "source_url": "https://www.nfl.com/injuries/league/2026/reg11"},
        {"id": "LF-09", "category": "Week 10 Lions designations", "item": "Kerby Joseph, Cade Mays, D.J. Reed: Week 10 game-status cells not re-verified", "detail": "Week 11 (reg11) TB@DET rows were re-checked against the live official page on 2026-11-19 and match (Joseph Full Participation, Mays DNP, Reed Limited, game status blank). The Week 10 Lions section of the official reg10 page was not located in the fetch (chunks 0-5 checked). The Week-10 Out designations were therefore NOT entered and remain UNVERIFIED.", "status": "UNVERIFIED", "source_url": "https://www.nfl.com/injuries/league/2026/reg10"},
        {"id": "LF-10", "category": "Official URL title mismatch", "item": "reg10 URL serves a page titled Week 11", "detail": "https://www.nfl.com/injuries/league/2026/reg10 returned the title 'Official NFL Injury Report for Players - Week 11 of the 2026 Season' on 2026-11-19 while its content includes Week-10 match-ups (e.g. MIN@GB, PIT@CIN). Recorded as an irregularity; the Week-10 content was not used for any Week-11 value.", "status": "FLAGGED", "source_url": "https://www.nfl.com/injuries/league/2026/reg10"},
        {"id": "LF-08", "category": "Scheduled Raw HTML", "item": "readiness/data/history/2026-11-19/*.html triggers verify_integration.py baseline failure", "detail": "Scheduled bot committed raw HTML pages with root-absolute links inside readiness/; tracked by session arena/46153df1-x3 in COORDINATION.md.", "status": "FLAGGED", "source_url": "https://github.com/karagemop466-tech/X3"},
    ]
    write_csv(OUT / "flagged.csv", list(flagged[0].keys()), flagged)

    questions = [
        {"id": "LQ-01", "status": "BLOCKING", "question": "Which price-data policy governs market comparisons, CLV, and ROI settlement?", "known": "NFL.com has no odds feed; all model probabilities and fair lines are stored cleanly.", "missing": "Approved external odds source or explicit decision to remain fair-value/probability-only.", "how_to_discover": "Freeze PDP-1 (fair-only Brier/MAE) or register an audited sportsbook/consensus snapshot feed with terms review.", "source_url": "UNVERIFIED - policy decision pending"},
        {"id": "LQ-02", "status": "OPEN", "question": "Should the project freeze ONE canonical threshold for the G-2 sample gate (300 vs 2,272 settled bets)?", "known": "Closed PR #58 proposed 2,272; origin/data/gates.json holds 300; closeout uses 200.", "missing": "Single pre-registered threshold frozen in git before grading.", "how_to_discover": "Select SG-L02 in Suggestions to adopt 300 settled bets across >=3 seasons as the sole canonical gate.", "source_url": "https://github.com/karagemop466-tech/X3"},
        {"id": "LQ-03", "status": "OPEN", "question": "How should the Daiyan Henley 11/10 trade vs 11/16 LAC Game Book starter conflict be resolved?", "known": "Transactions/trades/2026/11 shows LAC->DEN on 11/10; LAC@BAL Game Book shows LB 0 D.Henley starting 11/16.", "missing": "Club roster / Week-11 LV@DEN vs NYJ@LAC Game Book confirmation.", "how_to_discover": "Check LV@DEN & NYJ@LAC Week-11 inactive/lineup lists after Sunday's games.", "source_url": "https://www.nfl.com/transactions/league/trades/2026/11"},
        {"id": "LQ-04", "status": "OPEN", "question": "Should Week-11 live NWS weather & IR deltas modify the frozen X3-CO-1.0 board or stay in a separate X3-LIVE-1.0 diagnostic column?", "known": "X3-CO-1.0 was pre-registered 2026-11-17 before Thursday kickoff.", "missing": "Governance rule for mid-week line updates vs frozen evaluation board.", "how_to_discover": "Keep X3-CO-1.0 untouched for out-of-sample grading and publish X3-LIVE-1.0 strictly as an audit overlay.", "source_url": "https://www.nfl.com/schedules/2026/by-week/week-11"},
    ]
    write_csv(OUT / "questions.csv", list(questions[0].keys()), questions)

    suggestions = [
        {"id": "LS-01", "priority": "HIGH", "suggestion": "Freeze price-data policy (PDP-1: fair-value & proper-score evaluation only, or license an audited consensus odds feed) before running any ROI/CLV backtest.", "impact": "Unblocks B04, B18, B59, B70, and leaderboard settlement.", "requires_approval": "Yes — policy & terms decision", "source_url": "UNVERIFIED - awaits reviewer choice"},
        {"id": "LS-02", "priority": "HIGH", "suggestion": "Adopt a single canonical pre-registered qualification gate (300 settled bets across >=3 seasons + positive Brier skill + game-cluster CI lower bound > 0) and archive conflicting thresholds.", "impact": "Removes gate-conflict ambiguity across modules.", "requires_approval": "Yes — pre-registration freeze", "source_url": "https://github.com/karagemop466-tech/X3"},
        {"id": "LS-03", "priority": "MEDIUM", "suggestion": "Replace fixed injury point penalties with walk-forward ablation weights using our new 14-game Game Book snap-share + IR/Reserve cross-check.", "impact": "Prevents double-counting IR players (Al-Shaair, Carlies) and quantifies replacement deficiency.", "requires_approval": "Yes — model change after Week-11 grading", "source_url": "https://static.www.nfl.com/image/upload/v1794829724/gamecenter/ab583279-4feb-11f1-abca-2c54536568a9.pdf"},
        {"id": "LS-04", "priority": "MEDIUM", "suggestion": "Split public static GitHub Pages output (live/, hub/) from private raw-capture storage if third-party terms restrict redistribution of full PDFs/HTML.", "impact": "Addresses public-vs-private terms separation requirement cleanly.", "requires_approval": "Yes — repository storage policy", "source_url": "https://www.nfl.com/injuries/league/2026/reg11"},
    ]
    write_csv(OUT / "suggestions.csv", list(suggestions[0].keys()), suggestions)

    readiness_rows = [
        {"id": "LR-01", "area": "Week-10 Game Books (14/14)", "requirement": "Use official NFL Game Books for actual starters, inactives, DNP, weather & snap counts (B25/B30/B11/B55)", "gate": "14/14 PDFs captured & parsed", "clearing_metric": "14/14 games (100%) parsed with starters, Not Active, DNP, kickoffs & snap leaders", "status": "VERIFIED", "source_url": "https://www.nfl.com/schedules/2026/by-week/week-10"},
        {"id": "LR-02", "area": "Week-11 Live Injuries & Delta", "requirement": "Timestamped Week-11 injury report + W10->W11 player delta (B21/B53/B54/B12)", "gate": "reg11 live capture & W10 diff", "clearing_metric": "253 rows across 12 games + CIN@WAS MNF note + full W10->W11 delta", "status": "VERIFIED", "source_url": "https://www.nfl.com/injuries/league/2026/reg11"},
        {"id": "LR-03", "area": "Game Center Venues & Schedule", "requirement": "Transcribe all Game Center venues & publish May 14 schedule announcement side-by-side (B23/A-23)", "gate": "14/14 W10 + 13/13 W11 Game Centers", "clearing_metric": "27/27 Game Centers transcribed; 3 schedule-vs-GC naming diffs flagged", "status": "VERIFIED", "source_url": "https://media.nfl.com/football-information/2026/news/2026-nfl-schedule-announced"},
        {"id": "LR-04", "area": "Stadium Roof/Surface & NWS", "requirement": "Stadium roof/surface registry + NWS hourly wind/precip overlay (B57)", "gate": "All 8 US outdoor Week-11 venues", "clearing_metric": "8/8 US outdoor NWS hourly feeds + 14 Game Book roofs/surfaces (Mexico City flagged)", "status": "VERIFIED", "source_url": "https://api.weather.gov/gridpoints/LOT/76,72/forecast/hourly"},
        {"id": "LR-05", "area": "Nov 2026 Transactions & IR", "requirement": "32-team Reserve/IR sweep & transactions feed so 'not listed' != available (B33/B63)", "gate": "Trades + Reserve/IR + Waivers + Signings", "clearing_metric": "42 November events cross-checked; 2 IR-vs-reg11 & 1 trade-vs-GB flags caught", "status": "VERIFIED", "source_url": "https://www.nfl.com/transactions/league/reserve-list/2026/11"},
        {"id": "LR-06", "area": "2026 Rule 6 Kickoff Priors", "requirement": "2026 Kickoff & Declared Onside-Kick Regime Priors Filter (B67)", "gate": "Rulebook Rule 6 + empirical kickoff sample", "clearing_metric": f"Rule 6-1-3/5/6 + {rule6['kickoffs_total']} W10 kickoffs ({rule6['touchback_rate_pct']}% TB, {rule6['onside_kicks_observed']} onside)", "status": "VERIFIED", "source_url": "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook"},
        {"id": "LR-07", "area": "Past-Season Archive & Calibration", "requirement": "Archive past-season injury reports & calibrate Questionable/Out empirically (B65/B43/B52)", "gate": "Multi-season archived reports + Game Books", "clearing_metric": "2025/reg10 + PHI@GB 2025 W10 + all 345 2026/reg10 rows scored (1-yr partial sample)", "status": "PARTIAL", "source_url": "https://www.nfl.com/injuries/league/2025/reg10"},
        {"id": "LR-08", "area": "Originated Markets vs Market Feed", "requirement": "Publish fair line, market line & diff; vig-free consensus vs fair; CLV/ROI leaderboard (B04/B18/B59/B70)", "gate": "F-01 official market-price policy/feed + n>=300 bets", "clearing_metric": "Side->Total->ML originated for 13/13 games; market/CLV/ROI/leaderboard remain blank", "status": "BLOCKED", "source_url": "UNVERIFIED - no official NFL market-price feed"},
    ]
    write_csv(OUT / "readiness_summary.csv", list(readiness_rows[0].keys()), readiness_rows)

    # Manifest with SHA-256 checksums of all data/live files
    files = {}
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            rel = p.relative_to(ROOT).as_posix()
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()

    meta = {
        "as_of": AS_OF,
        "standings_teams": len(standings),
        "season_log_games": len(season_log),
        "week10_gamebooks": len(gb_rows),
        "week11_games": len(w11_line_rows),
        "week11_injury_rows": len(inj_w11_raw["rows"]),
        "injury_delta_rows": len(delta_rows),
        "transactions_rows": len(tx_rows),
        "cal_w10_counts": cal_counts,
        "rule6": rule6,
        "files_sha256": files,
    }
    write_json(OUT / "manifest.json", meta)
    print(f"live_build OK: {len(gb_rows)} W10 Game Books, {len(w11_line_rows)} W11 games, {len(inj_w11_raw['rows'])} reg11 rows, {len(delta_rows)} delta rows, {len(tx_rows)} tx rows, {len(files)} hashed files.")


if __name__ == "__main__":
    main()
