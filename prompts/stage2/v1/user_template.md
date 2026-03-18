# Stage 2 User Template

Analyze this electrical schematic image. Use the pre-computed OpenCV geometry data to cross-reference your visual analysis.

## Context Files
- **Geometry JSON**: Pre-computed wire segments, chains, dashed regions, and slider detections
- **Wire Map**: Formatted text summary of Stage 1 geometry

## Your Task
Scan the ENTIRE image systematically (left-to-right, top-to-bottom) and return a JSON object with the discovery inventory (components, cables, terminals, wire labels, partition labels, crossover detection).

Trust the OpenCV slider detection results — if geometry shows slider_terminals > 0, ensure matching terminals have has_slider=true.
