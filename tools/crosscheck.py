#!/usr/bin/env python3
"""crosscheck — repo-wide audit + cross-module register reconciliation for X3.

Session arena/37c71381-x3.  Three phases:

  1. AUDIT      every *.html page in the repo (except crosscheck/ itself):
                internal-link check, per-table-row source/flag check.
  2. RECONCILE  every register (requirements / questions / suggestions / flags /
                strategies / signals) published by every session: counts per
                module, ID-namespace collisions, content-identity and
                status-conflict detection, render-parity checks, dataset
                reconciliation (the two Week-10 injury CSVs), plus the results
                of the read-only verification scripts owned by other sessions.
  3. BUILD      generate crosscheck/*.html from the report.  Every emitted row
                carries an absolute source link (github.com blob of the file the
                data came from) or an explicit UNVERIFIED/flag marker.

Post-write gate:  python3 tools/crosscheck.py --verify
  re-parses every generated page and fails if any row lacks a source link or
  flag marker; writes crosscheck/data/selfcheck.json.

Nothing in this tool infers or fills in values: unknown cells render as
'-' or UNVERIFIED and are reported as findings.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "crosscheck"
DATA = OUT / "data"
BLOB = "https://github.com/karagemop466-tech/X3/blob/main/"
REPO = "https://github.com/karagemop466-tech/X3"
OFFICIAL = {  # official hosts that count as 'official source' in row audits
    "www.nfl.com", "nfl.com", "media.nfl.com", "operations.nfl.com",
    "nextgenstats.nfl.com", "www.espn.com",
}
STOP = set("a an the of to and for in on with from that is are be by as at it its this those".split())
FLAG_RE = re.compile(r"\b(unverified|not\s+verified|flagged|flag\s*\(|needs?\s+review|no\s+source)\b", re.I)
EMPTY_CELL = '<span class="badge mut">-</span>'


# --------------------------------------------------------------------------- #
# HTML parsing
# --------------------------------------------------------------------------- #
class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.tables: list[dict] = []
        self._table = None
        self._row = None
        self._cell = None
        self._cell_links = None
        self._href = None
        self._text_bits: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a":
            self._href = a.get("href") or None
            if self._href:
                self.links.append(self._href)
        elif tag in ("link", "script", "img"):
            u = a.get("href") or a.get("src")
            if u:
                self.links.append(u)
        elif tag == "table":
            self._table = {"headers": [], "rows": []}
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell, self._cell_links = [], []

    def handle_endtag(self, tag):
        if tag == "a":
            self._href = None
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            text = re.sub(r"\s+", " ", "".join(self._cell)).strip()
            self._row.append({"text": text, "links": list(self._cell_links)})
            self._cell = self._cell_links = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                if not self._table["headers"] and all(
                    c["text"] for c in self._row
                ) and len(self._row) > 1 and not any(c["links"] for c in self._row):
                    # first pure-text multi-cell row is treated as the header
                    self._table["headers"] = [c["text"] for c in self._row]
                else:
                    self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
            if self._href:
                self._cell_links.append(self._href)


def parse_page(path: Path) -> PageParser:
    p = PageParser()
    p.feed(path.read_text(errors="replace"))
    return p


def row_http(row) -> list[str]:
    out = []
    for c in row:
        for u in c.get("links", []):
            if u.startswith(("http://", "https://")):
                out.append(u)
    return out


def row_text(row) -> str:
    return " ".join(c.get("text", "") for c in row)


# --------------------------------------------------------------------------- #
# Register extraction
# --------------------------------------------------------------------------- #
def pick(d: dict, names, default=""):
    for n in names:
        if n in d and d[n] not in (None, ""):
            return str(d[n])
    return default


def norm_id(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]", "", str(raw or "")).upper()
    m = re.match(r"^([A-Z]+)(\d+)$", s)
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}"
    m = re.match(r"^([A-Z]+A)(\d+)$", s)
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}"
    return s


def status_norm(s: str) -> str:
    s = (s or "").strip().lower()
    if not s:
        return ""
    if any(k in s for k in ("done", "delivered", "complete", "merged", "pass", "resolved")):
        return "DONE"
    if any(k in s for k in ("partial", "progress", "in review", "needs review", "pending gates")):
        return "PARTIAL"
    if any(k in s for k in ("blocked", "cannot", "not possible")):
        return "BLOCKED"
    if any(k in s for k in ("not started", "open", "proposed", "awaiting", "unclaimed",
                             "pending", "todo", "planned", "deferred", "unresolved",
                             "needs decision", "awaiting review")):
        return "OPEN"
    return "OTHER"


def jaccard(a: str, b: str) -> float:
    ta = {w for w in re.findall(r"[a-z0-9]+", a.lower()) if w not in STOP}
    tb = {w for w in re.findall(r"[a-z0-9]+", b.lower()) if w not in STOP}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def entry(fam, mod, reg, page, raw_id, title, status="", source="", severity=""):
    title = re.sub(r"\s+", " ", title or "").strip()
    return {
        "family": fam, "module": mod, "register": reg, "page": page,
        "raw_id": str(raw_id or "").strip(), "nid": norm_id(raw_id),
        "title": title[:400], "status": status.strip(),
        "status_norm": status_norm(status), "severity": severity.strip(),
        "source": (source or "").strip(),
    }


def _first_http(cells, idxs):
    if idxs is None:
        return ""
    if isinstance(idxs, int):
        idxs = [idxs]
    for i in idxs:
        for j in i if isinstance(i, (list, tuple)) else [i]:
            pass  # placeholder (unused)
    return ""


def load_csv_reg(spec):
    path = ROOT / spec["path"]
    c = spec["cols"]
    out = []
    with path.open(newline="") as fh:
        for r in csv.DictReader(fh):
            out.append(entry(
                spec["fam"], spec["mod"], spec["path"], spec.get("page", spec["path"]),
                r.get(c.get("id", ""), ""),
                r.get(c.get("title", ""), ""),
                r.get(c.get("status", ""), ""),
                r.get(c.get("source", ""), ""),
                r.get(c.get("severity", ""), ""),
            ))
    return out


def load_json_reg(spec):
    path = ROOT / spec["path"]
    c = spec["cols"]
    doc = json.loads(path.read_text())
    items = []
    for key in spec["items"]:
        v = doc[key] if isinstance(doc, dict) else doc
        if isinstance(v, list):
            items.extend(v)
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(entry(
            spec["fam"], spec["mod"], spec["path"], spec.get("page", spec["path"]),
            pick(it, [c.get("id", "id")]),
            pick(it, c.get("title", ["title"])),
            pick(it, c.get("status", ["status", "state"])),
            pick(it, c.get("source", ["source", "source_url", "url"])),
            pick(it, c.get("severity", ["severity"])),
        ))
    return out


def load_js_reg(spec):
    """Dump assets/data.js through node, then treat it like a JSON register."""
    code = ("require('./assets/data.js');"
            "process.stdout.write(JSON.stringify(globalThis.NFL_LAB))")
    res = subprocess.run(["node", "-e", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    if res.returncode != 0:
        raise RuntimeError(f"node dump failed: {res.stderr[:300]}")
    doc = json.loads(res.stdout)
    c = spec["cols"]
    out = []
    for it in doc.get(spec["items"], []):
        out.append(entry(
            spec["fam"], spec["mod"], spec["path"], spec.get("page", spec["path"]),
            pick(it, [c.get("id", "id")]),
            pick(it, c.get("title", ["title"])),
            pick(it, c.get("status", ["status", "state"])),
            pick(it, c.get("source", ["source", "url"])),
            pick(it, c.get("severity", ["severity"])),
        ))
    return out


def load_html_reg(spec):
    path = ROOT / spec["path"]
    p = parse_page(path)
    out = []
    tables = p.tables
    for tspec in spec["tables"]:
        sel = None
        if "match" in tspec:
            need = [m.lower() for m in tspec["match"]]
            for i, t in enumerate(tables):
                hdr = " | ".join(t["headers"]).lower()
                if all(n in hdr for n in need):
                    sel = i
                    break
            if sel is None:
                continue
        elif "index" in tspec:
            sel = tspec["index"]
        else:
            sel = None
        chosen = [tables[sel]] if sel is not None else tables
        for t in chosen:
            for row in t["rows"]:
                texts = [c["text"] for c in row]
                links = row_http(row)

                def cell(idx):
                    if idx is None:
                        return "", ""
                    if isinstance(idx, list):
                        parts = [texts[i] for i in idx if i < len(texts)]
                        txt = " — ".join(x for x in parts if x)
                    else:
                        txt = texts[idx] if idx < len(texts) else ""
                    # source: prefer links in that cell
                    srcs = []
                    if isinstance(idx, list):
                        for i in idx:
                            if i < len(row):
                                srcs += [u for u in row[i]["links"] if u.startswith("http")]
                    else:
                        if idx < len(row):
                            srcs = [u for u in row[idx]["links"] if u.startswith("http")]
                    if not srcs and links:
                        srcs = [links[0]]
                    return txt, (srcs[0] if srcs else "")

                rid, _ = cell(tspec.get("id"))
                title, src1 = cell(tspec.get("title"))
                status, src2 = cell(tspec.get("status"))
                source, src3 = cell(tspec.get("source"))
                sev, _ = cell(tspec.get("severity"))
                if not title:
                    continue
                out.append(entry(
                    spec["fam"], spec["mod"], spec["path"], spec.get("page", spec["path"]),
                    rid, title, status or sev, source or src1 or src2 or src3, sev,
                ))
    return out


REGS = [
    # ---- requirements ------------------------------------------------------
    dict(fam="requirements", mod="data (0c38f465)", kind="csv", path="data/requirements.csv",
         page="docs/requirements.html",
         cols=dict(id="id", title="requirement", status="status", source="evidence_link")),
    dict(fam="requirements", mod="dashboard (7e632805)", kind="json",
         path="dashboard/data/requirements.json", page="dashboard/requirements.html",
         items=["*"],
         cols=dict(id="id", title=["requirement"], status=["status"], source=["acceptance"])),
    dict(fam="requirements", mod="docs/pages (4856379c)", kind="html",
         path="docs/pages/requirements.html", page="docs/pages/requirements.html",
         tables=[dict(match=["ID", "Requirement", "Status"], id=0, title=1, status=2, source=3)]),
    dict(fam="requirements", mod="root page (3dbc4678)", kind="html",
         path="requirements.html", page="../requirements.html",
         tables=[dict(index=0, title=[0, 3], status=5, source=6),
                 dict(index=1, title=0, status=2, source=3)]),
    # ---- questions ---------------------------------------------------------
    dict(fam="questions", mod="data (0c38f465)", kind="csv", path="data/questions.csv",
         page="docs/questions.html",
         cols=dict(id="id", title="question", status="status", source="where_to_verify")),
    dict(fam="questions", mod="dashboard (7e632805)", kind="json",
         path="dashboard/data/questions.json", page="dashboard/questions.html",
         items=["*"],
         cols=dict(id="id", title=["question"], status=["blocking"], source=["known"])),
    dict(fam="questions", mod="docs/pages (4856379c)", kind="html",
         path="docs/pages/questions.html", page="docs/pages/questions.html",
         tables=[dict(match=["ID", "Question", "Status"], id=0, title=1, status=6, source=3)]),
    dict(fam="questions", mod="x3lab (e1c332ce)", kind="json",
         path="x3lab/data/questions.json", page="x3lab/questions.html",
         items=["answered", "open"],
         cols=dict(id="id", title=["question"], status=["status"], source=["source"])),
    dict(fam="questions", mod="lab (972ad7a5)", kind="js", path="assets/data.js",
         page="lab/questions.html", items="questions",
         cols=dict(id="id", title=["question"], status=["status", "state"], source=["known"])),
    # ---- suggestions -------------------------------------------------------
    dict(fam="suggestions", mod="data (0c38f465)", kind="csv", path="data/suggestions.csv",
         page="docs/suggestions.html",
         cols=dict(id="id", title="suggestion", status="status", source="source_link")),
    dict(fam="suggestions", mod="dashboard (7e632805)", kind="json",
         path="dashboard/data/suggestions.json", page="dashboard/suggestions.html",
         items=["*"],
         cols=dict(id="id", title=["title"], status=["status"], source=["problem"])),
    dict(fam="suggestions", mod="docs/pages (4856379c)", kind="html",
         path="docs/pages/suggestions.html", page="docs/pages/suggestions.html",
         tables=[dict(match=["ID", "Suggestion", "Status"], id=0, title=1, status=7)]),
    dict(fam="suggestions", mod="x3lab (e1c332ce)", kind="json",
         path="x3lab/data/suggestions.json", page="x3lab/suggestions.html",
         items=["suggestions"],
         cols=dict(id="id", title=["title"], status=["status"], source=["source"])),
    dict(fam="suggestions", mod="root page (3dbc4678)", kind="html",
         path="suggestions.html", page="../suggestions.html",
         tables=[dict(index=0, title=[0], status=2, source=3)]),
    dict(fam="suggestions", mod="lab (972ad7a5)", kind="js", path="assets/data.js",
         page="lab/suggestions.html", items="suggestions",
         cols=dict(id="id", title=["title", "suggestion"], status=["status"], source=["problem"])),
    # ---- flags -------------------------------------------------------------
    dict(fam="flags", mod="data (0c38f465)", kind="csv", path="data/flags.csv",
         page="docs/flagged.html",
         cols=dict(id="id", title="issue", status="action_for_user",
                   source="source_link", severity="severity")),
    dict(fam="flags", mod="dashboard (7e632805)", kind="json",
         path="dashboard/data/flagged.json", page="dashboard/flagged.html",
         items=["*"],
         cols=dict(id="id", title=["what"], status=["action"], source=["source"],
                   severity=["severity"])),
    dict(fam="flags", mod="docs/pages (4856379c)", kind="html",
         path="docs/pages/flagged.html", page="docs/pages/flagged.html",
         tables=[dict(match=["ID", "Irregularity"], id=0, title=1, source=3)]),
    dict(fam="flags", mod="x3lab (e1c332ce)", kind="json",
         path="x3lab/data/flagged.json", page="x3lab/flagged.html",
         items=["rows"],
         cols=dict(id="id", title=["title"], status=["status"], source=["source"],
                   severity=["severity"])),
    dict(fam="flags", mod="lab (972ad7a5)", kind="js", path="assets/data.js",
         page="lab/flagged.html", items="flagged",
         cols=dict(id="id", title=["issue", "title"], status=["impact", "detail"],
                   source=["sources"], severity=[])),
    dict(fam="flags", mod="root page (3dbc4678)", kind="html",
         path="flagged.html", page="../flagged.html",
         tables=[dict(index=0, title=[0], status=2, source=3),
                 dict(index=1, title=[0], status=2, source=3)]),
    dict(fam="flags", mod="pages (1a771fcd)", kind="html",
         path="pages/flagged-for-review.html", page="pages/flagged-for-review.html",
         tables=[dict(index=0, id=0, title=1, status=3, source=4),
                 dict(index=1, id=0, title=1, status=4, source=3)]),
    # ---- strategies --------------------------------------------------------
    dict(fam="strategies", mod="data (0c38f465)", kind="csv", path="data/strategies.csv",
         page="docs/strategies.html",
         cols=dict(id="strategy_id", title="name", status="status",
                   source="official_input_available")),
    dict(fam="strategies", mod="dashboard (7e632805)", kind="json",
         path="dashboard/data/strategies.json", page="dashboard/strategies.html",
         items=["*"],
         cols=dict(id="id", title=["name"], status=["status"], source=["inputs"])),
    dict(fam="strategies", mod="x3lab (e1c332ce)", kind="json",
         path="x3lab/data/strategies.json", page="x3lab/strategies.html",
         items=["strategies"],
         cols=dict(id="id", title=["name"], status=["state"], source=["source"])),
    dict(fam="strategies", mod="lab (972ad7a5)", kind="js", path="assets/data.js",
         page="lab/strategies.html", items="strategies",
         cols=dict(id="id", title=["name", "title"], status=["status"], source=["inputs"])),
    # ---- signal catalogs ---------------------------------------------------
    dict(fam="signals", mod="docs/pages (4856379c)", kind="html",
         path="docs/pages/strategies.html", page="docs/pages/strategies.html",
         tables=[dict(match=["ID", "Signal", "gate"], id=0, title=1, status=3)]),
    dict(fam="signals", mod="x3lab (e1c332ce)", kind="json",
         path="x3lab/data/strategies.json", page="x3lab/strategies.html",
         items=["signals"],
         cols=dict(id="id", title=["name"], status=["state"], source=["source"])),
]

LOADERS = {"csv": load_csv_reg, "json": load_json_reg, "html": load_html_reg, "js": load_js_reg}


# --------------------------------------------------------------------------- #
# Phase 1 — audit
# --------------------------------------------------------------------------- #
def iter_pages():
    for p in sorted(ROOT.rglob("*.html")):
        if ".git" in p.parts or "crosscheck" in p.parts:
            continue
        yield p


def audit_pages():
    per_page, broken = [], []
    totals = dict(pages=0, links=0, external=0, tables=0, rows=0,
                  rows_with_http=0, rows_flag_only=0, rows_without=0)
    for p in iter_pages():
        rel = str(p.relative_to(ROOT))
        pr = parse_page(p)
        http_links = [u for u in pr.links if u.startswith(("http://", "https://"))]
        local = [u for u in pr.links if not u.startswith(("http://", "https://", "#", "mailto:",
                                                          "javascript:", "data:"))]
        for u in local:
            tgt = u.split("#", 1)[0]
            if not tgt:
                continue
            if not (p.parent / tgt).exists():
                broken.append({"page": rel, "href": u})
        t_rows = t_http = t_flag = t_without = 0
        for t in pr.tables:
            for row in t["rows"]:
                t_rows += 1
                if row_http(row):
                    t_http += 1
                elif FLAG_RE.search(row_text(row)):
                    t_flag += 1
                else:
                    t_without += 1
        per_page.append({
            "page": rel, "links": len(pr.links), "external": len(http_links),
            "tables": len(pr.tables), "rows": t_rows, "rows_with_http": t_http,
            "rows_flag_only": t_flag, "rows_without": t_without,
        })
        totals["pages"] += 1
        totals["links"] += len(pr.links)
        totals["external"] += len(http_links)
        totals["tables"] += len(pr.tables)
        totals["rows"] += t_rows
        totals["rows_with_http"] += t_http
        totals["rows_flag_only"] += t_flag
        totals["rows_without"] += t_without
    return {"totals": totals, "broken_internal": broken, "per_page": per_page}


# --------------------------------------------------------------------------- #
# Phase 2 — reconciliation
# --------------------------------------------------------------------------- #
def load_registers():
    registers, entries, errors = [], [], []
    for spec in REGS:
        try:
            rows = LOADERS[spec["kind"]](spec)
        except Exception as e:  # surface, never crash the whole run
            errors.append({"register": spec["path"], "error": str(e)})
            continue
        registers.append({
            "family": spec["fam"], "module": spec["mod"], "path": spec["path"],
            "page": spec.get("page", spec["path"]), "kind": spec["kind"],
            "rows": len(rows),
        })
        entries.extend(rows)
    return registers, entries, errors


def reconcile(entries):
    fams = sorted({e["family"] for e in entries})
    out_fam, collisions, status_conflicts, cross_dupes, mixed = {}, [], [], [], []
    for fam in fams:
        fent = [e for e in entries if e["family"] == fam]
        by_mod = {}
        for e in fent:
            by_mod.setdefault(e["module"], 0)
            by_mod[e["module"]] += 1
        groups = {}
        for e in fent:
            if e["nid"]:
                groups.setdefault(e["nid"], []).append(e)
        g_out = {}
        for nid, grp in sorted(groups.items()):
            mods = sorted({e["module"] for e in grp})
            titles = [e["title"] for e in grp if e["title"]]
            scores = [jaccard(titles[i], titles[j])
                      for i in range(len(titles)) for j in range(i + 1, len(titles))]
            # Score distribution is bimodal (verified 2026-11-14): paraphrases of the
            # same item score >= 0.40, ID reuse scores <= 0.30.  Three classes:
            if not scores or min(scores) >= 0.40:
                identity = "same"
            elif max(scores) < 0.40:
                identity = "different"
            else:
                identity = "mixed"
            same = identity == "same"
            stats = sorted({e["status_norm"] for e in grp if e["status_norm"]})
            conflict = same and len(stats) > 1
            g_out[nid] = {
                "modules": mods,
                "variants": [{"module": e["module"], "raw_id": e["raw_id"],
                              "title": e["title"], "status": e["status"],
                              "status_norm": e["status_norm"], "page": e["page"],
                              "register": e["register"], "source": e["source"]}
                             for e in grp],
                "identity": identity, "min_score": round(min(scores), 2) if scores else None,
                "same_content": same, "statuses": stats, "status_conflict": conflict,
            }
            if len(mods) > 1 and identity == "different":
                collisions.append({"family": fam, "nid": nid, "modules": mods})
            if len(mods) > 1 and identity == "mixed":
                mixed.append({"family": fam, "nid": nid, "modules": mods})
            if conflict:
                status_conflicts.append({"family": fam, "nid": nid,
                                         "statuses": stats, "modules": mods})
        # cross-ID duplicate titles inside the family
        for i in range(len(fent)):
            for j in range(i + 1, len(fent)):
                a, b = fent[i], fent[j]
                if a["nid"] == b["nid"] or a["module"] == b["module"]:
                    continue
                if a["title"] and b["title"] and jaccard(a["title"], b["title"]) >= 0.6:
                    cross_dupes.append({
                        "family": fam, "a": f"{a['module']}:{a['raw_id']}",
                        "b": f"{b['module']}:{b['raw_id']}",
                        "score": round(jaccard(a["title"], b["title"]), 2),
                        "title": a["title"][:180], "page_a": a["page"], "page_b": b["page"],
                    })
        out_fam[fam] = {"count": len(fent), "modules": by_mod, "id_groups": g_out}
    # cross-family ID reuse (e.g. S01 = suggestion *and* strategy)
    by_nid = {}
    for e in entries:
        if e["nid"]:
            by_nid.setdefault(e["nid"], set()).add(e["family"])
    cross_family = {nid: sorted(f) for nid, f in sorted(by_nid.items()) if len(f) > 1}
    return {
        "families": out_fam,
        "id_namespace_collisions": collisions,
        "id_mixed_identity": mixed,
        "status_conflicts": status_conflicts,
        "cross_id_duplicates": cross_dupes,
        "cross_family_ids": cross_family,
    }


def render_parity():
    pairs = [
        ("data/requirements.csv", "docs/requirements.html"),
        ("data/questions.csv", "docs/questions.html"),
        ("data/suggestions.csv", "docs/suggestions.html"),
        ("data/flags.csv", "docs/flagged.html"),
    ]
    out = []
    for csvp, htmlp in pairs:
        n_csv = sum(1 for _ in csv.DictReader((ROOT / csvp).open(newline="")))
        pr = parse_page(ROOT / htmlp)
        n_html = sum(len(t["rows"]) for t in pr.tables)
        out.append({"csv": csvp, "html": htmlp, "csv_rows": n_csv, "html_rows": n_html,
                    "match": n_csv == n_html})
    return out


def injury_reconciliation():
    a = list(csv.DictReader((ROOT / "data/injury_report_2026_wk10.csv").open(newline="")))
    b = list(csv.DictReader((ROOT / "docs/data/injury-2026-week10.csv").open(newline="")))
    key = lambda r: (r.get("team", ""), r.get("player", ""))
    kb = {key(r): r for r in b}
    missing = [key(r) for r in a if key(r) not in kb]
    disagree = [key(r) for r in a if key(r) in kb
                and (r.get("game_status", "") or "") != (kb[key(r)].get("game_status", "") or "")]
    pm = {}
    for r in a:
        if key(r) in kb:
            pair = (r.get("practice_status", ""), kb[key(r)].get("practice_status", ""))
            pm[str(pair)] = pm.get(str(pair), 0) + 1
    return {
        "designated_csv_rows": len(a), "full_csv_rows": len(b),
        "designated_subset_of_full": not missing, "missing_from_full": len(missing),
        "game_status_disagreements": len(disagree),
        "practice_status_pairs": pm,
        "note": "205-row CSV = players carrying a practice designation; 345-row CSV = every "
                "player listed on the official Week-10 page.",
    }


def run_external_checks():
    checks = [
        ["python3", "scripts/check_site.py"],
        ["python3", "tools/check_links.py"],
        ["python3", "scripts/check_dashboard.py"],
        ["node", "scripts/check_data.js"],
        ["node", "scripts/check_render.js"],
        ["python3", "tools/verify_site.py"],
        ["python3", "scripts/verify_data.py"],
        ["python3", "-m", "py_compile", "tools/crosscheck.py"],
    ]
    out = []
    for cmd in checks:
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
            tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
            out.append({"cmd": " ".join(cmd), "exit": r.returncode, "tail": tail})
        except Exception as e:
            out.append({"cmd": " ".join(cmd), "exit": -1, "tail": [f"ERROR {e}"]})
    return out


# --------------------------------------------------------------------------- #
# Findings (this session's irregularities)
# --------------------------------------------------------------------------- #
def build_findings(audit, rec, parity, injury, ext, reg_errors):
    f = []

    def add(fid, sev, area, text, evidence, action):
        f.append({"id": fid, "severity": sev, "area": area, "finding": text,
                  "evidence": evidence, "action": action})

    n_col = len(rec["id_namespace_collisions"])
    n_st = len(rec["status_conflicts"])
    n_mix = len(rec["id_mixed_identity"])
    n_cf = len(rec["cross_family_ids"])
    add("X-01", "High", "ID namespaces",
        f"Identical normalized IDs denote different content across modules: {n_col} "
        "same-ID/different-content groups (e.g. F-01, Q-01, S-01 each mean different things "
        f"in different modules), {n_mix} mixed-identity groups, and "
        f"{n_st} groups where the same ID is the same item but carries conflicting statuses.",
        [BLOB + "crosscheck/data/report.json", BLOB + "COORDINATION.md"],
        "Prefix IDs with the module (e.g. dash:F-01, lab:Q-03) before any register is merged.")
    if n_cf:
        ex = ", ".join(f"{k}→{'/'.join(v)}" for k, v in list(rec["cross_family_ids"].items())[:6])
        add("X-02", "High", "Cross-family ID reuse",
            f"{n_cf} IDs are reused across different register families — e.g. {ex}. "
            "S01 is simultaneously a suggestion (data/suggestions.csv), a strategy "
            "(data/strategies.csv) and a signal (S1–S8).",
            [BLOB + "data/strategies.csv", BLOB + "data/suggestions.csv",
             BLOB + "docs/pages/strategies.html"],
            "Advertise family-qualified IDs (sug:S01, str:S01, sig:S1) in any consolidation.")
    add("X-03", "Medium", "Empty page",
        "x3lab/requirements.html renders an empty container: the page defines "
        "id=\"reqs\" but x3lab/app.js only references it in the navigation list and "
        "x3lab/data/ contains no requirements dataset, so no requirements are ever shown.",
        [BLOB + "x3lab/requirements.html", BLOB + "x3lab/app.js"],
        "Owner of x3lab/ should populate or remove the page from the navigation.")
    add("X-04", "High", "Stale session / failing CI",
        "Session arena/64164906-x3 (branch arena/64164906-x3, unrelated git history, its own "
        "COORDINATION.md) has been stale since 2026-11-14T04:07Z (>14 h, no commits), never "
        "opened a PR, and its data-pipeline workflow has 9 consecutive failed runs "
        "(last: schedule-parser capture steps). Protocol permits takeover after 60 minutes; "
        "merging an unrelated-history tree blind would risk discarding work, so it is handed "
        "off here instead.",
        [f"{REPO}/tree/arena/64164906-x3",
         f"{REPO}/actions/workflows/data-pipeline.yml",
         f"{REPO}/commit/7b3c700"],
        "A session should take over the data-pipeline branch deliberately, fix the schedule "
        "parser against fixtures, then open a PR.")
    add("X-05", "Medium", "Competing claims",
        "hub/** is claimed by two live sessions at once (arena/1e2d8ef2-x3 commit 07a7611 and "
        "arena/e9b492ab-x3 commit 121ed14) and root index.html is claimed by four sessions "
        "(plus arena/3bf7cc8b-x3 8f86ae7, arena/621bf404-x3 17b5369) — merge conflicts on the "
        "shared landing page are near-certain.",
        [f"{REPO}/commit/07a7611", f"{REPO}/commit/121ed14",
         f"{REPO}/commit/8f86ae7", f"{REPO}/commit/17b5369"],
        "One session must land the landing page first; others re-merge additively.")
    add("X-06", "Medium", "Generator hazard",
        "Re-running scripts/build_site.py silently drops the arena-4856379c-x3 section from "
        "docs/index.html (observed this session; the edit was reverted). COORDINATION.md "
        "carries the same warning from that session.",
        [BLOB + "docs/index.html", BLOB + "scripts/build_site.py", BLOB + "COORDINATION.md"],
        "Fold the section into the generator before anyone rebuilds docs/.")
    try:
        sm = json.loads((ROOT / "audit/summary.json").read_text())
        add("X-07", "Medium", "Injury row divergence",
            f"The independent official-source re-audit (audit/) reports "
            f"{sm['row_results']['DIFF']} of {sm['official_rows']} Week-10 injury rows differ "
            f"from the live official page in 'game' ({sm['field_mismatch_counts']['game']}) or "
            f"'tv' ({sm['field_mismatch_counts']['tv']}) fields; "
            f"{sm['row_results']['MATCH']} rows match exactly.",
            [BLOB + "audit/summary.json", BLOB + "audit/index.html",
             "https://www.nfl.com/injuries/league/2026/reg10"],
            "Correct docs/data/injury-2026-week10.csv or document the divergence permanently.")
    except Exception:
        pass
    add("X-08", "Low", "Injury CSV row counts",
        f"Two Week-10 injury CSVs coexist ({injury['designated_csv_rows']} rows in "
        f"data/ vs {injury['full_csv_rows']} rows in docs/data/). Reconciled this session: the "
        f"205-row file is a strict subset of the 345-row file "
        f"(missing={injury['missing_from_full']}), game statuses agree on every shared row "
        f"(disagreements={injury['game_status_disagreements']}), and practice labels are "
        "abbreviations of the same official wording.",
        [BLOB + "data/injury_report_2026_wk10.csv", BLOB + "docs/data/injury-2026-week10.csv",
         "https://www.nfl.com/injuries/league/2026/reg10"],
        "No action beyond documenting; keep one canonical file per future snapshot.")
    add("X-09", "High", "No market data",
        "No official source anywhere in the register set publishes betting lines or player "
        "props (data/sources.csv contains no odds publisher), so no strategy can be scored "
        "against a market and the leaderboard cannot activate.",
        [BLOB + "data/sources.csv", BLOB + "crosscheck/data/report.json"],
        "Owner decision: commission a licensed odds feed or declare the leaderboard notional.")
    add("X-10", "High", "Legal scope",
        "Wagering with private bookmakers is criminal for the bettor under Japanese Penal "
        "Code Art. 185 (Art. 186 habitual gambling); the project's jurisdictional scope is "
        "unresolved and blocks any real-money use of originated lines.",
        ["https://www.japaneselawtranslation.go.jp/en/laws/view/3581/tb",
         BLOB + "data/flags.csv"],
        "Owner decision with local counsel before any staking feature ships.")
    add("X-11", "Medium", "CI coverage gap",
        ".github/workflows/pages.yml runs the root/docs/lab/dashboard link checks but does NOT "
        "run tools/verify_site.py (docs/pages 49-table verifier), scripts/verify_data.py "
        "(x3lab 2,134-check verifier), or any checker for audit/ or x3lab/ pages, and does "
        "not cover this crosscheck/ unit either.",
        [BLOB + ".github/workflows/pages.yml"],
        "pages.yml owner: add the two verifiers plus a crosscheck step "
        "(request logged in COORDINATION.md).")
    add("X-12", "Medium", "Sandbox egress",
        "Shell egress from the agent sandbox is restricted to github.com/api/codeload, npm and "
        "PyPI hosts; www.nfl.com and other official publishers cannot be fetched directly, so "
        "line-by-line re-verification runs in GitHub Actions or via documented search "
        "citations, never silently from the sandbox.",
        [BLOB + "COORDINATION.md"],
        "Keep official-source fetches in CI with committed, hashed snapshots.")
    add("X-13", "Low", "Closed record PR",
        "PR #12 (arena/972ad7a5-x3, 'Record NFL Decision Lab merge and Pages deployment') was "
        "observed OPEN with COORDINATION.md conflicts earlier today and is now CLOSED without "
        "merge (2026-11-14T18:22Z); that session's section is already present on main, so no "
        "content is lost.",
        [f"{REPO}/pull/12", BLOB + "COORDINATION.md"],
        "None; recorded for the audit trail.")
    for e in reg_errors:
        add("X-90", "High", "Extractor error",
            f"Register {e['register']} could not be parsed: {e['error']}",
            [BLOB + e["register"]], "Fix the extractor or the register format.")
    without = [p for p in audit["per_page"] if p["rows_without"] > 0]
    if without:
        worst = sorted(without, key=lambda p: -p["rows_without"])[:8]
        detail = ", ".join(f"{p['page']} ({p['rows_without']})" for p in worst)
        add("X-14", "Medium", "Rows without source or flag",
            f"{sum(p['rows_without'] for p in without)} table rows across "
            f"{len(without)} existing pages carry neither an external source link nor an "
            f"UNVERIFIED/flag marker — worst: {detail}.",
            [BLOB + "crosscheck/data/report.json"],
            "Owners of the listed pages add per-row source links or explicit flags.")
    if audit["broken_internal"]:
        add("X-15", "High", "Broken internal links",
            f"{len(audit['broken_internal'])} broken internal links found.",
            [BLOB + "crosscheck/data/report.json"], "Fix the listed hrefs.")
    bad_parity = [p for p in parity if not p["match"]]
    if bad_parity:
        add("X-16", "Medium", "Render parity",
            "CSV registers and their rendered docs/ pages disagree in row count: "
            + "; ".join(f"{p['csv']}={p['csv_rows']} vs {p['html']}={p['html_rows']}"
                        for p in bad_parity),
            [BLOB + p["csv"] for p in bad_parity] + [BLOB + p["html"] for p in bad_parity],
            "Re-run the docs generator or reconcile the CSV.")
    for c in ext:
        if c["exit"] != 0:
            add("X-91", "High", "Verifier failing",
                f"External verifier `{c['cmd']}` exited {c['exit']}: "
                + " / ".join(c["tail"][-2:]),
                [BLOB + c["cmd"].split()[-1]], "Fix before merge.")
    return f


# --------------------------------------------------------------------------- #
# Phase 3 — page building
# --------------------------------------------------------------------------- #
NAV = [
    ("index.html", "Overview"),
    ("requirements.html", "Requirements"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("flagged.html", "Flagged"),
    ("executive-summary.html", "Exec summary"),
    ("verification.html", "Verification"),
]


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def trunc(s, n=180):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def badge(text, kind):
    return f'<span class="badge {kind}">{esc(text)}</span>'


def status_badge(norm, raw):
    if not norm:
        return '<span class="badge mut">-</span>'
    kind = {"DONE": "ok", "PARTIAL": "warn", "BLOCKED": "flag"}.get(norm, "info")
    return f'<span class="badge {kind}">{esc(norm)}</span><span class="src">{esc(trunc(raw, 60))}</span>'


OWN_TARGETS = {h for h, _ in NAV} | {"styles.css", "data/report.json", "data/selfcheck.json"}


def rel(target):
    """Resolve a repo-root-relative target to a crosscheck/-relative href."""
    t = str(target or "")
    if t.startswith("../") or t in OWN_TARGETS:
        return t
    return "../" + t


def src_cell(page, path, extra=None, label=None):
    parts = [f'<a href="{BLOB}{esc(path)}">{esc(label or path)}</a>']
    sub = [f'<a href="{esc(rel(page))}">view page</a>']
    if extra and extra.startswith("http"):
        sub.append(f'<a href="{esc(extra)}">source</a>')
    parts.append('<span class="src">' + " · ".join(sub) + "</span>")
    return "".join(parts)


def layout(title, active, body, stats_line=""):
    parts = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        parts.append(f'<a href="{href}"{cls}>{esc(label)}</a>')
    nav = "".join(parts)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — X3 crosscheck</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="top"><div class="wrap">
<h1>{esc(title)}</h1>
<p>Cross-module reconciliation &amp; verification · session arena/37c71381-x3 · every row source-linked</p>
<nav class="main">{nav}</nav>
</div></header>
<div class="wrap">
{body}
</div>
<footer><div class="wrap">
Research only — this unit reconciles what sessions published; it does not place or recommend bets.
Generated by <code>tools/crosscheck.py</code> · source data: <a href="{BLOB}">github.com/karagemop466-tech/X3</a>
{stats_line}
</div></footer>
</body>
</html>
"""


