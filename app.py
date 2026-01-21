import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- הגדרות דף (UI) ---
st.set_page_config(page_title="The Commander 🚀", layout="wide")

st.title("⚡ The Commander: AI Trading Scanner")
st.markdown("### מערכת סריקה אלגוריתמית לניהול תיק הנדסי")

# --- סרגל צד להגדרות (Sidebar) ---
st.sidebar.header("⚙️ הגדרות משתמש")
account_size = st.sidebar.number_input("גודל תיק ($)", value=10000, step=1000)
risk_per_trade = st.sidebar.slider("סיכון לעסקה (%)", 0.5, 3.0, 2.0) / 100
benchmark = st.sidebar.text_input("מדד ייחוס", value="SPY")

# רשימת המניות (אפשר לערוך מכאן!)
default_tickers = "NVDA, AMD, MSFT, AAPL, GOOGL, META, TSLA, AVGO, PLTR, GEV, AMZN"
tickers_input = st.sidebar.text_area("רשימת מניות (מופרד בפסיק)", value=default_tickers)
tickers = [t.strip().upper() for t in tickers_input.split(',')]

# --- הפונקציות ההנדסיות ---
def check_earnings(ticker):
    """בודק אם יש דוח ב-5 הימים הקרובים"""
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar
        if calendar is not None and not calendar.empty:
            # בדיקה גנרית לתאריך דוח
            next_date = calendar.iloc[0][0] 
            if isinstance(next_date, (datetime, pd.Timestamp)):
                days = (next_date.replace(tzinfo=None) - datetime.now()).days
                if 0 <= days <= 5:
                    return True, days
    except:
        return False, -1
    return False, -1

def run_scanner():
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # הורדת נתוני בנצ'מארק
    spy_data = yf.download(benchmark, period="3mo", progress=False)
    if not spy_data.empty:
        # טיפול במולטי-אינדקס אם קיים
        if isinstance(spy_data.columns, pd.MultiIndex):
            spy_data.columns = spy_data.columns.droplevel(1)
        spy_return = (spy_data['Close'].iloc[-1] - spy_data['Close'].iloc[0]) / spy_data['Close'].iloc[0]
    else:
        st.error("שגיאה במשיכת נתוני מדד ייחוס")
        return []

    total_tickers = len(tickers)
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"סורק את {ticker}...")
        progress_bar.progress((i + 1) / total_tickers)
        
        try:
            # 1. סינון דוחות
            risk, days = check_earnings(ticker)
            if risk:
                continue # מדלגים בשקט

            # 2. נתונים טכניים
            df = yf.download(ticker, period="1y", progress=False)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)

            # אינדיקטורים
            df['SMA_50'] = df['Close'].rolling(50).mean()
            df['SMA_200'] = df['Close'].rolling(200).mean()
            df['Prev_Low'] = df['Low'].shift(1).rolling(20).min()
            
            # ATR
            df['TR'] = np.maximum((df['High'] - df['Low']), 
                       np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                                  abs(df['Low'] - df['Close'].shift(1))))
            df['ATR'] = df['TR'].rolling(14).mean()

            # RS Score
            stock_ret = (df['Close'].iloc[-1] - df['Close'].iloc[-60]) / df['Close'].iloc[-60]
            rs_score = stock_ret - spy_return

            # בדיקת איתות להיום
            today = df.iloc[-1]
            trend = "Bearish"
            if today['SMA_50'] > today['SMA_200']: trend = "Bullish"
            
            # לוגיקה: רק אם מגמה עולה + SFP
            if (trend == "Bullish") and \
               (today['Low'] < today['Prev_Low']) and \
               (today['Close'] > today['Prev_Low']):
                
                # חישוב כמויות
                stop_loss = today['Close'] - (1 * today['ATR'])
                take_profit = today['Close'] + (2 * today['ATR'])
                risk_per_share = today['Close'] - stop_loss
                qty = math.floor((account_size * risk_per_trade) / risk_per_share)
                
                if qty > 0:
                    results.append({
                        'Ticker': ticker,
                        'Price': round(today['Close'], 2),
                        'RS Score': round(rs_score * 100, 2),
                        'Qty': qty,
                        'Stop Loss': round(stop_loss, 2),
                        'Take Profit': round(take_profit, 2),
                        'Investment': round(qty * today['Close'], 2)
                    })
        except Exception as e:
            continue

    progress_bar.empty()
    status_text.empty()
    return results

# --- כפתור הפעלה ---
if st.button('🚀 הרץ סריקת שוק', use_container_width=True):
    with st.spinner('מנתח שווקים ומחשב סיכונים...'):
        data = run_scanner()
        
    if data:
        st.success(f"נמצאו {len(data)} הזדמנויות העונות לקריטריונים!")
        df_res = pd.DataFrame(data).sort_values(by='RS Score', ascending=False)
        
        # הצגת טבלה מעוצבת
        st.dataframe(df_res, use_container_width=True)
        
        # סיכום טקסטואלי לנייד
        st.markdown("### 📋 סיכום להעתקה")
        for index, row in df_res.iterrows():
            st.code(f"{row['Ticker']} | BUY: {row['Price']} | Qty: {row['Qty']} | SL: {row['Stop Loss']} | TP: {row['Take Profit']}")
            
    else:
        st.info("הסריקה הסתיימה. לא נמצאו איתותי SFP איכותיים היום. שמור על הכסף.")

