import fitz
doc = fitz.open('C:/Users/Aman/Downloads/1-2.pdf')
page = doc[1]

print("Images from get_image_info(xrefs=True):")
for i, info in enumerate(page.get_image_info(xrefs=True)):
    print(f"Info {i}: bbox={info.get('bbox')}, xref={info.get('xref')}")

