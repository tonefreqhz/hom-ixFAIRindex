# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def markdown_to_html(md: str) -> str:
    """
    Convert Markdown text to HTML for embedding into the assembled publication.
    """
    import markdown  # pip install markdown

    return markdown.markdown(
        md,
        extensions=["fenced_code", "tables"],
        output_format="html5",
    )


# ---------------------------------------------------------------------
# Bootstrap: resolve project root robustly
#
# This script lives at: <project_root>/sweep_up/inbox/assemble_full_ebook.py
#
# Reproducibility rule:
#   - ALL canonical paths (inputs/, outputs/, publication/, build/) are rooted at PROJECT_ROOT
#   - Never depend on current working directory (CWD) for canonical repo paths
# ---------------------------------------------------------------------
INBOX_DIR = Path(__file__).resolve().parent


def _try_git_root(start: Path) -> Path | None:
    """Prefer git root if available (most robust)."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if out:
            return Path(out).resolve()
    except Exception:
        return None
    return None


def find_project_root(start: Path) -> Path:
    """
    Find repo root when this script lives in <root>/sweep_up/inbox.

    Strategy:
    1) Try git root (authoritative).
    2) Heuristic fallback: walk up ancestors until we find:
         sweep_up/inbox/ AND inputs/ AND outputs/
    """
    git_root = _try_git_root(start)
    if git_root is not None:
        return git_root

    for p in [start, *start.parents]:
        if (p / "sweep_up" / "inbox").is_dir() and (p / "inputs").is_dir() and (p / "outputs").is_dir():
            return p.resolve()

    raise RuntimeError(f"Could not find project root above: {start}")


PROJECT_ROOT = find_project_root(INBOX_DIR)

# Ensure project root is on sys.path so imports work from any CWD
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------
# Path anchors (canonical repo locations)
# ---------------------------------------------------------------------
PUBLICATION_DIR = PROJECT_ROOT / "publication"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
BUILD_PROCESSED_DIR = PROJECT_ROOT / "build" / "processed"
INPUTS_CANONICAL_DIR = PROJECT_ROOT / "inputs" / "canonical"


def render_section_slug(slug: str) -> str:
    """
    Read sections/<slug>/section.md and wrap it as a <section> block.
    """
    md_path = PROJECT_ROOT / "sections" / slug / "section.md"
    if not md_path.exists():
        raise FileNotFoundError(f"Missing section.md for slug '{slug}': {md_path}")

    md = md_path.read_text(encoding="utf-8")
    return f'<section id="{slug}">\n{markdown_to_html(md)}\n</section>\n'


# ---------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------
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


def normalize_outputs_to_assets(html: str) -> str:
    """
    Canonical print-bundle layout (from rebuild_publish.ps1) uses:
      OUTDIR/assets/...

    But source HTML may reference:
      /outputs/...  or outputs/...

    Rewrite those to:
      assets/...

    Also heals legacy path variants found in embedded papers:
      - assetsfigures/...         -> assets/figures/...
      - assetsfair_assets/...     -> assets/fair_assets/...
      - assetsdraft_paper_assets/ -> assets/draft_paper_assets/...
      - fig_fair_level.png        -> assets/fair_assets/fig_fair_level.png
      - fig_fair_contributions.png-> assets/fair_assets/fig_fair_contributions.png

    Covers src= and href= in both quote styles.
    """
    # root-absolute -> bundle-relative
    html = re.sub(r'(src|href)="/outputs/', r'\1="assets/', html, flags=re.I)
    html = re.sub(r"(src|href)='/outputs/", r"\1='assets/", html, flags=re.I)

    # already relative outputs/... -> assets/...
    # IMPORTANT: keep the trailing slash after assets/ (avoids "assetsfigures" bug)
    html = re.sub(r'(src|href)="outputs/', r'\1="assets/', html, flags=re.I)
    html = re.sub(r"(src|href)='outputs/", r"\1='assets/", html, flags=re.I)

    # heal missing-slash legacy variants
    html = re.sub(r'(src|href)=(["\'])assetsfigures/', r"\1=\2assets/figures/", html, flags=re.I)
    html = re.sub(r'(src|href)=(["\'])assetsfair_assets/', r"\1=\2assets/fair_assets/", html, flags=re.I)
    html = re.sub(r'(src|href)=(["\'])assetsdraft_paper_assets/', r"\1=\2assets/draft_paper_assets/", html, flags=re.I)

    # heal bare FAIR filenames (they live in assets/fair_assets/ in the bundle)
    html = re.sub(
        r'(src|href)=(["\'])fig_fair_level\.png\2',
        r'\1=\2assets/fair_assets/fig_fair_level.png\2',
        html,
        flags=re.I,
    )

    html = re.sub(
        r'(src|href)=(["\'])fig_fair_contributions\.png\2',
        r'\1=\2assets/fair_assets/fig_fair_contributions.png\2',
        html,
        flags=re.I,
    )

    # heal a known filename mismatch (legacy "crash" vs canonical "crisis")
    html = re.sub(
        r"fig_price_and_fair_with_crash_starts\.png",
        "fig_price_and_fair_with_crisis_starts.png",
        html,
        flags=re.I,
    )

    # optional: rewrite outputs/... shown inside <code>...</code> blocks only
    def _rewrite_outputs_in_code(m):
        inner = re.sub(r"\boutputs/", "assets/", m.group(1), flags=re.I)
        return f"<code>{inner}</code>"

    html = re.sub(
        r"<code>(.*?)</code>",
        _rewrite_outputs_in_code,
        html,
        flags=re.I | re.S,
    )

    return html


def copy_if_exists(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return False
    shutil.copy2(src, dst)
    print(f"[OK] Copied: {src.name} -> {dst}")
    return True


def pick_first_existing(candidates: list[Path], label: str) -> Path:
    for p in candidates:
        if p.exists():
            return p
    msg = "\n  - " + "\n  - ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"Missing {label}. Looked in:{msg}")


# ---------------------------------------------------------------------
# Bundle-contract helpers (rebuild_publish.ps1 is canonical)
# ---------------------------------------------------------------------
def looks_like_print_bundle_dir(p: Path) -> bool:
    """
    Heuristic: CWD is a print bundle if it is .../publication/print_*
    """
    try:
        p = p.resolve()
    except Exception:
        return False
    return p.is_dir() and p.parent.name == "publication" and p.name.startswith("print_")


def bootstrap_assets_from_repo_outputs(outdir: Path) -> None:
    """
    If OUTDIR/assets/* are missing, create and populate them from repo outputs/*.

    This makes assemble usable standalone (and also heals partially-built bundles).
    It does NOT replace rebuild_publish.ps1 as canonical; it simply makes the bundle
    conform to the canonical layout.
    """
    mapping = [
        (OUTPUTS_DIR / "figures", outdir / "assets" / "figures"),
        (OUTPUTS_DIR / "fair_assets", outdir / "assets" / "fair_assets"),
        (OUTPUTS_DIR / "draft_paper_assets", outdir / "assets" / "draft_paper_assets"),
    ]

    for src, dst in mapping:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"[OK] Bootstrapped asset folder: {src} -> {dst}")
        else:
            print(f"[WARN] Missing outputs folder (cannot bootstrap): {src}")


def assert_bundle_layout(outdir: Path, *, attempt_bootstrap: bool = True) -> None:
    """
    Ensure OUTDIR looks like a rebuild_publish.ps1 print bundle.
    If attempt_bootstrap=True, missing dirs will be created/populated from repo outputs/.
    """
    required = [
        outdir / "assets" / "figures",
        outdir / "assets" / "fair_assets",
        outdir / "assets" / "draft_paper_assets",
    ]

    missing = [p for p in required if not p.exists()]
    if missing and attempt_bootstrap:
        print("[WARN] Print bundle missing canonical assets/. Bootstrapping from repo outputs/ ...")
        bootstrap_assets_from_repo_outputs(outdir)

    missing2 = [p for p in required if not p.exists()]
    if missing2:
        msg = "\n  - " + "\n  - ".join(str(p) for p in missing2)
        raise RuntimeError(
            "Print bundle does not match canonical rebuild_publish.ps1 layout.\n"
            "Missing required directories:" + msg + "\n\n"
            "Fix: run rebuild_publish.ps1 first (or create these assets/ folders in OUTDIR)."
        )


def resolve_in_bundle(outdir: Path, rel_under_assets: str, *, allow_repo_fallback: bool = True) -> Path:
    """
    Resolve an asset using canonical bundle locations.

    Primary:
      - OUTDIR/<filename>                    (ps1 copies some files flat into bundle root)
      - OUTDIR/assets/<rel_under_assets>     (ps1 copies folders here)

    Optional fallback (dev convenience only):
      - PROJECT_ROOT/outputs/<rel_under_assets>
    """
    rel = Path(rel_under_assets)

    candidates = [
        outdir / rel.name,
        outdir / "assets" / rel,
    ]

    if allow_repo_fallback:
        candidates.append(OUTPUTS_DIR / rel)

    return pick_first_existing(candidates, label=f"bundle asset {rel_under_assets}")


# ---------------------------------------------------------------------
# Domain-specific generation / bundling
# ---------------------------------------------------------------------
def run_annual_exhibits(outdir_assets_figures: Path) -> None:
    """
    Generate annual exhibits directly into the print bundle assets/figures/ directory.
    """
    outdir_assets_figures.mkdir(parents=True, exist_ok=True)

    canonical_csv = INPUTS_CANONICAL_DIR / "homeatix_model.csv"
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
        str(outdir_assets_figures),
    ]
    print("[RUN] " + " ".join(cmd))
    subprocess.check_call(cmd)


def ensure_cash_share_quarterly_in_bundle(outdir_assets_figures: Path) -> None:
    """
    rebuild_publish.ps1 does not explicitly include this file.
    If it's referenced by Part I HTML, ensure it exists in OUTDIR/assets/figures/.

    Sources tried (in order):
      1) PROJECT_ROOT/outputs/england_wales_cash_share_quarterly.png
      2) PROJECT_ROOT/outputs/figures/england_wales_cash_share_quarterly.png
      3) INBOX_DIR/england_wales_cash_share_quarterly.png
    """
    dst = outdir_assets_figures / "england_wales_cash_share_quarterly.png"
    if dst.exists():
        return

    candidates = [
        OUTPUTS_DIR / "england_wales_cash_share_quarterly.png",
        OUTPUTS_DIR / "figures" / "england_wales_cash_share_quarterly.png",
        INBOX_DIR / "england_wales_cash_share_quarterly.png",
    ]

    for src in candidates:
        if copy_if_exists(src, dst):
            return

    print("[WARN] Missing cash-share quarterly figure. Looked in:")
    for c in candidates:
        print("       -", c)


# ---------------------------------------------------------------------
# Part I HTML block (uses canonical bundle paths: assets/figures/...)
# ---------------------------------------------------------------------
def part1_html() -> str:
    """
    Part I block injected before both papers.

    Canonical bundle paths:
      - figures live under assets/figures/ relative to index.html
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
        <img src="assets/figures/exhibit_1_turnover_cashshare_annual.png"
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
        <img src="assets/figures/exhibit_2a_transaction_levels_annual.png"
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
        <img src="assets/figures/exhibit_2b_transaction_mix_shares_annual.png"
             alt="Exhibit 2b — Transaction mix shares (annual)" loading="lazy" />
        <figcaption><strong>Figure 2b.</strong> Transaction mix shares (annual).</figcaption>
      </figure>
    </section>

    <hr />

    <section id="part1-fig3">
      <h3>Figure 3 — Mortgage outstanding composition by lender type (annual)</h3>
      <p>
        This exhibit shows how the stock of mortgage lending is distributed across lender types.
        Shifts in composition matter because “credit availability” is not a single dial: it is mediated
        by lender balance sheets, underwriting posture, and the kinds of borrowers each segment serves.
      </p>
      <figure>
        <img src="assets/figures/exhibit_3_mortgage_composition_annual.png"
             alt="Exhibit 3 — Mortgage outstanding composition by lender type (annual, share of total)"
             loading="lazy" />
        <figcaption><strong>Figure 3.</strong> Mortgage outstanding composition by lender type (annual, share of total).</figcaption>
      </figure>
    </section>

    <hr />

    <section id="homeix-identity">
      <h2>Home@ix — The Identity (as developed) and the Reproducible Build</h2>

      <p>
        Home@ix uses accounting identities to describe the housing system as a throughput machine.
        The point is not “math for effect”. The point is discipline: when the system is constrained by absorption, credit gates, delivery friction,
        and value-capture reality, output behaves like a set of multipliers. If one dial is near zero, the product collapses.
      </p>

      <section id="homeix-identity-ams">
        <h3>Identity 1: Affordable Market Supply (AMS)</h3>

        <p>
          We start with the supply identity: the affordable supply the system can deliver, given real-world throttles.
        </p>

        <p><strong>Affordable Market Supply</strong>:</p>
        <p>$$AMS = (HM \\cdot P \\cdot AR \\cdot D \\cdot T \\cdot PVC) + HS$$</p>

        <ul>
          <li><strong>HM</strong>: housebuilding market capacity (deliverable output, not theoretical land)</li>
          <li><strong>P</strong>: affordable proportion of delivery</li>
          <li><strong>AR</strong>: absorption rate (how fast homes can be sold/let without destabilising price)</li>
          <li><strong>D</strong>: diversity (tenure/product mix widening take-up)</li>
          <li><strong>T</strong>: throughput (permission → start → completion conversion efficiency)</li>
          <li><strong>PVC</strong>: planning value capture that works in practice</li>
          <li><strong>HS</strong>: existing affordable housing stock</li>
        </ul>
      </section>

      <section id="homeix-identity-an">
        <h3>Identity 2: Affordable Housing Need (AN), derived</h3>

        <p>
          Need persists (and often rises) when supply is tethered to private-market throughput and absorption constraints.
          Home@ix expresses this by introducing a sequencing/fast-tracking factor <strong>F</strong> and a stabiliser term:
          a ring-fenced <strong>New Circuit of Credit</strong> (<strong>NCC</strong>) that funds affordable delivery without simply bidding up existing stock.
        </p>

        <p><strong>Start from the expanded form</strong>:</p>
        <p>$$AN = HD + (HM \\cdot P \\cdot AR \\cdot D \\cdot T \\cdot PVC \\cdot F) + HS - AMS + NCC$$</p>

        <p><strong>Substitute</strong> $$AMS = (HM \\cdot P \\cdot AR \\cdot D \\cdot T \\cdot PVC) + HS$$ <strong>and simplify</strong>:</p>
        <p>$$AN = HD + (HM \\cdot P \\cdot AR \\cdot D \\cdot T \\cdot PVC \\cdot (F - 1)) + NCC$$</p>

        <ul>
          <li><strong>HD</strong>: HomeMaker effective demand (need in households, not only “bankable demand this quarter”)</li>
          <li><strong>F</strong>: sequencing/fast-tracking factor (the sign convention is: baseline at $$F=1$$)</li>
          <li><strong>NCC</strong>: New Circuit of Credit Creation (the stabiliser that decouples affordable supply from private-market freeze/thaw cycles)</li>
        </ul>
      </section>

      <section id="repo-structure">
        <h3>Reproducibility: from canonical inputs to the figures in this book</h3>

        <p>
          This repository is organised so a reader can move from source data to computed series to plotted exhibits—and regenerate the print bundle.
          The print folder you are reading is a portable snapshot of that pipeline.
        </p>

        <ul>
          <li><strong>Canonical inputs (source of truth):</strong> <code>inputs/canonical/</code></li>
          <li><strong>Intermediate processing (rebuildable cache):</strong> <code>build/processed/</code></li>
          <li><strong>Generated artefacts referenced by papers:</strong> <code>outputs/figures/</code>, <code>outputs/fair_assets/</code>, <code>outputs/draft_paper_assets/</code></li>
          <li><strong>Portable publication bundle:</strong> <code>publication/print_*/</code> containing <code>index.html</code> and copied <code>assets/</code></li>
        </ul>

        <p>
          Operationally, the maths “computes” as deterministic column derivations and transforms inside the Python scripts,
          and the figures are the audit trail of those computations.
        </p>

        <ul>
          <li><code>sweep_up/inbox/homeatix_annual_exhibits.py</code> — reads canonical data and generates the Part I exhibits into <code>assets/figures/</code></li>
          <li><code>sweep_up/inbox/assemble_full_ebook.py</code> — writes the combined <code>index.html</code> into the print bundle and normalises asset paths to <code>assets/</code></li>
        </ul>
      </section>
    </section>

    <hr />

    <section id="part1-fig4">
      <h3>Figure 4 — Indexed price vs indexed turnover (annual)</h3>
      <p>
        When turnover collapses, price indices can lag or understate stress because fewer transactions generate weaker price discovery.
        Liquidity risk becomes macro-relevant.
      </p>
      <figure>
        <img src="assets/figures/exhibit_4_price_vs_turnover_index_annual.png"
             alt="Exhibit 4 — House price vs turnover (indexed, annual)" loading="lazy" />
        <figcaption><strong>Figure 4.</strong> Indexed price vs turnover (annual).</figcaption>
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
        <img src="assets/figures/england_wales_cash_share_quarterly.png"
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
      <li><strong>Bundled figures:</strong> <code>assets/figures/</code> (relative to this <code>index.html</code>)</li>
    </ul>
  </section>
