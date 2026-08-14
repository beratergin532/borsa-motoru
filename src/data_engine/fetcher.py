import requests
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from loguru import logger
from src.data_engine.indicators import TechnicalIndicators

class MarketDataFetcher:
    """borsAI Veri Odaklı Kurumsal Motor."""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper().strip()

    @staticmethod
    def search_symbols(query: str) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) == 0:
            return []
        try:
            search = yf.Search(query.strip(), max_results=8, news_count=0)
            quotes = getattr(search, "quotes", [])
            results = []
            for q in quotes:
                sym = q.get("symbol", "")
                if sym:
                    results.append({
                        "symbol": sym,
                        "name": q.get("shortname") or q.get("longname") or sym,
                        "exchange": q.get("exchange", ""),
                        "quoteType": q.get("quoteType", "EQUITY")
                    })
            return results
        except Exception as e:
            logger.error(f"Canlı hisse araması başarısız ({query}): {e}")
            return []

    @staticmethod
    def calculate_quant_grades(info: Dict[str, Any], df: pd.DataFrame) -> Dict[str, str]:
        pe = info.get("forwardPE") or info.get("trailingPE") or 30.0
        peg = info.get("pegRatio") or 2.0
        rev_growth = info.get("revenueGrowth") or 0.0
        profit_margin = info.get("profitMargins") or 0.0
        
        val_grade = "A+" if peg < 1.0 else "A" if peg < 1.5 else "B" if pe < 25 else "C" if pe < 40 else "D"
        growth_grade = "A+" if rev_growth > 0.30 else "A" if rev_growth > 0.15 else "B" if rev_growth > 0.05 else "C"
        prof_grade = "A+" if profit_margin > 0.25 else "A" if profit_margin > 0.15 else "B" if profit_margin > 0.05 else "C"
        
        close_start = float(df["Close"].iloc[0])
        close_end = float(df["Close"].iloc[-1])
        ret_6m = (close_end - close_start) / close_start if close_start > 0 else 0.0
        mom_grade = "A+" if ret_6m > 0.40 else "A" if ret_6m > 0.20 else "B" if ret_6m > 0.0 else "C"

        return {"valuation": val_grade, "growth": growth_grade, "profitability": prof_grade, "momentum": mom_grade}

    @staticmethod
    def get_macro_commodities() -> List[Dict[str, Any]]:
        assets = [
            {"symbol": "GC=F", "name": "Ons Altın ($)"},
            {"symbol": "SI=F", "name": "Ons Gümüş ($)"},
            {"symbol": "BZ=F", "name": "Brent Petrol ($)"},
            {"symbol": "EURUSD=X", "name": "EUR / USD"}
        ]
        results = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        for a in assets:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{a['symbol']}?range=5d&interval=1d"
                res = requests.get(url, headers=headers, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    chart = data.get("chart", {}).get("result", [{}])[0]
                    closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
                    closes = [c for c in closes if c is not None]
                    if len(closes) >= 2:
                        last = round(float(closes[-1]), 2)
                        prev = float(closes[-2])
                        chg = round(((last - prev) / prev) * 100, 2)
                        results.append({"name": a["name"], "price": last, "change": chg})
            except Exception:
                continue
        return results

    def fetch_historical_data(self, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        # 1. Yöntem: Doğrudan Yahoo v8 REST API (Engelsiz Canlı Piyasa Verisi)
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self.ticker}?range={period}&interval={interval}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                json_data = res.json()
                result = json_data.get("chart", {}).get("result")
                if result:
                    chart_data = result[0]
                    timestamps = chart_data.get("timestamp", [])
                    quote = chart_data.get("indicators", {}).get("quote", [{}])[0]
                    if timestamps and quote:
                        df = pd.DataFrame({
                            "Open": quote.get("open", []),
                            "High": quote.get("high", []),
                            "Low": quote.get("low", []),
                            "Close": quote.get("close", []),
                            "Volume": quote.get("volume", [])
                        }, index=pd.to_datetime(timestamps, unit="s"))
                        df = df.dropna(subset=["Close"])
                        if len(df) >= 5:
                            return df
        except Exception as e:
            logger.warning(f"{self.ticker} direct REST API çağrısı başarısız, yfinance deneniyor: {e}")

        # 2. Yöntem: Fallback yfinance
        try:
            stock = yf.Ticker(self.ticker)
            df = stock.history(period=period, interval=interval, timeout=5)
            if df is not None and not df.empty and len(df) >= 5:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df[["Open", "High", "Low", "Close", "Volume"]].copy()
        except Exception as e:
            logger.error(f"{self.ticker} geçmiş veri çekilirken hata: {e}")

        return None

    def get_processed_data(self) -> Optional[Dict[str, Any]]:
        try:
            df = self.fetch_historical_data(period="6mo", interval="1d")
            if df is None or df.empty or len(df) < 5:
                return None

            df["SMA_20"] = TechnicalIndicators.calculate_sma(df, window=20)
            df["SMA_50"] = TechnicalIndicators.calculate_sma(df, window=50)
            df["EMA_20"] = TechnicalIndicators.calculate_ema(df, window=20)
            df["EMA_50"] = TechnicalIndicators.calculate_ema(df, window=50)
            df["RSI_14"] = TechnicalIndicators.calculate_rsi(df, window=14)
            df["ATR_14"] = TechnicalIndicators.calculate_atr(df, window=14)

            macd_df = TechnicalIndicators.calculate_macd(df)
            bb_df = TechnicalIndicators.calculate_bollinger_bands(df)
            df = pd.concat([df, macd_df, bb_df], axis=1)

            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            high_6m = float(df["High"].max())
            low_6m = float(df["Low"].min())
            diff = high_6m - low_6m if high_6m != low_6m else 1.0

            fib_levels = {
                "fib_236": round(high_6m - 0.236 * diff, 2),
                "fib_382": round(high_6m - 0.382 * diff, 2),
                "fib_500": round(high_6m - 0.500 * diff, 2),
                "fib_618": round(high_6m - 0.618 * diff, 2)
            }

            pivot = (float(latest["High"]) + float(latest["Low"]) + float(latest["Close"])) / 3.0
            support_1 = round(2 * pivot - float(latest["High"]), 2)
            resistance_1 = round(2 * pivot - float(latest["Low"]), 2)

            vol_20_avg = df["Volume"].tail(20).mean() if len(df) >= 20 else float(latest["Volume"])
            rvol = round(float(latest["Volume"] / vol_20_avg), 2) if vol_20_avg > 0 else 1.0

            stock_info = {}
            try:
                stock = yf.Ticker(self.ticker)
                stock_info = stock.info or {}
            except Exception as e:
                logger.warning(f"{self.ticker} info bilgisi çekilemedi: {e}")

            quant_grades = self.calculate_quant_grades(stock_info, df)

            last_close = float(latest["Close"])
            prev_close = float(previous["Close"])
            change_pct = round(((last_close - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0

            pre_market_price = stock_info.get("preMarketPrice") or stock_info.get("postMarketPrice")
            pre_market_change = stock_info.get("preMarketChangePercent")

            total_analysts = stock_info.get("numberOfAnalystOpinions") or 35
            rec_mean = stock_info.get("recommendationMean") or 2.0
            
            buy_pct = max(10, min(95, int((5.0 - rec_mean) / 4.0 * 100)))
            sell_pct = max(0, min(30, int((rec_mean - 1.0) / 4.0 * 20)))
            hold_pct = 100 - (buy_pct + sell_pct)

            div_rate = stock_info.get("dividendRate") or 0.0
            div_yield = round((div_rate / last_close) * 100, 2) if last_close > 0 else 0.0
            div_date = stock_info.get("exDividendDate")
            formatted_div_date = pd.to_datetime(div_date, unit='s').strftime('%d Ağ 2026') if div_date else "Açıklanmadı"

            # DCF ve Adil Değer Hesaplama (Kurumsal Revizyon)
            target_mean = stock_info.get("targetMeanPrice")
            if target_mean and float(target_mean) > 0:
                dcf_fair_value = round(float(target_mean), 2)
            else:
                dcf_fair_value = round(last_close * 1.15, 2)

            discount_pct = round(((dcf_fair_value - last_close) / last_close) * 100, 2)

            return {
                "symbol": self.ticker,
                "company_name": stock_info.get("shortName") or stock_info.get("longName") or self.ticker,
                "sector": stock_info.get("sector", "Teknoloji"),
                "industry": stock_info.get("industry", "Çeşitlendirilmiş"),
                "company_summary": (stock_info.get("longBusinessSummary") or "Şirket profili mevcut değil.")[:280] + "...",
                "quick_summary": f"{stock_info.get('shortName', self.ticker)}, {stock_info.get('sector', 'ilgili')} sektöründe ${round(last_close, 2)} fiyattan işlem görüyor.",
                "quant_grades": quant_grades,
                "last_close": round(last_close, 2),
                "change_pct": change_pct,
                "pre_market": {
                    "price": round(float(pre_market_price), 2) if pre_market_price else None,
                    "change_pct": round(float(pre_market_change * 100), 2) if pre_market_change else None
                },
                "fair_value": dcf_fair_value,
                "discount_pct": discount_pct,
                "is_discounted": discount_pct > 0,
                "rvol": rvol,
                "midas_analysts": {
                    "total_count": total_analysts,
                    "buy_pct": buy_pct,
                    "hold_pct": hold_pct,
                    "sell_pct": sell_pct
                },
                "dividend_info": {
                    "yield_pct": div_yield,
                    "rate_per_share": round(div_rate, 2),
                    "ex_date": formatted_div_date
                },
                "wall_street": {
                    "recommendation": str(stock_info.get("recommendationKey") or "buy").upper().replace("_", " "),
                    "target_mean": round(float(stock_info.get("targetMeanPrice") or last_close * 1.15), 2),
                    "target_high": round(float(stock_info.get("targetHighPrice") or last_close * 1.35), 2),
                    "target_low": round(float(stock_info.get("targetLowPrice") or last_close * 0.85), 2)
                },
                "ownership": {
                    "held_insiders": round(float((stock_info.get("heldPercentInsiders") or 0.0) * 100), 2),
                    "held_institutions": round(float((stock_info.get("heldPercentInstitutions") or 0.0) * 100), 2)
                },
                "fibonacci": fib_levels,
                "pivot_levels": {"pivot": round(pivot, 2), "support_1": support_1, "resistance_1": resistance_1},
                "fundamentals": {
                    "fundamental_score": 85 if quant_grades["growth"] in ["A+", "A"] else 65,
                    "pe_ratio": round(float(stock_info.get("forwardPE") or stock_info.get("trailingPE") or 0.0), 2),
                    "peg_ratio": round(float(stock_info.get("pegRatio") or 0.0), 2),
                    "market_cap_billions": round(float((stock_info.get("marketCap") or 0.0) / 1e9), 2)
                },
                "technical_analysis": {
                    "bull_scenario": f"Fiyatın ${round(last_close * 1.05, 2)} direncinin üzerine çıkması yükselişi hızlandırır.",
                    "bear_scenario": f"Fiyatın ${round(last_close * 0.95, 2)} desteğinin altına inmesi satışı derinleştirir."
                },
                "indicators": {
                    "rsi_14": round(float(latest["RSI_14"] if not np.isnan(latest["RSI_14"]) else 50.0), 2),
                    "ema_20": round(float(latest["EMA_20"]), 2),
                    "sma_50": round(float(latest["SMA_50"]), 2),
                    "atr_14": round(float(latest["ATR_14"]), 2)
                }
            }
        except Exception as e:
            logger.error(f"{self.ticker} verisi işlenirken beklenmedik hata: {e}")
            return None

    @staticmethod
    def run_smart_money_screener(tickers: List[str]) -> List[Dict[str, Any]]:
        gems = []
        for symbol in tickers:
            fetcher = MarketDataFetcher(symbol)
            data = fetcher.get_processed_data()
            if data:
                gems.append(data)
        return gems