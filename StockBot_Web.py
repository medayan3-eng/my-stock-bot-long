import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time

# ==========================================
# ⚙️ הגדרות
# ==========================================
st.set_page_config(page_title="StockBot Pro V13", layout="wide", page_icon="💎")

# תאריכי דוחות (ידני)
EARNINGS_CALENDAR = {
    'NVDA': '21/02/2026', 'PLTR': '05/02/2026', 'CRWD': '04/03/2026',
    'PANW': '20/02/2026', 'ZS': '27/02/2026', 'SNOW': '28/02/2026',
    'MSFT': '23/04/2026', 'GOOGL': '23/04/2026', 'AMZN': '25/04/2026',
    'TSLA': '21/04/2026', 'META': '24/04/2026', 'AAPL': '01/05/2026'
}

# רשימת המניות
STOCKS = list(set([
    'CCJ', 'LEU', 'BWXT', 'OKLO', 'SMR', 'NNE', 'CEG', 'TLN', 'VST', 'PEG',
    'URA', 'NLR', 'UEC', 'NXE', 'FSLR', 'ENPH', 'NEE',
    'VRT', 'ETN', 'MOD', 'GLW', 'ANET', 'PSTG', 'STX', 'WDC',
    'NVDA', 'AMD', 'AVGO', 'ARM', 'TSM', 'SMCI', 'MU', 'GFS', 'ON', 'MRVL', 'INTC',
    'IONQ', 'RGTI', 'QBTS', 'QUBT', 'IBM', 'GOOGL', 'MSFT', 'HON',
    'PANW', 'CRWD', 'ZS', 'NET', 'PLTR', 'FTNT', 'TENB', 'DT', 'SNOW', 'DDOG', 'MNDY', 'CYBR',
    'RKLB', 'ASTS', 'LUNR', 'SPCE', 'JOBY', 'ACHR', 'KTOS', 'AVAV', 'RTX', 'LMT', 'AXON', 'BA',
    'CRSP', 'VRTX', 'LLY', 'NVO', 'BEAM', 'NTLA',
    'MSTR', 'COIN', 'HOOD', 'SQ', 'FI', 'PYPL',
    'WIX', 'INNO', 'CAMT', 'NVMI'
]))

