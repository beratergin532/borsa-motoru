from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from src.api.routes import router

app = FastAPI(
    title=settings.APP_NAME,
    description="Otonom Borsa Analiz, AI Akıl Yürütme ve Risk Motoru API Servisi",
    version="1.0.0"
)

# Dashboard (React / Streamlit) erişimi için CORS İzinleri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {
        "status": "active",
        "app_name": settings.APP_NAME,
        "environment": settings.ENV,
        "docs_url": "/docs"
    }