</section>
""".strip()


def fair_preface_html() -> str:
    return """
<section id="fair-preface">
  <h2>FAIR — Professional summary (LinkedIn-style)</h2>

  <p class="meta">
    This section is a distilled, non-technical bridge into the FAIR working paper.
    It is written for housing policy, finance, and economics audiences.
  </p>

  <div class="box">
    <p><strong>Thesis:</strong> The UK housing crisis isn’t only about prices. In stressed regimes, markets can “clear” through <strong>exclusion</strong>, not repricing.</p>
    <p>
      When turnover collapses and mortgage-dependent households are screened out, the reported price index becomes a
      <em>selected statistic</em> generated by a thinner, wealthier transacting set.
    </p>
  </div>

  <h3>The coupled system (four loops)</h3>
  <ol>
    <li><strong>Bank credit quality and mortgage concentration</strong></li>
    <li><strong>Mortgage lending and broad money dynamics</strong> (deposit creation / M4 channel)</li>
    <li><strong>Supply delivery constraints</strong> and developer pacing within absorption bands</li>
    <li><strong>Affordability</strong> understood as access-and-allocation, not only burden ratios</li>
  </ol>

  <h3>Why “low arrears” can be a false comfort</h3>
  <p>
    Headline arrears can look stable even as vulnerability rises, because the observed borrower pool can improve via
    <strong>compositional selection</strong> (marginal cohorts stop transacting or are screened out of new lending).
    Buy-to-let arrears can behave as a leading indicator when landlord cashflows tighten.
  </p>

  <h3>Introducing FAIR (a forward regime signal)</h3>
  <p>
    FAIR is a quarterly indicator designed as a <strong>2–3 year forward regime signal</strong> for affordability as access/allocation.
    It combines:
  </p>
  <ul>
    <li><strong>Credit–price decoupling</strong> (a credit–price wedge)</li>
    <li><strong>Market depth</strong> (turnover dynamics relative to stock)</li>
    <li><em>Optional:</em> new-build share dynamics as a composition proxy</li>
  </ul>

  <div class="box">
    <p><strong>Transparent form (as used in this project):</strong></p>
    <p>$$FAIR = 100 \\times (0.55 \\times \\text{credit–price wedge} - 0.35 \\times \\text{turnover growth} + 0.10 \\times \\Delta\\text{new-build share})$$</p>
    <p class="meta">Components are z-scored against pooled baseline windows (2003–2007 and 2013–2019) to avoid structural-break periods.</p>
  </div>

  <h3>Interpretation bands</h3>
  <table>
    <thead>
      <tr><th>FAIR level</th><th>Regime signal</th></tr>
    </thead>
    <tbody>
      <tr><td>&ge; 50</td><td>Strong deterioration risk</td></tr>
      <tr><td>20 to 50</td><td>Mild deterioration bias</td></tr>
      <tr><td>&minus;20 to 20</td><td>Neutral / noisy</td></tr>
      <tr><td>&minus;50 to &minus;20</td><td>Mild improvement bias</td></tr>
      <tr><td>&lt; &minus;50</td><td>Strong improvement (often stress-driven)</td></tr>
    </tbody>
  </table>

  <h3>Policy implication (what gets missed)</h3>
  <p>
    If affordability deterioration is driven by <strong>allocation and throughput failure under mortgage-credit dominance</strong>,
    then symptom levers alone (temporary subsidies, short-run tax changes) can lag the regime shift.
  </p>

  <table>
    <thead>
      <tr><th>Problem loop</th><th>Symptom lever</th><th>Structural lever</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>Mortgage-credit dominance ties stability to housing</td>
        <td>Macroprudential tweaks, temporary guarantees</td>
        <td>Ring-fenced affordable housing credit; alternative tenure finance</td>
      </tr>
      <tr>
        <td>Thin-market clearing excludes mortgaged households</td>
        <td>Buyer grants, transaction stimulus</td>
        <td>Shared equity, co-op models, community land trusts</td>
      </tr>
      <tr>
        <td>Developer pacing constrains near-term throughput</td>
        <td>Planning speed incentives</td>
        <td>Counter-cyclical delivery vehicles; public build-to-live options</td>
      </tr>
    </tbody>
  </table>

  <div class="box">
    <p><strong>Bridge:</strong> The FAIR paper that follows formalises the measurement, definitions, and reproducible build for this indicator.</p>
  </div>
