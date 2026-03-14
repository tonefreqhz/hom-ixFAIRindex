import pathlib, re
p = pathlib.Path('publication/print_latest/index.html')
text = p.read_text(encoding='utf-8')

# Remove (Draft) from title
text = text.replace('Home@ix \u2014 Full Working Book (Draft)', 'Home@ix \u2014 Full Working Book')
text = text.replace('(Draft)', '')

# Remove Known Issues box
text = re.sub(
    r'\s*<section class="box">\s*<h2>Known issues.*?</section>',
    '',
    text,
    flags=re.DOTALL | re.IGNORECASE
)

p.write_text(text, encoding='utf-8')

remaining_draft  = '(Draft)' in text
remaining_issues = 'Known issues' in text
print('[OK] Done')
print(f'  (Draft) still present      : {remaining_draft}')
print(f'  Known issues still present : {remaining_issues}')
