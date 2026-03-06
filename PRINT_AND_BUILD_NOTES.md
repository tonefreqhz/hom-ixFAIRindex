# Reproducible Self‑Pub Kit — Anchor (Ground Truth for Home@ix FAIR Index)

> This repo exists because **drift is the default**—and reproducibility is a feature you have to build on purpose.
> Anchored to prevent LLM hallucinations in math-heavy property market analysis (Gödel/Tarski-inspired external observation).

Last updated: 2026-03-06  
Owner machine: Windows (PowerShell 7.x, pwsh)  
Verified on owner machine: PowerShell 7.5.4  
Repo: https://github.com/tonefreqhz/hom-ixFAIRindex  
Branch: main

---

## 0) What this file is (and is not)
This ANCHOR is the **single source of truth** for: repo layout, commands, verified toolchain, and “good state” checks for Home@ix FAIR Index.

- If anything disagrees with this file, **update this file first**, then fix reality to match.
- Standardize Markdown code fences to ~~~ in this repo.
- PowerShell note: do **not** use `<like-this>` placeholders in runnable commands (PowerShell parses `<` and `>` as redirection).
- **Terminal safety:** Only paste lines inside ~~~powershell fences into PowerShell. Everything else is documentation.

---

## Command sequences must start from repo root (anti-drift)
Every runnable command sequence in this repo must begin by changing directory to **PROJECT_ROOT** (repo root).  
Do not assume the current shell location; drift starts there.

Canonical on owner machine:

~~~powershell
cd "$HOME\OneDrive\Desktop\homeix"
~~~

Sanity checks:

~~~powershell
pwd
git rev-parse --show-toplevel
~~~

Stop if `git rev-parse --show-toplevel` does not resolve to the repo you intend.

---

## 1) Machine + repo ground truth
- Owner machine: Windows (PowerShell 7.x, pwsh)
- Verified on owner machine: PowerShell 7.5.4
- Repo: https://github.com/tonefreqhz/hom-ixFAIRindex
- Branch: `main`
- Repo root (owner machine): `C:\Users\peewe\OneDrive\Desktop\homeix`

### Toolchain verification (must be PowerShell 7.x)
Run these in the repo root to confirm you are using **PowerShell 7.x (pwsh)** and not Windows PowerShell 5.1.

~~~powershell
cd "$HOME\OneDrive\Desktop\homeix"
$PSVersionTable.PSVersion
(Get-Process -Id $PID).Path
~~~

### Repo root must match exactly (anti-drift)
If the folder is suffixed (example: `.old`), rename it back to the canonical root:

~~~powershell
cd "$HOME\OneDrive"
Rename-Item "homeix.old" "homeix"
~~~

---

## Printing / Building the Home@ix publication (reproducible workflow)

This note documents the file structure and the exact commands used to build the publication output that appears under `publication/print_*`. It is intended for repeatability by co-authors, reviewers, and interested readers.

### 1. High-level structure
- `publication/`
  - `print_YYYYMMDD_HHMMSS/`
    A self-contained, timestamped snapshot used for a specific release/print run.
    This folder is what you open/share for review.
    - `index.html`
      The rendered publication output (HTML).
    - `figures/` and/or `outputs/figures/`
      Generated figures used by the publication.
    - `outputs/draft_paper_assets/`, `outputs/fair_assets/`
      Additional generated assets (figures/tables) used in the paper/publication.
    - `_backup_before_stamp_*/`
      Auto-created backups made prior to watermarking/stamping (not used in the build).

### 2. Standard workflow (overview)
1. Generate/refresh figures and publication assets.
2. Create or update a new `publication/print_*` folder for a release.
3. Watermark/stamp figures inside that print folder (so the stamp is part of the artefact).
4. Render/build the publication output (HTML/PDF/etc) from the print folder.
5. Spot-check output visually (figures render, watermark visible on light/dark backgrounds).
6. Commit the notes + (optionally) the print artefact references, then tag a release.

