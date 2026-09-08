"""Offline sanity checks - no network required.

Run with:  python -m tests.test_offline
Builds synthetic price series and verifies the indicators and the rule engine.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import indicators as ind
from src import screener as sc
from src import exits as ex
from src.config import DEFAULTS


def synth(n=400, drift=0.0006, vol=0.012, seed=1, vol_spike=True):
    rng = np.random.default_rng(seed)
    ret = rng.normal(drift, vol, n)
    close = 50 * np.exp(np.cumsum(ret))
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    openp = close * (1 + rng.normal(0, 0.002, n))
    volume = rng.integers(800_000, 1_200_000, n).astype(float)
    if vol_spike:
        volume[-1] *= 2.2
    idx = pd.bdate_range("2023-01-02", periods=n)
    return pd.DataFrame(
        {"Open": openp, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx
    )


def check(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}  {name}")
    assert cond, name


def main():
    df = synth()

    # --- indicators -------------------------------------------------------- #
    s50 = ind.sma(df["Close"], 50)
    check("SMA50 has values", s50.notna().sum() == len(df) - 49)
    check("SMA50 warm-up is NaN", pd.isna(s50.iloc[48]))

    r = ind.rsi(df["Close"], 14).dropna()
    check("RSI within 0-100", bool((r >= 0).all() and (r <= 100).all()))

    up = pd.Series(np.arange(1, 60, dtype=float))
    check("RSI of a pure uptrend is 100", abs(ind.rsi(up, 14).iloc[-1] - 100.0) < 1e-6)

    a = ind.atr(df, 14).dropna()
    check("ATR positive", bool((a > 0).all()))

    tr = ind.true_range(df).dropna()
    check("TR >= High-Low", bool((tr >= (df["High"] - df["Low"]).loc[tr.index] - 1e-9).all()))

    check("pct_return math", abs(ind.pct_return(pd.Series([100.0, 110.0]), 1) - 0.10) < 1e-9)
    check("slope_pct math", abs(ind.slope_pct(pd.Series([100.0, 120.0]), 1) - 20.0) < 1e-9)

    # --- screener ---------------------------------------------------------- #
    cfg = DEFAULTS
    fnd = {"sector": "Technology", "inst_own": 0.72, "next_earnings": None, "short_name": "Test"}
    m = sc.compute_metrics("TEST", df, cfg, bench_return=0.02, fundamentals=fnd)
    check("metrics carry a price", m["price"] > 0)
    check("volume surge detected", m["vol_ratio"] >= 1.5)
    check("institutional parsed as %", m["inst_own_pct"] == 72.0)
    check("52w high ratio <= 100", m["pct_of_52w_high"] <= 100.5)

    checks, warns = sc.evaluate_rules(m, cfg, {"etf": "XLK", "rsi": 61.0, "rs_pct": 3.2, "ok": True})
    check("all rules evaluated", set(checks.keys()) == set(sc.RULES))
    check("liquidity passes on synthetic data", checks["liquidity"])
    check("volume surge rule passes", checks["volume_surge"])
    check("missing earnings -> warning not failure", checks["earnings_clear"] and any("earnings" in w.lower() for w in warns))

    score = sc.score_candidate(m, checks, cfg, {"etf": "XLK", "rsi": 61.0, "rs_pct": 3.2, "ok": True})
    check("score in 0-100", 0 <= score <= 100)

    # extended stock must fail the not_extended rule
    m_ext = dict(m, dist_sma50_pct=14.0)
    chk_ext, _ = sc.evaluate_rules(m_ext, cfg, {"ok": True})
    check("extended price fails not_extended", not chk_ext["not_extended"])

    # deep pullback must fail near_sma50
    m_low = dict(m, dist_sma50_pct=-9.0)
    chk_low, _ = sc.evaluate_rules(m_low, cfg, {"ok": True})
    check("deep pullback fails near_sma50", not chk_low["near_sma50"])

    # low institutional ownership must fail
    m_inst = dict(m, inst_own_pct=4.0)
    chk_inst, _ = sc.evaluate_rules(m_inst, cfg, {"ok": True})
    check("low institutional ownership fails", not chk_inst["institutional"])

    # full scan over a small universe
    prices = {"AAA": synth(seed=2), "BBB": synth(seed=3), "SPY": synth(seed=4), "SHORT": synth(n=100, seed=5)}
    res = sc.scan(prices, cfg, {"XLK": {"etf": "XLK", "rsi": 60, "rs_pct": 1.0, "ok": True}},
                  {"AAA": fnd, "BBB": fnd, "SHORT": fnd}, ["AAA", "BBB", "SHORT"])
    check("scan returns one row per ticker", len(res) == 3)
    check("short history flagged", res[res.ticker == "SHORT"]["status"].iloc[0].startswith("insufficient"))
    check("benchmark excluded", "SPY" not in res["ticker"].tolist())

    # --- exits -------------------------------------------------------------- #
    plan = ex.build_plan(entry=100.0, atr=2.0, swing_low=95.0, cfg=cfg,
                         pattern="Cup & Handle", breakout_level=100.0, pattern_height=15.0)
    check("stop below entry", plan.initial_stop < 100.0)
    check("stop is the tighter of ATR/swing", plan.initial_stop >= 94.0)
    check("target = breakout + height", plan.target == 115.0)
    check("reward/risk computed", plan.reward_risk and plan.reward_risk > 1)
    check("position sizing respects risk", plan.capital_at_risk <= cfg["risk"]["account_size"] * 0.0101)
    check("ladder has three stages", len(plan.ladder) == 3)
    check("trailing stop math", ex.trailing_stop(120.0, 2.0, 2.0) == 116.0)

    plan2 = ex.build_plan(entry=100.0, atr=2.0, swing_low=None, cfg=cfg)
    check("no pattern -> no target", plan2.target is None)

    print("\nAll offline checks passed.")


if __name__ == "__main__":
    main()
