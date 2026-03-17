"""Visualize cable zone with plain ASCII."""
import cv2
import numpy as np
import sys
sys.path.insert(0, ".")
from cv_preprocess import load_and_preprocess

image_path = "test-data/image.png"
img, gray, binary = load_and_preprocess(image_path)

# Focus on cable zone: x=290..380, y=230..420
# Subsample by 2 in x for readability
x1, x2 = 290, 380
y1, y2 = 230, 420

region = binary[y1:y2, x1:x2]
rh, rw = region.shape

# Print with plain ASCII
print(f"Region x={x1}..{x2}, y={y1}..{y2}")
print(f"Legend: # = foreground, . = background")
print()

# Column header
hdr = "     "
for x in range(0, rw, 10):
    hdr += f"{x1+x:<10d}"
print(hdr)

for y_off in range(0, rh, 2):  # every other row
    y_abs = y1 + y_off
    row = f"{y_abs:4d} "
    for x_off in range(rw):
        if region[y_off, x_off] > 0:
            row += "#"
        else:
            row += "."
    print(row)
