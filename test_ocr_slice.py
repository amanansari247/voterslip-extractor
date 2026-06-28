import fitz
import cv2
import numpy as np

doc = fitz.open('C:/Users/Aman/AppData/Local/Temp/091c3631-5277-4588-b0a4-b47bd18fb7ff_fnl list 2.rar.7ff/11-31.pdf')
page = doc[1] # Page 2

# Render page to image at 300 DPI
pix = page.get_pixmap(dpi=300)
img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

if pix.n == 4:
    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
else:
    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

# Let's save it to see the dimensions and layout
cv2.imwrite('page2_scanned.jpg', img_array)
print(f"Saved page2_scanned.jpg. Dimensions: {img_array.shape}")
