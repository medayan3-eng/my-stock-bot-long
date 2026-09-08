"""Technical indicators used by the screener.

All functions take/return pandas objects and never mutate their inputs.
Wilder smoothing (RMA) is used for RSI and ATR, matching Murphy / classic TA.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
# Moving averages
# --------------------------------------------------------------------------- #
def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()


def rma(series: pd.Series, length: int) -> pd.Series:
    """Wilder's smoothed moving average."""
    return series.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


# --------------------------------------------------------------------------- #
# Momentum
# --------------------------------------------------------------------------- #
def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)

    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # avg_loss == 0 -> pure uptrend -> RSI 100
    out = out.where(avg_loss != 0, 100.0)
    out = out.where(avg_gain.notna() & avg_loss.notna())
    return out


def pct_return(close: pd.Series, lookback: int) -> float:
    """Simple % return over `lookback` bars. Returns np.nan if not enough data."""
    if len(close) < lookback + 1:
        return float("nan")
    past = close.iloc[-(lookback + 1)]
    last = close.iloc[-1]
    if not np.isfinite(past) or past == 0:
        return float("nan")
    return float(last / past - 1.0)


# --------------------------------------------------------------------------- #
# Volatility
# --------------------------------------------------------------------------- #
def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["Close"].shift(1)
    ranges = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    return rma(true_range(df), length)


def atr_percent(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """ATR normalised by price, so it is comparable across lengths and tickers."""
    return atr(df, length) / df["Close"] * 100.0


# --------------------------------------------------------------------------- #
# Trend helpers
# --------------------------------------------------------------------------- #
def slope_pct(series: pd.Series, lookback: int) -> float:
    """% change of a series (e.g. SMA200) over `lookback` bars."""
    s = series.dropna()
    if len(s) < lookback + 1:
        return float("nan")
    past = s.iloc[-(lookback + 1)]
    if not np.isfinite(past) or past == 0:
        return float("nan")
    return float(s.iloc[-1] / past - 1.0) * 100.0


def rolling_high(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=max(20, length // 4)).max()


def rolling_low(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=max(20, length // 4)).min()


def swing_low(df: pd.DataFrame, lookback: int = 20) -> float:
    """Lowest low of the last `lookback` bars - a natural structural stop."""
    if len(df) < 2:
        return float("nan")
    return float(df["Low"].iloc[-lookback:].min())


def last_valid(series: pd.Series) -> float:
    s = series.dropna()
    return float(s.iloc[-1]) if len(s) else float("nan")
