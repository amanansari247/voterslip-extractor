import cv2
import numpy as np
import os

img = cv2.imread('page2_scanned.jpg')
H, W = img.shape[:2]

# Math grid based on empirical values
cols = 3
rows = 10
start_x = 154
start_y = 163  # Calculated from row 7 (2259) - 7 * 299.4 = 163.2
cell_w = 734
cell_h = 299.5

os.makedirs('cells', exist_ok=True)

count = 0
for r in range(rows):
    for c in range(cols):
        x = int(start_x + c * cell_w)
        y = int(start_y + r * cell_h)
        w = int(cell_w)
        h = int(cell_h)
        
        cell_img = img[y:y+h, x:x+w]
        if cell_img.shape[0] > 0 and cell_img.shape[1] > 0:
            cv2.imwrite(f'cells/cell_{r}_{c}.jpg', cell_img)
            count += 1

print(f"Extracted {count} cells.")
