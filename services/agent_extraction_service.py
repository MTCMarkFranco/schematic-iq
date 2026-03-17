"""
Stage 3 Service — Agent Extraction (Code Interpreter)

Builds the per-image user message, streams the agent response,
and extracts the structured JSON output. All agent lifecycle
(creation, file uploads, cleanup) is handled by FoundryService.
"""

import sys
import json
import base64
import time
import re

from openai.types.responses import (
    ResponseAudioDeltaEvent,
    ResponseCodeInterpreterCallCodeDeltaEvent,
    ResponseCodeInterpreterCallCodeDoneEvent,
    ResponseCodeInterpreterCallCompletedEvent,
    ResponseCodeInterpreterCallInProgressEvent,
    ResponseCodeInterpreterCallInterpretingEvent,
    ResponseCompletedEvent,
    ResponseErrorEvent,
    ResponseOutputItemDoneEvent,
    ResponseReasoningTextDeltaEvent,
    ResponseTextDeltaEvent,
)
from openai.types.responses.response_code_interpreter_tool_call import (
    ResponseCodeInterpreterToolCall,
)


# ────────────────────────────────────────────────────────────────────────────
#  USER MESSAGE BUILDER
# ────────────────────────────────────────────────────────────────────────────

def _build_user_message(geometry, discovery, wire_map, image_filename):
    """Build the per-image user message with Stage 1/2 context."""
    img_size = geometry.get("image_size", {})
    width = img_size.get("width", 0)
    height = img_size.get("height", 0)
    scale = geometry.get("scale", 1.0)

    wires = geometry.get("wires", [])
    h_wires = [w for w in wires if w.get("orientation") == "horizontal"]
    v_wires = [w for w in wires if w.get("orientation") == "vertical"]

    bus_lines = []
    if v_wires:
        max_vlen = max(w["length"] for w in v_wires)
        bus_lines = sorted(
            [w for w in v_wires if w["length"] >= max_vlen * 0.85],
            key=lambda w: w["x1"],
        )

    slider_rects = geometry.get("slider_rects", [])
    dashed_regions = geometry.get("dashed_regions", [])

    comp_list = discovery.get("components", [])
    cable_list = discovery.get("cables", [])
    term_list = discovery.get("terminals", [])
    wire_labels = discovery.get("wire_labels", [])
    has_crossovers = discovery.get("has_crossovers", False)

    def _lbl(item):
        return item["label"] if isinstance(item, dict) else item

    comp_labels = [_lbl(c) for c in comp_list]
    cable_labels = [_lbl(c) for c in cable_list]
    term_labels = [_lbl(t) for t in term_list]

    msg = f"""Analyze the attached electrical schematic image.
Write and run OpenCV code using Code Interpreter to extract ALL objects,
wire routing, terminal-to-cable assignments, and connections.

Three files have been uploaded to your Code Interpreter sandbox:
1. **{image_filename}** \u2014 the schematic image
2. **geometry.json** \u2014 Stage 1 pre-computed OpenCV geometry (authoritative)
3. **discovery.json** \u2014 Stage 2 LLM-based component/cable/terminal discovery

Load them with:
```python
import cv2, numpy as np, json, glob, os

for f in glob.glob('/mnt/data/*'):
    print(f, os.path.getsize(f))

img = cv2.imread('/mnt/data/{image_filename}')
if img is None:
    pngs = glob.glob('/mnt/data/*.png')
    if pngs:
        img = cv2.imread(pngs[0])
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
print(f"Image loaded: {{img.shape[1]}}x{{img.shape[0]}} pixels")

geo_files = glob.glob('/mnt/data/*geometry*') or glob.glob('/mnt/data/*.json')
with open(geo_files[0]) as f:
    geometry = json.load(f)

disc_files = glob.glob('/mnt/data/*discovery*')
with open(disc_files[0]) as f:
    discovery = json.load(f)
```

## IMAGE PROPERTIES
- Filename: {image_filename}
- Size: {width} x {height} pixels
- Scale factor: {scale:.1f}x

## STAGE 1 \u2014 Pre-computed Geometry (OpenCV, authoritative)

### Wire Segments ({len(wires)} total: {len(h_wires)} horizontal, {len(v_wires)} vertical)
"""

    if h_wires:
        msg += "Horizontal wires (sorted by y):\n```json\n"
        msg += json.dumps(sorted(h_wires, key=lambda w: w['y1'])[:40], indent=2)
        msg += "\n```\n\n"

    if v_wires:
        msg += "Vertical wires (sorted by x):\n```json\n"
        msg += json.dumps(sorted(v_wires, key=lambda w: w['x1'])[:25], indent=2)
        msg += "\n```\n\n"

    msg += f"""### Bus Lines ({len(bus_lines)} detected)
```json
{json.dumps(bus_lines, indent=2) if bus_lines else "[]"}
```

### Dashed Regions ({len(dashed_regions)} detected)
```json
{json.dumps(dashed_regions, indent=2) if dashed_regions else "[]"}
```

### Slider Terminals ({len(slider_rects)} detected by CV)
```json
{json.dumps(slider_rects, indent=2) if slider_rects else "[]"}
```

## STAGE 2 \u2014 Discovery (LLM inventory scan)
- Components: {', '.join(comp_labels) if comp_labels else 'None'}
- Cables: {', '.join(cable_labels) if cable_labels else 'None'}
- Terminals ({len(term_labels)}): {', '.join(term_labels) if term_labels else 'None'}
- Wire color labels: {', '.join(wire_labels) if wire_labels else 'None'}
- Has crossovers: {'Yes' if has_crossovers else 'No'}
"""

    if cable_list:
        msg += "\n### Cable Details\n"
        for c in cable_list:
            if isinstance(c, dict):
                adj = ", ".join(c.get("adjacent_labels", [])) or "none"
                opc = c.get("off_page_connector") or "none"
                msg += f"- {c['label']} @ {c.get('position', '?')} | adjacent: [{adj}] | off-page connector: {opc}\n"
            else:
                msg += f"- {c}\n"

    if term_list:
        msg += "\n### Terminal Details\n"
        for t in term_list:
            if isinstance(t, dict):
                tb = t.get("terminal_block", "?") or "?"
                slider = t.get("has_slider", False)
                slider_tag = " | SLIDER: YES" if slider else ""
                msg += f"- {t['label']} in {tb}{slider_tag}\n"
            else:
                msg += f"- {t}\n"

    if comp_list:
        msg += "\n### Component Details\n"
        for c in comp_list:
            if isinstance(c, dict):
                left = ", ".join(c.get("left_side_labels", [])) or "none"
                right = ", ".join(c.get("right_side_terminals", [])) or "none"
                msg += f"- {c['label']} @ {c.get('position', '?')} | LEFT refs: [{left}] | RIGHT terminals: [{right}]\n"
            else:
                msg += f"- {c}\n"

    wire_label_str = ', '.join(wire_labels) if wire_labels else 'R, W, B, BK'

    msg += f"""
## PRE-COMPUTED WIRE MAP
{wire_map}

## ANALYSIS STEPS
Use Code Interpreter to execute these steps sequentially.

1. **Terminal Rectangle Detection**: Detect all terminal rectangles. Expected: {len(term_labels)} terminals.
2. **Cable Circle Detection**: Find cable circles in the dashed region. Expected: {len(cable_labels)} cables.
3. **Bus Line Identification**: Identify the {len(bus_lines)} bus lines.
4. **Right-Side Wire Detection**: Check each terminal for rightward wires.
5. **Bus Intersection Analysis**: BEND vs STRAIGHT at each bus line.
6. **Jumper Pair Detection**: Identify jumpered terminal pairs.
7. **Cable Assignment**: Map bus positions to cable circles.
8. **Generate Output JSON**: Wire colors cycle through: {wire_label_str} per cable.

## OUTPUT JSON SCHEMA
Return a single JSON object:
```json
{{{{
  "objects": [
    {{{{"system_object_id": "OBJ1", "object_type": "TERMINAL", "visual_form": "rectangle", "raw_text": "964", "confidence_score": 0.9, "has_slider": false}}}},
    {{{{"system_object_id": "OBJ2", "object_type": "WIRE", "visual_form": "line", "raw_text": "R", "confidence_score": 0.95}}}},
    {{{{"system_object_id": "OBJ3", "object_type": "CABLE_LABEL", "visual_form": "circle", "raw_text": "N8000", "confidence_score": 0.95}}}},
    {{{{"system_object_id": "OBJ4", "object_type": "OFF_PAGE_CONNECTOR", "visual_form": "circle", "raw_text": "RA 530", "confidence_score": 0.9}}}}
  ],
  "connections": [
    {{{{"connection_id": "C1", "source_object_id": "OBJ1", "target_object_id": "OBJ2", "relationship_type": "DIRECT_WIRE"}}}},
    {{{{"connection_id": "C2", "source_object_id": "OBJ2", "target_object_id": "OBJ3", "relationship_type": "WIRE_TO_CABLE"}}}},
    {{{{"connection_id": "C3", "source_object_id": "OBJ3", "target_object_id": "OBJ4", "relationship_type": "CABLE_TO_CONNECTOR"}}}},
    {{{{"connection_id": "C4", "source_object_id": "OBJ1", "target_object_id": "OBJ5", "relationship_type": "JUMPER_SHORT"}}}}
  ],
  "partition_memberships": [
    {{{{"partition_id": "TB1", "member_object_id": "OBJ1"}}}}
  ]
}}}}
```

### Object Types
- TERMINAL, WIRE, CABLE_LABEL, OFF_PAGE_CONNECTOR, SYMBOLIC_COMPONENT

### Connection Types
- DIRECT_WIRE, WIRE_TO_CABLE, CABLE_TO_CONNECTOR, JUMPER_SHORT, PIN_OF, ANNOTATES

### Rules
- Every WIRE: exactly 2 connections (DIRECT_WIRE + WIRE_TO_CABLE)
- Normalize cable text: "N 8000" \u2192 "N8000"
- Cycle wire colors per cable independently
- Trust Code Interpreter results over visual estimation
- After ALL analysis, output ONLY the final JSON
"""

    return msg


