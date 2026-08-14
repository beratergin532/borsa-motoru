from src.data_engine.fetcher import MarketDataFetcher
from src.ai_engine.llm_client import HybridAIEngine
from src.risk_engine.portfolio import RiskEngine
from loguru import logger

def test_full_chain():
    symbol = "NVDA"
    portfolio_value = 50000.0  # Örnek 50.000 Dolar Portföy
    risk_profile = "balanced"   # "aggressive", "balanced", "conservative"

    logger.info(f"=== {symbol} TAM ZİNCİR TESTİ BAŞLATILIYOR ===")
    
    # 1. Veri ve Teknik İndikatör Motoru
    fetcher = MarketDataFetcher(symbol)
    market_data = fetcher.get_processed_data()
    if not market_data:
        logger.error("Veri çekilemedi!")
        return

    # 2. Yapay Zeka Karar Motoru
    ai_engine = HybridAIEngine()
    report = ai_engine.generate_analysis(market_data)

    # 3. Risk ve Pozisyon Boyutlandırma Motoru
    risk_engine = RiskEngine(portfolio_value=portfolio_value)
    risk_result = risk_engine.calculate_position(market_data, profile=risk_profile)

    # Sonuçları Ekran Formatında Sunma
    print("\n" + "="*60)
    print(f"📊 PORTFÖY VE RİSK RAPORU [{risk_result.symbol}] - Profil: {risk_result.risk_profile.upper()}")
    print("="*60)
    print(f"Mevcut Portföy Bakiyesi : ${risk_result.portfolio_value:,.2f}")
    print(f"Hisse Fiyatı            : ${risk_result.entry_price:.2f}")
    print(f"Önerilen Hisse Adedi    : {risk_result.suggested_shares} Lot")
    print(f"Ayrılacak Tutar         : ${risk_result.max_position_dollars:,.2f}")
    print(f"Dinamik Stop-Loss (ATR) : ${risk_result.stop_loss_price:.2f}")
    print(f"Hedef Fiyat (Take-Profit): ${risk_result.take_profit_price:.2f}")
    print(f"Maksimum Göze Alınan Risk: ${risk_result.max_loss_dollars:,.2f}")
    print("="*60)

    if report:
        print(f"\n🤖 YAPAY ZEKA ANALİZİ VE SİNYALİ")
        print(f"Aksiyon Kılavuzu: {report.strategy.action} (Güven: %{report.strategy.confidence_score})")
        print(f"AI Analiz Skoru : {report.overall_score}/100")
        print(f"Gerekçe         : {report.summary_reasoning}")
        print("="*60 + "\n")

if __name__ == "__main__":
    test_full_chain()