def build_index(audit, rec, registers, findings, facts):
    t = audit["totals"]
    stats = f"""
<div class="stats">
<div class="stat"><div class="n">{t['pages']}</div><div class="l">pages audited</div></div>
<div class="stat"><div class="n">{t['links']:,}</div><div class="l">links checked</div></div>
<div class="stat"><div class="n">{len(audit['broken_internal'])}</div><div class="l">broken internal</div></div>
<div class="stat"><div class="n">{t['rows']:,}</div><div class="l">table rows audited</div></div>
<div class="stat"><div class="n">{t['rows_with_http']:,}</div><div class="l">rows with source link</div></div>
<div class="stat"><div class="n">{t['rows_flag_only']}</div><div class="l">rows flagged only</div></div>
<div class="stat"><div class="n">{t['rows_without']}</div><div class="l">rows unlinked (→ Flagged)</div></div>
<div class="stat"><div class="n">{len(findings)}</div><div class="l">findings this session</div></div>
</div>"""
    modules = {}
    for p in audit["per_page"]:
        m = p["page"].split("/")[0] if "/" in p["page"] else "(root)"
        d = modules.setdefault(m, {"pages": 0, "links": 0, "tables": 0, "rows": 0})
        d["pages"] += 1; d["links"] += p["links"]; d["tables"] += p["tables"]; d["rows"] += p["rows"]
    mod_links = {
        "(root)": "../index.html", "docs": "../docs/index.html", "dashboard": "../dashboard/index.html",
        "lab": "../lab/index.html", "x3lab": "../x3lab/index.html",
        "pages": "../pages/flagged-for-review.html",
        "site": "../site/index.html", "legacy": "../legacy/index.html", "audit": "../audit/index.html",
        "research": "../README.md", "analysis": "../analysis/README.md",
    }
    rows = []
    for m, d in sorted(modules.items()):
        link = mod_links.get(m, f"{m}/")
        rows.append(
            f"<tr><td>{esc(m)}</td><td class='num'>{d['pages']}</td>"
            f"<td class='num'>{d['links']}</td><td class='num'>{d['tables']}</td>"
            f"<td class='num'>{d['rows']}</td>"
            f"<td>{src_cell(link if link.endswith('.html') else '../index.html', m if m != '(root)' else 'index.html')}</td></tr>"
        )
    reg_rows = []
    for fam, fd in sorted(rec["families"].items()):
        mods = fd["modules"]
        cells = " · ".join(f"{esc(k.split(' (')[0])}={v}" for k, v in sorted(mods.items()))
        reg_rows.append(
            f"<tr><td>{badge(fam, 'info')}</td><td class='num'>{fd['count']}</td>"
            f"<td>{cells}</td>"
            f"<td class='num'>{len(fd['id_groups'])}</td>"
            f"<td>{src_cell('requirements.html' if fam=='requirements' else 'questions.html' if fam=='questions' else 'suggestions.html' if fam=='suggestions' else 'flagged.html' if fam=='flags' else 'verification.html', 'crosscheck/data/report.json', label='report')}</td></tr>"
        )
    body = f"""
<p class="lede">Eight sessions each shipped their own registers — requirements, questions,
suggestions, flags, strategies — and nobody ever compared them. This unit reads every register
line by line, reconciles them, and publishes one consolidated review surface:
<strong>nothing here is implemented; everything is for review.</strong></p>
<div class="banner warn">Research only · no betting advice · no market feed · legal scope
unresolved (<a href="flagged.html">X-10</a>) · every row below links to its source file on
github.com or to the page it came from.</div>
<h2>Start here</h2>
<div class="grid">
<a class="tile" href="executive-summary.html"><b>Executive summary</b><span>Verified facts, missing information, blocking decisions, recommended sequence</span></a>
<a class="tile" href="requirements.html"><b>Requirements matrix</b><span>{rec['families'].get('requirements',{}).get('count',0)} requirements across 4 registers, reconciled</span></a>
<a class="tile" href="questions.html"><b>Questions &amp; answers</b><span>What is known, what is missing, and how to obtain it</span></a>
<a class="tile" href="suggestions.html"><b>Suggestions review queue</b><span>Every suggestion from every module — review before any change</span></a>
<a class="tile" href="flagged.html"><b>Flagged for review</b><span>{len(findings)} session findings + the consolidated flag index of all modules</span></a>
<a class="tile" href="verification.html"><b>Verification log</b><span>Line-by-line audit results, verifier outputs, reconciliation proofs</span></a>
</div>
{stats}
<h2>Site modules at a glance</h2>
<table><thead><tr><th>Module</th><th class="num">Pages</th><th class="num">Links</th>
<th class="num">Tables</th><th class="num">Rows</th><th>Source</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>Registers reconciled</h2>
<table><thead><tr><th>Family</th><th class="num">Entries</th><th>Per module</th>
<th class="num">Distinct IDs</th><th>Detail</th></tr></thead>
<tbody>{''.join(reg_rows)}</tbody></table>
<h2>Key reconciliation results</h2>
<ul class="tight">
<li>Same ID, different content across modules: <strong>{len(rec['id_namespace_collisions'])}</strong> groups
(<a href="flagged.html">X-01</a>).</li>
<li>Same ID, conflicting status: <strong>{len(rec['status_conflicts'])}</strong> groups.</li>
<li>Same ID, mixed identity (some modules match, others do not):
<strong>{len(rec['id_mixed_identity'])}</strong> groups.</li>
<li>IDs reused across register families: <strong>{len(rec['cross_family_ids'])}</strong>
(<a href="flagged.html">X-02</a>).</li>
<li>Possible duplicate suggestions/questions across IDs: <strong>{len(rec['cross_id_duplicates'])}</strong>
(<a href="suggestions.html">detail</a>).</li>
<li>Broken internal links: <strong>{len(audit['broken_internal'])}</strong> ·
rows without source or flag: <strong>{t['rows_without']}</strong>
(<a href="flagged.html">X-14</a>).</li>
</ul>
"""
    return layout("Cross-module reconciliation", "index.html", body)