### 3. Commands used (PowerShell)
All commands below are run from the repository root unless stated otherwise.

#### 3.1 Locate the latest print folder
~~~powershell
cd "$HOME\OneDrive\Desktop\homeix"
$root = "$HOME\OneDrive\Desktop\homeix"
$pub = Join-Path $root "publication"
$latestPrint = Get-ChildItem -LiteralPath $pub -Directory -Filter "print_*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestPrint.FullName
~~~

---

### 9.1 FAIR headline level (figure provenance)
**Figure:** Home@ix FAIR: Level  
**Used in:** Section 9.1 (FAIR headline level)

**File referenced by manuscript/publication:**
- `outputs/figures/fig_fair_level.png`

**How it is produced (current workflow):**
- Figure generation and full ebook assembly are orchestrated by: `sweep_up/inbox/assemble_full_ebook.py`
- Path/layout conventions are defined in: `src/paths.py`

**Important:** The orchestrator currently lives under `sweep_up/inbox/`, but the canonical figure location used by the paper is under `outputs/figures/`. Therefore, the build must write final figures to:
- `outputs/figures/` (repo-root relative)

**Build invariant (must hold for reproducibility):**  
Regardless of where the orchestrator script lives, all output paths must be resolved from the repository root — not from the script directory and not from the current working directory.

---

### 🔧 What was broken in your pasted version (and why it mattered)
Two formatting issues caused the document to render incorrectly:

1. **The headings were escaped.**  
   You had `\#` and `\##`, which renders as literal `#` characters instead of headings. That makes the document hard to scan and easy to misread.

2. **The PowerShell code fence was never closed.**  
   The triple-backtick PowerShell block opened and then the text jumped into “9.1 FAIR…” without a closing ~~~ line. Markdown then treats everything after it as code (monospace), which breaks the structure of the note.

---

### 🎯 Key takeaway (the important bit)
The invariant is the point: **everything must resolve from repo root**. The fastest way to prevent regressions is to make the build enforce it (print `PROJECT_ROOT`, fail fast if expected directories aren’t found, and copy assets based on actual references).

---

### 2026-03-01 — Pipeline rebuild: canonical paths + inbox path bugfixes
**What happened**  
The rebuild pipeline failed across multiple steps due to scripts assuming the project root was `sweep_up/inbox` and hard-coding local Windows paths + an old Homeatix filename.

**Fixes applied**  
- Standardized path resolution using:
  - `PROJECT_ROOT = Path(__file__).resolve().parents[2]`
  - Inputs from `inputs/canonical/`
  - Outputs written to `outputs/`
  - Publication bundles under `publication/print_<timestamp>/`
- Updated scripts to stop reading/writing under `sweep_up/inbox/outputs`.

**Files updated (high level)**  
- `sweep_up/inbox/choose_calm_baseline.py`
  - Removed hard-coded `C:\...` paths
  - Reads canonical Homeatix input: `inputs/canonical/homeatix_model.csv`
  - Reads quarterly features from `outputs/features_quarterly.csv`
  - Adds robust “resolve first existing path” behavior
- `sweep_up/inbox/fix_domain_terms.py`
  - Reads `outputs/features_quarterly_with_fair.csv` (not `sweep_up/inbox/outputs/...`)
  - Reads canonical Homeatix input: `inputs/canonical/homeatix_model.csv`
  - Writes `outputs/draft_paper_assets/domain_terms_state1_state2.csv`

**Result**  
Pipeline completes successfully and creates a publication bundle, e.g.: `publication/print_20260301_203942`

---

### 2026-03-02 — Full build workflow: chapters/edits → regenerate figures → assemble print bundle
**Goal**  
Establish a repeatable workflow to:
- edit chapters / draft content
- regenerate all figures + derived assets (full build)
- assemble a self-contained publication bundle under `publication/print_*` for review/printing

**Build invariant (must hold)**  
All canonical paths resolve from **PROJECT_ROOT** (repo root), not from:
- the script directory (`sweep_up/inbox/`)
- the current working directory (CWD)

