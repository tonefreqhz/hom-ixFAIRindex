import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from pathlib import Path


# ============================================================
# CONFIG (change ROOT once)
# ============================================================
ROOT = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix")

INPATH = ROOT / "outputs" / "features_quarterly.csv"
OUTDIR = ROOT / "outputs" / "fair_assets"
OUTDIR.mkdir(parents=True, exist_ok=True)

GEO = "EW"

# FAIR weights (explicit + auditable)
W_WEDGE = 0.55
W_TURN  = -0.35
W_NB    = 0.10  # used only if NB series exists

# Baseline windows (pooled)
BASELINE_WINDOWS = [
    ("2003Q1", "2007Q4"),
    ("2013Q1", "2019Q4"),
]


# ============================================================
# HELPERS
# ============================================================
def yoy_pct(x: pd.Series) -> pd.Series:
    # YoY percent change (as decimal), quarterly series -> shift(4)
    return x.pct_change(4)

def zscore_with_baseline(x: pd.Series, baseline_mask: pd.Series) -> pd.Series:
    base = x.loc[baseline_mask].dropna()
    mu = base.mean()
    sd = base.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(np.nan, index=x.index)
    return (x - mu) / sd

def period_to_qend(period_str: pd.Series) -> pd.Series:
    # '1999Q1' -> quarter-end timestamp
    return pd.PeriodIndex(period_str.astype(str), freq="Q").to_timestamp("Q")

def baseline_mask_from_p(p: pd.Series) -> pd.Series:
    q = pd.to_datetime(p).dt.to_period("Q")
    mask = pd.Series(False, index=q.index)
    for a, b in BASELINE_WINDOWS:
        mask = mask | ((q >= pd.Period(a)) & (q <= pd.Period(b)))
    return mask


def assert_has_ew_quarters(df: pd.DataFrame, year: int = 2024):
    df = df.copy()
    df["geo"] = df["geo"].astype(str).str.strip().str.upper()
    df["period"] = df["period"].astype(str).str.strip()

    got = sorted(df.loc[(df["geo"] == "EW") & (df["period"].str.startswith(str(year))), "period"].unique().tolist())
    need = [f"{year}Q1", f"{year}Q2", f"{year}Q3", f"{year}Q4"]
    missing = [q for q in need if q not in got]

    print(f"EW {year} quarters in features_quarterly.csv:", got)
    if missing:
        raise ValueError(
            f"Missing EW quarters upstream in features_quarterly.csv: {missing}\n"
            f"This means the base monthly extraction / quarterly aggregation did not generate those quarters.\n"
            f"Fix build_forward_indicator.py first (monthly coverage + quarterly build)."
        )


# ============================================================
# LOAD
# ============================================================
if not INPATH.exists():
    raise FileNotFoundError(f"Missing input: {INPATH}")

df = pd.read_csv(INPATH)

# Basic schema checks
for col in ["period", "geo"]:
    if col not in df.columns:
        raise KeyError(f"Missing required column '{col}' in {INPATH}. Found: {list(df.columns)}")

# Stage gate: ensure narrative-critical quarters exist
assert_has_ew_quarters(df, year=2024)

# Ensure time index
if "p" not in df.columns:
    df["p"] = period_to_qend(df["period"])
df["p"] = pd.to_datetime(df["p"], errors="coerce")
if df["p"].isna().any():
    bad = df.loc[df["p"].isna(), ["period"]].head(10)
    raise ValueError(f"Could not parse some period->timestamp rows. Examples:\n{bad}")

# Select GEO
df["geo"] = df["geo"].astype(str).str.strip().str.upper()
g = df.loc[df["geo"] == GEO].copy()
g = g.sort_values("p").reset_index(drop=True)

# Required columns from your schema
REQ = ["avg_house_price_gbp", "mb_total_gbp_m", "turnover_pct_q"]
missing_req = [c for c in REQ if c not in g.columns]
if missing_req:
    raise KeyError(f"Missing required columns {missing_req}. Found: {list(g.columns)}")

