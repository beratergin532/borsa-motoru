import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data_engine.fetcher import MarketDataFetcher
from src.data_engine.news import NewsEngine
from src.ai_engine.llm_client import HybridAIEngine
from src.risk_engine.portfolio import RiskEngine
from src.risk_engine.paper_trading import PaperTradingLogger
from src.notification_engine.scanner import AutoMarketScanner

st.set_page_config(
    page_title="Institutional Trading Terminal",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #0b0e14; }
    .stMetric { background-color: #151924; padding: 12px; border-radius: 8px; border: 1px solid #232733; }
    .quant-box { background-color: #1e222d; padding: 10px; border-radius: 6px; text-align: center; border: 1px solid #2a2e39; }
    .midas-summary { background-color: #151924; padding: 15px; border-radius: 8px; border-left: 4px solid #29b6f6; margin-bottom: 15px; }
    .midas-news-card { background-color: #151924; padding: 15px; border-radius: 8px; border: 1px solid #232733; margin-top: 15px; margin-bottom: 15px; }
    .card-bull { background-color: #0d2b1d; border-left: 4px solid #00e676; padding: 12px; border-radius: 6px; }
    .card-bear { background-color: #311319; border-left: 4px solid #ff1744; padding: 12px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=1800)
def cached_market_data(symbol: str):
    fetcher = MarketDataFetcher(symbol)
    return fetcher.get_processed_data()

@st.cache_data(ttl=3600)
def cached_ai_analysis(market_data: dict):
    ai_engine = HybridAIEngine()
    return ai_engine.generate_analysis(market_data)

st.sidebar.title("🏛️ Borsa Terminali")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Modül Seçin",
    options=[
        "🏠 Piyasa Genel Bakış",
        "🔍 Derin Hisse Analizi",
        "🏆 Seeking Alpha Top Rated Stocks",
        "⚔️ Rakip Karşılaştırma",
        "💼 Sanal Portföy (Paper Trading)"
    ]
)
st.sidebar.markdown("---")

# SAYFA 1: PİYASA GENEL BAKIŞ
if page == "🏠 Piyasa Genel Bakış":
    st.title("📈 Piyasa Genel Bakış & Otonom Tarama Engine")

    with st.spinner("Piyasa ve Emtia verileri çekiliyor..."):
        sp500 = yf.Ticker("^GSPC").history(period="2d")
        nasdaq = yf.Ticker("^IXIC").history(period="2d")
        vix = yf.Ticker("^VIX").history(period="2d")

        sp_close = round(sp500["Close"].iloc[-1], 2)
        sp_change = round(((sp500["Close"].iloc[-1] - sp500["Close"].iloc[-2]) / sp500["Close"].iloc[-2]) * 100, 2)
        nas_close = round(nasdaq["Close"].iloc[-1], 2)
        nas_change = round(((nasdaq["Close"].iloc[-1] - nasdaq["Close"].iloc[-2]) / nasdaq["Close"].iloc[-2]) * 100, 2)
        vix_close = round(vix["Close"].iloc[-1], 2)

        commodities = MarketDataFetcher.get_macro_commodities()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("S&P 500", f"{sp_close:,.2f}", f"%{sp_change}")
    c2.metric("NASDAQ 100", f"{nas_close:,.2f}", f"%{nas_change}")
    c3.metric("VIX Korku Endeksi", f"{vix_close} Puan")
    
    sentiment_score = max(10, min(90, int(100 - (vix_close * 2.5))))
    if sentiment_score >= 60:
        c4.success(f"Piyasa Duygusu: {sentiment_score}/100 (Boğa)")
    else:
        c4.warning(f"Piyasa Duygusu: {sentiment_score}/100 (Temkinli)")

    st.markdown("---")
    st.subheader("🥇 Altın, Gümüş ve Emtia Fiyatları")
    m_cols = st.columns(len(commodities)) if commodities else []
    for idx, item in enumerate(commodities):
        m_cols[idx].metric(item["name"], f"${item['price']:,.2f}", f"%{item['change']}")

# app.py -> SAYFA 1 (PİYASA GENEL BAKIŞ) İÇİNDEKİ OTONOM TARAMA BÖLÜMÜ:
    st.markdown("---")
    st.subheader("🤖 Otonom Piyasa Tarayıcısı & Sinyal Paneli")
    st.caption("Sistem takip listesindeki hisselerde kurumsal hacim patlaması veya %85+ alım fırsatı yakalarsa ekranında canlı kartlar olarak gösterir ve Telegram'a aktarır.")

    if st.button("📡 Otonom Piyasayı Tara ve Fırsatları Getir"):
        watch_list = ["NVDA", "AAPL", "MSFT", "MU", "AMD", "TSLA", "PLTR", "AMZN", "GOOGL", "META", "LLY", "AVGO"]
        with st.spinner("Piyasa taranıyor ve kritik sinyaller analiz ediliyor..."):
            found_signals = []
            ai_engine = HybridAIEngine()

            for sym in watch_list:
                data = cached_market_data(sym)
                if data:
                    rvol = data.get("rvol", 1.0)
                    rsi = data.get("indicators", {}).get("rsi_14", 50.0)
                    smart_money = data.get("smart_money_alert", False)

                    if smart_money or rsi <= 38:
                        report = cached_ai_analysis(data)
                        if report and report.strategy.action == "BUY":
                            found_signals.append({
                                "data": data,
                                "report": report
                            })
                            # Telegram Varsa Gönder (Hata alsa bile ekran akışı kesilmez)
                            try:
                                TelegramNotifier.send_signal_alert(
                                    symbol=sym,
                                    action=f"🚨 SİNYAL: {report.strategy.action}",
                                    confidence=report.strategy.confidence_score,
                                    price=data["last_close"],
                                    target=report.strategy.take_profit,
                                    stop=report.strategy.stop_loss,
                                    reasoning=report.summary_reasoning
                                )
                            except Exception:
                                pass

            if found_signals:
                st.success(f"Taramada {len(found_signals)} adet kritik fırsat tespit edildi!")
                for item in found_signals:
                    d = item["data"]
                    r = item["report"]
                    with st.expander(f"🟢 {d['symbol']} - {d['company_name']} | AI Güven: %{r.strategy.confidence_score} | Vade: {r.strategy.time_horizon}"):
                        c_a, c_b, c_c, c_d = st.columns(4)
                        c_a.metric("Anlık Fiyat", f"${d['last_close']}")
                        c_b.metric("DCF Adil Değer", f"${d['fair_value']}")
                        c_c.metric("Hedef Fiyat (TP)", f"${r.strategy.take_profit}")
                        c_d.metric("Stop Loss (SL)", f"${r.strategy.stop_loss}")
                        st.write(f"**AI Gerekçesi:** {r.summary_reasoning}")
                        st.write(f"**Hacim Oranı (RVOL):** `{d['rvol']}x` | **RSI (14):** `{d['indicators']['rsi_14']}`")
            else:
                st.info("Piyasa taranmıştır. Şu an için kriterlere uyan ekstra bir sinyal bulunmuyor.")
                
# SAYFA 2: DERİN HİSSE ANALİZİ (OTOMATİK ARAMA İPTAL EDİLDİ)
elif page == "🔍 Derin Hisse Analizi":
    st.title("🔍 Derin Hisse Analizi")

    with st.sidebar.form(key="search_form"):
        st.subheader("🔎 Hisse Arama Paneli")
        symbol_input = st.text_input("ABD Hisse Kodu Girin (Örn: NVDA, AAPL, MSFT)", value="").upper().strip()
        portfolio_input = st.number_input("Portföy Bakiyesi ($)", value=50000.0, step=1000.0)
        risk_profile = st.selectbox("Risk Profili", options=["balanced", "aggressive", "conservative"], index=0)
        submit_button = st.form_submit_button(label="🚀 Analiz Et")

    # Sayfa ilk açıldığında veya arama yapılmadığında yönlendirme mesajı gösterir
    if not symbol_input and not submit_button:
        st.info("👈 Analize başlamak için sol panelden bir ABD hisse kodu girip 'Analiz Et' butonuna basınız (Örn: NVDA, AAPL, MSFT, TSLA).")

    elif symbol_input:
        market_data = cached_market_data(symbol_input)

        if not market_data:
            st.error(f"'{symbol_input}' sembolüne ait borsa verisi çekilemedi. Geçerli bir kod girin.")
            st.stop()

        risk_engine = RiskEngine(portfolio_value=portfolio_input)
        risk_res = risk_engine.calculate_position(market_data, profile=risk_profile)

        ai_report = cached_ai_analysis(market_data)
        news_items = NewsEngine.get_company_news(symbol_input, limit=6)

        st.markdown(f"## {market_data['symbol']} - {market_data['company_name']}")
        
        div = market_data["dividend_info"]
        change_color = "#00e676" if market_data["change_pct"] >= 0 else "#ff1744"
        
        m_col1, m_col2, m_col3 = st.columns([2, 1, 1])
        with m_col1:
            st.markdown(
                f"<h1 style='display:inline;'>${market_data['last_close']:,.2f}</h1> "
                f"<span style='color:{change_color}; font-size:24px; font-weight:bold;'>%{market_data['change_pct']}</span>",
                unsafe_allow_html=True
            )
        with m_col2:
            st.metric("Temettü Tarihi", div["ex_date"])
        with m_col3:
            st.metric("Hisse Başı Temettü", f"${div['rate_per_share']}")

        st.markdown("---")

        st.subheader("📊 Analist Tahminleri (Wall Street)")
        m_analysts = market_data["midas_analysts"]
        st.caption(f"Son 3 ayda {m_analysts['total_count']} analistin verdiği tahminlerdir.")

        a_col1, a_col2, a_col3 = st.columns(3)
        a_col1.write(f"🟢 **Al (%{m_analysts['buy_pct']})**")
        a_col1.progress(m_analysts['buy_pct'] / 100)
        a_col2.write(f"⚪ **Tut (%{m_analysts['hold_pct']})**")
        a_col2.progress(m_analysts['hold_pct'] / 100)
        a_col3.write(f"🔴 **Sat (%{m_analysts['sell_pct']})**")
        a_col3.progress(m_analysts['sell_pct'] / 100)

        st.markdown("---")

        if ai_report:
            st.markdown(f"<div class='midas-summary'><b>🤖 AI Hisse Özeti:</b> {ai_report.summary_reasoning}</div>", unsafe_allow_html=True)

            with st.expander("🔎 Midas Tarzı Detaylı Boğa ve Ayı Analizini Gör"):
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.markdown("🟢 **Boğanın Dedikleri (Yükseliş Katalizörleri):**")
                    for opp in ai_report.thesis.opportunities:
                        st.write(f"• {opp}")
                with col_b2:
                    st.markdown("🔴 **Ayının Dedikleri (Düşüş Riskleri):**")
                    for rsk in ai_report.thesis.risks:
                        st.write(f"• {rsk}")

        st.markdown("---")

        st.subheader("🎖️ Seeking Alpha Quant Karnesi")
        q = market_data["quant_grades"]
        q1, q2, q3, q4 = st.columns(4)
        q1.markdown(f"<div class='quant-box'><b>Değerleme</b><br><h2>{q['valuation']}</h2></div>", unsafe_allow_html=True)
        q2.markdown(f"<div class='quant-box'><b>Büyüme</b><br><h2>{q['growth']}</h2></div>", unsafe_allow_html=True)
        q3.markdown(f"<div class='quant-box'><b>Kârlılık</b><br><h2>{q['profitability']}</h2></div>", unsafe_allow_html=True)
        q4.markdown(f"<div class='quant-box'><b>Momentum</b><br><h2>{q['momentum']}</h2></div>", unsafe_allow_html=True)

        st.markdown("---")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 İnteraktif Grafik & İndikatörler",
            "🎯 AI Karar & Risk Yönetimi",
            "📑 Bilanço & Sahiplik",
            "📰 Canlı Haberler"
        ])

        with tab1:
            # MIDAS STİLİ GRAFİK KONTROLLERİ (ZAMAN UFUKLARI & GRAFİK TÜRÜ)
            gc_col1, gc_col2 = st.columns([2, 1])
            with gc_col1:
                selected_period = st.radio(
                    "Zaman Aralığı Seçin:",
                    options=["1mo", "3mo", "6mo", "1y", "5y"],
                    format_func=lambda x: {"1mo": "1 Ay", "3mo": "3 Ay", "6mo": "6 Ay", "1y": "1 Yıl", "5y": "5 Yıl"}[x],
                    horizontal=True
                )
            with gc_col2:
                chart_type = st.radio("Grafik Türü:", options=["Mum Grafiği", "Çizgi Grafiği"], horizontal=True)

            df_hist = MarketDataFetcher(symbol_input).fetch_historical_data(period=selected_period)
            if df_hist is not None:
                df_hist["EMA20"] = df_hist["Close"].ewm(span=20, adjust=False).mean()
                df_hist["EMA50"] = df_hist["Close"].ewm(span=50, adjust=False).mean()

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                
                if chart_type == "Mum Grafiği":
                    fig.add_trace(go.Candlestick(x=df_hist.index, open=df_hist['Open'], high=df_hist['High'], low=df_hist['Low'], close=df_hist['Close'], name="Fiyat"), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Close'], name="Fiyat", line=dict(color='#00e676', width=2)), row=1, col=1)

                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA20'], name="EMA 20", line=dict(color='orange', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['EMA50'], name="EMA 50", line=dict(color='cyan', width=1.5)), row=1, col=1)

                fib_618 = market_data["fibonacci"]["fib_618"]
                fig.add_hline(y=fib_618, line_dash="dash", line_color="gold", annotation_text=f"Fibonacci %61.8 (${fib_618})", row=1, col=1)

                fig.add_trace(go.Bar(x=df_hist.index, y=df_hist['Volume'], marker_color='gray', name="Hacim"), row=2, col=1)
                fig.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

            # MIDAS STİLİ GRAFİK ALTI SON DAKİKA FLAŞ HABER KARTI
            if news_items:
                top_news = news_items[0]
                st.markdown(
                    f"""
                    <div class='midas-news-card'>
                        <span style='color:#888; font-size:12px;'>⏱️ Son Haber • {top_news['publisher']}</span><br>
                        <b style='font-size:16px;'>{top_news['badge']} {top_news['title']}</b>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                with st.expander("📰 Haber Analizini ve Detayını Gör >"):
                    st.write(f"**Duygu Analizi:** {top_news['sentiment']} | **Öncelik:** {top_news['priority']}")
                    st.markdown(f"-[Habere Git ({top_news['publisher']})]({top_news['link']})")

        with tab2:
            col_a, col_r = st.columns(2)
            with col_a:
                st.subheader("🤖 Yapay Zeka Karar Raporu")
                if ai_report:
                    st.write(f"- İşlem Vadesi: **{ai_report.strategy.time_horizon}**")
                    st.write(f"- Önerilen Alım: **${ai_report.strategy.suggested_entry}**")
                    st.write(f"- Stop Loss: **${ai_report.strategy.stop_loss}**")
                    st.write(f"- Hedef Fiyat: **${ai_report.strategy.take_profit}**")

            with col_r:
                st.subheader("🛡️ Risk Boyutlandırma")
                st.write(f"Maksimum Tutar: **${risk_res.max_position_dollars:,.2f}**")
                st.success(f"Önerilen Adet: **{risk_res.suggested_shares} Lot**")
                st.warning(f"ATR Stop Loss: **${risk_res.stop_loss_price}**")

                if st.button("📥 Sanal Portföye Ekle"):
                    if ai_report:
                        saved = PaperTradingLogger.log_trade_signal(
                            symbol=market_data['symbol'], action=ai_report.strategy.action,
                            confidence=ai_report.strategy.confidence_score, entry_price=market_data['last_close'],
                            stop_loss=risk_res.stop_loss_price, take_profit=risk_res.take_profit_price,
                            suggested_shares=risk_res.suggested_shares, reasoning=ai_report.summary_reasoning
                        )
                        if saved:
                            st.success("Portföye eklendi!")

        with tab3:
            own = market_data["ownership"]
            st.metric("Kurumsal Fon Sahipliği", f"%{own['held_institutions']}")
            st.metric("Şirket Yöneticileri (Insider)", f"%{own['held_insiders']}")

        with tab4:
            for item in news_items:
                st.markdown(f"**{item['badge']} [{item['sentiment']}]** - [{item['title']}]({item['link']}) *({item['publisher']})*")

# SAYFA 3: SEEKING ALPHA TOP RATED STOCKS
elif page == "🏆 Seeking Alpha Top Rated Stocks":
    st.title("🏆 Seeking Alpha Tarzı En Yüksek Puanlı Hisseler")
    top_leaders = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "LLY", "AVGO", "MU", "PLTR"]
    leader_rows = []
    for sym in top_leaders:
        data = cached_market_data(sym)
        if data:
            q = data["quant_grades"]
            leader_rows.append({
                "Sembol": data["symbol"], "Fiyat ($)": data["last_close"],
                "Wall St Görüşü": data["wall_street"]["recommendation"],
                "Değerleme": q["valuation"], "Büyüme": q["growth"], "Kârlılık": q["profitability"]
            })
    st.dataframe(pd.DataFrame(leader_rows), use_container_width=True)

# SAYFA 4: RAKİP KARŞILAŞTIRMA
elif page == "⚔️ Rakip Karşılaştırma":
    st.title("⚔️ Sektörel & Rakip Karşılaştırma")
    symbols_str = st.text_input("Semboller (Virgülle ayırın)", value="NVDA, AMD, INTC").upper()
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
    if st.button("Kıyasla") and symbols:
        comp_data = []
        for sym in symbols:
            d = cached_market_data(sym)
            if d:
                comp_data.append({
                    "Sembol": d["symbol"], "Fiyat ($)": d["last_close"],
                    "DCF Adil Değer ($)": d["fair_value"], "Fon Sahipliği (%)": d["ownership"]["held_institutions"],
                    "Değerleme": d["quant_grades"]["valuation"], "Büyüme": d["quant_grades"]["growth"]
                })
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True)

# SAYFA 5: SANAL PORTFÖY
elif page == "💼 Sanal Portföy (Paper Trading)":
    st.title("💼 Sanal Portföy ve Canlı PnL Takibi")
    trades = PaperTradingLogger.get_portfolio_summary()
    if trades:
        st.dataframe(pd.DataFrame(trades), use_container_width=True)
    else:
        st.info("Henüz sanal işlem bulunmuyor.")