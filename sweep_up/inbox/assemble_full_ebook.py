from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------
# Bootstrap: resolve project root robustly from this file's location
# This file lives at: <project_root>/sweep_up/inbox/assemble_full_ebook.py
# ---------------------------------------------------------------------
INBOX_DIR = Path(__file__).resolve().parent


def find_project_root(start: Path) -> Path:
    """
    Find repo root when this script lives in <root>/sweep_up/inbox.

    Strategy:
    - Walk up ancestors until we find a folder that contains:
        sweep_up/inbox/   AND   inputs/   AND   outputs/
    This avoids accidentally treating sweep_up/inbox as the project root.
    """
    for p in [start, *start.parents]:
        if (p / "sweep_up" / "inbox").is_dir() and (p / "inputs").is_dir() and (p / "outputs").is_dir():
            return p

    raise RuntimeError(f"Could not find project root above: {start}")


PROJECT_ROOT = find_project_root(INBOX_DIR).resolve()

# Ensure project root is on sys.path so imports work from any CWD
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------
# Path anchors
# ---------------------------------------------------------------------
PUBLICATION_DIR = PROJECT_ROOT / "publication"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
BUILD_PROCESSED_DIR = PROJECT_ROOT / "build" / "processed"
INPUTS_CANONICAL_DIR = PROJECT_ROOT / "inputs" / "canonical"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _extract_block(html: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, flags=re.I | re.S)
    return m.group(1).strip() if m else None


def extract_mainish(html: str) -> str:
    for tag in ("main", "article", "body"):
        blk = _extract_block(html, tag)
        if blk:
            return blk
    return html  # last resort


def strip_base_tag(html: str) -> str:
    return re.sub(r"<base\b[^>]*>\s*", "", html, flags=re.I)


def strip_mathjax_scripts(html: str) -> str:
    # remove MathJax config blocks + the CDN loader, we'll add one unified config
    html = re.sub(
        r"<script>\s*window\.MathJax\s*=\s*\{.*?\};\s*</script>",
        "",
        html,
        flags=re.I | re.S,
    )
    html = re.sub(r"<script[^>]+mathjax@3[^>]+></script>", "", html, flags=re.I)
    return html


def normalize_root_absolute_outputs(html: str) -> str:
    """
    Some source HTML may use root-absolute /outputs/... which breaks in a file bundle.
    Convert to relative outputs/... so our copied bundle outputs/ folder is used.
    """
    html = re.sub(r'src="/outputs/', 'src="outputs/', html, flags=re.I)
    html = re.sub(r"src='/outputs/", "src='outputs/", html, flags=re.I)
    return html


def copy_if_exists(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        print(f"[WARN] Missing (not copied): {src}")
        return
    shutil.copy2(src, dst)
    print(f"[OK] Copied: {src.name} -> {dst}")


def copy_tree_if_exists(src_dir: Path, dst_dir: Path) -> None:
    """
    Copy an entire directory tree into the bundle.
    Keeps the same structure so src="outputs/..." continues to work.
    """
    if not src_dir.exists():
        print(f"[WARN] Missing directory (not copied): {src_dir}")
        return
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
    print(f"[OK] Copied directory: {src_dir} -> {dst_dir}")


def pick_first_existing(candidates: list[Path], label: str) -> Path:
    for p in candidates:
        if p.exists():
            return p
    msg = " / ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Missing {label}. Looked in: {msg}")


def run_annual_exhibits(outdir: Path) -> None:
    """
    Generate annual exhibits directly into the print bundle figures/ directory.
    """
    outdir.mkdir(parents=True, exist_ok=True)

    # Preferred canonical source
    canonical_csv = INPUTS_CANONICAL_DIR / "homeatix_model.csv"

    # Fallback to legacy local CSV (what your current script used)
    legacy_csv = INBOX_DIR / "Homeatix housing market model(Sheet1) (4).csv"

    csv_path = canonical_csv if canonical_csv.exists() else legacy_csv
    if not csv_path.exists():
        print(f"[WARN] Annual CSV not found at: {canonical_csv}")
        print(f"[WARN] Annual CSV not found at: {legacy_csv}")
        print("       Annual exhibits will not be regenerated unless you fix the CSV path.")
        return

    script = INBOX_DIR / "homeatix_annual_exhibits.py"
    if not script.exists():
        raise FileNotFoundError(f"Missing exhibit generator script: {script}")

    cmd = [
        sys.executable,
        str(script),
        "--csv",
        str(csv_path),
        "--outdir",
        str(outdir),
    ]
    print("[RUN] " + " ".join(cmd))
    subprocess.check_call(cmd)


