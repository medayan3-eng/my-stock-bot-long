import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ==========================================
# ⚙️ הגדרות: מניות, דוחות וסקטורים
# ==========================================
st.set_page_config(page_title="StockBot Strategic AI", layout="wide", page_icon="🧠")

# 1. מסד נתונים לתאריכי דוחות (מתעדכן ידנית)
# פורמט: 'TICKER': 'DD/MM/YYYY'
EARNINGS_CALENDAR = {
    'NVDA': '21/02/2026', 'PLTR': '05/02/2026', 'CRWD': '04/03/2026',
    'PANW': '20/02/2026', 'ZS': '27/02/2026', 'SNOW': '28/02/2026',
    'MSFT': '23/04/2026', 'GOOGL': '23/04/2026', 'AMZN': '25/04/2026',
    'TSLA': '21/04/2026', 'META': '24/04/2026', 'AAPL': '01/05/2026',
    'ARM': '07/02/2026', 'SMCI': '29/01/2026', 'AMD': '30/01/2026',
    'IONQ': '27/03/2026', 'RKLB': '26/02/2026', 'VRT': '21/02/2026'
}

# 2. רשימת ה-30+ החדשות והקיימות (ממוינות לסקטורים)
STOCKS = list(set([
    # --- ☢️ Nuclear & Clean Energy (הטרנד של 2026) ---
    'CCJ', 'LEU', 'BWXT', 'OKLO', 'SMR', 'NNE', # קיימים
    'CEG', 'TLN', 'VST', 'PEG', # חברות חשמל שמספקות ל-Data Centers
    'URA', 'NLR', 'UEC', 'NXE', # כריית אורניום
    'FSLR', 'ENPH', 'NEE', # אנרגיה סולארית ומתחדשת

    # --- ❄️ AI Cooling & Infrastructure (הצוואר בקבוק) ---
    'VRT', 'ETN', 'MOD', 'GLW', # קירור וכבלים לחוות שרתים (חם מאוד!)
    'ANET', 'PSTG', 'STX', 'WDC', # אחסון ותקשורת

    # --- 🧠 AI Chips & Compute ---
    'NVDA', 'AMD', 'AVGO', 'ARM', 'TSM', 'SMCI', 'MU', 
    'GFS', 'ON', 'MRVL', 'INTC',

    # --- ⚛️ Quantum Computing ---
    'IONQ', 'RGTI', 'QBTS', 'QUBT', 'IBM', 'GOOGL', 'MSFT',
    'HON', # Honeywell (שחקנית קוונטום חזקה)

    # --- 🛡️ Cyber & Software ---
    'PANW', 'CRWD', 'ZS', 'NET', 'PLTR', 
    'FTNT', 'TENB', 'DT', 'SNOW', 'DDOG', 'MNDY', 'CYBR',

    # --- 🚀 Space & Defense ---
    'RKLB', 'ASTS', 'LUNR', 'SPCE', 'JOBY', 'ACHR',
    'KTOS', 'AVAV', 'RTX', 'LMT', 'AXON', 'BA',

    # --- 🧬 Biotech (Gene Editing) ---
    'CRSP', 'VRTX', 'LLY', 'NVO', 'BEAM', 'NTLA',

    # --- 💰 Crypto & Fintech ---
    'MSTR', 'COIN', 'HOOD', 'SQ', 'FI', 'PYPL'
]))

# רשימת ה-IPO (ללא שינוי)
IPO_DATA = [
    {"Company": "SpaceX", "Valuation": "$250B", "Sector": "Space", "Status": "Rumored 2025", "Hype": "🔥🔥🔥🔥🔥"},
    {"Company": "OpenAI", "Valuation": "$100B+", "Sector": "AI", "Status": "Unlikely Soon", "Hype": "🔥🔥🔥🔥🔥"},
    {"Company": "Databricks", "Valuation": "$43B", "Sector": "Data", "Status": "Expected 2025", "Hype": "🔥🔥🔥🔥"},
    {"Company": "Stripe", "Valuation": "$65B", "Sector": "Fintech", "Status": "Expected 2025", "Hype": "🔥🔥🔥🔥"},
    {"Company": "Discord", "Valuation": "$15B", "Sector": "Social", "Status": "Rumored", "Hype": "🔥🔥"},
]

