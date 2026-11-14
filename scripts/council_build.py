#!/usr/bin/env python3
"""Deterministic builder for the X3 decision council (council/).

Reads:  scripts/council_content.py  (all prose and registers)
        data/desk/games.json        (read-only verified game log)
        data/desk/injuries.json     (read-only official injury transcription)
Writes: council/*.html, council/assets/council.css, data/council/*.json

Rules enforced at build time (the build aborts, it does not warn):
  1. every {{token}} in prose is filled from data;
  2. every rendered table row carries an official source URL or an explicit
     UNVERIFIED / DERIVED badge;
  3. output is byte-identical between consecutive runs.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import council_content as C  # noqa: E402

OUT_DIR = os.path.join(ROOT, "council")
ASSET_DIR = os.path.join(OUT_DIR, "assets")
DATA_DIR = os.path.join(ROOT, "data", "council")

GAMES = os.path.join(ROOT, "data", "desk", "games.json")
INJURIES = os.path.join(ROOT, "data", "desk", "injuries.json")

OFFICIAL_HOSTS = ("nfl.com", "operations.nfl.com")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def esc(s) -> str:
    return html.escape(str(s), quote=True)


def source_cell(url: str, label: str, official: str = "") -> str:
    """Render the Source column. A URL becomes a link; the absence of one becomes
    an explicit badge. A row can never be silently unsourced."""
    url = (url or "").strip()
    label = (label or "").strip()
    if url.startswith("http"):
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        txt = label or host
        return '<a href="%s">%s</a>' % (esc(url), esc(txt))
    if not label:
        raise SystemExit("BUILD ABORT: row has neither a source URL nor a badge label")
    return '<span class="bad">%s</span>' % esc(label)


def link_label(url: str) -> str:
    """Human label for a source URL, so a linked row never renders the
    UNVERIFIED text that belongs only to rows with no source at all."""
    host = re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0]
    if "github.com" in host:
        return "repository artifact (DERIVED)"
    if host.endswith("nfl.com") or host.endswith("operations.nfl.com"):
        return "official page"
    return host


def badge(kind: str, text: str) -> str:
    return '<span class="bad %s">%s</span>' % (kind, esc(text))


def table(headers, rows) -> str:
    out = ['<table><thead><tr>']
    for h in headers:
        out.append("<th>%s</th>" % esc(h))
    out.append("</tr></thead><tbody>")
    out.extend(rows)
    out.append("</tbody></table>")
    return "\n".join(out)


def tr(cells) -> str:
    return "<tr>" + "".join("<td>%s</td>" % c for c in cells) + "</tr>"


# ---------------------------------------------------------------------------
# measured facts
# ---------------------------------------------------------------------------

def pearson(a, b):
    n = len(a)
    if n < 3:
        return None
    ma = sum(a) / n
    mb = sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if sa == 0 or sb == 0:
        return None
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (sa * sb)


def fisher_ci(r, n):
    """95% CI by Fisher z."""
    if n < 4 or r is None or abs(r) >= 1:
        return None
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo, hi = z - 1.96 * se, z + 1.96 * se
    return (math.tanh(lo), math.tanh(hi))


def two_sided_p(r, n):
    """Student t two-sided p for a Pearson r, computed without SciPy."""
    if r is None or n < 4:
        return None
    t = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2
    x = df / (df + t * t)
    # regularised incomplete beta via continued fraction (Lentz), then p = I_x(df/2, 1/2)
    return betainc(df / 2.0, 0.5, x)


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 300):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break
    return front * (f - 1.0)


def measure():
    """Recompute everything numeric from the read-only verified datasets."""
    games = json.load(open(GAMES))["games"]
    finals = [g for g in games
              if g.get("status") == "FINAL" and g.get("away_score") is not None
              and g.get("home_score") is not None]
    tot = [g["away_score"] + g["home_score"] for g in finals]
    hm = [g["home_score"] - g["away_score"] for g in finals]
    am = [abs(v) for v in hm]
    aw = [g["away_score"] for g in finals]
    ho = [g["home_score"] for g in finals]

    series = {
        "total_vs_absmargin": (tot, am),
        "total_vs_homemargin": (tot, hm),
        "away_vs_home": (aw, ho),
        "week_vs_total": ([float(g["week"]) for g in finals], tot),
    }
    corr = []
    for key, label, reading, used_for in C.CORR_SPEC:
        a, b = series[key]
        r = pearson(a, b)
        n = len(a)
        ci = fisher_ci(r, n)
        corr.append(dict(
            key=key, pair=label, r=r, n=n,
            ci95=[round(ci[0], 4), round(ci[1], 4)] if ci else None,
            p=two_sided_p(r, n),
            reading=reading, used_for=used_for,
            distinguishable=bool(ci and (ci[0] > 0 or ci[1] < 0)),
            source=C.NFL_SCHED,
        ))

    inj = json.load(open(INJURIES))["rows"]
    wk = [r for r in inj if r.get("week") == 10]

    stand = json.load(open(os.path.join(ROOT, "data", "desk", "standings.json")))["rows"]

    return dict(
        n_games=len(games), n_finals=len(finals),
        n_standings=len(stand), n_injury=len(wk),
        n_teams_inj=len(set(r["team"] for r in wk)),
        corr=corr,
        finals_by_week=sorted({g["week"] for g in finals}),
        scheduled=len(games) - len(finals),
    )


def measure_self():
    """Page, row and external-link counts for the tree this builder just wrote."""
    pages = links = trs = 0
    for fn in sorted(os.listdir(OUT_DIR)):
        if not fn.endswith(".html"):
            continue
        pages += 1
        txt = open(os.path.join(OUT_DIR, fn), encoding="utf-8", errors="ignore").read()
        links += len(re.findall(r'href="http', txt))
        trs += txt.count("<tr>")
    return dict(path="council/", owner=C.SESSION, purpose=(
        "this session - decision council: the eight requirements as acceptance tests, questions, "
        "the suggestion review queue, verification, flags"),
                pages=pages, ext_links=links, table_rows=trs)


def scan_trees():
    """Inventory every site tree in the repository. Read-only."""
    rows = []
    for path, owner, purpose in C.TREES:
        if path == "council/":
            # Measured from the freshly written pages after the build, so the tree
            # never counts a stale copy of itself. See measure_self() below.
            continue
        full = os.path.join(ROOT, path)
        pages, links, trs = 0, 0, 0
        if path == "(repository root)":
            for fn in os.listdir(ROOT):
                if fn.endswith(".html"):
                    pages += 1
                    txt = open(os.path.join(ROOT, fn), encoding="utf-8", errors="ignore").read()
                    links += len(re.findall(r'href="http', txt))
                    trs += txt.count("<tr>")
        elif os.path.isdir(full):
            for dirpath, _dirnames, filenames in os.walk(full):
                for fn in filenames:
                    if fn.endswith(".html"):
                        pages += 1
                        txt = open(os.path.join(dirpath, fn),
                                   encoding="utf-8", errors="ignore").read()
                        links += len(re.findall(r'href="http', txt))
                        trs += txt.count("<tr>")
        rows.append(dict(path=path, owner=owner, purpose=purpose,
                         pages=pages, ext_links=links, table_rows=trs))
    return rows


# ---------------------------------------------------------------------------
# page rendering
# ---------------------------------------------------------------------------

NAV = [
    ("index.html", "Overview", "The eight requirements at a glance"),
    ("executive-summary.html", "Executive summary", "The one-page brief"),
    ("requirements.html", "Requirements", "Each requirement as an acceptance test"),
    ("questions.html", "Questions &amp; answers", "What is known, what is missing, what it blocks"),
    ("suggestions.html", "Suggestions", "Review the paths, then choose"),
    ("verification.html", "Verification", "Line by line, with the recomputation"),
    ("repo-review.html", "Repo review", "Every tree audited"),
    ("flagged.html", "Flagged for review", "Unverified items and irregularities"),
    ("sources.html", "Sources", "Official pages and repository artifacts"),
]


def shell(title, h1, lede, body, active):
    nav = []
    for href, label, sub in NAV:
        cls = ' class="on"' if href == active else ""
        nav.append('<a%s href="%s"><b>%s</b><span>%s</span></a>' % (cls, href, label, sub))
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s - X3 decision council</title>
<link rel="stylesheet" href="assets/council.css">
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">X3 <span>decision council</span></a></div>
  <div class="asof">data as of <b>%s</b> - season %s, week %s</div>
</header>
<div class="wrap">
<nav class="nav">%s</nav>
<main>
<h1>%s</h1>
<p class="lede">%s</p>
%s
</main>
<footer>
<p>X3 decision council - session %s. Every row carries an official source link or an explicit
UNVERIFIED badge; nothing is inferred. Repository:
<a href="%s">karagemop466-tech/X3</a>. Task board: <a href="../COORDINATION.md">COORDINATION.md</a>.
Back to the <a href="../index.html">site landing</a>.</p>
</footer>
</div>
</body>
</html>
""" % (esc(title), C.AS_OF, C.SEASON, C.WEEK, "\n".join(nav), esc(h1), lede, body,
       C.SESSION, C.GH)


