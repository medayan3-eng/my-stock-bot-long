"""
app_il.py — TASE Israel Stock Scanner (Murphy Method)
סורק מניות בורסת ת"א — שיטת מרפי
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from screener_il import calculate_indicators_il, debug_ticker_il
from backtester_il import run_backtest_il
from news_fetcher_il import fetch_news_il, fetch_market_news_il
from stock_universe_il import STOCK_UNIVERSE_IL, SECTOR_MAP, get_by_sector

# ══════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="📊 סורק מניות ת\"א — מרפי",
    page_icon="🇮🇱",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Heebo:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'Heebo', sans-serif;
    direction: rtl;
  }
  .stApp { background: #070b14; color: #dde4f0; }

  /* Header */
  .main-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 2rem; font-weight: 700;
    color: #00e5c0; letter-spacing: -1px;
    margin-bottom: 0.1rem;
  }
  .sub-header {
    font-size: 0.78rem; color: #3d4f6b;
    letter-spacing: 2px; text-transform: uppercase;
    font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 1rem;
  }

  /* Market bar */
  .market-bar {
    background: #0b1120;
    border: 1px solid #172035;
    border-radius: 12px;
    padding: 0.9rem 1.4rem;
    display: flex; gap: 1.8rem;
    align-items: center; flex-wrap: wrap;
    margin-bottom: 1.2rem;
  }
  .mkt-item    { display:flex; flex-direction:column; min-width:90px; }
  .mkt-label   { font-size:0.66rem; color:#3d4f6b; text-transform:uppercase; letter-spacing:1px; font-family:'IBM Plex Mono',monospace; }
  .mkt-val     { font-family:'IBM Plex Mono',monospace; font-size:1.05rem; font-weight:700; }
  .mkt-chg     { font-family:'IBM Plex Mono',monospace; font-size:0.75rem; }

  /* VIX / Fear box */
  .fear-box        { border-radius:8px; padding:0.5rem 1rem; display:flex; flex-direction:column; align-items:center; min-width:140px; }
  .fear-box-green  { background:rgba(0,229,192,0.10); border:2px solid #00e5c0; }
  .fear-box-yellow { background:rgba(251,191,36,0.10); border:2px solid #fbbf24; }
  .fear-box-red    { background:rgba(248,113,113,0.12); border:2px solid #f87171; }
  .fear-val-green  { font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#00e5c0; }
  .fear-val-yellow { font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#fbbf24; }
  .fear-val-red    { font-family:'IBM Plex Mono',monospace; font-size:1.5rem; font-weight:700; color:#f87171; }
  .fear-label      { font-size:0.65rem; color:#8a9ab5; text-transform:uppercase; letter-spacing:1px; font-family:'IBM Plex Mono',monospace; }
  .fear-msg        { font-size:0.70rem; text-align:center; margin-top:0.2rem; }

  /* Cards */
  .metric-card {
    background: #0f1927; border: 1px solid #172035;
    border-radius: 8px; padding: 0.9rem;
    margin: 0.2rem 0; border-left: 3px solid #00e5c0;
  }
  .stock-card {
    background: #0f1927; border: 1px solid #172035;
    border-radius: 12px; padding: 1.4rem;
    margin: 0.5rem 0; transition: border-color 0.2s;
  }
  .stock-card:hover { border-color: #00e5c0; box-shadow: 0 0 20px rgba(0,229,192,0.08); }

  /* Typography */
  .ticker-symbol { font-family:'IBM Plex Mono',monospace; font-size:1.3rem; font-weight:700; color:#00e5c0; }
  .price-display { font-family:'IBM Plex Mono',monospace; font-size:1.05rem; color:#dde4f0; }
  .company-name  { color:#5a7099; font-size:0.82rem; margin-right:0.6rem; }
  .scan-stat  { font-family:'IBM Plex Mono',monospace; font-size:1.7rem; font-weight:700; color:#00e5c0; }
  .scan-label { font-size:0.70rem; color:#3d4f6b; text-transform:uppercase; letter-spacing:1px; font-family:'IBM Plex Mono',monospace; }

  /* Badges */
  .badge        { display:inline-block; padding:0.17rem 0.5rem; border-radius:4px; font-size:0.70rem; font-family:'IBM Plex Mono',monospace; font-weight:700; margin:0.1rem; }
  .badge-green  { background:rgba(0,229,192,0.12);  color:#00e5c0; border:1px solid rgba(0,229,192,0.3); }
  .badge-yellow { background:rgba(251,191,36,0.12); color:#fbbf24; border:1px solid rgba(251,191,36,0.3); }
  .badge-red    { background:rgba(248,113,113,0.12); color:#f87171; border:1px solid rgba(248,113,113,0.3); }
  .badge-blue   { background:rgba(96,165,250,0.12); color:#60a5fa; border:1px solid rgba(96,165,250,0.3); }
  .badge-purple { background:rgba(167,139,250,0.12); color:#a78bfa; border:1px solid rgba(167,139,250,0.3); }

  /* Sidebar */
  div[data-testid="stSidebar"] { background: #0b1120; border-left: 1px solid #172035; }
  .stButton > button {
    background: #00e5c0; color: #070b14;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 700; border: none; border-radius: 8px;
    padding: 0.6rem 1.5rem; width: 100%;
    letter-spacing: 0.5px;
  }
  .stButton > button:hover { background: #00c4a4; }

  /* News */
  .news-item {
    background: #0f1927; border: 1px solid #172035;
    border-radius: 8px; padding: 0.85rem;
    margin: 0.3rem 0; border-right: 3px solid #60a5fa;
  }
  .news-title { color: #60a5fa; font-size: 0.87rem; font-weight: 600; }
  .news-meta  { color: #3d4f6b; font-size: 0.70rem; font-family:'IBM Plex Mono',monospace; margin-top:0.2rem; }

  hr { border-color: #172035; }

  /* RTL fix for Streamlit tabs */
  [data-testid="stTab"] { direction: rtl; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  MARKET DATA
# ══════════════════════════════════════════════
@st.cache_data(ttl=180)
def fetch_tase_market_data():
    symbols = {
        "^TA35.TA":  "ת\"א 35",
        "^TA125.TA": "ת\"א 125",
        "^VIX":      "VIX (ארה\"ב)",
        "USDILS=X":  "דולר/שקל",
    }
    result = {}
    for sym, label in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="2d", interval="1d")
            if len(hist) >= 2:
                prev  = float(hist['Close'].iloc[-2])
                curr  = float(hist['Close'].iloc[-1])
                chg_p = (curr - prev) / prev * 100
            elif len(hist) == 1:
                curr = float(hist['Close'].iloc[-1]); chg_p = 0
            else:
                curr = chg_p = 0
            result[label] = {"value": curr, "change_pct": chg_p}
        except Exception:
            result[label] = {"value": 0, "change_pct": 0}
    return result


def render_market_bar():
    data = fetch_tase_market_data()
    vix  = data.get('VIX (ארה"ב)', {}).get("value", 0)

    if   vix <= 0:  vix_cls = "green";  vix_msg = "אין נתון"
    elif vix < 20:  vix_cls = "green";  vix_msg = "✅ פחד נמוך — אפשר לסחור"
    elif vix < 28:  vix_cls = "yellow"; vix_msg = "⚠️ זהירות — מניות חזקות בלבד"
    else:           vix_cls = "red";    vix_msg = "🚫 פחד גבוה — לא להיכנס"

    def tile(label, d):
        v   = d.get("value", 0)
        chg = d.get("change_pct", 0)
        col = "#00e5c0" if chg >= 0 else "#f87171"
        arrow = "▲" if chg >= 0 else "▼"
        fmt = f"{v:,.2f}" if v < 1000 else f"{v:,.0f}"
        return (f'<div class="mkt-item">'
                f'<span class="mkt-label">{label}</span>'
                f'<span class="mkt-val">{fmt}</span>'
                f'<span class="mkt-chg" style="color:{col}">{arrow} {abs(chg):.2f}%</span>'
                f'</div>')

    tiles = "".join(tile(k, v) for k, v in data.items() if "VIX" not in k)
    vix_str = f"{vix:.2f}" if vix else "—"
    msg_col = {"green": "#00e5c0", "yellow": "#fbbf24", "red": "#f87171"}[vix_cls]

    # שעון ישראל
    il_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M:%S')
    is_market_open = _is_tase_open()

    st.markdown(f"""
    <div class="market-bar">
      <div class="fear-box fear-box-{vix_cls}">
        <span class="fear-label">😨 VIX אמריקה</span>
        <span class="fear-val-{vix_cls}">{vix_str}</span>
        <span class="fear-msg" style="color:{msg_col};">{vix_msg}</span>
      </div>
      <div style="width:1px;background:#172035;align-self:stretch;"></div>
      {tiles}
      <div style="margin-right:auto;text-align:left;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:0.72rem;color:#3d4f6b;">
          🕐 {il_time} 🇮🇱
        </div>
        <div style="font-size:0.72rem;margin-top:0.2rem;
                    color:{'#00e5c0' if is_market_open else '#f87171'};">
          {'🟢 בורסה פתוחה' if is_market_open else '🔴 בורסה סגורה'}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    return vix


