import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"


# --- CONFIG: set your file path here ---
CSV_PATH = r"C:\Users\peewe\OneDrive\Desktop\homeix\Homeatix housing market model(Sheet1) (4).csv"


# Define "pre-crisis" as pre-GFC (edit if you prefer a different convention)
PRE_GFC_START = 1998
PRE_GFC_END = 2007

TURN_COL = "stock_turnover_ PCT"

# --- Load ---
df = pd.read_csv(CSV_PATH, encoding="cp1252")

# Clean column names (handles non-breaking spaces and stray whitespace)
df.columns = (
    df.columns.astype(str)
    .str.replace("\u00A0", " ", regex=False)
    .str.strip()
)

# Standardise missing tokens used in the file
df = df.replace(["nul", "NUL", "null", "NULL", ""], np.nan)

# Parse Year and turnover
df["Year"] = pd.to_numeric(df.get("Year"), errors="coerce")

if TURN_COL not in df.columns:
    raise ValueError(f"Missing column '{TURN_COL}'. Found columns: {list(df.columns)}")

df[TURN_COL] = pd.to_numeric(df[TURN_COL], errors="coerce")

# Keep annual rows only: Year present AND Month missing (monthly block has Month filled)
if "Month" in df.columns:
    annual = df[df["Year"].notna() & df["Month"].isna()].copy()
else:
    annual = df[df["Year"].notna()].copy()

annual = annual.dropna(subset=[TURN_COL]).sort_values("Year")

# Optional: enforce expected span
annual = annual[annual["Year"].between(1998, 2023)]

if annual.empty:
    raise ValueError("No annual rows with turnover found after cleaning/filtering.")

# --- Compute peak (pre-GFC window) and latest ---
latest_year = int(annual["Year"].max())
latest_turn = float(annual.loc[annual["Year"] == latest_year, TURN_COL].iloc[0])

pre = annual[annual["Year"].between(PRE_GFC_START, PRE_GFC_END)]
if pre.empty:
    raise ValueError(f"No data found in pre-GFC window {PRE_GFC_START}â€“{PRE_GFC_END}.")

peak_row = pre.loc[pre[TURN_COL].idxmax()]
peak_year = int(peak_row["Year"])
peak_turn = float(peak_row[TURN_COL])

collapse_pct = (peak_turn - latest_turn) / peak_turn * 100

# Print stats for your write-up
print("=== Market Depth (Md) / Stock Turnover (% of stock) ===")
print(f"Preâ€‘GFC peak ({PRE_GFC_START}â€“{PRE_GFC_END}): {peak_turn:.2f}% in {peak_year}")
print(f"Latest year in dataset: {latest_year} = {latest_turn:.2f}%")
print(f"Collapse from preâ€‘GFC peak to {latest_year}: {collapse_pct:.1f}%")

# --- Plot ---
plt.style.use("seaborn-v0_8-whitegrid")
fig, ax = plt.subplots(figsize=(14, 6), dpi=200)

ax.plot(annual["Year"], annual[TURN_COL], color="#123C69", linewidth=3)

# Highlight peak + latest points
ax.scatter([peak_year], [peak_turn], color="#E63946", s=90, zorder=5)
ax.scatter([latest_year], [latest_turn], color="#2A9D8F", s=90, zorder=5)

# Annotate points
ax.annotate(
    f"Preâ€‘GFC peak\n{peak_turn:.2f}% ({peak_year})",
    xy=(peak_year, peak_turn),
    xytext=(peak_year + 1, peak_turn + 0.6),
    arrowprops=dict(arrowstyle="->", color="#E63946", lw=1.5),
    fontsize=11,
    color="#E63946",
    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#E63946", lw=1)
)

ax.annotate(
    f"Latest\n{latest_turn:.2f}% ({latest_year})",
    xy=(latest_year, latest_turn),
    xytext=(latest_year - 7, latest_turn + 0.8),
    arrowprops=dict(arrowstyle="->", color="#2A9D8F", lw=1.5),
    fontsize=11,
    color="#2A9D8F",
    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#2A9D8F", lw=1)
)

# Big banner number
ax.text(
    0.02, 0.92,
    f"Liquidity collapse (vs preâ€‘GFC peak): âˆ’{collapse_pct:.1f}%",
    transform=ax.transAxes,
    fontsize=20,
    fontweight="bold",
    color="#111111",
    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#111111", lw=1.2, alpha=0.96)
)

# Titles + axes
ax.set_title("Market Depth (Md): Stock Turnover (% of Housing Stock), 1998â€“2023", fontsize=16, pad=12)
ax.set_ylabel("Turnover (% of stock)", fontsize=12)
ax.set_xlabel("")

# Nice y-limits for banner aesthetics
ax.set_ylim(
    max(0, float(annual[TURN_COL].min()) - 0.8),
    float(annual[TURN_COL].max()) + 1.2
)

# Footnote/source
fig.text(
    0.01, 0.01,
    f"Source: Home@ix Potton model. Preâ€‘GFC peak defined as {PRE_GFC_START}â€“{PRE_GFC_END}. Latest available year: {latest_year}.",
    ha="left", va="bottom", fontsize=10, color="#333333"
)

plt.tight_layout(rect=[0, 0.03, 1, 1])

# Save outputs
(OUTPUTS_DIR / "figures").mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUTS_DIR / "figures" / "homeix_market_depth_turnover_1998_2023.png", bbox_inches="tight")
plt.savefig("homeix_market_depth_turnover_1998_2023.svg", bbox_inches="tight")

plt.show()

