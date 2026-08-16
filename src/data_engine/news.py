# src/data_engine/news.py

import yfinance as yf
from typing import List, Dict, Any, Optional
from loguru import logger

class NewsEngine:
    """Haber başlıklarını duygu (Sentiment) ve önem derecesine göre etiketleyen kurumsal motor."""

    POS_WORDS = [
        "record", "growth", "beat", "surge", "jump", "rekor", "yükseliş", 
        "büyüme", "kazanç", "upgrade", "buy", "partnership", "soar", "profit"
    ]
    NEG_WORDS = [
        "drop", "fall", "miss", "loss", "decline", "düşüş", "zarar", 
        "soruşturma", "downgrade", "sell", "lawsuit", "risk", "warn", "plunge", "sink"
    ]
    CRITICAL_WORDS = [
        "fed", "rate", "war", "sec", "earnings", "ceo", "split", 
        "savaş", "faiz", "enflasyon", "bilanço", "investigation", "tariff"
    ]

    @classmethod
    def get_company_news(cls, symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        target_symbol = symbol.upper().strip() if symbol and len(symbol.strip()) > 0 else "^GSPC"
        
        try:
            ticker = yf.Ticker(target_symbol)
            news_data = ticker.news or []
            parsed_news = []

            for item in news_data[:limit]:
                content = item.get("content", {})
                
                # Hem yeni nesil hem eski yfinance JSON yapısıyla tam uyumluluk
                title = content.get("title") or item.get("title", "Piyasa Gelişmesi")
                link = content.get("canonicalUrl", {}).get("url") or item.get("link", "#")
                publisher = (
                    content.get("provider", {}).get("displayName") 
                    or item.get("publisher") 
                    or "Finans Basını"
                )
                provider_time = (
                    content.get("pubDate") 
                    or item.get("providerPublishTime") 
                    or 0
                )

                title_lower = title.lower()

                # 1. NLP Duyarlılık Tespiti
                is_pos = any(w in title_lower for w in cls.POS_WORDS)
                is_neg = any(w in title_lower for w in cls.NEG_WORDS)

                if is_pos and not is_neg:
                    sentiment = "POZİTİF"
                    badge_color = "🟢"
                elif is_neg and not is_pos:
                    sentiment = "NEGATİF"
                    badge_color = "🔴"
                else:
                    sentiment = "NÖTR"
                    badge_color = "⚪"

                # 2. Öncelik & Kritiklik Tespiti
                priority = "KRİTİK" if any(w in title_lower for w in cls.CRITICAL_WORDS) else "ÖNEMLİ"

                parsed_news.append({
                    "title": title,
                    "publisher": publisher,
                    "link": link,
                    "sentiment": sentiment,
                    "badge": badge_color,
                    "priority": priority,
                    "published_at": provider_time,
                    "symbol": target_symbol
                })

            # Eğer hisseye özel haber bulunamadıysa genel piyasa haberlerine düş (Fallback)
            if not parsed_news and symbol:
                return cls.get_company_news(symbol=None, limit=limit)

            logger.info(f"{target_symbol} için {len(parsed_news)} haber başarıyla işlendi.")
            return parsed_news

        except Exception as e:
            logger.error(f"{target_symbol} haber akışı çekilirken hata: {e}")
            return []