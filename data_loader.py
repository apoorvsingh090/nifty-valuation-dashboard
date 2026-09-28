"""Load PE/PB history (local cache, refreshable) + monthly price (local parquet -> Yahoo chart API)."""
import os, glob
import pandas as pd
import requests

PE_DIR = os.path.join(os.path.dirname(__file__), "data", "pe")

def load_pe(slug):
    path = os.path.join(PE_DIR, f"{slug}.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, comment="#")
    df["Month"] = pd.to_datetime(df["Month"])
    df = df.sort_values("Month").set_index("Month").asfreq("MS")
    # NSE sometimes publishes 0 for missing -> treat as NaN
    for c in ["PE", "PB", "DividendYield"]:
        if c in df.columns:
            df[c] = df[c].where(df[c] > 0)
    return df

def load_all_pe():
    out = {}
    for f in glob.glob(os.path.join(PE_DIR, "*.csv")):
        slug = os.path.splitext(os.path.basename(f))[0]
        df = load_pe(slug)
        if df is not None and len(df):
            out[slug] = df
    return out

def load_local_monthly_price(parquet_path):
    df = pd.read_parquet(parquet_path, columns=["datetime", "close"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    m = df.set_index("datetime")["close"].resample("ME").last()
    m.index = m.index.to_period("M").to_timestamp()
    m = m.rename("price").to_frame()
    m.index.name = "Month"
    return m.asfreq("MS")

def fetch_yahoo_monthly(ticker, rng="10y"):
    """Direct Yahoo chart API (more reliable than yfinance wrapper on Render)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    r = requests.get(url, params={"range": rng, "interval": "1mo"},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    ts = res.get("timestamp", [])
    closes = res["indicators"]["quote"][0].get("close", [])
    rows = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        rows.append((pd.to_datetime(t, unit="s").tz_localize("UTC").tz_convert("Asia/Kolkata").tz_localize(None), float(c)))
    if len(rows) < 12:
        return None  # insufficient (e.g. discontinued Yahoo sectoral series)
    px = pd.DataFrame(rows, columns=["Month", "price"]).sort_values("Month")
    px["Month"] = px["Month"].dt.to_period("M").dt.to_timestamp()
    px = px.groupby("Month").last().asfreq("MS")
    return px

def monthly_price_for(slug, meta, local_dir=None):
    # 1) local parquet (user's minutely files)
    pq = meta.get("parquet")
    if local_dir and pq:
        p = os.path.join(local_dir, pq)
        if os.path.exists(p):
            try:
                return load_local_monthly_price(p), "local-minutely"
            except Exception:
                pass
    # 2) Yahoo
    t = meta.get("yahoo")
    if t:
        for rng in ("10y", "max"):
            try:
                px = fetch_yahoo_monthly(t, rng)
                if px is not None:
                    return px, f"yahoo:{t}"
            except Exception:
                continue
    return None, "none"
