import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]
lines = page.get_text("text").split('\n')

for i, line in enumerate(lines[:50]):
    print(f"[{i:2d}] {repr(line)}")
