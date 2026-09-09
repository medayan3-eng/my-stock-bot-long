"""Murphy Swing Screener - one button, no settings.

Everything (market regime, sector strength, the ten stock rules, pattern
recognition, targets, stops and position sizing) runs automatically.
Thresholds live in config.yaml; the interface exposes nothing to tweak.

    streamlit run app.py
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
    VIX,
    download_prices,
    download_prices_chunked,
    get_fundamentals,
    load_universe_csv,
)

st.set_page_config(page_title="Murphy Swing Screener", page_icon="📈", layout="wide")

BASE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE, "config.yaml")
UNIVERSE_PATH = os.path.join(BASE, "universe.csv")

cfg = load_config(CFG_PATH)
# The universe is pre-defined, so ownership data is not fetched per ticker.
cfg["ownership"]["on_missing"] = "pass"
cfg["earnings"]["on_missing"] = "warn"


# --------------------------------------------------------------------------- #
# Cached loaders
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def load_universe() -> List[str]:
    tickers, _ = load_universe_csv(UNIVERSE_PATH)
    return tickers


@st.cache_data(ttl=60 * 60 * 3, show_spinner=False)
def fetch_context(period: str) -> Dict[str, pd.DataFrame]:
    """Benchmark, VIX and all eleven sector ETFs - one small request."""
    extras = [cfg["regime"]["benchmark"], VIX] + market_mod.sector_universe()
    return download_prices(extras, period=period)


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("📈 Murphy Swing Screener")
st.caption(
    "End-of-day scan for multi-week to multi-month swing trades. Market regime, "
    "sector strength, ten technical rules, chart patterns and price targets all "
    "run automatically - press the button and read the results."
)

tickers = load_universe()
c1, c2 = st.columns([1, 3])
run = c1.button("▶️ Run scan", type="primary", use_container_width=True)
c2.caption(
    f"{len(tickers):,} tickers loaded (S&P 500 + Russell 2000). "
    "First run of the day takes several minutes."
)


# --------------------------------------------------------------------------- #
# The scan
# --------------------------------------------------------------------------- #
def run_scan() -> dict:
    bar = st.progress(0.0, text="Loading market context...")

    context = fetch_context(cfg["scan"]["history_period"])
    bench_df = context.get(cfg["regime"]["benchmark"])
    sector_prices = {e: context[e] for e in market_mod.sector_universe() if e in context}
    sector_table = market_mod.build_sector_table_from(cfg, bench_df, sector_prices)
    regime = market_mod.evaluate_regime(cfg, context)

    def on_download(done, total, label):
        bar.progress(min(0.05 + 0.75 * done / max(total, 1), 0.80), text=label)

    prices = download_prices_chunked(
        tickers, period=cfg["scan"]["history_period"], progress=on_download
    )

    def on_analyse(done, total, label):
        bar.progress(min(0.80 + 0.19 * done / max(total, 1), 0.99), text=label)

    bar.progress(0.82, text="Analysing charts and detecting patterns...")
    results = screener_mod.scan(
        prices, cfg, sector_table, {}, tickers,
        sector_prices=sector_prices, progress=on_analyse,
    )

    valid = [t for t in tickers if t in prices and len(prices[t]) > 210]
    breadth = None
    if valid:
        above = sum(
            1 for t in valid
            if pd.notna(ind.last_valid(ind.sma(prices[t]["Close"], 200)))
            and float(prices[t]["Close"].iloc[-1]) > ind.last_valid(ind.sma(prices[t]["Close"], 200))
        )
        breadth = above / len(valid) * 100.0
    regime = market_mod.apply_breadth(regime, cfg, breadth)

    # Earnings dates are one slow request per ticker, so they are fetched only
    # for the shortlist - the only names where the answer changes a decision.
    if not results.empty and cfg["earnings"].get("enabled", True):
        short = results[results.get("rules_passed", 0) >= 8]["ticker"].head(80).tolist()
        if short:
            bar.progress(0.99, text=f"Checking earnings dates for {len(short)} finalists...")
            results = add_earnings(results, short)

    bar.progress(1.0, text="Done.")
    bar.empty()
    return {"prices": prices, "regime": regime, "results": results,
            "sector_table": sector_table, "loaded": len(prices)}


def add_earnings(results: pd.DataFrame, shortlist: List[str]) -> pd.DataFrame:
    """Attach the next earnings date to the finalists and enforce the blackout."""
    today = dt.date.today()
    blackout = int(cfg["earnings"]["blackout_days"])
    results = results.copy()
    for t in shortlist:
        try:
            fnd = get_fundamentals(t, need_info=False, need_earnings=True)
        except Exception:
            continue
        nxt = fnd.get("next_earnings")
        if not nxt:
            continue
        days = (nxt - today).days
        mask = results["ticker"] == t
        results.loc[mask, "next_earnings"] = nxt.isoformat()
        results.loc[mask, "days_to_earnings"] = days
        if days <= blackout:
            results.loc[mask, "chk_earnings_clear"] = False
            results.loc[mask, "passes_all"] = False
            results.loc[mask, "warnings"] = f"Earnings in {days} day(s) - do not enter."
    return results


if run:
    st.session_state["scan"] = run_scan()
    st.session_state["scan_time"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

state = st.session_state.get("scan")
if not state:
    st.info("Press **Run scan**. Best done after the US close, when the last daily bar is final.")
    st.stop()

regime = state["regime"]
results: pd.DataFrame = state["results"]
prices = state["prices"]

st.caption(f"Last scan: {st.session_state.get('scan_time', '')} · {state['loaded']:,} tickers with usable data")

m1, m2, m3, m4 = st.columns(4)
m1.metric(
    f"{regime.benchmark} vs SMA{cfg['regime']['benchmark_ma']}",
    f"{regime.benchmark_price:,.2f}",
    f"{(regime.benchmark_price / regime.benchmark_sma - 1) * 100:+.1f}%" if regime.benchmark_sma else "n/a",
)
m2.metric("VIX", f"{regime.vix:.1f}" if regime.vix else "n/a",
          "calm" if regime.vix_ok else "panic",
          delta_color="normal" if regime.vix_ok else "inverse")
m3.metric("Breadth above SMA200", f"{regime.breadth_pct:.0f}%" if regime.breadth_pct is not None else "n/a")
m4.metric("Full-pass candidates", int(results["passes_all"].sum()) if not results.empty else 0)

if regime.ok:
    st.success("**RISK-ON — long entries allowed**")
else:
    st.error("**RISK-OFF — stand aside.** " + " ".join(regime.notes))
    st.caption("Candidates below are for study only while the regime switch is off.")

tab_res, tab_chart, tab_plan, tab_sec = st.tabs(
    ["🔎 Candidates", "📊 Chart & levels", "🎯 Trade plan", "🏭 Sectors"]
)

# ------------------------------- Candidates -------------------------------- #
with tab_res:
    if results.empty:
        st.warning("No results.")
    else:
        winners = results[results["passes_all"]] if "passes_all" in results else results
        near = results[(~results.get("passes_all", False)) & (results.get("rules_passed", 0) >= 8)]

        st.subheader(f"Passed every rule — {len(winners)}")
        cols = [c for c in [
            "ticker", "score", "price", "pattern", "pattern_confidence",
            "pattern_breakout", "pattern_target", "pct_to_target",
            "support", "resistance", "dist_sma50_pct", "rs_excess_pct",
            "vol_ratio_max3", "squeeze_ratio", "sector_etf", "days_to_earnings",
        ] if c in results.columns]

        conf = {
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
            "pattern_confidence": st.column_config.NumberColumn("Conf.", format="%.2f"),
            "pct_to_target": st.column_config.NumberColumn("Upside to target", format="%.1f%%"),
            "dist_sma50_pct": st.column_config.NumberColumn("% vs 50MA", format="%.2f%%"),
            "rs_excess_pct": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
            "vol_ratio_max3": st.column_config.NumberColumn("Vol x avg", format="%.2f"),
            "squeeze_ratio": st.column_config.NumberColumn("ATR10/50", format="%.2f"),
        }
        if winners.empty:
            st.info("Nothing cleared all ten rules today. The near-misses below are worth a look.")
        else:
            st.dataframe(winners[cols], use_container_width=True, hide_index=True, column_config=conf)

        st.subheader(f"Near misses (8+ of 10 rules) — {len(near)}")
        if not near.empty:
            show = near[cols + ["failed_rules"]] if "failed_rules" in near else near[cols]
            st.dataframe(show.head(60), use_container_width=True, hide_index=True, column_config=conf)

        st.download_button(
            "⬇️ Download full results (CSV)",
            results.to_csv(index=False).encode("utf-8"),
            file_name=f"scan_{dt.date.today().isoformat()}.csv",
            mime="text/csv",
        )

# ------------------------------- Chart ------------------------------------- #
def _ranked(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    ok = df[df["status"] == "ok"] if "status" in df else df
    return ok.sort_values(["passes_all", "score"], ascending=[False, False])["ticker"].tolist()


with tab_chart:
    order = _ranked(results)
    if not order:
        st.info("Nothing to display.")
    else:
        sel = st.selectbox("Ticker", order, key="chart_ticker")
        row = results[results["ticker"] == sel].iloc[0]
        df = prices.get(sel)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Price", f"${row['price']:.2f}")
        k2.metric("Pattern", row.get("pattern") or "None",
                  f"conf {row.get('pattern_confidence', 0):.2f}")
        k3.metric("Target", f"${row['pattern_target']:.2f}" if row.get("pattern_target") else "n/a",
                  f"{row['pct_to_target']:+.1f}%" if row.get("pct_to_target") else None)
        k4.metric("Score", f"{row['score']:.0f}/100")

        if row.get("pattern_note"):
            st.caption(row["pattern_note"])

        if df is not None and len(df) > 60:
            try:
                import plotly.graph_objects as go

                plot = df.iloc[-220:]
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=plot.index, open=plot["Open"], high=plot["High"],
                    low=plot["Low"], close=plot["Close"], name=sel))
                fig.add_trace(go.Scatter(x=plot.index, y=ind.sma(df["Close"], 50).iloc[-220:],
                                         name="SMA 50", line=dict(width=1.4)))
                fig.add_trace(go.Scatter(x=plot.index, y=ind.sma(df["Close"], 200).iloc[-220:],
                                         name="SMA 200", line=dict(width=1.4)))
                for label, key, dash in (
                    ("Resistance", "resistance", "dot"),
                    ("Support", "support", "dot"),
                    ("Breakout", "pattern_breakout", "dash"),
                    ("Target", "pattern_target", "dashdot"),
                ):
                    val = row.get(key)
                    if val and pd.notna(val):
                        fig.add_hline(y=float(val), line_dash=dash, opacity=0.6,
                                      annotation_text=f"{label} {float(val):.2f}",
                                      annotation_position="right")
                fig.update_layout(height=520, xaxis_rangeslider_visible=False,
                                  margin=dict(l=10, r=10, t=30, b=10),
                                  legend=dict(orientation="h"))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.line_chart(df["Close"].iloc[-220:])

        st.subheader("Rule breakdown")
        st.dataframe(
            pd.DataFrame([
                {"Rule": screener_mod.RULE_LABELS[r], "Pass": bool(row.get(f"chk_{r}", False))}
                for r in screener_mod.RULES if f"chk_{r}" in row
            ]),
            hide_index=True, use_container_width=True,
        )
        if row.get("warnings"):
            st.warning(row["warnings"])
        with st.expander("All metrics"):
            st.json({k: (None if pd.isna(v) else v) for k, v in row.items() if not k.startswith("chk_")})

# ------------------------------- Trade plan -------------------------------- #
with tab_plan:
    order = _ranked(results)
    if not order:
        st.info("Run a scan first.")
    else:
        sel = st.selectbox("Ticker", order, key="plan_ticker")
        row = results[results["ticker"] == sel].iloc[0].to_dict()
        plan = exit_engine.auto_plan(row, cfg)

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Entry (last close)", f"${plan.entry:.2f}")
        p2.metric("Initial stop", f"${plan.initial_stop:.2f}", f"-{plan.risk_pct:.1f}%")
        p3.metric("Shares", f"{plan.shares:,}")
        p4.metric("Capital at risk", f"${plan.capital_at_risk:,.0f}")
        st.caption(
            f"Stop placed {plan.stop_basis}. Risk ${plan.risk_per_share:.2f}/share · "
            f"position ${plan.position_value:,.0f} · "
            f"{cfg['risk']['risk_per_trade_pct']:g}% of a ${cfg['risk']['account_size']:,.0f} account."
        )

        if plan.target:
            st.success(
                f"**{row.get('pattern')}** → target **${plan.target:.2f}** "
                f"({row.get('pct_to_target', 0):+.1f}%) · reward/risk **{plan.reward_risk:.2f}R**"
            )
            st.caption(plan.target_basis)
        else:
            st.info("No measured-move target — the ladder below manages the exit.")

        st.subheader("Profit ladder")
        st.dataframe(pd.DataFrame(plan.ladder), hide_index=True, use_container_width=True)
        st.caption(
            f"Runner: trail {cfg['exits']['trail_atr_multiple']:g} × ATR below the highest close "
            f"since entry (≈ ${exit_engine.trailing_stop(plan.entry, plan.atr, cfg['exits']['trail_atr_multiple']):.2f} today)."
        )

# ------------------------------- Sectors ----------------------------------- #
with tab_sec:
    table = state.get("sector_table") or {}
    if not table:
        st.info("Sector data unavailable.")
    else:
        sdf = pd.DataFrame(table.values()).sort_values("rs_pct", ascending=False, na_position="last")
        st.dataframe(sdf, hide_index=True, use_container_width=True, column_config={
            "etf": "Sector ETF",
            "rsi": st.column_config.NumberColumn("RSI(14)", format="%.1f"),
            "rs_pct": st.column_config.NumberColumn("RS vs SPY", format="%.2f%%"),
            "ok": st.column_config.CheckboxColumn("Strong"),
        })
        st.caption("Top-down: leaders inside leading sectors.")