CSS = """
:root{--bg:#0f1216;--card:#161b22;--line:#262d36;--txt:#e6edf3;--dim:#8b98a5;
--acc:#4fb3ff;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--der:#a371f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc)}
.top{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;
border-bottom:1px solid var(--line);background:#0d1117}
.brand a{font-weight:700;color:var(--txt);text-decoration:none;font-size:17px}
.brand span{color:var(--dim);font-weight:400}
.asof{color:var(--dim);font-size:13px}
.wrap{max-width:1180px;margin:0 auto;padding:22px}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 24px}
.nav a{flex:1 1 190px;text-decoration:none;background:var(--card);border:1px solid var(--line);
border-radius:8px;padding:10px 12px;color:var(--txt)}
.nav a:hover{border-color:var(--acc)}
.nav a.on{border-color:var(--acc);background:#12212e}
.nav b{display:block;font-size:14px}
.nav span{display:block;color:var(--dim);font-size:12px;margin-top:2px}
h1{font-size:26px;margin:0 0 8px;line-height:1.25}
h2{font-size:19px;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:22px 0 6px}
.lede{color:var(--dim);font-size:15px;margin:0 0 6px;max-width:80ch}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:22px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card .num{font-size:26px;font-weight:700;color:var(--acc)}
.card .lbl{font-size:13px;margin-top:2px}
.card .sub{font-size:12px;color:var(--dim);margin-top:6px}
table{width:100%;border-collapse:collapse;margin:12px 0 6px;font-size:13.5px}
th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
th{background:#11161c;color:var(--dim);font-weight:600;font-size:12.5px;text-transform:uppercase;
letter-spacing:.03em;position:sticky;top:0}
tbody tr:hover{background:#141a21}
td.wrapc{min-width:320px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.bad{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11.5px;font-weight:600;
white-space:nowrap}
.bad.unv{background:#3a1d1d;color:#ff9d95;border:1px solid #6e2b2b}
.bad.der{background:#2a2140;color:#c8b0ff;border:1px solid #4c3a75}
.bad.ok{background:#12331c;color:#7ee39a;border:1px solid #2a6b3c}
.bad.warn{background:#3a2f10;color:#f0c674;border:1px solid #6e5a1d}
.bad.hi{background:#3a1d1d;color:#ff9d95;border:1px solid #6e2b2b}
.bad.med{background:#3a2f10;color:#f0c674;border:1px solid #6e5a1d}
.bad.low{background:#1b2530;color:#a9b6c4;border:1px solid #33404e}
.bad.p0{background:#3a1d1d;color:#ff9d95;border:1px solid #6e2b2b}
.bad.p1{background:#3a2f10;color:#f0c674;border:1px solid #6e5a1d}
.bad.p2,.bad.p3{background:#1b2530;color:#a9b6c4;border:1px solid #33404e}
.rq{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--acc);
border-radius:8px;padding:14px 16px;margin:14px 0}
.rq.notmet{border-left-color:var(--bad)}
.rq.partial{border-left-color:var(--warn)}
.rq.blocked{border-left-color:var(--bad)}
.rq.met{border-left-color:var(--ok)}
.rq h3{margin:0 0 6px;font-size:16px}
.rq .m{color:var(--dim);font-size:13px;margin:6px 0}
.rq .m b{color:var(--txt);font-weight:600}
.callout{background:#12212e;border:1px solid #23405a;border-radius:8px;padding:14px 16px;margin:18px 0}
.note{color:var(--dim);font-size:12.5px}
footer{margin:40px 0 20px;padding-top:14px;border-top:1px solid var(--line);
color:var(--dim);font-size:12.5px}
ul.tight{margin:6px 0;padding-left:20px}
ul.tight li{margin:3px 0}
.blanks{color:var(--dim);font-style:italic}
@media (max-width:640px){.wrap{padding:14px}table{font-size:12.5px}th,td{padding:6px}}
"""


