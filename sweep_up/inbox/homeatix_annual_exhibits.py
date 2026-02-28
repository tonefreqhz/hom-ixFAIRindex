import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

CSV_PATH = "Homeatix housing market model(Sheet1) (4).csv"

# -----------------------
# Load + clean
# -----------------------
df = pd.read_csv(CSV_PATH, encoding="cp1252")

df = df.replace(["nul", "NUL", "null", "NULL", ""], np.nan)

# Coerce numeric where possible
for c in df.columns:
    if c not in ["Month"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

annual = df[df["Year"].notna()].copy()
annual["Year"] = annual["Year"].astype(int)
annual = annual.sort_values("Year")

# -----------------------
# Derived annual fields
# -----------------------
annual["total_old_stock"] = annual[["old_stock_england","old_stock_wales"]].sum(axis=1, skipna=True)
annual["total_new_build"] = annual[["new_build_england","new_build_wales"]].sum(axis=1, skipna=True)

# prefer provided total_transactions; else compute
annual["total_transactions_use"] = annual["total_transactions"]
annual.loc[annual["total_transactions_use"].isna(), "total_transactions_use"] = (
    annual["total_old_stock"] + annual["total_new_build"]
)

# cash total: prefer provided total_cash_transactions; else sum components
annual["total_cash_use"] = annual["total_cash_transactions"]
if "cash_transactions_england" in annual.columns and "cash_transactions_wales" in annual.columns:
    annual.loc[annual["total_cash_use"].isna(), "total_cash_use"] = annual[
        ["cash_transactions_england","cash_transactions_wales"]
    ].sum(axis=1, skipna=True)

annual["cash_share"] = annual["total_cash_use"] / annual["total_transactions_use"]

annual["new_build_share"] = annual["total_new_build"] / (annual["total_old_stock"] + annual["total_new_build"])
annual["old_stock_share"] = 1 - annual["new_build_share"]

# Helper for index chart
def to_index(s):
    s = s.astype(float)
    base = s.dropna().iloc[0] if s.dropna().shape[0] else np.nan
    return 100 * s / base

# -----------------------
# Exhibit 1 — Turnover & cash share
# -----------------------
fig, ax1 = plt.subplots(figsize=(11,5))
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
plt.savefig("exhibit_1_turnover_cashshare_annual.png", dpi=200)
plt.close()

# -----------------------
# Exhibit 2a — Transaction levels (old vs new)
# -----------------------
fig, ax = plt.subplots(figsize=(11,5))
ax.plot(annual["Year"], annual["total_old_stock"], label="Old stock transactions", color="slategray", lw=2)
ax.plot(annual["Year"], annual["total_new_build"], label="New build transactions", color="crimson", lw=2)
ax.set_title("Exhibit 2a — Transaction levels: old stock vs new build (annual)")
ax.set_ylabel("Transactions")
ax.grid(True, alpha=0.2)
ax.legend()
plt.tight_layout()
plt.savefig("exhibit_2a_transaction_levels_annual.png", dpi=200)
plt.close()

# -----------------------
# Exhibit 2b — Transaction mix shares
# -----------------------
fig, ax = plt.subplots(figsize=(11,5))
ax.plot(annual["Year"], annual["new_build_share"], label="New build share", color="crimson", lw=2)
ax.plot(annual["Year"], annual["old_stock_share"], label="Old stock share", color="slategray", lw=2)
ax.set_title("Exhibit 2b — Transaction mix: shares (annual)")
ax.set_ylabel("Share of transactions")
ax.set_ylim(0,1)
ax.grid(True, alpha=0.2)
ax.legend()
plt.tight_layout()
plt.savefig("exhibit_2b_transaction_mix_shares_annual.png", dpi=200)
plt.close()

# -----------------------
# Exhibit 3 — Mortgage composition (annual) if present
# -----------------------
mort_cols = ["mb_banks_gbp","mb_building_societies_gbp","mb_specialist_lenders_gbp","mb_others_gbp","mb_total_outstanding_gbp"]
mort_present = all(c in annual.columns and annual[c].notna().any() for c in mort_cols)

if mort_present:
    comp = annual[["Year"] + mort_cols].dropna(subset=["mb_total_outstanding_gbp"]).copy()
    for c in ["mb_banks_gbp","mb_building_societies_gbp","mb_specialist_lenders_gbp","mb_others_gbp"]:
        comp[c+"_share"] = comp[c] / comp["mb_total_outstanding_gbp"]

    fig, ax = plt.subplots(figsize=(11,5))
    ax.stackplot(
        comp["Year"],
        [comp["mb_banks_gbp_share"], comp["mb_building_societies_gbp_share"],
         comp["mb_specialist_lenders_gbp_share"], comp["mb_others_gbp_share"]],
        labels=["Banks","Building societies","Specialist lenders","Others"],
        alpha=0.9
    )
    ax.set_title("Exhibit 3 — Mortgage outstanding composition by lender type (annual, share of total)")
    ax.set_ylabel("Share")
    ax.set_ylim(0,1)
    ax.grid(True, alpha=0.2)
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig("exhibit_3_mortgage_composition_annual.png", dpi=200)
    plt.close()
else:
    print("Exhibit 3 not produced: mortgage outstanding columns not present in annual block. "
          "To do this annually, take December values from the monthly block.")

# -----------------------
# Exhibit 4 — House price vs turnover (indexed)
# -----------------------
fig, ax = plt.subplots(figsize=(11,5))
if "avg_house_price_gbp_england_wales" in annual.columns:
    ax.plot(annual["Year"], to_index(annual["avg_house_price_gbp_england_wales"]),
            label="Avg house price (index, base=100)", color="black", lw=2)
ax.plot(annual["Year"], to_index(annual["stock_turnover_ PCT"]),
        label="Stock turnover (index, base=100)", color="navy", lw=2)

ax.set_title("Exhibit 4 — House price vs turnover (indexed, annual)")
ax.set_ylabel("Index (base year = 100)")
ax.grid(True, alpha=0.2)
ax.legend()
plt.tight_layout()
plt.savefig("exhibit_4_price_vs_turnover_index_annual.png", dpi=200)
plt.close()

# -----------------------
# Summary stats CSV
# -----------------------
summary = {
    "start_year": int(annual["Year"].min()),
    "end_year": int(annual["Year"].max()),
    "mean_turnover_pct": float(annual["stock_turnover_ PCT"].mean(skipna=True)),
    "mean_cash_share": float(annual["cash_share"].mean(skipna=True)),
    "mean_new_build_share": float(annual["new_build_share"].mean(skipna=True)),
    "corr_turnover_cash_share": float(annual[["stock_turnover_ PCT","cash_share"]].corr().iloc[0,1]),
    "corr_turnover_new_build_share": float(annual[["stock_turnover_ PCT","new_build_share"]].corr().iloc[0,1]),
}

pd.DataFrame([summary]).to_csv("exhibits_summary_stats_annual.csv", index=False)

print("Done: wrote annual exhibits PNGs + exhibits_summary_stats_annual.csv")
