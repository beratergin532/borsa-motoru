import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import yfinance as yf
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TRADES_FILE = BASE_DIR / "logs" / "paper_trades.json"

class PaperTradingLogger:
    """Canlı PnL (Kâr/Zarar) ve Otomatik Stop-Loss hesaplamalı Sanal Portföy Motoru."""

    @staticmethod
    def _load_trades() -> List[Dict[str, Any]]:
        if not TRADES_FILE.exists():
            return []
        try:
            with open(TRADES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @classmethod
    def log_trade_signal(
        cls,
        symbol: str,
        action: str,
        confidence: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        suggested_shares: int,
        reasoning: str
    ) -> bool:
        try:
            trades = cls._load_trades()
            trade_record = {
                "id": len(trades) + 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "action": action,
                "confidence_pct": confidence,
                "entry_price": entry_price,
                "current_price": entry_price,
                "pnl_dollars": 0.0,
                "pnl_pct": 0.0,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "shares": suggested_shares,
                "total_cost": round(entry_price * suggested_shares, 2),
                "status": "OPEN",
                "ai_reasoning": reasoning
            }
            trades.append(trade_record)
            TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TRADES_FILE, "w", encoding="utf-8") as f:
                json.dump(trades, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Sanal işlem kaydedilirken hata: {e}")
            return False

    @classmethod
    def get_portfolio_summary(cls) -> List[Dict[str, Any]]:
        """Açık pozisyonların güncel borsa fiyatıyla canlı kâr/zararını hesaplar."""
        trades = cls._load_trades()
        updated_trades = []

        for trade in trades:
            if trade["status"] == "OPEN":
                try:
                    ticker = yf.Ticker(trade["symbol"])
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        current_price = round(float(hist["Close"].iloc[-1]), 2)
                        entry_price = trade["entry_price"]
                        shares = trade["shares"]
                        
                        pnl_dollars = round((current_price - entry_price) * shares, 2)
                        pnl_pct = round(((current_price - entry_price) / entry_price) * 100, 2)

                        status = "OPEN"
                        if current_price <= trade["stop_loss"]:
                            status = "CLOSED_STOP_LOSS"
                        elif current_price >= trade["take_profit"]:
                            status = "CLOSED_TAKE_PROFIT"

                        trade["current_price"] = current_price
                        trade["pnl_dollars"] = pnl_dollars
                        trade["pnl_pct"] = pnl_pct
                        trade["status"] = status
                except Exception as e:
                    logger.error(f"{trade['symbol']} PnL güncellenirken hata: {e}")

            updated_trades.append(trade)

        return updated_trades