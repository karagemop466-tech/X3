#!/usr/bin/env python3
"""Deterministic builder for the decision ledger pages in ledger/.

Inputs (read-only): data/ledger/*.csv, hub/data/lines.json (model fair lines),
data/hub/injuries_2026_wk10.csv (via verify_ledger). Every number on a page is computed
here at build time; nothing is typed into prose. Market prices are never filled: the
market columns stay blank, and the difference column is computed only when a market value
exists (none does).

Derived values are labelled DERIVED on the page:
  * final margin and total (home minus away, home plus away) from official finals
  * correlations and Fisher-z 95% intervals from official finals only, n published
  * fair moneyline = normal approximation P(home win) = Phi(fair margin / sigma), where
    sigma is the sample standard deviation of official final margins (n published).
    The approximation is uncalibrated: no market prices exist to test it against.
"""
import csv, html, json, math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verify_ledger as V  # reuse the same reconciliation and row rules
import ledger_extract as LE  # the one documented code alias (LAR->LA, AZ->ARI)

GAMES = V.ROOT / "data" / "desk" / "games.json"

ROOT = V.ROOT
OUT = ROOT / "ledger"
LINES = ROOT / "hub" / "data" / "lines.json"
WEEK_URL = "https://www.nfl.com/schedules/2026/by-week/week-{}"
STANDINGS_URL = "https://www.nfl.com/standings/league/2026/REG"
INJ_URL = "https://www.nfl.com/injuries/league/2026/reg10"
ASOF = "2026-11-14"


def esc(x):
    return html.escape(str(x), quote=True)


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def american(p):
    if p >= 0.5:
        return f"-{round(100 * p / (1 - p))}"
    return f"+{round(100 * (1 - p) / p)}"


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy)


def fisher_ci(r, n):
    z = math.atanh(r)
    se = 1.0 / math.sqrt(n - 3)
    return math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)


def compute():
    res = V.read("results_2026.csv")
    rows = []
    for g in res:
        h, a = int(g["home_score"]), int(g["away_score"])
        rows.append({**g, "h": h, "a": a, "margin": h - a, "total": h + a, "week": int(g["week"])})
    n = len(rows)
    margins = [r["margin"] for r in rows]
    mean_m = sum(margins) / n
    sigma = math.sqrt(sum((m - mean_m) ** 2 for m in margins) / (n - 1))
    corr = []
    specs = [
        ("Total points vs. home margin", [r["total"] for r in rows], [r["margin"] for r in rows],
         "signed margin (home minus away)"),
        ("Total points vs. absolute margin", [r["total"] for r in rows], [abs(r["margin"]) for r in rows],
         "size of the winning margin, unsigned"),
        ("Home points vs. away points", [r["h"] for r in rows], [r["a"] for r in rows],
         "scoring by each side"),
        ("Week number vs. total points", [r["week"] for r in rows], [r["total"] for r in rows],
         "scoring trend across weeks 1-10"),
    ]
    for label, x, y, note in specs:
        r = pearson(x, y)
        lo, hi = fisher_ci(r, len(x))
        corr.append({"label": label, "r": r, "lo": lo, "hi": hi, "n": len(x), "note": note})
    fair = []
    model = json.loads(LINES.read_text())["rows"]
    official = {}
    for g in json.loads(GAMES.read_text())["games"]:
        if g["week"] == 10 and g["status"] == "SCHEDULED":
            official[frozenset((g["away"], g["home"]))] = (g["away"], g["home"])
    for m in model:
        key = frozenset(LE.MODEL_TO_CAPTURE.get(t, t) for t in (m["home"], m["away"]))
        off_away, off_home = official[key]
        model_home = LE.MODEL_TO_CAPTURE.get(m["home"], m["home"])
        spread_model_home = m["model_spread_home"]          # sportsbook sign, model's own 'home'
        margin_model_home = -spread_model_home              # expected margin for model's 'home'
        # Re-express from the OFFICIAL home side. The team-level margin is unchanged; only the
        # label orientation differs for rows where the model's home/away is reversed.
        reversed_orientation = model_home != off_home
        margin_off_home = -margin_model_home if reversed_orientation else margin_model_home
        spread_off_home = -margin_off_home
        p_home = norm_cdf(margin_off_home / sigma)
        fair.append({
            "game": f"{off_away}@{off_home}", "home": off_home, "away": off_away,
            "date": m["date"], "slot": m["slot"], "reversed": reversed_orientation,
            "spread_home": spread_off_home, "total": m["model_total"], "p_home": p_home,
            "ml_home": american(p_home), "ml_away": american(1 - p_home),
        })
    return rows, n, sigma, mean_m, corr, fair


