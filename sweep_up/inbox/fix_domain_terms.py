from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

FQ_PATH = ROOT / "outputs" / "features_quarterly_with_fair.csv"
if not FQ_PATH.exists():
    alt = ROOT / "features_quarterly_with_fair.csv"
    if alt.exists():
        FQ_PATH = alt

HOME_PATH = ROOT / "Homeatix housing market model(Sheet1) (4).csv"

print("Using FQ:", FQ_PATH)
print("Using HOME:", HOME_PATH)

# --- Load quarterly features ---
fq = pd.read_csv(FQ_PATH)

# --- Load Homeatix (handle Windows/Excel encodings + messy rows) ---
# Key improvement: interpret "nul" as NA so cleaning is reliable.
home = pd.read_csv(
    HOME_PATH,
    encoding="cp1252",
    engine="python",
    na_values=["nul", "NUL", "NULL", "null", ""],
    keep_default_na=True,
)

# normalize column names (strip spaces + replace NBSP)
home.columns = (
    home.columns.astype(str)
    .str.replace("\u00A0", " ", regex=False)  # NBSP -> normal space
    .str.strip()
)

# --- geo filter ---
GEO = "ew"  # your file uses "EW"
if "geo" not in fq.columns:
    raise KeyError(f"'geo' not found in FQ. Columns: {fq.columns.tolist()}")

fq["geo_norm"] = (
    fq["geo"].astype(str)
    .str.replace("\u00A0", " ", regex=False)
    .str.strip()
    .str.lower()
)
fq = fq.loc[fq["geo_norm"].eq(GEO)].copy()
print("Rows after geo filter:", len(fq))

# --- mortgages: £m -> £bn ---
if "mb_total_gbp_m" not in fq.columns:
    raise KeyError(f"mb_total_gbp_m not found. Columns: {fq.columns.tolist()}")
fq["mortgage_stock_gbp_bn"] = pd.to_numeric(fq["mb_total_gbp_m"], errors="coerce") / 1000.0

# --- transactions: to k (infer scale) ---
if "tx_total" not in fq.columns:
    raise KeyError("tx_total not found")
fq["tx_total"] = pd.to_numeric(fq["tx_total"], errors="coerce")
tx_med = float(np.nanmedian(fq["tx_total"].values))
fq["transactions_k"] = fq["tx_total"] / 1000.0 if tx_med > 1000 else fq["tx_total"]

# --- dwellings: prefer new name, fall back to legacy; infer millions vs absolute count ---
if "all_dwellings_n" in fq.columns:
    dwell_col = "all_dwellings_n"
elif "all_dwellings_raw" in fq.columns:
    dwell_col = "all_dwellings_raw"
else:
    raise KeyError(
        "No dwellings column found in FQ (expected 'all_dwellings_n' or 'all_dwellings_raw'). "
        f"Columns: {fq.columns.tolist()}"
    )

fq[dwell_col] = pd.to_numeric(fq[dwell_col], errors="coerce")
dw_med = float(np.nanmedian(fq[dwell_col].values))
# Heuristic: if median < 1000, assume already in millions; else assume absolute count
fq["dwellings_m"] = fq[dwell_col] if dw_med < 1000 else fq[dwell_col] / 1_000_000

# --- turnover ---
if "turnover_pct_q" not in fq.columns:
    raise KeyError("turnover_pct_q not found")
fq["turnover_pct_q"] = pd.to_numeric(fq["turnover_pct_q"], errors="coerce")

# --- prices: use Homeatix annual series ---
YEAR_COL = "Year"
PRICE_COL = "avg_house_price_gbp_england_wales"

print("Homeatix columns:", home.columns.tolist())
if YEAR_COL not in home.columns or PRICE_COL not in home.columns:
    raise KeyError(f"Expected '{YEAR_COL}' and '{PRICE_COL}'. Found: {home.columns.tolist()}")

# Keep annual rows only; coerce year/price numeric
home2 = home[[YEAR_COL, PRICE_COL]].copy()
home2[YEAR_COL] = pd.to_numeric(home2[YEAR_COL], errors="coerce")
home2[PRICE_COL] = pd.to_numeric(home2[PRICE_COL], errors="coerce")
home2 = home2.dropna(subset=[YEAR_COL, PRICE_COL]).copy()

home2 = home2.rename(columns={YEAR_COL: "year", PRICE_COL: "avg_house_price_gbp"})
home2["year"] = home2["year"].astype(int)

