"""The screening engine.

For every ticker we compute a metric block, then evaluate each rule
independently so the UI can show exactly why a candidate passed or failed.
Nothing here places orders - the output is a ranked watchlist for manual review.
"""
from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import indicators as ind
from .data import BENCHMARK, get_fundamentals
from .market import sector_status

# Rule order defines column order in the results table.
RULES: List[str] = [
    "liquidity",
    "trend_52w",
    "near_sma50",
    "not_extended",
    "volume_surge",
    "rel_strength",
    "squeeze",
    "institutional",
    "sector_strength",
    "earnings_clear",
]

RULE_LABELS: Dict[str, str] = {
    "liquidity": "Liquidity",
    "trend_52w": "52w Uptrend",
    "near_sma50": "At/Above 50MA",
    "not_extended": "Not Extended",
    "volume_surge": "Volume Surge",
    "rel_strength": "RS vs SPY",
    "squeeze": "Vol Squeeze",
    "institutional": "Institutional",
    "sector_strength": "Sector Strength",
    "earnings_clear": "Earnings Clear",
}


def _pct(a: float, b: float) -> float:
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return float("nan")
    return (a / b - 1.0) * 100.0


def compute_metrics(
    ticker: str,
    df: pd.DataFrame,
    cfg: dict,
    bench_return: float,
    fundamentals: Optional[dict] = None,
) -> dict:
    t, v, l, rs_cfg, sq = (
        cfg["trend"],
        cfg["volume"],
        cfg["liquidity"],
        cfg["relative_strength"],
        cfg["squeeze"],
    )
    close = df["Close"]
    price = float(close.iloc[-1])

    sma50 = ind.sma(close, t["sma_fast"])
    sma200 = ind.sma(close, t["sma_slow"])
    sma50_last = ind.last_valid(sma50)
    sma200_last = ind.last_valid(sma200)

    high_52w = ind.last_valid(ind.rolling_high(df["High"], t["high_52w_lookback"]))
    low_52w = ind.last_valid(ind.rolling_low(df["Low"], t["high_52w_lookback"]))

    avg_vol = ind.last_valid(ind.sma(df["Volume"], v["avg_length"]))
    vol_today = float(df["Volume"].iloc[-1])
    vol_max_n = float(df["Volume"].iloc[-int(v["surge_lookback_days"]):].max())

    atr_short = ind.last_valid(ind.atr_percent(df, sq["short_atr"]))
    atr_long = ind.last_valid(ind.atr_percent(df, sq["long_atr"]))
    atr_abs = ind.last_valid(ind.atr(df, cfg["exits"]["atr_length"]))

    stock_ret = ind.pct_return(close, int(rs_cfg["lookback_days"]))
    fundamentals = fundamentals or {}
    sector = fundamentals.get("sector")
    next_earn = fundamentals.get("next_earnings")
    days_to_earn = (next_earn - dt.date.today()).days if isinstance(next_earn, dt.date) else None

    inst = fundamentals.get("inst_own")
    inst_pct = round(inst * 100.0, 1) if isinstance(inst, (int, float)) else None

    return {
        "ticker": ticker,
        "name": fundamentals.get("short_name"),
        "date": df.index[-1].date().isoformat(),
        "price": round(price, 2),
        "sma50": round(sma50_last, 2) if np.isfinite(sma50_last) else None,
        "sma200": round(sma200_last, 2) if np.isfinite(sma200_last) else None,
        "dist_sma50_pct": round(_pct(price, sma50_last), 2),
        "sma200_slope_pct": round(ind.slope_pct(sma200, t["sma200_slope_lookback"]), 2),
        "high_52w": round(high_52w, 2) if np.isfinite(high_52w) else None,
        "low_52w": round(low_52w, 2) if np.isfinite(low_52w) else None,
        "pct_of_52w_high": round(price / high_52w * 100.0, 1) if np.isfinite(high_52w) and high_52w else None,
        "avg_vol50": int(avg_vol) if np.isfinite(avg_vol) else None,
        "vol_today": int(vol_today),
        "vol_ratio": round(vol_today / avg_vol, 2) if np.isfinite(avg_vol) and avg_vol else None,
        "vol_ratio_max3": round(vol_max_n / avg_vol, 2) if np.isfinite(avg_vol) and avg_vol else None,
        "dollar_volume": int(avg_vol * price) if np.isfinite(avg_vol) else None,
        "ret_60d_pct": round(stock_ret * 100.0, 2) if np.isfinite(stock_ret) else None,
        "bench_ret_60d_pct": round(bench_return * 100.0, 2) if np.isfinite(bench_return) else None,
        "rs_excess_pct": round((stock_ret - bench_return) * 100.0, 2)
        if np.isfinite(stock_ret) and np.isfinite(bench_return)
        else None,
        "atr_pct_short": round(atr_short, 2) if np.isfinite(atr_short) else None,
        "atr_pct_long": round(atr_long, 2) if np.isfinite(atr_long) else None,
        "squeeze_ratio": round(atr_short / atr_long, 2)
        if np.isfinite(atr_short) and np.isfinite(atr_long) and atr_long
        else None,
        "atr14": round(atr_abs, 2) if np.isfinite(atr_abs) else None,
        "swing_low_20": round(ind.swing_low(df, cfg["exits"]["swing_low_lookback"]), 2),
        "inst_own_pct": inst_pct,
        "sector": sector,
        "next_earnings": next_earn.isoformat() if isinstance(next_earn, dt.date) else None,
        "days_to_earnings": days_to_earn,
    }