# ────────────────────────────────────────────────────────────────────────────
#  AGENT EXECUTION
# ────────────────────────────────────────────────────────────────────────────

def run_agent_extraction(image_path, geometry, discovery, wire_map, console, foundry_service):
    """Execute Stage 3 extraction via Foundry Agent with Code Interpreter.

    All agent lifecycle (creation, file uploads, temp versions, cleanup)
    is delegated to foundry_service.

    Returns (parsed_extraction_dict, elapsed_seconds).
    """
    import os

    t0 = time.time()
    console.print(f"  [green]\u2714[/green] Foundry project client ready")

    # Get or create agent
    agent_name, base_version = foundry_service.get_or_create_agent()

    image_filename = os.path.basename(image_path)
    uploaded_ids = []
    temp_version = None
    final_response = None

    # Upload files for Code Interpreter
    console.print(f"  Uploading files for Code Interpreter...")

    with open(image_path, "rb") as f:
        img_id = foundry_service.upload_file_handle(f)
    uploaded_ids.append(img_id)
    console.print(f"  [green]\u2714[/green] Image uploaded ({img_id})")

    geo_bytes = json.dumps(geometry, indent=2).encode("utf-8")
    geo_id = foundry_service.upload_file("geometry.json", geo_bytes)
    uploaded_ids.append(geo_id)
    console.print(f"  [green]\u2714[/green] Geometry JSON uploaded ({geo_id})")

    disc_bytes = json.dumps(discovery, indent=2).encode("utf-8")
    disc_id = foundry_service.upload_file("discovery.json", disc_bytes)
    uploaded_ids.append(disc_id)
    console.print(f"  [green]\u2714[/green] Discovery JSON uploaded ({disc_id})")

    rule_ids = foundry_service.upload_rule_files()
    uploaded_ids.extend(rule_ids)

    try:
        # Create temp agent version with all uploaded files
        temp_version = foundry_service.create_temp_agent_version(uploaded_ids)

        user_message = _build_user_message(geometry, discovery, wire_map, image_filename)

        # Encode a low-res thumbnail for visual context (full image is in CI files)
        import cv2
        _img = cv2.imread(image_path)
        _h, _w = _img.shape[:2]
        _max_dim = 1024
        if max(_h, _w) > _max_dim:
            _scale = _max_dim / max(_h, _w)
            _img = cv2.resize(_img, (int(_w * _scale), int(_h * _scale)),
                              interpolation=cv2.INTER_AREA)
        _, _buf = cv2.imencode('.png', _img)
        image_b64 = base64.b64encode(_buf.tobytes()).decode()
        console.print(
            f"  [dim]Inline thumbnail: {_img.shape[1]}x{_img.shape[0]} "
            f"({len(image_b64) // 1024}KB b64)[/dim]"
        )

        input_content = [
            {"type": "input_text", "text": user_message},
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{image_b64}",
            },
        ]

        # Stream agent response (with retry for transient 500 errors)
        max_retries = 2
        for attempt in range(1, max_retries + 2):
            console.print(
                f"  Running agent [bold]{agent_name}[/bold] v{temp_version} "
                f"(streaming{f', attempt {attempt}' if attempt > 1 else ''})...\n"
            )
            try:
                stream = foundry_service.stream_agent_response(input_content, temp_version)
                full_text, ci_call_count, final_response = _process_stream(stream, t0)
                break
            except Exception as stream_err:
                err_name = type(stream_err).__name__
                is_server_error = "APIError" in err_name or "InternalServerError" in err_name
                if is_server_error and attempt <= max_retries:
                    wait = 30 * attempt
                    console.print(
                        f"  [yellow]\u26a0[/yellow] Server error (attempt {attempt}/{max_retries + 1}), "
                        f"retrying in {wait}s..."
                    )
                    time.sleep(wait)
                    t0 = time.time()  # reset timer for next attempt
                else:
                    raise

        output_text = full_text.strip()
        console.print(
            f"  [green]\u2714[/green] Agent streaming complete "
            f"({len(output_text):,} chars, {ci_call_count} CI calls)"
        )

        # Extract JSON from response
        parsed = _extract_json(output_text)

        if parsed is None and output_text:
            console.print(
                f"  [yellow]\u26a0[/yellow] No valid JSON in streamed output, "
                f"requesting structured output..."
            )
            response2 = foundry_service.follow_up_agent_response(
                previous_response_id=final_response.id if final_response else None,
                agent_version=temp_version,
                prompt=(
                    "Your analysis is complete. Now output ONLY the final "
                    "JSON extraction object with 'objects', 'connections', "
                    "and 'partition_memberships' arrays. "
                    "No markdown code fences. No explanation. "
                    "Start with { and end with }."
                ),
            )
            output_text2 = response2.output_text or ""
            console.print(
                f"  [green]\u2714[/green] Follow-up response ({len(output_text2):,} chars)"
            )
            parsed = _extract_json(output_text2)

        if parsed is None:
            preview = (output_text or "")[:500]
            raise RuntimeError(f"Agent did not produce valid JSON. Preview: {preview}")

    except Exception as exc:
        console.print(f"  [red]\u2717[/red] Agent call failed: {type(exc).__name__}: {exc}")
        raise
    finally:
        foundry_service.cleanup_resources(temp_version, uploaded_ids)

    elapsed = time.time() - t0
    return parsed, elapsed


