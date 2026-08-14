import urllib.request
import urllib.parse
import json
from loguru import logger
from config.settings import settings

class TelegramNotifier:
    """Kritik borsa sinyallerini ve RVOL anomalilerini Telegram'a anlık ileten bildirim motoru."""

    @staticmethod
    def send_signal_alert(
        symbol: str,
        action: str,
        confidence: int,
        price: float,
        target: float,
        stop: float,
        reasoning: str
    ) -> bool:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

        if not token or not chat_id:
            logger.warning("Telegram Bot Token veya Chat ID yapılandırılmamış. Bildirim atlandı.")
            return False

        message = (
            f"🚨 *OTONOM BORSA SİNYALİ* 🚨\n\n"
            f"📌 *Hisse:* `{symbol}`\n"
            f"🎯 *AI Kararı:* `{action}` (%{confidence} Güven)\n"
            f"💵 *Anlık Fiyat:* ${price}\n"
            f"🟢 *Hedef Fiyat (TP):* ${target}\n"
            f"🔴 *Stop Loss (SL):* ${stop}\n\n"
            f"🧠 *AI Gerekçesi:* {reasoning}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    logger.info(f"{symbol} için Telegram bildirimi başarıyla gönderildi.")
                    return True
        except Exception as e:
            logger.error(f"Telegram bildirimi gönderilemedi: {e}")
            return False
        return False