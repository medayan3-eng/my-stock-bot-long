"""
app_il.py — TASE Israel Stock Scanner (Murphy Method)
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import calendar
import warnings
warnings.filterwarnings('ignore')

from screener_il import calculate_indicators_il, debug_ticker_il
from backtester_il import run_backtest_il
from news_fetcher_il import fetch_news_il, fetch_market_news_il
from stock_universe_il import STOCK_UNIVERSE_IL, SECTOR_MAP, get_by_sector

st.set_page_config(
    page_title="📊 TASE Stock Scanner — Murphy",
    page_icon="🇮🇱",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
  html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; direction: ltr; }
  .stApp { background: #070b14; color: #dde4f0; }
  .main-header { font-family:'IBM Plex Mono',monospace; font-size:2rem; font-weight:700; color:#00e5c0; letter-spacing:-1px; margin-bottom:0.1rem; }
  .sub-header  { font-size:0.78rem; color:#3d4f6b; letter-spacing:2px; text-transform:uppercase; font-family:'IBM Plex Mono',monospace; margin-bottom:1rem; }
  .market-bar  { background:#0b1120; border:1px solid #172035; border-radius:12px; padding:0.9rem 1.4rem; display:flex; gap:1.8rem; align-items:center; flex-wrap:wrap; margin-bottom:1.2rem; }
  .mkt-item    { display:flex; flex-direction:column; min-width:90px; }
  .mkt-label   { font-size:0.66rem; color:#3d4f6b; text-transform:uppercase; letter-spacing:1px; font-family:'IBM Plex Mono',monospace; }
  .mkt-val     { font-family:'IBM Plex Mono',monospace; font-size:1.05rem; font-weight:700; }
  .mkt-chg     { font-family:'IBM Plex Mono',monospace; font-size:0.75rem; }
  .fear-box        { border-radius:8px; padding:0.5rem 1rem; display:flex; flex-direction:column; align-items:center; min-width:140px; }
  .fear-box-green  { background:rgba(0,229,192,0.10);  border:2px solid #00e5c0; }
  .fear-box-yellow { background:rgba(251,191,36,0.10); border:2px solid #fbbf24; }
  .fear-box-red    { background:rgba(248,113,113,0.12); border:2px solid #f87171; }
  .fear-val-green  { font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#00e5c0; }
  .fear-val-yellow { font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#fbbf24; }
  .fear-val-red    { font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#f87171; }
  .fear-label      { font-size:0.65rem; color:#8a9ab5; text-transform:uppercase; letter-spacing:1px; font-family:'IBM Plex Mono',monospace; }
  .fear-msg        { font-size:0.70rem; text-align:center; margin-top:0.2rem; }
  .metric-card { background:#0f1927; border:1px solid #172035; border-radius:8px; padding:0.9rem; margin:0.2rem 0; border-left:3px solid #00e5c0; }
  .stock-card  { background:#0f1927; border:1px solid #172035; border-radius:12px; padding:1.4rem; margin:0.5rem 0; }
  .stock-card:hover { border-color:#00e5c0; box-shadow:0 0 20px rgba(0,229,192,0.08); }
  .ticker-symbol { font-family:'IBM Plex Mono',monospace; font-size:1.3rem; font-weight:700; color:#00e5c0; }
  .price-display { font-family:'IBM Plex Mono',monospace; font-size:1.05rem; color:#dde4f0; }
  .company-name  { color:#5a7099; font-size:0.82rem; margin-left:0.6rem; }
  .scan-stat  { font-family:'IBM Plex Mono',monospace; font-size:1.7rem; font-weight:700; color:#00e5c0; }
  .scan-label { font-size:0.70rem; color:#3d4f6b; text-transform:uppercase; letter-spacing:1px; font-family:'IBM Plex Mono',monospace; }
  .badge        { display:inline-block; padding:0.17rem 0.5rem; border-radius:4px; font-size:0.70rem; font-family:'IBM Plex Mono',monospace; font-weight:700; margin:0.1rem; }
  .badge-green  { background:rgba(0,229,192,0.12);  color:#00e5c0; border:1px solid rgba(0,229,192,0.3); }
  .badge-yellow { background:rgba(251,191,36,0.12); color:#fbbf24; border:1px solid rgba(251,191,36,0.3); }
  .badge-red    { background:rgba(248,113,113,0.12); color:#f87171; border:1px solid rgba(248,113,113,0.3); }
  .badge-blue   { background:rgba(96,165,250,0.12); color:#60a5fa; border:1px solid rgba(96,165,250,0.3); }
  div[data-testid="stSidebar"] { background:#0b1120; border-right:1px solid #172035; }
  .stButton > button { background:#00e5c0; color:#070b14; font-family:'IBM Plex Mono',monospace; font-weight:700; border:none; border-radius:8px; padding:0.6rem 1.5rem; width:100%; }
  .stButton > button:hover { background:#00c4a4; }
  .news-item  { background:#0f1927; border:1px solid #172035; border-radius:8px; padding:0.85rem; margin:0.3rem 0; border-left:3px solid #60a5fa; }
  .news-title { color:#60a5fa; font-size:0.87rem; font-weight:600; }
  .news-meta  { color:#3d4f6b; font-size:0.70rem; font-family:'IBM Plex Mono',monospace; margin-top:0.2rem; }
  hr { border-color:#172035; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  ISRAEL CLOCK — DST-aware (UTC+3 summer, UTC+2 winter)
#  DST: last Sunday of March → last Sunday of October
# ══════════════════════════════════════════════
def _israel_now() -> datetime:
    utc = datetime.utcnow()
    y   = utc.year

    def last_sunday(year, month):
        last_day = calendar.monthrange(year, month)[1]
        d = datetime(year, month, last_day)
        offset = (d.weekday() + 1) % 7   # days past last Sunday
        return d - timedelta(days=offset)

    dst_on  = last_sunday(y, 3).replace(hour=2)   # last Sun March 02:00
    dst_off = last_sunday(y, 10).replace(hour=2)  # last Sun October 02:00
    offset  = 3 if dst_on <= utc < dst_off else 2
    return utc + timedelta(hours=offset)


def _is_tase_open() -> bool:
    """TASE: Sun–Thu 09:00–17:30, Fri 09:00–13:45, Sat closed."""
    n  = _israel_now()
    wd = n.weekday()   # Mon=0 … Sun=6
    hm = (n.hour, n.minute)
    if wd == 5:  return False                            # Saturday
    if wd == 4:  return (9,0) <= hm <= (13,45)          # Friday
    return (9,0) <= hm <= (17,30)                        # Sun–Thu


# ══════════════════════════════════════════════
#  MARKET DATA
# ══════════════════════════════════════════════
@st.cache_data(ttl=180)
def fetch_tase_market_data():
    symbols = {"^TA35.TA":"TA-35", "^TA125.TA":"TA-125", "^VIX":"VIX (US)", "USDILS=X":"USD/ILS"}
    result = {}
    for sym, label in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="2d", interval="1d")
            if len(hist) >= 2:
                prev = float(hist['Close'].iloc[-2]); curr = float(hist['Close'].iloc[-1])
                chg  = (curr - prev) / prev * 100
            elif len(hist) == 1:
                curr = float(hist['Close'].iloc[-1]); chg = 0
            else:
                curr = chg = 0
            result[label] = {"value": curr, "change_pct": chg}
        except Exception:
            result[label] = {"value": 0, "change_pct": 0}
    return result


def render_market_bar():
    data = fetch_tase_market_data()
    vix  = data.get("VIX (US)", {}).get("value", 0)
    if   vix <= 0:  vix_cls="green";  vix_msg="No data"
    elif vix < 20:  vix_cls="green";  vix_msg="✅ Low fear — safe to trade"
    elif vix < 28:  vix_cls="yellow"; vix_msg="⚠️ Caution — strong stocks only"
    else:           vix_cls="red";    vix_msg="🚫 High fear — DO NOT enter"

    def tile(label, d):
        v=d.get("value",0); chg=d.get("change_pct",0)
        col="#00e5c0" if chg>=0 else "#f87171"
        arrow="▲" if chg>=0 else "▼"
        fmt=f"{v:,.2f}" if v<1000 else f"{v:,.0f}"
        return (f'<div class="mkt-item"><span class="mkt-label">{label}</span>'
                f'<span class="mkt-val">{fmt}</span>'
                f'<span class="mkt-chg" style="color:{col}">{arrow} {abs(chg):.2f}%</span></div>')

    tiles   = "".join(tile(k,v) for k,v in data.items() if k!="VIX (US)")
    vix_str = f"{vix:.2f}" if vix else "—"
    msg_col = {"green":"#00e5c0","yellow":"#fbbf24","red":"#f87171"}[vix_cls]
    il_now  = _israel_now()
    il_time = il_now.strftime('%H:%M:%S')
    mopen   = _is_tase_open()

    st.markdown(f"""
    <div class="market-bar">
      <div class="fear-box fear-box-{vix_cls}">
        <span class="fear-label">😨 VIX Fear Index</span>
        <span class="fear-val-{vix_cls}">{vix_str}</span>
        <span class="fear-msg" style="color:{msg_col};">{vix_msg}</span>
      </div>
      <div style="width:1px;background:#172035;align-self:stretch;"></div>
      {tiles}
      <div style="margin-left:auto;text-align:right;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:#3d4f6b;">
          🕐 {il_time} 🇮🇱 IL
        </div>
        <div style="font-size:0.72rem;margin-top:0.2rem;color:{'#00e5c0' if mopen else '#f87171'};">
          {'🟢 TASE Open' if mopen else '🔴 TASE Closed'}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    return vix


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Parameters")
        st.markdown("---")
        min_price  = st.slider("Min Price (₪)", 2, 200, 10)
        min_volume = st.number_input("Min Avg Volume (K shares/day)", 10, 5000, 100, 10)
        min_beta   = st.slider("Min Beta", 0.0, 3.0, 0.5, 0.1)
        st.markdown("---")
        st.markdown("**RSI**")
        rsi_range  = st.slider("RSI Range", 10, 90, (10, 55))
        rsi_min, rsi_max = rsi_range[0], rsi_range[1]
        rsi_period = st.number_input("RSI Period", 5, 21, 14)
        st.caption(f"Stocks with RSI between {rsi_min} – {rsi_max}")
        st.markdown("---")
        st.markdown("**Trend Filters**")
        req_ma      = st.checkbox("Above Long MA (MA200/MA120)", value=True)
        req50       = st.checkbox("Above MA50", value=True)
        req20       = st.checkbox("Above MA20 (optional)", value=False)
        req_uptrend = st.checkbox("📈 52-Week Uptrend (Murphy)", value=True,
                                  help="Price > 1yr ago + MA50 > MA200 + Price > MA200")
        st.markdown("---")
        st.markdown("**Bollinger Bands**")
        bb_period = st.number_input("BB Period", 10, 30, 20)
        bb_std    = st.slider("BB Std Dev", 1.5, 3.0, 2.0, 0.1)
        st.markdown("---")
        st.markdown("**Sector Filter**")
        all_sectors     = ["All"] + list(SECTOR_MAP.keys())
        selected_sector = st.selectbox("Sector", all_sectors)
        st.markdown("---")
        fresh_only = st.checkbox("🟢 Fresh Signals (≤5 days)", value=False)
        max_stocks = st.slider("Max stocks to scan", 20, len(STOCK_UNIVERSE_IL), len(STOCK_UNIVERSE_IL))
        st.markdown("---")
        run_scan = st.button("🔍 STEP 1 — RUN SCAN", use_container_width=True)
        st.caption("Live data from yfinance")
        st.markdown("")
        run_bt   = st.button("📊 STEP 2 — BACKTEST", use_container_width=True)
        st.caption("Tests Step 1 stocks only — 1 year history")
        st.markdown("")
        debug_input = st.text_input("🔧 Debug ticker (e.g. TEVA.TA)").upper().strip()
        run_debug   = st.button("🔧 Debug single stock", use_container_width=True)

        return dict(
            min_price=min_price, min_volume=min_volume*1_000, min_beta=min_beta,
            rsi_min=rsi_min, rsi_max=rsi_max, rsi_period=int(rsi_period),
            require_above_ma=req_ma, require_above_50=req50, require_above_20=req20,
            require_uptrend_52w=req_uptrend, bb_period=int(bb_period), bb_std=bb_std,
            show_fresh_only=fresh_only, selected_sector=selected_sector,
            max_stocks=max_stocks, run_scan=run_scan, run_backtest=run_bt,
            run_debug=run_debug, debug_ticker=debug_input,
        )