# ==========================================
# 🧠 המנוע החכם (עם סינון איכות)
# ==========================================
# תיקון 1: הורדנו את הזיכרון ל-0. כל רענון יביא נתונים חדשים!
@st.cache_data(ttl=0) 
def get_stock_data(tickers):
    data = []
    progress_bar = st.progress(0)
    status = st.empty()
    
    for i, ticker in enumerate(tickers):
        progress_bar.progress((i + 1) / len(tickers))
        status.text(f"Analyzing Fundamentals & Technicals: {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            # טכני
            df = stock.history(period="1y")
            if len(df) < 50: continue

            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            df['SMA_200'] = df['Close'].rolling(window=200).mean()
            price = df['Close'].iloc[-1]

            # RSI (EMA)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]

            # Support
            support = df['Low'].tail(60).min()
            dist_support = ((price - support) / price) * 100

            # --- Fundamentals & Quality Check (החלק החדש!) ---
            info = stock.info
            
            # 1. רווחיות (Profit Margins)
            margins = info.get('profitMargins', 0) 
            # 2. צמיחה (Revenue Growth)
            growth = info.get('revenueGrowth', 0)
            
            target_price = info.get('targetMeanPrice', price)
            recommendation = info.get('recommendationKey', 'hold').upper().replace('_', ' ')
            
            upside_pct = 0
            if target_price:
                upside_pct = ((target_price - price) / price) * 100

            # עיצוב טקסט לאנליסטים
            arrow = "▲" if upside_pct > 0 else "▼"
            target_str = f"${target_price:.2f}" if target_price else "N/A"
            analyst_outlook = f"{recommendation} | {arrow} {upside_pct:.1f}% (Target: {target_str})"

            earnings_date = EARNINGS_CALENDAR.get(ticker, "TBD")

            # --- Scoring System V2 (המחמיר) ---
            score = 0
            sma200 = df['SMA_200'].iloc[-1]

            # 1. טכני (בסיס)
            if not pd.isna(sma200) and price > sma200: score += 20 # מגמה חיובית
            else: score -= 10 # עונש על מגמה שלילית

            # 2. RSI (הזדמנות)
            if 30 <= rsi_val <= 60: score += 15
            elif rsi_val < 30: score += 20 # זול, אבל...
            
            # 3. פילטר איכות (הגנה מסכין נופלת) 🛡️
            if margins and margins > 0.10: score += 15 # חברה רווחית מאוד (+10%)
            elif margins and margins < 0: score -= 20 # חברה מפסידה כסף! עונש כבד!
            
            if growth and growth > 0.10: score += 10 # צומחת מעל 10%
            elif growth and growth < 0: score -= 15 # הכנסות מתכווצות!

            # 4. אנליסטים ורצפה
            if upside_pct > 15: score += 15
            if dist_support < 5: score += 15

            # Verdict (פסק דין)
            verdict = "WAIT"
            if score >= 75: verdict = "💎 STRONG BUY" # העלינו את הרף
            elif score >= 55: verdict = "🟢 BUY"
            elif score <= 20: verdict = "🔴 SELL"

            data.append({
                "Ticker": ticker,
                "Price": price,
                "Score": score,
                "Verdict": verdict,
                "Analyst Outlook": analyst_outlook,
                "Margins": f"{margins*100:.1f}%" if margins else "N/A", # להצגה
                "Growth": f"{growth*100:.1f}%" if growth else "N/A",   # להצגה
                "Earnings Date": earnings_date,
                "Dist_Support %": dist_support,
                "RSI": rsi_val,
                "History": df
            })

        except: continue
            
    progress_bar.empty()
    status.empty()
    return pd.DataFrame(data)

# ==========================================
# 🖥️ התצוגה
# ==========================================
st.title("💎 StockBot Pro V13 (Real-Time & Quality Filtered)")

if st.button("🚀 SCAN LIVE MARKET"):
    with st.spinner('Analyzing Fundamentals & Technicals...'):
        df_results = get_stock_data(STOCKS)
        
        snipers = df_results[df_results['Dist_Support %'] < 3]
        if not snipers.empty:
            targets = ", ".join(snipers['Ticker'].tolist())
            st.success(f"🎯 SNIPER ALERT: {targets} are near support!")

        tab1, tab2, tab3 = st.tabs(["📋 Strategic Board", "📊 Quality Metrics", "📈 Charts"])

        # --- Tab 1: הלוח הראשי ---
        with tab1:
            def style_dataframe(row):
                styles = [''] * len(row)
                if 'STRONG' in row['Verdict']: 
                    styles[2] = 'background-color: #d4edda; color: black; font-weight: bold'
                elif 'SELL' in row['Verdict']: 
                    styles[2] = 'background-color: #f8d7da; color: black'
                return styles

            st.dataframe(
                df_results[['Ticker', 'Price', 'Verdict', 'Analyst Outlook', 'Earnings Date', 'Dist_Support %']]
                .style.apply(style_dataframe, axis=1)
                .format({"Price": "${:.2f}", "Dist_Support %": "{:.1f}%"}),
                use_container_width=True,
                height=700
            )

        # --- Tab 2: נתוני איכות (חדש!) ---
        with tab2:
            st.markdown("### 📊 Fundamental Health Check")
            st.info("Margins: Is the company profitable? | Growth: Is revenue increasing?")
            
            # צבעים לרווחיות וצמיחה
            def color_funds(val):
                if val == "N/A": return ""
                try:
                    num = float(val.strip('%'))
                    return 'color: green' if num > 0 else 'color: red'
                except: return ""

            st.dataframe(
                df_results[['Ticker', 'Verdict', 'Margins', 'Growth', 'Analyst Outlook']]
                .style.map(color_funds, subset=['Margins', 'Growth']),
                use_container_width=True
            )

        # --- Tab 3: Charts ---
        with tab3:
            top = df_results[df_results['Score'] >= 55].sort_values('Score', ascending=False)
            if top.empty:
                st.warning("No high-quality stocks found. The filter is strict!")
            else:
                for i, row in top.iterrows():
                    with st.expander(f"{row['Ticker']} | Score: {row['Score']} | Margins: {row['Margins']}"):
                        hist = row['History']
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Price', line=dict(color='blue')))
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_200'], name='SMA 200', line=dict(color='black')))
                        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("System Ready. Cache Disabled (Live Data). Quality Filters Active.")
