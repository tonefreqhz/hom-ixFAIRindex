import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Project root = .../homeix (because this file is .../homeix/sweep_up/inbox/build_forward_indicator.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"

# ============================================================
# CONFIG
# ============================================================

# Canonical input (single source of truth)
INPUT_PATH = INPUTS_CANON / "homeatix_model.csv"

# Stock file: try canonical folder first, then project root, then sweep_up/inbox (backward compat)
_STOCK_NAME = "UK Housing Stock 2023 ons(UK Housing Stock) (1).csv"
_STOCK_CANDIDATES = [
    INPUTS_CANON / _STOCK_NAME,
    PROJECT_ROOT / _STOCK_NAME,
    PROJECT_ROOT / "sweep_up" / "inbox" / _STOCK_NAME,
]
STOCK_PATH = next((p for p in _STOCK_CANDIDATES if p.exists()), _STOCK_CANDIDATES[0])

OUT_DIR = OUTPUTS_DIR
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Forward horizons (quarters)
HORIZONS = [8, 12]

# Lags to build for key predictors (quarters)
LAGS = [1, 2, 4, 8]

# Series bounds (prevents baseline + prevents garbage far-future years)
SERIES_START_DATE = pd.Timestamp("1999-01-01")
SERIES_END_DATE = pd.Timestamp("2035-12-31")

DEBUG = False

# gate behaviour
REQUIRE_COMPLETE_2024 = False  # True = strict (raise). False = warn + continue.

# ============================================================
# HELPERS
# ============================================================
NA_TOKENS = ["nul", "NUL", "NULL", "", " ", "na", "n/a", "  "]


def read_homeatix_csv(path: Path) -> pd.DataFrame:
    # cp1252 handles odd exports; utf-8-sig handles BOM exports
    for enc in ["utf-8-sig", "cp1252", "latin1"]:
        try:
            df = pd.read_csv(
                path,
                encoding=enc,
                na_values=NA_TOKENS,
                keep_default_na=True,
            )
            return df
        except Exception:
            continue
    raise RuntimeError(f"Failed to read {path} with utf-8-sig/cp1252/latin1")


def find_col(df: pd.DataFrame, name: str) -> str:
    # Prefer exact match; otherwise case-insensitive trim match
    if name in df.columns:
        return name
    low = {str(c).strip().lower(): c for c in df.columns}
    key = name.strip().lower()
    if key in low:
        return low[key]
    raise KeyError(f"Column not found: {name}. Available: {list(df.columns)}")


def _normalize_colname(x) -> str:
    return str(x).strip().lower().replace("\ufeff", "")


def load_annual_dwellings_stock(stock_path: Path) -> pd.DataFrame:
    """
    Loads annual dwellings stock and returns columns:
      - year (int)
      - all_dwellings_n (float): number of dwellings (not thousands)
    """
    s = pd.read_csv(stock_path)
    if s.empty:
        raise ValueError(f"Stock file is empty: {stock_path}")

    s = s.copy()
    s.columns = [_normalize_colname(c) for c in s.columns]

    # 1) Find year column
    year_candidates = [c for c in s.columns if c in {"year", "yr"} or "year" in c]
    if not year_candidates:
        raise ValueError(
            "Could not find a 'year' column in stock file. "
            f"Columns found: {list(s.columns)}"
        )
    year_col = year_candidates[0]

    # 2) Find dwellings stock column
    preferred = [
        "all_dwellings_k",
        "all dwellings (thousands)",
        "all dwellings",
        "all_dwellings",
        "total dwellings",
    ]
    stock_col = None

    for p in preferred:
        if p in s.columns:
            stock_col = p
            break

    if stock_col is None:
        keywords = ("dwell", "stock", "total", "all")
        candidates = [c for c in s.columns if c != year_col and any(k in c for k in keywords)]
        if candidates:
            stock_col = candidates[0]

    if stock_col is None:
        raise ValueError(
            "Could not infer the dwellings stock column in stock file. "
            f"Columns found: {list(s.columns)}"
        )

    # Clean and coerce
    s[year_col] = pd.to_numeric(s[year_col], errors="coerce").astype("Int64")
    s[stock_col] = (
        s[stock_col]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
    )
    s[stock_col] = pd.to_numeric(s[stock_col], errors="coerce")

    s = s.dropna(subset=[year_col, stock_col]).copy()
    s[year_col] = s[year_col].astype(int)

    colname = stock_col.lower()
    in_thousands = ("_k" in colname) or ("thousand" in colname) or ("000" in colname)

    if in_thousands:
        s["all_dwellings_n"] = s[stock_col] * 1000.0
    else:
        med = float(s[stock_col].median())
        if med < 1_000_000:
            s["all_dwellings_n"] = s[stock_col] * 1000.0
        else:
            s["all_dwellings_n"] = s[stock_col].astype(float)

    out = (
        s.rename(columns={year_col: "year"})[["year", "all_dwellings_n"]]
        .sort_values("year")
        .reset_index(drop=True)
    )

    if out.empty:
        raise ValueError(f"No usable rows parsed from stock file: {stock_path}")

    return out


def assert_has_ew_2024q1234(quarterly: pd.DataFrame, require_complete: bool = True):
    q = quarterly.copy()
    q["geo"] = q["geo"].astype(str).str.strip().str.upper()
    q["period"] = q["period"].astype(str).str.strip()

    ew2024 = q.loc[
        (q["geo"] == "EW") & (q["period"].str.startswith("2024")),
        ["period", "months_with_tx"],
    ].drop_duplicates().sort_values("period")

    print("EW 2024 quarters in features_quarterly.csv:")
    if ew2024.empty:
        print("  (none)")
    else:
        for _, r in ew2024.iterrows():
            m = int(r["months_with_tx"]) if not pd.isna(r["months_with_tx"]) else r["months_with_tx"]
            print(f"  {r['period']}: months_with_tx={m}")

    need = ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]
    missing = [p for p in need if p not in set(ew2024["period"].tolist())]
    bad = ew2024.loc[ew2024["months_with_tx"].fillna(0).astype(int) < 3, "period"].tolist()

    if missing or bad:
        msg = (
            "EW 2024 coverage check failed.\n"
            f" - missing quarter labels: {missing if missing else 'none'}\n"
            f" - incomplete quarters (months_with_tx < 3): {bad if bad else 'none'}\n"
            "This is driven by missing months in outputs/features_monthly_extracted.csv.\n"
        )
        if require_complete:
            raise ValueError(msg)
        else:
            print("WARNING:", msg)


