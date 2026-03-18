# Configuration

## Overview

Schematic-IQ centralizes all runtime configuration in `services/config/`. Defaults match current behavior exactly — adopting the config layer is a zero-behavior-change operation.

## Configuration Sources (priority order)

1. **CLI arguments / explicit overrides** (highest)
2. **Environment variables**
3. **config.yaml** (optional, if present in repo root)
4. **Built-in defaults** (lowest)

## Usage

```python
from services.config.load import load_config

config = load_config()

# Access settings
config.azure.openai_endpoint
config.stage1.kernel_length
config.stage2.num_runs
config.stage3.agent_model
config.pipeline_mode
```

## Environment Variables

| Variable | Config Path | Default |
|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | `azure.openai_endpoint` | — |
| `AZURE_OPENAI_API_VERSION` | `azure.openai_api_version` | `2024-12-01-preview` |
| `AZURE_OPENAI_MINI_DEPLOYMENT` | `azure.openai_mini_deployment` | `gpt-4o-mini` |
| `AZURE_AI_PROJECT_ENDPOINT` | `azure.ai_project_endpoint` | — |
| `DISCOVERY_RUNS` | `stage2.num_runs` | `3` |
| `DISCOVERY_MAX_TOKENS` | `stage2.max_tokens` | `14000` |
| `AGENT_NAME` | `stage3.agent_name` | `schematic-iq-extractor` |
| `AGENT_MODEL` | `stage3.agent_model` | `gpt-5.4-pro` |
| `PIPELINE_MODE` | `pipeline_mode` | `v1` |
| `OUTPUT_DIR` | `output_dir` | `output` |

## Optional YAML Config

Create `config.yaml` in the repo root:

```yaml
azure:
  openai_mini_deployment: gpt-4o-mini

stage2:
  num_runs: 3
  max_tokens: 14000
  temperature: 0.8

stage3:
  agent_name: schematic-iq-extractor
  agent_model: gpt-5.4-pro

pipeline_mode: v1
```

## Stage Configuration Details

### Stage 1 — OpenCV Geometry

All pixel thresholds scale dynamically based on image width (reference: 1536px). The config values are base values at reference scale.

### Stage 2 — Discovery

- `num_runs`: Number of independent LLM scans (union-merged)
- `max_tokens`: Max completion tokens per run
- `temperature`: LLM temperature (0.8 for discovery variance)

### Stage 3 — Agent Extraction

- `agent_model`: Foundry agent model (currently gpt-5.4-pro)
- `stream_timeout`: Max seconds to wait for agent response
- `max_retries`: Retry count for transient errors
