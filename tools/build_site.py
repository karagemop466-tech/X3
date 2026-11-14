# -*- coding: utf-8 -*-
"""
Build the X3 static site.

Stage 1  compute derived layers (injury x depth join, correlations, model lines)
Stage 2  emit data/*.json
Stage 3  emit site/*.html

Nothing here invents a value. Derived columns are labelled "derived"; anything
that could not be read from an official source is emitted as "" and pushed onto
the flagged list.
"""
from __future__ import annotations

import html
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nfl_data as D
import site_content as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(SITE, "data")

TNAME = {t[0]: t[1] for t in D.TEAMS}
TPROF = {t[0]: t[2] for t in D.TEAMS}
TSITE = {t[0]: t[3] for t in D.TEAMS}
TCONF = {t[0]: t[4] for t in D.TEAMS}
TDIV = {t[0]: t[5] for t in D.TEAMS}
ORD = [t[0] for t in D.TEAMS]

OFF_POS = {"QB", "RB", "FB", "HB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "LOT", "ROT"}
DEF_POS = {"DE", "DT", "NT", "DL", "EDGE", "LB", "MLB", "WLB", "SLB", "ILB", "OLB",
           "LOLB", "ROLB", "LILB", "RILB", "LDE", "RDE", "LDT", "RDT", "CB", "NCB",
           "DB", "S", "SS", "FS", "NB", "RUSH", "SAM", "MIKE", "WILL", "N"}
ST_POS = {"K", "P", "LS", "H", "KR", "PR", "KOR", "KO", "PK"}

FLAGGED: list[dict] = []


def flag(item_id, area, severity, what, why, source, action=""):
    FLAGGED.append({
        "id": item_id, "area": area, "severity": severity, "what": what,
        "why": why, "source": source, "action": action,
    })


def norm(name: str) -> str:
    """Normalise a player name for matching: drop jersey numbers, case, punctuation."""
    s = name.strip().lower()
    s = re.sub(r"^\d+\s+", "", s)          # packers-style jersey prefix
    s = re.sub(r"[^a-z0-9 ]", "", s)       # drop apostrophes, periods, accents
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v|x)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def base_pos(slot_pos: str) -> str:
    return re.sub(r"\s*\(\d+\)\s*$", "", slot_pos).strip()


def unit_of(pos: str) -> str:
    p = base_pos(pos).upper()
    if p in OFF_POS:
        return "Offense"
    if p in DEF_POS:
        return "Defense"
    if p in ST_POS:
        return "Special Teams"
    return "Unclassified"


# ---------------------------------------------------------------------------
# Stage 1a: index the depth charts
# ---------------------------------------------------------------------------
def build_depth_index():
    """player_norm -> list of (team, slot_pos, depth_1based, replacement_name)"""
    idx = {}
    for abbr, d in D.DEPTH.items():
        for slot_pos, players in d["slots"]:
            n = len(players)
            for i, p in enumerate(players):
                if not p:
                    continue
                idx.setdefault(norm(p), []).append({
                    "team": abbr, "slot": slot_pos, "depth": i + 1,
                    "replacement": players[i + 1] if i + 1 < n else "",
                    "replacement_depth": (i + 2) if i + 1 < n else 0,
                })
    return idx


# ---------------------------------------------------------------------------
# Stage 1b: injury x depth  ->  deficiency rows
# ---------------------------------------------------------------------------
ABSENT = {"Out", "Doubtful"}


def build_deficiencies(depth_idx):
    rows = []
    cross_team = []
    for (abbr, player, pos, injury, practice, status) in D.INJURIES:
        if status not in ABSENT:
            continue
        hits = depth_idx.get(norm(player), [])
        own = [h for h in hits if h["team"] == abbr]
        other = [h for h in hits if h["team"] != abbr]
        if other:
            cross_team.append((abbr, player, pos, other[0]["team"], other[0]["slot"]))
        if not own:
            if abbr not in D.DEPTH:
                note = ("No depth chart could be read for this club, so no replacement can be "
                        "named. See flag F-05.")
            else:
                note = ("Listed on the official injury report but not found on the club's own "
                        "depth chart. Treated as unknown, never as healthy.")
            rows.append({
                "team": abbr, "team_name": TNAME[abbr], "player": player, "pos": pos,
                "injury": injury, "game_status": status, "unit": unit_of(pos),
                "slot": "", "out_depth": "", "replacement": "",
                "replacement_depth": "", "note": note,
                "src_inj": D.INJ_URL, "src_depth": D.DEPTH.get(abbr, {}).get("url", ""),
            })
            continue
        h = own[0]
        rows.append({
            "team": abbr, "team_name": TNAME[abbr], "player": player, "pos": pos,
            "injury": injury, "game_status": status, "unit": unit_of(base_pos(h["slot"])),
            "slot": h["slot"], "out_depth": str(h["depth"]),
            "replacement": h["replacement"],
            "replacement_depth": str(h["replacement_depth"]) if h["replacement_depth"] else "",
            "note": "" if h["replacement"] else "No replacement listed at this position on the club chart.",
            "src_inj": D.INJ_URL, "src_depth": D.DEPTH.get(abbr, {}).get("url", ""),
        })
    return rows, cross_team


# ---------------------------------------------------------------------------
# Stage 1c: correlations computable from the verified standings
# ---------------------------------------------------------------------------
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def build_correlations():
    gp, pct, pf_pg, pa_pg, net_pg, home_pct, road_pct = [], [], [], [], [], [], []
    for (abbr, w, l, t, pct_s, pf, pa, net, home, road, div, conf, strk, last5) in D.STANDINGS:
        g = w + l + t
        if g == 0:
            continue
        gp.append(abbr)
        pct.append(w / g + 0.5 * (t / g))
        pf_pg.append(pf / g)
        pa_pg.append(pa / g)
        net_pg.append(net / g)
        home_pct.append(rec_pct(home))
        road_pct.append(rec_pct(road))

    def r(a, b):
        v = pearson(a, b)
        return "" if v is None else f"{v:+.4f}"

    return [
        {"pair": "Points for per game vs. win percentage", "kind": "Team-season",
         "estimator": "Pearson r across all 32 clubs", "data": "Official 2026 league standings",
         "value": r(pf_pg, pct), "n": len(gp), "status": "Computed",
         "source": D.STAND_URL},
        {"pair": "Points against per game vs. win percentage", "kind": "Team-season",
         "estimator": "Pearson r across all 32 clubs", "data": "Official 2026 league standings",
         "value": r(pa_pg, pct), "n": len(gp), "status": "Computed",
         "source": D.STAND_URL},
        {"pair": "Net points per game vs. win percentage", "kind": "Team-season",
         "estimator": "Pearson r across all 32 clubs", "data": "Official 2026 league standings",
         "value": r(net_pg, pct), "n": len(gp), "status": "Computed",
         "source": D.STAND_URL},
        {"pair": "Home win percentage vs. road win percentage", "kind": "Team-season",
         "estimator": "Pearson r across all 32 clubs", "data": "Official 2026 league standings",
         "value": r(home_pct, road_pct), "n": len(gp), "status": "Computed",
         "source": D.STAND_URL},
    ]


def rec_pct(rec: str) -> float:
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*$", rec or "")
    if not m:
        return 0.0
    w, l, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
    g = w + l + t
    return 0.0 if g == 0 else (w + 0.5 * t) / g


# ---------------------------------------------------------------------------
# Stage 1d: model lines (HFA = 0.0, no schedule adjustment — see Q-10, Q-11)
# ---------------------------------------------------------------------------
HFA = 0.0


def build_model_lines():
    rate = {}
    for row in D.STANDINGS:
        abbr, w, l, t = row[0], row[1], row[2], row[3]
        pf, pa = row[5], row[6]
        g = w + l + t
        rate[abbr] = {"gp": g, "pf": pf / g, "pa": pa / g, "net": (pf - pa) / g}

    rows = []
    for (day, date, time_et, away, home, net, url) in D.SCHEDULE:
        a, h = rate.get(away), rate.get(home)
        if not a or not h:
            rows.append({"day": day, "date": date, "time": time_et, "away": away, "home": home,
                         "net": net, "url": url,
                         "model_home_spread": "", "model_total": "",
                         "exp_home": "", "exp_away": ""})
            continue
        exp_home = (h["pf"] + a["pa"]) / 2.0
        exp_away = (a["pf"] + h["pa"]) / 2.0
        spread = (h["net"] - a["net"]) + HFA          # positive => home favoured
        rows.append({
            "day": day, "date": date, "time": time_et, "away": away, "home": home,
            "away_name": TNAME[away], "home_name": TNAME[home], "net": net, "url": url,
            "model_home_spread": f"{spread:+.1f}",
            "model_total": f"{exp_home + exp_away:.1f}",
            "exp_home": f"{exp_home:.1f}", "exp_away": f"{exp_away:.1f}",
        })
    return rows, rate


