# Methodology

Everything the platform publishes is computed from official NFL sources. This
document states exactly how, so that a reviewer can reproduce or challenge any
number on the site.

---

## 1. Data provenance

`scripts/fetch_official.py` retrieves every source from the registry in
`scripts/lib/official.py`. The registry contains only:

| Publisher | Hosts |
|---|---|
| NFL | `nfl.com`, `operations.nfl.com`, `media.nfl.com`, `static.www.nfl.com` |
| Official NFL clubs | the 32 club-operated domains listed in `scripts/lib/official.py` |

For each source the fetcher records, in `data/datasets/fetch_manifest.json`:

* the exact URL requested and the final URL after redirects,
* the HTTP status,
* the byte count,
* the **SHA-256 of the raw payload**,
* the UTC timestamp of the fetch.

The raw payloads are cached in `data/raw/` (git-ignored) and uploaded as a
CI artefact for audit. The committed artefacts are the parsed datasets, each of
which carries `source_url` on every row.

`scripts/build_datasets.py` converts the raw payloads into flat datasets.
`scripts/validate_site.py` then refuses to pass the build if any dataset row
lacks an official `source_url`, or if any published link points at a
non-official host.

---

## 2. The no-inference rule

A value is published only if an official source publishes it.

* A blank official cell is rendered as an explicit **unverified** marker, never
  as a zero, a dash or a best guess.
* A statistic that cannot be computed because its dataset is missing is
  **omitted**, and the omission is recorded on the Flagged for Review page
  with the reason and the source that was checked.
* No commercial betting line, projection service, injury feed or third-party
  aggregator is ingested anywhere in the pipeline.

---

## 3. Injury-report semantics

The official NFL injury report is a **practice-participation record**, not a
statement of fact.

* A player who is absent from the report is recorded as **not reported**.
  Absence is not evidence of availability.
* A player with no game-status designation is recorded as **no designation**.
* The report week, the game date and the fetch timestamp are stored with every
  row, so a back-test can only use information that existed at decision time.
* Historical weeks are retrieved from the official archive at
  `https://www.nfl.com/injuries/league/<season>/reg<week>`. Note that this is
  the archive **as published today**: a week's page may have been revised after
  the fact, so it can contain late information (for example game-day inactives)
  that was not available when the bet was placed. This limitation applies to
  every availability back-test and is flagged on the site.

---

## 4. Depth resolution

Depth ordering is published by clubs, not by the league, so the resolution
order is strict:

1. **The club's own official depth chart.** The pipeline probes every official
   club domain, accepts a page only when it genuinely contains a depth-chart
   table, and keeps one page per club so that a club's application shell
   cannot be counted twice.
2. **The official game book**, which lists the starters and the order in which
   substitutes entered. (Not yet implemented; see S-009.)
3. **Blank and flagged.** When neither resolves, the replacement's depth string
   is left blank and the gap appears on the Flagged for Review page.

A depth string is never inferred from a player's reputation, from statistics or
from a previous season.

---

## 5. The line model

`scripts/compute_signals.py` originates every published line. Model version
`line-model-v1.0`.

**Inputs** (official only): team points for and points against from the
official league standings; the number of games each team has played; the
official final scores of completed games.

**Step 1 — league baseline.** `league_points_per_game` is the total points
scored across all teams divided by the total team-games played.

**Step 2 — team adjustments.**

```
adj_off_i = (PF_i / G_i − league_ppg) × G_i / (G_i + k)     k = 4
adj_def_i = (PA_i / G_i − league_ppg) × G_i / (G_i + k)
```

The factor `G_i / (G_i + k)` shrinks a team towards the league mean. A team
with four games played is pulled 50 per cent towards the mean; a team with
sixteen games is pulled 20 per cent. `k = 4` is a **model choice**, not an
observed quantity, and it is versioned with the model.

**Step 3 — expected scores.**

```
exp_home = league_ppg + (adj_off_home + adj_def_away) / 2 + HFA / 2
exp_away = league_ppg + (adj_off_away + adj_def_home) / 2 − HFA / 2
```

`HFA` is the average home margin across all completed official games, so the
home-field term is measured rather than assumed.

**Step 4 — published lines.** The spread is rounded to the nearest half point
and shifted against the favourite by `MARGIN_PCT × margin standard deviation`,
where `MARGIN_PCT = 3%`. The quoted prices are `p_fair − margin / 2` on both
sides, which carries the same hold.

**Known limitation.** The model does not adjust for availability. The depth
string of a replacement cannot be resolved for every club from official
sources, so an availability adjustment is not published rather than being
estimated. This is recorded as the state of strategy ST-002.

---

## 6. Validation: walk-forward, purged

The back-test uses an **anchored walk-forward** scheme:

* For each week, ratings are built from games completed strictly before that
  week.
* No random split is used, so no information leaks backwards in time.
* A team's games immediately adjacent to a boundary are excluded from the
  training window when that team also appears in the evaluation block
  (a team-level purge), so that slow-moving features cannot bridge the split.
* Each evaluation week is a fold. Stability is measured as the share of folds
  in which the edge was positive.

---

## 7. Skill share: removing luck from the equation

For a strategy with beliefs `p_i` about each bet and binary outcomes `y_i`:

```
model-implied variance = Σ p_i (1 − p_i)
observed variance      = Σ (y_i − mean(p))²
skill share           = model-implied variance / observed variance
```

The **residual share** is the luck component: the part of the outcome the
model did not explain. The skill share is reported with:

* a **block-bootstrap** 95 per cent interval, and
* a **permutation test** that shuffles the outcomes against the probabilities
  to give the probability of observing a skill share that large by chance.

A strategy is only eligible if its skill share clears the gate threshold
*and* the bootstrap interval excludes zero skill. A strategy that wins by luck
produces a skill share indistinguishable from zero and fails the gate.

---

## 8. Correlation

`scripts/compute_signals.py` publishes Pearson correlations between team-level
signals computed from the official standings, and between game-level score
relationships computed from official final scores. The unit of observation,
the sample size and the method are stated next to each matrix.

Correlations that cannot be computed from the available official data are
**not published**. The player-prop correlation matrix requires per-game
official player logs; until those are ingested, the matrix is listed as
unavailable with the reason rather than estimated.

---

## 9. The circularity problem, stated plainly

The platform originates its own lines, so a strategy evaluated against those
lines is, by construction, being compared with the model that produced them.
Three safeguards apply:

1. Every strategy in the register uses a signal **deliberately different** from
   the line model's inputs (for example a Pythagorean-expectation residual
   rather than a points adjustment).
2. The line model itself is published as the **benchmark**, not as a
   competitor, so its skill is visible without it being ranked against
   itself.
3. Suggestion **S-002** proposes a stronger design — a separately specified
   evaluation reference, trained on a disjoint period and a disjoint feature
   set — and records that it is open.

---

## 10. Gates

Ten gates (G1–G10) are defined on the Strategies page, together with their
thresholds and the measured value for each strategy. A strategy must clear
every gate to be eligible for scoring and reward. Thresholds are labelled as
proposals where they depend on an unanswered question.

---

## 11. Reproducibility

Every published artefact can be regenerated from the committed code:

```bash
python scripts/fetch_official.py     # official payloads + provenance manifest
python scripts/build_datasets.py     # verified datasets
python scripts/compute_signals.py    # lines, correlations, back-test
python scripts/build_site.py         # the site
python scripts/validate_site.py      # links, source links, unverified markers
```

The same sequence runs unattended in GitHub Actions on every push and on a
twice-daily schedule.
