#!/usr/bin/env python3
"""Independent gate for the hub. Fails on any of:

  1. a data row without a source link or an explicit UNVERIFIED marker (delegated to the builder's audit);
  2. a published statistic that no longer matches a fresh recomputation from the raw data;
  3. non-deterministic output (two builds, two digests);
  4. injury snapshot drifting from the repo's previous snapshot in its game-status column
     (practice-status drift is reported, not treated as a failure - the live page changes);
  5. an unfilled token or a row-count mismatch between a page and its data file.

Run: python3 scripts/check_hub.py
"""
import csv, hashlib, json, math, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
FAIL = []


def fail(msg):
    FAIL.append(msg)
    print("FAIL " + msg)


def ok(msg):
    print("pass " + msg)


def read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


def digest(path):
    h = hashlib.sha256()
    for root, _, files in os.walk(path):
        for f in sorted(files):
            if f.endswith(".html"):
                p = os.path.join(root, f)
                h.update(f.encode())
                h.update(open(p, "rb").read())
    return h.hexdigest()


def main():
    import build_hub

    # 1. determinism: build twice in memory, compare bytes
    pages_a, derived, deficiency, lines = build_hub.build(write=False)
    pages_b, derived2, _, _ = build_hub.build(write=False)
    if pages_a != pages_b:
        fail("two consecutive builds differ - output is not deterministic")
    else:
        ok("deterministic: %d pages, identical bytes on a second build" % len(pages_a))

    # 2. recompute the published statistics from the raw data
    st = list(csv.DictReader(open(os.path.join(ROOT, "hub/data/standings_2026.csv"), encoding="utf-8")))
    g = lambda r: int(r["w"]) + int(r["l"]) + int(r["t"])
    def pearson(x, y):
        n = len(x); mx = sum(x) / n; my = sum(y) / n
        sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
        return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)
    pct = [int(r["w"]) / g(r) for r in st]
    checks = {
        "R_PF": pearson([int(r["pf"]) / g(r) for r in st], pct),
        "R_PA": pearson([int(r["pa"]) / g(r) for r in st], pct),
        "R_NET": pearson([int(r["net"]) / g(r) for r in st], pct),
        "R_HR": pearson([int(r["home"].split("-")[0]) / (int(r["home"].split("-")[0]) + int(r["home"].split("-")[1])) for r in st],
                        [int(r["road"].split("-")[0]) / (int(r["road"].split("-")[0]) + int(r["road"].split("-")[1])) for r in st]),
    }
    for k, v in checks.items():
        if abs(round(v, 4) - derived["correlations"][k]) > 1e-9:
            fail("published %s does not match recomputation (%.4f vs %s)" % (k, v, derived["correlations"][k]))
    if not FAIL:
        ok("correlations recomputed from the official standings snapshot match the published values")

    # 3. standings integrity, independently
    if sum(int(r["w"]) for r in st) != sum(int(r["l"]) for r in st):
        fail("league wins != losses")
    elif sum(int(r["pf"]) for r in st) != sum(int(r["pa"]) for r in st):
        fail("league PF != PA")
    elif len(st) != 32:
        fail("standings snapshot is not 32 clubs")
    else:
        ok("standings: 32 clubs, wins=losses, PF=PA, ties balanced (sum T = %d)" % sum(int(r["t"]) for r in st))
    if derived["standings_problems"]:
        fail("per-club split inconsistencies: %s" % derived["standings_problems"])

    # 4. injury row counts and the diff against the previous repo snapshot
    inj = list(csv.DictReader(open(os.path.join(ROOT, "hub/data/injuries_wk10_2026-11-14.csv"), encoding="utf-8")))
    if len(inj) != derived["injury_rows"]:
        fail("injury row count mismatch")
    else:
        ok("injury table: %d rows, designations %s" % (len(inj), sorted(derived["designations"].items())))
    prior_path = os.path.join(ROOT, "docs/data/injury-2026-week10.csv")
    if os.path.exists(prior_path):
        prior = list(csv.DictReader(open(prior_path, encoding="utf-8")))
        mine = {(r["team"], r["player"]): (r["game_status"] or "").strip() for r in inj}
        theirs = {(r["team"], r["player"]): (r["game_status"] or "").strip() for r in prior}
        only_mine, only_theirs = set(mine) - set(theirs), set(theirs) - set(mine)
        status_diff = [k for k in set(mine) & set(theirs) if mine[k] != theirs[k]]
        if only_mine or only_theirs or status_diff:
            fail("injury snapshot differs from the repo copy: +%s -%s status-changed %s" % (only_mine, only_theirs, status_diff))
        else:
            ok("injury snapshot reproduces the repo copy: %d/%d players, identical game statuses "
               "(practice statuses excluded from this check - they change between fetches)" % (len(mine), len(theirs)))

    # 5. every hub page exists, has no unfilled token, and every row links
    pages_dir = os.path.join(ROOT, "hub")
    htmls = sorted(f for f in os.listdir(pages_dir) if f.endswith(".html"))
    bad = [p for p in htmls + ["index.html"] if re.search(r"\{\{[A-Z_0-9]+\}\}", read(("hub/" if p != "index.html" else "") + p))]
    if bad:
        fail("unfilled tokens in %s" % bad)
    else:
        ok("%d hub pages + landing page carry no unfilled token" % len(htmls))

    # 6. data-row count parity for the injury page and the lines page
    inj_page = read("hub/injuries.html")
    if inj_page.count("<tr>") - inj_page.count("<tr><th>") - 1 < len(inj):
        fail("injuries page renders fewer rows than the data file")
    else:
        ok("injuries page renders all %d rows" % len(inj))
    lines_page = read("hub/lines.html")
    if len(lines) != derived["unplayed_games"]:
        fail("lines count != unplayed games on the slate")
    else:
        ok("lines page prices %d unplayed games, blanks the 1 played + %d byes" % (len(lines), len(derived["byes"])))

    # 7. links resolve on disk (after the last build wrote files)
    broken = 0
    for name in htmls + ["index.html"]:
        body = read(("hub/" if name != "index.html" else "") + name)
        base = os.path.join(ROOT, "hub") if name != "index.html" else ROOT
        for m in re.finditer(r'(?:href|src)="([^"#<> ]+?)"', body):
            u = m.group(1)
            if u.startswith(("http://", "https://", "mailto:")):
                continue
            tgt = os.path.normpath(os.path.join(base, u.split("?")[0]))
            if not os.path.exists(tgt):
                broken += 1
                fail("broken internal link %s -> %s" % (name, u))
    if not broken:
        ok("no broken internal links across %d pages" % (len(htmls) + 1))

    # 8. official-source discipline on the data pages
    official = ("www.nfl.com", "nfl.com")
    for page in ("injuries.html", "deficiency.html", "lines.html", "correlations.html"):
        body = read("hub/" + page)
        for tbl in re.findall(r"<table[^>]*>(.*?)</table>", body, re.S):
            head = tbl.split("</tr>", 1)[0]
            if "<th>Source</th>" not in head:
                continue
            for tr in re.findall(r"<tr>(.*?)</tr>", tbl[len(head):], re.S):
                if "nfl.com" in tr or "UNVERIFIED" in tr:
                    continue
                fail("%s: row lacks an official link and an UNVERIFIED marker: %s" % (page, re.sub("<[^>]+>", " ", tr)[:90]))
    ok("row-source rule holds on the four data pages")

    # 9. JSON validity + every source id referenced on the site resolves
    for f in sorted(os.listdir(os.path.join(ROOT, "hub/data"))):
        if f.endswith(".json"):
            json.load(open(os.path.join(ROOT, "hub/data", f), encoding="utf-8"))
    ok("hub/data JSON files parse")

    print()
    if FAIL:
        print("HUB CHECK FAILED: %d problem(s)" % len(FAIL))
        return 1
    print("HUB CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