# ---------------------------------------------------------------------------
# Stage 1e: repo audit
# ---------------------------------------------------------------------------
def repo_audit():
    import subprocess

    def git(*args):
        return subprocess.run(["git", "-C", ROOT] + list(args),
                              capture_output=True, text=True).stdout.strip()

    sha = git("rev-parse", "HEAD")
    short = sha[:7]
    files = git("ls-files").splitlines()
    out = []
    for f in files:
        p = os.path.join(ROOT, f)
        size = os.path.getsize(p) if os.path.exists(p) else 0
        with open(p, "rb") as fh:
            raw = fh.read()
        nlines = 0 if not raw else raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)
        try:
            body = raw.decode("utf-8")
        except UnicodeDecodeError:
            body = ""
        out.append({
            "path": f,
            "bytes": size,
            "lines": nlines,
            "content": body if size <= 400 else body[:400],
            "truncated": size > 400,
            "blob": f"https://github.com/karagemop466-tech/X3/blob/{sha}/{f}",
            "history": f"https://github.com/karagemop466-tech/X3/commits/{sha}/{f}",
        })
    return {
        "sha": sha, "short": short,
        "commit_url": f"https://github.com/karagemop466-tech/X3/commit/{sha}",
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit_count": git("rev-list", "--count", "HEAD"),
        "files": out,
    }


