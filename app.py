"""NSE Index Valuation Dashboard — PE/PB timing: sizing vs entry/exit. Deploys on Render."""
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from registry import INDICES, local_parquet_dir
from data_loader import load_all_pe, load_pe, monthly_price_for
from analysis import verdict_for_index, signal_from_pct, ERA_START

st.set_page_config(page_title="NSE Valuation Timing Dashboard", layout="wide",
                   page_icon="📊")

SOURCE_NOTE = ("Valuation: NSE Indices via Downstox free CSV (monthly PE/PB/yield). "
               "Like-for-like stats use consolidated-earnings era only (Apr-2021 onward); "
               "NSE switched from standalone on 31 Mar 2021. Not investment advice.")

@st.cache_data(ttl=6 * 3600, show_spinner="Loading valuation history…")
def get_pe():
    return load_all_pe()

@st.cache_data(ttl=6 * 3600, show_spinner="Loading price history…")
def get_price(slug):
    meta = INDICES[slug]
    return monthly_price_for(slug, meta, local_parquet_dir())

@st.cache_data(ttl=6 * 3600)
def get_verdicts():
    pe = get_pe()
    out = {}
    for slug in INDICES:
        df = pe.get(slug)
        if df is None:
            continue
        px, _src = get_price(slug)
        out[slug] = verdict_for_index(slug, df, px)
    return out

def badge(label):
    color = {"Good sizing tool": "green", "Fair sizing tool": "blue",
             "Context only": "orange", "Avoid for timing": "red", "No data": "gray"}.get(label, "gray")
    return f":{color}[**{label}**]"

# ---------- header ----------
st.title("📊 NSE Index Valuation — can P/E (or P/B) time entries?")
st.caption(SOURCE_NOTE + " Educational tool. Not SEBI-registered advice.")
era_note = st.expander("⚠️ Read this: the 2021 methodology break", expanded=False)
with era_note:
    st.markdown(
        "On **31 Mar 2021 NSE moved index P/E from standalone to consolidated earnings**. "
        "Nifty 50 fell 40.43 → 33.20 overnight with no price move. "
        "Every percentile, median, 10th/90th band in this app is computed **only from Apr-2021 onward** "
        "so readings are like-for-like. Long charts show the full history with a break line at Apr-2021."
    )

pe_data = get_pe()
verdicts = get_verdicts()

# ---------- overview table ----------
st.subheader("Overview — all indices, current reading vs own era")
rows = []
for slug, meta in INDICES.items():
    v = verdicts.get(slug)
    if not v or not v.get("stats"):
        rows.append({"Index": meta["name"], "Signal": "—", "PE": "—", "PE pct": "—",
                     "PB": "—", "Yield %": "—", "PE use": "No data", "PB use": "No data"})
        continue
    s = v["stats"]
    rows.append({
        "Index": meta["name"],
        "Signal": v["signal"],
        "PE": round(s["cur_pe"], 2),
        "PE pct": f"{s['pe_pct']:.0f}th",
        "PE med (era)": round(s["pe_med"], 1),
        "PB": round(s["cur_pb"], 2) if pd.notna(s["cur_pb"]) else "—",
        "Yield %": round(s["cur_yield"], 2) if pd.notna(s["cur_yield"]) else "—",
        "EY %": round(s["ey"], 2),
        "PE use": v["pe_label"],
        "PB use": v["pb_label"],
    })
ov = pd.DataFrame(rows)
def _hl(r):
    if r["Signal"] in ("Cheap", "Fair-cheap"): return ["background-color:#e8f5e9"] * len(r)
    if r["Signal"] in ("Rich", "Extreme"): return ["background-color:#fce4ec"] * len(r)
    return [""] * len(r)
st.dataframe(ov.style.apply(_hl, axis=1), use_container_width=True, hide_index=True)
st.caption("Signal = current PE percentile within own consolidated era (≤10th Cheap, 10-30 Fair-cheap, 30-70 Fair, 70-90 Rich, >90 Extreme). "
           "Indices are never ranked against each other.")

# ---------- detail ----------
st.divider()
slugs = list(INDICES.keys())
default_ix = slugs.index("nifty-50") if "nifty-50" in slugs else 0
slug = st.selectbox("Index detail", slugs, index=default_ix,
                    format_func=lambda s: INDICES[s]["name"])
meta = INDICES[slug]
v = verdicts.get(slug)
df = pe_data.get(slug)