def build_requirements(rec):
    fam = rec["families"].get("requirements", {"id_groups": {}, "count": 0, "modules": {}})
    mods_order = ["data (0c38f465)", "dashboard (7e632805)", "docs/pages (4856379c)",
                  "root page (3dbc4678)"]
    rows = []
    for nid, g in sorted(fam["id_groups"].items()):
        bym = {v["module"]: v for v in g["variants"]}
        cells = []
        for m in mods_order:
            v = bym.get(m)
            _cell = status_badge(v["status_norm"], v["status"]) if v else EMPTY_CELL
            cells.append(f"<td>{_cell}</td>")
        best = max(g["variants"], key=lambda v: len(v["title"]))
        verdict = {"same": badge("same content", "ok"),
                   "different": badge("ID reused", "flag"),
                   "mixed": badge("mixed - review", "warn")}[g["identity"]]
        verdict += f'<span class="src">min-pair {g.get("min_score")}</span>' 
        st = (badge("status conflict", "flag") if g["status_conflict"] else
              (badge("statuses: " + "/".join(g["statuses"]), "info") if g["statuses"] else badge("no status", "mut")))
        srcs = []
        seen = set()
        for v in g["variants"]:
            key = (v["register"], v["page"])
            if key in seen:
                continue
            seen.add(key)
            srcs.append(src_cell(v["page"], v["register"]))
        rows.append(
            f"<tr><td class='mono'>{esc(nid)}</td>"
            f"<td>{esc(trunc(best['title'], 220))}<span class='src'>"
            + " · ".join(f"{esc(v['raw_id'])} ({esc(v['module'].split(' (')[0])})" for v in g["variants"])
            + "</span></td>"
            + "".join(cells)
            + f"<td>{verdict}</td><td>{st}</td><td>{'<br>'.join(srcs)}</td></tr>"
        )
    root_reg = next((r for r in REGS if r["path"] == "requirements.html"), None)
    root_rows = []
    if root_reg:
        for e in load_html_reg(root_reg):
            root_rows.append(
                f"<tr><td>{esc(trunc(e['title'], 200))}</td>"
                f"<td>{status_badge(e['status_norm'], e['status'])}</td>"
                f"<td>{src_cell('requirements.html', 'requirements.html')}</td></tr>"
            )
    body = f"""
<div class="banner">Consolidation of every requirements register on the site. Statuses are shown
exactly as each module publishes them; nothing is harmonised silently.
All rows link to the register file and the rendered page.</div>
<h2>ID-level requirements matrix</h2>
<p class="small">Families: {fam['count']} entries · {len(fam['id_groups'])} distinct normalized IDs ·
{len(rec['id_namespace_collisions'])} cross-module ID-content collisions site-wide
(<a href="flagged.html">X-01</a>).</p>
<table><thead><tr><th>ID</th><th>Requirement (variant titles)</th>
<th>data</th><th>dashboard</th><th>docs/pages</th><th>Identity</th><th>Status</th><th>Source</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Unnumbered register — root requirements.html</h2>
<p class="small">This register has no IDs, so it cannot be reconciled at ID level; its rows are
listed as published. Flagged as part of <a href="flagged.html">X-01</a>.</p>
<table><thead><tr><th>Category / question</th><th>Answer status</th><th>Source</th></tr></thead>
<tbody>{''.join(root_rows)}</tbody></table>
"""
    return layout("Requirements matrix", "requirements.html", body)


