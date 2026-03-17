# ⚡ SCHEMATIC-IQ — Electrical Schematic Extraction Pipeline

> **AI-powered reverse engineering of electrical control schematics into structured, machine-readable JSON — achieving 95–99% extraction accuracy through an agentic Code Interpreter pipeline.**

![Pipeline](https://img.shields.io/badge/Pipeline-3%20Stages-blue?style=for-the-badge&logo=lightning)
![OpenCV](https://img.shields.io/badge/Stage%201-OpenCV-green?style=for-the-badge&logo=opencv)
![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-0078D4?style=for-the-badge&logo=microsoftazure)
![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=for-the-badge&logo=python)

---

```
  ╔═╗╔═╗╦ ╦╔═╗╔╦╗╔═╗╔╦╗╦╔═╗  ╦╔═╗
  ╚═╗║  ╠═╣║╣ ║║║╠═╣ ║ ║║    ║║ ╣
  ╚═╝╚═╝╩ ╩╚═╝╩ ╩╩ ╩ ╩ ╩╚═╝  ╩╚═╝
  Electrical Schematic Extraction Pipeline
```

---

## 🏗️ Architecture — 3-Stage Agentic Pipeline

Schematic-IQ converts complex electrical schematic diagrams (CAD exports, PDFs, raster images) into fully structured JSON — capturing every component, wire, cable, terminal, and connection with pixel-level precision.

### The Breakthrough: Agentic Code Interpreter

Early iterations of this pipeline used reasoning models (o1) to interpret wire routing from raw pixels — and consistently hit a ceiling around 60–80% accuracy. **The fundamental problem: asking an LLM to visually trace dense, criss-crossing wires through bus lines and crossovers is unreliable**, no matter how much reasoning budget you give it.

The breakthrough came from flipping the approach: **instead of asking the LLM to *see* the wires, we ask it to *write deterministic OpenCV code* that traces them**. By deploying an Azure AI Foundry Agent with Code Interpreter, the agent writes and executes custom Python/OpenCV analysis code against the actual image pixels — producing deterministic, reproducible results that don't hallucinate.

This agentic approach, guided by pre-computed geometry and a discovery inventory from earlier stages, achieves **95–99% extraction accuracy** across diverse schematic styles.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   📐 STAGE 1            🔍 STAGE 2              🤖 STAGE 3                   │
│   OpenCV Geometry    →   LLM Discovery       →   Agentic Extraction          │
│   (~1s)                  (~8s, gpt-4o-mini)      (~5min, gpt-5.4-pro + CI)   │
│                                                                               │
│   Wire masks             Component inventory     Agent writes & executes      │
│   Hough line detect      Cable/terminal map      custom OpenCV code per       │
│   Chain merging          Spatial layout           image in Code Interpreter   │
│   Slider detection       Crossover detection     Deterministic wire tracing   │
│   Bus line geometry      Wire label inventory    95–99% accuracy              │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

<p align="center">
  <img src="https://img.shields.io/badge/Stage%201-OpenCV-brightgreen?style=flat-square" />
  ➡️
  <img src="https://img.shields.io/badge/Stage%202-Discovery-purple?style=flat-square" />
  ➡️
  <img src="https://img.shields.io/badge/Stage%203-Agent%20+%20Code%20Interpreter-blue?style=flat-square" />
</p>

---

## 📐 Stage 1 — OpenCV Geometry Extraction

> **Deterministic computer vision — the foundation everything else builds on.**

Electrical schematics are *dense* — dozens of criss-crossing wires, tiny text labels, crossover junctions, and tightly packed symbols. Stage 1 uses **OpenCV** to extract deterministic, pixel-exact wire geometry *before* any LLM sees the image.

**What it does:**
- **Morphological wire extraction** — Long thin kernels (horizontal & vertical) isolate wire-like features while destroying text strokes and symbol noise
- **Hough Line Transform** — Detects precise wire segments with sub-pixel accuracy
- **Collinear segment merging** — Joins fragmented wire pieces into continuous chains
- **Wire chain building** — Groups connected segments into logical wire paths
- **Dashed region detection** — Identifies terminal block partition boundaries
- **Slider terminal detection** — Locates slider contact markers via rectangle analysis
- **Cable routing map** — Computes cable circle positions and bus line intersections
- **Terminal wire analysis** — Detects which terminals have rightward wires vs. jumper connections

**What it produces:**
```json
{
  "image_size": { "width": 3072, "height": 2304 },
  "scale": 2.0,
  "wires": [ { "x1": 450, "y1": 820, "x2": 1200, "y2": 820, "orientation": "horizontal", "length": 750 } ],
  "wire_chains": [ { "chain_id": 0, "wire_indices": [3, 7, 12] } ],
  "dashed_regions": [ { "x": 100, "y": 200, "width": 400, "height": 1800 } ],
  "slider_rects": [ { "x": 150, "y": 600, "width": 30, "height": 45 } ],
  "summary": { "wires": 47, "wire_chains": 12, "dashed_regions": 2, "slider_terminals": 3 }
}
```

**Why this matters:** The agent in Stage 3 receives this structured geometry as authoritative ground truth. Instead of guessing where wires go, the agent's Code Interpreter code can load exact pixel coordinates and trace connections deterministically.

---

## 🔍 Stage 2 — Discovery (LLM Inventory Scan)

> **Fast, cheap inventory scan — tells the agent exactly what to look for.**

Stage 2 runs a **multi-pass vision scan** using `gpt-4o-mini` to catalog everything visible in the diagram. This discovery inventory becomes the checklist that Stage 3's agent validates against.

**Strategy: Best-of-3 Union Merge**
- Runs **3 independent scans** of the schematic with `gpt-4o-mini`
- **Union-merges** results, deduplicating by label — catches items any single run might miss
- Cross-references CV-detected slider terminals with discovered terminal labels
- Total cost: pennies. Total time: ~8 seconds.

**What it discovers:**

| Category | Examples |
|----------|----------|
| Components | `RA 530`, `RA 506B` (relay/device boxes) |
| Cables | `N8000`, `N7888`, `N6000` (cable circles) |
| Terminals | `964`, `963`, `955` (terminal block entries) |
| Wire Labels | `R`, `W`, `B`, `BK` (wire color codes) |
| Partitions | `TB1` (terminal block boundaries) |
| Crossovers | Whether wire crossings exist |

**Wire Map Supplements:** After discovery, Stage 2 also computes:
- **Cable routing map** — cable circle positions relative to bus lines
- **Terminal wire analysis** — detects jumper pairs (terminals sharing a connection without their own cable wire)

These supplements are appended to the OpenCV wire map, giving Stage 3's agent a complete spatial picture.

---

## 🤖 Stage 3 — Agentic Extraction (Foundry Agent + Code Interpreter)

> **The breakthrough: an AI agent that writes and executes its own OpenCV analysis code.**

This is where Schematic-IQ achieves its 95–99% accuracy. Instead of asking a vision model to interpret pixels directly, we deploy an **Azure AI Foundry Agent** equipped with **Code Interpreter** that:

1. **Receives** the schematic image + Stage 1 geometry + Stage 2 discovery as uploaded files
2. **Writes custom Python/OpenCV code** tailored to the specific image
3. **Executes the code** in a sandboxed environment against the actual image pixels
4. **Iterates** — running multiple Code Interpreter calls, refining detection, fixing edge cases
5. **Produces** the final structured JSON extraction

**Why this works:**
- **Deterministic wire tracing** — OpenCV morphological operations, Hough transforms, and contour analysis don't hallucinate. A wire detected at pixel (450, 820) is really there.
- **Guided by prior stages** — The agent knows exactly what terminals, cables, and components to look for (from Stage 2) and where wires physically run (from Stage 1).
- **Self-correcting** — The agent can write validation code, check its own results, and re-run analysis when something doesn't add up.
- **Domain rules** — 15+ rule files (wire routing, cable assignment, terminal block conventions, crossover handling) are uploaded to Code Interpreter as reference documents.

**Agent lifecycle (managed by FoundryService):**
```
  get_or_create_agent()          Find or create the base agent
        │
  upload_file() × N              Upload image, geometry, discovery, rules
        │
  create_temp_agent_version()    Clone base agent with uploaded files attached
        │
  stream_agent_response()        Stream the agent's analysis (5–15 CI calls)
        │
  cleanup_resources()            Delete temp version + uploaded files
```

**Post-processing & Validation:**
After the agent produces its extraction, an automated post-processing pipeline:
- Normalizes the JSON schema (object types, connection types)
- Normalizes cable labels (`N 8000` → `N8000`)
- Validates structural graph integrity (orphaned objects, missing connections, wire completeness)
- Cross-checks against Stage 2 discovery (every discovered item must appear in extraction)
- Enforces CV slider detection (overrides agent hallucinations on slider status)

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your Azure credentials

# Run the pipeline on a schematic image
python main.py path/to/schematic.png
```

### 📦 Requirements

| Package | Purpose |
|---------|---------|
| `openai` | Azure OpenAI + Foundry Agent API |
| `azure-ai-projects` | Azure AI Foundry project client |
| `azure-identity` | Entra ID authentication (DefaultAzureCredential) |
| `opencv-python-headless` | Stage 1 geometry extraction |
| `numpy` | Array operations for CV |
| `rich` | Terminal UI (progress, tables, panels) |
| `python-dotenv` | Environment config |
| `PyMuPDF` | PDF page-to-image conversion |

### 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-12-01-preview`) |
| `AZURE_OPENAI_MINI_DEPLOYMENT` | Discovery model deployment (e.g., `gpt-4o-mini`) |
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry project endpoint (for agent lifecycle) |
| `DISCOVERY_RUNS` | Number of discovery passes (default: `3`) |
| `DISCOVERY_MAX_TOKENS` | Max tokens per discovery run (default: `14000`) |

---

## 📂 Output

Each run produces timestamped outputs in the `output/` directory:

| File | Contents |
|------|----------|
| `*-stage1-geometry.json` | OpenCV wire geometry, chains, dashed regions, sliders |
| `*-stage2-discovery.json` | Component/cable/terminal inventory (union-merged) |
| `*-stage3-final.json` | ✅ Final validated extraction with all objects + connections |

---

## 📁 Project Structure

```
schematic-iq/
├── main.py                          # Pipeline orchestrator (~130 lines)
├── services/
│   ├── foundry_service.py           # Azure AI client management + agent lifecycle
│   ├── geometry_extraction_service.py  # Stage 1: OpenCV geometry extraction
│   ├── discovery_service.py         # Stage 2: LLM discovery (best-of-N merge)
│   ├── agent_extraction_service.py  # Stage 3: Agent message building + stream processing
│   └── validation_service.py        # Post-processing, validation, cross-checks
├── prompts/
│   ├── system-prompt-discovery.md           # Stage 2 chat completion system prompt
│   ├── agent-instructions-extraction.md     # Stage 3 Foundry Agent instructions
│   └── rules/                               # Domain rule library (15+ files)
│       ├── wire.md, cable.md, terminalblock.md, spatial.md, ...
│       └── validation.md
├── requirements.txt
├── output/                          # Timestamped pipeline outputs
├── scripts/                         # Utility scripts
│   ├── extract_pdf_images.py        # PDF → image conversion
│   └── bundle_*.ps1                 # SSL certificate helpers
├── docs/                            # Documentation
│   └── optimizations.md             # Evolution log & lessons learned
└── test-data/                       # Sample schematics for testing
```

---

## 📝 Future Work

### Image Segmentation with Azure Document Intelligence
- Split input images into sections using **Azure Document Intelligence** to identify diagram regions
- Process sections through the pipeline in parallel for faster throughput

### Parallel Section Processing
- Use `asyncio` for concurrent LLM/agent calls across diagram sections
- Merge step reconciles results from sections into a unified graph

---

## 🔬 Evolution & Lessons Learned

Schematic-IQ evolved through several architectural iterations before arriving at the current agentic approach. See [docs/optimizations.md](docs/optimizations.md) for the full history.

### Key Insights

| Insight | Detail |
|---------|--------|
| **Vision models can't trace wires** | Even reasoning models (o1) plateau at 60–80% accuracy when visually tracing dense wire routing. They consistently confuse crossovers with junctions. |
| **Code Interpreter is the breakthrough** | Having the agent write and execute OpenCV code produces deterministic, reproducible results — the same code will trace the same wire the same way every time. |
| **Prior stages guide the agent** | Stage 1 geometry + Stage 2 discovery give the agent a structured foundation. Without them, the agent wastes Code Interpreter calls on basic detection instead of deep analysis. |
| **Best-of-N discovery** | Running 3 cheap discovery passes and union-merging catches items any single run would miss. |
| **Domain rules matter** | 15+ rule files covering wire routing, terminal blocks, cable assignment, and crossover handling give the agent domain expertise it wouldn't have from training data alone. |
| **Hybrid CV + LLM + Agent** | The three-tier approach (classical CV → cheap LLM inventory → agentic Code Interpreter) dramatically outperforms any single-model approach. |

---

## 📊 Sample Output

### TB1 Wiring Diagram

`mermaid
graph LR
    subgraph TB1["TB1"]
        OBJ7["T-654"]
        OBJ8["T-653"]
        OBJ9["T-652"]
        OBJ10["T-651"]
        OBJ11["T-964"]
        OBJ12["T-963"]
        OBJ13["T-962"]
        OBJ14["T-961"]
        OBJ15["T-960"]
        OBJ16["T-959"]
        OBJ17["T-958"]
        OBJ18["T-957"]
        OBJ19["T-956"]
        OBJ20["T-955 🛝"]
        OBJ21["T-954"]
        OBJ22["T-953"]
        OBJ23["T-952"]
        OBJ24["T-951"]
    end

    OBJ25("Wire r")
    OBJ26("Wire w")
    OBJ27("Wire b")
    OBJ28("Wire n")
    OBJ29("Wire R")
    OBJ30("Wire W")
    OBJ31("Wire B")
    OBJ32("Wire BK")
    OBJ33("Wire 1")
    OBJ34("Wire 2")
    OBJ35("Wire 3")
    OBJ36("Wire 4")
    OBJ37("Wire R ")
    OBJ38("Wire R  ")
    OBJ39("Wire W ")
    OBJ40("Wire W  ")
    OBJ41("Wire B ")
    OBJ42("Wire B  ")
    OBJ43("Wire BK ")
    OBJ44("Wire BK  ")
    OBJ45("Wire 1 ")
    OBJ46("Wire 2 ")
    OBJ47("Wire 3 ")
    OBJ48("Wire 4 ")

    OBJ4[["Cable N8000 4C"]]
    OBJ5[["Cable N7888 4C"]]
    OBJ6[["Cable N6000 4C"]]

    OBJ25 -->|WIRE_TO_CABLE| OBJ4
    OBJ29 -->|WIRE_TO_CABLE| OBJ4
    OBJ29 -->|DIRECT_WIRE| OBJ7
    OBJ26 -->|WIRE_TO_CABLE| OBJ4
    OBJ30 -->|WIRE_TO_CABLE| OBJ4
    OBJ30 -->|DIRECT_WIRE| OBJ8
    OBJ27 -->|WIRE_TO_CABLE| OBJ4
    OBJ31 -->|WIRE_TO_CABLE| OBJ4
    OBJ31 -->|DIRECT_WIRE| OBJ9
    OBJ28 -->|WIRE_TO_CABLE| OBJ4
    OBJ32 -->|WIRE_TO_CABLE| OBJ4
    OBJ32 -->|DIRECT_WIRE| OBJ10

    OBJ33 -->|WIRE_TO_CABLE| OBJ5
    OBJ34 -->|WIRE_TO_CABLE| OBJ5
    OBJ35 -->|WIRE_TO_CABLE| OBJ5
    OBJ36 -->|WIRE_TO_CABLE| OBJ5
    OBJ37 -->|WIRE_TO_CABLE| OBJ5
    OBJ37 -->|DIRECT_WIRE| OBJ11
    OBJ39 -->|WIRE_TO_CABLE| OBJ5
    OBJ39 -->|DIRECT_WIRE| OBJ13
    OBJ41 -->|WIRE_TO_CABLE| OBJ5
    OBJ41 -->|DIRECT_WIRE| OBJ15
    OBJ43 -->|WIRE_TO_CABLE| OBJ5
    OBJ43 -->|DIRECT_WIRE| OBJ17

    OBJ38 -->|WIRE_TO_CABLE| OBJ6
    OBJ38 -->|DIRECT_WIRE| OBJ12
    OBJ40 -->|WIRE_TO_CABLE| OBJ6
    OBJ40 -->|DIRECT_WIRE| OBJ14
    OBJ42 -->|WIRE_TO_CABLE| OBJ6
    OBJ42 -->|DIRECT_WIRE| OBJ16
    OBJ44 -->|WIRE_TO_CABLE| OBJ6
    OBJ44 -->|DIRECT_WIRE| OBJ18
    OBJ45 -->|WIRE_TO_CABLE| OBJ6
    OBJ46 -->|WIRE_TO_CABLE| OBJ6
    OBJ47 -->|WIRE_TO_CABLE| OBJ6
    OBJ48 -->|WIRE_TO_CABLE| OBJ6

    classDef terminal fill:#4a90d9,stroke:#2c5282,color:#fff
    classDef unused fill:#a0aec0,stroke:#718096,color:#fff,stroke-dasharray:5 5
    classDef wire fill:#68d391,stroke:#276749,color:#000
    classDef cable fill:#f6e05e,stroke:#975a16,color:#000
    classDef connector fill:#fc8181,stroke:#9b2c2c,color:#fff
    classDef lbl fill:#d6bcfa,stroke:#6b46c1,color:#000

    class OBJ7,OBJ8,OBJ9,OBJ10,OBJ11,OBJ12,OBJ13,OBJ14,OBJ15,OBJ16,OBJ17,OBJ18,OBJ19,OBJ20,OBJ21,OBJ22,OBJ23,OBJ24 terminal
    class OBJ25,OBJ26,OBJ27,OBJ28,OBJ29,OBJ30,OBJ31,OBJ32,OBJ33,OBJ34,OBJ35,OBJ36,OBJ37,OBJ38,OBJ39,OBJ40,OBJ41,OBJ42,OBJ43,OBJ44,OBJ45,OBJ46,OBJ47,OBJ48 wire
    class OBJ4,OBJ5,OBJ6 cable
```

#### Legend

| Shape | Color | Type |
|-------|-------|------|
| Rectangle `[]` | Blue | Terminal (active) |
| Rectangle `[]` dashed | Gray | Terminal (unused) |
| Rounded `()` | Green | Wire |
| Double bracket `[[]]` | Yellow | Cable Label |
| Circle `(())` | Red | Off-page Connector |
| Rounded `()` | Purple | Label / Annotation |

#### Relationship Types

| Line Style | Meaning |
|------------|---------|
| `-->` solid arrow | DIRECT_WIRE, WIRE_TO_CABLE, CABLE_TO_CONNECTOR |
| `-.->` dashed arrow | ANNOTATES |
| `---` solid line | JUMPER_SHORT |

### Final JSON Output

`json
{
  "objects": [
    {
      "system_object_id": "OBJ1",
      "object_type": "SYMBOLIC_COMPONENT",
      "visual_form": "rectangle",
      "raw_text": "RA 530",
      "confidence_score": 0.83
    },
    {
      "system_object_id": "OBJ2",
      "object_type": "SYMBOLIC_COMPONENT",
      "visual_form": "rectangle",
      "raw_text": "RA 506B",
      "confidence_score": 0.82
    },
    {
      "system_object_id": "OBJ3",
      "object_type": "SYMBOLIC_COMPONENT",
      "visual_form": "rectangle",
      "raw_text": "RA 500B",
      "confidence_score": 0.8
    },
    {
      "system_object_id": "OBJ4",
      "object_type": "CABLE_LABEL",
      "visual_form": "circle",
      "raw_text": "N8000",
      "confidence_score": 0.93
    },
    {
      "system_object_id": "OBJ5",
      "object_type": "CABLE_LABEL",
      "visual_form": "circle",
      "raw_text": "N7888",
      "confidence_score": 0.93
    },
    {
      "system_object_id": "OBJ6",
      "object_type": "CABLE_LABEL",
      "visual_form": "circle",
      "raw_text": "N6000",
      "confidence_score": 0.92
    },
    {
      "system_object_id": "OBJ7",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "654",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ8",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "653",
      "confidence_score": 0.96,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ9",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "652",
      "confidence_score": 0.96,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ10",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "651",
      "confidence_score": 0.96,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ11",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "964",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ12",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "963",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ13",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "962",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ14",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "961",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ15",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "960",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ16",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "959",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ17",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "958",
      "confidence_score": 0.97,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ18",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "957",
      "confidence_score": 0.96,
      "has_slider": true
    },
    {
      "system_object_id": "OBJ19",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "956",
      "confidence_score": 0.95,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ20",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "955",
      "confidence_score": 0.97,
      "has_slider": true
    },
    {
      "system_object_id": "OBJ21",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "954",
      "confidence_score": 0.96,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ22",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "953",
      "confidence_score": 0.96,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ23",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "952",
      "confidence_score": 0.96,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ24",
      "object_type": "TERMINAL",
      "visual_form": "rectangle",
      "raw_text": "951",
      "confidence_score": 0.96,
      "has_slider": false
    },
    {
      "system_object_id": "OBJ25",
      "object_type": "EXTERNAL_REF",
      "visual_form": "text_label",
      "raw_text": "530",
      "confidence_score": 0.88
    },
    {
      "system_object_id": "OBJ26",
      "object_type": "EXTERNAL_REF",
      "visual_form": "text_label",
      "raw_text": "506B",
      "confidence_score": 0.85
    },
    {
      "system_object_id": "OBJ27",
      "object_type": "EXTERNAL_REF",
      "visual_form": "text_label",
      "raw_text": "500B",
      "confidence_score": 0.85
    },
    {
      "system_object_id": "OBJ28",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "fake-B10-1",
      "confidence_score": 0.9
    },
    {
      "system_object_id": "OBJ29",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "fake-B10-2",
      "confidence_score": 0.9
    },
    {
      "system_object_id": "OBJ30",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "fake-B10-9",
      "confidence_score": 0.9
    },
    {
      "system_object_id": "OBJ31",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "fake-B10-5",
      "confidence_score": 0.9
    },
    {
      "system_object_id": "OBJ32",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "fake-B18",
      "confidence_score": 0.9
    },
    {
      "system_object_id": "OBJ33",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "(fake-B18-M2)",
      "confidence_score": 0.85
    },
    {
      "system_object_id": "OBJ34",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "fake-B17-M2",
      "confidence_score": 0.85
    },
    {
      "system_object_id": "OBJ35",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "fake-STA GRD BUS",
      "confidence_score": 0.8
    },
    {
      "system_object_id": "OBJ36",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "(fake-BSC62-S2)",
      "confidence_score": 0.8
    },
    {
      "system_object_id": "OBJ37",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "(fake-BS64-S2)",
      "confidence_score": 0.8
    },
    {
      "system_object_id": "OBJ38",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "(fake-B18-S2)",
      "confidence_score": 0.8
    },
    {
      "system_object_id": "OBJ39",
      "object_type": "LABEL",
      "visual_form": "text_label",
      "raw_text": "NC",
      "confidence_score": 0.8
    },
    {
      "system_object_id": "OBJ40",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "R",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ41",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "W",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ42",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "B",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ43",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "BK",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ44",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "R",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ45",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "R",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ46",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "W",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ47",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "W",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ48",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "B",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ49",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "B",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ50",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "BK",
      "confidence_score": 0.7
    },
    {
      "system_object_id": "OBJ51",
      "object_type": "WIRE",
      "visual_form": "line",
      "raw_text": "BK",
      "confidence_score": 0.7
    }
  ],
  "connections": [
    {
      "connection_id": "C1",
      "source_object_id": "OBJ25",
      "target_object_id": "OBJ1",
      "relationship_type": "PIN_OF"
    },
    {
      "connection_id": "C2",
      "source_object_id": "OBJ26",
      "target_object_id": "OBJ2",
      "relationship_type": "PIN_OF"
    },
    {
      "connection_id": "C3",
      "source_object_id": "OBJ27",
      "target_object_id": "OBJ3",
      "relationship_type": "PIN_OF"
    },
    {
      "connection_id": "C4",
      "source_object_id": "OBJ7",
      "target_object_id": "OBJ40",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C5",
      "source_object_id": "OBJ40",
      "target_object_id": "OBJ4",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C6",
      "source_object_id": "OBJ8",
      "target_object_id": "OBJ41",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C7",
      "source_object_id": "OBJ41",
      "target_object_id": "OBJ4",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C8",
      "source_object_id": "OBJ9",
      "target_object_id": "OBJ42",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C9",
      "source_object_id": "OBJ42",
      "target_object_id": "OBJ4",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C10",
      "source_object_id": "OBJ10",
      "target_object_id": "OBJ43",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C11",
      "source_object_id": "OBJ43",
      "target_object_id": "OBJ4",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C12",
      "source_object_id": "OBJ11",
      "target_object_id": "OBJ44",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C13",
      "source_object_id": "OBJ44",
      "target_object_id": "OBJ5",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C14",
      "source_object_id": "OBJ12",
      "target_object_id": "OBJ45",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C15",
      "source_object_id": "OBJ45",
      "target_object_id": "OBJ6",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C16",
      "source_object_id": "OBJ13",
      "target_object_id": "OBJ46",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C17",
      "source_object_id": "OBJ46",
      "target_object_id": "OBJ5",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C18",
      "source_object_id": "OBJ14",
      "target_object_id": "OBJ47",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C19",
      "source_object_id": "OBJ47",
      "target_object_id": "OBJ6",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C20",
      "source_object_id": "OBJ15",
      "target_object_id": "OBJ48",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C21",
      "source_object_id": "OBJ48",
      "target_object_id": "OBJ5",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C22",
      "source_object_id": "OBJ16",
      "target_object_id": "OBJ49",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C23",
      "source_object_id": "OBJ49",
      "target_object_id": "OBJ6",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C24",
      "source_object_id": "OBJ18",
      "target_object_id": "OBJ50",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C25",
      "source_object_id": "OBJ50",
      "target_object_id": "OBJ5",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C26",
      "source_object_id": "OBJ18",
      "target_object_id": "OBJ51",
      "relationship_type": "DIRECT_WIRE"
    },
    {
      "connection_id": "C27",
      "source_object_id": "OBJ51",
      "target_object_id": "OBJ6",
      "relationship_type": "WIRE_TO_CABLE"
    },
    {
      "connection_id": "C28",
      "source_object_id": "OBJ28",
      "target_object_id": "OBJ7",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C29",
      "source_object_id": "OBJ29",
      "target_object_id": "OBJ8",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C30",
      "source_object_id": "OBJ30",
      "target_object_id": "OBJ9",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C31",
      "source_object_id": "OBJ31",
      "target_object_id": "OBJ10",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C32",
      "source_object_id": "OBJ32",
      "target_object_id": "OBJ11",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C33",
      "source_object_id": "OBJ33",
      "target_object_id": "OBJ13",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C34",
      "source_object_id": "OBJ34",
      "target_object_id": "OBJ16",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C35",
      "source_object_id": "OBJ35",
      "target_object_id": "OBJ20",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C36",
      "source_object_id": "OBJ36",
      "target_object_id": "OBJ21",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C37",
      "source_object_id": "OBJ37",
      "target_object_id": "OBJ22",
      "relationship_type": "UNRESOLVED"
    },
    {
      "connection_id": "C38",
      "source_object_id": "OBJ38",
      "target_object_id": "OBJ23",
      "relationship_type": "UNRESOLVED"
    }
  ],
  "partition_memberships": [
    { "partition_id": "TB1", "member_object_id": "OBJ1" },
    { "partition_id": "TB1", "member_object_id": "OBJ2" },
    { "partition_id": "TB1", "member_object_id": "OBJ3" },
    { "partition_id": "TB1", "member_object_id": "OBJ4" },
    { "partition_id": "TB1", "member_object_id": "OBJ5" },
    { "partition_id": "TB1", "member_object_id": "OBJ6" },
    { "partition_id": "TB1", "member_object_id": "OBJ7" },
    { "partition_id": "TB1", "member_object_id": "OBJ8" },
    { "partition_id": "TB1", "member_object_id": "OBJ9" },
    { "partition_id": "TB1", "member_object_id": "OBJ10" },
    { "partition_id": "TB1", "member_object_id": "OBJ11" },
    { "partition_id": "TB1", "member_object_id": "OBJ12" },
    { "partition_id": "TB1", "member_object_id": "OBJ13" },
    { "partition_id": "TB1", "member_object_id": "OBJ14" },
    { "partition_id": "TB1", "member_object_id": "OBJ15" },
    { "partition_id": "TB1", "member_object_id": "OBJ16" },
    { "partition_id": "TB1", "member_object_id": "OBJ17" },
    { "partition_id": "TB1", "member_object_id": "OBJ18" },
    { "partition_id": "TB1", "member_object_id": "OBJ19" },
    { "partition_id": "TB1", "member_object_id": "OBJ20" },
    { "partition_id": "TB1", "member_object_id": "OBJ21" },
    { "partition_id": "TB1", "member_object_id": "OBJ22" },
    { "partition_id": "TB1", "member_object_id": "OBJ23" },
    { "partition_id": "TB1", "member_object_id": "OBJ24" },
    { "partition_id": "TB1", "member_object_id": "OBJ25" },
    { "partition_id": "TB1", "member_object_id": "OBJ26" },
    { "partition_id": "TB1", "member_object_id": "OBJ27" },
    { "partition_id": "TB1", "member_object_id": "OBJ28" },
    { "partition_id": "TB1", "member_object_id": "OBJ29" },
    { "partition_id": "TB1", "member_object_id": "OBJ30" },
    { "partition_id": "TB1", "member_object_id": "OBJ31" },
    { "partition_id": "TB1", "member_object_id": "OBJ32" },
    { "partition_id": "TB1", "member_object_id": "OBJ33" },
    { "partition_id": "TB1", "member_object_id": "OBJ34" },
    { "partition_id": "TB1", "member_object_id": "OBJ35" },
    { "partition_id": "TB1", "member_object_id": "OBJ36" },
    { "partition_id": "TB1", "member_object_id": "OBJ37" },
    { "partition_id": "TB1", "member_object_id": "OBJ38" },
    { "partition_id": "TB1", "member_object_id": "OBJ39" },
    { "partition_id": "TB1", "member_object_id": "OBJ40" },
    { "partition_id": "TB1", "member_object_id": "OBJ41" },
    { "partition_id": "TB1", "member_object_id": "OBJ42" },
    { "partition_id": "TB1", "member_object_id": "OBJ43" },
    { "partition_id": "TB1", "member_object_id": "OBJ44" },
    { "partition_id": "TB1", "member_object_id": "OBJ45" },
    { "partition_id": "TB1", "member_object_id": "OBJ46" },
    { "partition_id": "TB1", "member_object_id": "OBJ47" },
    { "partition_id": "TB1", "member_object_id": "OBJ48" },
    { "partition_id": "TB1", "member_object_id": "OBJ49" },
    { "partition_id": "TB1", "member_object_id": "OBJ50" },
    { "partition_id": "TB1", "member_object_id": "OBJ51" }
  ]
}
```

-

---

<p align="center">
  <b>⚡ Built with Schematic-IQ — Powering electrical infrastructure digitization ⚡</b>
</p>
