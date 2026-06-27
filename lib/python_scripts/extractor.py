"""
Voter Data Extractor - Extracts voter information and photos from election PDF files.
Uses position-based matching to correctly pair each voter with their photo.
"""
import fitz
import sys
import json
import re
import base64
import os
import io

# Fix UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def extract_pdf_data(pdf_path):
    doc = fitz.open(pdf_path)
    
    polling_station = ""
    all_voters = []
    
    # ── Step 1: Extract polling station from page 1 ────────────────────────
    page1_text = doc[0].get_text("text").split('\n')
    for i, line in enumerate(page1_text):
        if "ਪਪਤਲਅਗ ਬਬਥ" in line or "ਪੋਲਿੰਗ ਬੂਥ" in line:
            if i > 0:
                polling_station = page1_text[i-1].strip()
            break
            
    if not polling_station and len(doc) > 1:
        page2_text = doc[1].get_text("text").split('\n')
        for i, line in enumerate(page2_text):
            if "ਪਪਤਲਅਗ ਬਬਥ" in line or "ਪੋਲਿੰਗ ਬੂਥ" in line:
                if i > 0:
                    polling_station = page2_text[i-1].strip()
                break

    # ── Step 2: Process each voter page ────────────────────────────────────
    for page_num in range(1, len(doc)):
        page = doc[page_num]
        
        # ── 2a: Get image positions and xrefs ─────────────────
        # get_image_info(xrefs=True) gives positions AND the correct xref
        img_info_list = page.get_image_info(xrefs=True)
        
        # Build a list of (position, xref) pairs
        img_entries = []
        for info in img_info_list:
            bbox = info["bbox"]
            xref = info.get("xref")
            if xref:
                img_entries.append({
                    "xref": xref,
                    "x": bbox[0],
                    "y": bbox[1],
                    "cx": (bbox[0] + bbox[2]) / 2,
                    "cy": (bbox[1] + bbox[3]) / 2,
                })
        
        # Sort by row (y) then column (x) — group into rows first
        # Use a tolerance of ~40 pts to group images in the same row
        img_entries.sort(key=lambda e: (round(e["y"] / 40) * 40, e["x"]))
        
        # ── 2b: Extract voter text entries with positions ─────────────────
        # Use "dict" mode to get each text span's exact position
        blocks = page.get_text("dict")["blocks"]
        
        all_spans = []
        for block in blocks:
            if block["type"] == 0:  # text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            all_spans.append({
                                "text": text,
                                "x": span["bbox"][0],
                                "y": span["bbox"][1],
                                "y2": span["bbox"][3],
                                "bbox": span["bbox"],
                            })
        
        # Find name markers (voter entries start with serial + name)
        name_markers = [s for s in all_spans 
                        if "ਨਵਮ" in s["text"] or "ਨਾਮ" in s["text"]]
        
        # For each name marker, find the associated serial number
        voter_positions = []
        used_serials = set()
        
        for nm in name_markers:
            best_serial = None
            best_dist = 99999
            
            for s in all_spans:
                if s["text"].isdigit() and 1 <= int(s["text"]) <= 2000:
                    key = (s["x"], s["y"])
                    if key in used_serials:
                        continue
                    dy = nm["y"] - s["y"]
                    dx = abs(nm["x"] - s["x"])
                    # Serial should be above or very close to the name, same column
                    if -5 <= dy <= 30 and dx < 60:
                        dist = abs(dy) + dx * 0.5
                        if dist < best_dist:
                            best_dist = dist
                            best_serial = s
            
            if best_serial:
                used_serials.add((best_serial["x"], best_serial["y"]))
                voter_positions.append({
                    "serial": int(best_serial["text"]),
                    "serial_x": best_serial["x"],
                    "serial_y": best_serial["y"],
                    "name_x": nm["x"],
                    "name_y": nm["y"],
                })
        
        # Sort voters by visual position (row by row, left to right)
        voter_positions.sort(key=lambda v: (round(v["serial_y"] / 40) * 40, v["serial_x"]))
        
        # ── 2c: Match each voter position to its closest image ────────────
        voter_to_image = {}
        used_images = set()
        
        for vp in voter_positions:
            best_img_idx = None
            best_dist = 99999
            
            for img_idx, ie in enumerate(img_entries):
                if img_idx in used_images:
                    continue
                # Image should be to the right of the voter text and at similar Y
                dy = abs(ie["cy"] - (vp["serial_y"] + 25))  # center of image vs voter
                dx = ie["x"] - vp["serial_x"]
                
                if dx > 0 and dx < 250 and dy < 50:
                    d = dy + dx * 0.05  # weight Y more than X
                    if d < best_dist:
                        best_dist = d
                        best_img_idx = img_idx
            
            if best_img_idx is not None:
                used_images.add(best_img_idx)
                voter_to_image[vp["serial"]] = best_img_idx
        
        # ── 2d: Extract actual text data using plain text mode ────────────
        # (This is more reliable for getting the field values)
        lines = page.get_text("text").split('\n')
        
        page_voters = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.isdigit() and i + 1 < len(lines) and \
               ("ਨਵਮ" in lines[i+1] or "ਨਾਮ" in lines[i+1]):
                try:
                    serial = int(line)
                    name_raw = lines[i+1].strip()
                    relative_raw = lines[i+2].strip() if i+2 < len(lines) else ""
                    house_raw = lines[i+3].strip() if i+3 < len(lines) else ""
                    
                    age = ""
                    gender = ""
                    voter_id = ""
                    
                    look_ahead = lines[i+4 : i+14]
                    for la in look_ahead:
                        la = la.strip()
                        if la.isdigit() and not age:
                            age = la
                        elif la in ["ਇਸਤਰਤ", "ਪਪਰਸ਼", "ਔਰਤ", "ਮਰਦ"] and not gender:
                            gender = la
                        elif (la.startswith("REW") or la.startswith("TGO") or 
                              la.startswith("BDP") or 
                              (len(la) == 10 and la[:3].isalpha() and la[3:].isdigit())):
                            voter_id = la
                    
                    name = name_raw.split(":", 1)[1].strip() if ":" in name_raw else name_raw
                    relative = relative_raw.split(":", 1)[1].strip() if ":" in relative_raw else relative_raw
                    house = house_raw.split(":", 1)[1].strip() if ":" in house_raw else house_raw
                    
                    # Get photo for this voter
                    photo_b64 = None
                    if serial in voter_to_image:
                        img_idx = voter_to_image[serial]
                        xref = img_entries[img_idx]["xref"]
                        try:
                            base_image = doc.extract_image(xref)
                            img_bytes = base_image["image"]
                            ext = base_image["ext"]
                            b64 = base64.b64encode(img_bytes).decode("utf-8")
                            photo_b64 = f"data:image/{ext};base64,{b64}"
                        except Exception:
                            photo_b64 = None
                    
                    page_voters.append({
                        "serial": str(serial),
                        "name": name,
                        "relativeName": relative,
                        "houseNumber": house,
                        "age": age,
                        "gender": gender,
                        "voterId": voter_id,
                        "pollingStation": polling_station,
                        "photo": photo_b64,
                    })
                    
                    i += 10
                except Exception:
                    i += 1
            else:
                i += 1
        
        all_voters.extend(page_voters)

    doc.close()
    return {
        "pollingStation": polling_station,
        "voters": all_voters,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: extractor.py <input.pdf> <output.json>"}))
        sys.exit(1)
        
    try:
        data = extract_pdf_data(sys.argv[1])
        with open(sys.argv[2], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
