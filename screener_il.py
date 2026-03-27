"""
screener_il.py — Israel TASE Stock Screener
סורק מניות לבורסת תל אביב — שיטת מרפי

הבדלים מהסורק האמריקאי:
- מחירים בשקלים (₪)
- שעות מסחר: 09:00–17:30 ישראל (UTC+3)
- מדד ייחוס: ת"א 125 (במקום S&P 500)
- נפח: נמוך בהרבה — פילטר מותאם
- בטא מחושב מול ת"א 125
- ממוצע נע 200 יום פחות נפוץ — MA120 גיבוי
- אין ממשל שוק יומי זמין חינם → ניתוח טכני בלבד
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ──────────────────────────────────────────────────────────────
#  DATA DOWNLOAD
# ──────────────────────────────────────────────────────────────
def _get_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        t  = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d", auto_adjust=True, actions=False)
        if df is None or df.empty or 'Close' not in df.columns:
            return pd.DataFrame()
        cols = [c for c in ['Open','High','Low','Close','Volume'] if c in df.columns]
        df = df[cols].dropna(subset=['Close']).copy()
        # Handle MultiIndex columns (yfinance quirk)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────
#  INDICATORS
# ──────────────────────────────────────────────────────────────
def _rsi(close: pd.Series, period: int = 14) -> float:
    if len(close) < period * 2:
        return 50.0
    delta    = close.diff()
    avg_gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = float(rsi.iloc[-1])
    return round(val, 1) if not np.isnan(val) else 50.0


def _bb(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    if len(close) < period + 2:
        return 0.5, None, None
    mid   = close.rolling(period).mean()
    sigma = close.rolling(period).std()
    upper = mid + std_dev * sigma
    lower = mid - std_dev * sigma
    pct   = (close - lower) / (upper - lower)
    val   = float(pct.iloc[-1])
    u, l  = float(upper.iloc[-1]), float(lower.iloc[-1])
    return (round(val, 3) if not np.isnan(val) else 0.5,
            round(u, 2)   if not np.isnan(u)   else None,
            round(l, 2)   if not np.isnan(l)   else None)


def _macd(close: pd.Series, fast=12, slow=26, signal=9):
    if len(close) < slow + signal + 5:
        return 0.0, 0.0, 0.0
    ema_fast    = close.ewm(span=fast,   adjust=False).mean()
    ema_slow    = close.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist        = macd_line - signal_line
    return (round(float(macd_line.iloc[-1]),  4),
            round(float(signal_line.iloc[-1]), 4),
            round(float(hist.iloc[-1]),        4))


def _trend_pct(close: pd.Series, days: int = 20) -> float:
    if len(close) < days + 2:
        return 0.0
    start = float(close.iloc[-days-1])
    end   = float(close.iloc[-1])
    return round((end - start) / start * 100, 2) if start > 0 else 0.0


def _uptrend_52w(close: pd.Series) -> bool:
    """
    מגמת עלייה מרפי: מחיר גבוה מלפני שנה + MA50 > MA200 + מחיר > MA200.
    אם אין מספיק נתונים: MA50 > MA120 כגיבוי.
    """
    if len(close) < 60:
        return False
    price = float(close.iloc[-1])
    ma50  = float(close.rolling(50).mean().iloc[-1])

    if len(close) >= 200:
        ma200 = float(close.rolling(200).mean().iloc[-1])
        price_ago = float(close.iloc[0])
        return (price > price_ago and price > ma200 and ma50 > ma200)
    elif len(close) >= 120:
        # גיבוי: MA120
        ma120 = float(close.rolling(120).mean().iloc[-1])
        return (price > ma120 and ma50 > ma120)
    return False


def _relative_strength_tase(close: pd.Series, bench_close: pd.Series) -> float:
    """RS = תשואת המניה / תשואת ת"א 125 ב-63 ימים אחרונים."""
    try:
        if len(close) < 65 or len(bench_close) < 65:
            return 1.0
        common = close.index.intersection(bench_close.index)
        if len(common) < 50:
            return 1.0
        s = close.loc[common]
        m = bench_close.loc[common]
        stock_ret = float(s.iloc[-1]) / float(s.iloc[-63]) - 1
        bench_ret = float(m.iloc[-1]) / float(m.iloc[-63]) - 1
        if bench_ret == 0:
            return 1.0
        return round(stock_ret / abs(bench_ret), 2)
    except Exception:
        return 1.0


