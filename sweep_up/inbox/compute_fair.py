import numpy as np
import pandas as pd
from pathlib import Path

IN_FEAT = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\features_quarterly_with_wedge.csv")
OUT_FEAT = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\features_quarterly_with_fair.csv")
OUT_BASE = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\fair_summary_baseline_stats.csv")

COL_PERIOD = "period"
COL_GEO = "geo"

COL_WEDGE = "W"
COL_TURN_YOY = "gTO_yoy"
COL_NEWBUILD_SHARE = "newbuild_share_of_transactions"

BASE_WINDOWS = [("2003Q1","2007Q4"), ("2013Q1","2019Q4")]

W_WEDGE = 0.55
W_TURN  = -0.35
W_NB    = 0.10

def in_any_window(p: pd.Period, windows):
    for a, b in windows:
        if p >= pd.Period(a, freq="Q") and p <= pd.Period(b, freq="Q"):
            return True
    return False

def zscore(x: pd.Series, mu: float, sig: float) -> pd.Series:
    if sig == 0 or np.isnan(sig):
        return pd.Series(np.nan, index=x.index)
    return (x - mu) / sig

df = pd.read_csv(IN_FEAT)
df["p"] = pd.PeriodIndex(df[COL_PERIOD], freq="Q")
df = df.sort_values([COL_GEO, "p"]).reset_index(drop=True)

for c in [COL_GEO, COL_PERIOD, COL_WEDGE, COL_TURN_YOY]:
    if c not in df.columns:
        raise ValueError(f"Missing required column '{c}' in {IN_FEAT}")

use_nb = COL_NEWBUILD_SHARE in df.columns

if use_nb:
    df["dNB_yoy"] = df.groupby(COL_GEO)[COL_NEWBUILD_SHARE].pct_change(4)
else:
    df["dNB_yoy"] = np.nan

df["is_baseline"] = df["p"].apply(lambda p: in_any_window(p, BASE_WINDOWS))

stats_rows = []
out_frames = []

for geo, g in df.groupby(COL_GEO, sort=False):
    base_vars = [COL_WEDGE, COL_TURN_YOY] + (["dNB_yoy"] if use_nb else [])
    gb = g[g["is_baseline"]][base_vars].dropna()

    if gb.empty:
        raise ValueError(
            f"No valid baseline rows for geo={geo}. "
            f"Check coverage of {BASE_WINDOWS} and NaNs in {base_vars}."
        )

    muW,  sdW  = float(gb[COL_WEDGE].mean()), float(gb[COL_WEDGE].std(ddof=0))
    muTO, sdTO = float(gb[COL_TURN_YOY].mean()), float(gb[COL_TURN_YOY].std(ddof=0))
    if use_nb:
        muNB, sdNB = float(gb["dNB_yoy"].mean()), float(gb["dNB_yoy"].std(ddof=0))
    else:
        muNB, sdNB = np.nan, np.nan

    gg = g.copy()
    gg["zW"]  = zscore(gg[COL_WEDGE], muW, sdW)
    gg["zTO"] = zscore(gg[COL_TURN_YOY], muTO, sdTO)
    gg["zNB"] = zscore(gg["dNB_yoy"], muNB, sdNB) if use_nb else 0.0

    gg["fair_wedge_contrib"] = 100.0 * (W_WEDGE * gg["zW"])
    gg["fair_turn_contrib"]  = 100.0 * (W_TURN  * gg["zTO"])
    gg["fair_nb_contrib"]    = 100.0 * (W_NB    * gg["zNB"]) if use_nb else 0.0

    gg["FAIR"]  = gg["fair_wedge_contrib"] + gg["fair_turn_contrib"] + gg["fair_nb_contrib"]
    gg["dFAIR"] = gg["FAIR"].diff(1)

    stats_rows.append({
        "geo": geo,
        "baseline_windows": "; ".join([f"{a}-{b}" for a, b in BASE_WINDOWS]),
        "use_newbuild_term": bool(use_nb),
        "n_baseline_rows_used": int(len(gb)),
        "mu_W": muW, "sd_W": sdW,
        "mu_gTO_yoy": muTO, "sd_gTO_yoy": sdTO,
        "mu_dNB_yoy": muNB, "sd_dNB_yoy": sdNB,
    })
    out_frames.append(gg)

out = pd.concat(out_frames, ignore_index=True)

OUT_FEAT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_FEAT, index=False)
pd.DataFrame(stats_rows).to_csv(OUT_BASE, index=False)

print("Wrote:", OUT_FEAT)
print("Wrote:", OUT_BASE)
print(out[[COL_GEO, COL_PERIOD, "FAIR", "dFAIR"]].tail(10).to_string(index=False))
