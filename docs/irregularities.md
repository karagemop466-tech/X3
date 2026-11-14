# Irregularities and repository review findings

Review conducted on 2026-11-14 by session `64164906`, working line by line
against official sources. Each item is either resolved, carried as a flagged
item on the published site, or recorded here because it bounds what earlier
verification is possible.

---

## 1. The repository had no prior work

At the start of this session the repository contained exactly two things: a
`README.md` whose entire content was the single line `# X3`, and one commit
(`e124230 Initial commit`) on `main`. There was no requirements register, no
data pipeline, no test suite, no site and no history to reconcile against.

**Consequence:** nothing could be migrated or cross-checked, and no earlier
verification is possible. Every artefact in this repository was created in this
session.

**Status:** resolved by building the platform from scratch. Recorded because it
bounds what the platform can claim about continuity.

---

## 2. The build environment cannot reach the official sources directly

Shell egress from the authoring environment resolves only
`github.com`, `api.github.com`, `codeload.github.com`,
`registry.npmjs.org`, `pypi.org` and `files.pythonhosted.org`. A request to
`https://www.nfl.com/` fails with a TLS connection close, and no other host is
reachable either.

**Consequence:** the official payloads cannot be pulled from the shell, and
the GitHub Actions artefact and log endpoints, which redirect to Azure blob
storage, are equally unreachable from here.

**Resolution:** official sources are retrieved **inside GitHub Actions**, whose
runners have full egress. The committed datasets are the verified snapshot of
such a run, and every payload is identified by its SHA-256 and fetch time in
`data/datasets/fetch_manifest.json`. Build failures are diagnosed from
committed reports (`data/datasets/build_errors.json`,
`data/datasets/structure_report.json`) rather than from CI logs, because the
logs are not reachable from this environment.

**Status:** resolved by design; recorded as a flagged item.

---

## 3. `operations.nfl.com/rules/` and `nfl.com/news/nfl-communications` return HTTP 404

Two of the first registry entries were invalid:

* `https://operations.nfl.com/rules/` → **404**. The official rulebook lives
  at `https://operations.nfl.com/rules-officiating/2026-nfl-rulebook`, and the
  full 2026 Official Playing Rules PDF is published by NFL Communications at
  `media.nfl.com`.
* `https://www.nfl.com/news/nfl-communications` → **404**. The official media
  and league-statement channel is `https://media.nfl.com/`.

**Resolution:** both were replaced with verified URLs, and every registry
entry now records its HTTP status in the fetch manifest so a broken reference
is visible rather than silent. A fetcher that returns 404 is recorded as a
failure, not silently skipped.

**Status:** resolved.

---

## 4. Official club domains: the Texans and the Titans were transposed

The initial registry mapped `houston-texans` to `texans.com`, which is the
**Tennessee** Titans' domain, and `tennessee-titans` to the same host. The
Houston Texans' official site is `houstontexans.com`.

**Consequence:** both clubs would have appeared to have no official depth
chart, and the Houston Texans' roster and depth data would have been
attributed to the wrong club.

**Resolution:** the domains were corrected, and the depth-chart fetcher now
accepts one page per club only when the page genuinely contains a depth-chart
table.

**Status:** resolved.

---

## 5. Several club sites return the same application shell for every path

For the Arizona Cardinals, six different depth-chart URLs each returned
**1,125,463 bytes** — byte-identical application shells rather than six
charts. For the Philadelphia Eagles, six URLs each returned roughly 500 bytes,
which is a stub rather than a chart.

**Consequence:** a naive fetch-and-count would have reported depth-chart
coverage for clubs that publish none, and would have inflated the unit count.

**Resolution:** `parse_depth_chart` now accepts a page only when the page
identifies itself as a depth chart *and* contains a table with at least five
rows and at least two columns. Rejected candidates are recorded in
`data/datasets/depth_charts.json` under `rejected_candidates`, with the reason.

**Status:** resolved.

---

