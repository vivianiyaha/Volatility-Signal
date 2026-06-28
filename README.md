# ⬡ AI SCANNER — Synthetic Volatility Intelligence

**Production-ready Streamlit SMC/ICT trading scanner for Deriv Synthetic Indices.**

## Features
- 🔮 Full SMC analysis: BOS, CHOCH, Order Blocks, FVG, Liquidity Sweeps
- 📊 ICT concepts: Premium/Discount zones, Market Maker Model
- 📈 Technical indicators: EMA50, EMA200, RSI 14, ATR, Volume
- 🎯 6-factor weighted confidence scoring (75%+ threshold)
- 💡 BUY/SELL signals with Entry, SL, TP1, TP2, TP3
- ⚙ Background scanner (every 60s) — runs even when tab is idle
- 🗄 SQLite persistence (signals, trades, account_history, daily_summary)
- 🎨 Purple / Black / Violet / Burnt-Orange professional theme

## Supported Markets
All 20 Deriv Volatility Indices including:
- Volatility 10/15/25/30/50/75/90/100 Index
- Volatility 5/150/250 (1s) Index variants

## Setup
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Usage
1. Open sidebar → set account balance, risk %, select pairs & timeframe
2. Click **START** — scanner launches background thread + immediate scan
3. Signals appear in real-time with full trade plans
4. Click **STOP** to halt; **SCAN NOW** for immediate manual scan
5. All signals & trades saved to `ai_scanner.db`

## Confidence Scoring
| Factor | Weight |
|---|---|
| Market Structure (HH/HL/LH/LL, BOS, CHOCH) | 25% |
| SMC (Order Blocks, FVG, Premium/Discount) | 25% |
| RSI 14 Confirmation | 15% |
| EMA 50/200 Trend | 15% |
| Liquidity Sweep | 10% |
| Price Action (Engulfing, Pin Bar, Rejection) | 10% |

Signals only generated when **confidence ≥ 75%**.

## Risk Warning
Synthetic Volatility Indices are high-risk instruments. This scanner is for
educational and analytical purposes. Trade responsibly.