def bundle_extra_figures(figures_dir: Path) -> None:
    """
    Copy any extra figures generated by other scripts (if present).
    Priority: outputs/ (generated) then inbox/ (manual drop-ins).
    """
    copy_if_exists(
        OUTPUTS_DIR / "england_wales_cash_share_quarterly.png",
        figures_dir / "england_wales_cash_share_quarterly.png",
    )
    copy_if_exists(
        INBOX_DIR / "england_wales_cash_share_quarterly.png",
        figures_dir / "england_wales_cash_share_quarterly.png",
    )


def part1_html() -> str:
    """
    Part I block injected before both papers.
    Figure paths are relative to index.html (figures/..).
    """
    return """
<section id="part1">
  <h2>Part I — The 2024 Foundations: Market Function Before Price</h2>

  <p>
    Home@ix began from an observation that sounds simple but changes the whole measurement problem:
    in UK housing stress regimes, the market does not reliably clear through orderly repricing.
    It often clears through <strong>rationing participation</strong>. Turnover collapses, transaction chains fail,
    mortgage-dependent households are screened out, and the observed price index becomes a <em>selected statistic</em> produced by a thinner, wealthier transacting set.
  </p>

  <p>
    Part I sets the domain terms for the rest of the book. Before we define FAIR (the derived, reproducible regime indicator),
    we anchor the foundational claim with a canonical diagnostic module: turnover (market liquidity), cash-versus-mortgage dynamics (access to finance),
    and the balance between new build and old stock activity (delivery and churn capacity).
  </p>

  <div class="box">
    <strong>Working proposition:</strong> affordability is not only a burden ratio; it is an <strong>access-and-allocation regime outcome</strong>.
    In thin markets, price signals can lag while exclusion and mobility failure worsen in real time.
  </div>

  <hr />

  <section id="part1-exhibits">
    <h3>1. A canonical diagnostic module (market depth, access, and mix)</h3>
    <p>
      The exhibits below are treated as a single system lens. Read together, they diagnose whether the housing system is clearing via price,
      or via <em>quantity and composition</em> (thin-market clearing).
    </p>

    <hr />

    <section id="part1-fig1">
      <h3>Figure 1 — Turnover and cash share (annual)</h3>
      <p>
        Turnover is the housing market’s <strong>functionality / liquidity</strong> indicator: how many homes change hands relative to the stock.
        Cash share is a <strong>participation / exclusion</strong> indicator: when cash share rises alongside weak turnover, it is consistent with
        mortgage-dependent households being rationed out by rates, underwriting, or deposit constraints.
      </p>
      <figure>
        <img src="figures/exhibit_1_turnover_cashshare_annual.png"
             alt="Exhibit 1 — Stock turnover (%) and cash share (annual)" loading="lazy" />
        <figcaption><strong>Figure 1.</strong> Stock turnover and cash share (annual).</figcaption>
      </figure>
    </section>

    <hr />

    <section id="part1-fig2a">
      <h3>Figure 2a — Transaction levels: old stock vs new build (annual)</h3>
      <p>
        “Housing activity” is not one market. Old stock dominates volume and is more <strong>credit- and chain-sensitive</strong>.
        New build volumes reflect additional constraints (planning, labour, build finance, developer pacing). The split helps distinguish
        <em>access/finance stress</em> from <em>delivery/capacity stress</em>.
      </p>
      <figure>
        <img src="figures/exhibit_2a_transaction_levels_annual.png"
             alt="Exhibit 2a — Transaction levels: old stock vs new build (annual)" loading="lazy" />
        <figcaption><strong>Figure 2a.</strong> Transaction levels: old stock vs new build (annual).</figcaption>
      </figure>
    </section>

    <hr />

    <section id="part1-fig2b">
      <h3>Figure 2b — Transaction mix shares (annual)</h3>
      <p>
        Mix shares reveal <strong>compositional clearing</strong>: who is still able to transact when the market thins.
        Shifts in shares can signal allocation stress even when headline prices appear stable.
      </p>
      <figure>
        <img src="figures/exhibit_2b_transaction_mix_shares_annual.png"
             alt="Exhibit 2b — Transaction mix shares (annual)" loading="lazy" />
        <figcaption><strong>Figure 2b.</strong> Transaction mix shares (annual).</figcaption>
      </figure>
    </section>

    <hr />

    <section id="part1-fig4">
      <h3>Figure 4 — Indexed price vs indexed turnover (annual)</h3>
      <p>
        When turnover collapses, price indices can lag or understate stress because fewer transactions generate weaker price discovery.
        Liquidity risk becomes macro-relevant.
      </p>
      <figure>
        <img src="figures/exhibit_4_price_vs_turnover_index_annual.png"
             alt="Exhibit 4 — House price vs turnover (indexed, annual)" loading="lazy" />
        <figcaption><strong>Figure 4.</strong> Indexed price vs indexed turnover (annual).</figcaption>
      </figure>
    </section>

    <hr />

    <section id="part1-cashshare-ew">
      <h3>Supplement — Cash purchases share (England vs Wales, quarterly)</h3>
      <p>
        A cross-nation comparison helps separate broad regime shifts from local noise.
        Divergences can reflect geography-specific credit conditions, investor mix, or compositional effects.
      </p>
      <figure>
        <img src="figures/england_wales_cash_share_quarterly.png"
             alt="Cash purchases as a proportion of total transactions (quarterly): England vs Wales"
             loading="lazy" />
        <figcaption><strong>Supplement.</strong> Cash purchases as a proportion of total transactions (quarterly): England vs Wales.</figcaption>
      </figure>
    </section>
  </section>

  <hr />

  <section id="part1-bridge-to-identity">
    <h3>2. Why this forces an accounting identity (and later, FAIR)</h3>
    <p>
      If the system clears through <strong>quantities and composition</strong> under stress, then an affordability framework must track access-to-finance
      and market depth/throughput — not just price levels.
    </p>
    <div class="box">
      <strong>Bridge statement:</strong> Part I defines the failure mode (thin-market clearing). FAIR later converts that diagnosis into a reproducible quarterly monitor.
    </div>
  </section>

  <hr />

  <section id="part1-source-note">
    <h3>3. Source note (reproducibility)</h3>
    <ul>
      <li><strong>Exhibits generator:</strong> <code>sweep_up/inbox/homeatix_annual_exhibits.py</code></li>
      <li><strong>Bundled figures:</strong> <code>figures/</code> (relative to this <code>index.html</code>)</li>
    </ul>
  </section>
</section>
""".strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Assemble the full Home@ix print bundle into a publication/print_* folder."
    )
    p.add_argument(
        "--outdir",
        type=str,
        default="",
        help="Optional output directory. If omitted, a new publication/print_YYYYMMDD_HHMMSS folder is created.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.outdir.strip():
        outdir = Path(args.outdir).expanduser().resolve()
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir = (PUBLICATION_DIR / f"print_{stamp}").resolve()

    outdir.mkdir(parents=True, exist_ok=True)

    print("ASSEMBLE PATHS")
    print("  __file__:", Path(__file__).resolve())
    print("  CWD:", Path.cwd().resolve())
    print("  PROJECT_ROOT:", PROJECT_ROOT)
    print("  INBOX_DIR:", INBOX_DIR)
    print("  INPUTS_CANONICAL_DIR:", INPUTS_CANONICAL_DIR)
    print("  BUILD_PROCESSED_DIR:", BUILD_PROCESSED_DIR)
    print("  OUTPUTS_DIR:", OUTPUTS_DIR)
    print("  PUBLICATION_DIR:", PUBLICATION_DIR)
    print("  OUTDIR:", outdir)

    follow = pick_first_existing(
        [
            PROJECT_ROOT / "homeix_followup_paper.html",
            INBOX_DIR / "homeix_followup_paper.html",
        ],
        label="homeix_followup_paper.html",
    )

    fair = pick_first_existing(
        [
            PROJECT_ROOT / "homeix_fair_paper.html",
            INBOX_DIR / "homeix_fair_paper.html",
        ],
        label="homeix_fair_paper.html",
    )

    figures_dir = outdir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # 1) Regenerate exhibits into the bundle
    run_annual_exhibits(figures_dir)

    # 2) Copy any additional figures
    bundle_extra_figures(figures_dir)

    # 2b) Copy paper/FAIR assets referenced as outputs/... into the bundle
    copy_tree_if_exists(OUTPUTS_DIR / "figures", outdir / "outputs" / "figures")
    copy_tree_if_exists(OUTPUTS_DIR / "fair_assets", outdir / "outputs" / "fair_assets")
    copy_tree_if_exists(OUTPUTS_DIR / "draft_paper_assets", outdir / "outputs" / "draft_paper_assets")

    # 3) Assemble HTML
    follow_html = normalize_root_absolute_outputs(strip_mathjax_scripts(strip_base_tag(_read(follow))))
    fair_html = normalize_root_absolute_outputs(strip_mathjax_scripts(strip_base_tag(_read(fair))))

    follow_body = extract_mainish(follow_html)
    fair_body = extract_mainish(fair_html)

    human_stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    known_issues = """
<section class="box">
  <h2>Known issues (pre-publication)</h2>
  <ul>
    <li><strong>Animation rendering:</strong> some animated assets may not display in all viewers. Use exported GIF/PNG fallbacks in <code>assets/</code> where provided.</li>
    <li><strong>Math rendering:</strong> equations are standardised to <code>$$...$$</code>. If any equations appear unrendered, open the HTML in a modern browser (MathJax-enabled).</li>
  </ul>
</section>
""".strip()

    out = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Home@ix — Full Working Book (print bundle)</title>

  <!-- MathJax (standardised to $$..$$) -->
  <script>
    window.MathJax = {{
      tex: {{
        displayMath: [['$$','$$']],
        inlineMath: []
      }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>

  <style>
    :root {{ --max: 980px; }}
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.6; margin: 2rem; color: #111; }}
    main {{ max-width: var(--max); margin: 0 auto; }}
    h1, h2, h3 {{ line-height: 1.15; }}
    .meta {{ color: #444; }}
    .box {{ border: 1px solid #ddd; padding: 12px 14px; border-radius: 10px; background: #fafafa; margin: 1.2rem 0; }}
    figure {{ margin: 1.25rem 0; padding: .75rem; border: 1px dashed #cfcfcf; border-radius: 10px; }}
    figcaption {{ color: #444; font-size: .95rem; }}
    hr {{ border: 0; border-top: 1px solid #eee; margin: 2rem 0; }}

    figure {{ max-width: 900px; margin-left: auto; margin-right: auto; }}
    figure img {{ display: block; max-width: 100%; height: auto; margin: 0 auto; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Home@ix — Full Working Book (Draft)</h1>
      <p class="meta"><strong>Print bundle:</strong> {outdir.name} &nbsp;|&nbsp; <strong>Built:</strong> {human_stamp}</p>
    </header>

    {known_issues}

    <hr />

    {part1_html()}

    <hr />

    <section id="followup">
      <h2>Follow-up Paper</h2>
      {follow_body}
    </section>

    <hr />

    <section id="fair">
      <h2>FAIR Paper</h2>
      {fair_body}
    </section>

    <hr />
  </main>
</body>
</html>
"""

    (outdir / "index.html").write_text(out, encoding="utf-8")
    print(f"Wrote: {outdir / 'index.html'}")


if __name__ == "__main__":
    main()