def _missing_policy(policy: str) -> tuple:
    """Returns (passes, is_warning) for a rule whose input data is missing."""
    if policy == "fail":
        return False, False
    if policy == "pass":
        return True, False
    return True, True  # "warn"


def evaluate_rules(m: dict, cfg: dict, sector_info: dict) -> tuple:
    """Returns (checks: dict[str,bool], warnings: list[str])."""
    checks: Dict[str, bool] = {}
    warnings: List[str] = []

    t, ez, v, l = cfg["trend"], cfg["entry_zone"], cfg["volume"], cfg["liquidity"]
    rs_cfg, sq, own, sec, earn = (
        cfg["relative_strength"],
        cfg["squeeze"],
        cfg["ownership"],
        cfg["sector"],
        cfg["earnings"],
    )

    # 1. Liquidity ---------------------------------------------------------- #
    checks["liquidity"] = bool(
        m["price"] is not None
        and m["price"] >= l["min_price"]
        and m["avg_vol50"] is not None
        and m["avg_vol50"] >= l["min_adv_shares"]
        and (not l.get("min_dollar_volume") or (m["dollar_volume"] or 0) >= l["min_dollar_volume"])
    )

    # 2. 52-week uptrend ---------------------------------------------------- #
    checks["trend_52w"] = bool(
        m["sma200_slope_pct"] is not None
        and np.isfinite(m["sma200_slope_pct"])
        and m["sma200_slope_pct"] > t["min_sma200_slope_pct"]
        and m["pct_of_52w_high"] is not None
        and m["pct_of_52w_high"] >= t["min_pct_of_52w_high"]
    )

    # 3. Contact with the 50-day MA ---------------------------------------- #
    d50 = m["dist_sma50_pct"]
    has_d50 = d50 is not None and np.isfinite(d50)
    checks["near_sma50"] = bool(has_d50 and d50 >= -abs(ez["max_pct_below_sma50"]))

    # 4. Risk-reward capping ------------------------------------------------ #
    checks["not_extended"] = bool(has_d50 and d50 <= abs(ez["max_pct_above_sma50"]))

    # 5. Volume surge ------------------------------------------------------- #
    mult = float(v["surge_multiple"])
    checks["volume_surge"] = bool(
        (m["vol_ratio"] is not None and m["vol_ratio"] >= mult)
        or (m["vol_ratio_max3"] is not None and m["vol_ratio_max3"] >= mult)
    )

    # 6. Relative strength vs the benchmark --------------------------------- #
    checks["rel_strength"] = bool(
        m["rs_excess_pct"] is not None
        and m["rs_excess_pct"] > rs_cfg["min_excess_return_pct"]
    )

    # 7. Volatility squeeze ------------------------------------------------- #
    checks["squeeze"] = bool(
        m["squeeze_ratio"] is not None and m["squeeze_ratio"] < sq["max_ratio"]
    )

    # 8. Institutional ownership -------------------------------------------- #
    if m["inst_own_pct"] is None:
        ok, warn = _missing_policy(own.get("on_missing", "warn"))
        checks["institutional"] = ok
        if warn:
            warnings.append("Institutional ownership unavailable - verify manually.")
    else:
        checks["institutional"] = m["inst_own_pct"] >= own["min_institutional_pct"]

    # 9. Sector strength ----------------------------------------------------- #
    if not sec.get("enabled", True):
        checks["sector_strength"] = True
    elif sector_info.get("ok") is None:
        ok, warn = _missing_policy(sec.get("on_missing", "warn"))
        checks["sector_strength"] = ok
        if warn:
            warnings.append("Sector could not be mapped to an ETF - check sector trend manually.")
    else:
        checks["sector_strength"] = bool(sector_info["ok"])

    # 10. Earnings blackout --------------------------------------------------- #
    if not earn.get("enabled", True):
        checks["earnings_clear"] = True
    elif m["days_to_earnings"] is None:
        ok, warn = _missing_policy(earn.get("on_missing", "warn"))
        checks["earnings_clear"] = ok
        if warn:
            warnings.append("Next earnings date unknown - confirm before entering.")
    else:
        checks["earnings_clear"] = m["days_to_earnings"] > int(earn["blackout_days"])
        if not checks["earnings_clear"]:
            warnings.append(f"Earnings in {m['days_to_earnings']} day(s).")

    return checks, warnings