</section>
""".strip()


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Assemble the full Home@ix ebook HTML (index.html) inside a canonical publication print bundle."
    )
    p.add_argument(
        "--outdir",
        type=str,
        default="",
        help="Output directory (print bundle). If omitted and CWD is publication/print_*, uses CWD; otherwise creates a new publication/print_YYYYMMDD_HHMMSS.",
    )
    p.add_argument(
        "--no-exhibits",
        action="store_true",
        help="Skip regenerating annual exhibits (still assembles HTML).",
    )
    p.add_argument(
        "--skip-bundle-check",
        action="store_true",
        help="Skip validation that OUTDIR matches rebuild_publish.ps1 bundle layout (dev-only).",
    )
    return p.parse_args()


def fair_maths_explained_html() -> str:
    md = r"""
# Home@ix FAIR — The Maths Explained

This paper builds a **forward-looking affordability regime indicator** (FAIR) for UK housing. The maths is deliberately simple — it's accounting identities and z-score composites, not econometric estimation. Here's a structured walkthrough of every mathematical piece, from the supply identities through to the final FAIR number.

---

## 🏗️ 1. The Supply & Need Identities

These aren't statistical models — they're **accounting frameworks** that express housing as a throughput system where each factor is a multiplier. If any one term collapses toward zero, the whole product collapses.

