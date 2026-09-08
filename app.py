"""Murphy Swing Screener - Streamlit front end.

Run at the end of the trading day:  streamlit run app.py
The app never trades. It produces a ranked shortlist for manual analysis.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Dict, List

import pandas as pd
import streamlit as st"""Murphy Swing Screener - Streamlit front end.

Run at the end of the trading day:  streamlit run app.py
The app never trades. It produces a ranked shortlist for manual analysis.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Dict, List

import pandas as pd
import streamlit as st

from src import exits as exit_engine
from src import indicators as ind
from src import market as market_mod
from src import screener as screener_mod
from src.config import load_config
from src.data import (
    BENCHMARK,
    VIX,
    download_prices,
    get_fundamentals,
    load_universe_csv,
    parse_universe,
)

st.set_page_config(page_title="Murphy Swing Screener", page_icon="📈", layout="wide")

CFG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
UNIVERSE_PATH = os.path.join(os.path.dirname(__file__), "universe.csv")


# --------------------------------------------------------------------------- #
# Cached data access
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60 * 30, show_spinner=False)
def cached_prices(tickers: tuple, period: str) -> Dict[str, pd.DataFrame]:
    return download_prices(list(tickers), period=period)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def cached_fundamentals(tickers: tuple, need_info: bool, need_earnings: bool) -> Dict[str, dict]:
    return {
        t: get_fundamentals(t, need_info=need_info, need_earnings=need_earnings)
        for t in tickers
    }


@st.cache_data(ttl=60 * 30, show_spinner=False)
def cached_sector_table(_cfg: dict, bench_df: pd.DataFrame) -> Dict[str, dict]:
    return market_mod.build_sector_table(_cfg, bench_df)


@st.cache_data(show_spinner=False)
def load_default_universe() -> tuple:
    """Returns (text_for_the_box, {ticker: sector})."""
    tickers, sectors = load_universe_csv(UNIVERSE_PATH)
    if tickers:
        return "\n".join(tickers), sectors
    fallback = "AAPL MSFT NVDA AMD AVGO META GOOGL AMZN JPM XOM CAT UNH COST LLY NFLX"
    return fallback, {}


# --------------------------------------------------------------------------- #
# Sidebar: configuration
# --------------------------------------------------------------------------- #
cfg = load_config(CFG_PATH)

st.sidebar.title("⚙️ Screener settings")
st.sidebar.caption("Defaults come from config.yaml. Changes here apply to this session only.")

with st.sidebar.expander("Market regime", expanded=True):
    cfg["regime"]["benchmark_ma"] = st.number_input("Benchmark SMA length", 50, 300, int(cfg["regime"]["benchmark_ma"]), 10)
    cfg["regime"]["use_vix"] = st.checkbox("Use VIX filter", value=bool(cfg["regime"]["use_vix"]))
    cfg["regime"]["vix_max"] = st.number_input("Block longs when VIX >", 10.0, 60.0, float(cfg["regime"]["vix_max"]), 1.0)
    cfg["regime"]["breadth_min_pct"] = st.slider("Min % of universe above its SMA200 (0 = off)", 0, 100, int(cfg["regime"]["breadth_min_pct"]))

with st.sidebar.expander("Trend & entry zone", expanded=True):
    cfg["trend"]["min_pct_of_52w_high"] = st.slider("Min % of 52-week high", 50.0, 100.0, float(cfg["trend"]["min_pct_of_52w_high"]), 1.0)
    cfg["trend"]["sma200_slope_lookback"] = st.number_input("SMA200 slope lookback (bars)", 5, 60, int(cfg["trend"]["sma200_slope_lookback"]), 1)
    cfg["entry_zone"]["max_pct_below_sma50"] = st.slider("Max % below the 50MA", 0.0, 10.0, float(cfg["entry_zone"]["max_pct_below_sma50"]), 0.5)
    cfg["entry_zone"]["max_pct_above_sma50"] = st.slider("Max % above the 50MA", 1.0, 20.0, float(cfg["entry_zone"]["max_pct_above_sma50"]), 0.5)

with st.sidebar.expander("Volume, liquidity & RS", expanded=False):
    cfg["volume"]["surge_multiple"] = st.slider("Volume surge multiple", 1.0, 4.0, float(cfg["volume"]["surge_multiple"]), 0.1)
    cfg["volume"]["surge_lookback_days"] = st.number_input("Surge lookback (days)", 1, 10, int(cfg["volume"]["surge_lookback_days"]), 1)
    cfg["liquidity"]["min_price"] = st.number_input("Min price ($)", 1.0, 100.0, float(cfg["liquidity"]["min_price"]), 1.0)
    cfg["liquidity"]["min_adv_shares"] = st.number_input("Min average daily volume (shares)", 50_000, 10_000_000, int(cfg["liquidity"]["min_adv_shares"]), 50_000)
    cfg["relative_strength"]["lookback_days"] = st.number_input("RS lookback (days)", 20, 250, int(cfg["relative_strength"]["lookback_days"]), 5)

