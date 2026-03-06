cd "C:\\Users\\peewe\\OneDrive\\Desktop\\homeix"

\# Replace the file with the cleaned version

Set-Content -Path "PRINT\_AND\_BUILD\_NOTES.md" -Value @"

\# Reproducible Self‑Pub Kit — Anchor (Ground Truth for Home@ix FAIR Index)



> This repo exists because \*\*drift is the default\*\*—and reproducibility is a feature you have to build on purpose.

> Anchored to prevent LLM hallucinations in math-heavy property market analysis (Gödel/Tarski-inspired external observation).



Last updated: 2026-03-06  

Owner machine: Windows (PowerShell 7.x, pwsh)  

Verified on owner machine: PowerShell 7.5.4  

Repo: https://github.com/tonefreqhz/hom-ixFAIRindex  

Branch: main



---



\## 0) What this file is (and is not)

This ANCHOR is the \*\*single source of truth\*\* for: repo layout, commands, verified toolchain, and “good state” checks for Home@ix FAIR Index.



\- If anything disagrees with this file, \*\*update this file first\*\*, then fix reality to match.

\- Standardize Markdown code fences to ~~~ in this repo.

\- PowerShell note: do \*\*not\*\* use `<like-this>` placeholders in runnable commands (PowerShell parses `<` and `>` as redirection).

\- \*\*Terminal safety:\*\* Only paste lines inside ~~~powershell fences into PowerShell. Everything else is documentation.



---



\## Command sequences must start from repo root (anti-drift)

Every runnable command sequence in this repo must begin by changing directory to \*\*PROJECT\_ROOT\*\* (repo root).  

Do not assume the current shell location; drift starts there.



Canonical on owner machine:



~~~powershell

cd "$HOME\\OneDrive\\Desktop\\homeix"

~~~



Sanity checks:



~~~powershell

pwd

git rev-parse --show-toplevel

~~~



Stop if `git rev-parse --show-toplevel` does not resolve to the repo you intend.



---



\## 1) Machine + repo ground truth

\- Owner machine: Windows (PowerShell 7.x, pwsh)

\- Verified on owner machine: PowerShell 7.5.4

\- Repo: https://github.com/tonefreqhz/hom-ixFAIRindex

\- Branch: `main`

\- Repo root (owner machine): `C:\\Users\\peewe\\OneDrive\\Desktop\\homeix`



\### Toolchain verification (must be PowerShell 7.x)

Run these in the repo root to confirm you are using \*\*PowerShell 7.x (pwsh)\*\* and not Windows PowerShell 5.1.



~~~powershell

cd "$HOME\\OneDrive\\Desktop\\homeix"

$PSVersionTable.PSVersion

(Get-Process -Id $PID).Path

~~~



\### Repo root must match exactly (anti-drift)

If the folder is suffixed (example: `.old`), rename it back to the canonical root:



~~~powershell

cd "$HOME\\OneDrive"

Rename-Item "homeix.old" "homeix"

~~~



---



\## Printing / Building the Home@ix publication (reproducible workflow)



This note documents the file structure and the exact commands used to build the publication output that appears under `publication/print\_\*`. It is intended for repeatability by co-authors, reviewers, and interested readers.



\### 1. High-level structure

\- `publication/`

&nbsp; - `print\_YYYYMMDD\_HHMMSS/`

&nbsp;   A self-contained, timestamped snapshot used for a specific release/print run.

&nbsp;   This folder is what you open/share for review.

&nbsp;   - `index.html`

&nbsp;     The rendered publication output (HTML).

&nbsp;   - `figures/` and/or `outputs/figures/`

&nbsp;     Generated figures used by the publication.

&nbsp;   - `outputs/draft\_paper\_assets/`, `outputs/fair\_assets/`

&nbsp;     Additional generated assets (figures/tables) used in the paper/publication.

&nbsp;   - `\_backup\_before\_stamp\_\*/`

&nbsp;     Auto-created backups made prior to watermarking/stamping (not used in the build).



\### 2. Standard workflow (overview)

1\. Generate/refresh figures and publication assets.

2\. Create or update a new `publication/print\_\*` folder for a release.

3\. Watermark/stamp figures inside that print folder (so the stamp is part of the artefact).

4\. Render/build the publication output (HTML/PDF/etc) from the print folder.

5\. Spot-check output visually (figures render, watermark visible on light/dark backgrounds).

6\. Commit the notes + (optionally) the print artefact references, then tag a release.



\### 3. Commands used (PowerShell)

All commands below are run from the repository root unless stated otherwise.