### Identity 1: Affordable Market Supply (AMS)

$$AMS = (HM \cdot P \cdot AR \cdot D \cdot T \cdot PVC) + HS$$

This is a **multiplicative chain** — deliverable affordable housing is the product of:

| **Term** | **Meaning** |
|----------|-------------|
| $$HM$$ | Housebuilding market capacity (actual deliverable output) |
| $$P$$ | Affordable proportion of that delivery |
| $$AR$$ | Absorption rate (how fast homes sell without destabilising price) |
| $$D$$ | Diversity of tenure/product mix (widens take-up) |
| $$T$$ | Throughput efficiency (permission → start → completion) |
| $$PVC$$ | Planning value capture that works in practice |
| $$HS$$ | Existing affordable housing stock (additive, not multiplicative) |

The key insight: because the first six terms are **multiplied**, a bottleneck in *any one* (say absorption rate drops near zero during a credit crunch) kills the entire flow — even if land, planning, and capacity are fine.

### Identity 2: Affordable Housing Need (AN)

Start from the expanded form:

$$AN = HD + (HM \cdot P \cdot AR \cdot D \cdot T \cdot PVC \cdot F) + HS - AMS + NCC$$

Now substitute the AMS definition and simplify. Since $$AMS = (HM \cdot P \cdot AR \cdot D \cdot T \cdot PVC) + HS$$, the $$HS$$ terms cancel and the multiplicative block partially cancels:

