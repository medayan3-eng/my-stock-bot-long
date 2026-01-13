import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time

# ==========================================
# ⚙️ הגדרות: מניות וסקטורים
# ==========================================
st.set_page_config(page_title="StockBot Strategic AI", layout="wide", page_icon="🛡️")

EARNINGS_CALENDAR = {
    'NVDA': '21/02/2026', 'PLTR': '05/02/2026', 'CRWD': '04/03/2026',
    'PANW': '20/02/2026', 'ZS': '27/02/2026', 'SNOW': '28/02/2026',
    'MSFT': '23/04/2026', 'GOOGL': '23/04/2026', 'AMZN': '25/04/2026',
    'TSLA': '21/04/2026', 'META': '24/04/2026', 'AAPL': '01/05/2026',
    'ARM': '07/02/2026', 'SMCI': '29/01/2026', 'AMD': '30/01/2026',
    'IONQ': '27/03/2026', 'RKLB': '26/02/2026', 'VRT': '21/02/2026'
}

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

IPO_DATA = [
    {"Company": "SpaceX", "Valuation": "$250B", "Sector": "Space", "Status": "Rumored 2025", "Hype": "🔥🔥🔥🔥🔥"},
    {"Company": "OpenAI", "Valuation": "$100B+", "Sector": "AI", "Status": "Unlikely Soon", "Hype": "🔥🔥🔥🔥🔥"},
    {"Company": "Databricks", "Valuation": "$43B", "Sector": "Data", "Status": "Expected 2025", "Hype": "🔥🔥🔥🔥"},
    {"Company": "Stripe", "Valuation": "$65B", "Sector": "Fintech", "Status": "Expected 2025", "Hype": "🔥🔥🔥🔥"},
]

# ==========================================
# 🧠 המנוע ההיברידי (Batch Processing)
# ==========================================
@st.cache_data(ttl=900) # זיכרון ל-15 דקות
def get_stock_data(tickers):
    data = []
    status = st.empty()
    progress_bar = st.progress(0)
    
    # שלב 1: משיכה המונית של המחירים (מהיר וחסין לחסימות)
    status.text("🚀 Phase 1: Bulk Downloading Market Data...")
    try:
        # מוריד את כל ההיסטוריה במכה אחת
        batch_history = yf.download(tickers, period="1y", group_by='ticker', threads=True, progress=False)
    except Exception as e:
        st.error(f"Critical Error downloading batch data: {e}")
        return pd.DataFrame()

    total = len(tickers)
    
    # שלב 2: עיבוד וניסיון עדין למשיכת נתוני אנליסטים
    for i, ticker in enumerate(tickers):
        progress_bar.progress((i + 1) / total)
        status.text(f"Phase 2: Analyzing {ticker}...")
        
        try:
            # חילוץ הדאטה של המניה מתוך המאגר הגדול
            # yf.download מחזיר מבנה שונה אם זו מניה אחת או רבות
            if len(tickers) > 1:
                df = batch_history[ticker].copy()
            else:
                df = batch_history.copy()
            
            # ניקוי שורות ריקות (קורה לפעמים במשיכה המונית)
            df.dropna(how='all', inplace=True)
            
            if len(df) < 50: continue

            # --- Technicals (חישוב מהיר ללא אינטרנט) ---
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            df['SMA_200'] = df['Close'].rolling(window=200).mean()
            price = float(df['Close'].iloc[-1])

            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            rsi_val = 100 - (100 / (1 + rs)).iloc[-1]

            # Support
            support = df['Low'].tail(60).min()
            dist_support = ((price - support) / price) * 100

            # --- Fundamentals (החלק הרגיש) ---
            # מנסים למשוך נתוני אנליסטים. אם נכשל - לא קורסים!
            analyst_outlook = "N/A (Data Blocked)"
            target_price = None
            upside_pct = 0
            
            try:
                stock_info = yf.Ticker(ticker)
                info = stock_info.info
                
                target_price = info.get('targetMeanPrice')
                recommendation = info.get('recommendationKey', 'hold').upper().replace('_', ' ')
                
                if target_price:
                    upside_pct = ((target_price - price) / price) * 100
                    arrow = "▲" if upside_pct > 0 else "▼"
                    analyst_outlook = f"{recommendation} | {arrow} {upside_pct:.1f}% (Target: ${target_price:.2f})"
                else:
                    analyst_outlook = f"{recommendation} | Target: N/A"
            except:
                # אם נחסמנו, נשארים עם נתונים טכניים בלבד
                pass

            earnings_date = EARNINGS_CALENDAR.get(ticker, "TBD")

            # Scoring (מותאם גם אם אין אנליסטים)
            score = 0
            sma200 = df['SMA_200'].iloc[-1]
            if not pd.isna(sma200) and price > sma200: score += 25
            if 30 <= rsi_val <= 60: score += 15
            elif rsi_val < 30: score += 25
            if dist_support < 5: score += 20
            # בונוס אנליסטים רק אם הצלחנו למשוך
            if target_price and upside_pct > 15: score += 15

            verdict = "WAIT"
            if score >= 70: verdict = "💎 STRONG BUY"
            elif score >= 50: verdict = "🟢 BUY"
            elif score <= 20: verdict = "🔴 SELL"

            data.append({
                "Ticker": ticker,
                "Price": price,
                "Score": score,
                "Verdict": verdict,
                "Analyst Outlook": analyst_outlook,
                "Upside_Num": upside_pct,
                "Earnings Date": earnings_date,
                "RSI": rsi_val,
                "Dist_Support %": dist_support,
                "History": df
            })
            
        except Exception as e:
            continue

    progress_bar.empty()
    status.empty()
    
    if not data:
        return pd.DataFrame()
        
    return pd.DataFrame(data)

