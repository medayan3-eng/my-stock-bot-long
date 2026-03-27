"""
vix_analyzer.py — VIX Spike Behavior Analysis
==============================================
Answers: "When VIX spiked above threshold in the past,
          which stocks went UP and which went DOWN?"

Logic:
- Download 2 years of daily VIX data
- Detect every period where VIX crossed above `threshold`
- For each spike event: measure stock returns during the spike window
  (from day VIX crossed threshold → until VIX fell back below threshold)
- Aggregate across all events: avg return per stock during spikes
- Classify: consistent risers (safe havens) vs consistent fallers (risky)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


# ──────────────────────────────────────────────────────────────
#  STEP 1: Find all VIX spike windows
# ──────────────────────────────────────────────────────────────
def get_vix_spike_windows(threshold: float = 25.0, lookback_days: int = 730) -> list:
    """
    Download VIX history and find all windows where VIX > threshold.

    Returns list of (start_date, end_date, peak_vix) tuples.
    Each window = consecutive trading days with VIX above threshold.
    """
    end   = datetime.today()
    start = end - timedelta(days=lookback_days)

    try:
        vix = yf.Ticker("^VIX")
        df  = vix.history(start=start, end=end, interval="1d")
        if df.empty:
            return []

        close = df['Close'].dropna()
        above = close > threshold

        windows = []
        in_spike   = False
        spike_start = None

        for date, is_above in above.items():
            if is_above and not in_spike:
                in_spike    = True
                spike_start = date
            elif not is_above and in_spike:
                in_spike = False
                peak_vix = float(close.loc[spike_start:date].max())
                windows.append({
                    "start":    spike_start,
                    "end":      date,
                    "peak_vix": round(peak_vix, 2),
                    "days":     (date - spike_start).days,
                })

        # Handle ongoing spike at end of data
        if in_spike and spike_start is not None:
            peak_vix = float(close.loc[spike_start:].max())
            windows.append({
                "start":    spike_start,
                "end":      close.index[-1],
                "peak_vix": round(peak_vix, 2),
                "days":     (close.index[-1] - spike_start).days,
            })

        return windows

    except Exception as e:
        return []


# ──────────────────────────────────────────────────────────────
#  STEP 2: Measure stock return during each VIX window
# ──────────────────────────────────────────────────────────────
def _measure_stock_during_spikes(ticker: str, windows: list,
                                  lookback_days: int = 730) -> dict:
    """
    For a single ticker, measure its % return during each VIX spike window.
    Returns dict with aggregated stats across all spike events.
    """
    try:
        end   = datetime.today()
        start = end - timedelta(days=lookback_days + 30)

        t  = yf.Ticker(ticker)
        df = t.history(start=start, end=end, interval="1d", auto_adjust=True)
        if df is None or df.empty or 'Close' not in df.columns:
            return {}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close'].dropna()
        if len(close) < 10:
            return {}

        event_returns = []

        for w in windows:
            w_start = pd.Timestamp(w['start'])
            w_end   = pd.Timestamp(w['end'])

            # Find closest available trading days
            available = close.index
            starts_after  = available[available >= w_start]
            ends_before   = available[available <= w_end]

            if len(starts_after) == 0 or len(ends_before) == 0:
                continue

            p_start = starts_after[0]
            p_end   = ends_before[-1]

            if p_end <= p_start:
                continue

            price_start = float(close.loc[p_start])
            price_end   = float(close.loc[p_end])

            if price_start <= 0:
                continue

            ret = (price_end - price_start) / price_start * 100
            event_returns.append({
                "spike_start": w_start.strftime('%Y-%m-%d'),
                "spike_end":   w_end.strftime('%Y-%m-%d'),
                "peak_vix":    w['peak_vix'],
                "return_pct":  round(ret, 2),
                "went_up":     ret > 0,
            })

        if not event_returns:
            return {}

        returns   = [e['return_pct'] for e in event_returns]
        went_up   = sum(1 for e in event_returns if e['went_up'])
        went_down = len(event_returns) - went_up
        pct_up    = went_up / len(event_returns) * 100

        return {
            "ticker":          ticker,
            "ticker_short":    ticker.replace('.TA', ''),
            "num_events":      len(event_returns),
            "pct_rose":        round(pct_up, 1),
            "pct_fell":        round(100 - pct_up, 1),
            "avg_return":      round(float(np.mean(returns)), 2),
            "median_return":   round(float(np.median(returns)), 2),
            "best_event":      round(float(max(returns)), 2),
            "worst_event":     round(float(min(returns)), 2),
            "consistent_up":   pct_up >= 60,    # rose in ≥60% of spikes
            "consistent_down": pct_up <= 40,    # fell in ≥60% of spikes
            "events":          event_returns,
        }

    except Exception:
        return {}


# ──────────────────────────────────────────────────────────────
#  STEP 3: Run full analysis across all tickers
# ──────────────────────────────────────────────────────────────
def run_vix_spike_analysis(
    tickers:      list,
    threshold:    float = 25.0,
    lookback_days: int  = 730,
    progress_bar  = None,
    status_text   = None,
) -> dict:
    """
    Full pipeline:
    1. Find all VIX spike windows
    2. For each ticker, measure behavior during those windows
    3. Return structured results

    Returns:
    {
        "threshold":   float,
        "windows":     list of spike events,
        "risers":      list of stocks that consistently rose,
        "fallers":     list of stocks that consistently fell,
        "mixed":       list of stocks with mixed behavior,
        "all_stocks":  full list sorted by avg_return desc,
        "summary":     dict with aggregate stats,
    }
    """
    # ── Find VIX windows ─────────────────────────────────────
    windows = get_vix_spike_windows(threshold, lookback_days)

    if not windows:
        return {
            "error":     f"No VIX spikes above {threshold} found in the last {lookback_days//365} years",
            "threshold": threshold,
            "windows":   [],
        }

    # ── Analyze each ticker ───────────────────────────────────
    results   = []
    done, total = 0, len(tickers)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_measure_stock_during_spikes, t, windows, lookback_days): t
                   for t in tickers}
        for fut in as_completed(futures):
            done += 1
            if progress_bar:
                progress_bar.progress(done / total)
            if status_text:
                status_text.caption(f"Analyzing {done}/{total} stocks…")
            res = fut.result()
            if res and res.get('num_events', 0) > 0:
                results.append(res)

    if not results:
        return {
            "error":     "No data returned for any ticker",
            "threshold": threshold,
            "windows":   windows,
        }

    # ── Sort & classify ───────────────────────────────────────
    results.sort(key=lambda x: x['avg_return'], reverse=True)

    risers  = [r for r in results if r['consistent_up']]
    fallers = [r for r in results if r['consistent_down']]
    mixed   = [r for r in results if not r['consistent_up'] and not r['consistent_down']]

    # Sort risers by pct_rose then avg_return
    risers.sort(key=lambda x: (x['pct_rose'], x['avg_return']), reverse=True)
    fallers.sort(key=lambda x: (x['pct_fell'], -x['avg_return']), reverse=True)

    # ── Summary stats ─────────────────────────────────────────
    all_returns = [r['avg_return'] for r in results]
    summary = {
        "num_spikes":        len(windows),
        "tickers_analyzed":  len(results),
        "avg_spike_days":    round(np.mean([w['days'] for w in windows]), 1),
        "max_vix_seen":      round(max(w['peak_vix'] for w in windows), 2),
        "pct_stocks_rose":   round(sum(1 for r in results if r['avg_return'] > 0) / len(results) * 100, 1),
        "avg_return_all":    round(float(np.mean(all_returns)), 2),
        "num_risers":        len(risers),
        "num_fallers":       len(fallers),
        "num_mixed":         len(mixed),
    }

    return {
        "threshold":  threshold,
        "windows":    windows,
        "risers":     risers,
        "fallers":    fallers,
        "mixed":      mixed,
        "all_stocks": results,
        "summary":    summary,
    }
