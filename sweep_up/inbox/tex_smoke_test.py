from plot_style import configure_matplotlib
import matplotlib.pyplot as plt

status = configure_matplotlib(tex=True)
print("Matplotlib status:", status)

fig, ax = plt.subplots(figsize=(6, 2))
ax.axis("off")
ax.text(0.02, 0.55, r"Test: $\mathrm{FAIR}_t = \alpha + \beta x_t$", fontsize=16)
fig.savefig("tex_smoke_test.png", dpi=200)
print("Wrote tex_smoke_test.png")