This prevents accidental reads/writes under `sweep_up/inbox/outputs` and ensures the manuscript references stay valid.

**What we fixed today**  
- Resolved missing Markdown conversion used by the assembler:
  - Added `markdown_to_html(md)` to `sweep_up/inbox/assemble_full_ebook.py`
- Installed the required Python dependency:
  - `markdown` (Python package), so Markdown sections can render into HTML during assembly
- Verified the assembler prints resolved paths at runtime (PROJECT_ROOT, OUTDIR, etc.) to confirm root-based pathing.

**Full build commands (Windows / PowerShell)**  
Run from repository root:

~~~powershell
# One-time environment setup (if needed)
py -m pip install markdown
# Sanity check
py -c "import markdown; print(markdown.__version__)"
# Full build: regenerate exhibits/figures/assets and assemble publication bundle
# (Do NOT pass --no-exhibits)
py .\sweep_up\inbox\assemble_full_ebook.py --outdir .\publication\print_latest
~~~

---

### Print bundle build: path harmonisation (PROJECT_ROOT)
The inbox build scripts are **anchored to the repo root** so they run correctly from any working directory.

- `assemble_full_ebook.py` resolves `PROJECT_ROOT` by walking upward from its own location (`sweep_up/inbox/assemble_full_ebook.py`) and then anchors all canonical paths: `inputs/`, `outputs/`, `build/`, `publication/`.
- Do **not** rely on the current working directory (CWD) for canonical repo paths.
- Quick sanity check:

~~~powershell
py -m py_compile sweep_up/inbox/assemble_full_ebook.py
~~~

---

### 💡 Tiny PowerShell convenience (optional)
Since you already set git pager off for show/diff, a nice “one-liner build” people can copy is:

~~~powershell
py sweep_up/inbox/assemble_full_ebook.py --outdir publication/print_latest
~~~

---

### Build (Windows)
**Prerequisites**  
- Windows 10/11
- Python 3.11+ installed (use the Windows `py` launcher)

**Create the print bundle**  
From PowerShell, run:

~~~powershell
cd path\to\hom-ixFAIRindex\sweep_up\inbox
py .\assemble_full_ebook.py --outdir ..\..\print_test
~~~

---

### 🖨️ Print sequence (current pipeline)
The print workflow is driven by: `.\sweep_up\inbox\rebuild_publish.ps1`  
It performs an end-to-end run that rebuilds outputs, creates a publication bundle, then watermarks figures inside that bundle.

1. **Environment + paths**  
   Sets project root and runs from it.  
   Uses venv Python at: `.\.venv\Scripts\python.exe`  
   Generates a timestamp ($stamp) used to version output folders.

2. **Rebuild (generate fresh outputs)**  
   Recomputes/refreshes the build artifacts needed for publication.  
   Archives previous outputs into: `.\outputs_archive_<stamp>`  
   (keeps old runs out of the way but preserved)