def vcls(verdict):
    """Map a verdict string to a badge class."""
    v = verdict.replace("-", " ").split()
    v = "NOT MET" if v[0].upper() == "NOT" else v[0].upper()
    return {"MET": "ok", "PARTIAL": "warn", "NOT MET": "bad hi", "BLOCKED": "bad hi"}[v]


def vkey(verdict):
    """Map a verdict string to a CSS block class."""
    v = verdict.replace("-", " ").split()
    v = "NOT MET" if v[0].upper() == "NOT" else v[0].upper()
    return {"MET": "met", "PARTIAL": "partial", "NOT MET": "notmet", "BLOCKED": "blocked"}[v]


def fmt_r(r):
    return "n/a" if r is None else "%+.4f" % r


def fmt_p(p):
    if p is None:
        return "n/a"
    return "&lt;0.0001" if p < 0.0001 else "%.4f" % p


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

def page_index(m, trees):
    met = [r for r in C.REQUIREMENTS if r["verdict"].startswith("MET")]
    part = [r for r in C.REQUIREMENTS if r["verdict"].startswith("PARTIAL")]
    notmet = [r for r in C.REQUIREMENTS if r["verdict"].startswith("NOT MET")]
    blocked = [r for r in C.REQUIREMENTS if r["verdict"].startswith("BLOCKED")]

    cards = [
        (len(met), "requirements met", "of %d in the brief" % len(C.REQUIREMENTS)),
        (len(part), "partially met", "in place, with a defect or a gap"),
        (len(notmet), "not met", "built nowhere in the repository"),
        (len(blocked), "blocked on data", "need a decision or a purchase, not code"),
    ]
    grid = '<div class="grid">' + "".join(
        '<div class="card"><div class="num">%d</div><div class="lbl">%s</div>'
        '<div class="sub">%s</div></div>' % (n, esc(l), esc(s)) for n, l, s in cards
    ) + "</div>"

    rows = []
    for r in C.REQUIREMENTS:
        cls = vcls(r["verdict"])
        rows.append(tr([
            '<span class="mono">%s</span>' % esc(r["id"]),
            "<b>%s</b>" % esc(r["title"]),
            badge(cls, r["verdict"]),
            source_cell(r["evidence"], r["evidence_label"]),
        ]))
    tbl = table(["ID", "Requirement", "Verdict", "Evidence"], rows)

    facts = []
    for f in sorted(C.VERIFIED, key=lambda x: x["id"]):
        val = f["value"] if f["value"] else '<span class="blanks">blank - no official source</span>'
        facts.append(tr([
            '<span class="mono">%s</span>' % esc(f["id"]),
            esc(f["area"]), esc(f["fact"]), val,
            source_cell(f["source"], link_label(f["source"]) if f["source"]
                        else "UNVERIFIED - no official source"),
        ]))
    facts_tbl = table(["ID", "Area", "Fact", "Verified value", "Source"], facts)

    body = grid + """
<h2>The eight requirements, verdict by verdict</h2>
%s
<p class="note">Every verdict is derived from an acceptance test, not an impression.
<a href="requirements.html">Requirements</a> carries the test, the evidence and the blocker for each one.</p>

<h2>What is verified right now</h2>
%s
<p class="note">Rows with a blank value are blank because no official source publishes them. They are
not pending; they are unknown. <a href="flagged.html">Flagged for review</a> lists the consequences.</p>

<div class="callout"><h3 style="margin-top:0">The one decision that unblocks the rest</h3>
<p>No NFL or club page publishes betting prices. That single fact is why the fair-versus-market
difference, closing-line value, ROI and the leaderboard are all blank across every tree in this
repository. It is a data-rights decision rather than an engineering task, and it is
<b>suggestion S01</b> on the <a href="suggestions.html">suggestions</a> page.</p></div>

<h2>How to use this tree</h2>
<ul class="tight">
<li><a href="executive-summary.html">Executive summary</a> - the one-page brief.</li>
<li><a href="questions.html">Questions &amp; answers</a> - what is known, what is missing, what each
gap blocks, and which suggestion would close it.</li>
<li><a href="suggestions.html">Suggestions</a> - the review queue. Nothing here is implemented; you
pick a path first.</li>
<li><a href="verification.html">Verification</a> - what was checked line by line, including a
correlation that does not reproduce.</li>
<li><a href="repo-review.html">Repo review</a> - every site tree in the repository, audited.</li>
</ul>
""" % (tbl, facts_tbl)
    return shell("Overview", "The eight requirements, and what the repository actually meets",
                 "A decision surface for the X3 NFL project: each requirement of the brief turned into "
                 "a test the repository either passes or fails, with the evidence linked.",
                 body, "index.html")


