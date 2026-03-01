from plot_style import configure_matplotlib
import matplotlib.pyplot as plt

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"


status = configure_matplotlib(tex=True)
print("Matplotlib status:", status)

fig, ax = plt.subplots(figsize=(6, 2))
ax.axis("off")
ax.text(0.02, 0.55, r"Test: $\mathrm{FAIR}_t = \alpha + \beta x_t$", fontsize=16)
(OUTPUTS_DIR / "figures").mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUTS_DIR / "figures" / "tex_smoke_test.png", dpi=200)
print("Wrote tex_smoke_test.png")

