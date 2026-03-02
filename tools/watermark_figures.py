import argparse
import os
from pathlib import Path
from PIL import Image, ImageEnhance

PNG_EXT = {".png"}

def load_rgba(path: Path) -> Image.Image:
    im = Image.open(path)
    return im.convert("RGBA")

def set_opacity(im: Image.Image, opacity: float) -> Image.Image:
    """opacity: 0..1"""
    if opacity >= 1:
        return im
    if opacity <= 0:
        out = im.copy()
        out.putalpha(0)
        return out
    r, g, b, a = im.split()
    a = ImageEnhance.Brightness(a).enhance(opacity)
    out = Image.merge("RGBA", (r, g, b, a))
    return out

def paste_with_margin(base: Image.Image, overlay: Image.Image, corner: str, margin_px: int):
    bw, bh = base.size
    ow, oh = overlay.size

    if corner == "tl":
        x, y = margin_px, margin_px
    elif corner == "tr":
        x, y = bw - ow - margin_px, margin_px
    elif corner == "bl":
        x, y = margin_px, bh - oh - margin_px
    elif corner == "br":
        x, y = bw - ow - margin_px, bh - oh - margin_px
    else:
        raise ValueError("corner must be one of: tl,tr,bl,br")

    base.alpha_composite(overlay, dest=(x, y))

def make_tm_badge(color=(0, 180, 120, 255), scale_px=64) -> Image.Image:
    """
    Simple 'TM' badge without relying on fonts installed.
    We draw a tiny badge by rasterizing from an embedded image approach would be better,
    but this minimal approach uses Pillow's default bitmap font.
    """
    from PIL import ImageDraw, ImageFont

    # badge canvas
    pad = int(scale_px * 0.25)
    w = scale_px + 2 * pad
    h = scale_px + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # rounded rect background (transparent-ish)
    bg = (0, 0, 0, 0)
    # outline
    outline = color
    draw.rounded_rectangle([1, 1, w - 2, h - 2], radius=int(scale_px * 0.25), fill=bg, outline=outline, width=max(2, scale_px // 18))

    # text
    try:
        font = ImageFont.truetype("arial.ttf", int(scale_px * 0.6))
    except:
        font = ImageFont.load_default()

    text = "TM"
    tw, th = draw.textbbox((0, 0), text, font=font)[2:]
    tx = (w - tw) // 2
    ty = (h - th) // 2
    draw.text((tx, ty), text, font=font, fill=color)
    return im

def stamp_one(path: Path, logo_col: Path, logo_white: Path | None,
              logo_corner: str, tm_corner: str,
              logo_frac: float, tm_frac: float,
              logo_opacity: float, tm_opacity: float,
              margin_frac: float, use_white_on_dark: bool):

    base = load_rgba(path)
    bw, bh = base.size
    margin_px = int(min(bw, bh) * margin_frac)

    # Choose logo: coloured by default; optionally switch to white if image is "dark".
    logo_path = logo_col
    if use_white_on_dark and logo_white is not None:
        # very lightweight darkness heuristic (sample a small region)
        sample = base.resize((64, 64)).convert("RGB")
        pixels = list(sample.getdata())

        avg = sum((p[0] + p[1] + p[2]) for p in pixels) / (len(pixels) * 3)
        if avg < 90:  # dark background -> white logo reads better
            logo_path = logo_white

    logo = load_rgba(logo_path)
    # scale logo to fraction of min dimension
    target_logo_w = int(min(bw, bh) * logo_frac)
    logo = logo.resize((target_logo_w, int(target_logo_w * logo.size[1] / logo.size[0])), Image.LANCZOS)
    logo = set_opacity(logo, logo_opacity)

    # TM badge color sampled from logo (roughly) or set fixed
    # We'll just use a Home@ix-ish teal/green; tweak if you have brand RGB.
    tm_color = (0, 180, 120, 255)
    tm_size = int(min(bw, bh) * tm_frac)
    tm = make_tm_badge(color=tm_color, scale_px=tm_size)
    tm = set_opacity(tm, tm_opacity)

    out = base.copy()
    paste_with_margin(out, logo, logo_corner, margin_px)
    paste_with_margin(out, tm, tm_corner, margin_px)

    # Save back as PNG (keep alpha if present)
    out.save(path, format="PNG")

def iter_pngs(root: Path):
    for p in root.rglob("*"):
        if p.suffix.lower() in PNG_EXT and p.is_file():
            yield p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Folder containing figures (will recurse).")
    ap.add_argument("--logo_col", required=True, help="Coloured logo/icon PNG path.")
    ap.add_argument("--logo_white", default="", help="White logo PNG path (optional).")
    ap.add_argument("--logo_corner", default="tr", choices=["tl","tr","bl","br"])
    ap.add_argument("--tm_corner", default="br", choices=["tl","tr","bl","br"])
    ap.add_argument("--logo_frac", type=float, default=0.10, help="Logo width as fraction of min(image_w,image_h).")
    ap.add_argument("--tm_frac", type=float, default=0.05, help="TM badge size as fraction of min dimension.")
    ap.add_argument("--logo_opacity", type=float, default=0.22)
    ap.add_argument("--tm_opacity", type=float, default=0.40)
    ap.add_argument("--margin_frac", type=float, default=0.02)
    ap.add_argument("--use_white_on_dark", action="store_true")
    ap.add_argument("--dry_run", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    logo_col = Path(args.logo_col)
    logo_white = Path(args.logo_white) if args.logo_white else None

    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")
    if not logo_col.exists():
        raise SystemExit(f"Missing logo_col: {logo_col}")
    if logo_white is not None and not logo_white.exists():
        raise SystemExit(f"Missing logo_white: {logo_white}")

    paths = list(iter_pngs(root))
    print(f"Found {len(paths)} PNG files under {root}")

    for p in paths:
        # avoid watermarking the logo assets themselves if they live under root
        if p.resolve() in {logo_col.resolve()} or (logo_white and p.resolve() == logo_white.resolve()):
            continue

        if args.dry_run:
            print(f"[DRY] would stamp: {p}")
            continue

        try:
            stamp_one(
                p, logo_col, logo_white,
                args.logo_corner, args.tm_corner,
                args.logo_frac, args.tm_frac,
                args.logo_opacity, args.tm_opacity,
                args.margin_frac, args.use_white_on_dark
            )
            print(f"[OK] {p}")
        except Exception as e:
            print(f"[FAIL] {p} :: {e}")

if __name__ == "__main__":
    main()
