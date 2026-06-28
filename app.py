import streamlit as st
import pandas as pd
import numpy as np
import time
import threading
import json
from datetime import datetime, timedelta
import sqlite3
import os
import random

from scanner_engine import ScannerEngine
from database import DatabaseManager
from signal_generator import SignalGenerator
from risk_manager import RiskManager
from ui_components import render_metric_card, render_signal_card, render_trade_row

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI SCANNER — Synthetic Indices",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS Theme ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --purple: #7B2FBE;
    --violet: #9D4EDD;
    --light-violet: #C77DFF;
    --burnt-orange: #CC5500;
    --orange-glow: #E07B39;
    --black: #0A0A0F;
    --dark: #0F0F1A;
    --card: #13131F;
    --card2: #1A1A2E;
    --border: #2A2A45;
    --text: #E8E8F0;
    --muted: #6B6B8A;
    --green: #00E5A0;
    --red: #FF4466;
    --blue: #4488FF;
}

* { font-family: 'Space Grotesk', sans-serif !important; box-sizing: border-box; }

html, body, .stApp {
    background-color: var(--black) !important;
    color: var(--text) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F0F1A 0%, #13131F 100%) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSlider label {
    color: var(--light-violet) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* Inputs */
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
}
.stSelectbox > div > div:hover,
.stNumberInput > div > div > input:focus {
    border-color: var(--violet) !important;
    box-shadow: 0 0 0 2px rgba(157,78,221,0.2) !important;
}

/* Buttons */
.stButton > button {
    width: 100% !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    border: none !important;
    transition: all 0.2s !important;
    padding: 10px 16px !important;
}
.stButton > button:first-child { background: linear-gradient(135deg, var(--purple), var(--violet)) !important; color: white !important; }
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 4px 20px rgba(123,47,190,0.4) !important; }

/* Metric cards */
.metric-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--purple), var(--violet), var(--burnt-orange));
}
.metric-label { font-size: 11px; color: var(--muted); font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 6px; }
.metric-value { font-size: 24px; font-weight: 700; font-family: 'JetBrains Mono', monospace !important; }
.metric-sub { font-size: 11px; color: var(--muted); margin-top: 4px; }
.positive { color: var(--green) !important; }
.negative { color: var(--red) !important; }
.neutral { color: var(--light-violet) !important; }

/* Signal cards */
.signal-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
}
.signal-card.buy { border-left: 3px solid var(--green); }
.signal-card.sell { border-left: 3px solid var(--red); }
.signal-card.no-trade { border-left: 3px solid var(--muted); }
.signal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.signal-pair { font-size: 18px; font-weight: 700; color: var(--light-violet); }
.signal-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
.badge-buy { background: rgba(0,229,160,0.15); color: var(--green); border: 1px solid rgba(0,229,160,0.3); }
.badge-sell { background: rgba(255,68,102,0.15); color: var(--red); border: 1px solid rgba(255,68,102,0.3); }
.badge-wait { background: rgba(107,107,138,0.15); color: var(--muted); border: 1px solid rgba(107,107,138,0.3); }
.signal-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.signal-field { background: var(--card2); border-radius: 8px; padding: 10px 14px; }
.field-label { font-size: 10px; color: var(--muted); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
.field-value { font-size: 14px; font-weight: 600; font-family: 'JetBrains Mono', monospace !important; margin-top: 2px; }
.confidence-bar { background: var(--card2); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; }
.conf-track { height: 6px; background: var(--border); border-radius: 3px; margin-top: 8px; overflow: hidden; }
.conf-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, var(--purple), var(--burnt-orange)); }
.reason-box { background: var(--card2); border-radius: 8px; padding: 12px 14px; font-size: 12px; color: var(--muted); line-height: 1.6; }
.reason-title { color: var(--light-violet); font-weight: 600; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }

/* Section headers */
.section-header {
    display: flex; align-items: center; gap: 10px;
    font-size: 13px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px; margin-bottom: 16px;
}
.section-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--violet); display: inline-block; }

