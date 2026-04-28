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
from config import OVERBOUGHT, OVERSOLD, DARK, SECTOR_NAMES_ZH

st.set_page_config(
    page_title="S&P 500 Breadth Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.session_state.setdefault("sort_mode", "contrib")
st.session_state.setdefault("time_range", "5Y")
st.session_state.setdefault("theme", "dark")

from config import LIGHT
T       = DARK if st.session_state.theme == "dark" else LIGHT
is_dark = st.session_state.theme == "dark"

# ─── CSS ─────────────────────────────────────────────────────
st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True)

st.markdown(f"""<style>
html, body, [class*="css"] {{
    font-family: "Sora", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif !important;
    -webkit-font-smoothing: antialiased;
    font-variant-numeric: tabular-nums;
}}
.stApp {{background-color:{T['bg_body']};}}
.block-container {{padding:0 1.6rem 3rem 1.6rem !important;max-width:100% !important;}}
[data-testid="stSidebar"],#MainMenu,footer,.stDeployButton {{display:none !important;}}
div[data-testid="stVerticalBlock"]>div {{gap:0;}}

/* ── buttons ── */
.stButton>button {{
    background:{T['bg_input']};
    border:1px solid {T['border']};
    color:{T['text_p']};
    border-radius:999px;
    font-size:11px;font-weight:600;
    font-family:"Sora",sans-serif;
    padding:5px 16px;
    transition:background 180ms,border-color 180ms,color 180ms;
    white-space:nowrap;min-height:32px;
}}
.stButton>button:hover {{
    border-color:{T['blue']};color:{T['blue']};
    background:{T['bg_surface']};
}}

/* ── text input ── */
.stTextInput input {{
    background:{T['bg_input']} !important;
    border:1px solid {T['border']} !important;
    border-radius:12px !important;
    color:{T['text_h']} !important;
    font-family:"Sora",sans-serif !important;
    font-size:13px !important;
    padding:10px 14px !important;
}}
.stTextInput input:focus {{border-color:{T['blue']} !important;}}
.stTextInput label {{
    color:{T['text_dim']} !important;
    font-size:10px !important;font-weight:700 !important;
    text-transform:uppercase;letter-spacing:.12em;
}}

/* ── selectbox ── */
.stSelectbox > div > div {{
    background:{T['bg_input']} !important;
    border:1px solid {T['border']} !important;
    border-radius:12px !important;
    color:{T['text_h']} !important;
}}
.stSelectbox > div > div > div {{
    color:{T['text_h']} !important;
}}
/* 下拉選單本體 */
[data-baseweb="popover"] [data-baseweb="menu"] {{
    background:{T['bg_surface']} !important;
    border:1px solid {T['border']} !important;
    border-radius:12px !important;
}}
[data-baseweb="popover"] li {{
    background:{T['bg_surface']} !important;
    color:{T['text_p']} !important;
}}
[data-baseweb="popover"] li:hover {{
    background:{T['bg_input']} !important;
    color:{T['text_h']} !important;
}}
[data-baseweb="popover"] [aria-selected="true"] {{
    background:{T['bg_input']} !important;
    color:{T['green']} !important;
}}

.stMarkdown p,.stMarkdown span {{color:{T['text_p']};}}
hr {{border:none;border-top:1px solid {T['border']};margin:6px 0 16px;}}
@keyframes blink {{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
@keyframes pulse-dot {{0%,100%{{box-shadow:0 0 0 0 {T['green']}55}}50%{{box-shadow:0 0 0 5px {T['green']}00}}}}
</style>""", unsafe_allow_html=True)

# ─── 工具函數 ─────────────────────────────────────────────────
def card(html: str, pad: str = "20px 22px") -> None:
    st.markdown(
        '<div style="background:' + T["bg_card"] + ';border:1px solid ' + T["border"] + ';'
        'border-radius:20px;padding:' + pad + ';margin-bottom:14px;'
        'box-shadow:0 1px 0 rgba(255,255,255,0.04) inset,0 24px 60px -30px rgba(0,0,0,0.5);">'
        + html + '</div>', unsafe_allow_html=True)

