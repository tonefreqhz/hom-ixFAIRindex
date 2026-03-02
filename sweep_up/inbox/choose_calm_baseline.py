import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# PROJECT PATHS (no hard-coded C:\...)
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../homeix

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"

# ============================================================
# PATHS
# ============================================================
# Quarterly features produced by build_forward_indicator.py
IN_Q = OUTPUTS_DIR / "features_quarterly.csv"

# Canonical Homeatix model file (the one you renamed)
MB_M = INPUTS_CANON / "homeatix_model.csv"

OUT = OUTPUTS_DIR / "calm_baseline_candidates_wedge.csv"
OUT_FEAT = OUTPUTS_DIR / "features_quarterly_with_wedge.csv"

# ============================================================
# KNOBS
# ============================================================
MIN_RUN_Q = 8          # minimum run length (quarters)
ROLL_VOL_Q = 8         # rolling volatility window
PCTL = 80              # calm threshold percentile on abs YoY moves (price, turnover)
WEDGE_PCTL = 80        # calm threshold percentile on abs wedge

# Use lowercase here; we normalize mortgage headers to lowercase below.
MB_DATE_COL = "month"                       # monthly date column in mortgage file
MB_LEVEL_COL = "mb_total_outstanding_gbp"   # mortgage stock level column
MB_AGG = "mean"                             # "mean" (quarterly avg) or "eoq" (end-of-quarter)

PRINT_MB_COLS = True                        # print mortgage columns for debugging
PRINT_MB_HEAD = 3                           # rows to print


# ============================================================
# HELPERS
# ============================================================
def read_csv_robust(path: Path):
    """
    Robust CSV reader:
    - tries encodings: utf-8 -> cp1252 -> latin-1
    - tries delimiters: comma or semicolon
    - normalizes NBSP in headers + text cells
    """
    encodings = ["utf-8", "cp1252", "latin-1"]
    seps = [",", ";"]

    last_err = None
    for enc in encodings:
        for sep in seps:
            try:
                df_ = pd.read_csv(path, encoding=enc, sep=sep)

                # normalize column names: remove NBSP, strip, lowercase
                df_.columns = (
                    pd.Index(df_.columns)
                    .map(lambda x: str(x).replace("\u00A0", " ").strip().lower())
                )

                # normalize text cells (object + pandas string dtype)
                for c in df_.select_dtypes(include=["object", "string"]).columns:
                    df_[c] = (
                        df_[c]
                        .astype("string")
                        .str.replace("\u00A0", " ", regex=False)
                        .str.strip()
                    )

                return df_, {"encoding": enc, "sep": sep}
            except Exception as e:
                last_err = e

    raise last_err


def resolve_existing_path(candidates: list[Path], label: str) -> Path:
    """
    Pick the first existing path from candidates, otherwise raise a useful error.
    """
    for p in candidates:
        if p.exists():
            return p

    msg = [f"{label} not found. Looked in:"]
    msg.extend([f" - {str(p)}" for p in candidates])
    raise FileNotFoundError("\n".join(msg))


# ============================================================
# RESOLVE INPUTS (robust)
# ============================================================
IN_Q = resolve_existing_path(
    [
        IN_Q,
        PROJECT_ROOT / "outputs" / "features_quarterly.csv",
    ],
    label="Quarterly features file (features_quarterly.csv)",
)

MB_M = resolve_existing_path(
    [
        MB_M,
        INPUTS_CANON / "homeatix_model.csv",
        PROJECT_ROOT / "inputs" / "canonical" / "homeatix_model.csv",
        # fallback: if someone left it in inbox
        PROJECT_ROOT / "sweep_up" / "inbox" / "homeatix_model.csv",
    ],
    label="Canonical Homeatix model file (homeatix_model.csv)",
)

# ============================================================
# LOAD QUARTERLY FEATURES
# ============================================================
df = pd.read_csv(IN_Q)

# Period handling + sort
df["p"] = pd.PeriodIndex(df["period"], freq="Q")
df = df.sort_values(["geo", "p"]).reset_index(drop=True)