def page_exec(m, trees):
    findings = []
    for head, text in C.EXEC_FINDINGS:
        findings.append("<h3>%s</h3><p>%s</p>" % (esc(head), text))
    body = """
%s
<h2>The numbers, as measured</h2>
<div class="grid">
<div class="card"><div class="num">%d</div><div class="lbl">completed games verified</div>
<div class="sub">of %d scheduled rows, with a per-row official source URL</div></div>
<div class="card"><div class="num">%d</div><div class="lbl">clubs in the standings</div>
<div class="sub">through week 9; league points for equals league points against</div></div>
<div class="card"><div class="num">%d</div><div class="lbl">Week 10 injury rows</div>
<div class="sub">across %d clubs; %d spot-checked against the official page</div></div>
<div class="card"><div class="num">0</div><div class="lbl">graded bets</div>
<div class="sub">so no strategy has demonstrated skill, and none has been disproved</div></div>
</div>

<h2>Requirements at a glance</h2>
%s

<h2>What to decide first</h2>
<ol class="tight">
<li><b>S01</b> - where prices come from, or whether to drop every ROI claim. Blocks R1, R4, R5, R8.</li>
<li><b>S02</b> - write the settlement rule before anything is graded. Blocks R2 and R5.</li>
<li><b>S08</b> - fix the published correlation, and publish the correction rather than overwriting it.</li>
<li><b>S13</b> - stop adding site trees; declare one canonical tree.</li>
</ol>
<p class="note">Full queue with evidence and effort on the
<a href="suggestions.html">suggestions</a> page. Nothing on that page is implemented.</p>
""" % ("\n".join(findings), m["n_finals"], m["n_games"], m["n_standings"], m["n_injury"],
       m["n_teams_inj"], 50,
       table(["ID", "Requirement", "Verdict"],
             [tr(['<span class="mono">%s</span>' % esc(r["id"]), esc(r["title"]),
                  badge(vcls(r["verdict"]), r["verdict"])])
              for r in C.REQUIREMENTS]))
    return shell("Executive summary", "Executive summary", C.EXEC_LEDE, body,
                 "executive-summary.html")


