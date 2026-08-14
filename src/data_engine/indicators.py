import pandas as pd
import numpy as np

class TechnicalIndicators:
    """Tüm teknik indikatörleri saf pandas/numpy ile hatasız hesaplar."""

    @staticmethod
    def calculate_sma(df: pd.DataFrame, window: int = 20, column: str = "Close") -> pd.Series:
        """Basit Hareketli Ortalama (SMA)"""
        return df[column].rolling(window=window).mean()

    @staticmethod
    def calculate_ema(df: pd.DataFrame, window: int = 20, column: str = "Close") -> pd.Series:
        """Üstel Hareketli Ortalama (EMA)"""
        return df[column].ewm(span=window, adjust=False).mean()

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, window: int = 14, column: str = "Close") -> pd.Series:
        """Göreceli Güç Endeksi (RSI)"""
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        # Sıfıra bölünme hatasını önle
        loss = loss.replace(0, np.nan)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)  # Yetersiz veride nötr değer (50) döndür

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = "Close"
    ) -> pd.DataFrame:
        """MACD, Sinyal Çizgisi ve Histogramı"""
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            "MACD": macd_line,
            "MACD_Signal": signal_line,
            "MACD_Hist": histogram
        })

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame, window: int = 20, num_std: float = 2.0, column: str = "Close"
    ) -> pd.DataFrame:
        """Bollinger Bantları (Üst, Orta, Alt)"""
        sma = df[column].rolling(window=window).mean()
        std = df[column].rolling(window=window).std()
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        return pd.DataFrame({
            "BB_Upper": upper_band,
            "BB_Middle": sma,
            "BB_Lower": lower_band
        })

    @staticmethod
    def calculate_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
        """Average True Range (Risk ve Stop-Loss hesabı için)"""
        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift())
        low_close = np.abs(df["Low"] - df["Close"].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return pd.Series(true_range).rolling(window=window).mean()