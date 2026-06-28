"""Get exact card boundaries from the Ajmer Hindi PDF."""
import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open('C:/Users/Aman/Downloads/AJMER NAGAR NIGAM-Ward No-001-Part No-001.pdf')
page = doc[2]

# From analysis:
# 3 columns, x starts: ~34, ~208, ~381
# Column widths: 208-34=174, 381-208=173, 555-381=174
# Card height: ~72.3
# First card y: ~150 (header area 0-150)
# Last card bottom: look at drawings

# Let's get the rectangle boundaries
drawings = page.get_drawings()

# Collect unique rectangles
rects = []
for d in drawings:
    for item in d["items"]:
        if item[0] == "re":
            r = item[1]
            w = r.width
            h = r.height
            if w > 100 and h > 50:  # filter to card-sized rectangles
                rects.append({
                    "x0": round(r.x0, 1),
                    "y0": round(r.y0, 1),
                    "x1": round(r.x1, 1),
                    "y1": round(r.y1, 1),
                    "w": round(w, 1),
                    "h": round(h, 1)
                })

print(f"Card-sized rectangles found: {len(rects)}")
for r in rects[:10]:
    print(f"  ({r['x0']}, {r['y0']}) -> ({r['x1']}, {r['y1']})  w={r['w']} h={r['h']}")

# Let's also count how many name labels per page to verify card count
for pg_idx in [2, 3, 4, 38]:
    if pg_idx >= len(doc):
        continue
    pg = doc[pg_idx]
    blocks = pg.get_text("dict")["blocks"]
    count = 0
    for b in blocks:
        if b['type'] == 0:
            for line in b["lines"]:
                for span in line["spans"]:
                    if span["text"].strip() in ['नपम:', 'नपम :']:
                        count += 1
    print(f"Page {pg_idx}: {count} voter cards")

# Check the serial numbers on page 2 to confirm 
pg = doc[2]
blocks = pg.get_text("dict")["blocks"]
serials = []
for b in blocks:
    if b['type'] == 0:
        for line in b["lines"]:
            for span in line["spans"]:
                t = span["text"].strip()
                if t.isdigit() and 1 <= int(t) <= 30:
                    serials.append({
                        "text": t,
                        "x": round(span["bbox"][0], 1),
                        "y": round(span["bbox"][1], 1)
                    })

# Filter for serial numbers (they're in bold boxes near top of cards)
print(f"\nPotential serial numbers on page 2: {len(serials)}")
for s in serials[:15]:
    print(f"  Serial {s['text']} at x={s['x']}, y={s['y']}")
