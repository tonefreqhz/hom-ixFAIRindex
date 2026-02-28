from __future__ import annotations
from pathlib import Path

# Repo root = parent of /src
ROOT = Path(__file__).resolve().parents[1]

INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"
BUILD = ROOT / "build"

FAIR_ASSETS = OUTPUTS / "fair_assets"
DRAFT_PAPER_ASSETS = OUTPUTS / "draft_paper_assets"
FIGURES = OUTPUTS / "figures"
TABLES = OUTPUTS / "tables"
REPORTS = OUTPUTS / "reports"

SWEEP_UP = ROOT / "sweep_up"
INBOX = SWEEP_UP / "inbox"
PUBLICATION = INBOX / "publication"

def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
