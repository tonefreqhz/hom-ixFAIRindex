# make_ons_fig3_three_panel_median_and_lq.py
# Rebuild ONS Fig 3-style three-panel animated histograms (Median + LQ), 1997–2024.

import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.animation import FuncAnimation, FFMpegWriter


# -----------------------------
# User settings
# -----------------------------
IN_XLSX = r"C:\Users\peewe\OneDrive\Desktop\homeix\datadownload.xlsx"


OUT_MEDIAN = "ons_fig3_three_panel_MEDIAN_1997_2024.mp4"
OUT_LQ = "ons_fig3_three_panel_LQ_1997_2024.mp4"

START_YEAR = 1997
END_YEAR = 2024

FPS = 0.5
BITRATE = 3000
DPI = 160

# Bins per panel (tweak if desired)
BINS_RATIO = 28
BINS_EARN = 28
BINS_HP = 28


# -----------------------------
# Helpers
# -----------------------------
def _norm_colname(x) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def detect_header_row(xlsx_path: str, sheet_name: str, max_scan_rows: int = 30):
    """
    Detect which row contains the header by scoring candidate rows based on:
    - count of non-empty cells
    - presence of common identifiers ("LA code", "LA name", etc.)
    Returns: (header_row_index_0_based, score)
    """
    preview = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=None,
        nrows=max_scan_rows,
        engine="openpyxl",
    )

    best = (0, -1)
    for r in range(len(preview)):
        row = preview.iloc[r].tolist()
        row_norm = [_norm_colname(v) for v in row]

        nonempty = sum(1 for v in row_norm if v != "" and v.lower() != "nan")
        text = " | ".join(row_norm).lower()

        # Heuristics: reward rows that look like headers
        score = nonempty * 100
        if "la code" in text or "lacode" in text:
            score += 5000
        if "la name" in text or "local authority" in text:
            score += 4000
        if any(re.fullmatch(r"\d{4}", v) for v in row_norm):
            score += 3000
        if "region" in text:
            score += 1000

        if score > best[1]:
            best = (r, score)

    return best


def read_sheet_with_detected_header(xlsx_path: str, sheet_name: str):
    header_row, score = detect_header_row(xlsx_path, sheet_name)
    print(f"[header-detect] sheet='{sheet_name}' -> header row = {header_row} (score={score})")

    df = pd.read_excel(
        xlsx_path,
        sheet_name=sheet_name,
        header=header_row,
        engine="openpyxl",
    )

    # Clean column names
    df.columns = [_norm_colname(c) for c in df.columns]
    return df


def extract_year_columns(df: pd.DataFrame):
    """
    Return list of (year:int, column_name) for columns whose header starts with a year,
    e.g. "1997", "1997 Ratio", "1997 £".
    """
    out = []
    for c in df.columns:
        s = _norm_colname(c)
        m = re.match(r"^(\d{4})\b", s)
        if m:
            out.append((int(m.group(1)), c))
    out.sort(key=lambda t: t[0])
    return out



def load_long(df: pd.DataFrame, value_suffix: str, start_year: int, end_year: int):
    """
    Convert a wide LA-by-year sheet to long format with columns: Year, Value, ValueLabel
    """
    year_cols = extract_year_columns(df)
    year_cols = [(y, c) for (y, c) in year_cols if start_year <= y <= end_year]
    if not year_cols:
        raise ValueError("No year columns found in the requested range.")

    values = []
    years = []
    for y, col in year_cols:
        ser = pd.to_numeric(df[col], errors="coerce")
        values.append(ser.to_numpy(dtype=float))
        years.append(y)

    mat = np.vstack(values)  # shape: (n_years, n_rows)
    long = pd.DataFrame(
        {
            "Year": np.repeat(np.array(years, dtype=int), mat.shape[1]),
            "Value": mat.reshape(-1),
        }
    )
    long["ValueLabel"] = value_suffix
    long = long.dropna(subset=["Value"])
    return long


def robust_xlim(vals: np.ndarray, qlo=0.01, qhi=0.99, pad=0.05):
    """
    Robust x-limits based on quantiles (handles outliers).
    """
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return (0.0, 1.0)

    lo = float(np.quantile(vals, qlo))
    hi = float(np.quantile(vals, qhi))
    if lo == hi:
        lo -= 1.0
        hi += 1.0
    span = hi - lo
    return (lo - pad * span, hi + pad * span)


