import pathlib, re

p = pathlib.Path('publication/print_latest/index.html')
text = p.read_text(encoding='utf-8')

css_patch = """
<style>
  .MathJax_SVG svg { font-size: 120% !important; }
  .MathJax_SVG_Display svg { font-size: 120% !important; }
  mjx-container svg { width: auto !important; height: auto !important; font-size: 120% !important; }
</style>
"""

# Insert just before </head>
text = text.replace('</head>', css_patch + '</head>', 1)
p.write_text(text, encoding='utf-8')
print('[OK] CSS patch injected')