with st.sidebar.expander("Squeeze, ownership, sector, earnings", expanded=False):
    cfg["squeeze"]["max_ratio"] = st.slider("Max ATR(10)/ATR(50) ratio", 0.5, 1.5, float(cfg["squeeze"]["max_ratio"]), 0.05)
    cfg["ownership"]["min_institutional_pct"] = st.slider("Min institutional ownership %", 0.0, 90.0, float(cfg["ownership"]["min_institutional_pct"]), 1.0)
    cfg["sector"]["enabled"] = st.checkbox("Sector strength filter", value=bool(cfg["sector"]["enabled"]))
    cfg["sector"]["mode"] = st.selectbox("Sector rule", ["rsi_or_rs", "rsi_only", "rs_only"], index=["rsi_or_rs", "rsi_only", "rs_only"].index(cfg["sector"]["mode"]))
    cfg["earnings"]["enabled"] = st.checkbox("Earnings blackout filter", value=bool(cfg["earnings"]["enabled"]))
    cfg["earnings"]["blackout_days"] = st.number_input("Blackout window (days before earnings)", 0, 30, int(cfg["earnings"]["blackout_days"]), 1)

with st.sidebar.expander("Risk & position sizing", expanded=False):
    cfg["risk"]["account_size"] = st.number_input("Account size ($)", 1_000.0, 100_000_000.0, float(cfg["risk"]["account_size"]), 1_000.0)
    cfg["risk"]["risk_per_trade_pct"] = st.slider("Risk per trade (%)", 0.1, 5.0, float(cfg["risk"]["risk_per_trade_pct"]), 0.1)
    cfg["risk"]["max_position_pct"] = st.slider("Max position size (% of account)", 1.0, 100.0, float(cfg["risk"]["max_position_pct"]), 1.0)
    cfg["exits"]["initial_stop_atr_multiple"] = st.slider("Initial stop (x ATR)", 1.0, 5.0, float(cfg["exits"]["initial_stop_atr_multiple"]), 0.5)
    cfg["exits"]["trail_atr_multiple"] = st.slider("Trailing stop (x ATR)", 1.0, 5.0, float(cfg["exits"]["trail_atr_multiple"]), 0.5)

st.sidebar.markdown("---")
prefiltered = st.sidebar.checkbox(
    "Universe pre-filtered in Finviz", value=True,
    help=(
        "The Finviz screen already enforces price, average volume, institutional "
        "ownership >= 10%, beta > 1 and price above the 200-day SMA, and universe.csv "
        "carries the sector. With this on, the app trusts those and skips the slow "
        "per-ticker Yahoo profile request - scans run roughly 10x faster."
    ),
)
cfg["scan"]["fetch_fundamentals"] = st.sidebar.checkbox(
    "Fetch fundamentals (slower)", value=bool(cfg["scan"]["fetch_fundamentals"]),
    help="Earnings dates, plus ownership and sector when the box above is off.",
)
if prefiltered:
    cfg["ownership"]["on_missing"] = "pass"
strict_mode = st.sidebar.checkbox("Show only full passes", value=False)