def _is_tase_open() -> bool:
    """בורסת ת"א פתוחה 09:00–17:30 ראשון–חמישי (שעון ישראל = UTC+3)."""
    now_il = datetime.utcnow() + timedelta(hours=3)
    if now_il.weekday() in (5, 6):   # שבת=5, ראשון=6 — אבל ראשון פתוח!
        # Python: Mon=0…Sun=6; ת"א סגורה בשבת (5)
        if now_il.weekday() == 5:    # שבת
            return False
    if now_il.weekday() == 4 and now_il.hour >= 14:  # שישי אחה"צ
        return False
    h, m = now_il.hour, now_il.minute
    return (9, 0) <= (h, m) <= (17, 30)


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ פרמטרים")
        st.markdown("---")

        min_price  = st.slider("מחיר מינימום (₪)", 2, 200, 10)
        min_volume = st.number_input("נפח יומי מינימום (אלפי מניות)", 10, 5000, 100, 10)
        min_beta   = st.slider("בטא מינימום", 0.0, 3.0, 0.5, 0.1)

        st.markdown("---")
        st.markdown("**RSI**")
        rsi_range  = st.slider("טווח RSI", 10, 90, (10, 55))
        rsi_min    = rsi_range[0]
        rsi_max    = rsi_range[1]
        rsi_period = st.number_input("תקופת RSI", 5, 21, 14)
        st.caption(f"מניות עם RSI בין {rsi_min} – {rsi_max}")

        st.markdown("---")
        st.markdown("**פילטרי מגמה**")
        req_ma      = st.checkbox("מעל ממוצע ארוך (MA200/MA120)", value=True)
        req50       = st.checkbox("מעל MA50", value=True)
        req20       = st.checkbox("מעל MA20 (אופציונלי)", value=False)
        req_uptrend = st.checkbox("📈 מגמת עלייה 52 שבועות (מרפי)", value=True,
                                  help="מחיר > שנה קודמת + MA50 > MA200 + מחיר > MA200")

        st.markdown("---")
        st.markdown("**בולינגר**")
        bb_period = st.number_input("תקופת BB", 10, 30, 20)
        bb_std    = st.slider("סטיית BB", 1.5, 3.0, 2.0, 0.1)

        st.markdown("---")
        st.markdown("**סינון מגזר**")
        all_sectors = ["הכל"] + list(SECTOR_MAP.keys())
        selected_sector = st.selectbox("מגזר", all_sectors)

        st.markdown("---")
        fresh_only = st.checkbox("🟢 סיגנלים טריים (≤5 ימים)", value=False)
        max_stocks = st.slider("מניות לסריקה", 20, len(STOCK_UNIVERSE_IL),
                               len(STOCK_UNIVERSE_IL))

        st.markdown("---")
        run_scan = st.button("🔍 שלב 1 — סרוק עכשיו", use_container_width=True)
        st.caption("נתונים חיים מ-yfinance")
        st.markdown("")
        run_bt = st.button("📊 שלב 2 — בק-טסט", use_container_width=True)
        st.caption("בודק רק את מניות שלב 1 — שנה אחורה")
        st.markdown("")
        debug_input = st.text_input("🔧 בדוק מניה ספציפית (למשל TEVA.TA)").upper().strip()
        run_debug   = st.button("🔧 בדוק מניה", use_container_width=True)

        return dict(
            min_price=min_price,
            min_volume=min_volume * 1_000,
            min_beta=min_beta,
            rsi_min=rsi_min, rsi_max=rsi_max,
            rsi_period=int(rsi_period),
            require_above_ma=req_ma,
            require_above_50=req50,
            require_above_20=req20,
            require_uptrend_52w=req_uptrend,
            bb_period=int(bb_period), bb_std=bb_std,
            show_fresh_only=fresh_only,
            selected_sector=selected_sector,
            max_stocks=max_stocks,
            run_scan=run_scan, run_backtest=run_bt,
            run_debug=run_debug, debug_ticker=debug_input,
        )


