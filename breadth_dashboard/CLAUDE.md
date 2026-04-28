# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```powershell
# from the breadth_dashboard directory
py -m streamlit run app.py
```

`streamlit` is not in PATH — always use `py -m streamlit` instead of `streamlit` directly.

Syntax-check any file without running:
```powershell
py -m py_compile app.py
py -m py_compile modules/breadth_calc.py
```

## Architecture

Single-page Streamlit app with a data pipeline underneath.

```
app.py                  ← UI layout, Plotly charts, all HTML generation, CSS injection
config.py               ← All constants and theme colour dicts
launcher.py             ← PyInstaller entry point: starts Streamlit + opens browser automatically
build_exe.py            ← Run with `py build_exe.py` to produce dist/SP500_Breadth/SP500_Breadth.exe
modules/
  sp500_fetcher.py      ← S&P 500 constituents from Wikipedia + market-cap weights via yfinance
  market_data.py        ← Batched yfinance download of price history for all ~503 tickers
  breadth_calc.py       ← All indicator math: breadth history, per-stock metrics, sector breadth
  cache.py              ← Thin wrapper around diskcache; cache lives in ./cache/
```

**Data flow:** `sp500_fetcher` → `market_data` → `breadth_calc` → `app.py` renders

## Caching

- `diskcache` (SQLite-backed, `./cache/`) — TTL 24 hr for prices, 7 days for market caps.
- `@st.cache_resource` wraps `load_all_data()` in `app.py` — Streamlit skips it on re-renders.
- First run downloads ~503 tickers × 20 years (5–10 min). Subsequent runs load from cache instantly.
- Both cache layers must be cleared together to force a refresh:
  ```python
  cache.clear_all(); st.cache_resource.clear(); st.rerun()
  ```
  Clearing only `diskcache` has no effect because Streamlit still serves the in-memory copy.

## Key Config Values (`config.py`)

| Constant | Value | Purpose |
|---|---|---|
| `OVERBOUGHT` | 85 | Red threshold — 減碼訊號 |
| `OVERSOLD` | 15 | Green threshold — 加碼訊號 |
| `START_DATE` | `"2004-01-01"` | History start for yfinance |
| `BATCH_SIZE` | 50 | Tickers per yfinance download batch |
| `BATCH_SLEEP` | 1.5 s | Sleep between batches |

## Theme System

Two theme dicts in `config.py`: `DARK` (Omega Design System tokens), `LIGHT`. Default theme is **dark**.

`app.py` reads `st.session_state.theme`, selects `T = DARK or LIGHT`, and injects all colours via a `st.markdown("<style>…</style>")` block. Sora font is loaded via `<link rel="stylesheet">` (not `@import` — Streamlit's DOM injection breaks `@import`). Charts are rebuilt via `plot_base()` which reads from `T`.

Theme toggle is a single button (`btn_theme`) in the title row (cycles dark ↔ light). Default session-state values: `theme="dark"`, `time_range="5Y"`, `sort_mode="contrib"`. `.streamlit/config.toml` also sets `[theme] base="dark"` to ensure Streamlit Cloud renders dark before the first Python render.

### Colour Key Reference

| Key pattern | Format | Use for |
|---|---|---|
| `blue`, `red`, `green`, `orange`, `gold` | `#rrggbb` hex | CSS in `st.markdown` HTML |
| `line_50`, `line_200` | `#rrggbb` hex | Plotly `line.color` |
| `line_50_glow`, `line_200_glow` | `rgba(…)` | Plotly glow backing-trace `line.color` |
| `red_fill`, `green_fill`, `blue_fill` | `rgba(r,g,b,a)` | Plotly `fillcolor` **only** |

**Critical:** Plotly rejects 8-digit hex (`#rrggbbaa`). Never write `f"{T['red']}14"` as a Plotly colour — use the pre-defined `T["red_fill"]` or an inline `rgba()` string instead. CSS in `st.markdown` accepts 8-digit hex fine.

## HTML Generation Rules

All HTML in `app.py` is built by **string concatenation**, not f-strings with embedded expressions.

```python
# CORRECT — string concatenation
html = '<div style="color:' + T["red"] + ';">text</div>'

# WRONG — nested f-string with mixed quotes silently corrupts HTML
html = f'<div style="{f"color:{T[\"red\"]}"}">text</div>'  # corrupts
```

## Page Layout

```
Title row: 市場寬度 · Market Breadth + subtitle   [☀ 淺色 / ☾ 深色]
──────────────────────────────────────────────────────────────────
Meta row: ● 市場開盤中 · 更新於 YYYY-MM-DD  [資料非最新 badge if stale]
KPI gauges [5 cols]                          [↻ 更新資料 col]
  Left card:  50 日均線寬度  — large %, delta arrow, gauge track, signal label
  Right card: 200 日均線寬度 — same
──────────────────────────────────────────────────────────────────
Left col [3]                    Right col [1]
  Time-range st.radio (pill CSS)  查詢個股排名 (st.selectbox, all 503)
  Breadth chart card (620 px)     ↳ result card (if query active):
  Sector bar chart card               avatar chip + symbol + company
                                      三種排名並排 (#N / total)
                                      詳細資訊（依 sort_mode 切換）
                                  Tab indicator row (市值貢獻/距均線/突破訊號)
                                  Sort buttons (same 3 options, functional)
                                  Top-10 ranking table (dot + name + values)
                                  Sector multi-period table
                                    (5日 / 20日 / 50日 % above 50MA pill badges)
```

