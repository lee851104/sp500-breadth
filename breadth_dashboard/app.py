"""
S&P 500 市場寬度監控儀表板
執行：py -m streamlit run app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

import modules.cache as cache
from modules.sp500_fetcher import get_constituents_with_weight
from modules.market_data import download_prices
from modules.breadth_calc import (
    calc_breadth_history, calc_stock_metrics,
    calc_sector_breadth, calc_sector_breadth_multiperiod,
    get_breadth_status, get_extreme_stats,
)
from config import OVERBOUGHT, OVERSOLD, DARK, LIGHT, SECTOR_COLORS, SECTOR_NAMES_ZH

st.set_page_config(
    page_title="S&P 500 Breadth Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

for k, v in [("theme", "light"), ("sort_mode", "contrib"), ("time_range", "5Y")]:
    if k not in st.session_state:
        st.session_state[k] = v

T       = DARK if st.session_state.theme == "dark" else LIGHT
is_dark = st.session_state.theme == "dark"

# ─── CSS ─────────────────────────────────────────────────────
st.markdown(f"""<style>
.stApp {{background-color:{T['bg_body']};}}
.block-container {{padding:0 1.4rem 2rem 1.4rem !important;max-width:100% !important;}}
[data-testid="stSidebar"],#MainMenu,footer,.stDeployButton {{display:none !important;}}
div[data-testid="stVerticalBlock"]>div {{gap:0;}}
.stButton>button {{
    background:{T['bg_input']};border:1px solid {T['border']};
    color:{T['text_p']};border-radius:6px;font-size:11px;font-weight:600;
    padding:4px 14px;transition:background .15s,border-color .15s,color .15s;
    white-space:nowrap;min-height:30px;
}}
.stButton>button:hover {{border-color:{T['blue']};color:{T['blue']};background:{T['bg_surface']};}}
.stMarkdown p,.stMarkdown span {{color:{T['text_p']};}}
hr {{border:none;border-top:1px solid {T['border']};margin:4px 0 14px;}}
@keyframes blink {{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
</style>""", unsafe_allow_html=True)

# ─── 工具函數 ─────────────────────────────────────────────────
def card(html: str, pad: str = "16px 18px") -> None:
    st.markdown(
        '<div style="background:' + T["bg_card"] + ';border:1px solid ' + T["border"] + ';'
        'border-radius:10px;padding:' + pad + ';margin-bottom:12px;">'
        + html + '</div>', unsafe_allow_html=True)

def section_lbl(text: str, mb: str = "12px") -> str:
    return (
        '<span style="display:block;font-size:9px;font-weight:700;letter-spacing:.13em;'
        'text-transform:uppercase;color:' + T["text_dim"] + ';margin-bottom:' + mb + ';">'
        + text + '</span>')

def delta_html(val) -> str:
    if val is None: return ""
    c = T["green"] if val >= 0 else T["red"]
    a = "▲" if val >= 0 else "▼"
    return (
        '<span style="color:' + c + ';font-size:10.5px;font-weight:700;">' + a + "\u202f" + f"{abs(val):.1f}%" + '</span>'
        '<span style="color:' + T["text_dim"] + ';font-size:9px;">\u202f昨</span>')

def signal_tag(s50: int, s200: int) -> str:
    if s200 == 1:  return '<span style="background:' + T["gold"] + '22;color:' + T["gold"] + ';padding:2px 6px;border-radius:4px;font-size:9px;font-weight:700;">↑200d</span>'
    if s50  == 1:  return '<span style="background:' + T["blue"] + '22;color:' + T["blue"] + ';padding:2px 6px;border-radius:4px;font-size:9px;font-weight:700;">↑50d</span>'
    if s50  == -1: return '<span style="background:' + T["red"]  + '22;color:' + T["red"]  + ';padding:2px 6px;border-radius:4px;font-size:9px;font-weight:700;">↓50d</span>'
    if s200 == -1: return '<span style="background:' + T["red"]  + '22;color:' + T["red"]  + ';padding:2px 6px;border-radius:4px;font-size:9px;font-weight:700;">↓200d</span>'
    return '<span style="color:' + T["text_dim"] + ';font-size:11px;">—</span>'

def plot_base(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=4, r=16, t=10, b=4),
        font=dict(family="system-ui,sans-serif", color=T["text_p"], size=10),
        hovermode="x unified", dragmode="pan",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=T["tooltip_bg"], bordercolor=T["border"],
                        font_color=T["text_h"], font_size=11),
    )
    fig.update_xaxes(gridcolor=T["grid"], gridwidth=.5, showline=False, zeroline=False,
                     tickfont=dict(size=9, color=T["text_dim"]),
                     showspikes=True, spikecolor=T["text_dim"],
                     spikethickness=1, spikedash="dot", spikesnap="cursor")
    fig.update_yaxes(gridcolor=T["grid"], gridwidth=.5, showline=False, zeroline=False,
                     tickfont=dict(size=9, color=T["text_dim"]))
    return fig

# ─── 指標位置面板 ─────────────────────────────────────────────
def indicators_html(val50, val200) -> str:
    def _block(label, val):
        if val is None: return ""
        pct = float(val)
        dot = max(2.0, min(98.0, pct))
        if   pct <= OVERSOLD:   c = T["green"]
        elif pct >= OVERBOUGHT: c = T["red"]
        else:                   c = T["blue"]
        ds = f"{dot:.2f}"
        ps = f"{pct:.1f}"
        return (
            '<div style="flex:1;min-width:0;">'
            '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">'
            '<span style="font-size:12px;font-weight:700;color:' + T["text_p"] + ';">' + label + '</span>'
            '<span style="font-size:20px;font-weight:900;color:' + c + ';letter-spacing:-.5px;">' + ps + '%</span>'
            '</div>'
            '<div style="position:relative;height:10px;border-radius:5px;overflow:visible;background:' + T["bg_input"] + ';">'
            '<div style="position:absolute;left:0;top:0;width:15%;height:100%;background:' + T["green"] + '50;border-radius:5px 0 0 5px;"></div>'
            '<div style="position:absolute;left:85%;top:0;width:15%;height:100%;background:' + T["red"] + '50;border-radius:0 5px 5px 0;"></div>'
            '<div style="position:absolute;left:' + ds + '%;top:50%;width:16px;height:16px;'
            'border-radius:50%;background:' + c + ';transform:translate(-50%,-50%);z-index:5;'
            'box-shadow:0 0 6px ' + c + 'cc;border:2px solid ' + T["bg_card"] + ';"></div>'
            '</div>'
            '</div>'
        )

    if val50 is None and val200 is None: return ""
    return (
        '<div style="display:flex;gap:24px;align-items:center;">'
        + _block("50日市場寬度", val50)
        + '<div style="width:1px;height:40px;background:' + T["border"] + ';flex-shrink:0;"></div>'
        + _block("200日市場寬度", val200)
        + '</div>'
    )

# ─── 資料載入 ─────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_all_data():
    constituents = get_constituents_with_weight()
    symbols      = constituents["symbol"].tolist()
    _ph = st.empty(); _pb = st.empty()

    def on_progress(cur, total, msg):
        _ph.caption(msg); _pb.progress(int(cur / total * 100) if total else 0)

    prices        = download_prices(symbols, progress_cb=on_progress)
    _ph.empty(); _pb.empty()
    history       = calc_breadth_history(prices)
    stock_metrics = calc_stock_metrics(prices, constituents)
    sector_data   = calc_sector_breadth(stock_metrics)
    sector_multi  = calc_sector_breadth_multiperiod(prices, constituents)
    extremes      = get_extreme_stats(history)
    return history, stock_metrics, sector_data, sector_multi, extremes

with st.spinner("載入資料中…"):
    history, stock_metrics, sector_data, sector_multi, extremes = load_all_data()

def latest(col):
    if history.empty or col not in history.columns: return None, None
    s = history[col].dropna()
    return (float(s.iloc[-1]), float(s.iloc[-1] - s.iloc[-2])) if len(s) >= 2 else (None, None)

cur50,  d50  = latest("above_50")
cur200, d200 = latest("above_200")

# 資料最後交易日
data_date = (
    history.index[-1].strftime("%Y-%m-%d")
    if not history.empty else "—"
)
today_str = date.today().strftime("%Y-%m-%d")
is_stale  = (not history.empty) and (data_date < today_str)

# ═══════════════════════════════════════════════════════════════
# 頂部列
# ═══════════════════════════════════════════════════════════════
hdr_l, hdr_r = st.columns([5, 2])

with hdr_l:
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;padding:12px 0 6px;">'
        '<span style="font-size:14px;font-weight:700;letter-spacing:.06em;'
        'text-transform:uppercase;color:' + T["text_h"] + ';">S&amp;P 500 Breadth</span>'
        '<span style="width:7px;height:7px;border-radius:50%;background:' + T["green"] + ';'
        'display:inline-block;animation:blink 2s infinite;"></span>'
        '</div>', unsafe_allow_html=True)

with hdr_r:
    c1, c2 = st.columns(2)
    with c1:
        lbl_light = ("✓ " if not is_dark else "") + "淺色"
        if st.button(lbl_light, key="btn_light"):
            st.session_state.theme = "light"; st.rerun()
    with c2:
        lbl_dark = ("✓ " if is_dark else "") + "深色"
        if st.button(lbl_dark, key="btn_dark"):
            st.session_state.theme = "dark"; st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 指標面板 + 資料日期 + 更新按鈕
# ═══════════════════════════════════════════════════════════════
sig_html = indicators_html(cur50, cur200)
ind_col, btn_col = st.columns([5, 1], gap="small")

with ind_col:
    if sig_html:
        stale_badge = (
            ' <span style="font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;'
            'background:' + T["orange"] + '22;color:' + T["orange"] + ';">資料非最新</span>'
            if is_stale else ""
        )
        date_row = (
            '<div style="font-size:10px;color:' + T["text_dim"] + ';margin-bottom:8px;">'
            '資料截至 <b style="color:' + T["text_p"] + ';">' + data_date + '</b>'
            + stale_badge + '</div>'
        )
        card(date_row + sig_html, pad="10px 16px")

with btn_col:
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    if st.button("↻ 更新資料", key="btn_refresh"):
        cache.clear_all()
        st.cache_resource.clear()
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# 主體：左欄（大）+ 右欄
# ═══════════════════════════════════════════════════════════════
left_col, right_col = st.columns([3, 1], gap="medium")

# ───────────────────────────────────────────────────────────────
# 左欄
# ───────────────────────────────────────────────────────────────
with left_col:

    # ── 時間範圍按鈕 ────────────────────────────────────────
    range_opts = ["1Y", "3Y", "5Y", "10Y", "ALL"]
    rcols = st.columns([1, 1, 1, 1, 1, 6])
    for opt, rc in zip(range_opts, rcols):
        with rc:
            active = "✓ " if st.session_state.time_range == opt else ""
            if st.button(active + opt, key="r_" + opt):
                st.session_state.time_range = opt; st.rerun()

    # ── 歷史圖 ──────────────────────────────────────────────
    days_map = {"1Y": 365, "3Y": 1095, "5Y": 1825, "10Y": 3650, "ALL": 99999}
    cutoff   = pd.Timestamp(date.today() - timedelta(days=days_map[st.session_state.time_range]))
    h_plot   = history[history.index >= cutoff] if not history.empty else history

    fig = go.Figure()
    if not h_plot.empty:
        xs = h_plot.index.tolist()

        # 色帶
        fig.add_trace(go.Scatter(x=xs + xs[::-1], y=[OVERBOUGHT]*len(xs) + [100]*len(xs),
            fill="toself", fillcolor="rgba(224,86,86,0.10)",
            line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=xs + xs[::-1], y=[0]*len(xs) + [OVERSOLD]*len(xs),
            fill="toself", fillcolor="rgba(76,175,130,0.10)",
            line=dict(width=0), hoverinfo="skip", showlegend=False))

        # 50MA 面積填充
        fig.add_trace(go.Scatter(x=h_plot.index, y=h_plot["above_50"],
            fill="tozeroy", fillcolor=T["blue_fill"],
            line=dict(width=0), hoverinfo="skip", showlegend=False))

        # 參考線
        for yv, col, ann in [
            (OVERBOUGHT, T["red"],      " 超買 85%"),
            (OVERSOLD,   T["green"],    " 超賣 15%"),
            (50,         T["text_dim"], " 50%"),
        ]:
            fig.add_hline(y=yv, line_dash="dot", line_color=col, line_width=.8,
                          annotation_text=ann,
                          annotation_font=dict(size=8.5, color=col),
                          annotation_position="right")

        # 50MA 發光底層 + 主線
        fig.add_trace(go.Scatter(x=h_plot.index, y=h_plot["above_50"],
            line=dict(color=T["line_50_glow"], width=9),
            hoverinfo="skip", showlegend=False))

        # 計算 50MA hover 附加欄位
        y50 = h_plot["above_50"]
        chg50 = y50.diff()
        ma20_50 = y50.rolling(20).mean()
        customdata_50 = list(zip(
            chg50.fillna(0).round(1),
            ma20_50.fillna(y50).round(1),
        ))
        fig.add_trace(go.Scatter(x=h_plot.index, y=y50,
            name="50日均線寬度",
            line=dict(color=T["line_50"], width=2),
            customdata=customdata_50,
            hovertemplate=(
                "<b>50日寬度：%{y:.1f}%</b><br>"
                "日變化：%{customdata[0]:+.1f}%<br>"
                "20日均值：%{customdata[1]:.1f}%"
                "<extra></extra>"
            )))

        # 200MA 發光底層 + 細點虛線
        fig.add_trace(go.Scatter(x=h_plot.index, y=h_plot["above_200"],
            line=dict(color=T["line_200_glow"], width=7),
            hoverinfo="skip", showlegend=False))

        y200 = h_plot["above_200"]
        chg200 = y200.diff()
        ma20_200 = y200.rolling(20).mean()
        customdata_200 = list(zip(
            chg200.fillna(0).round(1),
            ma20_200.fillna(y200).round(1),
        ))
        fig.add_trace(go.Scatter(x=h_plot.index, y=y200,
            name="200日均線寬度",
            line=dict(color=T["line_200"], width=1.4, dash="dot"),
            customdata=customdata_200,
            hovertemplate=(
                "<b>200日寬度：%{y:.1f}%</b><br>"
                "日變化：%{customdata[0]:+.1f}%<br>"
                "20日均值：%{customdata[1]:.1f}%"
                "<extra></extra>"
            )))

        # ── 圖內當日數值注解（左上角）──────────────────────
        annotations_data = []
        if cur50  is not None: annotations_data.append((cur50,  d50,  T["line_50"],  "50日"))
        if cur200 is not None: annotations_data.append((cur200, d200, T["line_200"], "200日"))

        for i, (val, dlt, col, label_txt) in enumerate(annotations_data):
            arrow = "▲" if (dlt or 0) >= 0 else "▼"
            d_str = f"{abs(dlt or 0):.1f}%"
            ann_text = f"<b>{label_txt}：{val:.1f}%</b>  {arrow} {d_str}"
            fig.add_annotation(
                xref="paper", yref="paper",
                x=0.01, y=0.97 - i * 0.09,
                text=ann_text,
                showarrow=False,
                font=dict(size=10.5, color=col, family="system-ui"),
                align="left", xanchor="left", yanchor="top",
                bgcolor="rgba(0,0,0,0)",
            )

    fig = plot_base(fig, height=620)
    fig.update_yaxes(
        range=[0, 100],
        tickvals=[0, 15, 50, 85, 100],
        ticktext=["0%", "15%", "50%", "85%", "100%"],
        fixedrange=True,
    )

    chart_lbl = (
        '<div style="font-size:9px;font-weight:700;letter-spacing:.13em;'
        'text-transform:uppercase;color:' + T["text_dim"] + ';margin-bottom:10px;">'
        '歷史市場寬度（2004 – ' + str(date.today().year) + '）</div>'
    )
    st.markdown(
        '<div style="background:' + T["bg_card"] + ';border:1px solid ' + T["border"] + ';'
        'border-radius:10px;padding:16px 16px 4px;margin-bottom:12px;">' + chart_lbl,
        unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "displayModeBar": True,
        "modeBarButtonsToRemove": [
            "zoom2d","select2d","lasso2d","zoomIn2d","zoomOut2d","autoScale2d","toImage"],
        "displaylogo": False,
    })
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 板塊橫條圖 ──────────────────────────────────────────
    sector_rows = ""
    if not sector_data.empty:
        for _, row in sector_data.iterrows():
            pct  = row["above_50_pct"]
            name = SECTOR_NAMES_ZH.get(row["sector"], row["sector"])
            clr  = T["green"] if pct >= 60 else (T["orange"] if pct >= 40 else T["red"])
            sector_rows += (
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                '<div style="width:72px;font-size:11px;color:' + T["text_p"] + ';text-align:right;flex-shrink:0;">' + name + '</div>'
                '<div style="flex:1;height:16px;background:' + T["bg_input"] + ';border-radius:4px;position:relative;overflow:visible;">'
                '<div style="position:absolute;left:50%;top:-3px;width:1px;height:22px;background:' + T["border"] + ';z-index:1;"></div>'
                '<div style="width:' + f"{pct:.0f}" + '%;height:100%;background:' + clr + ';border-radius:4px;position:relative;z-index:2;"></div>'
                '</div>'
                '<div style="width:34px;font-size:10.5px;font-weight:700;color:' + clr + ';text-align:right;flex-shrink:0;">' + f"{pct:.0f}" + '%</div>'
                '</div>'
            )
    card(section_lbl("板塊寬度（高於 50日均線）") + sector_rows)

# ───────────────────────────────────────────────────────────────
# 右欄
# ───────────────────────────────────────────────────────────────
with right_col:

    # 排行榜排序按鈕
    sort_labels = {"contrib": "市值貢獻", "dist": "距均線", "signal": "突破訊號"}
    sc1, sc2, sc3 = st.columns(3)
    for key, col in [("contrib", sc1), ("dist", sc2), ("signal", sc3)]:
        with col:
            a = ("✓ " if st.session_state.sort_mode == key else "") + sort_labels[key]
            if st.button(a, key="sort_" + key):
                st.session_state.sort_mode = key; st.rerun()

    rank_rows = ""
    if not stock_metrics.empty:
        df_r = stock_metrics.copy()
        if   st.session_state.sort_mode == "contrib": df_r = df_r.nlargest(10, "contrib_score")
        elif st.session_state.sort_mode == "dist":    df_r = df_r.dropna(subset=["dist_50"]).nlargest(10, "dist_50")
        else:
            df_r["_sp"] = df_r["signal_200"].abs() * 2 + df_r["signal_50"].abs()
            df_r = df_r.nlargest(10, "_sp")

        for i, (_, row) in enumerate(df_r.iterrows(), 1):
            cs     = row.get("contrib_score", 0) or 0
            contrib = ("+" if cs >= 0 else "") + f"{cs*100:.2f}%"
            cc     = T["green"] if cs >= 0 else T["red"]
            d50v   = row.get("dist_50")
            if d50v is not None:
                dist_s = ("+" if d50v >= 0 else "") + f"{d50v:.1f}%"
                dc     = T["green"] if d50v >= 0 else T["red"]
            else:
                dist_s, dc = "—", T["text_dim"]

            rank_rows += (
                '<div style="display:flex;align-items:center;gap:5px;padding:9px 0;'
                'border-bottom:1px solid ' + T["border"] + ';">'
                '<div style="width:16px;color:' + T["text_dim"] + ';font-size:11px;flex-shrink:0;">' + str(i) + '</div>'
                '<div style="flex:1;min-width:0;">'
                '<span style="font-size:14px;font-weight:700;color:' + T["text_h"] + ';display:block;">' + row["symbol"] + '</span>'
                '<span style="font-size:10px;color:' + T["text_dim"] + ';display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:80px;">' + str(row["company"])[:18] + '</span>'
                '</div>'
                '<div style="font-size:12px;font-weight:700;color:' + cc + ';width:52px;text-align:right;">' + contrib + '</div>'
                '<div style="font-size:12px;font-weight:700;color:' + dc + ';width:46px;text-align:right;">' + dist_s + '</div>'
                '<div style="width:44px;text-align:right;">' + signal_tag(int(row.get("signal_50", 0) or 0), int(row.get("signal_200", 0) or 0)) + '</div>'
                '</div>'
            )

    rank_header = (
        '<div style="display:flex;align-items:center;gap:5px;padding-bottom:8px;'
        'border-bottom:1px solid ' + T["border"] + ';margin-bottom:2px;">'
        '<div style="width:16px;"></div>'
        '<div style="flex:1;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:' + T["text_dim"] + ';">股票</div>'
        '<div style="width:52px;text-align:right;font-size:10px;font-weight:700;color:' + T["text_dim"] + ';">貢獻</div>'
        '<div style="width:46px;text-align:right;font-size:10px;font-weight:700;color:' + T["text_dim"] + ';">距50</div>'
        '<div style="width:44px;text-align:right;font-size:10px;font-weight:700;color:' + T["text_dim"] + ';">訊號</div>'
        '</div>'
    )
    card(section_lbl("個股排行 Top 10") + rank_header + rank_rows)

    # 板塊多時間框架寬度表
    def _pct_cell(val):
        if val is None:
            return '<td style="padding:4px 6px;text-align:center;font-size:11px;color:' + T["text_dim"] + ';">—</td>'
        v = float(val)
        if v >= 70:   bg, fc = T["green"] + "28", T["green"]
        elif v >= 50: bg, fc = T["orange"] + "20", T["orange"]
        elif v >= 30: bg, fc = T["red"] + "18", T["red"]
        else:         bg, fc = T["red"] + "30", T["red"]
        return (
            '<td style="padding:4px 6px;text-align:center;font-size:11px;font-weight:700;'
            'color:' + fc + ';background:' + bg + ';border-radius:3px;">'
            + f"{v:.0f}%" + '</td>'
        )

    tbl_rows = ""
    if not sector_multi.empty:
        for _, row in sector_multi.iterrows():
            tbl_rows += (
                '<tr>'
                '<td style="padding:4px 6px;font-size:11px;color:' + T["text_p"] + ';white-space:nowrap;">'
                + str(row["sector_zh"]) + '</td>'
                + _pct_cell(row.get("pct_5d"))
                + _pct_cell(row.get("pct_20d"))
                + _pct_cell(row.get("pct_50d"))
                + '</tr>'
            )

    tbl_html = (
        '<table style="width:100%;border-collapse:separate;border-spacing:0 2px;">'
        '<thead><tr>'
        '<th style="padding:4px 6px;text-align:left;font-size:9px;font-weight:700;'
        'letter-spacing:.1em;text-transform:uppercase;color:' + T["text_dim"] + ';">板塊</th>'
        '<th style="padding:4px 6px;text-align:center;font-size:9px;font-weight:700;'
        'letter-spacing:.1em;text-transform:uppercase;color:' + T["text_dim"] + ';">5日</th>'
        '<th style="padding:4px 6px;text-align:center;font-size:9px;font-weight:700;'
        'letter-spacing:.1em;text-transform:uppercase;color:' + T["text_dim"] + ';">20日</th>'
        '<th style="padding:4px 6px;text-align:center;font-size:9px;font-weight:700;'
        'letter-spacing:.1em;text-transform:uppercase;color:' + T["text_dim"] + ';">50日</th>'
        '</tr></thead>'
        '<tbody>' + tbl_rows + '</tbody>'
        '</table>'
    )
    card(section_lbl("板塊寬度（高於 50MA %）") + tbl_html)
