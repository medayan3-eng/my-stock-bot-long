"""Screener configuration.

Every threshold lives here so the trading logic stays free of magic numbers.
config.yaml (optional) overrides these defaults; the Streamlit sidebar
overrides config.yaml at runtime.
"""
from __future__ import annotations

import copy
import os
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    # ---------------- Market regime (master on/off switch) ---------------- #
    "regime": {
        "benchmark": "SPY",
        "benchmark_ma": 200,          # SPY must trade above its 200-day SMA
        "vix_max": 25.0,              # block new longs above this VIX level
        "use_vix": True,
        "breadth_min_pct": 0.0,       # % of universe above its own SMA200 (0 = off)
    },

    # ---------------- Trend / structure ---------------- #
    "trend": {
        "sma_fast": 50,
        "sma_slow": 200,
        "sma200_slope_lookback": 20,  # SMA200 must be higher than 20 bars ago
        "min_sma200_slope_pct": 0.0,
        "high_52w_lookback": 252,
        "min_pct_of_52w_high": 80.0,  # price in the top quartile of the year
    },

    # ---------------- Entry zone around the 50-day MA ---------------- #
    "entry_zone": {
        "max_pct_below_sma50": 2.0,   # pullback / support tail tolerance
        "max_pct_above_sma50": 5.0,   # risk-reward capping
    },

    # ---------------- Volume ---------------- #
    "volume": {
        "avg_length": 50,
        "surge_multiple": 1.5,        # today OR max(last 3d) >= 1.5x avg volume
        "surge_lookback_days": 3,
    },

    # ---------------- Liquidity ---------------- #
    "liquidity": {
        "min_price": 5.0,
        "min_adv_shares": 500_000,
        "min_dollar_volume": 0,       # optional: ADV * price floor
    },

    # ---------------- Relative strength ---------------- #
    "relative_strength": {
        "lookback_days": 60,
        "min_excess_return_pct": 0.0,  # stock return minus SPY return
    },

    # ---------------- Volatility squeeze ---------------- #
    "squeeze": {
        "short_atr": 10,
        "long_atr": 50,
        "max_ratio": 1.0,             # ATR%(10) / ATR%(50) must be below this
    },

    # ---------------- Fundamentals ---------------- #
    "ownership": {
        "min_institutional_pct": 10.0,
        "on_missing": "warn",         # pass | fail | warn  (warn = pass + flag)
    },

    # ---------------- Sector strength (top-down) ---------------- #
    "sector": {
        "enabled": True,
        "min_rsi": 50.0,
        "rsi_length": 14,
        "rs_lookback_days": 60,
        "mode": "rsi_or_rs",          # rsi_or_rs | rsi_only | rs_only
        "on_missing": "warn",
    },

    # ---------------- Event risk ---------------- #
    "earnings": {
        "enabled": True,
        "blackout_days": 7,           # do not enter within N days of earnings
        "on_missing": "warn",
    },

    # ---------------- Exit / trade management ---------------- #
    "exits": {
        "initial_stop_atr_multiple": 2.0,
        "atr_length": 14,
        "swing_low_lookback": 20,
        "trail_atr_multiple": 2.0,
        "tier1_gain_pct": 10.0,       # move stop to breakeven
        "tier2_gain_pct": 20.0,       # tighten trail
        "tier3_gain_pct": 25.0,       # sell half, let the rest run
        "tier3_sell_fraction": 0.5,
        "tier2_trail_atr_multiple": 1.5,
    },

    # ---------------- Risk / position sizing ---------------- #
    "risk": {
        "account_size": 100_000.0,
        "risk_per_trade_pct": 1.0,
        "max_position_pct": 20.0,
    },

    # ---------------- Scan behaviour ---------------- #
    "scan": {
        "history_period": "2y",
        "chunk_size": 60,
        "batch_pause_seconds": 0.6,
        "min_bars": 260,              # need ~1y+ of data for 52w / SMA200
        "fetch_fundamentals": True,
        "score_weights": {
            "relative_strength": 30,
            "volume_surge": 20,
            "proximity_52w_high": 20,
            "squeeze": 15,
            "sector": 15,
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    """Load config.yaml if present, otherwise return the defaults."""
    if not os.path.exists(path):
        return copy.deepcopy(DEFAULTS)
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as fh:
            user_cfg = yaml.safe_load(fh) or {}
        return _deep_merge(DEFAULTS, user_cfg)
    except Exception:
        return copy.deepcopy(DEFAULTS)
