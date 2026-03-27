"""
news_fetcher_il.py — חדשות למניות ישראליות
"""

import yfinance as yf
from datetime import datetime


def fetch_news_il(ticker: str) -> list:
    """
    מושך חדשות למניה ישראלית דרך yfinance.
    """
    try:
        t    = yf.Ticker(ticker)
        news = t.news
        if not news:
            return []

        result = []
        for item in news[:10]:
            title     = (item.get('title') or
                         item.get('content', {}).get('title', ''))
            url       = (item.get('link') or item.get('url') or
                         item.get('content', {}).get('url', ''))
            publisher = (item.get('publisher') or
                         item.get('source', {}).get('displayName', ''))
            pub_time  = item.get('providerPublishTime') or item.get('pubDate', '')
            if isinstance(pub_time, int):
                try:
                    pub_str = datetime.fromtimestamp(pub_time).strftime('%d/%m/%Y %H:%M')
                except Exception:
                    pub_str = str(pub_time)
            else:
                pub_str = str(pub_time)[:16] if pub_time else ''

            if title:
                result.append({
                    'title':     title,
                    'url':       url,
                    'publisher': publisher,
                    'published': pub_str,
                })
        return result
    except Exception:
        return []


def fetch_market_news_il() -> list:
    """
    חדשות שוק כלליות — ת"א 35, ת"א 125.
    """
    headlines = []
    seen = set()
    sources = ["^TA125.TA", "^TA35.TA", "TEVA.TA", "ICL.TA", "ESLT.TA", "BEZQ.TA"]
    for sym in sources:
        try:
            t    = yf.Ticker(sym)
            news = t.news or []
            for item in news[:6]:
                title = (item.get('title') or
                         item.get('content', {}).get('title', ''))
                if not title or title in seen:
                    continue
                seen.add(title)
                pub_time = item.get('providerPublishTime') or 0
                try:
                    pub_str = datetime.fromtimestamp(pub_time).strftime('%d/%m %H:%M')
                except Exception:
                    pub_str = ''
                url = (item.get('link') or item.get('url') or
                       item.get('content', {}).get('url', ''))
                headlines.append({
                    'title':     title,
                    'publisher': item.get('publisher', ''),
                    'published': pub_str,
                    'url':       url,
                })
        except Exception:
            pass
    return headlines[:30]