# ══════════════════════════════════════════════
#  STOCK CARD  — rsi_period passed explicitly, NO NameError
# ══════════════════════════════════════════════
def render_stock_card_il(stock, bt_summary=None, rsi_period=14):
    score        = stock.get('score', 0)
    rsi          = stock.get('rsi', 0)
    bb_pct       = stock.get('bb_pct', 0.5)
    trend_4w     = stock.get('trend_4w', 0)
    macd_hist    = stock.get('macd_hist', 0)
    macd_bullish = stock.get('macd_bullish', False)
    fresh        = stock.get('signal_fresh', False)
    sig_date     = stock.get('signal_date', '')
    price        = stock.get('price', 0)
    rs           = stock.get('rs', 1.0)
    vol_ratio    = stock.get('volume_ratio', 1.0)
    vol_spike    = stock.get('volume_spike', False)
    support      = stock.get('support')
    resistance   = stock.get('resistance')
    near_sup     = stock.get('near_support', False)
    patterns     = stock.get('patterns', [])
    uptrend_52w  = stock.get('uptrend_52w', False)
    rr_ratio     = stock.get('rr_ratio', 0)
    rr_valid     = stock.get('rr_valid', False)
    rr_stop      = stock.get('rr_stop')
    rr_target    = stock.get('rr_target')
    summary      = stock.get('summary', '')
    ticker       = stock.get('ticker', '')
    ticker_s     = stock.get('ticker_short', ticker.replace('.TA',''))
    name         = stock.get('name', ticker_s)
    market_cap   = stock.get('market_cap_m')
    mc_text      = f"MCap ₪{market_cap:,.0f}M" if market_cap else ""

    sig_col = "#00e5c0" if score>=7 else "#fbbf24" if score>=5 else "#f87171"
    tv_url  = f"https://www.tradingview.com/chart/?symbol=TASE%3A{ticker_s}&interval=D"

    badges = []
    if stock.get('above_ma'):   badges.append('<span class="badge badge-green">MA ✓</span>')
    if stock.get('above_50'):   badges.append('<span class="badge badge-green">MA50 ✓</span>')
    if uptrend_52w:             badges.append('<span class="badge badge-green">📈 52W UPTREND</span>')
    if rsi < 30:                badges.append('<span class="badge badge-red">RSI EXTREME</span>')
    elif rsi < 40:              badges.append('<span class="badge badge-yellow">RSI OVERSOLD</span>')
    if bb_pct < 0.2:            badges.append('<span class="badge badge-green">BB LOWER ✓</span>')
    if trend_4w > 0:            badges.append('<span class="badge badge-green">4W UPTREND</span>')
    if macd_bullish:            badges.append('<span class="badge badge-green">MACD ✓</span>')
    else:                       badges.append('<span class="badge badge-red">MACD ✗</span>')
    if vol_spike:               badges.append('<span class="badge badge-yellow">⚡ VOL SPIKE</span>')
    if near_sup:                badges.append('<span class="badge badge-green">🎯 NEAR SUPPORT</span>')
    for p in patterns[:1]:      badges.append(f'<span class="badge badge-blue">📐 {p}</span>')
    if rr_valid:                badges.append(f'<span class="badge badge-green">R/R 1:{rr_ratio}</span>')
    badges.append('<span class="badge badge-green">🟢 FRESH</span>' if fresh
                  else '<span class="badge badge-yellow">⚠️ LATE</span>')

    bt_html = ""
    if bt_summary:
        wr=bt_summary.get('win_rate',0); tot=bt_summary.get('total_trades',0); avg=bt_summary.get('avg_return',0)
        wc="#00e5c0" if wr>=60 else "#fbbf24" if wr>=45 else "#f87171"
        bt_html = f"""<div style="margin-top:0.5rem;padding:0.5rem 0.9rem;background:#0b1120;border-radius:6px;border:1px solid #172035;display:flex;gap:2rem;">
          <div><div class="scan-label">📊 Win Rate</div><div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;font-weight:700;color:{wc};">{wr:.0f}%</div></div>
          <div><div class="scan-label">Trades</div><div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;color:#dde4f0;">{tot}</div></div>
          <div><div class="scan-label">Avg Return</div><div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;color:{'#00e5c0' if avg>=0 else '#f87171'};">{avg:+.1f}%</div></div>
        </div>"""

    sr_parts = []
    if support:    sr_parts.append(f'<span style="color:#00e5c0;">🟩 Support: ₪{support}</span>')
    if resistance: sr_parts.append(f'<span style="color:#f87171;">🟥 Resistance: ₪{resistance}</span>')
    if rr_valid:   sr_parts.append(f'<span style="color:#fbbf24;">Stop: ₪{rr_stop} → Target: ₪{rr_target} (1:{rr_ratio})</span>')
    sr_html = (f'<div style="margin-top:0.4rem;font-size:0.76rem;font-family:\'IBM Plex Mono\',monospace;">'
               f'{" &nbsp;|&nbsp; ".join(sr_parts)}</div>') if sr_parts else ""

    summary_html = (f'<div style="margin-top:0.5rem;padding:0.5rem 0.8rem;background:rgba(0,229,192,0.05);'
                    f'border-left:3px solid #00e5c0;border-radius:0 6px 6px 0;font-size:0.8rem;color:#8a9ab5;line-height:1.6;">'
                    f'💡 {summary}</div>') if summary else ""

    st.markdown(f"""
    <div class="stock-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
          <span class="ticker-symbol">{ticker_s}</span>
          <span class="company-name">{name}</span>
          {'<span style="font-size:0.70rem;color:#3d4f6b;font-family:\'IBM Plex Mono\',monospace;"> '+mc_text+'</span>' if mc_text else ''}
        </div>
        <div style="text-align:right;">
          <div class="price-display">₪{price:,.2f}</div>
          <div style="font-weight:700;color:{sig_col};font-size:0.85rem;font-family:'IBM Plex Mono',monospace;">Score: {score}/10</div>
        </div>
      </div>
      <div style="margin:0.5rem 0;">{''.join(badges)}</div>
      <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:0.4rem;margin-top:0.6rem;">
        <div><div class="scan-label">RSI({rsi_period})</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
                  color:{'#f87171' if rsi<30 else '#fbbf24' if rsi<40 else '#dde4f0'};">{rsi:.1f}</div></div>
        <div><div class="scan-label">MACD Hist</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
                  color:{'#00e5c0' if macd_bullish else '#f87171'};">{macd_hist:+.3f}</div></div>
        <div><div class="scan-label">BB%B</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
                  color:{'#00e5c0' if bb_pct<0.2 else '#dde4f0'};">{bb_pct:.2f}</div></div>
        <div><div class="scan-label">RS vs TA125</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
                  color:{'#00e5c0' if rs>1 else '#f87171'};">{rs:+.2f}</div></div>
        <div><div class="scan-label">Vol Ratio</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
                  color:{'#fbbf24' if vol_spike else '#dde4f0'};"> {'⚡' if vol_spike else ''}{vol_ratio:.1f}x</div></div>
        <div><div class="scan-label">4W Trend</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
                  color:{'#00e5c0' if trend_4w>0 else '#f87171'};"> {'▲' if trend_4w>0 else '▼'} {abs(trend_4w):.1f}%</div></div>
      </div>
      {sr_html}
      {summary_html}
      <div style="margin-top:0.5rem;font-size:0.68rem;font-family:'IBM Plex Mono',monospace;color:#3d4f6b;">
        📅 {sig_date} &nbsp; {'✅ Buy now' if fresh else '⚠️ Verify before entry'}
        &nbsp;&nbsp;<a href="{tv_url}" target="_blank" style="color:#60a5fa;text-decoration:none;">📊 TradingView →</a>
      </div>
      {bt_html}
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  CHART
# ══════════════════════════════════════════════
def render_chart_il(ticker, params):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 40:
            st.warning(f"Not enough data for {ticker}"); return
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df['Close'].squeeze()
        df['MA20']  = close.rolling(20).mean()
        df['MA50']  = close.rolling(50).mean()
        df['MA120'] = close.rolling(120).mean()
        df['BBm']   = close.rolling(params['bb_period']).mean()
        df['BBs']   = close.rolling(params['bb_period']).std()
        df['BBu']   = df['BBm'] + params['bb_std'] * df['BBs']
        df['BBl']   = df['BBm'] - params['bb_std'] * df['BBs']
        delta = close.diff()
        g = delta.clip(lower=0).rolling(params['rsi_period']).mean()
        l = (-delta.clip(upper=0)).rolling(params['rsi_period']).mean()
        df['RSI'] = 100 - 100 / (1 + g / l)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.70,0.30], vertical_spacing=0.04)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name=ticker,
            increasing_line_color='#00e5c0', decreasing_line_color='#f87171'), row=1, col=1)
        for ma,col,w in [('MA20','#fbbf24',1),('MA50','#60a5fa',1.5),('MA120','#a78bfa',1.5)]:
            if ma in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma,
                    line=dict(color=col, width=w), opacity=0.85), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBu'], name='BB Upper',
            line=dict(color='#3d4f6b', width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBl'], name='BB Lower',
            line=dict(color='#3d4f6b', width=1, dash='dot'),
            fill='tonexty', fillcolor='rgba(61,79,107,0.07)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI',
            line=dict(color='#fbbf24', width=1.5)), row=2, col=1)
        fig.add_hline(y=45, line_dash="dot", line_color="#00e5c0", opacity=0.5, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#f87171", opacity=0.5, row=2, col=1)
        ts = ticker.replace('.TA','')
        fig.update_layout(plot_bgcolor='#0f1927', paper_bgcolor='#070b14',
            font=dict(color='#dde4f0', family='IBM Plex Mono'),
            xaxis_rangeslider_visible=False, height=520,
            margin=dict(l=10,r=10,t=35,b=10),
            title=dict(text=f"{ts} — 6-Month Chart", font=dict(color='#00e5c0', size=14)),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=9)))
        fig.update_xaxes(gridcolor='#172035'); fig.update_yaxes(gridcolor='#172035')
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart error: {e}")


# ══════════════════════════════════════════════
#  BACKTEST RESULTS
# ══════════════════════════════════════════════
def render_backtest_panel_il(bt_data):
    st.markdown("### 📊 Backtest Results — 12 months, scanned stocks only")
    overall=bt_data.get('overall',{}); per_stock=bt_data.get('per_stock',{})
    total=overall.get('total_trades',0); wins=overall.get('wins',0)
    loss=overall.get('losses',0); wr=overall.get('win_rate',0)
    avg_r=overall.get('avg_return',0); best=overall.get('best_trade',0); worst=overall.get('worst_trade',0)
    wc="#00e5c0" if wr>=60 else "#fbbf24" if wr>=45 else "#f87171"
    cols=st.columns(6)
    for col,lbl,val,clr in zip(cols,
        ["Total Trades","✅ Wins","❌ Losses","Win Rate","Avg Return","Best / Worst"],
        [str(total),str(wins),str(loss),f"{wr:.1f}%",f"{avg_r:+.2f}%",f"{best:+.1f}% / {worst:+.1f}%"],
        ["#dde4f0","#00e5c0","#f87171",wc,"#00e5c0" if avg_r>=0 else "#f87171","#dde4f0"]):
        col.markdown(f'<div class="metric-card"><div class="scan-label">{lbl}</div>'
                     f'<div class="scan-stat" style="color:{clr};font-size:1.25rem;">{val}</div></div>',
                     unsafe_allow_html=True)
    if per_stock:
        st.markdown("#### Per-Stock Statistics")
        rows=[{"Ticker":t.replace('.TA',''),"Trades":s.get('total_trades',0),
               "Wins":s.get('wins',0),"Losses":s.get('losses',0),
               "Win Rate":f"{s.get('win_rate',0):.0f}%","Avg Return":f"{s.get('avg_return',0):+.2f}%",
               "Best Trade":f"{s.get('best_trade',0):+.1f}%","Worst Trade":f"{s.get('worst_trade',0):+.1f}%",
               "Avg Hold (d)":s.get('avg_hold_days',0)} for t,s in per_stock.items()]
        st.dataframe(pd.DataFrame(rows).sort_values("Win Rate",ascending=False),
                     use_container_width=True, hide_index=True)
    with st.expander("📋 Full Trade Log"):
        log=bt_data.get('trade_log',[])
        if log:
            df_log=pd.DataFrame(log).rename(columns={
                'ticker':'Ticker','buy_date':'Buy Date','sell_date':'Sell Date',
                'buy_price':'Buy Price (₪)','sell_price':'Sell Price (₪)',
                'return_%':'Return %','hold_days':'Hold Days','result':'Result','rsi_at_buy':'RSI at Buy'})
            st.dataframe(df_log, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
#  NEWS
# ══════════════════════════════════════════════
def render_market_news():
    st.markdown("### 📰 Market News")
    st.caption("Headlines from major TASE indices via yfinance")
    if st.button("🔄 Refresh News", key="refresh_news"):
        st.cache_data.clear()
    with st.spinner("Loading news..."):
        headlines = fetch_market_news_il()
    if not headlines:
        st.info("No news available right now."); return
    for h in headlines:
        st.markdown(f'<div class="news-item"><a href="{h.get("url","#")}" target="_blank" '
                    f'class="news-title">{h.get("title","")}</a>'
                    f'<div class="news-meta">{h.get("publisher","")} · {h.get("published","")}</div>'
                    f'</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def main():
    st.markdown('<div class="main-header">🇮🇱 TASE STOCK SCANNER</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live Screener · Murphy Method · Tel Aviv Stock Exchange · Signal Backtester</div>',
                unsafe_allow_html=True)

    vix    = render_market_bar()
    params = render_sidebar()

    if vix >= 28:
        st.error("🚫 **VIX above 28 — Very high fear. Do not enter new positions today.**")
    elif vix >= 20:
        st.warning("⚠️ **VIX 20–28 — Caution. Consider only high-score stocks (≥7).**")

    for k in ['scan_results_il','backtest_results_il']:
        if k not in st.session_state: st.session_state[k] = None

    # ── DEBUG
    if params.get('run_debug') and params.get('debug_ticker'):
        t = params['debug_ticker']
        if not t.endswith('.TA'): t += '.TA'
        with st.spinner(f"Debugging {t}..."):
            msg = debug_ticker_il(t, params)
        st.info(msg)

    # ── STEP 1: SCAN
    if params['run_scan']:
        sector = params.get('selected_sector','All')
        if sector != 'All':
            universe = get_by_sector(sector) or STOCK_UNIVERSE_IL
        else:
            universe = STOCK_UNIVERSE_IL[:params['max_stocks']]
        tag = f"  (Sector: {sector})" if sector != 'All' else ''
        st.info(f"🔍 Scanning {len(universe)} stocks{tag}...")
        pb=st.progress(0); st_txt=st.empty(); results=[]
        for i,ticker in enumerate(universe):
            pb.progress((i+1)/len(universe))
            st_txt.caption(f"Scanning {ticker.replace('.TA','')}… ({i+1}/{len(universe)}) — found: {len(results)}")
            try:
                r = calculate_indicators_il(ticker, params)
                if r and r.get('passes_filter'): results.append(r)
            except Exception: pass
        results.sort(key=lambda x: (-x.get('score',0), x.get('ticker','')))
        st.session_state.scan_results_il=results; st.session_state.backtest_results_il=None
        pb.empty(); st_txt.empty()
        if not results:
            st.warning("⚠️ 0 stocks passed filters. Try: RSI Max=65, uncheck MA, lower Min Beta.")

    # ── STEP 2: BACKTEST
    if params['run_backtest']:
        scan_res=st.session_state.scan_results_il
        if not scan_res:
            st.warning("⚠️ Run Step 1 first!")
        else:
            tickers=[r['ticker'] for r in scan_res]
            st.info(f"📊 Backtesting {len(tickers)} stocks — 1 year history…")
            pb2=st.progress(0); st2=st.empty()
            bt=run_backtest_il(tickers, params, pb2, st2)
            st.session_state.backtest_results_il=bt
            pb2.empty(); st2.empty()

    # ── DISPLAY
    results=st.session_state.scan_results_il
    bt_data=st.session_state.backtest_results_il

    if results is not None:
        if not results:
            st.info("No stocks matched filters. Try relaxing criteria.")
        else:
            st.markdown("---")
            c1,c2,c3,c4=st.columns(4)
            strong=sum(1 for r in results if r.get('score',0)>=7)
            avg_rsi=np.mean([r.get('rsi',0) for r in results])
            near_bb=sum(1 for r in results if r.get('bb_pct',1)<0.2)
            for col,lbl,val in [(c1,"Stocks Found",str(len(results))),(c2,"Strong ≥7",str(strong)),
                                 (c3,"Avg RSI",f"{avg_rsi:.1f}"),(c4,"Near BB Lower",str(near_bb))]:
                col.markdown(f'<div class="metric-card"><div class="scan-label">{lbl}</div>'
                              f'<div class="scan-stat">{val}</div></div>', unsafe_allow_html=True)
            st.markdown("---")
            cf1,cf2,cf3=st.columns(3)
            with cf1: min_score=st.slider("Min Score",0,10,0)
            with cf2: sort_by=st.selectbox("Sort by",["Score","RSI (lowest)","Win Rate (backtest)"])
            with cf3: fresh_only=st.checkbox("Fresh signals only",value=False)

            filtered=[r for r in results if r.get('score',0)>=min_score]
            if fresh_only: filtered=[r for r in filtered if r.get('signal_fresh',False)]
            st.caption(f"🔍 Passed screener: {len(results)} stocks | Showing: {len(filtered)}")
            if sort_by=="RSI (lowest)":
                filtered.sort(key=lambda x: x.get('rsi',100))
            elif sort_by=="Win Rate (backtest)" and bt_data:
                ps=bt_data.get('per_stock',{})
                filtered.sort(key=lambda x: ps.get(x['ticker'],{}).get('win_rate',0),reverse=True)

            st.markdown(f"### 🎯 {len(filtered)} Opportunities")
            t1,t2,t3,t4=st.tabs(["📋 Stocks","📈 Charts","📰 News","📊 Backtest"])

            with t1:
                if not filtered: st.info("No stocks to display with current filters.")
                for stock in filtered:
                    bts=bt_data.get('per_stock',{}).get(stock['ticker']) if bt_data else None
                    render_stock_card_il(stock, bts, rsi_period=params['rsi_period'])

            with t2:
                if filtered:
                    opts=[r['ticker'].replace('.TA','')+" — "+r.get('name','')[:30] for r in filtered[:30]]
                    idx=st.selectbox("Select stock for chart",range(len(opts)),format_func=lambda i:opts[i])
                    render_chart_il(filtered[idx]['ticker'], params)
                else: st.info("No stocks to display.")

            with t3:
                if filtered:
                    opts=[r['ticker'].replace('.TA','')+" — "+r.get('name','')[:25] for r in filtered[:30]]
                    si=st.selectbox("News for",range(len(opts)),format_func=lambda i:opts[i],key="ns_il")
                    with st.spinner("Loading news..."):
                        news=fetch_news_il(filtered[si]['ticker'])
                    if news:
                        for item in news:
                            st.markdown(f'<div class="news-item"><a href="{item.get("url","#")}" '
                                        f'target="_blank" class="news-title">{item.get("title","")}</a>'
                                        f'<div class="news-meta">{item.get("publisher","")} · {item.get("published","")}'
                                        f'</div></div>', unsafe_allow_html=True)
                    else: st.info("No news found for this stock.")
                    st.markdown("---"); render_market_news()
                else: render_market_news()

            with t4:
                if bt_data: render_backtest_panel_il(bt_data)
                else: st.info("Press **STEP 2 — BACKTEST** in the sidebar after scanning.")
    else:
        st.markdown(f"""
        <div style="text-align:center;padding:5rem 2rem;color:#3d4f6b;">
          <div style="font-size:3.5rem;margin-bottom:1rem;">🇮🇱</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:1.15rem;color:#5a7099;">
            Press <strong style="color:#00e5c0;">STEP 1 — RUN SCAN</strong> to start
          </div>
          <div style="font-size:0.85rem;margin-top:0.6rem;color:#3d4f6b;">
            TASE stock screener based on John Murphy's technical analysis<br>
            Finds oversold stocks in uptrends · MA · RSI · Bollinger Bands · MACD
          </div>
          <div style="margin-top:2rem;display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;">
            <div style="text-align:center;"><div style="font-family:'IBM Plex Mono',monospace;font-size:1.5rem;color:#00e5c0;">{len(STOCK_UNIVERSE_IL)}</div>
              <div style="font-size:0.72rem;color:#3d4f6b;">Stocks in Universe</div></div>
            <div style="text-align:center;"><div style="font-family:'IBM Plex Mono',monospace;font-size:1.5rem;color:#60a5fa;">₪</div>
              <div style="font-size:0.72rem;color:#3d4f6b;">Israeli Shekel</div></div>
            <div style="text-align:center;"><div style="font-family:'IBM Plex Mono',monospace;font-size:1.5rem;color:#a78bfa;">TA-125</div>
              <div style="font-size:0.72rem;color:#3d4f6b;">Benchmark Index</div></div>
          </div>
        </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