def _beta_tase(close: pd.Series, bench_close: pd.Series) -> float:
    """בטא מול ת"א 125."""
    try:
        s = close.pct_change().dropna()
        m = bench_close.pct_change().dropna()
        common = s.index.intersection(m.index)
        if len(common) < 30:
            return 1.0
        sv = s.loc[common].values.astype(float)
        mv = m.loc[common].values.astype(float)
        cov = np.cov(sv, mv)[0][1]
        var = np.var(mv)
        return round(float(cov / var), 2) if var > 0 else 1.0
    except Exception:
        return 1.0


def _support_resistance(df: pd.DataFrame, window: int = 8, n: int = 2):
    """
    רמות תמיכה/התנגדות — window קצר יותר כי שוק ישראלי פחות סחיר.
    """
    try:
        close = df['Close']
        high  = df['High']
        low   = df['Low']
        price = float(close.iloc[-1])

        local_highs, local_lows = [], []
        for i in range(window, len(close) - window):
            if float(high.iloc[i]) == float(high.iloc[i-window:i+window+1].max()):
                local_highs.append(float(high.iloc[i]))
            if float(low.iloc[i]) == float(low.iloc[i-window:i+window+1].min()):
                local_lows.append(float(low.iloc[i]))

        def cluster(levels, pct=0.025):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]
            for lvl in levels[1:]:
                if abs(lvl - clusters[-1][-1]) / clusters[-1][-1] < pct:
                    clusters[-1].append(lvl)
                else:
                    clusters.append([lvl])
            return [round(np.mean(c), 2) for c in clusters if len(c) >= n]

        supports    = cluster(local_lows)
        resistances = cluster(local_highs)

        sup  = max([s for s in supports    if s < price], default=None)
        res  = min([r for r in resistances if r > price], default=None)
        near = sup is not None and abs(price - sup) / price < 0.04

        return sup, res, near
    except Exception:
        return None, None, False


def _volume_spike(volume: pd.Series, threshold: float = 2.0):
    try:
        avg = float(volume.rolling(30).mean().iloc[-1])
        today = float(volume.iloc[-1])
        if avg <= 0:
            return 1.0, False
        ratio = round(today / avg, 2)
        return ratio, ratio >= threshold
    except Exception:
        return 1.0, False


