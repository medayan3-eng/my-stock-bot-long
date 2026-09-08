"""Data access layer.

Free sources only:
  * Yahoo Finance via the `yfinance` package (prices, volume, sector,
    institutional ownership, earnings dates).

Every network call is wrapped so that one bad ticker never kills a scan.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Dict, List, Optional

import pandas as pd

try:  # keeps unit tests importable without the dependency installed
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

OHLCV = ["Open", "High", "Low", "Close", "Volume"]

# Yahoo sector name -> SPDR sector ETF
SECTOR_ETF: Dict[str, str] = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
    # Finviz uses slightly different labels than Yahoo for two sectors.
    "Financial": "XLF",
    "Consumer Discretionary": "XLY",
}

BENCHMARK = "SPY"
VIX = "^VIX"


def _clean(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    df = df.copy()
    missing = [c for c in OHLCV if c not in df.columns]
    if missing:
        return None
    df = df[OHLCV].dropna(how="all")
    df = df[df["Close"].notna()]
    if df.empty:
        return None
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def download_prices(
    tickers: List[str],
    period: str = "3y",
    interval: str = "1d",
) -> Dict[str, pd.DataFrame]:
    """Batch-download daily OHLCV. Returns {ticker: DataFrame}."""
    if yf is None:
        raise RuntimeError("yfinance is not installed. Run: pip install -r requirements.txt")

    tickers = sorted({t.strip().upper() for t in tickers if t and t.strip()})
    if not tickers:
        return {}

    raw = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        auto_adjust=True,      # split & dividend adjusted -> clean long-term MAs
        group_by="ticker",
        threads=True,
        progress=False,
    )

    out: Dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return out

    if isinstance(raw.columns, pd.MultiIndex):
        level0 = set(raw.columns.get_level_values(0))
        for t in tickers:
            if t not in level0:
                continue
            cleaned = _clean(raw[t])
            if cleaned is not None:
                out[t] = cleaned
    else:  # single ticker -> flat columns
        cleaned = _clean(raw)
        if cleaned is not None:
            out[tickers[0]] = cleaned
    return out


def get_fundamentals(
    ticker: str,
    need_info: bool = True,
    need_earnings: bool = True,
) -> dict:
    """Institutional ownership, sector, next earnings date.

    `need_info=False` skips the slow Yahoo `.info` request. Use it when the
    universe was already pre-filtered elsewhere (e.g. Finviz) so ownership and
    sector are known - it cuts scan time by roughly an order of magnitude.
    Any field Yahoo does not provide comes back as None instead of raising.
    """
    info: dict = {}
    result = {
        "ticker": ticker,
        "sector": None,
        "industry": None,
        "inst_own": None,        # 0..1
        "market_cap": None,
        "next_earnings": None,   # datetime.date
        "short_name": None,
    }
    if yf is None:
        return result

    try:
        tk = yf.Ticker(ticker)
    except Exception:
        return result

    for getter in ("get_info", "info") if need_info else ():
        try:
            attr = getattr(tk, getter)
            info = attr() if callable(attr) else attr
            if info:
                break
        except Exception:
            info = {}

    if isinstance(info, dict) and info:
        result["sector"] = info.get("sector")
        result["industry"] = info.get("industry")
        result["market_cap"] = info.get("marketCap")
        result["short_name"] = info.get("shortName") or info.get("longName")
        held = info.get("heldPercentInstitutions")
        if isinstance(held, (int, float)) and not math.isnan(held):
            # Yahoo occasionally returns 65.4 instead of 0.654
            result["inst_own"] = held / 100.0 if held > 1.5 else float(held)

    if need_earnings:
        result["next_earnings"] = _next_earnings(tk)
    return result


def _next_earnings(tk) -> Optional[dt.date]:
    today = dt.date.today()
    # Preferred: full earnings-date table
    try:
        edf = tk.get_earnings_dates(limit=12)
        if edf is not None and not edf.empty:
            idx = pd.to_datetime(edf.index).tz_localize(None)
            future = sorted(d.date() for d in idx if d.date() >= today)
            if future:
                return future[0]
    except Exception:
        pass
    # Fallback: calendar
    try:
        cal = tk.calendar
        if isinstance(cal, dict):
            vals = cal.get("Earnings Date") or []
            vals = vals if isinstance(vals, (list, tuple)) else [vals]
            future = []
            for v in vals:
                d = pd.to_datetime(v, errors="coerce")
                if pd.notna(d) and d.date() >= today:
                    future.append(d.date())
            if future:
                return sorted(future)[0]
        elif isinstance(cal, pd.DataFrame) and not cal.empty:
            d = pd.to_datetime(cal.iloc[0, 0], errors="coerce")
            if pd.notna(d) and d.date() >= today:
                return d.date()
    except Exception:
        pass
    return None


def sector_etf_for(sector: Optional[str]) -> Optional[str]:
    if not sector:
        return None
    return SECTOR_ETF.get(sector.strip())


def load_universe_csv(path: str) -> tuple:
    """Read universe.csv -> (tickers, {ticker: sector}).

    Column 1 must hold the ticker. An optional 'sector' column (as exported
    from Finviz) lets the screener skip the slow Yahoo sector lookup.
    """
    import csv

    tickers: List[str] = []
    sectors: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None) or []
            cols = [h.strip().lower() for h in header]
            sec_idx = cols.index("sector") if "sector" in cols else None
            if cols and cols[0] not in ("ticker", "symbol"):
                reader = [header] + list(reader)  # no header row after all
            for row in reader:
                if not row or not row[0].strip():
                    continue
                t = row[0].strip().upper()
                if t in sectors or t in tickers:
                    continue
                tickers.append(t)
                if sec_idx is not None and len(row) > sec_idx and row[sec_idx].strip():
                    sectors[t] = row[sec_idx].strip()
    except Exception:
        return [], {}
    return tickers, sectors


def parse_universe(text: str) -> List[str]:
    """Accepts tickers separated by commas, spaces, semicolons or newlines."""
    if not text:
        return []
    for ch in [",", ";", "\t", "\n", "\r"]:
        text = text.replace(ch, " ")
    seen, out = set(), []
    for tok in text.split(" "):
        t = tok.strip().upper()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out
