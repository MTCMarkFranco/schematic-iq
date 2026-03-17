"""
Junction analysis: For each rung × vertical intersection, check if the
horizontal rung CONTINUES past the vertical (CROSSOVER) or TERMINATES (BEND).
Also dump raw pixel neighborhoods for key junctions.
"""
import cv2
import numpy as np

IMG = r"test-data\image.png"
img = cv2.imread(IMG, cv2.IMREAD_GRAYSCALE)
_, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
h, w = binary.shape

# Rung y-values (from leftward-scan diagnostic)
rung_ys = [249, 271, 294, 316, 339, 361, 383, 406]
# Individual vertical run x-positions in the cable routing zone
vert_xs = [322, 332, 342, 350, 358]

# Nearest HW for each rung (for terminal identification)
hw_ys = [248, 293, 338, 382, 406]
rung_hw_map = {}
for ry in rung_ys:
    nearest_hw = min(hw_ys, key=lambda hy: abs(hy - ry))
    dist = abs(nearest_hw - ry)
    rung_hw_map[ry] = (nearest_hw, dist)

print("Rung → HW mapping:")
for ry, (hy, d) in sorted(rung_hw_map.items()):
    tag = "DIRECT" if d <= 2 else "INDIRECT"
    print(f"  Rung y={ry} → HW y={hy} (dist={d}px) [{tag}]")

# Determine vertical wire width at each x
print("\nVertical wire widths:")
for vx in vert_xs:
    # Sample several y positions to find the wire width
    widths = []
    for test_y in range(250, 400, 20):
        # Scan left and right from vx to find wire edges
        left = vx
        while left > 0 and binary[test_y, left] > 0:
            left -= 1
        right = vx
        while right < w - 1 and binary[test_y, right] > 0:
            right += 1
        wire_width = right - left - 1
        if wire_width > 0:
            widths.append(wire_width)
    if widths:
        avg_w = np.mean(widths)
        print(f"  x={vx}: avg width={avg_w:.1f}px (range {min(widths)}-{max(widths)})")
    else:
        print(f"  x={vx}: NO foreground detected")

print("\n" + "=" * 70)
print("JUNCTION ANALYSIS: Does rung continue PAST vertical?")
print("=" * 70)

# For each junction, check pixels to the RIGHT of the vertical
# beyond the vertical's line width (offset +4 to +8 from center)
results = {}
for ry in rung_ys:
    print(f"\nRung y={ry} (→ HW y={rung_hw_map[ry][0]}, {rung_hw_map[ry][1]}px):")
    for vx in vert_xs:
        # First, find exact wire width at this y
        left_edge = vx
        while left_edge > 0 and binary[ry, left_edge] > 0:
            left_edge -= 1
        right_edge = vx
        while right_edge < w - 1 and binary[ry, right_edge] > 0:
            right_edge += 1
        wire_extent = right_edge - left_edge - 1

        # Check BEYOND the right edge of the vertical wire
        # Sample 5 pixels past the right edge
        right_pixels = []
        for offset in range(1, 6):
            rx = right_edge + offset
            if 0 <= rx < w:
                # Check a 3-pixel band at ry ± 1
                band = [binary[ry + dy, rx] for dy in range(-1, 2)
                        if 0 <= ry + dy < h]
                right_pixels.append(max(band) > 0)
            else:
                right_pixels.append(False)

        # Check BEYOND the left edge
        left_pixels = []
        for offset in range(1, 6):
            lx = left_edge - offset
            if 0 <= lx < w:
                band = [binary[ry + dy, lx] for dy in range(-1, 2)
                        if 0 <= ry + dy < h]
                left_pixels.append(max(band) > 0)
            else:
                left_pixels.append(False)

        right_count = sum(right_pixels)
        left_count = sum(left_pixels)

        if right_count >= 3 and left_count >= 3:
            verdict = "CROSSING"
        elif left_count >= 3 and right_count <= 1:
            verdict = ">>> BEND-RIGHT (terminates HERE) <<<"
        elif right_count >= 3 and left_count <= 1:
            verdict = ">>> BEND-LEFT (terminates HERE) <<<"
        elif right_count <= 1 and left_count <= 1:
            verdict = "ENDPOINT"
        else:
            verdict = f"UNCLEAR"

        results[(ry, vx)] = verdict
        r_str = ''.join(['#' if p else '.' for p in right_pixels])
        l_str = ''.join(['#' if p else '.' for p in left_pixels])
        print(f"  x={vx} [w={wire_extent}px]: L={l_str}({left_count}) R={r_str}({right_count}) → {verdict}")


# Now check what's BELOW the routing zone for each vertical
# to see which cable each vertical connects to
print("\n" + "=" * 70)
print("VERTICAL RUN PROFILES (below routing zone, y=410 to y=560)")
print("=" * 70)

for vx in vert_xs:
    print(f"\nVertical x={vx}:")
    segments = []
    in_seg = False
    seg_start = 0
    for y in range(410, min(560, h)):
        is_fg = binary[y, vx] > 0
        if is_fg and not in_seg:
            seg_start = y
            in_seg = True
        elif not is_fg and in_seg:
            segments.append((seg_start, y - 1))
            in_seg = False
    if in_seg:
        segments.append((seg_start, min(559, h - 1)))

    for s, e in segments:
        print(f"  Segment y={s}-{e} (len={e - s + 1})")

    # Check horizontal extensions at various y levels below routing zone
    for y in range(420, min(560, h), 10):
        if binary[y, vx] > 0:
            # Scan right
            rx = vx
            while rx < w - 1 and binary[y, rx] > 0:
                rx += 1
            # Scan left
            lx = vx
            while lx > 0 and binary[y, lx] > 0:
                lx -= 1
            total_w = rx - lx - 1
            if total_w > 5:  # Only show wide horizontal features
                print(f"  y={y}: horizontal extent x={lx + 1}..{rx - 1} (width={total_w})")


# Dump raw pixel neighborhoods for the key BEND junctions
print("\n" + "=" * 70)
print("RAW PIXEL DUMP for junctions with BEND verdict")
print("=" * 70)

for (ry, vx), verdict in results.items():
    if "BEND" in verdict:
        print(f"\n--- Junction (y={ry}, x={vx}) [{verdict}] ---")
        # Show 15x15 pixel neighborhood
        for dy in range(-7, 8):
            row = []
            for dx in range(-7, 8):
                py, px = ry + dy, vx + dx
                if 0 <= py < h and 0 <= px < w:
                    row.append("##" if binary[py, px] > 0 else "..")
                else:
                    row.append("??")
            y_label = f"y={ry + dy:3d}"
            print(f"  {y_label} {''.join(row)}")
        print(f"         {''.join(f'{vx + dx:4d}'[-2:] for dx in range(-7, 8))}")


# Also: check rightward from last vertical (x=358) for all rungs
print("\n" + "=" * 70)
print("RIGHTWARD OF LAST VERTICAL (x=358): where does each rung go?")
print("=" * 70)
for ry in rung_ys:
    rx = 358
    while rx < w - 1 and binary[ry, rx] > 0:
        rx += 1
    # Skip gap
    end_x = rx
    print(f"  Rung y={ry}: foreground ends at x={end_x} (extends {end_x - 358}px past x=358)")
