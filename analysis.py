"""Valuation stats + timing-effectiveness grading (PE vs PB: sizing vs entry/exit)."""
import numpy as np
import pandas as pd

ERA_START = "2021-04"  # NSE standalone -> consolidated break (31 Mar 2021). Like-for-like only after.
CASH_M = 0.005  # ~6% p.a. on uninvested sleeve in tilt backtest

def era_stats(pe_df):
    era = pe_df[pe_df.index >= ERA_START].copy()
    era = era[(era["PE"].notna())]
    if len(era) < 24:
        return None
    pe = era["PE"].dropna()
    pb = era["PB"].dropna() if "PB" in era else pd.Series(dtype=float)
    cur = pe_df.iloc[-1]
    def q(s, x): return float(np.percentile(s, x))
    out = {
        "n_era": int(len(pe)),
        "cur_pe": float(pe.iloc[-1]),
        "cur_pb": float(era["PB"].iloc[-1]) if "PB" in era and pd.notna(era["PB"].iloc[-1]) else float("nan"),
        "cur_yield": float(era["DividendYield"].iloc[-1]) if "DividendYield" in era else float("nan"),
        "pe_med": float(pe.median()),
        "pe_p10": q(pe, 10), "pe_p90": q(pe, 90),
        "pe_min": float(pe.min()), "pe_max": float(pe.max()),
        "pe_cv": float(pe.std() / pe.mean()) if pe.mean() else float("nan"),
        "pe_max_med": float(pe.max() / pe.median()) if pe.median() else float("nan"),
        "pb_med": float(pb.median()) if len(pb) else float("nan"),
        "pb_p10": q(pb, 10) if len(pb) else float("nan"),
        "pb_p90": q(pb, 90) if len(pb) else float("nan"),
        "pb_cv": float(pb.std() / pb.mean()) if len(pb) and pb.mean() else float("nan"),
        "pe_pb_corr": float(era[["PE", "PB"]].corr().iloc[0, 1]) if len(pb) else float("nan"),
        "pe_ar1": float(pe.autocorr(1)) if len(pe) > 3 else float("nan"),
    }
    # percentile rank of current within era (ties round up)
    out["pe_pct"] = float((pe <= out["cur_pe"]).mean() * 100)
    pbv = out["cur_pb"]
    out["pb_pct"] = float((pb <= pbv).mean() * 100) if len(pb) and pd.notna(pbv) else float("nan")
    out["ey"] = 100.0 / out["cur_pe"] if out["cur_pe"] else float("nan")
    return out

def signal_from_pct(p):
    if pd.isna(p): return "—"
    if p <= 10: return "Cheap"
    if p <= 30: return "Fair-cheap"
    if p <= 70: return "Fair"
    if p <= 90: return "Rich"
    return "Extreme"

def grade_metric(cv, max_med, corr_1y=None, corr_3y=None):
    """Return (label, detail) for one ratio."""
    if pd.isna(cv):
        return ("No data", "Insufficient history.")
    if cv > 0.35 or (not pd.isna(max_med) and max_med > 3.0):
        return ("Avoid for timing",
                "Earnings-distorted: spikes come from collapsing E, not price. High PE can mark distress, low PE can precede cuts. Do not use for entry/exit.")
    if cv > 0.25:
        return ("Context only",
                "Noisy: usable as background context for sizing, not as a trigger.")
    # low-vol regime
    pred = 0
    if corr_1y is not None and not pd.isna(corr_1y) and corr_1y < -0.30: pred += 1
    if corr_3y is not None and not pd.isna(corr_3y) and corr_3y < -0.40: pred += 1
    if pred >= 1:
        return ("Good sizing tool",
                "Mean-reverting and negatively linked to forward returns. Use to scale exposure, not binary in/out.")
    return ("Fair sizing tool",
            "Mean-reverting but weak forward link in sample. Use to tilt size; keep SIP running.")