# ---------- HTML helpers ----------
CSS = "ledger/style.css"
NAV = [("index.html", "Overview"), ("results.html", "Results feed"), ("prices.html", "Price store &amp; origination"),
       ("depth.html", "Replacement depth"), ("leaderboard.html", "Leaderboard &amp; demotion"),
       ("correlation.html", "Correlation"), ("flagged.html", "Flagged for review")]


def page(name, title, body):
    items = []
    for h, t in NAV:
        cls = ' class="on"' if h == name else ""
        items.append('<a href="%s"%s>%s</a>' % (h, cls, t))
    nav = "".join(items)
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} - X3 decision ledger</title>
<link rel="stylesheet" href="style.css"></head>
<body>
<header class="top"><div class="brand">X3 decision ledger</div>
<div class="asof">Data as of {ASOF} (UTC) - 2026 season, Week 10</div></header>
<nav class="nav">{nav}<a href="../hub/index.html">Full decision desk</a><a href="../index.html">Site root</a></nav>
<main>
{body}
</main>
<footer>Every table row links its official source or is marked UNVERIFIED. DERIVED values are calculations from official
inputs, not predictions. This site places no bets and pays no rewards. Built by tools/build_ledger.py; checked by
tools/verify_ledger.py.</footer>
</body></html>
"""
    (OUT / name).write_text(doc)


def table(headers, rows_html, caption=""):
    th = "".join(f"<th>{h}</th>" for h in headers)
    cap = f"<caption>{caption}</caption>" if caption else ""
    return f'<div class="tw"><table>{cap}<thead><tr>{th}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>'


def link(url, label=None):
    label = label or url.replace("https://", "")
    return f'<a href="{esc(url)}" rel="noopener">{esc(label)}</a>'


def build_all():
    OUT.mkdir(exist_ok=True)
    rows, n, sigma, mean_m, corr, fair = compute()
    n_teams, mism = V.reconcile()
    dep = V.read("replacement_depth_wk10.csv")
    px = V.read("price_snapshots.csv")
    lf = V.read("leaderboard_fields.csv")
    dg = V.read("demotion_gate.csv")
    join_counts = {}
    for d in dep:
        join_counts[d["join"]] = join_counts.get(d["join"], 0) + 1
    with_repl = sum(1 for d in dep if d["replacement"])
    n_out = sum(1 for d in dep if d["game_status"] == "Out")
    n_dbt = sum(1 for d in dep if d["game_status"] == "Doubtful")
    n_px_filled = sum(1 for r in px if r["opening_value"] or r["closing_value"])
    recon_line = (f"{n_teams - len({t for t, _ in mism})} of {n_teams} clubs match the official standings on "
                  f"W, L, T, points for, points against, home and road records"
                  if n_teams else "no clubs checked")
    (OUT / "style.css").write_text(STYLE)

    # ---- index
    cards = [
        (f"{n}", "official FINAL games in the results feed", "results.html"),
        (f"{n_teams - len({t for t, _ in mism})}/{n_teams}", "clubs reconciled to the live standings", "results.html"),
        (f"{len(fair)} x 3 = {len(px)}", "originated markets (side, total, moneyline)", "prices.html"),
        (f"{n_px_filled}", "market prices recorded (no official price source)", "prices.html"),
        (f"{with_repl}/{len(dep)}", "Out or Doubtful starters with a named replacement on the club chart", "depth.html"),
        ("0", "strategies ranked on the signal leaderboard (no settled bets)", "leaderboard.html"),
    ]
    card_html = "".join(f'<a class="card" href="{h}"><div class="num">{v}</div><div class="lbl">{l}</div></a>'
                        for v, l, h in cards)
    idx_rows = [
        ["Results feed", "Official 2026 finals, one row per game, source link per row, reconciled to standings",
         "results.html"],
        ["Price store and origination", "Side, then total, then moneyline; fair, market and difference columns",
         "prices.html"],
        ["Replacement depth", "Depth of each replacement behind an Out or Doubtful starter", "depth.html"],
        ["Leaderboard and demotion", "Signal and staking tracked apart; demotion gate (proposed)", "leaderboard.html"],
        ["Correlation", "Coefficients from official finals only, with n and 95% interval", "correlation.html"],
        ["Flagged for review", "Unverified items and irregularities, with evidence links", "flagged.html"],
    ]
    idx_table = table(["Page", "What it holds", "Open"],
                      [f"<tr class=\"k-meta\"><td>{esc(a)}</td><td>{esc(b)}</td><td><a href=\"{c}\">open</a></td></tr>" for a, b, c in idx_rows])
    body = f"""<section class="hero"><h1>Decision ledger</h1>
