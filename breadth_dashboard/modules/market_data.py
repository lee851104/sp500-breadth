"""
yfinance 批次下載所有 S&P 500 成分股的歷史收盤價
- 分批（BATCH_SIZE 支/批），批次間 sleep 避免 rate limit
- 完整資料快取 24 小時（diskcache）
- 提供 callback 讓 Streamlit 即時顯示進度
"""
import time
import pandas as pd
import yfinance as yf
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import modules.cache as cache
from config import START_DATE, CACHE_TTL, BATCH_SIZE, BATCH_SLEEP
from datetime import date
from typing import Callable, Optional

_PRICE_KEY = f"price_data_{date.today()}"


def download_prices(
    symbols: list[str],
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> pd.DataFrame:
    """
    下載所有成分股自 START_DATE 起的調整後日收盤價。
    回傳 DataFrame：index=日期, columns=symbol

    progress_cb(current_batch, total_batches, status_msg) — 用於 Streamlit 進度條
    """
    cached = cache.get(_PRICE_KEY)
    if cached is not None:
        return cached

    batches = [symbols[i:i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]
    total = len(batches)
    frames = []

    for idx, batch in enumerate(batches):
        if progress_cb:
            progress_cb(idx, total, f"下載第 {idx+1} / {total} 批（{batch[0]} …）")

        for attempt in range(3):
            try:
                raw = yf.download(
                    batch,
                    start=START_DATE,
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )
                # yfinance 多股票回傳 MultiIndex columns
                if isinstance(raw.columns, pd.MultiIndex):
                    close = raw["Close"]
                else:
                    # 單支股票
                    close = raw[["Close"]].rename(columns={"Close": batch[0]})
                frames.append(close)
                break
            except Exception as e:
                if attempt == 2:
                    # 三次皆失敗：略過此批
                    pass
                else:
                    time.sleep(10)

        if idx < total - 1:
            time.sleep(BATCH_SLEEP)

    if progress_cb:
        progress_cb(total, total, "下載完成，整理資料中…")

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, axis=1)
    prices.index = pd.to_datetime(prices.index)
    prices.sort_index(inplace=True)

    # 只保留 symbols 中存在的欄位，去除重複
    prices = prices.loc[:, ~prices.columns.duplicated()]

    cache.set(_PRICE_KEY, prices, ttl=CACHE_TTL)
    return prices
