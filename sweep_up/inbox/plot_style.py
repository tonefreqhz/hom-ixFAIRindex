import shutil
import matplotlib as mpl

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUTS_CANON = PROJECT_ROOT / "inputs" / "canonical"
BUILD_DIR = PROJECT_ROOT / "build"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLICATION_DIR = PROJECT_ROOT / "publication"


def configure_matplotlib(tex: bool = True) -> dict:
    """
    Configure Matplotlib to render math consistently.
    Returns a small status dict so logs can say what mode we used.
    """
    has_pdflatex = shutil.which("pdflatex") is not None
    use_tex = bool(tex and has_pdflatex)

    mpl.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "legend.fontsize": 10,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "text.usetex": use_tex,
    })

    if use_tex:
        mpl.rcParams["text.latex.preamble"] = r"\usepackage{lmodern}\usepackage[T1]{fontenc}"

    return {"usetex": use_tex, "has_pdflatex": has_pdflatex}
