import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

doc = fitz.open(sys.argv[1])
page = doc[1] # Page 2
blocks = page.get_text("blocks")

for b in blocks[:15]:
    print(f"BBox: {b[:4]} -> Text: {repr(b[4])}")