# YoY series
df["gP_yoy"] = df.groupby("geo")["avg_house_price_gbp"].pct_change(4)
df["gTO_yoy"] = df.groupby("geo")["turnover_pct_q"].pct_change(4)

# Volatility proxies (rolling std of YoY)
df["volP_8q"] = (
    df.groupby("geo")["gP_yoy"]
      .rolling(ROLL_VOL_Q, min_periods=ROLL_VOL_Q)
      .std(ddof=0)
      .reset_index(level=0, drop=True)
)
df["volTO_8q"] = (
    df.groupby("geo")["gTO_yoy"]
      .rolling(ROLL_VOL_Q, min_periods=ROLL_VOL_Q)
      .std(ddof=0)
      .reset_index(level=0, drop=True)
)

# ============================================================
# LOAD MORTGAGE MONTHLY, AGGREGATE TO QUARTERLY
# ============================================================
mb, mb_meta = read_csv_robust(MB_M)

print(f"[mortgage] read ok: encoding={mb_meta['encoding']} sep='{mb_meta['sep']}' rows={len(mb)} cols={mb.shape[1]}")
if PRINT_MB_COLS:
    print("[mortgage] columns (copy/paste):")
    print(list(mb.columns))
    print(f"[mortgage] head({PRINT_MB_HEAD}):")
    print(mb.head(PRINT_MB_HEAD).to_string(index=False))

if MB_DATE_COL not in mb.columns:
    raise ValueError(f"'{MB_DATE_COL}' not found in mortgage file columns: {list(mb.columns)}")
if MB_LEVEL_COL not in mb.columns:
    raise ValueError(f"'{MB_LEVEL_COL}' not found in mortgage file columns: {list(mb.columns)}")

mb = mb[[MB_DATE_COL, MB_LEVEL_COL]].copy()

# Treat common null-ish strings as missing (your file uses "nul")
nullish = {"nul": pd.NA, "null": pd.NA, "": pd.NA, "nan": pd.NA, "<na>": pd.NA}
mb[MB_DATE_COL] = mb[MB_DATE_COL].replace(nullish)
mb[MB_LEVEL_COL] = mb[MB_LEVEL_COL].replace(nullish)

# Drop the "year-only" header block rows (no month) before parsing
mb = mb.dropna(subset=[MB_DATE_COL]).copy()

# Parse month dates (your file looks like dd/mm/yyyy)
if pd.api.types.is_numeric_dtype(mb[MB_DATE_COL]):
    mb[MB_DATE_COL] = pd.to_datetime(mb[MB_DATE_COL], unit="D", origin="1899-12-30", errors="coerce")
else:
    mb[MB_DATE_COL] = pd.to_datetime(mb[MB_DATE_COL], errors="coerce", dayfirst=True)

# Coerce mortgage level to numeric, drop missing
mb[MB_LEVEL_COL] = pd.to_numeric(mb[MB_LEVEL_COL], errors="coerce")
mb = mb.dropna(subset=[MB_DATE_COL, MB_LEVEL_COL]).copy()

if len(mb) == 0:
    raise ValueError("After cleaning mortgage data, no valid (month, level) rows remain. Check the source CSV.")

mb = mb.sort_values(MB_DATE_COL)
mb["p"] = pd.PeriodIndex(mb[MB_DATE_COL], freq="Q")

if MB_AGG == "mean":
    mb_q = mb.groupby("p", as_index=False)[MB_LEVEL_COL].mean()
elif MB_AGG == "eoq":
    mb_q = mb.groupby("p", as_index=False)[MB_LEVEL_COL].last()
else:
    raise ValueError("MB_AGG must be 'mean' or 'eoq'")

mb_q = mb_q.sort_values("p")
mb_q["gMB_yoy"] = mb_q[MB_LEVEL_COL].pct_change(4)

# Broadcast mortgage series to geo (works when your features file is a single geo like 'EW')
if df["geo"].nunique() != 1:
    raise ValueError(
        f"features_quarterly has {df['geo'].nunique()} geos, but mortgage file has no geo column. "
        "Either add geo to the mortgage file or filter features to one geo before merging."
    )