\#### 3.1 Locate the latest print folder

~~~powershell

cd "$HOME\\OneDrive\\Desktop\\homeix"

$root = "$HOME\\OneDrive\\Desktop\\homeix"

$pub = Join-Path $root "publication"

$latestPrint = Get-ChildItem -LiteralPath $pub -Directory -Filter "print\_\*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

$latestPrint.FullName

~~~



---



\### 9.1 FAIR headline level (figure provenance)

\*\*Figure:\*\* Home@ix FAIR: Level  

\*\*Used in:\*\* Section 9.1 (FAIR headline level)



\*\*File referenced by manuscript/publication:\*\*

\- `outputs/figures/fig\_fair\_level.png`



\*\*How it is produced (current workflow):\*\*

\- Figure generation and full ebook assembly are orchestrated by: `sweep\_up/inbox/assemble\_full\_ebook.py`

\- Path/layout conventions are defined in: `src/paths.py`



\*\*Important:\*\* The orchestrator currently lives under `sweep\_up/inbox/`, but the canonical figure location used by the paper is under `outputs/figures/`. Therefore, the build must write final figures to:

\- `outputs/figures/` (repo-root relative)



\*\*Build invariant (must hold for reproducibility):\*\*  

Regardless of where the orchestrator script lives, all output paths must be resolved from the repository root — not from the script directory and not from the current working directory.



---



\### 🔧 What was broken in your pasted version (and why it mattered)

Two formatting issues caused the document to render incorrectly:



1\. \*\*The headings were escaped.\*\*  

&nbsp;  You had `\\#` and `\\##`, which renders as literal `#` characters instead of headings. That makes the document hard to scan and easy to misread.



2\. \*\*The PowerShell code fence was never closed.\*\*  

&nbsp;  The triple-backtick PowerShell block opened and then the text jumped into “9.1 FAIR…” without a closing ~~~ line. Markdown then treats everything after it as code (monospace), which breaks the structure of the note.



---



\### 🎯 Key takeaway (the important bit)

The invariant is the point: \*\*everything must resolve from repo root\*\*. The fastest way to prevent regressions is to make the build enforce it (print `PROJECT\_ROOT`, fail fast if expected directories aren’t found, and copy assets based on actual references).



---



\### 2026-03-01 — Pipeline rebuild: canonical paths + inbox path bugfixes

\*\*What happened\*\*  

The rebuild pipeline failed across multiple steps due to scripts assuming the project root was `sweep\_up/inbox` and hard-coding local Windows paths + an old Homeatix filename.



\*\*Fixes applied\*\*  

\- Standardized path resolution using:

&nbsp; - `PROJECT\_ROOT = Path(\_\_file\_\_).resolve().parents\[2]`

&nbsp; - Inputs from `inputs/canonical/`

&nbsp; - Outputs written to `outputs/`

&nbsp; - Publication bundles under `publication/print\_<timestamp>/`

\- Updated scripts to stop reading/writing under `sweep\_up/inbox/outputs`.



\*\*Files updated (high level)\*\*  

\- `sweep\_up/inbox/choose\_calm\_baseline.py`

&nbsp; - Removed hard-coded `C:\\...` paths

&nbsp; - Reads canonical Homeatix input: `inputs/canonical/homeatix\_model.csv`

&nbsp; - Reads quarterly features from `outputs/features\_quarterly.csv`

&nbsp; - Adds robust “resolve first existing path” behavior

\- `sweep\_up/inbox/fix\_domain\_terms.py`

&nbsp; - Reads `outputs/features\_quarterly\_with\_fair.csv` (not `sweep\_up/inbox/outputs/...`)

&nbsp; - Reads canonical Homeatix input: `inputs/canonical/homeatix\_model.csv`

&nbsp; - Writes `outputs/draft\_paper\_assets/domain\_terms\_state1\_state2.csv`



\*\*Result\*\*  

Pipeline completes successfully and creates a publication bundle, e.g.: `publication/print\_20260301\_203942`



---



\### 2026-03-02 — Full build workflow: chapters/edits → regenerate figures → assemble print bundle

\*\*Goal\*\*  

Establish a repeatable workflow to:

\- edit chapters / draft content

\- regenerate all figures + derived assets (full build)

\- assemble a self-contained publication bundle under `publication/print\_\*` for review/printing



\*\*Build invariant (must hold)\*\*  

All canonical paths resolve from \*\*PROJECT\_ROOT\*\* (repo root), not from:

\- the script directory (`sweep\_up/inbox/`)

\- the current working directory (CWD)



