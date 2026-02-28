# assemble_full_ebook.py
from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def _extract_block(html: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, flags=re.I | re.S)
    return m.group(1).strip() if m else None

def extract_mainish(html: str) -> str:
    for tag in ("main", "article", "body"):
        blk = _extract_block(html, tag)
        if blk:
            return blk
    return html  # last resort

def strip_base_tag(html: str) -> str:
    return re.sub(r"<base\b[^>]*>\s*", "", html, flags=re.I)

def strip_mathjax_scripts(html: str) -> str:
    # remove MathJax config blocks + the CDN loader, we'll add one unified config
    html = re.sub(r"<script>\s*window\.MathJax\s*=\s*\{.*?\};\s*</script>", "", html, flags=re.I | re.S)
    html = re.sub(r"<script[^>]+mathjax@3[^>]+></script>", "", html, flags=re.I)
    return html

def main():
    follow = ROOT / "homeix_followup_paper.html"
    fair   = ROOT / "homeix_fair_paper.html"

    if not follow.exists():
        raise FileNotFoundError(f"Missing {follow}")
    if not fair.exists():
        raise FileNotFoundError(f"Missing {fair}")

    outdir = Path.cwd()  # we will run this with CWD = publication\print_$stamp
    outdir.mkdir(parents=True, exist_ok=True)

    follow_html = strip_mathjax_scripts(strip_base_tag(_read(follow)))
    fair_html   = strip_mathjax_scripts(strip_base_tag(_read(fair)))

    follow_body = extract_mainish(follow_html)
    fair_body   = extract_mainish(fair_html)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    known_issues = """
    <section class="box">
      <h2>Known issues (pre-publication)</h2>
      <ul>
        <li><strong>Animation rendering:</strong> some animated assets may not display in all viewers. Use exported GIF/PNG fallbacks in <code>assets/</code> where provided.</li>
        <li><strong>Math rendering:</strong> LaTeX rendering is still being standardized across sections. If any equations appear unrendered, open the HTML in a modern browser (MathJax-enabled).</li>
      </ul>
    </section>
    """.strip()

    out = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Home@ix — Full Working Book (print bundle)</title>

  <!-- Unified MathJax (supports $$..$$ and \\(..\\)) -->
  <script>
    window.MathJax = {{
      tex: {{
        displayMath: [['$$','$$']],
        inlineMath: [['\\\\(','\\\\)']]
      }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>

  <style>
    :root {{ --max: 980px; }}
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; line-height: 1.6; margin: 2rem; color: #111; }}
    main {{ max-width: var(--max); margin: 0 auto; }}
    h1, h2, h3 {{ line-height: 1.15; }}
    .meta {{ color: #444; }}
    .box {{ border: 1px solid #ddd; padding: 12px 14px; border-radius: 10px; background: #fafafa; margin: 1.2rem 0; }}
    figure {{ margin: 1.25rem 0; padding: .75rem; border: 1px dashed #cfcfcf; border-radius: 10px; }}
    figcaption {{ color: #444; font-size: .95rem; }}
    hr {{ border: 0; border-top: 1px solid #eee; margin: 2rem 0; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Home@ix — Full Working Book (Draft)</h1>
      <p class="meta"><strong>Print bundle:</strong> {outdir.name} &nbsp;|&nbsp; <strong>Built:</strong> {stamp}</p>
    </header>

    {known_issues}

    <hr />
    <section id="followup">
      <h2>Follow-up Paper</h2>
      {follow_body}
    </section>

    <hr />
    <section id="fair">
      <h2>FAIR Paper</h2>
      {fair_body}
    </section>

  </main>
</body>
</html>
"""

    (outdir / "index.html").write_text(out, encoding="utf-8")
    print(f"Wrote: {outdir / 'index.html'}")

if __name__ == "__main__":
    main()
