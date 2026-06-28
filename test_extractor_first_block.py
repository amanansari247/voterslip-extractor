import sys, io, fitz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'lib/python_scripts')
doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]
text = page.get_text("text")
lines = text.split('\n')
for i, line in enumerate(lines):
    if 'नपम:' in line or 'नपम :' in line:
        block_lines = []
        for j in range(i, min(i + 15, len(lines))):
            block_lines.append(lines[j].strip())
        print("FIRST BLOCK:", block_lines)
        break
