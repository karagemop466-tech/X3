#!/usr/bin/env python3
"""
X3 / page builders for the eight market-structure requirements (session arena/f0880a0b-x3).

Rendered by tools/build_hub.py, which passes itself in so these pages share one
stylesheet, one navigation and one row-source gate. Kept in a separate module so the
older page builders in build_hub.py stay readable and a parallel session editing them
does not collide with this work.

Five pages:
  markets.html        side, then total, then moneyline; fair / market / difference columns
  price-store.html    the append-only snapshot store, what a close means, what is missing
  results.html        the verified results feed and the three checks that gate it
  replacements.html   the DEPTH of the replacement, not the fact of one
  leaderboard.html    extended by p_leader (see build_hub) - not rebuilt here

Every table row either cites an official URL or carries an explicit UNVERIFIED / DERIVED
marker; the build fails otherwise (tools/verify_hub.py).
"""
from __future__ import annotations

import json
import os


def build(B, J, C, X):
    """B = the build_hub module (helpers), J = json loader, C = hub_content, X = x3_content."""
    esc, badge, link, table, page = B.esc, B.badge, B.link, B.table, B.page
    AS_OF = B.AS_OF

    markets = J("markets.json")
    results = J("results.json")
    depth = J("depth_replacement.json")
    corr = J("correlations.json")
    strat = J("strategies.json")
    try:
        store = J("price_store.json")
    except Exception:
        store = None

    # =====================================================================
    # 1. ORIGINATED MARKETS  (requirements: order, and fair/market/difference)
    # =====================================================================
    def p_markets():
        bt = markets["backtest"]
        rows = []
        for r in markets["live"]:
            for market, fair_lbl, fair_val, price_lbl, price_val in (
                ("1. side (home handicap)", "spread", f"{r['side_fair_line']:+.1f}",
                 "home price", f"{r['side_fair_price_home']:.3f}"),
                ("2. total", "total", f"{r['total_fair_line']:.1f}",
                 "over price", f"{r['total_fair_price_over']:.3f}"),
                ("3. moneyline", "no handicap",
                 (f"home {r['ml_fair_american_home']:+d}"
                  if isinstance(r["ml_fair_american_home"], int) else "n/a"),
                 "home price", f"{r['ml_fair_home']:.3f}"),
            ):
                rows.append([
                    f"<b>{esc(r['away'])}</b> at <b>{esc(r['home'])}</b><br>"
                    f"<span class='mut'>{esc(r['date_iso'])}"
                    + ("<br>neutral site" if r["neutral_site"] else "") + "</span>",
                    esc(market),
                    f"<b>{esc(fair_val)}</b><br><span class='mut'>{esc(fair_lbl)}</span>",
                    f"{price_val}<br><span class='mut'>{esc(price_lbl)}</span>",
                    "<span class='blank'></span>",
                    "<span class='blank'></span>",
                    "<span class='blank'></span> " + badge("UNVERIFIED"),
                    badge("DERIVED"),
                    link(r["source_results"], "schedule") + " " + link(r["source_game_page"], "game centre"),
                ])
        tbl = table(["Matchup", "Market (origination order)", "Fair line", "Our fair price",
                     "Market line", "Market price", "Difference", "State", "Sources"], rows,
                    tid="mk",
                    note="The fair line and the fair price are ours and are labelled DERIVED. The "
                         "market line, the market price and the difference are blank because no "
                         "official NFL price publication exists (F-18) - they are not zero and not "
                         "estimated. A 'difference' is only meaningful against a real price, so it "
                         "stays empty until one exists.")

        back = table(["Check", "Result", "Reading"],
                     [["Walk-forward games scored", str(bt["n"]),
                       "every game from week 3 onward; weeks 1-2 have fewer than two complete weeks of "
                       "history, so nothing is published for them"],
                      ["MAE, our side vs a constant home -2.5",
                       f"{bt['mae_margin']} vs {bt['mae_margin_naive_-2.5']} points",
                       "our side model is better than the constant by "
                       f"{bt['mae_margin_naive_-2.5'] - bt['mae_margin']:+.2f} points, with the "
                       "interval on that difference published on the leaderboard page"],
                      ["MAE, our total vs a constant 45.0",
                       f"{bt['mae_total']} vs {bt['mae_total_naive_45.0']} points",
                       "our total model is WORSE than the constant on this sample; published as-is "
                       "(F-21)"],
                      ["Side direction hit rate",
                       f"{bt['side_direction_hit']}/{bt['n']} = {bt['side_direction_rate']:.1%}",
                       f"home win rate in the same sample is {bt['home_win_rate_in_sample']:.1%}, so "
                       "the hit rate must be read against that baseline, not against 50%"],
                      ["r(predicted margin, actual margin)",
                       f"{bt['r_pred_actual_margin']:+.4f} "
                       f"[{bt['r_ci95'][0]:+.4f}, {bt['r_ci95'][1]:+.4f}]",
                       "the model's ranking of games is real and modest; the interval is published"],
                      ["sigma used to turn a margin into a probability", f"{bt['sigma_margin']} points",
                       "sd of walk-forward residuals. It is the model's own error bar, and it is why "
                       "a fair line is not a prediction of the score"]],
                     kind="meta",
                     note="Recomputed by tools/markets_engine.py on every build from "
                          "data/x3/verified/results.json. No number on this page is typed by hand.")

        order = table(["Step", "Market", "How it is produced", "Why in this order"],
                      [["1", "Side (handicap)",
                        "margin model on final scores: home_margin = hfa + net[home] - net[away]",
                        "the side is the strongest of the three and does not depend on the other two"],
                       ["2", "Total",
                        "separate pace model on the same finals: total = base + pace[home] + pace[away]",
                        "fitted second because it is the weaker model; side and total are only "
                        "weakly related (measured r published on the correlation page), so the total "
                        "cannot borrow the side's evidence"],
                       ["3", "Moneyline",
                        "P(home win) = Phi(margin / sigma), sigma from walk-forward residuals",
                        "a moneyline is a side with the handicap removed, so it inherits the side's "
                        "error by construction and is never priced from an independent guess"]],
                      kind="meta")
        priors = table(["Parameter", "Value", "Evidence", "Status"],
                       [["home-field advantage", f"{markets['model']['hfa_points']:+.3f} points",
                         "fitted on 2026 finals, neutral-site games excluded from the estimate",
                         "DERIVED - differs from X3-v1, which applies 0.0 (F-19)"],
                        ["league average team score",
                         f"{markets['model']['league_avg_team_score']:.2f}",
                         "fitted total model intercept / 2", "DERIVED"],
                        ["sigma (margin)", f"{markets['sigma_margin']} points",
                         "sd of walk-forward residual", "DERIVED"],
                        ["training window", f"{markets['model']['n_games']} final games",
                         "2026 weeks 1-10 from the verified results feed", "VERIFIED inputs"],
                        ["market prices", "", "no official NFL price publication exists (F-18)",
                         "UNVERIFIED - blank"]],
                       kind="meta")
        body = f"""
<section class="callout"><h2>The order is the requirement</h2>
<p>Side first, then the total, then the moneyline. That order is not cosmetic: the moneyline is
derived from the side model's margin distribution, so it cannot be priced before the side exists,
and the total is fitted separately because borrowing the side's evidence for it would double-count
the same games.</p></section>
<h2>Origination order, step by step</h2>
{order}
<h2>Our numbers for the unplayed slate ({len(markets['live'])} games, {len(rows)} market rows)</h2>
<p class="lede">Three markets per game. Fair line and fair price are ours. Market line, market price
and difference are blank and flagged: the official game centre for a Week-10 game carries
participation, team stats and standings and no odds at all, and nfl.com/odds/ returns 404 (both
checked {AS_OF}).</p>
<input class="filt" data-for="mk" placeholder="filter: team, market, side, total, moneyline...">
{tbl}
<h2>How the numbers behave out of sample</h2>
{back}
<h2>Parameters behind the board</h2>
{priors}
"""
        page("markets.html", "Originated markets: side, total, moneyline",
             "Our own line for every unplayed game, originated in the order the arithmetic "
             "allows, with the fair line, the market line and the difference kept as separate "
             "columns.", body, "markets")

    # =====================================================================
    # 2. PRICE SNAPSHOT STORE
    # =====================================================================
    def p_store():
        st = markets["store"]
        mv = st["movement"]
        head = table(["Quantity", "Value", "What it means"],
                     [["markets in the store", f"{st['markets']}",
                       "one row per market per side, across games we have originated"],
                      ["rows with a recorded close", f"{st['closing_recorded']}",
                       "every played game, refitted on all finals dated before kickoff"],
                      ["rows with a close still PENDING", f"{st['closing_pending']}",
                       "the unplayed slate: the close does not exist yet and is never imputed"],
                      ["snapshot files written", f"{st['snapshots_written']}",
                       "one file per build date in data/x3/verified/snapshots/<date>.json, append-only"],
                      ["open-to-close pairs we can measure",
                       f"{mv['pairs_recorded']}",
                       f"mean |movement| {mv['mean_abs_movement_points']} points, max "
                       f"{mv['max_abs_movement_points']}; {mv['moved']} of {mv['pairs_recorded']} "
                       "moved at all"],
                      ["market open / close", "",
                       "UNVERIFIED - no official NFL price publication exists (F-18), so there is "
                       "nothing to snapshot"]],
                     kind="meta",
                     note="Counts are read from data/x3/verified/markets.json at build time.")

        demo = []
        for r in markets["live"][:6]:
            demo.append([f"<b>{esc(r['away'])} at {esc(r['home'])}</b>",
                         "side (home)", f"{r['side_fair_line']:+.1f}", "PENDING",
                         "PENDING", badge("UNVERIFIED"), badge("DERIVED"),
                         link(r["source_results"], "schedule")])
        for g in markets["backtest_markets"][:6]:
            demo.append([f"<b>{esc(g['away'])} at {esc(g['home'])}</b><br><span class='mut'>week "
                         f"{esc(str(g['week']))}</span>",
                         "side (home)", f"{g['side_open']:+.1f}", f"{g['side_close']:+.1f}",
                         f"{g['side_close'] - g['side_open']:+.1f}", badge("DERIVED"),
                         badge("VERIFIED"), link(g["source"], "schedule")])
        demotbl = table(["Game", "Market", "Open", "Close", "Movement", "Market price", "State",
                         "Source"], demo, tid="ps",
                        note="Six rows from each end of the store. Open and close are OUR numbers; "
                             "the market columns belong to a source that does not exist, so they are "
                             "blank. A reconstructed close is labelled as such in the CSV's note "
                             "column - it is not a captured price.")

        definition = table(["Concept", "Definition used here", "Why this definition"],
                           [["Open (played game)", "our number fitted on finals from weeks before "
                             "the game's week", "it is what we could have published on the Tuesday"],
                            ["Close (played game)", "our number fitted on every final dated before "
                             "that game's kickoff", "it is the last number we could have published "
                             "before the ball was kicked"],
                            ["Open (unplayed game)", "our number fitted on every final available now",
                             "one capture, no second observation yet"],
                            ["Close (unplayed game)", "PENDING", "the event has not happened; "
                             "imputing it would be inventing the thing the store exists to record"],
                            ["Market open / close", "blank", "no official price exists (F-18) and "
                             "none may be inferred from our own model"]],
                           kind="meta")
        body = f"""
<section class="callout"><h2>What this store is for</h2>
<p>A backtest is only as good as the numbers it grades. This store gives every market we originate
a dated opening and closing observation in a committed file, so a future backtest grades the number
we actually published rather than a number refitted with hindsight. It deliberately does not contain
a market price: that column is blank because no official source publishes one.</p></section>
{head}
<h2>Open and close, defined before anything is measured</h2>
{definition}
<h2>Rows from both ends of the store</h2>
<input class="filt" data-for="ps" placeholder="filter: team, PENDING, week...">
{demotbl}
<h2>Honest limits</h2>
<p class="lede">There is one snapshot milestone so far, so every close in the store is a
<em>reconstructed</em> close (our own model refitted), not a captured one. The movement figures above
are therefore the movement of our own number, and are labelled that way wherever they appear. Turning
this into a real open/close record needs a scheduled capture, which is suggestion S-17.</p>
"""
        page("price-store.html", "Price snapshot store",
             "Every market we originate gets a dated opening and closing observation in a committed, "
             "append-only store - and a blank market column, because no official price exists.",
             body, "price-store")

    # =====================================================================
    # 3. VERIFIED RESULTS FEED
    # =====================================================================
    def p_results():
        c = results["checks"]
        cnt = results["counts"]
        cards = "".join(
            f'<div class="card"><div class="num">{v}</div><div class="lbl">{k}</div>'
            f'<div class="sub">{s}</div></div>' for k, v, s in [
                ("games in the feed", cnt["games_total"], "every scheduled 2026 game in the capture"),
                ("final games", cnt["finals"], "both scores present; nothing imputed"),
                ("clubs reconciled", cnt["clubs"], "all 32, against the official standings"),
                ("standings mismatches", c["R2_standings_reconciliation"]["mismatches"],
                 "W-L-T-PF-PA-games played, per club"),
            ])
        checks = table(["Check", "Rule", "Result", "Source"],
                       [["R1 completeness", c["R1_completeness"]["rule"],
                         f"{c['R1_completeness']['dropped']} rows dropped",
                         link(results["sources"]["schedule"], "week pages")],
                        ["R2 standings reconciliation", c["R2_standings_reconciliation"]["rule"],
                         f"{c['R2_standings_reconciliation']['clubs_compared']} clubs compared, "
                         f"{c['R2_standings_reconciliation']['mismatches']} mismatches",
                         link(results["sources"]["standings"], "standings")],
                        ["R3 box-score sample", c["R3_box_score_sample"]["rule"],
                         f"{c['R3_box_score_sample']['agreed']}/{c['R3_box_score_sample']['checked']} "
                         "agree", link(c["R3_box_score_sample"]["source"], "week 1")]],
                       kind="meta",
                       note="The three checks are run on every build by tools/results_feed.py; a "
                            "failure exits non-zero and CI blocks the deploy.")

        agg = []
        for r in c["R2_standings_reconciliation"]["rows"]:
            f, s = r["feed"], r["standings"]
            agg.append([f"<b>{esc(r['team'])}</b>",
                        f"{f['w']}-{f['l']}-{f['t']}", f"{f['pf']}", f"{f['pa']}", str(f["g"]),
                        f"{s['w']}-{s['l']}-{s['t']}", f"{s['pf']}", f"{s['pa']}", str(s["g"]),
                        badge("VERIFIED") if r["agree"] else badge("FAIL"),
                        link(results["sources"]["standings"], "standings")])
        aggtbl = table(["Club", "Results W-L-T", "PF", "PA", "GP", "Standings W-L-T", "PF", "PA",
                        "GP", "Agree", "Source"], agg, tid="ag",
                       note="The left block is our feed's own arithmetic over the final scores; the "
                            "right block is the official standings transcription. Agreement is what "
                            "authorises this feed to be used for backtests.")

        rows = []
        for r in results["rows"]:
            rows.append([
                str(r["week"]), esc(r["date_iso"]),
                f"<b>{esc(r['away'])}</b> at <b>{esc(r['home'])}</b>"
                + (" <span class='mut'>(neutral)</span>" if r["neutral_site"] else ""),
                (f"{r['away_score']}-{r['home_score']}" if r["status"] == "FINAL" else "scheduled"),
                (f"{r['margin_home']:+d}" if r["margin_home"] != "" else ""),
                (f"{r['total']}" if r["total"] != "" else ""),
                badge("VERIFIED") if r["status"] == "FINAL" else badge("UNVERIFIED"),
                link(r["source"], f"week {r['week']}"),
            ])
        gametbl = table(["Week", "Date", "Game", "Score", "Home margin", "Total", "State", "Source"],
                        rows, tid="res",
                        note="Scheduled rows carry no score and are marked UNVERIFIED rather than "
                             "given a placeholder. Totals and margins are arithmetic on the two "
                             "scores in the same row.")
        avail = table(["Week", "Report rows", "Source"],
                      [[str(a["week"]), str(a["rows"]), link(a["source"], f"week {a['week']} report")]
                       for a in results["availability_feed"]],
                      kind="meta",
                      note="The availability feed the backtests can join to: the official weekly "
                           "injury report, per week, as captured.")
        body = f"""
<div class="grid">{cards}</div>
<h2>Why this feed can be trusted enough to backtest on</h2>
<p class="lede">A results feed that is not reconciled is a source of confident nonsense. Three
independent checks run on every build: completeness (a final without both scores is dropped, never
filled), reconciliation to the official standings through a different page transcribed by a
different session, and a score-by-score comparison of a sample against a live read.</p>
{checks}
<h2>Reconciliation, club by club</h2>
<input class="filt" data-for="ag" placeholder="filter: club, FAIL...">
{aggtbl}
<h2>The feed, row by row ({len(results['rows'])} games)</h2>
<input class="filt" data-for="res" placeholder="filter: team, week, scheduled...">
{gametbl}
<h2>Availability feed</h2>
{avail}
<h2>Why there is a second results page</h2>
<p class="note">A parallel session also publishes a results page at
<a href="results.html">hub/results.html</a>, built from its own capture of the same official week
pages. Both reconcile to the same official standings with zero mismatches. They are kept side by side
rather than merged or overwritten, and that duplication is recorded as flag F-27.</p>
<h2>Limits, stated on the feed itself</h2>
<ul>{''.join(f'<li>{esc(x)}</li>' for x in results['limitations'])}</ul>
"""
        page("verified-results.html", "Verified results feed",
             "One row per scheduled game, reconciled to the official standings with zero mismatches, "
             "so a backtest has something real to grade.", body, "verified-results")

    # =====================================================================
    # 4. DEPTH OF THE REPLACEMENT
    # =====================================================================
    def p_replacements():
        c = depth["counts"]
        cards = "".join(
            f'<div class="card"><div class="num">{v}</div><div class="lbl">{k}</div>'
            f'<div class="sub">{s}</div></div>' for k, v, s in [
                ("absences, Out or Doubtful", c["absences_out_or_doubtful"],
                 "the population this page resolves"),
                ("replacement named", c["replacement_named"],
                 "man and chart tier both known from a club chart"),
                ("still UNVERIFIED", c["replacement_unverified"],
                 "no chart match, a cross-role match refused, or the chain exhausted"),
                ("3rd string or deeper", c["replaced_by_3rd_string_or_deeper"],
                 "the absences that actually cost depth"),
            ])
        rows = []
        for r in depth["rows"]:
            rows.append([
                f"<b>{esc(r['club'])}</b>", esc(r["player"]), esc(r["pos"]), esc(r["unit"]),
                esc(r["status"]),
                (str(r["tier"]) if r["tier"] != "" else ""),
                (f"<b>{esc(r['replacement'])}</b>" if r["replacement"] else ""),
                (esc(r["depth_of_replacement"]) if r["depth_of_replacement"] else ""),
                (badge("VERIFIED") if r["state"] == "VERIFIED" else badge("UNVERIFIED")),
                esc(r["why"]) if r["why"] else esc(r["chain"]),
                link(r["source_report"], "report")
                + (" " + link(r["chart_url"], "chart") if r["chart_url"] else ""),
            ])
        tbl = table(["Club", "Unavailable", "Pos", "Unit", "Designation", "His tier",
                     "Replacement", "Depth of replacement", "State", "Evidence", "Sources"],
                    rows, tid="rep",
                    note="'His tier' is where the unavailable player sits on his club's chart. "
                         "'Depth of replacement' is the tier of the first man below him who is not "
                         "himself Out or Doubtful in the same official report. A blank replacement "
                         "with UNVERIFIED is a refusal, not an omission.")
        clubs = table(["Club", "Absences", "Starters out", "Off", "Def", "ST", "Deepest replacement",
                       "Mean replacement tier", "Chart as-of", "Sources"],
                      [[f"<b>{esc(c['club'])}</b>", str(c["absences"]), str(c["starters_out"]),
                        str(c["offence"]), str(c["defence"]), str(c["st"]),
                        esc(c["deepest"]) if c["deepest"] else "",
                        (str(c["mean_replacement_tier"]) if c["mean_replacement_tier"] != "" else ""),
                        esc(c["chart_as_of"]) if c["chart_as_of"] else "no date printed",
                        (link(c["chart_url"], "chart") if c["chart_url"]
                         else badge("UNVERIFIED") + " " + link(X.S["injuries"], "report"))]
                       for c in depth["clubs"]],
                      tid="clubd",
                      note="A club with an empty 'deepest replacement' has no resolvable absence at "
                           "this snapshot. 'No date printed' is the common case: only 5 of 32 club "
                           "charts carry an as-of date. Houston publishes its chart as an image only, "
                           "so its row carries no chart link and is badged UNVERIFIED.")
        deepest = table(["Club", "Player", "Pos", "Designation", "Replacement", "Depth", "Sources"],
                        [[f"<b>{esc(r['club'])}</b>", esc(r["player"]), esc(r["pos"]),
                          esc(r["status"]), f"<b>{esc(r['replacement'])}</b>",
                          esc(r["depth_of_replacement"]),
                          link(r["chart_url"], "chart") + " " + link(r["source_report"], "report")]
                         for r in depth["deepest_holes"] if r["replacement"]],
                        tid="deep",
                        note="The deepest holes on the Week-10 slate, worst first.")
        body = f"""
<div class="grid">{cards}</div>
<section class="callout"><h2>Depth of the replacement, not the fact of one</h2>
<p>Two absences at the same position are not the same event. This page resolves every official
Out/Doubtful designation to the man who replaces him and to his rung on the club's chart, by walking
down the chart from the unavailable player to the first name that is not also unavailable in the same
report. Where that walk cannot be completed from an official source, the row is published UNVERIFIED
with the reason - it is never filled with a plausible name.</p></section>
<h2>Deepest holes this week</h2>
{deepest}
<h2>Per-club summary</h2>
<input class="filt" data-for="clubd" placeholder="filter: club...">
{clubs}
<h2>Every absence, resolved or refused ({len(depth['rows'])} rows)</h2>
<input class="filt" data-for="rep" placeholder="filter: club, position, third string...">
{tbl}
<h2>Limits of the source</h2>
<ul>{''.join(f'<li>{esc(x)}</li>' for x in depth['limits'])}</ul>
"""
        page("replacements.html", "Depth of the replacement",
             "Every officially unavailable player resolved to the man who replaces him and to that "
             "man's rung on the club chart - or published unverified with the reason.",
             body, "replacements")

    # =====================================================================
    # 5. signal vs staking - rendered inside leaderboard by build_hub
    # =====================================================================
    def leaderboard_blocks():
        ev = strat["signal_evidence"]
        srows = []
        for s in strat["strategies"]:
            sig = s["signal_status"]
            srows.append([
                f"<b>{esc(s['id'])}</b>", esc(s["name"]), esc(s["family"]),
                (f"{s['signal_score']:+.3f}" if isinstance(s["signal_score"], (int, float)) else ""),
                (f"[{s['signal_ci'][0]:+.3f}, {s['signal_ci'][1]:+.3f}]"
                 if s["signal_ci"] and None not in s["signal_ci"] else ""),
                (str(s["signal_n"]) if s["signal_n"] else ""),
                badge("ESTABLISHED" if sig == "ESTABLISHED" else
                      ("FAILED" if sig == "FAILED" else
                       ("PARTIAL" if sig == "INCONCLUSIVE" else "NOT RUN"))) + " " + esc(sig),
                "<span class='blank'></span>",
                badge("BLOCKED"),
                (str(s["rank"]) if s["rank"] else "-"),
                "PAPER",
            ])
        stbl = table(["Strategy", "Name", "Family", "Signal score", "Signal 95% CI", "n",
                      "Signal verdict", "Staking score", "Staking state", "Rank", "Tier"], srows,
                     tid="sigs",
                     note="The signal column is measured on outcomes with n and an interval. The "
                          "staking column is empty and BLOCKED because no price exists, so no "
                          "staking number can stand in for a signal number. A strategy is ranked "
                          "only when both columns exist.")
        contract = table(["Rule", "Consequence"],
                         [[esc(x), ""] for x in strat["scoring_contract"]], kind="meta")
        dem = strat["demotion_gate"]
        def _res(cid):
            for k, v in dem["results"].items():
                if k.startswith(cid + "_"):
                    return v
            return {"fires": False}
        demrows = [[f"<b>{esc(cl['id'])}</b>", esc(cl["condition"]),
                    (badge("FAIL") + " FIRING") if _res(cl["id"])["fires"] else "clear",
                    esc(json.dumps({kk: vv for kk, vv in _res(cl["id"]).items()
                                    if kk != "fires"}, default=str)[:240])]
                   for cl in dem["clauses"]]
        demtbl = table(["Clause", "Condition", "State now", "Measured value"], demrows,
                       kind="meta",
                       note="Evaluated on every build by tools/strategies_engine.py against "
                            + esc(dem["evaluated_against"]) + ". Verdict: " + esc(dem["verdict"]))
        evid = table(["Object", "Value", "n", "Reading"],
                     [["Paired improvement in absolute margin error vs the constant -2.5",
                       f"{ev['margin']['mean_improvement']:+.3f} pts",
                       str(ev["n_games"]),
                       f"95% CI [{ev['margin']['ci95'][0]:+.3f}, {ev['margin']['ci95'][1]:+.3f}] - "
                       "contains zero, so the label is INCONCLUSIVE"],
                      ["Paired improvement in absolute total error vs the constant 45.0",
                       f"{ev['total']['mean_improvement']:+.3f} pts", str(ev["n_games"]),
                       f"95% CI [{ev['total']['ci95'][0]:+.3f}, {ev['total']['ci95'][1]:+.3f}] - "
                       "the model is worse than the constant"],
                      ["Direction hit rate", f"{ev['direction']['rate']:.1%}", str(ev["n_games"]),
                       f"always-away baseline {ev['direction']['baseline_always_away']:.1%}; "
                       f"advantage {ev['direction']['advantage_over_always_away']:+.3f} per game, CI "
                       f"[{ev['direction']['advantage_ci95'][0]:+.3f}, "
                       f"{ev['direction']['advantage_ci95'][1]:+.3f}]"],
                      ["Brier score, model moneyline", f"{ev['moneyline_calibration']['brier']:.4f}",
                       str(ev["n_games"]),
                       f"base-rate Brier {ev['moneyline_calibration']['brier_base_rate']:.4f} - "
                       + ev["moneyline_calibration"]["reading"]],
                      ["Variants tried (multiple testing)",
                       str(ev["multiple_testing"]["variants_tried"]),
                       str(ev["n_games"]),
                       f"corrected threshold on any single test: {ev['multiple_testing']['note']}"]],
                     kind="meta",
                     note="This is the luck-removal evidence in full. Nothing here is a return claim; "
                          "it is a statement about whether the forecast carries information.")
        return stbl, contract, demtbl, evid, ev

    # =====================================================================
    # 6. correlation page blocks (official numbers only, n published)
    # =====================================================================
    def correlation_blocks():
        rows = [[esc(r["x"]), esc(r["y"]),
                 (f"<b>{r['value']:+.4f}</b>" if r["value"] is not None else ""),
                 (f"[{r['ci95_low']:+.3f}, {r['ci95_high']:+.3f}]"
                  if r["ci95_low"] is not None else ""),
                 (f"{r['r2']:.3f}" if r["r2"] is not None else ""),
                 str(r["n"]), esc(r["note"]), link(r["source"], "source")]
                for r in corr["rows"]]
        computed = table(["Variable X", "Variable Y", "r", "95% CI (Fisher z)", "R^2", "n", "Reading",
                          "Official source"], rows, tid="corx",
                         note="Every row here is computed from a transcribed official page and "
                              "carries its n. A row without n would be a claim, not a measurement, "
                              "and the builder refuses one.")
        brows = [[esc(r["x"]), esc(r["y"]), "<span class='blank'></span>", badge("UNVERIFIED"),
                  esc(r["note"]), esc(r["data_required"]), link(r["source"], "rule source")]
                 for r in corr["blank_rows"]]
        blank = table(["Relationship", "Between", "Value", "State", "Why it is blank",
                       "What would fill it", "Source"], brows, tid="corblank",
                      note="These are the coefficients a parlay or prop model actually needs. No "
                           "official publication contains them, so they are published as structure "
                           "with the missing artefact named rather than filled with an estimate.")
        return computed, blank

    return {
        "p_markets": p_markets,
        "p_store": p_store,
        "p_results": p_results,
        "p_replacements": p_replacements,
        "leaderboard_blocks": leaderboard_blocks,
        "correlation_blocks": correlation_blocks,
        "data": {"markets": markets, "results": results, "depth": depth, "corr": corr,
                 "strat": strat},
    }
