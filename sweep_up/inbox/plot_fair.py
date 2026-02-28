import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.animation import FuncAnimation
from pathlib import Path

# ---------------- Paths ----------------
IN = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\features_quarterly_with_fair.csv")
OUTDIR = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs\figures")
OUTDIR.mkdir(parents=True, exist_ok=True)

LOGO_PATH = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\width_531.png")
LOGO = mpimg.imread(LOGO_PATH)  # RGBA PNG with transparency is ideal

# ---------------- Helpers ----------------
def add_logo(ax, img=LOGO, zoom=0.14, alpha=0.85, loc="lower right", pad=0.02):
    """
    Adds a logo image as an inset axes in axes-fraction coordinates.

    zoom: size as fraction of axes (roughly square box). Try 0.10–0.18.
    pad: distance from edges in axes fraction.
    loc: 'lower right', 'lower left', 'upper right', 'upper left'
    """
    if loc == "lower right":
        x0, y0 = 1 - pad - zoom, pad
    elif loc == "lower left":
        x0, y0 = pad, pad
    elif loc == "upper right":
        x0, y0 = 1 - pad - zoom, 1 - pad - zoom
    elif loc == "upper left":
        x0, y0 = pad, 1 - pad - zoom
    else:
        raise ValueError("loc must be one of: lower/upper left/right")

    axins = ax.inset_axes([x0, y0, zoom, zoom], transform=ax.transAxes)
    axins.imshow(img, alpha=alpha)
    axins.axis("off")
    return axins

# ---------------- Load data ----------------
df = pd.read_csv(IN)
df["p"] = pd.PeriodIndex(df["period"], freq="Q").to_timestamp("Q")
df = df.sort_values(["geo", "p"])

geo = df["geo"].iloc[0]
g = df[df["geo"] == geo].copy()

# ---- Option A: exclude provisional tail quarters for charts only ----
TAIL_EXCLUDE_Q = 6   # 2=last 2 quarters, 4=1 year, 6=18 months
g["q"] = pd.PeriodIndex(g["period"], freq="Q")
cutoff_q = g["q"].max() - TAIL_EXCLUDE_Q
g_plot = g[g["q"] <= cutoff_q].copy()
g_plot["p"] = g_plot["q"].dt.to_timestamp("Q")

# ---- Figure subtitle (self-contained metadata) ----
BASELINE_TXT = "Baseline z-score windows: 2003Q1–2007Q4, 2013Q1–2019Q4"
WEIGHTS_TXT  = "Weights: 0.55 wedge, −0.35 turnover, 0.10 new-build (optional)"
TAIL_TXT     = f"Charts exclude provisional tail: last {TAIL_EXCLUDE_Q} quarters"
subtitle = f"{BASELINE_TXT} | {WEIGHTS_TXT} | {TAIL_TXT}"

# ---------------- Figure 1: FAIR level ----------------
fig, ax = plt.subplots(figsize=(12, 5))

ax.plot(g_plot["p"], g_plot["FAIR"], lw=2.2, color="black", label="FAIR")

ymin = np.nanmin(g_plot["FAIR"].values)
ymax = np.nanmax(g_plot["FAIR"].values)
pad = 0.15 * (ymax - ymin + 1e-9)
ylow, yhigh = ymin - pad, ymax + pad
ax.set_ylim(ylow, yhigh)

bands = [
    (-50, -20, "#eaf7ff"),
    (-20,  20, "#f5f5f5"),
    ( 20,  50, "#fff1e6"),
]
outer = [
    (ylow, -50, "#d7f0ff"),
    ( 50, yhigh, "#ffe0cc"),
]
for lo, hi, c in outer + bands:
    lo2, hi2 = max(lo, ylow), min(hi, yhigh)
    if lo2 < hi2:
        ax.axhspan(lo2, hi2, color=c, zorder=0)

ax.axhline(0, color="#666", lw=1)
ax.set_title(f"Home@ix FAIR — Level (geo={geo})")
ax.set_ylabel("FAIR (index)")
ax.grid(True, alpha=0.25)
ax.legend(loc="upper left")

ax.text(
    0.01, 0.02, subtitle,
    transform=ax.transAxes,
    fontsize=9, alpha=0.85,
    va="bottom", ha="left"
)

# Add logo (bottom-right)
add_logo(ax, zoom=0.14, alpha=0.85, loc="lower right")

