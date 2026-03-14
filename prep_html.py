import pathlib, re

src = pathlib.Path('publication/print_latest/index.html')
out = pathlib.Path('publication/print_latest/index_prepped.html')

text = src.read_text(encoding='utf-8')

# 1. Fix ALL mojibake em-dash variants everywhere in the document
text = text.replace('ÔÇö', '\u2014')
text = text.replace('\u00e2\u20ac\u201c', '\u2014')

# 2. Find all title tags and report
titles = re.findall(r'<title>(.*?)</title>', text, flags=re.DOTALL)
print(f'  Found {len(titles)} <title> tag(s):')
for i, t in enumerate(titles):
    print(f'    [{i}] {t.strip()[:80]}')

# 3. Keep only the FIRST title tag — remove all subsequent ones
first = True
def keep_first_title(m):
    global first
    if first:
        first = False
        return m.group(0)
    return ''
text = re.sub(r'<title>.*?</title>', keep_first_title, text, flags=re.DOTALL)

# 4. Strip stacked CSS patches
text = re.sub(r'<style[^>]*>\s*/\* mjpage v2.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>\s*\.MathJax_SVG.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>\s*mjx-container.*?</style>', '', text, flags=re.DOTALL)

# 5. Inject clean math size CSS
css = """<style>
  /* mjpage v2 SVG size fix */
  span.mjpage { font-size: 1.4em !important; line-height: 1.8 !important; }
  span.mjpage__block { display: block; font-size: 1.4em !important; margin: 1em 0 !important; }
  .mjpage svg { width: auto !important; }
  .mjpage svg > g { transform: scale(2) !important; transform-origin: left center; }
</style>"""

text = text.replace('</head>', css + '\n</head>', 1)

out.write_text(text, encoding='utf-8')

# 6. Verify
titles_after = re.findall(r'<title>(.*?)</title>', text, flags=re.DOTALL)
moji_count = text.count('ÔÇö')
print(f'\n[OK] index_prepped.html written')
print(f'  Title tags after: {len(titles_after)}')
print(f'  Title: {titles_after[0].strip()}')
print(f'  Mojibake remaining: {moji_count}')