P  = pd.to_numeric(g["avg_house_price_gbp"], errors="coerce")
MB = pd.to_numeric(g["mb_total_gbp_m"], errors="coerce")
TO = pd.to_numeric(g["turnover_pct_q"], errors="coerce")

HAS_NB = "newbuild_share_of_transactions" in g.columns
if HAS_NB:
    NB = pd.to_numeric(g["newbuild_share_of_transactions"], errors="coerce")
else:
    NB = pd.Series(np.nan, index=g.index)


# ============================================================
# BUILD COMPONENTS
# ============================================================
g["gP_yoy"]  = yoy_pct(P)
g["gMB_yoy"] = yoy_pct(MB)
g["gTO_yoy"] = yoy_pct(TO)

g["W_wedge"] = g["gP_yoy"] - g["gMB_yoy"]
g["dNB_yoy"] = (NB - NB.shift(4)) if HAS_NB else 0.0

base = baseline_mask_from_p(g["p"])
g["zW"]  = zscore_with_baseline(g["W_wedge"], base)
g["zTO"] = zscore_with_baseline(g["gTO_yoy"], base)
g["zNB"] = zscore_with_baseline(g["dNB_yoy"], base) if HAS_NB else 0.0

w_nb = W_NB if HAS_NB else 0.0

g["fair_wedge_contrib"] = 100 * (W_WEDGE * g["zW"])
g["fair_turn_contrib"]  = 100 * (W_TURN  * g["zTO"])
g["fair_nb_contrib"]    = 100 * (w_nb    * g["zNB"]) if HAS_NB else 0.0

g["FAIR"]  = g["fair_wedge_contrib"] + g["fair_turn_contrib"] + g["fair_nb_contrib"]
g["dFAIR"] = g["FAIR"].diff()


# ============================================================
# SAVE AUDIT TABLE
# ============================================================
out_cols = [
    "geo", "period", "p",
    "avg_house_price_gbp", "mb_total_gbp_m", "turnover_pct_q", "newbuild_share_of_transactions",
    "gP_yoy", "gMB_yoy", "gTO_yoy", "W_wedge", "dNB_yoy",
    "zW", "zTO", "zNB",
    "fair_wedge_contrib", "fair_turn_contrib", "fair_nb_contrib",
    "FAIR", "dFAIR",
]
out_cols = [c for c in out_cols if c in g.columns]

audit_path = OUTDIR / "fair_quarterly_audit.csv"
g[out_cols].to_csv(audit_path, index=False)


# ============================================================
# PLOTS
# ============================================================
# Plot 1: FAIR level
fig, ax = plt.subplots(figsize=(11.5, 5.8))
ax.plot(g["p"], g["FAIR"], color="black", linewidth=2.2, label="FAIR")
ax.axhline(0, color="grey", linewidth=1, alpha=0.7)

for y in [50, 20, -20, -50]:
    ax.axhline(y, color="tab:blue", linewidth=1, alpha=0.18)

ax.set_title("Home@ix FAIR (England & Wales): level (baseline excludes 2008–2012 and 2020+)")
ax.set_ylabel("FAIR (z-scored vs pooled baseline; scaled ×100)")
ax.set_xlabel("Quarter")
ax.legend(loc="upper left")
fig.tight_layout()

fig_level_path = OUTDIR / "fig_fair_level.png"
fig.savefig(fig_level_path, dpi=220)
plt.close(fig)

# Plot 2: Contributions
fig, ax = plt.subplots(figsize=(11.5, 5.8))
ax.stackplot(
    g["p"],
    g["fair_wedge_contrib"].fillna(0.0),
    g["fair_turn_contrib"].fillna(0.0),
    g["fair_nb_contrib"].fillna(0.0) if HAS_NB else np.zeros(len(g)),
    labels=["Wedge (price vs mortgage stock)", "Turnover (market depth)", "New-build share (optional)"],
    colors=["#d62728", "#1f77b4", "#2ca02c"],
    alpha=0.65,
)
ax.plot(g["p"], g["FAIR"], color="black", linewidth=2.0, label="FAIR (sum)")
ax.axhline(0, color="grey", linewidth=1, alpha=0.7)
ax.set_title("Home@ix FAIR: component contributions")
ax.set_ylabel("Contribution to FAIR")
ax.set_xlabel("Quarter")
ax.legend(loc="upper left", ncol=2)
fig.tight_layout()