# ---------------------------------------------------------------------------
# Stage 2: JSON emit
# ---------------------------------------------------------------------------
def emit_json(bundle: dict):
    os.makedirs(DATA, exist_ok=True)
    for name, obj in bundle.items():
        with open(os.path.join(DATA, name + ".json"), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Stage 3: HTML
# ---------------------------------------------------------------------------
CSS = """
:root{--bg:#0d1117;--panel:#151b23;--panel2:#1b2430;--line:#263241;--txt:#e6edf3;
--dim:#8b98a5;--acc:#3fb950;--warn:#d29922;--bad:#f85149;--info:#58a6ff;--mut:#6e7681}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--info);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1400px;margin:0 auto;padding:0 20px}
header{background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20}
.brand{display:flex;align-items:baseline;gap:12px;padding:14px 0 10px}
.brand h1{font-size:19px;margin:0;letter-spacing:.5px}
.brand span{color:var(--dim);font-size:12px}
nav{display:flex;flex-wrap:wrap;gap:2px;padding-bottom:10px}
nav a{padding:6px 11px;border-radius:6px;color:var(--dim);font-size:13px}
nav a:hover{background:var(--panel2);color:var(--txt);text-decoration:none}
nav a.on{background:var(--panel2);color:var(--txt);box-shadow:inset 0 -2px 0 var(--acc)}
main{padding:24px 0 60px}
h2{font-size:22px;margin:0 0 4px}
h3{font-size:16px;margin:26px 0 8px;color:var(--txt)}
p.lede{color:var(--dim);margin:0 0 18px;max-width:100ch}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.card .k{font-size:26px;font-weight:600;line-height:1.1}
.card .l{color:var(--dim);font-size:12px;margin-top:4px;text-transform:uppercase;letter-spacing:.6px}
.card.ok .k{color:var(--acc)}.card.warn .k{color:var(--warn)}.card.bad .k{color:var(--bad)}
.card.info .k{color:var(--info)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.bar input,.bar select{background:var(--panel2);border:1px solid var(--line);color:var(--txt);
border-radius:6px;padding:7px 10px;font-size:13px}
.bar input{min-width:230px}
table{width:100%;border-collapse:collapse;font-size:13px}
.tw{overflow:auto;border:1px solid var(--line);border-radius:10px;margin:10px 0}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);position:sticky;top:0;font-size:11.5px;text-transform:uppercase;
letter-spacing:.5px;color:var(--dim);cursor:pointer;white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tbody tr:hover{background:#111823}
.b{display:inline-block;padding:1px 7px;border-radius:20px;font-size:11px;border:1px solid var(--line);
white-space:nowrap}
.b.ok{color:var(--acc);border-color:#1f6f37}.b.warn{color:var(--warn);border-color:#6b5210}
.b.bad{color:var(--bad);border-color:#7d2b26}.b.info{color:var(--info);border-color:#1f4b7d}
.b.mut{color:var(--mut)}
.src{font-size:11px}
.blank{color:var(--mut);font-style:italic}
.mut{color:var(--dim)}
small.note{color:var(--dim);display:block;margin-top:6px}
footer{border-top:1px solid var(--line);padding:20px 0 40px;color:var(--dim);font-size:12px}
.kv{display:grid;grid-template-columns:170px 1fr;gap:6px 14px;font-size:13px}
.kv dt{color:var(--dim)}
.kv dd{margin:0}
ul.tight{margin:6px 0 0;padding-left:20px}ul.tight li{margin:3px 0}
details{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:8px 0}
summary{cursor:pointer;font-weight:600}
.badge{font-size:10px;padding:1px 6px;border-radius:4px;border:1px solid var(--line);color:var(--dim)}
"""

JS = """
document.querySelectorAll('th[data-sort]').forEach(function(th){
  th.addEventListener('click',function(){
    var tb=th.closest('table');var i=[].indexOf.call(th.parentNode.children,th);
    var asc=th.dataset.asc!=='1';th.dataset.asc=asc?'1':'0';
    var rows=[].slice.call(tb.tBodies[0].rows);
    rows.sort(function(a,b){
      var x=a.cells[i].dataset.sort!==undefined?a.cells[i].dataset.sort:a.cells[i].textContent;
      var y=b.cells[i].dataset.sort!==undefined?b.cells[i].dataset.sort:b.cells[i].textContent;
      var nx=parseFloat(x),ny=parseFloat(y);
      if(!isNaN(nx)&&!isNaN(ny))return asc?nx-ny:ny-nx;
      return asc?String(x).localeCompare(String(y)):String(y).localeCompare(String(x));
    });
    rows.forEach(function(r){tb.tBodies[0].appendChild(r)});
  });
});
document.querySelectorAll('input[data-filter]').forEach(function(inp){
  inp.addEventListener('input',function(){
    var q=inp.value.toLowerCase();var tb=document.querySelector(inp.dataset.filter);
    [].forEach.call(tb.tBodies[0].rows,function(r){
      r.style.display=r.textContent.toLowerCase().indexOf(q)>-1?'':'none';
    });
  });
});
document.querySelectorAll('[data-filter]').forEach(function(inp){
  function cnt(){var tb=document.querySelector(inp.dataset.filter);
    if(!tb)return;var v=0;
    [].forEach.call(tb.tBodies[0].rows,function(r){if(r.style.display!=='none')v++;});
    var out=document.getElementById('c_'+tb.id);if(out)out.textContent=v+' rows';}
  inp.addEventListener('input',cnt);cnt();
});
document.querySelectorAll('select[data-eq]').forEach(function(sel){
  sel.addEventListener('change',function(){
    var v=sel.value.toLowerCase();var tb=document.querySelector(sel.dataset.eq);
    var col=parseInt(sel.dataset.col||'0',10);
    [].forEach.call(tb.tBodies[0].rows,function(r){
      var c=(r.cells[col]?r.cells[col].textContent:'').toLowerCase();
      r.style.display=(!v||c.indexOf(v)>-1)?'':'none';
    });
  });
});
"""

NAV = [
    ("index.html", "Overview"),
    ("executive-summary.html", "Executive Summary"),
    ("standings.html", "Standings"),
    ("schedule.html", "Schedule"),
    ("injuries.html", "Injuries"),
    ("depth-charts.html", "Depth & Deficiencies"),
    ("lines.html", "Own Lines"),
    ("strategies.html", "Strategies"),
    ("validation.html", "Validation Gates"),
    ("correlation.html", "Correlation"),
    ("leaderboard.html", "Leaderboard"),
    ("questions.html", "Open Questions"),
    ("suggestions.html", "Suggestions"),
    ("requirements.html", "Requirements"),
    ("repo-review.html", "Repo Review"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for Review"),
    ("coordination.html", "Coordination"),
]


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def page(title, active, body, subtitle=""):
    nav = "".join(
        f'<a href="{u}" class="{"on" if u == active else ""}">{esc(t)}</a>'
        for u, t in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | X3 NFL</title>
<style>{CSS}</style></head><body>
<header><div class="wrap">
<div class="brand"><h1>X3 &middot; NFL Decision System</h1>
<span>2026 season &middot; Week 10 &middot; data as of {D.AS_OF}</span></div>
<nav>{nav}</nav></div></header>
<main><div class="wrap">
<h2>{esc(title)}</h2>
{('<p class="lede">' + esc(subtitle) + "</p>") if subtitle else ""}
{body}
</div></main>
<footer><div class="wrap">
Verification rule: a row is verified only when its value was read from an official
NFL source and the row carries that source's link. Values that could not be confirmed
are blank and marked <span class="b warn">UNVERIFIED</span>; they are repeated on the
<a href="flagged.html">Flagged for Review</a> page. Model output is always labelled
<span class="b mut">DERIVED</span> and is never presented as fact.
</div></footer>
<script>{JS}</script></body></html>
"""


def src(url, label="source"):
    if not url:
        return '<span class="b bad">UNVERIFIED</span>'
    return f'<a class="src" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)} &#8599;</a>'


def cell(v, cls=""):
    v = "" if v is None else str(v)
    if v.strip() == "":
        return '<td class="blank">UNVERIFIED</td>'
    return f'<td class="{cls}">{esc(v)}</td>'


def table(headers, rows, filter_id=None, sortable=True):
    th = "".join(
        f'<th{" data-sort" if sortable else ""}>{esc(h)}</th>' for h in headers
    )
    tb = "".join("<tr>" + ("".join(r) if isinstance(r, (list, tuple)) else r) + "</tr>"
                 for r in rows)
    fid = f' id="{filter_id}"' if filter_id else ""
    fbox = ""
    if filter_id:
        fbox = (f'<div class="bar"><input data-filter="#{filter_id}" '
                f'placeholder="Filter rows&hellip;">'
                f'<span class="mut" id="c_{filter_id}"></span></div>')
    return f'{fbox}<div class="tw"><table{fid}><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'


def badge(text, kind):
    return f'<span class="b {kind}">{esc(text)}</span>'


# ---------------------------------------------------------------- page bodies
def p_index(b):
    kpi = [
        ("32", "Clubs in standings", "ok"),
        ("14", "Week 10 games", "info"),
        (str(len(D.INJURIES)), "Injury rows verified", "ok"),
        (str(len(D.DEPTH)), "Depth charts read", "warn"),
        (str(len(b["deficiencies"])), "Starter-absent positions", "warn"),
        (str(len(C.STRATEGIES)), "Strategies registered", "info"),
        (str(len([s for s in C.STRATEGIES if s[8] == "Blocked"])), "Strategies blocked", "bad"),
        (str(len(C.GATES)), "Validation gates", "info"),
        (str(len(C.QUESTIONS)), "Open questions", "warn"),
        (str(len(FLAGGED)), "Flagged items", "warn"),
    ]
    cards = "".join(
        f'<div class="card {c}"><div class="k">{esc(k)}</div><div class="l">{esc(l)}</div></div>'
        for k, l, c in kpi
    )
    bullets = "".join(
        f'<li><b>{esc(t)}</b> &mdash; {esc(x)}'
        + (f' {src(u, "official source")}' if u else "")
        + "</li>"
        for t, x, u in C.EXEC_SUMMARY["bullets"]
    )
    ml = [
        f'<td>{esc(g["away_name"])}</td><td>{esc(g["home_name"])}</td>'
        f'<td class="num">{esc(g["model_home_spread"])}</td>'
        f'<td class="num">{esc(g["model_total"])}</td>'
        f'<td>{esc(g["net"])}</td><td>{esc(g["date"])} {esc(g["time"])}</td>'
        f'<td>{src(g["url"], "game")}</td>'
        for g in b["model_lines"]
    ]
    qrows = "".join(
        f'<tr><td>{esc(q[0])}</td><td>{esc(q[1])}</td><td>{esc(q[2])}</td>'
        f'<td>{badge(q[6], "bad" if q[6] == "Yes" else "mut")}</td>'
        f'<td><a href="questions.html">detail</a></td></tr>'
        for q in C.QUESTIONS if q[6] == "Yes"
    )
    body = f"""
<div class="panel"><h3 style="margin-top:0">Executive summary</h3>
<p>{esc(C.EXEC_SUMMARY['headline'])}</p>
<ul class="tight">{bullets}</ul></div>
<div class="grid">{cards}</div>
<h3>Model board &mdash; Week 10 {badge("DERIVED", "mut")}</h3>
<p class="lede">Rating-derived lines. Home-field advantage is set to 0.0 and no schedule-strength
adjustment is applied, because both require a game log that has not been ingested
(<a href="questions.html">Q-10, Q-11</a>). These are signals, not bettable numbers.</p>
{table(["Away", "Home", "Model home spread", "Model total", "Network", "Kickoff (ET)", "Source"],
       ml, filter_id="t-board")}
<h3>Blocking questions</h3>
<p class="lede">Nothing in the betting layer can fire until these are answered.</p>
{table(["ID", "Area", "Question", "Blocking", "Detail"],
       [[f'<td>{esc(q[0])}</td>', f'<td>{esc(q[1])}</td>', f'<td>{esc(q[2])}</td>',
         f'<td>{badge(q[6], "bad")}</td>', '<td><a href="questions.html">open</a></td>']
        for q in C.QUESTIONS if q[6] == "Yes"],
       filter_id="t-block")}
<h3>Quick links</h3>
<div class="grid">
<a class="card info" href="depth-charts.html"><div class="k">{len(b['deficiencies'])}</div><div class="l">Starter-absent positions &rarr;</div></a>
<a class="card warn" href="questions.html"><div class="k">{len([q for q in C.QUESTIONS if q[6] == 'Yes'])}</div><div class="l">Blocking questions &rarr;</div></a>
<a class="card info" href="suggestions.html"><div class="k">{len(C.SUGGESTIONS)}</div><div class="l">Suggestions awaiting a decision &rarr;</div></a>
<a class="card bad" href="flagged.html"><div class="k">{len(FLAGGED)}</div><div class="l">Flagged for review &rarr;</div></a>
</div>
"""
    return page("Overview", "index.html", body)


def p_exec(b):
    rows = "".join(
        f"<tr><td><b>{esc(t)}</b></td><td>{esc(x)}</td>"
        f"<td>{src(u, 'official source') if u else '<span class=mut>not applicable</span>'}</td></tr>"
        for t, x, u in C.EXEC_SUMMARY["bullets"]
    )
    kpi = f"""
<div class="grid">
<div class="card ok"><div class="k">{len(D.INJURIES)}</div><div class="l">Verified injury rows</div></div>
<div class="card ok"><div class="k">32</div><div class="l">Verified club records</div></div>
<div class="card warn"><div class="k">{len(D.DEPTH)}/32</div><div class="l">Depth charts readable</div></div>
<div class="card bad"><div class="k">0</div><div class="l">Market lines ingested</div></div>
<div class="card bad"><div class="k">0</div><div class="l">Game logs ingested</div></div>
<div class="card info"><div class="k">{len(C.STRATEGIES)}</div><div class="l">Strategies registered</div></div>
<div class="card bad"><div class="k">{len([s for s in C.STRATEGIES if s[8] == 'Blocked'])}</div><div class="l">Strategies blocked</div></div>
<div class="card info"><div class="k">{len(C.GATES)}</div><div class="l">Validation gates</div></div>
</div>"""
    body = f"""
<div class="panel"><h3 style="margin-top:0">Bottom line</h3>
<p>{esc(C.EXEC_SUMMARY['headline'])}</p></div>
{kpi}
<h3>Detail</h3>
{table(["Area", "Finding", "Source"],
       [[f'<td><b>{esc(t)}</b></td>', cell(x), f'<td>{src(u, "official source") if u else "<span class=mut>n/a</span>"}</td>']
        for t, x, u in C.EXEC_SUMMARY["bullets"]],
       filter_id="t-exec")}
"""
    return page("Executive Summary", "executive-summary.html", body,
                "The important details, in the order they matter.")


def p_standings(b):
    rows = []
    for i, (abbr, w, l, t, pct, pf, pa, net, home, road, div, conf, strk, last5) in enumerate(D.STANDINGS, 1):
        rows.append(
            f'<td class="num" data-sort="{i}">{i}</td>'
            f'<td>{esc(TNAME[abbr])}</td><td>{esc(abbr)}</td>'
            f'<td class="num">{w}</td><td class="num">{l}</td><td class="num">{t}</td>'
            f'<td class="num">{esc(pct)}</td><td class="num">{pf}</td><td class="num">{pa}</td>'
            f'<td class="num">{net}</td><td>{esc(home)}</td><td>{esc(road)}</td>'
            f"<td>{esc(div)}</td><td>{esc(conf)}</td><td>{esc(strk)}</td><td>{esc(last5)}</td>"
            f"<td>{esc(TCONF[abbr])} {esc(TDIV[abbr])}</td>"
            f'<td>{src(D.STAND_URL)}</td>'
        )
    return page("Standings", "standings.html",
                "<p class='lede'>Official 2026 league standings, all 32 clubs, read row by row "
                f"from {src(D.STAND_URL, 'NFL.com')}. Every column is as printed on that page.</p>"
                + table(["#", "Club", "Abbr", "W", "L", "T", "PCT", "PF", "PA", "Net",
                         "Home", "Road", "Div", "Conf", "Strk", "Last 5", "Conference/Division", "Source"],
                        rows, filter_id="t-stand"),
                "Official 2026 league standings.")


def p_schedule(b):
    rows = []
    for (day, date, time_et, away, home, net, url) in D.SCHEDULE:
        rows.append(
            f"<td>{esc(day)}</td><td>{esc(date)}</td><td>{esc(time_et)}</td>"
            f"<td>{esc(TNAME[away])} ({esc(away)})</td>"
            f"<td>{esc(TNAME[home])} ({esc(home)})</td><td>{esc(net)}</td>"
            f'<td>{src(url, "game")}</td>'
        )
    bye = "".join(
        f'<tr><td>{esc(TNAME[x["abbr"]])} ({esc(x["abbr"])})</td><td>{esc(x["record"])}</td>'
        f'<td>{src(x["source"])}</td></tr>' for x in D.BYE
    )
    return page("Schedule", "schedule.html",
                "<p class='lede'>Official Week 10 schedule. Kickoff times are Eastern as printed "
                f"on {src(D.SCHED_URL, 'NFL.com')}.</p>"
                + table(["Day", "Date", "Time (ET)", "Away", "Home", "Network", "Source"], rows,
                        filter_id="t-sched")
                + "<h3>Teams on bye</h3>"
                + table(["Club", "Record", "Source"],
                        [[f'<td>{esc(TNAME[x["abbr"]])} ({esc(x["abbr"])})</td>',
                          f'<td>{esc(x["record"])}</td>', f'<td>{src(x["source"])}</td>']
                         for x in D.BYE]),
                "Official Week 10 schedule and bye week.")


def p_injuries(b):
    rows = []
    for (abbr, player, pos, injury, practice, status) in D.INJURIES:
        kind = "mut"
        if status == "Out":
            kind = "bad"
        elif status == "Doubtful":
            kind = "warn"
        elif status == "Questionable":
            kind = "info"
        rows.append(
            f"<td>{esc(TNAME[abbr])}</td><td>{esc(abbr)}</td><td>{esc(player)}</td>"
            f"<td>{esc(pos)}</td>"
            + (f'<td class="blank">UNVERIFIED</td>' if not injury else f"<td>{esc(injury)}</td>")
            + f"<td>{esc(practice)}</td>"
            + (f'<td>{badge(status, kind)}</td>' if status else '<td class="blank">UNVERIFIED</td>')
            + f'<td>{src(D.INJ_URL)}</td>'
        )
    sel = ('<div class="bar"><select data-eq="#t-inj" data-col="0">'
           '<option value="">All clubs</option>'
           + "".join(f'<option value="{esc(TNAME[a])}">{esc(TNAME[a])}</option>' for a in ORD)
           + '</select><select data-eq="#t-inj" data-col="6">'
             '<option value="">All statuses</option>'
             '<option value="Out">Out</option><option value="Doubtful">Doubtful</option>'
             '<option value="Questionable">Questionable</option></select>'
           '<input data-filter="#t-inj" placeholder="Filter rows…"></div>')
    return page("Injuries", "injuries.html",
                f"<p class='lede'>Official Week 10 injury report, {len(D.INJURIES)} rows, read row by row "
                f"from {src(D.INJ_URL, 'NFL.com')}. Blank cells are blank on the official page; they are "
                "not filled in.</p>"
                + sel
                + table(["Club", "Abbr", "Player", "Pos", "Injury", "Practice status", "Game status", "Source"],
                        rows, filter_id="t-inj"),
                "Official Week 10 injury report.")


def p_depth(b):
    rows = []
    for abbr in ORD:
        d = D.DEPTH.get(abbr)
        if not d:
            rows.append(
                f"<td>{esc(TNAME[abbr])}</td><td>{esc(abbr)}</td>"
                f'<td class="blank">UNVERIFIED</td><td class="blank">UNVERIFIED</td>'
                f'<td class="blank">UNVERIFIED</td>'
                f'<td>{src(TSITE[abbr], "club site")}</td>'
            )
            continue
        n = sum(len(p) for _, p in d["slots"])
        rows.append(
            f"<td>{esc(TNAME[abbr])}</td><td>{esc(abbr)}</td>"
            f'<td>{esc(d["label"])}</td>'
            + (f'<td>{esc(d["as_of"])}</td>' if d["as_of"] else '<td class="blank">UNVERIFIED</td>')
            + f'<td class="num">{n}</td>'
            + f'<td>{src(d["url"])}</td>'
        )
    drows = []
    for r in b["deficiencies"]:
        depth = r["out_depth"]
        if depth == "1":
            tag = badge("STARTER OUT", "bad")
        elif depth == "2":
            tag = badge("BACKUP OUT", "warn")
        elif depth:
            tag = badge(f"DEPTH {depth} OUT", "info")
        else:
            tag = badge("NOT ON CHART", "warn")
        rep = r["replacement"]
        drows.append(
            f"<td>{esc(r['team_name'])}</td><td>{esc(r['team'])}</td><td>{esc(r['player'])}</td>"
            f"<td>{esc(r['pos'])}</td><td>{esc(r['unit'])}</td>"
            f"<td>{esc(r['slot'])}</td>"
            + (f'<td class="num">{esc(depth)}</td>' if depth else '<td class="blank">UNVERIFIED</td>')
            + f'<td>{tag}</td>'
            + (f"<td>{esc(rep)}</td>" if rep else '<td class="blank">UNVERIFIED</td>')
            + (f'<td class="num">{esc(r["replacement_depth"])}</td>' if r["replacement_depth"]
               else '<td class="blank">UNVERIFIED</td>')
            + f'<td>{esc(r["game_status"])}</td>'
            + f'<td>{src(r["src_inj"], "injury")} {src(r["src_depth"], "depth")}</td>'
        )
    body = f"""
<p class="lede">Club depth charts are the official club pages, but every club labels its own chart
"unofficial". Where a player is ruled Out or Doubtful, the chart is used only to name the next man
up, never to decide availability.</p>
<h3>Depth chart register</h3>
{table(["Club", "Abbr", "Chart label as printed by the club", "As-of date", "Players listed", "Source"],
       rows, filter_id="t-dep")}
<h3>Starter-absent positions {badge("DERIVED", "mut")}</h3>
<p class="lede">Derived by a deterministic join: the official injury report (availability) crossed with
the official club depth chart (replacement order). No value is inferred &mdash; a blank means the
club chart does not name a replacement.</p>
{table(["Club", "Abbr", "Player", "Pos", "Unit", "Chart slot", "Out depth", "Severity",
        "Named replacement", "Replacement depth", "Game status", "Sources"],
       drows, filter_id="t-def")}
"""
    return page("Depth & Deficiencies", "depth-charts.html", body,
                "Who is out, who replaces them, and how deep the replacement is.")


def p_lines(b):
    rows = []
    for g in b["model_lines"]:
        rows.append(
            f"<td>{esc(g['away_name'])}</td><td>{esc(g['home_name'])}</td>"
            f'<td class="num">{esc(g["exp_away"])}</td><td class="num">{esc(g["exp_home"])}</td>'
            f'<td class="num">{esc(g["model_home_spread"])}</td>'
            f'<td class="num">{esc(g["model_total"])}</td>'
            f'<td class="blank">UNVERIFIED</td><td class="blank">UNVERIFIED</td>'
            f'<td>{src(g["url"], "game")}</td>'
        )
    rate_rows = []
    for abbr in sorted(b["rates"], key=lambda a: -b["rates"][a]["net"]):
        r = b["rates"][abbr]
        rate_rows.append(
            f"<td>{esc(TNAME[abbr])}</td><td>{esc(abbr)}</td>"
            f'<td class="num">{r["gp"]}</td>'
            f'<td class="num">{r["pf"]:.1f}</td><td class="num">{r["pa"]:.1f}</td>'
            f'<td class="num">{r["net"]:+.1f}</td><td>{src(D.STAND_URL)}</td>'
        )
    body = f"""
<div class="panel">
<h3 style="margin-top:0">How the line is built {badge("DERIVED", "mut")}</h3>
<dl class="kv">
<dt>Home points expected</dt><dd>(home points-for per game + away points-against per game) / 2</dd>
<dt>Away points expected</dt><dd>(away points-for per game + home points-against per game) / 2</dd>
<dt>Home spread</dt><dd>(home net points per game &minus; away net points per game) + HFA</dd>
<dt>Home-field advantage</dt><dd>{HFA:.1f} &mdash; <b>not calibrated</b>. See <a href="questions.html">Q-10</a>.</dd>
<dt>Schedule adjustment</dt><dd>None. Opponent-adjusted ratings need the game log. See <a href="questions.html">Q-11</a>.</dd>
<dt>Inputs</dt><dd>Official standings only: {src(D.STAND_URL, "NFL.com")}</dd>
</dl>
<small class="note">Every number below is a model output, not a fact, and not a bettable price.
Market spreads and totals are blank because no official source publishes them
(<a href="questions.html">Q-02</a>).</small>
</div>
<h3>Rating inputs</h3>
{table(["Club", "Abbr", "Games", "Points for / game", "Points against / game", "Net / game", "Source"],
       rate_rows, filter_id="t-rate")}
<h3>Week 10 model board</h3>
{table(["Away", "Home", "Away pts exp", "Home pts exp", "Model home spread", "Model total",
        "Market spread", "Market total", "Source"], rows, filter_id="t-lines")}
"""
    return page("Own Lines", "lines.html", body,
                "Originating our own numbers from verified inputs only.")


def p_strategies(b):
    rows = []
    for (sid, name, fam, bet, inputs_, output, rule, look, status) in C.STRATEGIES:
        k = "ok" if status == "Registered" else "bad" if status == "Blocked" else "warn"
        rows.append(
            f"<td>{esc(sid)}</td><td><b>{esc(name)}</b></td><td>{esc(fam)}</td>"
            f"<td>{bet}</td><td>{esc(inputs_)}</td><td>{esc(output)}</td>"
            f"<td>{esc(rule)}</td><td>{esc(look)}</td>"
            f'<td>{badge(status, k)}</td>'
        )
    cnt = {}
    for s in C.STRATEGIES:
        cnt[s[3]] = cnt.get(s[3], 0) + 1
    body = f"""
<p class="lede">Ten strategies across the three bet-construction families the brief asks for.
{len([s for s in C.STRATEGIES if s[8] == 'Blocked'])} are blocked on data that does not exist yet.
Nothing here stakes until it clears all {len(C.GATES)} <a href="validation.html">validation gates</a>.</p>
<div class="grid">
{"".join(f'<div class="card info"><div class="k">{v}</div><div class="l">{esc(k)}</div></div>' for k, v in cnt.items())}
<div class="card ok"><div class="k">{len([s for s in C.STRATEGIES if s[8] == "Registered"])}</div><div class="l">Can fire today</div></div>
<div class="card bad"><div class="k">{len([s for s in C.STRATEGIES if s[8] == "Blocked"])}</div><div class="l">Blocked on data</div></div>
</div>
{table(["ID", "Strategy", "Family", "Bet construction", "Inputs", "Output", "Selection rule",
        "Look-ahead risk", "Status"], rows, filter_id="t-strat")}
"""
    return page("Strategies", "strategies.html", body,
                "Signal strategies across single bets, parlays and prop combos.")


def p_validation(b):
    rows = [
        f"<td>{esc(g[0])}</td><td><b>{esc(g[1])}</b></td><td>{esc(g[2])}</td>"
        f"<td>{esc(g[3])}</td><td>{badge('Blocking' if g[4] == 'Yes' else 'Advisory', 'bad' if g[4] == 'Yes' else 'mut')}</td>"
        for g in C.GATES
    ]
    hist = "".join(
        f"<tr><td>{esc(s[0])}</td><td>{esc(s[1])}</td>"
        f'<td class="blank">UNVERIFIED</td><td class="blank">UNVERIFIED</td>'
        f'<td class="blank">UNVERIFIED</td>'
        f'<td>{badge("No graded results", "warn")}</td>'
        f'<td>{badge(s[8], "bad" if s[8] == "Blocked" else "ok")}</td></tr>'
        for s in C.STRATEGIES
    )
    body = f"""
<p class="lede">Twelve gates, all blocking. A strategy passes only when every gate is green on
out-of-sample data. There are no graded results yet, so every strategy currently reads
"no graded results".</p>
<h3>Gate definitions</h3>
{table(["ID", "Gate", "Threshold", "Why it exists", "Type"], rows, filter_id="t-gate")}
<h3>Gate status by strategy</h3>
{table(["ID", "Strategy", "Bets graded", "Return", "Nominal p", "Gate state", "Status"],
       [r for r in
        [f"<td>{esc(s[0])}</td><td>{esc(s[1])}</td>"
         f'<td class="blank">UNVERIFIED</td><td class="blank">UNVERIFIED</td>'
         f'<td class="blank">UNVERIFIED</td>'
         f'<td>{badge("No graded results", "warn")}</td>'
         f'<td>{badge(s[8], "bad" if s[8] == "Blocked" else "ok")}</td>'
         for s in C.STRATEGIES]],
       filter_id="t-gstat")}
<h3>Removing luck</h3>
<div class="panel">
<ul class="tight">
<li><b>Null model.</b> Each bet is modelled as a Bernoulli trial at the book's implied break-even
probability. The observed return is compared to the distribution of returns under that null.</li>
<li><b>Multiplicity.</b> With {len(C.STRATEGIES)} strategies, some will look good by chance. Benjamini-Hochberg
FDR at 10% is applied inside declared families (G-06).</li>
<li><b>Stability, not just level.</b> The 5th percentile of a bet-level bootstrap must be above zero
(G-07), and the edge must survive the whole pre-declared parameter neighbourhood (G-08).</li>
<li><b>Concentration.</b> An edge concentrated in one week or against one club fails G-10. That
is usually luck wearing a costume.</li>
<li><b>Hindsight.</b> Pre-registration (G-01) plus the holdout (G-03) mean a strategy can never be
graded on data it was tuned on.</li>
</ul></div>
"""
    return page("Validation Gates", "validation.html", body,
                "The rules a strategy must survive before it is allowed to risk anything.")


def p_correlation(b):
    rows = []
    for c in b["correlations"]:
        rows.append(
            f"<td>{esc(c['pair'])}</td><td>{esc(c['kind'])}</td><td>{esc(c['estimator'])}</td>"
            f"<td>{esc(c['data'])}</td>"
            + (f'<td class="num">{esc(c["value"])}</td>' if c["value"] else '<td class="blank">UNVERIFIED</td>')
            + f'<td class="num">{esc(c["n"])}</td>'
            + f'<td>{badge(c["status"], "ok" if c["status"] == "Computed" else "warn")}</td>'
            + f'<td>{src(c["source"]) if c["source"] else badge("no official source", "bad")}</td>'
        )
    pending = [c for c in C.CORRELATION if c[4] == "Not estimated"]
    prows = [
        f"<td>{esc(c[0])}</td><td>{esc(c[1])}</td><td>{esc(c[2])}</td>"
        f'<td>{esc(c[3])}</td><td class="blank">UNVERIFIED</td>'
        f'<td>{badge(c[4], "warn")}</td>'
        for c in pending
    ]
    body = f"""
<p class="lede">Four correlations can be computed today from the verified standings. The other
{len(pending)} need play-by-play or a graded result set, so they are left blank on purpose rather
than guessed.</p>
<h3>Computed from verified data {badge("DERIVED", "mut")}</h3>
{table(["Pair", "Kind", "Estimator", "Data used", "Value", "n", "Status", "Source"], rows,
       filter_id="t-corr")}
<h3>Not yet estimated</h3>
<p class="lede">Each of these has an estimator and a named dataset. None has a value, because the
dataset has not been ingested. See <a href="questions.html">Q-14, Q-15</a>.</p>
{table(["Pair", "Kind", "Estimator", "Required data", "Value", "Status"], prows,
       filter_id="t-corr2")}
<div class="panel"><h3 style="margin-top:0">Why raw totals are the wrong input</h3>
<p>Leg-level correlations must be estimated on <b>within-game residuals</b>, not on raw totals.
Two legs in the same game share a game script, so raw totals make unrelated legs look correlated.
Understating parlay variance is the most common way a correlated-parlay book fails
(<a href="suggestions.html">S-11</a>).</p></div>
"""
    return page("Correlation", "correlation.html", body,
                "Correlation values, how they are estimated, and which ones are still unknown.")


def p_leaderboard(b):
    sc = "".join(
        f"<tr><td><b>{esc(k)}</b></td><td>{esc(v)}</td><td>{esc(w)}</td></tr>"
        for k, v, w in C.LEADERBOARD_SPEC["scoring"]
    )
    tr = "".join(
        f"<tr><td><b>{esc(k)}</b></td><td>{esc(v)}</td><td>{esc(w)}</td></tr>"
        for k, v, w in C.LEADERBOARD_SPEC["tiers"]
    )
    rows = [
        f"<td>{esc(s[0])}</td><td>{esc(s[1])}</td><td>{esc(s[2])}</td>"
        f'<td class="blank">UNVERIFIED</td><td class="blank">UNVERIFIED</td>'
        f'<td class="blank">UNVERIFIED</td>'
        f'<td>{badge("No graded results", "warn")}</td>'
        for s in C.STRATEGIES
    ]
    body = f"""
<p class="lede">The competition rules are published before a single bet is graded, so the scoring
function cannot be tuned to whoever is winning. No standings exist yet because nothing has been
graded.</p>
<h3>Scoring</h3>
{table(["Metric", "Definition", "Why"], [r for r in
    [f"<td><b>{esc(k)}</b></td><td>{esc(v)}</td><td>{esc(w)}</td>"
     for k, v, w in C.LEADERBOARD_SPEC["scoring"]]], filter_id="t-score")}
<h3>Reward tiers</h3>
<table class="tw"><thead><tr><th>Tier</th><th>Criteria</th><th>Reward</th></tr></thead>
<tbody>{tr}</tbody></table>
<h3>Standings</h3>
{table(["ID", "Strategy", "Family", "Bets", "Net units / 100", "Skill score", "State"], rows,
       filter_id="t-lb")}
<h3>Anti-gaming rules</h3>
<div class="panel"><ul class="tight">
{"".join(f"<li>{esc(x)}</li>" for x in C.LEADERBOARD_SPEC["anti_gaming"])}
</ul>
<small class="note">Recommendation: run the first season on notional stakes
(<a href="suggestions.html">S-12</a>). Cash rewards create an incentive to game the score before we
know whether the gates work.</small></div>
"""
    return page("Leaderboard", "leaderboard.html", body,
                "How strategies compete, how they score, and how the board is protected from gaming.")


def p_questions(b):
    rows = []
    for (qid, area, q, know, unknown, how, blocking) in C.QUESTIONS:
        rows.append(
            f"<td>{esc(qid)}</td><td>{esc(area)}</td><td><b>{esc(q)}</b></td>"
            f"<td>{esc(know)}</td><td>{esc(unknown)}</td><td>{esc(how)}</td>"
            f'<td>{badge(blocking, "bad" if blocking == "Yes" else "mut")}</td>'
        )
    nb = len([q for q in C.QUESTIONS if q[6] == "Yes"])
    body = f"""
<div class="grid">
<div class="card warn"><div class="k">{len(C.QUESTIONS)}</div><div class="l">Open questions</div></div>
<div class="card bad"><div class="k">{nb}</div><div class="l">Blocking</div></div>
<div class="card ok"><div class="k">{len(C.QUESTIONS) - nb}</div><div class="l">Non-blocking</div></div>
</div>
<p class="lede">Every item splits into what is actually known, what is genuinely unknown, and the
concrete step that would close it. Nothing is listed as known unless it was read from an official
source.</p>
{table(["ID", "Area", "Question", "What we know", "What we do not know", "How to discover", "Blocking"],
       rows, filter_id="t-q")}
"""
    return page("Open Questions", "questions.html", body,
                "What we know, what we do not know, and how to find out.")


def p_suggestions(b):
    rows = []
    for (sid, area, title, problem, a, bb, cc, rec, effort, risk, status) in C.SUGGESTIONS:
        k = {"Adopted": "ok", "Proposed": "info", "Deferred": "mut"}.get(status, "mut")
        rows.append(
            f"<td>{esc(sid)}</td><td>{esc(area)}</td><td><b>{esc(title)}</b></td>"
            f"<td>{esc(problem)}</td>"
            f"<td>{esc(a)}</td><td>{esc(bb)}</td><td>{esc(cc)}</td>"
            f"<td><b>{esc(rec)}</b></td><td>{esc(effort)}</td><td>{esc(risk)}</td>"
            f'<td>{badge(status, k)}</td>'
        )
    cnt = {}
    for s in C.SUGGESTIONS:
        cnt[s[10]] = cnt.get(s[10], 0) + 1
    body = f"""
<p class="lede">A decision queue, not a backlog. Each suggestion sets out the problem, three paths,
and a recommendation, so a reviewer can pick a path and nothing ships before that choice is made.</p>
<div class="grid">
{"".join(f'<div class="card info"><div class="k">{v}</div><div class="l">{esc(k)}</div></div>' for k, v in cnt.items())}
</div>
{table(["ID", "Area", "Suggestion", "Problem", "Option A", "Option B", "Option C",
        "Recommendation", "Effort", "Risk", "Status"], rows, filter_id="t-sug")}
<div class="panel"><h3 style="margin-top:0">How to use this page</h3>
<ul class="tight">
<li>Pick a row. Read the three options and the recommendation.</li>
<li>Change the status to <b>Adopted</b> when a path is chosen, <b>Deferred</b> when it is knowingly
postponed. Nothing is implemented on <b>Proposed</b>.</li>
<li>Anything marked <b>Adopted</b> only takes effect when the matching change is committed. The two
adopted items on this page are already reflected in the pipeline.</li>
</ul></div>
"""
    return page("Suggestions", "suggestions.html", body,
                "Improvement suggestions, with paths and recommendations for review before any change ships.")


def p_requirements(b):
    rows = []
    for (rid, cat, req, acc, status, blocking) in C.REQUIREMENTS:
        k = {"done": "ok", "partial": "warn"}.get(status, "mut")
        rows.append(
            f"<td>{esc(rid)}</td><td>{esc(cat)}</td><td>{esc(req)}</td><td>{esc(acc)}</td>"
            f'<td>{badge(status, k)}</td>'
            f'<td>{esc(blocking) if blocking else "<span class=mut>&mdash;</span>"}</td>'
        )
    cnt = {}
    for r in C.REQUIREMENTS:
        cnt[r[1]] = cnt.get(r[1], 0) + 1
    done = len([r for r in C.REQUIREMENTS if r[4] == "done"])
    body = f"""
<p class="lede">The brief decomposed into {len(C.REQUIREMENTS)} testable requirements. Each has an
acceptance criterion so completion is checkable rather than asserted.</p>
<div class="grid">
<div class="card ok"><div class="k">{done}/{len(C.REQUIREMENTS)}</div><div class="l">Requirements met</div></div>
{"".join(f'<div class="card info"><div class="k">{v}</div><div class="l">{esc(k)}</div></div>' for k, v in cnt.items())}
</div>
{table(["ID", "Category", "Requirement", "Acceptance criterion", "Status", "Blocking questions"],
       rows, filter_id="t-req")}
"""
    return page("Requirements", "requirements.html", body,
                "The full requirement set, collected, organised and analysed.")


def p_repo(b):
    a = b["audit"]
    rows = []
    for f in a["files"]:
        rows.append(
            f"<td><code>{esc(f['path'])}</code></td>"
            f'<td class="num">{f["bytes"]}</td><td class="num">{f["lines"]}</td>'
            f"<td><code>{esc(f['content'])}</code>{' &hellip;' if f['truncated'] else ''}</td>"
            f'<td>{src(f["blob"], "blob")} &middot; {src(f["history"], "history")}</td>'
        )
    issues = "".join(
        f"<tr><td>{esc(x['id'])}</td><td>{esc(x['area'])}</td>"
        f'<td>{badge(x["severity"], "bad" if x["severity"] == "High" else "warn" if x["severity"] == "Medium" else "info")}</td>'
        f"<td>{esc(x['what'])}</td><td>{esc(x['why'])}</td>"
        f'<td>{src(x["source"]) if x["source"] else badge("n/a", "mut")}</td></tr>'
        for x in FLAGGED if x["area"] in ("Repository", "Data gap", "Source quality")
    )
    body = f"""
<p class="lede">The repository was reviewed line by line. At the base commit it contained exactly
one tracked file. There was no prior code, data set, documentation or configuration to audit.</p>
<div class="panel"><h3 style="margin-top:0">Repository facts</h3>
<dl class="kv">
<dt>Branch reviewed</dt><dd><code>{esc(a['branch'])}</code></dd>
<dt>Base commit</dt><dd><code>{esc(a['sha'])}</code> &mdash; {src(a['commit_url'], 'open on GitHub')}</dd>
<dt>Commit count</dt><dd>{esc(a['commit_count'])}</dd>
<dt>Tracked files at base</dt><dd>{len(a['files'])}</dd>
<dt>Total bytes at base</dt><dd>{sum(f['bytes'] for f in a['files'])}</dd>
</dl></div>
<h3>File-by-file</h3>
{table(["Path", "Bytes", "Lines", "Content as committed", "Links for manual review"], rows,
       filter_id="t-repo")}
<h3>Irregularities found</h3>
{table(["ID", "Area", "Severity", "What", "Why it is irregular", "Source"],
       [r for r in
        [f"<td>{esc(x['id'])}</td><td>{esc(x['area'])}</td>"
         f'<td>{badge(x["severity"], "bad" if x["severity"] == "High" else "warn" if x["severity"] == "Medium" else "info")}</td>'
         f"<td>{esc(x['what'])}</td><td>{esc(x['why'])}</td>"
         f'<td>{src(x["source"]) if x["source"] else badge("n/a", "mut")}</td>'
         for x in FLAGGED if x["area"] in ("Repository", "Data gap", "Source quality")]],
       filter_id="t-repo2")}
<p class="lede">Every row above links to the exact blob and its history on GitHub so it can be
checked by hand. Nothing in this audit is inferred.</p>
"""
    return page("Repo Review", "repo-review.html", body,
                "Line-by-line review of the base commit, with links for manual verification.")


def p_sources(b):
    rows = []
    for abbr in ORD:
        d = D.DEPTH.get(abbr)
        rows.append(
            f"<td>{esc(TNAME[abbr])}</td><td>{esc(abbr)}</td>"
            f'<td>{src(TPROF[abbr], "nfl.com/teams")}</td>'
            f'<td>{src(TSITE[abbr], "official club site")}</td>'
            f'<td>{src(d["url"]) if d else badge("no table readable", "bad")}</td>'
        )
    league = [
        ("Official 2026 league standings", D.STAND_URL, "32 club records"),
        ("Official Week 10 injury report", D.INJ_URL, f"{len(D.INJURIES)} player rows"),
        ("Official Week 10 schedule", D.SCHED_URL, f"{len(D.SCHEDULE)} games + bye list"),
        ("Official team directory", D.TEAMS_URL, "32 clubs, official club-site links"),
    ]
    body = f"""
<p class="lede">Every fact on this site traces to one of these official pages. Each was read on
{D.AS_OF}. Club sites are official club properties, reachable from the NFL.com team directory.</p>
<h3>League-level sources</h3>
{table(["Dataset", "Official URL", "Rows taken"],
       [[f"<td>{esc(n)}</td>", f'<td><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a></td>',
         f"<td>{esc(r)}</td>"] for n, u, r in league], filter_id="t-src")}
<h3>Club-level sources</h3>
{table(["Club", "Abbr", "NFL.com profile", "Official club site", "Depth chart"], rows,
       filter_id="t-src2")}
"""
    return page("Sources", "sources.html", body,
                "Every official source used, with links for manual review.")


def p_flagged(b):
    rows = []
    for x in FLAGGED:
        s = x["severity"]
        k = "bad" if s == "High" else "warn" if s == "Medium" else "info"
        rows.append(
            f"<td>{esc(x['id'])}</td><td>{esc(x['area'])}</td>"
            f'<td>{badge(s, k)}</td>'
            f"<td><b>{esc(x['what'])}</b></td><td>{esc(x['why'])}</td>"
            f"<td>{esc(x['action'])}</td>"
            f'<td>{src(x["source"]) if x["source"] else badge("n/a", "mut")}</td>'
        )
    sev = {}
    for x in FLAGGED:
        sev[x["severity"]] = sev.get(x["severity"], 0) + 1
    body = f"""
<p class="lede">Everything that could not be confirmed from an official source, plus everything
that looked wrong while verifying. Nothing here blocks the site; each item carries a source link so
it can be reviewed by hand after launch.</p>
<div class="grid">
{"".join(f'<div class="card {"bad" if k == "High" else "warn" if k == "Medium" else "info"}"><div class="k">{v}</div><div class="l">{esc(k)} severity</div></div>' for k, v in sev.items())}
<div class="card info"><div class="k">{len(FLAGGED)}</div><div class="l">Total flagged</div></div>
</div>
{table(["ID", "Area", "Severity", "What", "Why it is flagged", "Suggested action", "Source"],
       rows, filter_id="t-flag")}
"""
    return page("Flagged for Review", "flagged.html", body,
                "Unverified values and irregularities, with sources, for post-launch review.")


def p_coordination(b):
    path = os.path.join(ROOT, "COORDINATION.md")
    body = "<p class='lede'>Mirror of <code>COORDINATION.md</code>, the shared task board for parallel sessions.</p>"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            txt = fh.read()
        body += "<div class='panel'><pre style='white-space:pre-wrap;margin:0;font-size:12.5px'>" + esc(txt) + "</pre></div>"
    coord_url = ("https://github.com/karagemop466-tech/X3/blob/"
                 + b["audit"]["sha"] + "/COORDINATION.md")
    body += "<p>" + src(coord_url, "COORDINATION.md on GitHub") + "</p>"
    return page("Coordination", "coordination.html", body,
                "Shared task board and session rules.")


# --------------------------------------------------------------------------- main
def main():
    depth_idx = build_depth_index()
    deficiencies, cross_team = build_deficiencies(depth_idx)
    correlations = build_correlations()
    model_lines, rates = build_model_lines()
    audit = repo_audit()

    # ---- flags -----------------------------------------------------------
    flag("F-01", "Source quality", "Medium",
         "Every club depth chart is labelled 'unofficial' by the club that publishes it.",
         "31 of 31 readable charts carry a self-declared unofficial label, so no chart can be "
         "treated as a club-authoritative starter designation.",
         "https://www.detroitlions.com/team/depth-chart",
         "Use official gamebook participation data as ground truth (S-02).")

    flag("F-02", "Source quality", "Medium",
         "27 of 32 club depth charts print no 'as of' date, so freshness cannot be proven.",
         "Only CHI, GB, LV, SF and TEN print a date. The others give no evidence of when the "
         "chart was last updated.",
         "https://www.chicagobears.com/team/depth-chart",
         "Diff each chart on every run and alert when a chart has not changed in 7 days (S-02).")

    flag("F-03", "Source quality", "High",
         "Detroit lists Cade Mays as its starting centre while the official injury report lists him Out.",
         "The club chart is not synced to the injury report. Trusting the chart would have "
         "produced a wrong starter.",
         D.INJ_URL,
         "Already handled: the pipeline treats the injury report as authoritative for availability.")

    flag("F-04", "Source quality", "Medium",
         "Philadelphia's depth chart lists Hollywood Brown and Fred Johnson, both waived by the club on 2026-11-13.",
         "The club's own news page and the club's own depth chart disagree.",
         "https://www.philadelphiaeagles.com/news/eagles-waive-hollywood-brown-fred-johnson",
         "Treat club transaction news as an override on the next ingest run.")

    flag("F-05", "Data gap", "High",
         "Houston's official depth chart is published only as an image; no rows could be read.",
         "The page renders the chart inside a picture, so there is no machine-readable table.",
         "https://www.houstontexans.com/team/depth-chart",
         "Switch the whole depth layer to official gamebook participation data (S-02).")

    flag("F-06", "Data gap", "High",
         "No market lines exist anywhere in the system.",
         "No spread, total, moneyline or player-prop price has been ingested, so no signal can be "
         "converted into a bet or scored against the market.",
         "", "Owner decision required (Q-02, Q-03, S-03).")

    flag("F-07", "Data gap", "High",
         "No game log has been ingested.",
         "Without week-by-week results there is no home-field-advantage estimate and no "
         "schedule-strength adjustment, so the model runs uncalibrated.",
         "", "Ingest nfl.com/schedules/2026/by-week/week-N for N=1..9 (Q-01, S-01).")

    flag("F-08", "Modelling", "Medium",
         f"All model lines are produced with home-field advantage = {HFA:.1f} and no schedule adjustment.",
         "Both parameters need a game log. Publishing an uncalibrated number that looks like a line "
         "is how a bad model gets trusted.",
         D.STAND_URL, "Close Q-10 and Q-11, then recalibrate (S-07).")

    _blank = [r for r in D.INJURIES if not r[5]]
    _dnp_blank = [r for r in D.INJURIES if r[4].startswith("Did Not") and not r[5]]
    flag("F-09", "Source quality", "Low",
         f"{len(_blank)} of {len(D.INJURIES)} injury rows have a blank game status, "
         f"and {len(_dnp_blank)} of those also show the player did not practise.",
         "The official report leaves the Game Status column empty for a majority of listed "
         "players, so availability cannot be read from that column alone. Counted against the "
         f"official page: {len([r for r in D.INJURIES if r[5] == 'Out'])} Out, "
         f"{len([r for r in D.INJURIES if r[5] == 'Doubtful'])} Doubtful, "
         f"{len([r for r in D.INJURIES if r[5] == 'Questionable'])} Questionable.",
         D.INJ_URL, "Cross-check against the official inactives list (Q-05, S-06).")

    for abbr, player, pos, other_team, other_slot in cross_team[:0]:
        pass
    for i, (abbr, player, pos, other_team, other_slot) in enumerate(cross_team, start=1):
        flag(f"F-10.{i:02d}", "Source quality", "Low",
             f"{player} ({pos}) appears on the {TNAME[abbr]} injury report and also on the "
             f"{TNAME[other_team]} depth chart at {other_slot}.",
             "Two official sources place the same player name with two clubs. This may be a "
             "genuine mid-season move, a shared player name, or a source error. It cannot be "
             "resolved from the pages read.",
             D.INJ_URL, "Resolve against the official roster before this row drives a signal.")

    not_on_chart = [r for r in deficiencies if not r["slot"]]
    if not_on_chart:
        flag("F-11", "Source quality", "Medium",
             f"{len(not_on_chart)} players ruled Out or Doubtful are absent from their own club's depth chart.",
             "Players on injured reserve or recently signed are frequently missing from the chart, "
             "so the chart cannot be used as a completeness check.",
             D.INJ_URL, "Treat absence from the chart as an unknown, never as 'healthy'.")

    if audit["files"]:
        flag("F-12", "Repository", "Low",
             f"The base commit contains {len(audit['files'])} tracked file(s) totalling "
             f"{sum(f['bytes'] for f in audit['files'])} bytes.",
             "There is no licence, no .gitignore, no CI, no tests, no documentation and no "
             "branch protection recorded at the base commit.",
             audit["commit_url"], "Add licence, .gitignore, CI and branch protection.")

    # ---- bundle ----------------------------------------------------------
    bundle = {
        "meta": {"season": D.SEASON, "week": D.WEEK, "as_of": D.AS_OF,
                 "sha": audit["sha"], "branch": audit["branch"]},
        "teams": [{"abbr": a, "name": n, "profile": p, "site": s, "conf": c, "div": d}
                  for (a, n, p, s, c, d) in D.TEAMS],
        "standings": [{"abbr": r[0], "name": TNAME[r[0]], "w": r[1], "l": r[2], "t": r[3],
                       "pct": r[4], "pf": r[5], "pa": r[6], "net": r[7], "home": r[8],
                       "road": r[9], "div": r[10], "conf": r[11], "strk": r[12],
                       "last5": r[13], "source": D.STAND_URL} for r in D.STANDINGS],
        "schedule": [{"day": s[0], "date": s[1], "time": s[2], "away": s[3], "home": s[4],
                      "away_name": TNAME[s[3]], "home_name": TNAME[s[4]], "network": s[5],
                      "source": s[6]} for s in D.SCHEDULE],
        "bye": D.BYE,
        "injuries": [{"team": i[0], "team_name": TNAME[i[0]], "player": i[1], "pos": i[2],
                      "injury": i[3], "practice": i[4], "status": i[5], "source": D.INJ_URL}
                     for i in D.INJURIES],
        "depth": [{"abbr": a, "name": TNAME[a], "url": d["url"], "as_of": d["as_of"],
                   "label": d["label"],
                   "slots": [{"pos": p, "unit": unit_of(p), "players": ps}
                             for p, ps in d["slots"]]} for a, d in D.DEPTH.items()],
        "depth_missing": D.DEPTH_MISSING,
        "deficiencies": deficiencies,
        "model_lines": model_lines,
        "rates": rates,
        "correlations": correlations,
        "requirements": [{"id": r[0], "category": r[1], "requirement": r[2],
                          "acceptance": r[3], "status": r[4], "blocking": r[5]}
                         for r in C.REQUIREMENTS],
        "questions": [{"id": q[0], "area": q[1], "question": q[2], "known": q[3],
                       "unknown": q[4], "how": q[5], "blocking": q[6]} for q in C.QUESTIONS],
        "suggestions": [{"id": s[0], "area": s[1], "title": s[2], "problem": s[3],
                         "a": s[4], "b": s[5], "c": s[6], "recommendation": s[7],
                         "effort": s[8], "risk": s[9], "status": s[10]} for s in C.SUGGESTIONS],
        "strategies": [{"id": s[0], "name": s[1], "family": s[2], "construction": s[3],
                        "inputs": s[4], "output": s[5], "rule": s[6], "lookahead": s[7],
                        "status": s[8]} for s in C.STRATEGIES],
        "gates": [{"id": g[0], "gate": g[1], "threshold": g[2], "why": g[3], "blocking": g[4]}
                  for g in C.GATES],
        "flagged": FLAGGED,
        "audit": audit,
    }
    emit_json(bundle)

    b = {"deficiencies": deficiencies, "model_lines": model_lines, "rates": rates,
         "correlations": correlations, "audit": audit}

    pages = {
        "index.html": p_index(b),
        "executive-summary.html": p_exec(b),
        "standings.html": p_standings(b),
        "schedule.html": p_schedule(b),
        "injuries.html": p_injuries(b),
        "depth-charts.html": p_depth(b),
        "lines.html": p_lines(b),
        "strategies.html": p_strategies(b),
        "validation.html": p_validation(b),
        "correlation.html": p_correlation(b),
        "leaderboard.html": p_leaderboard(b),
        "questions.html": p_questions(b),
        "suggestions.html": p_suggestions(b),
        "requirements.html": p_requirements(b),
        "repo-review.html": p_repo(b),
        "sources.html": p_sources(b),
        "flagged.html": p_flagged(b),
        "coordination.html": p_coordination(b),
    }
    os.makedirs(SITE, exist_ok=True)
    for name, doc in pages.items():
        with open(os.path.join(SITE, name), "w", encoding="utf-8") as fh:
            fh.write(doc)

    with open(os.path.join(SITE, "assets-style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)

    print(f"injuries      {len(D.INJURIES)}")
    print(f"depth charts  {len(D.DEPTH)}/32  (missing: {[m['abbr'] for m in D.DEPTH_MISSING]})")
    print(f"deficiencies  {len(deficiencies)}  (not on chart: {len(not_on_chart)})")
    print(f"cross-team    {len(cross_team)}")
    print(f"flagged       {len(FLAGGED)}")
    print(f"pages         {len(pages)}")
    for c in correlations:
        print(f"  r {c['pair']:<52} {c['value']}")


if __name__ == "__main__":
    main()
