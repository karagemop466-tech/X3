#!/usr/bin/env python3
"""Render the X3 decision-support site from the curated content and the
verified official datasets.

Every table row that carries a dataset value also carries the official source
link it was read from. A value that the official source does not publish is
rendered as an explicit 'unverified' marker and is listed on the Flagged for
Review page. Nothing is inferred.
"""

from __future__ import annotations

import html
import json
import os
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.diagnostics import failure_report
from lib.markdown import render as render_markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content")
DATA = os.path.join(ROOT, "data", "datasets")
ASSETS_SRC = os.path.join(ROOT, "scripts", "assets")
OUT = ROOT

NFL_COM = "https://www.nfl.com"
STANDINGS_URL = "https://www.nfl.com/standings/league/2026/REG"
INJURY_URL = "https://www.nfl.com/injuries/"
SCHEDULE_URL = "https://www.nfl.com/schedules/2026/REG10/"
STATS_URL = "https://www.nfl.com/stats/player-stats/"

NAV = [
    (
        "Overview",
        [
            ("index.html", "Dashboard"),
            ("executive-summary.html", "Executive Summary"),
            ("findings.html", "Findings &amp; Analysis"),
        ],
    ),
    (
        "Requirements",
        [("requirements.html", "Requirements Register")],
    ),
    (
        "Decision Support",
        [
            ("questions.html", "Questions &amp; Information Needed"),
            ("suggestions.html", "Suggestions &amp; Decision Paths"),
        ],
    ),
    (
        "Strategy",
        [
            ("strategies.html", "Strategies &amp; Validation Gates"),
            ("leaderboard.html", "Leaderboard Competition"),
        ],
    ),
    (
        "Data",
        [
            ("injuries.html", "Official Injury Report"),
            ("depth.html", "Lineup Depth &amp; Deficiencies"),
            ("lines.html", "Our Originated Lines"),
            ("data.html", "Datasets &amp; Correlations"),
        ],
    ),
    (
        "Governance",
        [
            ("flagged.html", "Flagged for Review"),
            ("sources.html", "Sources &amp; Methodology"),
            ("methodology.html", "Methodology"),
            ("validation.html", "Validation Report"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def e(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def load(name: str, folder: str = CONTENT):
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def badge(text: str, kind: str = "muted") -> str:
    return f'<span class="badge {kind}">{e(text)}</span>'


def unverified(label: str = "unverified") -> str:
    return (
        '<span class="unverified" title="Not published by the official source. '
        "Left blank by policy; never inferred.\">" + e(label) + "</span>"
    )


def cell(value, source_url: str = "", source_label: str = "Official source") -> str:
    """Render a dataset value with its source link, or an unverified marker."""
    if value is None or str(value).strip() == "":
        return unverified()
    out = e(value)
    if source_url:
        out += (
            f' <a class="src-link" href="{e(source_url)}" target="_blank" '
            f'rel="noopener" title="{e(source_label)}">source</a>'
        )
    return out


def num_cell(value, source_url: str = "", dp: int | None = None) -> str:
    if value is None or str(value).strip() == "":
        return unverified()
    try:
        f = float(value)
    except (TypeError, ValueError):
        return cell(value, source_url)
    text = f"{f:.{dp}f}" if dp is not None else (f"{f:g}")
    out = f'<span class="mono">{e(text)}</span>'
    if source_url:
        out += (
            f' <a class="src-link" href="{e(source_url)}" target="_blank" '
            f'rel="noopener">source</a>'
        )
    return out


def table(
    headers: list,
    rows: list,
    caption: str = "",
    table_id: str = "",
    source_url: str = "",
) -> str:
    """Render a sortable, filterable table.

    ``headers`` items are (label, sortable, numeric) tuples.
    """
    thead = []
    for h in headers:
        label, sortable, numeric = h
        cls = ["sortable"] if sortable else []
        if numeric:
            cls.append("num")
        attrs = ""
        if sortable:
            attrs = f' class="{" ".join(cls)}" data-numeric="{1 if numeric else 0}"'
        else:
            attrs = f' class="{" ".join(cls)}"' if cls else ""
        thead.append(f"<th{attrs}>{label}</th>")
    body = []
    for row in rows:
        tds = []
        for cell_html in row:
            tds.append(f"<td>{cell_html}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    cap = f'<p class="caption">{caption}</p>' if caption else ""
    src = (
        f'<p class="caption">Source: <a href="{e(source_url)}" target="_blank" rel="noopener">{e(source_url)}</a></p>'
        if source_url
        else ""
    )
    tid = f' id="{e(table_id)}"' if table_id else ""
    return (
        f'<div class="table-tools"><input type="search" placeholder="Filter rows…" aria-label="Filter rows">'
        f'<span class="count"></span></div>'
        f'<div class="table-wrap"><table{tid}><thead><tr>{"".join(thead)}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>{cap}{src}'
    )


def kv(pairs) -> str:
    items = "".join(f"<dt>{e(k)}</dt><dd>{v}</dd>" for k, v in pairs)
    return f'<dl class="kv">{items}</dl>'


def details(summary: str, body: str, open_attr: bool = False) -> str:
    return (
        f'<details{" open" if open_attr else ""}><summary>{summary}</summary>'
        f'<div class="detail-body">{body}</div></details>'
    )


def page(title: str, eyebrow: str, subtitle: str, body: str, active: str, extra_head: str = "") -> str:
    nav_html = []
    for group, items in NAV:
        links = []
        for href, label in items:
            cls = "active" if href == active else ""
            links.append(f'<a href="{href}" class="{cls}">{label}</a>')
        nav_html.append(
            f'<div class="nav-group"><a href="{items[0][0]}">{e(group)}'
            f'<span class="nav-caret">▼</span></a><div class="nav-menu">{"".join(links)}</div></div>'
        )

    freshness = FRESHNESS_HTML

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · X3 NFL Decision Support</title>
<meta name="description" content="{e(subtitle)}">
<link rel="stylesheet" href="assets/style.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%234a9eff'/><text x='16' y='22' font-size='16' font-family='sans-serif' font-weight='bold' text-anchor='middle' fill='%2306121f'>X3</text></svg>">
{extra_head}
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <div class="brand">
      <span class="brand-mark">X3</span>
      <span><a href="index.html">X3</a> <span class="brand-sub">NFL Decision Support</span></span>
    </div>
    <nav class="nav">{"".join(nav_html)}</nav>
    {freshness}
  </div>
</header>
<main>
  <div class="page-head">
    <div class="eyebrow">{eyebrow}</div>
    <h1>{title}</h1>
    <p class="sub">{subtitle}</p>
  </div>
  {body}
</main>
<footer class="site-footer">
  <div class="footer-inner">
    <div>
      <strong style="color:var(--text-dim)">X3 — NFL Decision Support.</strong>
      Every value on this site is read from an official NFL or official NFL club source and carries a source link.
      Values the official source does not publish are left blank and flagged, never inferred.
    </div>
    <div>
      <a href="sources.html">Sources &amp; methodology</a> ·
      <a href="flagged.html">Flagged for review</a> ·
      <a href="validation.html">Validation report</a> ·
      <a href="https://github.com/karagemop466-tech/X3" target="_blank" rel="noopener">Repository</a>
    </div>
  </div>
</footer>
<script src="assets/app.js"></script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# global state
# ---------------------------------------------------------------------------

STATE: dict = {}


def freshness_html() -> str:
    manifest = STATE.get("manifest")
    text = "Data age unknown"
    cls = ""
    if manifest:
        ts = manifest.get("fetched_at")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                age = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
                text = f"Data as of {dt.strftime('%Y-%m-%d %H:%M UTC')} · {age:.0f}h old"
                cls = " stale" if age > 48 else ""
            except ValueError:
                text = f"Data as of {ts}"
    return f'<span class="freshness{cls}">{e(text)}</span>'


FRESHNESS_HTML = ""


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------


def build_index() -> str:
    reqs = load("requirements.json")["requirements"]
    qs = load("questions.json")["questions"]
    sug = load("suggestions.json")["suggestions"]
    strat = load("strategies.json")["strategies"]
    inj = load("injuries.json", DATA)
    lines = load("our_lines.json", DATA)
    lb = load("leaderboard_rows.json", DATA)
    derived = load("derived.json", DATA) or {}

    implemented = sum(1 for r in reqs if r["status"] == "implemented")
    partial = sum(1 for r in reqs if r["status"] == "partial")
    blocking = [q for q in qs if q["blocking"] == "yes"]
    open_q = [q for q in qs if q["status"] == "open"]
    proposed = [s for s in sug if s["status"] == "proposed"]
    flagged = STATE.get("flagged_count", 0)

    rows_elig = lb.get("rows", []) if lb else []
    evaluated = [r for r in rows_elig if (r.get("metrics") or {}).get("bets")]
    eligible = [r for r in evaluated if STATE.get("eligible_ids", []) and r["strategy_id"] in STATE["eligible_ids"]]

    week = (inj or {}).get("week")
    inj_rows = (inj or {}).get("rows", [])
    out_count = sum(1 for r in inj_rows if r.get("game_status") == "Out")
    q_count = sum(1 for r in inj_rows if r.get("game_status") == "Questionable")
    d_count = sum(1 for r in inj_rows if r.get("game_status") == "Doubtful")

    body = []
    body.append(
        '<div class="grid cols-4">'
        + f'<div class="card kpi accent"><div class="value">{implemented}</div><div class="label">Requirements implemented</div>'
        f'<div class="note">{partial} partial · {len(reqs)} total</div></div>'
        + f'<div class="card kpi warn"><div class="value">{len(open_q)}</div><div class="label">Open questions</div>'
        f'<div class="note">{len(blocking)} block a decision</div></div>'
        + f'<div class="card kpi purple"><div class="value">{len(proposed)}</div><div class="label">Suggestions awaiting review</div>'
        f'<div class="note">{len(sug)} total on the board</div></div>'
        + f'<div class="card kpi bad"><div class="value">{flagged}</div><div class="label">Items flagged for review</div>'
        f'<div class="note">Unverified values and irregularities</div></div>'
        + "</div>"
    )

    body.append('<div class="grid cols-2" style="margin-top:14px">')
    body.append(
        '<div class="card"><h2>What needs a decision from you</h2>'
        + "<p>The questions below block a decision that cannot reasonably be made on the information currently held. "
        "Each one names what is known, what is missing and how to get it.</p>"
        + "".join(
            details(
                f'<span class="id-chip">{e(q["id"])}</span> {e(q["question"])}',
                f'<p class="prose">{e(q["why_it_matters"])}</p>'
                + f'<p class="prose"><strong>Blocks:</strong> {e(q["decision_blocked"])}</p>'
                + '<div class="known-box"><h5>What we know</h5><ul class="tight">'
                + (
                    "".join(
                        f'<li>{e(k["fact"])} (<a href="{e(k["source_url"])}" target="_blank" rel="noopener">{e(k["source_label"] or k["source_url"])}</a>)</li>'
                        for k in q.get("known", [])
                        if k.get("source_url")
                    )
                    or "<li>Nothing in this area has been confirmed from an official source yet.</li>"
                )
                + "</ul></div>"
                + '<div class="unknown-box"><h5>What is missing</h5><ul class="tight">'
                + "".join(f"<li>{e(x)}</li>" for x in q.get("unknown", []))
                + "</ul></div>"
                + "<h5 style='font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-faint)'>How to obtain it</h5>"
                + '<ul class="tight">'
                + "".join(f"<li>{e(s)}</li>" for s in q.get("how_to_obtain", []))
                + "</ul>",
            )
            for q in blocking[:4]
        )
        + '<p style="margin-top:12px"><a href="questions.html">See all ' + str(len(open_q)) + " questions →</a></p></div>"
    )

    sug_rows = []
    for s in proposed[:6]:
        sug_rows.append(
            [
                f'<span class="id-chip">{e(s["id"])}</span>',
                e(s["title"]),
                badge(s["priority"], {"P0": "bad", "P1": "warn", "P2": "muted"}.get(s["priority"], "muted")),
                e(s["category"]),
                f'<a href="suggestions.html#{e(s["id"])}">review →</a>',
            ]
        )
    body.append(
        '<div class="card"><h2>Suggestions awaiting your review</h2>'
        "<p>Each suggestion is a proposal with alternative paths and trade-offs. Nothing is applied until a path is chosen.</p>"
        + table(
            [("ID", False, False), ("Suggestion", False, False), ("Priority", False, False), ("Category", False, False), ("", False, False)],
            sug_rows,
        )
        + '<p style="margin-top:10px"><a href="suggestions.html">Open the suggestions board →</a></p></div>'
    )
    body.append("</div>")

    # current state
    body.append('<h2 style="margin:28px 0 12px;font-size:18px">Current official state</h2>')
    body.append('<div class="grid cols-4">')
    if inj:
        body.append(
            f'<div class="card kpi"><div class="value">{e(week) or "—"}</div><div class="label">Injury report week</div>'
            f'<div class="note">{len(inj_rows)} players reported</div></div>'
        )
        body.append(
            f'<div class="card kpi bad"><div class="value">{out_count}</div><div class="label">Out</div>'
            f'<div class="note">Game status from the official report</div></div>'
        )
        body.append(
            f'<div class="card kpi warn"><div class="value">{q_count}</div><div class="label">Questionable</div>'
            f'<div class="note">Game status from the official report</div></div>'
        )
        body.append(
            f'<div class="card kpi ok"><div class="value">{d_count}</div><div class="label">Doubtful</div>'
            f'<div class="note">Game status from the official report</div></div>'
        )
    if lines:
        body.append(
            f'<div class="card kpi accent"><div class="value">{len(lines.get("lines", []))}</div>'
            f'<div class="label">Originated lines</div><div class="note">Model {e(lines.get("model_version", ""))}</div></div>'
        )
    if derived.get("league_points_per_game") is not None:
        body.append(
            f'<div class="card kpi purple"><div class="value">{derived["league_points_per_game"]:.2f}</div>'
            f'<div class="label">League points per team per game</div><div class="note">Official standings, 2026</div></div>'
        )
    body.append("</div>")

    if lines and lines.get("lines"):
        rows = []
        for ln in lines["lines"]:
            rows.append(
                [
                    e(ln["game_date"]),
                    f'{e(ln["away_team"])} @ {e(ln["home_team"])}',
                    e(ln["published_spread"]),
                    e(ln["published_total"]),
                    f'{ln["fair_home_win_probability"]:.3f}',
                    f'{ln["published_home_price"]:.3f}',
                    '<a href="lines.html">detail →</a>',
                ]
            )
        body.append(
            '<h2 style="margin:26px 0 10px;font-size:16px">This week&rsquo;s originated lines</h2>'
            + table(
                [
                    ("Date", False, False),
                    ("Matchup", False, False),
                    ("Spread (home)", True, True),
                    ("Total", True, True),
                    ("Fair P(home)", True, True),
                    ("Published price", True, True),
                    ("", False, False),
                ],
                rows,
                caption=f"Originated by the platform's own model ({e(lines.get('model_version', ''))}). "
                f"Full method on the <a href=\"lines.html\">lines page</a>.",
            )
        )

    body.append(
        '<div class="callout" style="margin-top:26px"><h4>How to read this platform</h4>'
        "<p><strong>Verified</strong> means the value was read from an official NFL or official NFL club page, and the row links to it. "
        "<strong>Unverified</strong> means the official source does not publish that value, so it is left blank and listed on the "
        "<a href=\"flagged.html\">Flagged for Review</a> page. No value on this site is inferred, estimated or filled in from a proxy. "
        "Where a statistic could not be computed because the required official dataset is missing, the statistic is omitted and the omission is "
        "listed with the reason.</p></div>"
    )
    return page(
        "Dashboard",
        "Overview",
        "Everything on this platform is built from official NFL sources. Start with the decisions that are waiting on you, then work down to the data.",
        "".join(body),
        "index.html",
    )


def build_executive_summary() -> str:
    reqs = load("requirements.json")["requirements"]
    qs = load("questions.json")["questions"]
    sug = load("suggestions.json")["suggestions"]
    inj = load("injuries.json", DATA)
    lines = load("our_lines.json", DATA)
    derived = load("derived.json", DATA) or {}

    implemented = sum(1 for r in reqs if r["status"] == "implemented")
    blocking = [q for q in qs if q["blocking"] == "yes"]
    proposed = [s for s in sug if s["status"] == "proposed"]

    inj_rows = (inj or {}).get("rows", [])
    out_count = sum(1 for r in inj_rows if r.get("game_status") == "Out")
    q_count = sum(1 for r in inj_rows if r.get("game_status") == "Questionable")

    b = []
    b.append('<div class="callout"><h4>Purpose</h4><p>To give the owner a complete, verifiable basis for deciding how to act on NFL '
             "markets: a requirements register, an explicit list of what is known and unknown, a reviewable set of suggested improvements "
             "with alternative paths, a research programme for self-originated lines and strategies with machine-enforced validation gates, "
             "a competition that rewards skill rather than luck, and continuous official injury and depth tracking.</p></div>")

    b.append("<h2>Where the work stands</h2>")
    b.append(
        '<div class="grid cols-4">'
        f'<div class="card kpi accent"><div class="value">{implemented}/{len(reqs)}</div><div class="label">Requirements implemented</div></div>'
        f'<div class="card kpi warn"><div class="value">{len(blocking)}</div><div class="label">Questions that block a decision</div></div>'
        f'<div class="card kpi purple"><div class="value">{len(proposed)}</div><div class="label">Suggestions awaiting a path choice</div></div>'
        f'<div class="card kpi bad"><div class="value">{STATE.get("flagged_count", 0)}</div><div class="label">Flagged for review</div></div>'
        "</div>"
    )

    b.append("<h2>What the official data currently says</h2>")
    facts = []
    if inj:
        facts.append(
            f'The official NFL injury report for Week {inj.get("week")} contains <strong>{len(inj_rows)}</strong> player entries across '
            f'<strong>{len(inj.get("games", []))}</strong> games. <strong>{out_count}</strong> players carry an Out game status and '
            f"<strong>{q_count}</strong> are Questionable."
        )
    if derived.get("league_points_per_game") is not None:
        facts.append(
            f'The 2026 league average is <strong>{derived["league_points_per_game"]:.2f}</strong> points per team per game, computed from the '
            "official league standings."
        )
    if lines and lines.get("scales", {}).get("n_games"):
        sc = lines["scales"]
        facts.append(
            f'Across <strong>{sc["n_games"]}</strong> completed games with official final scores, the standard deviation of the scoring '
            f'margin is <strong>{sc["margin_sd"]:.2f}</strong> points and the average home margin is '
            f'<strong>{sc["home_avg_margin"]:.2f}</strong> points. Both are used by the platform&rsquo;s own line model.'
        )
    if not facts:
        facts.append(
            "The datasets needed for the quantitative summary were not present in this build, so no figures are quoted. See the "
            "<a href=\"flagged.html\">Flagged for Review</a> page for the specific omissions and their reasons."
        )
    b.append('<div class="card"><ul class="tight">' + "".join(f"<li>{f}</li>" for f in facts) + "</ul></div>")

    b.append("<h2>The five decisions that matter most</h2>")
    decisions = [
        (
            "Is this a private analysis tool or a published line operation?",
            "Everything downstream depends on it: the reward structure, whether a public leaderboard is appropriate, and whether a "
            "wagering interface may ever be built. It is question Q-001 and it is blocking.",
        ),
        (
            "Which market universe is in scope?",
            "Spread, moneyline, total and which player-prop types. This determines the official data that must be ingested and, "
            "therefore, which of the three strategy classes can actually be competed. It is question Q-023 and it is blocking.",
        ),
        (
            "What are the gate thresholds that define eligibility?",
            "Sample size, drawdown limit, skill-share threshold and correlation limit. Until these are set, the leaderboard can rank "
            "strategies but cannot reward them. It is question Q-008 and it is blocking.",
        ),
        (
            "May strategies be scored against an independent reference, or only against our own lines?",
            "Judging a strategy against the model that priced the game measures agreement, not skill. Suggestion S-002 proposes a "
            "two-model separation that stays entirely inside the official-data rule. It is question Q-010 and it is blocking.",
        ),
        (
            "Is there budget for official per-game box scores?",
            "Without per-game player logs the player-prop and prop-combination classes cannot be evaluated at all, so the competition "
            "would cover only two of the three classes the brief names. It is question Q-005.",
        ),
    ]
    b.append('<div class="grid cols-2">')
    for i, (title, detail) in enumerate(decisions, 1):
        b.append(
            f'<div class="card"><h3><span class="id-chip">{i}</span> {e(title)}</h3><p>{detail}</p></div>'
        )
    b.append("</div>")

    b.append("<h2>What is deliberately not done</h2>")
    b.append(
        '<div class="grid cols-3">'
        '<div class="card"><h3>No commercial lines are ingested</h3><p>The platform originates every line it publishes from official data. '
        "No betting feed, projection service or third-party injury source is used anywhere in the pipeline.</p></div>"
        '<div class="card"><h3>No value is inferred</h3><p>Where an official source does not publish a value, the cell is left blank and '
        "flagged. Where a statistic cannot be computed because its dataset is missing, the statistic is omitted and the omission is "
        "recorded with its reason.</p></div>"
        '<div class="card"><h3>No change is applied without a decision</h3><p>Suggestions are published with alternative paths and a '
        "recommendation, but every one of them stays in the <em>proposed</em> state until a reviewer chooses a path.</p></div>"
        "</div>"
    )

    b.append("<h2>Recommended next actions</h2>")
    actions = [
        ("Answer Q-001, Q-002 and Q-003", "A single sentence each. These three unlock the legal and commercial design."),
        ("Answer Q-008, Q-009 and Q-011", "The gate thresholds. They turn the leaderboard from a ranking into a competition."),
        ("Choose a path for suggestions S-002, S-005, S-006 and S-013", "These four decide whether the leaderboard measures skill at all."),
        ("Answer Q-023 and Q-005", "The market universe and the per-game data decision, which together determine the strategy coverage."),
    ]
    rows = [[f'<span class="id-chip">{i}</span>', e(a), e(d), badge("awaiting review", "warn")] for i, (a, d) in enumerate(actions, 1)]
    b.append(
        table(
            [("#", False, False), ("Action", False, False), ("Why", False, False), ("Status", False, False)],
            rows,
        )
    )

    b.append(
        '<div class="callout warn" style="margin-top:22px"><h4>Flagged items do not block delivery</h4>'
        "<p>Unverified values and irregularities are published on the <a href=\"flagged.html\">Flagged for Review</a> page with the source "
        "link that was checked, so they can be reviewed after the site is live and acted on then. They do not block the platform, and they "
        "are never filled in by guesswork in the meantime.</p></div>"
    )

    return page(
        "Executive Summary",
        "Overview",
        "Purpose, current state, the decisions that are ready, the decisions that are blocked, and the recommended next actions.",
        "".join(b),
        "executive-summary.html",
    )


def build_requirements() -> str:
    data = load("requirements.json")
    reqs = data["requirements"]
    b = []
    b.append(
        f'<p class="prose">{e(data["meta"]["subtitle"])}</p>'
    )
    counts = {}
    for r in reqs:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    b.append('<div class="grid cols-4">')
    for cat, n in counts.items():
        b.append(f'<div class="card kpi"><div class="value">{n}</div><div class="label">{e(cat)}</div></div>')
    b.append("</div>")

    status_kind = {
        "implemented": "ok",
        "partial": "warn",
        "planned": "info",
        "blocked": "bad",
    }
    rows = []
    for r in reqs:
        src = (
            f'<a href="{e(r["source_url"])}" target="_blank" rel="noopener">{e(r["source_url"])}</a>'
            if r.get("source_url")
            else e(r.get("source", ""))
        )
        rows.append(
            [
                f'<span class="id-chip">{e(r["id"])}</span>',
                e(r["category"]),
                f'<strong>{e(r["requirement"])}</strong>'
                + (f'<br><span style="color:var(--text-dim)"><em>Rationale:</em> {e(r["rationale"])}</span>' if r.get("rationale") else "")
                + (f'<br><span style="color:var(--text-faint)"><em>Acceptance:</em> {e(r["acceptance_criteria"])}</span>' if r.get("acceptance_criteria") else ""),
                badge(r["priority"], {"P0": "bad", "P1": "warn", "P2": "muted"}.get(r["priority"], "muted")),
                badge(r["status"], status_kind.get(r["status"], "muted")),
                src,
                e(r.get("verification", "")),
            ]
        )
    b.append(
        "<h2>Requirements register</h2>"
        + table(
            [
                ("ID", False, False),
                ("Category", False, False),
                ("Requirement", False, False),
                ("Priority", False, False),
                ("Status", False, False),
                ("Source", False, False),
                ("Verification performed", False, False),
            ],
            rows,
            caption=f"{len(reqs)} requirements traced to the project brief of {e(data['meta']['brief_source'])}.",
        )
    )
    b.append("<h2>Status legend</h2><div class=\"card\">" + kv(
        [(k, e(v)) for k, v in data["meta"]["status_legend"].items()]
    ) + kv([(k, e(v)) for k, v in data["meta"]["priority_legend"].items()]) + "</div>")
    return page(
        "Requirements Register",
        "Requirements",
        data["meta"]["subtitle"],
        "".join(b),
        "requirements.html",
    )


def build_questions() -> str:
    data = load("questions.json")
    qs = data["questions"]
    b = []
    blocking = [q for q in qs if q["blocking"] == "yes"]
    b.append(f'<p class="prose">{e(data["meta"]["subtitle"])}</p>')
    b.append('<div class="grid cols-4">')
    b.append(f'<div class="card kpi bad"><div class="value">{len(blocking)}</div><div class="label">Blocking questions</div></div>')
    b.append(f'<div class="card kpi warn"><div class="value">{len(qs) - len(blocking)}</div><div class="label">Non-blocking questions</div></div>')
    b.append(f'<div class="card kpi"><div class="value">{len(qs)}</div><div class="label">Questions on the register</div></div>')
    b.append(f'<div class="card kpi accent"><div class="value">{len(set(q["topic"] for q in qs))}</div><div class="label">Topics covered</div></div>')
    b.append("</div>")

    for q in qs:
        known = q.get("known", [])
        known_html = (
            '<div class="known-box"><h5>What we already know</h5><ul class="tight">'
            + "".join(
                f'<li>{e(k["fact"])}'
                + (
                    f' (<a href="{e(k["source_url"])}" target="_blank" rel="noopener">{e(k.get("source_label") or k["source_url"])}</a>)'
                    if k.get("source_url")
                    else " — " + e(k.get("source_label", "internal"))
                )
                + "</li>"
                for k in known
            )
            + "</ul></div>"
            if known
            else '<div class="known-box"><h5>What we already know</h5><p class="prose" style="margin:0">'
            "Nothing in this area has been confirmed from an official source yet. The platform has not assumed a value.</p></div>"
        )
        body = (
            f'<p class="prose">{e(q["why_it_matters"])}</p>'
            + kv(
                [
                    ("Blocks", e(q["decision_blocked"])),
                    ("Owner", e(q.get("owner", ""))),
                    ("Status", badge(q.get("status", "open"), "warn" if q.get("status") == "open" else "ok")),
                ]
            )
            + known_html
            + '<div class="unknown-box"><h5>What is missing</h5><ul class="tight">'
            + "".join(f"<li>{e(x)}</li>" for x in q.get("unknown", []))
            + "</ul></div>"
            + "<h5 style='font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-faint);margin-top:12px'>"
            "Suggested actions to discover the missing information</h5><ul class=\"tight\">"
            + "".join(f"<li>{e(s)}</li>" for s in q.get("how_to_obtain", []))
            + "</ul>"
        )
        b.append(
            details(
                f'<span class="id-chip">{e(q["id"])}</span> {e(q["question"])} '
                + badge(q["topic"], "muted")
                + (" " + badge("blocking", "bad") if q["blocking"] == "yes" else " " + badge("non-blocking", "info")),
                body,
                open_attr=(q["blocking"] == "yes"),
            )
        )
    return page(
        "Questions &amp; Information Needed",
        "Decision Support",
        data["meta"]["subtitle"],
        "".join(b),
        "questions.html",
    )


def build_suggestions() -> str:
    data = load("suggestions.json")
    sugs = data["suggestions"]
    b = []
    b.append(f'<p class="prose">{e(data["meta"]["subtitle"])}</p>')
    proposed = [s for s in sugs if s["status"] == "proposed"]
    b.append('<div class="grid cols-4">')
    b.append(f'<div class="card kpi purple"><div class="value">{len(proposed)}</div><div class="label">Awaiting a path choice</div></div>')
    b.append(f'<div class="card kpi ok"><div class="value">{sum(1 for s in sugs if s["status"] == "adopted")}</div><div class="label">Adopted</div></div>')
    b.append(f'<div class="card kpi"><div class="value">{len(sugs)}</div><div class="label">Suggestions on the board</div></div>')
    b.append(f'<div class="card kpi accent"><div class="value">{sum(1 for s in sugs if s["priority"] == "P0")}</div><div class="label">At P0 priority</div></div>')
    b.append("</div>")

    b.append('<div class="callout"><h4>How to review</h4><p>' + e(data["meta"]["how_to_review"]) + "</p></div>")

    for s in sugs:
        paths_html = []
        for p in s.get("paths", []):
            recommended = p["id"] == s.get("recommended_path")
            pros = "".join(f'<li class="pro">{e(x)}</li>' for x in p.get("pros", []))
            cons = "".join(f'<li class="con">{e(x)}</li>' for x in p.get("cons", []))
            paths_html.append(
                f'<div class="path-option{" recommended" if recommended else ""}">'
                f"<h4><span class=\"id-chip\">Path {e(p['id'])}</span> {e(p['name'])}"
                + (badge("recommended", "ok") if recommended else "")
                + "</h4>"
                f'<p class="prose">{e(p.get("description", ""))}</p>'
                + (f"<ul class=\"tight\">{pros}</ul>" if pros else "")
                + (f"<ul class=\"tight\">{cons}</ul>" if cons else "")
                + '<div class="path-meta">'
                + f"<span><b>Cost</b> {e(p.get('cost', ''))}</span>"
                + f"<span><b>Effort</b> {e(p.get('effort', ''))}</span>"
                + f"<span><b>Risk</b> {e(p.get('risk', ''))}</span>"
                + f"<span><b>Reversible</b> {e(p.get('reversible', ''))}</span>"
                + "</div></div>"
            )
        deps = "".join(f'<span class="id-chip" style="margin-right:5px">{e(d)}</span>' for d in s.get("dependencies", []))
        evidence = "".join(
            f'<li>{e(ev["fact"])}'
            + (
                f' (<a href="{e(ev["source_url"])}" target="_blank" rel="noopener">{e(ev.get("source_label") or ev["source_url"])}</a>)'
                if ev.get("source_url")
                else ""
            )
            + "</li>"
            for ev in s.get("evidence", [])
        )
        body = (
            f'<p class="prose"><strong>Problem.</strong> {e(s["problem"])}</p>'
            f'<p class="prose"><strong>Proposed change.</strong> {e(s["proposed_change"])}</p>'
            + f'<p class="prose"><strong>Expected impact.</strong> {e(s["expected_impact"])}</p>'
            + (f'<p class="prose"><strong>Dependencies.</strong> {deps}</p>' if deps else "")
            + "<h5 style='font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-faint);margin-top:14px'>Decision paths</h5>"
            + "".join(paths_html)
            + '<div class="callout ok" style="margin-top:12px"><h4>Recommendation</h4>'
            + f"<p>{e(s['recommendation_rationale'])}</p></div>"
            + (f"<h5 style='font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-faint);margin-top:14px'>Evidence</h5>"
               f"<ul class=\"tight\">{evidence}</ul>" if evidence else "")
        )
        b.append(
            f'<div id="{e(s["id"])}">'
            + details(
                f'<span class="id-chip">{e(s["id"])}</span> {e(s["title"])} '
                + badge(s["priority"], {"P0": "bad", "P1": "warn", "P2": "muted"}.get(s["priority"], "muted"))
                + " "
                + badge(s["category"], "muted")
                + " "
                + badge(s["status"], "info" if s["status"] == "proposed" else "ok"),
                body,
            )
            + "</div>"
        )
    return page(
        "Suggestions &amp; Decision Paths",
        "Decision Support",
        data["meta"]["subtitle"],
        "".join(b),
        "suggestions.html",
    )


def build_strategies() -> str:
    data = load("strategies.json")
    b = []
    b.append(f'<p class="prose">{e(data["meta"]["subtitle"])}</p>')
    b.append(
        '<div class="callout"><h4>Principle</h4><p>' + e(data["meta"]["principle"]) + "</p></div>"
    )

    b.append("<h2>Validation gates</h2><p class=\"prose\">A strategy must clear every gate to be eligible for scoring and reward. "
             "Thresholds are proposals pending the owner's decision on questions Q-008, Q-009 and Q-011; each is labelled accordingly.</p>")
    rows = []
    for g in data["gates"]:
        rows.append(
            [
                f'<span class="id-chip">{e(g["id"])}</span>',
                f'<strong>{e(g["name"])}</strong>',
                e(g["rule"]),
                e(g["threshold"]),
                badge(g["status"].split(" - ")[0], "warn" if g["status"].startswith("proposed") else "ok"),
                e(g["rationale"]),
            ]
        )
    b.append(
        table(
            [
                ("Gate", False, False),
                ("Name", False, False),
                ("Rule", False, False),
                ("Threshold", False, False),
                ("Status", False, False),
                ("Why it exists", False, False),
            ],
            rows,
        )
    )

    b.append("<h2>Strategy register</h2>")
    rows = []
    for s in data["strategies"]:
        src = "".join(
            f'<li>{e(i["name"])} — <a href="{e(i["source_url"])}" target="_blank" rel="noopener">{e(i["source_label"])}</a></li>'
            for i in s.get("inputs", [])
            if i.get("source_url")
        ) or '<li>No official input is available for this strategy yet; it is registered but cannot be evaluated.</li>'
        body = (
            f'<p class="prose"><strong>Hypothesis.</strong> {e(s["hypothesis"])}</p>'
            f'<p class="prose"><strong>Signal.</strong> {e(s["signal_definition"])}</p>'
            + kv([("Market", e(s["market"])), ("Class", e(s["class"])), ("State", e(s["state"]))])
            + "<h5 style='font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--text-faint);margin-top:12px'>Official inputs</h5>"
            + f'<ul class="tight">{src}</ul>'
            + (f'<p class="prose"><strong>Note.</strong> {e(s["notes"])}</p>' if s.get("notes") else "")
        )
        rows.append(
            [
                f'<span class="id-chip">{e(s["id"])}</span>',
                badge(s["class"], {"single": "info", "parlay": "purple", "prop": "warn", "prop_combo": "bad"}.get(s["class"], "muted")),
                f'<strong>{e(s["name"])}</strong>',
                e(s["market"]),
                e(s["hypothesis"]),
                badge(s["status"], "muted"),
            ]
        )
        b.append(details(f'<span class="id-chip">{e(s["id"])}</span> {e(s["name"])}', body))

    b.append("<h2>Strategy register summary</h2>")
    b.append(
        table(
            [
                ("ID", False, False),
                ("Class", False, False),
                ("Name", False, False),
                ("Market", False, False),
                ("Hypothesis", False, False),
                ("Status", False, False),
            ],
            rows,
        )
    )

    b.append("<h2>Explicitly out of scope</h2><div class=\"card\"><ul class=\"tight\">")
    for r in data["removed_from_scope"]:
        b.append(f"<li><strong>{e(r['item'])}</strong><br><span style='color:var(--text-faint)'>{e(r['reason'])}</span></li>")
    b.append("</ul></div>")
    return page(
        "Strategies &amp; Validation Gates",
        "Strategy",
        data["meta"]["subtitle"],
        "".join(b),
        "strategies.html",
    )


def build_leaderboard() -> str:
    spec = load("leaderboard.json")
    rows = load("leaderboard_rows.json", DATA) or {"rows": []}
    b = []
    b.append(f'<p class="prose">{e(spec["meta"]["subtitle"])}</p>')
    b.append('<div class="callout warn"><h4>Read this before the standings</h4><p>' + e(spec["meta"]["important_note"]) + "</p></div>")

    b.append("<h2>Scoring</h2>")
    comp_rows = [
        [f'<strong>{e(c["name"])}</strong>', e(c["definition"]), f'{c["weight"]:.0%}', e(c["reason"])]
        for c in spec["scoring"]["components"]
    ]
    b.append(
        table(
            [("Component", False, False), ("Definition", False, False), ("Weight", True, True), ("Why", False, False)],
            comp_rows,
        )
    )
    b.append(
        "<div class=\"card\">"
        + kv(
            [
                ("Normalisation", e(spec["scoring"]["normalisation"])),
                ("Tie-breaks", e(" · ".join(spec["scoring"]["tie_breaks"]))),
                ("Profit excluded", e(spec["scoring"]["profit_is_not_a_component"])),
            ]
        )
        + "</div>"
    )

    b.append("<h2>Rewards</h2>")
    tier_rows = [[t["tier"], t["share_of_pool"], e(t["eligibility"])] for t in spec["rewards"]["tiers"]]
    b.append(
        table([("Tier", False, False), ("Share of pool", False, False), ("Eligibility", False, False)], tier_rows)
    )
    b.append(
        '<div class="card">'
        + kv(
            [
                ("Per-class awards", e(spec["rewards"]["per_class_awards"])),
                ("Pool size", e(spec["rewards"]["pool_size"])),
                ("Transparency rule", e(spec["rewards"]["transparency_rule"])),
            ]
        )
        + "</div>"
    )

    b.append("<h2>Eligibility and fair play</h2>")
    b.append(
        '<div class="card">'
        + kv(
            [
                ("Eligibility rule", e(spec["eligibility"]["rule"])),
                ("Gate table", e(spec["eligibility"]["gate_table"])),
                ("Ineligible display", e(spec["eligibility"]["ineligible_display"])),
                ("Hypothesis register", e(spec["fair_play"]["hypothesis_register"])),
                ("Multiple testing", e(spec["fair_play"]["multiple_testing"])),
                ("No reuse", e(spec["fair_play"]["no_reuse"])),
                ("Price independence", e(spec["fair_play"]["price_independence"])),
            ]
        )
        + "</div>"
    )

    b.append("<h2>Current standings</h2>")
    benchmark = rows.get("benchmark")
    bench_rows = []
    if benchmark:
        m = benchmark["metrics"]
        bench_rows.append(
            [
                "Benchmark",
                e(benchmark["name"]),
                str(m.get("bets", 0)),
                e(m.get("net_units")),
                e(m.get("roi")),
                e(m.get("sharpe")),
                e(m.get("max_drawdown_units")),
                e(m.get("skill_share")),
                badge("reference only", "muted"),
            ]
        )
    strat_rows = []
    for r in rows.get("rows", []):
        m = r.get("metrics", {})
        f = r.get("folds", {})
        strat_rows.append(
            [
                f'<span class="id-chip">{e(r["strategy_id"])}</span>',
                e(strategies_name(r["strategy_id"])),
                str(m.get("bets", 0)),
                e(m.get("net_units")),
                e(m.get("roi")),
                e(m.get("sharpe")),
                e(m.get("max_drawdown_units")),
                e(m.get("skill_share")),
                e(f.get("positive_fold_share")),
                badge("evaluated" if m.get("bets") else "not evaluated", "ok" if m.get("bets") else "muted"),
            ]
        )
    b.append(
        table(
            [
                ("ID", False, False),
                ("Strategy", False, False),
                ("Bets", True, True),
                ("Net units", True, True),
                ("ROI", True, True),
                ("Sharpe", True, True),
                ("Max DD", True, True),
                ("Skill share", True, True),
                ("Positive folds", True, True),
                ("Status", False, False),
            ],
            bench_rows + strat_rows,
            caption="Rows are produced by the walk-forward harness in scripts/compute_signals.py using official final scores only. "
            "A strategy with no evaluated bets is shown so the omission is visible rather than hidden.",
        )
    )

    b.append("<h2>Competition state</h2>")
    b.append(
        '<div class="card">'
        + kv(
            [
                ("Cycle", e(spec["meta"]["cycle"])),
                ("Evaluated strategies", e(spec["current_state"]["evaluated_strategies"])),
                ("Next milestone", e(spec["current_state"]["next_milestone"])),
            ]
        )
        + "</div>"
    )
    blockers = "".join(f'<span class="id-chip" style="margin-right:5px">{e(x)}</span>' for x in spec["current_state"]["blockers"])
    b.append(f'<p class="prose">Open items blocking a fully scored competition: {blockers}</p>')
    return page(
        "Leaderboard Competition",
        "Strategy",
        spec["meta"]["subtitle"],
        "".join(b),
        "leaderboard.html",
    )


def strategies_name(sid: str) -> str:
    data = load("strategies.json")
    for s in data["strategies"]:
        if s["id"] == sid:
            return s["name"]
    return sid


def build_injuries() -> str:
    inj = load("injuries.json", DATA)
    b = []
    if not inj:
        b.append(
            '<div class="callout bad"><h4>Dataset unavailable</h4><p>The official injury report could not be retrieved in this build, so no '
            "rows are published. Nothing has been substituted. See the Flagged for Review page.</p></div>"
        )
        return page("Official Injury Report", "Data", "Official NFL injury report.", "".join(b), "injuries.html")

    rows = inj["rows"]
    out_rows = [r for r in rows if r.get("game_status") == "Out"]
    q_rows = [r for r in rows if r.get("game_status") == "Questionable"]
    d_rows = [r for r in rows if r.get("game_status") == "Doubtful"]

    b.append(
        f'<p class="prose">Week {e(inj.get("week"))} official injury report as published by the NFL, covering '
        f'<strong>{len(rows)}</strong> player entries across <strong>{len(inj.get("games", []))}</strong> games. '
        "Every row links to the official page it was read from. A player who does not appear in the report is recorded as "
        "<em>not reported</em>, which is not the same as healthy.</p>"
    )
    b.append('<div class="grid cols-4">')
    b.append(f'<div class="card kpi"><div class="value">{len(rows)}</div><div class="label">Players reported</div></div>')
    b.append(f'<div class="card kpi bad"><div class="value">{len(out_rows)}</div><div class="label">Out</div></div>')
    b.append(f'<div class="card kpi warn"><div class="value">{len(q_rows)}</div><div class="label">Questionable</div></div>')
    b.append(f'<div class="card kpi"><div class="value">{len(d_rows)}</div><div class="label">Doubtful</div></div>')
    b.append("</div>")

    b.append("<h2>Games this week</h2>")
    grows = []
    for g in inj.get("games", []):
        grows.append(
            [
                e(g.get("game_date")),
                e(g.get("game_time")) + " " + e(g.get("game_timezone")),
                e(g.get("network")),
                f'{e(g.get("away_team"))} ({e(g.get("away_record"))}) @ {e(g.get("home_team"))} ({e(g.get("home_record"))})',
                cell("", g.get("source_url", "")) if False else '<a class="src-link" href="' + e(g.get("source_url", "")) + '" target="_blank" rel="noopener">source</a>',
            ]
        )
    b.append(
        table(
            [("Date", False, False), ("Time", False, False), ("Network", False, False), ("Matchup", False, False), ("Official source", False, False)],
            grows,
            source_url=INJURY_URL,
        )
    )

    b.append("<h2>Full official injury report</h2>")
    trows = []
    for r in rows:
        status = r.get("game_status") or ""
        kind = {"Out": "bad", "Questionable": "warn", "Doubtful": "warn"}.get(status, "muted")
        trows.append(
            [
                e(r.get("game_date")),
                f'{e(r.get("away_team"))} @ {e(r.get("home_team"))}',
                e(r.get("team")),
                f'<a href="{e(r["player_url"])}" target="_blank" rel="noopener">{e(r.get("player"))}</a>' if r.get("player_url") else e(r.get("player")),
                e(r.get("position")),
                cell(r.get("injuries"), r.get("source_url", "")),
                badge(r.get("practice_status") or "not reported", "muted")
                if r.get("practice_status")
                else unverified("not reported"),
                badge(status, kind) if status else unverified("no designation"),
                '<a class="src-link" href="' + e(r.get("source_url", "")) + '" target="_blank" rel="noopener">source</a>',
            ]
        )
    b.append(
        table(
            [
                ("Date", False, False),
                ("Game", False, False),
                ("Team", False, False),
                ("Player", False, False),
                ("Pos", False, False),
                ("Injury", False, False),
                ("Practice status", False, False),
                ("Game status", False, False),
                ("Official source", False, False),
            ],
            trows,
            caption="Practice status and game status are the designations published by the official NFL injury report. "
            "An empty designation means the report did not list one.",
        )
    )
    return page(
        "Official Injury Report",
        "Data",
        "Every player listed on the current official NFL injury report, with practice status, game status and a source link.",
        "".join(b),
        "injuries.html",
    )


def build_depth() -> str:
    inj = load("injuries.json", DATA) or {"rows": []}
    depth = load("depth_charts.json", DATA) or {"clubs": []}
    resolution = load("depth_resolution.json", DATA) or {"resolved": [], "unresolved": []}
    b = []

    absent = [r for r in inj.get("rows", []) if r.get("game_status") in ("Out", "Doubtful", "Questionable")]
    club_teams = sorted({r.get("team", "") for r in absent if r.get("team")})
    clubs_with_chart = {c["club"] for c in depth.get("clubs", [])}
    resolved = resolution.get("resolved", [])
    unresolved = resolution.get("unresolved", [])

    b.append(
        '<p class="prose">The official injury report says <em>who</em> is unavailable. It does not say <em>who replaces them</em>. '
        "Depth ordering is published by the clubs themselves, so this page resolves a replacement's depth string only from an official "
        "club depth chart. Where no official chart resolves, the cell is left blank and flagged rather than guessed.</p>"
    )

    b.append('<div class="grid cols-4">')
    b.append(f'<div class="card kpi bad"><div class="value">{len(absent)}</div><div class="label">Unavailable or limited players</div></div>')
    b.append(f'<div class="card kpi accent"><div class="value">{len(clubs_with_chart)}</div><div class="label">Clubs with an official depth chart</div></div>')
    b.append(f'<div class="card kpi ok"><div class="value">{len(resolved)}</div><div class="label">Depth strings resolved from an official chart</div></div>')
    b.append(f'<div class="card kpi warn"><div class="value">{len(unresolved)}</div><div class="label">Unresolved — left blank and flagged</div></div>')
    b.append("</div>")

    b.append(
        '<div class="callout"><h4>Resolution order</h4><p>1. The club&rsquo;s official depth chart. 2. The official game book, which lists the '
        "starters and the order in which substitutes entered. 3. Blank, with the item flagged for review. Depth strings are never inferred "
        "from reputation, statistics or a prior season.</p></div>"
    )

    # Depth strings that were resolved
    b.append("<h2>Resolved depth strings</h2>")
    if resolved:
        rrows = []
        for r in resolved:
            rrows.append(
                [
                    e(r.get("game_date")),
                    e(r.get("team")),
                    f'<a href="{e(r["player_url"])}" target="_blank" rel="noopener">{e(r.get("player"))}</a>' if r.get("player_url") else e(r.get("player")),
                    e(r.get("position")),
                    e(r.get("unit")),
                    badge(r.get("game_status") or "", {"Out": "bad", "Questionable": "warn", "Doubtful": "warn"}.get(r.get("game_status", ""), "muted")),
                    badge(r.get("depth_string", ""), "purple"),
                    f'<a class="src-link" href="{e(r.get("depth_source_url", ""))}" target="_blank" rel="noopener">depth chart</a>'
                    if r.get("depth_source_url")
                    else unverified("no chart"),
                    f'<a class="src-link" href="{e(r.get("source_url", ""))}" target="_blank" rel="noopener">injury report</a>',
                ]
            )
        b.append(
            table(
                [
                    ("Date", False, False),
                    ("Club", False, False),
                    ("Unavailable player", False, False),
                    ("Pos", False, False),
                    ("Unit", False, False),
                    ("Game status", False, False),
                    ("Depth string", False, False),
                    ("Depth source", False, False),
                    ("Absence source", False, False),
                ],
                rrows,
                caption="The depth string is the player's position and his position in the club's own published depth ordering, for example WR3. "
                "It is read from the club's official depth chart and is never inferred.",
            )
        )
    else:
        b.append(
            '<div class="callout warn"><h4>No depth strings were resolved in this build</h4><p>Every absence below is left blank and flagged. '
            "The reason is listed on the Flagged for Review page.</p></div>"
        )

    # Unresolved absences, explicitly blank
    b.append("<h2>Unresolved absences</h2>")
    if unresolved:
        urows = []
        for r in unresolved:
            urows.append(
                [
                    e(r.get("game_date")),
                    e(r.get("team")),
                    f'<a href="{e(r["player_url"])}" target="_blank" rel="noopener">{e(r.get("player"))}</a>' if r.get("player_url") else e(r.get("player")),
                    e(r.get("position")),
                    e(r.get("unit")),
                    badge(r.get("game_status") or "", {"Out": "bad", "Questionable": "warn", "Doubtful": "warn"}.get(r.get("game_status", ""), "muted")),
                    unverified("depth string unresolved"),
                    f'<a class="src-link" href="{e(r.get("source_url", ""))}" target="_blank" rel="noopener">source</a>',
                ]
            )
        b.append(
            table(
                [
                    ("Date", False, False),
                    ("Club", False, False),
                    ("Unavailable player", False, False),
                    ("Pos", False, False),
                    ("Unit", False, False),
                    ("Game status", False, False),
                    ("Depth string", False, False),
                    ("Official source", False, False),
                ],
                urows,
                caption="These absences are real and sourced, but no official depth chart resolves the replacement's depth string, "
                "so the cell is left blank and flagged. It is not estimated.",
            )
        )

    # Depth-chart coverage
    b.append("<h2>Official depth-chart coverage</h2>")
    coverage = depth.get("coverage", {})
    if coverage:
        b.append(
            '<div class="grid cols-3">'
            f'<div class="card kpi ok"><div class="value">{coverage.get("clubs_resolved", 0)}</div>'
            f'<div class="label">Clubs with an official depth chart</div></div>'
            f'<div class="card kpi warn"><div class="value">{coverage.get("clubs_unresolved", 0)}</div>'
            f'<div class="label">Clubs with no chart resolved</div></div>'
            f'<div class="card kpi"><div class="value">{coverage.get("clubs_total", 32)}</div>'
            f'<div class="label">Clubs in the league</div></div>'
            "</div>"
        )
    cov_rows = []
    for club in depth.get("clubs", []):
        urls = ", ".join(
            f'<a href="{e(s["url"])}" target="_blank" rel="noopener">chart</a>' for s in club.get("sources", [])
        )
        groups = club.get("groups", [])
        positions = ", ".join(sorted({g["position"] for g in groups})) or unverified("no positions parsed")
        cov_rows.append([e(club["club"]), badge("official depth chart", "ok"), positions, urls])
    rejected = depth.get("rejected_candidates", [])
    for r in rejected:
        cov_rows.append(
            [e(r.get("club", "")), badge("not resolved", "warn"), unverified("no chart"), e(r.get("reason", ""))]
        )
    if cov_rows:
        b.append(
            table(
                [("Club", False, False), ("Official depth source", False, False), ("Positions published", False, False), ("Link", False, False)],
                cov_rows,
                caption="A club whose chart could not be retrieved is listed so the coverage gap is visible rather than silent.",
            )
        )
    else:
        b.append('<div class="callout warn"><p>No official club depth chart was retrieved in this build.</p></div>')

    return page(
        "Lineup Depth &amp; Deficiencies",
        "Data",
        "Which unit is short a starter, who the replacement is, and how deep the replacement is - resolved only from official sources.",
        "".join(b),
        "depth.html",
    )


def build_lines() -> str:
    lines = load("our_lines.json", DATA)
    b = []
    if not lines:
        b.append('<div class="callout bad"><h4>No lines published</h4><p>Lines are generated only when official team ratings are available. '
                 "That condition was not met in this build, so no line is shown. Nothing is estimated.</p></div>")
        return page("Our Originated Lines", "Data", "The platform's own lines.", "".join(b), "lines.html")

    b.append(
        '<div class="callout"><h4>These lines are originated here</h4><p>They are produced by the platform&rsquo;s own model from official '
        "NFL data. No commercial book&rsquo;s line, projection or injury feed is ingested anywhere in the pipeline, so a strategy can be "
        "scored on whether it disagrees with this model profitably. The method is published in full below and the model version is carried "
        "on every line.</p></div>"
    )

    b.append(
        '<div class="card">'
        + kv(
            [
                ("Model version", e(lines.get("model_version", ""))),
                ("League points per team per game", e(lines.get("league_points_per_game"))),
                ("Margin held", f"{float(lines.get('margin_pct', 0)):.1%}"),
                ("Shrinkage constant", e(lines.get("shrinkage_k"))),
                ("Margin standard deviation", e((lines.get("scales") or {}).get("margin_sd"))),
                ("Average home margin", e((lines.get("scales") or {}).get("home_avg_margin"))),
                ("Completed games used", e((lines.get("scales") or {}).get("n_games"))),
            ]
        )
        + "</div>"
    )

    rows = []
    for ln in lines.get("lines", []):
        rows.append(
            [
                e(ln.get("game_date")),
                e(ln.get("game_time")),
                f'{e(ln.get("away_team"))} @ {e(ln.get("home_team"))}',
                e(ln.get("expected_away_points")),
                e(ln.get("expected_home_points")),
                e(ln.get("published_spread")),
                e(ln.get("published_total")),
                e(ln.get("fair_home_win_probability")),
                e(ln.get("published_home_price")),
                e(ln.get("published_away_price")),
                '<a class="src-link" href="' + e(ln.get("schedule_source_url", "")) + '" target="_blank" rel="noopener">schedule</a>'
                + ' <a class="src-link" href="' + e(ln.get("source_url", "")) + '" target="_blank" rel="noopener">standings</a>',
            ]
        )
    b.append(
        "<h2>Current lines</h2>"
        + table(
            [
                ("Date", False, False),
                ("Time", False, False),
                ("Matchup", False, False),
                ("Exp away", True, True),
                ("Exp home", True, True),
                ("Spread (home)", True, True),
                ("Total", True, True),
                ("Fair P(home)", True, True),
                ("Price home", True, True),
                ("Price away", True, True),
                ("Official source", False, False),
            ],
            rows,
            caption="Spread is quoted for the home team. Prices are the platform's own quoted probabilities, which already carry the stated margin.",
        )
    )
    b.append(
        '<div class="callout warn" style="margin-top:18px"><h4>Known limitation</h4><p>The line model uses team scoring efficiency and the '
        "home-field effect. It does not yet adjust for availability, because the depth string of a replacement cannot be resolved for every "
        "club from official sources. That limitation is recorded as the state of strategy ST-002 and as a flagged item.</p></div>"
    )
    return page(
        "Our Originated Lines",
        "Data",
        "Point spreads, totals and quoted prices produced by the platform's own model from official NFL data.",
        "".join(b),
        "lines.html",
    )


def build_data_page() -> str:
    b = []
    standings = load(f"standings_{2026}.json", DATA)
    corr = load("correlations.json", DATA)
    manifest = load("manifest.json", DATA)
    stats = None
    for name in sorted(os.listdir(DATA)) if os.path.isdir(DATA) else []:
        if name.startswith("player_stats_passing_2026"):
            stats = load(name, DATA)
            break

    if standings:
        rows = []
        for r in standings["rows"]:
            rows.append(
                [
                    e(r.get("team")),
                    e(r.get("wins")),
                    e(r.get("losses")),
                    e(r.get("ties")),
                    e(r.get("win_pct")),
                    e(r.get("points_for")),
                    e(r.get("points_against")),
                    e(r.get("net_points")),
                    e(r.get("home")),
                    e(r.get("road")),
                    e(r.get("streak")),
                    e(r.get("last_5")),
                    '<a class="src-link" href="' + e(r.get("source_url", "")) + '" target="_blank" rel="noopener">source</a>',
                ]
            )
        b.append(
            "<h2>2026 league standings (official)</h2>"
            + table(
                [
                    ("Team", False, False),
                    ("W", True, True),
                    ("L", True, True),
                    ("T", True, True),
                    ("PCT", True, True),
                    ("PF", True, True),
                    ("PA", True, True),
                    ("Net", True, True),
                    ("Home", False, False),
                    ("Road", False, False),
                    ("Streak", False, False),
                    ("Last 5", False, False),
                    ("Official source", False, False),
                ],
                rows,
                source_url=STANDINGS_URL,
            )
        )

    if corr:
        for m in corr.get("matrices", []):
            labels = m["labels"]
            head = [""] + [f'<span class="nowrap">{e(l)}</span>' for l in labels]
            mrows = []
            for i, lab in enumerate(labels):
                cells = [f'<span class="nowrap">{e(lab)}</span>']
                for j, val in enumerate(m["matrix"][i]):
                    if val is None:
                        cells.append(unverified())
                    elif i == j:
                        cells.append('<span class="self">1.000</span>')
                    else:
                        cells.append(f"{val:.3f}")
                mrows.append(cells)
            b.append(
                f'<h2>{e(m["title"])}</h2>'
                + table(
                    [(h, False, True) for h in head],
                    mrows,
                    caption=f'{e(m["method"])} Unit of observation: {e(m["unit"])}. n = {e(m["n"])}. '
                    f'Source: <a href="{e(m["source_url"])}" target="_blank" rel="noopener">{e(m["source_url"])}</a>.',
                )
            )
        if corr.get("unavailable"):
            b.append("<h2>Correlations not published</h2>")
            for u in corr["unavailable"]:
                b.append(
                    f'<div class="callout warn"><h4>{e(u["item"])}</h4><p>{e(u["reason"])}</p>'
                    + (f'<p>Related: {e(u.get("related_question", ""))} · {e(u.get("related_suggestion", ""))}. '
                       f'Reference source: <a href="{e(u["source_url"])}" target="_blank" rel="noopener">{e(u["source_url"])}</a>.</p>'
                       if u.get("source_url") else "")
                    + "</div>"
                )

    if stats and stats.get("rows"):
        cols = stats.get("columns", [])
        keep = [c for c in cols if c in ("Pass Yds", "Yds/Att", "Att", "Cmp", "Cmp %", "TD", "INT", "Rate")][:8]
        srows = []
        for r in stats["rows"][:40]:
            cells = [f'<a href="{e(r["player_url"])}" target="_blank" rel="noopener">{e(r.get("player"))}</a>' if r.get("player_url") else e(r.get("player"))]
            for c in keep:
                cells.append(e(r.get(c)))
            cells.append('<a class="src-link" href="' + e(r.get("source_url", "")) + '" target="_blank" rel="noopener">source</a>')
            srows.append(cells)
        b.append(
            "<h2>2026 passing statistics (official, top 40)</h2>"
            + table(
                [("Player", False, False)] + [(e(c), True, True) for c in keep] + [("Official source", False, False)],
                srows,
                source_url=STATS_URL,
            )
        )

    if manifest:
        b.append("<h2>Dataset manifest</h2>")
        mrows = []
        for d in manifest.get("datasets", []):
            mrows.append(
                [
                    e(d.get("dataset")),
                    str(d.get("rows", "")),
                    e(d.get("source_key")),
                    f'<a href="{e(d.get("source_url"))}" target="_blank" rel="noopener">{e(d.get("source_url"))}</a>'
                    if str(d.get("source_url", "")).startswith("http")
                    else e(d.get("source_url")),
                    e(d.get("fetched_at") if isinstance(d.get("fetched_at"), str) else ", ".join(d.get("fetched_at", [])[:2])),
                ]
            )
        b.append(
            table(
                [
                    ("Dataset", False, False),
                    ("Rows", True, True),
                    ("Source key", False, False),
                    ("Official source", False, False),
                    ("Fetched (UTC)", False, False),
                ],
                mrows,
            )
        )
    return page(
        "Datasets &amp; Correlations",
        "Data",
        "The official datasets behind the platform, the correlation matrices computed from them, and the provenance for each.",
        "".join(b),
        "data.html",
    )


def build_findings() -> str:
    derived = load("derived.json", DATA) or {}
    inj = load("injuries.json", DATA) or {"rows": []}
    standings = load("standings_2026.json", DATA) or {"rows": []}
    b = []

    b.append(
        '<div class="callout"><h4>What "a finding" means here</h4><p>A finding is a statement computed from an official dataset, published '
        "with its source. An observation that the platform could not compute because a dataset is missing is listed on the "
        "<a href=\"flagged.html\">Flagged for Review</a> page instead of being stated loosely.</p></div>"
    )

    b.append("<h2>Availability</h2>")
    rows = inj.get("rows", [])
    by_team: dict = {}
    for r in rows:
        t = r.get("team", "")
        by_team.setdefault(t, {"out": 0, "q": 0, "d": 0, "total": 0})
        by_team[t]["total"] += 1
        if r.get("game_status") == "Out":
            by_team[t]["out"] += 1
        elif r.get("game_status") == "Questionable":
            by_team[t]["q"] += 1
        elif r.get("game_status") == "Doubtful":
            by_team[t]["d"] += 1
    frows = []
    for team, v in sorted(by_team.items(), key=lambda kv: -kv[1]["out"]):
        frows.append(
            [
                e(team),
                str(v["total"]),
                str(v["out"]),
                str(v["q"]),
                str(v["d"]),
                f"{v['out'] / v['total']:.0%}" if v["total"] else "",
                '<a class="src-link" href="' + e(INJURY_URL) + '" target="_blank" rel="noopener">source</a>',
            ]
        )
    if frows:
        b.append(
            "<h3>Offensive and defensive availability pressure by club</h3>"
            + table(
                [
                    ("Club", False, False),
                    ("Reported", True, True),
                    ("Out", True, True),
                    ("Questionable", True, True),
                    ("Doubtful", True, True),
                    ("Out share", True, True),
                    ("Official source", False, False),
                ],
                frows,
                caption="A high out-share is a flag for investigation, not a conclusion: it counts reported players across the whole roster, "
                "not starters. The depth page resolves which absences matter.",
            )
        )
    else:
        b.append('<div class="callout warn"><p>No injury rows were present in this build, so no availability finding is published.</p></div>')

    b.append("<h2>League baseline</h2>")
    b.append(
        '<div class="grid cols-3">'
        + (
            f'<div class="card kpi accent"><div class="value">{derived["league_points_per_game"]:.2f}</div>'
            f'<div class="label">Points per team per game</div><div class="note">Official 2026 league standings</div></div>'
            if derived.get("league_points_per_game") is not None
            else '<div class="card"><h3>Not computed</h3><p>The standings dataset was not available in this build, so no league baseline is stated.</p></div>'
        )
        + (
            f'<div class="card kpi"><div class="value">{(derived.get("scales") or {}).get("margin_sd") or "—"}</div>'
            f'<div class="label">Standard deviation of the scoring margin</div>'
            f'<div class="note">Official final scores, {e((derived.get("scales") or {}).get("n_games"))} games</div></div>'
            if (derived.get("scales") or {}).get("margin_sd")
            else '<div class="card"><h3>Not computed</h3><p>Official final scores were not available, so the margin scale is not stated.</p></div>'
        )
        + (
            f'<div class="card kpi"><div class="value">{(derived.get("scales") or {}).get("home_avg_margin") or "—"}</div>'
            f'<div class="label">Average home margin</div>'
            f'<div class="note">Official final scores</div></div>'
            if (derived.get("scales") or {}).get("home_avg_margin") is not None
            else '<div class="card"><h3>Not computed</h3><p>Official final scores were not available.</p></div>'
        )
        + "</div>"
    )

    if standings.get("rows"):
        rows_s = sorted(standings["rows"], key=lambda r: -(float(r.get("net_points") or 0)))
        top = rows_s[:5]
        bottom = rows_s[-5:]
        trows = []
        for r in top + bottom:
            trows.append(
                [
                    e(r.get("team")),
                    e(r.get("wins")),
                    e(r.get("losses")),
                    e(r.get("net_points")),
                    e(r.get("points_for")),
                    e(r.get("points_against")),
                    e(r.get("streak")),
                    '<a class="src-link" href="' + e(r.get("source_url", "")) + '" target="_blank" rel="noopener">source</a>',
                ]
            )
        b.append(
            "<h3>Best and worst net point differentials</h3>"
            + table(
                [
                    ("Club", False, False),
                    ("W", True, True),
                    ("L", True, True),
                    ("Net points", True, True),
                    ("PF", True, True),
                    ("PA", True, True),
                    ("Streak", False, False),
                    ("Official source", False, False),
                ],
                trows,
                source_url=STANDINGS_URL,
            )
        )

    b.append("<h2>Methodological findings</h2>")
    b.append(
        '<div class="card"><ul class="tight">'
        "<li><strong>The official injury report is a participation record, not a clearance.</strong> A club lists only the players it "
        "wants to report, so a player absent from the report cannot be assumed healthy. The platform records such players as "
        "<em>not reported</em> and never converts that into an availability claim.</li>"
        "<li><strong>Depth ordering is club-published and club-maintained.</strong> It is the only official route to a replacement's "
        "depth string, and its coverage is partial. The platform measures and publishes that coverage rather than filling the gaps.</li>"
        "<li><strong>Scoring a strategy against the model that priced the game measures agreement, not skill.</strong> This is the "
        "central methodological trap of an own-line platform, and it is why suggestion S-002 exists and why every strategy in the register "
        "uses a signal deliberately different from the line model's inputs.</li>"
        "<li><strong>A positive record is not evidence of skill at small sample.</strong> The platform therefore reports a skill share with "
        "a bootstrap interval and a permutation test against a pure-luck null, rather than a win rate alone.</li>"
        "<li><strong>Correlated parlay legs manufacture apparent edge.</strong> Multiplying correlated probabilities overstates the "
        "probability of the combination. The platform computes the correlation matrix and prices a parlay from the joint, not the product "
        "of the marginals.</li>"
        "<li><strong>Nothing is published that cannot be traced.</strong> Every table row links to the official page it came from, and the "
        "payload hash and fetch time are recorded for each source.</li>"
        "</ul></div>"
    )
    return page(
        "Findings &amp; Analysis",
        "Overview",
        "What the official data currently supports, and what it does not.",
        "".join(b),
        "findings.html",
    )


def build_flagged() -> str:
    flagged = STATE.get("flagged", [])
    b = []
    b.append(
        '<p class="prose">Every value that could not be confirmed from an official source, and every irregularity found, is listed here '
        "with the source that was checked and what would resolve it. These items are published for review; they do not block the platform, "
        "and nothing is filled in by guesswork in the meantime.</p>"
    )
    rows = []
    for f in flagged:
        src = (
            f'<a href="{e(f["source_url"])}" target="_blank" rel="noopener">{e(f["source_url"])}</a>'
            if f.get("source_url")
            else unverified("no source available")
        )
        rows.append(
            [
                f'<span class="id-chip">{e(f["id"])}</span>',
                e(f.get("category", "")),
                f'<strong>{e(f.get("item", ""))}</strong><br><span style="color:var(--text-dim)">{e(f.get("reason", ""))}</span>',
                badge(f.get("severity", "medium"), {"high": "bad", "medium": "warn", "low": "muted"}.get(f.get("severity", "medium"), "muted")),
                src,
                e(f.get("resolution", "")),
            ]
        )
    b.append(
        table(
            [
                ("ID", False, False),
                ("Category", False, False),
                ("Item and reason", False, False),
                ("Severity", False, False),
                ("Source checked", False, False),
                ("What would resolve it", False, False),
            ],
            rows,
            caption=f"{len(flagged)} flagged items.",
        )
    )
    return page(
        "Flagged for Review",
        "Governance",
        "Unverified values, missing datasets, irregularities and open risks, published for review with the source that was checked.",
        "".join(b),
        "flagged.html",
    )


def build_sources() -> str:
    manifest = load("fetch_manifest.json", DATA)
    b = []
    b.append(
        '<div class="callout"><h4>Source policy</h4><p>Only official NFL sources (<code>nfl.com</code>, <code>operations.nfl.com</code>) and '
        "official NFL club sites are used. No commercial betting line, projection service, injury feed or third-party aggregator is ingested "
        "anywhere in the pipeline. Every payload is recorded with its SHA-256 and UTC fetch time so any published number can be traced to "
        "the exact bytes it came from.</p></div>"
    )

    b.append("<h2>Official sources used</h2>")
    rows = [
        ["Official NFL injury report", "NFL.com", INJURY_URL, "Every player, practice status and game status for the current week."],
        ["League and division standings", "NFL.com", STANDINGS_URL, "Team records, points for and against, home and road splits."],
        ["Weekly schedule and results", "NFL.com", SCHEDULE_URL, "Matchups, kickoff times, networks and final scores."],
        ["Player statistics by category", "NFL.com", STATS_URL, "Official season player statistics for passing, rushing, receiving and the rest."],
        ["Team and player profiles", "NFL.com", "https://www.nfl.com/teams/", "Roster context and player profile links."],
        ["Official rulebook and rule changes", "NFL Football Operations", "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook", "The governing rules referenced by the platform."],
        ["League policy statements", "NFL Communications", "https://www.nfl.com/news/nfl-communications", "Official league positions, including on wagering policy."],
        ["Official club depth charts", "Official NFL club sites", "https://www.nfl.com/teams/", "Depth ordering, used only where a club publishes it."],
    ]
    b.append(
        table(
            [("Dataset", False, False), ("Publisher", False, False), ("Official URL", False, False), ("Used for", False, False)],
            [[e(a), e(bb), f'<a href="{e(c)}" target="_blank" rel="noopener">{e(c)}</a>', e(dd)] for a, bb, c, dd in rows],
        )
    )

    if manifest:
        b.append("<h2>Fetch provenance</h2>")
        records = manifest.get("records", [])
        prows = []
        for r in sorted(records, key=lambda x: x.get("key", "")):
            prows.append(
                [
                    e(r.get("key")),
                    e(r.get("category")),
                    badge("ok" if r.get("ok") else "failed", "ok" if r.get("ok") else "bad"),
                    str(r.get("status") or ""),
                    f'{r.get("bytes", 0):,}',
                    e((r.get("sha256") or "")[:16]),
                    e(r.get("fetched_at")),
                ]
            )
        ok_count = sum(1 for r in records if r.get("ok"))
        b.append(
            table(
                [
                    ("Source key", False, False),
                    ("Category", False, False),
                    ("Result", False, False),
                    ("HTTP", True, True),
                    ("Bytes", True, True),
                    ("SHA-256 (first 16)", False, False),
                    ("Fetched (UTC)", False, False),
                ],
                prows,
                caption=f"{ok_count} of {len(records)} registered official sources returned a payload in the latest run. "
                "Failed sources are shown so the gaps are visible; nothing is substituted for them.",
            )
        )
    return page(
        "Sources &amp; Methodology",
        "Governance",
        "Every official source the platform reads, with its hash and fetch time, and the method behind every published number.",
        "".join(b),
        "sources.html",
    )


def build_methodology() -> str:
    path = os.path.join(ROOT, "docs", "methodology.md")
    if not os.path.exists(path):
        return page(
            "Methodology",
            "Governance",
            "How every published number is computed.",
            '<div class="callout bad"><p>The methodology document is not present in this build.</p></div>',
            "methodology.html",
        )
    with open(path, encoding="utf-8") as fh:
        body = render_markdown(fh.read())
    return page(
        "Methodology",
        "Governance",
        "Exactly how each published number is produced: provenance, the no-inference rule, injury semantics, depth resolution, the line model, validation, the skill-share metric and correlation.",
        body,
        "methodology.html",
    )


def build_validation() -> str:
    report = STATE.get("validation", {})
    b = []
    b.append(
        '<p class="prose">The validation report is produced by <code>scripts/validate_site.py</code>, which runs on every pipeline execution '
        "and fails the build if an internal link is broken, if a dataset row lacks a source link, or if an unverified value is rendered as "
        "something other than an explicit marker.</p>"
    )
    checks = report.get("checks", [])
    rows = [[e(c["name"]), badge(c["result"], "ok" if c["result"] == "pass" else "bad"), e(c["detail"])] for c in checks]
    b.append(
        table(
            [("Check", False, False), ("Result", False, False), ("Detail", False, False)],
            rows,
            caption=f"Run at {e(report.get('generated_at', ''))}.",
        )
    )
    return page(
        "Validation Report",
        "Governance",
        "The automated checks that run against the published site on every pipeline execution.",
        "".join(b),
        "validation.html",
    )


# ---------------------------------------------------------------------------
# flag register
# ---------------------------------------------------------------------------


def build_flag_register() -> list[dict]:
    """Derive the flag register from what is actually present in the build."""
    flags: list[dict] = []
    n = 0

    def add(category, item, reason, severity="medium", source_url="", resolution=""):
        nonlocal n
        n += 1
        flags.append(
            {
                "id": f"F-{n:03d}",
                "category": category,
                "item": item,
                "reason": reason,
                "severity": severity,
                "source_url": source_url,
                "resolution": resolution,
            }
        )

    derived = load("derived.json", DATA) or {}
    for u in derived.get("unavailable", []):
        add(
            "Missing dataset",
            u.get("item", ""),
            u.get("reason", ""),
            "high",
            u.get("source_url", ""),
            "Retrieve the referenced official source and rebuild the dataset.",
        )

    inj = load("injuries.json", DATA)
    if inj:
        rows = inj.get("rows", [])
        if not rows:
            add(
                "Missing dataset",
                "Official injury report contained no player rows",
                "The official page was retrieved but no player entries could be parsed, so no injury data is published.",
                "high",
                INJURY_URL,
                "Inspect the page structure and adjust the parser; the source is confirmed reachable.",
            )
        blanks = sum(1 for r in rows if not r.get("injuries"))
        if blanks:
            add(
                "Unverified values",
                f"{blanks} injury rows have no published injury designation",
                "The official report leaves the injury column empty for these players. The cell is left blank and flagged; it is not inferred.",
                "low",
                INJURY_URL,
                "Nothing to resolve. An empty designation in the official report is the authoritative state.",
            )
        no_game_status = sum(1 for r in rows if not r.get("game_status"))
        if no_game_status:
            add(
                "Unverified values",
                f"{no_game_status} injury rows have no game status",
                "The official report publishes no game-status designation for these players. Absence of a designation is not evidence of availability.",
                "low",
                INJURY_URL,
                "Nothing to resolve. Recorded so that absence is never read as a clearance.",
            )

    depth = load("depth_charts.json", DATA)
    if depth:
        clubs = depth.get("clubs", [])
        add(
            "Coverage",
            f"Official depth charts retrieved for {len(clubs)} club site(s)",
            "Depth ordering is published per club in club-specific formats. Where no official chart resolved, the replacement's depth string is left blank.",
            "medium",
            "https://www.nfl.com/teams/",
            "Extend the club URL candidate list, or adopt the game-book substitution order as the second step of the fallback chain.",
        )
    else:
        add(
            "Coverage",
            "No official club depth chart was retrieved in this build",
            "The pipeline probes official club domains for depth charts. None resolved, so no depth string is published for any absence.",
            "high",
            "https://www.nfl.com/teams/",
            "Inspect the failed official club URLs in the fetch provenance on the Sources page and extend the candidate patterns.",
        )

    corr = load("correlations.json", DATA)
    if corr:
        for u in corr.get("unavailable", []):
            add(
                "Missing statistic",
                u.get("item", ""),
                u.get("reason", ""),
                "high",
                u.get("source_url", ""),
                f'Ingest official per-game box scores (suggestion {u.get("related_suggestion", "")}, question {u.get("related_question", "")}).',
            )

    manifest = load("fetch_manifest.json", DATA)
    if manifest:
        failed = [r for r in manifest.get("records", []) if not r.get("ok")]
        if failed:
            add(
                "Fetch failures",
                f"{len(failed)} official source URL(s) did not return a payload",
                "Each failure is listed with its HTTP status and error in the fetch provenance on the Sources page. No substitute data was used.",
                "low",
                "https://www.nfl.com/",
                "Review the failed URLs; many are expected depth-chart URL candidates that do not exist on that club's site.",
            )

    add(
        "Repository review",
        "The repository contained only a one-line README and a single initial commit at the start of this work",
        "No prior requirements register, data pipeline, tests or site existed, so nothing could be migrated or cross-checked against earlier work.",
        "low",
        "",
        "Nothing to resolve. Recorded because it bounds what earlier verification is possible.",
    )
    add(
        "Environment",
        "The build environment cannot reach nfl.com directly",
        "Shell egress in the authoring sandbox is restricted to github.com, api.github.com, codeload.github.com, registry.npmjs.org, pypi.org and files.pythonhosted.org. Official sources are therefore retrieved inside GitHub Actions, and the committed datasets are the verified snapshot of that run.",
        "low",
        "https://github.com/karagemop466-tech/X3",
        "None. The pipeline design accounts for it: raw payloads are fetched in CI and the manifest records the hash of every payload.",
    )
    add(
        "Scope",
        "Three of the four strategy classes cannot yet be evaluated",
        "The parlay, player-prop and prop-combination classes need per-game official player logs and an evaluation reference, neither of which is available yet.",
        "high",
        "https://www.nfl.com/stats/player-stats/",
        "Answer question Q-005 and approve suggestion S-013 so official per-game box scores can be ingested.",
    )
    add(
        "Compliance",
        "The commercial nature of the platform is not yet settled",
        "The platform originates lines and publishes a leaderboard with a reward structure. Whether that constitutes a regulated activity depends on answers to Q-001, Q-002 and Q-003.",
        "high",
        "https://www.nfl.com/news/nfl-communications",
        "Answer Q-001, Q-002 and Q-003 and obtain a jurisdiction-specific legal review before any transactional feature is built (suggestion S-017).",
    )
    return flags


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point: always leaves a diagnostic report on failure."""
    try:
        return _impl()
    except Exception as exc:  # noqa: BLE001
        failure_report("build_site", exc)
        raise


def _impl() -> int:
    global FRESHNESS_HTML
    STATE["flagged"] = build_flag_register()
    STATE["flagged_count"] = len(STATE["flagged"])
    STATE["validation"] = load("validation_report.json", DATA) or {
        "generated_at": "",
        "checks": [
            {"name": "Validation report", "result": "pending", "detail": "The report is written by scripts/validate_site.py after this build."}
        ],
    }
    lb = load("leaderboard_rows.json", DATA) or {"rows": []}
    STATE["eligible_ids"] = [
        r["strategy_id"]
        for r in lb.get("rows", [])
        if (r.get("metrics") or {}).get("bets")
        and (r.get("metrics") or {}).get("skill_share") is not None
        and (r.get("metrics") or {}).get("skill_share", 0) >= 0.25
    ]

    manifest = load("fetch_manifest.json", DATA)
    if manifest:
        STATE["manifest"] = {
            "fetched_at": max(
                (r.get("fetched_at") or "" for r in manifest.get("records", []) if r.get("fetched_at")),
                default=None,
            )
        }
    FRESHNESS_HTML = freshness_html()

    pages = {
        "index.html": build_index(),
        "executive-summary.html": build_executive_summary(),
        "requirements.html": build_requirements(),
        "questions.html": build_questions(),
        "suggestions.html": build_suggestions(),
        "strategies.html": build_strategies(),
        "leaderboard.html": build_leaderboard(),
        "injuries.html": build_injuries(),
        "depth.html": build_depth(),
        "lines.html": build_lines(),
        "data.html": build_data_page(),
        "findings.html": build_findings(),
        "flagged.html": build_flagged(),
        "sources.html": build_sources(),
        "methodology.html": build_methodology(),
        "validation.html": build_validation(),
    }

    os.makedirs(OUT, exist_ok=True)
    for name, html_text in pages.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(html_text)

    assets_out = os.path.join(OUT, "assets")
    os.makedirs(assets_out, exist_ok=True)
    for asset in ("style.css", "app.js"):
        shutil.copyfile(os.path.join(ASSETS_SRC, asset), os.path.join(assets_out, asset))

    print(f"wrote {len(pages)} pages + assets to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
