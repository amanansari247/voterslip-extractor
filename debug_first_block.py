import fitz
doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]
lines = page.get_text("text").split('\n')
for i, line in enumerate(lines):
    if 'नपम:' in line:
        block = [l.strip() for l in lines[i:i+15]]
        print(f"Block: {block}")
        break