def build_annual_price_map(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Build year -> avg_house_price map from annual rows.
    """
    df = df_raw.copy()

    year_col = find_col(df, "year")
    price_base = "avg_house_price_gbp_england_wales"
    price_col = price_base if price_base in df.columns else find_col(df, price_base)

    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")

    annual = (
        df.loc[df[year_col].notna(), [year_col, price_col]]
        .dropna(subset=[price_col])
        .drop_duplicates(subset=[year_col], keep="last")
        .rename(columns={year_col: "year", price_col: "avg_house_price_gbp"})
        .copy()
    )

    annual["year"] = annual["year"].astype(int)

    if annual.empty:
        print("WARNING: annual price map is empty (no year rows with avg_house_price).")
    else:
        print(
            f"\nAnnual house price map: {annual['year'].min()}..{annual['year'].max()} "
            f"({len(annual)} years)"
        )

    return annual.sort_values("year").reset_index(drop=True)


# ============================================================
# HOMEATIX MONTHLY EXTRACTION
# ============================================================
def extract_monthly_from_homeatix(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    annual_price = build_annual_price_map(df_raw)

    # Drop any existing 'date' columns to prevent duplicates
    if "date" in df.columns:
        df = df.loc[:, df.columns != "date"].copy()

    month_col = find_col(df, "Month")
    df["_month_raw"] = df[month_col].astype(str)

    df["__date"] = pd.to_datetime(df[month_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["__date"]).copy()

    out_of_range = (df["__date"] < SERIES_START_DATE) | (df["__date"] > SERIES_END_DATE)
    if out_of_range.any():
        print("\nWARNING: Dropping out-of-range Month values (showing up to 30 examples):")
        print(df.loc[out_of_range, ["_month_raw", "__date"]].head(30).to_string(index=False))
        df = df.loc[~out_of_range].copy()

    # Normalize any day in the month to month-start
    df["__date"] = df["__date"].dt.to_period("M").dt.to_timestamp(how="start")

    # If multiple rows collapse into same month after normalization, keep the last one
    df = df.sort_values("__date").groupby("__date", as_index=False).last()

    def _candidates(base: str) -> list[str]:
        """
        Preferred order:
          1) renamed monthly column: base + '_m'
          2) base itself
          3) base.1/base.2/base.3 (legacy duplicate-header disambiguation)
        """
        preferred = [f"{base}_m", base, f"{base}.1", f"{base}.2", f"{base}.3"]
        return [c for c in preferred if c in df.columns]

    def _to_num_clean(x: pd.Series) -> pd.Series:
        # Clean common CSV/Excel artifacts: commas, spaces, NBSP, currency signs
        s = x.astype(str)
        s = (
            s.str.replace("\u00A0", "", regex=False)  # non-breaking space
             .str.replace(",", "", regex=False)       # thousands separators
             .str.replace("Â£", "", regex=False)
             .str.strip()
        )
        # Treat obvious NA-ish strings as missing
        s = s.replace(
            {
                "": np.nan,
                "nan": np.nan,
                "None": np.nan,
                "NUL": np.nan,
                "nul": np.nan,
                "NULL": np.nan,
            }
        )
        return pd.to_numeric(s, errors="coerce")

    def _coalesce_numeric(base: str) -> pd.Series:
        cands = _candidates(base)
        if not cands:
            return pd.Series(np.nan, index=df.index)
        s = _to_num_clean(df[cands[0]])
        for c in cands[1:]:
            s = s.combine_first(_to_num_clean(df[c]))
        return s

    def _coalesce_gbp_to_millions(base: str) -> pd.Series:
        s = _coalesce_numeric(base)
        return s / 1e6

    # Build output explicitly
    out = pd.DataFrame({"date": df["__date"]})

    # Transactions (monthly)
    out["tx_existing_england"] = _coalesce_numeric("old_stock_england")
    out["tx_existing_wales"] = _coalesce_numeric("old_stock_wales")
    out["tx_newbuild_england"] = _coalesce_numeric("new_build_england")
    out["tx_newbuild_wales"] = _coalesce_numeric("new_build_wales")

    # Cash (monthly)
    out["cash_transactions_wales"] = _coalesce_numeric("cash_transactions_wales")
    out["cash_transactions_england"] = _coalesce_numeric("cash_transactions_england")

    # Mortgage balances (GBP -> GBP millions)
    out["mb_bs_gbp_m"] = _coalesce_gbp_to_millions("mb_building_societies_gbp")
    out["mb_banks_gbp_m"] = _coalesce_gbp_to_millions("mb_banks_gbp")
    out["mb_bs_plus_banks_gbp_m"] = _coalesce_gbp_to_millions("mb_bs_plus_banks_gbp")
    out["mb_specialist_gbp_m"] = _coalesce_gbp_to_millions("mb_specialist_lenders_gbp")
    out["mb_other_gbp_m"] = _coalesce_gbp_to_millions("mb_others_gbp")
    out["mb_total_reported_gbp_m"] = _coalesce_gbp_to_millions("mb_total_outstanding_gbp")

    # --- Canonical mortgage splicing (single source of truth for modelling) ---
    out["_mb_banks_plus_bs"] = out["mb_banks_gbp_m"] + out["mb_bs_gbp_m"]
    out["mb_bs_plus_banks_spliced_gbp_m"] = out["mb_bs_plus_banks_gbp_m"].combine_first(out["_mb_banks_plus_bs"])
    out["mb_total_gbp_m"] = out["mb_bs_plus_banks_spliced_gbp_m"].combine_first(out["mb_total_reported_gbp_m"])

    out["mb_regime_is_combined"] = out["mb_bs_plus_banks_gbp_m"].notna().astype(int)
    den = out["_mb_banks_plus_bs"].where(out["_mb_banks_plus_bs"] != 0)
    out["banks_share_of_mb"] = out["mb_banks_gbp_m"] / den

    out = out.drop(columns=["_mb_banks_plus_bs"], errors="ignore")

    # Prices + turnover raw (monthly)
    out["avg_house_price_gbp"] = _coalesce_numeric("avg_house_price_gbp_england_wales")
    out["turnover_pct_raw"] = _coalesce_numeric("stock_turnover_ PCT")

    dfm = out.copy()

    # Apply annual house price by year (fills gaps)
    dfm["year"] = dfm["date"].dt.year.astype(int)
    if not annual_price.empty:
        dfm = dfm.merge(annual_price, on="year", how="left", suffixes=("", "_annual"))
        if "avg_house_price_gbp_annual" in dfm.columns:
            dfm["avg_house_price_gbp"] = dfm["avg_house_price_gbp"].combine_first(dfm["avg_house_price_gbp_annual"])
            dfm = dfm.drop(columns=["avg_house_price_gbp_annual"], errors="ignore")
    dfm = dfm.drop(columns=["year"], errors="ignore")

    tx_parts = ["tx_existing_england", "tx_existing_wales", "tx_newbuild_england", "tx_newbuild_wales"]
    for c in tx_parts:
        if c not in dfm.columns:
            dfm[c] = np.nan
    dfm["tx_total"] = dfm[tx_parts].sum(axis=1, min_count=1)

    print("\nMonthly tx_total non-null by year (tail):")
    tmp = dfm.copy()
    tmp["year"] = tmp["date"].dt.year
    print(tmp.groupby("year")["tx_total"].apply(lambda s: int(s.notna().sum())).tail(10).to_string())

    print("\n2024 monthly rows (date + tx columns) [first 15]:")
    print(
        dfm.loc[dfm["date"].dt.year == 2024,
                ["date", "tx_existing_england", "tx_existing_wales", "tx_newbuild_england", "tx_newbuild_wales", "tx_total"]
        ].head(15).to_string(index=False)
    )

    if "avg_house_price_gbp" in dfm.columns:
        miss = dfm["avg_house_price_gbp"].isna().mean()
        print(f"\nMonthly avg_house_price_gbp missingness: {miss:.1%}")

    dfm["geo"] = "EW"
    dfm = dfm.sort_values(["date"]).groupby(["date"], as_index=False).last()
    dfm = dfm.loc[:, ~dfm.columns.duplicated()].copy()
    dfm = dfm.sort_values("date").reset_index(drop=True)

    return dfm


# ============================================================
# QUARTERLY AGGREGATION
# ============================================================
def monthly_to_quarterly(m: pd.DataFrame) -> pd.DataFrame:
    m = m.copy()
    m["date"] = pd.to_datetime(m["date"], errors="coerce")
    m = m.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    full_idx = pd.date_range(m["date"].min(), m["date"].max(), freq="MS")
    m = m.set_index("date").reindex(full_idx).rename_axis("date").reset_index()
    m["geo"] = m["geo"].fillna("EW")

    m["period"] = m["date"].dt.to_period("Q")

    flow_cols = [
        "tx_existing_wales", "tx_existing_england",
        "tx_newbuild_wales", "tx_newbuild_england",
        "tx_total",
    ]
    stock_last_cols = [
        "mb_bs_gbp_m", "mb_banks_gbp_m", "mb_bs_plus_banks_gbp_m",
        "mb_bs_plus_banks_spliced_gbp_m",
        "mb_specialist_gbp_m", "mb_other_gbp_m", "mb_total_gbp_m",
    ]
    level_mean_cols = ["avg_house_price_gbp"]

    for c in flow_cols + stock_last_cols + level_mean_cols:
        if c not in m.columns:
            m[c] = np.nan

    g = m.groupby(["geo", "period"], as_index=False)

    m["_has_tx"] = m["tx_total"].notna()
    months_in_q = g["_has_tx"].sum().rename(columns={"_has_tx": "months_with_tx"})

    q_flows = g[flow_cols].sum(min_count=3)
    q_last = g[stock_last_cols].last()
    q_mean = g[level_mean_cols].mean()

    q = (
        q_flows
        .merge(q_last, on=["geo", "period"], how="outer")
        .merge(q_mean, on=["geo", "period"], how="outer")
        .merge(months_in_q, on=["geo", "period"], how="left")
    )

    q["tx_newbuild_total"] = q["tx_newbuild_wales"] + q["tx_newbuild_england"]
    q["newbuild_share_of_transactions"] = q["tx_newbuild_total"] / q["tx_total"]

    q["period"] = q["period"].astype(str)
    return q.sort_values(["geo", "period"]).reset_index(drop=True)


# ============================================================
# MODEL MATRIX
# ============================================================
def build_model_matrix(q: pd.DataFrame) -> pd.DataFrame:
    df = q.copy()
    df["_period"] = pd.PeriodIndex(df["period"], freq="Q")
    df = df.sort_values(["geo", "_period"]).reset_index(drop=True)

    # Ensure these exist to avoid KeyError if upstream changed
    for c in ["turnover_pct_q", "avg_house_price_gbp", "mb_total_gbp_m", "tx_total", "newbuild_share_of_transactions"]:
        if c not in df.columns:
            df[c] = np.nan

    df["price_yoy"] = df.groupby("geo")["avg_house_price_gbp"].pct_change(4)
    df["mb_yoy"] = df.groupby("geo")["mb_total_gbp_m"].pct_change(4)
    df["tx_yoy"] = df.groupby("geo")["tx_total"].pct_change(4)

    predictors = [
        "turnover_pct_q",
        "newbuild_share_of_transactions",
        "tx_total",
        "avg_house_price_gbp",
        "mb_total_gbp_m",
        "price_yoy",
        "mb_yoy",
        "tx_yoy",
    ]

    for col in predictors:
        for L in LAGS:
            df[f"{col}_lag{L}q"] = df.groupby("geo")[col].shift(L)

    for h in HORIZONS:
        df[f"y_turnover_change_{h}q"] = df.groupby("geo")["turnover_pct_q"].shift(-h) - df["turnover_pct_q"]
        df[f"y_price_change_{h}q"] = df.groupby("geo")["avg_house_price_gbp"].shift(-h) - df["avg_house_price_gbp"]
        df[f"y_price_pct_{h}q"] = df.groupby("geo")["avg_house_price_gbp"].shift(-h) / df["avg_house_price_gbp"] - 1.0
        df[f"y_mb_pct_{h}q"] = df.groupby("geo")["mb_total_gbp_m"].shift(-h) / df["mb_total_gbp_m"] - 1.0

    return df.drop(columns=["_period"])


# ============================================================
# MAIN
# ============================================================
def main():
    if not INPUT_PATH.exists():
        print(f"ERROR: File not found: {INPUT_PATH}")
        sys.exit(1)

    if not STOCK_PATH.exists():
        print(f"ERROR: Stock file not found: {STOCK_PATH}")
        print(f"Searched in:")
        for p in _STOCK_CANDIDATES:
            print(f"  {p}")
        sys.exit(1)

    print(f"Stock file resolved to: {STOCK_PATH}")

    df_raw = read_homeatix_csv(INPUT_PATH)

    monthly = extract_monthly_from_homeatix(df_raw)
    if monthly.empty:
        print("ERROR: No monthly records extracted from Month column.")
        sys.exit(1)

    monthly["ym"] = monthly["date"].dt.to_period("M").astype(str)
    m2024 = sorted(monthly.loc[monthly["date"].dt.year == 2024, "ym"].unique().tolist())
    print("EW months present in 2024 (monthly extraction):", m2024)

    quarterly = monthly_to_quarterly(monthly)

    stock = load_annual_dwellings_stock(STOCK_PATH)

    quarterly = quarterly.copy()
    quarterly["year"] = quarterly["period"].astype(str).str.slice(0, 4).astype(int)
    quarterly = quarterly.merge(stock, on="year", how="left")

    if quarterly["all_dwellings_n"].isna().any():
        missing_years = sorted(quarterly.loc[quarterly["all_dwellings_n"].isna(), "year"].unique().tolist())
        max_stock_year = int(stock["year"].max())
        last_stock_val = float(stock.loc[stock["year"] == max_stock_year, "all_dwellings_n"].iloc[-1])

        too_late = [int(y) for y in missing_years if int(y) > max_stock_year]
        inside_or_early = [int(y) for y in missing_years if int(y) <= max_stock_year]

        if inside_or_early:
            raise ValueError(f"Missing dwelling stock for years <= {max_stock_year}: {inside_or_early}")

        print(
            f"WARNING: Missing dwelling stock for future years {too_late}. "
            f"Carrying forward {max_stock_year} value: {last_stock_val:,.0f}"
        )
        quarterly.loc[quarterly["year"].isin(too_late), "all_dwellings_n"] = last_stock_val

    quarterly["turnover_pct_q"] = quarterly["tx_total"] / quarterly["all_dwellings_n"]
    quarterly = quarterly.drop(columns=["year"])

    assert_has_ew_2024q1234(quarterly, require_complete=REQUIRE_COMPLETE_2024)

    model = build_model_matrix(quarterly)

    monthly_out = OUT_DIR / "features_monthly_extracted.csv"
    quarterly_out = OUT_DIR / "features_quarterly.csv"
    model_out = OUT_DIR / "model_matrix_quarterly.csv"

    monthly.drop(columns=["ym"], errors="ignore").to_csv(monthly_out, index=False)
    quarterly.to_csv(quarterly_out, index=False)
    model.to_csv(model_out, index=False)

    print("\nSaved:")
    print(f" - {monthly_out}")
    print(f" - {quarterly_out}")
    print(f" - {model_out}")

    print("\nExtracted date range:", monthly["date"].min(), "to", monthly["date"].max())
    print("Quarterly rows:", len(quarterly))

    print("\nMissingness (quarterly):")
    for c in ["mb_total_gbp_m", "avg_house_price_gbp", "all_dwellings_n", "turnover_pct_q"]:
        if c in quarterly.columns:
            print(f" - {c}: {quarterly[c].isna().mean():.1%}")


if __name__ == "__main__":
    main()
