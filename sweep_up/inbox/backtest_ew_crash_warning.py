import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"


# ---------------- Paths ----------------
FEATURES_PATH = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\features_quarterly_with_fair.csv")

OUTDIR = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\draft_paper_assets")
OUTDIR.mkdir(parents=True, exist_ok=True)

DATASET_DIR = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\datasets")
DATASET_DIR.mkdir(parents=True, exist_ok=True)

# ---------------- Manual crisis regime definitions (paper-aligned) ----------------
# These are EXOGENOUS regime onset labels (not algorithmic drawdown detection).
# Use quarter-end dates to match your p = PeriodIndex(...).to_timestamp("Q") convention.
MANUAL_CRISIS_STARTS = pd.to_datetime([
    "2007-09-30",  # GFC regime onset (edit if you want a different quarter)
    "2019-09-30",  # repo spike regime onset (edit if you want a different quarter)
])

# Exclude these windows from false-positive scoring (policy distortion / crisis regimes).
# Use inclusive [start, end]. Keep them conservative and defend in the paper.
EXCLUDE_WINDOWS = [
    ("2007-07-01", "2013-12-31"),  # GFC + aftermath (edit)
    ("2019-07-01", "2025-12-31"),  # repo->Covid->Going Direct (edit)
]

# ---------------- Crash detection (legacy; kept for debugging) ----------------
def identify_crash_starts(g, price_col, dd_thresh=0.15, horizon_q=12, cooldown_q=8):
    """
    Legacy crash start detector (price drawdown-based):
    Crash start = local peak where future min within horizon implies drawdown >= dd_thresh.
    cooldown_q prevents counting multiple nearby peaks as separate crash starts.
    """
    g = g.sort_values("p").copy()
    p = pd.to_numeric(g[price_col], errors="coerce").astype(float).values
    t = pd.to_datetime(g["p"]).values

    candidates = []
    for i in range(1, len(p) - 1):
        if np.isnan(p[i - 1]) or np.isnan(p[i]) or np.isnan(p[i + 1]):
            continue

        # local peak (allow plateau on the right)
        if not (p[i] > p[i - 1] and p[i] >= p[i + 1]):
            continue

        j_end = min(i + horizon_q, len(p) - 1)
        future_slice = p[i : j_end + 1]
        if np.all(np.isnan(future_slice)):
            continue

        future_min = np.nanmin(future_slice)
        dd = (p[i] - future_min) / (p[i] + 1e-12)
        if dd >= dd_thresh:
            candidates.append(pd.to_datetime(t[i]))

    candidates = pd.DatetimeIndex(sorted(candidates))
    if len(candidates) == 0:
        return candidates

    kept = [candidates[0]]
    for cs in candidates[1:]:
        if (cs.to_period("Q") - kept[-1].to_period("Q")).n >= cooldown_q:
            kept.append(cs)

    return pd.DatetimeIndex(kept)


def last_signal_before(g, crash_start, signal_mask):
    prior = g.loc[g["p"] < crash_start].loc[signal_mask]
    if prior.empty:
        return pd.NaT
    return prior["p"].iloc[-1]