# ══════════════════════════════════════════════
#  STOCK CARD
# ══════════════════════════════════════════════
def render_stock_card_il(stock, bt_summary=None):
    score       = stock.get('score', 0)
    rsi         = stock.get('rsi', 0)
    bb_pct      = stock.get('bb_pct', 0.5)
    trend_4w    = stock.get('trend_4w', 0)
    beta        = stock.get('beta', 0)
    macd_hist   = stock.get('macd_hist', 0)
    macd_bullish= stock.get('macd_bullish', False)
    fresh       = stock.get('signal_fresh', False)
    sig_date    = stock.get('signal_date', '')
    price       = stock.get('price', 0)
    rs          = stock.get('rs', 1.0)
    vol_ratio   = stock.get('volume_ratio', 1.0)
    vol_spike   = stock.get('volume_spike', False)
    support     = stock.get('support')
    resistance  = stock.get('resistance')
    near_sup    = stock.get('near_support', False)
    patterns    = stock.get('patterns', [])
    uptrend_52w = stock.get('uptrend_52w', False)
    rr_ratio    = stock.get('rr_ratio', 0)
    rr_valid    = stock.get('rr_valid', False)
    rr_stop     = stock.get('rr_stop')
    rr_target   = stock.get('rr_target')
    summary     = stock.get('summary', '')
    ticker      = stock.get('ticker', '')
    ticker_s    = stock.get('ticker_short', ticker.replace('.TA',''))
    name        = stock.get('name', ticker_s)
    market_cap  = stock.get('market_cap_m')
    mc_text     = f"שמ ₪{market_cap:,.0f}M" if market_cap else ""

    sig_col = "#00e5c0" if score >= 7 else "#fbbf24" if score >= 5 else "#f87171"

    # TradingView — מניות ישראליות עם prefix TASE
    tv_url = f"https://www.tradingview.com/chart/?symbol=TASE%3A{ticker_s}&interval=D"

    badges = []
    if stock.get('above_ma'):    badges.append('<span class="badge badge-green">MA ✓</span>')
    if stock.get('above_50'):    badges.append('<span class="badge badge-green">MA50 ✓</span>')
    if uptrend_52w:              badges.append('<span class="badge badge-green">📈 52ש ✓</span>')
    if rsi < 30:                 badges.append('<span class="badge badge-red">RSI קיצוני</span>')
    elif rsi < 40:               badges.append('<span class="badge badge-yellow">RSI OVERSOLD</span>')
    if bb_pct < 0.2:             badges.append('<span class="badge badge-green">BB תחתון ✓</span>')
    if trend_4w > 0:             badges.append('<span class="badge badge-green">טרנד עולה</span>')
    if macd_bullish:             badges.append('<span class="badge badge-green">MACD ✓</span>')
    else:                        badges.append('<span class="badge badge-red">MACD ✗</span>')
    if vol_spike:                badges.append('<span class="badge badge-yellow">⚡ נפח גבוה</span>')
    if near_sup:                 badges.append('<span class="badge badge-green">🎯 ליד תמיכה</span>')
    for p in patterns[:1]:       badges.append(f'<span class="badge badge-blue">📐 {p}</span>')
    if rr_valid:                 badges.append(f'<span class="badge badge-green">R/R 1:{rr_ratio}</span>')
    badges.append('<span class="badge badge-green">🟢 טרי</span>' if fresh else
                  '<span class="badge badge-yellow">⏱ ישן</span>')

    # Backtest HTML
    bt_html = ""
    if bt_summary:
        wr  = bt_summary.get('win_rate', 0)
        tot = bt_summary.get('total_trades', 0)
        avg = bt_summary.get('avg_return', 0)
        wc  = "#00e5c0" if wr >= 60 else "#fbbf24" if wr >= 45 else "#f87171"
        bt_html = f"""
        <div style="margin-top:0.5rem;padding:0.5rem 0.9rem;
                    background:#0b1120;border-radius:6px;border:1px solid #172035;
                    display:flex;gap:2rem;">
          <div><div class="scan-label">📊 אחוז הצלחה</div>
               <div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;font-weight:700;color:{wc};">{wr:.0f}%</div></div>
          <div><div class="scan-label">עסקאות</div>
               <div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;color:#dde4f0;">{tot}</div></div>
          <div><div class="scan-label">תשואה ממוצעת</div>
               <div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;
                    color:{'#00e5c0' if avg >= 0 else '#f87171'};">{avg:+.1f}%</div></div>
        </div>"""

    # Support/Resistance HTML
    sr_parts = []
    if support:    sr_parts.append(f'<span style="color:#00e5c0;">🟩 תמיכה: ₪{support}</span>')
    if resistance: sr_parts.append(f'<span style="color:#f87171;">🟥 התנגדות: ₪{resistance}</span>')
    if rr_valid:   sr_parts.append(f'<span style="color:#fbbf24;">סטופ: ₪{rr_stop} → יעד: ₪{rr_target} (1:{rr_ratio})</span>')
    sr_html = (f'<div style="margin-top:0.4rem;font-size:0.76rem;'
               f'font-family:\'IBM Plex Mono\',monospace;">'
               f'{" &nbsp;|&nbsp; ".join(sr_parts)}</div>') if sr_parts else ""

    summary_html = (f'<div style="margin-top:0.5rem;padding:0.5rem 0.8rem;'
                    f'background:rgba(0,229,192,0.05);border-right:3px solid #00e5c0;'
                    f'border-radius:0 6px 6px 0;font-size:0.8rem;color:#8a9ab5;line-height:1.6;">'
                    f'💡 {summary}</div>') if summary else ""

    st.markdown(f"""
    <div class="stock-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
          <span class="ticker-symbol">{ticker_s}</span>
          <span class="company-name">{name}</span>
          {'<span style="font-size:0.70rem;color:#3d4f6b;font-family:\'IBM Plex Mono\',monospace;">'+mc_text+'</span>' if mc_text else ''}
        </div>
        <div style="text-align:left;">
          <div class="price-display">₪{price:,.2f}</div>
          <div style="font-weight:700;color:{sig_col};font-size:0.85rem;font-family:'IBM Plex Mono',monospace;">
            ניקוד: {score}/10
          </div>
        </div>
      </div>

      <div style="margin:0.5rem 0;">{''.join(badges)}</div>

      <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:0.4rem;margin-top:0.6rem;">
        <div>
          <div class="scan-label">RSI({rsi_period if True else 14})</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
               color:{'#f87171' if rsi<30 else '#fbbf24' if rsi<40 else '#dde4f0'};">{rsi:.1f}</div>
        </div>
        <div>
          <div class="scan-label">MACD היסט</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
               color:{'#00e5c0' if macd_bullish else '#f87171'};">{macd_hist:+.3f}</div>
        </div>
        <div>
          <div class="scan-label">BB%B</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
               color:{'#00e5c0' if bb_pct<0.2 else '#dde4f0'};">{bb_pct:.2f}</div>
        </div>
        <div>
          <div class="scan-label">RS vs ת"א</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
               color:{'#00e5c0' if rs>1 else '#f87171'};">{rs:+.2f}</div>
        </div>
        <div>
          <div class="scan-label">נפח יחסי</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
               color:{'#fbbf24' if vol_spike else '#dde4f0'};">{'⚡' if vol_spike else ''}{vol_ratio:.1f}×</div>
        </div>
        <div>
          <div class="scan-label">טרנד 4ש</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:0.88rem;font-weight:700;
               color:{'#00e5c0' if trend_4w>0 else '#f87171'};">
            {'▲' if trend_4w>0 else '▼'} {abs(trend_4w):.1f}%
          </div>
        </div>
      </div>

      {sr_html}
      {summary_html}

      <div style="margin-top:0.5rem;font-size:0.68rem;font-family:'IBM Plex Mono',monospace;color:#3d4f6b;">
        📅 {sig_date} &nbsp;
        {'✅ כנס עכשיו' if fresh else '⚠️ בדוק לפני כניסה'}
        &nbsp;&nbsp;
        <a href="{tv_url}" target="_blank"
           style="color:#60a5fa;text-decoration:none;">📊 TradingView →</a>
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
            st.warning(f"אין מספיק נתונים ל-{ticker}")
            return

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

        delta  = close.diff()
        g      = delta.clip(lower=0).rolling(params['rsi_period']).mean()
        l      = (-delta.clip(upper=0)).rolling(params['rsi_period']).mean()
        df['RSI'] = 100 - 100 / (1 + g / l)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.70, 0.30], vertical_spacing=0.04)

        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name=ticker,
            increasing_line_color='#00e5c0',
            decreasing_line_color='#f87171'), row=1, col=1)

        for ma, col, w in [('MA20','#fbbf24',1),('MA50','#60a5fa',1.5),('MA120','#a78bfa',1.5)]:
            if ma in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma,
                    line=dict(color=col, width=w), opacity=0.85), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['BBu'], name='BB עליון',
            line=dict(color='#3d4f6b', width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBl'], name='BB תחתון',
            line=dict(color='#3d4f6b', width=1, dash='dot'),
            fill='tonexty', fillcolor='rgba(61,79,107,0.07)'), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI',
            line=dict(color='#fbbf24', width=1.5)), row=2, col=1)
        fig.add_hline(y=45, line_dash="dot", line_color="#00e5c0", opacity=0.5, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#f87171", opacity=0.5, row=2, col=1)

        ticker_short = ticker.replace('.TA', '')
        fig.update_layout(
            plot_bgcolor='#0f1927', paper_bgcolor='#070b14',
            font=dict(color='#dde4f0', family='IBM Plex Mono'),
            xaxis_rangeslider_visible=False, height=520,
            margin=dict(l=10, r=10, t=35, b=10),
            title=dict(text=f"{ticker_short} — גרף 6 חודשים",
                       font=dict(color='#00e5c0', size=14)),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=9)))
        fig.update_xaxes(gridcolor='#172035')
        fig.update_yaxes(gridcolor='#172035')
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"שגיאה בגרף: {e}")


# ══════════════════════════════════════════════
#  BACKTEST RESULTS
# ══════════════════════════════════════════════
def render_backtest_panel_il(bt_data):
    st.markdown("### 📊 תוצאות בק-טסט — 12 חודשים, מניות שלב 1 בלבד")
    overall   = bt_data.get('overall', {})
    per_stock = bt_data.get('per_stock', {})

    total = overall.get('total_trades', 0)
    wins  = overall.get('wins', 0)
    loss  = overall.get('losses', 0)
    wr    = overall.get('win_rate', 0)
    avg_r = overall.get('avg_return', 0)
    best  = overall.get('best_trade', 0)
    worst = overall.get('worst_trade', 0)
    wc    = "#00e5c0" if wr >= 60 else "#fbbf24" if wr >= 45 else "#f87171"

    cols = st.columns(6)
    for col, lbl, val, clr in zip(cols,
        ["סה\"כ עסקאות", "✅ רווחיות", "❌ הפסדיות", "% הצלחה", "תשואה ממוצעת", "טוב / גרוע"],
        [str(total), str(wins), str(loss), f"{wr:.1f}%",
         f"{avg_r:+.2f}%", f"{best:+.1f}% / {worst:+.1f}%"],
        ["#dde4f0", "#00e5c0", "#f87171", wc,
         "#00e5c0" if avg_r >= 0 else "#f87171", "#dde4f0"]):
        col.markdown(
            f'<div class="metric-card">'
            f'<div class="scan-label">{lbl}</div>'
            f'<div class="scan-stat" style="color:{clr};font-size:1.25rem;">{val}</div>'
            f'</div>', unsafe_allow_html=True)

    if per_stock:
        st.markdown("#### 📋 פירוט לפי מניה")
        rows = []
        for ticker, s in per_stock.items():
            rows.append({
                "מניה":          ticker.replace('.TA',''),
                "עסקאות":        s.get('total_trades', 0),
                "רווחיות":       s.get('wins', 0),
                "הפסדיות":       s.get('losses', 0),
                "% הצלחה":       f"{s.get('win_rate',0):.0f}%",
                "תשואה ממוצעת":  f"{s.get('avg_return',0):+.2f}%",
                "עסקה טובה":     f"{s.get('best_trade',0):+.1f}%",
                "עסקה גרועה":    f"{s.get('worst_trade',0):+.1f}%",
                "ימי החזקה":     s.get('avg_hold_days', 0),
            })
        df_bt = pd.DataFrame(rows).sort_values("% הצלחה", ascending=False)
        st.dataframe(df_bt, use_container_width=True, hide_index=True)

    with st.expander("📋 יומן עסקאות מלא"):
        log = bt_data.get('trade_log', [])
        if log:
            df_log = pd.DataFrame(log)
            # תרגום עמודות
            df_log = df_log.rename(columns={
                'ticker': 'מניה', 'buy_date': 'תאריך קנייה',
                'sell_date': 'תאריך מכירה', 'buy_price': 'מחיר קנייה (₪)',
                'sell_price': 'מחיר מכירה (₪)', 'return_%': 'תשואה %',
                'hold_days': 'ימים', 'result': 'תוצאה', 'rsi_at_buy': 'RSI בקנייה'
            })
            st.dataframe(df_log, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
#  MARKET NEWS TAB
# ══════════════════════════════════════════════
def render_market_news():
    st.markdown("### 📰 חדשות שוק כלליות")
    st.caption("חדשות שנאספות מ-yfinance עבור מדדי ת\"א הראשיים")
    if st.button("🔄 רענן חדשות", key="refresh_news"):
        st.cache_data.clear()
    with st.spinner("טוען חדשות..."):
        headlines = fetch_market_news_il()
    if not headlines:
        st.info("לא נמצאו חדשות כרגע.")
        return
    for h in headlines:
        st.markdown(
            f'<div class="news-item">'
            f'<a href="{h.get("url","#")}" target="_blank" class="news-title">'
            f'{h.get("title","")}</a>'
            f'<div class="news-meta">{h.get("publisher","")} · {h.get("published","")}</div>'
            f'</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def main():
    # Header
    st.markdown(
        '<div class="main-header">🇮🇱 סורק מניות ת"א — מרפי</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Live TASE Screener · Murphy Method · Signal Backtester</div>',
        unsafe_allow_html=True)

    vix    = render_market_bar()
    params = render_sidebar()

    # VIX warnings
    if vix >= 28:
        st.error("🚫 **VIX מעל 28 — פחד גבוה מאוד. אל תיכנסו לפוזיציות חדשות היום.**")
    elif vix >= 20:
        st.warning("⚠️ **VIX בין 20–28 — זהירות. שקלו רק מניות עם ציון גבוה (≥7).**")

    # Session state init
    for k in ['scan_results_il', 'backtest_results_il']:
        if k not in st.session_state:
            st.session_state[k] = None

    # ── DEBUG ──────────────────────────────────────────────────────
    if params.get('run_debug') and params.get('debug_ticker'):
        t = params['debug_ticker']
        if not t.endswith('.TA'):
            t += '.TA'
        with st.spinner(f"בודק {t}..."):
            msg = debug_ticker_il(t, params)
        st.info(msg)

    # ── STEP 1: SCAN ───────────────────────────────────────────────
    if params['run_scan']:
        sector = params.get('selected_sector', 'הכל')
        if sector != 'הכל':
            universe = get_by_sector(sector)
            if not universe:
                universe = STOCK_UNIVERSE_IL
        else:
            universe = STOCK_UNIVERSE_IL[:params['max_stocks']]
        st.info(f"🔍 סורק {len(universe)} מניות{'  (מגזר: ' + sector + ')' if sector != 'הכל' else ''}...")
        pb     = st.progress(0)
        st_txt = st.empty()
        results = []

        for i, ticker in enumerate(universe):
            pb.progress((i + 1) / len(universe))
            st_txt.caption(f"סורק {ticker.replace('.TA','')}… ({i+1}/{len(universe)}) — נמצאו: {len(results)}")
            try:
                r = calculate_indicators_il(ticker, params)
                if r and r.get('passes_filter'):
                    results.append(r)
            except Exception:
                pass

        results.sort(key=lambda x: (-x.get('score', 0), x.get('ticker', '')))
        st.session_state.scan_results_il     = results
        st.session_state.backtest_results_il = None
        pb.empty(); st_txt.empty()

        if not results:
            st.warning("⚠️ 0 מניות עברו את הפילטרים. נסה: RSI Max=65, בטל דרישת MA, הורד בטא מינימום.")

    # ── STEP 2: BACKTEST ───────────────────────────────────────────
    if params['run_backtest']:
        scan_res = st.session_state.scan_results_il
        if not scan_res:
            st.warning("⚠️ הרץ קודם את שלב 1!")
        else:
            tickers = [r['ticker'] for r in scan_res]
            st.info(f"📊 בק-טסט ל-{len(tickers)} מניות — שנה אחורה...")
            pb2 = st.progress(0)
            st2 = st.empty()
            bt  = run_backtest_il(tickers, params, pb2, st2)
            st.session_state.backtest_results_il = bt
            pb2.empty(); st2.empty()

    # ── DISPLAY ────────────────────────────────────────────────────
    results = st.session_state.scan_results_il
    bt_data = st.session_state.backtest_results_il

    if results is not None:
        if not results:
            st.info("אין מניות שעומדות בפילטרים. נסה להרפות את הקריטריונים.")
        else:
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            strong   = sum(1 for r in results if r.get('score', 0) >= 7)
            avg_rsi  = np.mean([r.get('rsi', 0) for r in results])
            near_bb  = sum(1 for r in results if r.get('bb_pct', 1) < 0.2)
            for col, lbl, val in [
                (c1, "מניות נמצאו",     str(len(results))),
                (c2, "חזקות ≥7",         str(strong)),
                (c3, "RSI ממוצע",        f"{avg_rsi:.1f}"),
                (c4, "ליד BB תחתון",     str(near_bb)),
            ]:
                col.markdown(
                    f'<div class="metric-card">'
                    f'<div class="scan-label">{lbl}</div>'
                    f'<div class="scan-stat">{val}</div>'
                    f'</div>', unsafe_allow_html=True)

            st.markdown("---")

            # Filter controls
            cf1, cf2, cf3 = st.columns(3)
            with cf1: min_score  = st.slider("ניקוד מינימום", 0, 10, 0)
            with cf2: sort_by    = st.selectbox("מיין לפי", ["ניקוד", "RSI (הנמוך ביותר)", "% הצלחה (בק-טסט)"])
            with cf3: fresh_only = st.checkbox("סיגנלים טריים בלבד", value=False)

            filtered = [r for r in results if r.get('score', 0) >= min_score]
            if fresh_only:
                filtered = [r for r in filtered if r.get('signal_fresh', False)]

            st.caption(f"🔍 עברו סריקה: {len(results)} מניות | מוצגות: {len(filtered)}")

            if sort_by == "RSI (הנמוך ביותר)":
                filtered.sort(key=lambda x: x.get('rsi', 100))
            elif sort_by == "% הצלחה (בק-טסט)" and bt_data:
                ps = bt_data.get('per_stock', {})
                filtered.sort(key=lambda x: ps.get(x['ticker'], {}).get('win_rate', 0), reverse=True)

            st.markdown(f"### 🎯 {len(filtered)} הזדמנויות")

            t1, t2, t3, t4 = st.tabs(["📋 מניות", "📈 גרפים", "📰 חדשות", "📊 בק-טסט"])

            with t1:
                if not filtered:
                    st.info("אין מניות להצגה עם הפילטרים הנוכחיים.")
                for stock in filtered:
                    bts = bt_data.get('per_stock', {}).get(stock['ticker']) if bt_data else None
                    render_stock_card_il(stock, bts)

            with t2:
                if filtered:
                    options = [r['ticker'].replace('.TA','') + " — " + r.get('name', '')[:30]
                               for r in filtered[:30]]
                    sel_idx = st.selectbox("בחר מניה לגרף", range(len(options)),
                                           format_func=lambda i: options[i])
                    if filtered:
                        render_chart_il(filtered[sel_idx]['ticker'], params)
                else:
                    st.info("אין מניות להצגה.")

            with t3:
                if filtered:
                    opts = [r['ticker'].replace('.TA','') + " — " + r.get('name','')[:25]
                            for r in filtered[:30]]
                    sn_idx = st.selectbox("חדשות עבור", range(len(opts)),
                                          format_func=lambda i: opts[i], key="ns_il")
                    if filtered:
                        ticker_for_news = filtered[sn_idx]['ticker']
                        with st.spinner("טוען חדשות..."):
                            news = fetch_news_il(ticker_for_news)
                        if news:
                            for item in news:
                                st.markdown(
                                    f'<div class="news-item">'
                                    f'<a href="{item.get("url","#")}" target="_blank" class="news-title">'
                                    f'{item.get("title","")}</a>'
                                    f'<div class="news-meta">'
                                    f'{item.get("publisher","")} · {item.get("published","")}'
                                    f'</div></div>', unsafe_allow_html=True)
                        else:
                            st.info("לא נמצאו חדשות למניה זו.")

                        st.markdown("---")
                        render_market_news()
                else:
                    render_market_news()

            with t4:
                if bt_data:
                    render_backtest_panel_il(bt_data)
                else:
                    st.info("לחץ **שלב 2 — בק-טסט** בסרגל הצד לאחר הסריקה.")

    else:
        # Welcome screen
        st.markdown("""
        <div style="text-align:center;padding:5rem 2rem;color:#3d4f6b;">
          <div style="font-size:3.5rem;margin-bottom:1rem;">🇮🇱</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:1.15rem;color:#5a7099;">
            לחץ <strong style="color:#00e5c0;">שלב 1 — סרוק עכשיו</strong> להתחלה
          </div>
          <div style="font-size:0.85rem;margin-top:0.6rem;color:#3d4f6b;">
            סורק מניות בורסת ת"א לפי שיטת ג'ון מרפי<br>
            מסנן oversold בתוך מגמת עלייה · ממוצעים נעים · RSI · בולינגר · MACD
          </div>
          <div style="margin-top:2rem;display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;">
            <div style="text-align:center;">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:1.5rem;color:#00e5c0;">{}</div>
              <div style="font-size:0.72rem;color:#3d4f6b;">מניות ביקום</div>
            </div>
            <div style="text-align:center;">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:1.5rem;color:#60a5fa;">₪</div>
              <div style="font-size:0.72rem;color:#3d4f6b;">שקל ישראלי</div>
            </div>
            <div style="text-align:center;">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:1.5rem;color:#a78bfa;">ת"א 125</div>
              <div style="font-size:0.72rem;color:#3d4f6b;">מדד ייחוס</div>
            </div>
          </div>
        </div>
        """.format(len(STOCK_UNIVERSE_IL)), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