def make_three_panel_mp4(
    xlsx_path: str,
    kind: str,
    spec: dict,
    out_path: str,
    start_year: int,
    end_year: int,
):
    """
    spec keys: ratio, earnings, price
      each: {"sheet": "...", "suffix": "...", "bins": int}
    """
    # Read sheets
    df_ratio = read_sheet_with_detected_header(xlsx_path, spec["ratio"]["sheet"])
    df_earn = read_sheet_with_detected_header(xlsx_path, spec["earnings"]["sheet"])
    df_price = read_sheet_with_detected_header(xlsx_path, spec["price"]["sheet"])

    # Long format
    ratio_long = load_long(df_ratio, spec["ratio"]["suffix"], start_year, end_year)
    earn_long = load_long(df_earn, spec["earnings"]["suffix"], start_year, end_year)
    price_long = load_long(df_price, spec["price"]["suffix"], start_year, end_year)

    years = np.arange(start_year, end_year + 1, dtype=int)

    # Precompute robust x-limits for stability across frames
    ratio_xlim = robust_xlim(ratio_long["Value"].to_numpy(), 0.01, 0.99, 0.08)
    earn_xlim = robust_xlim(earn_long["Value"].to_numpy(), 0.01, 0.99, 0.08)
    price_xlim = robust_xlim(price_long["Value"].to_numpy(), 0.01, 0.99, 0.08)

    # Figure
    fig, axes = plt.subplots(3, 1, figsize=(12, 10.5), dpi=DPI)
    fig.subplots_adjust(top=0.92, bottom=0.08, hspace=0.35)

    fig.patch.set_facecolor("white")
    ax_ratio, ax_earn, ax_price = axes

    # Title and sheet metadata (optional)
    fig.suptitle(
        f"ONS Fig 3 (rebuilt): LA distributions over time — {kind.upper()} series",
        fontsize=16,
        y=0.98,
    )
    fig.text(
        0.01,
        0.955,
        f"Sheets: Ratio='{spec['ratio']['sheet']}', Earnings='{spec['earnings']['sheet']}', Price='{spec['price']['sheet']}'",
        ha="left",
        va="top",
        fontsize=9.5,
        color="#444",
    )

    # YEAR LABEL: axis-level so it cannot be cropped out in MP4
    year_label = ax_ratio.text(
        0.99,
        0.95,
        "",
        transform=ax_ratio.transAxes,
        ha="right",
        va="top",
        fontsize=14,
        color="#222",
        bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=3),
    )

    # Styling helpers
    def setup_axis(ax, title, xlabel, xlim):
        ax.set_title(title, fontsize=12, loc="left")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Count of LAs")
        ax.grid(True, axis="y", alpha=0.25)
        ax.set_xlim(xlim)

    setup_axis(
        ax_ratio,
        f"Workplace affordability ratio ({spec['ratio']['suffix']})",
        "Ratio",
        ratio_xlim,
    )
    setup_axis(
        ax_earn,
        f"Workplace earnings ({spec['earnings']['suffix']})",
        "£",
        earn_xlim,
    )
    setup_axis(
        ax_price,
        f"House price ({spec['price']['suffix']})",
        "£",
        price_xlim,
    )

    # Initial empty artists (we'll redraw hists each frame)
    for ax in axes:
        ax.cla()

    # We rebuild axes each frame but keep consistent limits and style
    def draw_hist(ax, data, bins, xlim, title, xlabel):
        ax.hist(data, bins=bins, color="#2b6cb0", alpha=0.85, edgecolor="white", linewidth=0.6)
        ax.set_xlim(xlim)
        ax.set_title(title, fontsize=12, loc="left")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Count of LAs")
        ax.grid(True, axis="y", alpha=0.25)

    # Frame function
    def frame(i):
        y = int(years[i])

        # Filter each long table for the year
        r = ratio_long.loc[ratio_long["Year"] == y, "Value"].to_numpy()
        e = earn_long.loc[earn_long["Year"] == y, "Value"].to_numpy()
        p = price_long.loc[price_long["Year"] == y, "Value"].to_numpy()

        # Clear axes
        ax_ratio.cla()
        ax_earn.cla()
        ax_price.cla()

        # Draw
        draw_hist(
            ax_ratio,
            r,
            spec["ratio"]["bins"],
            ratio_xlim,
            f"Workplace affordability ratio ({spec['ratio']['suffix']})",
            "Ratio",
        )
        draw_hist(
            ax_earn,
            e,
            spec["earnings"]["bins"],
            earn_xlim,
            f"Workplace earnings ({spec['earnings']['suffix']})",
            "£",
        )
        draw_hist(
            ax_price,
            p,
            spec["price"]["bins"],
            price_xlim,
            f"House price ({spec['price']['suffix']})",
            "£",
        )

        # Re-add the year label inside top axis after cla()
        ax_ratio.text(
            0.99,
            0.95,
            f"Year: {y}",
            transform=ax_ratio.transAxes,
            ha="right",
            va="top",
            fontsize=14,
            color="#222",
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=3),
        )

        return []

    anim = FuncAnimation(fig, frame, frames=len(years), interval=1000 // FPS, blit=False)

    writer = FFMpegWriter(fps=FPS, metadata={"artist": "Home@ix"}, bitrate=BITRATE)
    anim.save(out_path, writer=writer)
    plt.close(fig)


def main():
    xlsx_path = IN_XLSX
    if not os.path.exists(xlsx_path):
        # Try alongside script
        here = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(here, IN_XLSX)
        if os.path.exists(candidate):
            xlsx_path = candidate
        else:
            raise FileNotFoundError(
                f"Workbook not found. Looked for '{IN_XLSX}' in current dir and script dir.\n"
                f"Current dir: {os.getcwd()}"
            )

    median_spec = {
        "ratio": {"sheet": "Median workplace ratio", "suffix": "Median", "bins": BINS_RATIO},
        "earnings": {"sheet": "Median workplace earning (£)", "suffix": "Median (£)", "bins": BINS_EARN},
        "price": {"sheet": "Median house price (£)", "suffix": "HP (£)", "bins": BINS_HP},
    }

    lq_spec = {
        "ratio": {"sheet": "LQ workplace ratio", "suffix": "LQ", "bins": BINS_RATIO},
        "earnings": {"sheet": "LQ workplace earning (£)", "suffix": "LQ (£)", "bins": BINS_EARN},
        "price": {"sheet": "LQ house price (£)", "suffix": "HP (£)", "bins": BINS_HP},
    }

    make_three_panel_mp4(
        xlsx_path=xlsx_path,
        kind="median",
        spec=median_spec,
        out_path=OUT_MEDIAN,
        start_year=START_YEAR,
        end_year=END_YEAR,
    )
    print(f"Saved: {os.path.abspath(OUT_MEDIAN)}")

    make_three_panel_mp4(
        xlsx_path=xlsx_path,
        kind="lq",
        spec=lq_spec,
        out_path=OUT_LQ,
        start_year=START_YEAR,
        end_year=END_YEAR,
    )
    print(f"Saved: {os.path.abspath(OUT_LQ)}")


if __name__ == "__main__":
    main()
