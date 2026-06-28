"""
database.py — SQLite persistence for AI Scanner
Tables: signals, trades, account_history, daily_summary
"""

import sqlite3
import json
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path: str = "ai_scanner.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pair        TEXT,
                timeframe   TEXT,
                signal      TEXT,
                entry       REAL,
                sl          REAL,
                tp1         REAL,
                tp2         REAL,
                tp3         REAL,
                rr          REAL,
                confidence  INTEGER,
                trend       TEXT,
                zone        TEXT,
                structure   TEXT,
                bos         INTEGER,
                liq_sweep   INTEGER,
                reason      TEXT,
                timestamp   TEXT
            );

            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pair        TEXT,
                signal      TEXT,
                entry       REAL,
                sl          REAL,
                tp1         REAL,
                tp2         REAL,
                tp3         REAL,
                lot_size    REAL,
                pnl         REAL,
                confidence  INTEGER,
                open_time   TEXT,
                close_time  TEXT,
                status      TEXT DEFAULT 'open'
            );

            CREATE TABLE IF NOT EXISTS account_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                balance     REAL,
                equity      REAL,
                pnl         REAL,
                timestamp   TEXT
            );

            CREATE TABLE IF NOT EXISTS daily_summary (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT UNIQUE,
                total_trades INTEGER,
                wins        INTEGER,
                losses      INTEGER,
                total_pnl   REAL,
                win_rate    REAL
            );
            """)

    def save_signal(self, sig: dict):
        with self._conn() as conn:
            conn.execute("""
            INSERT INTO signals
            (pair, timeframe, signal, entry, sl, tp1, tp2, tp3, rr,
             confidence, trend, zone, structure, bos, liq_sweep, reason, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                sig.get("pair"), sig.get("timeframe"), sig.get("signal"),
                sig.get("entry"), sig.get("sl"), sig.get("tp1"), sig.get("tp2"), sig.get("tp3"),
                sig.get("rr"), sig.get("confidence"), sig.get("trend"), sig.get("zone"),
                sig.get("structure"), int(sig.get("bos", False)), int(sig.get("liq_sweep", False)),
                sig.get("reason"), datetime.now().isoformat()
            ))

    def save_trade(self, trade: dict):
        with self._conn() as conn:
            conn.execute("""
            INSERT INTO trades
            (pair, signal, entry, sl, tp1, tp2, tp3, lot_size, pnl, confidence, open_time, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                trade.get("pair"), trade.get("signal"), trade.get("entry"),
                trade.get("sl"), trade.get("tp1"), trade.get("tp2"), trade.get("tp3"),
                trade.get("lot_size"), trade.get("pnl", 0.0), trade.get("confidence"),
                trade.get("open_time"), "open"
            ))

    def close_trade(self, trade_id: int, pnl: float, close_time: str):
        with self._conn() as conn:
            conn.execute("""
            UPDATE trades SET pnl=?, close_time=?, status='closed' WHERE id=?
            """, (pnl, close_time, trade_id))

    def get_signal_history(self, limit: int = 100):
        with self._conn() as conn:
            cur = conn.execute("""
            SELECT pair, timeframe, signal, entry, sl, tp1, tp2, tp3,
                   rr, confidence, trend, timestamp
            FROM signals ORDER BY id DESC LIMIT ?
            """, (limit,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_closed_trades(self, limit: int = 50):
        with self._conn() as conn:
            cur = conn.execute("""
            SELECT pair, signal, entry, sl, tp1, tp2, tp3,
                   lot_size, pnl, confidence, open_time, close_time
            FROM trades WHERE status='closed' ORDER BY id DESC LIMIT ?
            """, (limit,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def save_account_snapshot(self, balance: float, equity: float, pnl: float):
        with self._conn() as conn:
            conn.execute("""
            INSERT INTO account_history (balance, equity, pnl, timestamp)
            VALUES (?,?,?,?)
            """, (balance, equity, pnl, datetime.now().isoformat()))

    def update_daily_summary(self, wins: int, losses: int, total_pnl: float):
        today = datetime.now().strftime("%Y-%m-%d")
        total = wins + losses
        wr = (wins / total * 100) if total > 0 else 0.0
        with self._conn() as conn:
            conn.execute("""
            INSERT INTO daily_summary (date, total_trades, wins, losses, total_pnl, win_rate)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(date) DO UPDATE SET
                total_trades=excluded.total_trades,
                wins=excluded.wins,
                losses=excluded.losses,
                total_pnl=excluded.total_pnl,
                win_rate=excluded.win_rate
            """, (today, total, wins, losses, total_pnl, wr))
