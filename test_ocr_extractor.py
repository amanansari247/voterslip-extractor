import sys, io, fitz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'lib/python_scripts')
# pyrefly: ignore [missing-import]
from extractor import extract_voters_hindi

doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
# Limit to page 2 only to be fast
temp_doc = fitz.open()
temp_doc.insert_pdf(doc, from_page=0, to_page=2)
voters = extract_voters_hindi(temp_doc, 'Test Polling Station')
for v in voters[:5]: 
    print(f"Serial {v['serial']} | Name: {v['name']} | Relative: {v['relativeName']}")
