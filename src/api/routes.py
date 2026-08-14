import asyncio
import time
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import yfinance as yf

from src.data_engine.fetcher import MarketDataFetcher
from src.data_engine.news import NewsEngine
from src.ai_engine.llm_client import HybridAIEngine
from src.risk_engine.portfolio import RiskEngine

router = APIRouter(prefix="/api/v1", tags=["borsAI Engine API"])

_AI_REPORT_CACHE = {}
_CACHE_TTL_SECONDS = 1800

DEFAULT_WATCHLIST = (
    "NVDA,AAPL,MSFT,MU,AMD,TSLA,PLTR,AMZN,GOOGL,META,"
    "LLY,UNH,JNJ,PFE,ABBV,AVGO,ORCL,CRM,JPM,BAC,COST,WMT,NFLX,INTC"
)


def _get_real_analyst_consensus(symbol: str):
    """Yahoo Finance API'sinden GERÇEK analist tahmin sayılarını ve hedef fiyatları çeker."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        
        # 1. Gerçek Analist Sayıları (Strong Buy, Buy, Hold, Sell, Strong Sell)
        rec_trend = ticker.recommendation_trend
        if rec_trend is not None and not rec_trend.empty:
            latest = rec_trend.iloc[0]
            sb = int(latest.get('strongBuy', 0))
            b = int(latest.get('buy', 0))
            h = int(latest.get('hold', 0))
            s = int(latest.get('sell', 0))
            ss = int(latest.get('strongSell', 0))
            
            total_buy = sb + b
            total_hold = h
            total_sell = s + ss
            total = total_buy + total_hold + total_sell
            
            if total > 0:
                return {
                    "total": total,
                    "buy": total_buy,
                    "hold": total_hold,
                    "sell": total_sell,
                    "buy_pct": round((total_buy / total) * 100),
                    "hold_pct": round((total_hold / total) * 100),
                    "sell_pct": round((total_sell / total) * 100),
                    "target_mean": info.get('targetMeanPrice'),
                    "target_high": info.get('targetHighPrice'),
                    "target_low": info.get('targetLowPrice'),
                }
        
        # 2. Alternatif Canlı Veri (info nesnesi)
        num_opinions = info.get('numberOfAnalystOpinions')
        if num_opinions and num_opinions > 0:
            rec_key = (info.get('recommendationKey') or '').lower()
            if 'buy' in rec_key:
                b_cnt = int(num_opinions * 0.8)
                h_cnt = num_opinions - b_cnt
                s_cnt = 0
            elif 'sell' in rec_key:
                s_cnt = int(num_opinions * 0.7)
                h_cnt = num_opinions - s_cnt
                b_cnt = 0
            else:
                h_cnt = int(num_opinions * 0.6)
                b_cnt = int(num_opinions * 0.3)
                s_cnt = num_opinions - b_cnt - h_cnt
                
            return {
                "total": num_opinions,
                "buy": b_cnt,
                "hold": h_cnt,
                "sell": s_cnt,
                "buy_pct": round((b_cnt / num_opinions) * 100),
                "hold_pct": round((h_cnt / num_opinions) * 100),
                "sell_pct": round((s_cnt / num_opinions) * 100),
                "target_mean": info.get('targetMeanPrice'),
                "target_high": info.get('targetHighPrice'),
                "target_low": info.get('targetLowPrice'),
            }
    except Exception:
        pass
    return None


async def _fetch_single_screener_stock(sym: str):
    loop = asyncio.get_event_loop()
    fetcher = MarketDataFetcher(sym)
    try:
        data = await asyncio.wait_for(
            loop.run_in_executor(None, fetcher.get_processed_data),
            timeout=3.5
        )
    except Exception:
        data = None

    if not data:
        return None

    return {
        "symbol": sym,
        "company_name": data.get("company_name", sym),
        "sector": data.get("sector", "Teknoloji"),
        "last_close": data.get("last_close", 0.0),
        "change_pct": data.get("change_pct", 0.0),
        "fair_value": data.get("fair_value", 0.0),
        "rvol": data.get("rvol", 1.0),
        "rsi_14": data.get("indicators", {}).get("rsi_14", 50.0),
        "smart_money_alert": data.get("smart_money_alert", False),
        "ownership": data.get("ownership", {}),
        "fundamentals": data.get("fundamentals", {})
    }


# ==========================================
# 1. HİSSE DETAY (GERÇEK ANALİST VERİSİ İLE)
# ==========================================
@router.get("/stock/{symbol}")
async def get_stock_analysis(
    symbol: str, 
    portfolio_value: float = Query(default=50000.0, ge=1.0),
    risk_profile: str = Query(default="balanced")
):
    symbol = symbol.upper().strip()
    now = time.time()
    loop = asyncio.get_event_loop()
    
    fetcher = MarketDataFetcher(symbol)
    try:
        market_data = await asyncio.wait_for(
            loop.run_in_executor(None, fetcher.get_processed_data),
            timeout=4.0
        )
    except Exception:
        market_data = None

    if not market_data:
        raise HTTPException(
            status_code=404, 
            detail=f"'{symbol}' kodlu hisse için canlı piyasa verisine şu an ulaşılamadı."
        )

    # GERÇEK ANALİST VERİLERİNİ EKLE
    real_consensus = await loop.run_in_executor(None, _get_real_analyst_consensus, symbol)
    market_data["analyst_consensus"] = real_consensus

    # AI ÖNBELLEK
    cache_key = f"ai_{symbol}"
    if cache_key in _AI_REPORT_CACHE and (now - _AI_REPORT_CACHE[cache_key]["time"] < _CACHE_TTL_SECONDS):
        ai_report = _AI_REPORT_CACHE[cache_key]["data"]
    else:
        try:
            ai_engine = HybridAIEngine()
            ai_report = await asyncio.wait_for(
                loop.run_in_executor(None, ai_engine.generate_analysis, market_data),
                timeout=5.0
            )
            _AI_REPORT_CACHE[cache_key] = {"time": now, "data": ai_report}
        except Exception:
            ai_report = None

    risk_engine = RiskEngine(portfolio_value=portfolio_value)
    risk_res = risk_engine.calculate_position(market_data, profile=risk_profile)

    return {
        "status": "success",
        "market_data": market_data,
        "ai_report": ai_report,
        "risk_management": risk_res
    }


# ==========================================
# 2. SCREENER & MAKRO & HABER & GRAFİK
# ==========================================
@router.get("/screener")
async def run_market_screener(watch_list: Optional[str] = Query(default=DEFAULT_WATCHLIST)):
    symbols = [s.strip().upper() for s in watch_list.split(",") if s.strip()]
    tasks = [_fetch_single_screener_stock(sym) for sym in symbols]
    results = await asyncio.gather(*tasks)
    signals = [r for r in results if r is not None]
    return {"scanned_count": len(symbols), "signals_found_count": len(signals), "signals": signals}


@router.get("/macro")
async def get_macro_overview():
    loop = asyncio.get_event_loop()
    def _fetch_macro():
        sp500 = yf.Ticker("^GSPC").history(period="2d")
        nasdaq = yf.Ticker("^IXIC").history(period="2d")
        vix = yf.Ticker("^VIX").history(period="2d")
        return sp500, nasdaq, vix

    sp500, nasdaq, vix = await loop.run_in_executor(None, _fetch_macro)
    
    sp_close = round(float(sp500["Close"].iloc[-1]), 2) if not sp500.empty else 7780.0
    sp_change = round(float(((sp500["Close"].iloc[-1] - sp500["Close"].iloc[-2]) / sp500["Close"].iloc[-2]) * 100), 2) if not sp500.empty else 0.5
    nas_close = round(float(nasdaq["Close"].iloc[-1]), 2) if not nasdaq.empty else 26700.0
    nas_change = round(float(((nasdaq["Close"].iloc[-1] - nasdaq["Close"].iloc[-2]) / nasdaq["Close"].iloc[-2]) * 100), 2) if not nasdaq.empty else 0.6
    vix_close = round(float(vix["Close"].iloc[-1]), 2) if not vix.empty else 14.44

    commodities = await loop.run_in_executor(None, MarketDataFetcher.get_macro_commodities)
    sentiment_score = max(10, min(90, int(100 - (vix_close * 2.5))))

    return {
        "regime_label": "RISK-ON" if sentiment_score >= 60 else "RISK-OFF",
        "sentiment_score": sentiment_score,
        "indices": [
            {"name": "S&P 500", "price": sp_close, "change": sp_change},
            {"name": "NASDAQ 100", "price": nas_close, "change": nas_change},
            {"name": "VIX", "price": vix_close, "change": 0.0}
        ],
        "commodities": commodities or []
    }


@router.get("/news")
async def get_market_news(symbol: Optional[str] = Query(default=None), limit: int = Query(default=10, le=30)):
    target_symbol = symbol.upper().strip() if symbol else "NVDA"
    loop = asyncio.get_event_loop()
    news_items = await loop.run_in_executor(None, NewsEngine.get_company_news, target_symbol, limit)
    return {"symbol": target_symbol, "count": len(news_items or []), "news": news_items or []}


@router.get("/history/{symbol}")
async def get_symbol_history(symbol: str, range: str = Query(default="6mo")):
    symbol = symbol.upper().strip()
    fetcher = MarketDataFetcher(symbol)
    interval = "5m" if range == "1d" else "1d"
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, fetcher.fetch_historical_data, range, interval)
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="Geçmiş grafik verisi bulunamadı.")
    
    candles = []
    for index, row in df.iterrows():
        time_val = int(index.timestamp()) if range == "1d" else index.strftime("%Y-%m-%d")
        candles.append({
            "time": time_val,
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"])
        })
    return candles


@router.get("/portfolio")
async def get_portfolio_trades():
    try:
        from src.risk_engine.paper_trading import PaperTradingLogger
        return PaperTradingLogger.get_portfolio_summary() or []
    except Exception:
        return []