geo_only = df["geo"].iloc[0]
mb_q["geo"] = geo_only

# Merge gMB_yoy into features
df = df.merge(mb_q[["geo", "p", "gMB_yoy"]], on=["geo", "p"], how="left")

# ============================================================
# WEDGE + CALM FLAG
# ============================================================
df["W"] = df["gP_yoy"] - df["gMB_yoy"]

df["volW_8q"] = (
    df.groupby("geo")["W"]
      .rolling(ROLL_VOL_Q, min_periods=ROLL_VOL_Q)
      .std(ddof=0)
      .reset_index(level=0, drop=True)
)

# thresholds on valid rows only
valid = df[["gP_yoy", "gTO_yoy", "volP_8q", "volTO_8q", "W"]].dropna()
if len(valid) == 0:
    raise ValueError("No valid rows after computing YoY/volatility/wedge. Check date alignment and merge keys.")

p80_abs_gP = np.percentile(np.abs(valid["gP_yoy"]), PCTL)
p80_abs_gTO = np.percentile(np.abs(valid["gTO_yoy"]), PCTL)
p80_abs_W = np.percentile(np.abs(valid["W"]), WEDGE_PCTL)

med_volP = np.median(valid["volP_8q"])
med_volTO = np.median(valid["volTO_8q"])

# calm flag
df["calm"] = (
    (np.abs(df["gP_yoy"]) <= p80_abs_gP) &
    (np.abs(df["gTO_yoy"]) <= p80_abs_gTO) &
    (df["volP_8q"] <= med_volP) &
    (df["volTO_8q"] <= med_volTO) &
    (np.abs(df["W"]) <= p80_abs_W)
)

# ============================================================
# IDENTIFY CONSECUTIVE CALM RUNS PER GEO
# ============================================================
runs = []
for geo, g in df.groupby("geo", sort=False):
    g = g.sort_values("p").copy()

    # run_id increments when calm changes True<->False
    g["run_id"] = (g["calm"] != g["calm"].shift(1)).cumsum()

    for _, r in g.groupby("run_id"):
        if bool(r["calm"].iloc[0]) and len(r) >= MIN_RUN_Q:
            runs.append({
                "geo": geo,
                "start_period": str(r["p"].iloc[0]),
                "end_period": str(r["p"].iloc[-1]),
                "n_quarters": int(len(r)),
                "mean_abs_gP": float(np.nanmean(np.abs(r["gP_yoy"]))),
                "mean_abs_gTO": float(np.nanmean(np.abs(r["gTO_yoy"]))),
                "mean_abs_W": float(np.nanmean(np.abs(r["W"]))),
                "mean_W": float(np.nanmean(r["W"])),
            })

out = pd.DataFrame(runs)
if len(out) > 0:
    out = out.sort_values(["geo", "n_quarters"], ascending=[True, False])

# ============================================================
# WRITE OUTPUTS
# ============================================================
OUT.parent.mkdir(parents=True, exist_ok=True)

out.to_csv(OUT, index=False)
df.drop(columns=["p"]).to_csv(OUT_FEAT, index=False)

print("\nWrote candidates:", OUT)
print("Wrote features w/ wedge:", OUT_FEAT)

print("\nTop candidates (copy/paste):")
if len(out) == 0:
    print("(none found)")
else:
    print(out.head(15).to_string(index=False))

print("\nThresholds used (copy/paste):")
print(f"  abs(gP_yoy)  <= {p80_abs_gP:.6f}  (P{PCTL})")
print(f"  abs(gTO_yoy) <= {p80_abs_gTO:.6f}  (P{PCTL})")
print(f"  abs(W)       <= {p80_abs_W:.6f}  (P{WEDGE_PCTL})")
print(f"  volP_8q      <= {med_volP:.6f}  (median)")
print(f"  volTO_8q     <= {med_volTO:.6f}  (median)")
