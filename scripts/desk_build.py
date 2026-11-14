#!/usr/bin/env python3
"""Build the consolidated decision desk site into desk/.

Deterministic: reads only data/desk/*.json and the prose modules next to this file.
Every table row carries a source link; anything unconfirmed is rendered as an explicit
UNVERIFIED badge instead of a guessed value.

Pages
  index.html              executive dashboard
  executive-summary.html  decision document
  lines.html              originated lines + market gap
  model.html              ratings, calibration, backtest
  strategies.html         strategy competition + gate ledger
  leaderboard.html        competition rules, empty until gates pass
  correlations.html       measured correlations with n and CI
  injuries.html           official injury reports (weeks captured, duplicates dropped)
  lineups.html            starter/backup deficiency map
  questions.html          information register (known / missing / decision)
  suggestions.html        suggestions for review before implementation
  requirements.html       requirement tracking
  sources.html            source register
  repo-review.html        repository review + irregularities
  flagged.html            Flagged for Review (unverified items)
  games.html              verified game log
  standings.html          verified standings
  archive.html            links to prior session sites
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import desk_content as C

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "desk"
OUT = ROOT / "desk"

NAV = [
    ("index.html", "Overview"),
    ("executive-summary.html", "Executive summary"),
    ("lines.html", "Own lines"),
    ("model.html", "Model"),
    ("strategies.html", "Strategies"),
    ("leaderboard.html", "Leaderboard"),
    ("correlations.html", "Correlations"),
    ("injuries.html", "Injuries"),
    ("lineups.html", "Lineups"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("requirements.html", "Requirements"),
    ("games.html", "Game log"),
    ("standings.html", "Standings"),
    ("sources.html", "Sources"),
    ("repo-review.html", "Repo review"),
    ("flagged.html", "Flagged for review"),
    ("archive.html", "Archive"),
]


def e(x) -> str:
    return html.escape(str(x), quote=True)


def src(url: str, label: str = "") -> str:
    if not url:
        return '<span class="badge unv">UNVERIFIED</span>'
    host = url.split("/")[2] if "://" in url else url
    text = label or host
    return f'<a href="{e(url)}" target="_blank" rel="noopener">{e(text)}</a>'


def derived(label: str = "DERIVED") -> str:
    return f'<span class="badge der">{e(label)}</span>'


def flag(text: str) -> str:
    return f'<span class="badge unv">{e(text)}</span>'


def derivation(path: str, label: str = "") -> str:
    """A row explained by a file in this repository: stamped DERIVED, linkable locally."""
    return (f'<span class="badge der">{e(label or "DERIVED")}</span> '
            f'<span class="small mono">{e(path)}</span>')


CSS = """\
:root{--bg:#0b1220;--panel:#121b2c;--panel2:#18233a;--line:#243350;--ink:#e8eefb;
--dim:#93a4c4;--acc:#4ea1ff;--acc2:#5ce1c0;--warn:#ffcf6b;--bad:#ff8a8a;--good:#7ee787}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none} a:hover{text-decoration:underline}
header{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.96);
border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
.wrap{max-width:1280px;margin:0 auto;padding:0 20px}
.brand{display:flex;gap:14px;align-items:center;padding:14px 0 8px}
.brand h1{font-size:18px;margin:0;letter-spacing:.2px}
.brand .sub{color:var(--dim);font-size:12.5px}
nav{display:flex;flex-wrap:wrap;gap:6px;padding:0 0 12px}
nav a{padding:6px 10px;border:1px solid var(--line);border-radius:999px;font-size:12.5px;color:var(--dim)}
nav a:hover{color:var(--ink);border-color:var(--acc);text-decoration:none}
nav a.on{color:#06111f;background:var(--acc);border-color:var(--acc);font-weight:600}
main{max-width:1280px;margin:0 auto;padding:26px 20px 70px}
h2{font-size:22px;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:24px 0 8px;color:#cfe0ff}
p,li{color:#d3dded}
.lede{color:var(--dim);font-size:14.5px;margin:6px 0 18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi b{display:block;font-size:24px;line-height:1.2}
.kpi span{color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.8px}
.kpi small{display:block;color:#7d8fae;font-size:11.5px;margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:16px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card b{display:block;margin-bottom:4px}
.card span{color:var(--dim);font-size:13px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:14px 0;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);color:#b9cbe9;font-size:11.5px;text-transform:uppercase;
letter-spacing:.6px;position:sticky;top:0;white-space:nowrap}
tbody tr:hover{background:#16233b}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;
font-weight:600;letter-spacing:.3px;white-space:nowrap}
.badge.unv{background:#3a2a12;color:var(--warn);border:1px solid #6b5320}
.badge.der{background:#1b2f3d;color:#7fd7ff;border:1px solid #2c5a72}
.badge.ok{background:#14301f;color:var(--good);border:1px solid #2a5738}
.badge.bad{background:#3a1b1b;color:var(--bad);border:1px solid #6b2b2b}
.notice{background:#1a2233;border:1px solid var(--line);border-left:3px solid var(--acc);
border-radius:8px;padding:12px 14px;margin:16px 0;color:#cbd8ee;font-size:13.5px}
.notice.warn{border-left-color:var(--warn)} .notice.bad{border-left-color:var(--bad)}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
footer{border-top:1px solid var(--line);color:var(--dim);font-size:12.5px}
footer .wrap{padding:20px}
.small{font-size:12.5px;color:var(--dim)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.pos{color:var(--good)} .neg{color:var(--bad)}
"""


def page(name: str, title: str, body: str, subtitle: str = "") -> str:
    on = ' class="on"'
    links = "\n".join(
        f'<a href="{h}"{on if h == name else ""}>{e(t)}</a>' for h, t in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · NFL Decision Desk</title>
<style>{CSS}</style>
</head>
<body>
<header><div class="wrap">
<div class="brand">
  <div>
    <h1>NFL Decision Desk</h1>
    <div class="sub">{e(subtitle or 'Evidence-first line origination, validation and injury intelligence')}</div>
  </div>
</div>
<nav>{links}</nav>
</div></header>
<main>
{body}
</main>
<footer><div class="wrap">
<p><b>Evidence policy.</b> Every value is either read from an official source, computed from
official values and badged <span class="badge der">DERIVED</span>, or left blank and marked
<span class="badge unv">UNVERIFIED</span>. Nothing is inferred or filled in.</p>
<p>Built {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} from
<code>data/desk/*.json</code> · <a href="sources.html">source register</a> ·
<a href="flagged.html">flagged items</a> · <a href="archive.html">archive of earlier sessions</a></p>
</div></footer>
</body>
</html>
"""


def table(headers: list[str], rows: list[list[str]], numeric: set[int] | None = None,
          caption: str = "") -> str:
    numeric = numeric or set()
    num = ' class="num"'
    th = "".join(f'<th{num if i in numeric else ""}>{h}</th>'
                 for i, h in enumerate(headers))
    body = []
    for r in rows:
        cells = "".join(
            f'<td{num if i in numeric else ""}>{c}</td>' for i, c in enumerate(r))
        body.append(f"<tr>{cells}</tr>")
    cap = f'<caption class="small" style="text-align:left;padding:8px 10px">{caption}</caption>' if caption else ""
    return (f'<div class="tw"><table>{cap}<thead><tr>{th}</tr></thead>'
            f"<tbody>{''.join(body)}</tbody></table></div>")


def kpi(value: str, label: str, note: str = "") -> str:
    n = f"<small>{e(note)}</small>" if note else ""
    return f'<div class="kpi"><span>{e(label)}</span><b>{value}</b>{n}</div>'


# --------------------------------------------------------------------------- #
def load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def build() -> int:
    OUT.mkdir(exist_ok=True)
    data = {n: load(f"{n}.json") for n in
            ("games", "standings", "injuries", "depth", "deficiencies", "model",
             "correlations", "luck", "calibration", "strategies", "parse_report")}
    written = []

    def write(name: str, title: str, body: str, subtitle: str = "") -> None:
        (OUT / name).write_text(page(name, title, body, subtitle))
        written.append(name)

    # ---------------- index ----------------
    m = data["model"]
    bt = m["backtest"]
    dsum = data["deficiencies"]["summary"]
    st = data["strategies"]
    passed = sum(1 for s in st["strategies"] if not s["gates_fail"])
    body = f"""
<h2>Executive dashboard</h2>
<p class="lede">One consolidated desk: verified official data, originated lines, a gate ledger for
strategies, and an injury-to-lineup deficiency map. Unverified values are blank and flagged —
never estimated.</p>
<div class="kpis">
{kpi(str(m['inputs']['games']), 'Final games verified', f"Weeks {m['inputs']['weeks'][0]}–{m['inputs']['weeks'][-1]}")}
{kpi(str(len(data['standings']['rows'])), 'Clubs reconciled', 'W-L-T, PF, PA all match the game log')}
{kpi(f"{len(data['injuries']['rows']):,}", 'Injury-report rows', f"{len(data['injuries']['weeks'])} official weeks")}
{kpi(f"{dsum['matched']}", 'Injuries joined to a depth string', f"{dsum['unmatched']} not joinable (flagged)")}
{kpi(f"{bt['predicted_vs_actual_r']:+.3f}", 'Walk-forward correlation', f"n={bt['n']} games, MAE {bt['mae']}")}
{kpi(f"{passed}/{len(st['strategies'])}", 'Strategies with all gates passed', 'Leaderboard stays empty meanwhile')}
</div>

<div class="notice warn">
<b>Read this first.</b> The model is fitted on {m['inputs']['games']} verified 2026 finals and
back-tested week by week. It is <b>not</b> validated against market prices, because no licensed
odds feed exists in this repository. Own lines are published as
{derived('DERIVED')} numbers, not as recommendations.
</div>

<h2>What is verified, and how</h2>
{table(['Dataset', 'Rows', 'Official source', 'Cross-check performed'], [
 ['Final scores, weeks 1–10', str(bt['n'] + 16), src('https://www.nfl.com/schedules/2026/by-week/week-1', 'nfl.com schedules'),
  'Recomputed W-L-T, PF and PA for all 32 clubs — exact match to the standings page'],
 ['2026 standings', '32 clubs', src('https://www.nfl.com/standings/league/2026/reg', 'nfl.com standings'),
  'Independent recomputation from the game log'],
 ['Injury reports, weeks '
  + '-'.join(str(w) for w in [min(x['week'] for x in data['injuries']['weeks']), max(x['week'] for x in data['injuries']['weeks'])])
  + f" ({len(data['injuries']['weeks'])} weeks)",
  f"{len(data['injuries']['rows']):,} rows",
  src('https://www.nfl.com/injuries/league/2026/reg10', 'nfl.com injuries'),
  'Team headers and status vocabulary checked row by row'],
 ['Club depth charts', f"{sum(len(c['units']) for c in data['depth']['clubs'])} unit tables, 32 clubs",
  src('https://www.nfl.com/teams/', 'nfl.com teams'), '31 charts machine-readable; Houston image-only (flagged)'],
 ['Home-field advantage', f"{m['home_field_points']:+.2f} pts", src('https://www.nfl.com/schedules/2026/by-week/week-10', 'game log'),
  derived('computed') + ' from final scores only'],
 ['Market spreads and totals', '0 rows', flag('UNVERIFIED: no official source'), 'No licensed odds feed in this repository'],
])}

<h2>Where each decision lives</h2>
<div class="grid">
<a class="card" href="lines.html"><b>Own lines →</b><span>Week {m['originated_lines']['week']} originated spreads and totals with the measured gaps.</span></a>
<a class="card" href="strategies.html"><b>Strategy competition →</b><span>{len(st['strategies'])} hypotheses, each with a gate ledger. Nothing is claimed to be profitable.</span></a>
<a class="card" href="lineups.html"><b>Lineup deficiencies →</b><span>{dsum['starter_outs']} starter-level absences and the next man up at each slot.</span></a>
<a class="card" href="correlations.html"><b>Correlations →</b><span>{len(data['correlations']['pairs'])} measured coefficients with n and 95% CIs.</span></a>
<a class="card" href="questions.html"><b>Open questions →</b><span>{len(C.QUESTIONS)} questions, each with what we know, what is missing and the decision it blocks.</span></a>
<a class="card" href="suggestions.html"><b>Suggestions →</b><span>{len(C.SUGGESTIONS)} proposals to review before any implementation.</span></a>
</div>
"""
    write("index.html", "Overview", body)

    # ---------------- executive summary ----------------
    body = C.executive_summary(m, bt, dsum, data)
    write("executive-summary.html", "Executive summary", body)

    # ---------------- lines ----------------
    rows = []
    for r in m["originated_lines"]["rows"]:
        rows.append([
            str(r["week"]), r["date_iso"], e(r["kickoff_et"]),
            f"{e(r['away'])} @ {e(r['home'])}",
            f"{r['our_spread_home']:+.1f}", f"{r['our_total']:.1f}",
            src(r["inputs_source"], "inputs"),
            flag("no market price"),
            derived(),
        ])
    body = f"""
<h2>Own originated lines</h2>
<p class="lede">Spreads are from the home team's perspective (negative = home favoured). Totals are
the model's expected combined score. Every number below is model output, not market data.</p>
<div class="kpis">
{kpi(f"{m['home_field_points']:+.2f}", 'Measured home-field advantage', 'computed from final scores')}
{kpi(f"{m['league_avg_team_score']*2:.1f}", 'Model league total', 'base for the totals model')}
{kpi(str(len(m['originated_lines']['rows'])), 'Games priced', f"Week {m['originated_lines']['week']}")}
{kpi('0', 'Market prices', 'no licensed feed')}
</div>
{table(['Wk', 'Date', 'Kick ET', 'Matchup', 'Own spread (home)', 'Own total', 'Inputs', 'Market', 'Class'],
       rows, numeric={4, 5},
       caption='Own lines = DERIVED from verified results. Market columns stay blank because no official odds source exists in this repository.')}
<div class="notice">
<b>Why there is no "edge" column.</b> An edge requires a price. No official NFL source publishes
spreads or totals, so the market side is left blank and flagged rather than filled from a
secondary site. See <a href="suggestions.html">Suggestions S1</a> for the decision that unblocks it.
</div>
<h2>How the numbers are produced</h2>
{table(['Component', 'Formula', 'Class', 'Source'], [
 ['Net rating', 'margin = HFA + net[home] − net[away]; ridge least squares, centred on zero', derived(), derivation('data/desk/model.json')],
 ['Pace rating', 'total = base + pace[home] + pace[away]; separate ridge fit', derived(), derivation('data/desk/model.json')],
 ['Home field', f"{m['home_field_points']:+.2f} points measured from {m['inputs']['games']} finals", derived('measured'), derivation('data/desk/model.json')],
 ['Inputs', 'Final scores only — no prior season, no market, no manual input', derived('verified'),
  src('https://www.nfl.com/schedules/2026/by-week/week-10', 'official game log')],
])}
<h2>Calibration before anyone uses these lines</h2>
{table(['Metric', 'Value', 'Reading', 'Class'], [
 ['Walk-forward games', str(bt['games']), 'each week predicted using only earlier weeks', derivation('data/desk/calibration.json')],
 ['Mean absolute error', f"{bt['mae']} pts", 'average miss on the home margin', derivation('data/desk/calibration.json')],
 ['RMSE', f"{bt['rmse']} pts", 'penalises large misses', derivation('data/desk/calibration.json')],
 ['Bias', f"{bt['bias']} pts", 'positive = model under-predicts the home margin', derivation('data/desk/calibration.json')],
 ['Prediction/actual correlation', f"r = {bt['predicted_vs_actual_r']:+.3f} (n={bt['n']})",
  'the single most important number on this page; see the model page for its CI', derivation('data/desk/calibration.json')],
])}
"""
    write("lines.html", "Own lines", body)

    # ---------------- model ----------------
    r = data["correlations"]["pairs"]
    pred_actual = None
    body = f"""
<h2>Model and calibration</h2>
<p class="lede">A deliberately small model: two ridge regressions on final scores. The point is not
sophistication, it is that every parameter is measurable, reproducible and testable out of sample.</p>
<div class="kpis">
{kpi(f"{bt['predicted_vs_actual_r']:+.3f}", 'Walk-forward r', f"n={bt['n']}")}
{kpi(f"{bt['mae']}", 'MAE (points)', 'home margin')}
{kpi(f"{bt['rmse']}", 'RMSE (points)', 'home margin')}
{kpi(f"{bt['bias']:+.2f}", 'Bias', 'positive = under-predicts home margin')}
</div>
<div class="notice warn"><b>Honest reading.</b> A walk-forward correlation of {bt['predicted_vs_actual_r']:+.3f}
on {bt['n']} games is a weak signal. It is consistent with a real but small effect and is also
consistent with noise at this sample size. It cannot support a profitability claim, and it is
published with its uncertainty on the <a href="correlations.html">correlations page</a>.</div>
<h2>Club ratings</h2>
{table(['Team', 'Net rating', 'Pace rating', 'PF/g', 'PA/g', 'Net pts/g', 'Games', 'Source'],
       [[r_['team'], f"{r_['net_rating']:+.2f}", f"{r_['pace_rating']:+.2f}",
         f"{r_['points_for_pg']:.1f}", f"{r_['points_against_pg']:.1f}",
         f"{r_['net_points_pg']:+.1f}", str(r_['games']),
         src('https://www.nfl.com/standings/league/2026/reg', 'standings')]
        for r_ in m['ratings']], numeric={1, 2, 3, 4, 5, 6},
       caption='Ratings are DERIVED. PF/g, PA/g and net pts/g are directly computed from the verified game log.')}
<h2>Walk-forward backtest, week by week</h2>
{table(['Week', 'Games graded', 'Source'],
       [[str(w['week']), str(w['games']), src('https://www.nfl.com/schedules/2026/by-week/week-%d' % w['week'], 'nfl.com')]
        for w in bt['weeks']], numeric={1},
       caption='Week w is predicted by a model fitted only on weeks before w.')}
<h2>Known model limitations</h2>
{table(['Limitation', 'Status'], [[e(x), flag('UNVERIFIED: not corrected')] for x in m['limitations']])}
"""
    write("model.html", "Model", body)

    # ---------------- strategies ----------------
    grows = []
    for s in st["strategies"]:
        grows.append([e(s["id"]), e(s["name"]), e(s["family"]), e(s["construction"]),
                      ", ".join(s["gates_pass"]) or "—", ", ".join(s["gates_fail"]) or "—",
                      flag(s["status"]) if "blocked" in s["status"] else derived(s["status"]),
                      src('https://www.nfl.com/schedules/2026/by-week/week-1', 'data')])
    body = f"""
<h2>Strategy competition</h2>
<p class="lede">{e(st['policy'])}</p>
<div class="kpis">
{kpi(str(len(st['strategies'])), 'Strategies registered')}
{kpi(str(sum(1 for s in st['strategies'] if not s['gates_fail'])), 'Fully gated')}
{kpi('0', 'Graded bets', 'no market prices exist')}
{kpi('0', 'Leaderboard entries', 'gates not met')}
</div>
{table(['ID', 'Strategy', 'Family', 'Construction', 'Gates passed', 'Gates failed', 'Status', 'Data'],
       grows, caption='A strategy is promoted to the leaderboard only when every blocking gate is passed on later, untouched data.')}
<h2>Validation gates</h2>
{table(['Gate', 'Name', 'Rule', 'Blocking', 'Provenance'],
       [[e(g['id']), e(g['gate']), e(g['rule']), e(g['blocking']),
         derivation('data/desk/strategies.json')] for g in st['gates']])}
<div class="notice">
<b>Single, parlay and prop-combo coverage.</b> Singles are covered by S1–S5 and S9–S10, parlays by
S6–S7, player-prop combos by S8. S8 is blocked because no official player-prop history exists;
S6 and S7 are limited by sample size ({m['inputs']['games']} games), which is why the measured
correlation CIs on the <a href="correlations.html">correlations page</a> matter.
</div>
"""
    write("strategies.html", "Strategies", body)

    # ---------------- leaderboard ----------------
    lb = st["leaderboard_rule"]
    body = f"""
<h2>Leaderboard</h2>
<p class="lede">A competition structure that rewards repeatable skill and refuses to reward luck.
The board is intentionally empty: no strategy has passed the gates yet.</p>
<div class="notice bad"><b>Board status: empty by design.</b> Eligibility requires
{e(lb['eligibility'])}. Right now {st['graded_results']['rows']} bets are graded, because
{e(st['graded_results']['why'])}.</div>
{table(['Rank', 'Strategy', 'Graded bets', 'Vig-free ROI', '95% CI', 'Deflated Sharpe', 'Status'],
       [['—', 'no eligible strategy', '0', flag('UNVERIFIED'), flag('UNVERIFIED'),
         flag('UNVERIFIED'), flag('not eligible')]],
       numeric={2, 3, 4, 5})}
<h2>Competition rules</h2>
{table(['Rule', 'Definition', 'Basis'], [
 ['Eligibility', e(lb['eligibility']), derivation('data/desk/strategies.json')],
 ['Score', e(lb['score']), derivation('data/desk/strategies.json')],
 ['Rewards', e(lb['rewards']), flag('UNVERIFIED: no reward mechanism exists')],
 ['Anti-gaming 1', e(lb['anti_gaming'][0]), derivation('data/desk/strategies.json')],
 ['Anti-gaming 2', e(lb['anti_gaming'][1]), derivation('data/desk/strategies.json')],
 ['Anti-gaming 3', e(lb['anti_gaming'][2]), derivation('data/desk/strategies.json')],
])}
<h2>Reward design (proposal, not active)</h2>
<p>Rewards are notional and are listed as a proposal for review, not as a promise. Any real reward
scheme needs three decisions recorded first on the <a href="suggestions.html">Suggestions page</a>:
what is scored (model vs market), who can enter, and what happens when a strategy stops working.
The legal status of staking real money is unresolved and is listed on the
<a href="flagged.html">Flagged page</a> — no jurisdiction is asserted without a source.</p>
"""
    write("leaderboard.html", "Leaderboard", body)

    # ---------------- correlations ----------------
    crows = []
    for p in data["correlations"]["pairs"]:
        sig = "CI excludes 0" if (p["ci95"][0] > 0 or p["ci95"][1] < 0) else "CI includes 0 — not distinguishable from none"
        crows.append([e(p["pair"]), f"{p['r']:+.3f}", str(p["n"]),
                      f"[{p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f}]", f"{p['p']:.4f}",
                      e(p["reading"]), e(p["used_for"]),
                      flag(sig) if "includes" in sig else f'<span class="badge ok">{e(sig)}</span>',
                      src('https://www.nfl.com/standings/league/2026/reg', 'nfl.com')])
    body = f"""
<h2>Measured correlations</h2>
<p class="lede">{e(data['correlations']['method'])}</p>
<div class="kpis">
{kpi(str(len(data['correlations']['pairs'])), 'Coefficients measured')}
{kpi(str(sum(1 for p in data['correlations']['pairs'] if p['ci95'][0] > 0 or p['ci95'][1] < 0)), 'Clearing zero')}
{kpi(data['correlations']['sample_note'].split(';')[0].replace(' verified final games (2026 weeks 1-10)', ''), 'Games in sample')}
{kpi('0', 'Prop correlations', 'no official prop history')}
</div>
{table(['Pair', 'r', 'n', '95% CI', 'p', 'Reading', 'Used for', 'Verdict', 'Source'],
       crows, numeric={1, 2, 3, 4},
       caption='Pearson r on verified values. A coefficient whose CI includes 0 is reported as not distinguishable from no relationship — no effect is claimed.')}
<h2>What is deliberately not measured</h2>
<ul>{''.join(f'<li>{e(x)}</li>' for x in data['correlations']['not_measured'])}</ul>
<div class="notice warn"><b>Parlay policy.</b> Legs inside a parlay will not be multiplied as if
independent. A leg pair is only allowed when a measured joint distribution exists and its
correlation clears the CI test above. At {m['inputs']['games']} games, no leg pair currently qualifies.</div>
<h2>Pythagorean luck screen</h2>
{table(['Team', 'W', 'L', 'T', 'Pythag %', 'Expected wins', 'Actual wins', 'Luck delta', 'Source'],
       [[r_['team'], str(r_['w']), str(r_['l']), str(r_['t']), f"{r_['pythag_pct']:.3f}",
         f"{r_['expected_wins']:.2f}", f"{r_['actual_wins']:.1f}", f"{r_['luck_delta']:+.2f}",
         src('https://www.nfl.com/standings/league/2026/reg', 'standings')]
        for r_ in data['luck']['teams']], numeric={4, 5, 6, 7},
       caption=f"Pythagorean expectation with exponent 2.37 (conventional, not fitted). r(pythag vs actual) = {data['luck']['r_pythag_vs_actual']:+.3f}, n=32.")}
"""
    write("correlations.html", "Correlations", body)

    # ---------------- injuries ----------------
    weeks = {w["week"]: w for w in data["injuries"]["weeks"]}
    wrows = [[str(w["week"]), str(w["rows"]), str(w["teams"]), str(w["out"]), str(w["doubtful"]),
              str(w["questionable"]), str(w["no_status"]), src(w["url"], "official report")]
             for w in data["injuries"]["weeks"]]
    latest = max(weeks)
    by_team = {}
    for r_ in data["injuries"]["rows"]:
        if r_["week"] == latest and r_["status"] in ("Out", "Doubtful", "Questionable"):
            by_team.setdefault(r_["team"], []).append(r_)
    detail = []
    for team in sorted(by_team):
        for r_ in by_team[team]:
            detail.append([team, e(r_["player"]), e(r_["pos"]), e(r_["injury"] or "—"),
                           e(r_["practice"]), f'<span class="badge {"bad" if r_["status"]=="Out" else "unv"}">{e(r_["status"])}</span>',
                           src(r_["player_url"] or r_["source"], "nfl.com")])
    body = f"""
<h2>Official injury reports</h2>
<p class="lede">Parsed directly from NFL.com's official weekly injury report pages: weeks
{min(weeks)}–{max(weeks)}. A request for a future week returns the current week's report, so
duplicate future weeks are detected and dropped rather than published twice. Blank game
statuses are preserved as blank — they mean the club had not issued a designation, not that the
player is healthy.</p>
{table(['Week', 'Rows', 'Teams', 'Out', 'Doubtful', 'Questionable', 'No status', 'Source'],
       wrows, numeric={1, 2, 3, 4, 5, 6})}
<div class="notice"><b>Reading the blanks.</b> A row with no game status means no designation was
published for that player at capture time. It never means available.</div>
<h2>Week {latest} designations</h2>
<p class="lede">{len(detail)} players carry an Out, Doubtful or Questionable designation in week {latest}.</p>
{table(['Team', 'Player', 'Pos', 'Injury', 'Practice', 'Game status', 'Source'], detail,
       caption='Every row links to the player page on NFL.com; the week source link is on the table above.')}
"""
    write("injuries.html", "Injuries", body)

    # ---------------- lineups ----------------
    d = data["deficiencies"]
    s = d["summary"]
    lrows = []
    for r_ in d["rows"]:
        if r_["join"].startswith("matched") and isinstance(r_["depth_string"], int):
            lrows.append([r_["team"], e(r_["player"]), e(r_["pos"]), e(r_["status"]),
                          str(r_["week"]), e(r_["unit"]), e(r_["slot"]),
                          f"<b>{r_['depth_string']}</b>",
                          e(r_["replacement"] or "—"),
                          e(str(r_["replacement_depth"]) or "—"),
                          src(r_["depth_source"], "club chart"),
                          src(r_["injury_source"], "injury report")])
    unmatched = [r_ for r_ in d["rows"] if not r_["join"].startswith("matched")]
    urows = [[r_["team"], e(r_["player"]), e(r_["pos"]), e(r_["status"]),
              e(r_["join"] or "no join reason recorded"),
              src(r_["injury_source"], "injury report"), flag("UNVERIFIED: depth string")]
             for r_ in unmatched]
    starter_out = sum(1 for r_ in d["rows"] if r_["depth_string"] == 1)
    body = f"""
<h2>Lineup and depth deficiencies</h2>
<p class="lede">Every player with an Out or Doubtful designation across weeks {min(s['weeks'])}–{max(s['weeks'])}
is looked up on his own club's depth chart. The result shows how deep the club has to reach:
string 1 is the starter, string 2 the primary backup, strings 3 and 4 the emergency options.
Rows are per player per week, so a player out for two weeks appears twice.</p>
<div class="kpis">
{kpi(str(s['rows']), 'Out/Doubtful rows', f"weeks {s['weeks'][0]}–{s['weeks'][-1]}")}
{kpi(str(s['matched']), 'Joined to a depth string')}
{kpi(str(starter_out), 'String-1 absences', 'starters missing from the top of the chart')}
{kpi(str(s['by_depth_string']['2'] + s['by_depth_string']['3'] + s['by_depth_string']['4']),
     'Backup promotions', 'string 2+ absences, forcing a deeper body')}
{kpi(str(s['unmatched']), 'Not joinable', 'kept visible, never guessed')}
</div>
{table(['Team', 'Player', 'Pos', 'Status', 'Wk', 'Unit', 'Slot', 'String', 'Next man up', 'NMU string', 'Depth source', 'Injury source'],
       lrows, numeric={4, 7, 9},
       caption='"Next man up" is the player listed one string lower at the same slot on the same club chart. Club charts are club-published and most are labelled unofficial by the publisher.')}
<h2>Not joinable to a depth string</h2>
<p class="lede">These players are on the official injury report but could not be matched to their
club's captured depth chart. They are listed with the reason and flagged; no depth string is
invented for them.</p>
{table(['Team', 'Player', 'Pos', 'Status', 'Why no join', 'Injury source', 'Flag'], urows)}
<h2>Defensive vs offensive split</h2>
{table(['Group', 'Out/Doubtful rows', 'Source'], [[g.capitalize(), str(n), derivation('data/desk/deficiencies.json')] for g, n in s['by_group'].items()], numeric={1})}
<div class="notice warn"><b>What this page can and cannot tell you.</b> It tells you which clubs are
reaching past their starters at a specific position. It cannot tell you how many points that costs,
because that requires a model fitted on lineup outcomes — which needs several seasons of data. The
strategy that tries to price it (<a href="strategies.html">S4/S5</a>) is explicitly unvalidated.</div>
"""
    write("lineups.html", "Lineups", body)

    # ---------------- questions ----------------
    qrows = [[e(q["id"]), e(q["area"]), e(q["question"]), e(q["known"]), e(q["missing"]),
              e(q["decision"]), flag(q["status"]) if q["status"] != "answered" else
              f'<span class="badge ok">answered</span>',
              src(q["source"], "source") if q["source"] else flag("UNVERIFIED: no official source")]
             for q in C.QUESTIONS]
    body = f"""
<h2>Questions that must be answered before a decision</h2>
<p class="lede">{len(C.QUESTIONS)} questions, each with what we know, what is missing, and the decision
it blocks. A question stays open until an official source or an explicit owner decision closes it.</p>
<div class="kpis">
{kpi(str(len(C.QUESTIONS)), 'Questions')}
{kpi(str(sum(1 for q in C.QUESTIONS if q['status'] == 'blocked')), 'Blocked on missing data')}
{kpi(str(sum(1 for q in C.QUESTIONS if q['status'] == 'open')), 'Open decisions')}
{kpi(str(sum(1 for q in C.QUESTIONS if q['status'] == 'answered')), 'Answered')}
</div>
{table(['ID', 'Area', 'Question', 'What we know', 'What is missing', 'Decision it blocks', 'Status', 'Source'],
       qrows, caption='A missing answer is never filled with an assumption; it is left blank and flagged.')}
<h2>Missing-information discovery plan</h2>
{table(['Missing item', 'How it can be obtained', 'Blocks', 'Status'], [[e(a), e(b), e(c_), flag('UNVERIFIED: not obtained')] for a, b, c_ in C.DISCOVERY])}
"""
    write("questions.html", "Questions", body)

    # ---------------- suggestions ----------------
    srows = []
    for sg in C.SUGGESTIONS:
        stat = sg["status"]
        done_now = "implemented" in stat
        badge = ('<span class="badge ok">implemented</span>' if done_now
                 else flag("UNVERIFIED: " + stat))
        srows.append([e(sg["id"]), e(sg["title"]), e(sg["problem"]), e(sg["option_a"]),
                      e(sg["option_b"]), e(sg.get("option_c", "—")), e(sg["recommendation"]),
                      e(sg["cost"]), badge, derivation("scripts/desk_content.py")])
    body = f"""
<h2>Suggestions for review</h2>
<p class="lede">Nothing on this list has been implemented beyond what is already on the site. Each
item states the problem, at least two paths, a recommendation, and what choosing it costs. Pick a
path here before any further change is built.</p>
<div class="notice"><b>How to use this page.</b> Read the problem, compare the paths, then record a
decision. Suggestions that depend on missing data point at the exact
<a href="questions.html">question</a> that must close first.</div>
{table(['ID', 'Suggestion', 'Problem', 'Option A', 'Option B', 'Option C', 'Recommendation', 'Cost / risk', 'Status', 'Provenance'],
       srows, caption='Status means awaiting a decision unless marked implemented. Nothing here is a commitment. Provenance is the file in this repository that defines the proposal.')}
<h2>Ordered decision queue</h2>
{table(['Order', 'Suggestion', 'Why this order', 'Status'], [[str(i + 1), e(x[0]), e(x[1]), flag('UNVERIFIED: awaiting decision')] for i, x in enumerate(C.ORDER)])}
"""
    write("suggestions.html", "Suggestions", body)

    # ---------------- requirements ----------------
    rrows = []
    for (rid, cat, req, acc, status, ev, source) in C.REQUIREMENTS:
        cls = {"done": "ok", "partial": "unv"}.get(status, "bad")
        rrows.append([e(rid), e(cat), e(req), e(acc),
                      f'<span class="badge {cls}">{e(status)}</span>', e(ev),
                      src(source, "evidence") if source else derivation("desk/" + rid.lower() + " page")])
    done = sum(1 for r in C.REQUIREMENTS if r[4] == "done")
    body = f"""
<h2>Requirements</h2>
<p class="lede">Every requirement in the brief, with an acceptance test and an honest status. A
requirement is only "done" when the acceptance test can be demonstrated on the published site.</p>
<div class="kpis">
{kpi(str(len(C.REQUIREMENTS)), 'Requirements')}
{kpi(str(done), 'Done', 'demonstrable on the site')}
{kpi(str(sum(1 for r in C.REQUIREMENTS if r[4] == 'partial')), 'Partial', 'possible, not complete')}
{kpi(str(sum(1 for r in C.REQUIREMENTS if r[4] == 'blocked')), 'Blocked', 'needs missing data or a decision')}
</div>
{table(['ID', 'Category', 'Requirement', 'Acceptance test', 'Status', 'Evidence', 'Source'],
       rrows, caption='"Blocked" is not a failure of effort — it states precisely what is missing and links it.')}
"""
    write("requirements.html", "Requirements", body)

    # ---------------- games ----------------
    grows = []
    for g in sorted([x for x in data["games"]["games"] if x["status"] == "FINAL"],
                    key=lambda x: (x["week"], x["date_iso"])):
        grows.append([str(g["week"]), g["date_iso"], f"{g['away']} @ {g['home']}",
                      f"{g['away_score']}–{g['home_score']}", f"{g['home_score']-g['away_score']:+d}",
                      str(g["away_score"] + g["home_score"]), src(g["source"], "nfl.com")])
    body = f"""
<h2>Verified game log</h2>
<p class="lede">Every completed 2026 regular-season game captured from NFL.com's weekly schedule
pages. This is the sole input to the model.</p>
<div class="kpis">
{kpi(str(len(grows)), 'Final games')}
{kpi(str(sorted({g['week'] for g in data['games']['games']})[-1]), 'Latest week captured')}
{kpi(f"{sum(int(r[4]) for r in grows) / max(1, len(grows)):+.2f}", 'Mean home margin', 'computed')}
{kpi(f"{sum(int(r[5]) for r in grows) / max(1, len(grows)):.1f}", 'Mean total', 'computed')}
</div>
{table(['Wk', 'Date', 'Matchup', 'Score', 'Home margin', 'Total', 'Source'], grows, numeric={0, 3, 4, 5},
       caption='Scores are transcribed from the official schedule pages; the W-L-T, PF and PA of all 32 clubs were recomputed from this table and match the official standings exactly.')}
"""
    write("games.html", "Game log", body)

    # ---------------- standings ----------------
    srows = [[r_["abbr"], e(r_["name"]), f"{r_['w']}-{r_['l']}-{r_['t']}", r_["pct"],
              str(r_["pf"]), str(r_["pa"]), f"{r_['net']:+d}", e(r_["home"]), e(r_["road"]),
              e(r_["div"]), e(r_["conf"]), e(r_["strk"]), src(r_["source"], "nfl.com")]
             for r_ in data["standings"]["rows"]]
    body = f"""
<h2>2026 standings</h2>
<p class="lede">Captured from NFL.com and independently reconciled against the game log: for all 32
clubs, W-L-T, points for and points against match exactly.</p>
{table(['Team', 'Club', 'Rec', 'Pct', 'PF', 'PA', 'Net', 'Home', 'Road', 'Div', 'Conf', 'Strk', 'Source'],
       srows, numeric={3, 4, 5, 6},
       caption='PF = points for, PA = points against. Records are formatted exactly as published.')}
"""
    write("standings.html", "Standings", body)

    # ---------------- sources ----------------
    srcs = [
        ("NFL.com — weekly schedules", "https://www.nfl.com/schedules/2026/by-week/week-1",
         "Final scores and kickoff times, weeks 1-11", f"{len(data['games']['games'])} game rows"),
        ("NFL.com — league standings", "https://www.nfl.com/standings/league/2026/reg",
         "W-L-T, PF, PA, streaks", "32 clubs"),
        ("NFL.com — official injury report", "https://www.nfl.com/injuries/league/2026/reg10",
         "Player, position, injury, practice and game status", f"{len(data['injuries']['rows']):,} rows"),
        ("NFL.com — club directory", "https://www.nfl.com/teams/",
         "Club abbreviations, names and official club sites", "32 clubs"),
        ("Club sites — depth charts", "https://www.nfl.com/teams/",
         "Depth order per position, published by each club (most labelled unofficial)",
         f"{len(data['depth']['clubs'])} charts"),
    ]
    srows = [[e(n), src(u, u.split('/')[2]), e(w), e(r_)] for n, u, w, r_ in srcs]
    body = f"""
<h2>Source register</h2>
<p class="lede">Every value on this site traces to one of these pages. Nothing is cited to a source
that was not actually read for this build.</p>
{table(['Source', 'URL', 'What it provides', 'Rows used'], srows, caption='Capture date for all pages: 2026-11-14 (UTC). Raw pages are fetched by CI, parsed deterministically, and the parser is self-tested before any dataset is written.')}
<h2>Source policy</h2>
<ul>
<li><b>Official only.</b> NFL.com for league data; the club's own site for depth charts.</li>
<li><b>No secondary aggregation.</b> If a value exists only on a betting site, it is left blank
and appears on <a href="flagged.html">Flagged for review</a>.</li>
<li><b>Reproducible.</b> The capture and parse scripts are in the repository; the self-test fails
the build if a parser silently returns nothing.</li>
<li><b>No market data.</b> No odds source is used because none is official. This is the single
largest gap in the project and it is stated as such throughout.</li>
</ul>
<h2>Method references</h2>
{table(['Method', 'Why it is used', 'Reference'], [
 ['Walk-forward validation', 'Anything fitted after seeing results is hindsight',
  src('https://scikit-learn.org/stable/modules/cross_validation.html', 'scikit-learn docs')],
 ['Deflated Sharpe ratio', 'Reward must be adjusted for how many strategies were tried',
  src('https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551', 'Bailey & López de Prado')],
 ['Probability of backtest overfitting', 'Tests whether the best result is an artefact of search',
  src('https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253', 'Bailey et al.')],
 ['Pearson correlation and Fisher z', 'Effect size with a confidence interval, not a bare r',
  src('https://www.nist.gov/publications', 'NIST')],
])}
"""
    write("sources.html", "Sources", body)

    # ---------------- repo review ----------------
    body = C.repo_review(m, data)
    write("repo-review.html", "Repo review", body)

    # ---------------- flagged ----------------
    body = C.flagged(m, data)
    write("flagged.html", "Flagged for review", body)

    # ---------------- archive ----------------
    body = C.archive(data)
    write("archive.html", "Archive", body)

    print(f"wrote {len(written)} pages: {', '.join(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
