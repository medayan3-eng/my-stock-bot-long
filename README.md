# 📈 Murphy Swing Screener

An end-of-day screener for swing trades held from a few weeks to a few months,
built on the top-down logic of John Murphy's *Technical Analysis of the
Financial Markets*: **market → sector → stock**.

The app does not trade and does not send orders. It scans a universe you
control and returns a ranked shortlist with a full pass/fail breakdown, so the
final chart reading and the entry decision stay with you.

---

## Quick start

```bash
git clone <your-repo-url>
cd murphy-screener

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

The app opens at <http://localhost:8501>. Run it after the US close
(after 16:00 ET) so the last daily bar is final.

Offline logic check (no network needed):

```bash
python -m tests.test_offline
```

---

## What you need installed

| Tool | Why | Where |
|---|---|---|
| Python 3.10+ | runs everything | <https://www.python.org/downloads/> |
| Git | version control / push to GitHub | <https://git-scm.com/downloads> |
| A code editor (VS Code) | editing config, optional | <https://code.visualstudio.com/> |

No paid data subscription. Prices, volume, sector, institutional ownership
and earnings dates all come from Yahoo Finance through `yfinance`.

---

## Deploying to Streamlit Community Cloud (free)

1. Push this folder to a GitHub repository.
2. Go to <https://share.streamlit.io>, sign in with GitHub.
3. **New app** → pick the repo → main file `app.py` → **Deploy**.
4. You get a private URL you can open from any device, including your phone.

Yahoo occasionally rate-limits cloud IPs. If the hosted version returns empty
data, run it locally — the local run is always the reliable one.

---

## The screening rules

### Layer 1 — Market regime (master on/off switch)

| Check | Default |
|---|---|
| SPY above its 200-day SMA | required |
| VIX below the panic level | < 25 |
| Breadth: % of the universe above its own SMA200 | off by default |

When the regime is **RISK-OFF** the app still shows candidates, but flags them
as study-only. Murphy's premise: roughly 80% of a stock's move comes from the
market, so the best pattern fails in a falling tape.

### Layer 2 — Sector strength (top-down)

The stock's Yahoo sector is mapped to its SPDR ETF (XLK, XLE, XLF, XLV, XLY,
XLP, XLI, XLB, XLU, XLRE, XLC). The sector passes when its **RSI(14) > 50**
**or** its 60-day return beats SPY. Configurable to require either or both.

### Layer 3 — The stock

| # | Rule | Logic | Default |
|---|---|---|---|
| 1 | Liquidity | price ≥ floor **and** 50-day average volume ≥ floor | $5 / 500k shares |
| 2 | 52-week uptrend | SMA200 higher than 20 bars ago **and** price in the top quartile of the year | ≥ 80% of the 52-week high |
| 3 | At / above the 50MA | close above SMA50, or a shallow tag of support below it | ≥ −2% |
| 4 | Not extended | caps how far above the 50MA you may pay, keeping the stop close | ≤ +5% |
| 5 | Volume surge | today's volume **or** the 3-day max ≥ N × the 50-day average volume | ≥ 1.5× |
| 6 | Relative strength | 60-day return minus SPY's 60-day return | > 0 |
| 7 | Volatility squeeze | ATR%(10) / ATR%(50) — quiet before the break | < 1.0 |
| 8 | Institutional ownership | Yahoo `heldPercentInstitutions` | ≥ 10% |
| 9 | Sector strength | see layer 2 | on |
| 10 | Earnings blackout | no entry inside N days of the next report | 7 days |

Rules 3 and 4 together define the entry window: **−2% to +5% around the 50-day
moving average**.

Missing fundamental data never silently fails a stock. Each such rule has an
`on_missing` policy — `pass`, `fail` or `warn` (pass plus a visible flag).

### Score

A 0–100 ranking used only for sorting; it never overrides a failed rule.
Weights (editable in `config.yaml`): relative strength 30, volume surge 20,
proximity to the 52-week high 20, squeeze 15, sector 15.

---

## The exit algorithm

**First choice — pattern target (measured move, per Murphy):**

| Pattern | Target |
|---|---|
| Flag / pennant | breakout + the flagpole length |
| Symmetrical / ascending triangle | breakout + the base height |
| Channel / rectangle | breakout + the channel height |
| Cup & handle | breakout + the cup depth |
| Inverse head & shoulders | neckline + head-to-neckline distance |
| Double bottom | middle-peak breakout + bottoms-to-peak distance |

You read the pattern on the chart and type the breakout level and the height;
the app returns the target and the reward/risk in R.

**Fallback — the mechanical ladder** (when there is no clean pattern):

| Open profit | Action |
|---|---|
| +10% | stop to breakeven — the trade is now free |
| +20% | tighten to a 1.5 × ATR trailing stop |
| +25% | sell half; the runner trails 2 × ATR below the highest close, untouched |

**Initial stop:** the tighter of `entry − 2 × ATR(14)` and just under the
20-bar swing low. Position size follows from it:
`shares = (account × risk%) / (entry − stop)`, capped by the max position size.

---

## Project layout

```
murphy-screener/
├── app.py               Streamlit UI (scan, charts, trade plan, sectors)
├── config.yaml          all thresholds - edit here for permanent changes
├── universe.csv         your ticker list
├── requirements.txt
├── src/
│   ├── config.py        defaults + YAML merge
│   ├── data.py          yfinance access, sector map, fault tolerance
│   ├── indicators.py    SMA, RSI, ATR (Wilder), slopes, returns
│   ├── market.py        market regime + sector strength
│   ├── screener.py      metrics, rule engine, scoring
│   └── exits.py         pattern targets, stops, ladder, sizing
└── tests/test_offline.py
```

---

## Using it

0. Keep the Finviz pre-screen doing the coarse work (price, volume, ownership,
   beta, price above the 200-day SMA). Leave **Universe pre-filtered in Finviz**
   ticked in the sidebar: the app then trusts those cuts and reads the sector
   straight from `universe.csv`, skipping the slow per-ticker Yahoo profile call.
1. Paste your tickers into the text box, or replace `universe.csv`.
2. Press **Run scan** after the close.
3. Read the regime banner first. Red means no new longs.
4. Sort by score in **Results**; open **Chart & metrics** for anything that
   passes 8+ rules.
5. Draw the pattern yourself, then use **Trade plan** for the stop, size and
   target before you place the order.

Data is cached for 30 minutes (6 hours for fundamentals). Use **Clear cached
data** in the sidebar to force a refresh.

---

## Known limits

* Yahoo's institutional-ownership and earnings-date fields are occasionally
  missing or stale. Verify anything borderline on the company's IR page.
* `yfinance` is an unofficial API; scanning many hundreds of tickers at once
  can trigger rate limits. Keep the universe under ~300 names per run.
* Patterns are read by you, not detected automatically — deliberately.

## Roadmap ideas

* Beta is enforced upstream in Finviz (`ta_beta:o1`), so the app deliberately
  does not re-check it - it screens whatever universe you feed it
* Automatic base/consolidation detection (tightness, depth, duration)
* Gap-risk and post-gap-extension filters
* Open-position tracker that recomputes the trailing stop each evening
* Historical backtest of the rule set to calibrate the thresholds
* Alerts by email when a name enters the −2%/+5% window