def backtest_fair_warning(
    g,
    price_col,
    dd_thresh=0.15,
    horizon_q=12,
    follow_window_q=8,
    cooldown_q=8,
    manual_crisis_starts=None,
    exclude_windows=None,
):
    """
    Backtest framed for "crisis regime onset" events.

    - Events (crash_starts) are treated as exogenous, supplied via manual_crisis_starts.
    - Signal lead time is measured as quarters between last signal prior to crisis_start and the crisis_start quarter.
    - False positives are scored ONLY outside exclude_windows to avoid policy-distorted regimes.
    """
    g = g.sort_values("p").copy()

    fair = pd.to_numeric(g["FAIR"], errors="coerce")
    d_fair = pd.to_numeric(g.get("dFAIR", np.nan), errors="coerce")

    if "dFAIR" not in g.columns or d_fair.isna().all():
        d_fair = fair.diff()
    d_fair = d_fair.fillna(0.0)

    # Signals (draft defaults; calibrate as needed)
    sig_A = (fair > 20).rolling(2).mean() == 1.0        # FAIR > 20 for 2Q
    sig_B = (d_fair > 5).rolling(2).mean() == 1.0       # Î”FAIR > 5 for 2Q
    sig_C = (fair > 0) & (d_fair >= 0)                  # stress + worsening

    # --- Crisis regime onsets (manual / paper-aligned) ---
    if manual_crisis_starts is None:
        manual_crisis_starts = MANUAL_CRISIS_STARTS

    crash_starts = pd.DatetimeIndex(pd.to_datetime(manual_crisis_starts)).sort_values()

    # Ensure on-grid (quarter-end) for clean to_period("Q") comparisons
    crash_starts = pd.DatetimeIndex([pd.Timestamp(x).to_period("Q").to_timestamp("Q") for x in crash_starts])

    # --- Build events (one row per crisis_start) ---
    rows = []
    for cs in crash_starts:
        sA = last_signal_before(g, cs, sig_A)
        sB = last_signal_before(g, cs, sig_B)
        sC = last_signal_before(g, cs, sig_C)

        def lead_quarters(sig_date):
            if pd.isna(sig_date):
                return np.nan
            return (cs.to_period("Q") - sig_date.to_period("Q")).n

        rows.append({
            "crisis_start": cs,
            "leadQ_sigA_FAIR>20_2Q": lead_quarters(sA),
            "leadQ_sigB_dFAIR>5_2Q": lead_quarters(sB),
            "leadQ_sigC_FAIR>0_and_dFAIR>=0": lead_quarters(sC),
        })

    events = (
        pd.DataFrame(rows).sort_values("crisis_start")
        if rows
        else pd.DataFrame(
            columns=[
                "crisis_start",
                "leadQ_sigA_FAIR>20_2Q",
                "leadQ_sigB_dFAIR>5_2Q",
                "leadQ_sigC_FAIR>0_and_dFAIR>=0",
            ]
        )
    )

    # --- Exclusion mask for false-positive scoring ---
    if exclude_windows is None:
        exclude_windows = EXCLUDE_WINDOWS

    exclude_mask = pd.Series(False, index=g.index)
    for a, b in exclude_windows:
        a = pd.to_datetime(a)
        b = pd.to_datetime(b)
        exclude_mask |= (pd.to_datetime(g["p"]) >= a) & (pd.to_datetime(g["p"]) <= b)

    eval_mask = ~exclude_mask

    # False positives: for each signal quarter t, check crisis_start in [t, t + follow_window]
    def followed_by_crash(sig_mask: pd.Series) -> pd.Series:
        sig_times = pd.to_datetime(g["p"].where(sig_mask))
        ok = pd.Series(False, index=g.index)
        for idx, t in sig_times.items():
            if pd.isna(t):
                continue
            if bool(exclude_mask.loc[idx]):
                continue  # don't score signals during excluded crisis regimes
            end = t + pd.offsets.QuarterEnd(follow_window_q)
            ok.loc[idx] = ((crash_starts >= t) & (crash_starts <= end)).any()
        return ok

    follow_A = followed_by_crash(sig_A)
    follow_B = followed_by_crash(sig_B)
    follow_C = followed_by_crash(sig_C)

    def false_pos_rate(sig_mask, follow_mask):
        denom = int((sig_mask & eval_mask).sum())
        if denom == 0:
            return np.nan
        num = int(((sig_mask & ~follow_mask) & eval_mask).sum())
        return float(num / denom)

    summary = {
        "n_crisis_starts": int(len(crash_starts)),
        "avg_leadQ_sigA": float(np.nanmean(events["leadQ_sigA_FAIR>20_2Q"])) if len(events) else np.nan,
        "avg_leadQ_sigB": float(np.nanmean(events["leadQ_sigB_dFAIR>5_2Q"])) if len(events) else np.nan,
        "avg_leadQ_sigC": float(np.nanmean(events["leadQ_sigC_FAIR>0_and_dFAIR>=0"])) if len(events) else np.nan,
        "false_pos_rate_sigA_eval_only": false_pos_rate(sig_A, follow_A),
        "false_pos_rate_sigB_eval_only": false_pos_rate(sig_B, follow_B),
        "false_pos_rate_sigC_eval_only": false_pos_rate(sig_C, follow_C),
        "follow_window_q": follow_window_q,
        "exclude_windows": exclude_windows,
        "manual_crisis_starts": [str(pd.Timestamp(x)) for x in crash_starts],
        # legacy params kept for traceability (not used when manual crisis starts are supplied)
        "dd_thresh_legacy": dd_thresh,
        "horizon_q_legacy": horizon_q,
        "cooldown_q_legacy": cooldown_q,
    }

    sig_df = pd.DataFrame({
        "p": g["p"].values,
        "sig_A": sig_A.values.astype(bool),
        "sig_B": sig_B.values.astype(bool),
        "sig_C": sig_C.values.astype(bool),
        "excluded_from_fp_eval": exclude_mask.values.astype(bool),
    })

    return events, summary, crash_starts, sig_df


