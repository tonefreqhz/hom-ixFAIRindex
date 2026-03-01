# Printing / Building the Home@ix publication (reproducible workflow)

This note documents the file structure and the exact commands used to build the publication
output that appears under `publication/print_*`. It is intended for repeatability by
co-authors, reviewers, and interested readers.

## 1. High-level structure

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

## 2. Standard workflow (overview)

1. Generate/refresh figures and publication assets.
2. Create or update a new `publication/print_*` folder for a release.
3. Watermark/stamp figures inside that print folder (so the stamp is part of the artefact).
4. Render/build the publication output (HTML/PDF/etc) from the print folder.
5. Spot-check output visually (figures render, watermark visible on light/dark backgrounds).
6. Commit the notes + (optionally) the print artefact references, then tag a release.

## 3. Commands used (PowerShell)

All commands below are run from the repository root unless stated otherwise.

### 3.1 Locate the latest print folder

```powershell
$root = "C:\Users\peewe\OneDrive\Desktop\homeix"
$pub  = Join-Path $root "publication"

$latestPrint = Get-ChildItem -LiteralPath $pub -Directory -Filter "print_*" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

$latestPrint.FullName
```

---

## 9.1 FAIR headline level (figure provenance)

**Figure:** Home@ix FAIR: Level  
**Used in:** Section 9.1 (FAIR headline level)

**File referenced by manuscript/publication:**
- `outputs/figures/fig_fair_level.png`

**How it is produced (current workflow):**
- Figure generation and full ebook assembly are orchestrated by: `sweep_up/inbox/assemble_full_ebook.py`
- Path/layout conventions are defined in: `src/paths.py`

**Important:** The orchestrator currently lives under `sweep_up/inbox/`, but the canonical
figure location used by the paper is under `outputs/figures/`. Therefore, the build must
write final figures to:
- `outputs/figures/` (repo-root relative)

**Build invariant (must hold for reproducibility):**  
Regardless of where the orchestrator script lives, all output paths must be resolved from
the repository root — not from the script directory and not from the current working
directory.

---

## 🔧 What was broken in your pasted version (and why it mattered)

Two formatting issues caused the document to render incorrectly:

1. **The headings were escaped.**  
   You had `\#` and `\##`, which renders as literal `#` characters instead of headings. That
   makes the document hard to scan and easy to misread.

2. **The PowerShell code fence was never closed.**  
   The triple-backtick PowerShell block opened and then the text jumped into “9.1 FAIR…”
   without a closing ``` line. Markdown then treats everything after it as code (monospace),
   which breaks the structure of the note.

---

## 🎯 Key takeaway (the important bit)

The invariant is the point: **everything must resolve from repo root**. The fastest way to
prevent regressions is to make the build enforce it (print `PROJECT_ROOT`, fail fast if
expected directories aren’t found, and copy assets based on actual references).
## 2026-03-01 — Pipeline rebuild: canonical paths + inbox path bugfixes

### What happened
The rebuild pipeline failed across multiple steps due to scripts assuming the project root was `sweep_up/inbox`
and hard-coding local Windows paths + an old Homeatix filename.

### Fixes applied
- Standardized path resolution using:
  - `PROJECT_ROOT = Path(__file__).resolve().parents[2]`
  - Inputs from `inputs/canonical/`
  - Outputs written to `outputs/`
  - Publication bundles under `publication/print_<timestamp>/`
- Updated scripts to stop reading/writing under `sweep_up/inbox/outputs`.

### Files updated (high level)
- `sweep_up/inbox/choose_calm_baseline.py`
  - Removed hard-coded `C:\...` paths
  - Reads canonical Homeatix input: `inputs/canonical/homeatix_model.csv`
  - Reads quarterly features from `outputs/features_quarterly.csv`
  - Adds robust “resolve first existing path” behavior
- `sweep_up/inbox/fix_domain_terms.py`
  - Reads `outputs/features_quarterly_with_fair.csv` (not `sweep_up/inbox/outputs/...`)
  - Reads canonical Homeatix input: `inputs/canonical/homeatix_model.csv`
  - Writes `outputs/draft_paper_assets/domain_terms_state1_state2.csv`

### Result
Pipeline completes successfully and creates a publication bundle, e.g.:
`publication/print_20260301_203942`

