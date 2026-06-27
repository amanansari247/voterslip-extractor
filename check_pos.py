import fitz
doc = fitz.open('C:/Users/Aman/Downloads/1-2.pdf')
page = doc[1]  # Page 1

blocks = page.get_text('dict')['blocks']
print('--- SERIAL NUMBERS ---')
for b in blocks:
    if b['type'] == 0:
        for l in b['lines']:
            for s in l['spans']:
                t = s['text'].strip()
                if t.isdigit() and int(t) <= 6:
                    print(f"Serial {t} at: {s['bbox']}")

print('\n--- IMAGES ---')
img_info = page.get_image_info()
images = page.get_images(full=True)
for i in range(len(img_info)):
    print(f"Image info {i}: bbox={img_info[i]['bbox']}")
    print(f"Image xref {i}: {images[i]}")
