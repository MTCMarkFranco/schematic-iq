# Copilot-Ready PR Plan — *schematic-iq* (commit-by-commit checklist)

> **Goal:** Implement improvements **incrementally** in `services/*`, `prompts/*`, and `docs/*` without breaking the current **95–99% extraction accuracy path** described in the repo README. citeturn7search172
>
> **How to use (Copilot / Claude Opus agent mode):**
> 1. Create a new branch: `git checkout -b chore/pr-plan-hardening`.
> 2. Execute commits **in order** below. Each commit is designed to be independently shippable.
> 3. After each commit: run the **commands** in the “Verification” section and ensure acceptance criteria pass.
>
> **Repo context (from GitHub):** root contains `docs/`, `prompts/`, `services/`, `scripts/`, `test-data/`, `output/`, plus `main.py` and `requirements.txt`. citeturn7search172

---

## Guiding principles (non-negotiables)

- **Protect the current path:** Stage 1/2/3 behavior must remain the default until tests prove parity.
- **Determinism first:** Any new logic must be measurable, reproducible, and regression-tested.
- **Contracts everywhere:** Intermediate representations must be validated (schema + invariants).
- **No “big bang” refactor:** Every commit must leave the repo runnable.

---

## Pre-flight (one-time) — define “golden” invariants

### Baseline invariants (freeze these early)

- Stage 1 output is deterministic given the same input image.
- Stage 2 output is repeatable under a fixed model+seed/temperature configuration.
- Stage 3 output JSON conforms to schema and matches golden files for `test-data/*`.

---

# Commit-by-commit checklist

Each commit below includes:
- **Commit message** (use exactly)
- **Scope** (what to change)
- **Files** (where to put things)
- **Acceptance** (what must be true)
- **Verification** (commands)

> **NOTE:** Where the plan says “create file”, create it even if it starts minimal (scaffold). Expand in later commits.

---

## 1) Add a safety net: test harness + golden outputs (no logic changes)

**Commit:** `test: add golden harness for stage outputs`

**Scope**
- Introduce a minimal regression harness that can run the existing pipeline on a small fixture set and compare outputs.
- Add “golden” expected JSON outputs for current behavior.

**Files**
- `services/testing/__init__.py`
- `services/testing/golden.py` — helpers to load fixtures and compare JSON with stable sorting
- `services/testing/snapshot.py` — snapshot writer (optional)
- `test-data/fixtures/` — copy 2–5 representative images (or reference existing ones)
- `test-data/golden/` — expected outputs per fixture (`*.json`)
- `scripts/run_regression.py` — CLI that runs pipeline on fixtures and compares to golden
- `requirements.txt` — add `pytest` if not present
- `docs/testing.md` — how to run regression

**Acceptance**
- `scripts/run_regression.py` runs successfully and reports PASS using current code path.
- No changes to pipeline logic.

**Verification**
- `python scripts/run_regression.py --help`
- `python scripts/run_regression.py --suite smoke`

---

## 2) Introduce strict JSON schema for final output (validate only)

**Commit:** `feat: add json schema for final extraction output`

**Scope**
- Define a JSON Schema for the final structured output.
- Add validation step **after** Stage 3 (do not change extraction).

**Files**
- `services/schema/final_output.schema.json`
- `services/schema/validate.py` — `validate_final_output(data) -> (ok, errors)`
- `services/schema/__init__.py`
- `docs/schema.md` — what the schema covers and versioning approach

**Acceptance**
- Existing golden outputs validate cleanly.
- Regression suite still passes.

**Verification**
- `python scripts/run_regression.py --suite smoke`

---

## 3) Standardize config (models, temperature, seeds, timeouts) without altering defaults

**Commit:** `chore: add config layer with zero behavior change`

**Scope**
- Centralize run configuration (model names, temperature, seeds, max tokens, timeouts).
- Ensure defaults match current behavior.

**Files**
- `services/config/defaults.py`
- `services/config/types.py` (dataclasses / pydantic models)
- `services/config/load.py` (env + optional `config.yaml`)
- `docs/config.md`

**Acceptance**
- Running `main.py` with no config behaves exactly as before.
- Regression suite passes.

**Verification**
- `python scripts/run_regression.py --suite smoke`

---

## 4) Formalize Stage contracts (IR = Intermediate Representation)

**Commit:** `feat: add intermediate representation contracts for stages`

**Scope**
- Define typed IR objects for Stage 1 and Stage 2 outputs.
- Add lightweight validators (invariants) without changing computation.

**Files**
- `services/ir/stage1.py` — e.g., `WireMask`, `LineSegment`, `Junction`, `BusLine`
- `services/ir/stage2.py` — e.g., `Component`, `Terminal`, `Cable`, `SpatialLayout`
- `services/ir/validate.py`
- `services/ir/__init__.py`
- `docs/ir.md`

