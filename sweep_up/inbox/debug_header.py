import pandas as pd
from pathlib import Path

xlsx = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\datadownload.xlsx")
sheet = "Median workplace ratio"

prev = pd.read_excel(xlsx, sheet_name=sheet, header=None, nrows=25)
print("=== First 25 rows (raw) ===")
print(prev.to_string(index=False))

for hdr in range(0, 15):
    df = pd.read_excel(xlsx, sheet_name=sheet, header=hdr)
    cols = [str(c) for c in df.columns[:30]]
    yearish = [c for c in cols if any(str(y) in c for y in range(1997, 2026))]
    print(f"\n--- header={hdr} ---")
    print("first cols:", cols[:12])
    print("year-ish cols:", yearish[:12])
