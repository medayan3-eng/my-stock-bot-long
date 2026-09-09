"""Pattern-detection tests using synthetically constructed formations.

Each generator draws a textbook shape; the detector must name it correctly and
produce a sane breakout level and measured-move target.

    python -m tests.test_patterns
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import exits as ex
from src import patterns as pat
from src.config import DEFAULTS


def frame(close, noise=0.004, seed=0):
    rng = np.random.default_rng(seed)
    close = np.asarray(close, dtype=float)
    n = len(close)
    high = close * (1 + np.abs(rng.normal(0, noise, n)))
    low = close * (1 - np.abs(rng.normal(0, noise, n)))
    openp = close * (1 + rng.normal(0, noise / 2, n))
    vol = rng.integers(700_000, 1_300_000, n).astype(float)
    idx = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame(
        {"Open": openp, "High": high, "Low": low, "Close": close, "Volume": vol}, index=idx
    )


def make_flag():
    base = np.linspace(40, 42, 90)                     # quiet drift
    pole = np.linspace(42, 56, 20)                     # +33% thrust
    flag = 56 - np.linspace(0, 3, 18) + np.sin(np.linspace(0, 6, 18)) * 0.4
    return frame(np.concatenate([base, pole, flag]), seed=1)


def make_cup_handle():
    lead = np.linspace(45, 50, 40)
    x = np.linspace(0, np.pi, 90)
    cup = 50 - 12 * np.sin(x)                          # U from 50 down to 38
    handle = 50 - np.linspace(0, 2.5, 15)
    return frame(np.concatenate([lead, cup, handle]), seed=2)


def make_double_bottom():
    lead = np.linspace(60, 50, 30)
    d1 = np.concatenate([np.linspace(50, 40, 12), np.linspace(40, 48, 14)])
    d2 = np.concatenate([np.linspace(48, 40.5, 14), np.linspace(40.5, 47, 14)])
    tail = np.linspace(47, 47.5, 6)
    return frame(np.concatenate([lead, d1, d2, tail]), noise=0.002, seed=3)


def make_inverse_hs():
    lead = np.linspace(70, 60, 25)
    ls = np.concatenate([np.linspace(60, 52, 10), np.linspace(52, 60, 10)])
    head = np.concatenate([np.linspace(60, 45, 12), np.linspace(45, 61, 12)])
    rs = np.concatenate([np.linspace(61, 53, 10), np.linspace(53, 59, 10)])
    return frame(np.concatenate([lead, ls, head, rs]), noise=0.002, seed=4)


def make_triangle():
    """Converging zig-zag with 13-bar legs so real fractal pivots form."""
    lead = np.linspace(30, 40, 30)
    segs, amp, center, cur = [], 6.0, 40.0, 40.0
    for i in range(7):
        amp *= 0.78
        target = center + (amp if i % 2 == 0 else -amp)
        segs.append(np.linspace(cur, target, 13))
        cur = target
    return frame(np.concatenate([lead] + segs), noise=0.002, seed=5)


def make_ascending_triangle():
    """Flat resistance, rising lows."""
    lead = np.linspace(28, 40, 30)
    segs, cur, low = [], 40.0, 33.0
    for i in range(6):
        if i % 2 == 0:
            segs.append(np.linspace(cur, low, 13)); cur = low; low += 1.4
        else:
            segs.append(np.linspace(cur, 40.0, 13)); cur = 40.0
    return frame(np.concatenate([lead] + segs), noise=0.0015, seed=7)


def make_base():
    lead = np.linspace(30, 44, 80)
    flat = 44 + np.sin(np.linspace(0, 8, 30)) * 0.9
    return frame(np.concatenate([lead, flat]), noise=0.002, seed=6)


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}  {name}")
    assert cond, name


def main():
    cfg = DEFAULTS

    # ---- pivots & levels -------------------------------------------------- #
    df = make_double_bottom()
    assert len(pat.pivot_lows(df)) >= 2 and len(pat.pivot_highs(df)) >= 1
    check("pivot detection finds highs and lows", True)

    lv = pat.support_resistance(df)
    price = float(df["Close"].iloc[-1])
    check("support sits below price", lv["support"] is None or lv["support"] < price)
    check("resistance sits above price", lv["resistance"] is None or lv["resistance"] > price)
    check("key levels returned", isinstance(lv["key_levels"], list))

    # ---- individual detectors --------------------------------------------- #
    cases = [
        ("Flag / Pennant", make_flag(), pat.detect_flag),
        ("Cup & Handle", make_cup_handle(), pat.detect_cup_handle),
        ("Double Bottom", make_double_bottom(), pat.detect_double_bottom),
        ("Inverse Head & Shoulders", make_inverse_hs(), pat.detect_inverse_hs),
        ("Base / Consolidation", make_base(), pat.detect_base),
    ]
    for expected, data, fn in cases:
        p = fn(data)
        check(f"{expected}: detector fires", p is not None)
        check(f"{expected}: named correctly", p.name == expected)
        check(f"{expected}: confidence in range", 0 <= p.confidence <= 1)
        check(f"{expected}: height positive", p.height > 0)
        check(f"{expected}: target above breakout",
              p.target > p.breakout_level)
        check(f"{expected}: target = breakout + height",
              abs(p.target - (p.breakout_level + p.height)) < 0.02)

    tri = pat.detect_triangle(make_triangle())
    check("Triangle: detector fires", tri is not None)
    check("Triangle: named as a triangle", "Triangle" in tri.name)
    check("Triangle: bullish target", tri.target > tri.breakout_level)

    asc = pat.detect_triangle(make_ascending_triangle())
    check("Ascending triangle: detector fires", asc is not None)
    check("Ascending triangle: named correctly", asc.name == "Ascending Triangle")

    # ---- top-level dispatch ------------------------------------------------ #
    res = pat.analyse(make_cup_handle())
    check("analyse returns a pattern name", res["pattern"] != "")
    check("analyse computes distance to target", res["pct_to_target"] is not None)
    check("analyse includes support/resistance keys",
          "support" in res and "resistance" in res)

    # random walk should usually NOT produce a high-confidence pattern
    rng = np.random.default_rng(11)
    walk = frame(50 * np.exp(np.cumsum(rng.normal(0, 0.02, 200))), seed=9)
    p = pat.detect_pattern(walk)
    check("random walk yields no false high-confidence pattern", p.confidence <= 0.95)

    # short history must not crash
    check("short frame handled", pat.detect_pattern(frame(np.linspace(10, 11, 20))).name
          == "No clear pattern")

    # ---- automatic trade plan ---------------------------------------------- #
    row = dict(
        price=100.0, atr14=2.0, swing_low_20=94.0, support=96.0,
        pattern="Cup & Handle", pattern_target=118.0,
    )
    plan = ex.auto_plan(row, cfg)
    check("auto_plan stop below entry", plan.initial_stop < 100.0)
    check("auto_plan prefers the support anchor", plan.initial_stop >= 94.0)
    check("auto_plan sizes the position", plan.shares > 0)
    check("auto_plan respects the risk budget",
          plan.capital_at_risk <= cfg["risk"]["account_size"] * 0.0101)
    check("auto_plan carries the pattern target", plan.target == 118.0)
    check("auto_plan computes reward/risk", plan.reward_risk > 1)

    plan2 = ex.auto_plan(dict(price=50.0, atr14=1.0, swing_low_20=None,
                              pattern="No clear pattern"), cfg)
    check("auto_plan works without a pattern", plan2.target is None and plan2.shares > 0)

    print("\nAll pattern checks passed.")


if __name__ == "__main__":
    main()