fig.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(OUTDIR / "fig_fair_level.png", dpi=220)
plt.close(fig)

# ---------------- Figure 2: Contributions ----------------
fig, ax = plt.subplots(figsize=(12, 5))
x = g_plot["p"]
c1 = g_plot["fair_wedge_contrib"].fillna(0.0)
c2 = g_plot["fair_turn_contrib"].fillna(0.0)
c3 = g_plot["fair_nb_contrib"].fillna(0.0)

ax.stackplot(
    x, c1, c2, c3,
    labels=["Wedge (price vs mortgage)", "Turnover (market depth)", "New-build share (optional)"],
    colors=["#ff6b6b", "#4dabf7", "#51cf66"],
    alpha=0.75
)
ax.plot(x, g_plot["FAIR"], color="black", lw=2.0, label="FAIR (sum)")
ax.axhline(0, color="#666", lw=1)
ax.set_title(f"Home@ix FAIR — Component Contributions (geo={geo})")
ax.set_ylabel("Contribution to FAIR")
ax.grid(True, alpha=0.25)
ax.legend(loc="upper left")

ax.text(
    0.01, 0.02, subtitle,
    transform=ax.transAxes,
    fontsize=9, alpha=0.85,
    va="bottom", ha="left"
)

# Add logo (bottom-right)
add_logo(ax, zoom=0.14, alpha=0.85, loc="lower right")

fig.tight_layout(rect=[0, 0.06, 1, 1])
fig.savefig(OUTDIR / "fig_fair_contrib.png", dpi=220)
plt.close(fig)

# ---------------- Animation: Direction-of-flow ----------------
g_plot["dFAIR_s"] = g_plot["dFAIR"].fillna(0.0)

# Color by LEVEL (stress), marker by DIRECTION (flow)
dot_colors  = np.where(g_plot["FAIR"].values > 0, "#ff6b6b", "#4dabf7")     # red=stress, blue=easing
dot_markers = np.where(g_plot["dFAIR_s"].values >= 0, "^", "v")            # ▲ worsening, ▼ improving

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(g_plot["p"], g_plot["FAIR"], lw=2.0, color="black")
ax.axhline(0, color="#666", lw=1)
ax.set_title(f"Home@ix FAIR — Level (color) + Flow (marker) (geo={geo})")
ax.set_ylabel("FAIR (index)")
ax.grid(True, alpha=0.25)

# Subtitle inside axes (bottom-left)
meta = ax.text(
    0.01, 0.02, subtitle,
    transform=ax.transAxes,
    fontsize=9, alpha=0.85,
    va="bottom", ha="left"
)

# Info text top-left
txt = ax.text(0.01, 0.95, "", transform=ax.transAxes, va="top", fontsize=11)

# Dot artist
dot, = ax.plot([], [], linestyle="None", marker="o", ms=11)

# Add logo (bottom-right)
logo_artist = add_logo(ax, zoom=0.14, alpha=0.85, loc="lower right")

ax.set_xlim(g_plot["p"].min(), g_plot["p"].max())
ymin = np.nanmin(g_plot["FAIR"].values)
ymax = np.nanmax(g_plot["FAIR"].values)
pad = 0.10 * (ymax - ymin + 1e-9)
ax.set_ylim(ymin - pad, ymax + pad)

def init():
    dot.set_data([], [])
    txt.set_text("")
    return dot, txt, meta, logo_artist

def update(i):
    xi = g_plot["p"].iloc[i]
    yi = g_plot["FAIR"].iloc[i]
    d  = g_plot["dFAIR_s"].iloc[i]

    dot.set_data([xi], [yi])
    dot.set_color(dot_colors[i])
    dot.set_marker(dot_markers[i])

    txt.set_text(f"{g_plot['period'].iloc[i]}  FAIR={yi: .1f}   Δ={d: .1f}")
    return dot, txt, meta, logo_artist

# NOTE: blit=False is more reliable with inset/logo artists
anim = FuncAnimation(fig, update, frames=len(g_plot), init_func=init, interval=90, blit=False)

# Requires: pip install pillow
anim.save(OUTDIR / "anim_fair_flow.gif", dpi=120, writer="pillow")
plt.close(fig)

print("Wrote figures to:", OUTDIR)
print(" - fig_fair_level.png")
print(" - fig_fair_contrib.png")
print(" - anim_fair_flow.gif")