# ---------------- Plot helpers ----------------
def save_price_fair_plot(g, price_col, crisis_starts, outpath_png):
    df = g.sort_values("p").copy()
    df["price"] = pd.to_numeric(df[price_col], errors="coerce")
    df["FAIR"] = pd.to_numeric(df["FAIR"], errors="coerce")

    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    ax1.plot(df["p"], df["price"], color="black", linewidth=2, label="Avg house price (GBP)")
    ax1.set_ylabel("House price (GBP)")
    ax1.set_xlabel("Quarter")

    ax2 = ax1.twinx()
    ax2.plot(df["p"], df["FAIR"], color="tab:blue", linewidth=1.8, label="FAIR")
    ax2.set_ylabel("FAIR")

    for cs in crisis_starts:
        ax1.axvline(pd.Timestamp(cs), color="tab:red", alpha=0.35, linewidth=1)

    ax1.set_title("England & Wales: house prices and FAIR (crisis regime onsets marked)")
    fig.tight_layout()
    fig.savefig(outpath_png, dpi=200)
    plt.close(fig)


def save_leadtime_bar(events, outpath_png):
    if events.empty:
        return

    means = {
        "A: FAIR>20 (2Q)": np.nanmean(events["leadQ_sigA_FAIR>20_2Q"]),
        "B: dFAIR>5 (2Q)": np.nanmean(events["leadQ_sigB_dFAIR>5_2Q"]),
        "C: FAIR>0 & dFAIR>=0": np.nanmean(events["leadQ_sigC_FAIR>0_and_dFAIR>=0"]),
    }
    labels = list(means.keys())
    vals = [means[k] for k in labels]

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(labels, vals, color=["tab:orange", "tab:green", "tab:blue"])
    ax.set_ylabel("Average lead time (quarters)")
    ax.set_title("Average warning lead time by signal definition (vs crisis regime onsets)")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(outpath_png, dpi=200)
    plt.close(fig)


def build_avg_leadtime_table(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["signal", "avg_lead_time_q", "median_lead_time_q", "n"])

    mapping = [
        ("A: FAIR>20 (2Q)", "leadQ_sigA_FAIR>20_2Q"),
        ("B: dFAIR>5 (2Q)", "leadQ_sigB_dFAIR>5_2Q"),
        ("C: FAIR>0 & dFAIR>=0", "leadQ_sigC_FAIR>0_and_dFAIR>=0"),
    ]

    rows = []
    for label, col in mapping:
        x = pd.to_numeric(events[col], errors="coerce")
        rows.append({
            "signal": label,
            "avg_lead_time_q": float(np.nanmean(x.values)) if x.notna().any() else np.nan,
            "median_lead_time_q": float(np.nanmedian(x.values)) if x.notna().any() else np.nan,
            "n": int(x.notna().sum()),
        })

    return pd.DataFrame(rows)


