import fitz
doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]
fonts = page.get_fonts()
for font in fonts:
    print(font)