def score_candidate(m: dict, checks: Dict[str, bool], cfg: dict, sector_info: dict) -> float:
    """0-100 ranking score. Ranking only - it never overrides a failed rule."""
    w = cfg["scan"]["score_weights"]

    def clamp(x: float) -> float:
        return max(0.0, min(1.0, x))

    rs = m.get("rs_excess_pct")
    rs_score = clamp((rs or 0) / 15.0)                       # +15% excess = full marks

    vr = max(m.get("vol_ratio") or 0, m.get("vol_ratio_max3") or 0)
    vol_score = clamp((vr - 1.0) / 1.5)                      # 2.5x avg volume = full marks

    prox = m.get("pct_of_52w_high")
    prox_score = clamp(((prox or 0) - 80.0) / 20.0)          # at the high = full marks

    sr = m.get("squeeze_ratio")
    squeeze_score = clamp((1.0 - (sr if sr is not None else 1.0)) / 0.4)

    if sector_info.get("ok") is None:
        sector_score = 0.5
    else:
        sector_score = 1.0 if sector_info["ok"] else 0.0
        rsi_val = sector_info.get("rsi")
        if sector_info["ok"] and rsi_val:
            sector_score = clamp(0.5 + (rsi_val - 50.0) / 40.0)

    total = (
        rs_score * w["relative_strength"]
        + vol_score * w["volume_surge"]
        + prox_score * w["proximity_52w_high"]
        + squeeze_score * w["squeeze"]
        + sector_score * w["sector"]
    )
    return round(total, 1)


def scan(
    prices: Dict[str, pd.DataFrame],
    cfg: dict,
    sector_table: Dict[str, dict],
    fundamentals: Optional[Dict[str, dict]] = None,
    tickers: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Run the full rule set over the universe. Returns one row per ticker."""
    bench_df = prices.get(cfg["regime"]["benchmark"], prices.get(BENCHMARK))
    bench_ret = (
        ind.pct_return(bench_df["Close"], int(cfg["relative_strength"]["lookback_days"]))
        if bench_df is not None and not bench_df.empty
        else float("nan")
    )

    fundamentals = fundamentals or {}
    universe = tickers if tickers is not None else list(prices.keys())
    skip = {cfg["regime"]["benchmark"], BENCHMARK, "^VIX"}
    min_bars = int(cfg["scan"]["min_bars"])

    rows = []
    for tk in universe:
        if tk in skip:
            continue
        df = prices.get(tk)
        if df is None or len(df) < min_bars:
            rows.append(
                {
                    "ticker": tk,
                    "status": f"insufficient data ({0 if df is None else len(df)} bars)",
                    "passes_all": False,
                    "score": 0.0,
                    "rules_passed": 0,
                }
            )
            continue

        fnd = fundamentals.get(tk, {})
        m = compute_metrics(tk, df, cfg, bench_ret, fnd)
        sec_info = sector_status(m.get("sector"), sector_table)
        m["sector_etf"] = sec_info.get("etf")
        m["sector_rsi"] = sec_info.get("rsi")
        m["sector_rs_pct"] = sec_info.get("rs_pct")

        checks, warns = evaluate_rules(m, cfg, sec_info)
        row = dict(m)
        row.update({f"chk_{k}": v for k, v in checks.items()})
        row["rules_passed"] = int(sum(checks.values()))
        row["rules_total"] = len(checks)
        row["passes_all"] = all(checks.values())
        row["score"] = score_candidate(m, checks, cfg, sec_info)
        row["failed_rules"] = ", ".join(RULE_LABELS[k] for k, ok in checks.items() if not ok)
        row["warnings"] = " | ".join(warns)
        row["status"] = "ok"
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(
        ["passes_all", "score", "rules_passed"], ascending=[False, False, False]
    ).reset_index(drop=True)