def debug_peak_future_drawdowns(g, price_col, horizon_q=12):
    """
    Debug helper for legacy price-drawdown crash detection.
    Not used by the manual crisis-onset backtest, but useful for sanity checks.
    """
    g = g.sort_values("p").copy()
    p = pd.to_numeric(g[price_col], errors="coerce").astype(float).values
    t = pd.to_datetime(g["p"]).values

    rows = []
    for i in range(1, len(p) - 1):
        if np.isnan(p[i - 1]) or np.isnan(p[i]) or np.isnan(p[i + 1]):
            continue
        if not (p[i] > p[i - 1] and p[i] >= p[i + 1]):
            continue

        j_end = min(i + horizon_q, len(p) - 1)
        future_slice = p[i : j_end + 1]
        if np.all(np.isnan(future_slice)):
            continue

        future_min = np.nanmin(future_slice)
        dd = (p[i] - future_min) / (p[i] + 1e-12)
        rows.append({"peak_date": pd.to_datetime(t[i]), "peak_price": p[i], "future_min": future_min, "dd": dd})

    out = pd.DataFrame(rows).sort_values("dd", ascending=False)
    return out


def write_method_note(outdir: Path, dataset_dir: Path):
    note = f"""METHOD NOTE (repeatability / reviewer)
====================================

This folder contains outputs produced by backtest_ew_crash_warning.py.

Purpose
-------
The figures/tables are intended to evaluate whether FAIR-based regime signals
provide *advance warning* ahead of exogenously defined "crisis regime onsets".

Key design choice (important)
-----------------------------
'Crisis starts' in this analysis are NOT detected from house price drawdowns.
They are MANUALLY defined, paper-aligned regime onset dates:

  MANUAL_CRISIS_STARTS = {list(map(str, MANUAL_CRISIS_STARTS))}

Rationale: nominal house prices may not exhibit a >=15% drawdown within a short horizon,
while affordability / stress regimes can worsen materially (the focus of this work).

Signals (current draft)
-----------------------
A: FAIR > 20 for 2 consecutive quarters
B: Î”FAIR > 5 for 2 consecutive quarters
C: FAIR > 0 AND Î”FAIR >= 0

Lead time definition
--------------------
For each crisis_start, we compute the last quarter prior to crisis_start where the
signal condition was true, then lead time is:

  lead_time_q = (crisis_start_quarter - signal_quarter) in quarters

False positives (evaluation policy)
-----------------------------------
Signals are scored for false positives only OUTSIDE excluded crisis-policy regimes:

  EXCLUDE_WINDOWS = {EXCLUDE_WINDOWS}

For a signal quarter t (outside excluded windows), it is counted as 'followed by crisis'
if any crisis_start occurs within [t, t + follow_window_q].

Files written (main)
--------------------
Paper assets:
- {outdir / "fig_price_and_fair_with_crash_starts.png"} :
  Price and FAIR series with vertical lines at MANUAL_CRISIS_STARTS.
- {outdir / "fig_avg_leadtime_by_signal.png"} :
  Bar chart of average lead time (quarters) by signal definition.
- {outdir / "ew_events_lead_times.csv"} :
  Row-per-crisis_start lead times for each signal (wide format).
- {outdir / "ew_summary.json"} :
  Summary metrics including false positive rates (eval-only) and configuration.

Datasets (reproducibility):
- {dataset_dir / "leadtime_by_signal_events.csv"} :
  Same as ew_events_lead_times.csv (canonical dataset output).
- {dataset_dir / "avg_leadtime_by_signal.csv"} :
  Aggregate table underlying the bar chart.

How to re-run
-------------
From the script directory:
  py .\\backtest_ew_crash_warning.py

Edits you may make explicitly in the paper
------------------------------------------
- The exact MANUAL_CRISIS_STARTS quarters (and justification)
- The EXCLUDE_WINDOWS ranges (and justification)
- Signal thresholds (A/B/C) and follow_window_q
"""
    (outdir / "README_METHOD_NOTE.txt").write_text(note, encoding="utf-8")


