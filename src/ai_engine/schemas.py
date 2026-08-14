from pydantic import BaseModel, Field
from typing import List, Literal

class InvestmentThesis(BaseModel):
    opportunities: List[str] = Field(description="Hisse için en kritik 3 büyüme fırsatı / katalizör")
    risks: List[str] = Field(description="Hisse için en kritik 3 risk veya tehdit")

class TradeStrategy(BaseModel):
    action: Literal["BUY", "HOLD", "SELL"] = Field(description="Veri odaklı nihai karar")
    confidence_score: int = Field(ge=0, le=100, description="Analiz güven skoru (0-100)")
    time_horizon: str = Field(description="Tahmini işlem vadesi (Örn: 1-3 Hafta Swing, 1-3 Ay Trend, 6+ Ay Yatırım)")
    suggested_entry: float = Field(description="Önerilen uygun alım/giriş seviyesi ($)")
    stop_loss: float = Field(description="Önerilen Stop-Loss seviyesi ($)")
    take_profit: float = Field(description="Önerilen Hedef Fiyat / Kar Al seviyesi ($)")
    risk_reward_ratio: float = Field(description="Riske edilen miktar / Beklenen kar oranı")

class StockAnalysisReport(BaseModel):
    symbol: str
    overall_score: int = Field(ge=0, le=100, description="Genel Borsa Motoru Skoru (0-100)")
    summary_reasoning: str = Field(description="Kısa, net ve veriye dayalı yönetici özeti")
    thesis: InvestmentThesis
    strategy: TradeStrategy