def _chart_patterns(df: pd.DataFrame) -> list:
    patterns = []
    try:
        close = df['Close']
        high  = df['High']
        low   = df['Low']
        if len(close) < 40:
            return patterns

        price = float(close.iloc[-1])
        last60 = close.iloc[-60:]
        if len(last60) >= 40:
            half  = len(last60) // 2
            low1  = float(last60.iloc[:half].min())
            low2  = float(last60.iloc[half:].min())
            mid_h = float(last60.iloc[half//2:half+half//2].max())
            if (abs(low1 - low2) / ((low1+low2)/2) < 0.035 and
                mid_h > max(low1, low2) * 1.025 and
                price > mid_h * 0.97):
                patterns.append("תחתית כפולה (W)")

        last40_high = high.iloc[-40:]
        last40_low  = low.iloc[-40:]
        res_flat    = (float(last40_high.max()) - float(last40_high.min())) / float(last40_high.mean()) < 0.045
        lows_arr    = last40_low.values.astype(float)
        if len(lows_arr) > 5:
            x = np.arange(len(lows_arr))
            slope = np.polyfit(x, lows_arr, 1)[0]
            if res_flat and slope > 0:
                patterns.append("משולש עולה")

        # גל עולה — higher highs + higher lows
        if len(close) >= 30:
            q1 = float(close.iloc[-30:-20].max())
            q2 = float(close.iloc[-20:-10].max())
            q3 = float(close.iloc[-10:].max())
            l1 = float(close.iloc[-30:-20].min())
            l2 = float(close.iloc[-20:-10].min())
            l3 = float(close.iloc[-10:].min())
            if q3 > q2 > q1 and l3 > l2 > l1:
                patterns.append("מגמת עלייה (HH+HL)")
    except Exception:
        pass
    return patterns


def _risk_reward(price: float, support, resistance, stop_pct: float = 0.06):
    try:
        stop = support if support else price * (1 - stop_pct)
        if resistance is None or resistance <= price:
            return {"ratio": 0, "valid": False, "stop": round(stop, 2), "target": None}
        risk   = price - stop
        reward = resistance - price
        ratio  = round(reward / risk, 2) if risk > 0 else 0
        return {
            "ratio":  ratio,
            "valid":  ratio >= 1.5,
            "stop":   round(stop, 2),
            "target": round(resistance, 2),
        }
    except Exception:
        return {"ratio": 0, "valid": False, "stop": None, "target": None}


def _generate_summary(ticker, price, rsi, macd_bullish, trend_4w, above_ma,
                       uptrend_52w, near_support, rs, patterns, vol_spike,
                       bb_pct, rr) -> str:
    reasons = []
    if uptrend_52w:
        reasons.append("במגמת עלייה מוכחת של 52 שבועות")
    if rsi < 30:
        reasons.append(f"RSI {rsi} — מכירת יתר קיצונית")
    elif rsi < 40:
        reasons.append(f"RSI {rsi} — oversold בתוך מגמה")
    if macd_bullish:
        reasons.append("MACD חיובי — מומנטום עולה")
    if near_support:
        reasons.append("קרוב לרמת תמיכה — כניסה בסיכון נמוך")
    if bb_pct < 0.2:
        reasons.append("ברצועת BB תחתונה — פוטנציאל קפיצה")
    if rs > 1.2:
        reasons.append(f"חוזק יחסי {rs}× מול ת\"א 125")
    if vol_spike:
        reasons.append("⚡ נפח חריג — כסף מוסדי?")
    if patterns:
        reasons.append(f"תבנית: {', '.join(patterns)}")
    if rr.get('valid'):
        reasons.append(f"R/R = 1:{rr['ratio']} ✓")
    if above_ma:
        reasons.append("מחיר מעל הממוצעים")
    if not reasons:
        reasons.append("עוברת את פרמטרי מרפי")
    return " | ".join(reasons[:5])


# ──────────────────────────────────────────────────────────────
#  DEBUG
# ──────────────────────────────────────────────────────────────
def debug_ticker_il(ticker: str, params: dict) -> str:
    try:
        df = _get_ohlcv(ticker, period="2y")
        if df.empty or len(df) < 30:
            return f"{ticker}: ❌ אין נתונים ({len(df)} שורות)"
        close = df['Close']
        price = round(float(close.iloc[-1]), 2)
        min_price = params.get('min_price', 5)
        if price < min_price:
            return f"{ticker}: ❌ מחיר ₪{price} < מינימום ₪{min_price}"
        avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1]) if 'Volume' in df else 0
        min_vol = params.get('min_volume', 50_000)
        if avg_vol < min_vol:
            return f"{ticker}: ❌ נפח {avg_vol:,.0f} נמוך מ-{min_vol:,.0f}"
        rsi = _rsi(close, params.get('rsi_period', 14))
        rsi_min, rsi_max = params.get('rsi_min', 0), params.get('rsi_max', 90)
        if rsi > rsi_max or rsi < rsi_min:
            return f"{ticker}: ❌ RSI={rsi} לא בטווח [{rsi_min}–{rsi_max}]"
        uptrend = _uptrend_52w(close)
        trend = _trend_pct(close, 20)
        return (f"{ticker}: ✅ עובר — מחיר=₪{price}, RSI={rsi}, "
                f"מגמה_52ש={'✓' if uptrend else '✗'}, טרנד_4ש={trend}%")
    except Exception as e:
        return f"{ticker}: ❌ שגיאה: {e}"


# ──────────────────────────────────────────────────────────────
#  BENCHMARK CACHE
# ──────────────────────────────────────────────────────────────
_BENCH_CACHE = {}

def _get_benchmark() -> pd.Series:
    global _BENCH_CACHE
    key = datetime.today().strftime('%Y-%m-%d')
    if key in _BENCH_CACHE:
        return _BENCH_CACHE[key]
    # נסה ת"א 125, אם נכשל — ת"א 35
    for sym in ["^TA125.TA", "^TA35.TA", "TA125.TA", "TA35.TA"]:
        df = _get_ohlcv(sym, period="1y")
        if not df.empty:
            s = df['Close']
            _BENCH_CACHE = {key: s}
            return s
    return pd.Series(dtype=float)