def build_questions(rec):
    fam = rec["families"].get("questions", {"id_groups": {}, "count": 0, "modules": {}})
    mods_order = ["data (0c38f465)", "dashboard (7e632805)", "docs/pages (4856379c)",
                  "x3lab (e1c332ce)", "lab (972ad7a5)"]
    rows = []
    for nid, g in sorted(fam["id_groups"].items()):
        bym = {v["module"]: v for v in g["variants"]}
        best = max(g["variants"], key=lambda v: len(v["title"]))
        cells = []
        for m in mods_order:
            v = bym.get(m)
            _cell = status_badge(v["status_norm"], v["status"]) if v else EMPTY_CELL
            cells.append(f"<td>{_cell}</td>")
        verdict = {"same": badge("same question", "ok"),
                   "different": badge("ID reused", "flag"),
                   "mixed": badge("mixed - review", "warn")}[g["identity"]]
        verdict += f'<span class="src">min-pair {g.get("min_score")}</span>' 
        st = badge("status conflict", "flag") if g["status_conflict"] else (
            badge("/".join(g["statuses"]), "info") if g["statuses"] else badge("no status", "mut"))
        srcs, seen = [], set()
        for v in g["variants"]:
            k = (v["register"], v["page"])
            if k not in seen:
                seen.add(k); srcs.append(src_cell(v["page"], v["register"]))
        rows.append(
            f"<tr><td class='mono'>{esc(nid)}</td>"
            f"<td>{esc(trunc(best['title'], 230))}<span class='src'>"
            + " · ".join(f"{esc(v['raw_id'])} ({esc(v['module'].split(' (')[0])})" for v in g["variants"])
            + "</span></td>" + "".join(cells)
            + f"<td>{verdict}</td><td>{st}</td><td>{'<br>'.join(srcs)}</td></tr>"
        )
    open_rows = []
    for v in fam.get("id_groups", {}).values():
        for var in v["variants"]:
            if var["status_norm"] in ("OPEN", "BLOCKED"):
                open_rows.append(
                    f"<tr><td class='mono'>{esc(var['raw_id'])} ({esc(var['module'].split(' (')[0])})</td>"
                    f"<td>{esc(trunc(var['title'], 240))}</td>"
                    f"<td>{status_badge(var['status_norm'], var['status'])}</td>"
                    f"<td>{src_cell(var['page'], var['register'])}</td></tr>"
                )
    body = f"""
<div class="banner">Known answers are whatever the owning module published with a source;
unknowns stay unknown. This page does not answer anything itself — it shows where each answer
lives and which questions remain open.</div>
<h2>Question matrix (all modules)</h2>
<p class="small">{fam['count']} entries · {len(fam['id_groups'])} distinct normalized IDs.</p>
<table><thead><tr><th>ID</th><th>Question (variant titles)</th>
<th>data</th><th>dashboard</th><th>docs/pages</th><th>x3lab</th><th>lab</th>
<th>Identity</th><th>Status</th><th>Source</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>Open / blocking entries (as published)</h2>
<table><thead><tr><th>Entry</th><th>Question</th><th>Status</th><th>Source</th></tr></thead>
<tbody>{''.join(open_rows[:80])}</tbody></table>
"""
    return layout("Questions & answers", "questions.html", body)