fig_contrib_path = OUTDIR / "fig_fair_contributions.png"
fig.savefig(fig_contrib_path, dpi=220)
plt.close(fig)


# ============================================================
# ANIMATION: “direction of flow” (ΔFAIR)
# ============================================================
anim_df = g.dropna(subset=["FAIR"]).reset_index(drop=True)
WINDOW = 48

fig = plt.figure(figsize=(11.5, 6.4))
gs = fig.add_gridspec(2, 1, height_ratios=[3.3, 1.4])
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[1, 0])

line_fair, = ax1.plot([], [], color="black", linewidth=2.2)
ax1.axhline(0, color="grey", linewidth=1, alpha=0.7)
ax1.axhline(50, color="tab:blue", linewidth=1, alpha=0.15)
ax1.axhline(-50, color="tab:blue", linewidth=1, alpha=0.15)
ax1.set_ylabel("FAIR")

pt = ax1.scatter([], [], s=65, color="tab:red", zorder=5)

bar = ax2.bar([0], [0], color="tab:purple", width=0.6)[0]
ax2.axhline(0, color="grey", linewidth=1, alpha=0.7)
ax2.set_xticks([0])
ax2.set_xticklabels(["Current ΔFAIR"])
ax2.set_ylabel("ΔFAIR")

ymin = float(np.nanmin(anim_df["FAIR"])) * 1.1
ymax = float(np.nanmax(anim_df["FAIR"])) * 1.1
ax1.set_ylim(ymin, ymax)

if anim_df["dFAIR"].notna().any():
    dymin = float(np.nanmin(anim_df["dFAIR"])) * 1.2
    dymax = float(np.nanmax(anim_df["dFAIR"])) * 1.2
else:
    dymin, dymax = -1, 1
ax2.set_ylim(dymin, dymax)

def init():
    if len(anim_df) >= 2:
        ax1.set_xlim(anim_df["p"].iloc[0], anim_df["p"].iloc[1])
    else:
        ax1.set_xlim(anim_df["p"].iloc[0], anim_df["p"].iloc[0] + pd.Timedelta(days=90))

    line_fair.set_data([], [])
    pt.set_offsets(np.empty((0, 2)))
    bar.set_height(0)
    return (line_fair, pt, bar)

def update(i):
    start = max(0, i - WINDOW)
    sub = anim_df.iloc[start:i+1]

    line_fair.set_data(sub["p"], sub["FAIR"])

    x0 = sub["p"].iloc[0]
    x1 = sub["p"].iloc[-1]
    if x0 == x1:
        x1 = x1 + pd.Timedelta(days=90)
    ax1.set_xlim(x0, x1)

    pt.set_offsets(np.array([[sub["p"].iloc[-1], sub["FAIR"].iloc[-1]]], dtype="object"))

    d = anim_df["dFAIR"].iloc[i]
    d = 0.0 if pd.isna(d) else float(d)
    bar.set_height(d)
    bar.set_color("tab:green" if d >= 0 else "tab:orange")

    q = anim_df["p"].iloc[i].to_period("Q")
    fair_now = float(anim_df["FAIR"].iloc[i])
    ax1.set_title(f"Home@ix FAIR (EW) — {q} | FAIR={fair_now:.1f} | ΔFAIR={d:.1f}")

    return (line_fair, pt, bar)

anim = FuncAnimation(fig, update, frames=len(anim_df), init_func=init, interval=120, blit=False)

gif_path = OUTDIR / "anim_fair_direction_of_flow.gif"
anim.save(gif_path, writer=PillowWriter(fps=8))
plt.close(fig)

print(f"\nSaved FAIR outputs to: {OUTDIR}")
print(" - fair_quarterly_audit.csv")
print(" - fig_fair_level.png")
print(" - fig_fair_contributions.png")
print(" - anim_fair_direction_of_flow.gif")
