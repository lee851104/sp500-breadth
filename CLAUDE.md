# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Layout

```
table20/
  design_mockup.html          ← Original static mockup
  mockup_a_terminal.html      ← Style alternative: Bloomberg terminal dark
  mockup_b_minimal.html       ← Style alternative: clean SaaS light
  mockup_c_neon.html          ← Style alternative: neon glassmorphism dark
  breadth_dashboard/          ← The live Streamlit application (all active development here)
    CLAUDE.md                 ← Detailed architecture, quirks, and HTML rules — read this too
```

All mockup HTMLs open directly in a browser with no server. All active development is inside `breadth_dashboard/`.

## Running the App

```powershell
cd breadth_dashboard
py -m streamlit run app.py
```

Open `http://localhost:8501`. First run takes 5–10 min (downloads ~503 tickers). Subsequent runs load from cache instantly.

## Syntax Check Without Running

```powershell
py -m py_compile breadth_dashboard/app.py
py -m py_compile breadth_dashboard/modules/breadth_calc.py
```

## Deploying to Streamlit Cloud

The app is deployed at `lee851104/sp500-breadth` on GitHub, branch `main`, entry point `breadth_dashboard/app.py`.  
After pushing changes, Streamlit Cloud auto-redeploys. To push:

```powershell
cd "c:\Users\User\Desktop\learn\claude code\table20"
git add .
git commit -m "..."
git push
```

## Architecture in One Paragraph

`sp500_fetcher.py` fetches the S&P 500 constituent list and market-cap weights from Wikipedia (uses a Chrome User-Agent to avoid 403). `market_data.py` downloads closing prices for all ~503 tickers from yfinance in batches of 50. `breadth_calc.py` computes the percentage of stocks above their 50-day and 200-day moving averages, per-stock metrics, sector aggregates, and multi-period sector breadth snapshots. `app.py` is a single-file Streamlit UI that reads from `config.py` for all thresholds and theme colours, then renders everything using injected CSS and Plotly charts. All data is cached via `diskcache` (SQLite, 24-hr TTL) and `@st.cache_resource`.

## Cache Clearing

Two cache layers must both be cleared to force a data refresh:

```python
cache.clear_all()           # clears diskcache (disk)
st.cache_resource.clear()   # clears Streamlit in-memory cache
st.rerun()
```

Clearing only one layer has no visible effect.

## Key Constants (`config.py`)

| Constant | Value | Meaning |
|---|---|---|
| `OVERBOUGHT` | 85 | Red / 減碼訊號 threshold |
| `OVERSOLD` | 15 | Green / 加碼訊號 threshold |
| `START_DATE` | `"2004-01-01"` | History start |
| `BATCH_SIZE` | 50 | Tickers per yfinance batch |

## Packaging as Windows EXE

```powershell
cd breadth_dashboard
py build_exe.py        # installs PyInstaller if missing, then builds
```

Output: `breadth_dashboard/dist/SP500_Breadth/SP500_Breadth.exe` (~300–500 MB folder).  
Distribute the entire `SP500_Breadth/` folder. `launcher.py` is the PyInstaller entry point — it passes `--global.developmentMode=false` to Streamlit (required, omitting causes RuntimeError) and opens the browser. `build_exe.py` copies `app.py`, `config.py`, and `modules/` next to the exe post-build because Streamlit reads source files from disk, not PyInstaller's temp dir.

See `breadth_dashboard/CLAUDE.md` for the full theme colour key, HTML generation rules, chart layer order, and known quirks.
