# Home@ix FAIR-Index

**hom-ixFAIRindex** is a reproducible research pipeline that generates a FAIR-scored housing-market index for the UK. Canonical inputs go in, figures and a publication bundle come out. You never edit outputs directly.

For the full step-by-step build guide see [QUICKSTART.md](QUICKSTART.md).

---

## W⚓ Anchor First

Before anything else:

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    .\anchor_verify.ps1

Every line must show [OK]. The final line must read:

    OK  All paths verified. Session is anchored.

Do not build until you see that line. This is the W⚓ Protocol.

---

## Run the Pipeline

    cd "C:\Users\peewe\OneDrive\Desktop\homeix"
    python sweep_up/inbox/assemble_full_ebook.py

That single command:

1. Reads canonical inputs from inputs/canonical/
2. Generates feature tables to outputs/
3. Scores FAIR dimensions and writes figures to outputs/figures/
4. Assembles a timestamped publication bundle under publication/print_<timestamp>/

**Build invariant:** all output paths resolve from the repository root — not from the script directory, not from the current working directory. This is enforced by src/paths.py.

---

## Confirm the Build

    .\anchor_verify.ps1

Then open the publication bundle:

    Start-Process publication\print_latest\index.html

---

## Repo Structure

    homeix/
    ├── ANCHOR.md                        # Path registry and canonical build commands
    ├── QUICKSTART.md                    # Step-by-step build guide
    ├── anchor.py                        # Python anchor check
    ├── anchor_verify.ps1                # PowerShell anchor gate (run this first)
    ├── src/
    │   └── paths.py                     # Single source of truth for all paths
    ├── inputs/
    │   ├── canonical/                   # Canonical input data (never edited)
    │   │   ├── homeatix_model.csv
    │   │   └── dwellings_stock_by_tenure_uk_annual.csv
    │   └── provenance/
    │       └── CHECKSUMS.sha256
    ├── outputs/
    │   ├── figures/                     # Generated figures
    │   ├── features_quarterly.csv
    │   ├── features_quarterly_with_fair.csv
    │   └── fair_assets/
    ├── publication/
    │   └── print_latest/
    │       └── index.html               # Open this for review
    ├── assets/
    │   ├── cover/
    │   └── branding/
    └── sweep_up/
        └── inbox/
            └── assemble_full_ebook.py   # Orchestrator — entry point for all builds

---

## Key Invariants

- **Inputs** are read-only. Never edit files under inputs/canonical/.
- **Outputs** are generated artefacts. Never edit files under outputs/ or publication/print_*/ directly.
- **Paths** always resolve from repo root. src/paths.py enforces this.
- **Checksums** in inputs/provenance/CHECKSUMS.sha256 must match before a build is considered reproducible.

---

## For Reviewers

The artefact to open is:

    publication/print_latest/index.html

Everything else is the machinery that produced it.

---

## Build History

| Date       | Notes |
|------------|-------|
| 2026-03-01 | Pipeline rebuild — canonical paths enforced, inbox path bugfixes, PROJECT_ROOT standardised across all scripts |
| 2026-03-14 | QUICKSTART.md added, README rewritten, W⚓ Protocol documented |

---

*Generated against anchor state: all paths [OK] — 14 March 2026*




