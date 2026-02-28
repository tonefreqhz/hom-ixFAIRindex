import pandas as pd
from pathlib import Path

# Plotting (PNG output)
import matplotlib
matplotlib.use("Agg")  # headless-safe (no GUI needed)
import matplotlib.pyplot as plt


# Use the folder where this script is saved
BASE = Path(__file__).resolve().parent


def read_csv_utf_safe(path: Path) -> pd.DataFrame:
    """
    Read CSV safely when files may be UTF-8 with BOM (common for Excel exports).
    Falls back to cp1252 if needed.
    """
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp1252")


def pick_one(prefix: str) -> Path:
    """
    Auto-find a single file matching a prefix, regardless of date range
    or whether the filename includes ' - Copy'.
    """
    hits = sorted(BASE.glob(f"{prefix}*.csv"))
    if not hits:
        raise FileNotFoundError(f"No file found for prefix '{prefix}' in: {BASE}")
    if len(hits) > 1:
        raise FileNotFoundError(
            f"Multiple files found for prefix '{prefix}' in: {BASE}\n"
            + "\n".join(str(p.name) for p in hits)
        )
    return hits[0]


# Auto-detect your files (works with "... - Copy.csv")
FILES = {
    "cash": pick_one("ukhpi-comparison-cas-vol-england"),
    "existing": pick_one("ukhpi-comparison-exi-vol-england"),
    "mortgage": pick_one("ukhpi-comparison-mor-vol-england"),
    "new_build": pick_one("ukhpi-comparison-new-vol-england"),
}