# ---------------- Main ----------------
feat = pd.read_csv(FEATURES_PATH)
feat["p"] = pd.PeriodIndex(feat["period"], freq="Q").to_timestamp("Q")
feat = feat.sort_values(["geo", "p"])

g = feat.loc[feat["geo"] == "EW"].copy()
if g.empty:
    raise ValueError(f"No rows found for geo='EW' in {FEATURES_PATH}")

PRICE_COL = "avg_house_price_gbp"
if PRICE_COL not in g.columns:
    raise KeyError(f"Expected '{PRICE_COL}' in features file. Available: {list(g.columns)}")

g[PRICE_COL] = pd.to_numeric(g[PRICE_COL], errors="coerce")

# Optional debug for legacy drawdown-based crash detection
dbg = debug_peak_future_drawdowns(g, PRICE_COL, horizon_q=12)
print("\n=== Debug (legacy): top future drawdowns from local peaks (12Q horizon) ===")
if dbg.empty:
    print("(no local peaks found under current rule)")
else:
    print(dbg.head(10).to_string(index=False))
    print("Max dd over local peaks:", float(dbg["dd"].max()))

print("\n=== Diagnostics (EW dataset) ===")
print("Rows:", len(g))
print("Quarter range:", g["p"].min(), "->", g["p"].max())
print("Price NA %:", float(pd.to_numeric(g[PRICE_COL], errors="coerce").isna().mean()))
print("FAIR NA %:", float(pd.to_numeric(g["FAIR"], errors="coerce").isna().mean()))

events, summary, crisis_starts, sig_df = backtest_fair_warning(
    g,
    price_col=PRICE_COL,
    dd_thresh=0.15,         # legacy (not used when manual crisis starts provided)
    horizon_q=12,           # legacy (not used when manual crisis starts provided)
    follow_window_q=8,
    cooldown_q=8,           # legacy (not used when manual crisis starts provided)
    manual_crisis_starts=MANUAL_CRISIS_STARTS,
    exclude_windows=EXCLUDE_WINDOWS,
)

print("\n=== Crisis regime onsets (manual) ===")
if len(crisis_starts) == 0:
    print("(none)")
else:
    for cs in crisis_starts:
        print(pd.Timestamp(cs).to_period("Q"))

print("\n=== Lead-time table (quarters before crisis onset; last signal before onset) ===")
print(events.to_string(index=False))

print("\n=== Summary ===")
for k, v in summary.items():
    print(f"{k}: {v}")

# ---------------- Persist derived tables (for paper + reproducibility) ----------------
events_out = DATASET_DIR / "leadtime_by_signal_events.csv"
events.to_csv(events_out, index=False)

avg_tbl = build_avg_leadtime_table(events)
avg_out = DATASET_DIR / "avg_leadtime_by_signal.csv"
avg_tbl.to_csv(avg_out, index=False)

print("\nWrote datasets:")
print(f" - {events_out}")
print(f" - {avg_out}")

# ---------------- Save draft assets ----------------
events.to_csv(OUTDIR / "ew_events_lead_times.csv", index=False)
pd.DataFrame({"crisis_start": crisis_starts}).to_csv(OUTDIR / "ew_crisis_starts.csv", index=False)
pd.Series(summary).to_json(OUTDIR / "ew_summary.json", indent=2, default_handler=str)

save_price_fair_plot(g, PRICE_COL, crisis_starts, OUTDIR / "fig_price_and_fair_with_crisis_starts.png")
save_leadtime_bar(events, OUTDIR / "fig_avg_leadtime_by_signal.png")

write_method_note(OUTDIR, DATASET_DIR)

print(f"\nSaved draft assets to: {OUTDIR}")
print(" - ew_events_lead_times.csv")
print(" - ew_crisis_starts.csv")
print(" - ew_summary.json")
print(" - fig_price_and_fair_with_crisis_starts.png")
print(" - fig_avg_leadtime_by_signal.png")
print(" - README_METHOD_NOTE.txt")