# ==========================================
# 🖥️ התצוגה
# ==========================================
st.title("🧠 StockBot Strategic (V12 - Hybrid)")

if st.button("🚀 RUN SMART SCAN"):
    with st.spinner('Accessing Global Market Data...'):
        df_results = get_stock_data(STOCKS)
        
        if df_results.empty:
            st.warning("⚠️ Market data unavailable. This usually resolves in 5-10 minutes. Yahoo is limiting cloud requests.")
        else:
            snipers = df_results[df_results['Dist_Support %'] < 3]
            if not snipers.empty:
                targets = ", ".join(snipers['Ticker'].tolist())
                st.success(f"🎯 SNIPER ALERT: {targets} are at support level!")

            tab1, tab2, tab3 = st.tabs(["📋 Strategic Board", "🗺️ Upside Map", "📈 Charts"])

            with tab1:
                def style_row(row):
                    styles = [''] * len(row)
                    if 'STRONG' in row['Verdict']: styles[2] = 'background-color: #d4edda; color: black; font-weight: bold'
                    elif 'SELL' in row['Verdict']: styles[2] = 'background-color: #f8d7da; color: black'
                    
                    # צבע לאנליסטים
                    outlook = str(row['Analyst Outlook'])
                    if '▲' in outlook: styles[3] = 'color: green; font-weight: bold'
                    elif '▼' in outlook: styles[3] = 'color: red'
                    return styles

                st.dataframe(
                    df_results[['Ticker', 'Price', 'Verdict', 'Analyst Outlook', 'Earnings Date', 'Dist_Support %']]
                    .style.apply(style_row, axis=1)
                    .format({"Price": "${:.2f}", "Dist_Support %": "{:.1f}%"}),
                    use_container_width=True, height=700
                )

            with tab2:
                fig = px.scatter(
                    df_results, x="RSI", y="Upside_Num",
                    color="Verdict", size="Score",
                    hover_data=["Ticker", "Analyst Outlook"], text="Ticker",
                    color_discrete_map={"💎 STRONG BUY": "green", "🟢 BUY": "lightgreen", "WAIT": "gold", "🔴 SELL": "red"},
                    title="Risk vs Reward"
                )
                fig.add_vline(x=40, line_dash="dash", line_color="blue")
                st.plotly_chart(fig, use_container_width=True)

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
