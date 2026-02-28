import matplotlib.pyplot as plt

eq = r"""
$\mathrm{ONS\ affordability:}\quad AR^{ONS}_t=\frac{\mathrm{Median\ house\ price}_t}{\mathrm{Median\ annual\ earnings}_t}$

$\mathrm{Sales\ per\ household:}\quad SPH_t=\frac{\mathrm{Sales\ count}_t}{\mathrm{Number\ of\ households}_t}$

$\mathrm{Sales\ per\ capita:}\quad SPC_t=\frac{\mathrm{Sales\ count}_t}{\mathrm{Population}_t}$

$\mathrm{Baseline\ liquidity:}\quad r_0=\frac{Sales_{base}}{Households_{base}}$

$\mathrm{Counterfactual\ sales:}\quad Sales^{cf}_t=r_0\times Households_t$

$\mathrm{Liquidity\ gap:}\quad Gap_t=Sales^{cf}_t-Sales_t$
""".strip()

fig = plt.figure(figsize=(12, 4.5), dpi=200)
fig.patch.set_facecolor("white")
plt.axis("off")
plt.text(0.02, 0.98, eq, va="top", fontsize=16)
plt.tight_layout()
plt.savefig("homeix_equations.png", bbox_inches="tight")
print("Wrote homeix_equations.png")
