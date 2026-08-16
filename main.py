import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from src.api.routes import router, run_market_screener, get_macro_overview
from src.data_engine.breadth import get_market_sentiment_and_breadth
from loguru import logger

app = FastAPI(
    title=settings.APP_NAME,
    description="Otonom Borsa Analiz, AI Akıl Yürütme ve Risk Motoru API Servisi",
    version="1.0.0"
)

# CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# ==========================================
# 🌟 BLOOMBERG STANDARDI: ASENKRON ÖNBELLEK ISITICI (CACHE WARMER)
# ==========================================
async def background_cache_warmer():
    """
    Sunucu ayaktayken 45 saniyede bir arka planda tüm verileri günceller.
    Kullanıcı istek attığında Yahoo Finance beklenmez; RAM'den 1ms'de yanıt döner.
    """
    await asyncio.sleep(2) # Sunucunun tam başlamasını bekle
    logger.info("🚀 borsAI Otomatik Veri Motoru (Cache Warmer) Devreye Girdi.")
    
    while True:
        try:
            # 3 kritik veri havuzunu paralel olarak arka planda ısıt
            await asyncio.gather(
                run_market_screener(),
                get_macro_overview(),
                get_market_sentiment_and_breadth(),
                return_exceptions=True
            )
            logger.info("⚡ Canlı Borsa & Sektör Verileri RAM üzerinde güncellendi.")
        except Exception as e:
            logger.warning(f"Cache Warmer döngü uyarısı: {e}")
            
        await asyncio.sleep(45) # 45 saniyede bir yenile


@app.on_event("startup")
async def startup_event():
    # Arka plan görevini ana döngüyü bloklamadan başlat
    asyncio.create_task(background_cache_warmer())


@app.get("/")
async def root():
    return {
        "status": "active",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "docs_url": "/docs"
    }