import fitz
import cv2
import numpy as np
import pytesseract
import sys
import io
import os
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

tessdata_dir = r'd:\voter-data-extraction'
config = f'--tessdata-dir {tessdata_dir} --psm 7' # PSM 7 treats the image as a single text line

doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]
blocks = page.get_text("dict")["blocks"]

for b in blocks:
    if b['type'] == 0:
        for line in b["lines"]:
            for span in line["spans"]:
                if 'जपवमद' in span["text"]:
                    bbox = span["bbox"]
                    
                    # Expand ONLY horizontally a bit, keep vertical tight
                    rect = fitz.Rect(bbox[0]-1, bbox[1], bbox[2]+1, bbox[3])
                    
                    # Render image of just this word (higher DPI for better OCR)
                    pix = page.get_pixmap(clip=rect, dpi=400)
                    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    if pix.n == 4:
                        img = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
                    else:
                        img = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                        
                    _, thresh = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY)
                    
                    ocr_text = pytesseract.image_to_string(thresh, lang='hin', config=config).strip()
                    
                    # Clean up random garbage
                    clean_text = re.sub(r'[^\u0900-\u097F\s]', '', ocr_text).strip()
                    print(f"Original mangled: {span['text']}")
                    print(f"OCR extracted: {ocr_text}")
                    print(f"Cleaned: {clean_text}")
                    sys.exit(0)
