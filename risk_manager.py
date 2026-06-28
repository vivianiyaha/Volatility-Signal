"""risk_manager.py — Position sizing & risk control."""

class RiskManager:
    def __init__(self, account_balance: float, risk_pct: float,
                 daily_loss_limit: float, max_open_trades: int):
        self.balance          = account_balance
        self.risk_pct         = risk_pct
        self.daily_loss_limit = daily_loss_limit
        self.max_open_trades  = max_open_trades

    def position_size(self, sl_distance: float, pip_value: float = 1.0) -> float:
        """Calculate position size based on risk %."""
        if sl_distance <= 0 or pip_value <= 0:
            return 0.01
        risk_amount = self.balance * (self.risk_pct / 100)
        size = risk_amount / (sl_distance * pip_value)
        return round(max(0.01, size), 2)

    def can_trade(self, open_trades: int, session_loss: float) -> tuple:
        """Return (allowed: bool, reason: str)."""
        if open_trades >= self.max_open_trades:
            return False, f"Max open trades ({self.max_open_trades}) reached"
        if session_loss <= -self.daily_loss_limit:
            return False, f"Daily loss limit (${self.daily_loss_limit:.2f}) hit — trading halted"
        return True, "OK"

    def risk_reward(self, entry: float, sl: float, tp: float) -> float:
        risk   = abs(entry - sl)
        reward = abs(tp - entry)
        return round(reward / risk, 2) if risk > 0 else 0.0
