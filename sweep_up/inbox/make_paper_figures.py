from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Optional (for GIF)
try:
    import imageio.v2 as imageio
except Exception:
    imageio = None


# ============================================================
# PATHS / IO
# ============================================================
ROOT = Path(__file__).resolve().parent
stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = ROOT / "outputs" / "figures_runs" / stamp

OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_file(root: Path, filename: str) -> Path:
    """
    Find a file in project root or anywhere below.
    If multiple matches exist, returns the most recently modified.
    """
    p = root / filename
    if p.exists():
        return p

    matches = list(root.rglob(filename))
    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return matches[0]

    csvs = sorted([x.name for x in root.rglob("*.csv")])
    raise FileNotFoundError(
        f"Missing file: {filename}\n"
        f"Searched: {root} (recursively)\n"
        f"CSV files found under project (first 60):\n - "
        + "\n - ".join(csvs[:60])
        + ("\n ... (truncated)" if len(csvs) > 60 else "")
    )


DOMAIN_CSV = find_file(ROOT, "domain_terms_state1_state2.csv")
CRASH_STARTS_CSV = find_file(ROOT, "ew_crash_starts.csv")
LEADTIMES_CSV = find_file(ROOT, "ew_events_lead_times.csv")


# ============================================================
# STYLE
# ============================================================
plt.rcParams.update({
    "figure.figsize": (12, 4.5),
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
})