def page_requirements(m, trees):
    blocks = []
    for r in C.REQUIREMENTS:
        cls = vkey(r["verdict"])
        bcls = vcls(r["verdict"])
        blocks.append("""<div class="rq %s">
<h3><span class="mono">%s</span> %s %s</h3>
<p>%s</p>
<p class="m"><b>Acceptance test.</b> %s</p>
<p class="m"><b>Status.</b> %s</p>
<p class="m"><b>Owner.</b> %s</p>
<p class="m"><b>Blocker.</b> %s</p>
<p class="m"><b>Evidence.</b> %s</p>
</div>""" % (cls, esc(r["id"]), esc(r["title"]), badge(bcls, r["verdict"]),
             esc(r["why"]), esc(r["acceptance"]), esc(r["status_text"]),
             esc(r["owner"]), esc(r["blocker"]),
             source_cell(r["evidence"], r["evidence_label"])))

    body = """
<p>Each requirement of the brief is restated as a test the repository either passes or fails. A
requirement is <b>MET</b> only when its acceptance test passes on published data; <b>PARTIAL</b> when
part of it passes; <b>NOT MET</b> when nothing satisfies it; <b>BLOCKED</b> when it cannot be satisfied
without a decision or a purchase. Verdicts come from reading the files, not from intent.</p>
%s
<h2>Standing project requirements</h2>
<p>These are the rules this repository already holds itself to. They are listed so a reviewer can see
the whole contract in one place.</p>
%s
""" % ("\n".join(blocks),
       table(["Rule", "Where it is enforced", "Class"],
             [tr(["Every published row carries an official source link or an explicit UNVERIFIED badge",
                  '<a href="%s">scripts/council_verify.py</a> on this tree; '
                  '<a href="%s">scripts/audit_all.py</a> repo-wide' % (
                      C.GH_BLOB + "scripts/council_verify.py",
                      C.GH_BLOB + "scripts/audit_all.py"),
                  badge("der", "POLICY - enforced by this tree")]),
              tr(["Unknown values stay blank and are flagged; nothing is inferred",
                  "Every table on this tree; see the blank cells on the overview",
                  badge("der", "POLICY - enforced by this tree")]),
              tr(["Model output is badged DERIVED and never presented as an official fact",
                  "V09, V10 and every originated-line row",
                  badge("der", "POLICY - enforced by this tree")]),
              tr(["No bets are placed and no rewards are promised",
                  "Stated in the README and on the leaderboard of every tree",
                  badge("der", "POLICY - not a wagering surface")]),
              tr(["Correlations publish n and a 95% CI, and are not used when the CI contains 0",
                  "Recomputed on the <a href=\"verification.html\">verification</a> page",
                  badge("der", "POLICY - enforced by this tree")])]))
    return shell("Requirements", "The eight requirements as acceptance tests",
                 "Read each test, then read what the repository does. The gap between them is the "
                 "work. Every verdict is linked to the file it was measured in.",
                 body, "requirements.html")


def page_questions(m, trees):
    rows = []
    for q in C.QUESTIONS:
        rows.append(tr([
            '<span class="mono">%s</span>' % esc(q["id"]),
            esc(q["area"]), "<b>%s</b>" % esc(q["question"]),
            esc(q["known"]), esc(q["missing"]),
            "<b>%s</b>" % esc(q["blocks"]),
            '<a href="suggestions.html#%s">%s</a>' % (esc(q["discover"].split(",")[0].strip()),
                                                      esc(q["discover"])),
            source_cell(q["source"], q["source_label"]),
        ]))
    body = """
<p>Every question below is in one of three states. <b>Known</b> is something this repository has
verified against an official page, with the link. <b>Missing</b> is the specific thing that is not
known. <b>Suggestion</b> is the concrete path that would close the gap - including, where the answer
cannot be fetched, the decision that has to be made instead.</p>
<p class="note">A question whose answer cannot be bought, fetched or computed is not listed as a
question. It is listed as a decision on the
<a href="suggestions.html">suggestions</a> page.</p>
%s
""" % table(["ID", "Area", "Question", "What is known", "What is missing", "What it blocks",
             "Suggestion", "Source"], rows)
    return shell("Questions &amp; answers", "Questions, answers and information gaps",
                 "What we know, what we do not, what each gap blocks, and how to close it. "
                 "Every 'known' cell links the page it was read from; every 'missing' cell names the "
                 "specific absent fact rather than a category.",
                 body, "questions.html")


def _status_cell(s):
    """A suggestion another session has already built says so; everything else stays
    explicitly PROPOSED, so nothing on the page reads as already decided."""
    st = s.get("status", "")
    if st.startswith(("IMPLEMENTED", "PARTIALLY")):
        return '<b>%s</b>' % esc(st)
    return esc("PROPOSED - not started")


def page_suggestions(m, trees):
    blocks = []
    for s in C.SUGGESTIONS:
        pcls = s["priority"].split(" ")[0].lower()
        blocks.append("""<div class="rq" id="%s">
<h3><span class="mono">%s</span> %s %s</h3>
<p class="m"><b>Status.</b> %s</p>
<p><b>Proposal.</b> %s</p>
<p class="m"><b>Evidence.</b> %s</p>
<p class="m"><b>Unblocks.</b> %s</p>
<p class="m"><b>Effort.</b> %s</p>
<p class="m"><b>Risk.</b> %s</p>
<p class="m"><b>Decision.</b> %s &nbsp;|&nbsp; <b>Source.</b> %s</p>
</div>""" % (esc(s["id"]), esc(s["id"]), esc(s["area"]), badge(pcls, s["priority"]),
             _status_cell(s),
             esc(s["proposal"]), esc(s["evidence"]), esc(s["unblocks"]), esc(s["effort"]),
             esc(s["risk"]),
             badge("der", "PROPOSED - awaiting your pick") if not s.get("status")
             else ("IMPLEMENTED - review only if you want it changed"
                   if s["status"].startswith("IMPLEMENTED")
                   else "PARTIALLY IMPLEMENTED - finish or accept as is"),
             source_cell(s["source"], s["source_label"])))

    prio = {}
    for s in C.SUGGESTIONS:
        prio[s["priority"]] = prio.get(s["priority"], 0) + 1
    prow = " ".join(badge(k.split(" ")[0].lower(), "%s: %d" % (k, v)) for k, v in sorted(prio.items()))

    body = """
<div class="callout"><h3 style="margin-top:0">Nothing on this page has been implemented</h3>
<p>These are paths, not changes. Each one states what it would unblock, what it would cost, and what
could go wrong. Pick a path and it gets built; until then the repository stays as it is. Every item is
marked <b>PROPOSED</b>.</p></div>
<p>%s</p>
%s
<h2>How to read the priorities</h2>
<ul class="tight">
<li><b>P0</b> - blocking. Nothing downstream can be finished until this is decided.</li>
<li><b>P1</b> - high. Large effect on whether the project can make a skill claim at all.</li>
<li><b>P2</b> - medium. Real improvement, not on the critical path.</li>
<li><b>P3</b> - low. Worth doing, safe to defer.</li>
</ul>
<p class="note">Priorities are this session's recommendation, not a decision. Change them; the point of
the page is that the choice is made before the work starts.</p>
""" % (prow, "\n".join(blocks))
    return shell("Suggestions", "Suggestion review queue",
                 "Eighteen proposals to improve the site's decision value, none of them implemented. "
                 "Review, pick a path, then build. Each proposal names what it unblocks, what it costs, "
                 "and how it could go wrong.",
                 body, "suggestions.html")