$$AN = HD + (HM \cdot P \cdot AR \cdot D \cdot T \cdot PVC \cdot (F - 1)) + NCC$$

- **$$HD$$** = HomeMaker effective demand (real household need, not just "bankable demand this quarter")
- **$$F$$** = sequencing/fast-tracking factor. At $$F = 1$$ (baseline), the middle term vanishes — need equals demand plus the credit stabiliser. When $$F > 1$$, fast-tracking adds supply; when $$F < 1$$, delays subtract it.
- **$$NCC$$** = New Circuit of Credit Creation — a ring-fenced funding channel for affordable delivery that doesn't just bid up existing stock prices.

This is the paper's structural claim in equation form: *need persists when supply is tethered to private-market throughput, and only a decoupled credit circuit can break the dependency.*

---

## 📊 2. FAIR — The Indicator (Step by Step)

FAIR converts the qualitative diagnosis ("markets clear through rationing, not repricing") into a **single reproducible number** each quarter.

### Step 1: Compute Year-on-Year Growth Rates

For house prices $$P_t$$, mortgage stock $$MB_t$$, and turnover $$TO_t$$:

$$g_t^P = \frac{P_t - P_{t-4}}{P_{t-4}}$$

$$g_t^{MB} = \frac{MB_t - MB_{t-4}}{MB_{t-4}}$$

