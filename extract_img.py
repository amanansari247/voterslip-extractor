import fitz
doc = fitz.open('C:/Users/Aman/Downloads/1-2.pdf')

for xref in [70, 68, 131, 129]:
    img = doc.extract_image(xref)
    ext = img["ext"]
    with open(f"img_{xref}.{ext}", "wb") as f:
        f.write(img["image"])
    print(f"Extracted {xref}")