# ============================================================
# HELPERS
# ============================================================
def _require(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")


def normalize_quarter_labels(s: pd.Series) -> pd.Series:
    """
    Normalize strings into canonical quarter label form 'YYYYQ#'.
    Does NOT validate; caller should validate with regex afterwards.
    """
    return (
        s.astype(str)
         .str.strip()
         .str.replace("\ufeff", "", regex=False)
         .str.upper()
         .str.replace("-", "", regex=False)
         .str.replace(" ", "", regex=False)
    )


def parse_quarter_period(s: pd.Series) -> pd.PeriodIndex:
    """
    Parse canonical labels like '1999Q1' to PeriodIndex(freq='Q').

    IMPORTANT: caller must pre-filter invalid rows; otherwise pandas will throw.
    """
    txt = normalize_quarter_labels(s)
    return pd.PeriodIndex(txt, freq="Q")


def pick_first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = set(df.columns)
    for c in candidates:
        if c in cols:
            return c
    return None


def savefig(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def ensure_numeric(df: pd.DataFrame, cols: list[str]):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")


# ============================================================
# LOAD DATA
# ============================================================
def load_domain() -> pd.DataFrame:
    """
    Loads domain_terms_state1_state2.csv and returns a clean quarterly dataframe with:
      - period: 'YYYYQ#'
      - _p: period[Q]
      - date: Timestamp at quarter start
    Filters out any non-quarter junk rows (e.g., 'Δ (End - Start)').
    """
    _require(DOMAIN_CSV)
    df = pd.read_csv(DOMAIN_CSV)

    if "period" not in df.columns:
        raise ValueError(
            f"{DOMAIN_CSV.name} must have a 'period' column. Found: {list(df.columns)}"
        )

    df = df.copy()

    raw = df["period"]
    cleaned = normalize_quarter_labels(raw)

    mask = cleaned.str.match(r"^\d{4}Q[1-4]$", na=False)

    dropped_vals = df.loc[~mask, "period"].dropna().astype(str).unique().tolist()
    if dropped_vals:
        print("NOTE: Dropping non-quarter rows in domain CSV (examples):", dropped_vals[:12])

    df = df.loc[mask].copy()
    df["period"] = cleaned.loc[mask]

    # Build a period Series and convert to timestamps via .dt
    df["_p"] = parse_quarter_period(df["period"]).astype("period[Q]")
    df["date"] = df["_p"].dt.to_timestamp(how="start")

    num_cols = [c for c in df.columns if c not in {"period", "_p", "date"}]
    ensure_numeric(df, num_cols)

    df = df.sort_values("date").reset_index(drop=True)
    return df



# ============================================================
# FIGURES
# ============================================================
def fig_mortgage_stock(domain: pd.DataFrame):
    col = pick_first_existing(domain, ["mortgage_stock_gbp_bn", "mb_total_gbp_bn", "mortgage_stock_bn"])
    if not col:
        raise ValueError(f"Could not find mortgage stock column. Available: {list(domain.columns)}")

    plt.figure()
    plt.plot(domain["date"], domain[col], lw=2)
    plt.title("Mortgage stock outstanding (£bn) — EW")
    plt.ylabel("£bn")
    plt.xlabel("")

    # Optional markers (matches your draft visuals)
    for q in ["2021Q1", "2025Q3"]:
        try:
            dt = pd.Period(q, freq="Q").to_timestamp(how="start")
            plt.axvline(dt, ls="--", color="k", lw=1)
        except Exception:
            pass

    savefig(OUT_DIR / "fig_domain_mortgage_stock_gbp_bn.png")


def fig_turnover(domain: pd.DataFrame):
    col = pick_first_existing(domain, ["turnover_pct_q", "turnover", "market_depth", "turnover_pct"])
    if not col:
        raise ValueError(f"Could not find turnover column. Available: {list(domain.columns)}")

    plt.figure()
    plt.plot(domain["date"], domain[col], lw=2)
    plt.title("Market depth (turnover, % per quarter) — EW")
    plt.ylabel("% of stock per quarter")
    plt.xlabel("")

    for q in ["2021Q1", "2025Q3"]:
        try:
            dt = pd.Period(q, freq="Q").to_timestamp(how="start")
            plt.axvline(dt, ls="--", color="k", lw=1)
        except Exception:
            pass

    savefig(OUT_DIR / "fig_domain_turnover_pct_q.png")


def fig_fair_level(domain: pd.DataFrame):
    fair_col = pick_first_existing(domain, ["fair", "FAIR", "fair_level"])
    if not fair_col:
        raise ValueError(f"Could not find FAIR column. Available: {list(domain.columns)}")

    plt.figure(figsize=(12, 4.8))
    plt.axhspan(-50, 50, color="#dddddd", alpha=0.35, zorder=0)
    plt.axhspan(50, 500, color="#f4b183", alpha=0.25, zorder=0)
    plt.axhspan(-500, -50, color="#9dc3e6", alpha=0.25, zorder=0)

    plt.plot(domain["date"], domain[fair_col], color="black", lw=2, label="FAIR")
    plt.title("Home@ix FAIR — Level (geo=EW)")
    plt.ylabel("FAIR (index)")
    plt.xlabel("")
    plt.legend(loc="upper left")

    savefig(OUT_DIR / "fig_fair_level.png")


def fig_fair_contrib(domain: pd.DataFrame):
    """
    Expects contribution columns if available.
    """
    fair_col = pick_first_existing(domain, ["fair", "FAIR", "fair_level"])
    wedge = pick_first_existing(domain, ["contrib_wedge", "wedge_contrib", "contribution_wedge"])
    turn = pick_first_existing(domain, ["contrib_turnover", "turnover_contrib", "contribution_turnover"])
    nb = pick_first_existing(domain, ["contrib_newbuild", "newbuild_contrib", "contribution_newbuild"])

    if not (wedge and turn and fair_col):
        raise ValueError(
            "Could not find required contribution columns. Need at least FAIR + wedge + turnover.\n"
            f"Available columns: {list(domain.columns)}"
        )

    x = domain["date"].values

    plt.figure(figsize=(12, 4.8))
    plt.axhline(0, color="k", lw=1, alpha=0.6)

    def fill_contrib(y, color, label):
        y = np.asarray(y, dtype=float)
        plt.fill_between(x, 0, y, where=(y >= 0), color=color, alpha=0.65, label=label)
        plt.fill_between(x, 0, y, where=(y < 0), color=color, alpha=0.65)

    fill_contrib(domain[wedge], "#ff6b6b", "Wedge (price vs mortgage)")
    fill_contrib(domain[turn], "#4d79ff", "Turnover (market depth)")
    if nb:
        fill_contrib(domain[nb], "#4caf50", "New-build share (optional)")

    plt.plot(domain["date"], domain[fair_col], color="black", lw=2, label="FAIR (sum)")

    plt.title("Home@ix FAIR — Component Contributions (geo=EW)")
    plt.ylabel("Contribution to FAIR")
    plt.xlabel("")
    plt.legend(loc="upper left")

    savefig(OUT_DIR / "fig_fair_contrib.png")


def fig_avg_leadtime(leadtimes: pd.DataFrame):
    plt.figure(figsize=(10, 4.6))

    A = pick_first_existing(leadtimes, ["leadQ_sigA_FAIR>20_2Q", "leadQ_sigA", "leadQ_A"])
    B = pick_first_existing(leadtimes, ["leadQ_sigB_dFAIR>5_2Q", "leadQ_sigB", "leadQ_B"])
    C = pick_first_existing(leadtimes, ["leadQ_sigC_FAIR>0_dFAIR>=0", "leadQ_sigC", "leadQ_C"])

    if A and B and C:
        vals = [
            float(pd.to_numeric(leadtimes[A], errors="coerce").mean()),
            float(pd.to_numeric(leadtimes[B], errors="coerce").mean()),
            float(pd.to_numeric(leadtimes[C], errors="coerce").mean()),
        ]
        labels = ["A: FAIR>20 (2Q)", "B: dFAIR>5 (2Q)", "C: FAIR>0 & dFAIR>=0"]
    else:
        num_cols = [c for c in leadtimes.columns if pd.api.types.is_numeric_dtype(leadtimes[c])]
        if not num_cols:
            raise ValueError(
                f"No numeric columns found in {LEADTIMES_CSV.name}. Columns: {list(leadtimes.columns)}"
            )
        labels = num_cols[:3]
        vals = [float(leadtimes[c].mean()) for c in labels]

    plt.bar(range(len(vals)), vals, color=["#ff7f0e", "#2ca02c", "#1f77b4"][:len(vals)])
    plt.xticks(range(len(vals)), labels, rotation=10)
    plt.title("Average warning lead time by signal definition")
    plt.ylabel("Average lead time (quarters)")

    savefig(OUT_DIR / "fig_avg_leadtime_by_signal.png")


def fig_price_and_fair(domain: pd.DataFrame, crash_starts: pd.DataFrame):
    fair_col = pick_first_existing(domain, ["fair", "FAIR", "fair_level"])
    price_col = pick_first_existing(domain, ["avg_house_price_gbp", "house_price_gbp", "price_gbp", "avg_price_gbp"])

    if not fair_col or not price_col:
        raise ValueError(
            "Could not find required columns for price+FAIR plot.\n"
            "Need FAIR and house price.\n"
            f"Available columns: {list(domain.columns)}"
        )

    fig, ax1 = plt.subplots(figsize=(12, 4.8))
    ax2 = ax1.twinx()

    ax1.plot(domain["date"], domain[price_col], color="#1f77b4", lw=2, label="House price (GBP)")
    ax2.plot(domain["date"], domain[fair_col], color="black", lw=2, label="FAIR")

    for dt in crash_starts["crash_start"]:
        ax1.axvline(dt, color="red", alpha=0.25, lw=1)

    ax1.set_title("England & Wales: house prices and FAIR (crash starts marked)")
    ax1.set_xlabel("Quarter")
    ax1.set_ylabel("House price (GBP)")
    ax2.set_ylabel("FAIR")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    savefig(OUT_DIR / "fig_price_and_fair_with_crash_starts.png")


# ============================================================
# ANIMATED GIF
# ============================================================
def make_fair_gif(domain: pd.DataFrame, out_path: Path, fps: int = 12, tail_quarters: int = 72):
    """
    Animated GIF of FAIR level drawing through time (last N quarters).
    """
    if imageio is None:
        raise RuntimeError("imageio is not installed. Install with: py -m pip install imageio")

    fair_col = pick_first_existing(domain, ["fair", "FAIR", "fair_level"])
    if not fair_col:
        raise ValueError(f"Could not find FAIR column. Available: {list(domain.columns)}")

    d = domain.dropna(subset=[fair_col]).copy()
    if d.empty:
        raise ValueError("No FAIR data available after dropping NaNs.")

    d = d.tail(tail_quarters).reset_index(drop=True)

    frames = []
    tmp_png = OUT_DIR / "_tmp_frame.png"

    y = d[fair_col].values.astype(float)
    ypad = max(50.0, float(np.nanstd(y) * 1.25))
    ymin = float(np.nanmin(y) - ypad)
    ymax = float(np.nanmax(y) + ypad)

    for i in range(2, len(d) + 1):
        plt.figure(figsize=(10, 4.2))
        plt.axhline(0, color="k", lw=1, alpha=0.5)

        plt.plot(d["date"].iloc[:i], d[fair_col].iloc[:i], color="black", lw=2)
        plt.scatter(d["date"].iloc[i - 1], d[fair_col].iloc[i - 1], color="black", s=25)

        plt.ylim(ymin, ymax)
        plt.title("Home@ix FAIR — evolving signal (EW)")
        plt.ylabel("FAIR")
        plt.xlabel("")

        savefig(tmp_png)
        frames.append(imageio.imread(tmp_png))

    imageio.mimsave(out_path, frames, fps=fps)

    try:
        tmp_png.unlink(missing_ok=True)
    except Exception:
        pass


# ============================================================
# MAIN
# ============================================================
def load_crash_starts(*args, **kwargs):
    """
    Return crash start dates as a DataFrame with a 'crash_start' column.
    Accepts:
      - None -> empty DataFrame
      - list/tuple/set of dates/strings
      - DataFrame (must contain 'crash_start')
    """
    import pandas as pd

    x = None
    if args:
        x = args[0]
    if x is None:
        x = kwargs.get("crash_starts", None)

    # If already a DataFrame, validate/normalize
    if isinstance(x, pd.DataFrame):
        if "crash_start" not in x.columns:
            raise ValueError(f"crash_starts DataFrame must have 'crash_start'. Columns: {list(x.columns)}")
        out = x.copy()
        out["crash_start"] = pd.to_datetime(out["crash_start"], errors="coerce")
        return out

    # If it's a list-like, wrap it
    if isinstance(x, (list, tuple, set)):
        out = pd.DataFrame({"crash_start": list(x)})
        out["crash_start"] = pd.to_datetime(out["crash_start"], errors="coerce")
        return out

    # Default: empty but correctly shaped
    return pd.DataFrame({"crash_start": pd.to_datetime([], errors="coerce")})

def load_leadtimes(
    csv_path=r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\draft_paper_assets\ew_events_lead_times.csv"
):
    """
    Load EW event lead times; coerce lead-time columns to numeric.
    """
    import pandas as pd

    p = Path(csv_path)
    if not p.exists():
        return pd.DataFrame()

    df = pd.read_csv(p)

    if "crash_start" in df.columns:
        df["crash_start"] = pd.to_datetime(df["crash_start"], errors="coerce")

    for c in df.columns:
        if c != "crash_start":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def main():
    # Sanity check inputs
    _require(DOMAIN_CSV)
    _require(CRASH_STARTS_CSV)
    _require(LEADTIMES_CSV)

    domain = load_domain()
    crash_starts = load_crash_starts()
    leadtimes = load_leadtimes()

    # Core domain plots
    fig_mortgage_stock(domain)
    fig_turnover(domain)

    # FAIR plots
    fig_fair_level(domain)

    # Contributions plot (optional based on columns)
    try:
        fig_fair_contrib(domain)
    except Exception as e:
        print("\nNOTE: Skipping contributions figure:", e)

    # Lead time + overlay chart
    fig_avg_leadtime(leadtimes)
    fig_price_and_fair(domain, crash_starts)

    # GIF (optional dependency)
    try:
        make_fair_gif(domain, OUT_DIR / "fair_signal.gif", fps=12, tail_quarters=72)
        print(f"\nSaved GIF: {OUT_DIR / 'fair_signal.gif'}")
    except Exception as e:
        print("\nNOTE: Skipping GIF:", e)

    print("\nSaved figures to:", OUT_DIR)
    print("Domain columns available:", list(domain.columns))
    print("Domain date range:", domain["date"].min(), "to", domain["date"].max())


if __name__ == "__main__":
    main()