if st.sidebar.button("🗑️ Clear cached data"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared.")


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("📈 Murphy Swing Screener")
st.caption(
    "End-of-day scanner for multi-week to multi-month swing trades. "
    "It surfaces candidates - you do the chart work and decide."
)

default_text, default_sectors = load_default_universe()
sector_map: Dict[str, str] = dict(default_sectors)

universe_text = st.text_area(
    "Universe (tickers separated by space, comma or newline)",
    value=st.session_state.get("universe_text", default_text),
    height=110,
)
uploaded = st.file_uploader(
    "...or upload a Finviz export / CSV (first column = ticker, optional 'Sector' column)",
    type=["csv", "txt"],
)
if uploaded is not None:
    try:
        udf = pd.read_csv(uploaded)
        tick_col = udf.columns[0]
        universe_text = " ".join(str(x) for x in udf[tick_col].dropna())
        sec_col = next((c for c in udf.columns if str(c).strip().lower() == "sector"), None)
        if sec_col is not None:
            sector_map.update(
                {
                    str(r[tick_col]).strip().upper(): str(r[sec_col]).strip()
                    for _, r in udf.dropna(subset=[tick_col, sec_col]).iterrows()
                }
            )
    except Exception:
        uploaded.seek(0)
        universe_text = uploaded.read().decode("utf-8", errors="ignore")

tickers: List[str] = parse_universe(universe_text)
st.session_state["universe_text"] = universe_text

col_a, col_b = st.columns([1, 3])
run = col_a.button("▶️ Run scan", type="primary", use_container_width=True)
known = sum(1 for t in tickers if sector_map.get(t))
col_b.caption(f"{len(tickers)} ticker(s) in the universe · {known} with a known sector.")


# --------------------------------------------------------------------------- #
# Scan
# --------------------------------------------------------------------------- #
def run_scan(tickers: List[str], cfg: dict) -> dict:
    fetch_list = tickers + [cfg["regime"]["benchmark"]]
    if cfg["regime"]["use_vix"]:
        fetch_list.append(VIX)

    with st.spinner("Downloading price history..."):
        prices = cached_prices(tuple(sorted(set(fetch_list))), cfg["scan"]["history_period"])

    bench_df = prices.get(cfg["regime"]["benchmark"])
    regime = market_mod.evaluate_regime(cfg, prices)

    with st.spinner("Measuring sector strength..."):
        sector_table = cached_sector_table(cfg, bench_df) if cfg["sector"]["enabled"] else {}

    fundamentals: Dict[str, dict] = {t: {"sector": sector_map.get(t)} for t in tickers}
    if cfg["scan"]["fetch_fundamentals"]:
        with st.spinner("Fetching earnings dates and ownership..."):
            got = cached_fundamentals(
                tuple(sorted(set(tickers))),
                need_info=not prefiltered,
                need_earnings=bool(cfg["earnings"]["enabled"]),
            )
        for t, fnd in got.items():
            base = fundamentals.get(t, {})
            merged = {k: v for k, v in fnd.items() if v is not None}
            base.update(merged)
            if not base.get("sector"):
                base["sector"] = sector_map.get(t)
            fundamentals[t] = base

    results = screener_mod.scan(prices, cfg, sector_table, fundamentals, tickers)

    breadth = None
    valid = [t for t in tickers if t in prices and len(prices[t]) > 210]
    if valid:
        above = 0
        for t in valid:
            c = prices[t]["Close"]
            s200 = ind.last_valid(ind.sma(c, 200))
            if pd.notna(s200) and float(c.iloc[-1]) > s200:
                above += 1
        breadth = above / len(valid) * 100.0
    regime = market_mod.apply_breadth(regime, cfg, breadth)

    return {"prices": prices, "regime": regime, "results": results, "sector_table": sector_table}


if run:
    if not tickers:
        st.error("Add at least one ticker.")
    else:
        st.session_state["scan"] = run_scan(tickers, cfg)
        st.session_state["scan_time"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

scan_state = st.session_state.get("scan")


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
if not scan_state:
    st.info("Set your universe and press **Run scan**. Recommended time: after the US close.")
    st.stop()

regime = scan_state["regime"]
results: pd.DataFrame = scan_state["results"]
prices = scan_state["prices"]

st.caption(f"Last scan: {st.session_state.get('scan_time', '')}")

m1, m2, m3, m4 = st.columns(4)
m1.metric(f"{regime.benchmark} vs SMA{cfg['regime']['benchmark_ma']}",
          f"{regime.benchmark_price:,.2f}",
          f"{(regime.benchmark_price / regime.benchmark_sma - 1) * 100:+.1f}%" if regime.benchmark_sma else "n/a")
m2.metric("VIX", f"{regime.vix:.1f}" if regime.vix else "n/a",
          "calm" if regime.vix_ok else "panic", delta_color="normal" if regime.vix_ok else "inverse")
m3.metric("Breadth (% above SMA200)", f"{regime.breadth_pct:.0f}%" if regime.breadth_pct is not None else "n/a")
m4.metric("Candidates", int(results["passes_all"].sum()) if not results.empty else 0)

if regime.ok:
    st.success(f"**{regime.headline}**")
else:
    st.error(f"**{regime.headline}** - " + " ".join(regime.notes))
    st.caption("Candidates below are shown for study only. The regime switch is off, so no new longs.")

tab_scan, tab_detail, tab_plan, tab_sectors = st.tabs(
    ["🔎 Results", "📊 Chart & metrics", "🎯 Trade plan", "🏭 Sectors"]
)

# ------------------------------- Results ---------------------------------- #
with tab_scan:
    if results.empty:
        st.warning("No results.")
    else:
        view = results[results["passes_all"]] if strict_mode else results
        chk_cols = [f"chk_{r}" for r in screener_mod.RULES if f"chk_{r}" in view.columns]
        base_cols = [
            "ticker", "score", "rules_passed", "price", "dist_sma50_pct",
            "pct_of_52w_high", "rs_excess_pct", "vol_ratio_max3", "squeeze_ratio",
            "inst_own_pct", "sector", "days_to_earnings",
        ]
        base_cols = [c for c in base_cols if c in view.columns]
        table = view[base_cols + chk_cols + ["failed_rules", "warnings"]] if not view.empty else view

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                "dist_sma50_pct": st.column_config.NumberColumn("% vs 50MA", format="%.2f%%"),
                "pct_of_52w_high": st.column_config.NumberColumn("% of 52w high", format="%.1f%%"),
                "rs_excess_pct": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
                "vol_ratio_max3": st.column_config.NumberColumn("Vol x avg (3d max)", format="%.2f"),
                "squeeze_ratio": st.column_config.NumberColumn("ATR10/ATR50", format="%.2f"),
                "inst_own_pct": st.column_config.NumberColumn("Inst %", format="%.1f%%"),
                **{c: st.column_config.CheckboxColumn(screener_mod.RULE_LABELS[c[4:]]) for c in chk_cols},
            },
        )
        st.download_button(
            "⬇️ Download results (CSV)",
            results.to_csv(index=False).encode("utf-8"),
            file_name=f"scan_{dt.date.today().isoformat()}.csv",
            mime="text/csv",
        )