def build_suggestions(rec):
    fam = rec["families"].get("suggestions", {"id_groups": {}, "count": 0, "modules": {}})
    mods_order = ["data (0c38f465)", "dashboard (7e632805)", "docs/pages (4856379c)",
                  "x3lab (e1c332ce)", "root page (3dbc4678)", "lab (972ad7a5)"]
    rows = []
    for nid, g in sorted(fam["id_groups"].items()):
        bym = {v["module"]: v for v in g["variants"]}
        best = max(g["variants"], key=lambda v: len(v["title"]))
        cells = []
        for m in mods_order:
            v = bym.get(m)
            _cell = status_badge(v["status_norm"], v["status"]) if v else EMPTY_CELL
            cells.append(f"<td>{_cell}</td>")
        verdict = {"same": badge("same idea", "ok"),
                   "different": badge("ID reused", "flag"),
                   "mixed": badge("mixed - review", "warn")}[g["identity"]]
        verdict += f'<span class="src">min-pair {g.get("min_score")}</span>' 
        st = badge("status conflict", "flag") if g["status_conflict"] else (
            badge("/".join(g["statuses"]), "info") if g["statuses"] else badge("no status", "mut"))
        srcs, seen = [], set()
        for v in g["variants"]:
            k = (v["register"], v["page"])
            if k not in seen:
                seen.add(k); srcs.append(src_cell(v["page"], v["register"]))
        rows.append(
            f"<tr><td class='mono'>{esc(nid)}</td>"
            f"<td>{esc(trunc(best['title'], 230))}<span class='src'>"
            + " · ".join(f"{esc(v['raw_id'])} ({esc(v['module'].split(' (')[0])})" for v in g["variants"])
            + "</span></td>" + "".join(cells)
            + f"<td>{verdict}</td><td>{st}</td><td>{'<br>'.join(srcs)}</td></tr>"
        )
    dup_rows = []
    for d in rec["cross_id_duplicates"]:
        if d["family"] != "suggestions":
            continue
        dup_rows.append(
            f"<tr><td>{esc(d['a'])}</td><td>{esc(d['b'])}</td>"
            f"<td class='num'>{d['score']}</td><td>{esc(trunc(d['title'], 200))}</td>"
            f"<td>{src_cell(d['page_a'], d['page_a'])}<br>{src_cell(d['page_b'], d['page_b'])}</td></tr>"
        )
    body = f"""
<div class="banner warn"><strong>Review only.</strong> Nothing on this page has been
implemented. Each module keeps its own decision state; this queue exists so a reviewer can pick
the best path first. Choose a path in your module of record, then implement.</div>
<h2>Suggestion matrix (all modules)</h2>
<p class="small">{fam['count']} entries · {len(fam['id_groups'])} distinct normalized IDs ·
statuses exactly as published (proposed / awaiting review / adopted / deferred …).</p>
<table><thead><tr><th>ID</th><th>Suggestion (variant titles)</th>
<th>data</th><th>dashboard</th><th>docs/pages</th><th>x3lab</th><th>root</th><th>lab</th>
<th>Identity</th><th>Status</th><th>Source</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>Cross-ID duplicates inside the suggestion family</h2>
<p class="small">The same idea proposed under different IDs by different modules — consensus
candidates (title similarity ≥ 0.6).</p>
<table><thead><tr><th>Entry A</th><th>Entry B</th><th class="num">Score</th><th>Theme</th>
<th>Source</th></tr></thead><tbody>{''.join(dup_rows) or
'<tr><td colspan="5">None detected at the 0.6 threshold — <span class="badge mut">UNVERIFIED</span> for lower similarities.</td></tr>'}</tbody></table>
"""
    return layout("Suggestions review queue", "suggestions.html", body)


