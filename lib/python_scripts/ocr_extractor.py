import fitz
import cv2
import numpy as np
import pytesseract
import base64
import re
import os

# Set Tesseract path if it's installed in the default location
# If the user added it to PATH, this isn't strictly necessary, but good practice on Windows
if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_ocr_pdf_data(pdf_path):
    doc = fitz.open(pdf_path)
    
    all_voters = []
    polling_station = "Unknown (Scanned PDF)"
    
    # Try to extract polling station from page 0
    try:
        page0 = doc[0]
        pix0 = page0.get_pixmap(dpi=150) # Lower DPI is faster
        img0_array = np.frombuffer(pix0.samples, dtype=np.uint8).reshape(pix0.height, pix0.width, pix0.n)
        if pix0.n == 4:
            img0 = cv2.cvtColor(img0_array, cv2.COLOR_RGBA2GRAY)
        else:
            img0 = cv2.cvtColor(img0_array, cv2.COLOR_RGB2GRAY)
            
        _, thresh0 = cv2.threshold(img0, 150, 255, cv2.THRESH_BINARY)
        text0 = pytesseract.image_to_string(thresh0, lang='pan+eng+hin')
        lines0 = text0.split('\n')
        
        for i, line in enumerate(lines0):
            if "ਪੋਲਿੰਗ ਬੂਥ" in line or "ਪਪਤਲਅਗ ਬਬਥ" in line or "मतदान" in line or "Polling" in line:
                # Polling station name is usually above the label in Punjabi PDFs
                if i > 0 and len(lines0[i-1].strip()) > 5:
                    polling_station = lines0[i-1].strip()
                else:
                    polling_station = line.strip()
                break
    except Exception:
        pass
        
    # ── Step 1: Process each voter page ────────────────────────────────────
    
    # Grid math based on empirical values
    cols = 3
    rows = 10
    start_x = 154
    start_y = 163  
    cell_w = 734
    cell_h = 299.5
    
    for page_num in range(1, len(doc)):
        page = doc[page_num]
        
        # Render page to image at 300 DPI
        pix = page.get_pixmap(dpi=300)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        if pix.n == 4:
            img = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        else:
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # If the page doesn't look like a 10x3 grid (e.g., last page), we might get empty cells
        for r in range(rows):
            for c in range(cols):
                x = int(start_x + c * cell_w)
                y = int(start_y + r * cell_h)
                w = int(cell_w)
                h = int(cell_h)
                
                cell_img = img[y:y+h, x:x+w]
                if cell_img.shape[0] == 0 or cell_img.shape[1] == 0:
                    continue
                
                # Split cell into text part (left) and photo part (right)
                # The cell is 734px wide. The photo is roughly the rightmost 200px.
                text_img = cell_img[:, :w-210]
                photo_img = cell_img[:, w-210:]
                
                # Enhance text image for OCR
                gray = cv2.cvtColor(text_img, cv2.COLOR_BGR2GRAY)
                # Thresholding to make text black on white
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                
                # Extract text using Tesseract with Punjabi and English
                # Note: 'pan' is the language code for Punjabi in Tesseract
                try:
                    text = pytesseract.image_to_string(thresh, lang='pan+eng')
                except Exception as e:
                    # If Tesseract fails, just skip
                    continue
                
                if not text.strip():
                    continue
                    
                # Basic parsing of the OCR text
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                if not lines:
                    continue
                
                # Try to extract details
                serial = ""
                voter_id = ""
                name = ""
                relative = ""
                house = ""
                age = ""
                gender = ""
                
                # Try to find serial number (usually first line, digits)
                for line in lines[:3]:
                    match = re.search(r'\b(\d{1,4})\b', line)
                    if match:
                        serial = match.group(1)
                        break
                
                # Try to find Voter ID (usually uppercase letters and numbers like REW1234567)
                for line in lines[:4]:
                    match = re.search(r'\b([A-Z]{3}\d{7})\b', line)
                    if match:
                        voter_id = match.group(1)
                        break
                
                # Try to find Name (ਨਾਮ or ਨਵਮ)
                for line in lines:
                    if 'ਨਾਮ' in line or 'ਨਵਮ' in line:
                        name = line.split(':')[-1].strip()
                        break
                
                # Try to find Relative Name (ਪਿਤਾ, ਪਤੀ, etc)
                for line in lines:
                    if 'ਪਿਤਾ' in line or 'ਪਤੀ' in line or 'ਮਾਤਾ' in line:
                        relative = line.split(':')[-1].strip()
                        break
                
                # Try to find Age (ਉਮਰ)
                for line in lines:
                    if 'ਉਮਰ' in line:
                        match = re.search(r'(\d+)', line)
                        if match:
                            age = match.group(1)
                        break
                        
                # Ensure we have at least a serial and a name
                if not serial or not name:
                    continue
                    
                # Convert photo to base64
                _, buffer = cv2.imencode('.jpg', photo_img)
                photo_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
                
                all_voters.append({
                    "serial": serial,
                    "name": name,
                    "relativeName": relative,
                    "houseNumber": house,
                    "age": age,
                    "gender": gender,
                    "voterId": voter_id,
                    "pollingStation": polling_station,
                    "photo": photo_b64,
                })

    doc.close()
    return {
        "pollingStation": polling_station,
        "voters": all_voters,
    }
