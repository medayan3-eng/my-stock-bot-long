"""Top-down context: market regime (on/off switch) and sector strength.

Murphy's premise: ~80% of a stock's move comes from the market and its
sector, so both are checked before any individual chart is considered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import indicators as ind
from .data import SECTOR_ETF, VIX, download_prices, sector_etf_for


@dataclass
class MarketRegime:
    ok: bool = False
    benchmark: str = "SPY"
    benchmark_price: float = float("nan")
    benchmark_sma: float = float("nan")
    benchmark_above_ma: bool = False
    vix: Optional[float] = None
    vix_ok: bool = True
    breadth_pct: Optional[float] = None
    breadth_ok: bool = True
    notes: List[str] = field(default_factory=list)

    @property
    def headline(self) -> str:
        return "RISK-ON - long entries allowed" if self.ok else "RISK-OFF - stand aside"


def evaluate_regime(cfg: dict, prices: Dict[str, pd.DataFrame]) -> MarketRegime:
    """`prices` must already contain the benchmark (and ^VIX if used)."""
    rc = cfg["regime"]
    bench = rc["benchmark"]
    reg = MarketRegime(benchmark=bench)

    bdf = prices.get(bench)
    if bdf is None or len(bdf) < rc["benchmark_ma"] + 5:
        reg.notes.append(f"No usable price history for {bench}; regime unknown.")
        return reg

    sma = ind.sma(bdf["Close"], rc["benchmark_ma"])
    reg.benchmark_price = float(bdf["Close"].iloc[-1])
    reg.benchmark_sma = ind.last_valid(sma)
    reg.benchmark_above_ma = reg.benchmark_price > reg.benchmark_sma
    if not reg.benchmark_above_ma:
        reg.notes.append(
            f"{bench} is below its {rc['benchmark_ma']}-day SMA "
            f"({reg.benchmark_price:.2f} vs {reg.benchmark_sma:.2f})."
        )

    if rc.get("use_vix", True):
        vdf = prices.get(VIX)
        if vdf is not None and not vdf.empty:
            reg.vix = float(vdf["Close"].iloc[-1])
            reg.vix_ok = reg.vix < float(rc["vix_max"])
            if not reg.vix_ok:
                reg.notes.append(f"VIX {reg.vix:.1f} is above the {rc['vix_max']:.0f} panic threshold.")
        else:
            reg.notes.append("VIX unavailable - volatility filter skipped.")

    reg.ok = reg.benchmark_above_ma and reg.vix_ok
    return reg


def apply_breadth(reg: MarketRegime, cfg: dict, breadth_pct: Optional[float]) -> MarketRegime:
    """Optional breadth check: % of the scanned universe above its own SMA200."""
    min_breadth = float(cfg["regime"].get("breadth_min_pct", 0) or 0)
    reg.breadth_pct = breadth_pct
    if min_breadth <= 0 or breadth_pct is None:
        return reg
    reg.breadth_ok = breadth_pct >= min_breadth
    if not reg.breadth_ok:
        reg.notes.append(
            f"Only {breadth_pct:.0f}% of the universe is above its 200-day SMA "
            f"(minimum {min_breadth:.0f}%)."
        )
        reg.ok = False
    return reg


# --------------------------------------------------------------------------- #
# Sector strength
# --------------------------------------------------------------------------- #
def sector_universe() -> List[str]:
    return sorted(set(SECTOR_ETF.values()))


def build_sector_table(cfg: dict, benchmark_df: Optional[pd.DataFrame]) -> Dict[str, dict]:
    """RSI and relative strength for every SPDR sector ETF."""
    sc = cfg["sector"]
    etfs = sector_universe()
    prices = download_prices(etfs, period="1y")
    lookback = int(sc["rs_lookback_days"])

    bench_ret = (
        ind.pct_return(benchmark_df["Close"], lookback)
        if benchmark_df is not None and not benchmark_df.empty
        else float("nan")
    )

    table: Dict[str, dict] = {}
    for etf in etfs:
        df = prices.get(etf)
        if df is None or df.empty:
            table[etf] = {"etf": etf, "rsi": None, "rs_pct": None, "ok": None}
            continue
        rsi_val = ind.last_valid(ind.rsi(df["Close"], int(sc["rsi_length"])))
        etf_ret = ind.pct_return(df["Close"], lookback)
        rs = (etf_ret - bench_ret) * 100.0 if pd.notna(etf_ret) and pd.notna(bench_ret) else None

        rsi_ok = pd.notna(rsi_val) and rsi_val > float(sc["min_rsi"])
        rs_ok = rs is not None and rs > 0

        mode = sc.get("mode", "rsi_or_rs")
        if mode == "rsi_only":
            ok = bool(rsi_ok)
        elif mode == "rs_only":
            ok = bool(rs_ok)
        else:
            ok = bool(rsi_ok or rs_ok)

        table[etf] = {
            "etf": etf,
            "rsi": None if pd.isna(rsi_val) else round(float(rsi_val), 1),
            "rs_pct": None if rs is None else round(float(rs), 2),
            "ok": ok,
        }
    return table


def sector_status(sector: Optional[str], table: Dict[str, dict]) -> dict:
    etf = sector_etf_for(sector)
    if etf is None or etf not in table:
        return {"etf": etf, "rsi": None, "rs_pct": None, "ok": None}
    return table[etf]
