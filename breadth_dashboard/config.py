# ── 門檻值 ──────────────────────────────────────────────────
OVERBOUGHT = 85
OVERSOLD   = 15

# ── 資料範圍 ─────────────────────────────────────────────────
START_DATE  = "2004-01-01"
CACHE_DIR   = "./cache"
CACHE_TTL   = 86400          # 24 小時（秒）
MCAP_TTL    = 604800         # 7 天

# ── 批次下載設定 ─────────────────────────────────────────────
BATCH_SIZE  = 50             # 每批股票數
BATCH_SLEEP = 1.5            # 批次間等待秒數

# ── 主題顏色（深色）— Omega Design System tokens ─────────────
DARK = {
    # surfaces
    "bg_body":    "#0E1014",   # --bg-1 app shell
    "bg_surface": "#15181E",   # --bg-2 card
    "bg_card":    "#15181E",   # --bg-2
    "bg_input":   "#1B1F26",   # --bg-3 raised
    "border":     "rgba(255,255,255,0.06)",  # --line-1
    # text
    "text_h":     "#F2F4F7",   # --fg-1 primary
    "text_p":     "#9BA3AF",   # --fg-2 secondary
    "text_dim":   "#5A6270",   # --fg-3 tertiary
    # brand colours
    "blue":       "#7AB7FF",   # --accent-blue
    "orange":     "#C9B89C",   # --accent-sand
    "green":      "#22D27A",   # --accent-green
    "red":        "#F26A7E",   # --accent-rose
    "gold":       "#C9B89C",   # --accent-sand (reuse)
    # chart lines
    "line_50":      "#22D27A",              # green for 50MA
    "line_200":     "#7AB7FF",              # blue for 200MA
    "line_50_glow": "rgba(34,210,122,0.18)",
    "line_200_glow":"rgba(122,183,255,0.15)",
    "grid":       "rgba(255,255,255,0.06)",
    "tooltip_bg": "rgba(21,24,30,0.95)",
    # rgba 版本供 Plotly fillcolor 使用
    "red_fill":   "rgba(242,106,126,0.10)",
    "green_fill": "rgba(34,210,122,0.08)",
    "blue_fill":  "rgba(122,183,255,0.08)",
}

# ── 主題顏色（淺色）— 保留，供切換使用 ──────────────────────
LIGHT = {
    "bg_body":    "#f2f3f7",
    "bg_surface": "#ffffff",
    "bg_card":    "#ffffff",
    "bg_input":   "#f5f6fa",
    "border":     "#e0e3ee",
    "text_h":     "#252d42",
    "text_p":     "#5c6480",
    "text_dim":   "#9ba3bc",
    "blue":       "#3d6fdb",
    "orange":     "#c96a30",
    "green":      "#2e8a60",
    "red":        "#c94444",
    "gold":       "#a07c28",
    "line_50":      "#1a6dd4",
    "line_200":     "#d05f10",
    "line_50_glow": "rgba(26,109,212,0.15)",
    "line_200_glow":"rgba(208,95,16,0.15)",
    "grid":       "#e0e3ee",
    "tooltip_bg": "#f5f6fa",
    # rgba 版本供 Plotly fillcolor 使用
    "red_fill":   "rgba(201,68,68,0.08)",
    "green_fill": "rgba(46,138,96,0.08)",
    "blue_fill":  "rgba(61,111,219,0.10)",
}

# ── 板塊顏色映射 ─────────────────────────────────────────────
SECTOR_COLORS = {
    "Information Technology": "#5b8af5",
    "Consumer Discretionary": "#6fa8dc",
    "Financials":             "#4caf82",
    "Industrials":            "#57c47a",
    "Health Care":            "#9e9e9e",
    "Consumer Staples":       "#a8a8a8",
    "Real Estate":            "#e0a04a",
    "Utilities":              "#e07b45",
    "Materials":              "#e06060",
    "Energy":                 "#d94f4f",
    "Communication Services": "#c94040",
}

SECTOR_NAMES_ZH = {
    "Information Technology": "資訊科技",
    "Consumer Discretionary": "非必需消費",
    "Financials":             "金融",
    "Industrials":            "工業",
    "Health Care":            "醫療保健",
    "Consumer Staples":       "必需消費",
    "Real Estate":            "房地產",
    "Utilities":              "公用事業",
    "Materials":              "原物料",
    "Energy":                 "能源",
    "Communication Services": "通訊服務",
}