**Acceptance**
- IR objects can be created from current Stage outputs.
- Validators run and pass for the smoke fixtures.

**Verification**
- `python scripts/run_regression.py --suite smoke`

---

## 5) Organize prompts with versioning + “policy pack”

**Commit:** `chore: version prompts and add policy pack scaffolding`

**Scope**
- Ensure prompts are stored in a consistent structure with explicit versions.
- Add a reusable “policy pack” markdown that Stage 3 always includes.

**Files**
- `prompts/stage2/v1/system.md`
- `prompts/stage2/v1/user_template.md`
- `prompts/stage3/v1/system.md`
- `prompts/stage3/v1/policy_pack.md` — your deterministic rules, schema reminders, JSON constraints
- `prompts/_shared/json_rules.md` — generic JSON-only rules
- `services/prompts/loader.py` — loads prompt sets by stage+version
- `docs/prompts.md` — prompt versioning and how to add v2

**Acceptance**
- Stage 2 and Stage 3 still use existing prompt text (copied into v1 files).
- Regression suite passes.

**Verification**
- `python scripts/run_regression.py --suite smoke`

---

## 6) Add deterministic preprocessing “library” (refactor-only)

**Commit:** `refactor: extract stage1 opencv geometry into services/stage1`

**Scope**
- Move Stage 1 OpenCV geometry into a clean module boundary.
- No algorithm changes.

**Files**
- `services/stage1/__init__.py`
- `services/stage1/geometry.py`
- `services/stage1/wire_masks.py`
- `services/stage1/junctions.py`
- `services/stage1/bus_lines.py`
- `docs/stage1.md`

**Acceptance**
- Same outputs byte-for-byte for smoke fixtures.

**Verification**
- `python scripts/run_regression.py --suite smoke --strict`

---

## 7) Extract Stage 2 discovery into services/stage2 (refactor-only)

**Commit:** `refactor: isolate stage2 discovery into services/stage2`

**Scope**
- Move Stage 2 discovery logic into a dedicated module.
- Ensure Stage 2 produces the same inventory fields.

**Files**
- `services/stage2/__init__.py`
- `services/stage2/discovery.py`
- `services/stage2/spatial_layout.py`
- `services/stage2/cable_terminal_map.py`
- `services/stage2/labels.py`
- `docs/stage2.md`

**Acceptance**
- Same Stage 2 IR for smoke fixtures.

**Verification**
- `python scripts/run_regression.py --suite smoke --strict`

---

## 8) Wrap Stage 3 agentic execution behind a single interface

**Commit:** `feat: add stage3 executor interface and keep current path default`

**Scope**
- Add a `Stage3Executor` interface so you can later introduce alternate executors (e.g., local, cached, replay).
- Default implementation calls the current GPT-5.4-pro + Code Interpreter flow as-is. citeturn7search172

**Files**
- `services/stage3/__init__.py`
- `services/stage3/executor.py` — interface + `DefaultAgenticExecutor`
- `services/stage3/prompting.py` — assembles image + IR + policy pack
- `docs/stage3.md`

**Acceptance**
- No output changes.
- Regression suite passes.

**Verification**
- `python scripts/run_regression.py --suite smoke --strict`

---

## 9) Add “replay mode” (run Stage 3 from saved tool artifacts)

**Commit:** `feat: add replay mode for stage3 to improve determinism and debugging`

**Scope**
- Allow Stage 3 to save/restore artifacts:
  - final JSON
  - code interpreter python script(s)
  - intermediate images (cropped regions, masks)
- Make it possible to reproduce a run without calling the model.

**Files**
- `services/stage3/replay.py`
- `output/runs/<run_id>/...` (ensure `.gitignore` excludes generated)
- `docs/replay.md`
- `scripts/replay_run.py`

**Acceptance**
- You can run a fixture once, then rerun in replay mode and get identical JSON.

**Verification**
- `python scripts/run_regression.py --suite smoke`
- `python scripts/replay_run.py --run output/runs/<id>`

---

## 10) Add post-processing normalizer (stable ordering, ID canonicalization)

**Commit:** `feat: add deterministic json normalization for stable diffs`

**Scope**
- Implement a normalizer that:
  - sorts arrays by stable keys
  - canonicalizes IDs (optional)
  - removes nondeterministic fields (timestamps) from comparison output

**Files**
- `services/postprocess/normalize.py`
- `services/postprocess/__init__.py`
- Update `services/testing/golden.py` to use normalizer
- `docs/postprocess.md`

**Acceptance**
- Golden comparisons become more stable and diff-friendly.
- No functional output change (only normalization on compare/save).

**Verification**
- `python scripts/run_regression.py --suite smoke --strict`

---

## 11) Add junction/merge “truth table” tests (protect your hard problem)

**Commit:** `test: add targeted unit tests for junction ambiguity cases`

