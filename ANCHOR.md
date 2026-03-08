# W⚓ Anchor — Home@ix FAIR Index

This file satisfies the `src/paths.py` root validator.

## Protocol
- Path registry: `src/paths.py` (canonical for pipeline scripts)
- Build anchor: `anchor.py` (DoughForge W⚓ protocol — covers, outputs, Pandoc commands)
- These two files are complementary, not duplicates.

## Repo relationships
- Template: https://github.com/tonefreqhz/reproducible-self-pub-kit
- Book build: https://github.com/tonefreqhz/DoughForge
- FAIR Index paper: https://github.com/tonefreqhz/hom-ixFAIRindex

## Build entry points
- Stage 1 (data): `sweep_up/inbox/assemble_full_ebook.py`
- Stage 2 (publication): `publication/print_<timestamp>/`
- Path verification: `python src/paths.py` or `python anchor.py`