<p>A single place for the inputs a decision needs: official results, the price store, replacement depth, the
leaderboard rules and the correlations. Blank means not verified. Nothing here is a bet recommendation.</p></section>
<section class="cards">{card_html}</section>
<section><h2>Modules</h2>{idx_table}</section>
<section><h2>What this ledger can and cannot support yet</h2>
<ul>
<li><b>Results: supported.</b> {esc(recon_line)}. Source: <a href="{STANDINGS_URL}">nfl.com standings</a>.</li>
<li><b>Prices: not supported.</b> No official source publishes 2026 opening or closing lines, so every
opening and closing cell is blank. ROI and closing-line value cannot be computed until a price source is chosen.</li>
<li><b>Signal vs staking: specified, not measured.</b> No strategy has settled bets, so the leaderboard holds no rows.</li>
<li><b>Demotion gate: proposed.</b> Thresholds are proposals for an owner decision, not adopted rules.</li>
</ul></section>"""
    page("index.html", "Overview", body)

    # ---- results
    rr = []
    for r in sorted(rows, key=lambda r: (r["week"], r["date_iso"], r["away"])):
        rr.append(f"<tr><td>{r['week']}</td><td>{esc(r['date_iso'])}</td><td>{esc(r['away'])}</td>"
                  f"<td class=\"num\">{r['a']}</td><td class=\"num\">{r['h']}</td><td>{esc(r['home'])}</td>"
                  f"<td class=\"num\">{r['margin']:+d}</td><td class=\"num\">{r['total']}</td>"
                  f"<td>{esc(r['neutral_site'])}</td><td>{link(r['source_url'], 'nfl.com week ' + str(r['week']))}</td></tr>")
    body = f"""<section class="hero"><h1>Results feed</h1>
<p><b>{n} official FINAL games</b> (2026 Weeks 1-10). Scores are as captured from nfl.com week pages. Margin and total
are <span class="tag d">DERIVED</span> from those scores. Reconciliation: {esc(recon_line)}, checked by
<code>tools/verify_ledger.py</code> against <a href="{STANDINGS_URL}">the live standings page</a>.</p></section>
{table(["Wk", "Date", "Away", "Away pts", "Home pts", "Home", "Home margin", "Total", "Neutral", "Source"], rr,
       caption="2026 FINAL games, one row per game")}"""
    page("results.html", "Results feed", body)

    # ---- prices
    fair_by_game = {frozenset((f["away"], f["home"])): f for f in fair}
    n_rev = sum(1 for f in fair if f["reversed"])
    rev_list = ", ".join(f["game"] for f in fair if f["reversed"]) or "none"
    pr = []
    for r in px:
        key = f"{r['away']}@{r['home']}"
        f = fair_by_game[frozenset((r["away"], r["home"]))]
        if r["market"] == "spread":
            fair_txt = f"{esc(f['home'])} {f['spread_home']:+.1f} (home) / {esc(f['away'])} {-f['spread_home']:+.1f}"
        elif r["market"] == "total":
            fair_txt = f"{f['total']:.1f}"
        else:
            fair_txt = f"{esc(f['home'])} {f['ml_home']} / {esc(f['away'])} {f['ml_away']}"
        pr.append(
            f"<tr><td>{esc(key)}</td><td>{esc(r['date_iso'])} {esc(r['kickoff_et'])}</td>"
            f"<td class=\"num\">{r['origination_order']}</td><td>{esc(r['market'])}</td>"
            f"<td><span class=\"tag d\">DERIVED</span> {fair_txt}</td>"
            f"<td class=\"blank\">UNVERIFIED</td><td class=\"blank\">UNVERIFIED</td>"
            f"<td class=\"blank\">blank</td><td>{esc(r['status'])}</td>"
            f"<td>{link(r['game_source_url'], 'nfl.com week 10')}</td></tr>")
    body = f"""<section class="hero"><h1>Price store and origination</h1>