/* Log */
.log-container { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; max-height: 280px; overflow-y: auto; font-family: 'JetBrains Mono', monospace !important; font-size: 12px; }
.log-entry { padding: 4px 0; border-bottom: 1px solid rgba(42,42,69,0.5); color: var(--muted); }
.log-entry .log-time { color: var(--violet); margin-right: 8px; }
.log-entry .log-msg { color: var(--text); }
.log-entry.buy .log-msg { color: var(--green); }
.log-entry.sell .log-msg { color: var(--red); }
.log-entry.info .log-msg { color: var(--light-violet); }
.log-entry.warn .log-msg { color: var(--orange-glow); }

/* Status indicator */
.status-indicator {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 14px; border-radius: 20px;
    font-size: 12px; font-weight: 600; letter-spacing: 1px;
}
.status-running { background: rgba(0,229,160,0.1); color: var(--green); border: 1px solid rgba(0,229,160,0.25); }
.status-stopped { background: rgba(107,107,138,0.1); color: var(--muted); border: 1px solid rgba(107,107,138,0.25); }
.pulse { width: 8px; height: 8px; border-radius: 50%; }
.pulse-green { background: var(--green); animation: pulse 1.5s infinite; }
.pulse-gray { background: var(--muted); }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }

/* Title */
.app-title {
    font-size: 28px; font-weight: 700;
    background: linear-gradient(135deg, var(--light-violet), var(--burnt-orange));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
}
.app-sub { font-size: 12px; color: var(--muted); letter-spacing: 2px; text-transform: uppercase; margin-top: -4px; }

/* Table */
.trade-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.trade-table th { background: var(--card2); color: var(--muted); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; font-size: 10px; padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
.trade-table td { padding: 10px 12px; border-bottom: 1px solid rgba(42,42,69,0.4); color: var(--text); font-family: 'JetBrains Mono', monospace; }
.trade-table tr:hover td { background: rgba(157,78,221,0.05); }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--card); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--violet); }

/* Divider */
hr { border-color: var(--border) !important; }

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; }

