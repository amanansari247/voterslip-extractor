import fitz
import os

doc = fitz.open("C:/Users/Aman/Downloads/1-2.pdf")
page = doc[1]
fonts = page.get_fonts()

os.makedirs("extracted_fonts", exist_ok=True)

for xref, ext, subtype, name, ref, encoding in fonts:
    try:
        font_data = doc.extract_font(xref)
        if font_data and font_data[3]:
            fname = name.replace("+", "_").replace(",", "_")
            fpath = f"extracted_fonts/{fname}.{font_data[1]}"
            with open(fpath, 'wb') as f:
                f.write(font_data[3])
            print(f"Extracted: {name} -> {fpath} ({len(font_data[3])} bytes)")
        else:
            print(f"No data for font: {name}")
    except Exception as e:
        print(f"Error extracting {name}: {e}")

doc.close()