<p>Every market we originate, in order: <b>1 side (spread)</b>, then <b>2 total</b>, then <b>3 moneyline</b>. For each
market the page shows the model's fair line, the market line (blank: no official price source), and the difference
(market minus fair, computed only when a market value exists). Opening and closing values stay blank until an official
or otherwise sourced price archive is adopted (owner decision, see Flagged).</p>
<p><b>Orientation:</b> home and away follow the official nfl.com listing. The model's own file labels {n_rev} games with
the home side reversed ({rev_list}); their team-level margins are unchanged and are re-expressed here. See LF-10.</p>
<p>Fair moneyline = normal approximation, P(home win) = &Phi;(fair margin / &sigma;), with &sigma; = {sigma:.2f} points, the sample
standard deviation of {n} official final margins (<span class="tag d">DERIVED</span>, uncalibrated).</p></section>
{table(["Game", "Date / kickoff ET", "Order", "Market", "Fair line (model)", "Market open", "Market close",
        "Difference", "Price status", "Source"], pr,
       caption="Week 10 unplayed games, 13 games x 3 markets")}"""
    page("prices.html", "Price store", body)

    # ---- depth
    dr = []
    for d in dep:
        repl = (f"{esc(d['replacement'])} (string {esc(d['replacement_string'])})" if d["replacement"]
                else "<span class=\"blank\">blank</span>")
        dr.append(
            f"<tr><td>{esc(d['team'])}</td><td>{esc(d['player'])}</td><td>{esc(d['position'])}</td>"
            f"<td>{esc(d['game_status'])}</td><td>{esc(d['injury'])}</td>"
            f"<td>{esc(d['unit'])} {esc(d['slot'])}</td><td class=\"num\">{esc(d['starter_string'])}</td>"
            f"<td>{repl}</td><td>{esc(d['join'])}</td><td>{esc(d['chart_labelled_unofficial'])}</td>"
            f"<td>{link(d['injury_source_url'], 'NFL injury report')}; {link(d['depth_source_url'], 'club depth chart')}</td></tr>")
    jc = "; ".join(f"{esc(k)}: {v}" for k, v in sorted(join_counts.items()))
    body = f"""<section class="hero"><h1>Replacement depth</h1>
<p><b>{len(dep)} Week-10 starters</b> listed Out ({n_out}) or Doubtful ({n_dbt}) on the official injury report. For each one the
page shows the replacement's string number on the club's own depth chart, as captured. A blank replacement means the
join failed, not that no replacement exists. Join results: {jc}.</p>
<p>Charts are self-labelled unofficial by most clubs and mostly undated, so these are <span class="tag u">UNVERIFIED</span>
inputs. Every status matches the official report (checked row by row); the Atlanta chart was re-read live for this build.</p>
</section>
{table(["Team", "Player", "Pos", "Status", "Injury", "Unit / slot", "Starter string", "Replacement (string)",
        "Join", "Chart unofficial", "Sources"], dr, caption="Out and Doubtful starters, Week 10")}"""
    page("depth.html", "Replacement depth", body)

    # ---- leaderboard & demotion
    lr = []
    for r in lf:
        lr.append(f"<tr><td>{esc(r['track'])}</td><td>{esc(r['field'])}</td><td>{esc(r['role'])}</td>"
                  f"<td>{esc(r['definition'])}</td><td>{esc(r['status'])}</td>"
                  f"<td>{link(r['source_url'], 'validation gates (hub)')}</td></tr>")
    dr2 = []
    for r in dg:
        dr2.append(f"<tr><td>{esc(r['id'])}</td><td>{esc(r['trigger'])}</td><td>{esc(r['metric'])}</td>"
                   f"<td>{esc(r['threshold'])}</td><td>{esc(r['min_sample'])}</td><td>{esc(r['action'])}</td>"
                   f"<td>{esc(r['scope'])}</td><td>{esc(r['status'])}</td>"
                   f"<td>{link(r['source_url'], 'validation gates (hub)')}</td></tr>")
    body = f"""<section class="hero"><h1>Leaderboard and demotion gate</h1>
