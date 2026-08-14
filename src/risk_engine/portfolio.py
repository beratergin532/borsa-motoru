import math
import numpy as np
from pydantic import BaseModel
from typing import Dict, Any, Literal

class PositionSizeResult(BaseModel):
    portfolio_value: float
    risk_profile: str
    max_position_dollars: float
    suggested_shares: int
    stop_loss_price: float
    take_profit_price: float
    risk_per_share: float
    max_loss_dollars: float

class RiskEngine:
    """Sermaye ve Volatilite (ATR) Odaklı Hata Korumalı Risk Motoru."""

    def __init__(self, portfolio_value: float = 50000.0):
        self.portfolio_value = max(100.0, portfolio_value)

    def calculate_position(
        self,
        market_data: Dict[str, Any],
        profile: Literal["conservative", "balanced", "aggressive"] = "balanced"
    ) -> PositionSizeResult:
        profile_limits = {
            "conservative": {"max_pos_pct": 0.05, "max_risk_pct": 0.01},
            "balanced": {"max_pos_pct": 0.10, "max_risk_pct": 0.02},
            "aggressive": {"max_pos_pct": 0.20, "max_risk_pct": 0.03}
        }
        limits = profile_limits.get(profile, profile_limits["balanced"])

        # NaN ve Null Fiyat Koruması
        last_price = market_data.get("last_close", 0.0)
        if last_price is None or np.isnan(last_price) or last_price <= 0:
            last_price = 1.0

        indicators = market_data.get("indicators", {})
        atr = indicators.get("atr_14", last_price * 0.03)
        if atr is None or np.isnan(atr) or atr <= 0:
            atr = last_price * 0.03

        max_pos_dollars = self.portfolio_value * limits["max_pos_pct"]
        shares_by_capital = math.floor(max_pos_dollars / last_price) if last_price > 0 else 0

        max_risk_dollars = self.portfolio_value * limits["max_risk_pct"]
        stop_distance = atr * 1.5
        shares_by_risk = math.floor(max_risk_dollars / stop_distance) if stop_distance > 0 else 0

        suggested_shares = max(1, min(shares_by_capital, shares_by_risk)) if shares_by_capital > 0 else 0
        stop_loss_price = round(max(0.01, last_price - stop_distance), 2)
        take_profit_price = round(last_price + (stop_distance * 2.0), 2)

        return PositionSizeResult(
            portfolio_value=self.portfolio_value,
            risk_profile=profile,
            max_position_dollars=round(max_pos_dollars, 2),
            suggested_shares=suggested_shares,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            risk_per_share=round(stop_distance, 2),
            max_loss_dollars=round(suggested_shares * stop_distance, 2)
        )