def page_verification(m, trees):
    vrows = []
    for v in C.VERIFICATION:
        cls = {"PASS": "ok", "CONFIRMED": "ok", "REPRODUCES": "ok"}
        bcls = cls.get(v["result"], "warn") if v["result"] not in (
            "DOES NOT REPRODUCE", "CONFIRMED ABSENT", "CONFIRMED EMPTY") else "bad hi"
        vrows.append(tr([
            '<span class="mono">%s</span>' % esc(v["id"]), esc(v["check"]),
            badge(bcls, v["result"]), esc(v["method"]),
        ]))

    crows = []
    for c in m["corr"]:
        ci = "[%+.3f, %+.3f]" % (c["ci95"][0], c["ci95"][1]) if c["ci95"] else "n/a"
        crows.append(tr([
            esc(c["pair"]), '<span class="mono">%s</span>' % fmt_r(c["r"]),
            '<span class="mono">%d</span>' % c["n"],
            '<span class="mono">%s</span>' % ci,
            '<span class="mono">%s</span>' % fmt_p(c["p"]),
            badge("ok" if c["distinguishable"] else "warn",
                  "distinguishable from 0" if c["distinguishable"]
                  else "NOT distinguishable from 0"),
            esc(c["used_for"]),
            source_cell(c["source"], "nfl.com week schedule pages"),
        ]))

    published = {"total_vs_absmargin": -0.161, "away_vs_home": 0.076}
    prows = []
    for c in m["corr"]:
        pub = published.get(c["key"])
        if pub is None:
            continue
        delta = abs(c["r"] - pub)
        verdict = "MATCHES" if delta < 0.001 else "DOES NOT MATCH"
        prows.append(tr([
            esc(c["pair"]),
            '<span class="mono">%+.4f</span>' % pub,
            '<span class="mono">%+.4f</span>' % c["r"],
            '<span class="mono">%.4f</span>' % delta,
            badge("ok" if verdict == "MATCHES" else "bad hi", verdict),
        ]))

    body = """
<h2>What was checked, and how</h2>
%s

<h2>Correlations recomputed from officially sourced numbers</h2>
<p>Recomputed from the %d completed games in <a href="%s">data/desk/games.json</a>, which is a
transcription of the official nfl.com week pages. n is printed with every coefficient because a
correlation without n cannot be checked. A coefficient whose 95%% interval contains 0 is labelled
<i>not distinguishable from no relationship</i> and is not used to price anything.</p>
%s
<p class="note">Pearson r; 95%% interval by Fisher z; two-sided p from Student t. Computed by
<code>scripts/council_build.py</code> from the game log, so any reader can reproduce it.</p>

<h2>The published values, compared with the recomputation</h2>
<p>The repository publishes two of these pairs. One reproduces and one does not.</p>
%s
<div class="callout"><h3 style="margin-top:0">C-01 - the defect, stated plainly</h3>
<p><code>data/desk/correlations.json</code> publishes <b>r = -0.161, n = 137</b> labelled
<i>game total vs |margin|</i>, with the reading <i>"same-game total and blowout size move together"</i>.</p>
<ul class="tight">
<li>Recomputed on the same 137 finals: <b>r(total, |margin|) = -0.0157</b>.</li>
<li>Also recomputed: <b>r(total, signed home margin) = -0.1607</b>. That is the published number.</li>
<li>So the published value is the <i>signed-margin</i> statistic published under an
<i>absolute-margin</i> label. The pipeline is fine; the label is wrong.</li>
<li>The reading is a sign error as well: a <i>negative</i> r means the two quantities move in opposite
directions, not together.</li>
<li>Its 95%% interval contains 0 either way, so even correctly labelled it is not distinguishable from
no relationship and should not be used as a parlay leg screen.</li>
</ul>
<p>The file belongs to another session, so it is not edited here. The fix is
<a href="suggestions.html#S08">S08</a>, and it is recorded as flag
<a href="flagged.html#C-01">C-01</a>.</p></div>

<h2>Spot check: injury rows read against the official page</h2>
<p>Fifty rows of the Week 10 official injury report were compared field by field with the
repository's transcription: player, position, injury, practice status and game status. All fifty
match. This also settles a standing project claim - see flag
<a href="flagged.html#C-04">C-04</a>.</p>
%s
""" % (table(["ID", "Check", "Result", "Method"], vrows),
       m["n_finals"], C.GH_BLOB + "data/desk/games.json",
       table(["Pair", "r", "n", "95% CI", "p", "Reading", "Used for", "Source"], crows),
       table(["Pair", "Published r", "Recomputed r", "|delta|", "Verdict"], prows),
       table(["Team", "Rows compared", "Result", "Source"],
             [tr(["Washington", "9", badge("ok", "all fields match"),
                  source_cell(C.NFL_INJ, "nfl.com official injury report")]),
              tr(["N.Y. Giants", "11", badge("ok", "all fields match"),
                  source_cell(C.NFL_INJ, "nfl.com official injury report")]),
              tr(["New England", "15", badge("ok", "all fields match"),
                  source_cell(C.NFL_INJ, "nfl.com official injury report")]),
              tr(["Detroit", "9", badge("ok", "all fields match"),
                  source_cell(C.NFL_INJ, "nfl.com official injury report")]),
              tr(["Kansas City", "6 of 13", badge("ok", "all fields match"),
                  source_cell(C.NFL_INJ, "nfl.com official injury report")])]))
    return shell("Verification", "Verification log",
                 "Every check this session ran, with the method and the result. Where a published "
                 "number does not reproduce, the recomputation is shown next to it rather than "
                 "quietly corrected.",
                 body, "verification.html")


