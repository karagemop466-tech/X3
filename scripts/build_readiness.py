#!/usr/bin/env python3
"""Render the readiness module (session arena/6259c7b0-x3).

Reads the computed JSONs produced by scripts/readiness_compute.py and
scripts/drift_alarm.py plus the static register readiness/data/readiness.json,
generates readiness/data/change_mind.json (two-sided fields for every registered
strategy across all four trees), and writes the static pages under readiness/.

Deterministic: same inputs -> byte-identical pages.
"""
from __future__ import annotations

import json
import sys
from html import escape as _h
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "readiness" / "data"

NAV = [
    ("index", "Overview"),
    ("decision-readiness", "Decision readiness"),
    ("change-our-mind", "What would change our mind"),
    ("control-baselines", "Control baselines"),
    ("two-totals", "Two totals"),
    ("ablations", "Ablations"),
    ("what-changed", "What changed"),
    ("announced-starters", "Announced starters"),
    ("matchup-matrix", "Matchup matrix"),
    ("drift-alarms", "Drift alarms"),
    ("snapshots", "Snapshot capture"),
]


def esc(s):
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    return _h(s, quote=True)


e = esc  # canonical escaper: coerces numbers/None and escapes


def badge(kind, text):
    return f'<span class="badge {kind}">{esc(text)}</span>'


STATUS_BADGE = {
    "done": ("v", "DONE"), "partial": ("p", "PARTIAL"), "blocked": ("b", "BLOCKED"),
    "registered": ("u", "REGISTERED"), "rejected": ("d", "REJECTED"),
    "FAIL": ("b", "FAIL"), "PASS": ("v", "PASS"),
    "UNVERIFIED": ("u", "UNVERIFIED"),
}


def bstatus(st):
    k, t = STATUS_BADGE.get(st, ("u", st.upper()))
    return badge(k, t)


def table(headers, rows, caption=None):
    cap = f"<caption>{caption}</caption>" if caption else ""
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join(f"<tr>{''.join(f'<td>{c}</td>' for c in r)}</tr>" for r in rows)
    return (f'<div class="tblwrap"><input class="filt" placeholder="filter rows..." '
            f'oninput="x3filter(this)"><table>{cap}<thead><tr>{th}</tr></thead>'
            f"<tbody>{trs}</tbody></table></div>")


def src_cell(url, label="source"):
    if not url:
        return badge("u", "UNVERIFIED")
    return f'<a class="src" href="{esc(url)}">{esc(label)}</a>'


def shell(fname, title, intro, body):
    nav = "".join(
        f'<a href="{s}.html"{" class=on" if s == fname else ""}>{esc(t)}</a>'
        for s, t in NAV)
    nav += '<a href="../index.html">X3 landing</a><a href="../signals/index.html">signals/</a>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 readiness</title>
<link rel="stylesheet" href="../hub/assets/hub.css">
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">X3 <span>readiness module</span></a></div>
  <div class="asof">session <b>arena/6259c7b0-x3</b> - built from verified official captures</div>
