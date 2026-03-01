import re
import sys
import fitz  # PyMuPDF

pdf_path = sys.argv[1]
doc = fitz.open(pdf_path)

pattern = re.compile(r"^(Figure|Exhibit)\s+\d+[A-Za-z]?\b", re.IGNORECASE)

for page in doc:
    t = page.get_text("text")
    for line in t.splitlines():
        s = " ".join(line.split()).strip()
        if s and pattern.match(s):
            print(s)
