# Quick Start — Home@ix FAIR-Index

**hom-ixFAIRindex** is a reproducible research pipeline that generates a FAIR-scored housing-market index for the UK. The outputs — figures, feature tables, and a publication bundle — are generated artefacts. You never edit outputs directly. You run the pipeline from canonical inputs, and the outputs follow.

This guide gets you from a blank terminal to a verified anchor, a built publication bundle, and a confirmed output set. Every path and every command has been verified against a live build.

---

## What You Are Building

The pipeline reads canonical input data from `inputs/canonical/`, runs a sequence of feature-engineering and scoring scripts, writes figures and tables to `outputs/`, and assembles a timestamped publication bundle under `publication/print_<timestamp>/`.

The single source of truth for all paths is `anchor.py`. If you ever lose your bearings, run it first:

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    python anchor.py

You will see something like this:

    [OK] Repo Root    : C:\...\homeix
    [OK] src/paths.py : C:\...\homeix\src\paths.py
    [OK] Orchestrator : C:\...\homeix\sweep_up\inbox\assemble_full_ebook.py
    [OK] Inputs       : C:\...\homeix\inputs\canonical
    [OK] Outputs      : C:\...\homeix\outputs
    [OK] Publication  : C:\...\homeix\publication

All lines must read [OK] before you build. If any read [MISSING], stop and resolve before proceeding.

**This is the W⚓ Protocol: anchor first, build second, never the other way around.**

---

## Prerequisites

Install these once. They do not change between builds.

| Tool   | Version | Install              |
|--------|---------|----------------------|
| Python | 3.12+   | python.org           |
| Pandoc | 3.x     | pandoc.org           |
| Pillow | latest  | pip install pillow   |
| PyYAML | latest  | pip install pyyaml   |

Verify your environment:

    python --version
    pandoc --version

If either command fails, install the missing tool before continuing.

---

## Step 1 — Confirm Your Anchor

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    .\anchor_verify.ps1

Every line must show [OK]. This is not optional. It takes three seconds and it has saved hours.

The final line of the output will read:

    OK  All paths verified. Session is anchored.

Do not proceed until you see that line.

---

## Step 2 — Verify Canonical Inputs

The pipeline reads two canonical input files. Both must be present before any build step:

| File            | Path                                                              |
|-----------------|-------------------------------------------------------------------|
| Homeatix model  | inputs/canonical/homeatix_model.csv                               |
| Dwellings stock | inputs/canonical/dwellings_stock_by_tenure_uk_annual.csv          |

Checksums for both files are held in `inputs/provenance/CHECKSUMS.sha256`. If you have replaced or updated an input file, regenerate the checksums before building.

---

## Step 3 — Run the Pipeline

The full pipeline is orchestrated by a single script:

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    python sweep_up/inbox/assemble_full_ebook.py

This script:

1. Reads canonical inputs from inputs/canonical/
2. Generates feature tables to outputs/
3. Scores FAIR dimensions and writes figures to outputs/figures/
4. Assembles a timestamped publication bundle under publication/print_<timestamp>/

**Build invariant:** all output paths are resolved from the repository root — not from the script directory and not from the current working directory. This is enforced by src/paths.py. Do not override it.

---

## Step 4 — Confirm Outputs

After the pipeline completes, verify the key output artefacts exist:

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    .\anchor_verify.ps1

Check specifically:

| Artefact            | Expected path                                    |
|---------------------|--------------------------------------------------|
| FAIR level figure   | outputs/figures/fig_fair_level.png               |
| FAIR contrib figure | outputs/figures/fig_fair_contrib.png             |
| Feature table       | outputs/features_quarterly.csv                   |
| FAIR feature table  | outputs/features_quarterly_with_fair.csv         |
| Publication bundle  | publication/print_latest/index.html              |

All five must show [OK] in the verify output before the build is considered complete.

---

## Step 5 — Review the Publication Bundle

Open the publication bundle in a browser:

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    Start-Process publication\print_latest\index.html

Check:

- Figures render correctly (light and dark backgrounds)
- FAIR level and contribution figures are present
- Watermark is visible where applied
- No broken image paths

Do not edit files inside publication/print_latest/ directly. If you find an error, fix it in the source scripts or manuscript, then rebuild from Step 3.

---

## The W⚓ Protocol — Emergency Reset

If the build breaks and you cannot identify why, run the three-step reset:

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    .\anchor_verify.ps1

1. **Anchor verify** — confirm all paths [OK]
2. **Check canonical inputs** — confirm both CSV files exist and checksums match
3. **Clear outputs and rebuild** — delete outputs/ contents and rerun assemble_full_ebook.py from Step 3

If all three steps fail to resolve the issue, consult ANCHOR.md at the repo root. It contains the full path registry and the canonical build commands. That file is the manual override.

---

## What Comes Next

This pipeline — **hom-ixFAIRindex** — produces the FAIR-scored housing index that underpins the Home@ix publication series. The canonical build is documented in PRINT_AND_BUILD_NOTES.md. The path registry is in ANCHOR.md. The orchestrator is sweep_up/inbox/assemble_full_ebook.py.

For reviewers: the publication bundle at publication/print_latest/ is the artefact to open. Everything else is the machinery that produced it.

For co-authors: anchor first, build second, never the other way around.

---

*Generated against anchor state: all paths [OK] — 14 March 2026*