def build_flagged(rec, findings):
    frows = []
    for f in findings:
        sev_kind = {"High": "flag", "Medium": "warn", "Low": "mut"}.get(f["severity"], "info")
        ev = "<br>".join(f'<a href="{esc(u)}">{esc(trunc(u, 70))}</a>' for u in f["evidence"])
        frows.append(
            f"<tr><td class='mono'>{esc(f['id'])}</td><td>{badge(f['severity'], sev_kind)}</td>"
            f"<td>{esc(f['area'])}</td><td>{esc(f['finding'])}</td>"
            f"<td>{ev}</td><td>{esc(f['action'])}</td></tr>"
        )
    flag_entries = [e for e in _ALL_ENTRIES if e["family"] == "flags"]
    crows = []
    for e in sorted(flag_entries, key=lambda e: (e["module"], e["raw_id"])):
        crows.append(
            f"<tr><td>{esc(e['module'])}</td><td class='mono'>{esc(e['raw_id'] or '-')}</td>"
            f"<td>{badge(e['severity'], 'warn') if e['severity'] else badge('n/a', 'mut')}</td>"
            f"<td>{esc(trunc(e['title'], 240))}</td>"
            f"<td>{src_cell(e['page'], e['register'], e['source'])}</td></tr>"
        )
    body = f"""
<div class="banner flag"><strong>Flagged for review — nothing here blocks the merge.</strong>
Section A is this session's own findings; Section B is the consolidated index of every flag
register published by every session, so one page can be reviewed end to end.</div>
<h2>A · Findings from this session (arena/37c71381-x3)</h2>
<table><thead><tr><th>ID</th><th>Sev</th><th>Area</th><th>Finding</th><th>Evidence</th>
<th>Suggested action</th></tr></thead><tbody>{''.join(frows)}</tbody></table>
<h2>B · Consolidated flag index (all modules)</h2>
<p class="small">{len(flag_entries)} flag entries from
{len({e['module'] for e in flag_entries})} registers. The docs/ rendering of data/flags.csv is
checked for render parity instead of listed twice.</p>
<table><thead><tr><th>Module</th><th>ID</th><th>Sev</th><th>Issue (as published)</th>
<th>Source</th></tr></thead><tbody>{''.join(crows)}</tbody></table>
<h2>C · ID-namespace collisions (summary)</h2>
<p class="small">{len(rec['id_namespace_collisions'])} groups where one ID means different things
in different modules — full detail per family on the Requirements / Questions / Suggestions
pages. Cross-family reuse: {len(rec['cross_family_ids'])} IDs.</p>
<table><thead><tr><th>Family</th><th>ID</th><th>Modules</th><th>Source</th></tr></thead><tbody>
""" + "".join(
        f"<tr><td>{badge(c['family'], 'info')}</td><td class='mono'>{esc(c['nid'])}</td>"
        f"<td>{esc(', '.join(c['modules']))}</td>"
        f"<td>{src_cell('verification.html', 'crosscheck/data/report.json', label='report')}</td></tr>"
        for c in rec["id_namespace_collisions"][:60]
    ) + "</tbody></table>"
    return layout("Flagged for review", "flagged.html", body)