/* Multiselect */
.stMultiSelect > div { background: var(--card2) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ───────────────────────────────────────────────────────
if "bot_running" not in st.session_state:
    st.session_state.bot_running = False
if "signals" not in st.session_state:
    st.session_state.signals = []
if "open_trades" not in st.session_state:
    st.session_state.open_trades = []
if "closed_trades" not in st.session_state:
    st.session_state.closed_trades = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "session_pnl" not in st.session_state:
    st.session_state.session_pnl = 0.0
if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0
if "last_scan_time" not in st.session_state:
    st.session_state.last_scan_time = None
if "account_balance" not in st.session_state:
    st.session_state.account_balance = 10000.0
if "wins" not in st.session_state:
    st.session_state.wins = 0
if "losses" not in st.session_state:
    st.session_state.losses = 0
if "scan_thread" not in st.session_state:
    st.session_state.scan_thread = None

# ─── All Volatility Pairs ─────────────────────────────────────────────────────
ALL_PAIRS = [
    "Volatility 10 Index",
    "Volatility 10 (1s) Index",
    "Volatility 15 Index",
    "Volatility 15 (1s) Index",
    "Volatility 25 Index",
    "Volatility 25 (1s) Index",
    "Volatility 30 Index",
    "Volatility 30 (1s) Index",
    "Volatility 50 Index",
    "Volatility 50 (1s) Index",
    "Volatility 75 Index",
    "Volatility 75 (1s) Index",
    "Volatility 90 Index",
    "Volatility 90 (1s) Index",
    "Volatility 100 Index",
    "Volatility 100 (1s) Index",
    "Volatility 150 (1s) Index",
    "Volatility 250 (1s) Index",
    "Volatility 5 Index",
    "Volatility 5 (1s) Index",
]

TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4"]

# ─── DB + Engine Init ─────────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    return DatabaseManager("ai_scanner.db")

@st.cache_resource
def get_engine():
    return ScannerEngine()

db = get_db()
engine = get_engine()

def add_log(msg, kind="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, {"time": ts, "msg": msg, "kind": kind})
    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[:200]

def run_scan(pairs, timeframe, risk_pct, lot_size, account_balance, daily_loss_limit, max_trades):
    """Run one scan cycle — called by background thread and direct trigger."""
    if not st.session_state.bot_running:
        return
    st.session_state.scan_count += 1
    st.session_state.last_scan_time = datetime.now().strftime("%H:%M:%S")
    add_log(f"Scan #{st.session_state.scan_count} started — {len(pairs)} pairs on {timeframe}", "info")

    new_signals = []
    for pair in pairs:
        if not st.session_state.bot_running:
            break
        sig = engine.analyze(pair, timeframe, account_balance, risk_pct, lot_size)
        new_signals.append(sig)
        db.save_signal(sig)
        if sig["signal"] in ("BUY", "SELL"):
            add_log(f"Signal: {sig['signal']} {pair} @ {sig['entry']:.4f} | Conf {sig['confidence']}%", sig["signal"].lower())
        else:
            add_log(f"No trade — {pair} (Conf {sig['confidence']}%)", "info")

    st.session_state.signals = new_signals
    add_log(f"Scan #{st.session_state.scan_count} complete.", "info")

def background_scanner(pairs, timeframe, risk_pct, lot_size, account_balance, daily_loss_limit, max_trades):
    """Runs in background thread, scans every 60s."""
    while st.session_state.bot_running:
        run_scan(pairs, timeframe, risk_pct, lot_size, account_balance, daily_loss_limit, max_trades)
        for _ in range(60):
            if not st.session_state.bot_running:
                break
            time.sleep(1)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="app-title">⬡ AI SCANNER</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub">Synthetic Indices · SMC/ICT</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="section-header"><span class="section-dot"></span>Account</div>', unsafe_allow_html=True)
    account_balance_input = st.number_input("Account Balance ($)", min_value=100.0, max_value=1_000_000.0,
                                             value=st.session_state.account_balance, step=100.0)
    st.session_state.account_balance = account_balance_input

    risk_pct = st.slider("Risk Per Trade (%)", 0.5, 5.0, 1.0, 0.1)
    daily_loss_limit = st.number_input("Daily Loss Limit ($)", min_value=10.0, value=200.0, step=10.0)
    max_trades = st.number_input("Max Open Trades", min_value=1, max_value=20, value=5, step=1)

    st.markdown("---")
    st.markdown('<div class="section-header"><span class="section-dot"></span>Market Setup</div>', unsafe_allow_html=True)
    selected_pairs = st.multiselect("Select Pairs", ALL_PAIRS, default=["Volatility 75 Index", "Volatility 100 Index", "Volatility 50 Index"])
    timeframe = st.selectbox("Timeframe", TIMEFRAMES, index=2)
    lot_size = st.number_input("Lot Size", min_value=0.01, max_value=100.0, value=0.01, step=0.01)

    st.markdown("---")
    st.markdown('<div class="section-header"><span class="section-dot"></span>Controls</div>', unsafe_allow_html=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("▶ START", key="start_btn"):
            if not st.session_state.bot_running:
                if not selected_pairs:
                    st.warning("Select at least one pair.")
                else:
                    st.session_state.bot_running = True
                    add_log("Bot started — scanning every 60s", "info")
                    # Start background thread
                    t = threading.Thread(
                        target=background_scanner,
                        args=(selected_pairs, timeframe, risk_pct, lot_size,
                              st.session_state.account_balance, daily_loss_limit, max_trades),
                        daemon=True
                    )
                    t.start()
                    st.session_state.scan_thread = t
                    # Immediate first scan
                    run_scan(selected_pairs, timeframe, risk_pct, lot_size,
                             st.session_state.account_balance, daily_loss_limit, max_trades)
    with col_s2:
        if st.button("■ STOP", key="stop_btn"):
            st.session_state.bot_running = False
            add_log("Bot stopped by user.", "warn")

    if st.button("↺ RESET SESSION", key="reset_btn"):
        st.session_state.signals = []
        st.session_state.open_trades = []
        st.session_state.closed_trades = []
        st.session_state.logs = []
        st.session_state.session_pnl = 0.0
        st.session_state.scan_count = 0
        st.session_state.wins = 0
        st.session_state.losses = 0
        st.session_state.bot_running = False
        add_log("Session reset.", "warn")

    if st.button("✕ CLOSE ALL TRADES", key="close_all_btn"):
        closed = len(st.session_state.open_trades)
        for t in st.session_state.open_trades:
            t["close_time"] = datetime.now().strftime("%H:%M:%S")
            t["pnl"] = 0.0
            st.session_state.closed_trades.append(t)
        st.session_state.open_trades = []
        add_log(f"Closed {closed} trades manually.", "warn")

    st.markdown("---")
    # Status
    if st.session_state.bot_running:
        st.markdown('<div class="status-indicator status-running"><span class="pulse pulse-green"></span>SCANNING LIVE</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-indicator status-stopped"><span class="pulse pulse-gray"></span>INACTIVE</div>', unsafe_allow_html=True)

    if st.session_state.last_scan_time:
        st.caption(f"Last scan: {st.session_state.last_scan_time} · #{st.session_state.scan_count}")

    # Manual scan trigger
    if st.button("⟳ SCAN NOW", key="scan_now"):
        if selected_pairs:
            run_scan(selected_pairs, timeframe, risk_pct, lot_size,
                     st.session_state.account_balance, daily_loss_limit, max_trades)
        else:
            st.warning("Select pairs first.")

# ─── MAIN DASHBOARD ───────────────────────────────────────────────────────────
st.markdown('<div class="app-title" style="font-size:22px;">⬡ AI SCANNER — Synthetic Volatility Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">SMC · ICT · Price Action · Multi-Timeframe Analysis</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─── Account Metrics ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header"><span class="section-dot"></span>Account Overview</div>', unsafe_allow_html=True)
total_trades = st.session_state.wins + st.session_state.losses
win_rate = (st.session_state.wins / total_trades * 100) if total_trades > 0 else 0.0
equity = st.session_state.account_balance + st.session_state.session_pnl
pnl_color = "positive" if st.session_state.session_pnl >= 0 else "negative"
pnl_sign = "+" if st.session_state.session_pnl >= 0 else ""

m1, m2, m3, m4, m5, m6 = st.columns(6)
metrics = [
    (m1, "Balance", f"${st.session_state.account_balance:,.2f}", "Session start", "neutral"),
    (m2, "Equity", f"${equity:,.2f}", "Live equity", "positive" if equity >= st.session_state.account_balance else "negative"),
    (m3, "Session P/L", f"{pnl_sign}${st.session_state.session_pnl:,.2f}", "This session", pnl_color),
    (m4, "Win Rate", f"{win_rate:.1f}%", f"{st.session_state.wins}W / {st.session_state.losses}L", "neutral"),
    (m5, "Open Trades", str(len(st.session_state.open_trades)), f"Max: {max_trades}", "neutral"),
    (m6, "Signals Today", str(len(st.session_state.signals)), f"Scan #{st.session_state.scan_count}", "neutral"),
]
for col, label, val, sub, color in metrics:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {color}">{val}</div>
            <div class="metric-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Signals + Log Layout ────────────────────────────────────────────────────
col_signals, col_log = st.columns([2, 1])

with col_signals:
    st.markdown('<div class="section-header"><span class="section-dot"></span>Live Signals</div>', unsafe_allow_html=True)

    if not st.session_state.signals:
        st.markdown("""
        <div style="background:var(--card);border:1px dashed var(--border);border-radius:12px;
                    padding:40px;text-align:center;color:var(--muted);">
            <div style="font-size:32px;margin-bottom:12px;">🔍</div>
            <div style="font-size:14px;font-weight:600;">No signals yet</div>
            <div style="font-size:12px;margin-top:6px;">Select pairs, click START or SCAN NOW</div>
        </div>""", unsafe_allow_html=True)
    else:
        for sig in st.session_state.signals:
            s = sig["signal"]
            badge_class = "badge-buy" if s == "BUY" else ("badge-sell" if s == "SELL" else "badge-wait")
            card_class = "buy" if s == "BUY" else ("sell" if s == "SELL" else "no-trade")
            conf = sig["confidence"]
            conf_color = "#00E5A0" if conf >= 80 else ("#E07B39" if conf >= 75 else "#6B6B8A")

            tp_grid = ""
            if s in ("BUY", "SELL"):
                tp_grid = f"""
                <div class="signal-grid">
                    <div class="signal-field">
                        <div class="field-label">Entry</div>
                        <div class="field-value neutral">{sig['entry']:.4f}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Stop Loss</div>
                        <div class="field-value negative">{sig['sl']:.4f}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">R:R Ratio</div>
                        <div class="field-value neutral">1 : {sig['rr']:.1f}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Take Profit 1</div>
                        <div class="field-value positive">{sig['tp1']:.4f}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Take Profit 2</div>
                        <div class="field-value positive">{sig['tp2']:.4f}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Take Profit 3</div>
                        <div class="field-value positive">{sig['tp3']:.4f}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Trend</div>
                        <div class="field-value" style="color:{'#00E5A0' if sig['trend']=='Bullish' else '#FF4466' if sig['trend']=='Bearish' else '#C77DFF'}">{sig['trend']}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Timeframe</div>
                        <div class="field-value neutral">{sig['timeframe']}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Lot Size</div>
                        <div class="field-value neutral">{sig['lot_size']:.2f}</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
                    <div class="signal-field">
                        <div class="field-label">Support Levels</div>
                        <div class="field-value" style="font-size:12px;color:var(--green);">{'  |  '.join([f"{s:.4f}" for s in sig['support_levels']])}</div>
                    </div>
                    <div class="signal-field">
                        <div class="field-label">Resistance Levels</div>
                        <div class="field-value" style="font-size:12px;color:var(--red);">{'  |  '.join([f"{r:.4f}" for r in sig['resistance_levels']])}</div>
                    </div>
                </div>"""

            st.markdown(f"""
            <div class="signal-card {card_class}">
                <div class="signal-header">
                    <div>
                        <span class="signal-pair">{sig['pair']}</span>
                        <span style="font-size:11px;color:var(--muted);margin-left:10px;">{sig['time']}</span>
                    </div>
                    <span class="signal-badge {badge_class}">{s}</span>
                </div>
                {tp_grid}
                <div class="confidence-bar">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div class="field-label">Confidence Score</div>
                        <div style="font-size:14px;font-weight:700;color:{conf_color};font-family:'JetBrains Mono',monospace;">{conf}%</div>
                    </div>
                    <div class="conf-track">
                        <div class="conf-fill" style="width:{conf}%;"></div>
                    </div>
                </div>
                <div class="reason-box">
                    <div class="reason-title">📊 Trade Analysis</div>
                    {sig['reason']}
                </div>
                {f'<div class="reason-box" style="margin-top:8px;border-left:2px solid var(--burnt-orange);"><div class="reason-title">⚠ Risk Warning</div>{sig["warning"]}</div>' if sig.get("warning") else ""}
            </div>""", unsafe_allow_html=True)

with col_log:
    st.markdown('<div class="section-header"><span class="section-dot"></span>Live Log</div>', unsafe_allow_html=True)
    log_html = '<div class="log-container">'
    if not st.session_state.logs:
        log_html += '<div class="log-entry"><span class="log-msg" style="color:var(--muted);">Waiting for scan...</span></div>'
    for entry in st.session_state.logs[:80]:
        log_html += f'<div class="log-entry {entry["kind"]}"><span class="log-time">[{entry["time"]}]</span><span class="log-msg"> {entry["msg"]}</span></div>'
    log_html += '</div>'
    st.markdown(log_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Score breakdown
    st.markdown('<div class="section-header"><span class="section-dot"></span>AI Scoring Weights</div>', unsafe_allow_html=True)
    weights = [
        ("Market Structure", 25, "#9D4EDD"),
        ("SMC Confirmation", 25, "#7B2FBE"),
        ("RSI Confirmation", 15, "#CC5500"),
        ("EMA Trend", 15, "#E07B39"),
        ("Liquidity Sweep", 10, "#C77DFF"),
        ("Price Action", 10, "#4488FF"),
    ]
    for name, pct, color in weights:
        st.markdown(f"""
        <div style="margin-bottom:8px;">
            <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">
                <span style="color:var(--muted);">{name}</span>
                <span style="color:{color};font-weight:600;font-family:'JetBrains Mono',monospace;">{pct}%</span>
            </div>
            <div style="height:4px;background:var(--border);border-radius:2px;">
                <div style="height:100%;width:{pct*4}%;background:{color};border-radius:2px;"></div>
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Open Positions ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header"><span class="section-dot"></span>Open Positions</div>', unsafe_allow_html=True)
if not st.session_state.open_trades:
    st.markdown('<div style="color:var(--muted);font-size:13px;padding:16px 0;">No open positions.</div>', unsafe_allow_html=True)
else:
    rows = ""
    for t in st.session_state.open_trades:
        pnl_cls = "positive" if t.get("pnl", 0) >= 0 else "negative"
        rows += f"""<tr>
            <td>{t.get('pair','—')}</td>
            <td>{'🟢 BUY' if t['signal']=='BUY' else '🔴 SELL'}</td>
            <td>{t.get('entry',0):.4f}</td>
            <td>{t.get('sl',0):.4f}</td>
            <td>{t.get('tp1',0):.4f}</td>
            <td>{t.get('tp2',0):.4f}</td>
            <td>{t.get('tp3',0):.4f}</td>
            <td>{t.get('lot_size',0):.2f}</td>
            <td class="{pnl_cls}">${t.get('pnl',0):.2f}</td>
            <td style="color:var(--muted)">{t.get('open_time','—')}</td>
        </tr>"""
    st.markdown(f"""
    <table class="trade-table"><thead><tr>
        <th>Pair</th><th>Direction</th><th>Entry</th><th>SL</th>
        <th>TP1</th><th>TP2</th><th>TP3</th><th>Lot</th><th>P/L</th><th>Time</th>
    </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Closed Trades ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header"><span class="section-dot"></span>Closed Trades</div>', unsafe_allow_html=True)
closed = db.get_closed_trades(50)
if not closed:
    st.markdown('<div style="color:var(--muted);font-size:13px;padding:16px 0;">No closed trades yet.</div>', unsafe_allow_html=True)
else:
    df = pd.DataFrame(closed)
    df_display = df[["pair","signal","entry","sl","tp1","pnl","confidence","close_time"]].copy() if "pnl" in df.columns else df
    st.dataframe(df_display, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Signal History ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header"><span class="section-dot"></span>Signal History</div>', unsafe_allow_html=True)
hist = db.get_signal_history(100)
if hist:
    df_hist = pd.DataFrame(hist)
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
else:
    st.markdown('<div style="color:var(--muted);font-size:13px;padding:16px 0;">No signal history yet.</div>', unsafe_allow_html=True)

# ─── Auto-refresh every 30s when bot is running ───────────────────────────────
if st.session_state.bot_running:
    time.sleep(0.5)
    st.rerun()
