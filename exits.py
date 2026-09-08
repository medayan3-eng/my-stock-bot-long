"""Exit planning.

Two layers, exactly as specified:

1. Pattern-based targets (Murphy, "Technical Analysis of the Financial
   Markets"): measured moves for flags, triangles, channels, rectangles,
   cup & handle, inverse head & shoulders and double bottoms.
2. If no clean pattern exists, a mechanical profit ladder:
   +10% -> stop to breakeven, +20% -> tighter trail, +25% -> sell half and
   let the rest run on a 2*ATR trailing stop.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

PATTERNS: Dict[str, str] = {
    "Flag / Pennant": (
        "Target = breakout level + the length of the flagpole (the move that "
        "preceded the consolidation). Measured from the breakout point."
    ),
    "Symmetrical Triangle": (
        "Target = breakout level + the height of the triangle at its widest "
        "point (the base). A parallel-trendline projection gives the same result."
    ),
    "Ascending Triangle": (
        "Target = horizontal resistance + the height of the triangle base."
    ),
    "Channel / Rectangle": (
        "Target = breakout level + the height of the channel (top minus bottom)."
    ),
    "Cup & Handle": (
        "Target = breakout level + the depth of the cup (rim minus bottom)."
    ),
    "Inverse Head & Shoulders": (
        "Target = neckline + the distance from the head's low to the neckline."
    ),
    "Double Bottom": (
        "Target = breakout of the middle peak + the distance from the bottoms "
        "to that peak."
    ),
    "No clear pattern": (
        "No measured move available - manage the position with the profit "
        "ladder and the trailing stop."
    ),
}


@dataclass
class TradePlan:
    entry: float
    atr: float
    initial_stop: float
    stop_basis: str
    risk_per_share: float
    risk_pct: float
    shares: int
    position_value: float
    capital_at_risk: float
    target: Optional[float] = None
    target_basis: str = ""
    reward_risk: Optional[float] = None
    ladder: List[dict] = None


def pattern_target(pattern: str, breakout_level: float, pattern_height: float) -> Optional[float]:
    """Measured move: breakout level plus the height of the formation."""
    if pattern not in PATTERNS or pattern == "No clear pattern":
        return None
    if breakout_level is None or pattern_height is None:
        return None
    if breakout_level <= 0 or pattern_height <= 0:
        return None
    return round(breakout_level + pattern_height, 2)


def initial_stop(
    entry: float,
    atr: float,
    swing_low: Optional[float],
    cfg: dict,
) -> tuple:
    """Widest sensible stop: max(ATR stop, structural swing low) -> tightest risk."""
    mult = float(cfg["exits"]["initial_stop_atr_multiple"])
    atr_stop = entry - mult * atr if atr and atr > 0 else None
    candidates = []
    if atr_stop:
        candidates.append((atr_stop, f"{mult:g} x ATR({cfg['exits']['atr_length']})"))
    if swing_low and swing_low < entry:
        candidates.append((swing_low * 0.995, f"below the {cfg['exits']['swing_low_lookback']}-bar swing low"))

    if not candidates:
        return round(entry * 0.92, 2), "fallback 8% stop"
    # The higher stop keeps risk per share smaller.
    stop, basis = max(candidates, key=lambda c: c[0])
    return round(stop, 2), basis


def build_ladder(entry: float, atr: float, cfg: dict) -> List[dict]:
    e = cfg["exits"]
    return [
        {
            "stage": f"+{e['tier1_gain_pct']:g}% open profit",
            "price": round(entry * (1 + e["tier1_gain_pct"] / 100.0), 2),
            "action": "Raise the stop to breakeven (entry). The trade is now free.",
        },
        {
            "stage": f"+{e['tier2_gain_pct']:g}% open profit",
            "price": round(entry * (1 + e["tier2_gain_pct"] / 100.0), 2),
            "action": (
                f"Tighten to a {e['tier2_trail_atr_multiple']:g} x ATR trailing stop "
                f"(~{e['tier2_trail_atr_multiple'] * atr:.2f} below the high)."
            ),
        },
        {
            "stage": f"+{e['tier3_gain_pct']:g}% open profit",
            "price": round(entry * (1 + e["tier3_gain_pct"] / 100.0), 2),
            "action": (
                f"Sell {int(e['tier3_sell_fraction'] * 100)}% of the position. "
                f"Let the rest run on a wider {e['trail_atr_multiple']:g} x ATR trailing "
                "stop and do not touch it."
            ),
        },
    ]


def build_plan(
    entry: float,
    atr: float,
    swing_low: Optional[float],
    cfg: dict,
    pattern: str = "No clear pattern",
    breakout_level: Optional[float] = None,
    pattern_height: Optional[float] = None,
) -> TradePlan:
    stop, basis = initial_stop(entry, atr, swing_low, cfg)
    risk_per_share = max(entry - stop, 0.01)

    r = cfg["risk"]
    capital_at_risk = r["account_size"] * r["risk_per_trade_pct"] / 100.0
    shares = int(capital_at_risk // risk_per_share)

    max_value = r["account_size"] * r["max_position_pct"] / 100.0
    if entry > 0 and shares * entry > max_value:
        shares = int(max_value // entry)

    target = pattern_target(pattern, breakout_level, pattern_height)
    target_basis = PATTERNS.get(pattern, "") if target else PATTERNS["No clear pattern"]
    rr = round((target - entry) / risk_per_share, 2) if target else None

    return TradePlan(
        entry=round(entry, 2),
        atr=round(atr, 2) if atr else 0.0,
        initial_stop=stop,
        stop_basis=basis,
        risk_per_share=round(risk_per_share, 2),
        risk_pct=round(risk_per_share / entry * 100.0, 2) if entry else 0.0,
        shares=max(shares, 0),
        position_value=round(shares * entry, 2),
        capital_at_risk=round(min(shares * risk_per_share, capital_at_risk), 2),
        target=target,
        target_basis=target_basis,
        reward_risk=rr,
        ladder=build_ladder(entry, atr, cfg),
    )


def trailing_stop(highest_close: float, atr: float, multiple: float = 2.0) -> float:
    """Chandelier-style trailing stop: highest close since entry minus N x ATR."""
    return round(highest_close - multiple * atr, 2)
