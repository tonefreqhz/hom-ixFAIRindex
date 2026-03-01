import pandas as pd
from pathlib import Path

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent

WIDE = BASE / "england_wales_sales_volume_breakdown_quarterly.csv"
LAG_QUARTERS = 6  # shaded provisional tail

def load_wide(path: Path) -> pd.DataFrame:
    # Quarter is stored in the first column; make it the index directly.
    df = pd.read_csv(path, header=[0, 1], index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df[~df.index.isna()].sort_index()
    df.index.name = "quarter"
    return df

def get_series(df: pd.DataFrame, metric: str, region: str) -> pd.Series:
    key = (metric, region)
    if key not in df.columns:
        # Helpful debug: show what *is* available
        available_metrics = sorted(set(k[0] for k in df.columns))
        available_regions = sorted(set(k[1] for k in df.columns))
        raise KeyError(
            f"Missing column {key}.\n"
            f"Available metrics include: {available_metrics[:12]}...\n"
            f"Available regions include: {available_regions}"
        )
    return pd.to_numeric(df[key], errors="coerce")

def main():
    wide = load_wide(WIDE)

    cash_share = get_series(wide, "cash_share_pct", "England")
    total_txn  = get_series(wide, "total_transactions", "England")

    data = pd.DataFrame({"cash_share_pct": cash_share, "total_txn": total_txn}).dropna(how="all")

    if data.empty:
        raise RuntimeError("No data after parsing. Check the input CSV contents.")

    # Define lag window start
    if len(data) > LAG_QUARTERS:
        lag_start = data.index[-LAG_QUARTERS]
    else:
        lag_start = data.index.min()

    settled = data.loc[data.index < lag_start, "cash_share_pct"].dropna()

    fig, ax1 = plt.subplots(figsize=(12.5, 6.5), dpi=160)
    ax2 = ax1.twinx()

    # Bars: transaction depth
    ax2.bar(
        data.index,
        data["total_txn"],
        width=70,  # works fine for quarter-end timestamps
        alpha=0.18,
        color="#4C78A8",
        label="Total transactions (cash+mortgage)"
    )

    # Lines: cash share
    ax1.plot(
        data.index,
        data["cash_share_pct"],
        linewidth=2.2,
        color="#F58518",
        label="Cash share (%) â€” all quarters"
    )

    if not settled.empty:
        ax1.plot(
            settled.index,
            settled.values,
            linewidth=2.2,
            linestyle="--",
            color="#E45756",
            label=f"Cash share (%) â€” excluding last {LAG_QUARTERS} quarters"
        )

    # Shade lag window
    ax1.axvspan(lag_start, data.index.max(), color="grey", alpha=0.12, label="Reporting-lag window (provisional tail)")
    ax1.axvline(lag_start, color="grey", linewidth=1.0, alpha=0.7)

    ax1.set_title("England: Cash share vs transaction depth (diagnostic view)")
    ax1.set_ylabel("Cash share (%)")
    ax2.set_ylabel("Total transactions (count)")
    ax1.grid(True, alpha=0.25)

    if data["cash_share_pct"].notna().any():
        ymin = max(0, float(data["cash_share_pct"].min()) - 2)
        ymax = min(100, float(data["cash_share_pct"].max()) + 2)
        ax1.set_ylim(ymin, ymax)

    # Combined legend
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True)

    fig.tight_layout()
    out = BASE / "exhibit_cashshare_diagnostics_england.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)

    print("Saved:", out)

if __name__ == "__main__":
    main()
