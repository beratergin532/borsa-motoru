import yfinance as yf
from typing import List, Dict, Any
from loguru import logger

class NewsEngine:
    """Haber başlıklarını duygu (Sentiment) ve önem derecesine göre etiketler."""

    POS_WORDS = ["record", "growth", "beat", "surge", "jump", "rekor", "yükseliş", "büyüme", "kazanç", "upgrade", "buy", "partnership"]
    NEG_WORDS = ["drop", "fall", "miss", "loss", "decline", "düşüş", "zarar", "soruşturma", "downgrade", "sell", "lawsuit", "risk", "warn"]
    CRITICAL_WORDS = ["fed", "rate", "war", "sec", "earnings", "ceo", "split", "savaş", "faiz", "enflasyon", "bilanço"]

    @classmethod
    def get_company_news(cls, symbol: str, limit: int = 6) -> List[Dict[str, Any]]:
        try:
            ticker = yf.Ticker(symbol)
            news_data = ticker.news
            parsed_news = []

            for item in news_data[:limit]:
                content = item.get("content", {})
                title = content.get("title") or item.get("title", "Haber Başlığı Yok")
                link = content.get("canonicalUrl", {}).get("url") or item.get("link", "#")
                publisher = content.get("provider", {}).get("displayName") or item.get("publisher", "Piyasa Haberi")

                title_lower = title.lower()

                # Duygu Tespiti
                if any(w in title_lower for w in cls.POS_WORDS):
                    sentiment = "POZİTİF"
                    badge_color = "🟢"
                elif any(w in title_lower for w in cls.NEG_WORDS):
                    sentiment = "NEGATİF"
                    badge_color = "🔴"
                else:
                    sentiment = "NÖTR"
                    badge_color = "⚪"

                # Önem Tespiti
                priority = "KRİTİK" if any(w in title_lower for w in cls.CRITICAL_WORDS) else "ÖNEMLİ"

                parsed_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "sentiment": sentiment,
                    "badge": badge_color,
                    "priority": priority
                })

            logger.info(f"{symbol} için {len(parsed_news)} haber başlığı duygu analiziyle çekildi.")
            return parsed_news
        except Exception as e:
            logger.error(f"{symbol} haberleri çekilirken hata oluştu: {e}")
            return []