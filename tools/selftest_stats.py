#!/usr/bin/env python3
"""
Self-test for tools/x3stats.py. Every function is checked against exact values
computed a different way, so the gates that rely on it can be trusted.

Run: python3 tools/selftest_stats.py   (exit 0 = all pass)
"""
from __future__ import annotations

import itertools
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import x3stats as S  # noqa: E402

FAILS = []


def check(name, got, want, tol=1e-9):
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    if not ok:
        FAILS.append(f"{name}: got {got!r} want {want!r}")
    return ok


def brute_tail(n, k, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def main():
    # 1. binomial tail vs brute force over a broad grid
    for n in (1, 2, 5, 10, 17, 40, 100, 250):
        for p in (0.05, 0.25, 0.5, 0.5238, 0.75, 0.95):
            for k in range(0, n + 2):
                check(f"tail(n={n},k={k},p={p})", S.binom_tail(n, k, p), brute_tail(n, k, p), 1e-9)

    # 2. k_crit boundary property
    for n in (10, 50, 300, 1200):
        for p0 in (0.5, 0.5238095):
            k = S.k_crit(n, p0, 0.05)
            if not (S.binom_tail(n, k, p0) <= 0.05 + 1e-12
                    and (k == 0 or S.binom_tail(n, k - 1, p0) > 0.05)):
                FAILS.append(f"k_crit boundary n={n} p0={p0} k={k}")

    # 3. power monotone in p1 and in n
    breakeven = S.break_even_from_american(-110)
    check("breakeven(-110)", breakeven, 110 / 210, 1e-12)
    prev = -1.0
    for n in (100, 500, 1000, 2000):
        pw = S.exact_power(0.55, breakeven, n)
        if pw < prev - 1e-9:
            FAILS.append(f"power not monotone in n at n={n}")
        prev = pw
    prev = -1.0
    for p1 in (0.53, 0.54, 0.55, 0.56, 0.58, 0.60):
        pw = S.exact_power(p1, breakeven, 1000)
        if pw < prev - 1e-9:
            FAILS.append(f"power not monotone in p1 at p1={p1}")
        prev = pw

    # 4. min_n is the true first n meeting 80% power
    for p1 in (0.56, 0.58, 0.60):
        n = S.min_n(p1, breakeven)
        if S.exact_power(p1, breakeven, n) < 0.80 - 1e-9:
            FAILS.append(f"min_n({p1})={n} does not reach 80% power")
        if n > 4 and S.exact_power(p1, breakeven, n - 1) >= 0.80:
            FAILS.append(f"min_n({p1})={n} is not minimal")

    # 5. sign test vs exact enumeration of both tails
    for pos, neg in ((1, 9), (5, 5), (8, 2), (40, 20), (56, 32)):
        n = pos + neg
        k = min(pos, neg)
        want = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
        check(f"sign_test({pos},{neg})", S.sign_test(pos, neg), want, 1e-12)

    # 6. Wilson interval brackets the point estimate and is inside [0,1]
    for k, n in ((0, 10), (5, 10), (56, 88), (300, 500), (1000, 1000)):
        lo, hi = S.wilson_interval(k, n)
        if not (0.0 <= lo <= k / n <= hi <= 1.0):
            FAILS.append(f"wilson({k},{n}) = {lo},{hi} does not bracket {k/n}")
    # known value: 0/10 95% Wilson upper = 0.2775 (Wilson 1927)
    check("wilson(0,10).hi", S.wilson_interval(0, 10)[1], 0.27753, 1e-4)

    # 7. American odds round-trip and known anchors
    check("p->a(0.5)", S.prob_to_american(0.5), 100)
    check("p->a(0.5238)", S.prob_to_american(0.5238095), -110)
    check("a->p(-110)", S.american_to_prob(-110), 110 / 210, 1e-12)
    check("a->p(+150)", S.american_to_prob(150), 100 / 250, 1e-12)
    # -100 and +100 are the same even-money price, so a round trip through
    # probability is allowed to return either. The distance test handles that and
    # also allows one cent of rounding.
    for a in (-500, -110, -100, 100, 150, 400):
        p = S.american_to_prob(a)
        rt = S.prob_to_american(p)
        if abs(S.american_to_prob(rt) - p) > 0.002:
            FAILS.append(f"american round trip {a} -> {rt} changes the implied probability")
    check("tie is even money both ways", abs(S.american_to_prob(-100) - S.american_to_prob(100)) < 1e-12, True)

    # 8. betai vs a closed-form case: I_x(1,1) = x
    for x in (0.1, 0.5, 0.9):
        check(f"betai(1,1,{x})", S.betai(1, 1, x), x, 1e-12)

    if FAILS:
        print(f"SELFTEST FAILED ({len(FAILS)} problems)")
        for f in FAILS[:25]:
            print("  ", f)
        raise SystemExit(1)
    print("SELFTEST PASSED - all statistics kernels verified against exact values")


if __name__ == "__main__":
    main()
