import fitz
doc = fitz.open('C:/Users/Aman/Downloads/1-2.pdf')
for page_num in range(min(3, len(doc))):
    page = doc[page_num]
    images = page.get_images(full=True)
    print(f"Page {page_num}: {len(images)} images")
    for img in images[:5]:
        xref = img[0]
        base_image = doc.extract_image(xref)
        ext = base_image["ext"]
        size = len(base_image["image"])
        w = base_image["width"]
        h = base_image["height"]
        print(f"  xref={xref}, ext={ext}, size={size} bytes, w={w}, h={h}")
doc.close()