if df is None or v is None or not v.get("stats"):
    st.warning("No valuation history for this index.")
    st.stop()
s = v["stats"]
fwd = v.get("fwd", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{meta['name']} PE", f"{s['cur_pe']:.2f}", f"{s['pe_pct']:.0f}th pct of era")
c2.metric("Era median PE", f"{s['pe_med']:.1f}", f"P10 {s['pe_p10']:.1f} · P90 {s['pe_p90']:.1f}")
c3.metric("P/B", f"{s['cur_pb']:.2f}" if pd.notna(s['cur_pb']) else "—",
          f"med {s['pb_med']:.2f}" if pd.notna(s.get('pb_med', float('nan'))) else "")
c4.metric("Earnings yield", f"{s['ey']:.2f}%", f"Div {s['cur_yield']:.2f}%" if pd.notna(s['cur_yield']) else "")

st.markdown(f"**PE verdict:** {badge(v['pe_label'])} — {v['pe_why']}")
st.markdown(f"**P/B verdict:** {badge(v['pb_label'])} — {v['pb_why']}")
st.info(f"**Entry/exit:** {v['entry']} Keep SIPs running; use extremes only to scale size.")

# charts: PE/PB history + price
px, px_src = get_price(slug)
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=df.index, y=df["PE"], name="P/E", mode="lines"), secondary_y=False)
if "PB" in df:
    fig.add_trace(go.Scatter(x=df.index, y=df["PB"], name="P/B", mode="lines"), secondary_y=True)
if px is not None:
    aligned = df.join(px, how="inner")
    fig.add_trace(go.Scatter(x=aligned.index, y=aligned["price"], name=f"Price ({px_src})",
                             mode="lines", opacity=0.45), secondary_y=False)
fig.add_vline(x=pd.to_datetime(ERA_START), line_dash="dash",
              annotation_text="Apr-21 basis change")
fig.update_layout(title=f"{meta['name']} — P/E & P/B history (full series, break at Apr-21)",
                  hovermode="x unified", height=420, legend=dict(orientation="h"))
fig.update_yaxes(title_text="P/E (left) + price", secondary_y=False)
fig.update_yaxes(title_text="P/B (right)", secondary_y=True)
st.plotly_chart(fig, use_container_width=True)

