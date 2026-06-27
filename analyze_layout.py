"""
Final mapping validation: confirm get_images xref order matches get_image_info order,
and verify that the spatial proximity approach maps correctly.
"""
import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open('C:/Users/Aman/Downloads/1-2.pdf')

for page_idx in [1, 2]:
    page = doc[page_idx]
    print(f"\n=== PAGE {page_idx} ===")
    
    img_info_list = page.get_image_info()
    images_list = page.get_images(full=True)
    
    print(f"  get_image_info count: {len(img_info_list)}")
    print(f"  get_images count: {len(images_list)}")
    
    # get_image_info has 'number' field - let's see if it maps to get_images index
    for ii in range(min(len(img_info_list), len(images_list))):
        info = img_info_list[ii]
        img = images_list[ii]
        bbox = info["bbox"]
        print(f"  [{ii}] info.number={info.get('number','?'):>3}, xref={img[0]}, pos=({bbox[0]:.0f},{bbox[1]:.0f})")
    
    # Now the critical question: does get_text("text") return voters in the same order
    # as the spatial layout (row by row, left to right)?
    lines = page.get_text("text").split("\n")
    
    print(f"\n  Text serial number order (from get_text):")
    serial_order = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.isdigit() and i + 1 < len(lines):
            next_line = lines[i+1].strip()
            if "\u0a28\u0a35\u0a2e" in next_line or "\u0a28\u0a3e\u0a2e" in next_line:
                serial_order.append(int(stripped))
    print(f"  {serial_order}")
    
    # Compare with spatial order
    blocks = page.get_text("dict")["blocks"]
    all_spans = []
    for block in blocks:
        if block["type"] == 0:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        all_spans.append({"text": text, "x": span["bbox"][0], "y": span["bbox"][1]})
    
    name_spans = [s for s in all_spans if "\u0a28\u0a35\u0a2e" in s["text"] or "\u0a28\u0a3e\u0a2e" in s["text"]]
    
    spatial_entries = []
    for ns in name_spans:
        nearest_serial = None
        min_dist = 99999
        for s in all_spans:
            if s["text"].isdigit() and 1 <= int(s["text"]) <= 1000:
                dy = ns["y"] - s["y"]
                dx = abs(ns["x"] - s["x"])
                if -5 <= dy <= 30 and dx < 60:
                    dist = abs(dy) + dx * 0.5
                    if dist < min_dist:
                        min_dist = dist
                        nearest_serial = s
        if nearest_serial:
            spatial_entries.append({
                "serial": int(nearest_serial["text"]),
                "x": nearest_serial["x"],
                "y": nearest_serial["y"],
            })
    
    # Sort spatially: row by row (y), left to right (x)
    spatial_entries.sort(key=lambda e: (round(e["y"] / 50) * 50, e["x"]))
    spatial_order = [e["serial"] for e in spatial_entries]
    print(f"  Spatial order: {spatial_order}")
    
    # Are they the same?
    print(f"  Match: {serial_order == spatial_order}")
    if serial_order != spatial_order:
        print(f"  MISMATCH DETECTED! Text order != Spatial order")
        # Show differences
        for i in range(max(len(serial_order), len(spatial_order))):
            t = serial_order[i] if i < len(serial_order) else "?"
            s = spatial_order[i] if i < len(spatial_order) else "?"
            marker = " <-- DIFF" if t != s else ""
            print(f"    [{i}] text={t}, spatial={s}{marker}")

doc.close()
