import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ==========================================
# ⚙️ הגדרות: רשימת המעקב
# ==========================================
st.set_page_config(page_title="StockBot Precision AI", layout="wide", page_icon="🎯")

# רשימת המעקב (ללא כפילויות)
STOCKS = list(set([
    # --- 1. Storage & Memory (כמו WDC שהתפוצצה) ---
    'WDC',  # Western Digital (הבעלים של SanDisk) - זיכרון
    'MU',   # Micron - הזיכרון המהיר שחייבים ל-AI
    'STX',  # Seagate - כוננים קשיחים לחוות שרתים
    'PSTG', # Pure Storage - אחסון מהיר מאוד
    
    # --- 2. AI Infrastructure & Cooling (הצוואר בקבוק הבא) ---
    'VRT',  # Vertiv - קירור לשרתים (חובה!)
    'ETN',  # Eaton - ניהול חשמל לדאטה סנטר
    'MOD',  # Modine - מערכות קירור תעשייתיות
    'ANET', # Arista Networks - תקשורת מהירה בין מחשבים

    # --- 3. Energy & Nuclear (חשמל ל-AI) ---
    'OKLO', 'SMR', 'NNE', 'CCJ', 'BWXT', 'VST', 'GEV', 'CEG', 'TLN',
    
    # --- 4. Quantum & Future Tech ---
    'IONQ', 'RGTI', 'QBTS', 'QUBT', 'IBM',
    
    # --- 5. Space & Defense ---
    'RKLB', 'ASTS', 'LUNR', 'SPCE', 'KTOS', 'AVAV', 'RTX', 'LMT', 'AXON',
    
    # --- 6. Cyber Security (התקפות AI) ---
    'PANW', 'CRWD', 'ZS', 'NET', 'TENB', 'S',

    # --- 7. Giants & Software ---
    'NVDA', 'AMD', 'AVGO', 'ARM', 'TSM', 'SMCI', 'PLTR',
    'MSFT', 'GOOGL', 'AMZN', 'META', 'AAPL', 'TSLA', 'NOW', 'CRM', 'DELL',
    
    # --- 8. Bio-Tech (Gene Editing 2026) ---
    'CRSP', 'VRTX', 'LLY', 'NVO', 'BEAM', 'NTLA',
    
    # --- 9. Crypto & Fintech ---
    'MSTR', 'COIN', 'HOOD', 'SQ', 'FI',
    
    # --- 10. Israeli Tech ---
    'CAMT', 'NVMI', 'CYBR', 'WIX', 'INNO', 'MNDY'
]))

ETFS = {'QTUM': 'Quantum ETF', 'URA': 'Uranium ETF', 'ITA': 'Defense ETF', 'SMH': 'Semi ETF'}
ALL_TICKERS = STOCKS + list(ETFS.keys())

# רשימת ה-10 המעניינות להנפקה (IPO)
IPO_DATA = [
    {"Company": "SpaceX", "Valuation": "$200B+", "Sector": "Space", "Status": "Rumored 2025/26", "Interest": "🔥🔥🔥🔥🔥"},
    {"Company": "OpenAI", "Valuation": "$100B+", "Sector": "AI", "Status": "Unlikely Soon", "Interest": "🔥🔥🔥🔥🔥"},
    {"Company": "Starlink", "Valuation": "$100B", "Sector": "Space/Telecom", "Status": "Spin-off Rumored", "Interest": "🔥🔥🔥🔥🔥"},
    {"Company": "Databricks", "Valuation": "$43B", "Sector": "Data AI", "Status": "Expected 2025", "Interest": "🔥🔥🔥🔥"},
    {"Company": "Stripe", "Valuation": "$65B", "Sector": "Fintech", "Status": "Expected 2025", "Interest": "🔥🔥🔥🔥"},
    {"Company": "Canva", "Valuation": "$26B", "Sector": "Design", "Status": "Expected 2025", "Interest": "🔥🔥🔥"},
    {"Company": "Revolut", "Valuation": "$45B", "Sector": "Fintech", "Status": "Expected 2025", "Interest": "🔥🔥🔥"},
    {"Company": "Shein", "Valuation": "$60B", "Sector": "E-Commerce", "Status": "Filing Process", "Interest": "🔥🔥🔥"},
    {"Company": "Discord", "Valuation": "$15B", "Sector": "Social", "Status": "Rumored", "Interest": "🔥🔥"},
    {"Company": "Boston Dynamics", "Valuation": "$10B", "Sector": "Robotics", "Status": "Hyunadi might list", "Interest": "🔥🔥"},
]