## 6. The depth-chart URL pattern works for 30 of 32 clubs, not all of them

`https://www.<club>.com/team/depth-chart` resolves for 30 clubs. Two clubs did
not resolve through any of the four probed patterns.

**Consequence:** the platform cannot resolve the depth string of a replacement
for every club from official sources alone.

**Resolution:** the gap is published as coverage on the Depth page and as a
flagged item, rather than being filled in. Suggestion S-009 proposes the
official game book's starters-and-substitutions order as the second step of the
resolution chain, which is the route to closing the remaining gap.

**Status:** open, tracked.

---

## 7. Official depth charts are published per club, not per league

There is no league-level depth-chart source. Each club publishes its own, in
its own format, and many omit positions entirely or are dated.

**Consequence:** depth-string resolution is inherently partial, and a league
model built on depth ordering will always carry coverage gaps.

**Resolution:** the coverage table on the Depth page publishes exactly how
many clubs resolved, and unresolved rows are left blank and flagged.

**Status:** open, tracked.

---

## 8. The official injury archive is current-state, not point-in-time

The official archive exposes every past week at
`https://www.nfl.com/injuries/league/<season>/reg<week>`, which makes a
multi-season availability back-test possible. However, each archived page is
the version NFL.com publishes **today**: a week may have been revised after
the fact, so an archive page can contain late information such as game-day
inactives that was not available when a bet would have been placed.

**Consequence:** an availability back-test built from the archive carries a
look-ahead risk that the platform cannot fully remove.

**Resolution:** the limitation is stated in the methodology and on the
Findings page. Any future live-validation cycle must use only the snapshot
captured at decision time.

**Status:** open, tracked.

---

## 9. The platform's own line creates a circularity risk in evaluation

This is a methodological irregularity rather than a data defect, and it is
recorded here because it is the most consequential design issue found.

Because the platform originates its own lines, a strategy scored against those
lines is being compared with the model that priced the game. A strategy that
merely echoes the model scores perfectly while adding nothing.

**Resolution:** three safeguards are in place (distinct signals, the model
published as a benchmark rather than a competitor, and the two-model proposal
in S-002), and the issue is stated explicitly on the Strategies page, in the
methodology, and on the Findings page.

**Status:** open, tracked.

---

## 10. Player-prop classes cannot yet be evaluated

`https://www.nfl.com/games/<slug>/boxscore` returns **404**, so the per-game
player logs required for player-prop and prop-combination strategies are not
available through the route that was tried.

**Consequence:** three of the four strategy classes cannot be evaluated, and
the player-prop correlation matrix cannot be computed.

**Resolution:** the limitation is published, the affected strategies are
marked as registered-but-not-evaluated, and the Flagged for Review page lists
the gap with the question and suggestion that would close it (Q-005, S-013).

**Status:** open, tracked.

---

## 11. GitHub Pages is locked to the legacy Jekyll build

The repository's Pages configuration cannot be modified with the token
available here (`PATCH /repos/…/pages` returns **403**). Pages is therefore
configured for the legacy build from the `main` branch root.

**Consequence:** the generated site must live at the repository root rather
than in a `docs/` folder, and the build is Jekyll-based.

**Resolution:** `_config.yml` excludes `data/`, `scripts/`, `docs/`, `site/`,
`.github/`, `README.md` and `COORDINATION.md` from the published output, so the
published site contains only the dashboard pages and their assets. The
generated HTML is committed to the repository so the site is published on every
merge to `main`.

**Status:** resolved.

---

## 12. GitHub Actions artefact and log endpoints are unreachable from the sandbox

`gh run download` and `gh run view --log` both fail with an EOF on the Azure
blob-storage redirect.

**Consequence:** CI failures could not be diagnosed from the workflow log.

**Resolution:** every build step writes a machine-readable report into
`data/datasets/` and the workflow commits those reports on failure, so the
diagnosis is available from the repository itself.

**Status:** resolved.