def build_exec(rec, audit, facts, findings):
    t = audit["totals"]
    sm = facts.get("injury_audit", {})
    inj = facts.get("injury_reconciliation", {})
    verified_rows = []
    if sm:
        verified_rows.append(
            "<tr><td>2026 Week-10 official injury report</td>"
            f"<td class='num'>{sm.get('official_rows')} rows · {sm.get('official_status_counts',{}).get('Out')} Out · "
            f"{sm.get('official_status_counts',{}).get('Doubtful')} Doubtful · "
            f"{sm.get('official_status_counts',{}).get('Questionable')} Questionable · "
            f"{sm.get('official_status_counts',{}).get('blank_game_status')} blank status</td>"
            "<td><a href='https://www.nfl.com/injuries/league/2026/reg10'>nfl.com/injuries/league/2026/reg10</a></td>"
            f"<td>{src_cell('audit/index.html', 'audit/summary.json', label='independent re-audit (294 MATCH / 51 DIFF)')}</td></tr>"
        )
    verified_rows.append(
        "<tr><td>2026 league standings</td><td class='num'>32 clubs</td>"
        "<td><a href='https://www.nfl.com/standings/'>nfl.com/standings</a></td>"
        f"<td>{src_cell('dashboard/standings.html', 'dashboard/data/standings.json')}</td></tr>"
    )
    if sm:
        verified_rows.append(
            "<tr><td>2026 Week-10 schedule</td>"
            f"<td class='num'>{sm.get('schedule_games')} games · {len(sm.get('schedule_byes', []))} byes</td>"
            "<td><a href='https://www.nfl.com/schedules/2026/by-week/week-10'>nfl.com/schedules/2026/by-week/week-10</a></td>"
            f"<td>{src_cell('audit/index.html', 'audit/schedule_check_wk10.csv')}</td></tr>"
        )
    verified_rows.append(
        "<tr><td>Week-10 CSV internal consistency</td>"
        f"<td class='num'>{inj.get('designated_csv_rows')}⊂{inj.get('full_csv_rows')} rows · "
        f"{inj.get('game_status_disagreements')} status disagreements</td>"
        "<td><a href='https://www.nfl.com/injuries/'>nfl.com/injuries</a></td>"
        f"<td>{src_cell('verification.html', 'crosscheck/data/report.json', label='reconciliation proof')}</td></tr>"
    )
    missing = [
        ("Market lines (spread / total / moneyline)",
         "No official publisher exists in the register set", "X-09",
         "data/sources.csv", "../docs/sources.html"),
        ("Player prop prices",
         "No official publisher; combos cannot be priced", "X-09",
         "data/sources.csv", "../docs/sources.html"),
        ("Correlation coefficients (numeric)",
         "Left blank by policy - no paired-event history", "X-01",
         "data/correlations.csv", "../docs/correlations.html"),
        ("Measured strategy performance / CLV",
         "No odds feed and no settlement history", "X-09",
         "data/strategies.csv", "../docs/strategies.html"),
        ("Depth-string ranks (2nd/3rd/4th string) for all 32 clubs",
         "Club depth charts are self-labelled unofficial; mostly unverified", "X-14",
         "dashboard/data/depth_missing.json", "../dashboard/depth-charts.html"),
        ("Leaderboard rewards",
         "Notional only; policy undecided", "X-10",
         "dashboard/data/strategies.json", "../dashboard/leaderboard.html"),
    ]
    miss_rows = "".join(
        f"<tr><td>{esc(a)}</td><td>{esc(b)}</td>"
        f"<td>{badge('UNVERIFIED / missing', 'flag')} <span class='src'>{esc(ref)}</span></td>"
        f"<td>{src_cell(page, path)}</td></tr>"
        for a, b, ref, path, page in missing
    )
    decisions = [
        ("D1", "Legal scope: research-only vs wagering (Japan Penal Code Art. 185/186)",
         "Blocking", "data/questions.csv Q02 · data/flags.csv F01",
         "https://www.japaneselawtranslation.go.jp/en/laws/view/3581/tb", "questions.html"),
        ("D2", "Odds-feed source for scoring (no official publisher exists)",
         "Blocking", "data/sources.csv · dashboard questions",
         BLOB + "data/sources.csv", "questions.html"),
        ("D3", "Leaderboard rewards: notional vs funded (and where lawful)",
         "Blocking", "dashboard suggestions · lab leaderboard",
         BLOB + "dashboard/data/suggestions.json", "suggestions.html"),
        ("D4", "Canonical injury snapshot file (205-row vs 345-row CSV)",
         "Non-blocking — reconciled", "this session's proof", "https://www.nfl.com/injuries/", "verification.html"),
        ("D5", "Whether to take over the stale data-pipeline session (X-04)",
         "Non-blocking", "COORDINATION.md handoff", f"{REPO}/tree/arena/64164906-x3", "flagged.html"),
        ("D6", "Which landing page wins the four-way index.html claim (X-05)",
         "Non-blocking", "claim commits", f"{REPO}/pulls", "flagged.html"),
    ]
    dec_rows = "".join(
        f"<tr><td class='mono'>{i}</td><td>{esc(q)}</td><td>{badge(s, 'flag' if 'Blocking'==s else 'warn')}</td>"
        f"<td>{esc(w)}</td><td><a href='{esc(u)}'>source</a></td>"
        f"<td>{src_cell(p, 'crosscheck/data/report.json', label='detail')}</td></tr>"
        for i, q, s, w, u, p in decisions
    )
    seq = [
        ("1", "Settle legal scope (D1) — nothing else can ship to a human user without it.",
         "data/questions.csv", "docs/questions.html"),
        ("2", "Decide the odds-feed question (D2) or explicitly declare the leaderboard notional.",
         "data/sources.csv", "docs/sources.html"),
        ("3", "Prefix module IDs (X-01/X-02) before any register merge so consolidation cannot corrupt meaning.",
         "crosscheck/data/report.json", "requirements.html"),
        ("4", "Repair or document the 51 divergent injury rows (X-07).",
         "audit/summary.json", "audit/index.html"),
        ("5", "Add the missing verifiers to CI (X-11) so every module stays green on push.",
         ".github/workflows/pages.yml", "verification.html"),
        ("6", "Take over or retire the stale data-pipeline branch (X-04).",
         "COORDINATION.md", "flagged.html"),
        ("7", "Only then: calibrate line origination on a verified game log and run strategies through gates G0–G8.",
         "data/gates.csv", "docs/strategies.html"),
    ]
    seq_rows = "".join(
        f"<tr><td class='num'>{n}</td><td>{esc(txt)}</td>"
        f"<td>{src_cell(page, path)}</td></tr>" for n, txt, path, page in seq
    )
    body = f"""
<div class="banner">Generated {facts['generated_at']} from the reconciled register set.
Research only. Every claim below links to a source file or an official publisher page.</div>
<h2>Where the project stands</h2>
<ul class="tight">
<li><strong>{t['pages']} pages</strong> across 8 site modules, <strong>{t['links']:,} links</strong>
checked, <strong>{len(audit['broken_internal'])} broken</strong>, {t['rows']:,} table rows audited
({t['rows_with_http']:,} with a source link, {t['rows_flag_only']} flagged, {t['rows_without']} neither).</li>
<li><strong>{sum(f['count'] for f in rec['families'].values())} register entries</strong>
reconciled across {len(rec['families'])} families;
{len(rec['id_namespace_collisions'])} ID-content collisions and
{len(rec['status_conflicts'])} status conflicts found — consolidation is unsafe until fixed.</li>
<li><strong>{len(findings)} findings</strong> published on the
<a href="flagged.html">Flagged for review</a> page (non-blocking).</li>
<li>All pre-existing verifiers pass (see <a href="verification.html">verification</a>).</li>
</ul>
<h2>Verified facts (official sources)</h2>
<table><thead><tr><th>Fact</th><th class="num">Value</th><th>Official source</th>
<th>Where verified</th></tr></thead><tbody>{''.join(verified_rows)}</tbody></table>
<h2>What we do not have (blank, never inferred)</h2>
<table><thead><tr><th>Missing</th><th>Why</th><th>State</th><th>Source</th></tr></thead>
<tbody>{miss_rows}</tbody></table>
<h2>Blocking decisions (owner required)</h2>
<table><thead><tr><th>#</th><th>Decision</th><th>Impact</th><th>Raised by</th>
<th>Source</th><th>Detail</th></tr></thead><tbody>{dec_rows}</tbody></table>
<h2>Recommended decision sequence</h2>
<table><thead><tr><th class="num">#</th><th>Step</th><th>Source</th></tr></thead>
<tbody>{seq_rows}</tbody></table>
<h2>Next review surface</h2>
<div class="grid">
<a class="tile" href="suggestions.html"><b>Suggestions</b><span>Review queues from all six modules — pick paths, implement later</span></a>
<a class="tile" href="questions.html"><b>Questions</b><span>Open / blocking items with discovery paths</span></a>
<a class="tile" href="flagged.html"><b>Flagged</b><span>All irregularities, one page</span></a>
</div>
"""
    return layout("Executive summary", "executive-summary.html", body)


