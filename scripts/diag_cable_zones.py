"""
Map cable-zone y-bands to cable labels by locating where cable text
appears vertically.  Then assign each horizontal wire to the nearest
cable band, producing a terminal→cable routing map.
"""
import cv2
import numpy as np

IMG = r"test-data\image.png"
img = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
_, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
h, w = binary.shape

# ------- 1: Cable zone vertical density profile -------
# The cable routing zone sits roughly at x=310..380.
# Scan each row to find text-heavy bands (cable label y-positions).
CABLE_X_LO, CABLE_X_HI = 310, 380
print(f"Cable zone: x={CABLE_X_LO}-{CABLE_X_HI}")
print("\nVertical density profile (foreground pixel count per row, y=230-430):")
densities = []
for y in range(230, 430):
    row_fg = int(np.sum(binary[y, CABLE_X_LO:CABLE_X_HI] > 0))
    densities.append((y, row_fg))
    bar = "#" * (row_fg // 2)
    if row_fg > 15:
        print(f"  y={y:3d}: {row_fg:3d} |{bar}")

# Find clusters of high-density rows (text lines)
print("\n--- Text band detection (high-density clusters) ---")
threshold = 20
in_band = False
band_start = 0
bands = []
for y, d in densities:
    if d >= threshold and not in_band:
        band_start = y
        in_band = True
    elif d < threshold and in_band:
        bands.append((band_start, y - 1))
        in_band = False
if in_band:
    bands.append((band_start, densities[-1][0]))

print(f"Detected {len(bands)} high-density bands:")
for b_start, b_end in bands:
    mid = (b_start + b_end) // 2
    total_px = sum(d for _, d in densities if b_start <= _ <= b_end)
    print(f"  y={b_start}-{b_end} (center={mid}, height={b_end - b_start + 1}px)")

# ------- 2: Associate bands with cable labels -------
# From discovery: N8000=top, N7888=middle, N6000=bottom
# Sort bands by y and assign labels
cable_labels = ["N8000", "N7888", "N6000"]
cable_y_centers = []
if len(bands) >= 3:
    # Take the 3 largest/most prominent bands
    sorted_bands = sorted(bands, key=lambda b: b[1] - b[0], reverse=True)
    top_bands = sorted(sorted_bands[:3], key=lambda b: b[0])  # sort by y position
    print(f"\nTop 3 bands (by size, sorted by y):")
    for i, (b_start, b_end) in enumerate(top_bands):
        mid = (b_start + b_end) // 2
        cable_y_centers.append(mid)
        print(f"  {cable_labels[i]}: y={b_start}-{b_end} (center={mid})")
else:
    print(f"\nOnly {len(bands)} bands detected, expected 3+")
    # Fallback: divide cable zone height into equal thirds
    zone_y_lo = 240
    zone_y_hi = 420
    third = (zone_y_hi - zone_y_lo) // 3
    for i, label in enumerate(cable_labels):
        mid = zone_y_lo + third * i + third // 2
        cable_y_centers.append(mid)
        print(f"  {label}: estimated center y={mid}")

# ------- 3: Map HW y → nearest cable via bridge rows -------
hw_ys = [248, 293, 338, 382, 406]
# Bridge rows from junction diagnostic (direct rungs)
rung_ys = [249, 294, 339, 383, 406]

print("\n--- HW → Cable routing map ---")
print(f"Cable centers: {list(zip(cable_labels, cable_y_centers))}")
for hw_y, rung_y in zip(hw_ys, rung_ys):
    # Find nearest cable center to the bridge row y
    dists = [(abs(rung_y - cy), label, cy) for label, cy in zip(cable_labels, cable_y_centers)]
    dists.sort()
    best_dist, best_label, best_cy = dists[0]
    print(f"  HW y={hw_y} → bridge y={rung_y} → {best_label} (center y={best_cy}, dist={best_dist}px)")

# ------- 4: Also scan for actual cable circle features -------
# Cable circles in schematics are typically larger circles (r=15-30px)
# Look for circular features in the cable zone using  HoughCircles
# on a sub-region
sub_img = img[230:430, CABLE_X_LO:CABLE_X_HI]
sub_blur = cv2.GaussianBlur(sub_img, (5, 5), 0)
circles = cv2.HoughCircles(
    sub_blur, cv2.HOUGH_GRADIENT, dp=1.2,
    minDist=30, param1=80, param2=30,
    minRadius=8, maxRadius=35
)
print("\n--- HoughCircles in cable zone (x=310-380, y=230-430) ---")
if circles is not None:
    for c in circles[0]:
        cx, cy, r = int(c[0]) + CABLE_X_LO, int(c[1]) + 230, int(c[2])
        print(f"  Circle at ({cx}, {cy}) r={r}")
else:
    print("  No circles detected")

# ------- 5: Broader scan for cable circle positions using full image -------
# Search the right half of the image for larger circles
print("\n--- HoughCircles full right half (x=280+) ---")
right_half = img[:, 280:]
right_blur = cv2.GaussianBlur(right_half, (5, 5), 0)
for param2 in [40, 30, 20]:
    circles2 = cv2.HoughCircles(
        right_blur, cv2.HOUGH_GRADIENT, dp=1.2,
        minDist=40, param1=80, param2=param2,
        minRadius=12, maxRadius=40
    )
    if circles2 is not None:
        print(f"  param2={param2}: {len(circles2[0])} circles")
        for c in circles2[0]:
            cx, cy, r = int(c[0]) + 280, int(c[1]), int(c[2])
            print(f"    ({cx}, {cy}) r={r}")
        break
    else:
        print(f"  param2={param2}: no circles")

# ------- 6: Text position via horizontal projection -------
# Narrow the cable zone to exclude borders (x=316-372)
INNER_X_LO, INNER_X_HI = 316, 372
print(f"\n--- Inner cable zone density (x={INNER_X_LO}-{INNER_X_HI}) ---")
for y in range(240, 420):
    row_fg = int(np.sum(binary[y, INNER_X_LO:INNER_X_HI] > 0))
    if row_fg > 10:
        bar = "#" * (row_fg // 2)
        print(f"  y={y:3d}: {row_fg:3d} |{bar}")
