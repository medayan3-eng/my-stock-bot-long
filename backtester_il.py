"""
backtester_il.py — Backtester for TASE Israeli stocks
בק-טסטר לבורסת תל אביב

לוגיקה:
- מוריד שנה של נתונים יומיים לכל מניה
- מדמה כניסות ויציאות לפי שיטת מרפי
- Buy:  RSI < rsi_max  AND  BB%B < 0.40  AND  מחיר > MA (ארוך)
- Sell: RSI > 65  OR  BB%B > 0.80  OR  מחיר < MA50 * 0.95
- מחשב: win_rate, avg_return, best/worst trade, avg_hold_days
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


def _rsi(s: pd.Series, period: int) -> pd.Series:
    delta    = s.diff()
    avg_gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def _bb_pct(s: pd.Series, period: int, std_dev: float) -> pd.Series:
    mid   = s.rolling(period).mean()
    sigma = s.rolling(period).std()
    lower = mid - std_dev * sigma
    upper = mid + std_dev * sigma
    return (s - lower) / (upper - lower)


def _backtest_one_il(ticker: str, params: dict) -> dict:
    try:
        end   = datetime.today()
        start = end - timedelta(days=420)

        t  = yf.Ticker(ticker)
        df = t.history(start=start, end=end, interval="1d",
                       auto_adjust=True, actions=False)
        if df is None or df.empty or 'Close' not in df.columns:
            return {}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.dropna()
        if len(close) < 60:
            return {}

        rsi_p  = params.get('rsi_period', 14)
        rsi_th = params.get('rsi_max', 45)
        bb_p   = params.get('bb_period', 20)
        bb_std = params.get('bb_std', 2.0)

        rsi_ser = _rsi(close, rsi_p)
        bb_ser  = _bb_pct(close, bb_p, bb_std)
        ma50    = close.rolling(50).mean()
        ma_long = close.rolling(120).mean() if len(close) < 200 else close.rolling(200).mean()

        buy_sig  = (rsi_ser < rsi_th) & (bb_ser < 0.40) & (close > ma_long) & (close > ma50 * 0.95)
        sell_sig = (rsi_ser > 65)     | (bb_ser > 0.80) | (close < ma50 * 0.95)

        # רק השנה האחרונה
        cutoff  = pd.Timestamp(end - timedelta(days=365))
        close_r = close[close.index >= cutoff]
        buy_r   = buy_sig[buy_sig.index >= cutoff]
        sell_r  = sell_sig[sell_sig.index >= cutoff]

        trades        = []
        in_trade      = False
        buy_price     = None
        buy_date      = None
        buy_rsi       = None
        cooldown_left = 0

        for date in close_r.index:
            if cooldown_left > 0:
                cooldown_left -= 1
                continue

            price   = float(close_r.loc[date])
            is_buy  = bool(buy_r.loc[date])  if date in buy_r.index  else False
            is_sell = bool(sell_r.loc[date]) if date in sell_r.index else False

            if not in_trade:
                if is_buy:
                    in_trade  = True
                    buy_price = price
                    buy_date  = date
                    buy_rsi   = float(rsi_ser.loc[date]) if date in rsi_ser.index else None
            else:
                if is_sell:
                    pct    = (price - buy_price) / buy_price * 100
                    hold_d = (date - buy_date).days
                    won    = pct > 0
                    trades.append({
                        "ticker":     ticker,
                        "buy_date":   buy_date.strftime('%Y-%m-%d'),
                        "sell_date":  date.strftime('%Y-%m-%d'),
                        "buy_price":  round(float(buy_price), 2),
                        "sell_price": round(float(price), 2),
                        "return_%":   round(pct, 2),
                        "hold_days":  hold_d,
                        "result":     "✅ רווח" if won else "❌ הפסד",
                        "rsi_at_buy": round(float(buy_rsi), 1) if buy_rsi else None,
                    })
                    in_trade = False
                    buy_price = None
                    if not won:
                        cooldown_left = 3

        # עסקה פתוחה בסוף התקופה
        if in_trade and buy_price is not None:
            last_price = float(close_r.iloc[-1])
            pct = (last_price - buy_price) / buy_price * 100
            hold_d = (close_r.index[-1] - buy_date).days
            trades.append({
                "ticker":     ticker,
                "buy_date":   buy_date.strftime('%Y-%m-%d'),
                "sell_date":  "פתוח",
                "buy_price":  round(float(buy_price), 2),
                "sell_price": round(float(last_price), 2),
                "return_%":   round(pct, 2),
                "hold_days":  hold_d,
                "result":     "🔵 פתוח",
                "rsi_at_buy": round(float(buy_rsi), 1) if buy_rsi else None,
            })

        if not trades:
            return {}

        closed   = [t for t in trades if t['sell_date'] != "פתוח"]
        all_r    = [t['return_%'] for t in trades]
        wins     = [t for t in closed if t['return_%'] > 0]
        win_r    = len(wins) / len(closed) * 100 if closed else 0
        holds    = [t['hold_days'] for t in trades]

        return {
            "ticker":        ticker,
            "trades":        trades,
            "total_trades":  len(trades),
            "wins":          len(wins),
            "losses":        len(closed) - len(wins),
            "win_rate":      round(win_r, 1),
            "avg_return":    round(float(np.mean(all_r)), 2),
            "best_trade":    round(float(max(all_r)), 2),
            "worst_trade":   round(float(min(all_r)), 2),
            "avg_hold_days": round(float(np.mean(holds)), 1),
        }

    except Exception:
        return {}


def run_backtest_il(tickers: list, params: dict,
                    progress_bar=None, status_text=None) -> dict:
    per_stock = {}
    trade_log = []
    done, total = 0, len(tickers)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_backtest_one_il, t, params): t for t in tickers}
        for fut in as_completed(futures):
            done += 1
            if progress_bar:
                progress_bar.progress(done / total)
            if status_text:
                status_text.caption(f"בק-טסט {done}/{total}…")
            res = fut.result()
            if res and res.get('total_trades', 0) > 0:
                t = res['ticker']
                per_stock[t] = {k: res[k] for k in
                    ['total_trades','wins','losses','win_rate',
                     'avg_return','best_trade','worst_trade','avg_hold_days']}
                trade_log.extend(res.get('trades', []))

    if not trade_log:
        return {"overall": {}, "per_stock": {}, "trade_log": []}

    all_r    = [t['return_%'] for t in trade_log]
    closed   = [t for t in trade_log if t['sell_date'] != "פתוח"]
    wins_all = [t for t in closed if t['return_%'] > 0]
    wr_all   = len(wins_all) / len(closed) * 100 if closed else 0

    overall = {
        "total_trades":   len(trade_log),
        "wins":           len(wins_all),
        "losses":         len(closed) - len(wins_all),
        "win_rate":       round(wr_all, 1),
        "avg_return":     round(float(np.mean(all_r)), 2),
        "best_trade":     round(float(max(all_r)), 2),
        "worst_trade":    round(float(min(all_r)), 2),
        "tickers_tested": len(per_stock),
    }
    trade_log.sort(key=lambda x: x['buy_date'], reverse=True)
    return {"overall": overall, "per_stock": per_stock, "trade_log": trade_log}