# --- Resolve duplicates deterministically (instead of raising) ---
# Policy: keep the LAST occurrence for each year in file order.
dup_years = home2.loc[home2.duplicated("year", keep=False), "year"].unique().tolist()
if dup_years:
    print(
        f"WARNING: Homeatix annual price has duplicate years {dup_years}. "
        "Keeping last occurrence per year."
    )
    home2 = home2.groupby("year", as_index=False).tail(1).sort_values("year").reset_index(drop=True)

# --- Validate annual series integrity (catches mislabels fast) ---
if home2.empty:
    raise ValueError(
        "Homeatix annual price series is empty after cleaning. "
        "Check the CSV and the YEAR_COL/PRICE_COL names."
    )

print("Homeatix annual year range:", int(home2["year"].min()), "to", int(home2["year"].max()))

# build year in fq
if "period" not in fq.columns:
    raise KeyError(f"'period' not found in FQ. Columns: {fq.columns.tolist()}")

fq["period"] = fq["period"].astype(str).str.replace("\u00A0", " ", regex=False).str.strip()
fq["year"] = pd.to_numeric(fq["period"].str[:4], errors="coerce").astype("Int64")

# avoid _x/_y suffixes by removing any existing price columns first
price_cols_existing = [c for c in fq.columns if "avg_house_price" in c]
if price_cols_existing:
    print("Dropping existing price cols in fq:", price_cols_existing)
    fq = fq.drop(columns=price_cols_existing)

# --- merge annual price onto quarterly ---
fq = fq.merge(home2, on="year", how="left")

if "avg_house_price_gbp" not in fq.columns:
    raise KeyError(f"'avg_house_price_gbp' missing after merge. Columns: {fq.columns.tolist()}")

# ----------------------------
# QUICK SANITY CHECKS
last_home_year = int(home2["year"].max())
missing_periods = fq.loc[fq["avg_house_price_gbp"].isna(), "period"].tolist()
print("Last Home year:", last_home_year)
print("Missing prices after merge (before any fill), first 30:", missing_periods[:30])
# ----------------------------

# provenance flag: ONLY mark rows we will carry forward (years > last_home_year and missing)
fq["avg_house_price_gbp_is_ffill"] = (
    fq["avg_house_price_gbp"].isna() & (fq["year"] > last_home_year)
).astype(int)

# --- fill missing prices ONLY for future years (e.g., 2025) ---
fq = fq.sort_values(["year", "period"]).copy()

last_year_prices = fq.loc[fq["year"] == last_home_year, "avg_house_price_gbp"].dropna()
if last_year_prices.empty:
    raise ValueError(
        f"No non-missing avg_house_price_gbp found for last_home_year={last_home_year}. "
        "Cannot carry forward into future years."
    )
last_known_price = float(last_year_prices.iloc[-1])

mask_future = fq["year"] > last_home_year
fq.loc[mask_future, "avg_house_price_gbp"] = fq.loc[mask_future, "avg_house_price_gbp"].fillna(last_known_price)

# --- build table ---
STATE1, STATE2 = "2020Q3", "2025Q4"
keep = [
    "period",
    "mortgage_stock_gbp_bn",
    "dwellings_m",
    "transactions_k",
    "turnover_pct_q",
    "avg_house_price_gbp",
    "avg_house_price_gbp_is_ffill",
    "FAIR",
]

missing_keep = [c for c in keep if c not in fq.columns]
if missing_keep:
    raise KeyError(f"Missing required columns for output: {missing_keep}\nFQ columns: {fq.columns.tolist()}")

out = fq.loc[fq["period"].isin([STATE1, STATE2]), keep].copy().sort_values("period")
if len(out) != 2:
    raise ValueError(f"Expected 2 rows for {STATE1},{STATE2}; got {len(out)} rows.\n{out}")

delta = out.iloc[1].copy()
delta["period"] = "Δ (End - Start)"
for c in keep[1:]:
    if c.endswith("_is_ffill"):
        delta[c] = ""
    else:
        delta[c] = out.iloc[1][c] - out.iloc[0][c]

out = pd.concat([out, delta.to_frame().T], ignore_index=True)

OUT_PATH = ROOT / "outputs" / "draft_paper_assets" / "domain_terms_state1_state2.csv"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_PATH, index=False)

print("Wrote:", OUT_PATH)
print(out)
