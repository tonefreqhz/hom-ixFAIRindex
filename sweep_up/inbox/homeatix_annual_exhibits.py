import argparse
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def to_index(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    base = s.dropna().iloc[0] if s.dropna().shape[0] else np.nan
    return 100 * s / base


def parse_args():
    ap = argparse.ArgumentParser(description="Generate Home@ix annual exhibits (PNGs + summary CSV).")
    ap.add_argument(
        "--csv",
        required=True,
        help="Path to Homeatix housing market model CSV (canonical: inputs/canonical/homeatix_model.csv)",
    )
    ap.add_argument(
        "--outdir",
        required=True,
        help="Output directory for figures + exhibits_summary_stats_annual.csv",
    )
    return ap.parse_args()


def month_to_num(x) -> float:
    """Convert Month values like 12, '12', 'Dec', 'December' into 12; unknown -> NaN."""
    if pd.isna(x):
        return np.nan

    # Numeric-ish (12, 12.0, "12")
    try:
        v = float(x)
        if 1 <= v <= 12:
            return int(v)
    except Exception:
        pass

    # String month name
    s = str(x).strip().lower()
    if not s:
        return np.nan

    mapping = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    # Allow "Dec-23" / "Dec 2023" style tokens
    token = s.split()[0].split("-")[0].split("/")[0]
    return mapping.get(token, np.nan)


def main():
    args = parse_args()
    csv_path = Path(args.csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # -----------------------
    # Load + clean
    # -----------------------
    df = pd.read_csv(csv_path, encoding="cp1252")
    df = df.replace(["nul", "NUL", "null", "NULL", ""], np.nan)

    # Coerce numeric where possible (keep Month as-is for parsing)
    for c in df.columns:
        if c not in ["Month"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "Year" not in df.columns:
        raise ValueError("Expected a 'Year' column in the canonical CSV.")

    # Split blocks:
    # - Annual block: Year present AND Month missing
    # - Monthly block: Year present AND Month present
    has_month_col = "Month" in df.columns
    if has_month_col:
        annual = df[df["Year"].notna() & df["Month"].isna()].copy()
        monthly = df[df["Year"].notna() & df["Month"].notna()].copy()
    else:
        # If no Month column exists, treat everything with Year as annual
        annual = df[df["Year"].notna()].copy()
        monthly = df.iloc[0:0].copy()

    annual["Year"] = annual["Year"].astype(int)
    annual = annual.sort_values("Year")

    # Prepare monthly MonthNum if available
    if not monthly.empty and has_month_col:
        monthly["Year"] = monthly["Year"].astype(int)
        monthly["MonthNum"] = monthly["Month"].map(month_to_num)
        monthly = monthly.sort_values(["Year", "MonthNum"])

    # -----------------------
    # Derived annual fields
    # -----------------------
    annual["total_old_stock"] = annual[["old_stock_england", "old_stock_wales"]].sum(axis=1, skipna=True)
    annual["total_new_build"] = annual[["new_build_england", "new_build_wales"]].sum(axis=1, skipna=True)

    # prefer provided total_transactions; else compute
    annual["total_transactions_use"] = annual.get("total_transactions", np.nan)
    annual.loc[annual["total_transactions_use"].isna(), "total_transactions_use"] = (
        annual["total_old_stock"] + annual["total_new_build"]
    )

    # cash total: prefer provided total_cash_transactions; else sum components
    annual["total_cash_use"] = annual.get("total_cash_transactions", np.nan)
    if "cash_transactions_england" in annual.columns and "cash_transactions_wales" in annual.columns:
        annual.loc[annual["total_cash_use"].isna(), "total_cash_use"] = annual[
            ["cash_transactions_england", "cash_transactions_wales"]
        ].sum(axis=1, skipna=True)

    annual["cash_share"] = annual["total_cash_use"] / annual["total_transactions_use"]

    annual["new_build_share"] = annual["total_new_build"] / (annual["total_old_stock"] + annual["total_new_build"])
    annual["old_stock_share"] = 1 - annual["new_build_share"]

    # -----------------------
    # Exhibit 1 — Turnover & cash share
    # -----------------------
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(annual["Year"], annual["stock_turnover_ PCT"], color="navy", lw=2, label="Stock turnover (%)")
    ax1.set_ylabel("Stock turnover (%)", color="navy")
    ax1.tick_params(axis="y", labelcolor="navy")
    ax1.grid(True, alpha=0.2)

    ax2 = ax1.twinx()
    ax2.plot(annual["Year"], annual["cash_share"], color="darkorange", lw=2, label="Cash share")
    ax2.set_ylabel("Cash share", color="darkorange")
    ax2.tick_params(axis="y", labelcolor="darkorange")

    ax1.set_title("Exhibit 1 — Stock turnover (%) and cash share (annual)")
    plt.tight_layout()
    plt.savefig(outdir / "exhibit_1_turnover_cashshare_annual.png", dpi=200)
    plt.close()

    # -----------------------
    # Exhibit 2a — Transaction levels (old vs new)
    # -----------------------
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(annual["Year"], annual["total_old_stock"], label="Old stock transactions", color="slategray", lw=2)
    ax.plot(annual["Year"], annual["total_new_build"], label="New build transactions", color="crimson", lw=2)
    ax.set_title("Exhibit 2a — Transaction levels: old stock vs new build (annual)")
    ax.set_ylabel("Transactions")
    ax.grid(True, alpha=0.2)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outdir / "exhibit_2a_transaction_levels_annual.png", dpi=200)
    plt.close()

    # -----------------------
    # Exhibit 2b — Transaction mix shares
    # -----------------------
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(annual["Year"], annual["new_build_share"], label="New build share", color="crimson", lw=2)
    ax.plot(annual["Year"], annual["old_stock_share"], label="Old stock share", color="slategray", lw=2)
    ax.set_title("Exhibit 2b — Transaction mix: shares (annual)")
    ax.set_ylabel("Share of transactions")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.2)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outdir / "exhibit_2b_transaction_mix_shares_annual.png", dpi=200)
    plt.close()

    # -----------------------
    # Exhibit 3 — Mortgage composition (annual; else Dec from monthly)
    # -----------------------
    mort_cols = [
        "mb_banks_gbp",
        "mb_building_societies_gbp",
        "mb_specialist_lenders_gbp",
        "mb_others_gbp",
        "mb_total_outstanding_gbp",
    ]

    def has_mortgage_cols(d: pd.DataFrame) -> bool:
        return all(c in d.columns and d[c].notna().any() for c in mort_cols)

    comp_source = None

    # Prefer annual block if present
    if has_mortgage_cols(annual):
        comp_source = annual[["Year"] + mort_cols].copy()
    else:
        # Fallback: take December from monthly block
        if not monthly.empty and has_mortgage_cols(monthly) and "MonthNum" in monthly.columns:
            dec = monthly[monthly["MonthNum"] == 12].copy()
            if not dec.empty:
                # If duplicates exist within year, keep last non-null total outstanding
                dec = dec.sort_values(["Year"])
                comp_source = (
                    dec[["Year"] + mort_cols]
                    .dropna(subset=["mb_total_outstanding_gbp"])
                    .drop_duplicates(subset=["Year"], keep="last")
                    .copy()
                )

    if comp_source is not None and not comp_source.empty:
        comp = comp_source.dropna(subset=["mb_total_outstanding_gbp"]).copy()

        for c in ["mb_banks_gbp", "mb_building_societies_gbp", "mb_specialist_lenders_gbp", "mb_others_gbp"]:
            comp[c + "_share"] = comp[c] / comp["mb_total_outstanding_gbp"]

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.stackplot(
            comp["Year"],
            [
                comp["mb_banks_gbp_share"],
                comp["mb_building_societies_gbp_share"],
                comp["mb_specialist_lenders_gbp_share"],
                comp["mb_others_gbp_share"],
            ],
            labels=["Banks", "Building societies", "Specialist lenders", "Others"],
            alpha=0.9,
        )
        ax.set_title("Exhibit 3 — Mortgage outstanding composition by lender type (annual, share of total)")
        ax.set_ylabel("Share")
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.2)
        ax.legend(loc="upper left")
        plt.tight_layout()
        plt.savefig(outdir / "exhibit_3_mortgage_composition_annual.png", dpi=200)
        plt.close()
    else:
        print(
            "Exhibit 3 not produced: mortgage outstanding columns not present in annual block "
            "and could not derive from December values in the monthly block."
        )

    # -----------------------
    # Exhibit 4 — House price vs turnover (indexed)
    # -----------------------
    fig, ax = plt.subplots(figsize=(11, 5))
    if "avg_house_price_gbp_england_wales" in annual.columns:
        ax.plot(
            annual["Year"],
            to_index(annual["avg_house_price_gbp_england_wales"]),
            label="Avg house price (index, base=100)",
            color="black",
            lw=2,
        )

    ax.plot(
        annual["Year"],
        to_index(annual["stock_turnover_ PCT"]),
        label="Stock turnover (index, base=100)",
        color="navy",
        lw=2,
    )

    ax.set_title("Exhibit 4 — House price vs turnover (indexed, annual)")
    ax.set_ylabel("Index (base year = 100)")
    ax.grid(True, alpha=0.2)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outdir / "exhibit_4_price_vs_turnover_index_annual.png", dpi=200)
    plt.close()

    # -----------------------
    # Summary stats CSV
    # -----------------------
    summary = {
        "start_year": int(annual["Year"].min()) if annual["Year"].notna().any() else np.nan,
        "end_year": int(annual["Year"].max()) if annual["Year"].notna().any() else np.nan,
        "mean_turnover_pct": float(annual["stock_turnover_ PCT"].mean(skipna=True)),
        "mean_cash_share": float(annual["cash_share"].mean(skipna=True)),
        "mean_new_build_share": float(annual["new_build_share"].mean(skipna=True)),
        "corr_turnover_cash_share": float(annual[["stock_turnover_ PCT", "cash_share"]].corr().iloc[0, 1]),
        "corr_turnover_new_build_share": float(annual[["stock_turnover_ PCT", "new_build_share"]].corr().iloc[0, 1]),
    }
    pd.DataFrame([summary]).to_csv(outdir / "exhibits_summary_stats_annual.csv", index=False)

    print(f"Done: wrote annual exhibits PNGs + exhibits_summary_stats_annual.csv to: {outdir}")


if __name__ == "__main__":
    main()