def forward_analysis(pe_df, px_df):
    """Join monthly PE/PB to price; correlations + bucket medians + tilt backtest."""
    df = pe_df.join(px_df, how="inner").sort_index().dropna(subset=["price"])
    if len(df) < 36:
        return {"n": len(df), "reason": "insufficient overlap (<36 months)"}
    df["ret"] = df["price"].pct_change()
    res = {"n": len(df)}
    for h in (12, 36):
        fwd = df["price"].shift(-h) / df["price"] - 1
        df[f"fwd{h}m"] = fwd
        res[f"corr_pe_fwd{h}m"] = float(df[["PE", f"fwd{h}m"]].corr().iloc[0, 1])
        if "PB" in df:
            res[f"corr_pb_fwd{h}m"] = float(df[["PB", f"fwd{h}m"]].corr().iloc[0, 1])
    # bucket medians (1-yr) for PE
    try:
        df["pe_bkt"] = pd.qcut(df["PE"], 4, labels=["Q1 cheap", "Q2", "Q3", "Q4 rich"], duplicates="drop")
        res["pe_buckets_1y"] = df.groupby("pe_bkt", observed=True)["fwd12m"].median().round(4).to_dict()
    except Exception:
        res["pe_buckets_1y"] = {}
    # tilt backtest: PE exposure ladder vs buy-hold
    def expo_pe(pe):
        if pe < 20: return 1.0
        if pe < 22: return 0.8
        if pe < 25: return 0.5
        return 0.3
    if "PB" in df.columns:
        pb_med = float(df["PB"].median())
        def expo_pb(pb):
            if pb < pb_med * 0.9: return 1.0
            if pb < pb_med: return 0.7
            if pb < pb_med * 1.15: return 0.4
            return 0.2
        expo = df["PB"].apply(expo_pb)
    else:
        expo = df["PE"].apply(expo_pe)
    tim = expo.shift(1) * df["ret"] + (1 - expo.shift(1)) * CASH_M
    bh = (1 + df["ret"]).cumprod()
    tm = (1 + tim.fillna(0)).cumprod()
    n = len(df)
    res.update({
        "bh_mult": float(bh.iloc[-1]),
        "tim_mult": float(tm.iloc[-1]),
        "bh_cagr": float(bh.iloc[-1] ** (12 / n) - 1),
        "tim_cagr": float(tm.iloc[-1] ** (12 / n) - 1),
        "bh_maxdd": float((bh / bh.cummax() - 1).min()),
        "tim_maxdd": float((tm / tm.cummax() - 1).min()),
        "avg_expo": float(expo.mean()),
        "start": str(df.index.min().date()), "end": str(df.index.max().date()),
    })
    return res

def verdict_for_index(slug, pe_df, px_df=None):
    st = era_stats(pe_df)
    fwd = forward_analysis(pe_df, px_df) if px_df is not None else {"n": 0, "reason": "valuation-only (no long price history)"}
    if st is None:
        return {"slug": slug, "stats": None, "verdict": "No data", "fwd": fwd}
    c1 = fwd.get("corr_pe_fwd12m"); c3 = fwd.get("corr_pe_fwd36m")
    b1 = fwd.get("corr_pb_fwd12m"); b3 = fwd.get("corr_pb_fwd36m")
    pe_label, pe_why = grade_metric(st["pe_cv"], st["pe_max_med"], c1, c3)
    pb_label, pb_why = grade_metric(st["pb_cv"], 1.0, b1, b3)
    # Entry/exit is binary timing: almost never recommended on valuation alone.
    if "Avoid" in pe_label:
        entry = "Do NOT use PE for entry/exit on this index."
    elif "Good" in pe_label and fwd.get("n", 0) >= 60:
        entry = "PE may justify tactical trim/add at extremes only; never full exit."
    else:
        entry = "Not an entry/exit trigger — sizing aid at best."
    return {"slug": slug, "stats": st, "pe_label": pe_label, "pe_why": pe_why,
            "pb_label": pb_label, "pb_why": pb_why, "entry": entry, "fwd": fwd,
            "signal": signal_from_pct(st["pe_pct"])}