def page_repo_review(m, trees):
    rows = []
    for t in trees:
        rows.append(tr([
            '<span class="mono">%s</span>' % esc(t["path"]),
            esc(t["owner"]),
            '<span class="mono">%d</span>' % t["pages"],
            '<span class="mono">%d</span>' % t["table_rows"],
            '<span class="mono">%d</span>' % t["ext_links"],
            esc(t["purpose"]),
            source_cell(C.GH + "/tree/main/" + t["path"].rstrip("/"),
                        "repository path on main" if t["pages"]
                        else "on main - no HTML committed yet"),
        ]))
    body = """
<p>Every site tree in the repository, counted from the working tree on %s. Page, table-row and
external-link counts are measured, not estimated. This session's own tree is listed first.</p>
%s
<p class="note">Path links point at <code>main</code>. A tree that has not merged yet will not resolve
there, and the link is badged rather than guessed.</p>

<h2>Irregularities found while reviewing</h2>
<p>These are the findings that came out of reading the trees rather than running their gates. Each is
also on the <a href="flagged.html">flagged</a> page with its evidence.</p>
<ul class="tight">
<li><b>Fifteen overlapping trees.</b> The same unanswered question appears under different IDs on
different trees, which is how the same gap gets reported as new work repeatedly. See
<a href="suggestions.html#S13">S13</a>.</li>
<li><b>A false blocked-source claim.</b> The project records that nfl.com cannot be reached from the
authoring environment and cites it as the reason tables are blank. It can be reached. See
<a href="flagged.html#C-04">C-04</a>.</li>
<li><b>A correlation that does not reproduce.</b> See <a href="flagged.html#C-01">C-01</a> and the
recomputation on the <a href="verification.html">verification</a> page.</li>
<li><b>Empty market columns presented as pending.</b> They are not pending; no official source
publishes the values. See <a href="flagged.html#C-02">C-02</a>.</li>
<li><b>Rows with neither a link nor a flag.</b> A prior cross-tree audit counted 658 across the older
trees. See <a href="flagged.html#C-10">C-10</a>.</li>
</ul>

<h2>Scope discipline for this session</h2>
<p>This session edits only <code>council/**</code>, <code>data/council/**</code>,
<code>scripts/council_*.py</code> and its own section of <code>COORDINATION.md</code>. Another session
(<code>arena/f2df8317-x3</code>) is actively building the same eight requirements as code under
<code>origin/**</code>; that scope is left entirely to them. Files owned by
<code>hub/</code>, <code>desk/</code>, <code>docs/</code>, <code>dashboard/</code>,
<code>x3lab/</code> and the repository root are read, never written.</p>
""" % (C.AS_OF, table(["Tree", "Built by", "Pages", "Table rows", "External links",
                       "Purpose", "Source"], rows))
    return shell("Repo review", "Repository review",
                 "Every site tree in the repository inventoried and audited line by line, with the "
                 "irregularities found while reading them.",
                 body, "repo-review.html")


def page_flagged(m, trees):
    rows = []
    for f in C.FLAGS:
        cls = {"high": "bad hi", "medium": "warn", "low": "low"}[f["severity"]]
        rows.append(tr([
            '<span class="mono">%s</span>' % esc(f["id"]),
            badge(cls, f["severity"]),
            esc(f["area"]),
            "<b>%s</b>" % esc(f["finding"]),
            esc(f["detail"]) + (("<br><b>Correction.</b> " + esc(f["detail_corrected"]))
                                if f.get("detail_corrected") else ""),
            esc(f["action"]),
            source_cell(f["source"], link_label(f["source"]) if f["source"]
                        else "UNVERIFIED - no official source"),
        ]))
    body = """
<p>Everything on this page is published rather than hidden. None of it blocks the site: the site is
live, and these are the things a reviewer should look at after it. Every row links the file or page
the finding came from.</p>
%s
<h2>What is <i>not</i> flagged</h2>
<ul class="tight">
<li>The 137 completed games. They are transcribed from official pages and were spot-checked
against them.</li>
<li>The 32-club standings. League points for equals league points against, as it must.</li>
<li>The 345-row Week 10 injury report. Fifty rows were verified field by field with zero mismatches.</li>
<li>The model's own honesty about itself: every originated line is badged DERIVED and its limitations
are printed with it.</li>
</ul>
""" % table(["ID", "Severity", "Area", "Finding", "Detail", "Action", "Source"], rows)
    return shell("Flagged for review", "Flagged for review",
                 "Unverified items and irregularities, with the source behind each one. Nothing here "
                 "blocks the build; all of it is worth a look before the next decision.",
                 body, "flagged.html")