# ==========================================
# 🧠 המנוע המדויק (Corrected Math)
# ==========================================
@st.cache_data(ttl=3600)
def get_stock_data(tickers):
    data = []
    progress_bar = st.progress(0)
    status = st.empty()
    
    for i, ticker in enumerate(tickers):
        progress_bar.progress((i + 1) / len(tickers))
        status.text(f"Calibrating Data: {ticker}...")
        
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="2y")
            if len(df) < 200: continue

            # --- Technicals (תיקון נוסחאות) ---
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            df['SMA_200'] = df['Close'].rolling(window=200).mean()
            
            # RSI מתוקן (EMA במקום SMA - תואם לאפליקציות)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            df['BB_Upper'] = df['Close'].rolling(window=20).mean() + (df['Close'].rolling(window=20).std() * 2)
            df['BB_Lower'] = df['Close'].rolling(window=20).mean() - (df['Close'].rolling(window=20).std() * 2)

            # --- Fundamentals (תיקון P/E) ---
            info = stock.info
            price = df['Close'].iloc[-1]
            
            # Upside Calculation
            target = info.get('targetMeanPrice', price)
            if target is None: target = price
            upside = ((target - price) / price) * 100
            
            # P/E Selection: מעדיפים Trailing כדי להתאים לאפליקציות
            pe_ratio = info.get('trailingPE')
            if pe_ratio is None:
                pe_ratio = info.get('forwardPE') # גיבוי אם אין נתון עבר
            
            pe_display = f"{pe_ratio:.2f}" if pe_ratio else "-"

            # --- Scoring ---
            score = 0
            rsi = df['RSI'].iloc[-1]
            sma200 = df['SMA_200'].iloc[-1]
            support = df['Low'].tail(60).min()
            dist_support = ((price - support) / price) * 100

            # Trend
            if price > sma200: score += 25
            else: score -= 25
            
            # RSI Logic
            if 40 <= rsi <= 60: score += 15
            elif rsi < 35: score += 25 # Oversold
            elif rsi > 75: score -= 15 # Overbought
            
            # Support
            if dist_support < 3: score += 20
            
            # Upside
            if upside > 15: score += 15

            # Verdict
            verdict = "WAIT"
            if score >= 70: verdict = "💎 STRONG BUY"
            elif score >= 50: verdict = "🟢 BUY"
            elif score <= 10: verdict = "🔴 SELL"

            data.append({
                "Ticker": ticker,
                "Price": price,
                "Score": score,
                "Verdict": verdict,
                "RSI": rsi,
                "Upside %": upside,
                "Dist_Support %": dist_support,
                "P/E Ratio": pe_display,
                "SMA_50": df['SMA_50'].iloc[-1], # שומרים לגרף
                "SMA_200": sma200,
                "History": df
            })

        except: continue
            
    progress_bar.empty()
    status.empty()
    return pd.DataFrame(data)

# ==========================================
# 🖥️ ממשק משתמש (UI)
# ==========================================
st.title("🎯 StockBot Precision Dashboard")
st.markdown("### Verified Data & Analysis (V8)")