<p><b>Ranking uses the signal track only.</b> Staking results are shown beside the signal, never inside the rank, so a
lucky staking run cannot hide a weak signal. A strategy is ranked only if every gate passes; otherwise it shows
NOT RANKED with the failing gate named.</p>
<p><b>Current leaderboard: 0 rows.</b> No strategy has settled bets or closing prices, so no signal can be measured.
The demotion thresholds below are <span class="tag u">PROPOSED</span> for an owner decision and are not in force.</p></section>
<h2>Signal and staking fields</h2>
{table(["Track", "Field", "Role", "Definition", "Status", "Source"], lr, caption="Leaderboard fields")}
<h2>Demotion gate: sends a live strategy back to paper</h2>
{table(["ID", "Trigger", "Metric", "Threshold", "Min sample", "Action", "Scope", "Status", "Source"], dr2,
       caption="Demotion rules")}"""
    page("leaderboard.html", "Leaderboard", body)

    # ---- correlation
    cr = []
    for c in corr:
        wk = " ".join(link(WEEK_URL.format(w), f"wk{w}") for w in range(1, 11))
        cr.append(f"<tr><td>{esc(c['label'])}</td><td class=\"num\">{c['r']:+.3f}</td>"
                  f"<td class=\"num\">[{c['lo']:+.3f}, {c['hi']:+.3f}]</td><td class=\"num\">{c['n']}</td>"
                  f"<td>{esc(c['note'])}</td><td>{wk}</td></tr>")
    body = f"""<section class="hero"><h1>Correlation</h1>
<p>Pearson correlations computed only from official FINAL scores (<span class="tag d">DERIVED</span>). Each row publishes
its <b>n</b> and a Fisher-z 95% interval. No price, prop or model number enters any coefficient.
Correlations between parlay legs need joint outcomes that do not yet exist, so they are not computed here.</p></section>
{table(["Pair", "r", "95% interval", "n", "Definition", "Official sources (weeks 1-10)"], cr,
       caption="Coefficients from official FINAL games")}"""
    page("correlation.html", "Correlation", body)

    # ---- flagged
    flags = [
        ("LF-01", "Price store is empty. No official source publishes 2026 opening or closing lines.",
         "UNVERIFIED", "../hub/flagged.html", "Owner decides the price source; then ingest with its own row URLs."),
        ("LF-02", f"Fair moneyline uses a normal approximation with sigma = {sigma:.2f} (n = {n}). It is uncalibrated.",
         "DERIVED", "prices.html", "Calibrate once closing prices exist; until then treat as a model output only."),
        ("LF-03", "Demotion and leaderboard thresholds are proposals, not adopted rules.",
         "PROPOSED", "leaderboard.html", "Owner decision on each D-rule and on ranking by signal only."),
        ("LF-04", "Replacement strings come from club depth charts that clubs label unofficial; most are undated.",
         "UNVERIFIED", "depth.html", "Use an official, dated depth source or keep the join as a flagged input."),
        ("LF-05", "One Week-10 Atlanta depth chart was re-read live and matched; other charts were not re-read this build.",
         "UNVERIFIED", "https://www.atlantafalcons.com/team/depth-chart", "Re-read remaining charts before relying on them."),
        ("LF-06", "The model uses LAR and AZ; the official game capture uses LA and ARI. The one alias is applied explicitly.",
         "DERIVED", "prices.html", "None; recorded so reviewers can trace the match."),
        ("LF-07", "The Week 1 game SF at LA is captured as a neutral site (East Melbourne). Not independently re-checked here.",
         "UNVERIFIED", "results.html", "Check the official game page before using neutral-site status."),
        ("LF-08", "The ledger is not yet linked from the root landing or the decision desk. PR #36 (arena/e9b492ab-x3) is open and conflicting on the hub files.",
         "UNVERIFIED", "https://github.com/karagemop466-tech/X3/pull/36", "Integration session adds the link after PR #36 is resolved."),
        ("LF-10", f"Model file hub/data/lines.json lists the home side reversed for {n_rev} games ({rev_list}) "
         "against the official listing. Team-level margins are unchanged; the ledger re-expresses them from the official home side.",
         "UNVERIFIED", "https://www.nfl.com/schedules/2026/by-week/week-10",
         "Owner corrects the orientation in the model (hub) after PR #36 is resolved; then re-run the ledger."),
        ("LF-09", "The live standings page text contains an unrendered template heading ('$year$ NFL $displayname$ Standings'). Only the table values are used.",
         "UNVERIFIED", STANDINGS_URL, "Note only; no value depends on the heading."),
    ]
    fr = []
    for fid, item, tag, ev, act in sorted(flags, key=lambda f: f[0]):
        ev_html = link(ev, ev) if ev.startswith("http") else f'<a href="{esc(ev)}">{esc(ev)}</a>'
        fr.append(f"<tr><td>{fid}</td><td>{esc(item)}</td><td><span class=\"tag u\">{esc(tag)}</span></td>"
                  f"<td>{ev_html}</td><td>{esc(act)}</td></tr>")
    body = f"""<section class="hero"><h1>Flagged for review</h1>
