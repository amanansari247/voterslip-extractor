import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]
blocks = page.get_text("dict")["blocks"]

for b in blocks[:50]:
    if b['type'] == 0:  # text block
        for line in b["lines"]:
            for span in line["spans"]:
                if 'जपवमद' in span["text"]:
                    print(f"Font: {span['font']}, Text: {span['text']}")