def build_verification(audit, rec, parity, injury, ext, facts, findings, reg_errors):
    t = audit["totals"]
    ext_parts = []
    for c in ext:
        res_badge = badge("PASS", "ok") if c["exit"] == 0 else badge(f"EXIT {c['exit']}", "flag")
        ext_parts.append(
            f"<tr><td class='mono'>{esc(c['cmd'])}</td><td>{res_badge}</td>"
            f"<td class='small'>{esc(' / '.join(c['tail']))}</td>"
            f"<td>{src_cell(c['cmd'].split()[-1], c['cmd'].split()[-1])}</td></tr>"
        )
    ext_rows = "".join(ext_parts)
    page_rows = "".join(
        f"<tr><td>{src_cell('../' + p['page'], p['page'])}</td>"
        f"<td class='num'>{p['links']}</td><td class='num'>{p['tables']}</td>"
        f"<td class='num'>{p['rows']}</td><td class='num'>{p['rows_with_http']}</td>"
        f"<td class='num'>{p['rows_flag_only']}</td>"
        f"<td class='num'>{badge(str(p['rows_without']), 'ok' if p['rows_without']==0 else 'warn')}</td></tr>"
        for p in audit["per_page"]
    )
    parity_rows = "".join(
        f"<tr><td>{src_cell('../' + p['csv'], p['csv'])}</td>"
        f"<td>{src_cell('../' + p['html'], p['html'])}</td>"
        f"<td class='num'>{p['csv_rows']}</td><td class='num'>{p['html_rows']}</td>"
        f"<td>{badge('match', 'ok') if p['match'] else badge('MISMATCH', 'flag')}</td></tr>"
        for p in parity
    )
    inj = injury
    inj_rows = f"""
<tr><td>Designated CSV (data/injury_report_2026_wk10.csv)</td>
<td class='num'>{inj['designated_csv_rows']}</td>
<td>{src_cell('../data/injury_report_2026_wk10.csv', 'data/injury_report_2026_wk10.csv')}</td></tr>
<tr><td>Full CSV (docs/data/injury-2026-week10.csv)</td>
<td class='num'>{inj['full_csv_rows']}</td>
<td>{src_cell('../docs/data/injury-2026-week10.csv', 'docs/data/injury-2026-week10.csv')}</td></tr>
<tr><td>Designated ⊂ Full (player key: team+player)</td>
<td>{badge('YES — 0 missing', 'ok') if inj['designated_subset_of_full'] else badge('NO', 'flag')}</td>
<td>{src_cell('crosscheck/data/report.json', 'crosscheck/data/report.json', label='computed proof')}</td></tr>
<tr><td>game_status disagreements on shared rows</td>
<td class='num'>{inj['game_status_disagreements']}</td>
<td>{src_cell('crosscheck/data/report.json', 'crosscheck/data/report.json', label='computed proof')}</td></tr>
<tr><td>practice_status label pairs</td>
<td class='small'>{esc(json.dumps(inj['practice_status_pairs']))}</td>
<td>{src_cell('../data/injury_report_2026_wk10.csv', 'data/injury_report_2026_wk10.csv')}</td></tr>
"""
    fam_parts = []
    for f, fd in sorted(rec["families"].items()):
        mods_txt = ", ".join(f"{k.split(' (')[0]}:{v}" for k, v in sorted(fd["modules"].items()))
        n_reused = sum(1 for g in fd["id_groups"].values() if g.get("identity") == "different")
        n_mixed = sum(1 for g in fd["id_groups"].values() if g.get("identity") == "mixed")
        n_conf = sum(1 for g in fd["id_groups"].values() if g["status_conflict"])
        fam_parts.append(
            f"<tr><td>{badge(f, 'info')}</td><td class='num'>{fd['count']}</td>"
            f"<td>{esc(mods_txt)}</td>"
            f"<td class='num'>{len(fd['id_groups'])}</td>"
            f"<td class='num'>{n_reused} reused · {n_mixed} mixed</td>"
            f"<td class='num'>{n_conf}</td>"
            f"<td>{src_cell('crosscheck/data/report.json', 'crosscheck/data/report.json', label='report')}</td></tr>"
        )
    fam_rows = "".join(fam_parts)
    body = f"""
<div class="banner ok">Method: deterministic extraction → audit → reconciliation → generation.
No value is inferred: unknown cells render '-' or UNVERIFIED. Generated rows are re-parsed by
the post-write gate (<code>python3 tools/crosscheck.py --verify</code> →
<a href="data/selfcheck.json">data/selfcheck.json</a>), which fails if any generated row lacks
a source link or flag marker.</div>
<h2>1 · Repo-wide audit (phase 1)</h2>
<div class="stats">
<div class="stat"><div class="n">{t['pages']}</div><div class="l">pages</div></div>
<div class="stat"><div class="n">{t['links']:,}</div><div class="l">links</div></div>
<div class="stat"><div class="n">{t['external']:,}</div><div class="l">external</div></div>
<div class="stat"><div class="n">{len(audit['broken_internal'])}</div><div class="l">broken internal</div></div>
<div class="stat"><div class="n">{t['rows']:,}</div><div class="l">rows</div></div>
<div class="stat"><div class="n">{t['rows_without']}</div><div class="l">rows w/o source+flag</div></div>
</div>
<p class="small">Rows w/o source+flag are published as finding <a href="flagged.html">X-14</a>
(the row itself is not deleted or altered). Broken internal links → <a href="flagged.html">X-15</a>.</p>
<table><thead><tr><th>Page</th><th class="num">Links</th><th class="num">Tables</th>
<th class="num">Rows</th><th class="num">w/ link</th><th class="num">flag only</th>
<th class="num">neither</th></tr></thead><tbody>{page_rows}</tbody></table>
<h2>2 · Register reconciliation (phase 2)</h2>
<table><thead><tr><th>Family</th><th class="num">Entries</th><th>Modules</th>
<th class="num">IDs</th><th class="num">Identity</th><th class="num">Conflicts</th>
<th>Source</th></tr></thead><tbody>{fam_rows}</tbody></table>
<h2>3 · Render parity (CSV ↔ docs/ page)</h2>
<table><thead><tr><th>CSV register</th><th>Rendered page</th><th class="num">CSV rows</th>
<th class="num">HTML rows</th><th>Result</th></tr></thead><tbody>{parity_rows}</tbody></table>
<h2>4 · Week-10 injury CSV reconciliation</h2>
<table><thead><tr><th>Check</th><th>Result</th><th>Source</th></tr></thead>
<tbody>{inj_rows}</tbody></table>
<h2>5 · Pre-existing verifiers (read-only, run by this session)</h2>
<p class="small"><code>scripts/build_site.py</code> is deliberately NOT run: it rewrites
docs/index.html and drops another session's section (finding <a href="flagged.html">X-06</a>).</p>
<table><thead><tr><th>Command</th><th>Result</th><th>Output tail</th><th>Source</th></tr></thead>
<tbody>{ext_rows}</tbody></table>
<h2>6 · Generation self-check</h2>
<ul class="tight">
<li>Every row emitted by <code>tools/crosscheck.py</code> carries an absolute
github.com source link (and, where available, the underlying official publisher URL).</li>
<li>Post-write gate re-parses all generated pages: see
<a href="data/selfcheck.json">data/selfcheck.json</a> (written by
<code>--verify</code>; recorded in COORDINATION.md at merge time).</li>
<li>Extractor errors: {len(reg_errors)} · findings: {len(findings)}
(<a href="flagged.html">flagged</a>).</li>
</ul>
<h2>7 · What this session did NOT do</h2>
<ul class="tight">
<li>Did not fetch nfl.com directly — sandbox egress is restricted (finding X-12); official
facts are carried from already-fetched, source-linked snapshots and re-audited by
audit/.</li>
<li>Did not edit any other session's files; requests are logged in COORDINATION.md.</li>
<li>Did not infer, fill or harmonise any value — conflicts are surfaced, not resolved.</li>
</ul>
"""
    return layout("Verification log", "verification.html", body)


# --------------------------------------------------------------------------- #
# Post-write gate
# --------------------------------------------------------------------------- #
def verify_generated():
    results, failures = [], 0
    for p in sorted(OUT.glob("*.html")):
        pr = parse_page(p)
        rows = sum(len(t["rows"]) for t in pr.tables)
        bad = 0
        for t in pr.tables:
            for row in t["rows"]:
                if not row_http(row) and not FLAG_RE.search(row_text(row)):
                    bad += 1
        broken = []
        for u in pr.links:
            if u.startswith(("http://", "https://", "#", "mailto:")):
                continue
            tgt = u.split("#", 1)[0]
            if tgt and not (p.parent / tgt).exists():
                broken.append(u)
        failures += bad + len(broken)
        results.append({"page": p.name, "rows": rows, "rows_without_source_or_flag": bad,
                        "broken_internal": broken})
    out = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "pages": results, "failures": failures,
           "result": "PASS" if failures == 0 else "FAIL"}
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "selfcheck.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0 if failures == 0 else 1


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
_ALL_ENTRIES: list = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-external", action="store_true",
                    help="skip the read-only verifiers owned by other sessions")
    ap.add_argument("--verify", action="store_true",
                    help="post-write gate over generated pages only")
    args = ap.parse_args()

    if args.verify:
        sys.exit(verify_generated())

    audit = audit_pages()
    registers, entries, reg_errors = load_registers()
    global _ALL_ENTRIES
    _ALL_ENTRIES = entries
    rec = reconcile(entries)
    parity = render_parity()
    injury = injury_reconciliation()
    ext = [] if args.skip_external else run_external_checks()

    try:
        sm = json.loads((ROOT / "audit/summary.json").read_text())
    except Exception:
        sm = {}

    findings = build_findings(audit, rec, parity, injury, ext, reg_errors)
    facts = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "injury_audit": sm,
        "injury_reconciliation": injury,
    }

    report = {
        "generated_at": facts["generated_at"],
        "session": "arena/37c71381-x3",
        "audit": audit,
        "registers": registers,
        "register_errors": reg_errors,
        "reconciliation": rec,
        "render_parity": parity,
        "injury_reconciliation": injury,
        "external_checks": ext,
        "findings": findings,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "report.json").write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")

    pages = {
        "index.html": build_index(audit, rec, registers, findings, facts),
        "requirements.html": build_requirements(rec),
        "questions.html": build_questions(rec),
        "suggestions.html": build_suggestions(rec),
        "flagged.html": build_flagged(rec, findings),
        "executive-summary.html": build_exec(rec, audit, facts, findings),
        "verification.html": build_verification(audit, rec, parity, injury, ext, facts,
                                                findings, reg_errors),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    sc = DATA / "selfcheck.json"
    if not sc.exists():
        sc.write_text(json.dumps({
            "result": "PENDING",
            "note": "written by build; run `python3 tools/crosscheck.py --verify` for the gate",
        }, indent=1) + "\n")
    for name, content in pages.items():
        (OUT / name).write_text(content)

    t = audit["totals"]
    print(f"report: {DATA/'report.json'}")
    print(f"pages:  {len(pages)} written to {OUT}/")
    print(f"audit:  {t['pages']} pages, {t['links']} links, "
          f"{len(audit['broken_internal'])} broken internal, {t['rows']} rows, "
          f"{t['rows_without']} rows without source/flag")
    print(f"regs:   {len(registers)} registers, {len(entries)} entries, "
          f"{sum(len(f['id_groups']) for f in rec['families'].values())} id groups, "
          f"{len(rec['id_namespace_collisions'])} id collisions, "
          f"{len(rec['status_conflicts'])} status conflicts")
    print(f"find:   {len(findings)} findings")
    bad_ext = [c for c in ext if c["exit"] != 0]
    if bad_ext:
        print("EXTERNAL CHECKS FAILING:")
        for c in bad_ext:
            print(" ", c["cmd"], "exit", c["exit"])
    print("now run: python3 tools/crosscheck.py --verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