def _process_stream(stream, start_time):
    """Process streaming events from the agent. Returns (full_text, ci_call_count, final_response)."""
    full_text = ""
    ci_call_count = 0
    in_code_block = False
    keepalive_count = 0
    last_status_time = time.time()
    final_response = None

    for event in stream:
        etype = getattr(event, 'type', '')

        if etype == 'keepalive' or (
            isinstance(event, ResponseAudioDeltaEvent) and event.delta is None
        ):
            keepalive_count += 1
            elapsed = time.time() - start_time
            if time.time() - last_status_time >= 10:
                sys.stdout.write(
                    f"\r\033[2m  \u23f3 Agent processing... "
                    f"{elapsed:.0f}s elapsed "
                    f"({'\u00b7' * min(keepalive_count, 30)})\033[0m"
                )
                sys.stdout.flush()
                last_status_time = time.time()
            continue

        if keepalive_count > 0 and etype != 'keepalive':
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            keepalive_count = 0

        if isinstance(event, ResponseReasoningTextDeltaEvent):
            sys.stdout.write(f"\033[2m{event.delta}\033[0m")
            sys.stdout.flush()

        elif isinstance(event, ResponseCodeInterpreterCallInProgressEvent):
            ci_call_count += 1
            print(f"\n\033[36m{'─'*60}\033[0m")
            print(f"\033[36m\u25b6 Code Interpreter call #{ci_call_count}\033[0m")
            print(f"\033[36m{'─'*60}\033[0m")

        elif isinstance(event, ResponseCodeInterpreterCallCodeDeltaEvent):
            if not in_code_block:
                print("\033[33m```python\033[0m")
                in_code_block = True
            sys.stdout.write(f"\033[33m{event.delta}\033[0m")
            sys.stdout.flush()

        elif isinstance(event, ResponseCodeInterpreterCallCodeDoneEvent):
            if in_code_block:
                print("\n\033[33m```\033[0m")
                in_code_block = False

        elif isinstance(event, ResponseCodeInterpreterCallInterpretingEvent):
            print("\033[35m\u23f3 Executing code...\033[0m")

        elif isinstance(event, ResponseCodeInterpreterCallCompletedEvent):
            if in_code_block:
                print("\n\033[33m```\033[0m")
                in_code_block = False
            print(f"\033[36m\u2714 Code Interpreter call #{ci_call_count} completed\033[0m")

        elif isinstance(event, ResponseOutputItemDoneEvent):
            item = event.item
            if isinstance(item, ResponseCodeInterpreterToolCall):
                if item.outputs:
                    for out in item.outputs:
                        if out.type == "logs" and out.logs:
                            lines = out.logs.strip().split('\n')
                            preview = lines[:80]
                            print(f"\033[32m\u250c\u2500\u2500 Output ({len(lines)} lines) \u2500\u2500\033[0m")
                            for line in preview:
                                print(f"\033[32m\u2502 {line}\033[0m")
                            if len(lines) > 80:
                                print(f"\033[32m\u2502 ... ({len(lines) - 80} more lines)\033[0m")
                            print(f"\033[32m\u2514{'─'*40}\033[0m")
                        elif out.type == "image":
                            print(f"\033[34m\ud83d\udcca [Image generated]\033[0m")
                if item.status == "failed":
                    print(f"\033[31m\u2717 Code Interpreter call failed\033[0m")
                elif item.status == "incomplete":
                    print(f"\033[33m\u26a0 Code Interpreter call incomplete\033[0m")

        elif isinstance(event, ResponseTextDeltaEvent):
            full_text += event.delta
            sys.stdout.write(event.delta)
            sys.stdout.flush()

        elif isinstance(event, ResponseCompletedEvent):
            final_response = event.response
            if not full_text and hasattr(final_response, 'output_text'):
                full_text = final_response.output_text or ""
            # Diagnostic: show response structure when output is empty
            if not full_text:
                _out = getattr(final_response, 'output', None)
                _status = getattr(final_response, 'status', 'unknown')
                _usage = getattr(final_response, 'usage', None)
                print(f"\n\033[33m  diag: status={_status}, "
                      f"output_items={len(_out) if _out else 0}, "
                      f"usage={_usage}\033[0m")
                if _out:
                    for _i, _item in enumerate(_out[:5]):
                        _itype = getattr(_item, 'type', type(_item).__name__)
                        _itext = getattr(_item, 'text', None)
                        _istatus = getattr(_item, 'status', None)
                        print(f"\033[33m  diag: output[{_i}] type={_itype} "
                              f"status={_istatus} "
                              f"text_len={len(_itext) if _itext else 0}\033[0m")
                        # Try to recover text from output items
                        if _itext and not full_text:
                            full_text = _itext

        elif isinstance(event, ResponseErrorEvent):
            print(f"\n\033[31m\u2717 Stream error: {event}\033[0m")

    print()
    return full_text, ci_call_count, final_response


# ────────────────────────────────────────────────────────────────────────────
#  JSON EXTRACTION HELPER
# ────────────────────────────────────────────────────────────────────────────

def _extract_json(text):
    """Extract a JSON object from text that may contain markdown or explanation."""
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    patterns = [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    start = text.find('{')
    if start >= 0:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break

    return None
