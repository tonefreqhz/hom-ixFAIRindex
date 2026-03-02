#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from pathlib import Path

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s or "section"

SECTION_MD_TEMPLATE = """# {title}

> Created: {created}

## Purpose
Write what this section is for.

## Key points
- Point 1
- Point 2

## Figures
- Put figures in: {fig_dir}

## Notes
- Draft notes here.
"""

INDEX_MD_TEMPLATE = """# {title}

- Source: `section.md`
- Assets: `assets/`

## Build notes
- Add this section to the assembly list (wherever your build enumerates sections).
"""

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Create a new section scaffold (markdown + assets dirs)."
    )
    ap.add_argument("title", help="Human title, e.g. 'Housing supply constraints'")
    ap.add_argument(
        "--root",
        default=".",
        help="Repo root (default: current directory)"
    )
    ap.add_argument(
        "--dir",
        default="sections",
        help="Base directory to create sections under (default: sections/)"
    )
    ap.add_argument(
        "--slug",
        default=None,
        help="Override auto-slug (default: slugified title)"
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    base = root / args.dir
    slug = args.slug or slugify(args.title)

    section_dir = base / slug
    assets_dir = section_dir / "assets"
    fig_dir = assets_dir / "figures"
    data_dir = assets_dir / "data"

    created = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Create dirs
    for d in (section_dir, assets_dir, fig_dir, data_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Create files (do not overwrite)
    files = {
        section_dir / "section.md": SECTION_MD_TEMPLATE.format(
            title=args.title, created=created, fig_dir=str(fig_dir.relative_to(root))
        ),
        section_dir / "index.md": INDEX_MD_TEMPLATE.format(title=args.title),
        section_dir / "README.md": f"# {args.title}\n\nScaffold for section `{slug}`.\n",
    }

    created_paths = []
    for path, content in files.items():
        if path.exists():
            continue
        path.write_text(content, encoding="utf-8")
        created_paths.append(path)

    print(f"[OK] Section scaffold ready: {section_dir.relative_to(root)}")
    if created_paths:
        print("[OK] Created files:")
        for p in created_paths:
            print(f"  - {p.relative_to(root)}")
    else:
        print("[WARN] No files created (they already exist).")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