# percentile gauge + era distribution
g1, g2 = st.columns([1, 2])
with g1:
    g = go.Figure(go.Indicator(mode="gauge+number", value=s["pe_pct"], title={"text": "PE percentile in era"},
                               gauge={"axis": {"range": [0, 100]},
                                      "steps": [{"range": [0, 10], "color": "#c8e6c9"},
                                                {"range": [10, 30], "color": "#e8f5e9"},
                                                {"range": [30, 70], "color": "#eeeeee"},
                                                {"range": [70, 90], "color": "#ffebee"},
                                                {"range": [90, 100], "color": "#ffcdd2"}]}))
    g.update_layout(height=260, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(g, use_container_width=True)
with g2:
    era = df[df.index >= ERA_START]["PE"].dropna()
    h = go.Figure()
    h.add_trace(go.Histogram(x=era, nbinsx=22, name="Era PE distribution"))
    h.add_vline(x=s["cur_pe"], line_color="red", annotation_text="current")
    h.add_vline(x=s["pe_med"], line_dash="dash", annotation_text="median")
    h.update_layout(title="Consolidated-era P/E distribution (Apr-21 → now)",
                    height=260, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(h, use_container_width=True)

# timing lab (only where price exists)
st.subheader("Timing lab — does starting valuation predict forward returns here?")
if fwd.get("n", 0) >= 36:
    m1, m2, m3 = st.columns(3)
    m1.metric("Overlap", f"{fwd['n']} months", f"{fwd['start']} → {fwd['end']}")
    m2.metric("PE→1yr corr", f"{fwd.get('corr_pe_fwd12m', float('nan')):.2f}",
              f"3yr {fwd.get('corr_pe_fwd36m', float('nan')):.2f}")
    m3.metric("PB→1yr corr", f"{fwd.get('corr_pb_fwd12m', float('nan')):.2f}",
              f"3yr {fwd.get('corr_pb_fwd36m', float('nan')):.2f}")
    st.caption("Negative = cheap (low ratio) precedes higher returns. |corr|<0.3 is noise; <-0.4 is usable for sizing; "
               "binary entry/exit needs much stronger + out-of-sample stability.")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown("**PE-quartile → median next-12m return**")
        bkt = fwd.get("pe_buckets_1y", {})
        if bkt:
            st.table(pd.DataFrame({"median 1-yr fwd": bkt}).T)
        else:
            st.write("—")
    with t2:
        st.markdown("**Tilt backtest (valuation-scaled exposure, cash 6%)**")
        st.write(f"Buy-hold: {fwd['bh_cagr']:.1%} CAGR, maxDD {fwd['bh_maxdd']:.1%}  →  "
                 f"Tilt: {fwd['tim_cagr']:.1%} CAGR, maxDD {fwd['tim_maxdd']:.1%} "
                 f"(avg expo {fwd['avg_expo']:.0%}, {fwd['bh_mult']:.2f}x vs {fwd['tim_mult']:.2f}x)")
        st.caption("Tilt uses prior-month ratio only (implementable). Costs/tax excluded — read the drawdown edge, not the CAGR edge.")
    # scatter
    aligned = df.join(px, how="inner").dropna(subset=["price"]).copy()
    aligned["fwd12"] = aligned["price"].shift(-12) / aligned["price"] - 1
    sc = go.Figure()
    sc.add_trace(go.Scatter(x=aligned["PE"], y=aligned["fwd12"], mode="markers", name="months",
                            text=aligned.index.strftime("%Y-%m"), hovertemplate="%{text}<br>PE %{x:.1f}<br>1-yr %{y:.1%}"))
    sc.update_layout(title="Starting P/E vs next-12m return (each dot = one month)",
                     xaxis_title="Starting P/E", yaxis_title="Next 12m return", height=340)
    st.plotly_chart(sc, use_container_width=True)
else:
    st.warning(f"Valuation-only mode for {meta['name']}: {fwd.get('reason', 'no long price history')}. "
               "Verdict above uses valuation mean-reversion diagnostics (CV, max/median, PE↔PB link), not a price backtest. "
               "Broad-market Pattern (Nifty 50/Bank/IT, where price exists) generalises: sizing yes, binary timing no.")

# learn
st.divider()
st.subheader("How to read this (informational)")
with st.expander("Sizing tool vs entry/exit tool — what the labels mean", expanded=True):
    st.markdown(
        "- **Good sizing tool**: ratio mean-reverts and cheap prints precede better 1-3yr returns. Scale exposure (e.g. 100/80/50/30%), never go 0%.\n"
        "- **Fair sizing / Context only**: directionally useful background; keep SIPs, defer lumpsums at extremes.\n"
        "- **Avoid for timing**: earnings-distorted (banks in NPA cycles, cyclicals, micro-caps, media/realty). High PE can mean collapsed E (distress), not overvaluation. Use P/B or skip.\n"
        "- **Entry/exit**: valuation alone is *not* recommended as a binary trigger for any index tested — even the best signal misses 1-yr moves and exits bull runs early. Use extremes only for tactical trim/add."
    )
with st.expander("Why Bank / PSU Bank / Metals / Realty / Media break P/E"):
    st.markdown(
        "Banks are leveraged: 1-2% ROA swings wipe out E and print PE 50-700 with no price move "
        "(Bank Nifty 2018-19 PE 53-67; Auto 737; Media 2483; Realty 755). "
        "In the dashboard these carry CV>0.35 and max/median>3 → graded *Avoid for timing*. P/B (CV~0.2-0.4) is the cleaner sizing dial there — "
        "Bank P/B→forward corr is −0.72 (1yr) / −0.80 (3yr) in 2017-26 vs −0.39/−0.26 for P/E."
    )
with st.expander("Data & refresh"):
    st.markdown(
        "- `python fetch_history.py` re-downloads all 20 CSVs into `data/pe/` (committed cache so Render builds offline).\n"
        "- Price: local `D:\\index_minutely` parquet if `LOCAL_PARQUET_DIR` set, else Yahoo chart API (`^NSEI`, `^NSEBANK`, `^CNXIT`, `^NSMIDCP` long history; "
        "other Yahoo sectorals are discontinued → valuation-only, by design).\n"
        f"- Loaded valuation files: {len(pe_data)} indices. Price-backed timing: "
        f"{sum(1 for k in INDICES if (lambda t: t[0] is not None)(get_price(k)))} indices."
    )
    if st.button("Refresh valuation cache now"):
        st.cache_data.clear()
        st.rerun()

st.caption("© Educational dashboard. Data: NSE Indices (via Downstox CSV), prices: user minutely files / Yahoo. Not investment advice.")