<p>Open items for the owner. None of them blocks publication: each one is either marked UNVERIFIED, DERIVED or PROPOSED on
the page where it applies, or is a note.</p></section>
{table(["ID", "Item", "Status", "Evidence", "What closes it"], fr, caption="Ledger flags")}"""
    page("flagged.html", "Flagged for review", body)
    return {"results": n, "clubs": n_teams, "mismatch": len(mism), "fair_games": len(fair), "price_rows": len(px),
            "depth_rows": len(dep), "sigma": round(sigma, 4), "corr": [(c["label"], round(c["r"], 4), c["n"]) for c in corr]}


STYLE = """
:root{--ink:#14202b;--mut:#5b6b7a;--line:#dbe3ea;--bg:#f6f8fa;--acc:#0b5cad;--warn:#8a5a00;--warnbg:#fff4d6;--ok:#17603b;--okbg:#e4f5ec}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header.top{background:#0f2a43;color:#fff;padding:14px 22px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.brand{font-weight:700;letter-spacing:.2px}.asof{opacity:.85;font-size:13px}
nav.nav{background:#fff;border-bottom:1px solid var(--line);padding:8px 16px;display:flex;gap:4px;flex-wrap:wrap}
nav.nav a{color:var(--ink);text-decoration:none;padding:6px 10px;border-radius:6px;font-size:14px}
nav.nav a:hover{background:#eef4fa}nav.nav a.on{background:var(--acc);color:#fff}
main{max-width:1200px;margin:0 auto;padding:18px 16px 40px}
h1{font-size:24px;margin:8px 0 6px}h2{font-size:18px;margin:26px 0 8px}
.hero p{max-width:900px;color:var(--ink)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px;text-decoration:none;color:var(--ink)}
.card:hover{border-color:var(--acc)}.num{font-variant-numeric:tabular-nums}
.card .num{font-size:24px;font-weight:700;color:var(--acc)}.card .lbl{color:var(--mut);font-size:13px;margin-top:4px}
.tw{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:10px;margin-bottom:14px}
table{border-collapse:collapse;width:100%;font-size:13.5px}caption{text-align:left;padding:8px 10px;color:var(--mut);font-size:13px}
th,td{padding:7px 10px;border-top:1px solid var(--line);vertical-align:top;text-align:left}
th{background:#f0f4f8;position:sticky;top:0;font-weight:600}
td.num,th.num{text-align:right}td.blank{color:var(--warn);background:var(--warnbg)}
.tag{display:inline-block;font-size:11px;font-weight:700;padding:1px 6px;border-radius:4px;letter-spacing:.3px}
.tag.d{background:#e6eefb;color:#174d8c}.tag.u{background:var(--warnbg);color:var(--warn)}
footer{max-width:1200px;margin:0 auto;padding:14px 16px 30px;color:var(--mut);font-size:12.5px;border-top:1px solid var(--line)}
a{color:var(--acc)}code{background:#eef2f6;padding:1px 4px;border-radius:3px}
ul{max-width:900px}li{margin:4px 0}
"""

if __name__ == "__main__":
    summary = build_all()
    print(json.dumps(summary, indent=1))
