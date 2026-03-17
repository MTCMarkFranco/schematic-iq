# Optimization Log — Electrical Schematic Extraction

## Architecture Evolution

Schematic-IQ went through three major architectural phases to reach 95–99% extraction accuracy.

### Phase 1: Pure LLM Extraction (o1 reasoning model)

The initial approach sent the schematic image directly to an o1 reasoning model with a detailed extraction prompt. The model was asked to visually trace every wire from source to destination and produce structured JSON.

**Result:** 60–80% accuracy. The model consistently confused wire crossovers with junctions, misrouted wires through dense bus lines, and hallucinated connections that didn't exist. Increasing reasoning budget and prompt refinement helped marginally but couldn't overcome the fundamental limitation: **vision models can't reliably trace lines through dense, criss-crossing wire bundles**.

### Phase 2: Hybrid CV + LLM (OpenCV geometry + o1 extraction)

Added a deterministic OpenCV pre-processing stage that extracted wire geometry (Hough lines, chain merging, collinear segments) before passing to the LLM. The model now received both the image and a structured wire map.

**Result:** ~80–85% accuracy. The wire map helped the model understand spatial layout, but it still relied on visual interpretation for the actual wire-to-cable routing decisions. Crossover confusion remained the dominant error.

### Phase 3: Agentic Code Interpreter (current architecture)

**The breakthrough.** Instead of asking the model to *see* the wires, we ask it to *write deterministic OpenCV code* that traces them. An Azure AI Foundry Agent with Code Interpreter:

1. Receives the image + Stage 1 geometry + Stage 2 discovery as uploaded files
2. Writes and executes custom Python/OpenCV analysis code per-image
3. Produces deterministic, reproducible wire tracing results
4. Iterates through multiple Code Interpreter calls, self-correcting as needed

**Result:** 95–99% accuracy. The agent's code-based approach eliminates hallucination — a Hough line detected at pixel (450, 820) is verifiably there. Domain rules (15+ files) give the agent expertise in terminal block conventions, crossover handling, and cable assignment.

---

## Current Architecture: 3-Stage Agentic Pipeline

| Stage | Model | Time | Purpose |
|-------|-------|------|---------|
| **Stage 1** — OpenCV Geometry | None (classical CV) | ~1s | Wire masks, Hough lines, chain merging, slider detection |
| **Stage 2** — Discovery | gpt-4o-mini (×3 runs) | ~8s | Component/cable/terminal inventory, best-of-3 union merge |
| **Stage 3** — Agentic Extraction | gpt-5.4-pro + Code Interpreter | ~5min | Agent writes & executes OpenCV code, deterministic wire tracing |

---

## What Didn't Work

### 1. Direct vision-based wire tracing (any model)
Asking o1, GPT-4o, or GPT-4o-mini to visually trace wires consistently failed at crossovers. The models confuse crossing wires with connected wires, especially in dense bus line regions.

### 2. Sending wire crossover reference images
Adding a second image (wire crossover diagram) as context **degraded accuracy** to 0–1/5. The extra visual input confused the model's interpretation of the primary schematic.

### 3. Low/medium reasoning effort
Setting `reasoning_effort="low"` or `"medium"` significantly degraded connectivity accuracy when using reasoning models. Wire tracing requires deep reasoning.

### 4. Insufficient token budgets
Reasoning models use a large portion of tokens for internal chain-of-thought (e.g., 10K reasoning tokens for 1.4K output tokens). Always set `max_completion_tokens` well above expected output size.

### 5. Generic "Process the image" prompts
Without explicit tracing instructions and domain-specific rules, models consistently misrouted wires. Prompt specificity matters more than model parameter tuning.

### 6. Single-pass discovery
A single discovery run misses 10–15% of components on dense schematics. The best-of-3 union merge strategy catches items any single run would miss.

---

## What Worked

### 1. Agentic Code Interpreter (the breakthrough)
Having the agent write and execute its own OpenCV analysis code produces deterministic, reproducible results. The same code traces the same wire the same way every time — no hallucination.

### 2. Three-tier hybrid approach
Classical CV (Stage 1) → cheap LLM inventory (Stage 2) → agentic Code Interpreter (Stage 3). Each stage builds on the last, and the agent receives authoritative guidance rather than starting from scratch.

### 3. Domain rule library
15+ rule files covering wire routing, terminal blocks, cable assignment, crossover handling, and validation. These give the agent domain expertise it wouldn't have from training data alone.

### 4. Best-of-N discovery
Running 3 cheap `gpt-4o-mini` passes and union-merging catches items any single run would miss. Cost: pennies. Time: ~8 seconds.

### 5. CV slider enforcement
Using OpenCV-detected slider rectangles as ground truth and overriding the agent's slider predictions. The agent occasionally hallucinates slider contacts; the CV detection is deterministic.

### 6. Post-processing graph validation
Structural checks (orphan detection, terminal completeness, wire integrity, connector reachability) catch systematic errors the agent introduces, allowing automated correction.

---

## Key Insights

| Insight | Detail |
|---------|--------|
| **Vision models can't trace wires** | Even o1 plateaus at 60–80% on dense wire routing. Crossover vs. junction confusion is the dominant error. |
| **Code Interpreter is the breakthrough** | Agent-written OpenCV code produces deterministic results — no hallucination. |
| **Prior stages guide the agent** | Without Stage 1/2 data, the agent wastes Code Interpreter calls on basic detection instead of deep analysis. |
| **Prompt specificity > model params** | A well-structured prompt outperforms all parameter tuning. |
| **Fewer images is better** | Sending only the primary schematic (no reference images) produces better results. |
| **Domain rules matter** | 15+ rule files give the agent domain expertise absent from training data. |

---

## Ground Truth Signal Paths (Test Image)

| # | Source Component | Destination Connector | Wire |
|---|---|---|---|
| 1 | EAX | N 2961 (PB 820A) | (+)BK |
| 2 | ARP | N 2961 (PB 820A) | (+)BK |
| 3 | ARR (top) | N 7320 (PB 484B) | (-)W |
| 4 | EAR | N 7320 (PB 484B) | (-)W |
| 5 | ARR (bottom) | N 1807 (PB 430A) | (-)W |
