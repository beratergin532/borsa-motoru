from typing import List
from loguru import logger
from src.data_engine.fetcher import MarketDataFetcher
from src.ai_engine.llm_client import HybridAIEngine
from src.notification_engine.telegram import TelegramNotifier

class AutoMarketScanner:
    """Sen uygulamaya bakmıyorken arka planda borsa fırsatlarını tarar ve otomatik Telegram uyarısı gönderir."""

    @classmethod
    def run_automatic_scan(cls, watch_list: List[str]) -> int:
        alerts_sent = 0
        ai_engine = HybridAIEngine()

        for symbol in watch_list:
            try:
                fetcher = MarketDataFetcher(symbol)
                data = fetcher.get_processed_data()

                if not data:
                    continue

                rvol = data.get("rvol", 1.0)
                rsi = data.get("indicators", {}).get("rsi_14", 50.0)
                smart_money = data.get("smart_money_alert", False)

                # OTONOM ALARM KOŞULLARI:
                # 1. Hacim Anomali Sinyali (RVOL >= 2.0 - Balina Girişi)
                # 2. Aşırı Satım Fırsatı (RSI <= 35)
                if smart_money or rsi <= 35:
                    ai_report = ai_engine.generate_analysis(data)
                    
                    if ai_report and ai_report.strategy.action == "BUY" and ai_report.strategy.confidence_score >= 80:
                        sent = TelegramNotifier.send_signal_alert(
                            symbol=symbol,
                            action=f"🚨 OTOMATİK SİNYAL: {ai_report.strategy.action}",
                            confidence=ai_report.strategy.confidence_score,
                            price=data["last_close"],
                            target=ai_report.strategy.take_profit,
                            stop=ai_report.strategy.stop_loss,
                            reasoning=f"[RVOL: {rvol}x | RSI: {rsi}] {ai_report.summary_reasoning}"
                        )
                        if sent:
                            alerts_sent += 1
            except Exception as e:
                logger.error(f"{symbol} otonom taramasında hata: {e}")

        return alerts_sent