# ------------------------------- Detail ----------------------------------- #
with tab_detail:
    ok_list = results[results["status"] == "ok"]["ticker"].tolist() if not results.empty else []
    if not ok_list:
        st.info("Nothing to display.")
    else:
        sel = st.selectbox("Ticker", ok_list, key="detail_ticker")
        row = results[results["ticker"] == sel].iloc[0]
        df = prices.get(sel)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", f"${row['price']:.2f}")
        c2.metric("vs 50MA", f"{row['dist_sma50_pct']:+.2f}%")
        c3.metric("RS vs SPY (60d)", f"{row['rs_excess_pct']:+.2f}%" if pd.notna(row["rs_excess_pct"]) else "n/a")
        c4.metric("Score", f"{row['score']:.0f}/100")

        if df is not None and len(df) > 50:
            try:
                import plotly.graph_objects as go

                plot = df.iloc[-250:]
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=plot.index, open=plot["Open"], high=plot["High"],
                    low=plot["Low"], close=plot["Close"], name=sel))
                fig.add_trace(go.Scatter(x=plot.index, y=ind.sma(df["Close"], 50).iloc[-250:],
                                         name="SMA 50", line=dict(width=1.5)))
                fig.add_trace(go.Scatter(x=plot.index, y=ind.sma(df["Close"], 200).iloc[-250:],
                                         name="SMA 200", line=dict(width=1.5)))
                fig.update_layout(height=460, xaxis_rangeslider_visible=False,
                                  margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.line_chart(df["Close"].iloc[-250:])

        st.subheader("Rule breakdown")
        rule_rows = [
            {"Rule": screener_mod.RULE_LABELS[r], "Pass": bool(row.get(f"chk_{r}", False))}
            for r in screener_mod.RULES if f"chk_{r}" in row
        ]
        st.dataframe(pd.DataFrame(rule_rows), hide_index=True, use_container_width=True)
        if row.get("warnings"):
            st.warning(row["warnings"])

        with st.expander("All metrics"):
            st.json({k: (None if pd.isna(v) else v) for k, v in row.items() if not k.startswith("chk_")})

# ------------------------------- Trade plan -------------------------------- #
with tab_plan:
    ok_list = results[results["status"] == "ok"]["ticker"].tolist() if not results.empty else []
    if not ok_list:
        st.info("Run a scan first.")
    else:
        sel = st.selectbox("Ticker", ok_list, key="plan_ticker")
        row = results[results["ticker"] == sel].iloc[0]

        c1, c2 = st.columns(2)
        entry = c1.number_input("Planned entry price ($)", value=float(row["price"]), step=0.01)
        atr_val = c2.number_input("ATR(14) ($)", value=float(row["atr14"] or 0.0), step=0.01)

        pattern = st.selectbox("Chart pattern", list(exit_engine.PATTERNS.keys()),
                               index=len(exit_engine.PATTERNS) - 1)
        breakout = height = None
        if pattern != "No clear pattern":
            p1, p2 = st.columns(2)
            breakout = p1.number_input("Breakout / neckline level ($)", value=float(row["price"]), step=0.01)
            height = p2.number_input("Pattern height ($)", value=round(float(row["price"]) * 0.10, 2), step=0.01,
                                     help="Flagpole length, triangle base, cup depth or head-to-neckline distance.")
            st.caption(exit_engine.PATTERNS[pattern])

        plan = exit_engine.build_plan(
            entry=entry, atr=atr_val, swing_low=float(row["swing_low_20"] or 0) or None,
            cfg=cfg, pattern=pattern, breakout_level=breakout, pattern_height=height,
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Initial stop", f"${plan.initial_stop:.2f}", f"-{plan.risk_pct:.1f}%")
        k2.metric("Shares", f"{plan.shares:,}")
        k3.metric("Position value", f"${plan.position_value:,.0f}")
        k4.metric("Capital at risk", f"${plan.capital_at_risk:,.0f}")
        st.caption(f"Stop placed {plan.stop_basis}. Risk per share ${plan.risk_per_share:.2f}.")

        if plan.target:
            st.success(f"Measured-move target **${plan.target:.2f}**  ·  reward/risk **{plan.reward_risk:.2f}R**")
            st.caption(plan.target_basis)
        else:
            st.info("No pattern target - the profit ladder below manages the exit.")

        st.subheader("Profit ladder")
        st.dataframe(pd.DataFrame(plan.ladder), hide_index=True, use_container_width=True)
        st.caption(
            f"Runner management: trail {cfg['exits']['trail_atr_multiple']:g} x ATR below the highest close "
            f"since entry (currently ≈ ${exit_engine.trailing_stop(entry, atr_val, cfg['exits']['trail_atr_multiple']):.2f})."
        )

# ------------------------------- Sectors ----------------------------------- #
with tab_sectors:
    table = scan_state.get("sector_table") or {}
    if not table:
        st.info("Sector filter disabled or unavailable.")
    else:
        sdf = pd.DataFrame(table.values()).sort_values("rs_pct", ascending=False, na_position="last")
        st.dataframe(sdf, hide_index=True, use_container_width=True,
                     column_config={
                         "etf": "Sector ETF",
                         "rsi": st.column_config.NumberColumn("RSI(14)", format="%.1f"),
                         "rs_pct": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
                         "ok": st.column_config.CheckboxColumn("Strong"),
                     })
        st.caption("Top-down: trade leaders inside leading sectors.")


from src import exits as exit_engine
from src import indicators as ind
from src import market as market_mod
from src import screener as screener_mod
from src.config import load_config
from src.data import (
    BENCHMARK,
    VIX,
    download_prices,
    get_fundamentals,
    load_universe_csv,
    parse_universe,
)

st.set_page_config(page_title="Murphy Swing Screener", page_icon="📈", layout="wide")

CFG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
UNIVERSE_PATH = os.path.join(os.path.dirname(__file__), "universe.csv")


# --------------------------------------------------------------------------- #
# Cached data access
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60 * 30, show_spinner=False)
def cached_prices(tickers: tuple, period: str) -> Dict[str, pd.DataFrame]:
    return download_prices(list(tickers), period=period)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def cached_fundamentals(tickers: tuple, need_info: bool, need_earnings: bool) -> Dict[str, dict]:
    return {
        t: get_fundamentals(t, need_info=need_info, need_earnings=need_earnings)
        for t in tickers
    }


@st.cache_data(ttl=60 * 30, show_spinner=False)
def cached_sector_table(_cfg: dict, bench_df: pd.DataFrame) -> Dict[str, dict]:
    return market_mod.build_sector_table(_cfg, bench_df)


@st.cache_data(show_spinner=False)
def load_default_universe() -> tuple:
    """Returns (text_for_the_box, {ticker: sector})."""
    tickers, sectors = load_universe_csv(UNIVERSE_PATH)
    if tickers:
        return "\n".join(tickers), sectors
    fallback = "AAPL MSFT NVDA AMD AVGO META GOOGL AMZN JPM XOM CAT UNH COST LLY NFLX"
    return fallback, {}


# --------------------------------------------------------------------------- #
# Sidebar: configuration
# --------------------------------------------------------------------------- #
cfg = load_config(CFG_PATH)

st.sidebar.title("⚙️ Screener settings")
st.sidebar.caption("Defaults come from config.yaml. Changes here apply to this session only.")

with st.sidebar.expander("Market regime", expanded=True):
    cfg["regime"]["benchmark_ma"] = st.number_input("Benchmark SMA length", 50, 300, int(cfg["regime"]["benchmark_ma"]), 10)
    cfg["regime"]["use_vix"] = st.checkbox("Use VIX filter", value=bool(cfg["regime"]["use_vix"]))
    cfg["regime"]["vix_max"] = st.number_input("Block longs when VIX >", 10.0, 60.0, float(cfg["regime"]["vix_max"]), 1.0)
    cfg["regime"]["breadth_min_pct"] = st.slider("Min % of universe above its SMA200 (0 = off)", 0, 100, int(cfg["regime"]["breadth_min_pct"]))

with st.sidebar.expander("Trend & entry zone", expanded=True):
    cfg["trend"]["min_pct_of_52w_high"] = st.slider("Min % of 52-week high", 50.0, 100.0, float(cfg["trend"]["min_pct_of_52w_high"]), 1.0)
    cfg["trend"]["sma200_slope_lookback"] = st.number_input("SMA200 slope lookback (bars)", 5, 60, int(cfg["trend"]["sma200_slope_lookback"]), 1)
    cfg["entry_zone"]["max_pct_below_sma50"] = st.slider("Max % below the 50MA", 0.0, 10.0, float(cfg["entry_zone"]["max_pct_below_sma50"]), 0.5)
    cfg["entry_zone"]["max_pct_above_sma50"] = st.slider("Max % above the 50MA", 1.0, 20.0, float(cfg["entry_zone"]["max_pct_above_sma50"]), 0.5)

with st.sidebar.expander("Volume, liquidity & RS", expanded=False):
    cfg["volume"]["surge_multiple"] = st.slider("Volume surge multiple", 1.0, 4.0, float(cfg["volume"]["surge_multiple"]), 0.1)
    cfg["volume"]["surge_lookback_days"] = st.number_input("Surge lookback (days)", 1, 10, int(cfg["volume"]["surge_lookback_days"]), 1)
    cfg["liquidity"]["min_price"] = st.number_input("Min price ($)", 1.0, 100.0, float(cfg["liquidity"]["min_price"]), 1.0)
    cfg["liquidity"]["min_adv_shares"] = st.number_input("Min average daily volume (shares)", 50_000, 10_000_000, int(cfg["liquidity"]["min_adv_shares"]), 50_000)
    cfg["relative_strength"]["lookback_days"] = st.number_input("RS lookback (days)", 20, 250, int(cfg["relative_strength"]["lookback_days"]), 5)

with st.sidebar.expander("Squeeze, ownership, sector, earnings", expanded=False):
    cfg["squeeze"]["max_ratio"] = st.slider("Max ATR(10)/ATR(50) ratio", 0.5, 1.5, float(cfg["squeeze"]["max_ratio"]), 0.05)
    cfg["ownership"]["min_institutional_pct"] = st.slider("Min institutional ownership %", 0.0, 90.0, float(cfg["ownership"]["min_institutional_pct"]), 1.0)
    cfg["sector"]["enabled"] = st.checkbox("Sector strength filter", value=bool(cfg["sector"]["enabled"]))
    cfg["sector"]["mode"] = st.selectbox("Sector rule", ["rsi_or_rs", "rsi_only", "rs_only"], index=["rsi_or_rs", "rsi_only", "rs_only"].index(cfg["sector"]["mode"]))
    cfg["earnings"]["enabled"] = st.checkbox("Earnings blackout filter", value=bool(cfg["earnings"]["enabled"]))
    cfg["earnings"]["blackout_days"] = st.number_input("Blackout window (days before earnings)", 0, 30, int(cfg["earnings"]["blackout_days"]), 1)

with st.sidebar.expander("Risk & position sizing", expanded=False):
    cfg["risk"]["account_size"] = st.number_input("Account size ($)", 1_000.0, 100_000_000.0, float(cfg["risk"]["account_size"]), 1_000.0)
    cfg["risk"]["risk_per_trade_pct"] = st.slider("Risk per trade (%)", 0.1, 5.0, float(cfg["risk"]["risk_per_trade_pct"]), 0.1)
    cfg["risk"]["max_position_pct"] = st.slider("Max position size (% of account)", 1.0, 100.0, float(cfg["risk"]["max_position_pct"]), 1.0)
    cfg["exits"]["initial_stop_atr_multiple"] = st.slider("Initial stop (x ATR)", 1.0, 5.0, float(cfg["exits"]["initial_stop_atr_multiple"]), 0.5)
    cfg["exits"]["trail_atr_multiple"] = st.slider("Trailing stop (x ATR)", 1.0, 5.0, float(cfg["exits"]["trail_atr_multiple"]), 0.5)

st.sidebar.markdown("---")
prefiltered = st.sidebar.checkbox(
    "Universe pre-filtered in Finviz", value=True,
    help=(
        "The Finviz screen already enforces price, average volume, institutional "
        "ownership >= 10%, beta > 1 and price above the 200-day SMA, and universe.csv "
        "carries the sector. With this on, the app trusts those and skips the slow "
        "per-ticker Yahoo profile request - scans run roughly 10x faster."
    ),
)
cfg["scan"]["fetch_fundamentals"] = st.sidebar.checkbox(
    "Fetch fundamentals (slower)", value=bool(cfg["scan"]["fetch_fundamentals"]),
    help="Earnings dates, plus ownership and sector when the box above is off.",
)
if prefiltered:
    cfg["ownership"]["on_missing"] = "pass"
strict_mode = st.sidebar.checkbox("Show only full passes", value=False)

if st.sidebar.button("🗑️ Clear cached data"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared.")


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("📈 Murphy Swing Screener")
st.caption(
    "End-of-day scanner for multi-week to multi-month swing trades. "
    "It surfaces candidates - you do the chart work and decide."
)

default_text, default_sectors = load_default_universe()
sector_map: Dict[str, str] = dict(default_sectors)

universe_text = st.text_area(
    "Universe (tickers separated by space, comma or newline)",
    value=st.session_state.get("universe_text", default_text),
    height=110,
)
uploaded = st.file_uploader(
    "...or upload a Finviz export / CSV (first column = ticker, optional 'Sector' column)",
    type=["csv", "txt"],
)
if uploaded is not None:
    try:
        udf = pd.read_csv(uploaded)
        tick_col = udf.columns[0]
        universe_text = " ".join(str(x) for x in udf[tick_col].dropna())
        sec_col = next((c for c in udf.columns if str(c).strip().lower() == "sector"), None)
        if sec_col is not None:
            sector_map.update(
                {
                    str(r[tick_col]).strip().upper(): str(r[sec_col]).strip()
                    for _, r in udf.dropna(subset=[tick_col, sec_col]).iterrows()
                }
            )
    except Exception:
        uploaded.seek(0)
        universe_text = uploaded.read().decode("utf-8", errors="ignore")

tickers: List[str] = parse_universe(universe_text)
st.session_state["universe_text"] = universe_text

col_a, col_b = st.columns([1, 3])
run = col_a.button("▶️ Run scan", type="primary", use_container_width=True)
known = sum(1 for t in tickers if sector_map.get(t))
col_b.caption(f"{len(tickers)} ticker(s) in the universe · {known} with a known sector.")


# --------------------------------------------------------------------------- #
# Scan
# --------------------------------------------------------------------------- #
def run_scan(tickers: List[str], cfg: dict) -> dict:
    fetch_list = tickers + [cfg["regime"]["benchmark"]]
    if cfg["regime"]["use_vix"]:
        fetch_list.append(VIX)

    with st.spinner("Downloading price history..."):
        prices = cached_prices(tuple(sorted(set(fetch_list))), cfg["scan"]["history_period"])

    bench_df = prices.get(cfg["regime"]["benchmark"])
    regime = market_mod.evaluate_regime(cfg, prices)

    with st.spinner("Measuring sector strength..."):
        sector_table = cached_sector_table(cfg, bench_df) if cfg["sector"]["enabled"] else {}

    fundamentals: Dict[str, dict] = {t: {"sector": sector_map.get(t)} for t in tickers}
    if cfg["scan"]["fetch_fundamentals"]:
        with st.spinner("Fetching earnings dates and ownership..."):
            got = cached_fundamentals(
                tuple(sorted(set(tickers))),
                need_info=not prefiltered,
                need_earnings=bool(cfg["earnings"]["enabled"]),
            )
        for t, fnd in got.items():
            base = fundamentals.get(t, {})
            merged = {k: v for k, v in fnd.items() if v is not None}
            base.update(merged)
            if not base.get("sector"):
                base["sector"] = sector_map.get(t)
            fundamentals[t] = base

    results = screener_mod.scan(prices, cfg, sector_table, fundamentals, tickers)

    breadth = None
    valid = [t for t in tickers if t in prices and len(prices[t]) > 210]
    if valid:
        above = 0
        for t in valid:
            c = prices[t]["Close"]
            s200 = ind.last_valid(ind.sma(c, 200))
            if pd.notna(s200) and float(c.iloc[-1]) > s200:
                above += 1
        breadth = above / len(valid) * 100.0
    regime = market_mod.apply_breadth(regime, cfg, breadth)

    return {"prices": prices, "regime": regime, "results": results, "sector_table": sector_table}


if run:
    if not tickers:
        st.error("Add at least one ticker.")
    else:
        st.session_state["scan"] = run_scan(tickers, cfg)
        st.session_state["scan_time"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

scan_state = st.session_state.get("scan")


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
if not scan_state:
    st.info("Set your universe and press **Run scan**. Recommended time: after the US close.")
    st.stop()

regime = scan_state["regime"]
results: pd.DataFrame = scan_state["results"]
prices = scan_state["prices"]

st.caption(f"Last scan: {st.session_state.get('scan_time', '')}")

m1, m2, m3, m4 = st.columns(4)
m1.metric(f"{regime.benchmark} vs SMA{cfg['regime']['benchmark_ma']}",
          f"{regime.benchmark_price:,.2f}",
          f"{(regime.benchmark_price / regime.benchmark_sma - 1) * 100:+.1f}%" if regime.benchmark_sma else "n/a")
m2.metric("VIX", f"{regime.vix:.1f}" if regime.vix else "n/a",
          "calm" if regime.vix_ok else "panic", delta_color="normal" if regime.vix_ok else "inverse")
m3.metric("Breadth (% above SMA200)", f"{regime.breadth_pct:.0f}%" if regime.breadth_pct is not None else "n/a")
m4.metric("Candidates", int(results["passes_all"].sum()) if not results.empty else 0)

if regime.ok:
    st.success(f"**{regime.headline}**")
else:
    st.error(f"**{regime.headline}** - " + " ".join(regime.notes))
    st.caption("Candidates below are shown for study only. The regime switch is off, so no new longs.")

tab_scan, tab_detail, tab_plan, tab_sectors = st.tabs(
    ["🔎 Results", "📊 Chart & metrics", "🎯 Trade plan", "🏭 Sectors"]
)

# ------------------------------- Results ---------------------------------- #
with tab_scan:
    if results.empty:
        st.warning("No results.")
    else:
        view = results[results["passes_all"]] if strict_mode else results
        chk_cols = [f"chk_{r}" for r in screener_mod.RULES if f"chk_{r}" in view.columns]
        base_cols = [
            "ticker", "score", "rules_passed", "price", "dist_sma50_pct",
            "pct_of_52w_high", "rs_excess_pct", "vol_ratio_max3", "squeeze_ratio",
            "inst_own_pct", "sector", "days_to_earnings",
        ]
        base_cols = [c for c in base_cols if c in view.columns]
        table = view[base_cols + chk_cols + ["failed_rules", "warnings"]] if not view.empty else view

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                "dist_sma50_pct": st.column_config.NumberColumn("% vs 50MA", format="%.2f%%"),
                "pct_of_52w_high": st.column_config.NumberColumn("% of 52w high", format="%.1f%%"),
                "rs_excess_pct": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
                "vol_ratio_max3": st.column_config.NumberColumn("Vol x avg (3d max)", format="%.2f"),
                "squeeze_ratio": st.column_config.NumberColumn("ATR10/ATR50", format="%.2f"),
                "inst_own_pct": st.column_config.NumberColumn("Inst %", format="%.1f%%"),
                **{c: st.column_config.CheckboxColumn(screener_mod.RULE_LABELS[c[4:]]) for c in chk_cols},
            },
        )
        st.download_button(
            "⬇️ Download results (CSV)",
            results.to_csv(index=False).encode("utf-8"),
            file_name=f"scan_{dt.date.today().isoformat()}.csv",
            mime="text/csv",
        )

# ------------------------------- Detail ----------------------------------- #
with tab_detail:
    ok_list = results[results["status"] == "ok"]["ticker"].tolist() if not results.empty else []
    if not ok_list:
        st.info("Nothing to display.")
    else:
        sel = st.selectbox("Ticker", ok_list, key="detail_ticker")
        row = results[results["ticker"] == sel].iloc[0]
        df = prices.get(sel)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", f"${row['price']:.2f}")
        c2.metric("vs 50MA", f"{row['dist_sma50_pct']:+.2f}%")
        c3.metric("RS vs SPY (60d)", f"{row['rs_excess_pct']:+.2f}%" if pd.notna(row["rs_excess_pct"]) else "n/a")
        c4.metric("Score", f"{row['score']:.0f}/100")

        if df is not None and len(df) > 50:
            try:
                import plotly.graph_objects as go

                plot = df.iloc[-250:]
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=plot.index, open=plot["Open"], high=plot["High"],
                    low=plot["Low"], close=plot["Close"], name=sel))
                fig.add_trace(go.Scatter(x=plot.index, y=ind.sma(df["Close"], 50).iloc[-250:],
                                         name="SMA 50", line=dict(width=1.5)))
                fig.add_trace(go.Scatter(x=plot.index, y=ind.sma(df["Close"], 200).iloc[-250:],
                                         name="SMA 200", line=dict(width=1.5)))
                fig.update_layout(height=460, xaxis_rangeslider_visible=False,
                                  margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.line_chart(df["Close"].iloc[-250:])

        st.subheader("Rule breakdown")
        rule_rows = [
            {"Rule": screener_mod.RULE_LABELS[r], "Pass": bool(row.get(f"chk_{r}", False))}
            for r in screener_mod.RULES if f"chk_{r}" in row
        ]
        st.dataframe(pd.DataFrame(rule_rows), hide_index=True, use_container_width=True)
        if row.get("warnings"):
            st.warning(row["warnings"])

        with st.expander("All metrics"):
            st.json({k: (None if pd.isna(v) else v) for k, v in row.items() if not k.startswith("chk_")})

# ------------------------------- Trade plan -------------------------------- #
with tab_plan:
    ok_list = results[results["status"] == "ok"]["ticker"].tolist() if not results.empty else []
    if not ok_list:
        st.info("Run a scan first.")
    else:
        sel = st.selectbox("Ticker", ok_list, key="plan_ticker")
        row = results[results["ticker"] == sel].iloc[0]

        c1, c2 = st.columns(2)
        entry = c1.number_input("Planned entry price ($)", value=float(row["price"]), step=0.01)
        atr_val = c2.number_input("ATR(14) ($)", value=float(row["atr14"] or 0.0), step=0.01)

        pattern = st.selectbox("Chart pattern", list(exit_engine.PATTERNS.keys()),
                               index=len(exit_engine.PATTERNS) - 1)
        breakout = height = None
        if pattern != "No clear pattern":
            p1, p2 = st.columns(2)
            breakout = p1.number_input("Breakout / neckline level ($)", value=float(row["price"]), step=0.01)
            height = p2.number_input("Pattern height ($)", value=round(float(row["price"]) * 0.10, 2), step=0.01,
                                     help="Flagpole length, triangle base, cup depth or head-to-neckline distance.")
            st.caption(exit_engine.PATTERNS[pattern])

        plan = exit_engine.build_plan(
            entry=entry, atr=atr_val, swing_low=float(row["swing_low_20"] or 0) or None,
            cfg=cfg, pattern=pattern, breakout_level=breakout, pattern_height=height,
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Initial stop", f"${plan.initial_stop:.2f}", f"-{plan.risk_pct:.1f}%")
        k2.metric("Shares", f"{plan.shares:,}")
        k3.metric("Position value", f"${plan.position_value:,.0f}")
        k4.metric("Capital at risk", f"${plan.capital_at_risk:,.0f}")
        st.caption(f"Stop placed {plan.stop_basis}. Risk per share ${plan.risk_per_share:.2f}.")

        if plan.target:
            st.success(f"Measured-move target **${plan.target:.2f}**  ·  reward/risk **{plan.reward_risk:.2f}R**")
            st.caption(plan.target_basis)
        else:
            st.info("No pattern target - the profit ladder below manages the exit.")

        st.subheader("Profit ladder")
        st.dataframe(pd.DataFrame(plan.ladder), hide_index=True, use_container_width=True)
        st.caption(
            f"Runner management: trail {cfg['exits']['trail_atr_multiple']:g} x ATR below the highest close "
            f"since entry (currently ≈ ${exit_engine.trailing_stop(entry, atr_val, cfg['exits']['trail_atr_multiple']):.2f})."
        )

# ------------------------------- Sectors ----------------------------------- #
with tab_sectors:
    table = scan_state.get("sector_table") or {}
    if not table:
        st.info("Sector filter disabled or unavailable.")
    else:
        sdf = pd.DataFrame(table.values()).sort_values("rs_pct", ascending=False, na_position="last")
        st.dataframe(sdf, hide_index=True, use_container_width=True,
                     column_config={
                         "etf": "Sector ETF",
                         "rsi": st.column_config.NumberColumn("RSI(14)", format="%.1f"),
                         "rs_pct": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
                         "ok": st.column_config.CheckboxColumn("Strong"),
                     })
        st.caption("Top-down: trade leaders inside leading sectors.")
