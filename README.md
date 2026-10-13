# NSE Index Valuation — can P/E or P/B time entries?

Streamlit dashboard, live on Streamlit Community Cloud. Covers 20 prominent NSE indices.

For each index it tells you whether **P/E / P/B is a sizing tool, context-only, or avoid-for-timing**,
charts current ratios vs history, and (where long price history exists) tests starting-valuation → forward returns.

## Data

- Valuation: NSE Indices monthly PE/PB/dividend-yield via Downstox free CSV (`/api/index-pe/<slug>/download`), cached in `data/pe/`.
  Refresh: `python fetch_history.py`
- Prices: local minutely parquet (`LOCAL_PARQUET_DIR`, default `D:\index_minutely`) → Yahoo chart API
  (`^NSEI`, `^NSEBANK`, `^CNXIT`, `^NSMIDCP`). Other Yahoo sectorals are discontinued → valuation-only mode by design.

**Critical:** like-for-like stats use consolidated-earnings era only (Apr-2021 onward).
NSE switched from standalone on 31 Mar 2021 (Nifty 50 40.43 → 33.20 overnight, no price move).

## Run locally

```bash
pip install -r requirements.txt
python fetch_history.py   # optional refresh
streamlit run app.py
```

## Deploy

Primary: [Streamlit Community Cloud](https://share.streamlit.io/) — import the repo, main file `app.py`
([live demo](https://nifty-valuation-dashboard-ukginbjcfbe7kh8szddxhi.streamlit.app/)).

Alternative (Render): Blueprint via `render.yaml`, or manual Web Service:
- Runtime: Python, Build: `pip install -r requirements.txt`
- Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
- Python version: `3.11.9` (`runtime.txt`)

No secrets required. Educational tool, not investment advice.