def section_lbl(text: str, mb: str = "14px") -> str:
    return (
        '<span style="display:block;font-size:10px;font-weight:700;letter-spacing:.14em;'
        'text-transform:uppercase;color:' + T["text_dim"] + ';margin-bottom:' + mb + ';'
        'font-family:Sora,sans-serif;">'
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

# ─── 指標面板（Omega breadth-gauge KPI card 樣式）─────────────
def indicators_html(val50, val200) -> str:
    def _kpi(label, val, delta):
        if val is None: return ""
        pct = float(val)
        dot = max(2.0, min(98.0, pct))
        if   pct <= OVERSOLD:   c = T["green"];  signal = "超賣 · 加碼區"
        elif pct >= OVERBOUGHT: c = T["red"];    signal = "超買 · 減碼區"
        elif pct >= 60:         c = T["green"];  signal = "多頭健康"
        elif pct >= 40:         c = T["blue"];   signal = "中性"
        else:                   c = T["red"];    signal = "偏弱"

        ds   = f"{dot:.2f}"
        ps   = f"{pct:.1f}"
        dstr = ""
        if delta is not None:
            arr  = "↑" if delta >= 0 else "↓"
            dc   = T["green"] if delta >= 0 else T["red"]
            dstr = (
                '<span style="font-size:11px;font-weight:600;color:' + dc + ';margin-left:8px;">'
                + arr + ' ' + f"{abs(delta):.1f}pt" + '</span>'
            )

        return (
            '<div style="flex:1;min-width:0;background:' + T["bg_input"] + ';'
            'border:1px solid ' + T["border"] + ';border-radius:16px;padding:16px 18px 14px;">'
            # header row
            '<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:10px;">'
            '<span style="font-size:12px;font-weight:500;color:' + T["text_p"] + ';'
            'font-family:Sora,sans-serif;">' + label + '</span>'
            '<div style="display:flex;align-items:baseline;">'
            '<span style="font-size:24px;font-weight:700;color:' + c + ';'
            'letter-spacing:-.5px;font-family:Sora,sans-serif;">' + ps + '%</span>'
            + dstr +
            '</div>'
            '</div>'
            # gauge track
            '<div style="position:relative;height:8px;border-radius:999px;'
            'background:rgba(255,255,255,0.04);">'
            # low zone
            '<div style="position:absolute;left:0;top:0;width:15%;height:100%;'
            'background:rgba(242,106,126,0.16);border-radius:999px 0 0 999px;"></div>'
            # high zone
            '<div style="position:absolute;left:85%;top:0;width:15%;height:100%;'
            'background:rgba(34,210,122,0.16);border-radius:0 999px 999px 0;"></div>'
            # tick 50%
            '<div style="position:absolute;left:50%;top:-1px;bottom:-1px;width:1px;'
            'background:rgba(255,255,255,0.1);"></div>'
            # marker
            '<div style="position:absolute;left:' + ds + '%;top:50%;'
            'width:14px;height:14px;border-radius:50%;'
            'background:' + c + ';transform:translate(-50%,-50%);'
            'box-shadow:0 0 0 3px ' + c + '30;border:2px solid ' + T["bg_card"] + ';'
            'transition:left .4s cubic-bezier(.2,.8,.2,1);"></div>'
            '</div>'
            # foot label
            '<div style="display:flex;justify-content:space-between;margin-top:6px;">'
            '<span style="font-size:10px;color:' + T["text_dim"] + ';">0%</span>'
            '<span style="font-size:10px;font-weight:600;color:' + c + ';">' + signal + '</span>'
            '<span style="font-size:10px;color:' + T["text_dim"] + ';">100%</span>'
            '</div>'
            '</div>'
        )

    if val50 is None and val200 is None: return ""
    return (
        '<div style="display:flex;gap:12px;">'
        + _kpi("50 日均線寬度", val50, d50)
        + _kpi("200 日均線寬度", val200, d200)
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
# 標題列
# ═══════════════════════════════════════════════════════════════
_head_col, _theme_col = st.columns([9, 1])
with _head_col:
    st.markdown(
        '<div style="padding:20px 0 4px;">'
        '<div style="display:flex;align-items:baseline;gap:12px;">'
        '<h1 style="margin:0;font-size:26px;font-weight:700;letter-spacing:-.4px;'
        'color:' + T["text_h"] + ';font-family:Sora,sans-serif;line-height:1.1;">市場寬度</h1>'
        '<span style="font-size:15px;font-weight:400;color:' + T["text_p"] + ';'
        'font-family:Sora,sans-serif;">· Market Breadth</span>'
        '</div>'
        '<p style="margin:4px 0 0;font-size:12px;color:' + T["text_p"] + ';font-family:Sora,sans-serif;">'
        '追蹤 S&amp;P 500 成分股位於 50/200 日均線上方的比例 — 判斷大盤強弱與健康度'
        '</p>'
        '</div>',
        unsafe_allow_html=True)
with _theme_col:
    st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
    if st.button("☾ 深色" if not is_dark else "☀ 淺色", key="btn_theme"):
        st.session_state["theme"] = "light" if is_dark else "dark"
        st.rerun()
st.markdown(
    '<div style="border-top:1px solid ' + T["border"] + ';margin:4px 0 18px;"></div>',
    unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 指標面板（全寬 KPI gauges）+ 右側更新按鈕
# ═══════════════════════════════════════════════════════════════
sig_html = indicators_html(cur50, cur200)
if sig_html:
    stale_badge = (
        ' <span style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;'
        'background:rgba(201,184,156,0.14);color:' + T["orange"] + ';">資料非最新</span>'
        if is_stale else ""
    )
    meta_row = (
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">'
        '<span style="width:7px;height:7px;border-radius:50%;background:' + T["green"] + ';'
        'display:inline-block;animation:pulse-dot 2s infinite;'
        'box-shadow:0 0 0 3px rgba(34,210,122,0.18);"></span>'
        '<span style="font-size:12px;color:' + T["text_p"] + ';">市場開盤中</span>'
        '<span style="color:' + T["text_dim"] + ';font-size:12px;">·</span>'
        '<span style="font-size:12px;color:' + T["text_dim"] + ';">更新於 ' + data_date + '</span>'
        + stale_badge +
        '</div>'
    )
    ind_col, refresh_col = st.columns([5, 1])
    with ind_col:
        st.markdown(meta_row + sig_html, unsafe_allow_html=True)
        st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    with refresh_col:
        st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
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

    # ── 時間範圍（st.radio 水平排，CSS 改成 pill 樣式）─────
    range_opts = ["1Y", "3Y", "5Y", "10Y", "ALL"]
    st.markdown(f"""<style>
    div[data-testid="stRadio"] > div {{
        display:flex; flex-direction:row; gap:6px; flex-wrap:wrap;
    }}
    div[data-testid="stRadio"] label {{
        display:inline-flex; align-items:center;
        padding:5px 16px; border-radius:999px;
        background:rgba(255,255,255,0.04);
        border:1px solid {T['border']};
        color:{T['text_p']}; font-size:12px; font-weight:500;
        font-family:Sora,sans-serif; cursor:pointer;
        transition:all 180ms;
    }}
    div[data-testid="stRadio"] label:hover {{
        color:{T['text_h']}; border-color:{T['blue']};
    }}
    div[data-testid="stRadio"] label[data-selected="true"],
    div[data-testid="stRadio"] input:checked + div {{
        background:{T['bg_input']}; color:{T['text_h']};
        border-color:{T['blue']}; font-weight:700;
    }}
    div[data-testid="stRadio"] input {{ display:none; }}
    div[data-testid="stRadio"] p {{ font-size:12px; margin:0; }}
    div[data-testid="stRadio"] > label {{ display:none; }}
    </style>""", unsafe_allow_html=True)

    selected_range = st.radio(
        "time_range_radio",
        options=range_opts,
        index=range_opts.index(st.session_state.time_range),
        horizontal=True,
        label_visibility="collapsed",
        key="time_range_radio",
    )
    if selected_range != st.session_state.time_range:
        st.session_state.time_range = selected_range
        st.rerun()

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

    st.markdown(
        '<div style="background:' + T["bg_card"] + ';border:1px solid ' + T["border"] + ';'
        'border-radius:20px;padding:20px 20px 6px;margin-bottom:14px;'
        'box-shadow:0 1px 0 rgba(255,255,255,0.04) inset,0 24px 60px -30px rgba(0,0,0,0.5);">'
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">'
        '<div>'
        '<span style="font-size:14px;font-weight:600;color:' + T["text_h"] + ';'
        'font-family:Sora,sans-serif;">指數 vs 寬度走勢</span>'
        '<span style="font-size:10px;color:' + T["text_dim"] + ';margin-left:10px;'
        'border:1px solid ' + T["border"] + ';border-radius:999px;padding:2px 8px;">'
        + st.session_state.time_range + '</span>'
        '</div>'
        '<div style="display:flex;align-items:center;gap:14px;font-size:11px;color:' + T["text_p"] + ';">'
        '<span style="display:inline-flex;align-items:center;gap:5px;">'
        '<span style="display:inline-block;width:14px;height:2px;background:' + T["line_50"] + ';border-radius:1px;"></span>'
        '50 日寬度</span>'
        '<span style="display:inline-flex;align-items:center;gap:5px;">'
        '<span style="display:inline-block;width:14px;height:0;border-top:2px dashed ' + T["line_200"] + ';"></span>'
        '200 日寬度</span>'
        '</div>'
        '</div>'
        '<p style="font-size:11px;color:' + T["text_dim"] + ';margin:0 0 4px;font-family:Sora,sans-serif;">'
        '寬度走低於指數創高 = 警覺訊號</p>',
        unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={
        "scrollZoom": True, "displayModeBar": True,
        "modeBarButtonsToRemove": [
            "zoom2d","select2d","lasso2d","zoomIn2d","zoomOut2d","autoScale2d","toImage"],
        "displaylogo": False,
    })
    st.markdown("</div>", unsafe_allow_html=True)

    # ── 板塊橫條圖（Omega sector-bar 樣式）─────────────────
    sector_rows = ""
    if not sector_data.empty:
        for _, row in sector_data.iterrows():
            pct  = row["above_50_pct"]
            name = SECTOR_NAMES_ZH.get(row["sector"], row["sector"])
            if pct >= 60:
                clr = T["green"]; fill = "rgba(34,210,122,0.85)"
            elif pct >= 40:
                clr = T["blue"];  fill = "rgba(122,183,255,0.85)"
            else:
                clr = T["red"];   fill = "rgba(242,106,126,0.85)"
            sector_rows += (
                '<div style="display:grid;grid-template-columns:80px 1fr 44px;'
                'align-items:center;gap:12px;padding:5px 0;">'
                '<span style="font-size:12px;font-weight:500;color:' + T["text_p"] + ';'
                'font-family:Sora,sans-serif;white-space:nowrap;overflow:hidden;'
                'text-overflow:ellipsis;">' + name + '</span>'
                '<div style="position:relative;height:12px;background:rgba(255,255,255,0.04);'
                'border-radius:4px;overflow:hidden;">'
                '<div style="height:100%;width:' + f"{pct:.0f}" + '%;background:' + fill + ';'
                'border-radius:4px;transition:width .6s cubic-bezier(.2,.8,.2,1);"></div>'
                '</div>'
                '<span style="font-size:12px;font-weight:700;color:' + clr + ';'
                'text-align:right;font-family:Sora,sans-serif;">' + f"{pct:.0f}" + '%</span>'
                '</div>'
            )
    card(section_lbl("板塊寬度（高於 50 日均線）") + sector_rows)

# ───────────────────────────────────────────────────────────────
# 右欄
# ───────────────────────────────────────────────────────────────
with right_col:

    # ── 個股排名查詢（全清單 selectbox，打字即時過濾）────────
    resolved_symbol = None
    if not stock_metrics.empty:
        df_all = stock_metrics.copy()
        all_options = [
            row["symbol"] + "  " + str(row["company"])[:32]
            for _, row in df_all.sort_values("symbol").iterrows()
        ]
        chosen = st.selectbox(
            "查詢個股排名",
            options=[""] + all_options,
            key="ticker_lookup",
            placeholder="輸入代碼或公司名稱…",
        )
        resolved_symbol = chosen.split("  ")[0].strip() if chosen else None

        if resolved_symbol:
            rank_contrib = (
                df_all.assign(_rank=df_all["contrib_score"].rank(ascending=False, method="min"))
                .set_index("symbol")["_rank"]
            )
            rank_dist = (
                df_all.dropna(subset=["dist_50"])
                .assign(_rank=lambda d: d["dist_50"].rank(ascending=False, method="min"))
                .set_index("symbol")["_rank"]
            )
            df_all["_sp"] = df_all["signal_200"].abs() * 2 + df_all["signal_50"].abs()
            rank_signal = (
                df_all.assign(_rank=df_all["_sp"].rank(ascending=False, method="min"))
                .set_index("symbol")["_rank"]
            )

            total_contrib = len(rank_contrib)
            total_dist    = len(rank_dist)
            total_signal  = len(rank_signal)

            row_data = df_all[df_all["symbol"] == resolved_symbol].iloc[0]
            company_name = str(row_data.get("company", ""))[:22]

            r_contrib = int(rank_contrib.get(resolved_symbol, 0))
            r_dist    = int(rank_dist.get(resolved_symbol, 0)) if resolved_symbol in rank_dist.index else None
            r_signal  = int(rank_signal.get(resolved_symbol, 0))

            def _rank_color(r, total):
                pct = r / total if total else 1
                if pct <= 0.1:  return T["green"]
                if pct <= 0.33: return T["blue"]
                if pct <= 0.66: return T["text_p"]
                return T["text_dim"]

            def _rank_cell(r, total, label):
                if r is None:
                    val_html = '<span style="color:' + T["text_dim"] + ';font-size:12px;">—</span>'
                else:
                    c = _rank_color(r, total)
                    val_html = (
                        '<span style="font-size:16px;font-weight:900;color:' + c + ';">#' + str(r) + '</span>'
                        '<span style="font-size:10px;color:' + T["text_dim"] + ';"> / ' + str(total) + '</span>'
                    )
                return (
                    '<div style="flex:1;text-align:center;padding:8px 4px;">'
                    '<div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
                    'color:' + T["text_dim"] + ';margin-bottom:4px;">' + label + '</div>'
                    + val_html +
                    '</div>'
                )

            # 下半部：依目前排序模式顯示對應詳細資訊
            sort_mode = st.session_state.sort_mode

            def _detail_row(label, val_html):
                return (
                    '<div style="display:flex;justify-content:space-between;align-items:center;'
                    'padding:5px 0;border-bottom:1px solid ' + T["border"] + ';">'
                    '<span style="font-size:11px;color:' + T["text_dim"] + ';">' + label + '</span>'
                    + val_html +
                    '</div>'
                )

            def _val(v, suffix="", positive_green=True):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return '<span style="font-size:12px;color:' + T["text_dim"] + ';">—</span>'
                c = T["green"] if (v >= 0 and positive_green) else (T["red"] if (v < 0 and positive_green) else T["text_p"])
                sign = "+" if v >= 0 else ""
                return '<span style="font-size:12px;font-weight:700;color:' + c + ';">' + sign + f"{v:.2f}" + suffix + '</span>'

            if sort_mode == "contrib":
                cs  = row_data.get("contrib_score", 0) or 0
                ret = row_data.get("daily_return")
                w   = row_data.get("weight_pct")
                detail_html = (
                    _detail_row("市值貢獻度", _val(cs * 100, "%"))
                    + _detail_row("日漲跌幅", _val(ret, "%"))
                    + _detail_row("指數權重", '<span style="font-size:12px;font-weight:700;color:' + T["text_p"] + ';">' + (f"{w:.3f}%" if w is not None else "—") + '</span>')
                )
            elif sort_mode == "dist":
                d50  = row_data.get("dist_50")
                d200 = row_data.get("dist_200")
                a50  = row_data.get("above_50")
                a200 = row_data.get("above_200")
                def _above_badge(flag):
                    if flag is None: return '<span style="color:' + T["text_dim"] + ';">—</span>'
                    if flag:
                        return '<span style="font-size:11px;font-weight:700;padding:1px 6px;border-radius:3px;background:' + T["green"] + '22;color:' + T["green"] + ';">高於均線</span>'
                    return '<span style="font-size:11px;font-weight:700;padding:1px 6px;border-radius:3px;background:' + T["red"] + '22;color:' + T["red"] + ';">低於均線</span>'
                detail_html = (
                    _detail_row("距 50日均線", _val(d50, "%"))
                    + _detail_row("50日均線位置", _above_badge(a50))
                    + _detail_row("距 200日均線", _val(d200, "%"))
                    + _detail_row("200日均線位置", _above_badge(a200))
                )
            else:  # signal
                s50  = int(row_data.get("signal_50",  0) or 0)
                s200 = int(row_data.get("signal_200", 0) or 0)
                d50  = row_data.get("dist_50")
                d200 = row_data.get("dist_200")
                detail_html = (
                    _detail_row("50日均線訊號", signal_tag(s50, 0))
                    + _detail_row("200日均線訊號", signal_tag(0, s200))
                    + _detail_row("距 50日均線", _val(d50, "%"))
                    + _detail_row("距 200日均線", _val(d200, "%"))
                )

            lookup_html = (
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">'
                '<div style="width:32px;height:32px;border-radius:10px;background:' + T["bg_input"] + ';'
                'display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
                '<span style="font-size:11px;font-weight:800;color:' + T["text_p"] + ';'
                'font-family:Sora,sans-serif;">' + resolved_symbol[:2] + '</span>'
                '</div>'
                '<div>'
                '<div style="font-size:15px;font-weight:700;color:' + T["text_h"] + ';'
                'font-family:Sora,sans-serif;letter-spacing:-.2px;">' + resolved_symbol + '</div>'
                '<div style="font-size:11px;color:' + T["text_dim"] + ';margin-top:1px;">' + company_name + '</div>'
                '</div>'
                '</div>'
                '<div style="display:flex;gap:4px;padding-bottom:12px;'
                'border-bottom:1px solid ' + T["border"] + ';margin-bottom:12px;">'
                + _rank_cell(r_contrib, total_contrib, "市值貢獻")
                + '<div style="width:1px;background:' + T["border"] + ';margin:4px 0;"></div>'
                + _rank_cell(r_dist, total_dist, "距均線")
                + '<div style="width:1px;background:' + T["border"] + ';margin:4px 0;"></div>'
                + _rank_cell(r_signal, total_signal, "突破訊號")
                + '</div>'
                + detail_html
            )
            card(lookup_html, pad="16px 18px")

    # 排行榜排序按鈕（tabs 樣式）
    sort_labels = {"contrib": "市值貢獻", "dist": "距均線", "signal": "突破訊號"}
    tab_items = ""
    for k, lbl in sort_labels.items():
        is_on = st.session_state.sort_mode == k
        dot_c = T["green"] if is_on else T["text_dim"]
        border_c = T["green"] if is_on else "transparent"
        text_c = T["text_h"] if is_on else T["text_p"]
        tab_items += (
            '<span style="font-size:13px;font-weight:500;color:' + text_c + ';'
            'padding:8px 0;border-bottom:2px solid ' + border_c + ';'
            'margin-right:16px;cursor:pointer;font-family:Sora,sans-serif;">' + lbl + '</span>'
        )
    st.markdown(
        '<div style="display:flex;border-bottom:1px solid ' + T["border"] + ';margin-bottom:12px;">'
        + tab_items + '</div>',
        unsafe_allow_html=True)
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

            dot_c = T["green"] if cs >= 0 else T["red"]
            rank_rows += (
                '<div style="display:grid;grid-template-columns:8px 1fr auto;'
                'align-items:center;gap:10px;padding:9px 4px;border-radius:8px;">'
                # dot
                '<div style="width:6px;height:6px;border-radius:50%;background:' + dot_c + ';flex-shrink:0;"></div>'
                # name block
                '<div style="min-width:0;">'
                '<span style="font-size:13px;font-weight:700;color:' + T["text_h"] + ';'
                'display:block;font-family:Sora,sans-serif;">' + row["symbol"] + '</span>'
                '<span style="font-size:11px;color:' + T["text_dim"] + ';display:block;'
                'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'
                'font-variant-numeric:tabular-nums;">' + str(row["company"])[:20] + '</span>'
                '</div>'
                # right values
                '<div style="text-align:right;font-family:Sora,sans-serif;">'
                '<span style="font-size:13px;font-weight:700;color:' + cc + ';display:block;">' + contrib + '</span>'
                '<span style="font-size:11px;color:' + dc + ';display:block;">' + dist_s + '</span>'
                '</div>'
                '</div>'
            )

    card(section_lbl("個股排行 Top 10") + rank_rows)

    # 板塊多時間框架寬度表（Omega badge 樣式）
    def _pct_cell(val):
        if val is None:
            return (
                '<td style="padding:5px 6px;text-align:center;font-size:11px;'
                'color:' + T["text_dim"] + ';">—</td>'
            )
        v = float(val)
        if v >= 70:
            bg = "rgba(34,210,122,0.14)";  fc = T["green"]
        elif v >= 50:
            bg = "rgba(122,183,255,0.12)"; fc = T["blue"]
        elif v >= 30:
            bg = "rgba(242,106,126,0.12)"; fc = T["red"]
        else:
            bg = "rgba(242,106,126,0.20)"; fc = T["red"]
        return (
            '<td style="padding:5px 6px;text-align:center;">'
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'font-size:11px;font-weight:600;background:' + bg + ';color:' + fc + ';'
            'font-family:Sora,sans-serif;font-variant-numeric:tabular-nums;">'
            + f"{v:.0f}%" + '</span></td>'
        )

    tbl_rows = ""
    if not sector_multi.empty:
        for _, row in sector_multi.iterrows():
            tbl_rows += (
                '<tr style="border-bottom:1px solid ' + T["border"] + ';">'
                '<td style="padding:7px 6px;font-size:12px;font-weight:500;'
                'color:' + T["text_p"] + ';white-space:nowrap;font-family:Sora,sans-serif;">'
                + str(row["sector_zh"]) + '</td>'
                + _pct_cell(row.get("pct_5d"))
                + _pct_cell(row.get("pct_20d"))
                + _pct_cell(row.get("pct_50d"))
                + '</tr>'
            )

    th_style = (
        'padding:5px 6px;font-size:10px;font-weight:700;letter-spacing:.12em;'
        'text-transform:uppercase;color:' + T["text_dim"] + ';'
        'font-family:Sora,sans-serif;border-bottom:1px solid ' + T["border"] + ';'
    )
    tbl_html = (
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr>'
        '<th style="' + th_style + 'text-align:left;">板塊</th>'
        '<th style="' + th_style + 'text-align:center;">5日</th>'
        '<th style="' + th_style + 'text-align:center;">20日</th>'
        '<th style="' + th_style + 'text-align:center;">50日</th>'
        '</tr></thead>'
        '<tbody>' + tbl_rows + '</tbody>'
        '</table>'
    )
    card(section_lbl("板塊寬度（高於 50MA %）") + tbl_html)