if st.button("🚀 RUN PRECISION SCAN"):
    with st.spinner('Fetching Real-Time Data...'):
        df_results = get_stock_data(ALL_TICKERS)
        
        strong_buys = df_results[df_results['Verdict'] == "💎 STRONG BUY"]
        snipers = df_results[df_results['Dist_Support %'] < 3]

        col1, col2, col3 = st.columns(3)
        col1.metric("Strong Buys", len(strong_buys))
        col2.metric("Sniper Alerts", len(snipers))
        col3.metric("Total Scanned", len(df_results))
        
        if not snipers.empty:
            st.success(f"🎯 SNIPER ALERT: {', '.join(snipers['Ticker'].tolist())} are near support!")

        tab1, tab2, tab3, tab4 = st.tabs(["📋 Live Data", "🗺️ Smart Map", "🦄 Top 10 IPOs", "📈 Technical Charts"])

        # --- Tab 1: Live Data ---
        with tab1:
            def highlight(val):
                if 'STRONG BUY' in val: return 'background-color: #d4edda; color: black; font-weight: bold'
                if 'SELL' in val: return 'background-color: #f8d7da; color: black'
                return ''

            st.dataframe(
                df_results[['Ticker', 'Price', 'Verdict', 'RSI', 'Upside %', 'Dist_Support %', 'P/E Ratio']]
                .style.map(highlight, subset=['Verdict'])
                .format({"Price": "${:.2f}", "Upside %": "{:.1f}%", "Dist_Support %": "{:.1f}%", "RSI": "{:.1f}"}),
                use_container_width=True, height=600
            )

        # --- Tab 2: Clean Map ---
        with tab2:
            st.markdown("### 🗺️ Risk vs. Reward (Filtered View)")
            
            # פילטר לניקיון המפה
            st.caption("Adjust the slider to filter out 'boring' stocks:")
            min_score = st.slider("Show Stocks with Score above:", 0, 100, 40)
            
            map_data = df_results[df_results['Score'] >= min_score].copy()
            map_data['Bubble_Size'] = map_data['Score'].apply(lambda x: max(x, 15)) # גודל מינימלי

            fig_map = px.scatter(
                map_data, x="RSI", y="Upside %", 
                color="Score", 
                size="Bubble_Size", 
                hover_data=["Ticker", "Price", "Verdict"], text="Ticker",
                color_continuous_scale="RdYlGn", 
                title=f"Market Map ({len(map_data)} Assets Shown)",
                height=650
            )
            
            # קווי עזר ברורים
            fig_map.add_vline(x=40, line_dash="dot", line_color="blue", annotation_text="Oversold")
            fig_map.add_hline(y=20, line_dash="dot", line_color="green", annotation_text="Upside Target")
            fig_map.add_shape(type="rect", x0=10, y0=20, x1=45, y1=map_data['Upside %'].max()*1.1, 
                             line=dict(color="Green"), fillcolor="Green", opacity=0.1)
            
            st.plotly_chart(fig_map, use_container_width=True)

        # --- Tab 3: IPOs ---
        with tab3:
            st.markdown("### 🦄 Top 10 Hottest Private Companies")
            st.dataframe(pd.DataFrame(IPO_DATA), use_container_width=True)

        # --- Tab 4: Charts ---
        with tab4:
            candidates = df_results[df_results['Score'] >= 50].sort_values(by='Score', ascending=False)
            
            if candidates.empty:
                st.warning("No high-quality setups found right now.")
            else:
                for index, row in candidates.iterrows():
                    with st.expander(f"{row['Verdict']} | {row['Ticker']}", expanded=True):
                        hist = row['History']
                        fig = go.Figure()
                        
                        # מחיר
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Price', line=dict(color='blue', width=2)))
                        # SMA 50 (הוסף לבקשתך)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_50'], name='SMA 50 (Mid-Term)', line=dict(color='orange', width=1.5, dash='dash')))
                        # SMA 200
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA_200'], name='SMA 200 (Long-Term)', line=dict(color='black', width=2)))
                        # רצועות
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['BB_Upper'], name='Bollinger', line=dict(color='gray', width=0.5), showlegend=False))
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['BB_Lower'], name='Bollinger', line=dict(color='gray', width=0.5), fill='tonexty', showlegend=False))
                        
                        fig.update_layout(title=f"{row['Ticker']} Technical Analysis", height=450, margin=dict(t=30, b=0, l=0, r=0))
                        st.plotly_chart(fig, use_container_width=True)
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("RSI (14D EMA)", f"{row['RSI']:.1f}")
                        c2.metric("P/E Ratio", row['P/E Ratio'])
                        c3.metric("Upside Potential", f"{row['Upside %']:.1f}%")
                        c4.metric("Dist to Support", f"{row['Dist_Support %']:.1f}%")

else:

    st.info("System Calibrated. Click START to run precision scan.")