This prevents accidental reads/writes under `sweep\_up/inbox/outputs` and ensures the manuscript references stay valid.



\*\*What we fixed today\*\*  

\- Resolved missing Markdown conversion used by the assembler:

&nbsp; - Added `markdown\_to\_html(md)` to `sweep\_up/inbox/assemble\_full\_ebook.py`

\- Installed the required Python dependency:

&nbsp; - `markdown` (Python package), so Markdown sections can render into HTML during assembly

\- Verified the assembler prints resolved paths at runtime (PROJECT\_ROOT, OUTDIR, etc.) to confirm root-based pathing.



\*\*Full build commands (Windows / PowerShell)\*\*  

Run from repository root:



~~~powershell

\# One-time environment setup (if needed)

py -m pip install markdown

\# Sanity check

py -c "import markdown; print(markdown.\_\_version\_\_)"

\# Full build: regenerate exhibits/figures/assets and assemble publication bundle

\# (Do NOT pass --no-exhibits)

py .\\sweep\_up\\inbox\\assemble\_full\_ebook.py --outdir .\\publication\\print\_latest

~~~



---



\### Print bundle build: path harmonisation (PROJECT\_ROOT)

The inbox build scripts are \*\*anchored to the repo root\*\* so they run correctly from any working directory.



\- `assemble\_full\_ebook.py` resolves `PROJECT\_ROOT` by walking upward from its own location (`sweep\_up/inbox/assemble\_full\_ebook.py`) and then anchors all canonical paths: `inputs/`, `outputs/`, `build/`, `publication/`.

\- Do \*\*not\*\* rely on the current working directory (CWD) for canonical repo paths.

\- Quick sanity check:



~~~powershell

py -m py\_compile sweep\_up/inbox/assemble\_full\_ebook.py

~~~



---



\### 💡 Tiny PowerShell convenience (optional)

Since you already set git pager off for show/diff, a nice “one-liner build” people can copy is:



~~~powershell

py sweep\_up/inbox/assemble\_full\_ebook.py --outdir publication/print\_latest

~~~



---



\### Build (Windows)

\*\*Prerequisites\*\*  

\- Windows 10/11

\- Python 3.11+ installed (use the Windows `py` launcher)



\*\*Create the print bundle\*\*  

From PowerShell, run:



~~~powershell

cd path\\to\\hom-ixFAIRindex\\sweep\_up\\inbox

py .\\assemble\_full\_ebook.py --outdir ..\\..\\print\_test

~~~



---



\### 🖨️ Print sequence (current pipeline)

The print workflow is driven by: `.\\sweep\_up\\inbox\\rebuild\_publish.ps1`  

It performs an end-to-end run that rebuilds outputs, creates a publication bundle, then watermarks figures inside that bundle.



1\. \*\*Environment + paths\*\*  

&nbsp;  Sets project root and runs from it.  

&nbsp;  Uses venv Python at: `.\\.venv\\Scripts\\python.exe`  

&nbsp;  Generates a timestamp ($stamp) used to version output folders.



2\. \*\*Rebuild (generate fresh outputs)\*\*  

&nbsp;  Recomputes/refreshes the build artifacts needed for publication.  

&nbsp;  Archives previous outputs into: `.\\outputs\_archive\_<stamp>`  

&nbsp;  (keeps old runs out of the way but preserved)



3\. \*\*Assemble publication bundle\*\*  

&nbsp;  Creates a versioned print bundle under: `.\\publication\\print\_<stamp>\\`  

&nbsp;  Writes/collects all assets required for the “print” output (HTML bundle + assets).  

&nbsp;  Script prints the key paths:  

&nbsp;  Publication bundle: `.\\publication\\print\_<stamp>`  

&nbsp;  Open combined ebook: `...\\publication\\print\_<stamp>\\index.html`



4\. \*\*Watermark figures (post-processing)\*\*  

&nbsp;  Runs `.\\tools\\watermark\_figures.py` against: `.\\publication\\print\_<stamp>\\assets\\figures`  

&nbsp;  Scans for PNGs and applies watermarking.  

&nbsp;  Output looks like:  

&nbsp;  Found N PNG files ...  

&nbsp;  \[OK] <file>.png for each processed image  

&nbsp;  DONE. when completed successfully



5\. \*\*Success criteria (what “good” looks like)\*\*  

&nbsp;  A successful end-to-end run shows:  

&nbsp;  Watermark step ends with DONE.  

&nbsp;  No Python exceptions/tracebacks  

&nbsp;  Bundle path is printed  

&nbsp;  index.html opens and renders correctly



