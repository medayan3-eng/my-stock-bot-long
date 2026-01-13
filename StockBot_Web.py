import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# ⚙️ הגדרות: מניות וסקטורים
# ==========================================
st.set_page_config(page_title="StockBot Strategic AI", layout="wide", page_icon="🧠")

# תאריכי דוחות (מתעדכן ידנית)
EARNINGS_CALENDAR = {
    'NVDA': '21/02/2026', 'PLTR': '05/02/2026', 'CRWD': '04/03/2026',
    'PANW': '20/02/2026', 'ZS': '27/02/2026', 'SNOW': '28/02/2026',
    'MSFT': '23/04/2026', 'GOOGL': '23/04/2026', 'AMZN': '25/04/2026',
    'TSLA': '21/04/2026', 'META': '24/04/2026', 'AAPL': '01/05/2026',
    'ARM': '07/02/2026', 'SMCI': '29/01/2026', 'AMD': '30/01/2026',
    'IONQ': '27/03/2026', 'RKLB': '26/02/2026', 'VRT': '21/02/2026'
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

# רשימת ה-IPO
IPO_DATA = [
    {"Company": "SpaceX", "Valuation": "$250B", "Sector": "Space", "Status": "Rumored 2025", "Hype": "🔥🔥🔥🔥🔥"},
    {"Company": "OpenAI", "Valuation": "$100B+", "Sector": "AI", "Status": "Unlikely Soon", "Hype": "🔥🔥🔥🔥🔥"},
    {"Company": "Databricks", "Valuation": "$43B", "Sector": "Data", "Status": "Expected 2025", "Hype": "🔥🔥🔥🔥"},
    {"Company": "Stripe", "Valuation": "$65B", "Sector": "Fintech", "Status": "Expected 2025", "Hype": "🔥🔥🔥🔥"},
]

# ==========================================
# 🧠 המנוע
# ==========================================
@st.cache_data(ttl=3600)
def get_stock_data(tickers):
    data = []
    progress_bar = st.progress(0)
    status = st.empty()
    
    for i, ticker in enumerate(tickers):
        progress_bar.progress((i + 1) / len(tickers))
        status.text(f"Analyzing: {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            if len(df) < 50: continue

            # Technicals
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            df['SMA_200'] = df['Close'].rolling(window=200).mean()
            price = df['Close'].iloc[-1]

            # RSI (EMA)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            rsi_val = 100 - (100 / (1 + rs)).iloc[-1]

            # Support
            support = df['Low'].tail(60).min()
            dist_support = ((price - support) / price) * 100

            # --- Analyst Data Merged ---
            info = stock.info
            target_price = info.get('targetMeanPrice', price)
            recommendation = info.get('recommendationKey', 'hold').upper().replace('_', ' ')
            
            upside_pct = 0
            if target_price:
                upside_pct = ((target_price - price) / price) * 100

            # בניית הסטרינג המאוחד (כמו בתמונה)
            arrow = "▲" if upside_pct > 0 else "▼"
            target_str = f"${target_price:.2f}" if target_price else "N/A"
            # הפורמט: RATING | ▲ 15% (Target: $100)
            analyst_outlook = f"{recommendation} | {arrow} {upside_pct:.1f}% (Target: {target_str})"

            earnings_date = EARNINGS_CALENDAR.get(ticker, "TBD")

            # Scoring
            score = 0
            sma200 = df['SMA_200'].iloc[-1]
            if not pd.isna(sma200) and price > sma200: score += 20
            if 30 <= rsi_val <= 60: score += 15
            elif rsi_val < 30: score += 25
            if upside_pct > 15: score += 20
            if dist_support < 5: score += 15
            if recommendation in ['STRONG BUY', 'BUY']: score += 10

            verdict = "WAIT"
            if score >= 70: verdict = "💎 STRONG BUY"
            elif score >= 50: verdict = "🟢 BUY"
            elif score <= 20: verdict = "🔴 SELL"

            data.append({
                "Ticker": ticker,
                "Price": price,
                "Score": score,
                "Verdict": verdict,
                "Analyst Outlook": analyst_outlook, # העמודה החדשה
                "Upside_Num": upside_pct, # נשמר למספרים בשביל המיון והגרף
                "Earnings Date": earnings_date,
                "RSI": rsi_val,
                "Dist_Support %": dist_support,
                "History": df
            })

        except: continue
            
    progress_bar.empty()
    status.empty()
    return pd.DataFrame(data)

# ==========================================
# 🖥️ התצוגה
# ==========================================
st.title("🧠 StockBot Strategic (V10)")

if st.button("🚀 RUN SCAN"):
    with st.spinner('Calculating...'):
        df_results = get_stock_data(STOCKS)
        
        snipers = df_results[df_results['Dist_Support %'] < 3]
        if not snipers.empty:
            targets = ", ".join(snipers['Ticker'].tolist())
            st.success(f"🎯 SNIPER ALERT (Near Support): {targets}")

        tab1, tab2, tab3 = st.tabs(["📋 Strategic Board", "🗺️ Upside Map", "📈 Charts"])

        # --- Tab 1 ---
        with tab1:
            st.markdown("### Analyst Forecasts & Earnings")
            
            def style_dataframe(row):
                styles = [''] * len(row)
                # צבע לרקע של ה-Verdict
                if 'STRONG' in row['Verdict']: 
                    styles[2] = 'background-color: #d4edda; color: black; font-weight: bold'
                elif 'SELL' in row['Verdict']: 
                    styles[2] = 'background-color: #f8d7da; color: black'
                
                # צבע לטקסט של האנליסטים (Analyst Outlook)
                outlook = row['Analyst Outlook']
                if 'STRONG BUY' in outlook or 'BUY' in outlook:
                    if '▲' in outlook:
                        styles[3] = 'color: green; font-weight: bold' # ירוק בוהק
                elif 'SELL' in outlook or '▼' in outlook:
                     styles[3] = 'color: red'
                
                return styles

            # הצגת הטבלה הנקייה
            st.dataframe(
                df_results[['Ticker', 'Price', 'Verdict', 'Analyst Outlook', 'Earnings Date', 'Dist_Support %']]
                .style.apply(style_dataframe, axis=1)
                .format({"Price": "${:.2f}", "Dist_Support %": "{:.1f}%"}),
                use_container_width=True,
                height=700
            )

        # --- Tab 2 ---
        with tab2:
            fig = px.scatter(
                df_results, x="RSI", y="Upside_Num",
                color="Verdict", size="Score",
                hover_data=["Ticker", "Analyst Outlook"],
                text="Ticker",
                color_discrete_map={"💎 STRONG BUY": "green", "🟢 BUY": "lightgreen", "WAIT": "gold", "🔴 SELL": "red"},
                title="Risk (RSI) vs. Reward (Upside)"
            )
            fig.add_hline(y=15, line_dash="dash", line_color="green")
            fig.add_vline(x=40, line_dash="dash", line_color="blue")
            st.plotly_chart(fig, use_container_width=True)

        # --- Tab 3 ---
        with tab3:
            top = df_results[df_results['Score'] >= 50].sort_values('Score', ascending=False)
            for i, row in top.iterrows():
                with st.expander(f"{row['Ticker']} | {row['Analyst Outlook']}"):
                    hist = row['History']
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Price', line=dict(color='blue')))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_200'], name='SMA 200', line=dict(color='black')))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_50'], name='SMA 50', line=dict(color='orange', dash='dash')))
                    st.plotly_chart(fig, use_container_width=True)
