"""Automatic chart-pattern recognition, following Murphy's definitions.

Detects, without any user input:
  * pivot highs / lows (fractals)
  * support and resistance levels (clustered pivots, ranked by touches)
  * flag / pennant
  * symmetrical, ascending and descending triangles
  * channel / rectangle
  * cup & handle
  * inverse head & shoulders
  * double bottom
  * base / consolidation (התכנסות)

Each detector returns a confidence score, the breakout level, the formation
height and the measured-move target. The highest-scoring pattern wins.
Everything is computed from OHLC only - no lookahead, no external data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Tunables (deliberately conservative - a missed pattern beats a false one)
# --------------------------------------------------------------------------- #
PIVOT_WINDOW = 5            # bars on each side that define a fractal
LOOKBACK = 140              # bars examined for pattern formation
LEVEL_TOLERANCE = 0.015     # 1.5% - pivots inside this band are the same level
MIN_CONFIDENCE = 0.45       # below this we report "no clear pattern"


@dataclass
class Pattern:
    name: str = "No clear pattern"
    confidence: float = 0.0
    breakout_level: Optional[float] = None
    height: Optional[float] = None
    target: Optional[float] = None
    direction: str = "bullish"
    bars: Optional[int] = None
    note: str = ""
    points: List[dict] = field(default_factory=list)   # for chart overlay

    def as_dict(self) -> dict:
        return {
            "pattern": self.name,
            "pattern_confidence": round(self.confidence, 2),
            "pattern_breakout": None if self.breakout_level is None else round(self.breakout_level, 2),
            "pattern_height": None if self.height is None else round(self.height, 2),
            "pattern_target": None if self.target is None else round(self.target, 2),
            "pattern_bars": self.bars,
            "pattern_note": self.note,
        }


# --------------------------------------------------------------------------- #
# Pivots and levels
# --------------------------------------------------------------------------- #
def pivot_highs(df: pd.DataFrame, window: int = PIVOT_WINDOW) -> List[Tuple[int, float]]:
    highs = df["High"].to_numpy(dtype=float)
    out = []
    for i in range(window, len(highs) - window):
        seg = highs[i - window: i + window + 1]
        if highs[i] == seg.max() and (seg.argmax() == window):
            out.append((i, float(highs[i])))
    return out


def pivot_lows(df: pd.DataFrame, window: int = PIVOT_WINDOW) -> List[Tuple[int, float]]:
    lows = df["Low"].to_numpy(dtype=float)
    out = []
    for i in range(window, len(lows) - window):
        seg = lows[i - window: i + window + 1]
        if lows[i] == seg.min() and (seg.argmin() == window):
            out.append((i, float(lows[i])))
    return out


def _cluster(points: List[Tuple[int, float]], tol: float = LEVEL_TOLERANCE) -> List[dict]:
    """Group pivot prices that sit within `tol` of each other into one level."""
    if not points:
        return []
    ordered = sorted(points, key=lambda p: p[1])
    clusters: List[List[Tuple[int, float]]] = [[ordered[0]]]
    for idx, price in ordered[1:]:
        ref = np.mean([p for _, p in clusters[-1]])
        if ref > 0 and abs(price - ref) / ref <= tol:
            clusters[-1].append((idx, price))
        else:
            clusters.append([(idx, price)])
    levels = []
    for c in clusters:
        levels.append(
            {
                "price": round(float(np.mean([p for _, p in c])), 2),
                "touches": len(c),
                "last_bar": max(i for i, _ in c),
            }
        )
    return levels


def support_resistance(df: pd.DataFrame, lookback: int = LOOKBACK) -> dict:
    """Nearest support below and resistance above the last close."""
    win = df.iloc[-lookback:] if len(df) > lookback else df
    price = float(win["Close"].iloc[-1])

    lows = _cluster(pivot_lows(win))
    highs = _cluster(pivot_highs(win))

    below = [l for l in lows if l["price"] < price * 0.999]
    above = [h for h in highs if h["price"] > price * 1.001]

    support = max(below, key=lambda l: (l["price"])) if below else None
    resistance = min(above, key=lambda h: (h["price"])) if above else None

    # Strongest level overall = most touches
    all_levels = sorted(lows + highs, key=lambda l: -l["touches"])[:6]

    return {
        "support": support["price"] if support else None,
        "support_touches": support["touches"] if support else None,
        "support_dist_pct": round((support["price"] / price - 1) * 100, 2) if support else None,
        "resistance": resistance["price"] if resistance else None,
        "resistance_touches": resistance["touches"] if resistance else None,
        "resistance_dist_pct": round((resistance["price"] / price - 1) * 100, 2) if resistance else None,
        "key_levels": all_levels,
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _fit(points: List[Tuple[int, float]]) -> Optional[Tuple[float, float]]:
    """Least-squares line through (bar_index, price). Returns (slope, intercept)."""
    if len(points) < 2:
        return None
    x = np.array([p[0] for p in points], dtype=float)
    y = np.array([p[1] for p in points], dtype=float)
    if np.ptp(x) == 0:
        return None
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def _line_at(fit: Tuple[float, float], x: float) -> float:
    return fit[0] * x + fit[1]


def _clamp01(x: float) -> float:
    """Clamp to [0, 0.95] - no detector should ever claim certainty."""
    return float(max(0.0, min(0.95, x)))


def _target(breakout: float, height: float) -> float:
    return round(breakout + height, 2)


def _adherence(
    points: List[Tuple[int, float]],
    fit: Tuple[float, float],
    scale: float,
) -> float:
    """How tightly the pivots hug their own trendline (1.0 = perfect).

    Containment alone is not enough: a wide band contains everything. A real
    trendline is one the pivots actually touch, so the residuals must be small
    relative to the formation's height.
    """
    if not points or scale <= 0:
        return 0.0
    res = [abs(p - _line_at(fit, i)) for i, p in points]
    return _clamp01(1.0 - (float(np.mean(res)) / scale) / 0.25) / 0.95


def _containment(
    win: pd.DataFrame,
    hi_fit: Tuple[float, float],
    lo_fit: Tuple[float, float],
    start: int = 0,
    tol: float = 0.02,
) -> float:
    """Fraction of bars that actually sit inside the two trendlines.

    Without this, a least-squares line through any four random pivots looks
    like a channel. Real formations contain price; noise does not.
    """
    highs = win["High"].to_numpy(dtype=float)
    lows = win["Low"].to_numpy(dtype=float)
    inside = 0
    total = 0
    for i in range(int(start), len(highs)):
        upper = _line_at(hi_fit, i)
        lower = _line_at(lo_fit, i)
        if upper <= 0 or lower <= 0 or upper <= lower:
            continue
        total += 1
        if highs[i] <= upper * (1 + tol) and lows[i] >= lower * (1 - tol):
            inside += 1
    return inside / total if total else 0.0


# --------------------------------------------------------------------------- #
# Individual detectors - each returns a Pattern or None
# --------------------------------------------------------------------------- #
def detect_flag(df: pd.DataFrame) -> Optional[Pattern]:
    """Sharp pole, then a tight drifting consolidation. Target = pole length."""
    close = df["Close"].to_numpy(dtype=float)
    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    n = len(close)
    if n < 60:
        return None

    best: Optional[Pattern] = None
    for flag_len in range(5, 31):                  # consolidation length
        for pole_len in range(8, 36):              # pole length
            start = n - flag_len - pole_len
            if start < 0:
                continue
            pole_lo = float(low[start: start + pole_len].min())
            pole_hi = float(high[start: start + pole_len].max())
            if pole_lo <= 0:
                continue
            pole_gain = pole_hi / pole_lo - 1.0
            if pole_gain < 0.15:                   # need a real thrust
                continue
            # the pole must actually rise (low before high)
            seg_low_idx = int(low[start: start + pole_len].argmin())
            seg_high_idx = int(high[start: start + pole_len].argmax())
            if seg_high_idx <= seg_low_idx:
                continue

            flag = slice(n - flag_len, n)
            f_hi = float(high[flag].max())
            f_lo = float(low[flag].min())
            f_range = f_hi - f_lo
            pole_height = pole_hi - pole_lo
            if pole_height <= 0:
                continue
            depth = f_range / pole_height
            if depth > 0.45:                       # consolidation too loose
                continue
            if f_lo < pole_lo + 0.4 * pole_height:  # retraced too much
                continue

            tightness = 1.0 - depth / 0.45
            thrust = _clamp01((pole_gain - 0.15) / 0.35)
            conf = _clamp01(0.45 + 0.30 * tightness + 0.25 * thrust)
            if best is None or conf > best.confidence:
                best = Pattern(
                    name="Flag / Pennant",
                    confidence=conf,
                    breakout_level=round(f_hi, 2),
                    height=round(pole_height, 2),
                    target=_target(f_hi, pole_height),
                    bars=flag_len + pole_len,
                    note=(
                        f"Pole of {pole_gain * 100:.0f}% over {pole_len} bars, then a "
                        f"{flag_len}-bar consolidation holding {depth * 100:.0f}% of it."
                    ),
                    points=[
                        {"label": "pole low", "bar": start + seg_low_idx, "price": pole_lo},
                        {"label": "pole high", "bar": start + seg_high_idx, "price": pole_hi},
                        {"label": "breakout", "bar": n - 1, "price": f_hi},
                    ],
                )
    return best


def detect_triangle(df: pd.DataFrame) -> Optional[Pattern]:
    """Converging trendlines: symmetrical, ascending or descending."""
    win = df.iloc[-LOOKBACK:] if len(df) > LOOKBACK else df
    n = len(win)
    if n < 40:
        return None
    ph, pl = pivot_highs(win), pivot_lows(win)
    if len(ph) < 2 or len(pl) < 2:
        return None
    ph, pl = ph[-4:], pl[-4:]

    hi_fit, lo_fit = _fit(ph), _fit(pl)
    if hi_fit is None or lo_fit is None:
        return None

    x0 = min(ph[0][0], pl[0][0])
    x1 = n - 1
    gap0 = _line_at(hi_fit, x0) - _line_at(lo_fit, x0)
    gap1 = _line_at(hi_fit, x1) - _line_at(lo_fit, x1)
    if gap0 <= 0 or gap1 <= 0 or gap1 >= gap0:
        return None
    convergence = 1.0 - gap1 / gap0
    if convergence < 0.25:
        return None

    price = float(win["Close"].iloc[-1])
    hi_slope_pct = hi_fit[0] / price * 100
    lo_slope_pct = lo_fit[0] / price * 100
    flat = 0.03                                    # % of price per bar ~ "flat"

    if abs(hi_slope_pct) < flat and lo_slope_pct > flat:
        name = "Ascending Triangle"
    elif abs(lo_slope_pct) < flat and hi_slope_pct < -flat:
        name = "Descending Triangle"
        return None                                # bearish - not a long setup
    elif hi_slope_pct < -flat and lo_slope_pct > flat:
        name = "Symmetrical Triangle"
    else:
        return None

    contain = _containment(win, hi_fit, lo_fit, start=x0)
    if contain < 0.85:                             # price must respect the lines
        return None
    adhere = min(_adherence(ph, hi_fit, gap0), _adherence(pl, lo_fit, gap0))
    if adhere < 0.55:
        return None

    breakout = _line_at(hi_fit, x1)
    height = gap0
    conf = _clamp01(
        0.28 + 0.25 * convergence + 0.27 * adhere + 0.15 * (contain - 0.85) / 0.15
    )
    if name == "Ascending Triangle":
        conf = _clamp01(conf + 0.05)

    return Pattern(
        name=name,
        confidence=conf,
        breakout_level=round(breakout, 2),
        height=round(height, 2),
        target=_target(breakout, height),
        bars=int(x1 - x0),
        note=(
            f"{len(ph)} pivot highs and {len(pl)} pivot lows converging "
            f"{convergence * 100:.0f}% over {int(x1 - x0)} bars; "
            f"{contain * 100:.0f}% of bars inside the lines."
        ),
        points=[{"label": "apex zone", "bar": x1, "price": breakout}],
    )


def detect_channel(df: pd.DataFrame) -> Optional[Pattern]:
    """Parallel trendlines: rising channel or horizontal rectangle."""
    win = df.iloc[-LOOKBACK:] if len(df) > LOOKBACK else df
    n = len(win)
    if n < 40:
        return None
    ph, pl = pivot_highs(win), pivot_lows(win)
    if len(ph) < 3 or len(pl) < 3:                 # two pivots fit any line
        return None
    hi_fit, lo_fit = _fit(ph[-4:]), _fit(pl[-4:])
    if hi_fit is None or lo_fit is None:
        return None

    price = float(win["Close"].iloc[-1])
    hi_s = hi_fit[0] / price * 100
    lo_s = lo_fit[0] / price * 100
    if abs(hi_s - lo_s) > 0.03:                    # not parallel
        return None

    x1 = n - 1
    upper = _line_at(hi_fit, x1)
    lower = _line_at(lo_fit, x1)
    height = upper - lower
    if height <= 0 or height / price > 0.35:
        return None
    if hi_s < -0.02:                               # falling channel - skip
        return None

    start = min(ph[-4:][0][0], pl[-4:][0][0])
    contain = _containment(win, hi_fit, lo_fit, start=start)
    if contain < 0.90:
        return None
    adhere = min(_adherence(ph[-4:], hi_fit, height), _adherence(pl[-4:], lo_fit, height))
    if adhere < 0.55:                              # pivots must touch the lines
        return None

    name = "Channel / Rectangle" if abs(hi_s) < 0.03 else "Rising Channel"
    conf = _clamp01(
        0.30 + 0.30 * adhere + 0.20 * (contain - 0.90) / 0.10
        + 0.05 * min(len(ph) + len(pl) - 6, 2)
    )
    return Pattern(
        name="Channel / Rectangle",
        confidence=conf,
        breakout_level=round(upper, 2),
        height=round(height, 2),
        target=_target(upper, height),
        bars=n,
        note=(
            f"{name}: {len(ph)} highs and {len(pl)} lows on parallel lines, "
            f"{contain * 100:.0f}% of bars contained."
        ),
        points=[
            {"label": "channel top", "bar": x1, "price": upper},
            {"label": "channel bottom", "bar": x1, "price": lower},
        ],
    )


def detect_cup_handle(df: pd.DataFrame) -> Optional[Pattern]:
    """Rounded U with matching rims, then a shallow handle."""
    close = df["Close"].to_numpy(dtype=float)
    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    n = len(close)
    if n < 70:
        return None

    best: Optional[Pattern] = None
    for cup_len in range(50, min(160, n - 5), 10):
        for handle_len in range(4, 26, 3):
            start = n - cup_len - handle_len
            if start < 0:
                continue
            cup = slice(start, start + cup_len)
            c_high = high[cup]
            c_low = low[cup]
            left_rim = float(c_high[: max(3, cup_len // 5)].max())
            right_rim = float(c_high[-max(3, cup_len // 5):].max())
            bottom = float(c_low.min())
            bottom_pos = int(c_low.argmin()) / cup_len
            if not (0.25 <= bottom_pos <= 0.75):   # bottom must be central
                continue
            if left_rim <= 0 or bottom <= 0:
                continue
            depth = (left_rim - bottom) / left_rim
            if not (0.10 <= depth <= 0.55):
                continue
            if abs(right_rim - left_rim) / left_rim > 0.06:   # rims must match
                continue
            rim_ref = max(left_rim, right_rim)
            # nothing inside the cup may poke meaningfully above the rims
            if float(c_high.max()) > rim_ref * 1.02:
                continue
            # the middle third must genuinely be the low area, not a spike
            mid = c_low[cup_len // 3: 2 * cup_len // 3]
            if len(mid) and float(mid.mean()) > bottom + 0.6 * (rim_ref - bottom):
                continue

            # a cup is rounded: the lower quarter of the range must span
            # a decent number of bars, otherwise it is a V reversal
            lower_quarter = bottom + 0.25 * (rim_ref - bottom)
            broad = int((c_low <= lower_quarter).sum())
            if broad < max(6, cup_len // 8):
                continue

            handle = slice(n - handle_len, n)
            h_low = float(low[handle].min())
            h_high = float(high[handle].max())
            rim = max(left_rim, right_rim)
            pullback = (rim - h_low) / (rim - bottom)
            if pullback > 0.40 or pullback < 0.02:  # handle too deep / absent
                continue
            if h_high > rim * 1.03:                 # already broken out hard
                continue

            depth_abs = rim - bottom
            shape = 1.0 - abs(bottom_pos - 0.5) * 2
            roundness = min(broad / max(cup_len / 4, 1), 1.0)
            conf = _clamp01(
                0.32 + 0.22 * shape + 0.20 * roundness + 0.18 * (1 - pullback / 0.40)
            )
            if best is None or conf > best.confidence:
                best = Pattern(
                    name="Cup & Handle",
                    confidence=conf,
                    breakout_level=round(rim, 2),
                    height=round(depth_abs, 2),
                    target=_target(rim, depth_abs),
                    bars=cup_len + handle_len,
                    note=(
                        f"{cup_len}-bar cup {depth * 100:.0f}% deep with matching rims, "
                        f"then a {handle_len}-bar handle retracing {pullback * 100:.0f}%."
                    ),
                    points=[
                        {"label": "cup bottom", "bar": start + int(c_low.argmin()), "price": bottom},
                        {"label": "rim / breakout", "bar": n - 1, "price": rim},
                    ],
                )
    return best


def detect_inverse_hs(df: pd.DataFrame) -> Optional[Pattern]:
    """Three troughs, the middle one lowest, breakout above the neckline."""
    win = df.iloc[-LOOKBACK:] if len(df) > LOOKBACK else df
    n = len(win)
    if n < 50:
        return None
    pl = pivot_lows(win)
    ph = pivot_highs(win)
    if len(pl) < 3 or len(ph) < 2:
        return None

    ls, head, rs = pl[-3], pl[-2], pl[-1]
    if not (head[1] < ls[1] and head[1] < rs[1]):
        return None
    if ls[1] <= 0:
        return None
    if abs(rs[1] - ls[1]) / ls[1] > 0.12:          # shoulders must be similar
        return None

    left_span = head[0] - ls[0]
    right_span = rs[0] - head[0]
    if min(left_span, right_span) < 5:
        return None
    time_sym = min(left_span, right_span) / max(left_span, right_span)
    if time_sym < 0.45:                            # lopsided - not a real H&S
        return None

    between = [p for p in ph if ls[0] < p[0] < rs[0]]
    if len(between) < 2:
        return None
    neck_fit = _fit(between[-2:])
    if neck_fit is None:
        return None
    neckline = _line_at(neck_fit, n - 1)
    height = neckline - head[1]
    if height <= 0:
        return None
    price = float(win["Close"].iloc[-1])
    if height / price > 0.60 or height / price < 0.05:
        return None

    symmetry = 1.0 - abs(rs[1] - ls[1]) / ls[1] / 0.12
    conf = _clamp01(0.30 + 0.30 * symmetry + 0.25 * time_sym)
    return Pattern(
        name="Inverse Head & Shoulders",
        confidence=conf,
        breakout_level=round(neckline, 2),
        height=round(height, 2),
        target=_target(neckline, height),
        bars=int(rs[0] - ls[0]),
        note=(
            f"Head at {head[1]:.2f} with shoulders at {ls[1]:.2f} / {rs[1]:.2f}; "
            f"neckline currently {neckline:.2f}."
        ),
        points=[
            {"label": "left shoulder", "bar": ls[0], "price": ls[1]},
            {"label": "head", "bar": head[0], "price": head[1]},
            {"label": "right shoulder", "bar": rs[0], "price": rs[1]},
            {"label": "neckline", "bar": n - 1, "price": neckline},
        ],
    )


def detect_double_bottom(df: pd.DataFrame) -> Optional[Pattern]:
    """Two matching troughs separated by an intervening peak."""
    win = df.iloc[-LOOKBACK:] if len(df) > LOOKBACK else df
    n = len(win)
    if n < 40:
        return None
    pl, ph = pivot_lows(win), pivot_highs(win)
    if len(pl) < 2 or not ph:
        return None

    b1, b2 = pl[-2], pl[-1]
    if b2[0] - b1[0] < 15 or b1[1] <= 0:
        return None
    if abs(b2[1] - b1[1]) / b1[1] > 0.05:
        return None

    between = [p for p in ph if b1[0] < p[0] < b2[0]]
    if not between:
        return None
    peak = max(between, key=lambda p: p[1])
    bottom = (b1[1] + b2[1]) / 2
    height = peak[1] - bottom
    if height / bottom < 0.07:
        return None

    match = 1.0 - abs(b2[1] - b1[1]) / b1[1] / 0.05
    conf = _clamp01(0.45 + 0.30 * match + 0.10)
    return Pattern(
        name="Double Bottom",
        confidence=conf,
        breakout_level=round(peak[1], 2),
        height=round(height, 2),
        target=_target(peak[1], height),
        bars=int(b2[0] - b1[0]),
        note=f"Bottoms at {b1[1]:.2f} and {b2[1]:.2f}, middle peak {peak[1]:.2f}.",
        points=[
            {"label": "first bottom", "bar": b1[0], "price": b1[1]},
            {"label": "middle peak", "bar": peak[0], "price": peak[1]},
            {"label": "second bottom", "bar": b2[0], "price": b2[1]},
        ],
    )


def detect_base(df: pd.DataFrame) -> Optional[Pattern]:
    """Tight sideways base (התכנסות) - the lowest-confidence fallback."""
    n = len(df)
    if n < 40:
        return None
    best: Optional[Pattern] = None
    for length in (15, 20, 25, 30, 40):
        if n < length + 5:
            continue
        seg = df.iloc[-length:]
        hi = float(seg["High"].max())
        lo = float(seg["Low"].min())
        if lo <= 0:
            continue
        rng = (hi - lo) / lo
        if rng > 0.18:
            continue
        # must be sideways, not a downtrend
        first = float(seg["Close"].iloc[0])
        last = float(seg["Close"].iloc[-1])
        if last < first * 0.94:
            continue
        # a base is a *contraction*, so recent range must be tighter than before
        prior = df.iloc[-(length * 2): -length]
        if len(prior) >= length // 2:
            p_hi, p_lo = float(prior["High"].max()), float(prior["Low"].min())
            if p_lo > 0 and (hi - lo) > (p_hi - p_lo) * 0.85:
                continue
        tight = 1.0 - rng / 0.18
        conf = _clamp01(0.40 + 0.25 * tight + 0.05 * (length / 40))
        if best is None or conf > best.confidence:
            best = Pattern(
                name="Base / Consolidation",
                confidence=conf,
                breakout_level=round(hi, 2),
                height=round(hi - lo, 2),
                target=_target(hi, hi - lo),
                bars=length,
                note=f"{length}-bar range of only {rng * 100:.1f}% - coiled.",
                points=[
                    {"label": "range high", "bar": n - 1, "price": hi},
                    {"label": "range low", "bar": n - 1, "price": lo},
                ],
            )
    return best


DETECTORS = (
    detect_flag,
    detect_cup_handle,
    detect_inverse_hs,
    detect_triangle,
    detect_double_bottom,
    detect_channel,
    detect_base,
)


def detect_pattern(df: pd.DataFrame) -> Pattern:
    """Run every detector and return the highest-confidence bullish formation."""
    found: List[Pattern] = []
    for fn in DETECTORS:
        try:
            p = fn(df)
        except Exception:
            p = None
        if p is not None and p.confidence >= MIN_CONFIDENCE:
            found.append(p)
    if not found:
        return Pattern()
    return max(found, key=lambda p: p.confidence)


def analyse(df: pd.DataFrame) -> dict:
    """Everything the screener needs: pattern + levels, in one call."""
    out = detect_pattern(df).as_dict()
    out.update(support_resistance(df))
    price = float(df["Close"].iloc[-1])
    bo = out.get("pattern_breakout")
    out["pct_to_breakout"] = round((bo / price - 1) * 100, 2) if bo else None
    tgt = out.get("pattern_target")
    out["pct_to_target"] = round((tgt / price - 1) * 100, 2) if tgt else None
    return out
