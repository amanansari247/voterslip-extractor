import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]
text = page.get_text("text")
lines = text.split('\n')

from extractor import extract_voters_hindi
voters = extract_voters_hindi(doc, "Test Polling Station")
for v in voters[:3]:
    print(v)
