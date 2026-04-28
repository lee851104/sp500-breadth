"""
取得 S&P 500 成分股清單與市值加權比例
- 成分股清單：Wikipedia（帶瀏覽器 UA 繞過 403），備援用 yfinance SPY holdings
- 市值資料：yfinance Ticker.fast_info（7 天快取）
"""
import io
import requests
import pandas as pd
import yfinance as yf
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import modules.cache as cache
from config import CACHE_TTL, MCAP_TTL
from datetime import date


_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_CONSTITUENTS_KEY = f"sp500_constituents_{date.today()}"
_MCAP_KEY         = f"sp500_mcap_{date.today()}"

# 模擬瀏覽器 User-Agent，避免 Wikipedia 回傳 403
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _fetch_from_wikipedia() -> pd.DataFrame:
    resp = requests.get(_WIKI_URL, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0][["Symbol", "Security", "GICS Sector"]].copy()
    df.columns = ["symbol", "company", "sector"]
    df["symbol"] = df["symbol"].str.replace(".", "-", regex=False)
    return df.dropna(subset=["symbol"]).reset_index(drop=True)


def _fetch_fallback() -> pd.DataFrame:
    """備援：從 yfinance 下載 SPY 的持倉名單（只有 ticker，無 sector）"""
    spy = yf.Ticker("SPY")
    try:
        holdings = spy.funds_data.top_holdings
        symbols = [s.replace(".", "-") for s in holdings.index.tolist()]
    except Exception:
        # 最終備援：硬編碼前 50 大
        symbols = [
            "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","BRK-B","LLY","AVGO",
            "JPM","TSLA","UNH","XOM","V","PG","MA","COST","HD","JNJ",
            "ABBV","WMT","NFLX","BAC","CRM","ORCL","CVX","MRK","AMD","PEP",
            "KO","TMO","ACN","ADBE","LIN","MCD","ABT","WFC","TXN","PM",
            "DHR","NEE","AMGN","RTX","UPS","QCOM","HON","T","VZ","CAT",
        ]
    df = pd.DataFrame({
        "symbol":  symbols,
        "company": symbols,
        "sector":  ["Unknown"] * len(symbols),
    })
    return df


def get_constituents() -> pd.DataFrame:
    """回傳 DataFrame，欄位：symbol, company, sector"""
    cached = cache.get(_CONSTITUENTS_KEY)
    if cached is not None:
        return cached

    try:
        df = _fetch_from_wikipedia()
    except Exception as e:
        print(f"[sp500_fetcher] Wikipedia 失敗 ({e})，使用備援清單")
        df = _fetch_fallback()

    cache.set(_CONSTITUENTS_KEY, df, ttl=CACHE_TTL)
    return df


def get_constituents_with_weight() -> pd.DataFrame:
    """
    回傳帶市值加權的 DataFrame：symbol, company, sector, market_cap, weight_pct
    改用批次下載市值（yf.download info），失敗個股填 0
    """
    cached = cache.get(_MCAP_KEY)
    if cached is not None:
        return cached

    df = get_constituents().copy()
    symbols = df["symbol"].tolist()

    mcaps = {}
    # 分批查市值，避免單次請求過多
    for sym in symbols:
        try:
            fi = yf.Ticker(sym).fast_info
            mcaps[sym] = getattr(fi, "market_cap", 0) or 0
        except Exception:
            mcaps[sym] = 0

    df["market_cap"] = df["symbol"].map(mcaps).fillna(0)
    total = df["market_cap"].sum()
    df["weight_pct"] = (df["market_cap"] / total * 100) if total > 0 else 0.0

    cache.set(_MCAP_KEY, df, ttl=MCAP_TTL)
    return df