- **Time-range selector**: `st.radio(horizontal=True, key="time_range_radio")` with CSS overrides to hide radio dots and style labels as pills. Do NOT use `st.columns` + `st.button` — columns spread out to equal widths and cannot be collapsed.
- **Stock search**: `st.selectbox(key="ticker_lookup")` with all 503 options pre-loaded sorted by symbol. Streamlit's built-in text filtering handles fuzzy search; exact matches are sorted first. The `[data-baseweb="popover"]` CSS selector styles the dropdown dark.
- `indicators_html(val50, val200)` renders two separate rounded KPI cards (not one flex row); dot clamped to `[2, 98]%`; gauge has low/high colour zones.
- `data_date` is taken from `history.index[-1]`, not `date.today()`.
- "資料非最新" pill badge appears when `data_date < today`.
- Theme toggle (`btn_theme`) is in the title row right column; ↻ 更新資料 sits beside the KPI gauges.

## Chart Architecture (`app.py`)

`plot_base(fig, height)` applies shared layout to every Plotly figure:
- `hovermode="x unified"`, `dragmode="pan"`, spike lines on x-axis
- Transparent backgrounds, grid from `T["grid"]`

The main breadth chart uses a **layered trace stack** (order matters):
1. Red zone polygon (85–100%, `fill="toself"`)
2. Green zone polygon (0–15%, `fill="toself"`)
3. 50 MA area fill (`fill="tozeroy"`, `fillcolor=T["blue_fill"]`)
4. Three `add_hline` reference lines (85%, 15%, 50%)
5. 50 MA **glow backing trace** — thick width, `color=T["line_50_glow"]`, `hoverinfo="skip"`
6. 50 MA **main line** — `width=2`, `customdata=[day_change, 20d_avg]`, rich hovertemplate
7. 200 MA **glow backing trace** — `color=T["line_200_glow"]`, `hoverinfo="skip"`
8. 200 MA **main line** — `width=1.4`, `dash="dot"`, same customdata pattern
9. `add_annotation` for current values (top-left, `xref="paper"`, `yref="paper"`)

The y-axis is `fixedrange=True` (only horizontal pan/zoom allowed). `scrollZoom=True` is passed in `config={}` to `st.plotly_chart`.

## `breadth_calc.py` Functions

| Function | Output |
|---|---|
| `calc_breadth_history(prices)` | Daily `above_50`, `above_200` % history |
| `calc_stock_metrics(prices, constituents)` | Per-stock metrics: dist_50/200, signals, contrib_score |
| `calc_sector_breadth(stock_metrics)` | Current sector 50/200 MA % |
| `calc_sector_breadth_multiperiod(prices, constituents, periods)` | Sector % above 50MA at N days ago (default: 5, 20, 50) |
| `get_extreme_stats(history)` | All-time high/low values and dates |

## Stock Lookup (個股排名查詢)

The right column starts with a `st.text_input` (key `"ticker_lookup"`). Query resolution order:
1. Exact `symbol` match → use directly.
2. Fuzzy match on `symbol` + `company` (case-insensitive `str.contains`) → if exactly 1 hit, auto-resolve; if multiple, show `st.selectbox` (max 10 options).
3. No match → red "查無符合" card.

The result card has two sections:
- **Top**: three rank badges side-by-side — 市值貢獻 (`contrib_score` desc), 距均線 (`dist_50` desc, excludes NaN rows), 突破訊號 (`signal_200.abs()*2 + signal_50.abs()` desc). Colour: top 10% green, top 33% blue, mid grey, bottom dim.
- **Bottom**: switches with `st.session_state.sort_mode` — contrib shows contrib_score/daily_return/weight_pct; dist shows dist_50/above_50/dist_200/above_200; signal shows signal tags + dist values.

`contrib_score = weight_pct × daily_return / 100` — this is a *daily* contribution, not long-term performance. A heavy stock that falls hard ranks last.

## Important Quirks

- Wikipedia returns 403 to Python's default UA — `sp500_fetcher.py` sends a Chrome User-Agent.
- yfinance multi-ticker `download()` returns a `MultiIndex` columns DataFrame; `market_data.py` extracts only the `"Close"` level.
- Ticker symbols with `.` (e.g. `BRK.B`) are normalised to `-` (`BRK-B`) for yfinance compatibility.
- `calc_stock_metrics` detects breakout/breakdown signals over a rolling 5-day window, not just the current day.
- Plotly annotation `text` accepts limited HTML-like markup (bold via `<b>`), but not full HTML.
