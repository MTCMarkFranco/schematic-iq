"""
Detect terminal rectangles using OpenCV contour analysis, measure their y-centroids,
and map them to cable zones.
"""
import cv2
import numpy as np

IMG = r"test-data\image.png"
img = cv2.imread(IMG)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
h, w = binary.shape

# Terminal block region (from dashed line detection): x=137..257, y=249..406
# Focus on this region
TB_X_LO, TB_X_HI = 130, 270
TB_Y_LO, TB_Y_HI = 240, 410

# Extract the terminal region
region = binary[TB_Y_LO:TB_Y_HI, TB_X_LO:TB_X_HI]

# Find contours (terminals are rectangular shapes)
contours, _ = cv2.findContours(region, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

# Filter for terminal-sized rectangles
# Typical terminal: width 20-60px, height 8-25px, roughly rectangular
rects = []
for cnt in contours:
    x, y, rw, rh = cv2.boundingRect(cnt)
    area = rw * rh
    if 15 <= rw <= 70 and 6 <= rh <= 30 and 100 <= area <= 2000:
        # Check rectangularity
        cnt_area = cv2.contourArea(cnt)
        if cnt_area > 0:
            rectness = cnt_area / area
            if rectness > 0.5:
                # Convert to absolute coords
                abs_x = x + TB_X_LO
                abs_y = y + TB_Y_LO
                cy = abs_y + rh // 2
                rects.append({
                    'x': abs_x, 'y': abs_y, 'w': rw, 'h': rh,
                    'cy': cy, 'rectness': rectness,
                    'area': cnt_area
                })

# Sort by y (top to bottom)
rects.sort(key=lambda r: r['cy'])

# Remove duplicates (nested rectangles at similar positions)
filtered = []
for r in rects:
    if not filtered or abs(r['cy'] - filtered[-1]['cy']) > 5:
        filtered.append(r)
    elif r['area'] > filtered[-1]['area']:
        filtered[-1] = r

print(f"Detected {len(filtered)} terminal-like rectangles:")
for r in filtered:
    print(f"  y={r['cy']:3d}: ({r['x']},{r['y']}) {r['w']}x{r['h']} rect={r['rectness']:.2f}")

# Also try horizontal projection to find terminal rows
print("\n--- Horizontal projection (foreground density per row) ---")
# Count fg pixels per row in the terminal block
densities = []
for y in range(TB_Y_LO, TB_Y_HI):
    row_fg = int(np.sum(binary[y, TB_X_LO:TB_X_HI] > 0))
    densities.append((y, row_fg))

# Find peaks (terminal centers are at high-density rows)
threshold = 40
peaks = []
in_peak = False
peak_start = 0
peak_max_y = 0
peak_max_val = 0
for y, d in densities:
    if d >= threshold and not in_peak:
        peak_start = y
        in_peak = True
        peak_max_y = y
        peak_max_val = d
    elif d >= threshold and in_peak:
        if d > peak_max_val:
            peak_max_y = y
            peak_max_val = d
    elif d < threshold and in_peak:
        peaks.append((peak_start, y - 1, peak_max_y, peak_max_val))
        in_peak = False
if in_peak:
    peaks.append((peak_start, densities[-1][0], peak_max_y, peak_max_val))

print(f"\n{len(peaks)} density peaks (terminal rows):")
for start, end, max_y, max_val in peaks:
    center = (start + end) // 2
    height = end - start + 1
    print(f"  y={start}-{end} (center={center}, h={height}px, max_density={max_val})")

# Map peaks to cable zones
boundaries = [
    {'y_lo': 0, 'y_hi': 311, 'label': 'N8000'},
    {'y_lo': 311, 'y_hi': 372, 'label': 'N7888'},
    {'y_lo': 372, 'y_hi': 644, 'label': 'N6000'},
]

print("\n--- Peak → Cable zone mapping ---")
for start, end, max_y, max_val in peaks:
    center = (start + end) // 2
    for bnd in boundaries:
        if bnd['y_lo'] <= center < bnd['y_hi']:
            print(f"  Row y={center} → {bnd['label']}")
            break
