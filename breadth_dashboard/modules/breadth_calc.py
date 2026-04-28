"""
計算市場寬度相關指標
- 歷史每日寬度（% 高於 50/200 日 MA）
- 個股當日指標（距均線 %、突破/跌破訊號、市值加權貢獻度）
- 板塊寬度分佈
"""
import pandas as pd
import numpy as np
from config import OVERBOUGHT, OVERSOLD


def calc_breadth_history(prices: pd.DataFrame) -> pd.DataFrame:
    """
    輸入：prices — index=日期, columns=symbol（調整後收盤價）
    輸出：DataFrame，index=日期，欄位 above_50, above_200（0–100 %）
    """
    sma50  = prices.rolling(50,  min_periods=40).mean()
    sma200 = prices.rolling(200, min_periods=150).mean()

    valid = prices.notna()
    n = valid.sum(axis=1).replace(0, np.nan)

    above_50  = (prices > sma50 ).sum(axis=1) / n * 100
    above_200 = (prices > sma200).sum(axis=1) / n * 100

    result = pd.DataFrame({
        "above_50":  above_50.round(2),
        "above_200": above_200.round(2),
    }).dropna()

    return result


def calc_stock_metrics(
    prices: pd.DataFrame,
    constituents: pd.DataFrame,
) -> pd.DataFrame:
    """
    計算每支股票的當日指標，用於排行榜。
    回傳 DataFrame，欄位：
      symbol, company, sector, weight_pct,
      price, daily_return,
      sma50, sma200,
      dist_50, dist_200,          # % 距均線
      above_50, above_200,        # bool
      signal_50, signal_200,      # +1 突破 / -1 跌破 / 0 無 (近5日)
      contrib_score               # weight_pct × daily_return
    """
    if prices.empty:
        return pd.DataFrame()

    sma50  = prices.rolling(50,  min_periods=40).mean()
    sma200 = prices.rolling(200, min_periods=150).mean()

    last   = prices.iloc[-1]
    prev   = prices.iloc[-2] if len(prices) > 1 else last
    s50_l  = sma50.iloc[-1]
    s200_l = sma200.iloc[-1]

    daily_return = (last / prev - 1) * 100

    # 突破/跌破：近 5 日內是否跨越均線
    def detect_signal(px: pd.DataFrame, sma: pd.DataFrame, window: int = 5) -> pd.Series:
        recent_px  = px.iloc[-window:]
        recent_sma = sma.iloc[-window:]
        above_now  = (recent_px.iloc[-1] > recent_sma.iloc[-1])
        crossed_up   = ((recent_px > recent_sma).any() & (recent_px < recent_sma).any())
        sig = pd.Series(0, index=px.columns)
        sig[above_now  & crossed_up] =  1
        sig[~above_now & crossed_up] = -1
        return sig

    sig50  = detect_signal(prices, sma50)
    sig200 = detect_signal(prices, sma200)

    records = []
    for _, row in constituents.iterrows():
        sym = row["symbol"]
        if sym not in prices.columns:
            continue
        p   = last.get(sym, np.nan)
        s50 = s50_l.get(sym, np.nan)
        s200= s200_l.get(sym, np.nan)
        ret = daily_return.get(sym, np.nan)
        w   = row.get("weight_pct", 0)

        records.append({
            "symbol":       sym,
            "company":      row["company"],
            "sector":       row["sector"],
            "weight_pct":   w,
            "price":        round(p, 2)   if pd.notna(p)   else None,
            "daily_return": round(ret, 2) if pd.notna(ret) else None,
            "sma50":        round(s50, 2) if pd.notna(s50) else None,
            "sma200":       round(s200,2) if pd.notna(s200) else None,
            "dist_50":      round((p / s50  - 1) * 100, 1) if pd.notna(p) and pd.notna(s50)  and s50  > 0 else None,
            "dist_200":     round((p / s200 - 1) * 100, 1) if pd.notna(p) and pd.notna(s200) and s200 > 0 else None,
            "above_50":     bool(p > s50)  if pd.notna(p) and pd.notna(s50)  else False,
            "above_200":    bool(p > s200) if pd.notna(p) and pd.notna(s200) else False,
            "signal_50":    int(sig50.get(sym, 0)),
            "signal_200":   int(sig200.get(sym, 0)),
            "contrib_score": round(w * ret / 100, 4) if pd.notna(ret) else 0.0,
        })

    return pd.DataFrame(records)


def calc_sector_breadth(stock_metrics: pd.DataFrame) -> pd.DataFrame:
    """
    按 GICS 板塊計算寬度（高於 50/200 日 MA 的比例）
    回傳：sector, count, above_50_pct, above_200_pct，依 above_50_pct 降序
    """
    if stock_metrics.empty:
        return pd.DataFrame()

    grp = stock_metrics.groupby("sector")
    result = pd.DataFrame({
        "count":         grp["symbol"].count(),
        "above_50_pct":  (grp["above_50"].sum() / grp["above_50"].count() * 100).round(1),
        "above_200_pct": (grp["above_200"].sum() / grp["above_200"].count() * 100).round(1),
    }).reset_index()

    return result.sort_values("above_50_pct", ascending=False)


def calc_sector_breadth_multiperiod(
    prices: pd.DataFrame,
    constituents: pd.DataFrame,
    periods: list = [5, 20, 50],
) -> pd.DataFrame:
    """
    計算各板塊在不同回顧期（N 日前）高於 50MA 的比例
    回傳：sector, sector_zh, count, pct_5d, pct_20d, pct_50d（依 pct_5d 降序）
    """
    from config import SECTOR_NAMES_ZH
    if prices.empty or constituents.empty:
        return pd.DataFrame()

    sma50 = prices.rolling(50, min_periods=40).mean()

    results = []
    sectors = constituents["sector"].dropna().unique()

    for sector in sectors:
        syms = constituents[constituents["sector"] == sector]["symbol"].tolist()
        syms = [s for s in syms if s in prices.columns]
        if not syms:
            continue
        row = {"sector": sector, "sector_zh": SECTOR_NAMES_ZH.get(sector, sector), "count": len(syms)}
        for p in periods:
            if len(prices) > p:
                px_n  = prices[syms].iloc[-(p+1)]
                sma_n = sma50[syms].iloc[-(p+1)]
                valid = sma_n.notna() & px_n.notna()
                n = valid.sum()
                pct = ((px_n[valid] > sma_n[valid]).sum() / n * 100) if n > 0 else None
            else:
                pct = None
            row[f"pct_{p}d"] = round(pct, 1) if pct is not None else None
        results.append(row)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df.sort_values("pct_5d", ascending=False, na_position="last").reset_index(drop=True)


def get_breadth_status(val: float) -> str:
    """根據寬度值回傳狀態文字"""
    if val >= OVERBOUGHT:
        return "overbought"
    if val <= OVERSOLD:
        return "oversold"
    return "normal"


def get_extreme_stats(history: pd.DataFrame) -> dict:
    """
    從歷史寬度 DataFrame 取最高/最低值及對應日期
    """
    if history.empty:
        return {}

    stats = {}
    for col in ["above_50", "above_200"]:
        if col not in history.columns:
            continue
        s = history[col].dropna()
        idx_high = s.idxmax()
        idx_low  = s.idxmin()
        stats[col] = {
            "max_val":  round(s.max(), 1),
            "max_date": str(idx_high.date()) if hasattr(idx_high, "date") else str(idx_high)[:10],
            "min_val":  round(s.min(), 1),
            "min_date": str(idx_low.date())  if hasattr(idx_low,  "date") else str(idx_low)[:10],
        }
    return stats
