from __future__ import annotations

from pathlib import Path
import shutil

PROJECT = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix")
ARCHIVE = Path(r"C:\Users\peewe\OneDrive\Desktop\homeix\outputs_archive_20260226_205052")

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"[skip] missing: {src}")
        return
    ensure_dir(dst)
    # Python 3.8+: dirs_exist_ok supported (your environment likely is)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    print(f"[ok] synced tree: {src} -> {dst}")

def latest_figures_run(fig_runs: Path) -> Path | None:
    if not fig_runs.exists():
        return None
    runs = [p for p in fig_runs.iterdir() if p.is_dir()]
    if not runs:
        return None
    # folders are timestamped so lexical sort works, but use mtime as backup
    runs.sort(key=lambda p: (p.name, p.stat().st_mtime), reverse=True)
    return runs[0]

def copy_glob(src_dir: Path, pattern: str, dst_dir: Path) -> int:
    ensure_dir(dst_dir)
    n = 0
    for f in src_dir.glob(pattern):
        if f.is_file():
            shutil.copy2(f, dst_dir / f.name)
            n += 1
    return n

def main() -> None:
    if not PROJECT.exists():
        raise SystemExit(f"Project root not found: {PROJECT}")
    if not ARCHIVE.exists():
        raise SystemExit(f"Archive root not found: {ARCHIVE}")

    ensure_dir(ARCHIVE / "figures")
    ensure_dir(ARCHIVE / "gifs")

    # 1) Latest figures_runs -> archive/{figures,gifs}
    fig_runs = PROJECT / "outputs" / "figures_runs"
    latest = latest_figures_run(fig_runs)
    if latest is None:
        print(f"[skip] no figures runs found under: {fig_runs}")
    else:
        pngs = copy_glob(latest, "*.png", ARCHIVE / "figures")
        gifs = copy_glob(latest, "*.gif", ARCHIVE / "gifs")
        print(f"[ok] latest figures run: {latest.name}  (png={pngs}, gif={gifs})")

    # 2) outputs/fair_assets -> archive/fair_assets
    copy_tree(PROJECT / "outputs" / "fair_assets", ARCHIVE / "fair_assets")

    # 3) outputs/draft_paper_assets -> archive/draft_paper_assets
    copy_tree(PROJECT / "outputs" / "draft_paper_assets", ARCHIVE / "draft_paper_assets")

    print("[done] sync complete")

if __name__ == "__main__":
    main()
