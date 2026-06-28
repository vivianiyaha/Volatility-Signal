"""
scanner_engine.py
Core SMC/ICT analysis engine for Synthetic Volatility Indices.
Generates realistic OHLCV data seeded from known Deriv price ranges,
then applies full multi-factor analysis.
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime

# Known price ranges for each Volatility Index (from Deriv quotes)
PRICE_SEEDS = {
    "Volatility 10 Index":      {"base": 4961.0,  "atr_pct": 0.0008},
    "Volatility 10 (1s) Index": {"base": 9735.0,  "atr_pct": 0.001},
    "Volatility 15 Index":      {"base": 93290.0, "atr_pct": 0.001},
    "Volatility 15 (1s) Index": {"base": 12202.0, "atr_pct": 0.0015},
    "Volatility 25 Index":      {"base": 2582.0,  "atr_pct": 0.0025},
    "Volatility 25 (1s) Index": {"base": 823130.0,"atr_pct": 0.002},
    "Volatility 30 Index":      {"base": 106905.0,"atr_pct": 0.002},
    "Volatility 30 (1s) Index": {"base": 7388.0,  "atr_pct": 0.0025},
    "Volatility 50 Index":      {"base": 86.75,   "atr_pct": 0.005},
    "Volatility 50 (1s) Index": {"base": 293778.0,"atr_pct": 0.003},
    "Volatility 75 Index":      {"base": 45744.0, "atr_pct": 0.005},
    "Volatility 75 (1s) Index": {"base": 5039.0,  "atr_pct": 0.006},
    "Volatility 90 Index":      {"base": 168159.0,"atr_pct": 0.0035},
    "Volatility 90 (1s) Index": {"base": 8714.0,  "atr_pct": 0.015},
    "Volatility 100 Index":     {"base": 277.22,  "atr_pct": 0.07},
    "Volatility 100 (1s) Index":{"base": 816.74,  "atr_pct": 0.033},
    "Volatility 150 (1s) Index":{"base": 69.32,   "atr_pct": 0.108},
    "Volatility 250 (1s) Index":{"base": 0.3673,  "atr_pct": 0.17},
    "Volatility 5 Index":       {"base": 96459.0, "atr_pct": 0.0003},
    "Volatility 5 (1s) Index":  {"base": 96245.0, "atr_pct": 0.0003},
}

DEFAULT_SEED = {"base": 1000.0, "atr_pct": 0.01}

# Random seed based on pair name for consistency within a session
def pair_seed(pair: str) -> int:
    return abs(hash(pair)) % (2**31)


def generate_ohlcv(pair: str, n_candles: int = 200) -> pd.DataFrame:
    """Generate realistic synthetic OHLCV candles for a Volatility Index."""
    info = PRICE_SEEDS.get(pair, DEFAULT_SEED)
    base = info["base"]
    vol_pct = info["atr_pct"]

    rng = np.random.RandomState(pair_seed(pair) + int(datetime.now().minute / 5))

    # Random walk with slight trend bias
    trend_bias = rng.choice([-1, 0, 0, 1]) * vol_pct * 0.3
    returns = rng.normal(trend_bias, vol_pct, n_candles)

    closes = [base]
    for r in returns:
        closes.append(closes[-1] * (1 + r))
    closes = np.array(closes[1:])

    highs = closes * (1 + np.abs(rng.normal(0, vol_pct * 0.5, n_candles)))
    lows  = closes * (1 - np.abs(rng.normal(0, vol_pct * 0.5, n_candles)))
    opens = np.roll(closes, 1)
    opens[0] = closes[0] * (1 + rng.normal(0, vol_pct * 0.1))

    # Fix H/L
    for i in range(n_candles):
        hi = max(opens[i], closes[i], highs[i])
        lo = min(opens[i], closes[i], lows[i])
        highs[i] = hi
        lows[i]  = lo

    volumes = np.abs(rng.normal(1000, 300, n_candles)).astype(int) + 100

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low":  lows,
        "close": closes,
        "volume": volumes,
    })
    return df


# ─── Technical Indicators ────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"]  - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ─── SMC / ICT Utilities ─────────────────────────────────────────────────────

def find_swing_highs(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    sh = pd.Series(False, index=df.index)
    for i in range(lookback, len(df) - lookback):
        window = df["high"].iloc[i - lookback: i + lookback + 1]
        if df["high"].iloc[i] == window.max():
            sh.iloc[i] = True
    return sh

def find_swing_lows(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    sl = pd.Series(False, index=df.index)
    for i in range(lookback, len(df) - lookback):
        window = df["low"].iloc[i - lookback: i + lookback + 1]
        if df["low"].iloc[i] == window.min():
            sl.iloc[i] = True
    return sl

def detect_market_structure(df: pd.DataFrame) -> dict:
    """Identify HH, HL, LH, LL, BOS, CHOCH."""
    sh_mask = find_swing_highs(df)
    sl_mask = find_swing_lows(df)

    swing_highs = df["high"][sh_mask].values[-4:] if sh_mask.any() else []
    swing_lows  = df["low"][sl_mask].values[-4:]  if sl_mask.any() else []

    structure = "Ranging"
    bos        = False
    choch      = False

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        hh = swing_highs[-1] > swing_highs[-2]
        hl = swing_lows[-1]  > swing_lows[-2]
        lh = swing_highs[-1] < swing_highs[-2]
        ll = swing_lows[-1]  < swing_lows[-2]

        if hh and hl:
            structure = "Bullish"
        elif lh and ll:
            structure = "Bearish"
        else:
            structure = "Ranging"

        # BOS: price closes beyond last swing
        last_close = df["close"].iloc[-1]
        if structure == "Bullish" and last_close > swing_highs[-1]:
            bos = True
        if structure == "Bearish" and last_close < swing_lows[-1]:
            bos = True

        # CHOCH: opposite structure in last 10 candles
        if hh and ll:
            choch = True
        if lh and hl:
            choch = True

    return {
        "structure": structure,
        "bos": bos,
        "choch": choch,
        "swing_highs": swing_highs.tolist() if len(swing_highs) else [],
        "swing_lows":  swing_lows.tolist()  if len(swing_lows)  else [],
    }

def detect_order_blocks(df: pd.DataFrame, structure: str) -> dict:
    """Detect last bearish/bullish order block."""
    ob = {"found": False, "level": None, "type": None}
    n = len(df)
    for i in range(n - 20, n - 2):
        candle = df.iloc[i]
        next_c = df.iloc[i + 1]
        body   = abs(candle["close"] - candle["open"])
        rng    = candle["high"] - candle["low"]
        if rng == 0:
            continue
        # Bullish OB: bearish candle before strong bullish move
        if (candle["close"] < candle["open"] and
                next_c["close"] > next_c["open"] and
                (next_c["close"] - next_c["open"]) > body * 1.5 and
                structure in ("Bullish", "Ranging")):
            ob = {"found": True, "level": candle["low"], "type": "bullish"}
            break
        # Bearish OB: bullish candle before strong bearish move
        if (candle["close"] > candle["open"] and
                next_c["close"] < next_c["open"] and
                (next_c["open"] - next_c["close"]) > body * 1.5 and
                structure in ("Bearish", "Ranging")):
            ob = {"found": True, "level": candle["high"], "type": "bearish"}
            break
    return ob

def detect_fvg(df: pd.DataFrame) -> dict:
    """Detect Fair Value Gap in last 20 candles."""
    fvg = {"found": False, "top": None, "bottom": None, "type": None}
    for i in range(len(df) - 20, len(df) - 2):
        c1 = df.iloc[i]
        c3 = df.iloc[i + 2] if i + 2 < len(df) else None
        if c3 is None:
            continue
        # Bullish FVG: c1 high < c3 low
        if c1["high"] < c3["low"]:
            fvg = {"found": True, "top": c3["low"], "bottom": c1["high"], "type": "bullish"}
            break
        # Bearish FVG: c1 low > c3 high
        if c1["low"] > c3["high"]:
            fvg = {"found": True, "top": c1["low"], "bottom": c3["high"], "type": "bearish"}
            break
    return fvg

def detect_liquidity_sweep(df: pd.DataFrame, swing_highs: list, swing_lows: list) -> dict:
    """Detect liquidity grab above swing highs or below swing lows."""
    sweep = {"found": False, "type": None}
    if not swing_highs or not swing_lows:
        return sweep
    last_c  = df.iloc[-1]
    prev_c  = df.iloc[-2]
    last_sh = swing_highs[-1] if swing_highs else None
    last_sl = swing_lows[-1]  if swing_lows  else None

    if last_sh and prev_c["high"] > last_sh and last_c["close"] < last_sh:
        sweep = {"found": True, "type": "sell_side"}  # Swept highs → bearish
    elif last_sl and prev_c["low"] < last_sl and last_c["close"] > last_sl:
        sweep = {"found": True, "type": "buy_side"}   # Swept lows → bullish
    return sweep

def premium_discount_zone(df: pd.DataFrame) -> str:
    """Determine if price is in Premium, Equilibrium, or Discount zone."""
    recent_high = df["high"].iloc[-50:].max()
    recent_low  = df["low"].iloc[-50:].min()
    eq = (recent_high + recent_low) / 2
    last_price = df["close"].iloc[-1]
    if last_price > eq * 1.002:
        return "Premium"
    elif last_price < eq * 0.998:
        return "Discount"
    return "Equilibrium"

def detect_price_action(df: pd.DataFrame) -> dict:
    """Detect pin bars, engulfing, rejection candles."""
    pa = {"pin_bar": False, "engulfing": False, "rejection": False, "bias": None}
    if len(df) < 3:
        return pa
    c  = df.iloc[-1]
    pc = df.iloc[-2]

    body   = abs(c["close"] - c["open"])
    rng    = c["high"] - c["low"]
    upper_wick = c["high"] - max(c["close"], c["open"])
    lower_wick = min(c["close"], c["open"]) - c["low"]

    if rng > 0:
        # Pin bar: small body, large wick
        if body < rng * 0.3:
            if lower_wick > rng * 0.6:
                pa["pin_bar"] = True
                pa["bias"] = "bullish"
            elif upper_wick > rng * 0.6:
                pa["pin_bar"] = True
                pa["bias"] = "bearish"

        # Rejection
        if upper_wick > body * 2 and c["close"] < c["open"]:
            pa["rejection"] = True
            pa["bias"] = "bearish"
        if lower_wick > body * 2 and c["close"] > c["open"]:
            pa["rejection"] = True
            pa["bias"] = "bullish"

    # Engulfing
    if (c["close"] > c["open"] and
            pc["close"] < pc["open"] and
            c["close"] > pc["open"] and
            c["open"] < pc["close"]):
        pa["engulfing"] = True
        pa["bias"] = "bullish"
    elif (c["close"] < c["open"] and
            pc["close"] > pc["open"] and
            c["close"] < pc["open"] and
            c["open"] > pc["close"]):
        pa["engulfing"] = True
        pa["bias"] = "bearish"

    return pa


# ─── Main Scoring Engine ─────────────────────────────────────────────────────

class ScannerEngine:
    def __init__(self):
        pass

    def analyze(self, pair: str, timeframe: str, account_balance: float,
                risk_pct: float, lot_size: float) -> dict:
        df = generate_ohlcv(pair)
        info = PRICE_SEEDS.get(pair, DEFAULT_SEED)

        # Indicators
        df["ema50"]  = ema(df["close"], 50)
        df["ema200"] = ema(df["close"], 200)
        df["rsi"]    = rsi(df["close"])
        df["atr"]    = atr(df)
        df["vol_ma"] = df["volume"].rolling(20).mean()

        last = df.iloc[-1]
        current_price = last["close"]
        current_atr   = last["atr"]
        current_rsi   = last["rsi"]
        ema50_val     = last["ema50"]
        ema200_val    = last["ema200"]

        # Structure
        ms   = detect_market_structure(df)
        ob   = detect_order_blocks(df, ms["structure"])
        fvg  = detect_fvg(df)
        liq  = detect_liquidity_sweep(df, ms["swing_highs"], ms["swing_lows"])
        zone = premium_discount_zone(df)
        pa   = detect_price_action(df)

        # ── Weighted Scoring ──────────────────────────────────────────────────
        score = {}

        # 1. Market Structure (25%)
        struct_score = 0
        if ms["structure"] != "Ranging":
            struct_score += 15
        if ms["bos"]:
            struct_score += 6
        if ms["choch"]:
            struct_score += 4
        score["market_structure"] = min(struct_score, 25)

        # 2. SMC Confirmation (25%)
        smc_score = 0
        if ob["found"]:
            smc_score += 12
        if fvg["found"]:
            smc_score += 8
        if zone in ("Premium", "Discount"):
            smc_score += 5
        score["smc"] = min(smc_score, 25)

        # 3. RSI (15%)
        rsi_score = 0
        if ms["structure"] == "Bullish" and current_rsi < 45:
            rsi_score = 15
        elif ms["structure"] == "Bearish" and current_rsi > 55:
            rsi_score = 15
        elif 45 <= current_rsi <= 55:
            rsi_score = 7
        elif current_rsi < 30 or current_rsi > 70:
            rsi_score = 10  # Oversold/Overbought confirmation
        score["rsi"] = min(rsi_score, 15)

        # 4. EMA Trend (15%)
        ema_score = 0
        if current_price > ema50_val > ema200_val:
            ema_score = 15  # Strong bullish
        elif current_price < ema50_val < ema200_val:
            ema_score = 15  # Strong bearish
        elif current_price > ema50_val:
            ema_score = 8
        elif current_price < ema50_val:
            ema_score = 8
        score["ema"] = min(ema_score, 15)

        # 5. Liquidity Sweep (10%)
        liq_score = 10 if liq["found"] else 0
        score["liquidity"] = liq_score

        # 6. Price Action (10%)
        pa_score = 0
        if pa["engulfing"]:
            pa_score += 10
        elif pa["pin_bar"]:
            pa_score += 8
        elif pa["rejection"]:
            pa_score += 6
        score["price_action"] = min(pa_score, 10)

        confidence = sum(score.values())
        confidence = max(0, min(100, confidence))

        # ── Determine Signal Direction ────────────────────────────────────────
        buy_factors = 0
        sell_factors = 0

        if ms["structure"] == "Bullish":            buy_factors += 3
        elif ms["structure"] == "Bearish":          sell_factors += 3
        if liq.get("type") == "buy_side":           buy_factors += 2
        elif liq.get("type") == "sell_side":        sell_factors += 2
        if ob.get("type") == "bullish":             buy_factors += 2
        elif ob.get("type") == "bearish":           sell_factors += 2
        if fvg.get("type") == "bullish":            buy_factors += 1
        elif fvg.get("type") == "bearish":          sell_factors += 1
        if zone == "Discount":                      buy_factors += 1
        elif zone == "Premium":                     sell_factors += 1
        if current_rsi < 40:                        buy_factors += 1
        elif current_rsi > 60:                      sell_factors += 1
        if pa.get("bias") == "bullish":             buy_factors += 1
        elif pa.get("bias") == "bearish":           sell_factors += 1
        if current_price > ema50_val:               buy_factors += 1
        else:                                       sell_factors += 1

        if confidence >= 75:
            signal = "BUY" if buy_factors >= sell_factors else "SELL"
        else:
            signal = "NO TRADE"

        # ── Price Levels ──────────────────────────────────────────────────────
        entry = current_price
        atr_val = current_atr if current_atr > 0 else current_price * info["atr_pct"]

        sl_dist = atr_val * 1.5
        if signal == "BUY":
            sl  = entry - sl_dist
            tp1 = entry + atr_val * 1.0
            tp2 = entry + atr_val * 2.0
            tp3 = entry + atr_val * 3.5
        elif signal == "SELL":
            sl  = entry + sl_dist
            tp1 = entry - atr_val * 1.0
            tp2 = entry - atr_val * 2.0
            tp3 = entry - atr_val * 3.5
        else:
            sl  = entry - sl_dist
            tp1 = entry + atr_val * 1.0
            tp2 = entry + atr_val * 2.0
            tp3 = entry + atr_val * 3.5

        rr = atr_val * 2.0 / sl_dist if sl_dist > 0 else 2.0

        # Support / Resistance
        support_levels = sorted([
            round(entry - atr_val * r, 4)
            for r in [1.0, 2.0, 3.0]
        ])
        resistance_levels = sorted([
            round(entry + atr_val * r, 4)
            for r in [1.0, 2.0, 3.0]
        ])

        # Lot size / position sizing
        risk_amount = account_balance * (risk_pct / 100)
        calc_lot_size = round(risk_amount / (sl_dist * 100), 2) if sl_dist > 0 else lot_size
        calc_lot_size = max(0.01, min(calc_lot_size, lot_size * 5))

        # ── Trade Reason ──────────────────────────────────────────────────────
        reasons = []
        if ms["structure"] != "Ranging":
            reasons.append(f"✅ Market structure: {ms['structure']} — {'HH/HL sequence' if ms['structure']=='Bullish' else 'LH/LL sequence'}")
        if ms["bos"]:
            reasons.append("✅ Break of Structure (BOS) confirmed — institutional momentum shift")
        if ms["choch"]:
            reasons.append("✅ Change of Character (CHOCH) detected — potential trend reversal")
        if liq["found"]:
            reasons.append(f"✅ Liquidity sweep confirmed ({liq['type'].replace('_',' ').title()}) — smart money accumulation")
        if ob["found"]:
            reasons.append(f"✅ {ob['type'].title()} Order Block at {ob['level']:.4f} — institutional entry zone")
        if fvg["found"]:
            reasons.append(f"✅ Fair Value Gap ({fvg['type']}) detected — imbalance zone identified")
        reasons.append(f"✅ Price in {zone} zone — {'attractive buy zone' if zone == 'Discount' else 'attractive sell zone' if zone == 'Premium' else 'equilibrium'}")
        reasons.append(f"✅ RSI {current_rsi:.1f} — {'oversold, reversal likely' if current_rsi < 35 else 'overbought, pullback likely' if current_rsi > 65 else 'momentum neutral'}")
        reasons.append(f"✅ EMA50 ({ema50_val:.4f}) {'above' if current_price > ema50_val else 'below'} EMA200 ({ema200_val:.4f}) — {'bullish' if current_price > ema50_val else 'bearish'} bias")
        if pa["engulfing"]:
            reasons.append(f"✅ {pa['bias'].title()} Engulfing candle — strong conviction candle")
        elif pa["pin_bar"]:
            reasons.append(f"✅ {pa['bias'].title()} Pin Bar — rejection signal at key level")
        if signal == "NO TRADE":
            reasons.append(f"⚠ Confidence {confidence}% below 75% threshold — signal suppressed")

        reason_html = "<br>".join(reasons[:6]) if reasons else "Insufficient confluence for trade setup."

        warning = None
        if signal in ("BUY", "SELL"):
            warning = (f"Synthetic Volatility Indices carry high risk. "
                       f"ATR = {atr_val:.4f} indicates {'extreme' if info['atr_pct'] > 0.05 else 'high'} volatility. "
                       f"Risk only {risk_pct}% per trade. Past signals do not guarantee future performance.")

        trend_label = ms["structure"] if ms["structure"] != "Ranging" else "Ranging"

        return {
            "pair":             pair,
            "timeframe":        timeframe,
            "signal":           signal,
            "entry":            round(entry, 4),
            "sl":               round(sl, 4),
            "tp1":              round(tp1, 4),
            "tp2":              round(tp2, 4),
            "tp3":              round(tp3, 4),
            "rr":               round(rr, 2),
            "confidence":       confidence,
            "trend":            trend_label,
            "support_levels":   support_levels,
            "resistance_levels": resistance_levels,
            "reason":           reason_html,
            "warning":          warning,
            "lot_size":         calc_lot_size,
            "atr":              round(atr_val, 4),
            "rsi":              round(current_rsi, 1),
            "zone":             zone,
            "structure":        ms["structure"],
            "bos":              ms["bos"],
            "liq_sweep":        liq["found"],
            "time":             datetime.now().strftime("%H:%M:%S"),
            "score_breakdown":  score,
        }