**Scope**
- Create micro-fixtures that specifically stress:
  - multi-wire junctions
  - crossovers vs joins
  - bus line taps

**Files**
- `test-data/micro/` (small crops)
- `services/stage1/tests/test_junctions.py`
- `services/stage1/tests/test_crossovers.py`
- `docs/test_cases.md`

**Acceptance**
- Unit tests pass.
- Regression suite passes.

**Verification**
- `pytest -q`
- `python scripts/run_regression.py --suite smoke`

---

## 12) Add metrics + trace logs (no vendor lock-in)

**Commit:** `feat: add structured logging and per-stage timing metrics`

**Scope**
- Introduce structured logs with:
  - stage timings
  - counts (components, wires, junctions)
  - validation errors (schema)

**Files**
- `services/telemetry/logger.py`
- `services/telemetry/metrics.py`
- Update `main.py` to emit metrics
- `docs/observability.md`

**Acceptance**
- Logs are JSON lines to stdout by default.
- Regression suite passes.

**Verification**
- `python scripts/run_regression.py --suite smoke --log-level info`

---

## 13) Add “fail-closed” behavior + clear error taxonomy

**Commit:** `feat: add error taxonomy and fail-closed validation gates`

**Scope**
- Define error classes (Stage1Error, Stage2Error, Stage3Error, SchemaError).
- If schema validation fails, pipeline returns non-zero exit and saves artifacts.

**Files**
- `services/errors.py`
- Update `services/schema/validate.py` usage
- Update `main.py` exit codes
- `docs/errors.md`

**Acceptance**
- On invalid JSON, run fails clearly, artifacts saved.
- Smoke regression still passes.

**Verification**
- `python scripts/run_regression.py --suite smoke`

---

## 14) Add a “compat mode” switch for future changes

**Commit:** `feat: add pipeline compatibility modes (v1 default)`

**Scope**
- Allow selecting `pipeline_mode=v1` (current) vs `pipeline_mode=v2` (future).
- v1 remains the default for stability.

**Files**
- `services/pipeline/modes.py`
- `services/pipeline/run.py`
- Update `main.py` to use `services/pipeline/run.py`
- `docs/pipeline_modes.md`

**Acceptance**
- v1 equals current behavior.

**Verification**
- `python scripts/run_regression.py --suite smoke --strict`

---

## 15) (Optional) Add a lightweight symbol detector plug-in (no training required)

**Commit:** `feat: add optional template-based symbol detector plugin (off by default)`

**Scope**
- Add a plugin mechanism that can enrich Stage 2 inventory with:
  - template matching candidates
  - confidence scores
- Keep OFF by default to avoid regressions.

**Files**
- `services/plugins/__init__.py`
- `services/plugins/template_symbols.py`
- `docs/plugins.md`

**Acceptance**
- Default pipeline unchanged.
- Plugin can be enabled via config.

**Verification**
- `python scripts/run_regression.py --suite smoke`

---

## 16) Add CI workflow to prevent regressions (GitHub Actions)

**Commit:** `ci: add regression workflow to protect 95–99% path`

**Scope**
- Add a workflow that runs:
  - unit tests
  - smoke regression suite (no external model calls if fixtures are replayable)

**Files**
- `.github/workflows/ci.yml`
- `docs/ci.md`

**Acceptance**
- CI passes on main branch for smoke suite.

**Verification**
- `act` locally (optional) or rely on GitHub Actions

---

# Implementation notes for Copilot Agent (Claude Opus mode)

## Execution discipline

- **Never edit prompts and algorithms in the same commit**.
- **Keep commits small** (one intent per commit).
- **After each commit:** run regression suite.
- **If any diff appears:** stop and either (a) revert or (b) put behavior behind a feature flag (config switch).

## Definitions

- **Golden outputs** live in `test-data/golden/` and must match normalized output.
- **Replay artifacts** live in `output/runs/` and are excluded from git.

---

# “Done” definition (PR acceptance)

A PR implementing commits **1–14** is accepted when:

- ✅ `python scripts/run_regression.py --suite smoke --strict` passes.
- ✅ Final JSON validates against `services/schema/final_output.schema.json`.
- ✅ Stage boundaries are clean (`services/stage1`, `services/stage2`, `services/stage3`).
- ✅ Prompts are versioned under `prompts/` and loaded via `services/prompts/loader.py`.
- ✅ Docs exist for config, stages, IR, schema, replay, testing.

---

# Appendix — Repo grounding (why this plan matches your structure)

- The repo’s README describes a **3-stage pipeline** (Stage 1 OpenCV geometry → Stage 2 LLM discovery → Stage 3 agentic extraction with GPT-5.4-pro + Code Interpreter) and claims **95–99% extraction accuracy**, which this PR plan explicitly protects with golden regression tests. citeturn7search172
- Internal Teams chatter confirms this repo and the multi-stage + Code Interpreter approach as the intended framework for others to build on. citeturn7search142