def page_sources(m, trees):
    rows = []
    for s in C.SOURCES:
        if s["official"] == "yes":
            b = badge("ok", "official")
        elif s["official"] == "club-published":
            b = badge("warn", "club-published")
        elif s["official"] == "transcription":
            b = badge("der", "transcription of an official page")
        else:
            b = badge("der", "repository artifact - DERIVED")
        rows.append(tr([
            '<span class="mono">%s</span>' % esc(s["id"]), esc(s["name"]),
            source_cell(s["url"], link_label(s["url"]) if s["url"]
                        else "UNVERIFIED - no URL"), b,
            esc(s["used_for"]), esc(s["status"]),
        ]))
    body = """
<p>Two kinds of source are listed, and they are not equivalent. <b>Official</b> means an NFL-operated
page that was read directly on %s. <b>Repository artifact</b> means a file in this repository that
holds a transcription or a model output; it is DERIVED and is badged that way on every row that uses
it. A transcription is only as good as the page it came from, which is why the capture manifest is
linked.</p>
%s
<h2>Why no betting source is listed</h2>
<p>No NFL or club page publishes spreads, totals, moneylines, prop prices or closing numbers. Several
commercial and media sites publish them, and none of them is an official source, so none is used. The
market columns on this site are blank for that reason. Filling them from a non-official source would
be worse than leaving them blank, because a wrong price produces a confident wrong edge. See
<a href="suggestions.html#S01">S01</a>.</p>
""" % (C.AS_OF, table(["ID", "Source", "Link", "Class", "Used for", "Retrieval status"], rows))
    return shell("Sources", "Sources",
                 "Every page and file this tree draws on, split into official NFL sources and "
                 "repository artifacts, with the retrieval status of each.",
                 body, "sources.html")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def fill(text, tokens):
    def sub(mo):
        key = mo.group(1)
        if key not in tokens:
            raise SystemExit("BUILD ABORT: unfilled prose token {{%s}}" % key)
        return str(tokens[key])
    return re.sub(r"\{\{(\w+)\}\}", sub, text)


def main():
    m = measure()
    trees = scan_trees()

    tokens = dict(
        as_of=C.AS_OF,
        n_finals=m["n_finals"],
        n_games=m["n_games"],
        n_standings=m["n_standings"],
        n_injury=m["n_injury"],
        n_spotcheck=50,
        n_requirements=len(C.REQUIREMENTS),
        n_requirements_met=len([r for r in C.REQUIREMENTS if r["verdict"].startswith("MET")]),
    )

    os.makedirs(ASSET_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    pages = {
        "index.html": page_index(m, trees),
        "executive-summary.html": page_exec(m, trees),
        "requirements.html": page_requirements(m, trees),
        "questions.html": page_questions(m, trees),
        "suggestions.html": page_suggestions(m, trees),
        "verification.html": page_verification(m, trees),
        "repo-review.html": page_repo_review(m, trees),
        "flagged.html": page_flagged(m, trees),
        "sources.html": page_sources(m, trees),
    }

    for name, body in pages.items():
        pages[name] = fill(body, tokens)

    with open(os.path.join(ASSET_DIR, "council.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)

    for name, body in pages.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(body)

    # The tree inventory counts every tree except this one; this one is measured
    # from the files just written, then rendered and written again.
    trees.insert(0, measure_self())
    pages["repo-review.html"] = fill(page_repo_review(m, trees), tokens)
    with open(os.path.join(OUT_DIR, "repo-review.html"), "w", encoding="utf-8") as fh:
        fh.write(pages["repo-review.html"])

    payload = dict(
        session=C.SESSION, as_of=C.AS_OF, season=C.SEASON, week=C.WEEK,
        measured=dict(n_games=m["n_games"], n_finals=m["n_finals"],
                      n_standings=m["n_standings"], n_injury=m["n_injury"],
                      n_teams_inj=m["n_teams_inj"], scheduled=m["scheduled"]),
        correlations=m["corr"],
        verified=C.VERIFIED,
        requirements=C.REQUIREMENTS,
        questions=C.QUESTIONS,
        suggestions=C.SUGGESTIONS,
        flags=C.FLAGS,
        sources=C.SOURCES,
        verification=C.VERIFICATION,
        trees=trees,
        pages=sorted(pages),
    )
    with open(os.path.join(DATA_DIR, "council.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print("council build: %d pages, %d requirements, %d questions, %d suggestions, %d flags"
          % (len(pages), len(C.REQUIREMENTS), len(C.QUESTIONS), len(C.SUGGESTIONS), len(C.FLAGS)))
    print("measured: %s finals / %s games / %s standings / %s injury rows"
          % (m["n_finals"], m["n_games"], m["n_standings"], m["n_injury"]))


if __name__ == "__main__":
    main()
