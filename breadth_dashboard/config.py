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

# ── 主題顏色（深色） ─────────────────────────────────────────
DARK = {
    "bg_body":    "#181c24",
    "bg_surface": "#1e2330",
    "bg_card":    "#232a38",
    "bg_input":   "#2a3245",
    "border":     "#2e3650",
    "text_h":     "#d4d8e8",
    "text_p":     "#8e95ad",
    "text_dim":   "#525e78",
    "blue":       "#5b8af5",
    "orange":     "#e07b45",
    "green":      "#4caf82",
    "red":        "#e05656",
    "gold":       "#c9a84c",
    "line_50":      "#5cabff",
    "line_200":     "#ffb55a",
    "line_50_glow": "rgba(92,171,255,0.22)",
    "line_200_glow":"rgba(255,181,90,0.22)",
    "grid":       "#2e3650",
    "tooltip_bg": "#2a3245",
    # rgba 版本供 Plotly fillcolor 使用
    "red_fill":   "rgba(224,86,86,0.10)",
    "green_fill": "rgba(76,175,130,0.09)",
    "blue_fill":  "rgba(91,138,245,0.12)",
}

# ── 主題顏色（淺色） ─────────────────────────────────────────
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