3. **Assemble publication bundle**  
   Creates a versioned print bundle under: `.\publication\print_<stamp>\`  
   Writes/collects all assets required for the “print” output (HTML bundle + assets).  
   Script prints the key paths:  
   Publication bundle: `.\publication\print_<stamp>`  
   Open combined ebook: `...\publication\print_<stamp>\index.html`

4. **Watermark figures (post-processing)**  
   Runs `.\tools\watermark_figures.py` against: `.\publication\print_<stamp>\assets\figures`  
   Scans for PNGs and applies watermarking.  
   Output looks like:  
   Found N PNG files ...  
   [OK] <file>.png for each processed image  
   DONE. when completed successfully

5. **Success criteria (what “good” looks like)**  
   A successful end-to-end run shows:  
   Watermark step ends with DONE.  
   No Python exceptions/tracebacks  
   Bundle path is printed  
   index.html opens and renders correctly

---

### 🧰 Current stage (where we are)
Pipeline runs and completes.  
Watermarking succeeds ([OK] ... + DONE.).  
Pillow emits a DeprecationWarning (noise, not a failure). We temporarily suppressed it via PYTHONWARNINGS=ignore::DeprecationWarning to validate the rest of the pipeline.

---

### 1) Attach / share these two files
Copy  
`C:\Users\peewe\OneDrive\Desktop\homeix\publication\print_latest\index.html`  
`C:\Users\peewe\OneDrive\Desktop\homeix\PRINT_AND_BUILD_NOTES.md`

### 2) Aide‑mémoire (paste into your covering email)
**Home@ix — Draft Package + What’s Needed**  

**Prepared:** 6 March 2026  

**What’s attached**  
Full working book (HTML): publication/print_latest/index.html  
Reproducible build/workflow context: PRINT_AND_BUILD_NOTES.md  
This aide‑mémoire: what’s done + what’s needed  

**What’s done**  
A full working draft is available as a self-contained HTML bundle. Open index.html in a browser; figures render inline.  
The build workflow is reproducible and documented:  
Print bundles live under publication/print_* (with print_latest used as the stable “current” pointer).  
Figures/assets are generated from source data and assembled into the print bundle.  
Watermarking/stamping is applied inside the print bundle as a post-process step.  
Build invariant (for reproducibility): all canonical paths resolve from repo root (PROJECT_ROOT), not from sweep_up/inbox/ and not from the current working directory.  
Recent build hardening (so failures are diagnosable)  
Two small robustness changes were made:  

STOCK_PATH resolution now checks a three-path candidate list (instead of two):  
inputs/canonical/  
repo root  
sweep_up/inbox/  
On failure, the script prints “Searched in:” listing all candidates.

**What’s still needed (in production order)**  
| Item | What’s needed | Notes |  
|------|---------------|-------|  
| Foreword | 400–600 words | Frame the UK housing crisis as a access/allocation regime outcome (not just a shortage story). |  
| Publication blurb | ~150 words | Back-cover/platform description: what it is, who it’s for, why it matters. |  
| Cover design | Title/subtitle/author (+ ISBN placeholder) | Can be minimal; just needs to be consistent and legible. |  
| Reference check | Verify bibliography entries | Cross-check against source documents; fix metadata/links. |  
| Final editorial pass | Comments/track changes | Any format is fine (annotated doc, email notes, Git issues). |  

**How to open/read the draft**  
Open: publication/print_latest/index.html in Chrome or Firefox.  
Allow a few seconds for initial rendering (figures/equations).  
Figures in the print bundle are watermarked for review/traceability.

### 3) Covering note variants (pick one)
**A) Editor / reviewer**  
Attached is the full working draft of Home@ix as a self-contained HTML bundle (publication/print_latest/index.html). It opens in a browser and includes the current figures and equations. The reproducible build/workflow context is in PRINT_AND_BUILD_NOTES.md. I’m looking for editorial feedback and a final pass; foreword + blurb + cover copy/design are still outstanding.

**B) Foreword writer**  
The book argues the UK housing crisis is best understood as a financial regime/access-and-allocation failure, not primarily a shortage narrative. The attached draft is the full working book (open index.html in a browser). I’m looking for a 400–600 word foreword that frames the argument and stakes from your perspective.

**C) Blurb / back-cover copy**  
I need a ~150-word back-cover blurb for Home@ix. It introduces a reproducible, forward-looking affordability indicator and a framework for reading the crisis as a regime outcome. The attached draft is the full working book (open index.html in a browser). I’m looking for copy that would make someone in housing policy/economics/finance pick it up.

**D) Endorser / outside expert**  
Attached is the working draft of Home@ix (open index.html in a browser). The core claim is that affordability exclusion can be diagnosed as a regime outcome visible in transaction structure, mortgage concentration, and credit impairment—beyond conventional price-ratio framing. I’d value your reaction and, if you’re willing, a short endorsement line.

**One-line rebuild command (for collaborators who want to reproduce)**  
From repo root:  
`.\sweep_up\inbox\rebuild_publish.ps1`  
Then open: publication/print_latest/index.html
