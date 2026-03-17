"""Search for jumper between terminals 963 and 964.
Look for vertical/diagonal connecting pixels between their wire levels."""
import cv2
import numpy as np
import sys
sys.path.insert(0, ".")
from cv_preprocess import load_and_preprocess

image_path = "test-data/image.png"
img, gray, binary = load_and_preprocess(image_path)
h, w = gray.shape

# Terminal 964: rect at x=320, y=238, h=23 → cy=249
# Terminal 963: rect at x=320, y=261, h=22 → cy=272
# Jumper would connect these two terminals

# Search areas:
# 1. RIGHT side of terminals (x > 374)
# 2. LEFT side between stubs (x < 320)
# 3. Between the terminal rects themselves (x=320-374)

# First, visualize RIGHT side of terminals (x=370..420)
print("=== Right side of terminals (x=370..420, y=235..285) ===")
for y in range(235, 286):
    row = f"{y:4d} "
    for x in range(370, min(w, 421)):
        if binary[y, x] > 0:
            row += "#"
        else:
            row += "."
    print(row)

# Between terminal rects (x=310..380, y=256..266) - the border zone
print("\n=== Border zone between 964 and 963 (x=310..380, y=256..268) ===")
for y in range(256, 269):
    row = f"{y:4d} "
    for x in range(310, min(w, 381)):
        if binary[y, x] > 0:
            row += "#"
        else:
            row += "."
    print(row)

# LEFT side stubs area - check for vertical connection between y=249 and y=272
# at various x positions
print("\n=== Vertical connectivity between y=249 and y=272 ===")
for x in range(120, 320, 5):
    # Check if there are continuous foreground pixels from y=249 to y=272
    col_slice = binary[249:273, x]
    fg_count = np.count_nonzero(col_slice)
    total = len(col_slice)
    if fg_count > 5:  # Significant foreground
        # Find which rows have foreground
        fg_rows = [249 + i for i in range(total) if col_slice[i] > 0]
        print(f"  x={x:4d}: {fg_count}/{total} foreground rows: {fg_rows[:10]}{'...' if len(fg_rows)>10 else ''}")

# Check specifically at x=190 (v-bus) between the two wire levels
print("\n=== Detailed column at x=190, y=248..275 ===")
for y in range(248, 276):
    row = f"{y:4d} "
    for x in range(185, 196):
        if binary[y, x] > 0:
            row += "#"
        else:
            row += "."
    print(row)

# Check x=314 (main v-bus) between the two levels
print("\n=== Detailed column at x=314, y=248..275 ===")
for y in range(248, 276):
    row = f"{y:4d} "
    for x in range(312, 318):
        if binary[y, x] > 0:
            row += "#"
        else:
            row += "."
    print(row)

# Also check the far right area (x=374..615) for any connecting lines
print("\n=== Far right scan (x=374..420, y=245..280) ===")
for y in range(245, 281):
    row = f"{y:4d} "
    for x in range(374, min(w, 421)):
        if binary[y, x] > 0:
            row += "#"
        else:
            row += "."
    print(row)

# Scan further right
print(f"\n=== Ultra far right (x=420..{min(w,500)}, y=245..280) ===")
for y in range(245, 281):
    row = f"{y:4d} "
    for x in range(420, min(w, 500)):
        if binary[y, x] > 0:
            row += "#"
        else:
            row += "."
    print(row)
