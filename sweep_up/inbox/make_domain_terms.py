import os
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"


# ---------
# CONFIG
# ---------
GEO = "EW"
START_PERIOD = "2020Q3"

# Baseline anchors (from your Terms of Domain paragraph)
BASE_DWELLINGS = 28_536_000
BASE_SQFT = 29_180_071_800

# Paths: adjust if needed
DATA_Q = r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\features_quarterly_with_fair.csv"

OUT_FIG = r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\figures"
OUT_ASSETS = r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\draft_paper_assets"
os.makedirs(OUT_FIG, exist_ok=True)
os.makedirs(OUT_ASSETS, exist_ok=True)

# ---------
# LOAD
# ---------
df = pd.read_csv(DATA_Q)

# Basic hygiene
df = df[df["geo"] == GEO].copy()
df["period"] = df["period"].astype(str)

# Sort by period (works if format like 2003Q1)
df["year"] = df["period"].str.slice(0, 4).astype(int)
df["q"] = df["period"].str[-1].astype(int)
df = df.sort_values(["year", "q"]).reset_index(drop=True)

END_PERIOD = df["period"].iloc[-1]

# Extract states (with clearer errors if missing)
_start = df[df["period"] == START_PERIOD]
_end = df[df["period"] == END_PERIOD]
if _start.empty:
    raise ValueError(f"START_PERIOD not found in data: {START_PERIOD}")
if _end.empty:
    raise ValueError(f"END_PERIOD not found in data: {END_PERIOD}")

s1 = _start.iloc[0]
s2 = _end.iloc[0]


def snapshot_row(s: pd.Series) -> dict:
    # Prefer the newer name; fall back to legacy if present
    if "all_dwellings_n" in s.index and pd.notna(s["all_dwellings_n"]):
        dwellings = float(s["all_dwellings_n"])
    elif "all_dwellings_raw" in s.index and pd.notna(s["all_dwellings_raw"]):
        dwellings = float(s["all_dwellings_raw"])
    else:
        raise KeyError("No dwellings column found (expected all_dwellings_n or all_dwellings_raw)")

    sqft = BASE_SQFT * (dwellings / BASE_DWELLINGS)

    return {
        "period": str(s["period"]),
        "mortgage_stock_gbp_bn": float(s["mb_total_gbp_m"]) / 1000.0,
        "dwellings_m": dwellings / 1_000_000.0,
        "implied_footprint_sqft_bn": sqft / 1_000_000_000.0,
        "transactions_k": float(s["tx_total"]) / 1000.0,
        "turnover_pct_q": float(s["turnover_pct_q"]),
        "avg_house_price_gbp": float(s["avg_house_price_gbp"]),
        "FAIR": float(s["FAIR"]) if "FAIR" in s.index and pd.notna(s["FAIR"]) else None,
    }


domain = pd.DataFrame([snapshot_row(s1), snapshot_row(s2)])

# Add deltas for readability
delta = domain.iloc[1].copy()
delta["period"] = "Î” (End - Start)"
for c in [
    "mortgage_stock_gbp_bn",
    "dwellings_m",
    "implied_footprint_sqft_bn",
    "transactions_k",
    "turnover_pct_q",
    "avg_house_price_gbp",
    "FAIR",
]:
    if c in domain.columns and pd.notna(domain.loc[0, c]) and pd.notna(domain.loc[1, c]):
        delta[c] = domain.loc[1, c] - domain.loc[0, c]

domain_out = pd.concat([domain, pd.DataFrame([delta])], ignore_index=True)

# Save domain table
domain_csv_path = os.path.join(OUT_ASSETS, "domain_terms_state1_state2.csv")
domain_out.to_csv(domain_csv_path, index=False)

# ---------
# FIG 1: Mortgage stock
# ---------
plt.figure(figsize=(10, 4.5))
plt.plot(df["period"], df["mb_total_gbp_m"] / 1000.0, linewidth=2)
plt.axvline(START_PERIOD, color="black", linestyle="--", linewidth=1)
plt.axvline(END_PERIOD, color="black", linestyle="--", linewidth=1)
plt.title(f"Mortgage stock outstanding (Â£bn) â€” {GEO}")
plt.ylabel("Â£bn")
plt.xticks(df["period"][::8], rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_FIG, "fig_domain_mortgage_stock_gbp_bn.png"), dpi=160)
plt.close()

# ---------
# FIG 2: Turnover
# ---------
plt.figure(figsize=(10, 4.5))
plt.plot(df["period"], df["turnover_pct_q"], linewidth=2)
plt.axvline(START_PERIOD, color="black", linestyle="--", linewidth=1)
plt.axvline(END_PERIOD, color="black", linestyle="--", linewidth=1)
plt.title(f"Market depth (turnover, % per quarter) â€” {GEO}")
plt.ylabel("% of stock per quarter")
plt.xticks(df["period"][::8], rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(OUT_FIG, "fig_domain_turnover_pct_q.png"), dpi=160)
plt.close()

print("END_PERIOD:", END_PERIOD)
print("Wrote:", domain_csv_path)