def load_quarterly(path: Path, value_col: str, out_col: str) -> pd.DataFrame:
    df = read_csv_utf_safe(path)

    required = {"Name", "Pivotable date", value_col}
    missing_cols = required - set(df.columns)
    if missing_cols:
        raise KeyError(f"{path.name} is missing columns: {sorted(missing_cols)}")

    df["date"] = pd.to_datetime(df["Pivotable date"], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    df = df[df["Name"].isin(["England", "Wales"])].copy()

    # quarter end timestamp (e.g., 2023Q4 -> 2023-12-31)
    df["quarter"] = df["date"].dt.to_period("Q").dt.to_timestamp("Q")

    # Take LAST non-null within each quarter (UKHPI quarterly series often repeats on monthly rows)
    df = (
        df.sort_values(["Name", "date"])
        .groupby(["Name", "quarter"], as_index=False)[value_col]
        .apply(lambda s: s.dropna().iloc[-1] if s.notna().any() else pd.NA)
    )

    return df.rename(columns={value_col: out_col})


def compute_cash_share_panel() -> pd.DataFrame:
    new_build = load_quarterly(FILES["new_build"], "Sales volume New build", "new_build")
    existing = load_quarterly(FILES["existing"], "Sales volume Existing properties", "existing")
    cash = load_quarterly(FILES["cash"], "Sales volume Cash purchases", "cash")
    mortgage = load_quarterly(FILES["mortgage"], "Sales volume Mortgage purchases", "mortgage")

    panel = (
        new_build.merge(existing, on=["Name", "quarter"], how="outer")
        .merge(cash, on=["Name", "quarter"], how="outer")
        .merge(mortgage, on=["Name", "quarter"], how="outer")
    )

    panel["total_transactions"] = panel["cash"] + panel["mortgage"]

    # Cash proportion of total (0-1), plus percent
    panel["cash_share"] = (panel["cash"] / panel["total_transactions"]).where(panel["total_transactions"] > 0)
    panel["cash_share_pct"] = 100 * panel["cash_share"]

    # Optional cross-check
    panel["total_stockmix_check"] = panel["new_build"] + panel["existing"]

    return panel


def make_png(cash_prop: pd.DataFrame, out_png: Path) -> None:
    """
    cash_prop: index = quarter, columns = ['England','Wales'], values = cash_share_pct
    """
    fig, ax = plt.subplots(figsize=(12, 6), dpi=160)

    for col in cash_prop.columns:
        ax.plot(cash_prop.index, cash_prop[col], linewidth=2.0, label=col)

    ax.set_title("Cash purchases as a proportion of total transactions (quarterly)")
    ax.set_ylabel("Cash share (%)")
    ax.set_xlabel("Quarter")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")

    # Keep y-limits sensible if data exists
    if cash_prop.notna().any().any():
        ymin = max(0, float(cash_prop.min().min()) - 2)
        ymax = min(100, float(cash_prop.max().max()) + 2)
        ax.set_ylim(ymin, ymax)

    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def describe_series(s: pd.Series) -> dict:
    """
    Return simple stats for a cash_share_pct series.
    """
    s = s.dropna().sort_index()
    if s.empty:
        return {"available": False}

    latest_q = s.index[-1]
    latest = float(s.iloc[-1])

    def get_change(periods: int):
        if len(s) <= periods:
            return None
        return float(s.iloc[-1] - s.iloc[-(periods + 1)])

    # quarterly series: 4 periods ~ 1y, 20 ~ 5y
    chg_1y = get_change(4)
    chg_5y = get_change(20)

    # Averages to give context
    avg_5y = float(s.tail(20).mean()) if len(s) >= 20 else float(s.mean())
    avg_10y = float(s.tail(40).mean()) if len(s) >= 40 else float(s.mean())

    # Peaks/troughs
    peak_q = s.idxmax()
    peak_v = float(s.max())
    trough_q = s.idxmin()
    trough_v = float(s.min())

    return {
        "available": True,
        "latest_q": latest_q,
        "latest": latest,
        "chg_1y": chg_1y,
        "chg_5y": chg_5y,
        "avg_5y": avg_5y,
        "avg_10y": avg_10y,
        "peak_q": peak_q,
        "peak_v": peak_v,
        "trough_q": trough_q,
        "trough_v": trough_v,
        "n": int(len(s)),
    }


def write_interpretation(cash_prop: pd.DataFrame, out_txt: Path) -> None:
    """
    Writes a short narrative based on the observed changes.
    """
    stats_eng = describe_series(cash_prop.get("England"))
    stats_wal = describe_series(cash_prop.get("Wales"))

    def fmt_pct(x):
        return "n/a" if x is None else f"{x:.2f}%"

    def fmt_pp(x):
        # percentage points change
        return "n/a" if x is None else f"{x:+.2f} pp"

    lines = []
    lines.append("Cash purchases as a proportion of total transactions — interpretation")
    lines.append("=" * 72)
    lines.append("")
    lines.append("What this metric is:")
    lines.append("- Cash share (%) = cash purchases / (cash purchases + mortgage purchases), quarterly.")
    lines.append("  Higher values mean a larger fraction of sales are not using a mortgage.")
    lines.append("")

    # Data-driven snapshot
    if stats_eng.get("available") or stats_wal.get("available"):
        lines.append("Latest snapshot (from your files):")
        if stats_eng.get("available"):
            lines.append(
                f"- England latest ({stats_eng['latest_q'].date()}): {stats_eng['latest']:.2f}% "
                f"(1y change {fmt_pp(stats_eng['chg_1y'])}, 5y change {fmt_pp(stats_eng['chg_5y'])})"
            )
            lines.append(
                f"  5y avg: {stats_eng['avg_5y']:.2f}%, 10y avg: {stats_eng['avg_10y']:.2f}%"
            )
            lines.append(
                f"  Peak: {stats_eng['peak_v']:.2f}% ({stats_eng['peak_q'].date()}), "
                f"Trough: {stats_eng['trough_v']:.2f}% ({stats_eng['trough_q'].date()})"
            )
        if stats_wal.get("available"):
            lines.append(
                f"- Wales latest ({stats_wal['latest_q'].date()}): {stats_wal['latest']:.2f}% "
                f"(1y change {fmt_pp(stats_wal['chg_1y'])}, 5y change {fmt_pp(stats_wal['chg_5y'])})"
            )
            lines.append(
                f"  5y avg: {stats_wal['avg_5y']:.2f}%, 10y avg: {stats_wal['avg_10y']:.2f}%"
            )
            lines.append(
                f"  Peak: {stats_wal['peak_v']:.2f}% ({stats_wal['peak_q'].date()}), "
                f"Trough: {stats_wal['trough_v']:.2f}% ({stats_wal['trough_q'].date()})"
            )
        lines.append("")

    # Interpretation, tied to directionality
    def direction(chg):
        if chg is None:
            return None
        if chg > 0.25:
            return "up"
        if chg < -0.25:
            return "down"
        return "flat"

    eng_dir_1y = direction(stats_eng.get("chg_1y")) if stats_eng.get("available") else None
    wal_dir_1y = direction(stats_wal.get("chg_1y")) if stats_wal.get("available") else None

    lines.append("What changes in cash share usually suggest:")
    lines.append("- If cash share rises (up):")
    lines.append("  - Mortgages may be harder/less attractive (higher rates, tighter lending, affordability squeeze).")
    lines.append("  - Cash-rich buyers can dominate: downsizers, investors, corporate/portfolio buyers, or overseas buyers.")
    lines.append("  - In downturns, mortgage-dependent demand often falls faster than cash demand, pushing the share up.")
    lines.append("- If cash share falls (down):")
    lines.append("  - Mortgage credit is more available/cheaper (lower rates, looser lending, improved sentiment).")
    lines.append("  - First-time buyer and mortgaged mover activity is stronger relative to cash buyers.")
    lines.append("")

    # A little more “so what”, using observed direction if present
    lines.append("What your most recent movement implies (based on 1-year change):")
    if stats_eng.get("available"):
        if eng_dir_1y == "up":
            lines.append(f"- England: cash share is rising over 1y ({fmt_pp(stats_eng['chg_1y'])}).")
            lines.append("  That pattern is consistent with mortgage headwinds and/or cash buyers being relatively more active.")
        elif eng_dir_1y == "down":
            lines.append(f"- England: cash share is falling over 1y ({fmt_pp(stats_eng['chg_1y'])}).")
            lines.append("  That leans toward improving mortgage accessibility/costs, or a rebound in mortgaged buyers.")
        else:
            lines.append(f"- England: cash share is broadly flat over 1y ({fmt_pp(stats_eng['chg_1y'])}).")
            lines.append("  That suggests the balance between cash and mortgaged buyers hasn’t shifted much recently.")
    if stats_wal.get("available"):
        if wal_dir_1y == "up":
            lines.append(f"- Wales: cash share is rising over 1y ({fmt_pp(stats_wal['chg_1y'])}).")
            lines.append("  Often seen when mortgage demand is softer than cash demand, or cash-rich segments are more active.")
        elif wal_dir_1y == "down":
            lines.append(f"- Wales: cash share is falling over 1y ({fmt_pp(stats_wal['chg_1y'])}).")
            lines.append("  Often aligns with relatively stronger mortgaged-buyer participation.")
        else:
            lines.append(f"- Wales: cash share is broadly flat over 1y ({fmt_pp(stats_wal['chg_1y'])}).")
            lines.append("  That indicates a stable mix of buyer financing types.")
    lines.append("")

    lines.append("Caveats (worth keeping you honest):")
    lines.append("- This is a *share*: it can rise even if cash purchases are flat, as long as mortgage purchases fall.")
    lines.append("- Cash vs mortgage is only one slice; it doesn’t tell you whether buyers are investors vs owner-occupiers.")
    lines.append("- If totals differ from new+existing counts, treat mix comparisons cautiously (the dataset can have quirks).")
    lines.append("")

    out_txt.write_text("\n".join(lines), encoding="utf-8")


def main():
    print("Using folder:", BASE)
    print("Detected files:")
    for k, p in FILES.items():
        print(f" - {k}: {p.name}")

    panel = compute_cash_share_panel()

    # Wide outputs
    q = (
        panel.pivot(
            index="quarter",
            columns="Name",
            values=[
                "total_transactions",
                "cash",
                "mortgage",
                "cash_share",
                "cash_share_pct",
                "new_build",
                "existing",
                "total_stockmix_check",
            ],
        )
        .sort_index()
    )

    # Standalone cash share (%)
    cash_prop = panel.pivot(index="quarter", columns="Name", values="cash_share_pct").sort_index()

    # Save CSVs (Excel-friendly UTF-8 BOM)
    out_wide = BASE / "england_wales_sales_volume_breakdown_quarterly.csv"
    out_long = BASE / "england_wales_sales_volume_panel_long.csv"
    out_cashshare = BASE / "england_wales_cash_share_quarterly_pct.csv"
    q.to_csv(out_wide, encoding="utf-8-sig")
    panel.sort_values(["quarter", "Name"]).to_csv(out_long, index=False, encoding="utf-8-sig")
    cash_prop.to_csv(out_cashshare, encoding="utf-8-sig")

    # Save PNG
    out_png = BASE / "england_wales_cash_share_quarterly.png"
    make_png(cash_prop, out_png)

    # Write-up
    out_txt = BASE / "cash_purchase_proportion_writeup.txt"
    write_interpretation(cash_prop, out_txt)

    # Console preview
    pd.set_option("display.width", 180)
    pd.set_option("display.max_columns", 60)

    print("\nSaved:")
    print(f" - {out_wide.name}")
    print(f" - {out_long.name}")
    print(f" - {out_cashshare.name}")
    print(f" - {out_png.name}")
    print(f" - {out_txt.name}")

    print("\nLast 8 quarters (cash share %, England/Wales):")
    print(cash_prop.tail(8).round(2))


if __name__ == "__main__":
    main()
