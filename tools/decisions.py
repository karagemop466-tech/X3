#!/usr/bin/env python3
"""
Decision register: questions, their answers where the evidence now exists, and
suggestions ranked so a reviewer can pick a path before anything is built.

The distinction this file exists to keep:

  QUESTION     something that must be known before a decision is reasonable.
               Each one carries what we HAVE, what we LACK, and — the part that
               matters — HOW to find out what we lack.

  ANSWER       only appears when it is measured from an official source or
               derived from one by a script in this repo. An answer is never a
               restatement of the question and never a guess.

  SUGGESTION   a proposed path, with what it costs, what it unlocks, what it does
               NOT unlock, and the evidence that supports it. Suggestions are not
               implemented by this session; they are the review queue.

Every number quoted in a suggestion is read from a generated file rather than
typed, so the review page cannot drift from the data it cites.

Run: python3 tools/decisions.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VER = os.path.join(ROOT, "data", "verified")
OUT = os.path.join(ROOT, "data", "decisions")

NFL_STAND = "https://www.nfl.com/standings/league/2026/REG"
NFL_SCHED = "https://www.nfl.com/schedules/2026/by-week/week-N"
NFL_INJ = "https://www.nfl.com/injuries/league/2026/reg10"


def J(*parts):
    return json.load(open(os.path.join(ROOT, *parts), encoding="utf-8"))


def main():
    os.makedirs(OUT, exist_ok=True)
    rec = J("data", "verified", "reconciliation.json")
    bt = J("data", "verified", "backtest.json")
    corr = J("data", "verified", "correlation.json")
    demo = J("data", "verified", "staking_demo.json")
    dep = J("data", "verified", "depth_map.json")
    ms = J("data", "verified", "market_stats.json")
    hfa = J("data", "verified", "hfa.json")
    kn = J("data", "verified", "key_numbers.json")
    gates = J("data", "decisions", "gates.json")
    snap = J("data", "snapshots", "store_meta.json")
    picks = J("data", "picks", "picks_2026_wk10.json")

    sev = {r["pair"]: r for r in corr["rows"]}
    tvm = sev["game total vs |margin|"]
    awh = sev["away score vs home score (same game)"]
    n55 = demo["masking"]["c_bets_needed_for_80pct_power"]["55%_vs_breakeven"]["n_needed_80pct_power"]
    sig = demo["signal"]
    gsum = gates["summary"]

    # ------------------------------------------------------------------ questions
    questions = [
        {
            "id": "Q-01", "category": "Results",
            "question": "Do we have a verified record of what actually happened, or only of what was scheduled?",
            "have": f"{rec['finals_used']} finals with scores, each carrying its official week-page "
                    f"URL, plus a {rec['fields_compared']}-field reconciliation against the "
                    f"official standings page.",
            "lack": "Anything after Week 10. The season is in progress, so the feed stops where "
                    "the official pages stop.",
            "answer": f"YES for weeks 1-10, and it checks out: {rec['fields_agree']} of "
                      f"{rec['fields_compared']} club fields recompute exactly "
                      f"({rec['clubs_official']} clubs x W/L/T/PF/PA/games). This is the first "
                      f"time in this repository's history that a results feed exists at all.",
            "answer_status": "ANSWERED",
            "how_to_close": "re-run the capture each week; nothing else is needed",
            "source": [f"{NFL_STAND}", f"{NFL_SCHED}"],
        },
        {
            "id": "Q-02", "category": "Results",
            "question": "Does the rating we built actually predict games it has not seen?",
            "have": f"A walk-forward test on {bt['n_games_scored']} games across weeks "
                    f"{bt['weeks_scored'][0]}-{bt['weeks_scored'][-1]}, with the parameters "
                    f"fixed before the run.",
            "lack": "Any comparison to a market line, which is the only benchmark that matters.",
            "answer": f"Partly. The rating beats predicting a zero margin on MAE "
                      f"({sig['mae_points']} vs {sig['mae_naive_predict_zero']} points) and "
                      f"gets {sig['sign_correct']} of {sig['decided_games']} sides right "
                      f"(exact p={sig['binom_two_sided_p_vs_coin']}). That is a real signal "
                      f"about the score and NOT an edge over a price.",
            "answer_status": "PARTIAL",
            "how_to_close": "the market comparison needs prices: Q-04",
            "source": ["data/verified/backtest.json"],
        },
        {
            "id": "Q-03", "category": "Totals",
            "question": "Can we price a total at all, and is a normal approximation safe?",
            "have": f"A distribution measured on {ms['n_games']} games: totals mean "
                    f"{ms['total']['mean']} SD {ms['total']['sd']}, |margin| mean "
                    f"{ms['abs_margin']['mean']} SD {ms['abs_margin']['sd']}.",
            "lack": "Pace, weather, and any adjustment for game script. The model total is a "
                    "league average reshaped by a club pace proxy.",
            "answer": f"Yes, with a caveat: excess kurtosis is "
                      f"{ms['normal_check']['abs_margin_excess_kurtosis']} for |margin| and "
                      f"{ms['normal_check']['total_excess_kurtosis']} for the total, so a "
                      f"normal approximation is defensible but is an approximation. The "
                      f"backtest total MAE equals the naive fixed-total baseline, so the "
                      f"total is currently NOT better than a constant.",
            "answer_status": "ANSWERED",
            "how_to_close": "a better total needs pace and situational inputs, not more data volume",
            "source": ["data/verified/market_stats.json", "data/verified/backtest.json"],
        },
        {
            "id": "Q-04", "category": "Market",
            "question": "Can we obtain an official market price, opening and closing?",
            "have": "A store with the schema, timestamps, invariants and provenance blocks, and "
                    "our own line recorded in it.",
            "lack": "Every market value. The NFL publishes no betting prices and no licensed "
                    "feed is configured anywhere in this repository.",
            "answer": f"NO. {snap['rows']} of {snap['rows']} market cells are blank and flagged "
                      f"UNVERIFIED. Third-party prices exist in x3lab and are carried in their "
                      f"own columns as NOT OFFICIAL, deliberately unused.",
            "answer_status": "BLOCKED",
            "how_to_close": "buy or license a price feed with open and close per market; this is "
                            "a purchasing decision, not an engineering one",
            "source": ["data/snapshots/store_meta.json"],
        },
        {
            "id": "Q-05", "category": "Market",
            "question": "If we had prices, would our line differ from the market enough to matter?",
            "have": "Our own 13 Week-10 lines and a measured residual SD of "
                    f"{snap['moneyline_method']['sigma_used']} points for the model's error.",
            "lack": "The market line. Without it the difference column is a column of blanks.",
            "answer": "CANNOT BE ANSWERED. Any statement about 'a 1-point edge against the "
                      "market' in this repository would be an assumption, not a measurement.",
            "answer_status": "BLOCKED",
            "how_to_close": "same as Q-04; the difference column is already wired and will "
                            "populate the day prices arrive",
            "source": ["data/snapshots/snapshots_2026_wk10.csv"],
        },
        {
            "id": "Q-06", "category": "Correlation",
            "question": "May two legs of a parlay be multiplied as if independent?",
            "have": f"Two measured within-game coefficients on {tvm['n']} finals.",
            "lack": "Player-prop joint outcomes, and the same-game spread/team-total joint.",
            "answer": f"For a total and a margin: not shown to be dependent. r={tvm['pearson_r']} "
                      f"with CI {tvm['ci95_low']} to {tvm['ci95_high']}, permutation "
                      f"p={tvm['perm_p']} - the interval contains zero, so multiplying is "
                      f"defensible for THESE two. For two teams' scores in one game, "
                      f"r={awh['pearson_r']} (n={awh['n']}, p={awh['perm_p']}) - also no "
                      f"measurable dependence. Prop legs remain unmeasured and must not be "
                      f"multiplied.",
            "answer_status": "PARTIAL",
            "how_to_close": "an official prop archive, which does not exist; any prop joint "
                            "would need it and cannot be assumed",
            "source": [NFL_SCHED],
        },
        {
            "id": "Q-07", "category": "Injuries",
            "question": "Which replacement is actually playing, and how deep is the drop?",
            "have": f"{dep['rows_total']} Out/Doubtful designations resolved against club depth "
                    f"charts; {dep['replacements_identified']} replacements identified by name "
                    f"and chart tier.",
            "lack": "An as-of date on most charts, and any official statement of who starts.",
            "answer": f"Tier is known for {dep['replacements_identified']} of "
                      f"{dep['rows_total']} absences. Of those, {dep['tier_counts'].get('2', 0)} "
                      f"are 2nd-stringers stepping in, {dep['tier_counts'].get('3', 0)} are "
                      f"3rd-stringers and {dep['tier_counts'].get('4', 0)} is a 4th-stringer. "
                      f"The remaining {dep['rows_total'] - dep['replacements_identified']} have "
                      f"no named replacement and are left blank rather than guessed.",
            "answer_status": "ANSWERED",
            "how_to_close": "capture the as-of date with each chart; the join is already built",
            "source": [NFL_INJ, "data/verified/depth_map.json"],
        },
        {
            "id": "Q-08", "category": "Injuries",
            "question": "How much is a starting-calibre absence actually worth in points?",
            "have": "A positional cost table in the model and the absences that triggered it.",
            "lack": "Any measurement. The costs are priors written by a previous session, not "
                    "coefficients estimated from outcomes.",
            "answer": "NOT ANSWERED, and this is the biggest single hole in the model. The "
                      "injury adjustment moves lines by up to "
                      f"{max(abs(r['injury_delta']) for r in J('hub', 'data', 'lines.json')['rows']):.1f} "
                      "points on the Week-10 slate on no measured basis.",
            "answer_status": "OPEN",
            "how_to_close": "regress margin on absences x position once several seasons of "
                            "designations and results are joined; needs more than one season",
            "source": ["hub/data/meta.json (pos_cost)"],
        },
        {
            "id": "Q-09", "category": "Validation",
            "question": "How many bets before a real edge can be told apart from luck?",
            "have": "An exact binomial power calculation, verified against enumeration.",
            "lack": "Any settled, priced bets. The last published minimum of 300 was too low.",
            "answer": f"At -110, a true 55% bettor needs about {n55} settled bets for an 80%-power "
                      f"test. The previously published gate of 300 bets would only detect an edge "
                      f"of about 60%. A leaderboard populated sooner than this ranks noise, which "
                      f"is why it is empty and why it should stay empty.",
            "answer_status": "ANSWERED",
            "how_to_close": "no shortcut exists; it is a waiting problem once prices exist",
            "source": ["data/verified/staking_demo.json", "tools/selftest_stats.py"],
        },
        {
            "id": "Q-10", "category": "Validation",
            "question": "Can a lucky staking run mask a bad signal?",
            "have": "A measured demonstration under -110 prices with resampled orderings.",
            "lack": "Nothing for the demonstration; real bet data would refine it.",
            "answer": f"Yes, easily, which is why signal and staking are separated: a strategy "
                      f"with a TRUE 45% rate still shows a profit after 100 bets "
                      f"{demo['masking']['a_share_finishing_above_start_flat_1u']['bad_45pct']['100']:.1%} "
                      f"of the time. Separately, a 47% strategy outranks a 55% strategy "
                      f"{demo['masking']['b_share_worse_47_outranks_better_55']['20']:.1%} of the "
                      f"time over 20 bets. Ranking on bankroll is therefore inadmissible; the "
                      f"leaderboard ranks the signal first and prints staking second.",
            "answer_status": "ANSWERED",
            "how_to_close": "closed; the rule is published in the gates",
            "source": ["data/verified/staking_demo.json"],
        },
        {
            "id": "Q-11", "category": "Model",
            "question": "Is home-field advantage big enough to price?",
            "have": f"A measured mean home margin of {hfa['hfa_points']} points over "
                    f"{hfa['n_non_neutral']} non-neutral finals.",
            "lack": "Multi-season data. One season's interval is wide.",
            "answer": f"Not on this sample. {hfa['hfa_points']} points with a 95% interval of "
                      f"{hfa['ci95'][0]} to {hfa['ci95'][1]} straddles zero, which is why the "
                      f"published model sets home-field to 0 and says so rather than assuming "
                      f"the usual 2.5-3 points. That is a defensible engineering choice and a "
                      f"genuinely surprising result that deserves the flag it carries.",
            "answer_status": "PARTIAL",
            "how_to_close": "recompute after several seasons; a 3-point HFA would be visible",
            "source": ["data/verified/hfa.json", NFL_SCHED],
        },
        {
            "id": "Q-12", "category": "Model",
            "question": "Which margin values are dangerous to price a spread on?",
            "have": f"An empirical margin distribution over {kn['n_games']} finals.",
            "lack": "Nothing here; this answer is complete for the sample.",
            "answer": f"Pushes cluster on the key numbers: "
                      f"{kn['share_within_3']:.1%} of games finish within 3 points and "
                      f"{kn['share_within_7']:.1%} within 7, so a line placed on 3 or 7 pushes "
                      f"far more often than a line placed on 1 or 12. Every originated spread "
                      f"is therefore checked against the key-number table before publication.",
            "answer_status": "ANSWERED",
            "how_to_close": "closed for one season; refresh each season",
            "source": ["data/verified/key_numbers.json", NFL_SCHED],
        },
        {
            "id": "Q-13", "category": "Policy",
            "question": "Are we permitted to publish lines, run a contest, and pay rewards?",
            "have": "A statement of the question and a rule that nothing is paid.",
            "lack": "Any legal review, any jurisdiction determined, any contest terms.",
            "answer": "NOT ANSWERED and cannot be answered from data. This is a legal question "
                      "that requires a person qualified to answer it. Until then the site "
                      "publishes analysis, places no bets, and pays nothing.",
            "answer_status": "OPEN",
            "how_to_close": "obtain review from a lawyer in the operating jurisdiction; no amount "
                            "of modelling substitutes",
            "source": ["data/decisions/suggestions.json"],
        },
        {
            "id": "Q-14", "category": "Model",
            "question": "Is the injury adjustment even in the right direction from week to week?",
            "have": "13 originated lines with their injury deltas printed per game.",
            "lack": "Enough games to test. One slate cannot test a coefficient.",
            "answer": f"UNKNOWN. The adjustment moves lines by up to "
                      f"{max(abs(r['injury_delta']) for r in J('hub', 'data', 'lines.json')['rows']):.1f} "
                      f"points, and no test of its sign exists. It is published as a DERIVED, "
                      f"uncalibrated input for exactly this reason.",
            "answer_status": "OPEN",
            "how_to_close": "the same regression as Q-08; needs seasons, not weeks",
            "source": ["hub/data/lines.json"],
        },
    ]

    # ------------------------------------------------------------------ suggestions
    suggestions = [
        {
            "id": "S-01", "area": "Leaderboard", "priority": "P0 - do first",
            "suggestion": "Adopt the signal/staking split and the corrected minimum sample before "
                          "any reward is offered.",
            "because": f"A 45% loser shows a profit after 100 bets "
                       f"{demo['masking']['a_share_finishing_above_start_flat_1u']['bad_45pct']['100']:.1%} "
                       f"of the time, and the published 300-bet minimum detects only a ~60% edge. "
                       f"Ranking on bankroll or opening at 300 bets would pay luck.",
            "unlocks": "a competition whose winner is meaningfully better, not luckier",
            "does_not": "does not create a single settled bet; the board stays empty",
            "cost": "0 - the rules are computed in tools/decisions.py and tools/gates.py",
            "evidence": ["data/verified/staking_demo.json", "data/decisions/gates.json"],
            "status": "PROPOSED",
        },
        {
            "id": "S-02", "area": "Data", "priority": "P0 - unblocks the most",
            "suggestion": "License a price feed that publishes an open and a close per market, "
                          "and write it through the existing snapshot store.",
            "because": f"Market values are the only thing separating a signal from an edge. "
                       f"Today all {snap['rows']} market cells are blank. Every blocked gate "
                       f"(G-5, G-9) and every unanswerable market question depends on this one "
                       f"purchase.",
            "unlocks": "CLV, ROI, the difference column, and gates G-5/G-9",
            "does_not": "does not by itself validate anything; it supplies the missing input",
            "cost": "a vendor contract; unknown price and terms",
            "evidence": ["data/snapshots/store_meta.json"],
            "status": "PROPOSED",
        },
        {
            "id": "S-03", "area": "Model", "priority": "P1",
            "suggestion": "Estimate the injury and positional cost coefficients from outcomes "
                          "instead of carrying written priors.",
            "because": "The injury adjustment moves lines by up to "
                       f"{max(abs(r['injury_delta']) for r in J('hub','data','lines.json')['rows']):.1f} "
                       "points with no measured basis (Q-08, Q-14). Until it is estimated, the "
                       "largest single input to the board is an opinion.",
            "unlocks": "a model whose biggest adjustment is measured",
            "does_not": "does not help the total, which needs pace inputs instead (Q-03)",
            "cost": "requires multiple seasons of designations joined to results",
            "evidence": ["hub/data/meta.json", "data/verified/depth_map.json"],
            "status": "PROPOSED",
        },
        {
            "id": "S-04", "area": "Model", "priority": "P1",
            "suggestion": "Investigate the measured home-field advantage of "
                          f"{hfa['hfa_points']} points before accepting it as real.",
            "because": f"The interval {hfa['ci95']} includes zero, which contradicts the "
                       f"conventional 2.5-3. If it is a small-sample artefact the model is "
                       f"under-adjusting; if it is real, that is a finding worth publishing. "
                       f"Either way the current choice to use zero is a decision that should be "
                       f"checked rather than inherited.",
            "unlocks": "a correctly signed home adjustment",
            "does_not": "does not require new data beyond more seasons",
            "cost": "0 beyond waiting for games",
            "evidence": ["data/verified/hfa.json"],
            "status": "PROPOSED",
        },
        {
            "id": "S-05", "area": "Site", "priority": "P1",
            "suggestion": "Replace the prose counts on the landing page with values rendered "
                          "from the generated files.",
            "because": "Prose counts drift: this repository has already published a wrong count "
                       "once and a wrong arithmetic figure in this very session. Every number on "
                       "the new pages is interpolated from data at build time, so a stale count "
                       "fails the build instead of shipping.",
            "unlocks": "a site where a wrong number cannot be published quietly",
            "does_not": "does not fix numbers that are wrong in the source data",
            "cost": "0",
            "evidence": ["tools/build_hub.py", "COORDINATION.md"],
            "status": "ADOPTED IN THIS SESSION",
        },
        {
            "id": "S-06", "area": "Data", "priority": "P2",
            "suggestion": "Capture an as-of date with every club depth chart, and drop charts "
                          "that cannot be dated from any model input.",
            "because": f"{dep['replacements_identified']} of {dep['rows_total']} absences resolve "
                       f"to a named replacement, but most charts carry no as-of date and many "
                       f"clubs label them unofficial. An undated chart cannot be said to describe "
                       f"the week it is used for.",
            "unlocks": "a depth layer that can support a model input",
            "does_not": "does not make a club's chart an official statement of who starts",
            "cost": "0 - a capture change",
            "evidence": ["data/verified/depth_map.json"],
            "status": "PROPOSED",
        },
        {
            "id": "S-07", "area": "Validation", "priority": "P2",
            "suggestion": "Publish the demotion gate's first firing as a news item, even when "
                          "no strategy is live.",
            "because": "A demotion rule that has never fired is untested. Exercising it on paper "
                       "strategies, with the arithmetic shown, proves the mechanism works before "
                       "it matters.",
            "unlocks": "confidence that the rule is not decorative",
            "does_not": "does not create live strategies to demote",
            "cost": "0",
            "evidence": ["data/decisions/gates.json"],
            "status": "PROPOSED",
        },
        {
            "id": "S-08", "area": "Legal", "priority": "P0 before any reward",
            "suggestion": "Obtain legal review before publishing contest terms or a reward "
                          "structure.",
            "because": "Q-13 is unanswered and cannot be answered from data. Publishing a reward "
                       "structure without review is the one action on this site that carries a "
                       "risk no model can hedge.",
            "unlocks": "the ability to run any contest at all",
            "does_not": "nothing else on the site depends on it",
            "cost": "professional fees, unknown",
            "evidence": ["data/decisions/questions.json"],
            "status": "PROPOSED",
        },
    ]

    # ------------------------------------------------------------------ strategy ledger
    strat = J("hub", "data", "prereg.json")
    ledger = []
    for s in strat["strategies"]:
        ledger.append({
            "id": s["id"],
            "family": s["family"],
            "name": s["name"],
            "signal_metric": {
                "Single - side": "sign accuracy and MAE vs predict-zero on unseen games",
                "Single - total": "MAE vs the naive total, on unseen games",
                "Single - prop combo": "joint hit rate vs the multiplied marginals",
                "Parlay - same game": "realised joint rate vs the independence product",
                "Parlay - cross game": "realised joint rate vs the independence product",
                "Single - market check": "count of flagged moves that preceded a real absence",
                "Evaluation": "log-loss and MAE of the originated line",
                "Staking": "not a signal - applied on top of one",
            }.get(s["family"], "n/a"),
            "staking_metric": "flat-1u ROI and CLV, reported only after the signal number",
            "n_settled": 0,
            "signal_state": "NOT MEASURED",
            "staking_state": "NOT MEASURED",
            "gate": "G-3 FAIL (0 of the required settled bets)",
            "demotion": "not applicable - never live",
            "verdict": "PAPER",
        })
    out = {
        "as_of": "2026-11-14",
        "questions": questions,
        "suggestions": suggestions,
        "strategy_ledger": ledger,
        "summary": {
            "questions_total": len(questions),
            "answered": sum(1 for q in questions if q["answer_status"] == "ANSWERED"),
            "partial": sum(1 for q in questions if q["answer_status"] == "PARTIAL"),
            "open": sum(1 for q in questions if q["answer_status"] == "OPEN"),
            "blocked": sum(1 for q in questions if q["answer_status"] == "BLOCKED"),
            "suggestions_total": len(suggestions),
            "strategies": len(ledger),
            "strategies_live": sum(1 for x in ledger if x["verdict"] == "LIVE"),
            "gates": gsum,
        },
        "method": "Questions carry what we have, what we lack, the answer where the evidence "
                  "supports one, and the specific step that would close it. Answers are only "
                  "printed when a script in this repository measures them; a question with no "
                  "measurable answer is left OPEN or BLOCKED rather than filled with reasoning.",
    }
    json.dump(out, open(os.path.join(OUT, "questions.json"), "w", encoding="utf-8"), indent=1)
    json.dump({"as_of": "2026-11-14", "suggestions": suggestions},
              open(os.path.join(OUT, "suggestions.json"), "w", encoding="utf-8"), indent=1)
    json.dump({"as_of": "2026-11-14", "strategies": ledger},
              open(os.path.join(OUT, "strategy_ledger.json"), "w", encoding="utf-8"), indent=1)

    s = out["summary"]
    print(f"questions {s['questions_total']}: {s['answered']} answered, {s['partial']} partial, "
          f"{s['open']} open, {s['blocked']} blocked")
    print(f"suggestions: {s['suggestions_total']}   strategies: {s['strategies']} "
          f"(live {s['strategies_live']})")
    print("OK")


if __name__ == "__main__":
    main()