# ──────────────────────────────────────────────────────────────
#  MAIN SCREENER
# ──────────────────────────────────────────────────────────────
def calculate_indicators_il(ticker: str, params: dict):
    """
    מחשב אינדיקטורים ומסנן מניות TASE.
    מחזיר dict עם כל הנתונים אם המניה עוברת את הפילטרים, אחרת None.
    """
    try:
        df = _get_ohlcv(ticker, period="2y")
        if df.empty or len(df) < 40:
            return None

        close  = df['Close']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series(dtype=float)
        price  = round(float(close.iloc[-1]), 2)

        # ── פילטר מחיר ──────────────────────────────────────────
        min_price = params.get('min_price', 5)      # שקלים
        if price < min_price:
            return None

        # ── פילטר נפח ─────────────────────────────────────────────
        if not volume.empty and len(volume) >= 20:
            avg_vol = float(volume.rolling(20).mean().iloc[-1])
        else:
            avg_vol = 0
        if np.isnan(avg_vol) or avg_vol < params.get('min_volume', 50_000):
            return None

        # ── ממוצעים נעים ─────────────────────────────────────────
        ma20  = round(float(close.rolling(20).mean().iloc[-1]),  2) if len(close) >= 20  else None
        ma50  = round(float(close.rolling(50).mean().iloc[-1]),  2) if len(close) >= 50  else None
        ma120 = round(float(close.rolling(120).mean().iloc[-1]), 2) if len(close) >= 120 else None
        ma200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None

        def ok(v): return v is not None and not np.isnan(v)

        # השתמש ב-MA120 אם אין MA200 (שוק קטן, פחות היסטוריה)
        ma_long  = ma200 if ok(ma200) else ma120
        above_ma = ok(ma_long) and price > ma_long
        above_50 = ok(ma50)    and price > ma50 * 0.97
        above_20 = ok(ma20)    and price > ma20

        if params.get('require_above_ma', True) and not above_ma:
            return None
        if params.get('require_above_50', True) and not above_50:
            return None

        # ── RSI ───────────────────────────────────────────────────
        rsi_period  = params.get('rsi_period', 14)
        rsi_max_val = params.get('rsi_max', 90)
        rsi_min_val = params.get('rsi_min', 0)
        current_rsi = _rsi(close, rsi_period)
        if current_rsi > rsi_max_val or current_rsi < rsi_min_val:
            return None

        # ── מגמה ─────────────────────────────────────────────────
        uptrend_52w = _uptrend_52w(close)
        if params.get('require_uptrend_52w', True) and not uptrend_52w:
            return None

        trend_4w = _trend_pct(close, 20)
        if trend_4w < -20.0:
            return None

        # ── בולינגר ──────────────────────────────────────────────
        bb_pct, bb_upper_v, bb_lower_v = _bb(
            close, params.get('bb_period', 20), params.get('bb_std', 2.0))

        # ── MACD ─────────────────────────────────────────────────
        macd_line, macd_signal, macd_hist = _macd(close)
        macd_bullish = macd_hist > 0

        # ── מדד ייחוס (ת"א 125) ──────────────────────────────────
        bench = _get_benchmark()
        beta  = _beta_tase(close, bench)

        min_beta = params.get('min_beta', 0.5)
        if min_beta > 0 and not np.isnan(beta) and beta < min_beta:
            return None

        rs = _relative_strength_tase(close, bench)

        # ── נפח ──────────────────────────────────────────────────
        vol_ratio, vol_spike = _volume_spike(volume)

        # ── תמיכה/התנגדות ────────────────────────────────────────
        support, resistance, near_support = _support_resistance(df)

        # ── תבניות ───────────────────────────────────────────────
        patterns = _chart_patterns(df)

        # ── R/R ──────────────────────────────────────────────────
        rr = _risk_reward(price, support, resistance)

        # ── ניתוח עדכניות סיגנל ──────────────────────────────────
        signal_fresh = True
        try:
            g = close.diff().clip(lower=0).ewm(com=rsi_period-1, min_periods=rsi_period).mean()
            l = (-close.diff().clip(upper=0)).ewm(com=rsi_period-1, min_periods=rsi_period).mean()
            rsi_ser = 100 - (100 / (1 + g / l))
            if len(rsi_ser) > 5:
                prev = float(rsi_ser.iloc[-5])
                signal_fresh = (not np.isnan(prev)) and prev > rsi_max_val
        except Exception:
            signal_fresh = True

        # ── ניקוד (0–10) ──────────────────────────────────────────
        score = 0.0

        # RSI
        if   current_rsi < 20: score += 4.0
        elif current_rsi < 25: score += 3.0
        elif current_rsi < 30: score += 2.5
        elif current_rsi < 35: score += 2.0
        elif current_rsi < 40: score += 1.5
        elif current_rsi < 50: score += 1.0
        else:                  score += 0.5

        # BB
        if   bb_pct < 0.05: score += 3.0
        elif bb_pct < 0.10: score += 2.5
        elif bb_pct < 0.20: score += 2.0
        elif bb_pct < 0.35: score += 1.5
        elif bb_pct < 0.50: score += 0.5

        # טרנד
        if   trend_4w >  5: score += 1.5
        elif trend_4w >  0: score += 1.0
        elif trend_4w > -5: score += 0.3

        # MA
        if above_ma:    score += 0.5
        if above_50:    score += 0.5
        if above_20:    score += 0.3
        if uptrend_52w: score += 1.0

        # MACD
        if macd_bullish: score += 0.5

        # נפח
        if vol_spike:         score += 0.7
        elif vol_ratio > 1.5: score += 0.3

        # חוזק יחסי
        if   rs > 1.5: score += 1.0
        elif rs > 1.0: score += 0.5

        # תמיכה / תבניות / R/R / סיגנל טרי
        if near_support:        score += 0.5
        if patterns:            score += 0.5
        if rr.get('valid'):     score += 0.5
        if signal_fresh:        score += 0.5

        score = round(min(10.0, score), 1)

        # ── שם החברה ─────────────────────────────────────────────
        name = ticker.replace('.TA', '')
        try:
            info = yf.Ticker(ticker).info
            long_name = info.get('longName') or info.get('shortName') or name
            name = long_name
        except Exception:
            pass

        # ── סיכום ────────────────────────────────────────────────
        summary = _generate_summary(
            ticker, price, current_rsi, macd_bullish, trend_4w,
            above_ma, uptrend_52w, near_support, rs,
            patterns, vol_spike, bb_pct, rr)

        # ── שווי שוק (אם זמין) ──────────────────────────────────
        market_cap = None
        try:
            info = yf.Ticker(ticker).fast_info
            mc = getattr(info, 'market_cap', None)
            if mc:
                market_cap = round(mc / 1_000_000, 0)  # במיליוני ₪
        except Exception:
            pass

        return {
            "ticker":        ticker,
            "ticker_short":  ticker.replace('.TA', ''),
            "name":          name,
            "price":         price,
            "currency":      "₪",
            "market_cap_m":  market_cap,
            "rsi":           current_rsi,
            "ma20":          ma20,
            "ma50":          ma50,
            "ma120":         ma120,
            "ma200":         ma200,
            "above_ma":      above_ma,
            "above_50":      above_50,
            "above_20":      above_20,
            "bb_pct":        bb_pct,
            "bb_upper":      bb_upper_v,
            "bb_lower":      bb_lower_v,
            "trend_4w":      trend_4w,
            "uptrend_52w":   uptrend_52w,
            "beta":          beta,
            "rs":            rs,
            "avg_volume":    round(avg_vol, 0),
            "volume_ratio":  round(vol_ratio, 2),
            "volume_spike":  vol_spike,
            "macd_line":     macd_line,
            "macd_signal":   macd_signal,
            "macd_hist":     macd_hist,
            "macd_bullish":  macd_bullish,
            "support":       support,
            "resistance":    resistance,
            "near_support":  near_support,
            "patterns":      patterns,
            "rr_ratio":      rr.get("ratio", 0),
            "rr_valid":      rr.get("valid", False),
            "rr_stop":       rr.get("stop"),
            "rr_target":     rr.get("target"),
            "signal_fresh":  signal_fresh,
            "signal_date":   datetime.today().strftime('%Y-%m-%d'),
            "summary":       summary,
            "score":         score,
            "passes_filter": True,
        }

    except Exception:
        return None
