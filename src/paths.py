from __future__ import annotations

from pathlib import Path
from typing import Union

# -----------------------------------------------------------------------------
# Repo root detection
# -----------------------------------------------------------------------------
# This file lives at: <repo_root>/src/paths.py
# So the repo root is the parent of the src/ directory.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

# Backwards-compatible alias (older scripts may import ROOT)
ROOT: Path = PROJECT_ROOT


def assert_project_root(root: Path) -> None:
    """Fail loudly if the repo root assumption is wrong."""
    expected = ["ANCHOR.md", "publication", "tools"]
    missing = [name for name in expected if not (root / name).exists()]
    if missing:
        raise RuntimeError(
            "PROJECT_ROOT looks wrong.\n"
            f"  PROJECT_ROOT: {root}\n"
            f"  Missing: {', '.join(missing)}\n"
            "If you moved src/paths.py, update the PROJECT_ROOT calculation."
        )


assert_project_root(PROJECT_ROOT)

# -----------------------------------------------------------------------------
# Top-level directories
# -----------------------------------------------------------------------------
INPUTS: Path = PROJECT_ROOT / "inputs"
OUTPUTS: Path = PROJECT_ROOT / "outputs"
BUILD: Path = PROJECT_ROOT / "build"
PUBLICATION: Path = PROJECT_ROOT / "publication"
EPUB_EXTRACT: Path = PROJECT_ROOT / "_epub_extract"

# -----------------------------------------------------------------------------
# Common subdirectories
# -----------------------------------------------------------------------------
INPUTS_CANONICAL: Path = INPUTS / "canonical"
BUILD_PROCESSED: Path = BUILD / "processed"

FAIR_ASSETS: Path = OUTPUTS / "fair_assets"
DRAFT_PAPER_ASSETS: Path = OUTPUTS / "draft_paper_assets"
FIGURES: Path = OUTPUTS / "figures"
TABLES: Path = OUTPUTS / "tables"
REPORTS: Path = OUTPUTS / "reports"

# -----------------------------------------------------------------------------
# Sweep-up / inbox (inputs & working scripts live here)
# -----------------------------------------------------------------------------
SWEEP_UP: Path = PROJECT_ROOT / "sweep_up"
INBOX: Path = SWEEP_UP / "inbox"


def ensure_dirs(*dirs: Union[Path, str]) -> None:
    """Create directories if they don't exist."""
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def debug_print() -> None:
    """Print the key paths (handy sanity check)."""
    items = [
        ("PROJECT_ROOT", PROJECT_ROOT),
        ("INPUTS", INPUTS),
        ("INPUTS_CANONICAL", INPUTS_CANONICAL),
        ("OUTPUTS", OUTPUTS),
        ("BUILD", BUILD),
        ("BUILD_PROCESSED", BUILD_PROCESSED),
        ("PUBLICATION", PUBLICATION),
        ("INBOX", INBOX),
        ("EPUB_EXTRACT", EPUB_EXTRACT),
    ]

    print("PATHS DEBUG")
    for name, p in items:
        print(f"  {name}: {p} (exists: {p.exists()})")


if __name__ == "__main__":
    debug_print()
