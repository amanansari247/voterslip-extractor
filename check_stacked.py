import fitz
doc = fitz.open('C:/Users/Aman/Downloads/1-2.pdf')
page = doc[1]

print("Images in top-left block (x < 250, y < 500):")
for i, img in enumerate(page.get_image_info()):
    bbox = img['bbox']
    if bbox[0] < 250 and bbox[1] < 500:
        print(f"Index {i}, bbox={bbox}")

print("\nAll image xrefs from get_images:")
images = page.get_images(full=True)
for i, img in enumerate(images):
    print(f"Xref {img[0]} (smask={img[1]})")

