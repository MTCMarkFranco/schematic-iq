"""Visualize the cable zone area to understand terminal-to-cable routing."""
import cv2
import numpy as np
import sys
sys.path.insert(0, ".")
from cv_preprocess import load_and_preprocess

image_path = "test-data/image.png"
img, gray, binary = load_and_preprocess(image_path)
h, w = gray.shape

# Cable zone area: x=270..390, y=220..420
# This covers terminal rects, cable circles, and connecting wires
x1, x2 = 270, 395
y1, y2 = 220, 420

print(f"Cable zone visualization ({x2-x1}x{y2-y1} pixels)")
print(f"x={x1}..{x2}, y={y1}..{y2}")
print()

# Create ASCII visualization - every pixel as '█' or ' '
# But that's too wide. Use 1:1 mapping but compress horizontally by 2
region = binary[y1:y2, x1:x2]
rh, rw = region.shape

# Print column headers (every 10 columns)
header = "     "
for x in range(0, rw, 10):
    header += f"{x1+x:<10d}"
print(header)

# Print rows
for y_off in range(rh):
    y_abs = y1 + y_off
    if y_off % 2 != 0:  # Skip every other row for readability
        continue
    line = f"{y_abs:4d} "
    for x_off in range(rw):
        if region[y_off, x_off] > 0:
            line += "█"
        else:
            line += " "
    print(line)

# Also print key coordinates
print("\n=== Key features ===")
print("Terminal rects (from detect_all_terms):")
print("  964: x=320, y=238, w=54, h=23 (cy=249)")
print("  963: x=320, y=261, w=54, h=22 (cy=272)")
print("  962: x=320, y=283, w=54, h=23 (cy=294)")
print("  961: x=320, y=305, w=54, h=23 (cy=316)")
print("  960: x=320, y=328, w=54, h=23 (cy=339)")
print("  959: x=320, y=350, w=54, h=23 (cy=361)")
print("  958: x=320, y=372, w=54, h=23 (cy=383)")
print("  957: x=320, y=395, w=48, h=22 (cy=406)")
print("Cable circles (from routing map):")
print("  N8000: (~346, ~281) r~32")
print("  N7888: (~346, ~342) r~32")
print("  N6000: (~346, ~402) r~32")