$$g_t^{TO} = \frac{TO_t - TO_{t-4}}{TO_{t-4}}$$

(The subscript $$t-4$$ means "same quarter last year" in quarterly data.)

### Step 2: Compute the Credit–Price Wedge

$$W_t = g_t^P - g_t^{MB}$$

This is the **core diagnostic variable**. When $$W_t > 0$$, house prices are growing faster than the mortgage stock that finances them — prices are *decoupling* from credit.

### Step 3: Optional New-Build Share Change

$$\Delta NB_t = NB_t - NB_{t-4}$$

A simple year-on-year difference (not a growth rate) in the new-build share of transactions.

### Step 4: Baseline Normalisation (Z-Scores)

Rather than z-scoring against the full history (which would let crisis periods distort what "normal" looks like), it pools two "relatively normal" windows:

- **2003Q1–2007Q4**
- **2013Q1–2019Q4**

For any series $$X_t$$:

$$z(X_t) = \frac{X_t - \mu_X}{\sigma_X}$$

where $$\mu_X$$ and $$\sigma_X$$ are computed **only from the baseline quarters**.

### Step 5: FAIR Composite

**Three-component version:**

$$FAIR_t = 100 \cdot \Big( 0.55 \cdot z(W_t) - 0.35 \cdot z(g_t^{TO}) + 0.10 \cdot z(\Delta NB_t) \Big)$$

