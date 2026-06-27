"""
Verification script: Extract data and verify that each voter's photo matches
by cross-checking the spatial positions in the PDF.
"""
import sys
import io
import os

# Fix stdout encoding FIRST, before any module that might also do it
if sys.platform == 'win32' and not isinstance(sys.stdout, io.TextIOWrapper) or \
   (hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import fitz
import json
import base64

# Import our extractor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib', 'python_scripts'))
from extractor import extract_pdf_data

pdf_path = 'C:/Users/Aman/Downloads/1-2.pdf'
print(f"Extracting from: {pdf_path}")
print("=" * 60)

data = extract_pdf_data(pdf_path)

print(f"Polling Station: {data['pollingStation']}")
print(f"Total Voters: {len(data['voters'])}")
print()

# Now verify by re-opening the PDF and checking positions
doc = fitz.open(pdf_path)

# For each voter page, rebuild the mapping independently and compare
verified = 0
mismatched = 0
no_photo = 0

for page_num in range(1, len(doc)):
    page = doc[page_num]
    
    img_info_list = page.get_image_info()
    images_list = page.get_images(full=True)
    
    # Build position -> xref mapping
    pos_to_xref = {}
    for ii in range(min(len(img_info_list), len(images_list))):
        bbox = img_info_list[ii]["bbox"]
        xref = images_list[ii][0]
        pos_to_xref[ii] = {
            "xref": xref,
            "x": bbox[0],
            "y": bbox[1],
        }
    
    # Sort by position (row, col)
    sorted_imgs = sorted(pos_to_xref.values(), key=lambda e: (round(e["y"] / 40) * 40, e["x"]))
    
    # Get voter text entries in order
    lines = page.get_text("text").split("\n")
    page_serials = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.isdigit() and i + 1 < len(lines) and \
           ("\u0a28\u0a35\u0a2e" in lines[i+1] or "\u0a28\u0a3e\u0a2e" in lines[i+1]):
            page_serials.append(int(line))
            i += 10
        else:
            i += 1
    
    # For this page, each serial should map to corresponding image in spatial order
    # Find each serial's position using dict mode
    blocks = page.get_text("dict")["blocks"]
    all_spans = []
    for block in blocks:
        if block["type"] == 0:
            for line_b in block["lines"]:
                for span in line_b["spans"]:
                    text = span["text"].strip()
                    if text:
                        all_spans.append({"text": text, "x": span["bbox"][0], "y": span["bbox"][1]})
    
    name_markers = [s for s in all_spans if "\u0a28\u0a35\u0a2e" in s["text"] or "\u0a28\u0a3e\u0a2e" in s["text"]]
    
    voter_pos = []
    used = set()
    for nm in name_markers:
        best = None
        best_d = 99999
        for s in all_spans:
            if s["text"].isdigit() and 1 <= int(s["text"]) <= 2000:
                k = (s["x"], s["y"])
                if k in used:
                    continue
                dy = nm["y"] - s["y"]
                dx = abs(nm["x"] - s["x"])
                if -5 <= dy <= 30 and dx < 60:
                    d = abs(dy) + dx * 0.5
                    if d < best_d:
                        best_d = d
                        best = s
        if best:
            used.add((best["x"], best["y"]))
            voter_pos.append({"serial": int(best["text"]), "x": best["x"], "y": best["y"]})
    
    voter_pos.sort(key=lambda v: (round(v["y"] / 40) * 40, v["x"]))
    
    # Match each voter to nearest image
    used_imgs = set()
    for vp in voter_pos:
        best_idx = None
        best_d = 99999
        for idx, ie in enumerate(sorted_imgs):
            if idx in used_imgs:
                continue
            dy = abs(ie["y"] - vp["y"])
            dx = ie["x"] - vp["x"]
            if dx > 0 and dx < 250 and dy < 50:
                d = dy + dx * 0.05
                if d < best_d:
                    best_d = d
                    best_idx = idx
        
        # Check if our extractor assigned the same photo
        serial_str = str(vp["serial"])
        voter_data = next((v for v in data["voters"] if v["serial"] == serial_str), None)
        
        if voter_data is None:
            continue
            
        if best_idx is not None:
            used_imgs.add(best_idx)
            expected_xref = sorted_imgs[best_idx]["xref"]
            
            if voter_data["photo"]:
                # Extract the first few bytes of the base64 to compare
                expected_img = doc.extract_image(expected_xref)
                expected_b64 = base64.b64encode(expected_img["image"]).decode("utf-8")[:50]
                actual_b64 = voter_data["photo"].split(",")[1][:50] if "," in voter_data["photo"] else ""
                
                if expected_b64 == actual_b64:
                    verified += 1
                else:
                    mismatched += 1
                    print(f"  MISMATCH: Serial {vp['serial']} on page {page_num}")
            else:
                no_photo += 1
        else:
            if voter_data["photo"]:
                mismatched += 1
                print(f"  UNEXPECTED PHOTO: Serial {vp['serial']} has photo but shouldn't")
            else:
                no_photo += 1

doc.close()

print(f"\n{'='*60}")
print(f"VERIFICATION RESULTS:")
print(f"  Verified correct: {verified}")
print(f"  Mismatched:       {mismatched}")
print(f"  No photo:         {no_photo}")
print(f"  Total:            {verified + mismatched + no_photo}")

if mismatched == 0:
    print(f"\n  ✓ ALL PHOTOS CORRECTLY MATCHED!")
else:
    print(f"\n  ✗ THERE ARE MISMATCHES - needs investigation")
