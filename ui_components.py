"""ui_components.py — Reusable HTML component builders."""

def render_metric_card(label: str, value: str, sub: str = "", color: str = "neutral") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color}">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>"""

def render_signal_card(sig: dict) -> str:
    s = sig.get("signal", "NO TRADE")
    card_cls  = "buy" if s == "BUY" else ("sell" if s == "SELL" else "no-trade")
    badge_cls = "badge-buy" if s == "BUY" else ("badge-sell" if s == "SELL" else "badge-wait")
    conf = sig.get("confidence", 0)
    return f"""
    <div class="signal-card {card_cls}">
        <div class="signal-header">
            <span class="signal-pair">{sig.get('pair','—')}</span>
            <span class="signal-badge {badge_cls}">{s}</span>
        </div>
        <div class="confidence-bar">
            <div class="conf-track">
                <div class="conf-fill" style="width:{conf}%;"></div>
            </div>
        </div>
    </div>"""

def render_trade_row(trade: dict) -> str:
    pnl = trade.get("pnl", 0)
    pnl_cls = "positive" if pnl >= 0 else "negative"
    sign = "+" if pnl >= 0 else ""
    return f"""
    <tr>
        <td>{trade.get('pair','—')}</td>
        <td>{'🟢 BUY' if trade.get('signal')=='BUY' else '🔴 SELL'}</td>
        <td>{trade.get('entry',0):.4f}</td>
        <td>{trade.get('sl',0):.4f}</td>
        <td>{trade.get('tp1',0):.4f}</td>
        <td class="{pnl_cls}">{sign}${pnl:.2f}</td>
        <td style="color:var(--muted)">{trade.get('open_time','—')}</td>
    </tr>"""