# ==========================================
# 🧠 המנוע: אנליסטים + טכני
# ==========================================
@st.cache_data(ttl=3600)
def get_stock_data(tickers):
    data = []
    progress_bar = st.progress(0)
    status = st.empty()
    
    for i, ticker in enumerate(tickers):
        progress_bar.progress((i + 1) / len(tickers))
        status.text(f"Analyzing Analysts & Charts: {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y") # מספיק שנה לניתוח שוטף
            if len(df) < 50: continue

            # --- Technicals ---
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

            # --- Analyst Data (החלק החדש) ---
            info = stock.info
            target_price = info.get('targetMeanPrice', price)
            recommendation = info.get('recommendationKey', 'hold').upper().replace('_', ' ')
            
            # חישוב Upside
            upside_pct = 0
            if target_price:
                upside_pct = ((target_price - price) / price) * 100

            # עיצוב הטקסט (כמו בתמונה שביקשת)
            # ירוק לעלייה, אדום לירידה
            target_display = f"${target_price:.2f}" if target_price else "N/A"
            
            # תאריך דוח הבא
            earnings_date = EARNINGS_CALENDAR.get(ticker, "TBD")

            # --- Scoring ---
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
                "Analyst Rating": recommendation, # BUY / HOLD / SELL
                "Target Price": target_display,
                "Upside %": upside_pct, # מספר נקי למיון
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
# 🖥️ התצוגה (Dashboard)
# ==========================================
st.title("🧠 StockBot Strategic (V9)")
st.caption("Includes: Analyst Targets, Earnings Dates & New AI Sectors")

if st.button("🚀 RUN STRATEGIC SCAN"):
    with st.spinner('Gathering Intelligence...'):
        df_results = get_stock_data(STOCKS)
        
        # מדדים עליונים
        strong = len(df_results[df_results['Verdict'] == "💎 STRONG BUY"])
        snipers = len(df_results[df_results['Dist_Support %'] < 3])
        avg_upside = df_results['Upside %'].mean()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Strong Buys", strong)
        c2.metric("Sniper Alerts", snipers)
        c3.metric("Avg Market Upside", f"{avg_upside:.1f}%")
        c4.metric("Total Stocks", len(df_results))

        if snipers > 0:
            targets = df_results[df_results['Dist_Support %'] < 3]['Ticker'].tolist()
            st.success(f"🎯 SNIPER ALERT (Near Support): {', '.join(targets)}")

        tab1, tab2, tab3, tab4 = st.tabs(["📋 Strategic Board", "🗺️ Upside Map", "🦄 IPOs", "📈 Charts"])

        # --- Tab 1: הטבלה האסטרטגית ---
        with tab1:
            st.markdown("### Analyst Forecasts & Earnings")
            
            # פונקציות צבע
            def color_verdict(v):
                if 'STRONG' in v: return 'background-color: #d4edda; color: black; font-weight: bold'
                if 'SELL' in v: return 'background-color: #f8d7da; color: black'
                return ''

            def color_upside(v):
                if v > 15: return 'color: green; font-weight: bold'
                if v < 0: return 'color: red'
                return 'color: black'

            # עיצוב הטבלה
            st.dataframe(
                df_results[['Ticker', 'Price', 'Verdict', 'Analyst Rating', 'Upside %', 'Target Price', 'Earnings Date', 'Dist_Support %']]
                .style.map(color_verdict, subset=['Verdict'])
                .map(color_upside, subset=['Upside %'])
                .format({
                    "Price": "${:.2f}", 
                    "Upside %": "{:.1f}%", 
                    "Dist_Support %": "{:.1f}%"
                }),
                use_container_width=True,
                height=700
            )

        # --- Tab 2: מפת הפוטנציאל ---
        with tab2:
            st.markdown("### 🗺️ Risk vs. Analyst Upside")
            fig = px.scatter(
                df_results, x="RSI", y="Upside %",
                color="Verdict", size="Score",
                hover_data=["Ticker", "Target Price", "Earnings Date"],
                text="Ticker",
                color_discrete_map={"💎 STRONG BUY": "green", "🟢 BUY": "lightgreen", "WAIT": "gold", "🔴 SELL": "red"},
                title="Top Left = Best Opportunities (Cheap + High Upside)"
            )
            fig.add_hline(y=15, line_dash="dash", line_color="green", annotation_text="High Upside Area")
            fig.add_vline(x=40, line_dash="dash", line_color="blue", annotation_text="Oversold Area")
            st.plotly_chart(fig, use_container_width=True)

        # --- Tab 3: IPOs ---
        with tab3:
            st.dataframe(pd.DataFrame(IPO_DATA), use_container_width=True)

        # --- Tab 4: גרפים ---
        with tab4:
            top_picks = df_results[df_results['Score'] >= 50].sort_values('Score', ascending=False)
            if top_picks.empty:
                st.info("No top picks currently.")
            else:
                for i, row in top_picks.iterrows():
                    with st.expander(f"{row['Ticker']} | Upside: {row['Upside %']:.1f}% | Report: {row['Earnings Date']}"):
                        hist = row['History']
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Price', line=dict(color='blue')))
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_200'], name='SMA 200', line=dict(color='black')))
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_50'], name='SMA 50', line=dict(color='orange', dash='dash')))
                        
                        st.plotly_chart(fig, use_container_width=True)
                        st.write(f"**Analyst Verdict:** {row['Analyst Rating']} -> Target: {row['Target Price']}")

else:
    st.info("System Ready. Database Updated with 2026 AI & Nuclear Stocks.")