**Two-component fallback** (when new-build data is unavailable):

$$FAIR_t = 100 \cdot \Big( 0.55 \cdot z(W_t) - 0.35 \cdot z(g_t^{TO}) \Big)$$

### Step 6: Direction-of-Flow

$$\Delta FAIR_t = FAIR_t - FAIR_{t-1}$$

---

## 🎯 3. Interpretation Bands

| **FAIR range** | **Regime reading** |
|----------------|-------------------|
| $$FAIR \ge 50$$ | Strong deterioration risk |
| $$20 \le FAIR < 50$$ | Mild deterioration bias |
| $$-20 \le FAIR < 20$$ | Neutral / noisy |
| $$-50 \le FAIR < -20$$ | Mild improvement bias |
| $$FAIR < -50$$ | Strong improvement (often itself stress-driven — e.g., post-crash credit collapse) |

---

## 🔍 4. Backtesting Framework

### Crash-Start Definition

A **crash start** is defined algorithmically as:
- A local price peak followed by a drawdown of at least $$X\%$$ within $$Y$$ quarters
- With a minimum cooldown of $$C$$ quarters between events

### Warning Rules (Illustrative)

| **Rule** | **Condition** | **What it captures** |
|----------|--------------|---------------------|
| A | $$FAIR > 20$$ for 2 consecutive quarters | Sustained elevated stress |
| B | $$\Delta FAIR > 5$$ for 2 consecutive quarters | Sustained acceleration |
| C | $$FAIR > 0$$ and $$\Delta FAIR \ge 0$$ | Broad worsening (looser trigger) |