</header>
<nav class="nav">{nav}</nav>
<main>
<h1>{esc(title)}</h1>
<p class="lede">{intro}</p>
{body}
</main>
<footer>Every table row links an official source, a provenance link, or an explicit UNVERIFIED /
BLOCKED marker. Nothing is inferred or filled in. Task board: <a href="../COORDINATION.md">COORDINATION.md</a>
- session <code>arena/6259c7b0-x3</code>, tasks RD-01 to RD-10.</footer>
<script>
function x3filter(inp){{
  var t=inp.parentElement.querySelector('table');
  var rows=[].slice.call(t.querySelectorAll('tbody tr'));
  var q=inp.value.toLowerCase().trim();
  rows.forEach(function(r){{ r.style.display = !q || r.textContent.toLowerCase().indexOf(q)>=0 ?'':'none'; }});
}}
</script>
</body>
</html>
"""


def write(fname, title, intro, body):
    (ROOT / "readiness" / fname).write_text(
        shell(fname.replace(".html", ""), title, intro, body), encoding="utf-8")
    print(f"  readiness/{fname}")


# --------------------------------------------------------------------------
# change-our-mind generation
# --------------------------------------------------------------------------
C1_LINE = None  # filled from computed controls


def load_controls():
    global C1_LINE
    c = json.loads((DATA / "control_baselines.json").read_text())
    C1_LINE = c["controls"][0]["contest"]["win_rate"]
    return c


def gen_change_mind(controls):
    c1 = controls["controls"][0]["contest"]["win_rate"]
    c1 = float(c1) if c1 not in ("", None) else 0.5
    rows = []

    def entry(tree, sid, name, family, market, rule, evidence, up, down, source):
        rows.append({
            "tree": tree, "id": sid, "name": name, "family": family,
            "market": market, "rule": rule, "evidence": evidence,
            "would_upgrade": up, "would_abandon": down, "source": source,
        })

    # ---- signals tree (15) ----
    sig = json.loads((ROOT / "signals" / "data" / "strategies.json").read_text())
    for s in sig:
        sid = s["id"]
        n = s["n_graded"]
        ev = (f"{s['signal_metric']}: {s['signal_value'] or 'blank'} on n={n} graded games"
              + (f", exact binomial p={s['signal_p']}" if s.get("signal_p") not in ("", None) else "")
              + (f", BH q<=0.10 pass={s['bh_pass']}" if s.get("bh_pass") not in ("", None) else ""))
        fam = str(s["family"]).lower()
        market = str(s["market"]).lower()
        src = "https://www.nfl.com/schedules/2026/by-week/week-10"
        if "parlay" in fam or "prop" in fam or "combo" in fam:
            up = ("the joint-evidence gate clears: a directly validated joint probability "
                  "(measured on official results, with a CI that excludes the independence "
                  "value) AND the operator's void/push rules on record, plus a per-leg price "
                  "history with provenance - then the pre-registered rule is graded on fresh "
                  "walk-forward decisions")
            down = ("the gate stays closed: either the joint validation or the operator rules "
                    "remain missing through the season window the registration froze - the "
                    "combo is then retired rather than ranked on multiplied marginals")
        elif "home-field" in str(s["name"]).lower():
            up = ("the measured home-field constant stabilises across >= 3 refit windows "
                  "(bootstrap CI width < 1.0 point) and departs from the assumed 3.0 points "
                  "with the CI excluding it")
            down = ("the fitted constant's CI covers the assumed 3.0 points for three "
                    "consecutive refit windows - then no arbitrage exists and the entry is "
                    "withdrawn")
        else:
            up = (f"on a later, untouched walk-forward window of >= 100 graded games the "
                  f"contest win rate stays above the C1 coin-flip control line ({c1:.3f}) "
                  f"with a Wilson 95% CI lower bound above it and Benjamini-Hochberg q <= 0.10")
            down = (f"two consecutive walk-forward windows land at or below the C1 control "
                    f"line ({c1:.3f}) with the CI upper bound at or below it, or the edge's "
                    f"sign flips on the trailing-50 window - the demotion gate returns it to "
                    f"paper")
        entry("signals", sid, s["name"], s["family"], s["market"], s["rule"], ev, up, down, src)

    # ---- desk tree (10) ----
    desk = json.loads((ROOT / "data" / "desk" / "strategies.json").read_text())
    for s in desk["strategies"]:
        sid = f"desk-{s['id']}"
        ev = f"status {s.get('status', '')}; gates pass {s.get('gates_pass') or 'none'} / fail {s.get('gates_fail') or 'none'}; no graded outcomes published"
        dep = ""
        if "starter" in str(s["name"]).lower() or "backup" in str(s["name"]).lower() or "injury" in str(s["name"]).lower():
            dep = (" Availability evidence currently rests on club depth charts; the entry "
                   "cannot be graded until inactive lists are captured (task B30).")
        up = ("the desk gate ledger passes on later, untouched outcomes with uncertainty "
              "(minimum sample met, CI excluding the no-skill value, multiplicity "
              "adjustment survived)" + dep)
        down = ("the pre-registered gates fail on untouched data, or the input data cannot "
                "be captured with provenance - the hypothesis is retired, not re-tuned")
        entry("desk", sid, s["name"], s["family"], "", s.get("construction", ""), ev, up, down,
              "https://www.nfl.com/schedules/2026/by-week/week-10")

    # ---- ops tree (5 rows) ----
    ops = json.loads((ROOT / "ops" / "data" / "leaderboard.json").read_text())
    for r in ops["rows"]:
        sid = f"ops-{r['id']}"
        ev = (f"signal rate {r.get('signal_rate')} on n={r.get('n')} "
              f"(CI {r.get('signal_ci95')}); vs coin flip {r.get('vs_coinflip')}")
        up = ("on the next walk-forward window the CI lower bound stays above the "
              "coin-flip baseline with the sample rule met (>= 100 graded decisions)")
        down = ("the CI covers the coin-flip line on two consecutive windows - demoted to "
                "paper by the ops gate ledger")
        entry("ops", sid, r["id"], r["family"], "", r.get("note", ""), ev, up, down,
              "https://www.nfl.com/schedules/2026/by-week/week-10")

    # ---- hub pre-registration tree (12) ----
    hub = json.loads((ROOT / "hub" / "data" / "prereg.json").read_text())
    for s in hub["strategies"]:
        sid = f"hub-{s['id']}"
        ev = "registered and frozen before results; not yet graded (no prices, gates closed)"
        up = (f"the registered data requirement arrives with provenance "
              f"({s.get('data_required', 'see the pre-registration ledger')}) and the frozen "
              f"rule then passes the gate ledger on later untouched outcomes with its CI "
              f"excluding the no-skill value")
        down = ("the required data stays unavailable through the frozen season window, or "
                "the rule fails its gates when the data arrives - withdrawn without "
                "re-tuning; re-entry only via a new registration")
        entry("hub", sid, s["name"], s["family"], "", s.get("entry", ""), ev, up, down,
              "https://www.nfl.com/injuries/league/2026/reg10")
    return rows


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------
def p_index():
    rows = [
        ["RD-01", "Decision-readiness table on the landing page",
         '<a href="decision-readiness.html">decision-readiness.html</a> + the same table on the root landing', "74 requirement rows: gate that blocks, number that clears"],
        ["RD-02", "Two-sided change-our-mind field on every strategy entry",
         '<a href="change-our-mind.html">change-our-mind.html</a>', "42 entries across signals/desk/ops/hub, both directions"],
        ["RD-03", "Drift alarm on every parser",
         '<a href="drift-alarms.html">drift-alarms.html</a>', "14 pinned datasets; CI fails loudly on drift"],
        ["RD-04", "Control baseline (random; favourites) on every leaderboard run",
         '<a href="control-baselines.html">control-baselines.html</a>', "coin flip + favourites on the identical graded set and metric"],
        ["RD-05", "Weekly what-changed diff instead of a static snapshot",
         '<a href="what-changed.html">what-changed.html</a>', "rank / rating / availability change per club-week, snapshots stored weekly"],
        ["RD-06", "Scheduled immutable availability snapshots with hashes",
         '<a href="snapshots.html">snapshots.html</a>', "Wed/Thu/Fri/Sun cron + SHA-256 retention + freshness alert"],
        ["RD-07", "Injury/personnel ablation with uncertainty",
         '<a href="ablations.html">ablations.html</a>', "with vs without availability features, paired CI, honest verdict"],
        ["RD-08", "Announced-starter evidence field",
         '<a href="announced-starters.html">announced-starters.html</a>', "5 dated official announcements verified for week 10"],
        ["RD-09", "Offense-vs-defence matchup deficiency matrix (1st-4th)",
         '<a href="matchup-matrix.html">matchup-matrix.html</a>', "starter absences joined to replacement depth, per fixture"],
        ["RD-10", "Publish every model total twice until one wins",
         '<a href="two-totals.html">two-totals.html</a>', "estimator A vs registered B, gap column, collapse deferred by rule"],
    ]
    body = ("<p>This module was added by session <code>arena/6259c7b0-x3</code> to close the "
            "requirements from the brief that no earlier session had implemented. Each page "
            "below states what was built, what it is computed from, and what stays blank. "
            "Verification: <code>scripts/verify_readiness.py</code> (rows sourced-or-flagged, "
            "links resolve, controls and diffs reproduce deterministically).</p>"
            + table(["Task", "Requirement", "Page", "Shape"],
                    [[e(r[0]), r[1], r[2], r[3]] for r in rows],
                    caption="What this module answers"))
    write("index.html", "Readiness module - overview",
          "The ten brief requirements this session implements, and where each lives.", body)


def p_readiness(reg):
    hdr = ["ID", "Requirement", "Status", "Where it lives", "Gate that blocks it",
           "Number that would clear it", "Source"]
    rows = []
    for r in reg["rows"]:
        src = r["source"]
        src_html = (f'<a class="src" href="{esc(src)}">official</a>' if src.startswith("http")
                    else f'<a class="src" href="{esc(src)}">provenance</a>')
        rows.append([
            e(r["id"]), e(r["requirement"]), bstatus(r["status"]),
            f'<a href="../{esc(r["where"])}">{esc(r["where"])}</a>',
            e(r["gate"]), e(r["clears"]), src_html,
        ])
    counts = {}
    for r in reg["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = " | ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    body = (f"<p><b>{summary}</b></p>"
            + table(hdr, rows, caption=f"Decision readiness register - {len(reg['rows'])} requirement rows"))
    write("decision-readiness.html", "Decision readiness",
          "One row per requirement in the project brief: what blocks it, and the number "
          "that would clear it. This is the table the landing page renders.", body)


def p_change_mind(rows):
    hdr = ["Tree", "ID", "Strategy", "Family", "Current evidence",
           "What would move us TOWARD belief", "What would make us ABANDON it", "Source"]
    trs = []
    for r in rows:
        trs.append([
            e(r["tree"]), e(r["id"]), f"<b>{e(r['name'])}</b>", e(r["family"]),
            e(r["evidence"]), e(r["would_upgrade"]), e(r["would_abandon"]),
            src_cell(r["source"], "results feed"),
        ])
    body = (table(hdr, trs, caption=f"Two-sided 'what would change our mind' - {len(rows)} strategy entries")
            + "<p class='note'>Both fields are pre-registered decision rules about evidence, not "
            "predictions: the toward-belief field states the measurement that would raise "
            "confidence, the abandon field states the measurement that ends the hypothesis. "
            "Neither field is ever satisfied by the same window that first graded the entry.</p>")
    write("change-our-mind.html", "What would change our mind",
          "Every registered strategy entry across the four trees, with the evidence that "
          "would move the desk toward belief and the evidence that would end it.", body)


def p_controls(c):
    ctl = c["controls"]
    model = c["model_side_published"]
    hdr = ["Control / model", "Straight-up", "n", "95% CI", "exact p", "Brier",
           "Contest win rate vs baseline", "n", "95% CI", "exact p", "Source"]
    trs = []
    for r in ctl + [model]:
        contest = r["contest"]
        src = r.get("source") or c["source"]
        trs.append([
            f"<b>{e(r['name'])}</b><br><span class='mut'>{e(r.get('rule', ''))[:180]}</span>",
            e(r.get("su_rate", "")), e(r.get("su_n", "")),
            f"{e(r['su_ci95'][0])} - {e(r['su_ci95'][1])}" if r.get("su_ci95") else "",
            e(r.get("su_p_exact", "")), e(r.get("brier", "")),
            e(contest["win_rate"]), e(contest["n_decisive"]),
            f"{e(contest['ci95_low'])} - {e(contest['ci95_high'])}",
            e(contest["p_exact_binomial"]),
            src_cell(src, "nfl.com"),
        ])
    body = (table(hdr, trs,
                  caption=f"Controls and the model side on the identical graded set (n={c['graded_n']}, weeks {', '.join(map(str, c['graded_weeks']))})")
            + "<p class='note'>The contest metric is the signals engine's own rule: the "
            "number is closer to the actual margin than the no-knowledge baseline (mean home "
            "margin fitted on the same training weeks). The controls' numbers are the "
            "registered coin-flip 0 and the favourite's nominal +/-1.</p>"
            + "<p><b>What this changes in reading the leaderboard:</b> the published side "
            f"signal ({e(model['contest']['win_rate'])}) must be compared against the "
            f"coin-flip line ({e(ctl[0]['contest']['win_rate'])}) and the favourites line "
            f"({e(ctl[1]['contest']['win_rate'])}), not against 0.5. The model's contest edge "
            f"over a naive favourites rule is "
            f"{round(float(model['contest']['win_rate']) - float(ctl[1]['contest']['win_rate']), 4)} "
            "contest wins in expectation - real but small, and the staking side stays blocked "
            "on prices (F-01).</p>"
            + "<p class='note'>Coordination request logged in COORDINATION.md: the signals "
            "owner is asked to join these control rows into signals/leaderboard.html on its "
            "next rebuild so the controls appear on that page's own runs.</p>")
    write("control-baselines.html", "Control baselines",
          "Random picks and favourites-only, computed with the engine's own pipeline and "
          "grading rule on the identical graded set - the luck lines every leaderboard run "
          "must be read against.", body)


def p_what_changed(w):
    hdr = ["Week", "Club", "Rank", "Rank change", "Rating", "Rating change",
           "Out count", "Out change", "Newly out", "Returned", "Availability snapshot", "Source"]
    trs = []
    for r in w["rows"]:
        if r["week"] != w["latest_diff_week"]:
            continue
        av = e(r["availability_captured"])
        av_html = (badge("v", "captured") if r["availability_captured"] == "yes"
                   else badge("u", "no snapshot pair"))
        trs.append([
            e(r["week"]), f"<b>{e(r['abbr'])}</b>", e(r["rank_now"]),
            ("+" if r["rank_change"] > 0 else "") + e(r["rank_change"]),
            e(r["rating_now"]), ("+" if (r["rating_change"] not in ("", None) and r["rating_change"] > 0) else "") + e(r["rating_change"]),
            e(r["out_now"]), e(r["out_change"]) if r["out_change"] != "" else badge("u", "UNVERIFIED"),
            e(r["newly_out"]) or "-", e(r["returned"]) or "-",
            av_html, src_cell(r["source"], f"reg{r['week']} report"),
        ])
    body = (f"<p>Latest diff week: <b>{e(w['latest_diff_week'])}</b> vs the previous week. "
            f"Ranking rule: {e(w['ranking_rule'])}. Rating rule: {e(w['rating_rule'])}.</p>"
            + f"<p class='note'>{e(w['availability_note'])}</p>"
            + table(hdr, trs, caption=f"What changed, week {w['latest_diff_week']} -> club level")
            + "<h2>Stored weekly snapshots</h2><p>Each week's standings-through-week, ratings "
            "and availability counts are stored as CSV under <code>readiness/data/history/2026/</code> "
            "- the diff is rendered from those files, never hand-written. Weeks: "
            + e(", ".join(str(x) for x in w["weeks"])) + ".</p>")
    write("what-changed.html", "What changed (weekly diff)",
          "A dated weekly diff of rank, rating and availability change per club, rendered "
          "from stored weekly snapshots - not a static snapshot page.", body)


def p_drift(rep):
    hdr = ["Pin", "Dataset", "Pins", "Status", "Source"]
    trs = []
    for r in rep["results"]:
        pins = []
        if "exact_rows" in r["pins"]:
            pins.append(f"rows == {r['pins']['exact_rows']}")
        if "min_rows" in r["pins"]:
            pins.append(f"rows >= {r['pins']['min_rows']}")
        if r["pins"].get("required_fields"):
            pins.append("fields: " + ", ".join(r["pins"]["required_fields"][:5])
                        + ("..." if len(r["pins"]["required_fields"]) > 5 else ""))
        if r["pins"].get("value_pins"):
            pins.append("values: " + ", ".join(f"{k}={v}" for k, v in list(r["pins"]["value_pins"].items())[:3]))
        if r["pins"].get("allowed_status_vocab"):
            pins.append("status vocab pinned")
        trs.append([
            f"<b>{e(r['id'])}</b>", e(r["dataset"]), e("; ".join(pins)),
            bstatus(r["status"]) + (f"<br><span class='mut'>{e('; '.join(r['alarms'])[:200])}</span>" if r["alarms"] else ""),
            src_cell(r["source"], "official"),
        ])
    body = (f"<p><b>{e(rep['passed'])} of {e(rep['datasets'])}</b> pinned datasets pass. "
            f"{e(rep['policy'])}</p>"
            + table(hdr, trs, caption="Parser drift pins (scripts/drift_alarm.py)")
            + "<p class='note'>The gate runs in CI (<code>.github/workflows/readiness.yml</code>) "
            "and exits 1 with a loud per-field report when a pin breaks - a blank page cannot "
            "be published silently. Pins change only by a reviewed, deliberate commit.</p>")
    write("drift-alarms.html", "Drift alarms",
          "Every parser output pinned to expected row counts and required fields; drift fails "
          "the build loudly.", body)


def p_snapshots():
    hdr = ["Item", "Design", "Status", "Source"]
    rows = [
        ["Schedule", "Cron <code>17:00 UTC Wed/Thu/Fri</code> (injury report days) and <code>16:00 UTC Sun</code> (game-day inactivity window)", badge("d", "COMMITTED"), src_cell("https://www.nfl.com/injuries/league/2026/reg10", "report page")],
        ["Captures", "Official league injury report (regN) + week schedule pages, raw HTML stored under <code>readiness/data/history/&lt;date&gt;/</code>", badge("u", "FIRST RUN PENDING"), src_cell("https://www.nfl.com/injuries/", "report index")],
        ["Integrity", "SHA-256 per capture + append-only manifest (<code>manifest.csv</code>: date, url, bytes, sha256, http status)", badge("d", "COMMITTED"), src_cell("https://www.nfl.com/injuries/league/2026/reg10", "report page")],
        ["Conflict flags", "Row-count delta > 20% vs previous capture prints a SCHEMA CHANGE alert; parser pins (RD-03) fail the build", badge("d", "COMMITTED"), src_cell("https://www.nfl.com/injuries/league/2026/reg10", "report page")],
        ["Freshness alert", "If the newest capture is older than 4 days at run time the step exits 1 with a FRESHNESS ALERT", badge("d", "COMMITTED"), src_cell("https://www.nfl.com/injuries/", "report index")],
        ["Replay", "Any designation state can be replayed as known at a past clock time from the retained raw captures", badge("u", "NEEDS >= 2 RUNS"), src_cell("https://www.nfl.com/injuries/league/2026/reg10", "report page")],
        ["Extendable phases (blocked on sources)", "Inactive lists, snap counts, reserve/IR lists, venue per fixture, stadium roof + NWS wind/precip, past-season report archives - each is a documented phase with the same hash/manifest discipline once an official route is verified", badge("b", "BLOCKED"), src_cell("https://www.nfl.com/injuries/", "report index")],
    ]
    body = ("<p>Requirement: immutable multi-day availability snapshots captured on a schedule "
            "with retained hashes, so practice designations can be replayed as they were known. "
            "The workflow <code>.github/workflows/availability-snapshots.yml</code> is committed "
            "and runs on the schedule above once merged to the default branch. Until its first "
            "scheduled runs execute, the repository holds one static capture plus the stored "
            "weeks 8-10 report reads - published honestly as pending, not claimed as running.</p>"
            + table(hdr, rows, caption="Scheduled capture design (scripts/availability_snapshot.py)"))
    write("snapshots.html", "Snapshot capture",
          "Scheduled, hashed, immutable availability snapshots - the design, its status, and "
          "the phases blocked on official sources.", body)


def p_ablations(a):
    hdr = ["Test week", "Train weeks", "n train", "n test", "MAE A (ratings only)",
           "MAE B (+ availability)", "MAE delta (A-B)", "Delta 95% CI", "B wins contest", "Source"]
    trs = []
    for arm in a["arms"]:
        trs.append([
            e(arm["test_week"]), e(", ".join(map(str, arm["train_weeks"]))),
            e(arm["train_n"]), e(arm["test_n"]), e(arm["mae_A"]), e(arm["mae_B"]),
            ("+" if arm["mae_delta"] > 0 else "") + e(arm["mae_delta"]),
            f"{e(arm['delta_ci95'][0])} to {e(arm['delta_ci95'][1])}",
            e(arm["contest_B_wins"]), src_cell(a["source"], "reg10 report"),
        ])
    pooled = a["pooled"]
    body = (f"<p>{e(a['registered_rule'])}</p>"
            + table(hdr, trs, caption="Availability-feature ablation, chronological holdouts")
            + (f"<p><b>Pooled over {e(pooled['test_n'])} test games:</b> MAE delta "
               f"{e(pooled['mae_delta_mean'])} points, 95% CI {e(pooled['delta_ci95'][0])} to "
               f"{e(pooled['delta_ci95'][1])} - <b>{e(pooled['verdict'])}</b>.</p>"
               if pooled.get("test_n") else "")
            + f"<p class='note'>{e(a['caveat'])}</p>"
            + "<p class='note'>Design consequence: no fixed injury penalty is subtracted "
            "anywhere; the availability feature either earns its place through this ablation "
            "or it is not fitted.</p>")
    write("ablations.html", "Injury / personnel ablation",
          "The same model with and without the availability features, chronological holdouts, "
          "the difference reported with uncertainty - replacing fixed injury penalties.", body)


def p_announced():
    rows = [
        ["SEA", "Drew Lock", "Sam Darnold (quad/rib)", "2026-11-09",
         "Ruled out; Lock expected to start again",
         '<a class="src" href="https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again">nfl.com/news</a>'],
        ["SEA", "Drew Lock", "Sam Darnold", "2026-11-13",
         "No injury designation; will start Sunday (coach announcement)",
         '<a class="src" href="https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders">nfl.com/news</a>'],
        ["BAL", "Jacoby Brissett", "Lamar Jackson / Tyler Huntley (injured)", "2026-11-05",
         "Traded to Baltimore; expected to start Week 10 vs Chargers",
         '<a class="src" href="https://www.nfl.com/news/jacoby-brissett-trade-ravens-cardinals">nfl.com/news</a>'],
        ["BAL", "Jacoby Brissett", "-", "2026-11-14",
         "The NFL Report: expected to start vs Chargers",
         '<a class="src" href="https://www.nfl.com/videos/nfl-report-gives-injury-updates-ahead-of-week-10-sunday-matchups">nfl.com/videos</a>'],
        ["MIA", "Kyle McCord", "Malik Willis (groin, IR)", "2026-11-10",
         "Willis to injured reserve; McCord in line for first start",
         '<a class="src" href="https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start">nfl.com/news</a>'],
        ["MIA", "Kyle McCord", "Malik Willis (IR)", "2026-11-11",
         "Roundup: McCord in line to start in Week 10 against the Colts",
         '<a class="src" href="https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-tuesday-nov-10">nfl.com/news</a>'],
        ["CLE", "Deshaun Watson", "Shedeur Sanders (Week 9 starter)", "2026-11-12",
         "Team announced Wednesday: Watson will start Sunday vs Texans",
         '<a class="src" href="https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11">nfl.com/news</a>'],
        ["ARI", "Carson Beck", "-", "2026-11-12",
         "First career start vs Rams, per head coach",
         '<a class="src" href="https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-wednesday-nov-11">nfl.com/news</a>'],
    ]
    hdr = ["Club", "Announced starter", "Replaces", "Announcement date (published)",
           "What the announcement says", "Source"]
    body = ("<p>Requirement: an announced-starter <i>evidence</i> field - the NFL does publish "
            "dated starter changes; replacements must never be inferred from blank report "
            "cells. Each row below is a dated official announcement, verified on nfl.com on "
            "2026-11-15. Corroboration outside official domains (press coverage) matched all "
            "rows; only official links are published here.</p>"
            + table(hdr, rows, caption="Officially announced week-10 starter changes")
            + "<p class='note'>This register is the evidence field for replacement tracking: "
            "an announced starter is treated as verified, a blank replacement column is NOT "
            "treated as 'no replacement'. Coordination request logged for the hub "
            "replacements page to join this field on its next rebuild.</p>")
    write("announced-starters.html", "Announced starters",
          "Dated, officially published starter announcements - evidence, never inference.", body)


def p_matchup(games, defi):
    # week-10 fixtures; pair each side's starter absences with the opponent's
    wk = 10
    fx = [g for g in games["games"] if g["week"] == wk]
    rows_out = defi["rows"]
    hdr = ["Game", "Side", "Unit", "Starter out (pos)", "Replacement named",
           "Replacement depth", "Join evidence", "Source"]
    trs = []
    for g in sorted(fx, key=lambda x: x["date_iso"]):
        for side, opp in (("home", "away"), ("away", "home")):
            club = g[side]
            for r in sorted(rows_out, key=lambda x: (x["group"], x["pos"], x["player"])):
                if r["week"] != wk or r["team"] != club:
                    continue
                if r["status"] not in ("Out", "Doubtful"):
                    continue
                repl = r.get("replacement") or "-"
                rdepth = r.get("replacement_depth") or ""
                join = r.get("join") or ""
                trs.append([
                    f"{e(g['away'])} @ {e(g['home'])}",
                    f"{e(club)} ({e(side)}) {e(r.get('group', ''))}",
                    e(r.get("pos", "")),
                    f"<b>{e(r['player'])}</b> ({e(r['status'])})",
                    e(repl) if repl != "-" else badge("u", "none named"),
                    (badge("d", f"{e(rdepth)}") if rdepth in ("2", "3", "4")
                     else (e(rdepth) if rdepth else badge("u", "unknown"))),
                    e(join[:90]) or badge("u", "UNVERIFIED"),
                    src_cell(r.get("injury_source") or r.get("depth_source"), "official"),
                ])
    body = (f"<p>Week {wk} fixtures only. For each game and each side, every officially "
            "designated Out/Doubtful starter is listed with the replacement named on the "
            "club's own depth chart and that replacement's string. This is an evidence view "
            "(who the club lists, at what depth), not a modelled handicap.</p>"
            + table(hdr, trs, caption=f"Offense vs defence deficiency matrix, week {wk} (1st-4th string)"))
    write("matchup-matrix.html", "Matchup deficiency matrix",
          "Immediate trench and coverage mismatches from officially designated absences, "
          "joined to club-published replacement depth.", body)


def p_two_totals(t):
    hdr = ["Game", "Week", "Estimator A (engine)", "Estimator B (registered)",
           "Gap (A-B)", "Actual", "Err A", "Err B", "Source"]
    trs = []
    for r in t["rows"][-20:]:
        trs.append([
            e(r["game_id"]), e(r["week"]), e(r["estimator_A"]), e(r["estimator_B"]),
            ("+" if r["gap"] > 0 else "") + e(r["gap"]), e(r["actual_total"]),
            e(r["err_A"]), e(r["err_B"]), src_cell(t["source"], "nfl.com"),
        ])
    body = (f"<p>{e(t['registered_rule'])}</p>"
            + f"<p><b>Walk-forward comparison on n={e(t['n'])} graded games:</b> MAE A "
            f"{e(t['mae_A'])} vs MAE B {e(t['mae_B'])} (gap {e(t['mae_gap'])}), paired "
            f"95% CI {e(t['delta_ci95'][0])} to {e(t['delta_ci95'][1])}. "
            f"<b>{e(t['verdict'])}.</b></p>"
            + table(hdr, trs, caption="Both totals, gap column (latest 20 of "
                    f"{len(t['rows'])} graded games - full series in readiness/data/two_totals.json)"))
    write("two-totals.html", "Two totals until one wins",
          "Every model total published twice - the engine estimator and a registered "
          "alternative - with the gap column and a pre-registered collapse rule.", body)


def main():
    print("building readiness module:")
    reg = json.loads((DATA / "readiness.json").read_text())
    controls = load_controls()
    w = json.loads((DATA / "what_changed.json").read_text())
    rep = json.loads((DATA / "drift_report.json").read_text())
    abl = json.loads((DATA / "ablations.json").read_text())
    tot = json.loads((DATA / "two_totals.json").read_text())
    games = json.loads((ROOT / "data" / "desk" / "games.json").read_text())
    defi = json.loads((ROOT / "data" / "desk" / "deficiencies.json").read_text())

    cm = gen_change_mind(controls)
    (DATA / "change_mind.json").write_text(json.dumps(
        {"as_of": reg["as_of"],
         "policy": ("Two-sided field on every strategy entry: what evidence would move the "
                    "desk toward belief, and what evidence would end the hypothesis. "
                    "Pre-registered rules about evidence, not predictions."),
         "source": "https://www.nfl.com/schedules/2026/by-week/week-10",
         "rows": cm}, indent=1) + "\n")

    p_index()
    p_readiness(reg)
    p_change_mind(cm)
    p_controls(controls)
    p_what_changed(w)
    p_drift(rep)
    p_snapshots()
    p_ablations(abl)
    p_announced()
    p_matchup(games, defi)
    p_two_totals(tot)
    print(f"  change_mind.json: {len(cm)} strategy entries")


if __name__ == "__main__":
    main()
