import pathlib, re, shutil, base64

src = pathlib.Path('publication/print_latest/index_prepped.html')
out = pathlib.Path('publication/print_latest/index_final.html')

text = src.read_text(encoding='utf-8')

# Fix any remaining mojibake
text = text.replace('ÔÇö', '\u2014')
text = text.replace('┬®', '\u00a9')

# Inline ALL images as base64 so Calibre never loses them
def inline_img(m):
    attr  = m.group(0)
    src_m = re.search(r'src=["\']([^"\']+)["\']', attr)
    if not src_m:
        return attr
    img_path = src_m.group(1)
    # resolve relative to the HTML file location
    full = pathlib.Path('publication/print_latest') / img_path
    if not full.exists():
        # try outputs/figures/
        name = pathlib.Path(img_path).name
        full = pathlib.Path('outputs/figures') / name
    if not full.exists():
        print(f'  [WARN] image not found: {img_path}')
        return attr
    ext = full.suffix.lstrip('.').lower()
    mime = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg',
            'gif':'image/gif','svg':'image/svg+xml'}.get(ext,'image/png')
    data = base64.b64encode(full.read_bytes()).decode()
    new_src = f'data:{mime};base64,{data}'
    result = attr.replace(src_m.group(1), new_src)
    print(f'  [OK] inlined {full.name} ({full.stat().st_size//1024}KB)')
    return result

text = re.sub(r'<img[^>]+>', inline_img, text)

out.write_text(text, encoding='utf-8')

moji = text.count('ÔÇö')
imgs = text.count('data:image')
print(f'\n[OK] index_final.html written')
print(f'  Mojibake remaining : {moji}')
print(f'  Images inlined     : {imgs}')
