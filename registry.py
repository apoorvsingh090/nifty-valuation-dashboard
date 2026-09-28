"""Index registry: display names, Yahoo price tickers, local parquet mapping."""
import os

# Yahoo chart-API tickers verified to return long monthly history.
# Others returned only 1 row (Yahoo discontinued) -> valuation-only mode.
INDICES = {
    "nifty-50":          {"name": "Nifty 50",          "yahoo": "^NSEI",      "parquet": "NIFTY50-INDEX.parquet",      "type": "Broad / Large-cap"},
    "nifty-next-50":     {"name": "Nifty Next 50",     "yahoo": "^NSMIDCP",   "parquet": "NIFTYNXT50-INDEX.parquet",   "type": "Large-cap extender"},
    "nifty-100":         {"name": "Nifty 100",         "yahoo": None,         "parquet": "NIFTY100-INDEX.parquet",     "type": "Broad / Large-cap"},
    "nifty-500":         {"name": "Nifty 500",         "yahoo": None,         "parquet": "NIFTY500-INDEX.parquet",     "type": "Broad market"},
    "nifty-bank":        {"name": "Nifty Bank",        "yahoo": "^NSEBANK",   "parquet": "NIFTYBANK-INDEX.parquet",    "type": "Sector / Financials"},
    "nifty-it":          {"name": "Nifty IT",          "yahoo": "^CNXIT",     "parquet": None,                         "type": "Sector / Tech"},
    "nifty-pharma":      {"name": "Nifty Pharma",      "yahoo": None,         "parquet": None,                         "type": "Sector / Healthcare"},
    "nifty-fmcg":        {"name": "Nifty FMCG",        "yahoo": None,         "parquet": None,                         "type": "Sector / Staples"},
    "nifty-auto":        {"name": "Nifty Auto",        "yahoo": None,         "parquet": None,                         "type": "Sector / Cyclical"},
    "nifty-energy":      {"name": "Nifty Energy",      "yahoo": None,         "parquet": None,                         "type": "Sector / Energy"},
    "nifty-metal":       {"name": "Nifty Metal",       "yahoo": None,         "parquet": None,                         "type": "Sector / Cyclical"},
    "nifty-psu-bank":    {"name": "Nifty PSU Bank",    "yahoo": None,         "parquet": None,                         "type": "Sector / Financials"},
    "nifty-consumption": {"name": "Nifty Consumption", "yahoo": None,         "parquet": None,                         "type": "Theme / Consumption"},
    "nifty-infra":       {"name": "Nifty Infra",       "yahoo": None,         "parquet": None,                         "type": "Theme / Infra"},
    "nifty-realty":      {"name": "Nifty Realty",      "yahoo": None,         "parquet": None,                         "type": "Sector / Realty"},
    "nifty-media":       {"name": "Nifty Media",       "yahoo": None,         "parquet": None,                         "type": "Sector / Media"},
    "nifty-midcap-50":   {"name": "Nifty Midcap 50",   "yahoo": None,         "parquet": None,                         "type": "Mid-cap"},
    "nifty-midcap-100":  {"name": "Nifty Midcap 100",  "yahoo": None,         "parquet": None,                         "type": "Mid-cap"},
    "nifty-smallcap-50": {"name": "Nifty Smallcap 50", "yahoo": None,         "parquet": None,                         "type": "Small-cap"},
    "nifty-smallcap-100":{"name": "Nifty Smallcap 100","yahoo": None,         "parquet": None,                         "type": "Small-cap"},
}

def local_parquet_dir():
    # Local minutely store (user machine). On Render this is unset -> Yahoo/cache mode.
    for cand in [os.environ.get("LOCAL_PARQUET_DIR", ""), r"D:\index_minutely", "data/parquet"]:
        if cand and os.path.isdir(cand):
            return cand
    return None