---



\### 🧰 Current stage (where we are)

Pipeline runs and completes.  

Watermarking succeeds (\[OK] ... + DONE.).  

Pillow emits a DeprecationWarning (noise, not a failure). We temporarily suppressed it via PYTHONWARNINGS=ignore::DeprecationWarning to validate the rest of the pipeline.



---



\### 1) Attach / share these two files

Copy  

`C:\\Users\\peewe\\OneDrive\\Desktop\\homeix\\publication\\print\_latest\\index.html`  

`C:\\Users\\peewe\\OneDrive\\Desktop\\homeix\\PRINT\_AND\_BUILD\_NOTES.md`



\### 2) Aide‑mémoire (paste into your covering email)

\*\*Home@ix — Draft Package + What’s Needed\*\*  



\*\*Prepared:\*\* 6 March 2026  



\*\*What’s attached\*\*  

Full working book (HTML): publication/print\_latest/index.html  

Reproducible build/workflow context: PRINT\_AND\_BUILD\_NOTES.md  

This aide‑mémoire: what’s done + what’s needed  



\*\*What’s done\*\*  

A full working draft is available as a self-contained HTML bundle. Open index.html in a browser; figures render inline.  

The build workflow is reproducible and documented:  

Print bundles live under publication/print\_\* (with print\_latest used as the stable “current” pointer).  

Figures/assets are generated from source data and assembled into the print bundle.  

Watermarking/stamping is applied inside the print bundle as a post-process step.  

Build invariant (for reproducibility): all canonical paths resolve from repo root (PROJECT\_ROOT), not from sweep\_up/inbox/ and not from the current working directory.  

Recent build hardening (so failures are diagnosable)  

Two small robustness changes were made:  



STOCK\_PATH resolution now checks a three-path candidate list (instead of two):  

inputs/canonical/  

repo root  

sweep\_up/inbox/  

On failure, the script prints “Searched in:” listing all candidates.



\*\*What’s still needed (in production order)\*\*  

| Item | What’s needed | Notes |  

|------|---------------|-------|  

| Foreword | 400–600 words | Frame the UK housing crisis as a access/allocation regime outcome (not just a shortage story). |  

| Publication blurb | ~150 words | Back-cover/platform description: what it is, who it’s for, why it matters. |  

| Cover design | Title/subtitle/author (+ ISBN placeholder) | Can be minimal; just needs to be consistent and legible. |  

| Reference check | Verify bibliography entries | Cross-check against source documents; fix metadata/links. |  

| Final editorial pass | Comments/track changes | Any format is fine (annotated doc, email notes, Git issues). |  



\*\*How to open/read the draft\*\*  

Open: publication/print\_latest/index.html in Chrome or Firefox.  

Allow a few seconds for initial rendering (figures/equations).  

Figures in the print bundle are watermarked for review/traceability.



\### 3) Covering note variants (pick one)

\*\*A) Editor / reviewer\*\*  

Attached is the full working draft of Home@ix as a self-contained HTML bundle (publication/print\_latest/index.html). It opens in a browser and includes the current figures and equations. The reproducible build/workflow context is in PRINT\_AND\_BUILD\_NOTES.md. I’m looking for editorial feedback and a final pass; foreword + blurb + cover copy/design are still outstanding.



\*\*B) Foreword writer\*\*  

The book argues the UK housing crisis is best understood as a financial regime/access-and-allocation failure, not primarily a shortage narrative. The attached draft is the full working book (open index.html in a browser). I’m looking for a 400–600 word foreword that frames the argument and stakes from your perspective.



\*\*C) Blurb / back-cover copy\*\*  

I need a ~150-word back-cover blurb for Home@ix. It introduces a reproducible, forward-looking affordability indicator and a framework for reading the crisis as a regime outcome. The attached draft is the full working book (open index.html in a browser). I’m looking for copy that would make someone in housing policy/economics/finance pick it up.



\*\*D) Endorser / outside expert\*\*  

Attached is the working draft of Home@ix (open index.html in a browser). The core claim is that affordability exclusion can be diagnosed as a regime outcome visible in transaction structure, mortgage concentration, and credit impairment—beyond conventional price-ratio framing. I’d value your reaction and, if you’re willing, a short endorsement line.



\*\*One-line rebuild command (for collaborators who want to reproduce)\*\*  

From repo root:  

`.\\sweep\_up\\inbox\\rebuild\_publish.ps1`  

Then open: publication/print\_latest/index.html

"@

Write-Host "Conformed PRINT\_AND\_BUILD\_NOTES.md for homeix."