### Evaluation Metrics

- **Lead time**
- **False-positive rate**

---

## 💡 5. Key Takeaways on the Maths

1. **Supply identities** use multiplication to encode the "weakest link" property.
2. **FAIR is a weighted z-score composite** with a baseline that excludes crisis windows.
3. **No parameters are estimated** — fixed weights by design.
4. **Baseline choice** is the most consequential methodological decision.
""".strip()

    return markdown_to_html(md)


def main() -> None:
    args = parse_args()
    cwd = Path.cwd().resolve()

    if args.outdir.strip():
        outdir = Path(args.outdir).expanduser().resolve()
    else:
        # IMPORTANT: rebuild_publish.ps1 runs assemble from inside $pub.
        # If CWD is already a print bundle, use it as OUTDIR.
        if looks_like_print_bundle_dir(cwd):
            outdir = cwd
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            outdir = (PUBLICATION_DIR / f"print_{stamp}").resolve()

    outdir.mkdir(parents=True, exist_ok=True)

    print("ASSEMBLE PATHS")
    print("  __file__:", Path(__file__).resolve())
    print("  CWD:", cwd)
    print("  PROJECT_ROOT:", PROJECT_ROOT)
    print("  INBOX_DIR:", INBOX_DIR)
    print("  INPUTS_CANONICAL_DIR:", INPUTS_CANONICAL_DIR)
    print("  BUILD_PROCESSED_DIR:", BUILD_PROCESSED_DIR)
    print("  OUTPUTS_DIR:", OUTPUTS_DIR)
    print("  PUBLICATION_DIR:", PUBLICATION_DIR)
    print("  OUTDIR:", outdir)

    # Canonical print bundle expectation (from rebuild_publish.ps1)
    if not args.skip_bundle_check:
        assert_bundle_layout(outdir, attempt_bootstrap=True)

    # Locate source HTMLs (ps1 may copy into bundle root; otherwise use repo/inbox)
    follow = pick_first_existing(
        [
            outdir / "homeix_followup_paper.html",
            PROJECT_ROOT / "homeix_followup_paper.html",
            INBOX_DIR / "homeix_followup_paper.html",
        ],
        label="homeix_followup_paper.html",
    )

    fair = pick_first_existing(
        [
            outdir / "homeix_fair_paper.html",
            PROJECT_ROOT / "homeix_fair_paper.html",
            INBOX_DIR / "homeix_fair_paper.html",
        ],
        label="homeix_fair_paper.html",
    )

    # Bundle figure locations (canonical)
    assets_figures_dir = outdir / "assets" / "figures"
    assets_figures_dir.mkdir(parents=True, exist_ok=True)

    # 1) Regenerate annual exhibits into assets/figures (optional)
    if args.no_exhibits:
        print("[SKIP] Annual exhibits regeneration (--no-exhibits).")
    else:
        run_annual_exhibits(assets_figures_dir)

    # 2) Ensure supplemental figure exists where Part I expects it
    ensure_cash_share_quarterly_in_bundle(assets_figures_dir)

    # 3) Assemble HTML (rewrite outputs/... -> assets/...)
    follow_html = normalize_outputs_to_assets(strip_mathjax_scripts(strip_base_tag(_read(follow))))
    fair_html = normalize_outputs_to_assets(strip_mathjax_scripts(strip_base_tag(_read(fair))))

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

    # ✅ Renamed from "my-new-section-title" to a stable, publication-ready slug:
    pre_part1 = render_section_slug("opening-chapters")

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
        inlineMath: [['\\\\(','\\\\)']],
      }},
      options: {{
        skipHtmlTags: ['script','noscript','style','textarea','pre','code']
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

    {pre_part1}

    {part1_html()}

    <hr />

    <section id="followup">
      <h2>Follow-up Paper</h2>
      {follow_body}
    </section>

    <hr />

    {fair_preface_html()}

    <hr />

    {fair_maths_explained_html()}

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
