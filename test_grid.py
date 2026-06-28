import cv2
import numpy as np

img = cv2.imread('page2_scanned.jpg')
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Thresholding
thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 10)

# Detect horizontal lines
horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
cnts_h = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnts_h = cnts_h[0] if len(cnts_h) == 2 else cnts_h[1]

# Detect vertical lines
vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
cnts_v = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnts_v = cnts_v[0] if len(cnts_v) == 2 else cnts_v[1]

print(f"Found {len(cnts_h)} horizontal line segments")
print(f"Found {len(cnts_v)} vertical line segments")

# Combine lines
grid = cv2.add(detect_horizontal, detect_vertical)

# Find contours in the grid
cnts = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cnts = cnts[0] if len(cnts) == 2 else cnts[1]

# Sort contours top-to-bottom
def sort_contours(cnts, method="left-to-right"):
    reverse = False
    i = 0
    if method == "right-to-left" or method == "bottom-to-top":
        reverse = True
    if method == "top-to-bottom" or method == "bottom-to-top":
        i = 1
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes), key=lambda b: b[1][i], reverse=reverse))
    return (cnts, boundingBoxes)

# Filter for boxes that look like voter slips
# Expected size: ~ 700-800px wide, ~ 200-350px high
valid_boxes = []
for c in cnts:
    x, y, w, h = cv2.boundingRect(c)
    if 700 < w < 850 and 200 < h < 400:
        valid_boxes.append((x, y, w, h))

print(f"Found {len(valid_boxes)} valid voter slip boxes")

# Sort them top-to-bottom, then left-to-right
valid_boxes.sort(key=lambda b: (round(b[1]/200)*200, b[0]))

if len(valid_boxes) > 0:
    for i, (x, y, w, h) in enumerate(valid_boxes[:3]):
        print(f"Box {i}: x={x}, y={y}, w={w}, h={h}")
        cv2.imwrite(f'box_{i}.jpg', img[y:y+h, x:x+w])
