#!/usr/bin/env python3
"""
Run the whole trading-desk pipeline in dependency order, then gate it.

    python3 scripts/ops_run.py

Order matters and is enforced here rather than by hope:
  ops_teamstats_source  -> data/ops/reference/teamstats.json   (official team stats)
  ops_model             -> model.json                          (ratings, origination, backtest)
  ops_join              -> join.json                           (injury x depth)
  ops_market            -> snapshots/props/correlation/leaderboard
  ops_content           -> results/requirements/questions/suggestions/flags/repo
  ops_build             -> ops/**.html + ops/data
  ops_verify            -> verification.json, rebuild, and the gate

Every step is deterministic; running this twice produces identical bytes, which
ops_verify checks as V10.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = [
    "ops_teamstats_source.py",
    "ops_model.py",
    "ops_join.py",
    "ops_market.py",
    "ops_content.py",
    "ops_build.py",
    "ops_verify.py",
]


def main():
    for i, step in enumerate(STEPS, 1):
        p = os.path.join(ROOT, "scripts", step)
        print(f"[{i}/{len(STEPS)}] {step}")
        r = subprocess.run([sys.executable, p], cwd=ROOT)
        if r.returncode != 0:
            print(f"FAILED at {step} (exit {r.returncode}) - stopping, nothing downstream is trusted")
            return r.returncode
    print("\nPIPELINE OK - every step succeeded and the gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
